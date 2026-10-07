"""
cp_alerts.py — Heads Up: the alert center (Coach Career).

Everything you'd want to know before it's too late, sorted by how much it matters:

  Recruiting   commits wavering or gone, top-3 changes, visits this week, a thin board, signing day
  Roster       starters thinking about the portal, unhappy starters, a cold locker room, who's hurt
  Your job     the seat, the AD's trust, the last year of your contract, a story deadline
  Schedule     rivalry week, a top-10 opponent, a trap game, the bye
  Money        over next year's NIL pool

  scan(league, team, base)   weekly (career_plus._alerts hands over the recruiting moves it saw)
  alerts(league)             what's live, most urgent first (the dashboard shows the top two)
  screen(league)             the alert center: by category, dismiss what you've handled
"""
from ui import WIDTH, C, ask, clear, clip, footer, key, pad, paint, section, title_bar

SEV = {3: ("URGENT", C.BRED), 2: ("SOON", C.BYELLOW), 1: ("FYI", C.GRAY)}
CATS = ["Recruiting", "Roster", "Your job", "Schedule", "Money"]


def _cp():
    import career_plus
    return career_plus


def _add(out, aid, cat, sev, text, keys):
    out.append({"id": aid, "cat": cat, "sev": sev, "text": text, "keys": keys})


def scan(league, team, base):
    cp = _cp()
    st = cp.state(league)
    out = []
    for text, keys in base:
        sev = 3 if "wavering" in text else 2
        _add(out, "rec:" + text.split(" committed")[0].split(" put")[0].split(" dropped")[0], "Recruiting", sev, text, keys)
    nxt_wk = league.week + 1
    # visits this coming week
    try:
        import recruit_plus
        ov = recruit_plus.S(league.recruiting).get("ov_index", {}).get(nxt_wk, [])
        mine = [r for t, r in ov if t is team]
        if mine:
            names = ", ".join(f"{r.stars}★ {r.name}" for r in mine[:3])
            _add(out, f"ov:{nxt_wk}", "Recruiting", 1, f"Official visits this week: {names}" + (f" +{len(mine) - 3}" if len(mine) > 3 else ""), "4→B")
    except Exception:                                   # noqa: BLE001, S110 — an alert is never worth a crash
        pass
    if league.week <= 12 and len(team.recruiting_targets) < 8:
        _add(out, "thin", "Recruiting", 1, f"Your board is thin ({len(team.recruiting_targets)} targets). 4 → F finds more.", "4→F")
    if league.week in (11, 12, 13):
        unsigned = [r for r in league.recruiting.commitments(team) if not getattr(r, "signed", False)]
        if unsigned:
            _add(out, "esd", "Recruiting", 2, f"Early signing day is coming: {len(unsigned)} commit{'s' if len(unsigned) != 1 else ''} still unsigned.", "4→C")
    # roster
    try:
        import morale
        for p in team.roster:
            if cp._is_starter(team, p) and morale.get(p) < 30:
                _add(out, f"mood:{p.name}", "Roster", 2, f"Starter {p.position} {p.name} is unhappy ({morale.word(morale.get(p))}).", "3→K")
    except Exception:                                   # noqa: BLE001, S110
        pass
    try:
        import personalities
        ch = personalities.chemistry(team)
        if ch < 40:
            _add(out, "chem", "Roster", 2, f"Locker-room chemistry is low ({ch:.0f}). It costs you on Saturdays.", "3→K")
    except Exception:                                   # noqa: BLE001, S110
        pass
    for p in team.roster:
        if getattr(p, "inj_games", 0) > 0 and cp._is_starter(team, p) and "opted out" not in str(getattr(p, "inj_desc", "")):
            n = p.inj_games
            _add(out, f"inj:{p.name}", "Roster", 1, f"Starter {p.position} {p.name} is out "
                 f"{'for the season' if n >= 99 else f'{n} more game' + ('s' if n != 1 else '')}.", "3→D")
    try:
        import transfer_watch
        for _odds, p, name, _col in transfer_watch._rows(league, team, True)[:6]:
            if name in ("Likely gone", "Halfway out the door") and cp._is_starter(team, p):
                _add(out, f"tw:{p.name}", "Roster", 2, f"Starter {p.position} {p.name} is a transfer risk ({name.lower()}).", "4→W")
    except Exception:                                   # noqa: BLE001, S110
        pass
    # the job
    coach = league.user_coach
    seat = getattr(coach, "seat", 0)
    if seat >= 70:
        _add(out, "seat", "Your job", 3, f"Your seat is {seat}/100. Your AD is talking about you, not to you.", "6→C")
    elif seat >= 55:
        _add(out, "seat", "Your job", 2, f"Your seat is warming: {seat}/100.", "6→C")
    try:
        import ad_trust
        tv = ad_trust.get(coach, team)
        if tv < 35:
            _add(out, "trust", "Your job", 2, f"Your AD's trust is low ({tv:.0f}/100, {ad_trust.word(tv)}).", "6→C")
    except Exception:                                   # noqa: BLE001, S110
        pass
    try:
        import finance
        k = finance.contract(coach)
        if k and finance.years_left(k, league) <= 1:
            _add(out, "contract", "Your job", 1, "This is the last year of your contract.", "6→C")
    except Exception:                                   # noqa: BLE001, S110
        pass
    story = st.get("start") or {}
    for ch in story.get("chapters") or []:
        if ch["status"] == "open" and ch["by"] == league.year:
            _add(out, "story", "Your job", 2, f"Story deadline this season: {ch['goal'].lower()} ({ch['title']}).", "6→L")
            break
    # the schedule
    import week as _wk
    g = _wk.next_game(league, team)
    if g is None and league.week < 13:
        _add(out, "bye", "Schedule", 1, "Bye week. A chance to heal and to recruit.", "")
    elif g is not None:
        o = g.opponent_of(team)
        rk = league.rankings.rank_of(o)
        try:
            import rivalries
            nm = rivalries.rivalry_name(team, o)
        except Exception:                               # noqa: BLE001
            nm = None
        if nm:
            _add(out, "rival", "Schedule", 2, f"Rivalry week: {nm} vs {o.school}.", "1")
        elif rk and rk <= 10:
            _add(out, "big", "Schedule", 1, f"Next: No. {rk} {o.school}. A chance to change your season.", "1")
        else:
            later = sorted((x for x in league.team_games(team) if not x.played and x.week > g.week), key=lambda x: x.week)
            if later and not rk:
                o2 = later[0].opponent_of(team)
                r2 = league.rankings.rank_of(o2)
                if r2 and r2 <= 15 and o.team_ovr >= team.team_ovr - 6:
                    _add(out, "trap", "Schedule", 1, f"Trap game: {o.school} this week, No. {r2} {o2.school} next. Don't look ahead.", "1")
    # money
    try:
        import finance
        av = finance.available(league, team)
        if av < 0:
            _add(out, "nil", "Money", 2, f"You're {finance.money(-av)} over next year's NIL pool.", "5→N")
    except Exception:                                   # noqa: BLE001, S110
        pass
    st["alerts"] = [dict(a, year=league.year, week=league.week) for a in out]


def alerts(league):
    st = _cp().state(league)
    gone = set(st.get("dismissed", {}).get(str(league.year), []))
    rows = [a for a in st["alerts"] if a.get("year") == league.year and a.get("id") not in gone]
    return sorted(rows, key=lambda a: -a.get("sev", 1))


def screen(league):
    cp = _cp()
    while True:
        st = cp.state(league)
        rows = alerts(league)
        clear()
        print(title_bar(f"HEADS UP · WEEK {league.week}"))
        n3 = sum(1 for a in rows if a.get("sev") == 3)
        print(f"\n   {len(rows)} alert{'s' if len(rows) != 1 else ''}" + (paint(f"   {n3} urgent", C.BRED, C.BOLD) if n3 else ""))
        if not rows:
            print(paint("\n   Nothing needs you. Enjoy it.", C.BGREEN))
        idx = []
        for cat in CATS:
            mine = [a for a in rows if a.get("cat") == cat]
            if not mine:
                continue
            print(section(cat.upper(), C.BCYAN))
            for a in mine:
                idx.append(a)
                lab, col = SEV.get(a.get("sev", 1), SEV[1])
                print(clip(f"   {paint(f'[{len(idx):>2}]', C.BYELLOW, C.BOLD)} {paint(pad(lab, 7), col, C.BOLD)}{a['text']}"
                           + (paint(f"   {a['keys']}", C.GRAY) if a.get("keys") else ""), WIDTH))
        gone = st.get("dismissed", {}).get(str(league.year), [])
        footer(*([key("#", "dismiss")] if idx else []), *([key("R", f"restore {len(gone)} dismissed")] if gone else []),
               key("B", "back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c.isdigit() and 1 <= int(c) <= len(idx):
            st.setdefault("dismissed", {}).setdefault(str(league.year), []).append(idx[int(c) - 1]["id"])
        elif c == "r" and gone:
            st["dismissed"][str(league.year)] = []
        else:
            return
