# Nexus for Google: The Beginner's Deployment Playbook

Welcome to Nexus for Google! Because this system operates as a private, secure, Asynchronous Closed-Loop Fusion Engine, you are going to host it on your own Google Cloud server. 

You do not need to be a DevOps engineer or coding expert to deploy this. The `nexus.sh` script does 95% of the heavy lifting. However, before you run the script, you must gather a few configuration keys. 

Follow this guide step-by-step. Open a blank notepad on your computer to collect these items as we go.

---

## Phase 1: The GCP Project & Secrets Checklist

### 1. Your Domain Name & Cloudflare API Token
1. You must own a domain name (e.g., `yourdomain.com`). Decide on the specific URL you will use for Nexus (e.g., `nexus.yourdomain.com`). 
   * 👉 **Save this as your `NEXUS_PUBLIC_DOMAIN`.**
2. *(Optional but Highly Recommended):* Route your domain's DNS through Cloudflare (it's free).
   * Go to Cloudflare > My Profile (top right) > API Tokens > Create Token > Create Custom Token.
   * Permissions: `Zone` | `DNS` | `Edit`.
   * Zone Resources: `Include` | `Specific Zone` | `yourdomain.com`.
   * Generate and copy the token.
   * 👉 **Save this as your `CLOUDFLARE_API_TOKEN`.** (Leave this blank later if you don't use Cloudflare).

### 2. Create the Master GCP Project
Everything must live inside a single Google Cloud Project.
1. Go to the [Google Cloud Console](https://console.cloud.google.com) and sign in.
2. Click the dropdown at the top left (next to the Google Cloud logo) and click **New Project**.
3. Name it `nexus-ai-engine` and click **Create**.
4. **Make sure your new project is selected at the top of the screen before proceeding!**
5. *Billing:* Go to **Billing** in the left menu and link a credit card. The server you will build is part of Google's "Always Free" tier, but Google requires a card on file to use cloud features.

> 🛑 **THE ONE PROJECT RULE:** 
> For steps 3, 4, and 5 below, you MUST ensure that your new `nexus-ai-engine` project is selected in the top-left dropdown of your Google Cloud dashboard!

### 3. Your Gemini AI Brain
This gives Nexus its intelligence.
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in, and click **Get API key** in the left menu.
3. Click **Create API key** and select your specific GCP project (`nexus-ai-engine`).
4. Copy the long string of letters and numbers generated. 
   * 👉 **Save this as your `NEXUS_API_KEY`.**

### 4. Your Document OCR Reader
This lets Nexus read text from scanned PDFs and images. *Ensure you are still in your `nexus-ai-engine` project!*
1. In the Google Cloud Console, search for "Document AI" in the top search bar. Click **Enable API** if prompted.
2. Click **Explore Processors**, find **Document OCR**, and click **Create Processor**.
3. Name it `nexus-ocr` and set the region to `us`. 
4. Once created, go to the Processor Details page. You will see an ID string that looks like `1a2b3c4d5e6f7g8h`. 
   * 👉 **Save this as your `DOCAI_PROCESSOR_ID`.**

### 5. Your Login Security (`credentials.json`)
This creates the secure "Sign in with Google" button so Nexus can read your Gmail/Drive. *Ensure you are still in your `nexus-ai-engine` project!*
1. **Consent Screen:** In the Google Cloud Console, search for "OAuth consent screen".
   * Choose **External** (or Internal if you are a Google Workspace business user) and click Create.
   * App name: `Nexus`. Select your email for the support and developer contact emails. Click Save and Continue.
   * *Skip Scopes and Test Users by clicking Save and Continue.*
   * **CRITICAL:** On the summary screen, click the **Publish App** button to push it to "In production". If you leave it in "Testing", your login tokens will expire every 7 days!
2. **Create Credentials:** Click **Credentials** on the left menu.
   * Click **+ CREATE CREDENTIALS** -> **OAuth client ID**.
   * Application type: **Desktop app**. Name it `Nexus Auth`. Click Create.
   * **CRITICAL:** Click the **Download JSON** button on the popup. Save it to your computer, rename it exactly to `credentials.json`, and place it inside your `Nexus-for-Google` folder (right next to the `nexus.sh` script).

### 6. Your Digital Lock (`NEXUS_HMAC_SECRET`)
This is a cryptographic secret used to lock your login session cookies. 
* Mash your keyboard right now to make a random 64-character string (e.g., `kjasdhfkjashdfkjh8923749823hjkfhsdf890234hjkfhsdf`).
* 👉 **Save this as your `NEXUS_HMAC_SECRET`.**

### 7. The VIP List (`AUTHORIZED_EMAILS`)
Write down a comma-separated list of exact Google email addresses allowed to log into your app.
* 👉 **Save this as your `AUTHORIZED_EMAILS`** (e.g., `you@gmail.com,partner@gmail.com`).

---

## Phase 2: Automated Deployment

Open your local terminal (Mac Terminal, Git Bash, or WSL) inside your project folder. Make sure the script is executable by running: 
<pre><code class="language-bash">chmod +x nexus.sh</code></pre>

### Step 1: Provision Infrastructure
Run the control panel:
<pre><code class="language-bash">./nexus.sh --provision</code></pre>
* The script will ask you to log in to your Google Account.
* **Select the `nexus-ai-engine` project from the list.**
* It will prompt you to provide the path to the `credentials.json` file you saved.
* It will prompt you to paste in the remaining variables you gathered in Phase 1.
* It will then talk to Google, create a free-tier virtual machine server, configure firewalls, and install the necessary software.

**CRITICAL DNS STEP:** At the end of this step, the terminal will output your new server's **Public IP Address**. Go to your domain provider (e.g., Cloudflare, GoDaddy) and create an **A Record** pointing `nexus.yourdomain.com` to that IP address.

### Step 2: Zero-Downtime Deployment
Wait about 5 minutes for your DNS record to propagate across the internet, then run:
<pre><code class="language-bash">./nexus.sh --deploy</code></pre>
* The script will compress your code, securely upload it to your new server, automatically inject your Client ID into the React UI, build the frontend, set up the databases, and launch the web server.

### Step 3: Setting Up the Auth Tunnel
The server is now running, but it doesn't have permission to read your emails yet. We need to create a secure tunnel to the server to grant it access.
<pre><code class="language-bash">./nexus.sh --auth-tunnel</code></pre>
* The script will pause the server and open a secure tunnel to your computer.
* A link will appear in your terminal. **Ctrl+Click** it to open it in your browser. 
* Google will warn you that the app isn't verified (because you just made it). Click **Advanced** -> **Go to Nexus (unsafe)**. Click **Continue** to grant the permissions.
* Return to your terminal. The script will automatically save the connection token and restart your Nexus server!

### You are done! 🎉
Navigate to your domain (`https://nexus.yourdomain.com`). Log in with Google, open the **System Settings** menu (gear icon), and click **Generate & Apply Theme** to bring Nexus for Google to life.to life.