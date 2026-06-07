# Layer 7: The Generative Chromatic Engine

## 7.1 AI Theme Generation & Dynamic Regeneration
Coding agents are **FORBIDDEN** from hardcoding UI colors (e.g., `bg-red-500`). All dynamic UI coloring MUST be driven by CSS Variables mapped from the JSON theme matrix.
1. **The Day 0 Seed:** The system is seeded via `CONFIG_SYSTEM` with a mathematically balanced Dark Mode palette (Backgrounds, 12 Support, 16 Category, and 20 Purpose colors) based on the user's Colormind configuration.
2. **AI Regeneration (The Scaling Law):** The system does not store empty/placeholder colors. If the user adds a 17th Category or a 21st Purpose, the backend MUST trigger the `GENERATE_UI_THEME` prompt. The LLM will re-evaluate the seed palette and output a perfectly redistributed HSL color wheel array for the exact new count, overwriting the JSON string in the database.

## 7.2 Entity Branding & Readability Modding
Entities utilize True Brand Hex codes extracted via Google Grounding (saved in `ENTITIES.primary_color_hex`). 
- **The WCAG Law:** True brand colors injected into the UI (e.g., Heatmaps, Sankey flows) may clash horribly with the AI-generated background. The frontend Javascript MUST run a WCAG AA contrast check. 
- **The Shift:** If the contrast ratio fails (< 4.5:1), the JS must mathematically shift the `Lightness (L)` in HSL or the Opacity until it reaches a readable threshold, preserving brand identity without breaking usability.

## 7.3 Backend Euclidean API Snapping
Google Drive and Gmail Workspace APIs strictly enforce an internal palette of ~24 Material colors. Sending an arbitrary brand hex causes an API failure.
- Before the `ACTIONABLE` worker calls the Workspace APIs to colorize a folder or label, it MUST run the True Brand Hex through a **3D Euclidean Distance** mathematical function in the RGB color space.
- *Math:* `Distance = sqrt((R2 - R1)^2 + (G2 - G1)^2 + (B2 - B1)^2)`
- The physically applied color is the nearest Euclidean neighbor from Google's predefined acceptable hex list, ensuring zero API crashes.