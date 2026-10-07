"""
links.py — What the window (play.py) can turn into a link, and what clicking one opens.

Every name the game prints that has a page behind it — players, teams, coaches and
coordinators, conferences, stadiums, rivalries and trophies, recruits, this season's
bowls — is listed here with an id. The window underlines those names wherever they
appear (screens, cards, the sidebar), and a click opens the page in a card without
leaving the screen you're on.

    index(league)   -> (key, [[text, id], ...])   key changes when the list does
    render(league, id) -> a function that prints the page (play.py captures it)

Names with no page (FCS programs) are listed with the id "-": they're read whole so
"Alabama A&M" is never a link to Alabama, but they aren't links themselves.

When two things share a name, the first one listed wins, in this order: your team's
players, your next opponent's, teams, conferences, coaches, every other player,
stadiums, rivalries and trophies, recruits, bowls, coaches without a job.
"""
import re

_objs = {}          # id -> ("kind", object or tuple)
_cache = {"fp": None, "key": None, "list": []}
_THE = re.compile(r"^(?:the battle for |the )", re.I)


def _you(lg):
    me = getattr(lg, "user_coach", None)
    return getattr(me, "team", None) if me is not None else getattr(lg, "user_team", None)


def _next_opp(lg, team):
    if team is None:
        return None
    for w in sorted(lg.schedule):
        if w < lg.week:
            continue
        for g in lg.schedule[w]:
            if not g.played and team in (g.home, g.away):
                return g.away if g.home is team else g.home
    return None


def _fingerprint(lg):
    rec = getattr(lg, "recruiting", None)
    return (id(lg), lg.year, lg.week, getattr(lg, "status", ""), sum(len(t.roster) for t in lg.teams),
            len(getattr(rec, "pool", []) or []), len(getattr(lg, "coach_pool", []) or []),
            id(_you(lg)), sum(1 for t in lg.teams for p in t.roster[:1]))


def index(lg):
    fp = _fingerprint(lg)
    if fp == _cache["fp"]:
        return _cache["key"], _cache["list"]
    import universe
    _objs.clear()
    seen, out = set(), []

    def add(text, kind, obj):
        text = str(text or "").strip()
        text = _THE.sub("", text)
        if len(text) < 3 or text in seen:
            return
        lid = f"{kind}{len(_objs)}"
        if obj is not None and lid not in _objs:
            _objs[lid] = (kind, obj)
        seen.add(text)
        out.append([text, lid])

    def add_obj(texts, kind, obj):
        lid = f"{kind}{len(_objs)}"
        _objs[lid] = (kind, obj)
        for text in texts:
            text = _THE.sub("", str(text or "").strip())
            if len(text) >= 3 and text not in seen:
                seen.add(text)
                out.append([text, lid])

    you = _you(lg)
    opp = _next_opp(lg, you)
    # players first for your team and the next opponent (short names too: 'J. Hobbs')
    for t in (you, opp):
        if t is None:
            continue
        for p in t.roster:
            add_obj((p.name, getattr(p, "short_name", None)), "p", p)
    teams = [t for t in lg.teams if not getattr(t, "fcs", False)]
    for t in teams:
        names = [t.school, f"{t.school} {t.nickname}"]
        import ui
        ab = ui.ABBREVIATIONS.get(t.school)
        if ab and len(ab) >= 3 and ab.isupper():
            names.append(ab)
        sn = ui.SHORT_NAMES.get(t.school)
        if sn and sn != t.school and len(sn) >= 5:
            names.append(sn)
        add_obj(names, "t", t)
    # FCS programs have no page, but their names must still be read whole: "Alabama A&M" isn't a link to Alabama
    for t in getattr(lg, "fcs_teams", []) or []:
        for text in (t.school, f"{t.school} {t.nickname}", t.school.upper()):
            if text not in seen:
                seen.add(text)
                out.append([text, "-"])
    for t in teams:                                # box headers and title bars print schools in capitals
        add_obj((t.school.upper(),), "t", t) if len(t.school) >= 4 else None
    import league as L
    for short, (full, _c) in L.CONF_INFO.items():
        if short != "Independent":
            add_obj((short, full, f"{short} Championship"), "f", short)
    import staff
    for t in teams:
        for c in (t.coach, getattr(t, "oc", None), getattr(t, "dc", None)):
            if c is not None:
                add_obj((c.name,), "c", c)
    shorts = {}
    for t in teams:
        for p in t.roster:
            s = getattr(p, "short_name", None)
            if s:
                shorts[s] = shorts.get(s, 0) + 1
    for t in teams:
        for p in t.roster:
            s = getattr(p, "short_name", None)
            add_obj((p.name,) + ((s,) if s and shorts.get(s) == 1 else ()), "p", p)   # 'T. Cromartie' if he's the only one
    for t in teams:
        if getattr(t, "stadium", None):
            add_obj((t.stadium,), "s", t)
    by_school = {t.school: t for t in teams}
    try:
        import commentary
        import rivalries
        for (a, b), name in list(commentary.RIVALRIES.items()):
            if a in by_school and b in by_school:
                add_obj((name,), "r", (by_school[a], by_school[b]))
        for pair, name in list(rivalries.TROPHIES.items()):
            a, b = tuple(pair)
            if a in by_school and b in by_school:
                add_obj((name,), "r", (by_school[a], by_school[b]))
    except Exception:
        pass
    rec = getattr(lg, "recruiting", None)
    if you is not None and rec is not None:
        for r in getattr(rec, "pool", []) or []:
            add_obj((r.name,), "k", r)
    for w in sorted(lg.schedule):
        for g in lg.schedule[w]:
            bn = getattr(g, "bowl_name", None)
            if bn and g.played and g.box is not None and g.game_type not in ("Conference Championship",) \
                    and not str(bn).startswith(("NP ", "National Championship")):
                add_obj((bn,), "b", g)
    for c in getattr(lg, "coach_pool", []) or []:
        add_obj((c.name,), "c", c)
    _cache.update(fp=fp, key=f"{lg.year}.{lg.week}.{len(out)}.{abs(hash(fp)) % 10 ** 8}.{universe.current()}",
                  list=out)
    return _cache["key"], out


def render(lg, lid):
    """A function that prints the page for this link, or None."""
    hit = _objs.get(lid)
    if hit is None:
        return None
    kind, obj = hit
    if kind == "p":
        import screens
        return lambda: screens.player_card(lg, obj)
    if kind == "t":
        import screens
        return lambda: screens._print_team_page(lg, obj)
    if kind == "c":
        import coach_screens
        return lambda: coach_screens.coach_view(lg, obj)
    if kind == "f":
        import screens
        return lambda: screens.show_standings(lg, [obj])
    if kind == "s":
        import stadium_screens
        return lambda: stadium_screens.stadium_screen(lg, obj)
    if kind == "r":
        import rivalries
        return lambda: rivalries.head_to_head(lg, *obj)
    if kind == "k":
        import recruiting_screens
        you = _you(lg)
        return (lambda: recruiting_screens.recruit_card(lg, you, obj)) if you is not None else None
    if kind == "b":
        import screens
        return lambda: screens.show_box_score(lg, obj)
    return None
