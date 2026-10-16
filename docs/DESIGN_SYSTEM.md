# Domino AI Playful Geometric tokens

Design philosophy: Stable Grid, Wild Decoration. Landing is playful, graph workspace is sober, readable, trustworthy.

Light colors:
- background #FFFDF5
- foreground #1E293B
- muted #F1F5F9
- mutedForeground #64748B
- accent #8B5CF6
- secondary #F472B6
- tertiary #FBBF24
- quaternary #34D399
- border #E2E8F0
- card #FFFFFF
- focus ring #8B5CF6

Heading font: Outfit, system-ui, sans-serif (700/800).
Body font: Plus Jakarta Sans, system-ui, sans-serif (400/500).
Radii: sm 8px; md 16px; lg 24px; full 9999px. Default border 2px.
Hard offset shadow: 4px 4px 0 #1E293B; hover 6px; active 2px. Cards may use 8px hard light/pink shadow.

Rules:
- Buttons: violet pill, dark 2px border, white foreground, hard shadow.
- Cards: white, thick dark border, rounded edges, contextual colored icon circles.
- Primary max-width 1152px; 12-column desktop grid; mobile stack; tappable >=48px.
- Background squiggles, dots and confetti are decorative and must not overlap data.
- Graph nodes and risk severity use explicit labels, shape, and text — never color-only.
- Respect `prefers-reduced-motion`; visible keyboard focus and contrast checks.
- Avoid pricing page or flashy misleading investment/risk claims.
