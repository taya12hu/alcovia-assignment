/* GTM metric engine.
 * Same definitions as sql/gtm_kpis.sql (tested against it by tests/test_metrics_match_sql.js).
 * Input: window.DATA (column tables) and a date range [d0, d1] as 'YYYY-MM-DD'.
 */
(function (root) {
  const T = (D, name) => {
    const t = D[name];
    return t.rows.map(r => Object.fromEntries(t.cols.map((c, i) => [c, r[i]])));
  };
  const addDays = (iso, n) => {
    const d = new Date(iso + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  };
  const dayDiff = (a, b) => Math.round((new Date(a + "T00:00:00Z") - new Date(b + "T00:00:00Z")) / 864e5);
  const inR = (x, a, b) => x != null && x >= a && x <= b;
  const sum = (xs, f = x => x) => xs.reduce((s, x) => s + f(x), 0);
  const monthEnd = m => addDays(addDays(m + "-01", 32).slice(0, 7) + "-01", -1);

  const TARGET_CPQL = 2500, TARGET_ROAS = 3;

  function index(D) {
    if (D._ix) return D._ix;
    const ix = {};
    for (const n of ["campaigns", "ad_creatives", "ad_daily", "leads", "students", "enrollments", "invoices",
                     "workshops", "payments", "monthly_targets", "landing_pages"]) ix[n] = T(D, n);
    ix.enr = Object.fromEntries(ix.enrollments.map(e => [e.enrollment_id, e]));
    ix.stu = Object.fromEntries(ix.students.map(s => [s.student_id, s]));
    ix.cr = Object.fromEntries(ix.ad_creatives.map(c => [c.creative_id, c]));
    ix.cmp = Object.fromEntries(ix.campaigns.map(c => [c.campaign_id, c]));
    ix.renewed = new Set(ix.enrollments.filter(e => e.renewal_of).map(e => e.renewal_of));
    ix.firstStart = {};
    for (const e of ix.enrollments) {
      const f = ix.firstStart[e.student_id];
      if (!f || e.start_on < f) ix.firstStart[e.student_id] = e.start_on;
    }
    ix.lastAdDate = ix.ad_daily.reduce((m, a) => (a.stat_date > m ? a.stat_date : m), "");
    Object.defineProperty(D, "_ix", { value: ix, enumerable: false });
    return ix;
  }

  function revenue(ix, d0, d1) {
    const prog = ix.invoices.filter(i => inR(i.issued_on, d0, d1) && i.status !== "cancelled")
      .map(i => ({ ...i, e: ix.enr[i.enrollment_id] }));
    const ws = ix.payments.filter(p => p.kind === "workshop" && inR(p.paid_on, d0, d1));
    const cash = sum(ix.payments.filter(p => inR(p.paid_on, d0, d1)), p => p.amount);
    let target = 0;
    for (const t of ix.monthly_targets) {
      const ms = t.month + "-01", me = monthEnd(t.month);
      if (ms <= d1 && me >= d0) {
        const a = d0 > ms ? d0 : ms, b = d1 < me ? d1 : me;
        target += t.revenue_target * (dayDiff(b, a) + 1) / (dayDiff(me, ms) + 1);
      }
    }
    const trial = prog.filter(i => i.e.product === "trial_3m");
    const fullNew = prog.filter(i => i.e.product === "full_program" && !i.e.renewal_of);
    const renew = prog.filter(i => i.e.renewal_of);
    const programme = sum(prog, i => i.amount), workshop = sum(ws, p => p.amount);
    return {
      target: Math.round(target), booked: programme + workshop, programme, workshop,
      pctOfTarget: target ? (programme + workshop) / target * 100 : null,
      trialRevenue: sum(trial, i => i.amount), fullNewRevenue: sum(fullNew, i => i.amount),
      renewalRevenue: sum(renew, i => i.amount),
      trialSignups: trial.length, fullSignups: fullNew.length, renewals: renew.length,
      workshopSeats: ws.length, cash,
      onboarded: Object.values(ix.firstStart).filter(s => inR(s, d0, d1)).length,
    };
  }

  function unpaid(ix, asOf) {
    const paidBy = new Set(ix.payments.filter(p => p.invoice_id && p.paid_on <= asOf).map(p => p.invoice_id));
    return ix.invoices.filter(i => i.issued_on <= asOf && i.status !== "cancelled" && !paidBy.has(i.invoice_id))
      .map(i => {
        const e = ix.enr[i.enrollment_id];
        return { invoice: i.invoice_id, name: ix.stu[e.student_id].display_name, product: e.product,
                 amount: i.amount, issued: i.issued_on, due: i.due_on, overdue: dayDiff(asOf, i.due_on) };
      }).sort((a, b) => b.overdue - a.overdue);
  }

  function renewals(ix, asOf) {
    const lim = addDays(asOf, 30);
    return ix.enrollments.filter(e => e.product === "trial_3m" && e.end_on > asOf && e.end_on <= lim && !ix.renewed.has(e.enrollment_id))
      .map(e => ({ name: ix.stu[e.student_id].display_name, start: e.start_on, end: e.end_on, daysLeft: dayDiff(e.end_on, asOf) }))
      .sort((a, b) => a.end.localeCompare(b.end));
  }

  function funnel(ix, d0, d1) {
    const c = ix.leads.filter(l => inR(l.created_on, d0, d1));
    const n = f => c.filter(f).length;
    const closed = c.filter(l => l.outcome !== "open" && l.qualified_on);
    const metaQ = n(l => l.source === "meta" && l.qualified_on);
    const spend = sum(ix.ad_daily.filter(a => inR(a.stat_date, d0, d1) && ix.cmp[ix.cr[a.creative_id].campaign_id].objective === "program"), a => a.spend);
    const f = {
      total: c.length, meta: n(l => l.source === "meta"), organic: n(l => l.source !== "meta"),
      qualified: n(l => l.qualified_on), booked: n(l => l.discovery_booked_on),
      showed: n(l => l.discovery_showed === 1), callsHappened: n(l => l.discovery_showed != null),
      interviews: n(l => l.ambition_interview_on), architect: n(l => l.architect_session_on),
      converted: n(l => l.outcome === "converted"), open: n(l => l.outcome === "open"),
      avgJourney: closed.length ? sum(closed, l => dayDiff(l.outcome_on, l.created_on)) / closed.length : null,
      programmeSpend: spend, metaQualified: metaQ, cpql: metaQ ? spend / metaQ : null,
    };
    f.showUpRate = f.callsHappened ? f.showed / f.callsHappened * 100 : null;
    f.dropAfterDiscovery = f.showed ? (1 - f.interviews / f.showed) * 100 : null;
    f.leadToPaid = f.total ? f.converted / f.total * 100 : null;
    f.qualifiedToPaid = f.qualified ? f.converted / f.qualified * 100 : null;
    f.dropReasons = {};
    for (const l of c) if (l.outcome === "dropped") f.dropReasons[l.drop_reason] = (f.dropReasons[l.drop_reason] || 0) + 1;
    return f;
  }

  function campaigns(ix, d0, d1) {
    const len = dayDiff(d1, d0) + 1, p0 = addDays(d0, -len), p1 = addDays(d0, -1);
    const lastDay = d1 < ix.lastAdDate ? d1 : ix.lastAdDate;
    const out = [];
    for (const cp of ix.campaigns) {
      const rows = ix.ad_daily.filter(a => ix.cr[a.creative_id].campaign_id === cp.campaign_id);
      const cur = rows.filter(a => inR(a.stat_date, d0, d1));
      if (!cur.length) continue;
      const prev = rows.filter(a => inR(a.stat_date, p0, p1));
      const imp = sum(cur, a => a.impressions), clicks = sum(cur, a => a.clicks), spend = sum(cur, a => a.spend);
      const lpv = sum(cur, a => a.lp_views), bounces = sum(cur, a => a.lp_bounces);
      const ctr = clicks / imp;
      const pImp = sum(prev, a => a.impressions);
      const pCtr = pImp ? sum(prev, a => a.clicks) / pImp : null;
      const lastRows = rows.filter(a => a.stat_date === lastDay);
      const freq = lastRows.length ? Math.max(...lastRows.map(a => a.frequency_7d)) : null;
      const leads = ix.leads.filter(l => l.source === "meta" && l.campaign_id === cp.campaign_id && inR(l.created_on, d0, d1));
      const qualified = leads.filter(l => l.qualified_on).length;
      const seats = ix.payments.filter(p => p.kind === "workshop" && p.utm_creative_id && ix.cr[p.utm_creative_id].campaign_id === cp.campaign_id && inR(p.paid_on, d0, d1));
      const m = {
        id: cp.campaign_id, name: cp.name, objective: cp.objective, lp: cp.landing_page_id, spend, imp, clicks,
        ctr: ctr * 100, ctrChange: pCtr ? (ctr - pCtr) / pCtr * 100 : null, freq,
        bounce: lpv ? bounces / lpv * 100 : null, loadMs: lpv ? sum(cur, a => a.lp_load_ms * a.lp_views) / lpv : null,
        leads: leads.length, qualified, converted: leads.filter(l => l.outcome === "converted").length,
        cpql: qualified ? spend / qualified : null, seats: seats.length,
        roas: spend ? sum(seats, p => p.amount) / spend : null,
      };
      m.decision = decide(m);
      out.push(m);
    }
    return out.sort((a, b) => a.objective.localeCompare(b.objective) || b.spend - a.spend);
  }

  // Same order of checks as SQL Q6. First rule that matches wins.
  function decide(m) {
    if (m.spend < 5000) return { key: "watch", label: "Watch", why: "Under ₹5,000 spent. Too early to judge." };
    if (m.objective === "program" && (!m.qualified || m.cpql > 2 * TARGET_CPQL))
      return { key: "pause", label: "Pause", why: m.qualified ? `₹${Math.round(m.cpql).toLocaleString("en-IN")} per qualified lead, over 2× the ₹2,500 target.` : "No qualified leads from this spend." };
    if (m.objective === "workshop" && m.roas < TARGET_ROAS / 2)
      return { key: "pause", label: "Pause", why: `Seats return only ${m.roas.toFixed(1)}× the spend.` };
    if (m.bounce > 55 || m.loadMs > 3000)
      return { key: "fix", label: "Fix landing page", why: `${Math.round(m.bounce)}% of visitors leave at once; page takes ${(m.loadMs / 1000).toFixed(1)}s to load.` };
    if (m.freq >= 3 || (m.ctrChange != null && m.ctrChange <= -20))
      return { key: "refresh", label: "Refresh creative", why: m.freq >= 3 ? `The same people saw these ads ${m.freq.toFixed(1)} times this week.` : `Click rate fell ${Math.abs(Math.round(m.ctrChange))}% vs the previous period.` };
    if ((m.objective === "program" && m.cpql <= TARGET_CPQL) || (m.objective === "workshop" && m.roas >= TARGET_ROAS))
      return { key: "scale", label: "Scale budget", why: m.objective === "program" ? `₹${Math.round(m.cpql).toLocaleString("en-IN")} per qualified lead, under target, with room in the audience.` : `Seats return ${m.roas.toFixed(1)}× the spend, with room in the audience.` };
    return { key: "keep", label: "Keep running", why: "Inside targets. No action needed." };
  }

  function creatives(ix, d0, d1) {
    const lastDay = d1 < ix.lastAdDate ? d1 : ix.lastAdDate;
    const by = {};
    for (const a of ix.ad_daily) {
      if (!inR(a.stat_date, d0, d1)) continue;
      const b = by[a.creative_id] || (by[a.creative_id] = { imp: 0, clicks: 0, spend: 0, freq: null });
      b.imp += a.impressions; b.clicks += a.clicks; b.spend += a.spend;
      if (a.stat_date === lastDay) b.freq = a.frequency_7d;
    }
    return Object.entries(by).filter(([, b]) => b.imp >= 2000).map(([id, b]) => {
      const cr = ix.cr[id];
      return { id, name: cr.name, format: cr.format, campaign: ix.cmp[cr.campaign_id].name, objective: ix.cmp[cr.campaign_id].objective,
               imp: b.imp, ctr: b.clicks / b.imp * 100, freq: b.freq, spend: b.spend };
    }).sort((a, b) => b.ctr - a.ctr);
  }

  function landingPages(ix, d0, d1) {
    return ix.landing_pages.map(lp => {
      const rows = ix.ad_daily.filter(a => inR(a.stat_date, d0, d1) && ix.cmp[ix.cr[a.creative_id].campaign_id].landing_page_id === lp.landing_page_id);
      const lpv = sum(rows, a => a.lp_views);
      return { id: lp.landing_page_id, name: lp.name, path: lp.url_path, views: lpv,
               bounce: lpv ? sum(rows, a => a.lp_bounces) / lpv * 100 : null,
               loadMs: lpv ? sum(rows, a => a.lp_load_ms * a.lp_views) / lpv : null };
    }).filter(l => l.views > 0);
  }

  function monthly(ix, asOf) {
    const lastMonth = asOf.slice(0, 7);
    return ix.monthly_targets.filter(t => t.month <= lastMonth).map(t => {
      const inv = ix.invoices.filter(i => i.issued_on.slice(0, 7) === t.month && i.status !== "cancelled").map(i => ({ ...i, e: ix.enr[i.enrollment_id] }));
      return {
        month: t.month, target: t.revenue_target,
        full: sum(inv.filter(i => i.e.product === "full_program" && !i.e.renewal_of), i => i.amount),
        trial: sum(inv.filter(i => i.e.product === "trial_3m"), i => i.amount),
        renewal: sum(inv.filter(i => i.e.renewal_of), i => i.amount),
        workshop: sum(ix.payments.filter(p => p.kind === "workshop" && p.paid_on.slice(0, 7) === t.month), p => p.amount),
        partial: t.month === lastMonth,
      };
    });
  }

  function computeGTM(D, d0, d1) {
    const ix = index(D);
    const asOf = d1 < D.asOf ? d1 : D.asOf;
    return {
      d0, d1, asOf, revenue: revenue(ix, d0, d1), unpaid: unpaid(ix, asOf), renewals: renewals(ix, asOf),
      funnel: funnel(ix, d0, d1), campaigns: campaigns(ix, d0, d1), creatives: creatives(ix, d0, d1),
      landingPages: landingPages(ix, d0, d1), monthly: monthly(ix, D.asOf),
      cohortMaturing: dayDiff(asOf, d1) < 30,
    };
  }

  root.GTM = { computeGTM, addDays, dayDiff, TARGET_CPQL, TARGET_ROAS };
})(typeof window !== "undefined" ? window : globalThis);
