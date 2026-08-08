# Output style — Claude-native presentation contract

**Primary rendering is a self-contained Artifact card** (same contract as the team-brief skill:
`skills/team-brief/references/render-artifact.md` + `assets/brief-card.template.html`) — a card with an
effort pill, a source chip, a real deep-link per `open_source` action, and an accent action chip per
`say_command`, ending in a chat action nudge. The Markdown structure below is the **fallback** for
surfaces that can't render an Artifact (e.g. Claude Code CLI). Either way, presentation is a pure
function of the validated payload — every item cited, no fabrication.

## Structure

```markdown
# Your day ahead

Morning, {preferred_name}. Here's your game plan for {local day, e.g. "Friday, August 7"}.

## 🧠 Top of mind

- **[{effort} min] {title}** — {detail}.
  {source line}
  {optional: Say: "…"}

## 🔔 FYI

### {Subgroup, e.g. Financial}

- **{title}** {detail}.
  {source line}

## 🗓 On your calendar

- **{start} — {title}** · {duration} min
  {location}
  {evidence-backed context}
  {source line}

{one-line coverage sentence}
```

## Rules

- **Greeting** uses `preferred_name` and the human local date.
- **Effort** shows as `[N min]` only when `effort_minutes` is set.
- **Bold** is reserved for key actions, amounts, deadlines, and event titles. Do not bold whole lines.
- **Source line** is visually secondary but always present. Format:
  `Source: {Gmail|Calendar|Drive} · {account_label} · [{Open message|Open event|Open file}]`
  When several citations back one item, list the primary source and, if useful, the account only.
  If Claude's native citation UI renders links automatically, rely on it and keep the text minimal.
- **Say lines** show a real follow-up command only when there is a corresponding `say_command`
  action. Never show a bare "[Add to cal]" chip with no backing action.
- **Calendar:** all-day events first, then chronological. Show location/attendees only when present.
  Context must be evidence-backed; never invent goals.
- **Conflicts:** render the affected item once, and add a plain caveat line, e.g.
  "⚠️ Sources disagree on the date (Gmail says Sunday; Calendar says Saturday) — please confirm."
- **Coverage line** (short, at the very end), e.g.:
  "Checked Personal Gmail and Calendar successfully. Work Drive was unavailable (reconnect needed)."
- **Empty day:** if nothing is actionable, say so warmly and show whatever calendar/coverage exists;
  do not manufacture items. See `../examples/empty-day.md`.

## Do NOT reproduce

Gmail sender chrome, "to me" headers, CC/© branding, an agent mailbox, an email footer address,
email-safe table layouts, or fake action chips. There is no agent email address in this version.

## Verbosity

Respect the `verbosity` preference. Default: short, highly scannable entries; one supporting line
per item. Higher verbosity may add one extra context line per calendar event, never more citations.
