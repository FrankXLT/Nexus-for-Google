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
Google Workspace APIs (specifically Gmail Labels) strictly enforce an internal palette. Sending an arbitrary brand hex causes an API failure.
- Before the `ACTIONABLE` worker calls the Gmail API, it MUST run the entity's True Brand Hex through a **3D Euclidean Distance** mathematical function in the RGB color space.
- The physically applied color MUST be the nearest Euclidean neighbor chosen from the predefined list of valid Gmail `textColor` and `backgroundColor` pairs. 
- **The Zero-Dependency Math Law:** Agents are FORBIDDEN from importing heavy math/imaging libraries (like `scipy`, `numpy`, or `colormath
- The physically applied color MUST be the nearest Euclidean neighbor chosen from the following exact predefined list of valid Gmail `textColor` and `backgroundColor` pairs. Agents are FORBIDDEN from hallucinating other combinations:
```json
[
  {"textColor": "#000000", "backgroundColor": "#43d692"},
  {"textColor": "#ffffff", "backgroundColor": "#434343"},
  {"textColor": "#000000", "backgroundColor": "#f691b2"},
  {"textColor": "#ffffff", "backgroundColor": "#fc2a1d"},
  {"textColor": "#000000", "backgroundColor": "#ffad46"},
  {"textColor": "#000000", "backgroundColor": "#ffffff"},
  {"textColor": "#000000", "backgroundColor": "#b3efd3"},
  {"textColor": "#ffffff", "backgroundColor": "#a479e2"},
  {"textColor": "#000000", "backgroundColor": "#fbd3e0"},
  {"textColor": "#ffffff", "backgroundColor": "#16a765"},
  {"textColor": "#000000", "backgroundColor": "#cccccc"},
  {"textColor": "#000000", "backgroundColor": "#a4c2f4"},
  {"textColor": "#000000", "backgroundColor": "#fc9775"},
  {"textColor": "#000000", "backgroundColor": "#ffbc6b"},
  {"textColor": "#ffffff", "backgroundColor": "#4cb04f"},
  {"textColor": "#ffffff", "backgroundColor": "#999999"},
  {"textColor": "#ffffff", "backgroundColor": "#000000"},
  {"textColor": "#ffffff", "backgroundColor": "#1a1a1a"},
  {"textColor": "#ffffff", "backgroundColor": "#cc3a21"},
  {"textColor": "#ffffff", "backgroundColor": "#ea9999"},
  {"textColor": "#ffffff", "backgroundColor": "#990000"},
  {"textColor": "#000000", "backgroundColor": "#fce8b2"},
  {"textColor": "#000000", "backgroundColor": "#f1c232"},
  {"textColor": "#ffffff", "backgroundColor": "#e69138"},
  {"textColor": "#ffffff", "backgroundColor": "#b45f06"},
  {"textColor": "#000000", "backgroundColor": "#d9d2e9"},
  {"textColor": "#000000", "backgroundColor": "#b4a7d6"},
  {"textColor": "#ffffff", "backgroundColor": "#8e7cc3"},
  {"textColor": "#ffffff", "backgroundColor": "#674ea7"},
  {"textColor": "#ffffff", "backgroundColor": "#351c75"},
  {"textColor": "#000000", "backgroundColor": "#c9daf8"},
  {"textColor": "#ffffff", "backgroundColor": "#6d9eeb"},
  {"textColor": "#ffffff", "backgroundColor": "#3c78d8"},
  {"textColor": "#ffffff", "backgroundColor": "#1155cc"},
  {"textColor": "#ffffff", "backgroundColor": "#0b5394"},
  {"textColor": "#000000", "backgroundColor": "#d0e0e3"},
  {"textColor": "#000000", "backgroundColor": "#a2c4c9"},
  {"textColor": "#ffffff", "backgroundColor": "#76a5af"},
  {"textColor": "#ffffff", "backgroundColor": "#45818e"},
  {"textColor": "#ffffff", "backgroundColor": "#134f5c"}
]