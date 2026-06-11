# Nexus V3 Deployment Playbook

This document details the exact procedures for provisioning infrastructure and deploying Nexus V3 in a production Google Cloud Platform (GCP) environment.

## 1. GCP Manual Provisioning Steps

Before running the automated scripts, the following steps MUST be executed manually within the Google Cloud Console:

1. **Create the GCP Project:** 
   * Navigate to the GCP Console and create a new project (e.g., `nexus-v3-prod`).
2. **Enable APIs:** 
   * Enable the following APIs: **Gmail API**, **Google Drive API**, and **Cloud Document AI API**.
3. **Configure the OAuth Consent Screen:** 
   * Set User Type to "External" and Publishing Status to **"In production"**.
   * Add required scopes (e.g., Gmail modify, Drive readonly).
   * Add your test user emails if the app is still in testing mode (otherwise, proceed through Google verification).
4. **Create OAuth 2.0 Credentials:** 
   * Create an **OAuth 2.0 Client ID** of type **Desktop app**. 
   * Download the JSON file, rename it to `credentials.json`, and place it in the secure secrets location on your local machine.
5. **Configure Document AI:** 
   * Navigate to Document AI. Create a new **Document OCR Processor** and note its **Processor ID** and **Location** (e.g., `us`).

## 2. Setting Up the Auth Tunnel

The backend requires a `token.json` file to communicate with Google Workspace APIs. This token must be generated locally and transferred.

1. **Execute Auth Tunnel Command:**
   ```bash
   ./nexus.sh --auth-tunnel
   ```
   *(This initiates local port forwarding or an automated flow to capture the token using `credentials.json`)*
2. Follow the prompt to authorize the application in your browser.
3. The generated `token.json` will securely authenticate the backend workers.

## 3. Automated Execution Flow

The `nexus.sh` script completely automates environment setup, dependency management, GCP Pub/Sub creation, and zero-downtime deployments.

### `./nexus.sh --provision`
* Validates `gcloud` authentication.
* Securely prompts and stores environment variables in `.env` (`NEXUS_HMAC_SECRET`, `NEXUS_API_KEY`, `NEXUS_PUBLIC_DOMAIN`, `AUTHORIZED_EMAILS`, `GOOGLE_CLIENT_ID`, `DOCAI_PROJECT_ID`, `DOCAI_LOCATION`, `DOCAI_PROCESSOR_ID`).
* Installs system dependencies (Python, Node.js, SQLite, UFW, Caddy).
* Creates the required directory structures and configures the firewall.
* Sets up a 2GB swap file.
* Automatically creates the GCP Pub/Sub topic and configures the push subscription endpoint to your domain.

### `./nexus.sh --deploy`
* Creates a timestamped release directory.
* Copies over the current source (excluding `.git`).
* Builds the SPA using `npm run build`.
* Installs backend Python dependencies in an isolated virtual environment.
* Runs the database initialization script (`db_init.py`).
* Updates the symlink to the new release directory (Zero-Downtime).
* Configures Caddy as a reverse proxy for the frontend dist and backend API/webhooks.
* Updates and restarts the `nexus.service` systemd daemon.
* Sets up Logrotate to rotate and compress `/opt/nexus/shared/logs/*.log` to prevent disk exhaustion.