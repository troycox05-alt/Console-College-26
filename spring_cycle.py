"""Persistent spring-football cycle for the year-round offseason.

Weeks 11-13 are not one menu anymore. Each player receives practice samples,
staff evaluation movement, a little real development, and an A-Day film result.
The results are stored on the player/team so the post-spring portal and fall
camp can react to what actually happened.
"""
import random

from ui import C, ask, clear, key, pad, paint, panel, pause, section, title_bar, truncate

EMPHASES = {
    "1": ("fundamentals", "Fundamentals", "Young players develop faster; cleaner technique, lower volatility."),
    "2": ("competition", "Competition", "More live reps; sharper evaluations and stronger depth-chart movement."),
    "3": ("young", "Young Players", "Freshmen and sophomores get extra reps and development."),
    "4": ("physical", "Physicality", "OL/DL/LB/RB get extra work; more development, slightly more injury risk."),
    "5": ("chemistry", "Chemistry", "Leadership and team work; morale rises and the room settles."),
    "6": ("passing", "Passing Game", "QB/WR/TE/CB/S receive extra competitive reps."),
}


def _state(league):
    import offseason_cal
    st = offseason_cal._state(league)
    sp = st.setdefault("spring", {})
    sp.setdefault("year", league.year)
    sp.setdefault("emphasis", None)
    sp.setdefault("focus_positions", [])
    sp.setdefault("weeks", {})
    sp.setdefault("standouts", [])
    sp.setdefault("stock_up", [])
    sp.setdefault("stock_down", [])
    sp.setdefault("injuries", [])
    sp.setdefault("aday", {})
    return sp


def _pkey(p):
    return f"{p.name}|{getattr(p, 'position', '')}|{getattr(p, 'number', '')}"


def _eligible_focus(pos, emphasis):
    if emphasis == "young":
        return True
    if emphasis == "physical":
        return pos in ("RB", "TE", "OL", "DL", "LB")
    if emphasis == "passing":
        return pos in ("QB", "WR", "TE", "CB", "S")
    return True


def _choose_plan(league, team):
    sp = _state(league)
    if sp.get("emphasis"):
        return sp["emphasis"]
    clear()
    print(title_bar(f"SPRING BALL PLAN · {team.school.upper()} · {league.year}"))
    print(paint("   Two practice blocks and A-Day. The emphasis changes development, evaluation and risk.", C.GRAY))
    print()
    for k, (_, name, desc) in EMPHASES.items():
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)} — {desc}")
    import webview
    webview.emit("spring", {"school": team.school, "year": league.year,
                            "options": [{"key": k, "name": n, "desc": dsc} for k, (_, n, dsc) in EMPHASES.items()]})
    ch = ask("Spring emphasis (Enter = Fundamentals):").strip()
    emphasis, name, _ = EMPHASES.get(ch, EMPHASES["1"])
    sp["emphasis"] = emphasis
    team.spring_focus = {"year": league.year, "pos": set(), "emphasis": emphasis}

    # Let the coach choose up to three close rooms. These become extra-film rooms.
    try:
        import offseason_cal
        bs = offseason_cal.battles(league, team)
    except Exception:
        bs = []
    if bs:
        clear()
        print(title_bar("SPRING POSITION BATTLES"))
        print(paint("   Pick up to three rooms for extra ones-vs-ones and film. Enter = spread reps around.", C.GRAY))
        for i, (_, pos, a, b) in enumerate(bs, 1):
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(pos,4)}{pad(truncate(a.name,22),23)} vs {truncate(b.name,22)}")
        raw = ask("Focus rooms (example 1,3):").strip()
        picks = []
        for tok in raw.replace(" ", ",").split(","):
            if tok.isdigit() and 1 <= int(tok) <= len(bs) and int(tok) - 1 not in picks:
                picks.append(int(tok) - 1)
        picks = picks[:3]
        focus = [bs[i][1] for i in picks]
        sp["focus_positions"] = focus
        team.spring_focus["pos"] = set(focus)
    return emphasis


def _tier_map(team):
    import practice
    starts = practice.starter_counts(team)
    out = {}
    for pos, n in starts.items():
        for i, p in enumerate(team.players_at(pos)):
            out[id(p)] = 0 if i < n else 1 if i < n * 2 else 2
    return out


def _practice_player(league, team, p, block, tier, emphasis):
    import practice
    forms, lines = [], []
    # Three visible session samples per spring block.
    for sess in range(1, 4):
        rng = random.Random(f"spring-rep:{league.seed}:{league.year}:{team.school}:{block}:{sess}:{p.name}")
        text, form = practice.stat_line(p, tier, rng)
        # Extra focus creates a better sample, not free talent.
        if p.position in set(_state(league).get("focus_positions", [])):
            form *= 1.10
        if _eligible_focus(p.position, emphasis):
            if emphasis in ("competition", "passing", "physical"):
                form *= 1.05
        lines.append(text)
        forms.append(max(-2.0, min(2.0, form)))
    avg = sum(forms) / len(forms)
    return lines, forms, avg


def _develop(league, team, p, block, emphasis, rng):
    """Small spring development; the larger offseason development already happened in winter."""
    import development
    import facilities
    scale = 0.035
    if emphasis == "fundamentals":
        scale = 0.055 if p.year <= 1 else 0.03
    elif emphasis == "young":
        scale = 0.065 if p.year <= 1 else 0.018
    elif emphasis == "physical" and p.position in ("RB", "TE", "OL", "DL", "LB"):
        scale = 0.05
    elif emphasis == "passing" and p.position in ("QB", "WR", "TE", "CB", "S"):
        scale = 0.05
    before = p.overall
    development.develop_player(p, team.coach, facilities.training_rating(team), rng,
                               team=team, scale=scale, in_season=True)
    return p.overall - before


def _injury_roll(league, team, p, block, emphasis, rng):
    if getattr(p, "inj_games", 0) > 0:
        return None
    import injuries
    weight = 0.18
    if emphasis == "physical":
        weight = 0.34
    elif emphasis == "competition":
        weight = 0.26
    if rng.random() >= injuries.injury_chance(p, weight=weight):
        return None
    kind, games, desc = injuries.roll_severity(rng)
    # A spring knock that would only remove him from today's practice is still worth recording,
    # but only multi-week injuries carry into the fall game counter.
    if kind in ("shaken", "game"):
        return desc
    p.inj_games = games
    p.inj_desc = desc
    p.inj_week = 0
    return desc


def run_block(league, team, block):
    """Run Spring Ball I or II once. Stores practice, development and evaluation stock."""
    sp = _state(league)
    k = str(block)
    if k in sp["weeks"]:
        review_block(league, team, block)
        return
    emphasis = _choose_plan(league, team)
    tiers = _tier_map(team)
    results = []
    rng = random.Random(f"spring-dev:{league.seed}:{league.year}:{team.school}:{block}")
    for p in list(team.roster):
        if getattr(p, "inj_games", 0) > 0:
            lines, forms, avg = ["Limited by injury."], [0.0], 0.0
            gain = 0
            inj = None
        else:
            lines, forms, avg = _practice_player(league, team, p, block, tiers.get(id(p), 2), emphasis)
            gain = _develop(league, team, p, block, emphasis, rng)
            inj = _injury_roll(league, team, p, block, emphasis, rng)
        # Stock is staff-facing and intentionally modest. It fades during the regular season.
        if emphasis == "chemistry":
            try:
                import morale
                morale.nudge(p, 2, "spring leadership work", league)
            except Exception:
                pass
        hist = p.__dict__.setdefault("spring_form", {})
        old = float(hist.get(league.year, 0.0))
        hist[league.year] = max(-2.5, min(2.5, old + avg * 0.60))
        sess = p.__dict__.setdefault("spring_sessions", {}).setdefault(league.year, {})
        sess[block] = [(lines[i] if i < len(lines) else "", forms[i] if i < len(forms) else 0.0) for i in range(len(forms))]
        results.append({"player": _pkey(p), "name": p.name, "pos": p.position, "avg": round(avg, 2), "gain": gain,
                        "injury": inj})
        if inj:
            sp["injuries"].append(f"{p.position} {p.name} — {inj}")
    sp["weeks"][k] = results
    _refresh_stock(league, team)
    # Evaluation only: staff order responds to spring tape. Fall camp remains the user's final call.
    try:
        import depth
        depth.staff_sort_yours(league, team)
    except Exception:
        pass
    review_block(league, team, block)
    if block == 2 and not sp.get("position_trials_done"):
        sp["position_trials_done"] = True
        try:
            if ask("Review spring position trials before A-Day? (y/n):").strip().lower() in ("y", "yes"):
                import offseason_cal
                offseason_cal.position_trials(league, team, random.Random(f"spring-trials:{league.seed}:{league.year}:{team.school}"))
        except Exception:
            pass


def _refresh_stock(league, team):
    rows = []
    for p in team.roster:
        form = float(getattr(p, "spring_form", {}).get(league.year, 0.0))
        rows.append((form, p))
    rows.sort(key=lambda x: -x[0])
    sp = _state(league)
    sp["stock_up"] = [f"{p.position} {p.name}" for f, p in rows if f >= .45][:6]
    sp["stock_down"] = [f"{p.position} {p.name}" for f, p in reversed(rows) if f <= -.45][:6]
    sp["standouts"] = [f"{p.position} {p.name}" for f, p in rows[:8] if f > .1]


def review_block(league, team, block):
    sp = _state(league)
    rows = list(sp.get("weeks", {}).get(str(block), []))
    clear()
    print(title_bar(f"SPRING BALL {'I' if block == 1 else 'II'} · {team.school.upper()}"))
    emp = sp.get("emphasis", "fundamentals").replace("_", " ").title()
    print(paint(f"   Emphasis: {emp} · three practice sessions per player this block.", C.GRAY))
    print(paint("   Practice number = performance versus expectation; spring stock changes what the staff believes, not just true OVR.", C.GRAY))
    print(section("STOCK UP", C.BGREEN))
    ups = sorted(rows, key=lambda x: -x["avg"])[:6]
    for x in ups:
        if x["avg"] <= 0:
            break
        gain = paint(f"  +{x['gain']} OVR", C.BGREEN) if x.get("gain", 0) > 0 else ""
        print(f"   {pad(x['pos'],4)}{pad(truncate(x['name'],25),26)} {paint(format(x['avg'], '+.1f'), C.BGREEN, C.BOLD)} practice{gain}")
    print(section("STOCK DOWN", C.BRED))
    downs = sorted(rows, key=lambda x: x["avg"])[:5]
    shown = False
    for x in downs:
        if x["avg"] >= 0:
            break
        shown = True
        print(f"   {pad(x['pos'],4)}{pad(truncate(x['name'],25),26)} {paint(format(x['avg'], '+.1f'), C.BRED, C.BOLD)} practice")
    if not shown:
        print(paint("   No meaningful negative trend this block.", C.GRAY))
    if sp.get("injuries"):
        print(section("MEDICAL", C.BYELLOW))
        for text in sp["injuries"][-4:]:
            print("   " + text)
    print(paint("\n   Practice stock changes staff evaluation; development and evaluation are separate.", C.GRAY))
    pause()


def spring_form(league, p):
    return float(getattr(p, "spring_form", {}).get(league.year, 0.0))


def apply_aday_film(league, team, sim):
    """Translate spring-game production into film stock used by staff and portal reactions."""
    scored = []
    for p, line in getattr(sim, "stats", {}).items():
        if p not in team.roster:
            continue
        off = (line.get("pass_yds", 0) / 85 + line.get("pass_td", 0) * 1.3 - line.get("ints", 0) * 1.3 +
               line.get("rush_yds", 0) / 35 + line.get("rush_td", 0) * 1.0 +
               line.get("rec_yds", 0) / 35 + line.get("rec_td", 0) * 1.0)
        deff = (line.get("tackles", 0) / 4 + line.get("tfl", 0) * .7 + line.get("sacks", 0) * 1.2 +
                line.get("ints", 0) * 1.4 + line.get("pbu", 0) * .35)
        score = max(-2.0, min(2.0, max(off, deff) - .45))
        if score:
            hist = p.__dict__.setdefault("spring_form", {})
            hist[league.year] = max(-2.5, min(2.5, float(hist.get(league.year, 0.0)) + score * .30))
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    sp = _state(league)
    sp["aday"]["film"] = [(p.name, p.position, round(s, 2)) for s, p in scored[:12]]
    _refresh_stock(league, team)
    try:
        import depth
        depth.staff_sort_yours(league, team)
    except Exception:
        pass
    # Morale follows the public spring result a little; this is what can help trigger Portal II.
    try:
        import morale
        for score, p in scored:
            if score >= 1.0:
                morale.nudge(p, 2, "strong spring game", league)
            elif score <= -.75:
                morale.nudge(p, -2, "rough spring game", league)
    except Exception:
        pass


def spring_summary_lines(league, team, limit=5):
    sp = _state(league)
    out = []
    if sp.get("stock_up"):
        out.append("Stock up: " + ", ".join(sp["stock_up"][:3]))
    if sp.get("stock_down"):
        out.append("Stock down: " + ", ".join(sp["stock_down"][:3]))
    if sp.get("aday", {}).get("score"):
        out.append("A-Day: " + sp["aday"]["score"])
    if sp.get("injuries"):
        out.append(f"Spring injuries: {len(sp['injuries'])}")
    return out[:limit]
