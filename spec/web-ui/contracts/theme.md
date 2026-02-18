# Theme

## Status
⏸️ Not started

## Purpose

Shared token system consumed by all renderer backends (DOM, Canvas, WebGL).
Ensures visual consistency across the entire UI. Tokens cover color, spacing,
typography, elevation, and motion. Dark mode is the primary design target.

See [doctrine](../doctrine.md) for the visual principles that govern
token choices.

## Depends On
None.

## Interface

```
ThemeTokens {
  color: {
    bg:        {surface, elevated, overlay}
    fg:        {primary, secondary, muted, inverse}
    accent:    {primary, hover, active}
    border:    {subtle, standard, strong, focus}
    status:    {error, warning, success, info}
  }
  spacing: {
    unit:      number (px)           // base grid unit
    xs:        number                // e.g., 2px
    sm:        number                // e.g., 4px
    md:        number                // e.g., 8px
    lg:        number                // e.g., 16px
    xl:        number                // e.g., 24px
  }
  typography: {
    fontFamily:    string            // variable font preferred
    fontMono:      string
    size:          {xs, sm, md, lg, xl}
    weight:        {normal, medium, semibold, bold}
    lineHeight:    {tight, normal, relaxed}
  }
  elevation: {
    shadow:    {none, low, medium, high}   // 2-4 levels
  }
  motion: {
    duration:  {fast, normal, slow}        // 120-250ms range
    easing:    {default, spring, easeOut}  // non-linear only
  }
  hit: {
    fineMin:   number                // fine-pointer min (32px class)
    coarseMin: number                // coarse-pointer min (44px)
  }
}
```

**Color lanes:** dark (primary), light, high-contrast, forced-colors.
Each lane is a complete set of tokens, not a filter on the primary.

## Invariants

1. All renderer backends consume the same token set — no backend-specific tokens
2. Dark mode tokens are designed independently, not derived by inversion
3. Every color lane is a complete, self-contained token set
4. Motion easing is always non-linear (spring or ease-out, never linear)
5. Motion duration stays in the 120-250ms range
6. Fine-pointer targets are at least 32px; coarse-pointer at least 44px effective

## Behavior

1. Theme is injected at renderer initialization; backends read tokens, not raw CSS values
2. Lane switching replaces the entire token set atomically (no partial swaps)
3. DOM backend applies tokens via CSS custom properties
4. Canvas/WebGL backend reads tokens directly from the theme object
5. Components reference semantic roles (e.g., `border.focus`) not literal colors
6. Missing tokens fall back to the dark lane defaults

## Anti-Patterns

1. Never hardcode colors, sizes, or durations — use tokens
2. Never derive dark mode from light mode by inversion
3. Never use linear easing
4. Never use high-saturation accents as defaults
5. Never create backend-specific token overrides
6. Never partially swap lane tokens (atomic replacement only)

## Out of Scope

- Token value definitions (design concern, not spec)
- User theme customization UI
- CSS-in-JS implementation details

## Conformance Check
Run: `node spec/web-ui/checks/theme.test.mjs`
