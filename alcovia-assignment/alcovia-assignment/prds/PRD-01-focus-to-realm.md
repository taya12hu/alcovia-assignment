# PRD-01: Focus sessions power the Realm

| | |
|---|---|
| **Owner** | Product, Systems & Analytics Lead |
| **Build** | Full-stack engineer |
| **Research and rollout** | Process/systems designer |
| **Status** | Proposed (first experiment after joining) |
| **Decision date** | End of week 4 of the experiment |

## 1. Problem

Students open the app for Home and the Realm game, then leave. Average use is about 2 minutes a day against a 30-minute goal.

Facts from the brief:
- 20 students used the app in 45 days.
- 13 used the Realm, the most-used feature this week.
- The Focus Timer was opened by 11 students, but only 5 use it regularly.
- 10 students opened the Syllabus, but only 1 did this week.
- Nobody opened the Study Planner this week.

The game is the reason students come. The study tools give nothing back, so students try them once and stop.

## 2. Hypothesis

If a finished focus session, and logging a chapter step, give students the things they want in the Realm, then more students will run focus sessions every day. Those sessions keep the app open for 25–50 minutes of real study.

**Why this feature first:**
- It is the only feature where long app time is *good* time.
- The connection already exists in a small way: focus sessions already hatch dragon eggs.
- It needs no new screen, only stronger rewards and one prompt.

## 3. Is 30 minutes the right goal?

Not on its own. Thirty minutes of scrolling would hit the number and hurt the student. This PRD tracks **focus minutes** (time with other apps blocked, working on a task) as the main measure. Total app time is a result of that, not the goal.

## 4. What changes

1. **Realm energy from focus.** Every completed 25-minute focus session gives Realm energy. Territories can only be conquered with energy.
   - Partial sessions give nothing.
   - Energy is capped at 4 sessions a day, so nobody is pushed into unhealthy screen time.
2. **Chapter steps unlock dragons.** Logging a chapter step unlocks a dragon tied to that subject. Steps are: notes made, practice score entered, past paper done.
3. **Start from Home.** One Home card says "Your next focus block" and shows the next task due. One tap starts the timer on that task.
4. **8 pm nudge.** A push notification after the daily quiz: "One focus block before bed? Your Realm needs 1 more energy."
   - It is only sent if the student has done no session that day.

## 5. Out of scope
- New game features.
- Leaderboard changes.
- Wellness and WHOOP.
- Parent app.

## 6. Who it's for
All active students. With about 20 app users, there are too few for a fair A/B split. So this runs as a **before/after on the whole cohort**, with the 4 weeks before launch as the baseline, plus interviews with 8 students.

## 7. Metrics

| Type | Metric | Baseline | Target after 4 weeks |
|---|---|---|---|
| **Primary** | Students with 3+ completed focus sessions a week | 5 | 10 |
| Secondary | Median focus minutes per active student per week | measured in week 0 | 2× baseline |
| Secondary | Weekly active students (opened the app on 3+ days) | 11–17 | 15 |
| Secondary | Chapters moved to stage 3 (practice ≥70%) per week | measured in week 0 | +30% |
| Guardrail | Focus sessions abandoned before the end | measured in week 0 | no worse |
| Guardrail | Sessions after 10:30 pm | measured in week 0 | no increase |
| Guardrail | Students who say the app "feels like pressure" (weekly 1-question poll) | – | under 20% |

## 8. Event tracking needed (add before launch)

| Event | When it fires | Properties |
|---|---|---|
| `app_open` | app comes to foreground | `student_id`, `source` (push, direct) |
| `screen_view` | any screen shown | `screen`, `ms_on_previous_screen` |
| `focus_started` | timer starts | `task_id`, `planned_min`, `entry_point` (home card, timer tab, push) |
| `focus_completed` | timer reaches the end | `minutes`, `task_id` |
| `focus_abandoned` | timer stopped early | `minutes_done` |
| `chapter_step_logged` | student logs a rigour step | `chapter_id`, `step`, `accuracy` |
| `realm_energy_spent` | energy used in the Realm | `amount`, `territory_id` |
| `push_opened` | notification tapped | `campaign` (e.g. `8pm_focus_nudge`) |

Events go to the app's own database: one `app_events` table, the same store the student dashboard reads. No new tool is needed at this scale.

## 9. Acceptance criteria

- A completed 25-minute session adds exactly 1 energy. A session stopped at 24 minutes adds 0.
- The 5th session in a day adds 0 energy and shows "Daily energy full. Rest up."
- The Home card shows the earliest task due today. If there is none, it shows "Start a free focus block."
- The 8 pm push is not sent to a student who already completed a session that day.
- All 8 events appear in `app_events` with correct properties, checked on a test account before release.

## 10. Rollout and decision

| Week | What happens |
|---|---|
| Week 0 | Ship event tracking only. Measure the baseline. |
| Week 1 | Release to all students. The systems designer briefs advisors so they can explain it in weekly calls. |
| Weeks 1–4 | Watch the primary metric weekly. Interview 8 students in week 2. |
| End of week 4 | Decide, using the rules below. |

**Decision rules:**
- **Keep and build on it** if the primary metric reaches 10 and no guardrail worsens.
- **Change the rewards** if it reaches 7–9.
- **Roll back** if it stays under 7 or any guardrail worsens.

## 11. Risks

| Risk | What we do |
|---|---|
| Students leave the timer running without studying. | Ask "What did you finish?" at the end of each session. Advisors spot-check against chapter progress. |
| Rewards feel like a chore. | Interviews in week 2. Energy cap of 4. |
| Parents worry about game time. | Show parents focus minutes, not game time. |
