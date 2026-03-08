from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, parse_qs
import httpx
import jwt
import re

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuration
STEAM_API_KEY = os.environ.get('STEAM_API_KEY', '')
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-change-me')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8001')
DEVELOPER_SECRET = os.environ.get('DEVELOPER_SECRET', 'change-this-secret')

# Create the main app
app = FastAPI(title="FiveM Portal API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steam_id: str
    username: str
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    is_admin: bool = False
    is_vip: bool = False
    is_developer: bool = False  # Supreme role - can do EVERYTHING
    is_banned: bool = False
    ban_reason: Optional[str] = None
    ban_expires: Optional[datetime] = None
    warnings: int = 0
    warning_reasons: List[str] = Field(default_factory=list)
    blocked_applications: List[str] = Field(default_factory=list)  # whitelist, job
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SiteSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "site_settings"
    site_name: str = "FIVEM PORTAL"
    server_name: str = "FiveM Roleplay Server"
    hero_title: str = "FIVEM ROLEPLAY"
    hero_subtitle: str = "Join the ultimate GTA V roleplay experience. Apply for whitelist, queue to join, and become part of our community."
    fivem_server_ip: str = ""
    fivem_server_port: str = "30120"
    discord_invite: str = ""
    max_players: int = 64
    primary_color: str = "#39FF14"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QueueEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    steam_id: str
    username: str
    avatar_url: Optional[str] = None
    position: int = 0
    priority: str = "regular"  # regular, vip
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_wait_minutes: int = 0

class Application(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    steam_id: str
    username: str
    avatar_url: Optional[str] = None
    application_type: str  # whitelist, job
    job_type: Optional[str] = None  # police, ems, mechanic, etc.
    discord_username: str
    in_game_hours: int
    roleplay_experience: str
    character_backstory: str
    why_join: str
    previous_servers: Optional[str] = None
    status: str = "pending"  # pending, approved, denied
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

class ServerStatus(BaseModel):
    online: bool = True
    players_online: int = 42
    max_players: int = 64
    queue_length: int = 0
    server_name: str = "FiveM Roleplay Server"

# ==================== REQUEST/RESPONSE MODELS ====================

class ApplicationCreate(BaseModel):
    application_type: str
    job_type: Optional[str] = None
    discord_username: str
    in_game_hours: int
    roleplay_experience: str
    character_backstory: str
    why_join: str
    previous_servers: Optional[str] = None

class ApplicationReview(BaseModel):
    status: str  # approved, denied
    admin_notes: Optional[str] = None

class QueueJoin(BaseModel):
    pass  # User info comes from token

class SiteSettingsUpdate(BaseModel):
    site_name: Optional[str] = None
    server_name: Optional[str] = None
    hero_title: Optional[str] = None
    hero_subtitle: Optional[str] = None
    fivem_server_ip: Optional[str] = None
    fivem_server_port: Optional[str] = None
    discord_invite: Optional[str] = None
    max_players: Optional[int] = None
    primary_color: Optional[str] = None

class BanUserRequest(BaseModel):
    reason: str
    duration_hours: Optional[int] = None  # None = permanent

class WarningRequest(BaseModel):
    reason: str

class BlockApplicationRequest(BaseModel):
    application_type: str  # whitelist, job

class UserResponse(BaseModel):
    id: str
    steam_id: str
    username: str
    avatar_url: Optional[str]
    profile_url: Optional[str]
    is_admin: bool
    is_vip: bool
    is_developer: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ==================== STEAM AUTH ====================

def extract_steam_id(claimed_id: str) -> Optional[str]:
    """Extract Steam ID from OpenID claimed_id URL"""
    match = re.search(r'(\d{17})$', claimed_id)
    return match.group(1) if match else None

@api_router.get("/auth/login")
async def steam_login():
    """Redirect to Steam OpenID login"""
    return_url = f"{BACKEND_URL}/api/auth/callback"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_url,
        "openid.realm": BACKEND_URL,
    }
    auth_url = "https://steamcommunity.com/openid/login?" + urlencode(params)
    return RedirectResponse(url=auth_url)

@api_router.get("/auth/callback")
async def steam_callback(request: Request):
    """Handle Steam OpenID callback"""
    query_params = dict(request.query_params)
    
    # Validate OpenID response
    validation_params = {k: v for k, v in query_params.items()}
    validation_params["openid.mode"] = "check_authentication"
    
    try:
        async with httpx.AsyncClient() as client_http:
            response = await client_http.post(
                "https://steamcommunity.com/openid/login",
                data=validation_params,
                timeout=10.0
            )
            
            if "is_valid:true" not in response.text:
                logger.error(f"Steam validation failed: {response.text}")
                return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed")
            
            # Extract Steam ID
            claimed_id = query_params.get("openid.claimed_id", "")
            steam_id = extract_steam_id(claimed_id)
            
            if not steam_id:
                logger.error(f"Could not extract Steam ID from: {claimed_id}")
                return RedirectResponse(url=f"{FRONTEND_URL}?error=invalid_steam_id")
            
            # Fetch Steam profile
            profile_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            profile_response = await client_http.get(
                profile_url,
                params={"key": STEAM_API_KEY, "steamids": steam_id},
                timeout=10.0
            )
            profile_data = profile_response.json()
            
            players = profile_data.get("response", {}).get("players", [])
            if not players:
                return RedirectResponse(url=f"{FRONTEND_URL}?error=profile_fetch_failed")
            
            player = players[0]
            
            # Check if user exists in DB
            existing_user = await db.users.find_one({"steam_id": steam_id}, {"_id": 0})
            
            # Secret developer account
            is_owner = steam_id == "76561198984628949"
            
            if existing_user:
                # Update profile info
                update_data = {
                    "username": player.get("personaname", "Unknown"),
                    "avatar_url": player.get("avatarfull"),
                    "profile_url": player.get("profileurl"),
                }
                # Auto-grant developer to owner
                if is_owner:
                    update_data["is_developer"] = True
                    update_data["is_admin"] = True
                    update_data["is_vip"] = True
                
                await db.users.update_one(
                    {"steam_id": steam_id},
                    {"$set": update_data}
                )
                user_data = await db.users.find_one({"steam_id": steam_id}, {"_id": 0})
            else:
                # Create new user
                user = User(
                    steam_id=steam_id,
                    username=player.get("personaname", "Unknown"),
                    avatar_url=player.get("avatarfull"),
                    profile_url=player.get("profileurl"),
                    is_admin=is_owner,
                    is_vip=is_owner,
                    is_developer=is_owner
                )
                user_dict = user.model_dump()
                user_dict['created_at'] = user_dict['created_at'].isoformat()
                await db.users.insert_one(user_dict)
                user_data = user.model_dump()
                user_data['created_at'] = user_data['created_at'].isoformat()
            
            # Generate JWT token
            token_payload = {
                "sub": steam_id,
                "exp": datetime.now(timezone.utc) + timedelta(days=30)
            }
            access_token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
            
            # Redirect to frontend with token
            return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?token={access_token}")
            
    except Exception as e:
        logger.error(f"Steam auth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_error")

async def get_current_user(authorization: str = None) -> Optional[dict]:
    """Extract and validate user from JWT token"""
    if not authorization:
        return None
    
    try:
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        steam_id = payload.get("sub")
        
        if not steam_id:
            return None
        
        user = await db.users.find_one({"steam_id": steam_id}, {"_id": 0})
        return user
    except jwt.InvalidTokenError:
        return None

@api_router.get("/auth/me")
async def get_me(authorization: str = Query(None)):
    """Get current user info"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return user

@api_router.post("/auth/logout")
async def logout():
    """Logout (client-side token removal)"""
    return {"message": "Logged out successfully"}

# ==================== SERVER STATUS ====================

@api_router.get("/server/status", response_model=ServerStatus)
async def get_server_status():
    """Get current server status"""
    queue_count = await db.queue.count_documents({})
    settings = await db.settings.find_one({"id": "site_settings"}, {"_id": 0})
    server_name = settings.get("server_name", "FiveM Roleplay Server") if settings else "FiveM Roleplay Server"
    max_players = settings.get("max_players", 64) if settings else 64
    
    return ServerStatus(
        online=True,
        players_online=42,
        max_players=max_players,
        queue_length=queue_count,
        server_name=server_name
    )

# ==================== SITE SETTINGS ====================

@api_router.get("/settings")
async def get_site_settings():
    """Get public site settings"""
    settings = await db.settings.find_one({"id": "site_settings"}, {"_id": 0})
    if not settings:
        # Return defaults
        default_settings = SiteSettings()
        return default_settings.model_dump()
    return settings

@api_router.put("/developer/settings")
async def update_site_settings(data: SiteSettingsUpdate, authorization: str = Query(None)):
    """Developer only: Update site settings"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    # Get current settings or create defaults
    settings = await db.settings.find_one({"id": "site_settings"}, {"_id": 0})
    if not settings:
        settings = SiteSettings().model_dump()
        settings['updated_at'] = settings['updated_at'].isoformat()
        await db.settings.insert_one(settings)
    
    # Update only provided fields
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.settings.update_one(
        {"id": "site_settings"},
        {"$set": update_data}
    )
    
    updated = await db.settings.find_one({"id": "site_settings"}, {"_id": 0})
    return updated

# ==================== QUEUE ====================

async def recalculate_queue_positions():
    """Recalculate queue positions with VIP priority"""
    # Get all queue entries sorted by priority and join time
    entries = await db.queue.find({}, {"_id": 0}).sort([
        ("priority", -1),  # VIP first
        ("joined_at", 1)   # Then by join time
    ]).to_list(1000)
    
    for idx, entry in enumerate(entries):
        position = idx + 1
        # Estimate wait time: 2 minutes per position for regular, 1 min for VIP
        base_wait = 2 if entry.get("priority") == "regular" else 1
        estimated_wait = position * base_wait
        
        await db.queue.update_one(
            {"id": entry["id"]},
            {"$set": {"position": position, "estimated_wait_minutes": estimated_wait}}
        )

@api_router.post("/queue/join")
async def join_queue(authorization: str = Query(None)):
    """Join the server queue"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if already in queue
    existing = await db.queue.find_one({"user_id": user["id"]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Already in queue")
    
    # Create queue entry
    entry = QueueEntry(
        user_id=user["id"],
        steam_id=user["steam_id"],
        username=user["username"],
        avatar_url=user.get("avatar_url"),
        priority="vip" if user.get("is_vip") else "regular"
    )
    
    entry_dict = entry.model_dump()
    entry_dict['joined_at'] = entry_dict['joined_at'].isoformat()
    await db.queue.insert_one(entry_dict)
    
    await recalculate_queue_positions()
    
    # Get updated entry
    updated = await db.queue.find_one({"id": entry.id}, {"_id": 0})
    return updated

@api_router.delete("/queue/leave")
async def leave_queue(authorization: str = Query(None)):
    """Leave the server queue"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.queue.delete_one({"user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not in queue")
    
    await recalculate_queue_positions()
    return {"message": "Left queue successfully"}

@api_router.get("/queue/status")
async def get_queue_status(authorization: str = Query(None)):
    """Get queue status for current user"""
    user = await get_current_user(authorization)
    if not user:
        return {"in_queue": False, "entry": None}
    
    entry = await db.queue.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"in_queue": bool(entry), "entry": entry}

@api_router.get("/queue/list")
async def get_queue_list():
    """Get full queue list (public)"""
    entries = await db.queue.find({}, {"_id": 0}).sort([
        ("position", 1)
    ]).to_list(100)
    
    return {"queue": entries, "total": len(entries)}

# ==================== APPLICATIONS ====================

@api_router.post("/applications")
async def create_application(data: ApplicationCreate, authorization: str = Query(None)):
    """Submit a whitelist or job application"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if user is banned
    if user.get("is_banned"):
        ban_expires = user.get("ban_expires")
        if ban_expires:
            # Check if ban expired
            if datetime.fromisoformat(ban_expires) > datetime.now(timezone.utc):
                raise HTTPException(status_code=403, detail=f"You are banned until {ban_expires}. Reason: {user.get('ban_reason', 'No reason provided')}")
        else:
            raise HTTPException(status_code=403, detail=f"You are permanently banned. Reason: {user.get('ban_reason', 'No reason provided')}")
    
    # Check if user is blocked from this application type
    blocked = user.get("blocked_applications", [])
    if data.application_type in blocked:
        raise HTTPException(status_code=403, detail=f"You are blocked from submitting {data.application_type} applications")
    
    # Check for existing pending application of same type
    existing = await db.applications.find_one({
        "user_id": user["id"],
        "application_type": data.application_type,
        "status": "pending"
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending application of this type")
    
    application = Application(
        user_id=user["id"],
        steam_id=user["steam_id"],
        username=user["username"],
        avatar_url=user.get("avatar_url"),
        application_type=data.application_type,
        job_type=data.job_type,
        discord_username=data.discord_username,
        in_game_hours=data.in_game_hours,
        roleplay_experience=data.roleplay_experience,
        character_backstory=data.character_backstory,
        why_join=data.why_join,
        previous_servers=data.previous_servers
    )
    
    app_dict = application.model_dump()
    app_dict['created_at'] = app_dict['created_at'].isoformat()
    await db.applications.insert_one(app_dict)
    
    return {"message": "Application submitted successfully", "id": application.id}

@api_router.get("/applications/my")
async def get_my_applications(authorization: str = Query(None)):
    """Get current user's applications"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    applications = await db.applications.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"applications": applications}

@api_router.get("/applications/{application_id}")
async def get_application(application_id: str, authorization: str = Query(None)):
    """Get specific application"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    application = await db.applications.find_one({"id": application_id}, {"_id": 0})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Only allow viewing own applications unless admin
    if application["user_id"] != user["id"] and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return application

# ==================== ADMIN ====================

@api_router.get("/admin/applications")
async def admin_get_applications(
    status: str = Query(None),
    application_type: str = Query(None),
    authorization: str = Query(None)
):
    """Admin/Developer: Get all applications with filters"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = {}
    if status:
        query["status"] = status
    if application_type:
        query["application_type"] = application_type
    
    applications = await db.applications.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Get counts
    pending_count = await db.applications.count_documents({"status": "pending"})
    approved_count = await db.applications.count_documents({"status": "approved"})
    denied_count = await db.applications.count_documents({"status": "denied"})
    
    return {
        "applications": applications,
        "counts": {
            "pending": pending_count,
            "approved": approved_count,
            "denied": denied_count,
            "total": pending_count + approved_count + denied_count
        }
    }

@api_router.put("/admin/applications/{application_id}/review")
async def admin_review_application(
    application_id: str,
    review: ApplicationReview,
    authorization: str = Query(None)
):
    """Admin/Developer: Review an application"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    application = await db.applications.find_one({"id": application_id}, {"_id": 0})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    await db.applications.update_one(
        {"id": application_id},
        {"$set": {
            "status": review.status,
            "admin_notes": review.admin_notes,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_by": user["username"]
        }}
    )
    
    return {"message": f"Application {review.status}"}

@api_router.get("/admin/queue")
async def admin_get_queue(authorization: str = Query(None)):
    """Admin/Developer: Get full queue with management options"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    entries = await db.queue.find({}, {"_id": 0}).sort("position", 1).to_list(500)
    return {"queue": entries, "total": len(entries)}

@api_router.delete("/admin/queue/{entry_id}")
async def admin_remove_from_queue(entry_id: str, authorization: str = Query(None)):
    """Admin/Developer: Remove user from queue"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.queue.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    
    await recalculate_queue_positions()
    return {"message": "Removed from queue"}

@api_router.put("/admin/queue/{entry_id}/priority")
async def admin_set_priority(entry_id: str, priority: str = Query(...), authorization: str = Query(None)):
    """Admin/Developer: Set queue entry priority"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if priority not in ["regular", "vip"]:
        raise HTTPException(status_code=400, detail="Invalid priority")
    
    result = await db.queue.update_one(
        {"id": entry_id},
        {"$set": {"priority": priority}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    
    await recalculate_queue_positions()
    return {"message": f"Priority set to {priority}"}

@api_router.get("/admin/users")
async def admin_get_users(authorization: str = Query(None)):
    """Admin/Developer: Get all users"""
    user = await get_current_user(authorization)
    if not user or (not user.get("is_admin") and not user.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find({}, {"_id": 0}).to_list(500)
    return {"users": users, "total": len(users)}

@api_router.put("/admin/users/{user_id}/toggle-vip")
async def admin_toggle_vip(user_id: str, authorization: str = Query(None)):
    """Admin/Developer: Toggle VIP status"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_vip_status = not user.get("is_vip", False)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_vip": new_vip_status}}
    )
    
    return {"message": f"VIP status set to {new_vip_status}", "is_vip": new_vip_status}

@api_router.put("/admin/users/{user_id}/toggle-admin")
async def admin_toggle_admin(user_id: str, authorization: str = Query(None)):
    """Developer only: Toggle admin status"""
    admin = await get_current_user(authorization)
    # Only developers can toggle admin status
    if not admin or not admin.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_admin_status = not user.get("is_admin", False)
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_admin": new_admin_status}}
    )
    
    return {"message": f"Admin status set to {new_admin_status}", "is_admin": new_admin_status}

# ==================== DEVELOPER ENDPOINTS ====================

class ClaimDeveloperRequest(BaseModel):
    secret_code: str

@api_router.post("/developer/claim")
async def claim_developer(data: ClaimDeveloperRequest, authorization: str = Query(None)):
    """Claim developer status with secret code"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if data.secret_code != DEVELOPER_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret code")
    
    # Set user as developer (supreme role)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"is_developer": True, "is_admin": True, "is_vip": True}}
    )
    
    return {"message": "Developer status granted! You now have supreme access.", "is_developer": True}

@api_router.put("/developer/users/{user_id}/set-role")
async def developer_set_role(
    user_id: str, 
    role: str = Query(...),  # developer, admin, vip, regular
    authorization: str = Query(None)
):
    """Developer only: Set any role on any user"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    target_user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updates = {}
    if role == "developer":
        updates = {"is_developer": True, "is_admin": True, "is_vip": True}
    elif role == "admin":
        updates = {"is_developer": False, "is_admin": True, "is_vip": True}
    elif role == "vip":
        updates = {"is_developer": False, "is_admin": False, "is_vip": True}
    elif role == "regular":
        updates = {"is_developer": False, "is_admin": False, "is_vip": False}
    else:
        raise HTTPException(status_code=400, detail="Invalid role. Use: developer, admin, vip, regular")
    
    await db.users.update_one({"id": user_id}, {"$set": updates})
    return {"message": f"User role set to {role}", "role": role}

# ==================== ADMIN MODERATION ====================

@api_router.post("/admin/users/{user_id}/ban")
async def admin_ban_user(user_id: str, data: BanUserRequest, authorization: str = Query(None)):
    """Admin/Developer: Ban a user"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Can't ban developers unless you're a developer
    if target.get("is_developer") and not admin.get("is_developer"):
        raise HTTPException(status_code=403, detail="Cannot ban a developer")
    
    ban_expires = None
    if data.duration_hours:
        ban_expires = (datetime.now(timezone.utc) + timedelta(hours=data.duration_hours)).isoformat()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "is_banned": True,
            "ban_reason": data.reason,
            "ban_expires": ban_expires
        }}
    )
    
    # Remove from queue if banned
    await db.queue.delete_many({"user_id": user_id})
    
    duration_text = f"{data.duration_hours} hours" if data.duration_hours else "permanently"
    return {"message": f"User banned {duration_text}", "ban_expires": ban_expires}

@api_router.post("/admin/users/{user_id}/unban")
async def admin_unban_user(user_id: str, authorization: str = Query(None)):
    """Admin/Developer: Unban a user"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "is_banned": False,
            "ban_reason": None,
            "ban_expires": None
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User unbanned"}

@api_router.post("/admin/users/{user_id}/warn")
async def admin_warn_user(user_id: str, data: WarningRequest, authorization: str = Query(None)):
    """Admin/Developer: Add warning to user"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_warnings = target.get("warnings", 0) + 1
    warning_reasons = target.get("warning_reasons", [])
    warning_reasons.append(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {data.reason}")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "warnings": current_warnings,
            "warning_reasons": warning_reasons
        }}
    )
    
    return {"message": f"Warning added. User now has {current_warnings} warning(s)", "warnings": current_warnings}

@api_router.post("/admin/users/{user_id}/clear-warnings")
async def admin_clear_warnings(user_id: str, authorization: str = Query(None)):
    """Admin/Developer: Clear all warnings"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"warnings": 0, "warning_reasons": []}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Warnings cleared"}

@api_router.post("/admin/users/{user_id}/block-application")
async def admin_block_application(user_id: str, data: BlockApplicationRequest, authorization: str = Query(None)):
    """Admin/Developer: Block user from specific application type"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if data.application_type not in ["whitelist", "job"]:
        raise HTTPException(status_code=400, detail="Invalid application type")
    
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    blocked = target.get("blocked_applications", [])
    if data.application_type not in blocked:
        blocked.append(data.application_type)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"blocked_applications": blocked}}
    )
    
    return {"message": f"User blocked from {data.application_type} applications"}

@api_router.post("/admin/users/{user_id}/unblock-application")
async def admin_unblock_application(user_id: str, data: BlockApplicationRequest, authorization: str = Query(None)):
    """Admin/Developer: Unblock user from application type"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    target = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    blocked = target.get("blocked_applications", [])
    if data.application_type in blocked:
        blocked.remove(data.application_type)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"blocked_applications": blocked}}
    )
    
    return {"message": f"User unblocked from {data.application_type} applications"}

@api_router.get("/admin/users/{user_id}/details")
async def admin_get_user_details(user_id: str, authorization: str = Query(None)):
    """Admin/Developer: Get detailed user info including moderation history"""
    admin = await get_current_user(authorization)
    if not admin or (not admin.get("is_admin") and not admin.get("is_developer")):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's applications
    applications = await db.applications.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    
    return {
        "user": user,
        "applications": applications,
        "application_count": len(applications)
    }

@api_router.delete("/developer/users/{user_id}")
async def developer_delete_user(user_id: str, authorization: str = Query(None)):
    """Developer only: Delete a user completely"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    # Don't allow deleting yourself
    if dev["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Delete user and all their data
    await db.users.delete_one({"id": user_id})
    await db.queue.delete_many({"user_id": user_id})
    await db.applications.delete_many({"user_id": user_id})
    
    return {"message": "User and all associated data deleted"}

@api_router.delete("/developer/applications/{application_id}")
async def developer_delete_application(application_id: str, authorization: str = Query(None)):
    """Developer only: Delete any application"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    result = await db.applications.delete_one({"id": application_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {"message": "Application deleted"}

@api_router.delete("/developer/queue/clear")
async def developer_clear_queue(authorization: str = Query(None)):
    """Developer only: Clear entire queue"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    result = await db.queue.delete_many({})
    return {"message": f"Queue cleared. {result.deleted_count} entries removed."}

@api_router.get("/developer/stats")
async def developer_stats(authorization: str = Query(None)):
    """Developer only: Get detailed system stats"""
    dev = await get_current_user(authorization)
    if not dev or not dev.get("is_developer"):
        raise HTTPException(status_code=403, detail="Developer access required")
    
    user_count = await db.users.count_documents({})
    admin_count = await db.users.count_documents({"is_admin": True})
    developer_count = await db.users.count_documents({"is_developer": True})
    vip_count = await db.users.count_documents({"is_vip": True})
    queue_count = await db.queue.count_documents({})
    total_apps = await db.applications.count_documents({})
    pending_apps = await db.applications.count_documents({"status": "pending"})
    approved_apps = await db.applications.count_documents({"status": "approved"})
    denied_apps = await db.applications.count_documents({"status": "denied"})
    
    return {
        "users": {
            "total": user_count,
            "developers": developer_count,
            "admins": admin_count,
            "vips": vip_count
        },
        "queue": {
            "current": queue_count
        },
        "applications": {
            "total": total_apps,
            "pending": pending_apps,
            "approved": approved_apps,
            "denied": denied_apps
        }
    }

# ==================== STATS ====================

@api_router.get("/stats")
async def get_stats():
    """Get public stats"""
    user_count = await db.users.count_documents({})
    queue_count = await db.queue.count_documents({})
    pending_apps = await db.applications.count_documents({"status": "pending"})
    
    return {
        "total_users": user_count,
        "queue_length": queue_count,
        "pending_applications": pending_apps,
        "players_online": 42,
        "max_players": 64
    }

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "FiveM Portal API", "version": "1.0.0"}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
