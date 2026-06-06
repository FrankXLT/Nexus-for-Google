# Layer 6: Frontend UI & Rendering Strategy

## 6.1 Rendering Performance Mandates
The frontend is a Material Design 3 Single Page Application (SPA). To prevent browser memory crashes on massive personal datasets, agents MUST strictly adhere to:
1. **DOM Virtualization (Windowing):** Any view rendering multiple artifacts (Knowledge Graph, Staging Grid, Taxonomy Matrix) MUST use virtualization. Only HTML nodes visible in the viewport (+ buffer) are rendered to the DOM.
2. **Server-Side Pagination:** Excel-style sorting and filtering MUST trigger server-side queries using SQL `LIMIT` and `OFFSET`. Fetching `SELECT *` to memory is forbidden.
3. **Debouncing:** All Omnibox text input and visual filter changes MUST be debounced by 300ms before firing a backend API fetch.
4. **Optimistic UI:** When a user executes an action (e.g., Approving a Quarantine item), the UI immediately reflects the success state locally, while the actual API call processes asynchronously in the background.

## 6.2 The Homepage (Omnibox & VQB)
- **The Omnibox (Multi-Source Proxy):** Dropdown toggle sets scope (`🌌 Local Nexus DB`, `📧 Proxy: Gmail`, `📁 Proxy: Google Drive`). Accepts text and visual "Chips".
- **Visual Query Box (VQB):** 
  - *Activity Heatmap:* Y-Axis = Top Senders (user-defined limit), X-Axis = Time (Month, Quarter, Year toggles). Colors use True Entity Brand Hex. **Quarantined senders flash RED.** 
  - *Taxonomy Flow:* Sankey diagram (`Category ➔ Alias ➔ Purpose`). Includes a "Shatter Aliases" toggle to expose sub-entities. Clicking any node drops a Chip into the Omnibox.

## 6.3 Search Results Engine (Tri-Mode)
Results render below the VQB via lazy-loading grids.
1. **Knowledge Graph (Nexus Scope):** Masonry grid of cards using the 1-3 sentence `ui_summary`.
2. **Volumetric Treemap (Nexus Scope):** 3-Tier D3.js (or equivalent) visual drill-down. Dynamically roots based on query depth (Broad Query = `Category ➔ Alias ➔ Sub-Entity`; Narrow Query = `Entity/Sub-Entity ➔ Purpose ➔ Artifact`).
3. **Staging Grid (Proxy Scope):** Inbox-style layout for raw Gmail/Drive queries. Checked items execute a batch dump to the `RAW` webhook ingress.
4. **Context Modal:** Clicking an artifact opens a central modal to edit taxonomy or deep-link to the workspace file.

## 6.4 Taxonomy Management (Zero Trust Console)
Administrative interface for managing `TAXONOMY_LINKAGES`.
- **Flow View:** Visual nodes/cards for merging aliases or re-parenting entities.
- **Matrix View:** Infinite-scroll, virtualized data grid of linkages with Excel-style inline dropdowns to rapidly bulk-edit `gmail_sync_mode` or Purpose mapping.