# KPI dictionary

Each metric has one definition, used in the SQL, the dashboards and the strategy document. The SQL is in `sql/`, the dashboard code in `dashboards/*/metrics.js`, and the tests in `tests/` check that they agree.

**Owners:**
- **Lead:** Product, Systems & Analytics Lead.
- **Sys:** process/systems designer.
- **Eng:** engineer.
- **Sales:** the person running the lead pipeline.
- **Adv:** academic advisor.

## GTM: revenue

| Metric | Formula | Source | Refresh | Owner |
|---|---|---|---|---|
| Booked revenue | Programme invoices issued in the period + workshop seats paid in the period | Invoices (ClickUp/Razorpay), Razorpay | Real time (webhook) | Lead |
| Revenue target | Each month's target × (days of that month inside the period ÷ days in the month) | `monthly_targets`, set by the founder | Monthly | Founder |
| % of target | Booked revenue ÷ target | – | – | Lead |
| Cash collected | Razorpay payments received in the period | Razorpay | Real time | Lead |
| Trial vs full programme | Booked revenue split by product. Renewals (trial → full) are shown separately. | Enrollments | Real time | Lead |
| New students onboarded | Students whose **first** enrollment starts in the period. Renewals are not counted again. | Enrollments | Real time | Sys |
| Workshop revenue | Workshop seats paid in the period × ₹3,999 | Razorpay (`notes.kind = workshop`) | Real time | Sys |
| Unpaid invoices | Invoices issued on or before the as-of date with no payment by that date. "Late" = past due date. | Invoices + payments | Real time | Sales |
| Renewals due | 3-month trials ending in the next 30 days that have no renewal yet | Enrollments | Daily | Sales |

## GTM: funnel (cohort view)

The funnel follows **leads created in the period** to wherever they are today, so the stages always add up. Recent periods look weaker until their leads finish the journey; the dashboard warns when this applies.

| Metric | Formula | Source |
|---|---|---|
| Total leads | Unique leads created in the period. Uniqueness is by phone-number hash, so the same parent from two ads counts once. | ClickUp |
| Qualified leads | Leads that passed qualification | ClickUp status |
| Discovery call show-up rate | Showed up ÷ calls whose date has passed | ClickUp + Smallest.ai call outcome |
| Drop-off after discovery | 1 − (ambition interviews ÷ showed up) | ClickUp |
| Architect sessions | Leads that reached the parent + teen roadmap session | ClickUp |
| Programme conversion | Paid ÷ total leads in the cohort. Also shown as paid ÷ qualified. | ClickUp + Razorpay |
| Cost per qualified lead (CPQL) | Programme ad spend in the period ÷ Meta leads created in the period that qualified | Meta Ads + ClickUp |
| Organic lead count | Leads with source organic or referral | ClickUp |
| Average lead journey | Average days from lead created to paid or dropped, for qualified leads that have finished | ClickUp |

## GTM: campaigns

| Metric | Formula |
|---|---|
| CTR | Link clicks ÷ impressions |
| CTR change | This period's CTR vs the previous period of the same length |
| Frequency | Meta's 7-day frequency on the last day of the period. Above 3 means the audience is tired of the ad. |
| Landing page bounce | Visitors who left without scrolling or submitting ÷ landing page views |
| Landing page load time | Median load time, weighted by visits |
| Workshop return (ROAS) | Seat revenue from the ad ÷ ad spend |

### Campaign decisions

Rules run in this order. The first match wins.

| Order | Decision | Rule |
|---|---|---|
| 1 | **Watch** | Under ₹5,000 spent. Too early to judge. |
| 2 | **Pause** | Programme: CPQL over 2× target (₹5,000), or no qualified leads. Workshop: return under 1.5×. |
| 3 | **Fix landing page** | Bounce over 55%, or load time over 3 seconds. Fix the page before blaming the ad. |
| 4 | **Refresh creative** | Frequency 3 or more, or CTR down 20%+ vs the previous period. |
| 5 | **Scale budget** | Programme: CPQL at or under ₹2,500. Workshop: return 3× or more. |
| 6 | **Keep running** | None of the above. |

Thresholds are starting points. Review them after the first month of real data.

## Student progress

| Metric | Formula | Source | Owner |
|---|---|---|---|
| Chapter stage | The highest step completed, in order: 1 read → 2 notes → 3 practice ≥70% → 4 timed past paper → 5 past paper ≥80%. A practice score under 70% keeps the chapter at stage 2. | App: chapter progress | Adv |
| Chapter readiness score | Stage points: 0, 10, 25, 50, 70, 100 | App | Adv |
| Syllabus covered with rigour | Chapters at stage 3+ ÷ all chapters in the syllabus | App | Adv |
| Expected pace | 25% of the syllabus per quarter from 1 April (days since 1 Apr ÷ 365) | Rule | Lead |
| Pace status | On track: within 10 points of expected. At risk: 10–20 points behind. Behind: more than 20 points behind. | – | Adv |
| Rigour adherence | Chapters at stage 3+ ÷ chapters started. Shows students who "finish" chapters by reading only. | App | Adv |
| Exam vs target | Latest exam score − target for that exam type. 10+ points under target means escalate to a subject tutor, because advisors are not subject experts. | App: exams | Adv |
| Task completion rate | Tasks due in the period and completed ÷ tasks due | App: tasks | Adv |
| Deadline adherence | Completed on or before the due date ÷ completed | App: tasks | Adv |
| Time estimate accuracy | 100 − average % gap between planned and actual minutes | App: tasks + focus timer | Adv |
| Focus minutes per week | Focus minutes in the period ÷ days × 7 | App: focus sessions | Lead |
| Quiz participation / score | Days attempted ÷ days in the period; average % score | App: quiz | Sys |
| Sleep, recovery, active minutes | Daily averages, only for students with consent and a connected device | WHOOP / Apple / Samsung / Garmin | Adv |

## Programme activities

Every activity type is measured in the same three ways.

| Dimension | Metric | Formula |
|---|---|---|
| **Quantity:** did Alcovia run it? | Held vs planned | Activities held ÷ planned in the period |
| | Attendance | Attended ÷ invited |
| | Reach | Unique students who attended |
| **Quality:** did Alcovians value it? | Average rating | 1–5, from a one-question form after the activity |
| | Rated 4+ | Share of ratings at 4 or 5 |
| **Student performance:** did it change anything? | Outcome score | 0–100, from the facilitator's rubric (see below) |
| | Follow-up done | Share of attendees who completed the agreed next action |

Outcome rubric and follow-up for each activity:

| Activity | Outcome score measures | Follow-up action |
|---|---|---|
| Career workshop | Average of the soft skills tracked (teamwork, adaptability, public speaking…) | Student writes a one-paragraph career reflection |
| Pod session | Participation and peer feedback | Each student commits to one action and reports back next pod |
| Peer session | Skill taught or learned (both sides rate) | Learner applies it in one task |
| Mentor call | Quality of questions prepared | One next step agreed with the mentor, done within 2 weeks |
| Personal branding | Content published on time; engagement on the post | LinkedIn post published by the student |
| Podcast | Preparation and hosting quality | Episode published |
| Competition prep | Mock score improvement | Registered and competed |
| Parent-child workshop | Parent and teen both rate | One shared goal written down |
| Out-of-city experience | Engagement and reflection | Reflection shared in the pod |
| Quarterly themes (social work, entrepreneurship) | Milestones hit against the quarter plan | Final showcase delivered |

**Collection with minimal manual work:**
- The facilitator ticks attendance in a ClickUp form. That form also sends the one-question rating link.
- n8n writes both into `activity_participation`.
- Follow-ups are created as tasks in the student's app, so completion is recorded when the student ticks them off.
