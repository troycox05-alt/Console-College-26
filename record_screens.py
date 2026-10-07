"""
record_screens.py — The record book on screen (Rankings tab -> [R], team page -> [R]).

National or any school; players (single game, season, career), teams (game,
season, streaks) and coaches. The season board mixes in this year's leaders while
the season is on, and the career board counts active players week by week.
"""
import records
from ui import (C, ask, back_key, clear, footer, key, menu_item, pad, paint, pause, section, title_bar, truncate)

VIEWS = [("G", "Single game", "players"), ("S", "Single season", "players"), ("R", "Career", "players"),
         ("T", "Team: game", "team"), ("Y", "Team: season", "team"), ("H", "Coaches", "coach")]


def hub(league, school=None):
    view = "S"
    top_n = 3
    while True:
        b = records.book(league)
        clear()
        scope = school or "FBS"
        print(title_bar(f"RECORD BOOK · {scope.upper()}", sub=f"KEPT SINCE {b.since or league.year}"))
        if b.since is None:
            print(paint(f"\n   Records are kept from the first game of {league.year}. The book fills in as the season is played.",
                        C.GRAY))
        tabs = "  ".join((paint(f"[{k}] {name}", C.BYELLOW, C.BOLD) if k == view else paint(f"[{k}] {name}", C.GRAY))
                         for k, name, _ in VIEWS)
        print("  " + tabs)
        print()
        _render(league, view, school, top_n)
        mine = _mine(league)
        items = [key("N", "national") if school else key("O", "a school"),
                 key("M", f"{mine}") if mine and school != mine else "",
                 key("O", "another school") if school else "",
                 key("+", "top 10" if top_n == 3 else "top 3"), back_key()]
        footer(*[i for i in items if i])
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c.upper() in {k for k, _, _ in VIEWS}:
            view = c.upper()
        elif c == "n":
            school = None
        elif c == "m" and mine:
            school = mine
        elif c == "o":
            from screens import pick_team
            t = pick_team(league)
            if t is not None:
                school = t.school
        elif c == "+":
            top_n = 10 if top_n == 3 else 3


def _mine(league):
    t = getattr(league, "user_team", None)
    if t is None and getattr(league, "user_coach", None) is not None:
        t = league.user_coach.team
    if t is None:
        t = getattr(league, "follow_team", None)
    return t.school if t is not None else None


def _row(place, e, national, width_detail=34, show_year=True):
    val = pad(paint(records.fmt("", e[0]), C.BWHITE, C.BOLD), 8, "right")
    who = pad(truncate(e[1], 22), 23)
    pos = pad(paint(e[2], C.BCYAN), 4) if e[2] else ""
    where = pad(truncate(e[3], 17), 18) if national else ""
    yr = paint(str(e[4]), C.GRAY) if show_year else ""
    wk = paint(f" wk {e[5]}", C.GRAY) if e[5] else ""
    det = paint(truncate(e[6], width_detail), C.GRAY) if e[6] else ""
    mark = paint("★", C.BYELLOW) if place == 1 else " "
    return f"   {mark}{place:>2}. {val}  {who}{pos}{where}{yr}{wk}  {det}"


def _render(league, view, school, n):
    national = school is None
    b = records.book(league)
    if view in ("G", "S", "R"):
        for grp, keys in records.GROUPS:
            if view in ("S", "R"):
                keys = [k for k in keys if k in records.CAREER_KEYS]     # longs are single plays: game view only
            if not keys:
                continue
            print(section(grp, C.BCYAN))
            for k in keys:
                if view == "G":
                    board = b.game.get(school or records.NATIONAL, {}).get(k, [])[:n]
                elif view == "S":
                    board = records.season_board(league, k, school=school, n=n)
                else:
                    board = records.career_board(league, k, school=school, n=n)
                print(paint(f"   {records.LABEL[k]}", C.BWHITE))
                if not board:
                    print(paint("        —", C.GRAY))
                for i, e in enumerate(board, 1):
                    print(_row(i, e, national, show_year=view != "R"))
    elif view in ("T", "Y"):
        store = b.team_game if view == "T" else b.team_season
        labels = records.TEAM_GAME if view == "T" else records.TEAM_SEASON
        for k, label in labels:
            board = store.get(school or records.NATIONAL, {}).get(k, [])[:n]
            print(section(label.upper(), C.BCYAN))
            if not board:
                print(paint("        —", C.GRAY))
            for i, e in enumerate(board, 1):
                e2 = (e[0], e[1], "", "", e[4], e[5], e[6], e[7])
                print(_row(i, e2, False))
        if view == "Y":
            live = sorted(((s, sch) for sch, s in b.streaks.items() if s >= 3 and (school is None or sch == school)),
                          reverse=True)[:5]
            if live:
                print(section("ACTIVE WINNING STREAKS", C.BGREEN))
                for s, sch in live:
                    print(f"      {paint(str(s), C.BWHITE, C.BOLD):>12}  {sch}")
    else:
        for k, label in records.COACH_KEYS:
            board = records.coach_board(league, k, school=school, n=n)
            print(section(label.upper() + (f" AT {school.upper()}" if school else ""), C.BCYAN))
            if not board:
                print(paint("        —", C.GRAY))
            for i, e in enumerate(board, 1):
                print(_row(i, e, national, show_year=False))
        print(paint("\n   Coaches' records count games coached from 2026 on.", C.GRAY))
