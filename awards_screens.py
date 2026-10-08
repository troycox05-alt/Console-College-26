"""
awards_screens.py — Awards Season and the NFL Draft, in the offseason and in the
Media Center archive.
"""
from ui import C, WIDTH, ask, clear, columns, pad, paint, pause, rating, rule, section, title_bar, truncate

GROUP_ORDER = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB", "K", "P"]


def awards_screen(league, year=None):
    aw = getattr(league, "awards", {}).get(year or max(getattr(league, "awards", {}) or [0]))
    clear()
    if not aw:
        print(title_bar("AWARDS SEASON"))
        print(paint("   No awards handed out yet — they come at the end of the season.", C.GRAY))
        pause()
        return
    print(title_bar(f"{aw['year']} AWARDS SEASON"))
    you = getattr(league, "user_team", None)
    mark = lambda t: paint(" ★", C.BMAGENTA) if you is not None and t is you else ""
    if aw["heisman"]:
        p, t, line = aw["heisman"]
        print(section("HEISMAN TROPHY", C.BYELLOW))
        import faces
        if faces.enabled():
            import faces_ui
            for ln in faces_ui.winner_hero(p, t, line, league.team_color(t), mark(t)):
                print(ln)
        else:
            print(f"   {paint(p.name, C.BWHITE, C.BOLD)}  {paint(f'{p.position} · {t.school}', C.GRAY)}{mark(t)}   {line}")
        print()
    print(section("THE BEST AT EVERY POSITION", C.BCYAN))
    for name, p, t, line in aw["positional"]:
        print(f"   {pad(paint(name, C.BYELLOW), 26)}{pad(p.name, 24)}{pad(t.school, 20)}{paint(line, C.GRAY)}{mark(t)}")
    extra = []
    if aw["freshman"]:
        p, t, line = aw["freshman"]
        extra.append(("Freshman of the Year", p.name, t, line))
    if aw["coach"]:
        name, t, rec = aw["coach"]
        extra.append(("Coach of the Year", name, t, rec))
    import faces
    if faces.enabled() and extra:
        import faces_ui
        cards = []
        for label, who, t, line in extra:
            if label.startswith("Freshman"):
                face = faces.player_portrait(aw["freshman"][0], team=t, year=0, mini=True)
            else:
                c = t.coach if t.coach is not None and t.coach.name == who else None
                face = faces.coach_portrait(c, mini=True) if c is not None else \
                    faces.name_portrait(who, school=t.school, role="coach", age=getattr(t.coach, "age", 50), mini=True)
            cards.append(faces_ui.mini_card(face, [paint(label, C.BYELLOW, C.BOLD), paint(who, C.BWHITE, C.BOLD),
                                                   paint(t.school, league.team_color(t)) + mark(t),
                                                   paint(truncate(str(line), 30), C.GRAY)], 49,
                                            league.team_color(t)))
        print()
        for ln in columns(*cards, gap=1):
            print(ln)
    else:
        for label, who, t, line in extra:
            print(f"   {pad(paint(label, C.BYELLOW), 26)}{pad(who, 24)}{pad(t.school, 20)}{paint(line, C.GRAY)}{mark(t)}")
    for which, title in (("first", "FIRST-TEAM ALL-AMERICA"), ("second", "SECOND-TEAM ALL-AMERICA")):
        print()
        print(section(title, C.BGREEN if which == "first" else C.GRAY))
        rows = sorted(aw[which], key=lambda x: GROUP_ORDER.index(x[0]))
        half = (len(rows) + 1) // 2
        for a, b in zip(rows[:half], rows[half:] + [None] * (2 * half - len(rows))):
            cells = []
            for r in (a, b):
                if r:
                    grp, p, t = r
                    cells.append(f"{paint(f'{grp:<3}', C.GRAY)}{pad(truncate(p.name, 20), 21)}{pad(truncate(t.school, 16), 17)}{mark(t)}")
            print("   " + pad(cells[0], 46) + (cells[1] if len(cells) > 1 else ""))
    import webview
    if webview.on():
        try:
            me = lambda t: you is not None and t is you
            d = {"year": aw["year"], "positional": [{"award": n, "name": p.name, "id": webview.pid(p), "school": t.school,
                                                    "line": webview.plain(line), "me": me(t)} for n, p, t, line in aw["positional"]],
                 "extra": [{"award": l, "name": w, "school": t.school, "line": webview.plain(str(ln)), "me": me(t)} for l, w, t, ln in extra]}
            if aw["heisman"]:
                p, t, line = aw["heisman"]
                d["heisman"] = {"name": p.name, "id": webview.pid(p), "pos": p.position, "school": t.school,
                                "line": webview.plain(line), "me": me(t), "color": webview._color(league, t)}
            for which in ("first", "second"):
                d[which] = [{"grp": g, "name": p.name, "id": webview.pid(p), "school": t.school, "me": me(t)}
                            for g, p, t in sorted(aw[which], key=lambda x: GROUP_ORDER.index(x[0]))]
            webview.emit("awards", d)
        except Exception:
            pass
    pause()


def draft_screen(league, year=None):
    drafts = getattr(league, "drafts", {})
    if not drafts:
        clear()
        print(title_bar("NFL DRAFT"))
        print(paint("   No drafts yet — the first one comes after this season.", C.GRAY))
        pause()
        return
    year = year or max(drafts)
    picks = drafts[year]
    view = "round1"
    you = getattr(league, "user_team", None)
    while True:
        clear()
        print(title_bar(f"{year} NFL DRAFT"))
        early = sum(1 for x in picks if x["early"])
        print(paint(f"   {len(picks)} players drafted  ·  {early} underclassmen  ·  "
                    f"{len({x['school'] for x in picks})} schools", C.GRAY))
        if view == "round1" or view.startswith("r"):
            rnd = 1 if view == "round1" else int(view[1:])
            print(section(f"ROUND {rnd}", C.BYELLOW))
            import faces
            if rnd == 1 and faces.enabled():                 # the top three picks, with their faces
                import faces_ui
                top3 = [x for x in picks if x["round"] == 1][:3]
                for ln in columns(*[faces_ui.pick_card(x, you.school if you is not None else None) for x in top3], gap=1):
                    print(ln)
                print()
            for x in [x for x in picks if x["round"] == rnd]:
                star = paint(" ★", C.BMAGENTA) if you is not None and x["school"] == you.school else ""
                tag = paint(" (early)", C.GRAY) if x["early"] else ""
                print(f"   {paint(str(x['overall_pick']).rjust(3), C.GRAY)}  "
                      f"{pad(x['nfl'], 16)}{pad(x['name'], 24)}{x['pos']:<4}{pad(x['school'], 20)}{x['cls']}{tag}{star}")
        elif view == "schools":
            print(section("PICKS BY SCHOOL", C.BCYAN))
            from collections import Counter
            n = Counter(x["school"] for x in picks)
            r1 = Counter(x["school"] for x in picks if x["round"] == 1)
            for school, k in n.most_common(20):
                star = paint(" ★", C.BMAGENTA) if you is not None and school == you.school else ""
                print(f"   {pad(school, 22)}{k:>3} picks   {paint(f'{r1[school]} in round 1', C.GRAY)}{star}")
        elif view == "yours" and you is not None:
            mine = [x for x in picks if x["school"] == you.school]
            print(section(f"{you.school.upper()} PICKS", C.BMAGENTA))
            for x in mine:
                print(f"   Round {x['round']}, pick {x['overall_pick']:>3}  {pad(x['nfl'], 16)}{pad(x['name'], 24)}{x['pos']}")
            if not mine:
                print(paint("   None this year.", C.GRAY))
            bonus = getattr(you, "draft_bonus", 0)
            print(paint(f"\n   Draft prestige bonus for {you.school}: +{bonus:.1f}", C.GRAY))
        print(rule())
        print(f"   {paint('[1-7]', C.BYELLOW)} a round   {paint('[S]', C.BYELLOW)} by school"
              + (f"   {paint('[Y]', C.BYELLOW)} your picks" if you is not None else "")
              + f"   {paint('[B]', C.GRAY)} back")
        import webview
        if webview.on():
            try:
                from collections import Counter
                d = {"year": year, "view": view, "n": len(picks), "early": early, "schools": len({x["school"] for x in picks}),
                     "you": you.school if you is not None else ""}
                if view == "round1" or view.startswith("r"):
                    rnd = 1 if view == "round1" else int(view[1:])
                    d["round"] = rnd
                    d["picks"] = [{"pick": x["overall_pick"], "nfl": x["nfl"], "name": x["name"], "pos": x["pos"], "school": x["school"],
                                   "cls": x["cls"], "early": bool(x["early"]), "me": you is not None and x["school"] == you.school}
                                  for x in picks if x["round"] == rnd]
                elif view == "schools":
                    n = Counter(x["school"] for x in picks)
                    r1 = Counter(x["school"] for x in picks if x["round"] == 1)
                    d["bySchool"] = [{"school": s, "n": k, "r1": r1[s], "me": you is not None and s == you.school} for s, k in n.most_common(20)]
                elif view == "yours" and you is not None:
                    d["mine"] = [{"round": x["round"], "pick": x["overall_pick"], "nfl": x["nfl"], "name": x["name"], "pos": x["pos"]}
                                 for x in picks if x["school"] == you.school]
                    d["bonus"] = round(getattr(you, "draft_bonus", 0), 1)
                webview.emit("draft", d)
            except Exception:
                pass
        c = ask("Select:").strip().lower()
        if c.isdigit() and 1 <= int(c) <= 7:
            view = f"r{c}"
        elif c == "s":
            view = "schools"
        elif c == "y" and you is not None:
            view = "yours"
        else:
            return
