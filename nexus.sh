#!/bin/bash
# nexus.sh - Local Workstation DevSecOps CLI for Nexus V3

set -e
set -o pipefail
export CLOUDSDK_COMPUTE_USE_OPENSSH=1

# Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}      NEXUS V3: MASTER CONTROL & DEPLOYMENT         ${NC}"
echo -e "${CYAN}====================================================${NC}"

# Ensure gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud CLI (gcloud) is not installed.${NC}"
    exit 1
fi

load_env() {
    if [ ! -f ".nexus_env" ]; then
        echo -e "${RED}Error: .nexus_env file not found. Run Option 1 (Provision) first.${NC}"
        exit 1
    fi
    TARGET_VM=$(grep "^TARGET_VM=" .nexus_env | cut -d'=' -f2 | tr -d '\r')
    TARGET_ZONE=$(grep "^TARGET_ZONE=" .nexus_env | cut -d'=' -f2 | tr -d '\r')
    PROJECT_ID=$(grep "^PROJECT_ID=" .nexus_env | cut -d'=' -f2 | tr -d '\r')
    NEXUS_PUBLIC_DOMAIN=$(grep "^NEXUS_PUBLIC_DOMAIN=" .nexus_env | cut -d'=' -f2 | tr -d '\r')
    CLOUDFLARE_API_TOKEN=$(grep "^CLOUDFLARE_API_TOKEN=" .nexus_env | cut -d'=' -f2 | tr -d '\r' || true)
}

provision() {
    echo -e "\n${CYAN}[1/6] Authentication & Project Setup...${NC}"
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    if [ -z "$ACTIVE_ACCOUNT" ]; then
        gcloud auth login
    fi

    IFS=$'\n' read -r -d '' -a projects < <( gcloud projects list --format="value(projectId,name)" && printf '\0' )
    for i in "${!projects[@]}"; do echo "[$i] ${projects[$i]}"; done
    read -p "Select Project number: " projIdx
    PROJECT_ID=$(echo "${projects[$projIdx]}" | awk '{print $1}')
    gcloud config set project "$PROJECT_ID" --quiet

    ZONE="us-central1-a"
    read -p "Enter Environment Label (e.g., dev, prod) [prod]: " ENV_LABEL
    ENV_LABEL=${ENV_LABEL:-prod}
    INSTANCE_NAME="nexus-v3-$ENV_LABEL"

    echo -e "\n${CYAN}[2/6] Enabling APIs...${NC}"
    gcloud services enable gmail.googleapis.com drive.googleapis.com pubsub.googleapis.com \
        documentai.googleapis.com compute.googleapis.com --project="$PROJECT_ID"

    echo -e "\n${CYAN}[3/6] Configuring Network Security...${NC}"
    if gcloud compute firewall-rules describe allow-http-https-nexus &> /dev/null; then
        echo -e "${GREEN}Firewall rule 'allow-http-https-nexus' exists.${NC}"
    else
        gcloud compute firewall-rules create allow-http-https-nexus \
            --action=ALLOW --rules=tcp:80,tcp:443,tcp:22 --source-ranges=0.0.0.0/0 \
            --target-tags=http-server,https-server --project="$PROJECT_ID"
    fi

    echo -e "\n${CYAN}[4/6] Injecting Environment Secrets...${NC}"
    
    # Prompt for credentials.json early so we can parse the Client ID
    read -p "Enter local path to your credentials.json file: " CREDS_PATH
    if [ -n "$CREDS_PATH" ] && [ -f "$CREDS_PATH" ]; then
        GOOGLE_CLIENT_ID=$(grep -o '"client_id":"[^"]*"' "$CREDS_PATH" | head -n 1 | cut -d'"' -f4)
        echo -e "${GREEN}Auto-extracted Google Client ID: $GOOGLE_CLIENT_ID${NC}"
    else
        echo -e "${RED}Error: credentials.json is required.${NC}"
        exit 1
    fi

    DOCAI_PROJECT_ID=$PROJECT_ID
    echo -e "${GREEN}Auto-mapped DocAI Project ID: $PROJECT_ID${NC}"

    read -p "NEXUS_HMAC_SECRET (Random 64-char string): " NEXUS_HMAC_SECRET
    read -p "NEXUS_API_KEY (Gemini): " NEXUS_API_KEY
    read -p "NEXUS_PUBLIC_DOMAIN (e.g., nexus.yourdomain.com): " NEXUS_PUBLIC_DOMAIN
    echo -e "${YELLOW}(Optional) To automatically fetch SSL certs behind the Cloudflare Proxy (Orange Cloud), provide a DNS API Token.${NC}"
    read -p "CLOUDFLARE_API_TOKEN (Leave blank if not using CF proxy): " CLOUDFLARE_API_TOKEN
    read -p "AUTHORIZED_EMAILS (comma separated): " AUTHORIZED_EMAILS
    read -p "DOCAI_PROCESSOR_ID: " DOCAI_PROCESSOR_ID

    cat > .nexus_env <<EOF
TARGET_VM=$INSTANCE_NAME
TARGET_ZONE=$ZONE
PROJECT_ID=$PROJECT_ID
NEXUS_PUBLIC_DOMAIN=$NEXUS_PUBLIC_DOMAIN
CLOUDFLARE_API_TOKEN=$CLOUDFLARE_API_TOKEN
EOF

    echo -e "\n${CYAN}[5/6] Provisioning the Virtual Machine...${NC}"
    gcloud compute instances create "$INSTANCE_NAME" \
        --project="$PROJECT_ID" --zone="$ZONE" --machine-type=e2-micro \
        --image-family=debian-12 --image-project=debian-cloud \
        --boot-disk-size=30GB --boot-disk-type=pd-standard \
        --tags=http-server,https-server \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --metadata=startup-script='#!/bin/bash
echo ">>> Starting Nexus Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl nodejs npm
curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/gpg.key" | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt" | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update && apt-get install -y caddy

echo ">>> Injecting Cloudflare Caddy Module..."
curl -1sLf -o /usr/bin/caddy "https://caddyserver.com/api/download?os=linux&arch=amd64&p=github.com%2Fcaddy-dns%2Fcloudflare"
chmod +x /usr/bin/caddy
systemctl restart caddy

echo ">>> Configuring 2GB Swap Space..."
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab

mkdir -p /opt/nexus/shared/data /opt/nexus/shared/logs /opt/nexus/shared/tmp /opt/nexus/releases /opt/nexus/shared/backups
chown -R '"$USER:$USER"' /opt/nexus
'
    
    echo -e "${YELLOW}Waiting 45 seconds for VM and packages to initialize...${NC}"
    sleep 45

    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --command="
        cat <<EOF > /opt/nexus/shared/.env
NEXUS_HMAC_SECRET='$NEXUS_HMAC_SECRET'
NEXUS_API_KEY='$NEXUS_API_KEY'
NEXUS_PUBLIC_DOMAIN='$NEXUS_PUBLIC_DOMAIN'
CLOUDFLARE_API_TOKEN='$CLOUDFLARE_API_TOKEN'
AUTHORIZED_EMAILS='$AUTHORIZED_EMAILS'
GOOGLE_CLIENT_ID='$GOOGLE_CLIENT_ID'
DOCAI_PROJECT_ID='$DOCAI_PROJECT_ID'
DOCAI_LOCATION='us'
DOCAI_PROCESSOR_ID='$DOCAI_PROCESSOR_ID'
EOF
    "

    # Push credentials securely to the server
    gcloud compute scp "$CREDS_PATH" "$INSTANCE_NAME:/opt/nexus/shared/credentials.json" --zone="$ZONE"

    echo -e "\n${CYAN}[6/6] Provisioning Pub/Sub...${NC}"
    gcloud pubsub topics create nexus-incoming-topic --project="$PROJECT_ID" || true
    gcloud pubsub subscriptions create nexus-incoming-sub --topic=nexus-incoming-topic \
        --push-endpoint="https://$NEXUS_PUBLIC_DOMAIN/webhook/gmail" --project="$PROJECT_ID" || \
    gcloud pubsub subscriptions modify-push-config nexus-incoming-sub \
        --push-endpoint="https://$NEXUS_PUBLIC_DOMAIN/webhook/gmail" --project="$PROJECT_ID"

    VM_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
    
    echo -e "\n${GREEN}====================================================${NC}"
    echo -e "${GREEN}Provisioning Complete!${NC}"
    echo -e "Your VM IP Address is: ${YELLOW}$VM_IP${NC}"
    if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
        echo -e "Ensure your Cloudflare DNS record points to ${YELLOW}$VM_IP${NC} (Orange Cloud Proxy is OK!)."
    else
        echo -e "ACTION REQUIRED: Go to your DNS provider and point ${YELLOW}$NEXUS_PUBLIC_DOMAIN${NC} to ${YELLOW}$VM_IP${NC}"
    fi
    echo -e "Once DNS propagates, run ${CYAN}./nexus.sh --deploy${NC} to push your code!"
}

deploy() {
    load_env
    echo -e "\n${CYAN}Starting Zero-Downtime Deployment to $TARGET_VM...${NC}"
    
    echo -e "\n${YELLOW}--- 1. Branch Selection ---${NC}"
    echo "Fetching git branches..."
    git fetch origin || true
    
    # Safely fetch remote branches into an array
    IFS=$'\n' read -r -d '' -a branches < <( git branch -r | grep "origin/" | grep -v "HEAD" | sed 's/^[ \t]*origin\///' && printf '\0' )
    if [ ${#branches[@]} -eq 0 ]; then
        echo -e "${YELLOW}No remote branches found. Proceeding with current local state.${NC}"
    else
        for i in "${!branches[@]}"; do
            echo "[$i] ${branches[$i]}"
        done
        echo ""
        read -p "Select branch number (or press Enter to deploy current local state without switching): " bIdx
        if [ -n "$bIdx" ]; then
            SELECTED_BRANCH="${branches[$bIdx]}"
            echo -e "${GREEN}Switching to branch: $SELECTED_BRANCH${NC}"
            git checkout "$SELECTED_BRANCH"
            git pull origin "$SELECTED_BRANCH"
        else
            echo -e "${YELLOW}Deploying current local workspace state.${NC}"
        fi
    fi
    
    echo -e "\n${YELLOW}--- 2. Database Backup ---${NC}"
    read -p "Backup remote SQLite databases before deploying? (Y/n): " doBackup
    if [[ ! "$doBackup" =~ ^[Nn]$ ]]; then
        echo "Creating backup on remote server..."
        gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --command="
            mkdir -p /opt/nexus/shared/backups
            TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
            cp /opt/nexus/shared/data/*.db /opt/nexus/shared/backups/ 2>/dev/null || echo 'No databases found to backup yet.'
            echo 'Databases backed up to /opt/nexus/shared/backups/'
        "
    fi

    echo -e "\n${YELLOW}--- 3. Packaging & Uploading ---${NC}"
    echo "Packaging local repository (excluding node_modules/ignored files)..."
    tar -czf /tmp/nexus_release.tar.gz --exclude='.git' --exclude='node_modules' --exclude='frontend/node_modules' --exclude='.env' --exclude='credentials.json' --exclude='token.json' --exclude='AUDITS' .
    
    echo "Pushing package to VM..."
    gcloud compute scp /tmp/nexus_release.tar.gz "$TARGET_VM:/tmp/nexus_release.tar.gz" --zone="$TARGET_ZONE"
    
    echo -e "\n${YELLOW}--- 4. Remote Build & Hot-Swap ---${NC}"
    echo "Executing remote build process..."
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --command="
        set -e
        RELEASE_DIR=/opt/nexus/releases/\$(date +%Y%m%d_%H%M%S)
        mkdir -p \$RELEASE_DIR
        tar -xzf /tmp/nexus_release.tar.gz -C \$RELEASE_DIR
        
        source /opt/nexus/shared/.env
        
        echo '-> Injecting Google Client ID into React Frontend...'
        echo \"VITE_GOOGLE_CLIENT_ID=\$GOOGLE_CLIENT_ID\" > \$RELEASE_DIR/frontend/.env

        echo '-> Building Frontend SPA (Remote Build Law)'
        cd \$RELEASE_DIR/frontend
        npm install
        npm run build
        
        echo '-> Building Backend Virtual Environment'
        cd \$RELEASE_DIR
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        
        echo '-> Executing Database Migrations'
        export NEXUS_SHARED_DIR=/opt/nexus/shared
        python backend/db_init.py
        
        echo '-> Updating Symlinks'
        ln -sfn \$RELEASE_DIR /opt/nexus/current
        
        echo '-> Configuring Caddy & Systemd'
        source /opt/nexus/shared/.env
        
        TLS_BLOCK=\"\"
        if [ -n \"\$CLOUDFLARE_API_TOKEN\" ]; then
            TLS_BLOCK=\"tls { dns cloudflare \$CLOUDFLARE_API_TOKEN }\"
        fi

        sudo bash -c \"cat > /etc/caddy/Caddyfile <<EOF
\$NEXUS_PUBLIC_DOMAIN {
    \$TLS_BLOCK
    root * /opt/nexus/current/frontend/dist
    file_server
    handle /api/* { reverse_proxy 127.0.0.1:8000 }
    handle /webhook/* { reverse_proxy 127.0.0.1:8000 }
}
EOF\"
        sudo systemctl reload caddy

        sudo bash -c \"cat > /etc/systemd/system/nexus.service <<EOF
[Unit]
Description=Nexus V3 Daemon
After=network.target

[Service]
User=\$USER
WorkingDirectory=/opt/nexus/current
Environment=PATH=/opt/nexus/current/venv/bin
EnvironmentFile=/opt/nexus/shared/.env
Environment=NEXUS_SHARED_DIR=/opt/nexus/shared
ExecStart=/opt/nexus/current/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF\"
        
        sudo bash -c \"cat > /etc/logrotate.d/nexus <<EOF
/opt/nexus/shared/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF\"

        sudo systemctl daemon-reload
        sudo systemctl enable nexus.service
        sudo systemctl restart nexus.service
        echo '-> Deployment Complete!'
    "
    rm /tmp/nexus_release.tar.gz
    echo -e "${GREEN}System is LIVE at https://$NEXUS_PUBLIC_DOMAIN${NC}"
}

auth_tunnel() {
    load_env
    echo -e "\n${YELLOW}Opening SSH Tunnel to $TARGET_VM on port 8080...${NC}"
    echo -e "When the Google Auth link appears, CTRL+CLICK to open it in your browser."
    
    AUTH_CMD="sudo systemctl stop nexus.service; export NEXUS_SHARED_DIR=/opt/nexus/shared; cd /opt/nexus/current && source venv/bin/activate && pip install google-auth-oauthlib google-api-python-client --quiet && python backend/auth/workspace_auth.py; sudo systemctl start nexus.service"
    
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --ssh-flag="-L" --ssh-flag="8080:127.0.0.1:8080" --command="$AUTH_CMD"
}

health() {
    load_env
    echo -e "\n${CYAN}Fetching Health Status for $TARGET_VM...${NC}"
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --command="
        echo -e '\n--- Systemd Service ---'
        sudo systemctl status nexus.service --no-pager | head -n 5
        echo -e '\n--- Caddy Proxy Status ---'
        sudo systemctl status caddy --no-pager | head -n 5
        echo -e '\n--- Disk Space ---'
        df -h / | tail -n 2
        echo -e '\n--- Database Sizes ---'
        ls -lh /opt/nexus/shared/data/*.db 2>/dev/null || echo 'No databases found.'
        echo -e '\n--- Worker Errors ---'
        sudo journalctl -u nexus.service -n 20 --no-pager | grep -i error || echo 'No recent errors.'
    "
}

clean() {
    load_env
    echo -e "\n${YELLOW}Cleaning old releases and running SQLite VACUUM...${NC}"
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --command="
        current_rel=\$(readlink -f \"/opt/nexus/current\")
        ls -d /opt/nexus/releases/*/ 2>/dev/null | grep -v \"\$current_rel\" | xargs -I {} sudo rm -rf {}
        sqlite3 /opt/nexus/shared/data/nexus_core.db 'VACUUM;'
        sqlite3 /opt/nexus/shared/data/nexus_kb.db 'VACUUM;'
        echo 'Cleanup complete.'
    "
}

show_menu() {
    echo -e "${CYAN}====================================================${NC}"
    echo -e "${CYAN}       NEXUS V3 MASTER CONTROL PANEL (LOCAL)        ${NC}"
    echo -e "${CYAN}====================================================${NC}"
    echo "1. Provision Infrastructure (--provision)"
    echo "2. Deploy Source Code (--deploy)"
    echo "3. Open Auth Tunnel (--auth-tunnel)"
    echo "4. Fleet Health Dashboard (--health)"
    echo "5. Clean Old Releases & Vacuum DB (--clean)"
    echo "6. Exit"
    echo -e "${CYAN}====================================================${NC}"
    read -p "Select an option: " opt
    case $opt in
        1) provision ;;
        2) deploy ;;
        3) auth_tunnel ;;
        4) health ;;
        5) clean ;;
        6) exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
}

case "$1" in
    --provision) provision ;;
    --deploy) deploy ;;
    --auth-tunnel) auth_tunnel ;;
    --health) health ;;
    --clean) clean ;;
    "") show_menu ;;
    *) echo -e "${RED}Unknown argument: $1${NC}" ;;
esac