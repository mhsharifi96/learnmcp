import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        lapis: "var(--lapis)",
        turquoise: "var(--turquoise)",
        saffron: "var(--saffron)",
        mist: "var(--mist)",
        surface: "var(--surface)",
        line: "var(--line)",
        quiet: "var(--quiet)",
        danger: "var(--danger)",
        ok: "var(--ok)",
      },
      fontFamily: {
        display: ["var(--font-body)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      maxWidth: { prose: "72ch" },
    },
  },
  plugins: [],
} satisfies Config;
