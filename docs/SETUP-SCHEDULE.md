# Setup — schedule a brief in Cowork

> Scheduled tasks run remotely (even when your computer is asleep) and have access to the same
> capabilities as regular Cowork tasks, including connected tools, Skills, and installed plugins.
> **Each scheduled run appears as its own Cowork session** — Cowork does not append to a fixed
> existing conversation. Unattended runs are **read-only**. (Sources S7, S9; access date 2026-08-07.)

> **Personal vs role/team brief.** The steps below are written for the personal daily brief
> (`prompts/scheduled-daily-brief.md`, `boo-preferences.json`, Gmail/Calendar/Drive). For the
> **role/team brief**, substitute `prompts/scheduled-team-brief.md` and `role-profile.json`, and
> enable **your role's** connectors on the task (e.g. Engineer → GitHub, Slack, Linear, Calendar;
> ⚡ Superhuman → whatever you connected). Everything else — own session per run, read-only unattended,
> the enable-connectors-on-the-task gotcha — is identical.

## Steps (current UI)

1. **Prerequisites**
   - A paid Claude plan with Cowork available.
   - Code execution enabled (needed for the Skill's validation script and file preferences).
   - The Boo plugin installed **or** the `daily-brief` Skill uploaded (see `docs/SETUP-CLAUDE.md`).
   - Your Google connectors enabled (Mode A) and/or the Boo connector added as a remote MCP
     connector (Mode B).
   - `boo-preferences.json` saved to your Claude account / Drive.

2. **Create the scheduled task**
   - Open Cowork → scheduled tasks → **New scheduled task**.
   - Paste the prompt from `prompts/scheduled-daily-brief.md` **verbatim**.
   - Set frequency to **daily** (weekday-only if you prefer) at your local brief time.
     - Note: an explicit timezone control in the scheduler is not documented (capability item T2).
       The Skill computes your local day from the IANA timezone in `boo-preferences.json` regardless,
       so the brief's "today" is correct even if the scheduler's clock differs. Verify the first run's
       date lines up and adjust the task time if needed.
   - **Approval mode:** choose the most conservative option. The prompt is already read-only, so no
     mutation should occur unattended; keep it that way.

3. **Run on demand** to test: trigger the task manually once and review the resulting session.

4. **Pause / resume**: use the task's controls in the scheduled-tasks list.

5. **Find past results**: each run is its own Cowork session in your task history.

## Manual dry-run checklist (do this before trusting the schedule)

- [ ] Manual brief renders with the correct local date and greeting.
- [ ] Every item shows a source line; amounts/deadlines are bold; efforts appear.
- [ ] Coverage line names which accounts/sources were checked and any unavailable.
- [ ] Disconnect one account → next brief shows partial coverage and still produces the rest.
- [ ] Ask "why is X top of mind?" → cited answer.
- [ ] Ask "show me the original message" → opens the source.
- [ ] "Draft a reply, show me first" → preview appears; on approval a **draft** is created (check
      Gmail Drafts) and nothing is sent.
- [ ] Trigger the scheduled task once → it produces the brief and makes **no** changes.
- [ ] (Multi-account) Removing one account leaves the others working.
- [ ] Record any failures as new scenarios in `evals/cases/scenarios.json` (+ a golden payload).

## Keeping brief time in sync

Two places hold "the time":
- the **Cowork task** run time (authoritative for *when it runs*), and
- `brief_time` in `boo-preferences.json` (used by Boo when it talks about your schedule).
Update both when you move the brief (e.g. "move the brief to 7:30 AM").

## ⚠️ Enable connectors ON THE TASK (biggest gotcha — from the live dry run)

A scheduled Cowork task does **not** inherit the connectors you toggled on in an interactive chat.
If you skip this, the run sees only some connectors (e.g. Drive) and reports Gmail/Calendar as
"no connector tools exposed this run" — the brief then correctly degrades to partial coverage but
has nothing to work with.

**Fix:** in the scheduled task's settings, find its **tools / connectors** selector and enable the
connectors your brief needs — **Gmail + Calendar (+ Drive)** for the personal brief, or **your role's
tools** for the team brief (e.g. GitHub, Slack, Linear, Calendar). If there's no per-task selector,
ensure they're enabled at the **Cowork / account** connector level. Connectors not in your
role/preferences are simply ignored.

Also: **hard-code your IANA timezone** in the prompt (replace any `<YOUR TIMEZONE>` placeholder). The
model will otherwise guess the zone, and a wrong guess shifts every day-boundary.

See the internal dry-run notes for the full set of live findings (O1–O5).
