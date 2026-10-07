"""
development.py — The offseason player development algorithm.

Each offseason a player goes through two phases, in order:

  1. BASE SKILLS
     A growth budget is set by:
        years in program  (young players jump, veterans plateau)
        x head coach development rating for his position group (0.6x - 1.4x)
        x player potential                                      (0.5x - 1.5x)
        x facilities                                            (0.92x - 1.08x)
     The budget is spread across fundamentals, weighted toward the ones his
     position cares about (a QB's IQ grows faster than his strength), and
     shrinks as a fundamental approaches 99. Durability drifts a little.
     There's a small chance of a setback (bad offseason, nagging injury).

  2. POSITION PROFICIENCY
     His primary-position proficiency closes part of the gap to his personal
     ceiling. How much depends on the coach's development rating, his
     potential, and his Football IQ *after* phase 1 — so the smarter he got,
     the better he learns to use his tools. Related positions tick up slightly.
"""
from models import FUNDAMENTALS, POSITION_WEIGHTS, PROFICIENCY_MAX, PROFICIENCY_MIN

# Average growth budget by offseason number (1st offseason, 2nd, ...).
GROWTH_BY_OFFSEASON = [5.0, 4.5, 3.5, 3.0, 2.5, 2.0]

RELATED = {
    "QB": ["RB", "WR", "S"],
    "RB": ["WR", "CB", "S", "LB"],
    "WR": ["RB", "CB", "TE", "S"],
    "TE": ["WR", "OL", "DL", "LB"],
    "OL": ["DL", "TE"],
    "DL": ["OL", "LB", "TE"],
    "LB": ["DL", "S", "TE", "RB"],
    "CB": ["S", "WR"],
    "S":  ["CB", "LB", "WR"],
    "K":  ["P"],
    "P":  ["K"],
}


IN_SEASON_SHARE = 1 / 3          # a third of a year's growth happens during the season, week by week
SEASON_WEEKS = 13


def develop_in_season(league, games=None):
    """After every regular-season week: every player on every roster grows a little."""
    if not (1 <= league.week <= SEASON_WEEKS):
        return
    import facilities
    import random
    rng = random.Random(f"insea:{league.seed}:{league.year}:{league.week}")
    scale = IN_SEASON_SHARE / SEASON_WEEKS
    for team in league.teams:
        if getattr(team, "fcs", False):
            continue
        tr = facilities.training_rating(team)
        for p in team.roster:
            develop_player(p, team.coach, tr, rng, team=team, scale=scale, in_season=True)


def develop_player(player, coach, facilities, rng, season_year=None, team=None, scale=None, in_season=False):
    """Run one step of development. Returns the change in overall.
    The offseason is two-thirds of a year's growth (scale 2/3); the season's weekly
    steps are the other third. With `team`, the coordinator who runs his side of
    the ball shares the work."""
    if scale is None:
        scale = 1 - IN_SEASON_SHARE
    before = player.overall
    import staff
    dev_rating = staff.dev_rating(team, coach, player.position)
    side = staff.side_coach(team, player.position) if team is not None else None

    coach_f = 0.45 + dev_rating / 100 * 1.1          # a teacher matters: 50 → 1.0, 90 → 1.44
    arc = player.__dict__.get("arc")
    if arc == "bloomer":                              # the late bloomer grows, faster with a staff that teaches
        coach_f *= 1.15 + 0.35 * max(0.0, min(1.0, (dev_rating - 40) / 50))
    elif arc == "bust":                               # the peaked blue-chipper stalls; good teachers soften it
        coach_f *= 0.50 + 0.30 * max(0.0, min(1.0, (dev_rating - 40) / 50))
    pot_f = 0.5 + player.potential / 100
    fac_f = 0.92 + facilities / 100 * 0.16
    base = GROWTH_BY_OFFSEASON[min(player.seasons_developed, len(GROWTH_BY_OFFSEASON) - 1)]
    # Players who picked a school that matched what they wanted develop faster;
    # bad fits stall out and become transfer candidates later.
    from traits import mod as trait_mod
    fit_f = getattr(player, "fit_bonus", 1.0) * trait_mod(player, "develop") \
        * trait_mod(coach, "develop", position=player.position)
    if side is not None:
        fit_f *= 1 + 0.5 * (trait_mod(side, "develop", position=player.position) - 1)         # his coordinator's traits, at half strength
    try:
        import poscoach
        fit_f *= poscoach.room_mult(team, player.position, player)
    except Exception:
        pass
    fit_f *= (player.__dict__.get("dev_boost", 1.0) if in_season
              else player.__dict__.pop("dev_boost", 1.0))    # extra work you put into him (Career inbox)
    import skills
    if team is not None and skills.user_coach_of(team) is not None:       # your coaching tree
        fit_f *= skills.guru_mult(team, player.position)
        if skills.team_has(team, "everybody_better"):
            fit_f *= 1.06
        if skills.team_has(team, "walk_on_magic") and getattr(player, "walk_on", False):
            fit_f *= 1.25
        if skills.team_has(team, "redshirt_factory") and player.year == 0 and not in_season:
            gp = list(getattr(player, "yearly_games", {}).values())
            if gp and gp[-1] <= 4:
                fit_f *= 1.20
    budget = base * coach_f * pot_f * fac_f * fit_f * scale
    noise = scale ** 0.5

    # ── Phase 1: base skills ──────────────────────────────────────────────
    weights = POSITION_WEIGHTS[player.position]
    setback = rng.random() < 0.04 * (scale if in_season else 1.0)
    bank = player.__dict__.setdefault("_grow", {}) if in_season else None
    gained = 0.0
    for f in FUNDAMENTALS:
        v = player.fundamentals[f]
        if f == "injury":
            change = rng.gauss(0.5 * scale, 2.0 * noise)
        else:
            focus = 0.5 + weights.get(f, 0) * 1.6         # position-relevant skills grow faster
            headroom = max(0.05, min(1.0, (99 - v) / 35))  # harder to improve near the top
            change = rng.gauss(budget * focus * headroom, 1.5 * noise)
            if setback:
                change -= rng.uniform(1, 4) * (0.5 if in_season else 1.0)
            gained += change * weights.get(f, 0)
        if in_season:                                   # a week's growth is fractions of a point: bank it
            bank[f] = bank.get(f, 0.0) + change
            whole = int(bank[f])
            bank[f] -= whole
            change = whole
        player.fundamentals[f] = int(max(15, min(99, round(v + change))))
    if in_season:
        wk = player.__dict__.setdefault("dev_weeks", [])  # the practice report reads the trend
        wk.append(round(gained, 3))
        del wk[:-4]

    # ── Phase 2: proficiency (uses the post-growth IQ) ────────────────────
    pos = player.position
    current = player.proficiency[pos]
    rate = 0.08 + dev_rating / 100 * 0.25 + player.fundamentals["iq"] / 100 * 0.12
    rate = max(0.08, min(0.6, rate)) * (0.75 + pot_f * 0.25)
    gap = player.prof_ceiling - current
    if gap > 0:
        current += gap * rate * scale + rng.gauss(0, 0.01 * noise)
    player.proficiency[pos] = _clamp_prof(current)

    iq_f = player.fundamentals["iq"] / 100
    for other in RELATED[pos]:
        player.proficiency[other] = _clamp_prof(player.proficiency[other] + rng.uniform(0, 0.015) * iq_f * scale)
    import subprof
    subprof.develop(player, rng, scale)                # shoring up the weak spots

    if not in_season:
        player.seasons_developed += 1
        if season_year is not None:
            player.history.append((season_year, player.overall))
    return player.overall - before


def _clamp_prof(value):
    return round(max(PROFICIENCY_MIN, min(PROFICIENCY_MAX, value)), 2)
