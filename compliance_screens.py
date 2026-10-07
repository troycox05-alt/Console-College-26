"""
compliance_screens.py — Compliance & Integrity: what's happening, and what you can do about it.

  [1] Cases          every investigation involving the program (and the ones only you know about)
  [2] Academics      the watch list, the team's APR, and what academic support is doing
  [3] Compliance office   its strength, what you're spending, and what it buys you
  [4] Sanctions & history probation, bans, scholarship cuts, vacated wins, the record
  [5] League wire    every headline in the country: reports, inquiries, rulings, arrests, APRs
  [6] Under investigation   every open case in the country, worst first
  [7] APR board      who's safe, who's close, who's below the line
  [A] Internal audit pay an outside firm to look (Coach Career / Athletic Director)

Looking never changes anything, except the audit and the budget tiers, which cost real money.
"""
import textwrap

import compliance as cp
from ui import C, WIDTH, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

LVL_COLOR = {1: C.BRED, 2: C.BYELLOW, 3: C.GRAY}
KIND_COLOR = {"ruling": C.BRED, "report": C.BRED, "allegations": C.BRED, "inquiry": C.BYELLOW, "self": C.BCYAN,
              "cleared": C.BGREEN, "appeal": C.BYELLOW, "incident": C.BMAGENTA, "academic": C.BYELLOW, "apr": C.BYELLOW}
STAGES = ("rumor", "inquiry", "allegations", "ruled")


def _owner(league):
    return cp.mine(league)


def _focus(league):
    me = _owner(league)
    if me is not None:
        return me, True
    import dashboard
    return dashboard.focus_team(league), False


def _wrap(text, w=WIDTH - 8, indent="   "):
    for ln in textwrap.wrap(text, w):
        print(indent + ln)


def _money(x):
    return cp._money(x)


def _sanction_line(team, league):
    s = getattr(team, "sanctions", None)
    if not s or s.get("until", 0) < league.year:
        return paint("none", C.BGREEN)
    bits = []
    bans = [b for b in (s.get("bans") or ([s["ban"]] if s.get("ban") else [])) if b >= league.year]
    if bans:
        bits.append("postseason ban " + ", ".join(str(b) for b in sorted(set(bans))))
    if s.get("probation_until") and s["probation_until"] >= league.year:
        bits.append(f"probation through {s['probation_until']}")
    if s.get("recruit_mult", 1.0) < 1.0:
        bits.append(f"recruiting cut {int((1 - s['recruit_mult']) * 100)}%")
    cut = cp.class_cut(team, league)
    if cut:
        bits.append(f"{cut} fewer scholarships this class")
    return paint("; ".join(bits) or f"through {s.get('until')}", C.BRED)


def _apr_line(team):
    a = cp.apr_of(team)
    if a is None:
        return paint("not yet measured", C.GRAY)
    col = C.BGREEN if a >= 950 else C.BYELLOW if a >= cp.APR_LINE else C.BRED
    tag = "safe" if a >= 950 else "near the line" if a >= cp.APR_LINE else f"BELOW {cp.APR_LINE}"
    return paint(f"{a}", col, C.BOLD) + paint(f"  ({tag})", C.GRAY)


# ═══ Hub ════════════════════════════════════════════════════════════════════

def hub(league):
    if not cp.active(league):
        clear()
        print(title_bar("COMPLIANCE & INTEGRITY"))
        print(paint("\n   The 2026 season is the first the CAB watches. Nothing has happened yet.", C.GRAY))
        pause()
        return
    team, own = _focus(league)
    while True:
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"COMPLIANCE & INTEGRITY  ·  {team.school.upper()}", color))
        s = cp._tables_ok(cp.st(team))
        pub = cp.public_cases(league, team)
        secrets = [c for c in cp.hidden_cases(league, team) if c["user"]] if own else []
        print()
        print(section("WHERE THE PROGRAM STANDS", color))
        if own:
            tier = cp.OFFICE_TIER[s["tier"]][2]
            print(f"   {paint('Compliance office', C.GRAY)}  {cp.office_word(cp.office_eff(team))}  "
                  f"{paint('(' + tier + ' budget)', C.GRAY)}")
        print(f"   {paint('Integrity', C.GRAY)}          {cp.rep_word(cp.rep(team))}")
        print(f"   {paint('APR', C.GRAY)}                {_apr_line(team)}")
        print(f"   {paint('Sanctions', C.GRAY)}          {_sanction_line(team, league)}")
        n_watch = len(cp.watch_list(team))
        print(f"   {paint('Academic watch', C.GRAY)}     {n_watch} player{'s' if n_watch != 1 else ''}")
        line = f"{len(pub)} open" if pub else "none"
        if secrets:
            line += paint(f"  ·  {len(secrets)} only you know about", C.BYELLOW)
        print(f"   {paint('Cases', C.GRAY)}              {line}")
        recent = cp.recent_news(league, 4, school=team.school)
        if recent:
            print()
            print(section("RECENTLY", color))
            for n in recent:
                when = "Wk %2d" % n["week"] if n["week"] < 18 else "offs."
                print(f"   {paint(when, C.GRAY)}  "
                      f"{paint(truncate(n['text'], WIDTH - 16), KIND_COLOR.get(n['kind'], C.BWHITE))}")
        print(rule())
        acts = ["[1] cases", "[2] academics"]
        if own:
            acts += ["[3] compliance office", "[4] sanctions & history", "[A] internal audit"]
        else:
            acts += ["[4] sanctions & history"]
        acts += ["[5] league wire", "[6] under investigation", "[7] APR board", "[B] back"]
        print("   " + "   ".join(acts))
        ch = ask("Select:").strip().lower()
        if ch in ("", "b"):
            return
        if ch == "1":
            cases_screen(league, team, own)
        elif ch == "2":
            academics_screen(league, team, own)
        elif ch == "3" and own:
            office_screen(league, team)
        elif ch == "4":
            history_screen(league, team)
        elif ch == "5":
            wire(league)
        elif ch == "6":
            investigations(league)
        elif ch == "7":
            apr_board(league)
        elif ch == "a" and own:
            audit_screen(league, team)


# ═══ Cases ══════════════════════════════════════════════════════════════════

def _case_row(i, c):
    lvl = paint(pad(cp.LEVEL_WORD[c["level"]], 10), LVL_COLOR[c["level"]], C.BOLD)
    kind = pad(cp.KINDS[c["kind"]]["label"], 24)
    stage = pad(cp.stage_label(c), 22)
    age = paint(f"{c['age']} wk", C.GRAY)
    return f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {lvl}{kind}{stage}{age}"


def cases_screen(league, team, own):
    while True:
        clear()
        print(title_bar(f"CASES  ·  {team.school.upper()}", league.conference_color(team.conference)))
        rows = [c for c in cp.cases(league, team.school) if not c["closed"] and (c["status"] != "hidden" or (own and c["user"]))]
        done = [c for c in cp.cases(league, team.school) if c["closed"] and c["status"] != "hidden"][-6:]
        print()
        if not rows:
            print(paint("   Nothing open.", C.GRAY))
        for i, c in enumerate(rows, 1):
            print(_case_row(i, c))
        if done:
            print()
            print(section("CLOSED", C.GRAY))
            for c in reversed(done):
                print(f"   {paint(pad(str(c['year']), 6), C.GRAY)}{pad(cp.LEVEL_WORD[c['level']], 11)}"
                      f"{pad(cp.KINDS[c['kind']]['label'], 24)}{paint(truncate(c.get('outcome') or 'closed', 44), C.GRAY)}")
        print(rule())
        ch = ask("Open # (Enter = back):").strip().lower()
        if ch in ("", "b"):
            return
        if ch.isdigit() and 1 <= int(ch) <= len(rows):
            case_screen(league, team, rows[int(ch) - 1], own)


def _timeline(c):
    order = ["hidden", "rumor", "inquiry", "allegations", "ruled"]
    cur = order.index(c["status"]) if c["status"] in order else (4 if c["closed"] else 0)
    if c["status"] == "appeal":
        cur = 4
    labels = ("undiscovered", "reports", "inquiry", "allegations", "ruling")
    out = []
    for i, lab in enumerate(labels):
        if i < cur:
            out.append(paint("✓ " + lab, C.BGREEN))
        elif i == cur and not c["closed"]:
            out.append(paint("● " + lab, C.BYELLOW, C.BOLD))
        elif i == cur:
            out.append(paint("✓ " + lab, C.BGREEN))
        else:
            out.append(paint("○ " + lab, C.GRAY))
    return "  ".join(out)


def case_screen(league, team, c, own):
    msg = ""
    while True:
        clear()
        print(title_bar(f"CASE #{c['id']}  ·  {team.school.upper()}", league.conference_color(team.conference)))
        print()
        lvl = cp.LEVEL_WORD[c["level"]]
        print(f"   {paint(lvl, LVL_COLOR[c['level']], C.BOLD)} {paint('(' + cp.LEVEL_BLURB[c['level']] + ')', C.GRAY)}  ·  "
              f"{cp.KINDS[c['kind']]['label']}")
        print()
        _wrap(c["text"][0].upper() + c["text"][1:] + ".")
        print()
        print("   " + _timeline(c))
        print()
        facts = []
        if c["how"]:
            facts.append(("Came out", {"report": "a media report", "whistle": "a whistleblower", "tip": "a tip to the CAB",
                                       "self": "your self-report", "audit": "your internal audit"}.get(c["how"], c["how"])))
        if c["status"] != "hidden":
            facts.append(("Cooperation", "full" if c["coop"] >= 2 else "good" if c["coop"] == 1 else "standard" if c["coop"] == 0
                          else "grudging" if c["coop"] == -1 else "stonewalling"))
        if c["counsel"]:
            facts.append(("Outside counsel", "retained"))
        if c["self_imposed"]:
            facts.append(("Self-imposed penalties", "announced"))
        if c["contest"] in ("pending", "won", "lost"):
            facts.append(("Allegations", {"pending": "being contested", "won": "contested and won", "lost": "contested and lost"}[c["contest"]]))
        if c["cover"] and own:
            facts.append(("Cover-up", paint("yes: if it comes out, it goes up a level", C.BRED)))
        if c["pnames"] and own:
            facts.append(("Players involved", ", ".join(c["pnames"][:4])))
        for k, v in facts:
            print(f"   {paint(pad(k, 24), C.GRAY)}{v}")
        if c["ruling"]:
            print()
            print(section("THE RULING", C.BRED))
            for ln in c["ruling"]["lines"]:
                print("   • " + ln)
        if c["outcome"] and not c["ruling"]:
            print()
            _wrap(c["outcome"])
        if msg:
            print()
            for ln in msg:
                _wrap(ln)
            msg = ""
        acts = []
        if own and not c["closed"]:
            if c["status"] == "hidden" and c["user"]:
                acts.append(("R", "come clean (self-report)"))
            if c["status"] in ("inquiry", "allegations") and not c["counsel"]:
                acts.append(("L", "hire outside counsel"))
            if c["status"] in ("inquiry", "allegations") and not c["self_imposed"]:
                acts.append(("I", "announce penalties on ourselves"))
            if c["status"] == "ruled" and c["level"] <= 2 and not c.get("appeal_done") and not c["appeal"]:
                acts.append(("A", "appeal"))
        print(rule())
        print("   " + "   ".join(f"[{k}] {lab}" for k, lab in acts + [("B", "back")]))
        ch = ask("Select:").strip().lower()
        if ch in ("", "b"):
            return
        ops = {"r": {"op": "report", "case": c["id"]}, "l": {"op": "counsel", "case": c["id"]},
               "i": {"op": "self_impose", "case": c["id"]}, "a": {"op": "appeal", "case": c["id"]}}
        if ch in ops and any(k.lower() == ch for k, _ in acts):
            msg = cp.apply_fx(league, team, ops[ch]) or ["Done."]


# ═══ Academics ══════════════════════════════════════════════════════════════

def academics_screen(league, team, own):
    msg = ""
    while True:
        clear()
        print(title_bar(f"ACADEMICS  ·  {team.school.upper()}", league.conference_color(team.conference)))
        s = cp._tables_ok(cp.st(team))
        print()
        acad = team.ratings.get("academics", 50)
        print(f"   {paint('The school', C.GRAY)}   {'elite' if acad >= 80 else 'strong' if acad >= 65 else 'solid' if acad >= 50 else 'demanding for athletes' if acad >= 35 else 'a struggle'}"
              f" academically   ·   {paint('APR', C.GRAY)} {_apr_line(team)}")
        if own:
            print(f"   {paint('Academic support', C.GRAY)}  {cp.SUPPORT_TIER[s['support']][2]}")
        hist = sorted(s["apr"].items())[-5:]
        if hist:
            print(f"   {paint('APR history', C.GRAY)}  " + "  ".join(f"{y}: {a}" for y, a in hist))
        print()
        print(section("ACADEMIC WATCH LIST", C.BYELLOW))
        watch = cp.watch_list(team, 2.45)
        if not watch:
            print(paint("   Nobody's in trouble.", C.GRAY))
        for p in watch[:14]:
            g = cp.gpa(p)
            held = paint("  OUT", C.BRED) if getattr(p, "suspended", False) and (p.inj_desc or "").startswith("academ") else ""
            print(f"   {pad(p.position, 4)}{pad(p.name, 22)}{pad(p.class_label, 7)}"
                  f"{paint(pad(cp.gpa_word(g), 12), cp.gpa_color(g))}{paint(f'OVR {p.overall}', C.GRAY)}{held}")
        if len(watch) > 14:
            print(paint(f"   … and {len(watch) - 14} more.", C.GRAY))
        if msg:
            print()
            _wrap(msg)
            msg = ""
        print(rule())
        acts = ["[B] back"]
        if own:
            acts.insert(0, "[S] academic support level")
        print("   " + "   ".join(acts))
        ch = ask("Select:").strip().lower()
        if ch in ("", "b"):
            return
        if ch == "s" and own:
            msg = _tier_pick(league, team, "support")


# ═══ Compliance office ══════════════════════════════════════════════════════

def _tier_pick(league, team, which):
    s = cp._tables_ok(cp.st(team))
    table = cp.OFFICE_TIER if which == "office" else cp.SUPPORT_TIER
    keys = list(table)
    cur = s["tier"] if which == "office" else s["support"]
    b = cp._budget(team)
    print()
    for i, k in enumerate(keys, 1):
        pct = table[k][1]
        cost = "saves " + _money(-b * pct) + "/yr" if pct < 0 else "costs " + _money(b * pct) + "/yr" if pct else "no change"
        mark = paint("  ← now", C.BCYAN) if k == cur else ""
        effect = (f"office {table[k][0]:+d}" if which == "office"
                  else f"grades {table[k][0] * 100:+.0f} pts/term")
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(table[k][2], 10)}{pad(cost, 26)}{paint(effect, C.GRAY)}{mark}")
    ch = ask("Pick (Enter = keep):").strip()
    if ch.isdigit() and 1 <= int(ch) <= len(keys):
        k = keys[int(ch) - 1]
        if which == "office":
            s["tier"] = k
        else:
            s["support"] = k
        return f"{'Compliance office' if which == 'office' else 'Academic support'} is now {table[k][2].lower()}. The cost comes out of next year's pool."
    return ""


def office_screen(league, team):
    msg = ""
    while True:
        clear()
        print(title_bar(f"COMPLIANCE OFFICE  ·  {team.school.upper()}", league.conference_color(team.conference)))
        s = cp._tables_ok(cp.st(team))
        eff = cp.office_eff(team)
        print()
        print(f"   {paint('Strength', C.GRAY)}   {cp.office_word(eff)}   {paint('Budget', C.GRAY)}  {cp.OFFICE_TIER[s['tier']][2]}")
        print(f"   {paint('Risk', C.GRAY)}       {cp.risk(league, team):.2f}× an average program's chance of something getting bent")
        print()
        _wrap("A strong office makes trouble less likely, finds problems before anyone else does, and turns them into "
              "self-reports, which the committee rewards. A thin one does the opposite. It also can't find what "
              "the head coach decides to hide.")
        print()
        _wrap("What raises the risk: a booster-driven or win-now athletic director, a big program, a low reputation for "
              "integrity, and the shortcuts you say yes to. What lowers it: a strong office, probation (a program under "
              "the microscope behaves), and a clean record.")
        if msg:
            print()
            _wrap(msg)
            msg = ""
        print(rule())
        print("   [T] change the budget   [B] back")
        ch = ask("Select:").strip().lower()
        if ch in ("", "b"):
            return
        if ch == "t":
            msg = _tier_pick(league, team, "office")


def audit_screen(league, team):
    clear()
    print(title_bar("INTERNAL AUDIT", league.conference_color(team.conference)))
    b = cp._budget(team)
    s = cp._tables_ok(cp.st(team))
    print()
    _wrap(f"An outside firm reads every booster, collective and recruiting file you have. It costs about "
          f"{_money(b * 0.0025)} from next year's pool. Whatever it finds, you report yourself: cooperation "
          f"and self-reporting shrink a penalty. It can't find something you've decided to hide.")
    if s.get("audit_year") == league.year:
        print(paint("\n   You've already had an audit this year.", C.BYELLOW))
        pause()
        return
    ch = ask("Commission it? (Y/N)").strip().lower()
    if ch == "y":
        found, lines = cp.internal_audit(league, team)
        print()
        for ln in lines:
            _wrap(ln)
        for c in found:
            print(f"   {paint('•', C.BYELLOW)} {cp.LEVEL_WORD[c['level']]}: {c['text']}")
        pause()


# ═══ Sanctions & history ════════════════════════════════════════════════════

def history_screen(league, team):
    clear()
    print(title_bar(f"SANCTIONS & HISTORY  ·  {team.school.upper()}", league.conference_color(team.conference)))
    s = cp._tables_ok(cp.st(team))
    print()
    print(section("NOW", C.BRED))
    print(f"   {paint('Sanctions', C.GRAY)}  {_sanction_line(team, league)}")
    live = [p for p in s["penalties"] if p["until"] >= league.year]
    for p in live:
        print(f"   {paint('•', C.BRED)} {cp.LEVEL_WORD[p['level']]}, {p['year']}: {p['why']}")
        for ln in p["lines"][:5]:
            print("       " + paint(ln, C.GRAY))
    if not live and not (getattr(team, 'sanctions', None) or {}).get("until", 0) >= league.year:
        print(paint("   None.", C.GRAY))
    vac = [v for v in s["vacated"]]
    if vac:
        print()
        print(section("VACATED", C.BYELLOW))
        for v in vac:
            print("   " + ", ".join(f"{n} wins in {y}" for y, n in v["years"].items()))
    print()
    print(section("THE RECORD", C.BCYAN))
    if not s["history"]:
        print(paint("   A clean file.", C.GRAY))
    for y, t in reversed(s["history"][-12:]):
        print(f"   {paint(str(y), C.GRAY)}  {truncate(t, WIDTH - 12)}")
    pause()


# ═══ League-wide ════════════════════════════════════════════════════════════

def wire(league):
    clear()
    print(title_bar("COMPLIANCE WIRE"))
    items = list(reversed(cp.root(league)["news"]))[:28]
    print()
    if not items:
        print(paint("   Quiet. So far.", C.GRAY))
    for n in items:
        when = f"{n['year']} " + (f"wk {n['week']}" if 0 < n["week"] < 18 else "offs.")
        head = paint(pad(when, 12), C.GRAY)
        body = textwrap.wrap(n["text"], WIDTH - 18)
        print(f"   {head}{paint(body[0], KIND_COLOR.get(n['kind'], C.BWHITE))}")
        for ln in body[1:]:
            print("   " + " " * 12 + paint(ln, KIND_COLOR.get(n["kind"], C.BWHITE)))
    pause()


def investigations(league):
    clear()
    print(title_bar("UNDER INVESTIGATION"))
    order = {"allegations": 0, "inquiry": 1, "appeal": 2, "ruled": 3, "rumor": 4}
    rows = sorted((c for c in cp.public_cases(league) if c["level"] <= 2 or c["school"] == (cp.mine(league).school if cp.mine(league) else "")),
                  key=lambda c: (c["level"], order.get(c["status"], 9), -c["age"]))
    print()
    if not rows:
        print(paint("   No open cases anywhere.", C.GRAY))
    else:
        print(paint(f"   {pad('SCHOOL', 20)}{pad('LEVEL', 11)}{pad('MATTER', 24)}{pad('STAGE', 22)}AGE", C.GRAY))
    for c in rows[:22]:
        print(f"   {pad(truncate(c['school'], 19), 20)}{paint(pad(cp.LEVEL_WORD[c['level']], 11), LVL_COLOR[c['level']], C.BOLD)}"
              f"{pad(cp.KINDS[c['kind']]['label'], 24)}{pad(cp.stage_label(c), 22)}{paint(str(c['age']) + ' wk', C.GRAY)}")
    print()
    print(section("SANCTIONED NOW", C.BRED))
    sanc = [t for t in league.teams if (getattr(t, "sanctions", None) or {}).get("until", 0) >= league.year]
    if not sanc:
        print(paint("   Nobody.", C.GRAY))
    for t in sanc[:12]:
        print(f"   {pad(truncate(t.school, 19), 20)}{_sanction_line(t, league)}")
    pause()


def apr_board(league):
    clear()
    print(title_bar("APR BOARD"))
    yrs = sorted(cp.root(league)["aprs"])
    print()
    if not yrs:
        print(paint("   The first APRs come out after the 2026 season.", C.GRAY))
        pause()
        return
    y = yrs[-1]
    vals = sorted(cp.root(league)["aprs"][y].items(), key=lambda kv: kv[1])
    print(paint(f"   {y} Academic Progress Rate  ·  the line is {cp.APR_LINE}", C.GRAY))
    print()
    print(section("LOWEST", C.BRED))
    for sch, a in vals[:10]:
        col = C.BRED if a < cp.APR_LINE else C.BYELLOW
        print(f"   {pad(truncate(sch, 24), 26)}{paint(str(a), col, C.BOLD)}" + (paint("   below the line", C.BRED) if a < cp.APR_LINE else ""))
    print()
    print(section("HIGHEST", C.BGREEN))
    for sch, a in list(reversed(vals))[:6]:
        print(f"   {pad(truncate(sch, 24), 26)}{paint(str(a), C.BGREEN, C.BOLD)}")
    pause()
