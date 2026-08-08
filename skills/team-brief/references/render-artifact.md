# Rendering the brief — native Artifact card (primary)

The brief is delivered as a **self-contained HTML Artifact card**, not flat markdown and not an inline
widget. This is the lesson from live runs: a skill's markdown renders "flat/pasted," and the inline
visualize widget is fragile (icon webfont → empty boxes; dropped text). Artifacts are the one rich
renderer a plugin can reliably produce.

## How to render
1. Build + validate the payload (step 5).
2. Fill `assets/brief-card.template.html` from the **validated payload** — presentation is a *pure
   function* of the payload; never add a claim that isn't in it.
3. Emit it as an **Artifact** (an HTML document the user views as a card).
4. In the **chat message under the card**, add a one-line **action nudge** offering the top 1–2 actions
   (e.g. *"Want me to draft the reply to Dana, or open PR #514?"*).

## The card contract (must hold)
- **Self-contained.** No external fonts, CSS, JS, or images. **No icon webfont** (use emoji / inline
  SVG). System font stack. Theme-aware via CSS variables (light + dark).
- **Structure:** header (`Your day ahead` + local date + run tag) → greeting → **🧠 Top of mind** (in
  `rank` order) → **🔔 FYI** (role subgroups, omit empty) → **🗓 On your calendar** (all-day first) →
  **coverage line**.
- **Every item is a card** with: effort pill (`[N min]` only when `effort_minutes` set), title, one
  detail line, a **source chip** = `{friendly source} · {account} · {workspace?}`, and:
  - for an `open_source` action → a real **deep-link** (`<a href>` from `citation.link`; the retrieval
    permalink invariant guarantees one exists);
  - for a `say_command` action → an **action chip** (accent) labelled with the action; on a static card
    it can't post to chat, so it maps to the chat follow-up nudge. **Never render a dead button.**
- **Severity in form:** items with `urgency:"today"` get a "today" stripe/pill; alert-type FYI items a
  danger stripe. Semantic color is separate from the brand accent.
- **Conflicts:** render once with a plain caveat line.
- **Coverage line:** what was checked; blocking gaps for missing-mandatory, "reconnect" for degraded.

## Fallback (CLI / no-artifact surfaces only)
Use the Markdown skeleton in `output-style.md` — still every-item-cited, still real deep-links, still
ending in an action nudge. Never silently prefer markdown on a surface that supports Artifacts.

## Reference render
A published example of the exact card: `evals/expected-v2/01-engineer-brief.json` rendered per this
contract (see `assets/brief-card.template.html`).
