"""
cp_tree.py — Your coaching tree, deeper (Coach Career).

  screen(league)          the tree: every assistant who worked for you, where they are, how you do
                          against them — [#] opens one, [G] the second generation, [S] the sport's
                          biggest trees, and the tree's combined numbers
  news(league)            when a branch moves (a new head coach, a coordinator job), it's a story
"""
from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    footer,
    key,
    pad,
    paint,
    pause,
    section,
    title_bar,
    truncate,
)


def _cp():
    import career_plus
    return career_plus


def _hc_history(c):
    return [h for h in getattr(c, "history", []) or [] if isinstance(h, dict)]


def _coord_history(c):
    return [e for e in getattr(c, "coord_history", []) or [] if isinstance(e, dict)]


def stats(league, rows):
    heads = [r for r in rows if r[3].startswith("head coach")]
    coords = [r for r in rows if "coordinator" in r[3]]
    w = l_ = titles = 0
    for c, _n, _roles, _now, _rec in rows:
        if c is None:
            continue
        hist = _hc_history(c)
        w += sum(h.get("w", 0) for h in hist)
        l_ += sum(h.get("l", 0) for h in hist)
        titles += sum(1 for h in hist if h.get("title"))
        t = getattr(c, "team", None)
        if t is not None and t.coach is c:
            w += t.wins
            l_ += t.losses
    return {"n": len(rows), "heads": len(heads), "coords": len(coords), "w": w, "l": l_, "titles": titles}


def second_gen(league, rows):
    """[(branch name, [(coach name, year, school, role)])] — who worked for your former assistants."""
    branches = {r[1] for r in rows if r[0] is not None and (_hc_history(r[0]) or r[3].startswith("head coach"))}
    me = league.user_coach.name
    out = {}
    for c in _cp()._all_coaches(league):
        if c.name == me:
            continue
        for e in _coord_history(c):
            if e.get("hc") in branches and c.name not in branches:
                out.setdefault(e["hc"], []).append((c.name, e.get("year"), e.get("school"), e.get("role")))
    return sorted(out.items(), key=lambda kv: -len(kv[1]))


def biggest(league):
    """[(head coach name, tree size, is it you)] — every coach's assistants, counted from their records."""
    me = league.user_coach.name
    trees = {}
    for c in _cp()._all_coaches(league):
        for e in _coord_history(c):
            hc = e.get("hc")
            if hc and hc != c.name:
                trees.setdefault(hc, set()).add(c.name)
    trees[me] = {r[1] for r in _cp().tree(league)} | trees.get(me, set())
    out = sorted(((n, len(v), n == me) for n, v in trees.items()), key=lambda x: (-x[1], x[0]))
    return out


def _games_vs(league, name):
    import cp_ach
    out = []
    for y, g, t in cp_ach.my_games(league):
        hc = {getattr(k, "school", k): v for k, v in (getattr(g, "hc", None) or {}).items()}
        opp = g.opponent_of(t)
        if hc.get(getattr(opp, "school", opp)) == name:
            out.append((y, g, t, opp))
    return out


def detail(league, row):
    c, name, roles, now, rec = row
    clear()
    print(title_bar(f"COACHING TREE · {name.upper()}"))
    print(f"\n   {paint(name, C.BWHITE, C.BOLD)}   {paint(now, C.BGREEN if now.startswith('head coach') else C.BWHITE)}"
          + (paint(f"   {rec}", C.GRAY) if rec else ""))
    if c is not None:
        bits = []
        if getattr(c, "overall", None):
            import scout
            bits.append(f"coach rating {scout.team(c.overall)}")
        if getattr(c, "offense_scheme", None):
            bits.append(f"{c.offense_scheme} offense")
        if getattr(c, "age", None):
            bits.append(f"age {c.age}")
        if bits:
            print(paint("   " + " · ".join(bits), C.GRAY))
    print(section("UNDER YOU", C.BYELLOW))
    for y, school, role in roles:
        print(f"   {pad(str(y), 7)}{pad(school or '', 22)}{role}")
    if c is not None:
        path = _coord_history(c)
        hist = _hc_history(c)
        if path or hist:
            print(section("HIS CAREER", C.BCYAN))
            for e in sorted(path, key=lambda e: e.get("year") or 0)[-8:]:
                print(clip(f"   {pad(str(e.get('year')), 7)}{pad(e.get('school') or '', 22)}{pad(e.get('role') or '', 22)}"
                           f"{paint('under ' + e['hc'] if e.get('hc') else '', C.GRAY)}", WIDTH))
            for h in hist[-8:]:
                print(clip(f"   {pad(str(h.get('year')), 7)}{pad(h.get('school', ''), 22)}{pad('head coach', 22)}"
                           f"{h.get('w', 0)}-{h.get('l', 0)}" + (paint("  national champions", C.BYELLOW) if h.get("title") else
                                                                  paint(f"  {h['post']}", C.GRAY) if h.get("post") else ""), WIDTH))
    games = _games_vs(league, name)
    print(section(f"AGAINST YOU · {sum(1 for _y, g, t, _o in games if getattr(g.winner, 'school', None) == getattr(t, 'school', t))}-"
                  f"{sum(1 for _y, g, t, _o in games if getattr(g.winner, 'school', None) != getattr(t, 'school', t))}", C.BMAGENTA))
    if not games:
        print(paint("   You've never met.", C.GRAY))
    for y, g, t, opp in games[-8:]:
        won = getattr(g.winner, "school", None) == getattr(t, "school", t)
        print(f"   {pad(str(y), 7)}{paint('W' if won else 'L', C.BGREEN if won else C.BRED, C.BOLD)} "
              f"{g.score_for(t)}-{g.score_for(opp)}  {'vs' if g.home is t else 'at'} {opp.school}")
    pause()


def screen(league):
    cp = _cp()
    mode = "tree"
    while True:
        rows = cp.tree(league)
        clear()
        print(title_bar(f"COACHING TREE · {league.user_coach.name.upper()}"))
        if not rows:
            print(paint("\n   Nobody yet. Every coordinator and position coach who works for you joins your tree, and you'll\n"
                        "   see where they go: the ones who become head coaches, and how you do against them.", C.GRAY))
            pause()
            return
        s = stats(league, rows)
        print(f"\n   {paint(str(s['n']), C.BWHITE, C.BOLD)} coaches have worked for you · "
              f"{paint(str(s['heads']), C.BGREEN, C.BOLD)} head coach{'es' if s['heads'] != 1 else ''} · "
              f"{paint(str(s['coords']), C.BCYAN, C.BOLD)} coordinators"
              + (f" · as head coaches: {s['w']}-{s['l']}" if s['w'] + s['l'] else "")
              + (paint(f" · {s['titles']} national title{'s' if s['titles'] != 1 else ''}", C.BYELLOW) if s["titles"] else ""))
        if mode == "tree":
            print(paint(f"\n   {'':5}{'COACH':<22}{'UNDER YOU':<28}{'NOW':<32}VS YOU", C.GRAY, C.BOLD))
            for i, (c, name, roles, now, rec) in enumerate(rows[:24], 1):
                span = (f"{roles[0][2]} {roles[0][0]}" + (f"–{roles[-1][0]}" if roles[-1][0] != roles[0][0] else "")) if roles else ""
                h2h = ""
                if now.startswith("head coach"):
                    w, l_ = cp.head_to_head(league, name)
                    h2h = f"{w}-{l_}" if w + l_ else "never met"
                col = C.BGREEN if now.startswith("head coach") else C.BWHITE if "coordinator" in now else C.GRAY
                print(clip(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)}{pad(truncate(name, 21), 22)}{pad(truncate(span, 27), 28)}"
                           f"{paint(pad(truncate(now, 31), 32), col)}{paint(h2h, C.BYELLOW)}", WIDTH))
            if len(rows) > 24:
                print(paint(f"   …and {len(rows) - 24} more.", C.GRAY))
        elif mode == "gen":
            print(section("THE SECOND GENERATION · WHO WORKED FOR YOUR ASSISTANTS", C.BCYAN))
            gen = second_gen(league, rows)
            if not gen:
                print(paint("   Nobody yet. When your assistants become head coaches, their staffs grow your tree too.", C.GRAY))
            for branch, kids in gen[:8]:
                print(f"   {paint(branch, C.BGREEN, C.BOLD)}  {paint(f'{len(kids)} assistant' + ('s' if len(kids) != 1 else ''), C.GRAY)}")
                for n_, y, sch, role in kids[:4]:
                    print(clip(f"      └ {pad(truncate(n_, 22), 23)}{paint(f'{role} at {sch}, {y}', C.GRAY)}", WIDTH))
        else:
            print(section("THE SPORT'S BIGGEST COACHING TREES", C.BYELLOW))
            big = biggest(league)
            mine_i = next((i for i, r in enumerate(big, 1) if r[2]), None)
            for i, (n_, k, me) in enumerate(big[:12], 1):
                print(f"   {paint(f'{i:>2}.', C.GRAY)} {paint(pad(n_, 26), C.BGREEN if me else C.BWHITE, C.BOLD if me else '')}{k}")
            if mine_i and mine_i > 12:
                print(paint(f"   …you're No. {mine_i} with {big[mine_i - 1][1]}.", C.BGREEN))
        footer(*([key("#", "open a coach")] if mode == "tree" else [key("T", "the tree")]),
               key("G", "second generation"), key("S", "biggest trees"), key("B", "back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c.isdigit() and mode == "tree" and 1 <= int(c) <= min(24, len(rows)):
            detail(league, rows[int(c) - 1])
        elif c == "g":
            mode = "gen"
        elif c == "s":
            mode = "big"
        elif c == "t":
            mode = "tree"
        else:
            return


def news(league):
    """Week 1 and season end: a branch that moved is a story."""
    cp = _cp()
    if not cp.mine(league):
        return
    st = cp.state(league)
    was = st.setdefault("tree_now", {})
    for c, name, roles, now, rec in cp.tree(league):
        old = was.get(name)
        was[name] = now
        if old is None or old == now:
            continue
        last = roles[-1] if roles else None
        under = f"your {last[2]} at {last[1]} in {last[0]}" if last else "one of your assistants"
        if now.startswith("head coach") and not old.startswith("head coach"):
            cp._story(league, "tree", f"Coaching tree: {name}, {under}, is the new {now}.")
            cp.state(league)["stories"][-1]["w"] = 40
        elif "coordinator" in now and "coordinator" not in old:
            cp._story(league, "tree", f"Coaching tree: {name} ({under}) is now {now}.")
