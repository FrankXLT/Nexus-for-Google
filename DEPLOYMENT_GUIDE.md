# Nexus V3: The Beginner's Deployment Playbook

Welcome to Nexus V3! Because this system operates as a private, secure, Asynchronous Closed-Loop Fusion Engine, you are going to host it on your own Google Cloud server. 

You do not need to be a DevOps engineer to deploy this. The `nexus.sh` script does 95% of the heavy lifting. However, before you run the script, you must gather **8 specific configuration keys** from various Google and Cloudflare dashboards. 

Follow this guide step-by-step. Open a blank notepad on your computer to collect these 8 items as we go.

---

## Phase 1: The Secrets Checklist (Gather These First!)

### 1. Your Domain Name & Cloudflare API Token (`NEXUS_PUBLIC_DOMAIN` & `CLOUDFLARE_API_TOKEN`)
You need a web address (domain) to access your Nexus dashboard.
1. You must own a domain name (e.g., `yourdomain.com`).
2. Decide on the specific URL you will use for Nexus (e.g., `nexus.yourdomain.com`). 
   * 👉 **Save this as your `NEXUS_PUBLIC_DOMAIN`.**
3. *(Optional but Highly Recommended):* Route your domain's DNS through Cloudflare (it's free).
   * Go to Cloudflare > My Profile (top right) > API Tokens > Create Token > Create Custom Token.
   * Permissions: `Zone` | `DNS` | `Edit`.
   * Zone Resources: `Include` | `Specific Zone` | `yourdomain.com`.
   * Click Continue to summary, then Create Token. Copy the secret token.
   * 👉 **Save this as your `CLOUDFLARE_API_TOKEN`.** (If you don't use Cloudflare, leave this blank later).

### 2. Your Google Cloud Project (`DOCAI_PROJECT_ID`)
Google Cloud is where your server and databases will live.
1. Go to the [Google Cloud Console](https://console.cloud.google.com) and sign in.
2. Click the dropdown at the top left (next to the Google Cloud logo) and click **New Project**.
3. Name it `nexus-ai-engine` and click **Create**.
4. Make sure your new project is selected at the top. Look at the "Project Info" card on your dashboard. Note the **Project ID** (it might have numbers at the end, like `nexus-ai-engine-12345`). 
   * 👉 **Save this as your `DOCAI_PROJECT_ID`.**
5. *Billing:* Go to **Billing** in the left menu and link a credit card. The server you will build is part of Google's "Always Free" tier, but Google requires a card on file to use cloud features.

### 3. Your Gemini AI Brain (`NEXUS_API_KEY`)
This gives Nexus its intelligence.
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in, and click **Get API key** in the left menu.
3. Click **Create API key** and select your new Google Cloud Project (`nexus-ai-engine`).
4. Copy the long string of letters and numbers generated. 
   * 👉 **Save this as your `NEXUS_API_KEY`.**

### 4. Your Document OCR Reader (`DOCAI_LOCATION` & `DOCAI_PROCESSOR_ID`)
This lets Nexus read text from scanned PDFs and images.
1. In the Google Cloud Console, search for "Document AI" in the top search bar. Click **Enable API** if prompted.
2. Click **Explore Processors**, find **Document OCR**, and click **Create Processor**.
3. Name it `nexus-ocr` and set the region to `us`. 
   * 👉 **Save `us` as your `DOCAI_LOCATION`.**
4. Once created, go to the Processor Details page. You will see an ID string that looks like `1a2b3c4d5e6f7g8h`. 
   * 👉 **Save this as your `DOCAI_PROCESSOR_ID`.**

### 5. Your Login Security (`GOOGLE_CLIENT_ID` & `credentials.json`)
This creates the secure "Sign in with Google" button so Nexus can read your Gmail/Drive.
1. **Consent Screen:** In the Google Cloud Console, search for "OAuth consent screen".
   * Choose **External** (or Internal if you are a Google Workspace business user) and click Create.
   * App name: `Nexus`. Select your email for the support and developer contact emails. Click Save and Continue.
   * *Skip Scopes and Test Users by clicking Save and Continue.*
   * **CRITICAL:** On the summary screen, click the **Publish App** button to push it to "In production". If you leave it in "Testing", your login tokens will expire every 7 days!
2. **Create Credentials:** Click **Credentials** on the left menu.
   * Click **+ CREATE CREDENTIALS** -> **OAuth client ID**.
   * Application type: **Desktop app**. Name it `Nexus Auth`. Click Create.
   * A box will pop up. Copy your "Client ID" (it ends in `.apps.googleusercontent.com`). 
     * 👉 **Save this as your `GOOGLE_CLIENT_ID`.**
   * **CRITICAL:** Click the **Download JSON** button on that popup. Save it to your computer, rename it exactly to `credentials.json`, and place it inside your `Nexus-for-Google` folder (right next to the `nexus.sh` script).

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
* It will prompt you to paste in all the variables you gathered in Phase 1.
* It will then talk to Google, create a free-tier virtual machine server, configure firewalls, and install the necessary software.

**CRITICAL DNS STEP:** At the end of this step, the terminal will output your new server's **Public IP Address**. Go to your domain provider (e.g., Cloudflare, GoDaddy) and create an **A Record** pointing `nexus.yourdomain.com` to that IP address.

### Step 2: Zero-Downtime Deployment
Wait about 5 minutes for your DNS record to propagate across the internet, then run:
<pre><code class="language-bash">./nexus.sh --deploy</code></pre>
* The script will compress your code, securely upload it to your new server, build the React frontend, set up the databases, and launch the web server.

### Step 3: Setting Up the Auth Tunnel
The server is now running, but it doesn't have permission to read your emails yet. We need to create a secure tunnel to the server to grant it access.
<pre><code class="language-bash">./nexus.sh --auth-tunnel</code></pre>
* The script will pause the server and open a secure tunnel to your computer.
* A link will appear in your terminal. **Ctrl+Click** it to open it in your browser. 
* Google will warn you that the app isn't verified (because you just made it). Click **Advanced** -> **Go to Nexus (unsafe)**. Click **Continue** to grant the permissions.
* Return to your terminal. The script will automatically save the connection token and restart your Nexus server!

### You are done! 🎉
Navigate to your domain (`https://nexus.yourdomain.com`). Log in with Google, open the **System Settings** menu (gear icon), and click **Generate & Apply Theme** to bring Nexus V3 to life.