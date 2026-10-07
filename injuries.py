"""
injuries.py — Who gets hurt, how badly, and how long he's out.

Every contact in a game (ball carrier and tackler, a sacked quarterback and
the rusher, a returner and the man who brings him down, plus a trickle of
trench wear on the linemen) is a chance for an injury. The odds scale with
the player's Durability fundamental (the "injury" rating: high = durable).

Severity:
    shaken up      back in after a few plays
    out for game   done today, fine next week
    short term     1-3 games
    long term      4-8 games
    season-ending  out for the year (heals in the offseason)

A player's status lives on the Player object:
    inj_games  games still to miss (0 = available; 99 = season)
    inj_desc   what it is
    inj_week   the week it happened
"""

CONTACT_RATE = 0.0078          # per weighted contact, for a 55-durability player

SEVERITY = (                    # (key, weight, games-missed range, descriptions)
    ("shaken", 44, (0, 0), ("shaken up", "slow to get up", "banged up")),
    ("game", 21, (0, 0), ("ankle injury", "shoulder injury", "hand injury", "hamstring tightness",
                          "being evaluated for a concussion", "knee injury")),
    ("short", 21, (1, 3), ("ankle sprain", "hamstring strain", "knee sprain", "shoulder sprain",
                           "concussion", "rib injury")),
    ("long", 10, (4, 8), ("high ankle sprain", "MCL sprain", "broken hand", "turf toe",
                          "separated shoulder", "broken foot")),
    ("season", 7, (99, 99), ("torn ACL", "Achilles tear", "broken leg", "Lisfranc injury")),
)
SEASON = 99


def injury_chance(player, weight=1.0):
    from traits import mod as trait_mod
    durability = player.fundamentals.get("injury", 55)
    prep = getattr(getattr(player, "team", None), "week_prep", None) or {}
    import skills
    if skills.team_has(getattr(player, "team", None), "strength"):
        weight *= 0.92                                               # Strength Program (coaching tree)
    team = getattr(player, "team", None)
    coach_mult = trait_mod(getattr(team, "coach", None), "team_injury", 1.0) if team is not None and getattr(team, "coach", None) is not None else 1.0
    return CONTACT_RATE * weight * (1.55 - durability / 100) * trait_mod(player, "injury") * coach_mult * prep.get("injury", 1.0)


def roll_severity(rng):
    total = sum(s[1] for s in SEVERITY)
    pick = rng.random() * total
    for key, w, (lo, hi), descs in SEVERITY:
        pick -= w
        if pick <= 0:
            return key, rng.randint(lo, hi), rng.choice(descs)
    key, _, (lo, hi), descs = SEVERITY[0]
    return key, lo, descs[0]


def outlook(games, week=None):
    """How long he's out, in words a head coach can plan around."""
    if games >= SEASON:
        return "out for the season"
    if games <= 0:
        return "did not return — expected back next week"
    back = f", back week {week + games + 1}" if week else ""
    return f"out {games} week{'s' if games != 1 else ''}{back}"


def is_available(player):
    return getattr(player, "inj_games", 0) <= 0


def status_text(player, short=False):
    g = getattr(player, "inj_games", 0)
    if g <= 0:
        return ""
    if g >= SEASON:
        return "OUT (season)" if short else f"Out for the season — {player.inj_desc}"
    if short:
        return f"OUT {g}g"
    return f"Out {g} game{'s' if g != 1 else ''} — {player.inj_desc}"


def weekly_healing(league, finished_week):
    """Called before a new week starts: players hurt before the week that just
    finished have now missed one more game."""
    for team in league.teams:
        for p in team.roster:
            g = getattr(p, "inj_games", 0)
            if 0 < g < SEASON and p.inj_week < finished_week:
                p.inj_games = g - 1
                if p.inj_games == 0:
                    p.inj_desc = None


def heal_all(league):
    for team in league.teams:
        for p in team.roster:
            p.inj_games, p.inj_desc, p.inj_week = 0, None, 0
