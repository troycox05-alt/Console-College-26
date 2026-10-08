"""
halftime.py — Your halftime adjustments (Career mode, your games).

At the half of every game you coach — simmed, big moments, every snap or the
broadcast — the game stops in the locker room. You see the first half, what
your staff is seeing, and make two calls:

  THE ADJUSTMENT (how you play the second half)
    Trust the staff        the staff's own adjustments stand (they make them either way)
    Lean on the run        more runs, clock keeps moving — fewer big plays
    Air it out             more shots downfield — more sacks, picks and stopped clocks
    Bring pressure         more blitzes — more sacks and negative plays, more big plays allowed
    Sit back in coverage   take away the deep ball — they can dink and run on you
    Protect the lead       (ahead) run it, punt it, play coverage, steady late — you may play not to lose
    Go for broke           (behind) fourth downs, trick plays, shots — could get ugly

  THE MESSAGE (what you say before they go back out)
    Let the coordinators talk   nothing changes
    Calm and clear              a small, sure lift, steadier late
    Light into them             a big lift if it lands — and if it doesn't, the room tightens up.
                                A warm locker room takes it better; so does a team that's behind.

The second half is played with your calls. The postgame podium and box score
know what you did at the half. Settings → [4] turns halftime stops off.
"""
from ui import C, ask, pad, paint, title_bar

ADJUST = {
    "staff":   ("Trust the staff", {}, [(True, "the staff's adjustments stand")]),
    "run":     ("Lean on the run", {"run": 0.16, "fam": {"deep": 0.8}},
                [(True, "more runs · clock keeps moving"), (False, "fewer big plays")]),
    "air":     ("Air it out", {"run": -0.16, "fam": {"deep": 1.45, "play_action": 1.2}},
                [(True, "more shots downfield"), (False, "more sacks and picks · clock stops")]),
    "press":   ("Bring pressure", {"blitz": 1.6},
                [(True, "more sacks and negative plays"), (False, "more big plays allowed")]),
    "cover":   ("Sit back in coverage", {"blitz": 0.6, "shell": 1.4},
                [(True, "take away the deep ball"), (False, "they can run and dink on you")]),
    "protect": ("Protect the lead", {"run": 0.12, "aggr": -25, "blitz": 0.8, "clutch": 0.3},
                [(True, "steadier late · fewer mistakes"), (False, "you may play not to lose")]),
    "broke":   ("Go for broke", {"aggr": 30, "trick": 2.5, "fam": {"deep": 1.3}, "run": -0.1, "clutch": -0.1},
                [(True, "fourth downs, trick plays, shots"), (False, "could get ugly")]),
}

MESSAGE = {
    "none":  ("Let the coordinators talk.", [(None, "nothing changes")]),
    "calm":  ("Calm and clear. Fix one thing at a time.", [(True, "small, sure lift · steadier late")]),
    "fire":  ("Light into them.", None),
}

STAFF_READ = {
    "half_run": "The run game's working better than the pass. Keep feeding it.",
    "half_pass": "The run's going nowhere. We should throw it.",
    "half_less_blitz": "Our blitzes are getting burned. Back off the pressure.",
    "half_two_high": "They're hitting us deep. We need two safeties back.",
    "half_box": "They're running on us. We need an extra man in the box.",
}


def _line(parts):
    return paint(" · ", C.GRAY).join(paint(t, C.BGREEN if g is True else C.BRED if g is False else C.BYELLOW)
                                     for g, t in parts)


def _fire_odds(sim, team):
    import personalities
    chem = personalities.chemistry(team)
    diff = sim.score[team] - sim.score[sim.other(team)]
    odds = 0.45 + (chem - 50) / 150 + (0.1 if diff < 0 else -0.05 if diff >= 14 else 0)
    tr = getattr(team.coach, "traits", []) or []
    if "players_coach" in tr or "motivator" in tr:
        odds += 0.1
    import skills
    if skills.team_has(team, "halftime_speech"):
        odds += 0.15                                               # Halftime Speech (coaching tree)
    return max(0.2, min(0.9, odds))


def ask_coach(sim):
    """Called from the sim at halftime when you're coaching this game."""
    team = sim.game.__dict__.get("halftime_team")
    if team is None or team not in sim.teams:
        return
    import settings
    if not settings.load().get("halftime", True):
        return
    opp = sim.other(team)
    us, them = sim.score[team], sim.score[opp]
    ts, os_ = sim.team_stats[team], sim.team_stats[opp]
    print()
    print(title_bar(f"HALFTIME  ·  {team.school.upper()} {us}, {opp.school.upper()} {them}"))
    print()
    for t, st in ((team, ts), (opp, os_)):
        print(f"   {pad(paint(t.school, C.BWHITE, C.BOLD), 24)} {st['rush_yds']:>4} rush  {st['pass_yds']:>4} pass  "
              f"{st['first_downs']:>3} first downs  {st['turnovers']} TO")
    plays = [e for e in sim.scoring if e[0] <= 2]
    if plays:
        from commentary import clock_str
        print()
        print(paint("   FIRST-HALF SCORING", C.GRAY, C.BOLD))
        for e in plays[-8:]:
            q, clk, who, desc = e[0], e[1], e[2], e[3]
            print(paint(f"   Q{q} {clock_str(clk):>5}  {pad(who.school[:16], 17)}{desc}",
                        C.BWHITE if who is team else C.GRAY))
    import sideline
    check = sideline.plan_check(sim, team)
    if check:
        print()
        print(paint("   THE GAME PLAN", C.GRAY, C.BOLD))
        for label, verdict, col in check:
            print(f"   {pad(label, 32)} " + paint(verdict, col))
    reads = [STAFF_READ[k] for _, k, _ in sim.plan[team].notes if k in STAFF_READ][-2:]
    if reads:
        print()
        for r in reads:
            print(paint("   Staff: " + r, C.BCYAN))
    import webview
    if webview.on():
        try:
            from commentary import clock_str
            webview.emit("half", {"us": {"school": team.school, "score": us, "stats": ts}, "them": {"school": opp.school, "score": them, "stats": os_},
                                  "scoring": [{"q": e[0], "clock": clock_str(e[1]), "team": e[2].school, "mine": e[2] is team,
                                               "what": webview.plain(e[3])} for e in plays[-8:]],
                                  "plan": [{"label": l_, "verdict": webview.plain(v_)} for l_, v_, _ in (check or [])],
                                  "reads": list(reads)})
        except Exception:
            pass
    diff = us - them
    off_keys = ["staff", "run", "air"]
    off_keys.append("protect" if diff > 0 else "broke" if diff < 0 else "protect")
    if diff == 0:
        off_keys.append("broke")
    def_keys = ["staff", "press", "cover"]
    picks = []
    for title, keys, side in (("THE ADJUSTMENT  ·  OFFENSE", off_keys, "Offense"),
                              ("THE ADJUSTMENT  ·  DEFENSE", def_keys, "Defense")):
        print()
        print(paint("   " + title, C.BYELLOW, C.BOLD))
        for i, k in enumerate(keys, 1):
            label, _, parts = ADJUST[k]
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(label, 22)} {_line(parts)}")
        webview.emit("opts", {"title": title.replace("  ·  ", " · "), "options": [
            {"key": str(i), "label": ADJUST[k][0], "line": webview.plain(_line(ADJUST[k][2]))} for i, k in enumerate(keys, 1)]}, add=True)
        c = ask(f"{side} in the second half (Enter = trust the staff):").strip()
        picks.append(keys[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(keys) else "staff")
    pick = tuple(picks)
    odds = _fire_odds(sim, team)
    print()
    print(paint("   THE MESSAGE", C.BYELLOW, C.BOLD))
    msgs = list(MESSAGE)
    for i, k in enumerate(msgs, 1):
        label, parts = MESSAGE[k]
        if parts is None:
            parts = [(None, f"{int(odds * 100)}%: big lift / else: the room tightens up")]
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(label, 42)} {_line(parts)}")
    webview.emit("opts", {"title": "The message", "options": [
        {"key": str(i), "label": MESSAGE[k][0],
         "line": webview.plain(_line(MESSAGE[k][1] if MESSAGE[k][1] is not None else
                                     [(None, f"{int(odds * 100)}%: big lift / else: the room tightens up")]))}
        for i, k in enumerate(msgs, 1)]}, add=True)
    c = ask("What do you tell them? (Enter = let the coordinators talk):").strip()
    say = msgs[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(msgs) else "none"
    result = apply(sim, team, pick, say, odds)
    print(paint("   → " + result, C.BCYAN))
    webview.emit("res", {"text": webview.plain(result)}, add=True)
    print()


def apply(sim, team, pick, say, odds=0.5):
    """Put the calls on the second half. Returns a line describing it."""
    picks = pick if isinstance(pick, tuple) else (pick,)
    adj = {}
    for pk in picks:                                      # offense call first, then defense (its pressure wins)
        adj.update(ADJUST[pk][1])
    labels = [ADJUST[pk][0] for pk in picks if pk != "staff"] or [ADJUST["staff"][0]]
    import skills
    boost = 1.5 if skills.team_has(team, "halftime_genius") else 1.0     # Halftime Genius (coaching tree)
    if boost != 1.0:
        adj = {k: (({f: 1 + (m - 1) * boost for f, m in v.items()}) if k == "fam" else
                   (1 + (v - 1) * boost) if k in ("blitz", "shell", "trick") else v * boost)
               for k, v in adj.items()}
    plan = sim.plan[team]
    plan.adj = dict(adj)
    if adj.get("clutch"):
        sim.clutch[team] = max(-1.6, min(2.4, sim.clutch[team] + adj["clutch"]))
    out = [" / ".join(labels) + "."]
    landed = None
    if say == "calm":
        sim.form[team] += 0.25
        sim.clutch[team] = max(-1.6, min(2.4, sim.clutch[team] + 0.15))
        out.append("They go back out settled.")
    elif say == "fire":
        landed = sim.rng.random() < odds
        if landed:
            sim.form[team] += 0.8
            out.append("It landed. They came out of the tunnel like a different team.")
        else:
            sim.form[team] -= 0.3
            sim.clutch[team] = max(-1.6, sim.clutch[team] - 0.2)
            out.append("It didn't land. Guys are pressing.")
    sim._prof.clear()                                     # ratings are cached with the old form
    sim.game.halftime_call = {"adjust": " / ".join(labels), "say": say, "landed": landed,
                              "half": (sim.score[team], sim.score[sim.other(team)]), "team": team.school}
    try:
        if say == "fire":
            import morale
            starters = [p for grp in team.starters().values() for p in grp]
            for p in starters:
                morale.nudge(p, 1 if landed else -2)
    except Exception:
        pass
    return " ".join(out)


def second_half(g, team):
    """(label, first-half score, second-half score) for the postgame."""
    call = getattr(g, "halftime_call", None)
    if not call or call.get("team") != team.school:
        return None
    us_h, them_h = call["half"]
    opp = g.opponent_of(team)
    return call, (us_h, them_h), (g.score_for(team) - us_h, g.score_for(opp) - them_h)
