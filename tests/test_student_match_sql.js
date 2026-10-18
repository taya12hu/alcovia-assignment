/* Checks the student dashboard's numbers against sql/student_kpis.sql. Run: node tests/test_student_match_sql.js */
const fs = require("fs"), path = require("path"), vm = require("vm"), { execFileSync } = require("child_process");
const root = path.join(__dirname, "..");
const ctx = { window: {} }; vm.createContext(ctx);
for (const f of ["dashboards/student/data.js", "dashboards/student/metrics.js"]) vm.runInContext(fs.readFileSync(path.join(root, f), "utf8"), ctx);
const S = ctx.window.STU.computeStudents(ctx.window.DATA, "2026-09-18", "2026-10-17");
const py = `
import sqlite3, json, sys
db = sqlite3.connect("${root}/data/alcovia_demo.db"); db.row_factory = sqlite3.Row
sql = open("${root}/sql/student_kpis.sql").read()
sql = "\\n".join(l for l in sql.splitlines() if not l.startswith("."))
out, buf = [], ""
for line in sql.splitlines(keepends=True):
    buf += line
    if sqlite3.complete_statement(buf):
        if any(l.strip() and not l.strip().startswith("--") for l in buf.splitlines()):
            out.append([dict(r) for r in db.execute(buf)])
        buf = ""
print(json.dumps(out))`;
const [syl, hab, prog, esc] = JSON.parse(execFileSync("python3", ["-c", py]).toString());
let checks = 0, fails = 0;
const eq = (l, a, b, tol = 0.06) => { checks++; if (!((a == null && b == null) || Math.abs(a - b) <= tol)) { fails++; console.log("FAIL", l, a, b); } };
for (const r of syl) { const j = S.rows.find(x => x.name === r.display_name); eq(r.display_name + " coverage", j.syl.coverage, r.coverage_pct); eq(r.display_name + " readiness", j.syl.readiness, r.readiness_score); eq(r.display_name + " rigour", j.syl.rigourAdherence, r.rigour_adherence_pct); }
for (const r of hab) { const j = S.rows.find(x => x.name === r.display_name); eq(r.display_name + " tasks", j.h.taskCompletion, r.task_completion_pct); eq(r.display_name + " deadline", j.h.deadlineAdherence, r.deadline_adherence_pct); eq(r.display_name + " focus", j.h.focusMinutes, r.focus_minutes, 0); eq(r.display_name + " quiz", j.h.quizAvg, r.quiz_avg_pct); }
const P = ctx.window.STU.computeStudents(ctx.window.DATA, "2026-04-01", "2026-10-17").programme;
for (const r of prog) { const j = P.find(x => x.key === r.activity_type); eq(r.activity_type + " held", j.held, r.held, 0); eq(r.activity_type + " rating", j.rating, r.avg_rating, 0.006); eq(r.activity_type + " outcome", j.outcome, r.avg_outcome_score); eq(r.activity_type + " followup", j.followUp, r.follow_up_done_pct); }
const jsEsc = S.rows.flatMap(r => r.flags.filter(f => f.label.endsWith("below target"))).length; eq("escalations", jsEsc, esc.length, 0);
console.log(`${checks - fails}/${checks} checks passed`); process.exit(fails ? 1 : 0);
