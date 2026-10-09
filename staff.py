"""
staff.py — Coordinators: the offensive and defensive coordinators on every
FBS staff, their resumes, and the staff carousel that runs every offseason.

A coordinator is a Coach with a role ("OC" or "DC"). He starts out rated
below the head coaches at his level, but his ceiling runs higher: the good
ones grow into head coaches. What he does shows up in four places, each at
a fraction of the head coach's weight:

  games        his side's in-game adjustments, blitz / trick-play nerve, and
               his traits (half strength) — HC 65% / coordinator 35%
  development  players on his side of the ball — HC 60% / coordinator 40%
  recruiting   staff recruiting hours and pull — HC 60% / each coordinator 20%,
               plus a boost with recruits from his home region
  his resume   every season: points, yards, passing and rushing per game (or
               allowed per game), national ranks, and how the unit did against
               what its talent said it should. Head coach searches read it.

The staff carousel, once a year after the head coaching carousel:
  1. Units are graded, coordinators grow (or slip), get older, retire.
  2. A new head coach cleans house — most coordinators leave, a few stay —
     and brings the people he's worked with.
  3. Coordinators whose units flopped get fired, sooner when the head
     coach's own seat is hot.
  4. Every opening is filled, biggest programs first. Power programs hire
     coordinators away from smaller ones; Group of Five programs promote
     high school and FCS coaches; fired head coaches land as coordinators.
"""
import world
import random

from names import FIRST_NAMES, LAST_NAMES, full_name
from recruiting_data import STATES

ROLE_NAMES = {"OC": "offensive coordinator", "DC": "defensive coordinator"}
ROLE_SHORT = {"OC": "OC", "DC": "DC", "HC": "HC"}
SIDE_KEYS = {"OC": ("passing_dev", "offense_dev", "trench_dev"), "DC": ("db_dev", "trench_dev")}
OFF_POS = {"QB", "RB", "WR", "TE", "OL"}
DEF_POS = {"DL", "LB", "CB", "S"}

GAME_WEIGHT = 0.35          # coordinator's share of his side's play-calling brain
DEV_WEIGHT = 0.40           # ...of development on his side of the ball
RECRUIT_WEIGHT = 0.20       # each coordinator's share of the staff's recruiting
REGION_PULL = 0.12          # interest boost per coordinator from a recruit's region
HC_BRING_ODDS = 0.55        # a new head coach's former coordinator follows him
STAY_ODDS = 0.28            # a coordinator survives a head coaching change


# ═══ Who's on the staff ═════════════════════════════════════════════════════

def role_of(coach):
    return getattr(coach, "role", "HC")


def side_coach(team, position):
    """The coordinator responsible for this position, if the team has one."""
    if position in OFF_POS:
        return getattr(team, "oc", None)
    if position in DEF_POS:
        return getattr(team, "dc", None)
    return None


def coach_surnames(league):
    """Every surname already on a coaching staff or in the candidate pools — a new
    coach gets one nobody else in the profession has, so 'Rogers' means one man."""
    out = set()
    for t in getattr(league, "teams", []):
        for c in (t.coach, getattr(t, "oc", None), getattr(t, "dc", None)):
            if c is not None:
                out.add(c.name.split()[-1])
    for c in list(getattr(league, "coach_pool", [])) + list(getattr(league, "staff_pool", [])):
        out.add(c.name.split()[-1])
    return out


def coordinators(league):
    return [c for t in league.teams for c in (getattr(t, "oc", None), getattr(t, "dc", None)) if c is not None]


def blend(hc_value, coord_value, weight):
    if coord_value is None:
        return hc_value
    return hc_value * (1 - weight) + coord_value * weight


def dev_rating(team, coach, position):
    """Development rating for a position: the head coach's, blended with the
    coordinator who runs that side of the ball."""
    c = side_coach(team, position) if team is not None else None
    if coach is None:                                     # no head coach right now (the job is open): the staff carries it
        base = c.dev_rating_for(position) if c is not None else 60
    else:
        base = coach.dev_rating_for(position)
    import skills
    w = DEV_WEIGHT * (1.5 if team is not None and skills.team_has(team, "staff_developer") else 1.0)
    v = blend(base, c.dev_rating_for(position) if c else None, w)
    import poscoach
    return poscoach.dev_blend(team, position, v)          # his position coach


def recruiting_rating(team):
    """The staff's recruiting: the head coach, and both coordinators on the road."""
    hc = team.coach.ratings["recruiting"] if team.coach is not None else 60
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    if oc is None and dc is None:
        return hc
    parts = [(hc, 1 - 2 * RECRUIT_WEIGHT)]
    for c in (oc, dc):
        parts.append((c.ratings["recruiting"] if c else hc, RECRUIT_WEIGHT))
    return sum(v * w for v, w in parts)


def region_pull(team, recruit):
    """Coordinators recruit the part of the country they're from."""
    n = sum(1 for c in (getattr(team, "oc", None), getattr(team, "dc", None))
            if c is not None and getattr(c, "recruit_region", None) == getattr(recruit, "region", None))
    return 1 + REGION_PULL * n


def _weight(team, side):
    """The coordinator's share of his side: most of it when he calls the plays."""
    return CALLER_WEIGHT if calls(team)["off" if side == "off" else "def"] != "HC" else GAME_WEIGHT


def game_iq(team, side):
    """How well this staff reads a game on one side of the ball (for GamePlan)."""
    import coach_profile
    from traits import mod as trait_mod
    hc_obj = team.coach
    hc = 0.55 * getattr(hc_obj, "overall", 70) + 0.45 * coach_profile.value(hc_obj, "game_day")
    hc += (trait_mod(hc_obj, "off_iq", 0.0) if side == "off" else trait_mod(hc_obj, "def_iq", 0.0))
    c = getattr(team, "oc" if side == "off" else "dc", None)
    cv = None
    if c is not None:
        cv = 0.55 * c.overall + 0.45 * coach_profile.value(c, "game_day")
        cv += (trait_mod(c, "off_iq", 0.0) if side == "off" else trait_mod(c, "def_iq", 0.0))
    return blend(hc, cv, _weight(team, side))


def aggression(team, side):
    hc = team.coach.aggression
    c = getattr(team, "oc" if side == "off" else "dc", None)
    return blend(hc, c.aggression if c else None, _weight(team, side))


def blitz(team):
    """How often the defense sends pressure: the head coach's blitz appetite (his fourth-down
    nerve unless he set one of his own) blended with his coordinator's."""
    hc = getattr(team.coach, "blitz", None)
    hc = team.coach.aggression if hc is None else hc
    c = getattr(team, "dc", None)
    cb = None if c is None else (getattr(c, "blitz", None) if getattr(c, "blitz", None) is not None else c.aggression)
    return blend(hc, cb, _weight(team, "def"))


def trait_share(team, key):
    """Coordinators' traits count at half strength."""
    from traits import mod as trait_mod
    total = 0.0
    for c in (getattr(team, "oc", None), getattr(team, "dc", None)):
        if c is not None:
            total += 0.5 * trait_mod(c, key, 0.0)
    return total


# ═══ Who calls the plays ═════════════════════════════════════════════════════
# Every head coach decides, side by side, whether he calls it himself or hands
# it to his coordinator. The caller's scheme is what the team runs that day and
# what it recruits to; the caller carries most of that side's in-game brain.

CALLER_WEIGHT = 0.70        # the play-caller's share of his side's game IQ / aggression


def _hc_lean(coach):
    """Offensive or defensive by background: (off-side dev) - (def-side dev)."""
    r = coach.ratings
    return (r["passing_dev"] + r["offense_dev"]) / 2 - r["db_dev"]


def default_calls(team):
    """What a head coach decides when his staff changes: call a side himself, or hand
    it to the coordinator. Offensive minds tend to keep the offense, defensive minds
    the defense — unless the coordinator he just hired is clearly better at it."""
    import zlib
    c = team.coach
    if c is None:
        return {"off": "OC", "def": "DC"}
    if getattr(c, "is_user", False):
        return {"off": "HC", "def": "HC"}          # you picked both schemes; you call both until you say otherwise
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    r = c.ratings
    lean = _hc_lean(c)
    h = zlib.crc32(f"calls|{c.name}|{getattr(oc, 'name', '')}|{getattr(dc, 'name', '')}".encode()) / 2 ** 32
    h2 = zlib.crc32(f"calls2|{c.name}|{getattr(dc, 'name', '')}".encode()) / 2 ** 32
    off_skill = (r["passing_dev"] + r["offense_dev"]) / 2
    def_skill = (r["db_dev"] + r["trench_dev"]) / 2
    # Offense
    if oc is None:
        off = True
    else:
        want = 0.8 if lean >= 4 else 0.08 if lean <= -4 else 0.35
        if oc.overall >= off_skill + 6:
            want *= 0.4                              # the new OC is better at this than he is
        off = h < want
    # Defense
    if dc is None:
        df = True
    else:
        want = 0.65 if lean <= -4 else 0.05 if lean >= 4 else 0.2
        if dc.overall >= def_skill + 6:
            want *= 0.4
        df = h2 < want
    return {"off": "HC" if off else "OC", "def": "HC" if df else "DC"}


def _staff_key(team):
    return (getattr(team.coach, "name", None), getattr(getattr(team, "oc", None), "name", None),
            getattr(getattr(team, "dc", None), "name", None))


def calls(team):
    """{'off': 'HC'|'OC', 'def': 'HC'|'DC'}. Your own choice stands; an AI head coach
    decides again whenever his staff changes."""
    mine = getattr(team, "play_calls", None)
    if mine and getattr(team, "play_calls_coach", None) is team.coach and getattr(team.coach, "is_user", False):
        return mine
    if mine and getattr(team, "play_calls_key", None) == _staff_key(team):
        return mine
    decided = default_calls(team)
    if team.coach is not None:
        team.play_calls, team.play_calls_key = decided, _staff_key(team)
        team.play_calls_coach = team.coach if getattr(team.coach, "is_user", False) else None
    return decided


def set_calls(team, off=None, df=None):
    cur = dict(calls(team))
    if off is not None:
        cur["off"] = off
    if df is not None:
        cur["def"] = df
    team.play_calls, team.play_calls_coach, team.play_calls_key = cur, team.coach, _staff_key(team)
    for side, role in (("off", "OC"), ("def", "DC")):              # a play-calling promise you just broke
        c = getattr(team, "oc" if role == "OC" else "dc", None)
        promised = c.__dict__.get("promised_calls") if c is not None else None
        if promised and promised[1] == side and cur[side] != role and not c.__dict__.get("calls_promise_broken"):
            c.__dict__["calls_promise_broken"] = True
            import season as _season
            c.stay_lean = (_season._YEAR[0], 1)                    # he'll take other schools' calls now
            try:
                from ui import C, paint
                print(paint(f"   {c.name} was promised the play-calling when you hired him. He won't forget this.",
                            C.BRED, C.BOLD))
            except Exception:
                pass


def play_caller(team, side):
    """The coach calling this side's plays today (falls back to the head coach
    when the coordinator's chair is empty)."""
    key = "off" if side == "off" else "def"
    if calls(team)[key] == "HC":
        return team.coach
    c = getattr(team, "oc" if key == "off" else "dc", None)
    return c if c is not None else team.coach


def called_schemes(team):
    """(offense, defense) the team actually runs — the play-callers' schemes."""
    return play_caller(team, "off").offense_scheme, play_caller(team, "def").defense_scheme


def caller_label(team, side):
    c = play_caller(team, side)
    return "head coach" if c is team.coach else ("OC" if side == "off" else "DC")


# ═══ Making coordinators ════════════════════════════════════════════════════

def make_coordinator(league, role, rng, anchor=None, level=None, origin=None, age=None, name=None):
    """A new coordinator. `anchor` is a head coach whose ratings set the level
    of his side of the ball (so a staff develops players about as well as the
    head coach alone would); otherwise `level` does."""
    from models import Coach
    from carousel import init_coach, PERSONALITY_WEIGHTS
    from traits import assign_coach_traits
    name = name or full_name(rng, avoid=coach_surnames(league))
    ratings = {}
    for key in Coach.RATING_KEYS:
        center = anchor.ratings[key] if anchor is not None else level
        if key == "recruiting":
            v = rng.gauss(center, 7)
        elif key in SIDE_KEYS[role]:
            v = rng.gauss(center + 1, 6)
        elif key == "special_dev":
            v = rng.gauss(center - 6, 6)
        else:
            v = rng.gauss(center - 11, 6)                     # the other side of the ball
        ratings[key] = int(max(25, min(97, round(v))))
    base = anchor.overall if anchor is not None else level
    ovr = int(max(38, min(88, round(rng.gauss(base - 9, 4)))))
    off_s = anchor.offense_scheme if anchor is not None and rng.random() < 0.7 else \
        rng.choice(["Spread RPO", "Pro Style", "West Coast", "Air Raid", "Smashmouth"])
    def_s = anchor.defense_scheme if anchor is not None and rng.random() < 0.7 else \
        rng.choice(["4-2-5 Quarters", "4-3 Zone", "Pressure 3-4", "Multiple Man", "3-3-5 Stack"])
    c = Coach(name, ovr, ratings, off_s, def_s, int(max(10, min(95, rng.gauss(55, 14)))))
    import coach_profile
    coach_profile.shape(c)
    c.team = None
    assign_coach_traits(c, rng)
    if len(c.traits) > 1 and rng.random() < 0.6:
        c.traits = c.traits[:1]
    init_coach(c, league.year, origin=origin or "position coach")
    c.age = age or int(max(MIN_AGE["coord"], min(64, rng.gauss(43, 7))))
    from carousel import roll_ceiling
    c.ceiling = min(roll_ceiling(ovr, rng, room=11), ovr + 18)  # room to grow; elite is still rare, and never +23
    from carousel import fit_ceiling
    fit_ceiling(c)                                               # ...but less of it every year he ages
    keys, weights = zip(*PERSONALITY_WEIGHTS.items())
    c.personality = rng.choices(keys, weights=[w * (1.6 if k == "climber" else 1) for k, w in zip(keys, weights)])[0]
    c.role = role
    c.coord_history = []
    c.staff_ties = set()
    c.recruit_region = STATES[rng.choice(list(STATES))][1]
    c.hired_year = None
    c.status = "unemployed"
    return c


def spread_regions(team):
    """A staff covers ground: the two coordinators recruit different regions, and
    one of them works the school's own backyard (a Texas school's staff is in Texas).
    A Homebody keeps his region."""
    from recruiting_data import REGION_NEIGHBORS
    import carousel
    home = carousel.region_of(team)
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    staff_ = [c for c in (oc, dc) if c is not None]
    if not home or not staff_:
        return
    fixed = [c for c in staff_ if getattr(c, "personality", None) == "homebody"]
    free = [c for c in staff_ if c not in fixed]
    taken = {getattr(c, "recruit_region", None) for c in fixed}
    if home not in taken and free:
        # the one already in the home region keeps it; otherwise the first free coordinator takes it
        mover = next((c for c in free if getattr(c, "recruit_region", None) == home), free[0])
        mover.recruit_region = home
        taken.add(home)
        free.remove(mover)
    for c in free:
        if getattr(c, "recruit_region", None) in taken:
            near = sorted(REGION_NEIGHBORS.get(home, ()) - taken) or sorted(set(REGION_NEIGHBORS) - taken)
            if near:
                c.recruit_region = random.Random(c.name).choice(near)
        taken.add(c.recruit_region)


def _attach(league, team, c, role, how, source):
    c.role = role
    c.team = team
    c.status = "employed"
    c.coord_since = league.year + 1
    c.__dict__.setdefault("coord_history", [])
    c.__dict__.setdefault("staff_ties", set())
    c.__dict__.setdefault("recruit_region", STATES[random.Random(c.name).choice(list(STATES))][1])
    setattr(team, "oc" if role == "OC" else "dc", c)
    spread_regions(team)
    if team.coach is not None:
        c.staff_ties.add(team.coach.name)
        team.coach.__dict__.setdefault("staff_ties", set()).add(c.name)
    if c in getattr(league, "staff_pool", []):
        league.staff_pool.remove(c)
    if c in league.coach_pool:
        league.coach_pool.remove(c)
    _staff_move(league, "in", team, role, c, how=how, source=source)


def _detach(league, team, role, why, dest=None):
    c = getattr(team, "oc" if role == "OC" else "dc", None)
    if c is None:
        return None
    setattr(team, "oc" if role == "OC" else "dc", None)
    _staff_move(league, "out", team, role, c, why=why, dest=dest)
    import finance
    finance.release(league, team, c, fired=why in ("fired", "cleaned out"))   # let go with years left: still paid
    if why in ("fired", "cleaned out"):
        c.let_go = (team.school, league.year)          # that school won't hire him right back
        import poscoach
        c._fallout = poscoach.fallout(league, team, c, role)   # his guys are unsettled; his signees are hurt
    c.team = None
    if why in ("fired", "cleaned out", "left", "contract up"):
        c.status = "unemployed"
        c.pool_years = 0
        if why != "left":
            league.__dict__.setdefault("staff_pool", []).append(c)
    return c


def setup(league, rng=None):
    """Give every FBS program an OC and a DC (new worlds, and older saves)."""
    league.__dict__.setdefault("staff_pool", [])
    league.__dict__.setdefault("staff_moves", {})
    import poscoach
    poscoach.ensure(league)                            # and a full room of position coaches
    for team in league.teams:
        for role in ("OC", "DC"):
            attr = "oc" if role == "OC" else "dc"
            if getattr(team, attr, None) is not None:
                continue
            r = random.Random(f"staff:{team.school}:{role}:{league.year}")
            c = make_coordinator(league, role, r, anchor=team.coach,
                                 origin=f"{team.school} {ROLE_NAMES[role]}")
            c.role, c.team, c.status = role, team, "employed"
            c.coord_since = league.year - r.choice((0, 0, 1, 1, 2, 3, 4))
            c.coord_since = max(c.coord_since, league.year - (c.age - MIN_AGE["coord"]))   # nobody runs a unit at 26
            setattr(team, attr, c)
            c.staff_ties.add(team.coach.name)
            team.coach.__dict__.setdefault("staff_ties", set()).add(c.name)


# ═══ The book: a coordinator's season ═══════════════════════════════════════

def unit_lines(league):
    """Every FBS team's offense and defense this season, with national ranks."""
    lines = {}
    for team in league.teams:
        g = pf = pa = py = ry = opy = ory = 0
        for game in league.team_games(team):
            if not game.played or game.box is None:
                continue
            opp = game.opponent_of(team)
            me, them = game.box.team_stats[team], game.box.team_stats[opp]
            g += 1
            pf += game.score_for(team)
            pa += game.score_for(opp)
            py, ry = py + me["pass_yds"], ry + me["rush_yds"]
            opy, ory = opy + them["pass_yds"], ory + them["rush_yds"]
        if not g:
            continue
        lines[team] = {"g": g, "ppg": pf / g, "pass": py / g, "rush": ry / g, "ypg": (py + ry) / g,
                       "papg": pa / g, "pass_a": opy / g, "rush_a": ory / g, "ypg_a": (opy + ory) / g}
    teams = list(lines)

    def rank(key, reverse):
        order = sorted(teams, key=lambda t: lines[t][key], reverse=reverse)
        return {t: i for i, t in enumerate(order, 1)}

    ranks = {
        "ppg": rank("ppg", True), "ypg": rank("ypg", True), "pass": rank("pass", True), "rush": rank("rush", True),
        "papg": rank("papg", False), "ypg_a": rank("ypg_a", False),
        "pass_a": rank("pass_a", False), "rush_a": rank("rush_a", False),
    }
    off_score = {t: lines[t]["ppg"] + lines[t]["ypg"] / 15 for t in teams}
    def_score = {t: lines[t]["papg"] + lines[t]["ypg_a"] / 15 for t in teams}
    off_rank = {t: i for i, t in enumerate(sorted(teams, key=lambda t: -off_score[t]), 1)}
    def_rank = {t: i for i, t in enumerate(sorted(teams, key=lambda t: def_score[t]), 1)}
    off_exp = {t: i for i, t in enumerate(sorted(teams, key=lambda t: -t.offense_ovr), 1)}
    def_exp = {t: i for i, t in enumerate(sorted(teams, key=lambda t: -t.defense_ovr), 1)}
    for t in teams:
        L = lines[t]
        for k, r in ranks.items():
            L[k + "_rank"] = r[t]
        L["off_rank"], L["def_rank"] = off_rank[t], def_rank[t]
        L["off_exp"], L["def_exp"] = off_exp[t], def_exp[t]
        L["n"] = len(teams)
    return lines


def season_entry(league, team, role, L):
    if role == "OC":
        return {"year": league.year, "school": team.school, "conf": team.conference, "role": "OC", "g": L["g"],
                "ppg": round(L["ppg"], 1), "pass": round(L["pass"], 1), "rush": round(L["rush"], 1),
                "ypg": round(L["ypg"], 1), "ppg_rank": L["ppg_rank"], "ypg_rank": L["ypg_rank"],
                "pass_rank": L["pass_rank"], "rush_rank": L["rush_rank"],
                "rank": L["off_rank"], "exp": L["off_exp"], "n": L["n"], "hc": team.coach.name if team.coach else ""}
    return {"year": league.year, "school": team.school, "conf": team.conference, "role": "DC", "g": L["g"],
            "ppg": round(L["papg"], 1), "pass": round(L["pass_a"], 1), "rush": round(L["rush_a"], 1),
            "ypg": round(L["ypg_a"], 1), "ppg_rank": L["papg_rank"], "ypg_rank": L["ypg_a_rank"],
            "pass_rank": L["pass_a_rank"], "rush_rank": L["rush_a_rank"],
            "rank": L["def_rank"], "exp": L["def_exp"], "n": L["n"], "hc": team.coach.name if team.coach else ""}


def resume_prior(coach):
    """The name a coordinator brings from before: no league needed."""
    import resume
    return resume.prior(coach)


def resume_score(coach, seasons=3):
    """What a coordinator's recent units say about him, roughly -10 to +16.
    Ranking well counts; beating what the roster's talent said counts more."""
    book = getattr(coach, "coord_history", [])[-seasons:]
    if not book:
        return 0.0
    tot = 0.0
    for s in book:
        n = s.get("n", 130)
        tot += (0.5 - s["rank"] / n) * 20                  # top of the country: +10, bottom: -10
        tot += (s["exp"] - s["rank"]) / n * 12              # did more than the talent: up to +/-12
        if s["rank"] <= s["exp"] and s["rank"] <= 10:
            tot += 1.5                                      # a top-10 unit that beat its talent
    avg = tot / len(book)
    return avg * len(book) / (len(book) + 1) + 1.5 * min(3, len(book))    # experience counts a little


# Head coaches whose staffs are famous for producing head coaches.
KNOWN_MENTORS = {}    # coach name -> the head coach he came up under (a universe file can fill it in)


def mentor(coach):
    """0-100: how much his coordinators grow under him. A few head coaches build whole
    coaching trees; some stunt the people around them."""
    if coach is None:
        return 55
    m = getattr(coach, "mentor", None)
    if m is None:
        import random as _r
        r = _r.Random(f"mentor:{coach.name}")
        m = KNOWN_MENTORS.get(coach.name) or int(max(20, min(96, r.gauss(56, 15))))
        coach.mentor = m
    return m


def mentor_word(m):
    return "builds coaching trees" if m >= 85 else "develops his staff" if m >= 68 else \
        "average" if m >= 45 else "stunts his assistants"


def record_seasons(league, rng):
    """End of season: every coordinator's unit goes in his book, and he grows."""
    from carousel import progress
    lines = unit_lines(league)
    for team in league.teams:
        L = lines.get(team)
        if L is None:
            continue
        for role in ("OC", "DC"):
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            if c is None:
                continue
            s = season_entry(league, team, role, L)
            c.coord_history.append(s)
            n = s["n"]
            bonus = (s["exp"] - s["rank"]) / n * 4 + (0.8 if s["rank"] <= 10 else 0.3 if s["rank"] <= 25 else 0)
            if len(c.coord_history) <= 3:
                bonus += 0.6                                  # young coordinators learn fast
            m = mentor(team.coach)
            bonus += (m - 55) / 40 * 0.9                      # the head coach he works for: a tree or a dead end
            if m >= 80:
                c.__dict__.setdefault("mentors", [])
                if team.coach.name not in c.mentors:
                    c.mentors.append(team.coach.name)
            s["growth"] = progress(c, bonus, rng)
    for c in coordinators(league) + getattr(league, "staff_pool", []):
        c.age += 1


# ═══ The staff carousel ═════════════════════════════════════════════════════

def _staff_move(league, side, team, role, c, **kw):
    moves = league.__dict__.setdefault("staff_moves", {}).setdefault(league.year, [])
    book = getattr(c, "coord_history", [])
    last = book[-1] if book else None
    moves.append(dict(side=side, school=team.school, conf=team.conference, prestige=team.prestige, role=role,
                      coach=c.name, age=c.age, overall=c.overall, last=last, **kw))


def staff_moves(league, year):
    return getattr(league, "staff_moves", {}).get(year, [])


def _new_hc_this_winter(league, team):
    return team.coach is not None and team.coach.hired_year == league.year + 1


def leave_for_head_job(league, team, coach, dest):
    """A coordinator hired as somebody's head coach."""
    if team is not None and team.coach is not None and mentor(team.coach) >= 80:
        coach.tree = team.coach.name                         # another branch on the tree
    role = role_of(coach)
    _detach(league, team, role, "promoted", dest=dest.school)


def user_team(league):
    """Your team in Coach Career mode, if you're running your own staff."""
    if getattr(league, "mode", None) != "career" or getattr(league, "staff_autopilot", False) \
            or getattr(league, "autosim", False):
        return None
    coach = getattr(league, "user_coach", None)
    if coach is None or coach.status == "retired":
        return None
    return coach.team


def offseason(league, rng):
    """After the head coaching carousel: clean-outs, firings, retirements, then
    every coordinator opening filled."""
    league.__dict__.setdefault("staff_pool", [])
    moves = league.__dict__.setdefault("staff_moves", {})
    moves[league.year] = [m for m in moves.get(league.year, []) if m.get("why") == "promoted"]
    me = user_team(league)
    import hotseat
    mes = hotseat.humans(league) if hotseat.state(league) is not None else ([me] if me is not None else [])

    for team in league.teams:
        for role in ("OC", "DC"):
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            if c is None:
                continue
            # Retirement.
            if c.age >= 62 and rng.random() < 0.12 + (c.age - 62) * 0.05:
                c.status = "retired"
                _detach(league, team, role, "retired")
                continue
            if any(team is m for m in mes):
                continue                               # human staffs make these calls themselves
            if getattr(league, "mode", None) == "commissioner" and __import__("commissioner").is_player_team(league, team):
                continue                               # a member lets his own coaches go (his orders)
            # A new head coach cleans house (sometimes he keeps a good one).
            if _new_hc_this_winter(league, team):
                keep = STAY_ODDS
                last = c.coord_history[-1] if c.coord_history else None
                if last and last["rank"] <= 25:
                    keep += 0.2
                if c.name in getattr(team.coach, "staff_ties", set()):
                    keep += 0.4
                if rng.random() > keep:
                    _detach(league, team, role, "cleaned out")
                continue
            # Firing: the unit flopped against its talent, or the head coach needs a scapegoat.
            if team is me:
                continue                               # your staff is yours to manage
            tenure = league.year - getattr(c, "coord_since", league.year) + 1
            book = [s for s in c.coord_history if s["school"] == team.school][-2:]
            if tenure < 2 or not book:
                continue
            n = book[-1]["n"]
            under = [(s["rank"] - s["exp"]) / n for s in book]
            seat = team.coach.seat if team.coach else 30
            odds = 0.0
            if under[-1] >= 0.35:
                odds = 0.55
            elif len(under) == 2 and all(u >= 0.18 for u in under):
                odds = 0.45
            elif book[-1]["rank"] >= n * 0.8:
                odds = 0.25
            if seat >= 60 and book[-1]["rank"] >= n * 0.5:
                odds += 0.25                           # a coach on the hot seat makes a change
            if rng.random() < odds:
                _detach(league, team, role, "fired")
    if getattr(league, "mode", None) == "commissioner":
        import member_offseason
        member_offseason.run_fires(league)             # members' let-go orders open their chairs now
    import poscoach
    poscoach.room_reports(league)                      # how each room grew this year, before anyone moves
    poscoach.offseason(league, rng)                    # position coaches grow, age, retire, move
    if mes:
        import offseason_cal
        for t in mes:
            with hotseat.acting_as(league, t):
                hotseat.maybe_pass(league, "YOUR COACHING STAFF")
                offseason_cal.january(league, t)       # each human gets the January staff phase
    import offseason_cal
    offseason_cal.staff_carousel(league, rng)          # the carousel: interviews, poaching, dominoes
    fill_openings(league, rng)                         # safety net: nothing is left open
    poscoach.fill_cpu(league, rng)
    if me is not None:
        poscoach.fill_yours(league, me)
    refresh_pool(league, rng)


def _willing(c, team, league, tie, offer=None):
    """Will this coordinator take this job (and, if there's an offer on the table, this money)?"""
    from carousel import PERSONALITIES
    import finance
    # Market realism: interest is not binary prestige alone. Elite assistants expect elite jobs,
    # and anybody hired this same offseason is protected from an immediate re-poach.
    try:
        import hiring_market
        if hiring_market.coord_interest(league, team, c, getattr(c, "role", None) or _best_side(c), tie, offer) < 12:
            return False
    except Exception:
        pass
    ratio = finance.money_ratio(league, c, offer, offer["role"], team) if offer is not None else 1.0
    if c.personality == "homebody" and not tie:
        from carousel import home_region, region_of
        reg = home_region(c)
        if reg and region_of(team) and region_of(team) != reg:
            return False                               # won't leave his part of the country
    if c.status == "unemployed" or c.team is None:
        return ratio >= 0.6
    cur = c.team
    if ratio < 0.85:
        return False
    if getattr(c, "moved_year", None) == league.year:
        return False                                   # he just took a job this winter
    tenure = league.year - getattr(c, "coord_since", league.year) + 1
    if tenure < 2 and not tie:
        return False
    jump = team.prestige - cur.prestige
    traits = PERSONALITIES.get(c.personality, PERSONALITIES["builder"])[2]
    need = traits["min_jump"] * 0.6
    if tie:
        need -= 12                                     # he'd follow his guy almost anywhere
    if cur.conference not in _power() and team.conference in _power():
        need -= 6                                      # the jump to the Power leagues
    if getattr(cur, "oc", None) is None and getattr(cur, "dc", None) is None:
        need -= 4
    need -= max(-0.3, min(0.8, ratio - 1)) * 10 * finance.money_weight(c)   # money shrinks the step up
    import skills
    if skills.team_has(team, "coaching_tree"):
        need -= 8                                      # Coaching Tree: people want to work for you
    if skills.team_has(cur, "coaching_tree"):
        need += 6                                      # ...and they're slow to leave
    lean = getattr(c, "stay_lean", None)               # what his head coach told him (Career inbox)
    if lean and league.year - lean[0] <= 1:
        need += 10 if lean[1] < 0 else -6
    return jump >= need


def _power():
    from season import BIG_CONFERENCES
    return set(BIG_CONFERENCES) | {"Independent"}


def _score(team, c, role, league):
    import resume  # what he's done, not what his ratings say
    s = resume.reputation(c, league) * 0.9 + resume_score(c) * 1.2 + (resume.recruit_rep(c) - 60) * 0.1
    if team.coach is not None:
        if c.name in getattr(team.coach, "staff_ties", set()):
            s += 9                                     # the head coach's own people
        scheme = team.coach.offense_scheme if role == "OC" else team.coach.defense_scheme
        if (c.offense_scheme if role == "OC" else c.defense_scheme) == scheme:
            s += 3
    if role_of(c) == "HC":                              # a fired head coach
        s += 3
    return s


def _generated(league, team, role, rng):
    """Fresh faces for an opening: high school and FCS coaches for Group of Five
    jobs; for Power jobs only a promoted position coach or a Pro League assistant."""
    from season import BIG_CONFERENCES
    power = team.conference in BIG_CONFERENCES or team.school == world.FLAGSHIP_INDEPENDENT
    # New faces come in below the program's proven coordinators: they haven't done it yet.
    level = team.ratings["coach"] - (9 if power else 10)
    out = []
    # High school coaches are a real pipeline — into Group of Five coordinator jobs only.
    kinds = ("position", "nfl") if power else ("hs", "hs", "hs", "fcs", "position")
    for kind in kinds:
        if kind == "hs":
            state = team.home_state if getattr(team, "home_state", None) and rng.random() < 0.6 \
                else rng.choice(list(STATES))
            origin = f"head coach at {rng.choice(LAST_NAMES)} {rng.choice(('Central', 'North', 'South', 'Memorial', 'Christian', 'Prep'))} High School ({state})"
            c = make_coordinator(league, role, rng, level=level + 1, origin=origin, age=rng.randint(33, 50))
            c.recruit_region = STATES[state][1]
            c.ceiling = max(c.ceiling, min(c.ceiling + 4, 88))  # the ones who make the jump have upside
        elif kind == "fcs":
            src = rng.choice(league.fcs_teams) if league.fcs_teams else None
            origin = f"{src.school} {ROLE_NAMES[role]} (FCS)" if src else f"FCS {ROLE_NAMES[role]}"
            c = make_coordinator(league, role, rng, level=level - 2, origin=origin)
        elif kind == "nfl":
            c = make_coordinator(league, role, rng, level=level,
                                 origin=f"Pro League {'quarterbacks' if role == 'OC' else 'defensive backs'} coach",
                                 age=rng.randint(36, 55))
        else:
            group = rng.choice(("quarterbacks", "offensive line", "wide receivers") if role == "OC"
                               else ("linebackers", "defensive line", "safeties"))
            origin = f"{team.school} {group} coach, promoted"
            c = make_coordinator(league, role, rng, level=level - 3, origin=origin,
                                 age=rng.randint(31, 48))
        c._generated = True
        out.append(c)
    return out


def fill_openings(league, rng):
    """Biggest programs first; a coordinator hired away opens a job below."""
    from season import BIG_CONFERENCES
    for _ in range(800):
        openings = [(t, r) for t in league.teams for r in ("OC", "DC")
                    if getattr(t, "oc" if r == "OC" else "dc", None) is None]
        if not openings:
            return
        team, role = max(openings, key=lambda x: x[0].prestige)
        power = team.conference in BIG_CONFERENCES or team.school == world.FLAGSHIP_INDEPENDENT
        ranked = candidates_for(league, team, role, rng)
        hired, offer = None, None
        import finance
        import hotseat
        picked = None
        with hotseat.acting_as(league, team):
            if team is user_team(league):
                hotseat.maybe_pass(league, "HIRE A COORDINATOR")
                import staff_screens
                picked = staff_screens.pick(league, team, role, ranked)   # the search judges interest itself
        if picked is not None:
            hired, offer = picked
        if hired is None:
            for c, tie in ranked[:14]:
                o = finance.coord_offer(league, team, c, role, rng)
                if _willing(c, team, league, tie, o):
                    hired, offer = c, o
                    break
        if hired is None:
            hired = next(c for c, _ in ranked if getattr(c, "_generated", False))
        _hire(league, team, role, hired, power, offer)


def candidates_for(league, team, role, rng):
    """Everyone who could fill this job, best first, as (coach, worked-with-the-HC)."""
    pool = league.staff_pool
    hc_ties = getattr(team.coach, "staff_ties", set()) if team.coach else set()
    cands = []
    for t in league.teams:
        for r in ("OC", "DC"):
            c = getattr(t, "oc" if r == "OC" else "dc", None)
            if c is None or t is team or getattr(c, "moved_year", None) == league.year:
                continue
            # "His guys": coordinators who worked under this head coach, and aren't
            # working under him somewhere else right now.
            tie = c.name in hc_ties and (t.coach is None or team.coach is None or t.coach.name != team.coach.name)
            if r != role:
                continue                               # coordinators stay on their side of the ball
            if t.prestige >= team.prestige and not tie:
                continue
            cands.append((c, tie))
    for c in pool:
        if getattr(c, "let_go", None) == (team.school, league.year) or getattr(c, "commish_member", None):
            continue
        if c.status == "unemployed" and (role_of(c) == role or (role_of(c) == "HC" and _best_side(c) == role)):
            cands.append((c, c.name in hc_ties))
    if team.prestige >= 58:
        for c in league.coach_pool:                    # fired head coaches take coordinator jobs at good programs
            if c.status == "unemployed" and c.history and not getattr(c, "is_user", False) \
                    and not getattr(c, "commish_member", None) \
                    and c.age < 64 and _best_side(c) == role:
                cands.append((c, c.name in hc_ties))
    for c in _generated(league, team, role, rng):
        cands.append((c, False))
    return sorted(cands, key=lambda x: -(_score(team, x[0], role, league) + rng.gauss(0, 2)))


def fire(league, team, role, why="fired"):
    """You let a coordinator go."""
    return _detach(league, team, role, why)


def potential_word(c):
    room = c.ceiling - c.overall
    return "Maxed out" if room <= 1 else "Some room" if room <= 5 else "High" if room <= 12 else "Very high"


def _best_side(c):
    off = sum(c.ratings[k] for k in SIDE_KEYS["OC"]) / 3
    dfn = sum(c.ratings[k] for k in SIDE_KEYS["DC"]) / 2
    return "OC" if off >= dfn else "DC"


def _hire(league, team, role, c, power, offer=None):
    if c.team is not None and role_of(c) in ("OC", "DC"):
        old = c.team
        old_role = role_of(c)
        how = "hired away"
        source = f"{old.school} {ROLE_NAMES[old_role]}"
        _detach(league, old, old_role, "left", dest=team.school)
    elif getattr(c, "_generated", False):
        how, source = "hired", c.origin
        c.__dict__.pop("_generated", None)
    elif role_of(c) == "HC":
        last = c.history[-1] if c.history else None
        how, source = "hired", (f"former {last['school']} head coach" if last else "former head coach")
        c.coord_history = getattr(c, "coord_history", [])
        c.staff_ties = getattr(c, "staff_ties", set())
    else:
        last = c.coord_history[-1] if getattr(c, "coord_history", None) else None
        how, source = "hired", (f"out of work — last at {last['school']}" if last else c.origin)
    c.origin = f"{team.school} {ROLE_NAMES[role]}"
    c.moved_year = league.year
    _attach(league, team, c, role, how, source)
    import finance
    finance.sign(league, team, c, offer or finance.coord_offer(league, team, c, role), start=league.year + 1)
    if offer and any(k in offer for k in ("play_calling", "ahc", "hc_out")):
        import coord_search
        coord_search.after_hire(league, team, role, c, offer)     # the package you negotiated


def refresh_pool(league, rng):
    keep = []
    for c in league.staff_pool:
        c.pool_years = getattr(c, "pool_years", 0) + 1
        if c.status == "retired" or c.pool_years >= 3 or (c.age >= 60 and rng.random() < 0.4):
            continue
        keep.append(c)
    league.staff_pool = keep


# ═══ For the head coaching carousel ═════════════════════════════════════════

def head_coach_candidates(league, team):
    """Sitting coordinators an AD would call about a head coaching job."""
    out = []
    for t in league.teams:
        for c in (getattr(t, "oc", None), getattr(t, "dc", None)):
            if c is None or len(getattr(c, "coord_history", [])) < 1:
                continue
            if c.age > 62:
                continue
            out.append(c)
    return out


def hc_bonus(team, coach, league):
    """A coordinator's case for a head coaching job: his units, and the
    stage he did it on."""
    if role_of(coach) not in ("OC", "DC"):
        return 0.0
    score = resume_score(coach)
    bonus = score * 1.4
    cur = coach.team
    if cur is not None and score > 0:
        bonus += max(0, cur.prestige - team.prestige) * 0.08   # a good unit on a big stage is a credential
    if score < 3:
        bonus -= 8                                           # nobody hires a coordinator whose unit flopped
    if cur is not None and cur.coach is not None:
        bonus += (mentor(cur.coach) - 55) * 0.12             # he comes from a coaching tree
    # Coordinators usually get their first head job at a smaller program and prove it
    # there. A Power job takes a chance only on an excellent one from an excellent program.
    big_job = team.prestige >= 66 or team.conference in _power()
    if big_job:
        elite = score >= 7 and cur is not None and cur.prestige >= 80
        own = cur is team and score >= 4                     # promoting your own coordinator is its own thing
        if not (elite or own):
            bonus -= 24 + max(0, team.prestige - 66) * 0.5
    return bonus - 9                                        # he's never run a program


def will_take_head_job(coach, team, league, rng):
    cur = coach.team
    if cur is None:
        return True
    if resume_score(coach) < 3:
        return False                                     # he isn't getting the interview
    odds = 0.85 if (team.prestige >= cur.prestige - 30 or team.conference in _power()) else 0.25
    lean = getattr(coach, "stay_lean", None)             # what you told him (Career inbox)
    if lean and league is not None and league.year - lean[0] <= 1:
        odds = odds * 0.45 if lean[1] < 0 else min(0.97, odds * 1.15)
    if coach.__dict__.get("hc_out_clause"):
        odds = min(0.97, odds * 1.15)                    # you wrote him a way out for exactly this
    return rng.random() < odds


# ═══ A world with a past ════════════════════════════════════════════════════
# A new world starts in 2026, but its coordinators didn't. Each gets the career
# that got him here — the stops before this one — and the units he ran here
# before this season, graded from the rosters he had. Nothing is a real result;
# it's the reputation a coordinator walks in with.

POSITION_GROUPS = {"OC": ("quarterbacks", "wide receivers", "offensive line", "running backs", "tight ends"),
                   "DC": ("linebackers", "safeties", "defensive line", "cornerbacks", "defensive backs")}


def _unit_from_rank(role, rank, n, r):
    """Believable per-game numbers for a unit that finished `rank` of `n`."""
    x = (rank - 1) / max(1, n - 1)                     # 0 = best in the country, 1 = worst
    if role == "OC":
        ppg = 41 - 25 * x + r.gauss(0, 1.5)
        ypg = 490 - 180 * x + r.gauss(0, 12)
    else:
        ppg = 13 + 22 * x + r.gauss(0, 1.5)
        ypg = 285 + 165 * x + r.gauss(0, 12)
    pass_share = min(0.72, max(0.42, r.gauss(0.57, 0.06)))
    return round(ppg, 1), round(ypg, 1), round(ypg * pass_share, 1), round(ypg * (1 - pass_share), 1)


# The youngest a man holds each job: a position coach out of the GA ranks, a coordinator after that.
MIN_AGE = {"position": 25, "coord": 30}


def _past_ranks(league, teams, order, role, year):
    """One national order per side per past season, so no two units share a rank:
    the roster's rank that year (rosters turn over, so it drifts the further back
    you go), nudged by how good the man now running it is, plus luck. Every unit
    also gets its season's numbers, and the stat ranks come from ranking those
    numbers against everybody else's — so #1 passing and #1 rushing is #1 in yards."""
    r = random.Random(f"pastrank:{league.seed}:{role}:{year}")
    n = len(teams)
    back = max(1, league.year - year)
    drift = n * 0.035 * back
    talent = sorted(teams, key=lambda t: order.index(t) + r.gauss(0, drift))
    exp = {t: i + 1 for i, t in enumerate(talent)}
    def score(t):
        c = getattr(t, "oc" if role == "OC" else "dc", None)
        skill = (c.overall - 70) * 0.9 if c is not None else 0
        return exp[t] - skill + r.gauss(0, n * 0.12)
    ranked = sorted(teams, key=score)
    out = {}
    stats = {}
    for i, t in enumerate(ranked):
        stats[t] = _unit_from_rank(role, i + 1, n, r)
    best_high = role == "OC"                              # a defense ranks by what it allowed
    def rank_by(idx):
        srt = sorted(teams, key=lambda t: -stats[t][idx] if best_high else stats[t][idx])
        return {t: j + 1 for j, t in enumerate(srt)}
    ppg_r, ypg_r, pass_r, rush_r = (rank_by(k) for k in range(4))
    for i, t in enumerate(ranked):
        ppg, ypg, pas, rush = stats[t]
        out[t] = (i + 1, exp[t], {"ppg": ppg, "ypg": ypg, "pass": pas, "rush": rush, "ppg_rank": ppg_r[t],
                                  "ypg_rank": ypg_r[t], "pass_rank": pass_r[t], "rush_rank": rush_r[t]})
    return out


def _entry(league, team, role, year, rank, exp, n, r, school=None, conf=None, hc="", line=None):
    if line is None:
        ppg, ypg, pas, rush = _unit_from_rank(role, rank, n, r)
        line = {"ppg": ppg, "ypg": ypg, "pass": pas, "rush": rush, "ppg_rank": rank, "ypg_rank": rank,
                "pass_rank": rank, "rush_rank": rank}
    return {"year": year, "school": school or team.school, "conf": conf or team.conference, "role": role,
            "g": 12, **line, "rank": rank, "exp": exp, "n": n, "hc": hc, "seeded": True}


def seed_past(league):
    """New worlds only: coordinators arrive with careers and last season's units."""
    from carousel import region_of, settle_homebody
    from recruiting_data import STATES as _ST
    teams = list(league.teams)
    off_order = sorted(teams, key=lambda t: -t.offense_ovr)
    def_order = sorted(teams, key=lambda t: -t.defense_ovr)
    n = len(teams)
    first = league.year - 12
    ranks = {(role, y): _past_ranks(league, teams, off_order if role == "OC" else def_order, role, y)
             for role in ("OC", "DC") for y in range(first, league.year)}
    since_of = {(t, role): getattr(getattr(t, "oc" if role == "OC" else "dc", None), "coord_since", league.year)
                for t in teams for role in ("OC", "DC")}
    claimed = set()                                    # (school, role, year) someone else already ran
    for team in teams:
        for role in ("OC", "DC"):
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            if c is None or getattr(c, "stops", None):
                continue
            r = random.Random(f"past:{league.seed}:{team.school}:{role}")
            settle_homebody(c, r)
            order = off_order if role == "OC" else def_order
            since = getattr(c, "coord_since", league.year)
            # Seasons here before this one.
            for yr in range(max(first, since), league.year):
                rank, exp, line = ranks[(role, yr)][team]
                c.coord_history.append(_entry(league, team, role, yr, rank, exp, n, r,
                                              hc=team.coach.name if team.coach else "", line=line))
            # The stops before he got here, most recent first. Homebodies never left home.
            home = getattr(c, "home_region", None)
            near = [t for t in teams if t is not team and (not home or region_of(t) == home)] or \
                [t for t in teams if t is not team]
            # Better coordinators came from bigger places.
            near.sort(key=lambda t: abs(t.prestige - (team.prestige - 8 + (c.overall - 70) * 0.4)))
            pool = near[:18]
            stops, year = [], since
            for i in range(r.choice((1, 2, 2, 3))):
                if not pool:
                    break
                prev = pool.pop(r.randrange(len(pool)))
                length = r.choice((1, 2, 2, 3, 3, 4))
                start = year - length
                age_then = c.age - (league.year - start)
                if age_then < MIN_AGE["position"]:
                    break                                      # he was still a GA (or a player) back then
                # Coordinated somewhere else first — if that school's man wasn't already in the chair.
                if i == 0 and age_then >= MIN_AGE["coord"] and r.random() < 0.6 and since_of[(prev, role)] >= year \
                        and start >= first and not any((prev, role, y) in claimed for y in range(start, year)):
                    job = role
                    claimed.update((prev, role, y) for y in range(start, year))
                else:
                    job = r.choice(POSITION_GROUPS[role]) + " coach"
                stops.append({"school": prev.school, "job": job, "start": start, "end": year - 1})
                if job in ("OC", "DC"):
                    for yr in range(start, year):
                        rank, exp, line = ranks[(role, yr)][prev]
                        c.coord_history.insert(0, _entry(league, prev, role, yr, rank, exp, n, r, line=line))
                year = start
            c.coord_history.sort(key=lambda e: e["year"])
            c.stops = stops
            if stops:
                s0 = stops[0]
                c.origin = f"{s0['school']} " + (ROLE_NAMES[s0["job"]] if s0["job"] in ROLE_NAMES else s0["job"])
            else:
                c.origin = f"promoted from {team.school}'s staff"


def stop_text(stop):
    job = stop["job"] if stop["job"] not in ("OC", "DC") else stop["job"]
    yrs = f"{stop['start']}" if stop["start"] == stop["end"] else f"{stop['start']}–{str(stop['end'])[-2:]}"
    return f"{stop['school']} {job} ({yrs})"


def background_text(coach):
    """Where he's been — never just the job he has now."""
    stops = getattr(coach, "stops", None)
    if stops:
        return " · ".join(stop_text(s) for s in stops)
    origin = getattr(coach, "origin", "") or "—"
    if origin == "FBS head coach":
        return "—"                                    # a real coach whose past isn't on file
    team = getattr(coach, "team", None)
    role = role_of(coach)
    if team is not None and role in ROLE_NAMES and origin == f"{team.school} {ROLE_NAMES[role]}":
        return "came up through the program's own staff"
    return origin


def buzz_score(coach):
    """Head-coach buzz: his recent units, plus the name he's made for himself —
    an elite coordinator at an elite program gets calls before he's proven anything."""
    score = resume_score(coach)
    import resume
    rep = max(0.0, resume.prior(coach) - 76) * 0.25          # the name he's made — results still count more
    team = getattr(coach, "team", None)
    if team is not None:
        rep += max(0.0, team.prestige - 80) * 0.05
    if coach.age <= 35 and score >= 6:
        rep += 1.5                                          # young and already producing: the next big thing
    return score + rep
