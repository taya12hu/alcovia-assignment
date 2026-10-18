"""
Run sql/gtm_kpis.sql for several date ranges and save the results to
tests/sql_results.json, so tests/test_metrics_match_sql.js can check the
dashboard's numbers against SQL.
"""
import json, os, re, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(os.path.join(ROOT, "data", "alcovia_demo.db"))
db.row_factory = sqlite3.Row
sql = "\n".join(l for l in open(os.path.join(ROOT, "sql", "gtm_kpis.sql")).read().splitlines() if not l.startswith("."))

stmts, buf = [], ""
for line in sql.splitlines(keepends=True):
    buf += line
    if sqlite3.complete_statement(buf):
        if any(not l.strip().startswith("--") and l.strip() for l in buf.splitlines()):
            stmts.append(buf)
        buf = ""

RANGES = [("2026-09-01", "2026-09-30"), ("2026-10-01", "2026-10-17"), ("2026-07-01", "2026-09-30"),
          ("2026-04-01", "2026-10-17"), ("2026-08-15", "2026-09-10")]
out = []
for d0, d1 in RANGES:
    as_of = min(d1, "2026-10-17")
    q = [re.sub(r"'2026-09-01' AS d0, '2026-09-30' AS d1", f"'{d0}' AS d0, '{d1}' AS d1", s)
         .replace("'2026-10-17' AS as_of", f"'{as_of}' AS as_of") for s in stmts]
    res = [[dict(r) for r in db.execute(s).fetchall()] for s in q]
    out.append({"d0": d0, "d1": d1, "revenue": res[0][0], "unpaid_count": len(res[1]), "renewals_due": len(res[2]),
                "funnel": res[3][0], "cpql": res[4][0], "campaigns": res[5]})
json.dump(out, open(os.path.join(ROOT, "tests", "sql_results.json"), "w"), indent=1)
print(f"saved {len(out)} ranges")
