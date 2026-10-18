# How every feature, dashboard and automation gets delivered

One process for anything the team builds: an app feature, a dashboard, an n8n automation, or a data upload. It has **6 stages and 3 gates**. A piece of work only moves forward when its gate is passed.

```
1 Frame  ->  2 Shape  ->  [Gate A]  ->  3 Build  ->  4 Test  ->  [Gate B]  ->  5 Launch  ->  6 Measure  ->  [Gate C]
```

## Who does what

**Roles:**
- **Lead:** you.
- **Eng:** the full-stack engineer.
- **Sys:** the process/systems designer.

**Letters:**
- **A** = accountable (one person, makes the call).
- **R** = does the work.
- **C** = consulted.

| Stage | Lead | Eng | Sys |
|---|---|---|---|
| 1 Frame | A, R | C | R |
| 2 Shape | A | R (tech design) | R (process, business rules) |
| 3 Build | C | A, R | R (ClickUp/n8n config) |
| 4 Test | A | R (technical tests) | R (user testing with students/advisors) |
| 5 Launch | A | R (release) | R (training, comms) |
| 6 Measure | A, R | C | R (feedback collection) |

## Stage 1: Frame (1–2 days)

**Goal:** agree on the problem and how success will be measured, before anyone builds.

**Output:** a one-page brief (the first section of the PRD template) answering:
1. Who has the problem, and what is the evidence? Separate facts from guesses.
2. What one number will tell us this worked? What is it today? What target and by when?
3. What could go wrong for the user (the guardrail metric)?
4. What is the smallest version that tests the idea?

**Done when:** the brief fits on one page, and the success number can actually be measured today. If it can't, measuring it becomes the first task.

## Stage 2: Shape (2–4 days)

**Goal:** decide exactly what gets built.

**Output:** a PRD (see `prds/PRD-01-focus-to-realm.md`) containing:
- Scope and what is out of scope.
- Acceptance criteria written as checks someone else can run.
- Events or data needed.
- The technical approach and the process changes.

**Gate A, approve to build.** The Lead says yes only if all of these are true:
- There is one success metric, with a baseline and a target.
- Acceptance criteria can be tested by someone who didn't write them.
- The data needed exists, or there is a task to create it.
- Effort is no more than 2 weeks. Bigger work is split into releases.
- The owner of each task is named.

## Stage 3: Build (1–2 weeks, timeboxed)

- Work is tracked as ClickUp tasks under the PRD. Each task has a single owner and a due date.
- **Scope rule:** new ideas during the build go to a "next version" list. They are not added to the current build. The Lead is the only person who can change scope.
- **For automations:**
  - Every n8n workflow has retries and an error alert.
  - Every write uses a unique key so a retry never creates duplicates.

## Stage 4: Test (2–3 days)

| Check | Who | What |
|---|---|---|
| Acceptance criteria | Eng | Every check in the PRD passes. |
| Data check | Lead | Numbers on screen match a manual SQL count for one sample period. |
| Failure check | Eng | Force the bad case: duplicate webhook, empty data, API down. Nothing breaks or double counts. |
| User test | Sys | 3–5 real students, parents or advisors use it without help. Note where they get stuck. |
| Load on people | Sys | Count the new manual steps the change adds for advisors or students. The target is zero. |

**Gate B, approve to launch:**
- All acceptance criteria pass.
- No open bugs that block a user from finishing the main task.
- Users in testing finished the main task without help.
- A rollback plan is written down.

## Stage 5: Launch (1 day)

**Release checklist:**
- [ ] Event tracking verified live on a test account.
- [ ] Error alerts reach a person (the ClickUp task or the email works).
- [ ] Advisors briefed in a 15-minute walkthrough. The one-page guide is pinned in ClickUp.
- [ ] Students and parents told what changed and why, in one message.
- [ ] Baseline numbers saved in the PRD.
- [ ] Review date booked in the calendar, 2 or 4 weeks out.

## Stage 6: Measure (2–4 weeks after launch)

**Post-launch review** (30 minutes, written up in the PRD):
1. The metric: target vs actual.
2. The guardrail: did anything get worse?
3. What users said.
4. The decision.

**Gate C, the decision:**
- **Keep:** it hit target. Add it to the standard process.
- **Improve:** some movement. One more round, maximum.
- **Remove:** no movement. Switch it off, and write down what was learned.

A feature that is never reviewed is treated as failed. This rule is what fixes "we built it but don't know if it works."

## Weekly rhythm

| When | Meeting | Length | Purpose |
|---|---|---|---|
| Monday | Plan | 30 min | Pick this week's tasks from the ranked list. Confirm owners. |
| Daily | Check-in (written in ClickUp) | 5 min | Done yesterday, doing today, anything blocked. |
| Thursday | Demo | 30 min | Show working software or config, not slides. |
| Friday | Metrics and risks | 30 min | Review live metrics for launched work. Update the risk list. |
| Monthly | Founder review | 45 min | Results against OKRs. Re-rank the backlog. |

## How work is ranked

Score each idea from 1 to 3 on four questions. Work on the highest totals first.

| Question | 1 | 3 |
|---|---|---|
| **Impact:** how much it moves revenue or student outcomes | small | large |
| **Confidence:** how sure we are, from data or user evidence | guess | proven |
| **Ease:** effort and dependencies | over 2 weeks, many dependencies | under 3 days |
| **Speed:** how fast it shows value | over a month | under a week |

A tie goes to the item that unblocks other work. Data and tracking usually come first for this reason.

## Common failures and the rule that stops each one

| Failure | Rule |
|---|---|
| Vague request | No build without the one-page brief (Stage 1). |
| Nobody owns it | One owner per task, named before Gate A. |
| Scope creep | New ideas go to the "next version" list. Only the Lead changes scope. |
| Wrong numbers | Data check against SQL before launch (Stage 4). |
| Automation breaks silently | Retries, unique keys, and an error alert to a named person. |
| Built but nobody uses it | User test before launch. Training at launch. |
| Never know if it worked | Review date booked at launch. No review counts as fail (Stage 6). |
