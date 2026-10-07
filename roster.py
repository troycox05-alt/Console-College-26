"""
roster.py — Creates players.

make_recruit()   builds a high-school recruit from his star rating: raw
                 fundamentals and a starting (not-yet-refined) proficiency.

generate_roster() builds a team's opening 2026 roster. Every player is
                 created as the freshman he once was (stars rolled from the
                 program's talent level), then run through the offseason
                 development algorithm once for every offseason he's had in
                 the program — so a RS-JR has been developed 3 times by his
                 current head coach.
"""
import random

from development import RELATED, develop_player
from models import FUNDAMENTALS, OFFENSE, DEFENSE, POSITIONS, Player
from names import FIRST_NAMES, LAST_NAMES, split_pair
from traits import assign_player_traits

ROSTER_SIZE = {"QB": 3, "RB": 4, "WR": 7, "TE": 3, "OL": 10,
               "DL": 9, "LB": 7, "CB": 6, "S": 4, "K": 2, "P": 2}

# Freshman talent level by high-school star rating.
STAR_TALENT = {1: 33, 2: 42, 3: 53, 4: 65, 5: 76}

# How each position's fundamentals typically sit relative to his talent level.
ARCHETYPES = {
    "QB": dict(strength=-6, speed=-8, quickness=-2, iq=6, injury=0, playmaker=4),
    "RB": dict(strength=0, speed=4, quickness=4, iq=-6, injury=-4, playmaker=2),
    "WR": dict(strength=-12, speed=6, quickness=4, iq=-4, injury=0, playmaker=3),
    "TE": dict(strength=5, speed=-4, quickness=-4, iq=0, injury=0, playmaker=-2),
    "OL": dict(strength=8, speed=-25, quickness=-6, iq=2, injury=2, playmaker=-30),
    "DL": dict(strength=7, speed=-12, quickness=2, iq=-6, injury=0, playmaker=-15),
    "LB": dict(strength=2, speed=-4, quickness=0, iq=2, injury=0, playmaker=-6),
    "CB": dict(strength=-14, speed=6, quickness=5, iq=-3, injury=0, playmaker=-2),
    "S":  dict(strength=-6, speed=2, quickness=0, iq=3, injury=0, playmaker=-2),
    "K":  dict(strength=4, speed=-25, quickness=-20, iq=2, injury=10, playmaker=0),
    "P":  dict(strength=4, speed=-25, quickness=-20, iq=2, injury=10, playmaker=0),
}

HEIGHT = {"QB": (72, 77), "RB": (68, 73), "WR": (69, 76), "TE": (75, 79), "OL": (75, 80),
          "DL": (73, 79), "LB": (72, 76), "CB": (69, 74), "S": (70, 75), "K": (69, 74), "P": (72, 77)}
WEIGHT = {"QB": (200, 235), "RB": (190, 225), "WR": (170, 215), "TE": (235, 265), "OL": (295, 335),
          "DL": (265, 315), "LB": (220, 250), "CB": (175, 200), "S": (190, 215), "K": (170, 205), "P": (190, 225)}
NUMBERS = {"QB": [(1, 19)], "RB": [(1, 49)], "WR": [(1, 19), (80, 89)], "TE": [(80, 89), (40, 49), (1, 19)],
           "OL": [(50, 79)], "DL": [(90, 99), (50, 79), (1, 49)], "LB": [(1, 59)], "CB": [(1, 39)],
           "S": [(1, 49)], "K": [(1, 49), (90, 99)], "P": [(1, 49), (90, 99)]}

# Opening-roster class mix and redshirt odds.
CLASS_WEIGHTS = [28, 26, 24, 22]   # FR, SO, JR, SR
REDSHIRT_ODDS = 0.35


def roll_stars(rng, score, pos=None):
    """High-school star rating from a 0-100 talent/recruiting score."""
    mu = 0.95 + score * 0.038       # blue bloods sign blue-chippers; the bottom signs two-stars
    if pos in ("K", "P"):
        mu -= 1.0                   # specialists rarely get big star ratings
    return max(1, min(5, round(rng.gauss(mu, 0.55))))


def make_recruit(rng, pos, stars, used_numbers, used_names, unique_last=False):
    offsets = ARCHETYPES[pos]
    talent = STAR_TALENT[stars] + rng.gauss(0, 3)

    fundamentals = {}
    for f in FUNDAMENTALS:
        if f == "injury":
            val = rng.gauss(70 + offsets[f], 12)
        else:
            val = rng.gauss(talent + offsets[f], 5)
        fundamentals[f] = int(max(15, min(99, round(val))))

    start_prof = _clamp(rng.gauss(0.72 + 0.04 * stars, 0.05), 0.55, 1.10)
    ceiling = _clamp(rng.gauss(1.0 + (stars - 3) * 0.02, 0.07), 0.85, 1.20)
    ceiling = min(1.20, max(ceiling, start_prof + 0.03))

    height, weight = rng.randint(*HEIGHT[pos]), rng.randint(*WEIGHT[pos])
    proficiency = {}
    for p in POSITIONS:
        if p == pos:
            v = start_prof
        elif p in RELATED[pos]:
            v = rng.uniform(0.40, 0.80)
        elif p in ("K", "P"):
            v = rng.uniform(0.1, 0.3)
        else:
            # A body that's nothing like the position's (a 320-pound lineman at safety) barely translates.
            mid = sum(WEIGHT[p]) / 2
            body = max(0.25, 1 - abs(weight - mid) / 120)
            v = max(0.1, rng.uniform(0.1, 0.45) * body)
        proficiency[p] = round(v, 2)

    potential = int(_clamp(round(rng.gauss(55 + (stars - 3) * 5, 16)), 1, 99))

    # On a roster (used_names holds that team's names) nobody shares a surname; in a
    # recruiting class, only the exact pair has to be new.
    lasts = {n[1] for n in used_names} if unique_last else set()
    while True:
        first, last = split_pair(rng, avoid=lasts)
        if (first, last) not in used_names:
            used_names.add((first, last))
            break

    player = Player(
        first_name=first, last_name=last, position=pos, year=0,
        number=_pick_number(rng, pos, used_numbers),
        height=height, weight=weight,
        fundamentals=fundamentals, proficiency=proficiency, redshirt=False,
        hs_stars=stars, potential=potential, prof_ceiling=round(ceiling, 2),
    )
    assign_player_traits(player, rng)
    # Stars are a projection, not a promise. A few kids are still growing into their bodies
    # (late bloomers, more often among the lightly recruited); a few blue-chippers have
    # already peaked. Nobody's told which is which: the staff that develops finds out.
    roll = rng.random()
    bloom = (0.12, 0.12, 0.11, 0.10, 0.06, 0.04)[max(0, min(5, stars))]
    bust = (0.03, 0.03, 0.04, 0.05, 0.09, 0.12)[max(0, min(5, stars))]
    if roll < bloom:
        player.__dict__["arc"] = "bloomer"
        player.potential = min(99, player.potential + rng.randint(12, 24))
    elif roll < bloom + bust:
        player.__dict__["arc"] = "bust"
        player.potential = max(1, player.potential - rng.randint(10, 22))
    return player


def make_prospect(rng, pos, stars, home_state, used_names):
    """An unsigned recruit: a real player with no team and no jersey number yet."""
    p = make_recruit(rng, pos, stars, set(), used_names)
    p.home_state = home_state
    p.year = 0
    p.history.clear()
    return p


def talent_score(team, pos):
    """How good a program's current roster is at this side of the ball."""
    if pos in OFFENSE:
        return team.ratings["offense"]
    if pos in DEFENSE:
        return team.ratings["defense"]
    return (team.ratings["offense"] + team.ratings["defense"]) / 2


def generate_roster(team, rng, season_year):
    """Opening roster: create each player as a freshman, then develop him."""
    used_numbers, used_names = set(), set()
    facilities = team.ratings["facilities"]

    for pos in POSITIONS:
        score = talent_score(team, pos)
        for _ in range(ROSTER_SIZE[pos]):
            stars = roll_stars(rng, score, pos)
            p = make_recruit(rng, pos, stars, used_numbers, used_names, unique_last=True)
            p.year = rng.choices(range(4), weights=CLASS_WEIGHTS)[0]
            p.redshirt = rng.random() < REDSHIRT_ODDS
            offseasons = p.year + (1 if p.redshirt else 0)
            first_year = season_year - offseasons
            p.history.append((first_year, p.overall))          # as a freshman
            p.events[first_year].append(f"Signed with {team.school} as a {stars}-star recruit")
            if p.redshirt:
                p.events[first_year].append("Redshirted")
            for i in range(offseasons):
                develop_player(p, team.coach, facilities, rng, season_year=first_year + i + 1, scale=1.0)
            team.add_player(p)


# How the rosters you inherit line up with the program ratings in teams_data.py.
# Four burn-in years of recruiting pull every roster toward prestige (tradition,
# academics, campus) and squeeze the league together, so on their own they'd forget
# who's actually good heading into 2026. settle_to_ratings() puts each side of the
# ball back on a line drawn through its rating, keeping part of what the burn-in did.
SETTLE_SLOPE = 0.35      # unit-overall points per rating point (fresh rosters: ~0.52; after burn-in: ~0.34)
SETTLE_KEEP = 0.15       # share of a team's burn-in drift (above or below its line) that it keeps


def settle_to_ratings(teams):
    """End of burn-in: move each team's offense and defense toward the overall its
    rating calls for. Every player on that side shifts by the same number of
    overall points (fundamentals scaled by his proficiency), so the depth chart,
    the stars and the gaps between players all stay as the burn-in left them."""
    teams = [t for t in teams if not getattr(t, "fcs", False)]
    if not teams:
        return
    for side, key in ((OFFENSE, "offense"), (DEFENSE, "defense")):
        now = [t.unit_overall(side) for t in teams]
        rat = [t.ratings[key] for t in teams]
        n = len(teams)
        m_now, m_rat = sum(now) / n, sum(rat) / n
        var = sum((r - m_rat) ** 2 for r in rat) or 1.0
        fit_slope = sum((r - m_rat) * (o - m_now) for r, o in zip(rat, now)) / var
        for t, o, r in zip(teams, now, rat):
            drift = o - (m_now + fit_slope * (r - m_rat))           # above or below where the burn-in's line puts him
            target = m_now + SETTLE_SLOPE * (r - m_rat) + SETTLE_KEEP * drift
            _shift_side(t, side, target - o)


def _shift_side(team, side, delta):
    if abs(delta) < 0.25:
        return
    for p in team.roster:
        if p.position not in side:
            continue
        prof = max(0.5, p.proficiency_at(p.position))
        d = delta / prof
        for f in FUNDAMENTALS:
            if f != "injury":
                p.fundamentals[f] = int(max(15, min(99, round(p.fundamentals[f] + d))))
        if p.history:
            p.history[-1] = (p.history[-1][0], p.overall)


def trim_to_template(team):
    """Hard-cap every position room at the roster template.

    Scholarships are finite. When a class comes in over the limit at a spot,
    the bottom of that room moves on — the walk-ons and the lowest-rated
    reserves first, never a starter."""
    cut = []
    for pos, size in ROSTER_SIZE.items():
        room = [p for p in team.roster if p.position == pos]
        if len(room) <= size:
            continue
        room.sort(key=lambda p: (not (getattr(p, "walk_on", False) and not getattr(p, "pwo", False)), p.overall, -p.year))
        for p in room[:len(room) - size]:
            team.roster.remove(p)
            cut.append(p)
    return cut


def sign_class(team, rng, season_year):
    """Fill every position back to roster size with walk-ons.

    These are the preferred walk-ons and late adds every program uses to round
    out a roster: unrated coming out of high school (0 stars) and a notch below
    the players the staff actually recruited."""
    used_numbers = {p.number for p in team.roster}
    used_names = {(p.first_name, p.last_name) for p in team.roster}
    score = team.recruiting_score
    signed = []
    for pos in POSITIONS:
        need = ROSTER_SIZE[pos] - len([p for p in team.roster if p.position == pos])
        for _ in range(max(0, need)):
            stars = max(1, roll_stars(rng, score * 0.88, pos))
            p = make_recruit(rng, pos, stars, used_numbers, used_names)
            p.hs_stars = 0                     # unrated: nobody offered him
            p.walk_on = True
            p.history.append((season_year, p.overall))
            p.events[season_year].append(f"Walked on at {team.school}")
            team.add_player(p)
            signed.append(p)
    return signed


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _pick_number(rng, pos, used):
    for lo, hi in NUMBERS[pos]:
        open_nums = [n for n in range(lo, hi + 1) if n not in used]
        if open_nums:
            n = rng.choice(open_nums)
            used.add(n)
            return n
    open_nums = [n for n in range(0, 100) if n not in used]
    n = rng.choice(open_nums)
    used.add(n)
    return n
