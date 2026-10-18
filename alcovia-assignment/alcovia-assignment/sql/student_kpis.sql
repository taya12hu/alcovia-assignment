-- =====================================================================
-- Student progress and programme KPIs. Runs on SQLite (tested).
-- Change the dates in each `params` block to pick a period.
--   python3 scripts/run_sql.py sql/student_kpis.sql
-- =====================================================================
.headers on
.mode column

-- ---------------------------------------------------------------------
-- Q1. Chapter stage per student, then syllabus coverage vs expected pace
--   stage 0 not started, 1 read, 2 notes, 3 practice >= 70%,
--   4 timed past paper done, 5 past paper >= 80% (exam ready)
--   coverage counts only chapters at stage 3+ (done with rigour)
--   expected = 25% of the syllabus per quarter from 1 April
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-10-17' AS as_of),
active AS (
  SELECT DISTINCT e.student_id FROM enrollments e, params
  WHERE e.start_on <= as_of AND e.end_on > as_of
),
st AS (
  SELECT a.student_id, c.chapter_id, c.subject_id,
    CASE
      WHEN p.read_on IS NULL OR p.read_on > as_of THEN 0
      WHEN p.notes_on IS NULL OR p.notes_on > as_of THEN 1
      WHEN p.practice_on IS NULL OR p.practice_on > as_of OR p.practice_accuracy < 70 THEN 2
      WHEN p.past_paper_on IS NULL OR p.past_paper_on > as_of THEN 3
      WHEN p.past_paper_accuracy >= 80 THEN 5 ELSE 4
    END AS stage
  FROM active a CROSS JOIN chapters c
  LEFT JOIN chapter_progress p ON p.student_id = a.student_id AND p.chapter_id = c.chapter_id, params
)
SELECT s.display_name,
       ROUND(100.0 * SUM(stage >= 3) / COUNT(*), 1)                    AS coverage_pct,
       ROUND(MIN(100, (julianday(as_of) - julianday('2026-04-01')) / 365 * 100), 1) AS expected_pct,
       ROUND(100.0 * SUM(stage >= 3) / COUNT(*)
             - MIN(100, (julianday(as_of) - julianday('2026-04-01')) / 365 * 100), 1) AS gap_pts,
       ROUND(AVG(CASE stage WHEN 0 THEN 0 WHEN 1 THEN 10 WHEN 2 THEN 25 WHEN 3 THEN 50 WHEN 4 THEN 70 ELSE 100 END), 1) AS readiness_score,
       ROUND(100.0 * SUM(stage >= 3) / NULLIF(SUM(stage >= 1), 0), 1)  AS rigour_adherence_pct,
       SUM(stage = 5)                                                   AS exam_ready_chapters
FROM st JOIN students s USING (student_id), params
GROUP BY st.student_id
ORDER BY gap_pts;

-- ---------------------------------------------------------------------
-- Q2. Daily habits per student for the period
--   task completion   = tasks due in period that are done / tasks due
--   deadline adherence= done on or before due date / done
--   estimate accuracy = 100 - average % error between planned and actual minutes
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-18' AS d0, '2026-10-17' AS d1),
active AS (SELECT DISTINCT student_id FROM enrollments, params WHERE start_on <= d1 AND end_on > d1),
t AS (
  SELECT student_id, COUNT(*) AS due,
         SUM(completed_on IS NOT NULL AND completed_on <= d1) AS done,
         SUM(completed_on IS NOT NULL AND completed_on <= d1 AND completed_on <= due_on) AS on_time,
         AVG(CASE WHEN completed_on <= d1 AND actual_min IS NOT NULL
                  THEN ABS(actual_min - estimated_min) * 1.0 / estimated_min END) AS est_err
  FROM tasks, params WHERE due_on BETWEEN d0 AND d1 GROUP BY student_id
),
f AS (SELECT student_id, SUM(minutes) AS focus_min, COUNT(*) AS sessions
      FROM focus_sessions, params WHERE started_on BETWEEN d0 AND d1 GROUP BY student_id),
q AS (SELECT student_id, COUNT(*) AS quizzes, AVG(100.0 * score / out_of) AS quiz_avg
      FROM quiz_attempts, params WHERE quiz_on BETWEEN d0 AND d1 GROUP BY student_id)
SELECT s.display_name,
       ROUND(100.0 * t.done / t.due, 1)              AS task_completion_pct,
       ROUND(100.0 * t.on_time / NULLIF(t.done,0), 1) AS deadline_adherence_pct,
       ROUND(MAX(0, 100 - 100 * t.est_err), 1)       AS estimate_accuracy_pct,
       COALESCE(f.focus_min, 0)                      AS focus_minutes,
       ROUND(COALESCE(f.focus_min, 0) * 7.0 / (julianday(d1) - julianday(d0) + 1)) AS focus_min_per_week,
       ROUND(100.0 * COALESCE(q.quizzes,0) / (julianday(d1) - julianday(d0) + 1), 1) AS quiz_participation_pct,
       ROUND(q.quiz_avg, 1)                          AS quiz_avg_pct
FROM active a JOIN students s USING (student_id)
LEFT JOIN t USING (student_id) LEFT JOIN f USING (student_id) LEFT JOIN q USING (student_id), params
ORDER BY task_completion_pct;

-- ---------------------------------------------------------------------
-- Q3. Programme KPIs by activity: quantity, quality, student performance
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-04-01' AS d0, '2026-10-17' AS d1),
planned AS (SELECT * FROM activities, params WHERE planned_on BETWEEN d0 AND d1)
SELECT a.activity_type,
       COUNT(DISTINCT a.activity_id)                                          AS planned,
       COUNT(DISTINCT CASE WHEN a.held_on IS NOT NULL THEN a.activity_id END) AS held,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN a.held_on IS NOT NULL THEN a.activity_id END)
             / COUNT(DISTINCT a.activity_id), 1)                              AS held_pct,          -- QUANTITY
       ROUND(100.0 * SUM(p.attended) / NULLIF(COUNT(p.student_id),0), 1)     AS attendance_pct,    -- QUANTITY
       ROUND(AVG(CASE WHEN p.attended = 1 THEN p.rating END), 2)              AS avg_rating,        -- QUALITY
       ROUND(100.0 * SUM(p.attended = 1 AND p.rating >= 4)
             / NULLIF(SUM(p.attended = 1 AND p.rating IS NOT NULL),0), 1)     AS rated_4_plus_pct,  -- QUALITY
       ROUND(AVG(CASE WHEN p.attended = 1 THEN p.outcome_score END), 1)       AS avg_outcome_score, -- PERFORMANCE
       ROUND(100.0 * SUM(p.attended = 1 AND p.follow_up_done = 1)
             / NULLIF(SUM(p.attended),0), 1)                                  AS follow_up_done_pct -- PERFORMANCE
FROM planned a
LEFT JOIN activity_participation p ON p.activity_id = a.activity_id AND a.held_on IS NOT NULL
GROUP BY a.activity_type
ORDER BY planned DESC;

-- ---------------------------------------------------------------------
-- Q4. Escalations: subjects where the latest exam is 10+ points under target
--   (advisors are not subject experts, so these go to a tutor)
-- ---------------------------------------------------------------------
WITH latest AS (
  SELECT e.*, ROW_NUMBER() OVER (PARTITION BY student_id, subject_id ORDER BY exam_on DESC) AS rn
  FROM exam_results e WHERE exam_on <= '2026-10-17'
)
SELECT s.display_name, sb.name AS subject, l.exam_type, l.score_pct, t.target_pct,
       l.score_pct - t.target_pct AS gap_pts
FROM latest l
JOIN score_targets t USING (student_id, subject_id, exam_type)
JOIN students s USING (student_id)
JOIN subjects sb USING (subject_id)
WHERE l.rn = 1 AND l.score_pct - t.target_pct <= -10
  AND l.student_id IN (SELECT student_id FROM enrollments WHERE start_on <= '2026-10-17' AND end_on > '2026-10-17')
ORDER BY gap_pts;
