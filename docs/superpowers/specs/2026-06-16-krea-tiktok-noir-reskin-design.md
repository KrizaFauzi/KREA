# KREA — TikTok Noir UI/UX Re-skin

**Date:** 2026-06-16
**Status:** Approved (design)

## Goal

Make KREA's frontend look professional, "TikTok-ish", clean, and simple. This is a
visual re-skin only — no layout restructuring, no new features, no backend or
behavior changes.

## Decisions

- **Visual direction:** TikTok Noir — true black background with TikTok's signature
  cyan (`#25F4EE`) and red (`#FE2C55`) accents.
- **Scope:** Clean re-skin. Keep the existing layout (header, chat timeline,
  message bubbles, video-prompt card, composer) and all React logic unchanged.
- **No additions:** no active step tracker, no welcome hero, no suggestion chips.

## Implementation surface

Almost entirely `frontend/src/styles.css`. Tiny class touch-ups in
`frontend/src/App.jsx` and `frontend/src/VideoPromptCard.jsx` only if a class is
needed — no logic changes. The dead styles for removed components
(`script-card` feedback rows, `approval-card`, `revise-box`, pending/discarded
variants) should be pruned where they no longer apply, keeping the classes that
`VideoPromptCard.jsx` actually uses (`script-card`, `script-meta`, `badge`,
`badge-soft`, `script-section`, `script-section-label`, `script-section-text`,
`prompt-block`, `feedback-row`, `feedback-btn`, `feedback-btn.primary`,
`feedback-status`).

## Color system (CSS variables)

```
--bg:      #000000   /* true black app background */
--panel:   #111111   /* assistant bubble / cards */
--panel-2: #18181b   /* insets, chips, prompt block */
--border:  #232323   /* hairline borders */
--text:    #ffffff
--muted:   #8a8a8a
--cyan:    #25F4EE    /* TikTok signature */
--red:     #FE2C55    /* TikTok signature */
--grad:    linear-gradient(90deg, #25F4EE, #FE2C55)
```

## Component styling

- **Header:** gradient (`--grad`) "KREA" wordmark; muted tagline; step chips kept
  but restyled as subtle dark pills with thin borders.
- **User bubble:** solid TikTok red (`--red`), white text, existing asymmetric
  radius.
- **Assistant bubble:** `--panel` with a `--border` hairline; markdown links and
  headings accented in cyan; `strong` stays white.
- **Video-prompt card:** black card; cyan (`--cyan`) section labels; prompt block
  on `--panel-2` inset; gradient "Salin prompt" button retaining the existing
  `✓ Tersalin` copied state.
- **Composer:** dark input (`--panel`) with a cyan focus ring; gradient send
  button; disabled state at reduced opacity.

## Polish details

- Consistent spacing rhythm and radii.
- Smooth focus/hover transitions on interactive elements.
- Slim custom dark scrollbar for the chat area.
- Subtle pulsing animation on the "KREA sedang mengetik…" typing indicator.
- Reduce emoji for a cleaner, more professional feel: keep 🎬 on the video-prompt
  card; drop the noisier 💡/📋 in favor of styled text labels.

## Out of scope

- Step-tracker, welcome hero, example chips.
- Any backend, API, or behavioral change.
- Layout/structure changes to the component tree.

## Success criteria

- App renders in true-black Noir theme with cyan/red accents across all states
  (empty, streaming, with messages, with a video-prompt card).
- No console errors; existing chat + copy flow works exactly as before.
- No references to deleted CSS classes that break current components.
