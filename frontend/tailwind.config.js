/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgBase: 'var(--bg-base)',
        bgSurface: 'var(--bg-surface)',
        textPrimary: 'var(--text-primary)',
        textSecondary: 'var(--text-secondary)',
        accentPrimary: 'var(--accent-primary)',
        success: 'var(--success, #34D399)',
        warning: 'var(--warning, #FBBF24)',
        error: 'var(--error, #EF4444)',
        info: 'var(--info, #556D8C)',
        muted: 'var(--muted, #8B949E)',
        highlight: 'var(--highlight, #FFF176)',
        aiSparkle: 'var(--ai-sparkle, #FABC12)',
      },
      boxShadow: {
        card: '0 4px 24px rgba(0,0,0,0.5)',
        glow: '0 0 20px rgba(106,90,169,0.3)',
        glowRed: '0 0 14px rgba(239,68,68,0.4)',
        glowGold: '0 0 12px rgba(250,188,18,0.35)',
        'inner-subtle': 'inset 0 1px 0 rgba(255,255,255,0.04)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', '"Cascadia Code"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      borderRadius: {
        xl: '14px',
        '2xl': '18px',
      },
    },
  },
  plugins: [],
}