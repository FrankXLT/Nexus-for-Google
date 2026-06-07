# Layer 6: Frontend UI & Rendering Strategy

## 6.1 Hosting, Tech Stack & Authentication Architecture
To enforce Zero-Trust, prevent "framework thrashing" by AI coding agents, and ensure rendering performance:
1. **The Technology Stack:** The frontend MUST be built using **Vite + React 18+ + Tailwind CSS**. React has the most mature ecosystem for DOM Virtualization (`react-virtuoso` or `react-window`), which is a mandatory structural law.
2. **Data Visualization:** **Mermaid.js** (via React wrapper components) MUST be used for rendering the VQB Taxonomy Sankey flows and linkages.
3. **Unified Routing (Zero CORS):** The SPA is built statically and served on the root domain (`/`) by the Caddy web server. Caddy acts as a reverse proxy, seamlessly routing all `/api/*` and `/webhook/*` calls back to the FastAPI Python server. Because the browser sees both the UI and the API on the exact same origin, CORS configurations are eliminated.
4. **Authentication (Google SSO & Strict Allowlist):** The frontend relies on Google Sign-In (OpenID Connect). Passwords are forbidden.
   - **The Bouncer:** When the frontend passes the Google ID Token to the backend, FastAPI MUST cryptographically verify the token and extract the user's `email`. It strictly checks this against the comma-separated `AUTHORIZED_EMAILS` list in the `.env` file. Unauthorized emails receive an `HTTP 403 Forbidden`.
   - **Session:** Authorized users receive an internal JWT stored in a secure, `HttpOnly`, `SameSite=Strict` cookie.
   - **Status Ping:** Because frontend JavaScript cannot read `HttpOnly` cookies (preventing XSS), the backend MUST expose an `/api/auth/status` endpoint. The React SPA silently pings this on initialization/refresh to verify cookie validity and route to the Dashboard.

## 6.2 Rendering Performance Mandates
The frontend is a Material Design 3 Single Page Application (SPA). To prevent browser memory crashes on massive personal datasets, agents MUST strictly adhere to:
1. **DOM Virtualization (Windowing):** Any view rendering multiple artifacts (Knowledge Graph, Staging Grid, Taxonomy Matrix) MUST use virtualization. Only HTML nodes visible in the viewport (+ buffer) are rendered to the DOM.
2. **Server-Side Pagination:** Excel-style sorting and filtering MUST trigger server-side queries using SQL `LIMIT` and `OFFSET`. Fetching `SELECT *` to memory is forbidden.
3. **Debouncing:** All Omnibox text input and visual filter changes MUST be debounced by 300ms before firing a backend API fetch.
4. **Optimistic UI:** When a user executes an action (e.g., Approving a Quarantine item), the UI immediately reflects the success state locally, while the actual API call processes asynchronously in the background.

## 6.3 The Homepage (Omnibox & VQB)
- **The Omnibox (Multi-Source Proxy):** Dropdown toggle sets scope (`🌌 Local Nexus DB`, `📧 Proxy: Gmail`, `📁 Proxy: Google Drive`). Accepts text and visual "Chips".
- **Visual Query Box (VQB):** 
  - *Activity Heatmap:* Y-Axis = Top Senders (user-defined limit), X-Axis = Time (Month, Quarter, Year toggles). Colors use True Entity Brand Hex. **Quarantined senders flash RED.** 
  - *Taxonomy Flow:* Sankey diagram (`Category ➔ Alias ➔ Purpose`). Includes a "Shatter Aliases" toggle to expose sub-entities. Clicking any node drops a Chip into the Omnibox.

## 6.4 Search Results Engine (Tri-Mode)
Results render below the VQB via lazy-loading grids.
1. **Knowledge Graph (Nexus Scope):** Masonry grid of cards using the 1-3 sentence `ui_summary`.
2. **Volumetric Treemap (Nexus Scope):** 3-Tier D3.js (or equivalent) visual drill-down. Dynamically roots based on query depth (Broad Query = `Category ➔ Alias ➔ Sub-Entity`; Narrow Query = `Entity/Sub-Entity ➔ Purpose ➔ Artifact`).
3. **Staging Grid (Proxy Scope):** Inbox-style layout for raw Gmail/Drive queries. Checked items execute a batch dump to the `RAW` webhook ingress.
4. **Context Modal:** Clicking an artifact opens a central modal to edit taxonomy or deep-link to the workspace file.

## 6.5 Taxonomy Management (Zero Trust Console)
Administrative interface for managing `TAXONOMY_LINKAGES`.
- **Flow View:** Visual nodes/cards for merging aliases or re-parenting entities.
- **Matrix View:** Infinite-scroll, virtualized data grid of linkages with Excel-style inline dropdowns to rapidly bulk-edit `gmail_sync_mode` or Purpose mapping.

## 6.6 The Aesthetic Law (Material Dashboard)
The frontend MUST strictly adhere to a modern Material Dashboard design language (e.g., Creative Tim). The default theme is **Dark Mode**.

### 6.6.1 CSS & Component Styling
1. **Dual-Layer Dark Mode:** The app background (`bg_base`) must be a deep, dark charcoal/black. The UI cards (`bg_surface`) must be a slightly elevated, lighter dark hue to create depth without harsh borders.
2. **Floating Offset Headers:** Dashboard cards containing charts, tables, or metrics MUST feature a colored, offset square header (floating slightly above and outside the top-left or top-center of the main card container) containing an icon and a soft drop-shadow.
3. **Elevation:** Strict use of soft CSS box-shadows to define Z-index elevation. Flat, border-only designs for major containers are forbidden.

### 6.6.2 SVG Icon Mapping (The Asset Vault)
The coding agent MUST strictly use the specific SVGs provided in the `/IMAGES/` directory. External web-font libraries (e.g., FontAwesome) are strictly forbidden to ensure offline capability and asset control.

**Core Navigation & UI Controls:**
- `menu.svg` & `menu-dots.svg`: Collapsing the left navigation sidebar or opening context menus.
- `user-round-svgrepo.svg`: Top-right profile and authentication state.
- `setting-config.svg` (or `settings-gear-options-preferences-configuration.svg`): Triggering the Zero Trust Settings modal.
- `sync-svgrepo-com.svg`: Manual UI state refreshes and polling indicators.
- `close-ellipse.svg`: Dismissing modals, notifications, or deleting Omnibox chips.
- `chevron-*.svg` (The entire suite including `double` and `selector` variants): Used for expanding Treemap nodes, dropdowns, and pagination.
- `filter.svg` & `filter-xmark.svg`: Column filtering in the Taxonomy Matrix.
- `open-external.svg`: Used on artifact cards to deep-link out to the native Workspace file.

**Search & Core Modes:**
- `search_icon.svg`, `gmail_icon.svg`, `google_drive_icon.svg`: Used inside the Omnibox for the multi-source proxy toggle.
- `knowledge_graph_icon.svg`: Tri-Mode toggle (Masonry Card view).
- `treemap_graph_icon.svg`: Tri-Mode toggle (Volumetric Drill-Down view).

**Data Visualization & Dashboards:**
- `heatmap_icon.svg`, `stats-svgrepo-com.svg`: Used as offset header icons for Activity and Metrics cards.
- `taxonomy_flow_icon.svg`, `flow-branch.svg`: Used in the VQB Sankey diagram toggles.

**Taxonomy Management & Alerts:**
- `taxonomy_table.svg`, `taxonomy_linkages_icon.svg`: Used in the Zero Trust Settings Console.
- `alert_quaratine.svg`: Flashing red indicator in the Global Notifier and the Heatmap.
- `bookmark_filled_icon.svg`, `bookmark_unfilled_icon.svg`: Toggles the `nexus_starred` 7-day velocity state.

**State Indicators & AI:**
- `google-gemini-logo.svg`: Used as a pulsing "sparkle/magic" indicator when an artifact is actively in the `EVALUATING` or `ASSIMILATING` LLM state.## 6.5 The Aesthetic Law (Material Dashboard)
The frontend MUST strictly adhere to a modern Material Dashboard design language (e.g., Creative Tim). The default theme is **Dark Mode**.

