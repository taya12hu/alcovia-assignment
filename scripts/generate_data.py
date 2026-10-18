"""
Generate the SYNTHETIC dataset used by both dashboards.

Every name, number and payment here is made up. Nothing comes from Alcovia.
The generator is seeded, so it produces the same data every run.

Outputs
  data/alcovia_demo.db    SQLite database (schema/schema.sql + data)
  data/seed.sql           INSERT statements (to load into any SQL database)
  dashboards/*/data.js    compact JSON the dashboards read

Run:  python3 scripts/generate_data.py
"""
import json, math, os, random, sqlite3
from datetime import date, timedelta

R = random.Random(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = date(2026, 10, 17)          # "data as of" date for the demo
START = date(2026, 4, 1)            # start of academic year & of the GTM history
D = lambda d: d.isoformat() if d else None

def days(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)

def poisson(lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= R.random()
        if p <= L:
            return k
        k += 1

rows = {t: [] for t in [
    "landing_pages", "campaigns", "ad_creatives", "ad_daily", "leads", "students",
    "enrollments", "invoices", "workshops", "payments", "monthly_targets",
    "subjects", "chapters", "chapter_progress", "score_targets", "exam_results",
    "tasks", "focus_sessions", "quiz_attempts", "wearable_daily", "activities",
    "activity_participation", "roadmap_milestones"]}

# ---------------------------------------------------------------- marketing
LP = {  # id: (name, path, median load ms, bounce rate)
    "lp_program_v1": ("Program page v1", "/program", 3900, 0.63),
    "lp_program_v2": ("Program page v2 (quiz-led)", "/program-v2", 1700, 0.37),
    "lp_workshop":   ("Workshop booking page", "/workshop", 2400, 0.44),
}
for k, v in LP.items():
    rows["landing_pages"].append((k, v[0], v[1]))

# campaign id: name, objective, landing page, start, lead->qualified rate, audience size factor
CAMPAIGNS = {
    "cmp_prog_parents_ncr": ("Program | Parents, Delhi NCR", "program", "lp_program_v1", date(2026, 4, 1), 0.42, 0.55),
    "cmp_prog_career_anx":  ("Program | Career-anxiety hook", "program", "lp_program_v2", date(2026, 5, 15), 0.38, 1.0),
    "cmp_prog_lookalike":   ("Program | Lookalike of enrolled families", "program", "lp_program_v2", date(2026, 7, 1), 0.50, 1.3),
    "cmp_prog_broad_metro": ("Program | Broad metro India", "program", "lp_program_v1", date(2026, 4, 1), 0.16, 2.5),
    "cmp_ws_career_day":    ("Workshop | Career simulation day", "workshop", "lp_workshop", date(2026, 4, 1), 0, 0.7),
    "cmp_ws_parent_teen":   ("Workshop | Parent + teen invite", "workshop", "lp_workshop", date(2026, 8, 1), 0, 1.2),
}
# creative id: campaign, name, format, base CTR, launch date offset (days after campaign start), daily budget
CREATIVES = [
    ("cr_ncr_reel_dayinlife", "cmp_prog_parents_ncr", "Reel: a day in an Alcovian's week", "reel", 0.021, 0, 330),
    ("cr_ncr_static_boards",  "cmp_prog_parents_ncr", "Static: board-exam stress", "static", 0.011, 0, 200),
    ("cr_ncr_carousel_mentors", "cmp_prog_parents_ncr", "Carousel: meet the mentors", "carousel", 0.015, 60, 240),
    ("cr_anx_reel_whatnext",  "cmp_prog_career_anx", "Reel: 'What do I do after 12th?'", "reel", 0.024, 0, 360),
    ("cr_anx_static_quiz",    "cmp_prog_career_anx", "Static: 2-minute career quiz", "static", 0.017, 0, 260),
    ("cr_anx_reel_parentvoice", "cmp_prog_career_anx", "Reel: parent testimonial", "reel", 0.019, 75, 280),
    ("cr_lal_reel_podcast",   "cmp_prog_lookalike", "Reel: teen hosts a podcast", "reel", 0.026, 0, 380),
    ("cr_lal_carousel_roadmap", "cmp_prog_lookalike", "Carousel: a personal roadmap", "carousel", 0.018, 0, 260),
    ("cr_lal_static_results", "cmp_prog_lookalike", "Static: term results", "static", 0.009, 20, 180),
    ("cr_brd_static_generic", "cmp_prog_broad_metro", "Static: 'Future-ready teens'", "static", 0.008, 0, 300),
    ("cr_brd_reel_montage",   "cmp_prog_broad_metro", "Reel: workshop montage", "reel", 0.012, 0, 300),
    ("cr_brd_carousel_fees",  "cmp_prog_broad_metro", "Carousel: programme & fees", "carousel", 0.006, 40, 220),
    ("cr_ws_reel_simulation", "cmp_ws_career_day", "Reel: crisis simulation clip", "reel", 0.028, 0, 260),
    ("cr_ws_static_seats",    "cmp_ws_career_day", "Static: 'Only 30 seats'", "static", 0.013, 0, 160),
    ("cr_ws_carousel_speakers", "cmp_ws_career_day", "Carousel: this fortnight's speaker", "carousel", 0.020, 30, 200),
    ("cr_pt_reel_together",   "cmp_ws_parent_teen", "Reel: parent and teen solve a case", "reel", 0.022, 0, 240),
    ("cr_pt_static_weekend",  "cmp_ws_parent_teen", "Static: weekend plan", "static", 0.010, 0, 150),
    ("cr_pt_carousel_faq",    "cmp_ws_parent_teen", "Carousel: what happens on the day", "carousel", 0.014, 10, 170),
]
for cid, c in CAMPAIGNS.items():
    rows["campaigns"].append((cid, c[0], c[1], c[2], D(c[3])))
for cr in CREATIVES:
    rows["ad_creatives"].append((cr[0], cr[1], cr[2], cr[3]))

# fortnightly workshops (Saturdays)
workshops = []
TOPICS = ["Architecture", "Investment banking", "Game design", "Clinical psychology", "Product management",
          "Law", "Marine biology", "Journalism", "Aerospace", "Brand marketing", "Data science",
          "Film direction", "Urban planning", "Diplomacy", "Sports management", "Neuroscience", "Fashion design"]
wd, i = date(2026, 4, 11), 0
while wd <= date(2026, 11, 30):
    wid = f"ws_{wd.strftime('%Y%m%d')}"
    workshops.append({"id": wid, "on": wd, "title": f"Career simulation: {TOPICS[i % len(TOPICS)]}", "cap": 30, "sold": 0})
    wd += timedelta(days=14); i += 1

def next_workshop(d):
    for w in workshops:
        if w["on"] > d + timedelta(days=1) and w["sold"] < w["cap"]:
            return w
    return None

pay_seq = [0]
def pay_id():
    pay_seq[0] += 1
    return f"pay_{pay_seq[0]:06d}"

lead_seq = [0]
leads = []
def new_lead(created, source, campaign=None, creative=None):
    lead_seq[0] += 1
    L = {"lead_id": f"CU-{100000 + lead_seq[0]}", "phone_hash": f"h{R.getrandbits(48):012x}",
         "created_on": created, "source": source, "campaign_id": campaign, "creative_id": creative}
    leads.append(L)
    return L

CPM = 185.0
for cr in CREATIVES:
    crid, cmp_id, _, _, base_ctr, offset, budget = cr
    camp = CAMPAIGNS[cmp_id]
    launch = camp[3] + timedelta(days=offset)
    lp = LP[camp[2]]
    for d in days(launch, TODAY):
        age = (d - launch).days
        spend = round(budget * R.uniform(0.8, 1.2), 2)
        imp = int(spend / (CPM * R.uniform(0.85, 1.15)) * 1000)
        ctr = base_ctr * math.exp(-age / 160.0) * R.uniform(0.85, 1.15)   # creative fatigue
        clicks = max(0, int(round(imp * ctr)))
        freq = round(min(5.2, 1.15 + (age / 7.0) * 0.11 / camp[5]) * R.uniform(0.96, 1.04), 2)
        lpv = int(round(clicks * R.uniform(0.78, 0.88)))
        bounces = int(round(lpv * min(0.95, lp[3] * R.uniform(0.9, 1.1))))
        load = int(lp[2] * R.uniform(0.85, 1.2))
        rows["ad_daily"].append((D(d), crid, spend, imp, clicks, freq, lpv, bounces, load))
        engaged = lpv - bounces
        if camp[1] == "program":
            for _ in range(poisson(engaged * 0.036)):
                new_lead(d, "meta", cmp_id, crid)
        else:
            for _ in range(poisson(engaged * 0.075)):
                w = next_workshop(d)
                if w:
                    w["sold"] += 1
                    rows["payments"].append((pay_id(), D(d), 3999.0, "workshop", None, w["id"], None, crid))

# organic + referral program leads
for d in days(START, TODAY):
    for _ in range(poisson(0.75)):
        new_lead(d, "organic")
    for _ in range(poisson(0.25)):
        new_lead(d, "referral")
# a few walk-in workshop seats per workshop (no ad)
for w in workshops:
    if w["on"] <= TODAY + timedelta(days=14):
        for _ in range(R.randint(2, 5)):
            if w["sold"] < w["cap"]:
                w["sold"] += 1
                paid = w["on"] - timedelta(days=R.randint(1, 10))
                if paid <= TODAY:
                    rows["payments"].append((pay_id(), D(paid), 3999.0, "workshop", None, w["id"], None, None))

for w in workshops:
    rows["workshops"].append((w["id"], D(w["on"]), w["title"], 3999.0, w["cap"]))

# ---------------------------------------------------------------- funnel
QUAL = {"organic": 0.58, "referral": 0.74}
CONV = {"meta": 0.50, "organic": 0.58, "referral": 0.66}
converted = []
leads.sort(key=lambda L: L["created_on"])
for L in leads:
    c = L["created_on"]
    q_rate = CAMPAIGNS[L["campaign_id"]][4] if L["source"] == "meta" else QUAL[L["source"]]
    L.update(qualified_on=None, discovery_booked_on=None, discovery_showed=None, ambition_interview_on=None,
             architect_session_on=None, outcome="open", outcome_on=None, drop_reason=None)
    def drop(on, why):
        if on <= TODAY:
            L["outcome"], L["outcome_on"], L["drop_reason"] = "dropped", on, why
    qd = c + timedelta(days=R.randint(0, 2))
    if qd > TODAY:
        continue
    if R.random() > q_rate:
        drop(qd, "not a fit"); continue
    L["qualified_on"] = qd
    bd = qd + timedelta(days=R.randint(1, 4))
    if R.random() > 0.82:
        drop(bd + timedelta(days=5), "never booked a call"); continue
    L["discovery_booked_on"] = bd           # = date of the scheduled call
    if bd > TODAY:
        continue
    showed = R.random() < 0.69
    L["discovery_showed"] = 1 if showed else 0
    if not showed:
        drop(bd + timedelta(days=3), "no-show"); continue
    ad = bd + timedelta(days=R.randint(3, 8))
    if ad > TODAY:
        continue
    if R.random() > 0.74:
        drop(ad, "teen not interested"); continue
    L["ambition_interview_on"] = ad
    xd = ad + timedelta(days=R.randint(4, 10))
    if xd > TODAY:
        continue
    if R.random() > 0.81:
        drop(xd, "parents did not attend"); continue
    L["architect_session_on"] = xd
    od = xd + timedelta(days=R.randint(1, 7))
    if od > TODAY:
        continue
    if R.random() < CONV[L["source"]]:
        L["outcome"], L["outcome_on"] = "converted", od
        converted.append(L)
    else:
        drop(od, R.choice(["price", "timing", "chose coaching instead"]))

for L in leads:
    rows["leads"].append((L["lead_id"], L["phone_hash"], D(L["created_on"]), L["source"], L["campaign_id"],
                          L["creative_id"], D(L["qualified_on"]), D(L["discovery_booked_on"]), L["discovery_showed"],
                          D(L["ambition_interview_on"]), D(L["architect_session_on"]), L["outcome"],
                          D(L["outcome_on"]), L["drop_reason"]))

# ---------------------------------------------------------------- customers & money
FIRST = ["Aarav", "Diya", "Kabir", "Myra", "Vihaan", "Anaya", "Reyansh", "Saanvi", "Arjun", "Ira", "Advik", "Kiara",
         "Ishaan", "Aadhya", "Shaurya", "Navya", "Rudra", "Tara", "Ayaan", "Zoya", "Dhruv", "Meher", "Vivaan", "Riya",
         "Krish", "Anvi", "Atharv", "Siya", "Yuvan", "Pari", "Rehaan", "Avni", "Neil", "Trisha", "Om", "Jiya",
         "Arnav", "Mishka", "Veer", "Ahana", "Laksh", "Inaya", "Parth", "Sana", "Hridaan", "Kavya", "Ved", "Prisha"]
R.shuffle(FIRST)
PRICE = {"trial_3m": 24999.0, "full_program": 149999.0}
students, enrollments = [], []
used_names = set()
stu_seq, enr_seq, inv_seq = [0], [0], [0]

def add_student(joined, lead_id):
    stu_seq[0] += 1
    while True:   # unique synthetic display names
        n = FIRST[(stu_seq[0] - 1) % len(FIRST)] + " " + "ABCDGJKMNPRSTV"[R.randint(0, 13)] + "."
        if n not in used_names:
            used_names.add(n); break
    s = {"id": f"stu_{stu_seq[0]:03d}", "name": n, "grade": R.choice([8, 9, 9, 10, 10, 11]), "joined": joined, "lead": lead_id}
    students.append(s)
    return s

def add_enrollment(stu, product, start, renewal_of=None):
    enr_seq[0] += 1
    e = {"id": f"enr_{enr_seq[0]:04d}", "stu": stu["id"], "product": product, "start": start,
         "end": start + timedelta(days=90 if product == "trial_3m" else 365), "price": PRICE[product], "renewal_of": renewal_of}
    enrollments.append(e)
    # invoice + payment
    inv_seq[0] += 1
    iid = f"INV-{2600 + inv_seq[0]}"
    issued = start
    status, paid_on = "unpaid", None
    if R.random() < (1.0 if start < START else 0.9):
        pd = issued + timedelta(days=min(R.choice([0, 0, 1, 2, 3, 5, 8, 12, 18]), 30))
        if pd <= TODAY:
            status, paid_on = "paid", pd
    if issued <= TODAY:
        rows["invoices"].append((iid, e["id"], D(issued), D(issued + timedelta(days=7)), e["price"], status))
        if paid_on:
            rows["payments"].append((pay_id(), D(paid_on), e["price"], "program", iid, None, None, None))
    return e

# a base of families who joined before April (full programme)
for k in range(9):
    s = add_student(date(2026, 1, 5) + timedelta(days=k * 9), None)
    add_enrollment(s, "full_program", s["joined"])
for L in sorted(converted, key=lambda L: L["outcome_on"]):
    s = add_student(L["outcome_on"], L["lead_id"])
    add_enrollment(s, "trial_3m" if R.random() < 0.64 else "full_program", L["outcome_on"])
# renewals: trials that ended on or before TODAY convert to full programme ~47% of the time
for e in list(enrollments):
    if e["product"] == "trial_3m" and e["end"] <= TODAY and R.random() < 0.47:
        stu = next(s for s in students if s["id"] == e["stu"])
        add_enrollment(stu, "full_program", e["end"], e["id"])

for s in students:
    rows["students"].append((s["id"], s["lead"], s["name"], s["grade"], D(s["joined"])))
for e in enrollments:
    rows["enrollments"].append((e["id"], e["stu"], e["product"], D(e["start"]), D(e["end"]), e["price"], e["renewal_of"]))

TARGETS = {"2026-04": (450000, 5), "2026-05": (550000, 6), "2026-06": (650000, 6), "2026-07": (750000, 7),
           "2026-08": (900000, 8), "2026-09": (1100000, 9), "2026-10": (1200000, 10), "2026-11": (1300000, 11),
           "2026-12": (1400000, 12)}
for m, (r, n) in TARGETS.items():
    rows["monthly_targets"].append((m, r, n))

# ---------------------------------------------------------------- student progress
active_ids = sorted({e["stu"] for e in enrollments if e["start"] <= TODAY < e["end"]})
active = [s for s in students if s["id"] in active_ids]

SYLLABUS = {
    "MATH": ("Mathematics", ["Real Numbers", "Polynomials", "Pair of Linear Equations", "Quadratic Equations",
             "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Introduction to Trigonometry",
             "Applications of Trigonometry", "Circles", "Areas Related to Circles", "Surface Areas and Volumes",
             "Statistics", "Probability"]),
    "SCI": ("Science", ["Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals",
            "Carbon and its Compounds", "Life Processes", "Control and Coordination", "How do Organisms Reproduce?",
            "Heredity", "Light: Reflection and Refraction", "The Human Eye", "Electricity",
            "Magnetic Effects of Electric Current", "Our Environment"]),
    "SST": ("Social Science", ["Rise of Nationalism in Europe", "Nationalism in India", "The Making of a Global World",
            "The Age of Industrialisation", "Print Culture and the Modern World", "Resources and Development",
            "Forest and Wildlife Resources", "Water Resources", "Agriculture", "Minerals and Energy Resources",
            "Manufacturing Industries", "Power Sharing"]),
    "ENG": ("English", ["A Letter to God", "Nelson Mandela", "Two Stories about Flying", "From the Diary of Anne Frank",
            "Glimpses of India", "Mijbil the Otter", "Madam Rides the Bus", "The Sermon at Benares", "The Proposal",
            "Grammar and Writing"]),
}
for sid, (name, chs) in SYLLABUS.items():
    rows["subjects"].append((sid, name))
    for i, ch in enumerate(chs, 1):
        rows["chapters"].append((f"{sid}_{i:02d}", sid, i, ch))

elapsed = (TODAY - START).days / 365.0
WINDOW_START = TODAY - timedelta(days=59)          # last 60 days of app activity
profiles = {}
for idx, s in enumerate(active):
    # 5 heavy app users, 6 occasional, rest light, matching the brief's adoption picture
    eng = 0.9 if idx < 5 else (0.45 if idx < 11 else 0.12)
    p = {"dil": R.uniform(0.35, 1.0), "abil": R.uniform(0.6, 0.94), "eng": eng,
         "aff": {k: R.uniform(-0.1, 0.1) for k in SYLLABUS}}
    profiles[s["id"]] = p
    for sid, (_, chs) in SYLLABUS.items():
        n_started = min(len(chs), int(round(len(chs) * elapsed * (0.85 + p["dil"] * 0.75) + R.uniform(-1, 1))))
        acc_base = p["abil"] + p["aff"][sid]
        for i in range(1, n_started + 1):
            t = START + timedelta(days=int(i / max(n_started, 1) * (TODAY - START).days * 0.93 * R.uniform(0.9, 1.0)))
            t = min(t, TODAY - timedelta(days=2))
            read_on, notes_on = t, None
            pr_on = pr_acc = pp_on = pp_acc = None
            recent = (TODAY - t).days < 20
            if R.random() < 0.72 + 0.28 * p["dil"]:
                notes_on = t + timedelta(days=R.randint(1, 4))
                if R.random() < (0.6 + 0.4 * p["dil"]) * (0.5 if recent else 1):
                    pr_on = notes_on + timedelta(days=R.randint(2, 6))
                    pr_acc = round(max(30, min(99, 100 * (acc_base + R.gauss(0, 0.08)))))
                    if pr_acc >= 70 and R.random() < (0.35 + 0.6 * p["dil"]) * (0.4 if recent else 1):
                        pp_on = pr_on + timedelta(days=R.randint(3, 12))
                        pp_acc = round(max(30, min(99, pr_acc + R.gauss(-3, 7))))
            clip = lambda d: d if d is None or d <= TODAY else None
            pr_on = clip(pr_on); pp_on = clip(pp_on) if pr_on else None
            if pr_on is None: pr_acc = None
            if pp_on is None: pp_acc = None
            rows["chapter_progress"].append((s["id"], f"{sid}_{i:02d}", D(read_on), D(clip(notes_on)), D(pr_on), pr_acc, D(pp_on), pp_acc))
        tgt = round(min(95, 100 * acc_base + 1) / 5) * 5
        for et, adj in (("formative", 5), ("unit_test", 0), ("half_yearly", -3)):
            rows["score_targets"].append((s["id"], sid, et, min(98, tgt + adj)))
        if s["joined"] < date(2026, 7, 10):
            rows["exam_results"].append((s["id"], sid, "unit_test", "2026-07-14", round(max(35, min(99, 100 * acc_base + R.gauss(-2, 7))))))
        if s["joined"] < date(2026, 9, 15):
            rows["exam_results"].append((s["id"], sid, "half_yearly", "2026-09-22", round(max(35, min(99, 100 * acc_base + R.gauss(-1, 7))))))

    tseq = 0
    for d in days(max(WINDOW_START, s["joined"]), TODAY + timedelta(days=3)):
        for _ in range(poisson(1.3)):
            tseq += 1
            due = d + timedelta(days=R.choice([0, 1, 2]))
            est = R.choice([20, 30, 30, 45, 60])
            done = done_on = actual = None
            if due <= TODAY or R.random() < 0.3:
                if R.random() < 0.35 + 0.6 * p["dil"]:
                    late = 0 if R.random() < 0.55 + 0.4 * p["dil"] else R.randint(1, 3)
                    done_on = due + timedelta(days=late)
                    if done_on > TODAY: done_on = None
                    if done_on and R.random() < 0.3 + 0.6 * p["eng"]:
                        actual = max(5, int(est * R.uniform(0.7, 1.0 + 0.9 * (1 - p["dil"]))))
            rows["tasks"].append((f"tsk_{s['id'][4:]}_{tseq:04d}", s["id"], D(due), D(done_on), est, actual,
                                  "advisor" if R.random() < 0.4 else "self"))
    fseq = 0
    for d in days(max(WINDOW_START, s["joined"]), TODAY):
        n = poisson(1.25 if p["eng"] > 0.8 else (0.25 if p["eng"] > 0.4 else 0.03))
        for _ in range(n):
            fseq += 1
            comp = R.random() < 0.82
            mins = R.choice([25, 25, 30, 45, 50]) if comp else R.randint(4, 18)
            rows["focus_sessions"].append((f"fs_{s['id'][4:]}_{fseq:04d}", s["id"], D(d), mins, 1 if comp else 0))
        if R.random() < 0.25 + 0.7 * p["eng"] * 0.9 + 0.1:
            score = sum(1 for _ in range(10) if R.random() < 0.35 + 0.5 * p["abil"])
            rows["quiz_attempts"].append((s["id"], D(d), score, 10))

# three students with a connected wearable (parental consent given)
for s, dev in zip([a for a in active][:3], ["whoop", "apple", "garmin"]):
    for d in days(WINDOW_START, TODAY):
        rows["wearable_daily"].append((s["id"], D(d), dev, int(R.gauss(48, 18)) if R.random() > 0.05 else None,
                                       round(R.gauss(7.1, 0.8), 1), round(min(99, max(20, R.gauss(64, 14))))))

# ---------------------------------------------------------------- programme activities
act_seq = [0]
def add_activity(atype, planned, title, invitees, held_p, rating_mu, outcome_mu, follow_p):
    act_seq[0] += 1
    aid = f"act_{act_seq[0]:04d}"
    held = planned if (R.random() < held_p and planned <= TODAY) else None
    rows["activities"].append((aid, atype, D(planned), D(held), title))
    if held:
        for s in invitees:
            pe = profiles.get(s["id"], {"eng": 0.5, "dil": 0.6})
            att = R.random() < 0.55 + 0.4 * max(pe["eng"], pe["dil"])
            rating = max(1, min(5, int(round(R.gauss(rating_mu, 0.7))))) if att and R.random() < 0.85 else None
            outc = round(max(10, min(100, R.gauss(outcome_mu + 15 * (pe["dil"] - 0.6), 12)))) if att else None
            fu = (1 if R.random() < follow_p else 0) if att else None
            rows["activity_participation"].append((aid, s["id"], 1, 1 if att else 0, rating, outc, fu))

def members(on):
    return [s for s in active if s["joined"] <= on]

for w in workshops:
    if w["on"] <= TODAY + timedelta(days=30):
        add_activity("career_workshop", w["on"], w["title"], members(w["on"]), 0.97, 4.2, 66, 0.55)
month = START
while month <= TODAY:
    nxt = date(month.year + (month.month // 12), month.month % 12 + 1, 1)
    mem = members(month + timedelta(days=14))
    pods = [mem[i:i + 5] for i in range(0, len(mem), 5)]
    for k, pod in enumerate(pods):
        add_activity("pod_session", month + timedelta(days=17 + k), f"Pod {k + 1}: {['Dreams','Aspirations','Fears','Vulnerabilities'][month.month % 4]}", pod, 0.86, 4.4, 70, 0.6)
    for k in range(0, len(mem) - 1, 2):
        add_activity("peer_session", month + timedelta(days=8 + k % 10), "Peer learning session", mem[k:k + 2], 0.72, 4.0, 62, 0.5)
    for s in mem:
        add_activity("mentor_call", month + timedelta(days=R.randint(5, 25)), f"Mentor call: {s['name']}", [s], 0.8, 4.5, 72, 0.45)
    shoot = R.sample(mem, min(8, len(mem)))
    add_activity("personal_branding", month + timedelta(days=24), "Personal branding shoot", shoot, 0.9, 3.8, 58, 0.4)
    month = nxt
for qtr_on, label in ((date(2026, 6, 20), "Q1"), (date(2026, 9, 19), "Q2")):
    mem = members(qtr_on)
    add_activity("podcast", qtr_on, f"{label} podcast shoot", R.sample(mem, min(6, len(mem))), 0.9, 4.7, 74, 0.5)
    add_activity("competition_prep", qtr_on - timedelta(days=10), f"{label} competition prep", R.sample(mem, min(5, len(mem))), 1.0, 4.1, 64, 0.6)
    add_activity("parent_child", qtr_on - timedelta(days=30), f"{label} parent-child workshop", mem, 0.95, 4.6, 70, 0.5)
    add_activity("out_of_city", qtr_on + timedelta(days=7), f"{label} out-of-city experience", mem, 0.75 if label == "Q2" else 1.0, 4.8, 68, 0.5)
# next quarter's activities, planned but not yet due
add_activity("podcast", date(2026, 12, 12), "Q3 podcast shoot", [], 1.0, 4.7, 74, 0.5)

mseq = 0
for s in active:
    p = profiles[s["id"]]
    m = date(s["joined"].year, s["joined"].month, 1)
    while m <= date(2026, 11, 1):
        due = m + timedelta(days=27)
        for track, title, prob in (("personal", "Monthly personal milestone", 0.4 + 0.5 * p["dil"]),
                                   ("academic", "Monthly syllabus checkpoint", 0.3 + 0.6 * p["dil"])):
            mseq += 1
            done = due - timedelta(days=R.randint(0, 6)) if (due <= TODAY and R.random() < prob) else None
            rows["roadmap_milestones"].append((f"ms_{mseq:05d}", s["id"], track, D(due), D(done), title))
        if m.month in (6, 9, 12):
            mseq += 1
            done = due if (due <= TODAY and R.random() < 0.5 + 0.4 * p["dil"]) else None
            rows["roadmap_milestones"].append((f"ms_{mseq:05d}", s["id"], "career", D(due), D(done), "Career roadmap step"))
        m = date(m.year + (m.month // 12), m.month % 12 + 1, 1)

# ---------------------------------------------------------------- write SQLite + seed.sql
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
db_path = os.path.join(ROOT, "data", "alcovia_demo.db")
if os.path.exists(db_path):
    os.remove(db_path)
con = sqlite3.connect(db_path)
con.executescript(open(os.path.join(ROOT, "schema", "schema.sql")).read())
ORDER = ["landing_pages", "campaigns", "ad_creatives", "ad_daily", "leads", "students", "enrollments",
         "invoices", "workshops", "payments", "monthly_targets", "subjects", "chapters", "chapter_progress",
         "score_targets", "exam_results", "tasks", "focus_sessions", "quiz_attempts", "wearable_daily",
         "activities", "activity_participation", "roadmap_milestones"]
def lit(v):
    if v is None: return "NULL"
    if isinstance(v, (int, float)): return repr(v)
    return "'" + str(v).replace("'", "''") + "'"
with open(os.path.join(ROOT, "data", "seed.sql"), "w") as f:
    f.write("-- SYNTHETIC demo data generated by scripts/generate_data.py. Not real Alcovia data.\nBEGIN;\n")
    for t in ORDER:
        if not rows[t]: continue
        ph = ",".join("?" * len(rows[t][0]))
        con.executemany(f"INSERT INTO {t} VALUES ({ph})", rows[t])
        for r in rows[t]:
            f.write(f"INSERT INTO {t} VALUES ({','.join(lit(v) for v in r)});\n")
    f.write("COMMIT;\n")
con.commit()

# ---------------------------------------------------------------- dashboard data (compact, column-oriented)
def table(t):
    cur = con.execute(f"SELECT * FROM {t}")
    cols = [c[0] for c in cur.description]
    return {"cols": cols, "rows": cur.fetchall()}

gtm = {"asOf": D(TODAY), "synthetic": True}
for t in ["landing_pages", "campaigns", "ad_creatives", "ad_daily", "leads", "students", "enrollments",
          "invoices", "workshops", "payments", "monthly_targets"]:
    gtm[t] = table(t)
stu = {"asOf": D(TODAY), "synthetic": True, "activeStudents": active_ids}
for t in ["students", "enrollments", "subjects", "chapters", "chapter_progress", "score_targets", "exam_results",
          "tasks", "focus_sessions", "quiz_attempts", "wearable_daily", "activities", "activity_participation",
          "roadmap_milestones"]:
    stu[t] = table(t)
for name, obj in (("gtm", gtm), ("student", stu)):
    out = os.path.join(ROOT, "dashboards", name)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "data.js"), "w") as f:
        f.write("/* SYNTHETIC demo data. Generated by scripts/generate_data.py */\nwindow.DATA=" +
                json.dumps(obj, separators=(",", ":")) + ";\n")

for t in ORDER:
    print(f"{t:24s}{len(rows[t]):6d}")
print("active students:", len(active_ids))
