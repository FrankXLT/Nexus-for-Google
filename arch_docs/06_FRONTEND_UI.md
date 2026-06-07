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

## 6.5 The Aesthetic Law (Material Design Dashboard)
The frontend MUST strictly adhere to the following design language, inspired by modern Material Dashboards. The default theme is **Dark Mode**.

### 6.5.1 CSS & Component Styling
1. **Dual-Layer Dark Mode:** The app background (`bg_base`) must be a deep, dark charcoal/black. The cards (`bg_surface`) must be a slightly elevated, lighter dark hue (e.g., deep navy/slate) to create depth without harsh borders.
2. **Floating Offset Headers:** Dashboard cards containing charts or metrics MUST feature a colored, offset square header (floating slightly above and outside the top-left or top-center of the main card container) containing an icon and a soft drop-shadow.
3. **Elevation:** Strict use of soft CSS box-shadows to define Z-index elevation. Flat, border-only designs for major containers are forbidden.

### 6.5.2 SVG Icon Mapping
The coding agent MUST use the specific SVGs provided in the `/images/` directory. Do not use external icon fonts.
- **`search_icon.svg`, `gmail_icon.svg`, `google_drive_icon.svg`**: Used inside the Omnibox for the multi-source proxy toggle.
- **`heatmap_icon.svg`**: Used as the offset header icon for the VQB Activity Heatmap card.
- **`taxonomy_flow_icon.svg` & `flow-branch-svgrepo-com.svg`**: Used in the VQB Sankey diagram toggles.
- **`knowledge_graph_icon.svg`**: Used in the Tri-Mode toggle to select the Masonry Card view.
- **`treemap_graph_icon.svg`**: Used in the Tri-Mode toggle to select the Volumetric Drill-Down view.
- **`taxonomy_table.svg` & `taxonomy_linkages_icon.svg`**: Used in the Zero Trust Settings Console.
- **`alert_quaratine.svg`**: Used as a flashing red indicator in the Global Notifier and the Heatmap.
- **`bookmark_filled_icon.svg` / `bookmark_unfilled_icon.svg`**: Used to toggle the `nexus_starred` 7-day velocity state.