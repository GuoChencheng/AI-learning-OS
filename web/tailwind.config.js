/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    screens: {
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px"
    },
    extend: {
      colors: {
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        subtle: "rgb(var(--color-subtle) / <alpha-value>)",
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        panel: "rgb(var(--color-panel) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        verified: "rgb(var(--color-state-verified) / <alpha-value>)",
        "open-loop": "rgb(var(--color-state-open-loop) / <alpha-value>)",
        "trust-gap": "rgb(var(--color-state-trust-gap) / <alpha-value>)",
        overdue: "rgb(var(--color-state-overdue) / <alpha-value>)",
        state: {
          verified: "rgb(var(--color-state-verified) / <alpha-value>)",
          open_loop: "rgb(var(--color-state-open-loop) / <alpha-value>)",
          trust_gap: "rgb(var(--color-state-trust-gap) / <alpha-value>)",
          overdue: "rgb(var(--color-state-overdue) / <alpha-value>)"
        }
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "Segoe UI",
          "ui-sans-serif",
          "system-ui",
          "sans-serif"
        ],
        display: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "Segoe UI",
          "ui-sans-serif",
          "system-ui",
          "sans-serif"
        ],
        mono: ["SFMono-Regular", "SF Mono", "ui-monospace", "monospace"]
      },
      fontSize: {
        display: ["2rem", { lineHeight: "1.08", fontWeight: "680", letterSpacing: "0em" }],
        h1: ["1.5rem", { lineHeight: "1.16", fontWeight: "650", letterSpacing: "0em" }],
        h2: ["1.125rem", { lineHeight: "1.28", fontWeight: "650", letterSpacing: "0em" }],
        body: ["0.9375rem", { lineHeight: "1.55", fontWeight: "400", letterSpacing: "0em" }],
        caption: ["0.8125rem", { lineHeight: "1.45", fontWeight: "450", letterSpacing: "0em" }],
        meta: ["0.75rem", { lineHeight: "1.35", fontWeight: "560", letterSpacing: "0em" }],
        micro: ["0.6875rem", { lineHeight: "1.35", fontWeight: "560", letterSpacing: "0em" }]
      },
      spacing: {
        gutter: "var(--layout-gutter)",
        rail: "var(--layout-rail)",
        section: "var(--layout-section-gap)",
        field: "var(--layout-field-gap)",
        "grid-gap": "var(--layout-grid-gap)"
      },
      maxWidth: {
        page: "var(--layout-page-max)",
        readable: "var(--layout-readable-max)",
        data: "var(--layout-data-max)"
      },
      gridTemplateColumns: {
        app: "var(--grid-app)",
        cockpit: "var(--grid-cockpit)",
        "dashboard-state": "var(--grid-dashboard-state)",
        strict: "repeat(12, minmax(0, 1fr))"
      },
      borderRadius: {
        DEFAULT: "var(--radius-sm)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-lg)",
        "2xl": "var(--radius-lg)",
        full: "999px"
      },
      letterSpacing: {
        tighter: "0em",
        tight: "0em",
        normal: "0em",
        wide: "0em",
        wider: "0em",
        widest: "0em"
      },
      boxShadow: {
        subtle: "none",
        focus: "0 0 0 2px rgb(var(--color-accent) / 0.18)"
      }
    }
  },
  plugins: []
};
