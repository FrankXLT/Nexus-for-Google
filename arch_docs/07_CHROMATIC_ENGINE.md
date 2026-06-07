# Layer 7: The Generative Chromatic Engine

## 7.1 AI Theme Generation & Database Injection
Coding agents are **FORBIDDEN** from hardcoding UI colors. All dynamic UI coloring MUST be driven by the database.

1. **The 8 Semantic Support Colors:** The system utilizes exactly 8 operational UI colors stored in `CONFIG_SYSTEM`: 
   - `primary` (Active tabs/focus rings/brand)
   - `success` (Completed/OK)
   - `warning` (Quotas/Alerts)
   - `error` (Quarantine/Failures/Destructive)
   - `info` (Toasts/Help)
   - `muted` (Disabled/Archived text)
   - `highlight` (Search term matches)
   - `ai_sparkle` (Gemini evaluation states).
2. **Database Color Injection (The Scaling Law):** The exact hex colors for taxonomy nodes do NOT live in a disconnected array. When the `GENERATE_UI_THEME` prompt runs, the backend Python worker MUST parse the AI's JSON output and execute a SQL `UPDATE` statement, permanently saving the generated hex codes into the `CATEGORIES.color_hex` and `PURPOSES.color_hex` columns. The frontend SPA queries these tables directly to assign CSS variables.

## 7.2 Entity Branding & Readability Modding
Entities utilize True Brand Hex codes extracted via Google Grounding (saved in `ENTITIES.primary_color_hex`). 
- **The WCAG Law:** True brand colors injected into the UI (e.g., Heatmaps, Sankey flows) may clash horribly with the AI-generated background. The frontend Javascript MUST run a WCAG AA contrast check. 
- **The Shift:** If the contrast ratio fails (< 4.5:1), the JS must mathematically shift the `Lightness (L)` in HSL or the Opacity until it reaches a readable threshold, preserving brand identity without breaking usability.

## 7.3 Backend Euclidean API Snapping
Google Drive and Gmail Workspace APIs strictly enforce an internal palette of ~24 Material colors. Sending an arbitrary brand hex causes an API failure.
- Before the `ACTIONABLE` worker calls the Workspace APIs to colorize a folder or label, it MUST run the True Brand Hex through a **3D Euclidean Distance** mathematical function in the RGB color space.
- *Math:* `Distance = sqrt((R2 - R1)^2 + (G2 - G1)^2 + (B2 - B1)^2)`
- The physically applied color is the nearest Euclidean neighbor from Google's predefined acceptable hex list, ensuring zero API crashes.