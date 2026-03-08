# FiveM Portal - Product Requirements Document

## Original Problem Statement
FiveM portal website with:
- Ability to queue to the server
- See how many players are ingame
- Apply for whitelist and jobs directly on the website
- Steam login integration using Steam Web API

## User Personas
1. **Regular Players** - Want to join server queue, apply for whitelist
2. **Applicants** - Submit detailed applications for whitelist/jobs
3. **VIP Members** - Priority queue access
4. **Administrators** - Review applications, manage queue, manage users

## Core Requirements (Static)
- Steam OpenID authentication
- Real-time server queue system with position, ETA, priority
- Whitelist application system with detailed forms
- Job application system (Police, EMS, Mechanic, etc.)
- Admin panel for application review and queue management
- Neon green cyberpunk-themed UI

## What's Been Implemented (March 8, 2026)

### Backend (FastAPI + MongoDB)
- [x] Steam OpenID authentication with JWT tokens
- [x] User management (VIP/Admin flags)
- [x] Queue system with position calculation, ETA, priority
- [x] Application system (whitelist + jobs)
- [x] Admin endpoints for reviewing applications
- [x] Admin endpoints for queue/user management
- [x] Server status API (simulated player count)
- [x] Public stats API

### Frontend (React + Tailwind)
- [x] Landing page with hero, stats, features
- [x] Steam login integration
- [x] Queue page with join/leave functionality
- [x] Application forms (whitelist + job tabs)
- [x] User dashboard with profile, queue status, applications
- [x] Admin panel with tabs for applications, queue, users
- [x] Neon green cyberpunk theme (#39FF14)
- [x] Glass morphism effects
- [x] Responsive design

## Prioritized Backlog

### P0 (Critical) - Completed
- Steam authentication ✅
- Queue system ✅
- Application system ✅
- Admin panel ✅

### P1 (Important) - Future
- Real FiveM server integration (replace simulated data)
- WebSocket for real-time queue updates
- Email notifications for application status
- Discord webhook integration

### P2 (Nice to Have) - Future
- Application templates
- Queue position history/analytics
- Multi-language support
- Dark/light theme toggle

## Technical Notes
- Player count is currently simulated (42/64)
- Server status always shows online for demo
- Steam API key stored in backend .env
- Colors easily customizable via CSS variables in index.css

## Next Tasks
1. Connect to real FiveM server for live player data
2. Implement WebSocket for real-time queue updates
3. Add Discord webhook for application notifications
4. Add admin notification when new applications arrive
