/* Checks that the dashboard's JavaScript numbers equal the SQL numbers.
 * Run: python3 scripts/export_sql_results.py && node tests/test_metrics_match_sql.js
 */
const fs = require("fs"), path = require("path"), vm = require("vm");
const root = path.join(__dirname, "..");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["dashboards/gtm/data.js", "dashboards/gtm/metrics.js"])
  vm.runInContext(fs.readFileSync(path.join(root, f), "utf8"), ctx);
const { computeGTM } = ctx.window.GTM, D = ctx.window.DATA;
const sql = JSON.parse(fs.readFileSync(path.join(root, "tests/sql_results.json"), "utf8"));

let fails = 0, checks = 0;
const eq = (label, a, b, tol = 0.6) => {
  checks++;
  const ok = (a == null && b == null) || Math.abs(Number(a) - Number(b)) <= tol;
  if (!ok) { fails++; console.log(`FAIL ${label}: js=${a} sql=${b}`); }
};

for (const run of sql) {
  const g = computeGTM(D, run.d0, run.d1), r = run.revenue, f = run.funnel, tag = `[${run.d0}..${run.d1}]`;
  eq(`${tag} target`, g.revenue.target, r.revenue_target, 1);
  eq(`${tag} booked`, g.revenue.booked, r.booked_revenue);
  eq(`${tag} trial`, g.revenue.trialRevenue, r.trial_revenue);
  eq(`${tag} full new`, g.revenue.fullNewRevenue, r.full_new_revenue);
  eq(`${tag} renewal`, g.revenue.renewalRevenue, r.renewal_revenue);
  eq(`${tag} workshop`, g.revenue.workshop, r.workshop_revenue);
  eq(`${tag} seats`, g.revenue.workshopSeats, r.workshop_seats);
  eq(`${tag} cash`, g.revenue.cash, r.cash_collected);
  eq(`${tag} onboarded`, g.revenue.onboarded, r.students_onboarded);
  eq(`${tag} leads`, g.funnel.total, f.total_leads);
  eq(`${tag} qualified`, g.funnel.qualified, f.qualified);
  eq(`${tag} showed`, g.funnel.showed, f.discovery_showed);
  eq(`${tag} show-up %`, g.funnel.showUpRate, f.show_up_rate_pct, 0.06);
  eq(`${tag} converted`, g.funnel.converted, f.converted);
  eq(`${tag} journey`, g.funnel.avgJourney, f.avg_journey_days, 0.06);
  eq(`${tag} cpql`, g.funnel.cpql, run.cpql.cost_per_qualified_lead, 1);
  eq(`${tag} unpaid count`, g.unpaid.length, run.unpaid_count);
  eq(`${tag} renewals due`, g.renewals.length, run.renewals_due);
  for (const c of run.campaigns) {
    const j = g.campaigns.find(x => x.id === c.campaign_id);
    eq(`${tag} ${c.campaign_id} spend`, j.spend, c.spend, 1);
    eq(`${tag} ${c.campaign_id} ctr`, j.ctr, c.ctr_pct, 0.006);
    checks++;
    if (!c.decision.startsWith(j.decision.label)) { fails++; console.log(`FAIL ${tag} ${c.campaign_id} decision js=${j.decision.label} sql=${c.decision}`); }
  }
}
console.log(`${checks - fails}/${checks} checks passed`);
process.exit(fails ? 1 : 0);
