# Layer 7: The Generative Chromatic Engine

## 7.1 AI Theme Generation (The Anti-Circus UI Law)
Coding agents are **FORBIDDEN** from hardcoding Tailwind UI colors (e.g., `bg-red-500`, `text-blue-600`) for structural taxonomy elements or entity badges. All dynamic UI coloring MUST be driven by CSS Variables mapped from an AI-generated JSON theme.
1. **The Seed:** Users input a 5-10 color hex palette in Settings.
2. **The Architect:** Nexus sends the seed to the `GENERATE_UI_THEME` prompt. The LLM mathematically calculates and outputs a complete JSON matrix containing:
   - `background` & `surface` (optimized to sit *outside* the seed palette for max contrast).
   - 12 `support` semantic colors (success, error, warning) harmonized/hue-shifted to the seed aesthetic.
   - 36 vibrant `category` colors.
   - 64 matte/desaturated `purpose` colors.

## 7.2 Entity Branding & Readability Modding
Entities utilize True Brand Hex codes extracted via Google Grounding (saved in `ENTITIES.primary_color_hex`). 
- **The WCAG Law:** True brand colors injected into the UI (e.g., Heatmaps, Sankey flows) may clash horribly with the AI-generated background. The frontend Javascript MUST run a WCAG AA contrast check. 
- **The Shift:** If the contrast ratio fails (< 4.5:1), the JS must mathematically shift the `Lightness (L)` in HSL or the Opacity until it reaches a readable threshold, preserving brand identity without breaking usability.

## 7.3 Backend Euclidean API Snapping
Google Drive and Gmail Workspace APIs strictly enforce an internal palette of ~24 Material colors. Sending an arbitrary brand hex causes an API failure.
- Before the `ACTIONABLE` worker calls the Workspace APIs to colorize a folder or label, it MUST run the True Brand Hex through a **3D Euclidean Distance** mathematical function in the RGB color space.
- *Math:* `Distance = sqrt((R2 - R1)^2 + (G2 - G1)^2 + (B2 - B1)^2)`
- The physically applied color is the nearest Euclidean neighbor from Google's predefined acceptable hex list, ensuring zero API crashes.