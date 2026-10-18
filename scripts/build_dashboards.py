"""Inline data.js and metrics.js into each dashboard so it is one self-contained HTML file in dist/."""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
for name, out in (("gtm", "gtm-tracker.html"), ("student", "student-progress.html")):
    folder = os.path.join(ROOT, "dashboards", name)
    if not os.path.exists(os.path.join(folder, "index.html")):
        continue
    html = open(os.path.join(folder, "index.html")).read()
    def inline(m):
        return "<script>\n" + open(os.path.join(folder, m.group(1))).read().replace("</script", "<\\/script") + "\n</script>"
    html = re.sub(r'<script src="([a-z_]+\.js)"></script>', inline, html)
    html = html.replace('<link rel="stylesheet" href="../shared.css">', "<style>\n" + open(os.path.join(ROOT, "dashboards", "shared.css")).read() + "</style>")
    open(os.path.join(ROOT, "dist", out), "w").write(html)
    print(out, round(len(html) / 1024), "KB")
