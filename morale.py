"""
morale.py — Every player's mood, 0 to 100.

Chemistry (personalities.py) is the temperature of the whole room. Morale is
each player's own: is he playing, is he winning, is he paid, did you keep your
word. It moves a little every week and a lot when you make a call about him.

WHERE IT COMES FROM (weekly, every roster in the country)
  Playing time    starters climb; a backup who expects to play (an upperclassman,
                  a blue-chipper, a kid one spot from the field) sours. Freshmen
                  buried on the depth chart mostly don't mind — yet.
  Results         wins lift everybody a little; blowout losses sting.
  The room        a warm locker room pulls everyone up, a fractured one down.
  Money           (your team) a starter paid well under his market grumbles.
  Who he is       Loyal, Humble and Grinder types sit higher; Divas, Mercenaries
                  and the Impatient sit lower and fall faster.
  Your calls      every inbox reply about a player (a promise, a benching, an NIL
                  raise, sitting him, backing him at the podium) moves him directly.
  Promises        at season's end, a kept promise is a big lift; a broken one is a
                  bigger drop.

WHAT IT DOES
  The portal      below 40 he's shopping; below 25 he's very likely gone. Above 75
                  he's hard to pry loose.
  Saturday        the starters' average mood is worth up to about half a point.
  Captains        happy veterans get more votes.
  The NFL         unhappy draft-eligible players leave more often; happy ones
                  come back a little more often.
  NIL demands     an unhappy starter asking for a raise comes with a threat.

The number is on every player card; the locker room screen (tab 3 → [K]) shows
who's up and who's sliding, and why.
"""
BASE = 60
TRAIT_BASE = {"loyal": 8, "humble": 5, "grinder": 4, "quiet_pro": 4, "captain": 4, "family_guy": 3, "leader": 3,
              "coachable": 3, "diva": -8, "mercenary": -6, "impatient": -5, "headcase": -6, "spotlight": -4,
              "hothead": -3, "stubborn": -2}
FRAGILE = {"diva": 1.4, "impatient": 1.3, "mercenary": 1.2, "headcase": 1.3, "loyal": 0.7, "humble": 0.8,
           "grinder": 0.8, "quiet_pro": 0.8, "sensitive": 1.4, "blue_collar": 0.7, "laid_back": 0.7}


def baseline(p):
    import traits
    b = BASE + sum(TRAIT_BASE.get(t, 0) for t in traits.tags(p))
    import skills
    if skills.team_has(getattr(p, "team", None), "hard_nosed"):
        b -= 4                                                     # Hard Nosed (coaching tree)
    return max(25, min(85, b))


def get(p):
    v = p.__dict__.get("morale")
    if v is None:
        v = p.morale = float(baseline(p))
    return v


def _fragility(p):
    f = 1.0
    import traits
    for t in traits.tags(p):
        f *= FRAGILE.get(t, 1.0)
    return f


def nudge(p, d, why=None, league=None):
    """Move a player's mood. Bad news hits fragile personalities harder."""
    if not d:
        return get(p)
    if d < 0:
        d *= _fragility(p)
    else:
        import skills
        if skills.team_has(getattr(p, "team", None), "open_door"):
            d *= 1.25                                              # Open Door (coaching tree)
    p.morale = max(0.0, min(100.0, get(p) + d))
    if why:
        log = p.__dict__.setdefault("mood_log", [])
        when = (league.year, league.week) if league is not None else None
        log.append((when, round(d), why))
        del log[:-6]
    return p.morale


def word(v):
    return ("fired up" if v >= 82 else "happy" if v >= 66 else "content" if v >= 50 else
            "restless" if v >= 36 else "unhappy" if v >= 22 else "wants out")


def color(v):
    from ui import C
    return C.BGREEN if v >= 66 else C.BWHITE if v >= 50 else C.BYELLOW if v >= 36 else C.BRED


def expects_to_play(p):
    return p.year >= 1 or p.hs_stars >= 4 or "impatient" in p.traits


def _rank(team, p):
    room = team.players_at(p.position)
    return room.index(p) if p in room else 99


# ═══ Weekly ═════════════════════════════════════════════════════════════════

def weekly(league, games):
    """After every week's games, every roster."""
    if league.week < 1:
        return
    from models import STARTING_LINEUP
    played = {}
    for g in games:
        if g.played:
            played[g.home] = g
            played[g.away] = g
    import hotseat
    mines = hotseat.humans(league)
    import personalities
    for team in league.teams:
        g = played.get(team)
        won = g is not None and g.winner is team
        blowout = g is not None and not won and abs(g.home_score - g.away_score) >= 28
        chem = personalities.chemistry(team)
        starters = {p for grp in team.starters().values() for p in grp}
        forces = contagion(team, starters)
        for p in team.roster:
            v = get(p)
            d = forces["pull"].get(id(p), 0.0)                  # the captains and the position room
            hurt = getattr(p, "inj_games", 0) > 0
            if p in starters:
                d += 1.0 if g is not None else 0.3
            elif not hurt and expects_to_play(p) and p.position not in ("K", "P"):
                n = STARTING_LINEUP.get(p.position, 1)
                behind = _rank(team, p) - n
                from traits import mod as trait_mod
                d -= (1.4 if behind <= 1 else 0.9 if p.hs_stars >= 4 else 0.4) * trait_mod(p, "role", 1.0)
                if getattr(p, "promise", None) == "made":
                    d += 0.6                                  # he's waiting on your word
            if g is not None:
                d += 0.6 if won else -0.9
                if blowout:
                    d -= 1.0
            if team.losses >= team.wins + 3:
                d -= 0.5                                      # a losing season wears on everybody
            d += (chem - 50) * 0.02
            if team.coach is not None:
                import coach_profile
                from traits import mod as trait_mod
                d += coach_profile.delta(team.coach, "relations") / 35 + trait_mod(team.coach, "relations", 0.0)
            if any(team is m for m in mines):
                import promises
                d += promises.weekly_drag(league, team, p, p in starters)
            if any(team is m for m in mines) and p in starters and p.overall >= 72:
                try:
                    import finance
                    mkt = finance.transfer_market(p)
                    if mkt >= 100_000 and (getattr(p, "nil", 0) or 0) < mkt * 0.45:
                        d -= 0.4
                except Exception:
                    pass
            if d < 0:
                d *= _fragility(p)
            v = v + d
            v += (baseline(p) - v) * 0.04                       # everybody drifts back toward who he is
            p.morale = max(0.0, min(100.0, v))
            if p.morale < 25:
                p.__dict__["disgruntled"] = league.year      # he's told people he's thinking about leaving
    if getattr(league, "mode", None) == "career":
        for mine in mines:
            with hotseat.acting_as(league, mine):
                _check_mine(league, mine)


def _check_mine(league, team):
    """A player of yours whose mood just fell through the floor asks to talk."""
    import people
    from ui import C
    flagged = league.__dict__.setdefault("_mood_flagged", set())
    core = set(sorted(team.roster, key=lambda q: -q.overall)[:35])      # the players who matter on Saturday
    worst = [p for p in team.roster if get(p) < 30 and (league.year, id(p)) not in flagged
             and (p in core or p.hs_stars >= 4) and p.position not in ("K", "P")]
    if not worst or league.week > 15:
        return
    p = min(worst, key=get)
    flagged.add((league.year, id(p)))
    why = p.__dict__.get("mood_log", [])
    reason = why[-1][2] if why else ("not playing" if p not in {q for grp in team.starters().values() for q in grp}
                                     else "the season")
    starter = p in {q for grp in team.starters().values() for q in grp}
    opts = [("Sit down with him. Hear him out.", {"hours": -2, "who": p, "morale": 15, "why_mood": "you sat down with him",
                                                  "meeting": True},
             f"An hour in your office. {p.first_name} felt heard."),
            ("Tell him the truth: his role is his role.",
             {"who": p, "morale": -5, "chem": 1, "why_mood": "told his role is his role"},
             "Straight talk. The rest of the room respects it; he doesn't love it.")]
    if not starter:
        opts.append(("Promise him snaps by November.", {"who": p, "promise": "made", "morale": 12, "why_mood": "promised snaps"},
                     f"{p.first_name} perks up. Now you owe him."))
    else:
        opts.append(("Make him a captain-in-training. Give him a voice.",
                     {"who": p, "morale": 10, "why_mood": "given a voice", "gamble": [(0.6, {"chem": 2}, "It worked. He's leading."),
                                                         ({"chem": -2}, "The real captains didn't love it.")]},
                     f"{p.first_name} has a seat at the table now."))
    people.choice(league, "Position coach", "Staff", f"{p.name} is struggling",
                  f"{p.first_name} ({p.position}, {p.class_label}) is in a bad place — his morale is "
                  f"{get(p):.0f}/100 ({word(get(p))}). What set him off: {reason}. If we don't do something, "
                  "he's a portal name in December.", opts, ref=p, color=C.BYELLOW,
                  silence={"who": p, "morale": -6}, silence_text="He noticed nobody came to talk to him.")


# ═══ Moods are contagious ═══════════════════════════════════════════════════

WILD = ("diva", "hothead", "headcase", "mercenary", "spotlight", "chippy")
LEADS = ("captain", "leader", "mentor", "quiet_pro", "tone_setter")


def contagion(team, starters=None):
    """Who's pulling whom. Captains pull the whole room toward their own mood; an
    unhappy wild card in the two-deep drags his position room down; a happy leader
    lifts his. Returns {"pull": {id(player): points}, "captains": avg or None,
    "drag": [(player, points)], "lift": [(player, points)]}."""
    from models import STARTING_LINEUP
    caps = [p for p in (getattr(team, "captains", None) or []) if p in team.roster]
    cap_avg = sum(get(p) for p in caps) / len(caps) if caps else None
    import skills
    thick = skills.team_has(team, "thick_skin")                    # coaching tree
    council = skills.team_has(team, "captains_council")
    pull, drag, lift = {}, [], []
    rooms = {}
    for p in team.roster:
        rooms.setdefault(p.position, []).append(p)
    for pos, room in rooms.items():
        two_deep = set(team.players_at(pos)[:STARTING_LINEUP.get(pos, 1) * 2])
        push = 0.0
        for p in room:
            if p not in two_deep:
                continue
            v = get(p)
            if v < 40 and any(t in p.traits for t in WILD):
                amt = -0.9 * (40 - v) / 20 * (0.5 if thick else 1.0)
                push += amt
                drag.append((p, amt))
            elif v >= 70 and any(t in p.traits for t in LEADS):
                amt = 0.3 * (v - 70) / 15 + 0.15
                push += amt
                lift.append((p, amt))
        push = max(-1.8, min(0.8, push))
        for p in room:
            own = next((a for q, a in drag + lift if q is p), 0.0)
            pull[id(p)] = push - own                            # nobody's dragged by himself
    if cap_avg is not None:
        for p in team.roster:
            if p in caps:
                continue
            pull[id(p)] = pull.get(id(p), 0.0) + (cap_avg - get(p)) * 0.035 * (1.5 if council else 1.0)
    return {"pull": pull, "captains": cap_avg, "caps": caps, "drag": drag, "lift": lift}


# ═══ Season's end ═══════════════════════════════════════════════════════════

def promises(league):
    """Every promise gets graded when the season ends."""
    from portal import STARTER_DEPTH
    for team in league.teams:
        for p in team.roster:
            pr = getattr(p, "promise", None)
            if pr != "made":
                continue
            n = STARTER_DEPTH.get(p.position, 2)
            kept = _rank(team, p) - n <= 1 or getattr(p, "games_played", 0) >= 6
            nudge(p, 12 if kept else -25, "a promise " + ("kept" if kept else "broken"), league)


# ═══ What morale does ═══════════════════════════════════════════════════════

def portal_factor(p):
    v = get(p)
    return 2.4 if v < 22 else 1.8 if v < 36 else 1.25 if v < 50 else 1.0 if v < 66 else 0.75 if v < 82 else 0.55


def team_lift(team, starters):
    """Rating points on Saturday: the starters' average mood, about half a point either way."""
    if not starters or getattr(team, "fcs", False):
        return 0.0
    avg = sum(get(p) for p in starters) / len(starters)
    return max(-0.55, min(0.55, (avg - 60) / 40 * 0.55))


def avg(players):
    players = list(players)
    return sum(get(p) for p in players) / len(players) if players else 0.0
