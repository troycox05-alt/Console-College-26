"""
poscoach.py — Position coaches: the eight assistants under the coordinators.

Every FBS staff has a coach for each room:
  QB  quarterbacks      RB  running backs     WR  wide receivers   TE  tight ends
  OL  offensive line    DL  defensive line    LB  linebackers      DB  corners and safeties

Each one has three ratings (1-100) and an age, a ceiling and a résumé line:
  dev        how much his room improves — blended into development at a quarter
             of the weight (head coach and coordinator still do most of it)
  recruiting how hard he works the kids at his position — interest you earn with
             a recruit at his position moves up to about ±12%
  eye        how well he reads his own room — the practice report and the staff's
             depth chart are sharper (or blurrier) at his positions

They grow while they're young, slip when they're old, retire, and get poached.
A good one is a coordinator in waiting: promote him (he takes his ratings with
him) and his room opens up.

IDENTITY. Every position coach is a type, and the type shapes his ratings:
  Developer    builds players (DEV high, recruiting so-so) — his room grows faster
  Recruiter    wins living rooms (REC high, DEV often mediocre), extra pull in his region
  Technician   coaches the details (EVAL high): the sharpest read on his room
  Players' coach  his room's morale holds up, and his players stay when things go wrong
  Climber      wants a coordinator job yesterday: grows fast, leaves fast
  Loyalist     goes where his coordinator goes, and nowhere else
His DEV drives a real multiplier on his room's growth (an elite line coach builds
lines: about +25% growth; a poor one costs about 10%). Each recruits one region hard.

TIES. Coordinators collect "their guys": assistants who worked under them. A coordinator
hired somewhere tries to bring them. Fire him and his guys are unsettled (they may follow
him out the door), and the players he signed take it personally.
"""
import random

from names import full_name

GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
GROUP_OF = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "OL": "OL",
            "DL": "DL", "LB": "LB", "CB": "DB", "S": "DB"}
SIDE = {"QB": "OC", "RB": "OC", "WR": "OC", "TE": "OC", "OL": "OC", "DL": "DC", "LB": "DC", "DB": "DC"}
TITLE = {"QB": "quarterbacks", "RB": "running backs", "WR": "wide receivers", "TE": "tight ends",
         "OL": "offensive line", "DL": "defensive line", "LB": "linebackers", "DB": "defensive backs"}

DEV_WEIGHT = 0.25          # share of a player's development rating
RECRUIT_SPAN = 0.12        # max interest swing at his position


class PosCoach:
    def __init__(self, name, group, age, dev, rec, eye, ceiling, origin):
        self.name, self.group, self.age = name, group, age
        self.dev, self.rec, self.eye = dev, rec, eye
        self.ceiling, self.origin = ceiling, origin
        self.since = None
        self.school = None            # where he works now (a school name, not the team object)
        self.history = []             # [(year, school, group)]
        self.kind = "Developer"
        self.region = None            # recruiting region he works hardest
        self.ties = set()             # coordinators he has worked under (names)
        self.unhappy = None           # (year, why) after his coordinator was let go
        self.bonus = 0                # a raise you gave him to stay

    @property
    def overall(self):
        return round(self.dev * 0.45 + self.eye * 0.3 + self.rec * 0.25)

    @property
    def role(self):
        return "POS"


def _clamp(v):
    return int(max(25, min(97, round(v))))


_taken = []                # the last few surnames handed out (a candidate list never repeats one)


KINDS = {"Developer": (9, -5, 0), "Recruiter": (-6, 11, -2), "Technician": (2, -4, 10),
         "Players' coach": (0, 3, 0), "Climber": (2, 3, 1), "Loyalist": (0, 0, 2)}
KIND_WEIGHTS = {"Developer": 26, "Recruiter": 24, "Technician": 16, "Players' coach": 14, "Climber": 12, "Loyalist": 8}
KIND_NOTE = {"Developer": "builds players", "Recruiter": "wins living rooms", "Technician": "coaches the details",
             "Players' coach": "his room loves him", "Climber": "wants to run his own side",
             "Loyalist": "follows his coordinator"}


def make(rng, group, level, origin, league=None, age=None, kind=None):
    avoid = set(_taken)
    if league is not None:
        import staff
        avoid |= staff.coach_surnames(league)
    name = full_name(rng, avoid=avoid)
    _taken.append(name.split()[-1])
    del _taken[:-40]
    age = age or int(max(26, min(66, rng.gauss(41, 9))))
    kind = kind or rng.choices(list(KIND_WEIGHTS), weights=list(KIND_WEIGHTS.values()))[0]
    dd, dr, de = KINDS[kind]
    dev, rec, eye = _clamp(rng.gauss(level + dd, 7)), _clamp(rng.gauss(level + dr, 7)), _clamp(rng.gauss(level + de, 7))
    young = max(0, 45 - age)
    ceiling = _clamp(max(dev, rec, eye) + rng.uniform(0, 4 + young * 0.6) + (3 if kind == "Climber" else 0))
    c = PosCoach(name, group, age, dev, rec, eye, ceiling, origin)
    c.kind = kind
    from recruiting_data import STATES
    c.region = STATES[rng.choice(list(STATES))][1]
    _pick_spec(c, rng)
    return fields(c)


SPECIALTIES = {
    "QB whisperer":     ("QB",),
    "Line builder":     ("OL", "DL"),
    "Pipeline":         None,                # one state he owns
    "Retention":        None,                # his room rarely hits the portal
    "Film junkie":      None,                # sharpest eye on staff
    "Walk-on whisperer": None,               # walk-ons grow like scholarship kids
    "Closer":           None,                # four- and five-stars listen to him
}
SPEC_NOTE = {"QB whisperer": "quarterbacks grow 8% faster", "Line builder": "linemen grow 8% faster",
             "Pipeline": "owns one state", "Retention": "his players rarely hit the portal",
             "Film junkie": "the sharpest read on his room", "Walk-on whisperer": "walk-ons grow 20% faster",
             "Closer": "elite recruits listen to him"}


def _pick_spec(c, r):
    opts = [k for k, g in SPECIALTIES.items() if g is None or c.group in g]
    w = [3 if SPECIALTIES[k] else 1 for k in opts]
    c.spec = r.choices(opts, weights=w)[0]
    if c.spec == "Pipeline":
        from recruiting_data import STATES
        same = [s for s, v in STATES.items() if v[1] == c.region] or list(STATES)
        c.pipe_state = r.choice(same)


def spec_line(c):
    fields(c)
    s = c.spec
    if s == "Pipeline":
        from recruiting_data import STATES
        return f"Pipeline: {STATES.get(c.pipe_state, (c.pipe_state,))[0]}"
    return s


def fields(c):
    """Older saves: fill in what newer coaches carry (a type that fits the ratings he has)."""
    if "kind" not in c.__dict__:
        r = random.Random(f"kind:{c.name}")
        roll = r.random()
        if roll < 0.12:
            c.kind = "Players' coach"
        elif roll < 0.22:
            c.kind = "Climber" if c.age < 45 else "Loyalist"
        else:
            best = max((c.dev, "Developer"), (c.rec - 1, "Recruiter"), (c.eye - 3, "Technician"))
            c.kind = best[1]
    for k, v in (("region", None), ("unhappy", None), ("bonus", 0)):
        if k not in c.__dict__:
            setattr(c, k, v)
    if "ties" not in c.__dict__:
        c.ties = set()
    if c.region is None:
        from recruiting_data import STATES
        c.region = STATES[random.Random(f"reg:{c.name}").choice(list(STATES))][1]
    if "spec" not in c.__dict__:
        _pick_spec(c, random.Random(f"spec:{c.name}"))
    if "room_log" not in c.__dict__:
        c.room_log = []                   # [(year, school, his room's growth, the league's)]
    return c


def rep_score(c):
    """How his rooms have grown against the country's, the last three years (OVR points)."""
    log = fields(c).room_log[-3:]
    return sum(g - avg for _, _, g, avg in log) / len(log) if log else 0.0


def rep_word(c):
    v = rep_score(c)
    if not fields(c).room_log:
        return "Unproven"
    return ("Hot name" if v >= 1.5 else "Proven developer" if v >= 0.7 else "Steady" if v >= -0.6
            else "Struggling")


def room_reports(league):
    """End of the season: how much each room grew, against the national average for that room."""
    import development  # noqa: F401
    by_group = {}
    rows = []
    for team in league.teams:
        for g, c in staff_of(team).items():
            if c is None:
                continue
            gains = []
            for p in team.roster:
                if GROUP_OF.get(p.position) != g:
                    continue
                start = next((o for y, o in reversed(p.history) if y == league.year), None)
                if start is not None:
                    gains.append(p.overall - start)
            if gains:
                v = sum(gains) / len(gains)
                rows.append((c, team, v))
                by_group.setdefault(g, []).append(v)
    avg = {g: sum(v) / len(v) for g, v in by_group.items()}
    for c, team, v in rows:
        fields(c).room_log.append((league.year, team.school, round(v, 1), round(avg[c.group], 1)))
        del c.room_log[:-6]


def level_for(team):
    return team.ratings.get("coach", 65) - 8 + (team.prestige - 60) * 0.15


def staff_of(team):
    return team.__dict__.setdefault("pos_coaches", {})


def ensure(league):
    """Every FBS program gets a full room of position coaches (new worlds and older saves)."""
    league.__dict__.setdefault("pos_pool", [])
    for team in league.teams:
        room = staff_of(team)
        for g in GROUPS:
            if room.get(g) is None:
                r = random.Random(f"pos:{team.school}:{g}:{league.year}")
                c = make(r, g, level_for(team), f"{team.school} {TITLE[g]} coach", league)
                c.school, c.since = team.school, league.year - r.choice((0, 1, 1, 2, 3, 5))
                room[g] = c
            else:
                fields(room[g])
    if not league.__dict__.get("_pos_ties"):
        league._pos_ties = True
        for team in league.teams:
            for role in ("OC", "DC"):
                coord = getattr(team, "oc" if role == "OC" else "dc", None)
                if coord is None:
                    continue
                mine = [c for g, c in staff_of(team).items() if c is not None and SIDE[g] == role]
                r = random.Random(f"ties:{team.school}:{role}")
                for c in r.sample(mine, min(len(mine), r.choice((1, 2, 2, 3)))):
                    tie(coord, c)
            for p in team.roster:                       # who signed whom, roughly
                seed_signee(team, p)


def all_coaches(league):
    return [c for t in league.teams for c in staff_of(t).values() if c is not None]


def of(team, position):
    if team is None:
        return None
    g = GROUP_OF.get(position)
    return staff_of(team).get(g) if g else None


# ═══ What they do ═══════════════════════════════════════════════════════════

def dev_blend(team, position, value):
    c = of(team, position)
    return value if c is None else value * (1 - DEV_WEIGHT) + c.dev * DEV_WEIGHT


def room_mult(team, position, player=None):
    """His room's growth: an elite developer builds players (about +25%), a poor one costs about 10%."""
    c = of(team, position)
    if c is None:
        return 1.0
    fields(c)
    m = 1 + (c.dev - 65) / 120
    if c.kind == "Developer":
        m *= 1.06
    if c.spec in ("QB whisperer", "Line builder"):
        m *= 1.08
    if c.spec == "Walk-on whisperer" and player is not None and getattr(player, "walk_on", False):
        m *= 1.2
    if c.unhappy:
        m *= 0.97
    return max(0.85, min(1.35, m))


def recruit_mult(team, position, recruit=None):
    c = of(team, position)
    if c is None:
        return 1.0
    fields(c)
    m = (c.rec - 62) / 230
    if c.kind == "Recruiter":
        m += 0.04
    if recruit is not None and c.region and getattr(recruit, "region", None) == c.region:
        m += 0.06 if c.kind == "Recruiter" else 0.035
    if recruit is not None and c.spec == "Pipeline" and getattr(recruit, "home_state", None) == c.pipe_state:
        m += 0.08
    if recruit is not None and c.spec == "Closer" and getattr(recruit, "stars", 0) >= 4:
        m += 0.06
    if c.unhappy:
        m -= 0.04
    return 1 + max(-0.15, min(0.22, m))


def eye_mult(team, position):
    """Blur multiplier for the staff's read at this position (0.7 sharp .. 1.3 shaky)."""
    c = of(team, position)
    if c is None:
        return 1.0
    fields(c)
    m = 1.3 - (c.eye - 40) / 90
    if c.kind == "Technician":
        m *= 0.9
    if c.spec == "Film junkie":
        m *= 0.85
    return max(0.7, min(1.3, m))


def portal_mult(team, player):
    """A Retention coach keeps his room home; an unsettled one doesn't."""
    c = of(team, player.position)
    if c is None:
        return 1.0
    fields(c)
    return (0.75 if c.spec == "Retention" else 1.0) * (1.15 if c.unhappy else 1.0)


def morale_cushion(team, position):
    """A players' coach softens bad news in his room."""
    c = of(team, position)
    return 0.6 if c is not None and fields(c).kind == "Players' coach" else 1.0


# ═══ Ties: a coordinator's guys ═════════════════════════════════════════════

def tie(coord, c):
    fields(c)
    c.ties.add(coord.name)
    coord.__dict__.setdefault("assistants", set()).add(c.name)


def guys_of(league, coord):
    """His guys who are position coaches somewhere right now: [(team, group, coach)]."""
    names = coord.__dict__.get("assistants", set())
    if not names:
        return []
    out = []
    for t in league.teams:
        for g, c in staff_of(t).items():
            if c is not None and c.name in names:
                out.append((t, g, c))
    for c in league.__dict__.get("pos_pool", []):
        if c.name in names:
            out.append((None, c.group, c))
    return out


def seed_signee(team, p):
    """Tag a player with the coordinator and position coach who signed him (older rosters: a guess)."""
    if "signed_coord" in p.__dict__:
        return
    import staff
    coord = staff.side_coach(team, p.position)
    pc = of(team, p.position)
    yrs = max(0, p.year + (1 if getattr(p, "redshirt", False) else 0))
    if coord is not None and getattr(coord, "coord_since", 9999) <= team_year(team) - yrs:
        p.signed_coord = coord.name
    else:
        p.signed_coord = None
    p.signed_pos = pc.name if pc is not None and (pc.since or 9999) <= team_year(team) - yrs else None


def team_year(team):
    return max((y for y, *_ in getattr(team, "historical_records", [])), default=2025) + 1


def tag_signee(team, p):
    import staff
    coord = staff.side_coach(team, p.position)
    pc = of(team, p.position)
    p.signed_coord = coord.name if coord is not None else None
    p.signed_pos = pc.name if pc is not None else None


def fallout(league, team, coach, role=None, quiet=True):
    """A coordinator (or position coach) is let go: his guys on staff are unsettled and the players
    he signed take it personally. Returns lines describing it."""
    lines = []
    import morale
    if role in ("OC", "DC"):
        for g, c in staff_of(team).items():
            if c is not None and SIDE[g] == role and coach.name in fields(c).ties:
                c.unhappy = (league.year, coach.name)
                lines.append(f"{c.name} ({TITLE[g]}) was one of {coach.name.split()[-1]}'s guys — he's unsettled.")
        hit, who = -12, "signed_coord"
    else:
        hit, who = -8, "signed_pos"
    n = 0
    for p in team.roster:
        if p.__dict__.get(who) == coach.name:
            morale.nudge(p, hit * morale_cushion(team, p.position), f"{coach.name}, who recruited him, is gone", league)
            n += 1
    if n:
        lines.append(f"{n} player{'s' if n != 1 else ''} {coach.name.split()[-1]} recruited took the news hard "
                     f"(morale down; some may think about the portal).")
    return lines


# ═══ Money ════════════════════════════════════════════════════════════════════
# A standard room (eight coaches at the program's own level) is part of operations already.
# What you pay above it — or save below it — comes out of (or back into) the money for players.

POS_SHARE = 0.012          # one position coach at the program's level, as a share of the budget


def salary(c, team):
    import finance
    q = max(0.45, min(2.0, 1 + (c.overall - level_for(team)) / 22 + max(-0.1, rep_score(fields(c)) * 0.05)))
    return int(round(POS_SHARE * finance.budget(team) * q / 5000) * 5000) + int(c.__dict__.get("bonus", 0))


def payroll_delta(team):
    """Above (+) or below (-) a standard room's cost."""
    room = team.__dict__.get("pos_coaches")
    if not room:
        return 0
    import finance
    std = POS_SHARE * finance.budget(team)
    return int(sum(salary(c, team) - std for c in room.values() if c is not None))


# ═══ The market ═════════════════════════════════════════════════════════════

def word(v):
    return ("Elite" if v >= 85 else "Great" if v >= 77 else "Good" if v >= 69 else
            "Average" if v >= 60 else "Shaky" if v >= 52 else "Poor")


def potential(c):
    room = c.ceiling - max(c.dev, c.rec, c.eye)
    return "Maxed" if room <= 1 else "Some" if room <= 5 else "High" if room <= 11 else "Very high"


def candidates(league, team, group, rng):
    """Who'd take this job: a few rising names, assistants at smaller programs, and anyone out of work."""
    lvl = level_for(team)
    out = []
    for c in league.__dict__.get("pos_pool", []):
        if c.group == group or rng.random() < 0.25:
            out.append(fields(c))
    smaller = [t for t in league.teams if t is not team and t.prestige < team.prestige - 3]
    rng.shuffle(smaller)
    for t in smaller[:3]:
        c = staff_of(t).get(group)
        if c is not None:
            out.append(c)
    kinds = [("hs", -6, (30, 52)), ("ga", -9, (25, 31)), ("fcs", -4, (29, 50)), ("nfl", 0, (34, 58)),
             ("analyst", -3, (27, 44))]
    for kind, d, ages in kinds:
        origin = {"hs": "high school head coach", "ga": "graduate assistant", "fcs": "FCS position coach",
                  "nfl": "NFL assistant", "analyst": "off-field analyst"}[kind]
        c = make(rng, group, lvl + d, origin, league, age=rng.randint(*ages))
        if kind == "ga":
            c.ceiling = min(90, c.ceiling + 4)          # the young ones have a little more upside — a little
        c._fresh = True
        out.append(c)
    return sorted(out, key=lambda c: -c.overall)[:10]


def willing(league, team, c):
    # A coach who just signed this winter does not immediately turn around and leave.
    if getattr(c, "since", None) is not None and c.since >= league.year + 1:
        return False
    try:
        import hiring_market
        return hiring_market.pos_interest(league, team, c) >= 12
    except Exception:
        if c.school is None:
            return True
        cur = next((t for t in league.teams if t.school == c.school), None)
        return cur is None or team.prestige > cur.prestige


def _remove_from(league, c, why):
    cur = next((t for t in league.teams if t.school == c.school), None)
    if cur is not None and staff_of(cur).get(c.group) is c:
        staff_of(cur)[c.group] = None
        log(league, cur, c, why)
    return cur


def hire(league, team, group, c, refill=True):
    if c in league.__dict__.get("pos_pool", []):
        league.pos_pool.remove(c)
    old = _remove_from(league, c, f"left for {team.school}") if c.school else None
    if old is not None and refill:                      # the school he left fills his chair
        r = random.Random(f"refill:{old.school}:{group}:{league.year}")
        n = make(r, group, level_for(old) - 2, f"promoted at {old.school}", league)
        n.school, n.since = old.school, league.year + 1
        staff_of(old)[group] = n
    c.__dict__.pop("_fresh", None)
    fields(c).unhappy = None
    c.bonus = 0
    c.group, c.school, c.since = group, team.school, league.year + 1
    c.history.append((league.year + 1, team.school, group))
    staff_of(team)[group] = c
    log(league, team, c, "hired")


def fire(league, team, group):
    c = staff_of(team).get(group)
    if c is None:
        return None
    staff_of(team)[group] = None
    c.school = None
    league.__dict__.setdefault("pos_pool", []).append(c)
    log(league, team, c, "fired")
    c._fallout = fallout(league, team, c)
    return c


def as_coordinator(league, pc, role, school=None):
    """A position coach as a coordinator candidate (a new Coach; nobody is moved yet)."""
    import staff
    fields(pc)
    r = random.Random(f"promote:{pc.name}:{league.year}:{role}")
    where = school or pc.school or "former"
    c = staff.make_coordinator(league, role, r, level=(pc.dev + pc.eye) / 2,
                               origin=f"{where} {TITLE[pc.group]} coach", age=pc.age, name=pc.name)
    for k in staff.SIDE_KEYS[role]:
        c.ratings[k] = _clamp((c.ratings[k] + pc.dev * 2) / 3)
    c.ratings["recruiting"] = pc.rec
    c.overall = int(max(40, min(80, round((pc.dev + pc.eye) / 2 - 7))))    # coaching a room isn't running a side of the ball
    from carousel import roll_ceiling
    c.ceiling = max(c.overall + 2, min(pc.ceiling - 2, roll_ceiling(c.overall, r, room=11 if pc.age <= 40 else 4)))
    c.personality = "climber" if pc.kind == "Climber" else c.personality
    c.recruit_region = pc.region or c.recruit_region
    c.assistants = set()
    c._generated = True
    c._from_pos = pc
    return c


def coord_candidates(league, team, role, n=4):
    """Position coaches on that side of the ball who are ready to run it: [(pc, their team)]."""
    pool = []
    for t in league.teams:
        for g, c in staff_of(t).items():
            if c is None or SIDE[g] != role or c.age > 60:
                continue
            ready = (c.dev + c.eye) / 2 + (4 if fields(c).kind == "Climber" else 0) + rep_score(c) * 2
            if ready >= 66 or t is team:
                pool.append((ready + (3 if t is team else 0), c, t))
    pool.sort(key=lambda x: -x[0])
    return [(c, t) for _, c, t in pool[:n]]


def colleagues(team, pc):
    """The assistants a newly promoted coordinator would want: his side's best colleagues."""
    side = SIDE[pc.group]
    mates = [c for g, c in staff_of(team).items() if c is not None and c is not pc and SIDE[g] == side
             and (c.since or 0) <= (pc.since or 0) + 1 and (c.since or 0) < team_year(team) + 1]
    return sorted(mates, key=lambda c: -c.overall)[:2]


def promote(league, team, group):
    """Make a position coach the coordinator on his side of the ball. Returns the new
    coordinator (the old one, if any, is let go first by the caller)."""
    import staff
    pc = staff_of(team).get(group)
    if pc is None:
        return None
    role = SIDE[group]
    c = as_coordinator(league, pc, role, school=team.school)
    c.origin = f"{team.school} {TITLE[group]} coach, promoted"
    for mate in colleagues(team, pc):
        tie(c, mate)
    staff_of(team)[group] = None
    staff._hire(league, team, role, c, team.conference in staff._power())
    log(league, team, pc, f"promoted to {role}")
    return c


def log(league, team, c, what):
    book = league.__dict__.setdefault("pos_moves", {}).setdefault(league.year, [])
    book.append((team.school, c.group, c.name, what))


# ═══ Every offseason ════════════════════════════════════════════════════════

def offseason(league, rng):
    """Growth and decline, retirements, and CPU staffs replacing the coaches they lose."""
    ensure(league)
    import staff
    me = staff.user_team(league)
    for team in league.teams:
        room = staff_of(team)
        for g in GROUPS:
            c = room.get(g)
            if c is None:
                continue
            c.age += 1
            for k in ("dev", "rec", "eye"):
                v = getattr(c, k)
                if c.age <= 45 and v < c.ceiling:
                    v += rng.choice((0, 1, 1, 2, 2, 3))
                elif c.age >= 58:
                    v -= rng.choice((0, 1, 1, 2))
                setattr(c, k, _clamp(min(v, c.ceiling)))
            if c.age >= 63 and rng.random() < 0.1 + (c.age - 63) * 0.06:
                room[g] = None
                log(league, team, c, "retired")
                continue
            if team is me:
                continue                                # your staff: your calls
            leave = 0.05 + (0.05 if c.kind == "Climber" else 0) - (0.03 if c.kind == "Loyalist" else 0)
            if rng.random() < leave:                    # moved on, out of coaching, or a job nobody tracks
                room[g] = None
                log(league, team, c, "left")
                if rng.random() < 0.6:
                    c.school = None
                    league.pos_pool.append(c)
        for role in ("OC", "DC"):                       # years together make a coordinator's guys
            coord = getattr(team, "oc" if role == "OC" else "dc", None)
            if coord is None:
                continue
            for g, c in room.items():
                if c is not None and SIDE[g] == role and coord.name not in fields(c).ties \
                        and rng.random() < 0.3 and len(coord.__dict__.get("assistants", ())) < 5:
                    tie(coord, c)
    league.pos_pool = [c for c in league.pos_pool if c.age < 66 and rng.random() < 0.8][-60:]


def fill_yours(league, team):
    """Any room you left empty gets an interim coach from a graduate assistant job."""
    for g in GROUPS:
        if staff_of(team).get(g) is None:
            r = random.Random(f"interim:{team.school}:{g}:{league.year}")
            n = make(r, g, level_for(team) - 8, "graduate assistant (interim)", league, age=r.randint(25, 30))
            n.school, n.since = team.school, league.year + 1
            staff_of(team)[g] = n


def fill_cpu(league, rng):
    """Safety net after the carousel: any CPU room still empty gets someone."""
    import staff
    me = staff.user_team(league)
    for team in league.teams:
        if team is me:
            continue
        for g in GROUPS:
            if staff_of(team).get(g) is None:
                n = make(rng, g, level_for(team), "hired from elsewhere", league)
                n.school, n.since = team.school, league.year + 1
                staff_of(team)[g] = n
