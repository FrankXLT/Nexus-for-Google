#!/bin/bash
# nexus.sh - Standalone DevSecOps Installer for Nexus

set -e
set -o pipefail
export CLOUDSDK_COMPUTE_USE_OPENSSH=1
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null || true

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}      NEXUS: MASTER CONTROL & DEPLOYMENT            ${NC}"
echo -e "${CYAN}====================================================${NC}"

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
    echo -e "\n${CYAN}[1/7] Authentication & Project Setup...${NC}"
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    if [ -z "$ACTIVE_ACCOUNT" ]; then
        CLOUDSDK_CORE_DISABLE_PROMPTS=0 gcloud auth login
    fi

    IFS=$'\n' read -r -d '' -a projects < <( gcloud projects list --format="value(projectId,name)" && printf '\0' )
    for i in "${!projects[@]}"; do echo "[$i] ${projects[$i]}"; done
    read -p "Select Project number: " projIdx
    PROJECT_ID=$(echo "${projects[$projIdx]}" | awk '{print $1}')
    gcloud config set project "$PROJECT_ID" --quiet

    ZONE="us-central1-a"
    read -p "Enter Environment Label (e.g., dev, prod) [prod]: " ENV_LABEL
    ENV_LABEL=${ENV_LABEL:-prod}
    INSTANCE_NAME="nexus-$ENV_LABEL"

    echo -e "\n${CYAN}[2/7] Enabling APIs...${NC}"
    gcloud services enable gmail.googleapis.com drive.googleapis.com pubsub.googleapis.com \
        documentai.googleapis.com compute.googleapis.com --project="$PROJECT_ID" --quiet

    echo -e "\n${CYAN}[3/7] Configuring Network Security...${NC}"
    FW_EXISTS=$(gcloud compute firewall-rules list --filter="name=allow-http-https-nexus" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | tr -d '\r' || true)
    
    if [ "$FW_EXISTS" == "allow-http-https-nexus" ]; then
        echo -e "${GREEN}Firewall rule 'allow-http-https-nexus' exists.${NC}"
    else
        echo "Creating firewall rule..."
        gcloud compute firewall-rules create allow-http-https-nexus \
            --action=ALLOW --rules=tcp:80,tcp:443,tcp:22 --source-ranges=0.0.0.0/0 \
            --target-tags=http-server,https-server --project="$PROJECT_ID" --quiet
    fi

    echo -e "\n${CYAN}[4/7] Injecting Environment Secrets...${NC}"
    
    read -r -p "Enter local path to your credentials.json file (e.g. ./credentials.json): " RAW_CREDS_PATH
    CREDS_PATH="${RAW_CREDS_PATH//\\//}"
    CREDS_PATH="${CREDS_PATH//\'/}"
    CREDS_PATH="${CREDS_PATH//\"/}"

    if [ -n "$CREDS_PATH" ] && [ -f "$CREDS_PATH" ]; then
        GOOGLE_CLIENT_ID=$(grep -o '"client_id":"[^"]*"' "$CREDS_PATH" | head -n 1 | cut -d'"' -f4)
        echo -e "${GREEN}Auto-extracted Google Client ID: $GOOGLE_CLIENT_ID${NC}"
    else
        echo -e "${RED}Error: credentials.json is required. File not found at '$CREDS_PATH'.${NC}"
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

    echo -e "\n${CYAN}[5/7] Provisioning the Virtual Machine...${NC}"
    VM_EXISTS=$(gcloud compute instances list --filter="name=$INSTANCE_NAME AND zone=$ZONE" --format="value(name)" --project="$PROJECT_ID" 2>/dev/null | tr -d '\r' || true)
    
    if [ "$VM_EXISTS" == "$INSTANCE_NAME" ]; then
        echo -e "${GREEN}Virtual Machine '$INSTANCE_NAME' already exists. Skipping creation.${NC}"
    else
        echo "Creating new VM instance..."
        gcloud compute instances create "$INSTANCE_NAME" \
            --project="$PROJECT_ID" --zone="$ZONE" --machine-type=e2-micro \
            --image-family=debian-12 --image-project=debian-cloud \
            --boot-disk-size=30GB --boot-disk-type=pd-standard \
            --tags=http-server,https-server \
            --scopes=https://www.googleapis.com/auth/cloud-platform \
            --quiet \
            --metadata=startup-script='#!/bin/bash
echo ">>> Starting Nexus Bootstrap..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 git curl nodejs npm

echo ">>> Enforcing Node.js v22 LTS..."
apt-get remove -y nodejs npm || true
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/gpg.key" | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt" | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update && apt-get install -y caddy libcap2-bin

echo ">>> Injecting Cloudflare Caddy Module..."
systemctl stop caddy || true
rm -f /usr/bin/caddy
curl -1sLf -o /usr/bin/caddy "https://caddyserver.com/api/download?os=linux&arch=amd64&p=github.com%2Fcaddy-dns%2Fcloudflare"
chmod +x /usr/bin/caddy
setcap cap_net_bind_service=+ep /usr/bin/caddy || true
systemctl start caddy

echo ">>> Configuring 2GB Swap Space..."
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
'
        echo -e "${YELLOW}Waiting 45 seconds for VM to boot...${NC}"
        sleep 45
    fi
    
    echo -e "${CYAN}Creating remote directory structure...${NC}"
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
        sudo mkdir -p /opt/nexus/shared/data /opt/nexus/shared/logs /opt/nexus/shared/tmp /opt/nexus/releases /opt/nexus/shared/backups
        sudo chown -R \$USER:\$USER /opt/nexus
    "

    echo "Injecting .env file to remote server..."
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
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

    echo "Uploading credentials.json..."
    gcloud compute scp "$CREDS_PATH" "$INSTANCE_NAME:/opt/nexus/shared/credentials.json" --zone="$ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no

    echo -e "\n${CYAN}[6/7] Provisioning Pub/Sub...${NC}"
    gcloud pubsub topics create nexus-incoming-topic --project="$PROJECT_ID" --quiet || true
    gcloud pubsub subscriptions create nexus-incoming-sub --topic=nexus-incoming-topic \
        --push-endpoint="https://$NEXUS_PUBLIC_DOMAIN/webhook/gmail" --project="$PROJECT_ID" --quiet || \
    gcloud pubsub subscriptions modify-push-config nexus-incoming-sub \
        --push-endpoint="https://$NEXUS_PUBLIC_DOMAIN/webhook/gmail" --project="$PROJECT_ID" --quiet

    VM_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="get(networkInterfaces[0].accessConfigs[0].natIP)" --quiet)
    
    echo -e "\n${CYAN}[7/7] Auto-Configuring Cloudflare DNS...${NC}"
    if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
        gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
            python3 -c '
import urllib.request, json, sys
token = \"$CLOUDFLARE_API_TOKEN\"
domain = \"$NEXUS_PUBLIC_DOMAIN\"
ip = \"$VM_IP\"

try:
    req = urllib.request.Request(\"https://api.cloudflare.com/client/v4/zones\", headers={\"Authorization\": f\"Bearer {token}\"})
    zones = json.loads(urllib.request.urlopen(req).read().decode(\"utf-8\"))[\"result\"]
    zone_id = None
    for z in zones:
        if domain.endswith(z[\"name\"]):
            zone_id = z[\"id\"]
            break
    
    if not zone_id:
        print(\"   -> Error: Could not find matching Cloudflare zone for\", domain)
        sys.exit(0)
    
    req = urllib.request.Request(f\"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={domain}&type=A\", headers={\"Authorization\": f\"Bearer {token}\"})
    records = json.loads(urllib.request.urlopen(req).read().decode(\"utf-8\"))[\"result\"]
    
    data = json.dumps({\"type\": \"A\", \"name\": domain, \"content\": ip, \"proxied\": True, \"ttl\": 1}).encode(\"utf-8\")
    headers = {\"Authorization\": f\"Bearer {token}\", \"Content-Type\": \"application/json\"}
    
    if records:
        record_id = records[0][\"id\"]
        req = urllib.request.Request(f\"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}\", data=data, headers=headers, method=\"PUT\")
        print(\"   -> Updating existing A Record for\", domain)
    else:
        req = urllib.request.Request(f\"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records\", data=data, headers=headers, method=\"POST\")
        print(\"   -> Creating new A Record for\", domain)
        
    urllib.request.urlopen(req)
    print(f\"   -> Cloudflare DNS successfully pointed {domain} to {ip} (Proxied)!\")
except Exception as e:
    print(f\"   -> Failed to update Cloudflare DNS: {e}\")
'
        "
    else
        echo -e "${YELLOW}Skipped Cloudflare DNS Automation (No Token Provided).${NC}"
    fi

    echo -e "\n${GREEN}====================================================${NC}"
    echo -e "${GREEN}Provisioning Complete!${NC}"
    echo -e "Your VM IP Address is: ${YELLOW}$VM_IP${NC}"
    if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
        echo -e "ACTION REQUIRED: Go to your DNS provider and point ${YELLOW}$NEXUS_PUBLIC_DOMAIN${NC} to ${YELLOW}$VM_IP${NC}"
    fi
    echo -e "Once DNS propagates, run ${CYAN}./nexus.sh --deploy${NC} to push your code!"
}

deploy() {
    load_env
    echo -e "\n${CYAN}Starting Zero-Downtime Deployment to $TARGET_VM...${NC}"
    
    echo -e "\n${YELLOW}--- 1. GitHub Branch Selection ---${NC}"
    REPO="FrankXLT/Nexus-for-Google"
    
    branches=()
    if command -v git &> /dev/null; then
        echo "Fetching remote branches from GitHub (using git)..."
        IFS=$'\n' read -r -d '' -a branches < <( git ls-remote --heads "https://github.com/$REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|^refs/heads/||' && printf '\0' )
    elif command -v curl &> /dev/null; then
        echo "Fetching remote branches via GitHub API..."
        IFS=$'\n' read -r -d '' -a branches < <( curl -s "https://api.github.com/repos/$REPO/branches" 2>/dev/null | grep '"name":' | cut -d'"' -f4 && printf '\0' )
    fi
    
    if [ ${#branches[@]} -eq 0 ]; then
        echo -e "${YELLOW}Notice: Could not fetch branches automatically. Defaulting to 'main'.${NC}"
        SELECTED_BRANCH="main"
    else
        for i in "${!branches[@]}"; do
            echo "[$i] ${branches[$i]}"
        done
        echo ""
        read -p "Select branch number to deploy [0]: " bIdx
        bIdx=$(echo "$bIdx" | tr -d '\r') # Force strip Windows carriage returns
        bIdx=${bIdx:-0}
        SELECTED_BRANCH=$(echo "${branches[$bIdx]}" | tr -d '\r') # Force strip Windows carriage returns
    fi
    echo -e "${GREEN}Targeting remote branch: $SELECTED_BRANCH${NC}"
    
    echo -e "\n${YELLOW}--- 2. Database Backup ---${NC}"
    read -p "Backup remote SQLite databases before deploying? (Y/n): " doBackup
    doBackup=$(echo "$doBackup" | tr -d '\r')
    if [[ ! "$doBackup" =~ ^[Nn]$ ]]; then
        echo "Creating backup on remote server..."
        gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
            mkdir -p /opt/nexus/shared/backups
            TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
            cp /opt/nexus/shared/data/*.db /opt/nexus/shared/backups/ 2>/dev/null || echo 'No databases found to backup yet.'
            echo 'Databases backed up to /opt/nexus/shared/backups/'
        "
    fi

    if [ -f "credentials.json" ]; then
        echo "Found local credentials.json. Syncing to remote server..."
        gcloud compute scp credentials.json "$TARGET_VM:/opt/nexus/shared/credentials.json" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no
    fi

    echo -e "\n${YELLOW}--- 3. Remote Build & Hot-Swap ---${NC}"
    echo "Commanding VM to download code directly from GitHub and build..."
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
        set -e
        
        echo '-> Stopping Nexus service to free CPU/RAM for the build process...'
        sudo systemctl stop nexus.service || true
        
        echo '-> Extracting variables securely without sourcing...'
        GOOGLE_CLIENT_ID=\$(grep '^GOOGLE_CLIENT_ID=' /opt/nexus/shared/.env | cut -d'=' -f2- | tr -d '\"' | tr -d \"'\")
        NEXUS_PUBLIC_DOMAIN=\$(grep '^NEXUS_PUBLIC_DOMAIN=' /opt/nexus/shared/.env | cut -d'=' -f2- | tr -d '\"' | tr -d \"'\" | tr -d '\r')
        CLOUDFLARE_API_TOKEN=\$(grep '^CLOUDFLARE_API_TOKEN=' /opt/nexus/shared/.env | cut -d'=' -f2- | tr -d '\"' | tr -d \"'\" | tr -d '\r')
        
        echo '-> Checking Node.js version...'
        CURRENT_NODE=\$(node -v 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1 || echo '0')
        if [ \"\$CURRENT_NODE\" -lt 22 ]; then
            echo '-> Upgrading Node.js to v22 (LTS) to support Vite...'
            sudo apt-get remove -y nodejs npm > /dev/null 2>&1 || true
            curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - > /dev/null 2>&1
            sudo apt-get install -y nodejs psmisc > /dev/null 2>&1
            hash -r
        fi

        echo '-> Verifying Caddy Cloudflare Module...'
        if ! /usr/bin/caddy list-modules | grep -q dns.providers.cloudflare; then
            echo '-> Auto-healing: Patching Caddy with Cloudflare plugin...'
            sudo systemctl stop caddy || true
            sudo rm -f /usr/bin/caddy
            sudo curl -1sLf -o /usr/bin/caddy \"https://caddyserver.com/api/download?os=linux&arch=amd64&p=github.com%2Fcaddy-dns%2Fcloudflare\"
            sudo chmod +x /usr/bin/caddy
        fi

        RELEASE_DIR=/opt/nexus/releases/\$(date +%Y%m%d_%H%M%S)
        mkdir -p \$RELEASE_DIR
        
        echo '-> Downloading repository directly from GitHub to bypass tarball caches...'
        git clone --depth 1 --branch ${SELECTED_BRANCH:-development} https://github.com/$REPO.git \$RELEASE_DIR
        rm -rf \$RELEASE_DIR/.git
               
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
        
        echo '-> Updating Symlinks and Permissions'
        ln -sfn \$RELEASE_DIR /opt/nexus/current
        sudo chmod 755 /opt/nexus
        sudo chmod 755 /opt/nexus/releases
        sudo chmod 755 \$RELEASE_DIR
        
        echo '-> Configuring Caddy & Systemd'

        TLS_BLOCK=\"\"
        if [ -n \"\$CLOUDFLARE_API_TOKEN\" ]; then
            TLS_BLOCK=\"tls {
        dns cloudflare \$CLOUDFLARE_API_TOKEN
    }\"
        fi

        cat > /tmp/Caddyfile <<EOF
\$NEXUS_PUBLIC_DOMAIN {
    \$TLS_BLOCK
    root * /opt/nexus/current/frontend/dist
    file_server
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }
    handle /webhook/* {
        reverse_proxy 127.0.0.1:8000
    }
}
EOF
        sudo mv /tmp/Caddyfile /etc/caddy/Caddyfile
        
        sudo setcap cap_net_bind_service=+ep /usr/bin/caddy || true
        sudo caddy fmt --overwrite /etc/caddy/Caddyfile || true
        sudo /usr/bin/caddy validate --config /etc/caddy/Caddyfile || echo 'WARNING: Caddy validation failed'
        sudo systemctl restart caddy

        cat > /tmp/nexus.service <<EOF
[Unit]
Description=Nexus Daemon
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
EOF
        sudo mv /tmp/nexus.service /etc/systemd/system/nexus.service
        
        cat > /tmp/nexus_logrotate <<EOF
/opt/nexus/shared/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
        sudo mv /tmp/nexus_logrotate /etc/logrotate.d/nexus

        sudo systemctl daemon-reload
        sudo systemctl enable nexus.service
        sudo systemctl start nexus.service
        echo '-> Deployment Complete!'
    "
    echo -e "${GREEN}System is LIVE at https://$NEXUS_PUBLIC_DOMAIN${NC}"
}

auth_tunnel() {
    load_env
    echo -e "\n${YELLOW}Opening SSH Tunnel to $TARGET_VM on port 8081...${NC}"
    echo -e "When the Google Auth link appears, CTRL+CLICK to open it in your browser."
    
    # Safely install psmisc, kill port 8081 specifically, and run auth script
    AUTH_CMD="sudo apt-get install -y psmisc >/dev/null 2>&1 || true; sudo fuser -k 8081/tcp 2>/dev/null || true; sudo systemctl stop nexus.service || true; export NEXUS_SHARED_DIR=/opt/nexus/shared; cd /opt/nexus/current && source venv/bin/activate && python -u backend/auth/workspace_auth.py; sudo systemctl start nexus.service"
    
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --ssh-flag="-L" --ssh-flag="8081:127.0.0.1:8081" --quiet --strict-host-key-checking=no --command="$AUTH_CMD"
}

health() {
    load_env
    echo -e "\n${CYAN}Fetching Health Status for $TARGET_VM...${NC}"
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
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
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID" --quiet --strict-host-key-checking=no --command="
        current_rel=\$(readlink -f \"/opt/nexus/current\")
        ls -d /opt/nexus/releases/*/ 2>/dev/null | grep -v \"\$current_rel\" | xargs -I {} sudo rm -rf {}
        sqlite3 /opt/nexus/shared/data/nexus_core.db 'VACUUM;'
        sqlite3 /opt/nexus/shared/data/nexus_kb.db 'VACUUM;'
        echo 'Cleanup complete.'
    "
}

ssh_terminal() {
    load_env
    echo -e "\n${CYAN}Opening interactive SSH terminal to $TARGET_VM...${NC}"
    gcloud compute ssh "$TARGET_VM" --zone="$TARGET_ZONE" --project="$PROJECT_ID"
}

download_dbs() {
    load_env
    echo -e "\n${CYAN}Downloading SQLite databases from $TARGET_VM...${NC}"
    mkdir -p ./local_db_inspect
    gcloud compute scp "$TARGET_VM:/opt/nexus/shared/data/*.db" "./local_db_inspect/" --zone="$TARGET_ZONE" --project="$PROJECT_ID"
    echo -e "${GREEN}Databases downloaded to ./local_db_inspect/${NC}"
}

show_menu() {
    echo -e "${CYAN}====================================================${NC}"
    echo -e "${CYAN}       NEXUS MASTER CONTROL PANEL (LOCAL)           ${NC}"
    echo -e "${CYAN}====================================================${NC}"
    echo "1. Provision Infrastructure (--provision)"
    echo "2. Deploy Source Code (--deploy)"
    echo "3. Open Auth Tunnel (--auth-tunnel)"
    echo "4. Fleet Health Dashboard (--health)"
    echo "5. Clean Old Releases & Vacuum DB (--clean)"
    echo "6. Open SSH Terminal (--ssh)"
    echo "7. Download Databases (--download-dbs)"
    echo "8. Exit"
    echo -e "${CYAN}====================================================${NC}"
    read -p "Select an option: " opt
    case $opt in
        1) provision ;;
        2) deploy ;;
        3) auth_tunnel ;;
        4) health ;;
        5) clean ;;
        6) ssh_terminal ;;
        7) download_dbs ;;
        8) exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
}

case "$1" in
    --provision) provision ;;
    --deploy) deploy ;;
    --auth-tunnel) auth_tunnel ;;
    --health) health ;;
    --clean) clean ;;
    --ssh) ssh_terminal ;;
    --download-dbs) download_dbs ;;
    "") show_menu ;;
    *) echo -e "${RED}Unknown argument: $1${NC}" ;;
esac
chmod +x nexus.sh