"""
Run a .sql file against the demo database and print each result as a table.
Works without the sqlite3 command-line tool (lines starting with '.' are skipped).

  python3 scripts/run_sql.py sql/gtm_kpis.sql
  python3 scripts/run_sql.py sql/student_kpis.sql
"""
import os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = sqlite3.connect(os.path.join(ROOT, "data", "alcovia_demo.db"))
text = "\n".join(l for l in open(sys.argv[1]).read().splitlines() if not l.startswith("."))

def statements(sql):
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            yield buf.strip()
            buf = ""

def fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v):,}"
    if isinstance(v, int):
        return f"{v:,}"
    return "" if v is None else str(v)

n = 0
for st in statements(text):
    body = "\n".join(l for l in st.splitlines() if not l.strip().startswith("--")).strip()
    if not body:
        continue
    n += 1
    title = next((l.strip("- ").strip() for l in st.splitlines() if l.strip().startswith("-- Q")), f"Query {n}")
    cur = db.execute(st)
    cols = [c[0] for c in cur.description]
    data = [[fmt(v) for v in r] for r in cur.fetchall()]
    w = [max(len(c), *(len(r[i]) for r in data)) if data else len(c) for i, c in enumerate(cols)]
    print(f"\n## {title}  ({len(data)} rows)")
    print("  ".join(c.ljust(w[i]) for i, c in enumerate(cols)))
    for r in data[:25]:
        print("  ".join(v.ljust(w[i]) for i, v in enumerate(r)))
    if len(data) > 25:
        print(f"... {len(data) - 25} more rows")
