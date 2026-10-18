-- =====================================================================
-- GTM KPIs. Runs on SQLite (tested) and Postgres (swap julianday() for date math).
-- Change the two dates in each `params` block to pick a period.
-- Every number on the GTM dashboard comes from one of these queries;
-- docs/kpi_dictionary.md defines each one in plain words.
--
--   sqlite3 data/alcovia_demo.db < sql/gtm_kpis.sql
-- =====================================================================
.headers on
.mode column

-- ---------------------------------------------------------------------
-- Q1. Revenue scorecard for the period
--   booked revenue  = programme invoices issued + workshop seats sold
--   cash collected  = Razorpay payments received
--   target          = monthly targets, pro-rated by days in the period
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-01' AS d0, '2026-09-30' AS d1),
prog AS (
  SELECT e.product, e.renewal_of IS NOT NULL AS is_renewal, i.amount
  FROM invoices i JOIN enrollments e USING (enrollment_id), params
  WHERE i.issued_on BETWEEN d0 AND d1 AND i.status <> 'cancelled'
),
ws AS (
  SELECT SUM(amount) AS amt, COUNT(*) AS seats
  FROM payments, params WHERE kind = 'workshop' AND paid_on BETWEEN d0 AND d1
),
cash AS (SELECT SUM(amount) AS amt FROM payments, params WHERE paid_on BETWEEN d0 AND d1),
tgt AS (
  -- pro-rate each month's target by the number of its days inside the period
  SELECT SUM(t.revenue_target *
             (julianday(MIN(d1, date(t.month || '-01', '+1 month', '-1 day')))
              - julianday(MAX(d0, t.month || '-01')) + 1)
             / (julianday(date(t.month || '-01', '+1 month')) - julianday(t.month || '-01'))) AS amt
  FROM monthly_targets t, params
  WHERE t.month || '-01' <= d1 AND date(t.month || '-01', '+1 month', '-1 day') >= d0
),
onboarded AS (
  SELECT COUNT(*) AS n FROM (
    SELECT student_id, MIN(start_on) AS first_start FROM enrollments GROUP BY student_id
  ), params WHERE first_start BETWEEN d0 AND d1
)
SELECT
  ROUND((SELECT amt FROM tgt))                                                AS revenue_target,
  (SELECT COALESCE(SUM(amount),0) FROM prog) + COALESCE((SELECT amt FROM ws),0) AS booked_revenue,
  ROUND(100.0 * ((SELECT COALESCE(SUM(amount),0) FROM prog) + COALESCE((SELECT amt FROM ws),0))
        / (SELECT amt FROM tgt), 1)                                           AS pct_of_target,
  (SELECT COALESCE(SUM(amount),0) FROM prog)                                  AS programme_revenue,
  (SELECT COALESCE(SUM(amount),0) FROM prog WHERE product='trial_3m')         AS trial_revenue,
  (SELECT COALESCE(SUM(amount),0) FROM prog WHERE product='full_program' AND NOT is_renewal) AS full_new_revenue,
  (SELECT COALESCE(SUM(amount),0) FROM prog WHERE is_renewal)                 AS renewal_revenue,
  COALESCE((SELECT amt FROM ws),0)                                            AS workshop_revenue,
  COALESCE((SELECT seats FROM ws),0)                                          AS workshop_seats,
  COALESCE((SELECT amt FROM cash),0)                                          AS cash_collected,
  (SELECT COUNT(*) FROM prog WHERE product='trial_3m')                        AS trial_signups,
  (SELECT COUNT(*) FROM prog WHERE product='full_program' AND NOT is_renewal) AS full_signups,
  (SELECT COUNT(*) FROM prog WHERE is_renewal)                                AS renewals,
  (SELECT n FROM onboarded)                                                   AS students_onboarded;

-- ---------------------------------------------------------------------
-- Q2. Invoices raised but not paid, as of the end of the period
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-10-17' AS as_of)
SELECT i.invoice_id, s.display_name, e.product, i.amount, i.issued_on, i.due_on,
       CAST(julianday(as_of) - julianday(i.due_on) AS INTEGER) AS days_overdue
FROM invoices i
JOIN enrollments e USING (enrollment_id)
JOIN students s USING (student_id), params
WHERE i.issued_on <= as_of AND i.status <> 'cancelled'
  AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.invoice_id = i.invoice_id AND p.paid_on <= as_of)
ORDER BY days_overdue DESC;

-- ---------------------------------------------------------------------
-- Q3. 3-month trials ending in the next 30 days (renewal pipeline)
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-10-17' AS as_of)
SELECT s.display_name, e.enrollment_id, e.start_on, e.end_on,
       CAST(julianday(e.end_on) - julianday(as_of) AS INTEGER) AS days_left
FROM enrollments e JOIN students s USING (student_id), params
WHERE e.product = 'trial_3m'
  AND e.end_on > as_of AND e.end_on <= date(as_of, '+30 days')
  AND NOT EXISTS (SELECT 1 FROM enrollments r WHERE r.renewal_of = e.enrollment_id)
ORDER BY e.end_on;

-- ---------------------------------------------------------------------
-- Q4. Funnel for leads CREATED in the period (cohort view)
--   A lead is counted once (phone_hash is unique), at every stage it reached.
--   Show-up rate only counts calls whose date has passed.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-01' AS d0, '2026-09-30' AS d1),
c AS (SELECT l.* FROM leads l, params WHERE created_on BETWEEN d0 AND d1)
SELECT
  COUNT(*)                                             AS total_leads,
  SUM(source = 'meta')                                 AS meta_leads,
  SUM(source <> 'meta')                                AS organic_and_referral_leads,
  SUM(qualified_on IS NOT NULL)                        AS qualified,
  SUM(discovery_booked_on IS NOT NULL)                 AS discovery_booked,
  SUM(discovery_showed = 1)                            AS discovery_showed,
  ROUND(100.0 * SUM(discovery_showed = 1) / NULLIF(SUM(discovery_showed IS NOT NULL),0), 1) AS show_up_rate_pct,
  SUM(ambition_interview_on IS NOT NULL)               AS ambition_interviews,
  ROUND(100.0 * (1 - 1.0 * SUM(ambition_interview_on IS NOT NULL) / NULLIF(SUM(discovery_showed = 1),0)), 1)
                                                       AS dropoff_after_discovery_pct,
  SUM(architect_session_on IS NOT NULL)                AS architect_sessions,
  SUM(outcome = 'converted')                           AS converted,
  ROUND(100.0 * SUM(outcome = 'converted') / COUNT(*), 2)        AS lead_to_paid_pct,
  ROUND(100.0 * SUM(outcome = 'converted') / NULLIF(SUM(qualified_on IS NOT NULL),0), 1) AS qualified_to_paid_pct,
  SUM(outcome = 'open')                                AS still_open,
  ROUND(AVG(CASE WHEN outcome <> 'open' AND qualified_on IS NOT NULL
                 THEN julianday(outcome_on) - julianday(created_on) END), 1) AS avg_journey_days
FROM c;

-- ---------------------------------------------------------------------
-- Q5. Cost per qualified lead (Meta only)
--   spend in the period / Meta leads created in the period that qualified
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-01' AS d0, '2026-09-30' AS d1)
SELECT
  ROUND(SUM(a.spend)) AS programme_ad_spend,
  (SELECT COUNT(*) FROM leads l, params p
     WHERE l.source='meta' AND l.qualified_on IS NOT NULL AND l.created_on BETWEEN p.d0 AND p.d1) AS meta_qualified_leads,
  ROUND(SUM(a.spend) / (SELECT COUNT(*) FROM leads l, params p
     WHERE l.source='meta' AND l.qualified_on IS NOT NULL AND l.created_on BETWEEN p.d0 AND p.d1)) AS cost_per_qualified_lead
FROM ad_daily a
JOIN ad_creatives cr USING (creative_id)
JOIN campaigns cp ON cp.campaign_id = cr.campaign_id, params
WHERE cp.objective = 'program' AND a.stat_date BETWEEN d0 AND d1;

-- ---------------------------------------------------------------------
-- Q6. Campaign scorecard + decision (scale / refresh / fix page / pause / watch)
--   Rules are spelled out in docs/kpi_dictionary.md section "Campaign decisions".
--   Frequency = Meta's 7-day frequency on the last day of the period.
--   CTR change compares with the previous period of the same length.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-01' AS d0, '2026-09-30' AS d1,
                       2500.0 AS target_cpql, 3.0 AS target_roas),
prev AS (SELECT date(d0, '-' || CAST(julianday(d1) - julianday(d0) + 1 AS INTEGER) || ' days') AS p0,
                date(d0, '-1 day') AS p1 FROM params),
cur AS (
  SELECT cr.campaign_id, SUM(spend) AS spend, SUM(impressions) AS imp, SUM(clicks) AS clicks,
         SUM(lp_views) AS lpv, SUM(lp_bounces) AS bounces,
         ROUND(SUM(lp_load_ms * lp_views) * 1.0 / NULLIF(SUM(lp_views),0)) AS load_ms
  FROM ad_daily a JOIN ad_creatives cr USING (creative_id), params
  WHERE stat_date BETWEEN d0 AND d1 GROUP BY cr.campaign_id
),
before AS (
  SELECT cr.campaign_id, 1.0 * SUM(clicks) / NULLIF(SUM(impressions),0) AS ctr
  FROM ad_daily a JOIN ad_creatives cr USING (creative_id), prev
  WHERE stat_date BETWEEN p0 AND p1 GROUP BY cr.campaign_id
),
freq AS (
  SELECT cr.campaign_id, MAX(frequency_7d) AS freq
  FROM ad_daily a JOIN ad_creatives cr USING (creative_id), params
  WHERE stat_date = (SELECT MAX(stat_date) FROM ad_daily, params WHERE stat_date <= d1)
  GROUP BY cr.campaign_id
),
lds AS (
  SELECT campaign_id, COUNT(*) AS leads, SUM(qualified_on IS NOT NULL) AS qualified,
         SUM(outcome='converted') AS converted
  FROM leads, params WHERE source='meta' AND created_on BETWEEN d0 AND d1 GROUP BY campaign_id
),
seats AS (
  SELECT cr.campaign_id, COUNT(*) AS seats, SUM(p.amount) AS revenue
  FROM payments p JOIN ad_creatives cr ON cr.creative_id = p.utm_creative_id, params
  WHERE p.kind='workshop' AND p.paid_on BETWEEN d0 AND d1 GROUP BY cr.campaign_id
),
m AS (
  SELECT cp.campaign_id, cp.name, cp.objective, ROUND(cur.spend) AS spend,
         ROUND(100.0 * cur.clicks / cur.imp, 2) AS ctr_pct,
         ROUND(100.0 * (1.0 * cur.clicks / cur.imp - b.ctr) / b.ctr, 0) AS ctr_change_pct,
         f.freq, ROUND(100.0 * cur.bounces / NULLIF(cur.lpv,0), 1) AS lp_bounce_pct, cur.load_ms,
         COALESCE(l.leads,0) AS leads, COALESCE(l.qualified,0) AS qualified, COALESCE(l.converted,0) AS converted,
         ROUND(cur.spend / NULLIF(l.qualified,0)) AS cpql,
         COALESCE(s.seats,0) AS seats, ROUND(COALESCE(s.revenue,0) / cur.spend, 2) AS roas,
         params.target_cpql, params.target_roas
  FROM campaigns cp JOIN cur USING (campaign_id)
  LEFT JOIN before b USING (campaign_id) LEFT JOIN freq f USING (campaign_id)
  LEFT JOIN lds l USING (campaign_id) LEFT JOIN seats s USING (campaign_id), params
)
SELECT campaign_id, objective, spend, ctr_pct, ctr_change_pct, freq, lp_bounce_pct, load_ms,
       leads, qualified, cpql, seats, roas,
       CASE
         WHEN spend < 5000 THEN 'Watch: not enough spend yet'
         WHEN objective='program'  AND (qualified = 0 OR cpql > 2 * target_cpql) THEN 'Pause'
         WHEN objective='workshop' AND roas < target_roas / 2 THEN 'Pause'
         WHEN lp_bounce_pct > 55 OR load_ms > 3000 THEN 'Fix landing page'
         WHEN freq >= 3 OR ctr_change_pct <= -20 THEN 'Refresh creative'
         WHEN (objective='program' AND cpql <= target_cpql) OR (objective='workshop' AND roas >= target_roas)
           THEN 'Scale budget'
         ELSE 'Keep running'
       END AS decision
FROM m ORDER BY objective, spend DESC;

-- ---------------------------------------------------------------------
-- Q7. Best and worst ads by CTR in the period (min 2,000 impressions)
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026-09-01' AS d0, '2026-09-30' AS d1)
SELECT cr.creative_id, cr.name, cr.format,
       SUM(impressions) AS impressions,
       ROUND(100.0 * SUM(clicks) / SUM(impressions), 2) AS ctr_pct,
       MAX(CASE WHEN stat_date = (SELECT MAX(stat_date) FROM ad_daily, params WHERE stat_date <= d1)
                THEN frequency_7d END) AS latest_frequency
FROM ad_daily a JOIN ad_creatives cr USING (creative_id), params
WHERE stat_date BETWEEN d0 AND d1
GROUP BY cr.creative_id HAVING SUM(impressions) >= 2000
ORDER BY ctr_pct DESC;

-- ---------------------------------------------------------------------
-- Q8. Monthly trend: booked revenue vs target, split by line
-- ---------------------------------------------------------------------
SELECT t.month,
       t.revenue_target,
       COALESCE((SELECT SUM(i.amount) FROM invoices i JOIN enrollments e USING (enrollment_id)
                 WHERE substr(i.issued_on,1,7) = t.month AND e.product='trial_3m'),0) AS trial,
       COALESCE((SELECT SUM(i.amount) FROM invoices i JOIN enrollments e USING (enrollment_id)
                 WHERE substr(i.issued_on,1,7) = t.month AND e.product='full_program'),0) AS full_program,
       COALESCE((SELECT SUM(amount) FROM payments p
                 WHERE p.kind='workshop' AND substr(p.paid_on,1,7) = t.month),0) AS workshop
FROM monthly_targets t
WHERE t.month <= '2026-10'
ORDER BY t.month;
