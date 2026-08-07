# Example: the engineer brief

Target Claude-native rendering for the **software_engineer** pilot. The validated payload it renders
from is `../../../evals/expected-v2/01-engineer-brief.json`. Six tools connected (GitHub, Google,
Slack, Linear, Sentry active; PagerDuty not connected). Notice: Top of mind is in `rank` order (code
before chat before tracking), every claim carries a Source line with the tool + scope, and the
coverage line is honest about PagerDuty.

---

# Your day ahead

Morning, Koushik. Here's your game plan for Friday, August 7.

## 🧠 Top of mind

- **[15 min] Review PR #514 — rate-limit middleware** — requested **your** review 14h ago; 2 approvals still needed.
  Source: GitHub · acme/api · [Open PR]
- **[20 min] CI failing on your branch feat/checkout-v2** — the e2e job failed on the latest push.
  Source: GitHub · acme/api · [Open the failing run]
- **[5 min] Reply to Dana's handoff question in #growth** — she's blocked on the API contract for the checkout flow.
  Source: Slack · #growth
  Say: *"Draft a reply to Dana in #growth confirming the /checkout response shape."*
- **[30 min] GRW-231 "Instrument checkout funnel" is due today** — assigned to you, in progress, due EOD.
  Source: Linear · GRW · [Open issue]

## 🔔 FYI

### Alerts

- **Checkout error rate up 3× (last 2h)** — spike in `TypeError` on /checkout since the 06:10 deploy.
  Source: Sentry · acme-web · [Open issue]

### Deploys

- **PR #509 merged and deployed to staging** — your feature-flag change is live on staging.
  Source: GitHub · acme/api

## 🗓 On your calendar

- **9:30 AM — Growth standup** · 15 min
  Source: Calendar · Google Workspace · [Open event]
- **2:00 PM — Sprint planning** · 60 min
  Carry over GRW-231 if the funnel work isn't done.
  Source: Calendar · Google Workspace · [Open event]

Checked GitHub, Slack, Linear, Sentry and Google Calendar successfully. PagerDuty isn't connected, so on-call/incident status isn't included. Routine bot/notification noise was filtered out.

---

Ask me things like *"why is the CI failure top of mind?"*, *"show me PR #514,"* *"draft the reply to
Dana but show me first,"* or *"what did you leave out?"*
