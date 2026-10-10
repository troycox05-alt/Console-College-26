"""
scheme_change.py — Change your own offense or defense mid-career (My career -> [K]).

A new system isn't free. The players are learning new calls, new reads, new footwork, so for a
stretch of games the team plays a little below itself, and the cost fades a bit every game:

  In-season change     8 games to install it, starting at about -1.6 form (≈ 2.7 points a game)
  Offseason change     4 games, starting at about -0.8 (spring ball and camp do most of the work)

Only the side you actually call plays for pays the full price; if a coordinator calls it, the new
scheme is yours on paper and the cost is a quarter as big. One change per side per season.
"""
from ui import C, ask, clear, menu_item, paint, pause, rule, title_bar

IN_SEASON = (8, 1.6)
OFFSEASON = (4, 0.8)


def _installs(team):
    return team.__dict__.setdefault("scheme_installs", [])


def penalty(team):
    """Form points the team loses this game to systems it's still installing (negative or 0)."""
    total = 0.0
    for d in team.__dict__.get("scheme_installs", []) or []:
        total += d["start"] * d["weight"] * d["left"] / d["games"]
    return -round(total, 2)


def after_game(team):
    """One more game of reps in the new system."""
    xs = team.__dict__.get("scheme_installs")
    if not xs:
        return
    for d in xs:
        d["left"] -= 1
    team.__dict__["scheme_installs"] = [d for d in xs if d["left"] > 0]


def status_lines(team):
    out = []
    for d in team.__dict__.get("scheme_installs", []) or []:
        done = d["games"] - d["left"]
        out.append(f"Installing the {d['scheme']} ({'offense' if d['side'] == 'off' else 'defense'}): "
                   f"{done}/{d['games']} games in, costing about {d['start'] * d['weight'] * d['left'] / d['games']:.1f} form")
    return out


def _offseason(league):
    return bool(league.season_complete or league.week == 0)


def change(league, team, coach, side, scheme):
    """Switch the coach's scheme on one side and start the install. Returns the install record."""
    import staff
    games, start = OFFSEASON if _offseason(league) else IN_SEASON
    calls_it = staff.play_caller(team, side) is coach
    weight = 1.0 if calls_it else 0.25
    old = coach.offense_scheme if side == "off" else coach.defense_scheme
    if side == "off":
        coach.offense_scheme = scheme
    else:
        coach.defense_scheme = scheme
    xs = [d for d in _installs(team) if d["side"] != side]        # a second switch replaces the first install
    rec = {"side": side, "scheme": scheme, "old": old, "games": games, "left": games, "start": start,
           "weight": weight, "year": league.year}
    xs.append(rec)
    team.__dict__["scheme_installs"] = xs
    coach.__dict__.setdefault("scheme_changed", {})[side] = league.year
    return rec


def screen(league, coach, team):
    import playbook as pb
    import staff
    msg = ""
    while True:
        clear()
        print(title_bar(f"CHANGE YOUR SCHEMES  ·  COACH {coach.name.upper()}"))
        off_by, def_by = staff.caller_label(team, "off"), staff.caller_label(team, "def")
        games, start = OFFSEASON if _offseason(league) else IN_SEASON
        print(f"\n   Offense: {paint(coach.offense_scheme, C.BWHITE, C.BOLD)}   {paint('(plays called by ' + off_by + ')', C.GRAY)}")
        print(f"   Defense: {paint(coach.defense_scheme, C.BWHITE, C.BOLD)}   {paint('(plays called by ' + def_by + ')', C.GRAY)}")
        when = "offseason" if _offseason(league) else "in-season"
        print(paint(f"\n   A switch now is an {when} install: {games} games to learn it, starting at about "
                    f"-{start:.1f} form (≈ {start * 1.7:.1f} points a game) and fading every game.", C.GRAY))
        print(paint("   Only the side you call plays for pays the full price; a coordinator's side costs a quarter of it.",
                    C.GRAY))
        for ln in status_lines(team):
            print(paint("   " + ln, C.BYELLOW))
        if msg:
            print(paint("\n   " + msg, C.BGREEN, C.BOLD))
            msg = ""
        print(rule())
        done = coach.__dict__.get("scheme_changed", {})
        print(menu_item("O", "Change my offense", "already switched this season" if done.get("off") == league.year else ""))
        print(menu_item("D", "Change my defense", "already switched this season" if done.get("def") == league.year else ""))
        print(menu_item("B", "Back", ""))
        import webview
        if webview.on():
            webview.emit("schemes", {"name": coach.name, "off": coach.offense_scheme, "def": coach.defense_scheme,
                                     "offBy": off_by, "defBy": def_by, "when": when, "games": games, "start": start,
                                     "installs": status_lines(team),
                                     "offDone": done.get("off") == league.year, "defDone": done.get("def") == league.year})
        c = ask("Select:").strip().lower()
        if c in ("", "b"):
            return
        if c not in ("o", "d"):
            continue
        side = "off" if c == "o" else "def"
        if done.get(side) == league.year:
            msg = "One change per side per season — the players need to settle."
            continue
        options = list(pb.OFFENSE_SCHEMES if side == "off" else pb.DEFENSE_SCHEMES)
        cur = coach.offense_scheme if side == "off" else coach.defense_scheme
        clear()
        print(title_bar(f"NEW {'OFFENSE' if side == 'off' else 'DEFENSE'}"))
        print()
        for i, name in enumerate(options, 1):
            print(menu_item(str(i), name, "current" if name == cur else ""))
        if webview.on():
            webview.emit("schemepick", {"side": side, "current": cur,
                                        "options": [{"key": str(i), "name": n, "current": n == cur} for i, n in enumerate(options, 1)]})
        pick = ask("Scheme # (Enter = cancel):").strip()
        if not pick.isdigit() or not 1 <= int(pick) <= len(options) or options[int(pick) - 1] == cur:
            continue
        new = options[int(pick) - 1]
        if ask(f"Switch to the {new}? The team will spend {games} games learning it. (y/n):").strip().lower() != "y":
            continue
        rec = change(league, team, coach, side, new)
        msg = (f"You're installing the {new}. {rec['games']} games to learn it"
               + ("" if rec["weight"] == 1.0 else " — your coordinator calls that side, so the cost is small") + ".")
