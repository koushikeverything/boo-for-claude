# Output style — role brief presentation contract

> **Primary rendering is the Artifact card** — see `references/render-artifact.md` and
> `assets/brief-card.template.html`. The Markdown below is the **fallback** for surfaces that can't
> render an Artifact (e.g. Claude Code CLI). Never prefer this markdown on a surface that supports
> Artifacts. Either way, every item stays cited, deep-linked, and the output ends in an action nudge.

Same skeleton for every role; role-specific content. Presentation is a pure function of the validated
payload.

## Structure

```markdown
# Your day ahead

Morning, {preferred_name}. Here's your game plan for {local day}.

## 🧠 Top of mind

- **[{effort} min] {title}** — {detail}.
  {source line}
  {optional: Say: "…"}

## 🔔 FYI

### {Subgroup}

- **{title}** — {detail}.
  {source line}

## 🗓 On your calendar

- **{start} — {title}** · {duration} min
  {location / context}
  {source line}

{one-line coverage sentence}
```

## Rules

- **Top of mind** is rendered in `rank` order (already computed).
- **Bold** only key actions, amounts, deadlines, and titles. `[N min]` only when `effort_minutes` set.
- **Source line** is secondary but always present:
  `Source: {Provider} · {workspace} · [{Open PR|Open run|Open issue|Open message|Open event}]`
  Provider is the friendly label (GitHub, Slack, Linear, Sentry, Google Calendar). `workspace` is the
  repo/channel/project when useful. Rely on Claude's native citation UI for links where it renders them.
- **`[Open …]` must be a real deep-link.** Render the `[Open PR|Open issue|Open message|Open event]`
  from the item's `citation.link`. If an item has an `open_source` action, a `link` is guaranteed
  (retrieval invariant). When a source has no URL, use a **Say line** instead (which prompts the
  connector in chat) — never print an "Open …" that leads nowhere.
- **Say lines** appear only when a real `say_command` action exists. No bare chips.
- **FYI subgroups** are role-flavored (engineer: Alerts, Deploys, Reviews, Updates). Omit empty ones.
- **Calendar:** all-day first, then chronological; location/attendees only when relevant; context must
  be evidence-backed (never invented).
- **Conflicts:** render the item once with a plain caveat, e.g. "⚠️ Linear marks this done but the
  GitHub PR is still open — please confirm."
- **Coverage line** (from the gating report + `source_status`), e.g.:
  "Checked GitHub, Slack, Linear, Sentry and Google Calendar. PagerDuty isn't connected (on-call not
  included)." Flag **missing mandatory** slots as a blocking gap and **degraded** ones as "reconnect".

## Do NOT reproduce

Tool chrome — Slack/Gmail headers, GitHub UI, sender lines, email footers, or fake buttons. Every
action is a real supported operation or a clearly-worded follow-up command.

## Verbosity

Respect the profile's `verbosity`. Default: short, one supporting line per item. Higher verbosity may
add one extra context line per calendar event, never more citations.
