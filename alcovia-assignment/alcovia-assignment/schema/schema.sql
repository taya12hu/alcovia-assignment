-- =====================================================================
-- Alcovia analytics schema (prototype)
-- One database that both dashboards read from.
-- Written in portable SQL: runs on SQLite as-is; on Postgres change
-- TEXT dates to DATE/TIMESTAMPTZ and INTEGER PRIMARY KEY to SERIAL.
--
-- Source-of-truth rule (see docs/architecture.md):
--   * Leads & funnel stages ......... ClickUp  (synced by n8n)
--   * Payments ...................... Razorpay (webhook via n8n)
--   * Ad spend / clicks / frequency . Meta Ads (daily pull via n8n)
--   * Student learning activity ..... Alcovia app database
--   * Programme activities & ratings  Google Form / ClickUp form (via n8n)
-- This database is a read copy for reporting. Nobody edits it by hand.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- GTM: marketing
-- ---------------------------------------------------------------------
CREATE TABLE landing_pages (
    landing_page_id TEXT PRIMARY KEY,          -- e.g. 'lp_program_v2'
    name            TEXT NOT NULL,
    url_path        TEXT NOT NULL
);

CREATE TABLE campaigns (
    campaign_id     TEXT PRIMARY KEY,          -- Meta campaign id
    name            TEXT NOT NULL,
    objective       TEXT NOT NULL CHECK (objective IN ('program','workshop')),
    landing_page_id TEXT REFERENCES landing_pages(landing_page_id),
    started_on      TEXT NOT NULL
);

CREATE TABLE ad_creatives (
    creative_id     TEXT PRIMARY KEY,          -- Meta ad id
    campaign_id     TEXT NOT NULL REFERENCES campaigns(campaign_id),
    name            TEXT NOT NULL,
    format          TEXT NOT NULL CHECK (format IN ('reel','static','carousel'))
);

-- One row per creative per day, as reported by Meta Insights API.
CREATE TABLE ad_daily (
    stat_date          TEXT NOT NULL,
    creative_id        TEXT NOT NULL REFERENCES ad_creatives(creative_id),
    spend              REAL NOT NULL,          -- INR
    impressions        INTEGER NOT NULL,
    clicks             INTEGER NOT NULL,       -- link clicks
    frequency_7d       REAL NOT NULL,          -- Meta's rolling 7-day frequency for the ad set
    lp_views           INTEGER NOT NULL,       -- landing page views (pixel)
    lp_bounces         INTEGER NOT NULL,       -- left without scrolling / submitting
    lp_load_ms         INTEGER NOT NULL,       -- median page load time that day
    PRIMARY KEY (stat_date, creative_id)       -- re-running the sync can never double count
);

-- ---------------------------------------------------------------------
-- GTM: leads and funnel (mirrors the ClickUp lead list)
-- One row per lead. Each stage stores the date it was reached.
-- NULL = not reached (yet).
-- ---------------------------------------------------------------------
CREATE TABLE leads (
    lead_id                TEXT PRIMARY KEY,   -- ClickUp task id
    phone_hash             TEXT NOT NULL UNIQUE, -- dedupe key: same parent never counted twice
    created_on             TEXT NOT NULL,
    source                 TEXT NOT NULL CHECK (source IN ('meta','organic','referral')),
    campaign_id            TEXT REFERENCES campaigns(campaign_id),
    creative_id            TEXT REFERENCES ad_creatives(creative_id),
    qualified_on           TEXT,
    discovery_booked_on    TEXT,
    discovery_showed       INTEGER CHECK (discovery_showed IN (0,1)), -- NULL until call date passes
    ambition_interview_on  TEXT,
    architect_session_on   TEXT,
    outcome                TEXT NOT NULL DEFAULT 'open'
                           CHECK (outcome IN ('open','converted','dropped')),
    outcome_on             TEXT,
    drop_reason            TEXT
);

-- ---------------------------------------------------------------------
-- GTM: customers, money
-- ---------------------------------------------------------------------
CREATE TABLE students (
    student_id   TEXT PRIMARY KEY,
    lead_id      TEXT UNIQUE REFERENCES leads(lead_id), -- links funnel -> student
    display_name TEXT NOT NULL,                         -- synthetic names only
    grade        INTEGER NOT NULL,
    joined_on    TEXT NOT NULL
);

CREATE TABLE enrollments (
    enrollment_id  TEXT PRIMARY KEY,
    student_id     TEXT NOT NULL REFERENCES students(student_id),
    product        TEXT NOT NULL CHECK (product IN ('trial_3m','full_program')),
    start_on       TEXT NOT NULL,
    end_on         TEXT NOT NULL,
    price          REAL NOT NULL,
    renewal_of     TEXT REFERENCES enrollments(enrollment_id)
);

-- Booked revenue lives here (an invoice is raised when a family signs up).
CREATE TABLE invoices (
    invoice_id     TEXT PRIMARY KEY,
    enrollment_id  TEXT NOT NULL REFERENCES enrollments(enrollment_id),
    issued_on      TEXT NOT NULL,
    due_on         TEXT NOT NULL,
    amount         REAL NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('paid','unpaid','cancelled'))
);

CREATE TABLE workshops (
    workshop_id    TEXT PRIMARY KEY,
    held_on        TEXT NOT NULL,              -- fortnightly
    title          TEXT NOT NULL,
    seat_price     REAL NOT NULL DEFAULT 3999,
    capacity       INTEGER NOT NULL
);

-- Cash collected lives here. One row per Razorpay payment.
CREATE TABLE payments (
    razorpay_payment_id TEXT PRIMARY KEY,      -- idempotency key for the webhook
    paid_on             TEXT NOT NULL,
    amount              REAL NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('program','workshop')),
    invoice_id          TEXT REFERENCES invoices(invoice_id),
    workshop_id         TEXT REFERENCES workshops(workshop_id),
    lead_id             TEXT REFERENCES leads(lead_id),
    utm_creative_id     TEXT REFERENCES ad_creatives(creative_id), -- which ad sold the workshop seat
    CHECK ( (kind = 'program'  AND invoice_id  IS NOT NULL)
         OR (kind = 'workshop' AND workshop_id IS NOT NULL) )
);

CREATE TABLE monthly_targets (
    month               TEXT PRIMARY KEY,      -- 'YYYY-MM'
    revenue_target      REAL NOT NULL,         -- booked revenue target, INR
    enrollment_target   INTEGER NOT NULL
);

-- ---------------------------------------------------------------------
-- STUDENT PROGRESS
-- ---------------------------------------------------------------------
CREATE TABLE subjects (
    subject_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL
);

CREATE TABLE chapters (
    chapter_id  TEXT PRIMARY KEY,
    subject_id  TEXT NOT NULL REFERENCES subjects(subject_id),
    seq         INTEGER NOT NULL,
    name        TEXT NOT NULL
);

-- The 5-step rigour. Each step stores when it happened (+ accuracy where relevant).
CREATE TABLE chapter_progress (
    student_id          TEXT NOT NULL REFERENCES students(student_id),
    chapter_id          TEXT NOT NULL REFERENCES chapters(chapter_id),
    read_on             TEXT,
    notes_on            TEXT,
    practice_on         TEXT,
    practice_accuracy   REAL,                  -- 0-100
    past_paper_on       TEXT,
    past_paper_accuracy REAL,                  -- 0-100, timed attempt
    PRIMARY KEY (student_id, chapter_id)
);

CREATE TABLE score_targets (
    student_id  TEXT NOT NULL REFERENCES students(student_id),
    subject_id  TEXT NOT NULL REFERENCES subjects(subject_id),
    exam_type   TEXT NOT NULL CHECK (exam_type IN ('formative','unit_test','half_yearly')),
    target_pct  REAL NOT NULL,
    PRIMARY KEY (student_id, subject_id, exam_type)
);

CREATE TABLE exam_results (
    student_id  TEXT NOT NULL REFERENCES students(student_id),
    subject_id  TEXT NOT NULL REFERENCES subjects(subject_id),
    exam_type   TEXT NOT NULL,
    exam_on     TEXT NOT NULL,
    score_pct   REAL NOT NULL,
    PRIMARY KEY (student_id, subject_id, exam_type, exam_on)
);

CREATE TABLE tasks (
    task_id        TEXT PRIMARY KEY,
    student_id     TEXT NOT NULL REFERENCES students(student_id),
    due_on         TEXT NOT NULL,
    completed_on   TEXT,                       -- NULL = not done
    estimated_min  INTEGER NOT NULL,
    actual_min     INTEGER,                    -- logged by focus timer when linked
    assigned_by    TEXT NOT NULL CHECK (assigned_by IN ('self','advisor'))
);

CREATE TABLE focus_sessions (
    session_id   TEXT PRIMARY KEY,
    student_id   TEXT NOT NULL REFERENCES students(student_id),
    started_on   TEXT NOT NULL,
    minutes      INTEGER NOT NULL,
    completed    INTEGER NOT NULL CHECK (completed IN (0,1))  -- 0 = abandoned early
);

CREATE TABLE quiz_attempts (
    student_id  TEXT NOT NULL REFERENCES students(student_id),
    quiz_on     TEXT NOT NULL,                 -- 8pm daily quiz
    score       INTEGER NOT NULL,
    out_of      INTEGER NOT NULL,
    PRIMARY KEY (student_id, quiz_on)
);

-- Only for students whose parents consented and who connected a device.
CREATE TABLE wearable_daily (
    student_id    TEXT NOT NULL REFERENCES students(student_id),
    day           TEXT NOT NULL,
    device        TEXT NOT NULL CHECK (device IN ('whoop','apple','samsung','garmin')),
    active_min    INTEGER,
    sleep_hours   REAL,
    recovery_pct  REAL,
    PRIMARY KEY (student_id, day)
);

-- ---------------------------------------------------------------------
-- PROGRAMME ACTIVITIES  (quantity / quality / performance)
-- ---------------------------------------------------------------------
CREATE TABLE activities (
    activity_id    TEXT PRIMARY KEY,
    activity_type  TEXT NOT NULL CHECK (activity_type IN (
                     'career_workshop','pod_session','peer_session','mentor_call',
                     'personal_branding','podcast','competition_prep',
                     'parent_child','out_of_city')),
    planned_on     TEXT NOT NULL,
    held_on        TEXT,                       -- NULL = planned but not conducted
    title          TEXT NOT NULL
);

CREATE TABLE activity_participation (
    activity_id        TEXT NOT NULL REFERENCES activities(activity_id),
    student_id         TEXT NOT NULL REFERENCES students(student_id),
    invited            INTEGER NOT NULL DEFAULT 1,
    attended           INTEGER NOT NULL CHECK (attended IN (0,1)),
    rating             INTEGER CHECK (rating BETWEEN 1 AND 5),       -- "How useful was this?"
    outcome_score      REAL CHECK (outcome_score BETWEEN 0 AND 100), -- rubric / skill score
    follow_up_done     INTEGER CHECK (follow_up_done IN (0,1)),      -- did the next action happen?
    PRIMARY KEY (activity_id, student_id)
);

CREATE TABLE roadmap_milestones (
    milestone_id  TEXT PRIMARY KEY,
    student_id    TEXT NOT NULL REFERENCES students(student_id),
    track         TEXT NOT NULL CHECK (track IN ('career','personal','academic')),
    due_on        TEXT NOT NULL,
    done_on       TEXT,
    title         TEXT NOT NULL
);

-- Indexes for the date-range filters the dashboards use
CREATE INDEX ix_leads_created   ON leads(created_on);
CREATE INDEX ix_payments_paid   ON payments(paid_on);
CREATE INDEX ix_invoices_issued ON invoices(issued_on);
CREATE INDEX ix_ad_daily_date   ON ad_daily(stat_date);
CREATE INDEX ix_focus_student   ON focus_sessions(student_id, started_on);
CREATE INDEX ix_tasks_student   ON tasks(student_id, due_on);
