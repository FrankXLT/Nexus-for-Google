#!/bin/bash
set -e

# Nexus V3 DevOps Shell

NEXUS_ROOT="/opt/nexus"
SHARED_DIR="$NEXUS_ROOT/shared"
CURRENT_DIR="$NEXUS_ROOT/current"
RELEASES_DIR="$NEXUS_ROOT/releases"
ENV_FILE="$SHARED_DIR/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[NEXUS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

setup_env() {
    if [ ! -f "$ENV_FILE" ]; then
        log "Initializing $ENV_FILE..."
        mkdir -p "$SHARED_DIR"
        read -p "Enter NEXUS_HMAC_SECRET: " hmac_secret
        read -p "Enter NEXUS_API_KEY (Gemini): " api_key
        read -p "Enter NEXUS_PUBLIC_DOMAIN (e.g., nexus.mydomain.com): " public_domain
        read -p "Enter AUTHORIZED_EMAILS (comma separated): " auth_emails
        read -p "Enter GOOGLE_CLIENT_ID: " google_client_id
        read -p "Enter DOCAI_PROJECT_ID: " docai_project_id
        read -p "Enter DOCAI_LOCATION (default 'us'): " docai_location
        docai_location=${docai_location:-us}
        read -p "Enter DOCAI_PROCESSOR_ID: " docai_processor_id
        
        cat <<EOF > "$ENV_FILE"
NEXUS_HMAC_SECRET="$hmac_secret"
NEXUS_API_KEY="$api_key"
NEXUS_PUBLIC_DOMAIN="$public_domain"
AUTHORIZED_EMAILS="$auth_emails"
GOOGLE_CLIENT_ID="$google_client_id"
DOCAI_PROJECT_ID="$docai_project_id"
DOCAI_LOCATION="$docai_location"
DOCAI_PROCESSOR_ID="$docai_processor_id"
EOF
        log ".env file created securely."
    else
        log ".env file already exists."
    fi
    source "$ENV_FILE"
}

provision() {
    log "Starting Provisioning Process..."
    
    # 1. GCP Authentication Check
    if ! gcloud auth print-access-token &> /dev/null; then
        error "gcloud is not authenticated. Please run 'gcloud auth login' first."
    fi

    # 2. Setup Env
    setup_env

    # 3. System Dependencies
    log "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv sqlite3 nodejs npm debian-keyring debian-archive-keyring apt-transport-https curl ufw
    
    # Install Caddy
    if ! command -v caddy &> /dev/null; then
        log "Installing Caddy..."
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
        sudo apt-get update
        sudo apt-get install -y caddy
    fi

    # 4. Directory Structure
    log "Creating directory structure..."
    sudo mkdir -p "$SHARED_DIR/data" "$SHARED_DIR/logs" "$SHARED_DIR/tmp" "$RELEASES_DIR"
    sudo chown -R $USER:$USER "$NEXUS_ROOT"

    # 5. Swap File (2GB)
    if [ ! -f "/swapfile" ]; then
        log "Creating 2GB swap file..."
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    else
        log "Swap file already exists."
    fi

    # 6. Firewall
    log "Configuring UFW..."
    sudo ufw allow 22/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable

    # 7. GCP Pub/Sub Provisioning
    log "Provisioning GCP Pub/Sub..."
    TOPIC_NAME="nexus-incoming-topic"
    SUB_NAME="nexus-incoming-sub"
    PUSH_ENDPOINT="https://${NEXUS_PUBLIC_DOMAIN}/webhook/gmail"

    if ! gcloud pubsub topics describe $TOPIC_NAME &> /dev/null; then
        gcloud pubsub topics create $TOPIC_NAME
        log "Created topic $TOPIC_NAME"
    fi

    if ! gcloud pubsub subscriptions describe $SUB_NAME &> /dev/null; then
        gcloud pubsub subscriptions create $SUB_NAME \
            --topic=$TOPIC_NAME \
            --push-endpoint="$PUSH_ENDPOINT"
        log "Created push subscription $SUB_NAME pointing to $PUSH_ENDPOINT"
    else
        # Update push endpoint just in case
        gcloud pubsub subscriptions modify-push-config $SUB_NAME --push-endpoint="$PUSH_ENDPOINT"
        log "Updated push subscription $SUB_NAME endpoint to $PUSH_ENDPOINT"
    fi

    log "Provisioning Complete."
}

deploy() {
    log "Starting Zero-Downtime Deployment..."
    
    source "$ENV_FILE"

    # 1. Prepare new release directory
    RELEASE_TAG=$(date +%Y%m%d_%H%M%S)
    RELEASE_PATH="$RELEASES_DIR/$RELEASE_TAG"
    mkdir -p "$RELEASE_PATH"
    
    log "Copying codebase to $RELEASE_PATH..."
    # Copy all files from current repo, excluding .git
    rsync -a --exclude='.git' ./ "$RELEASE_PATH/"
    
    # 2. SPA Build
    log "Building SPA..."
    if [ -f "$RELEASE_PATH/frontend/package.json" ]; then
        (cd "$RELEASE_PATH/frontend" && npm install && npm run build)
    else
        log "package.json not found, creating UI Stub..."
        mkdir -p "$RELEASE_PATH/frontend/dist"
        echo "<h1>Nexus V3 UI Stub</h1>" > "$RELEASE_PATH/frontend/dist/index.html"
    fi

    # 3. Python Virtual Environment
    log "Setting up Python venv..."
    python3 -m venv "$RELEASE_PATH/venv"
    source "$RELEASE_PATH/venv/bin/activate"
    pip install -r "$RELEASE_PATH/requirements.txt"

    # 4. Database Initialization
    log "Running database initialization..."
    export NEXUS_SHARED_DIR="$SHARED_DIR"
    python "$RELEASE_PATH/backend/db_init.py"
    deactivate

    # 5. Update Symlink
    log "Updating current symlink..."
    ln -sfn "$RELEASE_PATH" "$CURRENT_DIR"

    # 6. Setup Caddy
    log "Configuring Caddy..."
    cat <<EOF | sudo tee /etc/caddy/Caddyfile
${NEXUS_PUBLIC_DOMAIN} {
    root * ${CURRENT_DIR}/frontend/dist
    file_server
    
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /webhook/* {
        reverse_proxy 127.0.0.1:8000
    }
}
EOF
    sudo systemctl reload caddy

    # 7. Setup Systemd
    log "Configuring systemd..."
    cat <<EOF | sudo tee /etc/systemd/system/nexus.service
[Unit]
Description=Nexus V3 Daemon
After=network.target

[Service]
User=$USER
WorkingDirectory=${CURRENT_DIR}
Environment="PATH=${CURRENT_DIR}/venv/bin"
EnvironmentFile=${ENV_FILE}
Environment="NEXUS_SHARED_DIR=${SHARED_DIR}"
ExecStart=${CURRENT_DIR}/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable nexus.service
    sudo systemctl restart nexus.service

    # 8. Log Rotation
    log "Configuring Logrotate..."
    cat <<EOF | sudo tee /etc/logrotate.d/nexus
${SHARED_DIR}/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF

    log "Deployment Complete. $RELEASE_TAG is now live."
}

show_menu() {
    echo "=============================="
    echo "       NEXUS V3 DEVOPS        "
    echo "=============================="
    echo "1. Provision Infrastructure"
    echo "2. Deploy Application"
    echo "3. Exit"
    echo "=============================="
    read -p "Select an option: " opt
    case $opt in
        1) provision ;;
        2) deploy ;;
        3) exit 0 ;;
        *) error "Invalid option" ;;
    esac
}

case "$1" in
    --provision) provision ;;
    --deploy) deploy ;;
    --auth-tunnel) log "Auth tunnel placeholder" ;;
    --health) log "Health check placeholder" ;;
    --backup) log "Backup placeholder" ;;
    --clean) log "Clean placeholder" ;;
    "") show_menu ;;
    *) error "Unknown argument: $1" ;;
esac