#!/bin/bash

#######################################################################
#                    FiveM Portal Installation Script                   #
#                         For Ubuntu 24.04 LTS                          #
#######################################################################

set -e

# Färger för output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           FiveM Portal - Installationsskript                  ║"
    echo "║                    Ubuntu 24.04 LTS                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}[STEG]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[VARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[FEL]${NC} $1"
}

#######################################################################
#                         KONFIGURATION                                #
#######################################################################

# Fyll i dessa värden innan du kör scriptet!
DOMAIN="din-doman.se"
GITHUB_REPO="https://github.com/DITT-ANVANDARNAMN/DITT-REPO.git"
APP_NAME="fivem-portal"

# Databas
DB_NAME="fivem_portal"

# Steam API (din nyckel)
STEAM_API_KEY="DIN_STEAM_API_KEY"

# Säkerhetsnycklar (generera egna!)
JWT_SECRET="GENERERA_MED_openssl_rand_-hex_32"
DEVELOPER_SECRET="DIN_HEMLIGA_DEV_KOD"

# SSL
ENABLE_SSL="yes"
EMAIL_FOR_SSL="din-email@example.com"

#######################################################################
#                      AUTOMATISKA VARIABLER                           #
#######################################################################

APP_ROOT="/var/www/${APP_NAME}"
BACKEND_DIR="${APP_ROOT}/backend"
FRONTEND_DIR="${APP_ROOT}/frontend"
MONGO_URL="mongodb://localhost:27017"

if [ "$ENABLE_SSL" = "yes" ]; then
    SITE_URL="https://${DOMAIN}"
else
    SITE_URL="http://${DOMAIN}"
fi

#######################################################################
#                      VALIDERING AV CONFIG                            #
#######################################################################

validate_config() {
    print_step "Validerar konfiguration..."
    
    local errors=0
    
    if [ "$DOMAIN" = "din-doman.se" ]; then
        print_error "Du måste ändra DOMAIN variabeln!"
        errors=$((errors + 1))
    fi
    
    if [[ "$GITHUB_REPO" == *"DITT-ANVANDARNAMN"* ]]; then
        print_error "Du måste ändra GITHUB_REPO variabeln!"
        errors=$((errors + 1))
    fi
    
    if [ "$STEAM_API_KEY" = "DIN_STEAM_API_KEY" ]; then
        print_error "Du måste ändra STEAM_API_KEY variabeln!"
        errors=$((errors + 1))
    fi
    
    if [[ "$JWT_SECRET" == *"GENERERA"* ]]; then
        print_error "Du måste generera en JWT_SECRET!"
        print_warning "Kör: openssl rand -hex 32"
        errors=$((errors + 1))
    fi
    
    if [ "$EMAIL_FOR_SSL" = "din-email@example.com" ] && [ "$ENABLE_SSL" = "yes" ]; then
        print_error "Du måste ändra EMAIL_FOR_SSL för SSL-certifikat!"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        echo ""
        print_error "Rätta till $errors fel i konfigurationen ovan!"
        print_warning "Öppna detta script och ändra variablerna i KONFIGURATION-sektionen."
        exit 1
    fi
    
    print_success "Konfiguration validerad!"
}

#######################################################################
#                      INSTALLATION                                    #
#######################################################################

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Detta script måste köras som root!"
        print_warning "Kör: sudo bash $0"
        exit 1
    fi
}

install_dependencies() {
    print_step "Installerar systempaket..."
    
    apt update
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        git \
        curl \
        gnupg \
        ufw
    
    print_success "Systempaket installerade!"
}

install_nodejs() {
    print_step "Installerar Node.js 20..."
    
    if command -v node &> /dev/null; then
        print_warning "Node.js redan installerat: $(node -v)"
    else
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt install -y nodejs
        npm install -g yarn
        print_success "Node.js $(node -v) installerat!"
    fi
}

install_mongodb() {
    print_step "Installerar MongoDB..."
    
    if systemctl is-active --quiet mongod; then
        print_warning "MongoDB redan installerat och kör!"
    else
        curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
            gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
        
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
            tee /etc/apt/sources.list.d/mongodb-org-7.0.list
        
        apt update
        apt install -y mongodb-org
        
        systemctl start mongod
        systemctl enable mongod
        
        print_success "MongoDB installerat och startat!"
    fi
}

clone_repository() {
    print_step "Klonar repository..."
    
    mkdir -p "$APP_ROOT"
    
    if [ -d "${APP_ROOT}/.git" ]; then
        print_warning "Repository finns redan, uppdaterar..."
        cd "$APP_ROOT"
        git pull
    else
        git clone "$GITHUB_REPO" "$APP_ROOT"
    fi
    
    print_success "Repository klonat till $APP_ROOT"
}

setup_backend() {
    print_step "Konfigurerar backend..."
    
    cd "$BACKEND_DIR"
    
    # Skapa virtuell miljö
    python3 -m venv venv
    source venv/bin/activate
    
    # Installera dependencies
    pip install --upgrade pip
    pip install -r requirements.txt 2>/dev/null || \
    pip install fastapi uvicorn motor python-dotenv httpx pyjwt aiohttp
    
    # Skapa .env fil
    cat > .env << EOF
MONGO_URL="${MONGO_URL}"
DB_NAME="${DB_NAME}"
CORS_ORIGINS="*"
STEAM_API_KEY="${STEAM_API_KEY}"
JWT_SECRET="${JWT_SECRET}"
FRONTEND_URL="${SITE_URL}"
BACKEND_URL="${SITE_URL}"
DEVELOPER_SECRET="${DEVELOPER_SECRET}"
EOF
    
    deactivate
    
    print_success "Backend konfigurerad!"
}

setup_frontend() {
    print_step "Bygger frontend..."
    
    cd "$FRONTEND_DIR"
    
    # Skapa .env fil
    cat > .env << EOF
REACT_APP_BACKEND_URL=${SITE_URL}
EOF
    
    # Installera och bygg
    yarn install
    yarn build
    
    print_success "Frontend byggd!"
}

setup_systemd() {
    print_step "Skapar systemd-tjänst för backend..."
    
    cat > /etc/systemd/system/fivem-backend.service << EOF
[Unit]
Description=FiveM Portal Backend
After=network.target mongod.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${BACKEND_DIR}
Environment="PATH=${BACKEND_DIR}/venv/bin"
ExecStart=${BACKEND_DIR}/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable fivem-backend
    systemctl start fivem-backend
    
    print_success "Backend-tjänst skapad och startad!"
}

setup_nginx() {
    print_step "Konfigurerar Nginx..."
    
    cat > /etc/nginx/sites-available/fivem-portal << EOF
server {
    listen 80;
    server_name ${DOMAIN};

    # Frontend - statiska filer
    root ${FRONTEND_DIR}/build;
    index index.html;

    # Gzip komprimering
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    
    # Aktivera site
    ln -sf /etc/nginx/sites-available/fivem-portal /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Testa och starta om
    nginx -t
    systemctl restart nginx
    
    print_success "Nginx konfigurerad!"
}

setup_ssl() {
    if [ "$ENABLE_SSL" = "yes" ]; then
        print_step "Installerar SSL-certifikat med Let's Encrypt..."
        
        apt install -y certbot python3-certbot-nginx
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL_FOR_SSL"
        
        print_success "SSL-certifikat installerat!"
    else
        print_warning "SSL är inaktiverat. Siten körs på HTTP."
    fi
}

setup_firewall() {
    print_step "Konfigurerar brandvägg..."
    
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    
    print_success "Brandvägg konfigurerad!"
}

set_permissions() {
    print_step "Sätter filrättigheter..."
    
    chown -R www-data:www-data "$APP_ROOT"
    chmod -R 755 "$APP_ROOT"
    
    print_success "Filrättigheter satta!"
}

print_summary() {
    echo ""
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║              INSTALLATION SLUTFÖRD!                           ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "Din FiveM Portal är nu tillgänglig på:"
    echo -e "${GREEN}  ${SITE_URL}${NC}"
    echo ""
    echo -e "Viktiga kommandon:"
    echo -e "  ${BLUE}sudo systemctl status fivem-backend${NC}  - Kolla backend-status"
    echo -e "  ${BLUE}sudo systemctl restart fivem-backend${NC} - Starta om backend"
    echo -e "  ${BLUE}sudo journalctl -u fivem-backend -f${NC}  - Visa backend-loggar"
    echo -e "  ${BLUE}sudo systemctl status nginx${NC}          - Kolla nginx-status"
    echo ""
    echo -e "För att bli Developer:"
    echo -e "  1. Logga in med Steam på ${SITE_URL}"
    echo -e "  2. Gå till ${SITE_URL}/developer"
    echo -e "  3. Ange koden: ${YELLOW}${DEVELOPER_SECRET}${NC}"
    echo ""
    echo -e "Filer:"
    echo -e "  Backend:  ${BACKEND_DIR}"
    echo -e "  Frontend: ${FRONTEND_DIR}"
    echo -e "  Nginx:    /etc/nginx/sites-available/fivem-portal"
    echo ""
}

#######################################################################
#                         HUVUDPROGRAM                                 #
#######################################################################

main() {
    print_banner
    check_root
    validate_config
    
    echo ""
    echo -e "${YELLOW}Detta script kommer att installera:${NC}"
    echo "  - Python 3, pip, venv"
    echo "  - Node.js 20, Yarn"
    echo "  - MongoDB 7.0"
    echo "  - Nginx"
    echo "  - Let's Encrypt SSL (om aktiverat)"
    echo ""
    echo -e "Domän: ${GREEN}${DOMAIN}${NC}"
    echo -e "App:   ${GREEN}${APP_NAME}${NC}"
    echo ""
    
    read -p "Vill du fortsätta? (j/n): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        print_warning "Installation avbruten."
        exit 0
    fi
    
    install_dependencies
    install_nodejs
    install_mongodb
    clone_repository
    setup_backend
    setup_frontend
    set_permissions
    setup_systemd
    setup_nginx
    setup_ssl
    setup_firewall
    
    print_summary
}

# Kör huvudprogrammet
main "$@"
