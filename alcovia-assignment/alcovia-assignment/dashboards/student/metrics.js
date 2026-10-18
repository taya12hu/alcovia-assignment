/* Student progress metric engine.
 * Same definitions as sql/student_kpis.sql and docs/kpi_dictionary.md.
 */
(function (root) {
  const T = (D, name) => {
    const t = D[name];
    return t.rows.map(r => Object.fromEntries(t.cols.map((c, i) => [c, r[i]])));
  };
  const addDays = (iso, n) => { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const dayDiff = (a, b) => Math.round((new Date(a + "T00:00:00Z") - new Date(b + "T00:00:00Z")) / 864e5);
  const inR = (x, a, b) => x != null && x >= a && x <= b;
  const sum = (xs, f = x => x) => xs.reduce((s, x) => s + f(x), 0);
  const avg = (xs, f = x => x) => xs.length ? sum(xs, f) / xs.length : null;
  const by = (xs, k) => { const o = {}; for (const x of xs) (o[x[k]] || (o[x[k]] = [])).push(x); return o; };

  const YEAR_START = "2026-04-01";
  const READINESS = [0, 10, 25, 50, 70, 100];            // points for stage 0..5
  const STAGES = ["Not started", "Read", "Notes made", "Practice ≥70%", "Past paper done", "Exam ready (≥80%)"];
  const ESCALATE_GAP = 10;                                 // points below target that triggers tutor support

  // Stage = how far the chapter got through the rigour, counting only steps done by `asOf`, in order.
  function stage(p, asOf) {
    if (!p || !p.read_on || p.read_on > asOf) return 0;
    if (!p.notes_on || p.notes_on > asOf) return 1;
    if (!p.practice_on || p.practice_on > asOf || p.practice_accuracy < 70) return 2;
    if (!p.past_paper_on || p.past_paper_on > asOf) return 3;
    return p.past_paper_accuracy >= 80 ? 5 : 4;
  }
  const expectedCoverage = asOf => Math.min(100, Math.max(0, dayDiff(asOf, YEAR_START) / 365 * 100)); // 25% per quarter
  const paceStatus = gap => gap >= -10 ? "on_track" : gap >= -20 ? "at_risk" : "behind";

  function index(D) {
    if (D._ix) return D._ix;
    const ix = {};
    for (const n of ["students", "subjects", "chapters", "chapter_progress", "score_targets", "exam_results", "tasks",
                     "focus_sessions", "quiz_attempts", "wearable_daily", "activities", "activity_participation", "roadmap_milestones"]) ix[n] = T(D, n);
    ix.active = ix.students.filter(s => D.activeStudents.includes(s.student_id));
    ix.chBySubj = by(ix.chapters, "subject_id");
    ix.prog = {};
    for (const p of ix.chapter_progress) ix.prog[p.student_id + "|" + p.chapter_id] = p;
    for (const n of ["tasks", "focus_sessions", "quiz_attempts", "wearable_daily", "roadmap_milestones", "exam_results", "score_targets"]) ix[n + "BySt"] = by(ix[n], "student_id");
    ix.act = Object.fromEntries(ix.activities.map(a => [a.activity_id, a]));
    ix.partBySt = by(ix.activity_participation, "student_id");
    Object.defineProperty(D, "_ix", { value: ix, enumerable: false });
    return ix;
  }

  function syllabus(ix, sid, asOf) {
    const exp = expectedCoverage(asOf);
    const subjects = ix.subjects.map(sub => {
      const chs = ix.chBySubj[sub.subject_id];
      const chapters = chs.map(c => {
        const p = ix.prog[sid + "|" + c.chapter_id], st = stage(p, asOf);
        const practiceLow = p && p.practice_on && p.practice_on <= asOf && p.practice_accuracy < 70;
        const acc = p && p.past_paper_on && p.past_paper_on <= asOf ? p.past_paper_accuracy : (p && p.practice_on && p.practice_on <= asOf ? p.practice_accuracy : null);
        return { id: c.chapter_id, name: c.name, stage: st, score: READINESS[st], accuracy: acc, practiceLow };
      });
      const started = chapters.filter(c => c.stage >= 1), rig = chapters.filter(c => c.stage >= 3);
      const coverage = rig.length / chapters.length * 100;
      const targets = (ix.score_targetsBySt[sid] || []).filter(t => t.subject_id === sub.subject_id);
      const exams = (ix.exam_resultsBySt[sid] || []).filter(e => e.subject_id === sub.subject_id && e.exam_on <= asOf).sort((a, b) => a.exam_on.localeCompare(b.exam_on));
      const last = exams[exams.length - 1];
      const tgt = last ? (targets.find(t => t.exam_type === last.exam_type) || {}).target_pct : (targets.find(t => t.exam_type === "half_yearly") || {}).target_pct;
      return {
        id: sub.subject_id, name: sub.name, chapters, total: chapters.length, started: started.length, rigorous: rig.length,
        ready: chapters.filter(c => c.stage === 5).length, coverage, expected: exp, gap: coverage - exp,
        readiness: avg(chapters, c => c.score), rigourAdherence: started.length ? rig.length / started.length * 100 : null,
        lastExam: last ? { type: last.exam_type, on: last.exam_on, score: last.score_pct, target: tgt, gap: last.score_pct - tgt } : null,
        target: tgt,
      };
    });
    const all = subjects.flatMap(s => s.chapters);
    const coverage = all.filter(c => c.stage >= 3).length / all.length * 100;
    return { subjects, coverage, expected: exp, gap: coverage - exp, status: paceStatus(coverage - exp),
             readiness: avg(all, c => c.score), rigourAdherence: (() => { const st = all.filter(c => c.stage >= 1); return st.length ? all.filter(c => c.stage >= 3).length / st.length * 100 : null; })() };
  }

  function habits(ix, sid, d0, d1, asOf) {
    const dueTasks = (ix.tasksBySt[sid] || []).filter(t => inR(t.due_on, d0, d1) && t.due_on <= asOf);
    const done = dueTasks.filter(t => t.completed_on && t.completed_on <= asOf);
    const onTime = done.filter(t => t.completed_on <= t.due_on);
    const timed = done.filter(t => t.actual_min);
    const focus = (ix.focus_sessionsBySt[sid] || []).filter(f => inR(f.started_on, d0, d1));
    const days = dayDiff(d1, d0) + 1;
    const quiz = (ix.quiz_attemptsBySt[sid] || []).filter(q => inR(q.quiz_on, d0, d1));
    const lastFocus = (ix.focus_sessionsBySt[sid] || []).filter(f => f.started_on <= asOf).map(f => f.started_on).sort().pop() || null;
    const wear = (ix.wearable_dailyBySt[sid] || []).filter(w => inR(w.day, d0, d1));
    const parts = (ix.partBySt[sid] || []).map(p => ({ ...p, a: ix.act[p.activity_id] })).filter(p => p.a.held_on && inR(p.a.held_on, d0, d1));
    const ms = (ix.roadmap_milestonesBySt[sid] || []).filter(m => inR(m.due_on, d0, d1) && m.due_on <= asOf);
    return {
      tasksDue: dueTasks.length, tasksDone: done.length,
      taskCompletion: dueTasks.length ? done.length / dueTasks.length * 100 : null,
      deadlineAdherence: done.length ? onTime.length / done.length * 100 : null,
      estimateAccuracy: timed.length ? Math.max(0, 100 - avg(timed, t => Math.abs(t.actual_min - t.estimated_min) / t.estimated_min) * 100) : null,
      focusMinutes: sum(focus, f => f.minutes), focusPerWeek: sum(focus, f => f.minutes) / days * 7, focusSessions: focus.length,
      focusCompletion: focus.length ? focus.filter(f => f.completed).length / focus.length * 100 : null,
      daysSinceFocus: lastFocus ? dayDiff(asOf, lastFocus) : null,
      quizParticipation: quiz.length / days * 100, quizAvg: quiz.length ? avg(quiz, q => q.score / q.out_of * 100) : null,
      wearable: wear.length ? { device: wear[0].device, sleep: avg(wear.filter(w => w.sleep_hours != null), w => w.sleep_hours),
                                recovery: avg(wear.filter(w => w.recovery_pct != null), w => w.recovery_pct),
                                active: avg(wear.filter(w => w.active_min != null), w => w.active_min) } : null,
      activitiesInvited: parts.length, activitiesAttended: parts.filter(p => p.attended).length,
      attendance: parts.length ? parts.filter(p => p.attended).length / parts.length * 100 : null,
      activities: parts.sort((a, b) => b.a.held_on.localeCompare(a.a.held_on)),
      milestonesDue: ms.length, milestonesDone: ms.filter(m => m.done_on && m.done_on <= asOf).length,
      milestones: ms,
      focusByWeek: (() => { const w = {}; for (const f of focus) { const k = Math.floor(dayDiff(f.started_on, d0) / 7); w[k] = (w[k] || 0) + f.minutes; } return Array.from({ length: Math.ceil(days / 7) }, (_, i) => w[i] || 0); })(),
    };
  }

  // Exceptions an advisor should act on, with the suggested next step.
  function flags(syl, h) {
    const f = [];
    if (syl.status === "behind") f.push({ sev: "bad", label: "Behind on syllabus", action: `Plan a 2-week sprint: ${Math.round(-syl.gap)} points behind the 25%-per-quarter pace.` });
    else if (syl.status === "at_risk") f.push({ sev: "warn", label: "Syllabus at risk", action: "Add two self-study slots this week." });
    for (const s of syl.subjects) if (s.lastExam && s.lastExam.gap <= -ESCALATE_GAP)
      f.push({ sev: "bad", label: `${s.name} below target`, action: `Escalate to a ${s.name} tutor: scored ${s.lastExam.score}% vs ${s.lastExam.target}% target.` });
    if (syl.rigourAdherence != null && syl.rigourAdherence < 40) f.push({ sev: "warn", label: "Skipping steps", action: "Chapters are read but not practised. Ask for practice scores before marking done." });
    if (h.taskCompletion != null && h.taskCompletion < 60) f.push({ sev: "warn", label: "Low task completion", action: "Review the timetable with the student; tasks may be too many or too long." });
    if (h.daysSinceFocus == null || h.daysSinceFocus > 14) f.push({ sev: "neutral", label: "No focus sessions", action: "Not using the focus timer. Set one daily session as a task." });
    return f;
  }

  function computeStudents(D, d0, d1) {
    const ix = index(D), asOf = d1 < D.asOf ? d1 : D.asOf;
    const rows = ix.active.map(s => {
      const syl = syllabus(ix, s.student_id, asOf), h = habits(ix, s.student_id, d0, d1, asOf);
      return { id: s.student_id, name: s.display_name, grade: s.grade, joined: s.joined_on, syl, h, flags: flags(syl, h) };
    });
    return { asOf, d0, d1, rows, programme: programme(ix, d0, d1, asOf), expected: expectedCoverage(asOf) };
  }

  const TYPES = {
    career_workshop: "Career workshop", pod_session: "Pod session", peer_session: "Peer session", mentor_call: "Mentor call",
    personal_branding: "Personal branding shoot", podcast: "Podcast shoot", competition_prep: "Competition prep",
    parent_child: "Parent-child workshop", out_of_city: "Out-of-city experience",
  };
  function programme(ix, d0, d1, asOf) {
    return Object.entries(TYPES).map(([k, label]) => {
      const planned = ix.activities.filter(a => a.activity_type === k && inR(a.planned_on, d0, d1) && a.planned_on <= asOf);
      const held = planned.filter(a => a.held_on);
      const heldIds = new Set(held.map(a => a.activity_id));
      const parts = ix.activity_participation.filter(p => heldIds.has(p.activity_id));
      const att = parts.filter(p => p.attended), rated = att.filter(p => p.rating != null), out = att.filter(p => p.outcome_score != null);
      return {
        key: k, label, planned: planned.length, held: held.length, heldPct: planned.length ? held.length / planned.length * 100 : null,
        invited: parts.length, attended: att.length, attendance: parts.length ? att.length / parts.length * 100 : null,
        reach: new Set(att.map(p => p.student_id)).size,
        rating: avg(rated, p => p.rating), promoters: rated.length ? rated.filter(p => p.rating >= 4).length / rated.length * 100 : null,
        responseRate: att.length ? rated.length / att.length * 100 : null,
        outcome: avg(out, p => p.outcome_score), followUp: att.length ? att.filter(p => p.follow_up_done === 1).length / att.length * 100 : null,
      };
    });
  }

  root.STU = { computeStudents, stage, READINESS, STAGES, addDays, dayDiff, expectedCoverage, TYPES };
})(typeof window !== "undefined" ? window : globalThis);
