"""
stadium.py — A stadium built piece by piece.

Every program's stadium is made of PARTS: a lower bowl, end zone stands, an
upper deck, a student section, suites, a video board, the locker rooms, the
recruiting lounge, the grass... Each part has tiers. A tier costs money, takes
a season or more to build, and changes something:

  seats       capacity (and ticket money, if people come to fill them)
  noise       how loud the building gets: the home-field edge
  money       club seats, suites, concessions, video-board ads
  recruiting  what a recruit sees on a game-day visit
  in game     a home locker room players love, a visitors' room they hate,
              the grass they play on (home injuries)

One stadium project at a time. Big ones take two or three seasons. You can pay
as it's built or float a bond (more money, spread thinner). A stadium bigger
than its fan base plays half-empty — the fan base grows with prestige, winning
and a good game-day experience, and it grows slowly. A small school can build
itself an 80,000-seat bowl; it takes decades, and a program to fill it.

TOUGHEST PLACES TO PLAY
  The building (noise), the crowd (size and fill), the home record (this
  season and the three before), ranked visitors sent home beaten, the home
  streak and the tradition. Live all season; every final list is kept.
"""
import random

M = 1_000_000

# ═══ The parts ══════════════════════════════════════════════════════════════
# tiers: names from tier 0 up (a part with min 1 can't go below 1).
# cost[i]: $M to build tier i. build[i]: seasons it takes. seats: added per tier.
# fx: effect per tier above the part's minimum.
# req: {tier: [(part, tier needed)]}. wear: can age a tier in the offseason.

GROUPS = (("SEATING", ("lower_bowl", "end_zones", "upper_deck", "student_section", "club_seats", "suites")),
          ("ATMOSPHERE", ("canopy", "video_board", "sound", "lights", "tunnel")),
          ("FAN EXPERIENCE", ("concourse", "fan_plaza", "hall_of_fame", "press_box")),
          ("FOOTBALL", ("home_locker", "visitor_locker", "recruit_center", "surface")))

PARTS = {
    "lower_bowl": dict(
        name="Lower Bowl", min=1, seats=6000,
        tiers=["—", "Sideline Grandstands", "Grandstands & Bleachers", "Horseshoe Lower Bowl", "Full Lower Bowl",
               "Expanded Lower Bowl", "Grand Lower Bowl"],
        cost=[0, 0, 2.5, 4.0, 6.5, 9.0, 12.0], build=[0, 0, 1, 1, 2, 2, 2],
        fx={"noise": 0.3}, req={},
        blurb="The seats closest to the field. The base everything else is built on."),
    "end_zones": dict(
        name="End Zone Stands", min=0, seats=4000,
        tiers=["Open End Zones", "One End Zone", "Both End Zones", "Deep End Zone Stands", "Enclosed Bowl"],
        cost=[0, 3.5, 5.0, 7.0, 10.0], build=[0, 1, 1, 2, 2],
        fx={"noise": 0.5}, req={1: [("lower_bowl", 2)], 3: [("lower_bowl", 4)]},
        blurb="Close in the ends. An enclosed bowl traps the noise instead of letting it out."),
    "upper_deck": dict(
        name="Upper Deck", min=0, seats=5500,
        tiers=["None", "Home-Side Upper Deck", "Expanded Home Deck", "Towering Home Deck", "Visitor-Side Upper Deck",
               "Twin Upper Decks", "Wraparound Upper Deck"],
        cost=[0, 9.0, 11.0, 14.0, 18.0, 22.0, 27.0], build=[0, 2, 2, 2, 2, 3, 3],
        fx={"noise": 0.55}, req={1: [("lower_bowl", 3)], 4: [("lower_bowl", 4), ("end_zones", 2)],
                                 6: [("end_zones", 4)]},
        blurb="The big seat count — and steep decks hang the noise right over the field."),
    "student_section": dict(
        name="Student Section", min=0, seats=1500,
        tiers=["Scattered Students", "Student Section", "End Zone Student Wall", "Standing-Room Student Wall",
               "Legendary Student Section"],
        cost=[0, 0.6, 1.2, 2.0, 3.0], build=[0, 1, 1, 1, 1],
        fx={"noise": 0.8, "recruit": 1.0, "comfort": 0.005}, req={},
        blurb="The loudest seats in the building, and the ones recruits look at."),
    "club_seats": dict(
        name="Club Seats", min=0, seats=1200,
        tiers=["None", "Club Level", "Expanded Club", "Field Club", "Premium Club Ring"],
        cost=[0, 2.5, 4.0, 6.0, 9.0], build=[0, 1, 1, 1, 2],
        fx={"recruit": 0.25}, req={1: [("lower_bowl", 3)]},
        blurb="Padded seats and a buffet. Money every game — if the market can pay for them."),
    "suites": dict(
        name="Luxury Suites", min=0, seats=400,
        tiers=["None", "Suite Row", "Two Suite Levels", "Loge Boxes", "Luxury Tower"],
        cost=[0, 4.0, 6.0, 9.0, 13.0], build=[0, 1, 1, 2, 2],
        fx={"recruit": 0.5}, req={1: [("press_box", 1)], 3: [("upper_deck", 1)]},
        blurb="Twenty suites a tier, leased by the season. Big money where there's big money."),
    "canopy": dict(
        name="Roof Canopy", min=0, seats=0,
        tiers=["Open Air", "Roof Overhang", "Full Canopy"],
        cost=[0, 10.0, 18.0], build=[0, 2, 3],
        fx={"noise": 1.5, "comfort": 0.015}, req={1: [("upper_deck", 2)], 2: [("upper_deck", 4)]},
        blurb="A roof over the stands bounces every scream back onto the field — and keeps the rain off the "
               "fans, so a wet Saturday doesn't empty the building. The loudest thing you can build."),
    "video_board": dict(
        name="Video Board", min=0, seats=0, wear=True,
        tiers=["Scoreboard Only", "Video Board", "HD Video Board", "End Zone Boards", "Halo Board"],
        cost=[0, 0.6, 1.5, 3.0, 5.5], build=[0, 1, 1, 1, 1],
        fx={"noise": 0.3, "comfort": 0.008, "recruit": 0.5}, req={},
        blurb="Hype videos, replays and ad inventory. Screens age — keep it current."),
    "sound": dict(
        name="Sound System", min=0, seats=0, wear=True,
        tiers=["PA Speakers", "Stadium Sound", "Concert-Grade Sound", "Tuned Acoustic System"],
        cost=[0, 0.3, 0.8, 1.6], build=[0, 1, 1, 1],
        fx={"noise": 0.5}, req={},
        blurb="Third down, defense, the song everybody knows. Cheap noise."),
    "lights": dict(
        name="Stadium Lights", min=1, seats=0, wear=True,
        tiers=["—", "Standard Lights", "LED Light Show"],
        cost=[0, 0, 2.0], build=[0, 0, 1],
        fx={"noise": 0.3, "recruit": 1.0, "night": 0.02}, req={},
        blurb="LED lights that go dark and pulse after a touchdown: night games become events."),
    "tunnel": dict(
        name="Team Entrance", min=0, seats=0,
        tiers=["Gate Entrance", "Team Tunnel", "Signature Entrance"],
        cost=[0, 0.4, 1.2], build=[0, 1, 1],
        fx={"noise": 0.4, "recruit": 1.0}, req={},
        blurb="Smoke, a sign to touch, a run-out the whole building waits for."),
    "concourse": dict(
        name="Concourses", min=0, seats=0,
        tiers=["Open-Air Walkways", "Covered Concourse", "Wide Covered Concourse", "Climate-Controlled Concourse"],
        cost=[0, 1.5, 3.5, 6.0], build=[0, 1, 1, 2],
        fx={"comfort": 0.02, "concess": 0.6, "fans": 0.015}, req={},
        blurb="Shade, rain cover, shorter lines. People come back when a game day isn't a chore."),
    "fan_plaza": dict(
        name="Fan Plaza", min=0, seats=0,
        tiers=["Parking Lots", "Tailgate Grounds", "Fan Plaza", "Gameday Village"],
        cost=[0, 0.8, 2.0, 4.0], build=[0, 1, 1, 1],
        fx={"comfort": 0.012, "concess": 0.4, "fans": 0.02}, req={},
        blurb="Where Saturday starts at 8 a.m. Grows the fan base a little every year."),
    "hall_of_fame": dict(
        name="Hall of Fame", min=0, seats=0,
        tiers=["Trophy Case", "Hall of Fame", "Football Museum", "Legends Plaza & Museum"],
        cost=[0, 1.2, 2.5, 5.0], build=[0, 1, 1, 2],
        fx={"recruit": 2.0, "fans": 0.01}, req={},
        blurb="The history, on display. Recruits walk through it on every visit."),
    "press_box": dict(
        name="Press Box", min=0, seats=0,
        tiers=["Press Row", "Press Box", "Media Level", "Broadcast Center"],
        cost=[0, 1.5, 3.5, 6.0], build=[0, 1, 1, 2],
        fx={"recruit": 1.0}, req={},
        blurb="Where TV and the writers work. Exposure — and the base the suites hang from."),
    "home_locker": dict(
        name="Home Locker Room", min=1, seats=0, wear=True,
        tiers=["—", "Dated Locker Room", "Standard Locker Room", "Renovated Locker Room", "Showpiece Locker Room",
               "Players' Palace"],
        cost=[0, 0, 0.8, 1.8, 3.5, 6.0], build=[0, 0, 1, 1, 1, 1],
        fx={"recruit": 2.5, "edge": 0.04}, req={},
        blurb="Where your players get ready. Recruits film it; players play a little looser at home."),
    "visitor_locker": dict(
        name="Visitors' Locker Room", min=0, seats=0,
        tiers=["Standard Visitors' Room", "Spartan Visitors' Room", "Pink Visitors' Room"],
        cost=[0, 0.25, 0.15], build=[0, 1, 1],
        fx={"vis": 0.1}, req={},
        blurb="Low ceilings, cold showers, no carpet. Or pink walls. The other team notices."),
    "recruit_center": dict(
        name="Recruiting Lounge", min=0, seats=0, wear=True,
        tiers=["Sideline Passes", "Recruiting Lounge", "Gameday Recruiting Suite", "Recruiting Center",
               "Recruiting Palace"],
        cost=[0, 0.8, 2.0, 4.0, 7.0], build=[0, 1, 1, 1, 2],
        fx={"recruit": 3.0, "visit": 0.06}, req={},
        blurb="Where official visitors and their families spend game day. Every campus visit lands harder."),
    "surface": dict(
        name="Playing Surface", min=1, seats=0, wear=True,
        tiers=["—", "Worn Turf", "Modern Turf", "Natural Grass", "Heated Hybrid Grass"],
        cost=[0, 0, 0.6, 1.2, 2.5], build=[0, 0, 1, 1, 1],
        fx={"recruit": 0.75}, req={},
        blurb="What your players land on. Worn turf costs you players; good grass keeps them. Grass turns sloppy in "
               "the rain; heated hybrid grass drains fast and snow won't stick."),
}
ORDER = [k for _, keys in GROUPS for k in keys]
SEATING = [k for k in ORDER if PARTS[k]["seats"]]
INJURY = {1: 1.08, 2: 1.0, 3: 0.96, 4: 0.92}        # home-game injury rate by playing surface
TICKET = 45.0                # $ a new seat brings in, per game, when it's sold
CLUB_PRICE = 95.0            # $ per club seat per game, above a ticket
SUITE_LEASE = 55_000         # $ a suite a season
AD_REVENUE = 110_000         # $ a video-board tier brings in a season
BOND_TERMS = {6: 0.15, 10: 0.30}     # seasons: extra cost
PAY_CAP = 0.25               # NIL-pool stadium payments in any one season: at most this share of the budget
FUND_CAP = 1.5               # the fund tops out around this many years of budget (boosters give elsewhere)
BOND_CAP = 0.12              # bond payments in any one season: at most this share of the budget
CAMPAIGN = {"title": 0.25, "cfp": 0.15, "conf_champ": 0.10}   # a capital campaign after a big season: share of budget
NOISE_MAX = 15.0             # noise points for a 10/10 building
RECRUIT_MAX = 58.0
FAN_DRIFT = 0.12             # how far the fan base moves toward where it's heading each year


# A few buildings everybody knows: school -> parts that start at least this good.
KNOWN_PARTS = {"Washington": {"canopy": 1}, "Oregon": {"canopy": 1, "sound": 3}, "Iowa": {"visitor_locker": 2}, "Bayou State": {"student_section": 4, "lights": 2}, "Upcountry": {"tunnel": 2}, "Brazos": {"student_section": 4}}


def part(key):
    return PARTS[key]


def max_tier(key):
    return len(PARTS[key]["tiers"]) - 1


def tier_name(key, tier):
    return PARTS[key]["tiers"][tier]


# ═══ State ══════════════════════════════════════════════════════════════════

def _seed_parts(team, cap, rng, old_level=None):
    """Break a real stadium into parts: seats from its capacity, the rest from its reputation."""
    p = {k: PARTS[k]["min"] for k in ORDER}
    pres = team.prestige
    trad = team.ratings.get("tradition", 60)
    rec = (getattr(team, "fac", None) or {}).get("recruiting")
    if rec is None:
        rec = 1 + (team.ratings.get("facilities", 70) - 50) / 5.3
    lvl = old_level if old_level is not None else 2 + min(7.5, cap / 13500) + (pres - 60) / 25 + rng.gauss(0, 0.7)
    lvl = max(1, min(10, lvl))
    cl = lambda v, lo, hi: int(max(lo, min(hi, round(v))))
    # Seats.
    p["student_section"] = cl(cap / 20000 + rng.uniform(-0.3, 0.6), 1, 4)
    p["club_seats"] = cl((pres - 55) / 10 + cap / 40000 + rng.uniform(-0.5, 0.3), 0, 4)
    p["suites"] = cl((pres - 60) / 10 + cap / 45000 + rng.uniform(-0.5, 0.3), 0, 4)
    left = cap - sum(p[k] * PARTS[k]["seats"] for k in ("student_section", "club_seats", "suites"))
    p["lower_bowl"] = cl(left // 6000, 1, 6)
    left -= p["lower_bowl"] * 6000
    if p["lower_bowl"] >= 2:
        p["end_zones"] = cl(min(left * 0.45, 16000) // 4000, 0, 2 if p["lower_bowl"] < 4 else 4)
        left -= p["end_zones"] * 4000
    if p["lower_bowl"] >= 3:
        cap_ud = 3 if p["lower_bowl"] < 4 or p["end_zones"] < 2 else (5 if p["end_zones"] < 4 else 6)
        p["upper_deck"] = cl(left // 5500, 0, cap_ud)
        left -= p["upper_deck"] * 5500
    # Everything else.
    p["press_box"] = cl((pres - 45) / 15 + rng.uniform(-0.4, 0.4), 0, 3)
    if p["suites"] and not p["press_box"]:
        p["press_box"] = 1
    if p["suites"] >= 3 and not p["upper_deck"]:
        p["suites"] = 2
    p["video_board"] = cl(lvl / 2.5 + rng.uniform(-0.5, 0.5), 0, 4)
    p["sound"] = cl(lvl / 3.3 + rng.uniform(-0.5, 0.5), 0, 3)
    p["concourse"] = cl((lvl - 3) / 2.3 + rng.uniform(-0.5, 0.5), 0, 3)
    p["fan_plaza"] = cl((trad - 50) / 15 + lvl / 6 - 0.5 + rng.uniform(-0.4, 0.4), 0, 3)
    p["tunnel"] = cl((trad - 60) / 14 + rng.uniform(-0.3, 0.5), 0, 2)
    p["lights"] = 2 if lvl >= 8 and rng.random() < 0.45 else 1
    p["hall_of_fame"] = cl((trad - 55) / 12 + rng.uniform(-0.4, 0.4), 0, 3)
    p["home_locker"] = cl(1 + rec * 0.4 + rng.uniform(-0.5, 0.5), 1, 5)
    p["recruit_center"] = cl((rec - 2) / 2 + rng.uniform(-0.5, 0.5), 0, 4)
    r = rng.random()
    p["surface"] = 4 if pres >= 85 and r < 0.4 else 3 if (trad >= 75 and r < 0.6) else 1 if (pres < 52 and r < 0.4) else 2
    if pres >= 72 and p["upper_deck"] >= 2 and rng.random() < 0.08:
        p["canopy"] = 1
    if rng.random() < 0.04:
        p["visitor_locker"] = 1
    known = KNOWN_PARTS
    for k, v in known.get(team.school, {}).items():
        p[k] = max(p[k], v)
    extra = cap - sum(p[k] * PARTS[k]["seats"] for k in SEATING)
    return p, int(extra)


def ensure(team):
    """Build a program's stadium out of parts the first time it's needed (new worlds and old saves)."""
    st = getattr(team, "stad", None)
    if st:
        return st
    rng = random.Random(f"stadium:{team.school}")
    cap = int(getattr(team, "capacity", 40000))
    base = int(getattr(team, "base_capacity", cap) or cap)
    old_level = None
    if getattr(team, "fac", None) and "stadium" in team.fac:
        old_level = (getattr(team, "fac_start", None) or team.fac).get("stadium")
    start, start_extra = _seed_parts(team, base, random.Random(f"stadium:{team.school}"), old_level)
    if cap != base:                        # an old save with stadium upgrades: they show as new parts
        now, extra = _seed_parts(team, cap, random.Random(f"stadium:{team.school}"), team.fac.get("stadium"))
        for k in ORDER:
            now[k] = max(now[k], start[k]) if k not in SEATING else now[k]
    else:
        now, extra = dict(start), start_extra
    st = team.stad = {
        "parts": now, "extra": extra, "project": None, "log": [], "home_log": [], "streak": 0,
        "fans": float(base), "base_fans": float(base), "start_prestige": team.prestige, "opened": {},
        "fund": 0, "bonds": [],
    }
    team.stad_start = dict(start)
    team.base_capacity = base
    import finance
    st["fund"] = int(finance.budget(team) * rng.uniform(0.05, 0.35) // 10_000 * 10_000)   # what's already been raised
    sync(team, first=True)
    return st


def parts(team):
    return ensure(team)["parts"]


def sync(team, first=False):
    """Capacity, the stadium grade and the old facilities numbers follow the parts."""
    st = team.stad
    team.capacity = capacity(team)
    fac = getattr(team, "fac", None)
    if fac is not None:
        fac["stadium"] = grade(team)
        if first and getattr(team, "fac_start", None) is not None:
            team.fac_start["stadium"] = grade(team, team.stad_start)
    return st


def capacity(team, p=None):
    st = team.stad
    p = p or st["parts"]
    seats = sum(p[k] * PARTS[k]["seats"] for k in SEATING) + st["extra"]
    pr = st.get("project")
    if p is st["parts"] and pr and PARTS[pr["key"]]["seats"] and PARTS[pr["key"]]["build"][pr["tier"]] >= 2:
        seats = int(seats * 0.97)                       # construction closes a section
    return int(max(5000, seats))


def seats_of(team, key):
    return team.stad["parts"][key] * PARTS[key]["seats"] + (team.stad["extra"] if key == "lower_bowl" else 0)


# ═══ What the parts add up to ═══════════════════════════════════════════════

def _sum(p, fx):
    total = 0.0
    for k, lv in p.items():
        v = PARTS[k]["fx"].get(fx)
        if v:
            total += v * max(0, lv - PARTS[k]["min"])
    return total


def noise_rating(team, p=None):
    """1 (a quiet bowl) .. 10 (a roof over 100,000 screaming people): the building, not the crowd."""
    p = p or parts(team)
    return round(1 + 9 * min(1.0, _sum(p, "noise") / NOISE_MAX), 1)


NOISE_WORDS = ((8.5, "Deafening"), (7, "Loud"), (5.5, "Lively"), (4, "Average"), (2.5, "Quiet"), (0, "Sleepy"))


def noise_word(v):
    return next(w for lo, w in NOISE_WORDS if v >= lo)


def recruit_score(team, p=None):
    """0-100: the stadium as a recruit sees it on a game-day visit."""
    p = p or parts(team)
    pts = _sum(p, "recruit") + min(8.0, capacity(team, p) / 12500) + noise_rating(team, p) * 0.6
    return int(round(min(100, pts / RECRUIT_MAX * 100)))


def comfort(team):
    """Turnout bonus: a building people like spending a Saturday in."""
    return _sum(parts(team), "comfort")


def concessions(p):
    return _sum(p, "concess")


def home_edge(team):
    """Form points for the home team (the locker room)."""
    return _sum(parts(team), "edge")


def visitor_penalty(team):
    """Form points the visitors lose in this building."""
    return _sum(parts(team), "vis")


def injury_mult(team):
    return INJURY.get(parts(team)["surface"], 1.0)


def visit_mult(team):
    """A campus visit on a game day: the lounge, and how the place feels."""
    p = parts(team)
    return 1 + 0.06 * p["recruit_center"] + (recruit_score(team) - 50) * 0.002


def night_bonus(team):
    return _sum(parts(team), "night")


def fan_growth(team):
    return _sum(parts(team), "fans")


def grade(team, p=None):
    """The whole building on the old 1-10 scale: size, noise, amenities, what recruits see."""
    p = p or parts(team)
    cap = min(1.0, capacity(team, p) / 100000)
    noise = (noise_rating(team, p) - 1) / 9
    am_keys = ("concourse", "fan_plaza", "hall_of_fame", "press_box", "video_board", "sound", "lights")
    amen = sum(p[k] - PARTS[k]["min"] for k in am_keys) / sum(max_tier(k) - PARTS[k]["min"] for k in am_keys)
    rec = recruit_score(team, p) / 100
    return int(max(1, min(10, round(1 + 9 * (0.35 * cap + 0.25 * noise + 0.2 * amen + 0.2 * rec)))))


GRADES = ((9, "Elite"), (7, "Great"), (5, "Solid"), (3, "Aging"), (1, "Poor"))


def grade_word(g):
    return next(w for lo, w in GRADES if g >= lo)


def fanbase(team):
    return int(ensure(team)["fans"])


# ═══ Money ══════════════════════════════════════════════════════════════════

def premium_demand(team, fill=0.85):
    """How much of the premium seating a market this size actually buys."""
    return max(0.2, min(1.0, (team.prestige - 35) / 55)) * max(0.3, min(1.0, fill + 0.15))


def revenue(league, team):
    """(total, parts) the stadium brought in this season beyond what the budget was built around."""
    st = ensure(team)
    p, s0 = st["parts"], team.stad_start
    homes = [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played
             and getattr(g, "attendance", None)]
    if not homes:
        return 0, {}
    base_cap = team.base_capacity
    fill = sum(g.fill for g in homes) / len(homes)
    pd = premium_demand(team, fill)
    out = {}
    out["new seats"] = sum(max(0, min(g.attendance, team.capacity) - base_cap) for g in homes) * TICKET
    out["club seats"] = max(0, p["club_seats"] - s0["club_seats"]) * PARTS["club_seats"]["seats"] * CLUB_PRICE \
        * pd * len(homes)
    out["suites"] = max(0, p["suites"] - s0["suites"]) * 20 * SUITE_LEASE * pd
    out["concessions"] = max(0.0, concessions(p) - concessions(s0)) * sum(g.attendance for g in homes)
    out["video board ads"] = max(0, p["video_board"] - s0["video_board"]) * AD_REVENUE * pd
    import skills
    if skills.team_has(team, "stadium_exp"):
        out = {k: v * 1.25 for k, v in out.items()}     # Stadium Experience (coaching tree)
    out = {k: int(v) for k, v in out.items() if v >= 1}
    return sum(out.values()), out


# ═══ Building ═══════════════════════════════════════════════════════════════

def payments(team, year):
    """What the stadium takes out of a season's player-NIL pool (pay-as-built installments, deposits)."""
    return sum(a for y, a, what in getattr(team, "fac_spend", []) if y == year and what.startswith("stadium:"))


def bond_due(team, year):
    return sum(a for y, a in ensure(team).get("bonds", []) if y == year)


def bonds_left(team, after):
    return sum(a for y, a in ensure(team).get("bonds", []) if y > after)


def pay_cap(team):
    import finance
    return finance.budget(team) * PAY_CAP


def bond_cap(team):
    import finance
    return finance.budget(team) * BOND_CAP


def fund(team):
    return int(ensure(team).get("fund", 0))


def donations(league, team):
    """What boosters give the stadium fund a year: more at a big program, a winning one, a sold-out one."""
    import finance
    st = ensure(team)
    rate = 0.03 + max(0, team.prestige - 40) * 0.0006
    recs = [(r[1], r[2]) for r in getattr(team, "historical_records", [])[-1:]] + [(team.wins, team.losses)]
    pcts = [w / (w + l) for w, l in recs if w + l]
    if pcts:
        rate += 0.03 * max(0.0, sum(pcts) / len(pcts) - 0.5) * 2
    log = st.get("home_log", [])
    if log and log[-1][5] >= 0.95:
        rate += 0.01                                  # a waiting list for season tickets opens wallets
    style = (getattr(team, "ad", None) or {}).get("style")
    rate *= {"booster": 1.3, "brand": 1.2, "budget": 0.8}.get(style, 1.0)
    import skills
    if skills.team_has(team, "fundraiser"):
        rate *= 1.25                                   # Fundraiser (coaching tree)
    return int(finance.budget(team) * rate)


def price(team, key, tier):
    c = PARTS[key]["cost"][tier] * M
    import skills
    if skills.team_has(team, "groundbreaker"):
        c *= 0.85                                          # Groundbreaker (coaching tree)
    return int(c)


def plans(team, key, tier):
    """The ways to pay: ("fund",) when the fund covers it; otherwise cash for the rest, or a bond."""
    if fund(team) >= price(team, key, tier):
        return ["fund"]
    return ["build"] + list(BOND_TERMS)


def schedule(league, team, key, tier, plan="build"):
    """(from the fund now, [(season, amount)] after). "build": the rest out of the NIL pool over the build;
    a bond: the rest plus interest, paid out of the stadium fund every offseason."""
    c = price(team, key, tier)
    down = min(fund(team), c)
    rest = c - down
    if rest <= 0 or plan == "fund":
        return down, []
    if plan == "build":
        n, total = max(1, PARTS[key]["build"][tier]), rest
    else:
        n, total = plan, int(rest * (1 + BOND_TERMS[plan]))
    each = total // n
    return down, [(league.year + 1 + i, each) for i in range(n)]


def missing(team, key, tier):
    """Parts that must come first: [(part, tier)]."""
    p = parts(team)
    need = []
    for t in range(1, tier + 1):
        for k, lv in PARTS[key]["req"].get(t, []):
            if p[k] < lv and (k, lv) not in need:
                need.append((k, lv))
    return need


def can_build(league, team, key, plan="build"):
    """(ok, next tier, (down, schedule), reason)."""
    st = ensure(team)
    lv = st["parts"][key]
    if lv >= max_tier(key):
        return False, None, (0, []), "it's as good as it gets"
    tier = lv + 1
    pr = st.get("project")
    if pr:
        return False, tier, (0, []), (f"one stadium project at a time — the {tier_name(pr['key'], pr['tier']).lower()} "
                                      f"opens for the {pr['done'] + 1} season")
    need = missing(team, key, tier)
    if need:
        return False, tier, (0, []), "first you need: " + ", ".join(tier_name(k, t) for k, t in need)
    down, sched = schedule(league, team, key, tier, plan)
    if plan == "fund" and down < price(team, key, tier):
        return False, tier, (down, sched), "the stadium fund doesn't cover it"
    import finance
    if plan == "build" and sched:
        first = sched[0][1]
        left = finance.available(league, team)
        if first > left:
            return False, tier, (down, sched), (f"after the fund's {finance.money(down)}, the first payment is "
                                                f"{finance.money(first)} and you have {finance.money(left)} available")
        for y, a in sched:
            if payments(team, y) + a > pay_cap(team):
                return False, tier, (down, sched), (f"NIL-pool stadium payments in {y} would pass "
                                                    f"{finance.money(pay_cap(team))} (a quarter of the budget)")
    elif sched:
        for y, a in sched:
            if bond_due(team, y) + a > bond_cap(team):
                return False, tier, (down, sched), (f"bond payments in {y} would pass {finance.money(bond_cap(team))} "
                                                    f"a year — more debt than the school will carry")
    return True, tier, (down, sched), ""


def build(league, team, key, plan="build", who="the AD"):
    ok, tier, (down, sched), why = can_build(league, team, key, plan)
    if not ok:
        return False, why
    import finance
    st = team.stad
    name = tier_name(key, tier)
    yrs = max(1, PARTS[key]["build"][tier])
    done = league.year + yrs - 1
    st["fund"] = st.get("fund", 0) - down
    if plan == "build":
        for y, a in sched:
            team.fac_spend.append((y, a, f"stadium: {name}"))
    else:
        st.setdefault("bonds", []).extend(sched)
    total = down + sum(a for _, a in sched)
    st["project"] = {"key": key, "tier": tier, "done": done, "cost": total, "started": league.year, "plan": plan}
    sync(team)
    bits = []
    if down:
        bits.append(f"{finance.money(down)} from the stadium fund")
    if sched and plan == "build":
        bits.append(f"{finance.money(sum(a for _, a in sched))} from the NIL pool over {len(sched)} "
                    f"season{'s' if len(sched) != 1 else ''}")
    elif sched:
        bits.append(f"a {plan}-season bond ({finance.money(sched[0][1])} a year)")
    how = " + ".join(bits)
    st["log"].append((league.year, f"Broke ground: {PARTS[key]['name']} → {name} ({finance.money(total)}: {how})"))
    return True, f"Construction starts on the {name.lower()} — {how}. It opens for the {done + 1} season."


def deposit(league, team, amount):
    """Move money from next season's NIL pool into the stadium fund."""
    import finance
    amount = int(amount)
    if amount <= 0:
        return False, "Nothing to move."
    if amount > finance.available(league, team):
        return False, f"You have {finance.money(finance.available(league, team))} available."
    team.fac_spend.append((league.year + 1, amount, "stadium: fund deposit"))
    ensure(team)["fund"] = fund(team) + amount
    team.stad["log"].append((league.year, f"Moved {finance.money(amount)} of NIL money into the stadium fund"))
    return True, f"{finance.money(amount)} moved into the stadium fund."


def finish_projects(league, team, you=None):
    st = ensure(team)
    pr = st.get("project")
    if not pr or pr["done"] > league.year:
        return None
    key, tier = pr["key"], pr["tier"]
    before = capacity(team)
    st["parts"][key] = max(st["parts"][key], tier)
    st["project"] = None
    st["opened"][key] = league.year + 1
    sync(team)
    add = team.capacity - before
    extra = f" — capacity {team.capacity:,} (+{add:,})" if add > 0 else ""
    st["log"].append((league.year, f"Opened: {PARTS[key]['name']} → {tier_name(key, tier)}{extra}"))
    return f"{tier_name(key, tier)} is finished{extra}."


def gift(team, n=2, rng=None):
    """A donor pays for a couple of upgrades (booster windfalls): the cheapest useful ones."""
    ensure(team)
    rng = rng or random.Random()
    done = []
    for _ in range(n):
        opts = [k for k in ORDER if team.stad["parts"][k] < max_tier(k) and not missing(team, k, team.stad["parts"][k] + 1)
                and k != "visitor_locker"]
        if not opts:
            break
        k = min(opts, key=lambda k: PARTS[k]["cost"][team.stad["parts"][k] + 1] * rng.uniform(0.6, 1.4))
        team.stad["parts"][k] += 1
        done.append(tier_name(k, team.stad["parts"][k]).lower())
    sync(team)
    return done


def upgrade_now(team, key, why=""):
    """An upgrade that happens on the spot (an AD event, a donor)."""
    ensure(team)
    if team.stad["parts"][key] >= max_tier(key):
        return None
    team.stad["parts"][key] += 1
    sync(team)
    return tier_name(key, team.stad["parts"][key])


# ═══ The offseason ═════════════════════════════════════════════════════════

def home_games(league, team):
    return [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played]


def season_home(league, team):
    """This season at home: (wins, losses, ranked visitors beaten, avg crowd, avg fill)."""
    gs = home_games(league, team)
    w = sum(1 for g in gs if g.winner is team)
    ranked = sum(1 for g in gs if g.winner is team and (getattr(g, "ranks", {}) or {}).get(g.away))
    crowds = [g for g in gs if getattr(g, "attendance", None)]
    att = sum(g.attendance for g in crowds) // len(crowds) if crowds else 0
    fill = sum(g.fill for g in crowds) / len(crowds) if crowds else 0.0
    return w, len(gs) - w, ranked, att, fill


def home_streak(league, team):
    """Home wins in a row, carried across seasons."""
    n = 0
    for g in reversed(home_games(league, team)):
        if g.winner is team:
            n += 1
        else:
            return n
    return n + ensure(team).get("streak", 0)


def _drift_fans(league, team):
    st = team.stad
    recs = [(r[1], r[2]) for r in getattr(team, "historical_records", [])[-2:]] + [(team.wins, team.losses)]
    pcts = [w / (w + l) for w, l in recs if w + l]
    win = sum(pcts) / len(pcts) if pcts else 0.5
    prestige = max(0.5, min(3.0, 1 + (team.prestige - st["start_prestige"]) * 0.028))
    success = 0.85 + 0.3 * win
    amen = 1 + fan_growth(team)
    target = st["base_fans"] * prestige * success * amen
    # A full house builds a waiting list: selling out every week pulls the fan base up.
    w, l, _, att, fill = season_home(league, team)
    if fill >= 0.97 and w + l >= 3:
        target *= 1.04
    st["fans"] += (target - st["fans"]) * FAN_DRIFT


def end_of_season(league, rng, you=None):
    """Called from facilities.end_of_season: the record book, the fan base, wear, openings, CPU plans."""
    import ad_mode
    import skills
    import hotseat
    humans = hotseat.humans(league) if getattr(league, "mode", None) == "career" and not getattr(league, "autosim", False) else []

    def yours(t):
        return t is you or any(t is h for h in humans)

    def log(t, text):                                   # into the career log of the coach who runs that program
        with hotseat.acting_as(league, t):
            league.__dict__.setdefault("career_log", []).append((league.year, text))
    snapshot(league)
    for team in league.teams:
        st = ensure(team)
        w, l, ranked, att, fill = season_home(league, team)
        if w + l:
            st["home_log"].append((league.year, w, l, ranked, att, round(fill, 3)))
            del st["home_log"][:-12]
        st["streak"] = home_streak(league, team)
        _drift_fans(league, team)
        # The stadium fund: booster giving, a capital campaign after a big year, then the bond payments.
        gift_ = donations(league, team)
        import finance
        st["fund"] = min(fund(team) + gift_, max(fund(team), int(finance.budget(team) * FUND_CAP)))
        s_ = getattr(team, "_season_line", None) or {}
        if s_.get("year") == league.year:
            import finance
            for k_ in ("title", "cfp", "conf_champ"):
                if s_.get(k_):
                    camp = int(finance.budget(team) * CAMPAIGN[k_])
                    st["fund"] += camp
                    st["log"].append((league.year, f"Capital campaign after {'a national title' if k_ == 'title' else 'a playoff run' if k_ == 'cfp' else 'a conference title'}: "
                                                   f"{finance.money(camp)} for the stadium fund"))
                    if yours(team):
                        log(team, f"Stadium: boosters pledge {finance.money(camp)} to the stadium fund.")
                    break
        due = bond_due(team, league.year + 1)
        if due:
            st["fund"] -= due
            if st["fund"] < 0:
                short = -st["fund"]
                st["fund"] = 0
                team.fac_spend.append((league.year + 1, short, "stadium: bond payment the fund couldn't cover"))
                if yours(team):
                    import finance
                    log(team, f"Stadium: the fund came up {finance.money(short)} short on the bond — "
                              "it comes out of next season's NIL pool.")
        st["bonds"] = [(y, a) for y, a in st.get("bonds", []) if y > league.year + 1]
        st["last_gift"] = gift_
        msg = finish_projects(league, team)
        if msg and yours(team):
            log(team, f"Stadium: {msg}")
        # Wear and tear: screens, speakers, turf and locker rooms age.
        if not skills.team_has(team, "blueprint"):
            g = grade(team)
            import facilities as fa
            odds = (fa.DEGRADE_BASE + fa.DEGRADE_PER_LEVEL * g) * ad_mode.degrade_mult(league, team, "stadium")
            if rng.random() < odds:
                worn = [k for k in ORDER if PARTS[k].get("wear") and st["parts"][k] > max(PARTS[k]["min"], 1)]
                if worn:
                    k = rng.choice(worn)
                    st["parts"][k] -= 1
                    st["log"].append((league.year, f"Wear and tear: {PARTS[k]['name']} slipped to "
                                                   f"{tier_name(k, st['parts'][k])}"))
                    if yours(team):
                        log(team, f"Stadium: the {PARTS[k]['name'].lower()} slipped to "
                                  f"{tier_name(k, st['parts'][k]).lower()}.")
        del st["log"][:-30]
        sync(team)


# ═══ The CPU's building plan ═══════════════════════════════════════════════

STYLE_WANTS = {
    "recruiting": ("recruit_center", "home_locker", "hall_of_fame", "surface"),
    "booster": ("suites", "club_seats", "video_board", "concourse"),
    "brand": ("video_board", "suites", "lights", "tunnel", "press_box"),
    "big_game": ("student_section", "sound", "canopy", "end_zones", "visitor_locker"),
    "traditionalist": ("hall_of_fame", "student_section", "tunnel", "surface"),
    "win_now": ("home_locker", "surface", "recruit_center", "sound"),
    "analytics": ("club_seats", "concourse", "fan_plaza", "surface"),
    "budget": ("sound", "video_board", "fan_plaza"),
}


def _want(league, team, key, rng):
    """How badly this program wants the next tier of a part (the CPU AD's view)."""
    st = team.stad
    lv = st["parts"][key]
    P = PARTS[key]
    style = (getattr(team, "ad", None) or {}).get("style", "conference")
    frac = max(0.1, min(1.0, (team.prestige - 35) / 58))
    if P["seats"] >= 4000 or key == "lower_bowl":
        w, l, _, att, fill = season_home(league, team)
        log = st.get("home_log", [])
        fills = [x[5] for x in log[-2:]] + ([fill] if w + l else [])
        full = sum(fills) / len(fills) if fills else 0.8
        demand = st["fans"] * (0.95 + max(0, team.prestige - 60) / 200)
        short = demand - team.capacity
        if full >= 0.93 and short > P["seats"] * 0.4:
            score = 2.5 + short / 8000
        else:
            score = -4
    else:
        desired = frac * (max_tier(key) - P["min"]) + P["min"]
        score = (desired - lv) * 1.1
        if key == "visitor_locker":
            score = 1.0 if style in ("big_game", "traditionalist") and rng.random() < 0.15 else -5
        if key == "canopy":
            score -= 1.5
        if P["seats"] and team.capacity > st["fans"] * 1.05:
            score -= 1.5                                   # club seats, suites, students: only if they'd sell
    if key in STYLE_WANTS.get(style, ()):
        score += 1.0
    return score + rng.uniform(-0.6, 0.6)


def ai_build(league, team, rng, appetite=1.0):
    """The CPU AD's plan: seats if it keeps selling out, otherwise bring the building up to the program.
    It saves up for what it wants most; now and then it grabs something cheap instead."""
    st = ensure(team)
    if st.get("project"):
        return None
    opts = []
    for k in ORDER:
        lv = st["parts"][k]
        if lv >= max_tier(k) or missing(team, k, lv + 1):
            continue
        opts.append((_want(league, team, k, rng), k))
    opts = sorted((o for o in opts if o[0] > 0.3), reverse=True)
    if not opts:
        return None
    tries = opts[:1] + ([o for o in opts[1:4] if rng.random() < 0.35 * appetite])
    for _, k in tries:
        t = st["parts"][k] + 1
        for plan in plans(team, k, t):
            if plan == "build":
                continue                                    # CPU ADs don't touch the recruiting money
            if plan in BOND_TERMS and not (PARTS[k]["seats"] >= 4000 or k == "canopy"):
                continue                                    # they only borrow for the big pieces
            if plan in BOND_TERMS and fund(team) < price(team, k, t) * 0.25:
                continue                                    # a quarter down, at least
            ok, _, _, _ = can_build(league, team, k, plan)
            if ok:
                build(league, team, k, plan)
                return k
    return None


# ═══ Toughest places to play ═══════════════════════════════════════════════

def tough_score(league, team):
    """(score 0-100, parts) — the building, the crowd, the record, the scalps, the streak, the history."""
    st = ensure(team)
    nr = noise_rating(team)
    w, l, ranked, att, fill = season_home(league, team)
    log = [x for x in st["home_log"] if x[0] < league.year][-3:]
    if not att:                                          # no home games yet: last season's crowds, or a guess
        if log:
            att, fill = log[-1][4], log[-1][5]
        else:
            turnout = max(0.3, min(1.1, 0.6 + (team.prestige - 60) * 0.008 + comfort(team)))
            att = int(min(team.capacity, fanbase(team) * turnout))
            fill = att / team.capacity
    building = (nr - 1) / 9 * 20
    crowd = min(1.0, att / 100000) * 9 + min(1.0, fill) * 11
    # The record: this season counts double, shrunk toward .500 when there isn't much of it.
    hw = 2 * w + sum(x[1] for x in log)
    hl = 2 * l + sum(x[2] for x in log)
    pct = (hw + 3) / (hw + hl + 6)
    record = max(0.0, (pct - 0.25) / 0.75) * 35
    scalps_n = ranked + sum(x[3] for x in log)
    scalps = min(12.0, scalps_n * 3.0)
    streak = home_streak(league, team)
    streak_pts = min(8.0, streak * 0.6)
    tradition = max(0.0, min(5.0, (team.ratings.get("tradition", 60) - 50) / 9))
    total = building + crowd + record + scalps + streak_pts + tradition
    return round(total, 1), {"building": building, "crowd": crowd, "record": record, "scalps": scalps,
                             "streak": streak_pts, "tradition": tradition, "noise": nr, "att": att, "fill": fill,
                             "home": (w, l), "home3": (sum(x[1] for x in log) + w, sum(x[2] for x in log) + l),
                             "ranked": scalps_n, "run": streak}


def ranking(league):
    """[(team, score, parts)] best first."""
    rows = [(t,) + tough_score(league, t) for t in league.teams]
    rows.sort(key=lambda r: -r[1])
    return rows


def rank_of(league, team):
    cache = getattr(league, "_tough_cache", None)
    stamp = (league.year, league.week, sum(1 for w in league.schedule.values() for g in w if g.played))
    if not cache or cache[0] != stamp:
        cache = (stamp, {t: i for i, (t, _, _) in enumerate(ranking(league), 1)})
        league._tough_cache = cache
    return cache[1].get(team)


def snapshot(league):
    """Keep the final list of a finished season."""
    hist = league.__dict__.setdefault("tough_hist", {})
    hist[league.year] = [(t.school, s, round(p["noise"], 1), p["home"], p["att"]) for t, s, p in ranking(league)]
    for y in sorted(hist)[:-25]:
        del hist[y]


def last_final_rank(league, team, year=None):
    hist = getattr(league, "tough_hist", {})
    y = year if year is not None else max((y for y in hist if y < league.year), default=None)
    if y is None or y not in hist:
        return None
    for i, row in enumerate(hist[y], 1):
        if row[0] == team.school:
            return i
    return None
