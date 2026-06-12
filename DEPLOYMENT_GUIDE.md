# Nexus V3 Deployment Playbook

This document details the exact procedures for provisioning infrastructure and deploying Nexus V3 in a production Google Cloud Platform (GCP) environment using the local `nexus.sh` orchestrator.

**CRITICAL PARADIGM SHIFT:** The `nexus.sh` script is a **Local Remote-Control Utility**. You MUST run it on your local workstation (Mac Terminal, Git Bash, or WSL). It uses `gcloud` to dynamically create the server and pipe your local code directly over an SSH tunnel.

## 1. GCP Manual Pre-Flight Steps

Before running the automated scripts, you must configure Google's OAuth screens:

1. **Create the GCP Project & Billing:** Create a new project and ensure a billing account is linked (the `e2-micro` VM is in the Always Free tier).
2. **Configure the OAuth Consent Screen:** 
    * Set User Type to "External" and Publishing Status to **"In production"**.
    * Add your Google account email to the Test Users (if applicable).
3. **Create OAuth 2.0 Credentials:** 
    * Go to APIs & Services > Credentials. Create an **OAuth 2.0 Client ID** of type **Desktop app**.
    * Download the JSON file and rename it exactly to `credentials.json`. Keep it in your local Nexus project root folder.
4. **Configure Document AI:** 
    * Navigate to Document AI. Create a new **Document OCR Processor**. Keep the Project ID, Location (e.g., `us`), and Processor ID handy for the script.

## 2. Automated Infrastructure Provisioning

Open your local terminal at the root of the repository. Make sure the script is executable (`chmod +x nexus.sh`).

Run the script and select **Option 1**:

<pre><code class="language-bash">./nexus.sh</code></pre>

* **What it does:** It creates a local `.nexus_env` tracking file, enables all APIs, spawns the GCP `e2-micro` VM, punches holes in the Google Firewall for ports 80/443, installs Caddy/Node/Python on the VM via a startup script, provisions a 2GB OS Swap file to prevent memory panics, securely transfers your secrets to `/opt/nexus/shared/.env`, uploads your `credentials.json`, and creates the Pub/Sub topics.

**CRITICAL DNS STEP:** At the end of Option 1, the script will output the VM's Public IP address. You MUST go to your DNS provider and point an `A Record` for your domain (e.g., `nexus.yourdomain.com`) to this IP address before proceeding to deployment, so Caddy can automatically fetch the Let's Encrypt SSL certificate.

## 3. Zero-Downtime Deployment
Wait 5 minutes for your DNS record to propagate, run the script, and select **Option 2**:

<pre><code class="language-bash">./nexus.sh</code></pre>

* **What it does:** It connects to the VM, securely transfers your local code via a `.tar.gz` bundle, and triggers a remote build. It runs `npm install` and `npm run build` natively on the server, installs the Python dependencies, runs the SQLite database migrations, and hot-swaps the Caddy and Systemd daemon pointers for a zero-downtime release.

## 4. Setting Up the Auth Tunnel
The backend requires a `token.json` file to communicate with Google Workspace APIs. Because the VM is headless, we must tunnel the OAuth request to your local browser.

Run the script and select **Option 3**:

<pre><code class="language-bash">./nexus.sh</code></pre>

* **What it does:** It safely pauses the backend daemon, opens an SSH tunnel mapping the VM's port 8080 to your local port 8080, and runs `workspace_auth.py`. Click the link that appears in the terminal to authorize the application. Once complete, the token is saved on the server and the daemon automatically resumes!