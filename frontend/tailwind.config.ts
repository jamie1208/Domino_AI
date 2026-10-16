import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        accent: "hsl(var(--accent))",
        secondary: "hsl(var(--secondary))",
        tertiary: "hsl(var(--tertiary))",
        quaternary: "hsl(var(--quaternary))",
        border: "hsl(var(--border))",
        card: "hsl(var(--card))",
      },
      fontFamily: {
        heading: ["Outfit", "system-ui", "sans-serif"],
        body: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      borderRadius: { sm: "8px", md: "16px", lg: "24px" },
      boxShadow: {
        hard: "4px 4px 0 hsl(var(--foreground))",
        "hard-hover": "6px 6px 0 hsl(var(--foreground))",
        pink: "8px 8px 0 hsl(var(--secondary) / .45)",
        yellow: "8px 8px 0 hsl(var(--tertiary) / .55)",
      },
    },
  },
  plugins: [],
} satisfies Config;
