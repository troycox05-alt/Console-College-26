"""
recruit_plus.py — Recruiting, deeper: the systems around the weekly grind.

STANDING ORDERS (your queue)
  Any action on any recruit can be a standing order: once, every week, every
  other week, for N weeks, or every week until he commits. Orders sit in ONE
  queue, in the order you choose — the same recruit can be in it three times
  ("call Johnny, call Steven, call Johnny again"). At the end of every week the
  queue spends whatever hours you haven't, top to bottom; an order that doesn't
  fit is cut (a cheaper one further down can still run). The queue screen shows
  which orders will run and which will be cut before the week ends.
  Your coordinators can also run part of the board on autopilot (their side of
  the ball) with an hour cap you set. They go after your queue.

OFFICIAL VISITS
  Five per recruit, one per school, hosted at one of your home games. The
  Saturday decides it: the result, the opponent, the crowd, the noise, the
  stadium (lounge, locker room), a night game — and what he cares about. A
  packed night win over a ranked team sells him. A blowout loss in a half-empty
  building ends it. Every visit writes a report.

PITCHES
  A call, a position-coach visit or an in-home visit is a conversation: you
  choose what to sell. Hit what he cares about and it lands (and now you know);
  miss and he checks his phone. Standing orders use the best thing you know.

THE LIVING TRAIL
  Every recruit plays a senior season (weekly stats on his card). Ratings update
  in Weeks 5, 9 and 13 — risers and fallers. Summer camps in the preseason:
  bring kids to campus to see them in person. Hidden gems pop at camps.

THE DRAMA
  Crystal-ball predictions and "trending" news. Commitments are hard, soft, or
  silent (a silent commit to someone else still looks open to you). The early
  signing period (NP First Round week) locks hard commits in; soft ones wait,
  and on National Signing Day some of them flip. Signing Day is live: hats on
  the table, one at a time.

RIVALS FIGHT BACK
  Rival staffs use your hot seat, your record and your crowded position rooms
  against you. In the last weeks, collectives get into NIL bidding wars over
  four- and five-stars. A kid asks why you already have three quarterbacks.

PIPELINES
  Every recruit has a high school. Sign kids from a school and it becomes a
  pipeline (easier sells, free intel). Break a promise to one of its kids or cut
  him at signing day and that school goes cold. Pipelines fade slowly.

MORE PLAYERS
  JUCO transfers (older, ready now, less upside — they arrive as juniors),
  international kickers and punters, and preferred walk-ons you invite (no
  scholarship; the good ones earn one).

THE WAR ROOM
  Your own ordered big board with tiers, class needs, a class goal, and a
  hit-or-bust report on every class you've signed.
"""
import random
from collections import Counter, defaultdict
from netplay import capture

from recruiting_data import (ACTIONS, PERSONALITIES, PRIORITIES, PRIORITY_LABELS, STATES, TALENT,
                             TEAM_STATES)

OV_MAX = 5
OV_COST = 4
QUEUE_RULES = {"once": "once", "weekly": "every week", "biweekly": "every other week",
               "until": "every week until he commits", "weeks": "every week for {n} weeks"}
PITCH_ACTIONS = ("contact", "position_coach", "in_home")
EARLY_SIGNING_WEEK = 15
RATING_WEEKS = (5, 9, 13)
PWO_MAX = 6
CAMP_MAX = 12
OFF_POS = ("QB", "RB", "WR", "TE", "OL", "K", "P")
DEF_POS = ("DL", "LB", "CB", "S")
TRUTH_STARS = ((62, 5), (50, 4), (40, 3), (30, 2), (0, 1))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def S(cycle):
    """Everything this module keeps on the recruiting cycle (one class, one year)."""
    d = cycle.__dict__.get("plus")
    if d is None:
        d = cycle.__dict__["plus"] = {
            "queue": defaultdict(list), "auto": {}, "summary": {}, "ov_index": defaultdict(list),
            "visits": defaultdict(list), "log": defaultdict(list), "cb": {}, "camp": {}, "pwo": defaultdict(list),
            "enriched": False, "standouts": False, "rated": set(), "early_done": False, "bids": {},
            "neg": defaultdict(list), "silent": {}, "weekly_note": defaultdict(list),
        }
    return d


def g(r, attr, default=None):
    try:
        return getattr(r, attr)
    except AttributeError:
        return default


def say(cycle, team, r, text):
    """A line in this recruit's story, as your staff hears it."""
    S(cycle)["log"][(team, r)].append((cycle.league.week, text))


def log_of(cycle, team, r):
    return S(cycle)["log"].get((team, r), [])


def log_move(cycle, team, r, action, hours, result, source="you"):
    """Record one of your recruiting moves that doesn't go through apply_action (official visit invites,
    walk-on invites, summer camp) in league.recruit_actions — the list Export to Sheets reads."""
    try:
        lg = cycle.league
        if team is not getattr(lg, "user_team", None):
            return
        lg.__dict__.setdefault("recruit_actions", []).append(
            {"year": lg.year, "week": lg.week, "recruit": r.player.name, "pos": r.position, "stars": r.stars,
             "rank": r.national_rank, "action": action, "hours": hours, "pitch": "", "source": source,
             "result": result, "interest": round(r.interest.get(team, 0.0), 1),
             "relationship": round(cycle.relationship[(team, r)], 1)})
        del lg.recruit_actions[:-20000]
    except Exception:
        pass


def action_cost(team, action):
    cost = ACTIONS[action][1]
    if action == "evaluate":
        import skills
        if skills.team_has(team, "film_junkie"):
            cost = 1
    if action == "ov":
        cost = OV_COST
    return cost


# ═══ High schools and pipelines ═════════════════════════════════════════════

HS_WORDS = ("Central", "North", "South", "East", "West", "Lincoln", "Jefferson", "Washington", "Roosevelt",
            "Oak Ridge", "Heritage", "Westlake", "Riverside", "Mountain View", "Lakeview", "Summit", "Valley",
            "Bishop Gorman", "St. Thomas", "Cathedral", "Prep Academy", "Christian", "Memorial", "Northside",
            "Southside", "Eastside", "Highland", "Pine Forest", "Cedar Grove", "Red Bank", "Mater Dei", "St. John's",
            "Lake Travis", "Parkview", "Grayson", "Carver", "Booker T. Washington", "Plantation", "Madison",
            "Kennedy", "Hoover", "Liberty", "Independence", "Brookwood", "Allen", "Katy", "Duncanville", "Colquitt")


def schools_in(state):
    n = int(clamp(6 + TALENT.get(state, 0.2) * 7, 6, 28))
    rng = random.Random(f"hs:{state}")
    names = rng.sample(HS_WORDS, min(n, len(HS_WORDS)))
    return [w if any(x in w for x in ("Academy", "Prep", "Christian", "Mater Dei", "Cathedral", "St.", "Bishop"))
            else f"{w} High" for w in names]


def hs_key(r_or_state, hs=None):
    if hs is None:
        return f"{g(r_or_state, 'hs', '')}|{r_or_state.home_state}"
    return f"{hs}|{r_or_state}"


def pipelines(team):
    return team.__dict__.setdefault("pipelines", {})


def pipeline_of(team, r):
    return pipelines(team).get(hs_key(r), 0.0)


PIPE_WORDS = ((70, "a pipeline"), (45, "strong ties"), (20, "some ties"), (0, "no ties"))


def pipe_word(v):
    return next(w for lo, w in PIPE_WORDS if v >= lo)


def pipeline_hit(team, key, delta, why=""):
    p = pipelines(team)
    p[key] = clamp(p.get(key, 0.0) + delta, 0, 100)
    if p[key] <= 0.5:
        p.pop(key, None)


# ═══ Class chemistry and momentum ════════════════════════════════════════════

def class_momentum(cycle, team):
    """0..100: how much the current class itself has become a recruiting story.

    Quality matters more than raw headcount and returns diminish quickly, so elite
    classes get a useful pull without turning every late battle into an automatic win.
    """
    commits = cycle._class_of(team)
    if not commits:
        return 0.0
    quality = sum(max(0, r.stars - 2) * 5.0 for r in commits)
    headliners = sum(1 for r in commits if r.stars >= 4) * 4.0
    depth = min(30.0, len(commits) * 2.2)
    return clamp(quality + headliners + depth, 0, 100)


def momentum_word(v):
    if v >= 78: return "national buzz"
    if v >= 58: return "surging"
    if v >= 38: return "building"
    if v >= 18: return "taking shape"
    return "quiet"


def recruit_connection(a, b):
    """(strength, label) for two prospects. Strong ties are rare and deterministic."""
    if a is b:
        return 0.0, ""
    if g(a, "kind", "hs") == "hs" and g(b, "kind", "hs") == "hs" and a.home_state == b.home_state and g(a, "hs") == g(b, "hs"):
        return 1.0, f"high school teammate at {g(a, 'hs', 'their school')}"
    # A stable pseudo-social graph: some same-state kids know each other from camps/7-on-7.
    import hashlib
    key = "|".join(sorted((a.player.name, b.player.name))) + f"|{a.home_state}|{b.home_state}"
    roll = int(hashlib.sha1(key.encode()).hexdigest()[:8], 16) % 100
    if a.home_state == b.home_state:
        if roll < 24:
            return 0.62, "knows him from the in-state circuit"
        return 0.34, "same-state connection"
    if a.region == b.region:
        if roll < 10:
            return 0.42, "regional camp connection"
        return 0.16, "same-region familiarity"
    return 0.0, ""


def class_connections(cycle, team, r, limit=3):
    out = []
    for c in cycle._class_of(team):
        strength, label = recruit_connection(r, c)
        if strength:
            out.append((strength, c, label))
    return sorted(out, key=lambda x: (-x[0], x[1].national_rank or 9999))[:limit]


def class_pull(cycle, team, r):
    """Small interest multiplier from visible class momentum + people the recruit knows."""
    mom = class_momentum(cycle, team)
    social = sum(x[0] for x in class_connections(cycle, team, r, 3))
    # Max roughly +16%; most classes sit in the +2–8% range.
    return 1.0 + min(0.10, mom / 1000.0) + min(0.06, social * 0.035)


def commitment_ripple(cycle, new_commit, team):
    """A commitment can move related open targets immediately and creates a readable story."""
    st = S(cycle)
    notes = st["weekly_note"]
    moved = []
    mom = class_momentum(cycle, team)
    for r in cycle.pool:
        if r is new_commit or r.signed or r.committed_to is not None or team not in r.offers:
            continue
        strength, label = recruit_connection(r, new_commit)
        if strength <= 0:
            continue
        # Relationship is the headline; class buzz adds only a small tailwind.
        bump = min(5.5, 0.8 + strength * 3.4 + mom / 80.0)
        before = r.interest.get(team, 0.0)
        r.interest[team] = clamp(before + bump, 0, 100)
        if r.interest[team] > before + 0.5:
            moved.append((strength, r, label, bump))
            if team is getattr(cycle.league, "user_team", None) and (r in team.recruiting_targets or r.stars >= 4):
                say(cycle, team, r, f"Class reaction: {new_commit.player.name} committed; {label}. Your class is {momentum_word(mom)} (+{bump:.1f} interest).")
    if team is getattr(cycle.league, "user_team", None) and moved:
        moved.sort(key=lambda x: -x[0])
        names = ", ".join(x[1].player.name for x in moved[:3])
        notes[team].append(f"CLASS MOMENTUM: {new_commit.player.name}'s pledge resonated with {names}. The class is {momentum_word(mom)}.")

def pipeline_offseason(league):
    for t in league.teams:
        p = pipelines(t)
        for k in list(p):
            p[k] *= 0.9
            if p[k] < 2:
                del p[k]


# ═══ Enriching a class: schools, JUCOs, international specialists ═══════════

def enrich(cycle):
    st = S(cycle)
    if st["enriched"]:
        return
    st["enriched"] = True
    rng = random.Random(f"enrich:{cycle.league.seed}:{cycle.league.year}")
    for r in cycle.pool:
        if g(r, "hs") is None:
            r.hs = rng.choice(schools_in(r.home_state))
        if g(r, "kind") is None:
            r.kind = "hs"
    _add_jucos(cycle, rng)
    _add_internationals(cycle, rng)
    rerank(cycle)


def _add_jucos(cycle, rng):
    from recruiting import Recruit
    from roster import make_prospect
    used = {r.player.name for r in cycle.pool}
    states = list(TALENT)
    weights = [TALENT[s] for s in states]
    colleges = ("Iowa Western CC", "East Mississippi CC", "Hutchinson CC", "Garden City CC", "Butler CC",
                "Mississippi Gulf Coast CC", "Coffeyville CC", "Independence CC", "Blinn College", "Tyler JC",
                "Snow College", "Arizona Western", "Riverside City College", "Fort Scott CC", "Lackawanna College",
                "Northwest Mississippi CC", "Copiah-Lincoln CC", "Trinity Valley CC")
    for _ in range(110):
        pos = rng.choice(["QB", "RB", "WR", "WR", "TE", "OL", "OL", "OL", "DL", "DL", "DL", "LB", "LB", "CB",
                          "CB", "S"])
        state = rng.choices(states, weights=weights)[0]
        stars = rng.choices((2, 3, 4), weights=(45, 45, 10))[0]
        p = make_prospect(rng, pos, stars, state, used)
        for f in p.fundamentals:
            if f != "injury":
                p.fundamentals[f] = int(min(99, p.fundamentals[f] + rng.randint(5, 10)))   # two more years of football
        p.proficiency[pos] = round(min(1.1, p.proficiency[pos] + 0.08), 2)
        p.potential = max(20, p.potential - rng.randint(8, 18))                        # less runway left
        p.juco = rng.choice(colleges)
        from recruiting import RecruitingCycle
        pri = RecruitingCycle._roll_priorities(rng)
        if "playing_time" not in pri:
            pri[2] = "playing_time"                      # a JUCO kid wants the field, now
        r = Recruit(p, state, stars, pri, rng.choice(list(PERSONALITIES)))
        r.hs, r.kind = p.juco, "juco"
        p.hs_stars = stars
        cycle.pool.append(r)


def _add_internationals(cycle, rng):
    from recruiting import Recruit
    from roster import make_prospect
    used = {r.player.name for r in cycle.pool}
    places = (("Melbourne, Australia", "ProKick Australia"), ("Sydney, Australia", "ProKick Australia"),
              ("Perth, Australia", "ProKick Australia"), ("Auckland, New Zealand", "Rugby academy"),
              ("Munich, Germany", "Pro League Academy"), ("London, England", "Pro League Academy"),
              ("Toronto, Canada", "U Sports prep"), ("Monterrey, Mexico", "Borregos prep"))
    for i in range(8):
        pos = "P" if i < 5 else "K"
        where, acad = rng.choice(places[:4] if pos == "P" else places)
        p = make_prospect(rng, pos, rng.choice((3, 3, 4)), rng.choice(("CA", "TX", "FL")), used)
        p.fundamentals["kick_power"] = int(min(99, p.fundamentals.get("kick_power", 60) + rng.randint(8, 16)))
        p.intl = where
        from recruiting import RecruitingCycle
        r = Recruit(p, p.home_state, rng.choice((3, 4)), RecruitingCycle._roll_priorities(rng), "quiet")
        r.hs, r.kind, r.origin = acad, "intl", where
        p.hs_stars = r.stars
        cycle.pool.append(r)


def rerank(cycle):
    """National rankings follow the stars (and, inside a star tier, where he already sat)."""
    pool = cycle.pool
    old = {id(r): (r.national_rank or 9999) for r in pool}
    pool.sort(key=lambda r: (not getattr(r.player, "generational", False), -r.stars, old[id(r)], -r.true_grade))
    for i, r in enumerate(pool, 1):
        r.national_rank = i
        r.player.recruit_rank = i


def origin_line(r):
    k = g(r, "kind", "hs")
    if k == "juco":
        return f"JUCO · {g(r, 'hs', '')}"
    if k == "intl":
        return f"{g(r, 'origin', '')} · {g(r, 'hs', '')}"
    return g(r, "hs", "High School")


# ═══ Standing orders ════════════════════════════════════════════════════════

def queue(cycle, team):
    return S(cycle)["queue"][team]


def add_order(cycle, team, r, action, rule="weekly", n=0, pitch="auto", at=None):
    q = queue(cycle, team)
    e = {"r": r, "a": action, "rule": rule, "n": int(n or 0), "pitch": pitch, "last": None, "runs": 0,
         "added": (cycle.league.year, cycle.league.week)}
    if at is None:
        q.append(e)
    else:
        q.insert(max(0, min(len(q), at)), e)
    if r not in team.recruiting_targets:
        cycle.add_target(team, r)
    return e


def rule_text(e):
    t = QUEUE_RULES[e["rule"]]
    return t.format(n=e["n"]) if e["rule"] == "weeks" else t


def _check(cycle, team, e, week_key, offered=()):
    """(status, runnable) for one order right now — before hours. offered: recruits an earlier order
    in this week's run will have offered by the time this one comes up."""
    r, a = e["r"], e["a"]
    has_offer = team in r.offers or id(r) in offered
    if r.signed:
        return "done — he signed", False
    if e["rule"] == "until" and r.committed_to is not None:
        return ("done — he committed to you" if r.committed_to is team else "done — he committed elsewhere"), False
    if e["last"] == week_key:
        return "ran this week", False
    if e["rule"] == "biweekly" and e["last"] is not None and e["last"][0] == week_key[0] \
            and week_key[1] - e["last"][1] < 2:
        return "off week", False
    if a == "offer" and has_offer:
        return ("done — offer out" if team in r.offers else "offer already queued above"), False
    if a == "ov":
        return "use the visit planner", False
    if a not in ("evaluate", "offer") and not has_offer:
        return "needs an offer first", False
    if a == "close" and r.committed_to is team:
        return "he's already yours", False
    return "", True


def finished(e, status):
    return status.startswith("done")


def plan(cycle, team, hours=None):
    """What the queue does with the hours left this week: [(entry, status, cost, runs)]. Nothing is spent."""
    lg = cycle.league
    wk = (lg.year, lg.week)
    left = cycle.remaining_hours(team) if hours is None else hours
    out = []
    offered = set()
    for e in queue(cycle, team):
        status, ok = _check(cycle, team, e, wk, offered)
        cost = action_cost(team, e["a"])
        if ok and cost > left:
            out.append((e, "cut — out of hours", cost, False))
            continue
        if ok:
            left -= cost
            if e["a"] == "offer":
                offered.add(id(e["r"]))
            out.append((e, "runs", cost, True))
        else:
            out.append((e, status, cost, False))
    return out, left


def run_queue(cycle, team):
    """Spend the queue. Returns the summary dict for the week."""
    lg = cycle.league
    wk = (lg.year, lg.week)
    ran, cut, done = [], [], []
    for e in list(queue(cycle, team)):
        status, ok = _check(cycle, team, e, wk)
        if not ok:
            if finished(e, status):
                done.append((e["r"].name, status))
                queue(cycle, team).remove(e)
            continue
        cost = action_cost(team, e["a"])
        if cycle.remaining_hours(team) < cost:
            cut.append((e["r"].name, ACTIONS[e["a"]][0], cost))
            continue
        okk, msg = cycle.apply_action(team, e["r"], e["a"], pitch=e.get("pitch") or "auto", source="standing order")
        if not okk:
            cut.append((e["r"].name, ACTIONS[e["a"]][0], 0))
            continue
        e["last"] = wk
        e["runs"] += 1
        ran.append((e["r"].name, ACTIONS[e["a"]][0], cost, msg))
        if e["rule"] == "once":
            queue(cycle, team).remove(e)
        elif e["rule"] == "weeks":
            e["n"] -= 1
            if e["n"] <= 0:
                queue(cycle, team).remove(e)
    return {"ran": ran, "cut": cut, "done": done}


# Autopilot: a coordinator works his side of your board with a cap on hours.

def autopilot(cycle, team):
    return S(cycle)["auto"].setdefault(team, {"OC": {"on": False, "hours": 10}, "DC": {"on": False, "hours": 10}})


def run_autopilot(cycle, team, touched):
    ap = autopilot(cycle, team)
    out = []
    for role, side in (("OC", OFF_POS), ("DC", DEF_POS)):
        cfg = ap[role]
        if not cfg["on"]:
            continue
        budget = min(cfg["hours"], cycle.remaining_hours(team))
        board = [r for r in team.recruiting_targets if r.position in side and not r.signed and id(r) not in touched
                 and not (r.committed_to and r.committed_to is not team and r.interest.get(team, 0) < 40)]
        board.sort(key=lambda r: -(r.interest.get(team, 0) + r.stars * 4))
        for r in board:
            if budget < 1:
                break
            if r.committed_to is team:
                continue
            st = r.interest.get(team, 0)
            if team not in r.offers:
                a = "offer" if cycle.fit_value(team, r) >= 38 else "evaluate"
            elif r.scout[team] == 0:
                a = "evaluate"
            elif st > 45 and r.leader() is team:
                a = "close"
            elif st > 28:
                a = "position_coach"
            else:
                a = "contact"
            cost = action_cost(team, a)
            if cost > budget:
                a, cost = "contact", action_cost(team, "contact")
                if cost > budget or team not in r.offers:
                    continue
            ok, _ = cycle.apply_action(team, r, a, pitch="auto", source=f"{role} autopilot")
            if ok:
                budget -= cost
                out.append((role, r.name, ACTIONS[a][0]))
    return out


# ═══ Pitches ════════════════════════════════════════════════════════════════

def revealed(r):
    v = g(r, "revealed")
    if v is None:
        v = {}
        try:
            r.revealed = v
        except AttributeError:
            pass
    return v


def known(r, team):
    """His priorities your staff knows, in his order (film homework, plus what he's told you)."""
    base = set(r.priorities[:clamp(r.scout[team], 0, 3)]) | revealed(r).get(team, set())
    return [p for p in r.priorities if p in base]


def pitch_options(cycle, team, r, n=5):
    """[(key, strength word)] — what you could sell him on: what you know he wants first, then your best."""
    p = cycle.pitches(team, r)
    kn = known(r, team)
    rest = sorted((k for k in PRIORITIES if k not in kn), key=lambda k: -p.get(k, 0))
    opts = (kn + rest)[:n]
    return [(k, strength(p.get(k, 0))) for k in opts]


def strength(v):
    return "your strong suit" if v >= 75 else "a solid case" if v >= 55 else "a thin case" if v >= 35 else "a weak spot"


def pitch_mult(cycle, team, r, key):
    """(multiplier, reaction) — how a pitch on this topic lands."""
    if key in (None, ""):
        return 1.0, ""
    if key == "auto":
        kn = known(r, team)
        if not kn:
            return 1.0, ""
        p = cycle.pitches(team, r)
        key = max(kn, key=lambda k: p.get(k, 0) * (1.7, 1.4, 1.2)[r.priorities.index(k)])
    p = cycle.pitches(team, r).get(key, 50)
    label = PRIORITY_LABELS.get(key, key).lower()
    first = r.player.first_name
    if key in r.priorities:
        i = r.priorities.index(key)
        mult = (1.45, 1.3, 1.18)[i] * (0.7 + p / 170)
        revealed(r).setdefault(team, set()).add(key)
        tone = ("lit up", "leaned in", "nodded along")[i]
        weak = "" if p >= 45 else " — but he could tell your case there is thin"
        return mult, f"{first} {tone} when you talked about {label}{weak}."
    mult = 0.6
    return mult, f"{first} checked his phone while you talked about {label}. That isn't what he cares about."


# ═══ Official visits ════════════════════════════════════════════════════════

def ov_of(r):
    v = g(r, "ov")
    if v is None:
        v = {}
        try:
            r.ov = v
        except AttributeError:
            pass
    return v


def home_games_left(cycle, team):
    lg = cycle.league
    out = []
    for g_ in lg.team_games(team):
        if g_.home is team and not g_.neutral and not g_.played and g_.week >= max(1, lg.week):
            out.append(g_)
    return out


def can_invite(cycle, team, r, week=None, enforce=True):
    ov = ov_of(r)
    if r.signed:
        return False, "He's signed."
    if team not in r.offers:
        return False, "Offer him first — nobody takes an official visit without an offer."
    if team in ov:
        return False, f"He's already {'visited' if ov[team] < cycle.league.week else 'set to visit'} (Week {ov[team]})."
    if len(ov) >= OV_MAX:
        return False, f"He's used all {OV_MAX} official visits."
    if r.committed_to is not None and r.committed_to is not team and r.interest.get(team, 0) < 35:
        return False, f"He's committed to {r.committed_to.school} and won't take the trip."
    if r.interest.get(team, 0) < 15:
        return False, "He isn't interested enough to spend a visit on you yet."
    if enforce and cycle.remaining_hours(team) < OV_COST:
        return False, f"Setting up an official visit takes {OV_COST} hours; you're out."
    if week is not None and week in ov.values():
        return False, "He's visiting somewhere else that weekend."
    return True, ""


@capture.hook("rec", "acts", capture.b_visit)
def invite(cycle, team, r, game, enforce=True):
    ok, why = can_invite(cycle, team, r, game.week, enforce)
    if not ok:
        return False, why
    if enforce:
        cycle.hours_used[team] += OV_COST
    ov_of(r)[team] = game.week
    S(cycle)["ov_index"][game.week].append((team, r))
    if r not in cycle.by_team[team]:
        cycle.by_team[team].append(r)
    opp = game.away.school
    if r.stars >= 4:
        cycle._news(cycle.league.week, "visit", f"{r.stars}-star {r.position} {r.player.name} sets an official "
                                                f"visit to {team.school} (Week {game.week} vs {opp}).",
                    school=team.school, stars=r.stars)
    msg = f"{r.name} will officially visit for Week {game.week} vs {opp}."
    if enforce:
        log_move(cycle, team, r, "Official visit invite", OV_COST, msg)
    return True, msg


def ai_visits(cycle, team, board):
    """A CPU staff books official visits for its warmest targets at its next home games."""
    if getattr(cycle, "compressed", False):
        return
    games = [g_ for g_ in home_games_left(cycle, team) if g_.week > cycle.league.week]
    if not games:
        return
    rng = cycle.rng
    for r in board[:14]:
        if len(ov_of(r)) >= OV_MAX or team in ov_of(r) or team not in r.offers or r.signed:
            continue
        if r.committed_to is not None and r.committed_to is not team:
            continue
        if r.interest.get(team, 0) < 30 or rng.random() > 0.18:
            continue
        gm = games[0] if rng.random() < 0.6 or len(games) == 1 else games[1]
        invite(cycle, team, r, gm, enforce=False)


def resolve_visits(cycle, week):
    """After the Saturday: every official visit that weekend, graded."""
    idx = S(cycle)["ov_index"].pop(week, [])
    lg = cycle.league
    import hotseat
    mines = hotseat.humans(lg)
    for team, r in idx:
        if r.signed:
            continue
        gm = next((x for x in lg.schedule.get(week, []) if x.home is team and x.played), None)
        rep = _grade_visit(cycle, team, r, gm)
        if any(team is m for m in mines):
            S(cycle)["visits"][team].append(rep)
            say(cycle, team, r, rep["headline"])
            S(cycle)["weekly_note"][team].append(f"Official visit — {rep['headline']}")


def _grade_visit(cycle, team, r, gm):
    import stadium
    rng = random.Random(f"ov:{cycle.league.seed}:{cycle.league.year}:{team.school}:{r.player.name}")
    before = r.standing(team)
    pri = r.priorities
    w_result = 1.5 if "winning" in pri else 1.0
    w_build = 1.5 if "facilities" in pri else 1.0
    lines = []
    score = 4.0
    if gm is None:
        score += rng.gauss(0, 3)
        lines.append("No game that weekend — a campus tour and dinner with the staff.")
    else:
        opp = gm.opponent_of(team)
        won = gm.winner is team
        margin = gm.score_for(team) - gm.score_for(opp)
        orank = (getattr(gm, "ranks", None) or {}).get(opp)
        from commentary import rivalry_name
        riv = rivalry_name(team, opp)
        fill = getattr(gm, "fill", 0.8)
        att = getattr(gm, "attendance", 0)
        night = getattr(gm, "kick", 0) is not None and (getattr(gm, "kick", 0) or 0) >= 18 * 60
        res = (7 if won else -7) + (7 if won and orank else 0) + (4 if won and riv else 0) \
            + (-4 if not won and margin <= -21 else 0) + (-4 if won and getattr(opp, "fcs", False) else 0) \
            + (3 if won and 0 < margin <= 8 else 0)                       # a close win is a show
        score += res * w_result
        crowd = (fill - 0.8) * 26 + (stadium.noise_rating(team) - 5) * 1.1 + (3 if night and fill > 0.9 else 0)
        score += crowd
        build = (stadium.recruit_score(team) - 50) / 12 + stadium.parts(team)["recruit_center"] * 1.0
        score += build * w_build
        if "campus" in pri:
            score += (team.ratings.get("campus", 70) - 70) / 5
        wx_line = ""
        wx = getattr(gm, "wx", None)
        if wx and not wx.get("indoor"):                   # a kid from Miami in a November sleet storm
            import weather
            c = wx["q"][0]
            from_warm = getattr(r, "home_state", None) in ("FL", "TX", "LA", "GA", "AL", "MS", "SC", "AZ", "CA", "HI")
            if c["p"] >= 2 or wx.get("storm"):
                score -= 1.5 + (1.0 if from_warm else 0)
                wx_line = f"It poured all day. {'He had never been that wet in his life.' if from_warm else 'He stuck it out.'}"
            elif c["type"] == "snow" and c["p"]:
                score += -2.0 if from_warm else 1.0
                wx_line = "It snowed. He " + ("did not enjoy it." if from_warm else "loved it — a real football Saturday.")
            elif c["temp"] <= 32:
                score -= 2.0 if from_warm else 0.5
                wx_line = f"{c['temp']} degrees at kickoff." + (" He's still thawing out." if from_warm else "")
            elif 55 <= c["temp"] <= 78 and not c["p"] and weather.severity(wx) == 0:
                score += 0.8
                wx_line = "A perfect fall Saturday."
        score += rng.gauss(0, 3)
        who = f"No. {orank} {opp.school}" if orank else opp.school
        sc = f"{gm.score_for(team)}-{gm.score_for(opp)}"
        crowd_txt = (f"{att:,} packed in" if fill >= 0.97 else f"about {att:,} showed up" if fill >= 0.7
                     else f"a half-empty building ({att:,})")
        lines.append(f"{crowd_txt} for a {'night ' if night else ''}{'win' if won else 'loss'} "
                     f"{'over' if won else 'to'} {who}, {sc}.")
        if won and orank:
            lines.append("He was on the field for the postgame celebration.")
        elif won and riv:
            lines.append(f"He saw {riv} — and saw you win it.")
        elif not won and margin <= -21:
            lines.append("He left before the fourth quarter.")
        if wx_line:
            lines.append(wx_line)
        if stadium.parts(team)["recruit_center"] >= 2:
            lines.append("His family spent the game in the recruiting suite.")
        if fill >= 0.97 and stadium.noise_rating(team) >= 7:
            lines.append("The student section chanted his name.")
    key = (team, r)
    cycle.relationship[key] = clamp(cycle.relationship[key] + 10, 0, 100)
    if score > 0:
        cycle._add_interest(team, r, score * 1.35)
    else:
        r.interest[team] = clamp(r.interest.get(team, 0) + score * 0.7, 0, 100)
    after = r.standing(team)
    grade = "A home run" if score >= 24 else "A good weekend" if score >= 13 else "Fine" if score >= 4 else \
        "Flat" if score >= -2 else "A bad weekend"
    headline = f"{r.player.name} ({r.stars}★ {r.position}): {grade.lower()}. " + (lines[0] if lines else "")
    return {"week": cycle.league.week, "r": r, "score": round(score, 1), "grade": grade, "lines": lines,
            "before": before, "after": after, "headline": headline}


# ═══ The living trail ═══════════════════════════════════════════════════════

def senior_season(r, week):
    """His high school season through this week: (record, stat line)."""
    w = int(clamp(week, 0, 12))
    if w == 0:
        return "", "Senior season starts in Week 1."
    rng = random.Random(f"hs:{r.player.name}:{r.home_state}:{g(r, 'hs', '')}")
    q = r.true_grade
    team_w = sum(1 for _ in range(w) if rng.random() < clamp(0.35 + q / 150, 0.3, 0.9))
    rec = f"{team_w}-{w - team_w}"
    k = g(r, "kind", "hs")
    if k == "juco":
        return rec, f"{rec} at {g(r, 'hs', '')} · sophomore season"
    f = lambda base, spread: int(max(0, sum(rng.gauss(base * (q / 50), spread) for _ in range(w))))
    pos = r.position
    if pos == "QB":
        line = f"{f(210, 70):,} pass yds, {f(2.2, 1.2)} TD, {f(0.6, 0.6)} INT"
    elif pos == "RB":
        line = f"{f(125, 50):,} rush yds, {f(1.6, 1.0)} TD"
    elif pos in ("WR", "TE"):
        line = f"{f(5 if pos == 'WR' else 3, 2)} rec, {f(80 if pos == 'WR' else 45, 30):,} yds, {f(0.9, 0.7)} TD"
    elif pos == "OL":
        line = f"{f(1.2, 0.8)} pancakes a game on film · {f(0.3, 0.4)} sacks allowed"
    elif pos == "DL":
        line = f"{f(4, 2)} tackles, {f(1.0, 0.8)} sacks, {f(1.5, 1)} TFL"
    elif pos == "LB":
        line = f"{f(8, 3)} tackles, {f(1.2, 1)} TFL, {f(0.3, 0.4)} sacks"
    elif pos in ("CB", "S"):
        line = f"{f(4, 2)} tackles, {f(0.9, 0.8)} PBU, {f(0.35, 0.4)} INT"
    elif pos == "K":
        line = f"{f(1.2, 0.8)} FG, long {int(38 + q / 4 + rng.random() * 8)}"
    else:
        line = f"{40 + q / 12 + rng.random() * 3:.1f} avg per punt"
    return rec, f"{line} · team {rec}"


def truth_stars(r):
    return next(s for lo, s in TRUTH_STARS if r.true_grade >= lo)


def ratings_update(cycle, week):
    """Ratings services re-rank the country: risers and fallers."""
    st = S(cycle)
    if week not in RATING_WEEKS or week in st["rated"]:
        return
    st["rated"].add(week)
    rng = random.Random(f"ratings:{cycle.league.seed}:{cycle.league.year}:{week}")
    risers, fallers = [], []
    for r in cycle.pool:
        if r.signed:
            continue
        t = truth_stars(r)
        if t != r.stars and rng.random() < 0.22:
            old = r.stars
            r.stars = clamp(r.stars + (1 if t > r.stars else -1), 1, 5)
            (risers if r.stars > old else fallers).append((r, old))
    rerank(cycle)
    for r, old in sorted(risers, key=lambda x: -x[0].stars)[:4]:
        if r.stars >= 4:
            cycle._news(week, "rating", f"RISER: {r.position} {r.player.name} ({STATES[r.home_state][0]}) jumps to "
                                        f"{r.stars} stars — No. {r.national_rank} nationally.", stars=r.stars)
    for r, old in sorted(fallers, key=lambda x: -x[1])[:3]:
        if old >= 4:
            cycle._news(week, "rating", f"FALLER: {r.position} {r.player.name} drops to {r.stars} stars.",
                        stars=old)
    import hotseat
    for mine in hotseat.humans(cycle.league):
        mv = [(r, old) for r, old in risers + fallers if r in mine.recruiting_targets]
        if mv:
            S(cycle)["weekly_note"][mine].append(
                "Ratings update: " + ", ".join(f"{r.player.name} {'▲' if r.stars > old else '▼'} {r.stars}★"
                                               for r, old in mv[:6]))


def camp_standouts(cycle):
    """Summer camp season: a few kids everybody underrated show out."""
    st = S(cycle)
    if st["standouts"]:
        return
    st["standouts"] = True
    rng = random.Random(f"camps:{cycle.league.seed}:{cycle.league.year}")
    gems = [r for r in cycle.pool if truth_stars(r) > r.stars and g(r, "kind", "hs") == "hs"]
    rng.shuffle(gems)
    for r in gems[:6]:
        r.stars = clamp(r.stars + 1, 1, 5)
        r.attention += 20
        cycle._news(0, "rating", f"CAMP STANDOUT: {r.position} {r.player.name} ({STATES[r.home_state][0]}) "
                                 f"tore up the camp circuit — now a {r.stars}-star.", stars=r.stars)
    rerank(cycle)


@capture.hook("rec", None, capture.b_camp, ok=capture.camp_held)
def run_camp(cycle, team, recruits):
    """Your summer camp: they come to campus, you see them up close."""
    st = S(cycle)
    if st["camp"].get(team):
        return [], "You've already held camp this summer."
    st["camp"][team] = True
    out = []
    for r in recruits[:CAMP_MAX]:
        home = TEAM_STATES.get(team.school)
        near = home == r.home_state or (home and STATES[home][1] == r.region)
        if not near and r.interest.get(team, 0) < 10 and r.stars >= 4:
            out.append((r, "didn't make the trip"))
            continue
        r.scout[team] = clamp(r.scout[team] + 2, 0, 3)
        cycle.relationship[(team, r)] = clamp(cycle.relationship[(team, r)] + 8, 0, 100)
        r.interest[team] = clamp(r.interest.get(team, 0) + 5, 0, 45 if team not in r.offers else 100)
        gap = r.true_grade - {1: 33, 2: 37, 3: 46, 4: 54, 5: 66}[r.stars]
        verdict = ("looked better than his rating — a real find" if gap >= 6 else
                   "played right to his rating" if gap >= -4 else "didn't look like his rating up close")
        out.append((r, verdict))
        say(cycle, team, r, f"Summer camp: {verdict}.")
        log_move(cycle, team, r, "Summer camp", 0, f"Camp: {verdict}.")
    came = sum(1 for _, v in out if v != "didn't make the trip")
    return out, f"{came} came to camp."


# ═══ Commitments: hard, soft, silent — and the crystal ball ═════════════════

def on_commit(cycle, r, team, week):
    """Returns True if the commitment is silent (no news)."""
    rng = cycle.rng
    margin = r.lead_margin()
    if r.personality == "loyal" or margin >= 32:
        kind = "hard"
    elif r.personality in ("front_runner", "showman") or margin < 16:
        kind = "soft"
    else:
        kind = "hard" if rng.random() < 0.55 else "soft"
    r.commit_kind = kind
    silent = r.stars >= 3 and rng.random() < 0.12 and r.personality in ("quiet", "homebody", "family_first")
    r.silent = silent
    if silent:
        S(cycle)["silent"][id(r)] = week + rng.randint(2, 5)
    import hotseat
    if hotseat.is_human(cycle.league, team):
        S(cycle)["weekly_note"][team].append(
            f"COMMIT: {r.stars}★ {r.position} {r.player.name} — a {kind} commitment" + (" (silent for now)" if silent else ""))
    commitment_ripple(cycle, r, team)
    return silent


def public_commit(r, viewer=None):
    """Who the world thinks he's committed to. A silent commit looks open to everyone but his school."""
    c = r.committed_to
    if c is not None and g(r, "silent", False) and c is not viewer:
        return None
    return c


def commit_word(r):
    if r.committed_to is None:
        return ""
    if g(r, "early", False):
        return "SIGNED (early)"
    return {"hard": "hard commit", "soft": "soft commit"}.get(g(r, "commit_kind", "soft"), "committed") \
        + (" · silent" if g(r, "silent", False) else "")


def decommit_mult(r):
    return {"hard": 0.35, "soft": 1.6}.get(g(r, "commit_kind"), 1.0)


def crystal(r, cycle=None):
    """(school, confidence 0-100) — what the experts predict, or None. Only schools that have
    offered him (and, with the cycle, have room for him) count, and the confidence is his real
    signing-day odds."""
    if r.signed or r.committed_to is not None:
        return None
    import recruiting as rc
    able = [t for t in r.top_schools(8) if t in r.offers]
    if cycle is not None:
        able = [t for t in able if rc.block_reason(cycle.league, t, r, cycle._class_of(t)) is None]
    if not able or r.interest[able[0]] < 25:
        return None
    able = [t for t in able if r.interest[t] >= r.interest[able[0]] * rc.IN_RUNNING]
    w = [max(0.1, r.interest[t]) ** rc.PICK_EXP for t in able]
    conf = 100 * w[0] / sum(w)
    if cycle is not None:
        conf *= room_odds(cycle, able[0], r)
    conf = conf * 0.8 - 15          # calibrated against simulated signing days: late swings, spots taken, flips
    return able[0], int(clamp(round(conf), 10, 90))


def room_odds(cycle, team, r):
    """Will there still be a spot when he picks? Better prospects pick first on signing day, so count
    the uncommitted kids ranked ahead of him who lean to the same school at his position."""
    import recruiting as rc
    rem = room_left(cycle, team, r.position)
    ahead = sum(1 for rank in _leaning(cycle).get((team, r.position), ()) if rank < r.national_rank)
    if rem <= 0:
        return 0.15
    return min(1.0, rem / (ahead + 1)) ** 0.7


def room_left(cycle, team, pos):
    import recruiting as rc
    from roster import ROSTER_SIZE
    roster = [p for p in team.roster if p.position == pos]
    room = max(1, ROSTER_SIZE[pos] - len(roster) + sum(1 for p in roster if p.year >= 2))
    return room - sum(1 for x in cycle._class_of(team) if x.position == pos)


def _leaning(cycle):
    key = (getattr(cycle, "week", None), sum(1 for r in cycle.pool if r.committed_to is not None))
    c = cycle.__dict__.get("_lean_cache")
    if c and c[0] == key:
        return c[1]
    out = {}
    for x in cycle.pool:
        if x.signed or x.committed_to is not None or not x.interest:
            continue
        t = max(x.interest, key=lambda k: x.interest[k])
        out.setdefault((t, x.position), []).append(x.national_rank)
    cycle._lean_cache = (key, out)
    return out


def _silent_reveals(cycle, week):
    sil = S(cycle)["silent"]
    for r in cycle.pool:
        due = sil.get(id(r))
        if due is None:
            continue
        if r.committed_to is None or r.signed or week >= due:
            sil.pop(id(r), None)
            if r.committed_to is not None and g(r, "silent", False):
                r.silent = False
                cycle._news(week, "commit", f"{r.stars}-star {r.position} {r.player.name} announces he's committed to "
                                            f"{r.committed_to.school} — he'd been a silent commit for weeks.",
                            school=r.committed_to.school, stars=r.stars)


def _crystal_news(cycle, week):
    cb = S(cycle)["cb"]
    posted = 0
    for r in cycle.pool[:120]:
        if posted >= 3:
            break
        if r.stars < 4:
            continue
        pred = crystal(r, cycle)
        if pred is None:
            continue
        team, conf = pred
        last = cb.get(id(r))
        if conf >= 60 and (last is None or (last[0] is not team and conf >= 66 and week - last[2] >= 3)):
            cb[id(r)] = (team, conf, week)
            posted += 1
            if last is None:
                cycle._news(week, "cb", f"CRYSTAL BALL: {r.stars}-star {r.position} {r.player.name} trending to "
                                        f"{team.school} ({conf}%).", school=team.school, stars=r.stars)
            else:
                cycle._news(week, "cb", f"TRENDING: {r.player.name} ({r.stars}★ {r.position}) — the crystal ball flips "
                                        f"from {last[0].school} to {team.school} ({conf}%).", school=team.school,
                            stars=r.stars)


# ═══ Early signing period and National Signing Day ══════════════════════════

def early_signing(cycle, week):
    st = S(cycle)
    if week != EARLY_SIGNING_WEEK or st["early_done"] or getattr(cycle, "compressed", False):
        return
    st["early_done"] = True
    rng = random.Random(f"esp:{cycle.league.seed}:{cycle.league.year}")
    signed, held = defaultdict(list), defaultdict(list)
    for r in cycle.pool:
        t = r.committed_to
        if t is None or r.signed:
            continue
        kind = g(r, "commit_kind", "soft")
        rival = max((v for s, v in r.interest.items() if s is not t), default=0)
        close = r.interest.get(t, 0) - rival < 8
        p = (0.85 if kind == "hard" else 0.35) * (0.5 if close else 1.0)
        if rng.random() < p:
            r.signed = True
            r.early = True
            r.silent = False
            signed[t].append(r)
        else:
            held[t].append(r)
    big = sorted((r for rs in signed.values() for r in rs), key=lambda r: r.national_rank)[:5]
    for r in big:
        cycle._news(week, "commit", f"EARLY SIGNING DAY: {r.stars}-star {r.position} {r.player.name} signs with "
                                    f"{r.committed_to.school}.", school=r.committed_to.school, stars=r.stars)
    import hotseat
    for mine in hotseat.humans(cycle.league):
        s_, h_ = signed.get(mine, []), held.get(mine, [])
        note = (f"Early signing day: {len(s_)} of your {len(s_) + len(h_)} commits signed."
                + (f" Still out there: {', '.join(r.player.name for r in h_[:6])} — they can still flip until February."
                   if h_ else " Every commit is locked in."))
        st["weekly_note"][mine].append(note)
        st.setdefault("early_reports", {})[mine] = {"signed": s_, "held": h_}
        if mine is getattr(cycle.league, "user_team", None):
            st["early_report"] = st["early_reports"][mine]


def late_flip(cycle, r, rng):
    """National Signing Day: a soft commit who's been listening to someone else."""
    t = r.committed_to
    if t is None or g(r, "early", False):
        return None
    rival = max((s for s in r.interest if s is not t and s in r.offers), key=lambda s: r.interest[s], default=None)
    if rival is None:
        return None
    gap = r.interest[rival] - r.interest.get(t, 0)
    odds = (0.30 if g(r, "commit_kind") == "soft" else 0.06) * (1 + max(0, gap) / 8)
    if gap > -4 and rng.random() < odds:
        return rival
    return None


# ═══ Rivals fight back ══════════════════════════════════════════════════════

def crowded_mult(cycle, team, r):
    """'You already have three quarterbacks committed.' Returns a multiplier."""
    klass = cycle.class_cache.get(team)
    if not klass:
        return 1.0
    same = sum(1 for x in klass if x.position == r.position and x is not r)
    if not same:
        return 1.0
    memo = S(cycle).setdefault("needs_wk", {})
    k = (team.school, cycle.league.week)
    if k not in memo:
        if len(memo) > 400:
            memo.clear()
        memo[k] = cycle._needs(team)
    need = memo[k].get(r.position, 1)
    if same >= need + 1:
        return 0.5
    if same >= need:
        return 0.72
    return 1.0


def negative_recruiting(cycle, week):
    """Rivals use your record and your crowded rooms against you — for every coach at the table."""
    import hotseat
    hotseat.each_seat(cycle.league, lambda: _negative_recruiting(cycle, week))


def bidding_wars(cycle, week):
    import hotseat
    hotseat.each_seat(cycle.league, lambda: _bidding_wars(cycle, week))


# ═══ The week ═══════════════════════════════════════════════════════════════

def before_tick(cycle, week, user_team):
    """Saturday night, before the country's staffs move: your queue, your coordinators, the visits."""
    enrich(cycle)
    if week >= 1:
        camp_standouts(cycle)
    import hotseat
    humans = hotseat.humans(cycle.league)
    if (user_team is not None or humans) and not getattr(cycle, "compressed", False):
        for ht in (humans or [user_team]):                            # every coach at the table
            with hotseat.acting_as(cycle.league, ht):
                _run_human(cycle, week, ht)
    import commissioner
    if commissioner.active(cycle.league) and not getattr(cycle, "compressed", False):
        for pt in commissioner.player_teams(cycle.league):       # Commissioner Mode: each player's standing orders
            summ = run_queue(cycle, pt)
            touched = {id(e["r"]) for e in queue(cycle, pt) if e.get("last") == (cycle.league.year, week)}
            summ["auto"] = run_autopilot(cycle, pt, touched)
            summ["week"] = week
            S(cycle)["summary"][pt] = summ
    resolve_visits(cycle, week)


def after_tick(cycle, week, user_team):
    _silent_reveals(cycle, week)
    _crystal_news(cycle, week)
    ratings_update(cycle, week)
    negative_recruiting(cycle, week)
    bidding_wars(cycle, week)
    early_signing(cycle, week)
    import hotseat
    for mine in hotseat.humans(cycle.league):
        _pipeline_intel(cycle, mine)
        with hotseat.acting_as(cycle.league, mine):
            _post_weekly(cycle, mine, week)


def _pipeline_intel(cycle, team):
    p = pipelines(team)
    if not p:
        return
    for r in team.recruiting_targets:
        v = p.get(hs_key(r), 0)
        if v >= 30:
            r.scout[team] = max(r.scout[team], 2 if v >= 60 else 1)


def _post_weekly(cycle, team, week):
    notes = S(cycle)["weekly_note"].pop(team, [])
    lg = cycle.league
    if not notes or getattr(lg, "mode", None) != "career" or getattr(lg, "autosim", False):
        return
    try:
        import people
        people._post(lg, "Recruiting Office", "your recruiting staff", f"Recruiting report — {lg.week_name(week)}",
                     "\n".join("• " + n for n in notes[:10]), kind="note")
    except Exception:
        pass


# ═══ Signing: pipelines, walk-ons, the book ═════════════════════════════════

def on_attach(team, r, p, next_year):
    """He's on campus: the pipeline grows, the book records him, JUCO/international details stick."""
    k = g(r, "kind", "hs")
    p.hs_key = hs_key(r) if g(r, "hs") else None          # a class signed before high schools were tracked has none
    p.hs_name = g(r, "hs", "") or ""
    if k == "juco":
        p.year = 2
        p.events[next_year].append(f"JUCO transfer from {g(r, 'hs', '')}")
    elif k == "intl":
        p.events[next_year].append(f"From {g(r, 'origin', '')} ({g(r, 'hs', '')})")
    if k == "hs" and p.hs_key:
        pipeline_hit(team, p.hs_key, 25 if r.stars >= 3 else 15)
    book = team.__dict__.setdefault("signing_book", [])
    book.append({"year": next_year, "player": p, "stars": r.stars, "rank": r.national_rank, "pos": r.position,
                 "kind": k, "hs": g(r, "hs", ""), "early": bool(g(r, "early", False)),
                 "pwo": bool(getattr(p, "pwo", False))})
    del book[:-300]


def cut_at_signing(team, r):
    """Told to look elsewhere at signing day: his high school remembers."""
    if g(r, "kind", "hs") == "hs" and g(r, "hs"):
        pipeline_hit(team, hs_key(r), -20)


def broken_promise(team, p):
    k = getattr(p, "hs_key", None)
    if k:
        pipeline_hit(team, k, -30)


def pwo_list(cycle, team):
    return S(cycle)["pwo"][team]


def can_pwo(cycle, team, r):
    if r.signed or r.committed_to is not None:
        return False, "He's already spoken for."
    if r.stars > 2 and g(r, "kind", "hs") != "intl":
        return False, "A three-star-plus kid wants a scholarship, not a walk-on spot."
    if cycle.league.week < 8:
        return False, "Walk-on invites go out from Week 8 on."
    if len(pwo_list(cycle, team)) >= PWO_MAX:
        return False, f"You can bring in {PWO_MAX} preferred walk-ons."
    if r in pwo_list(cycle, team):
        return False, "He's already on your walk-on list."
    return True, ""


@capture.hook("rec", "acts", capture.b_pwo)
def add_pwo(cycle, team, r):
    ok, why = can_pwo(cycle, team, r)
    if not ok:
        return False, why
    pwo_list(cycle, team).append(r)
    log_move(cycle, team, r, "Preferred walk-on invite", 0, "Invited as a preferred walk-on.")
    return True, f"{r.player.name} is invited as a preferred walk-on — no scholarship, a shot to earn one."


def sign_pwos(league, cycle, rng, next_year):
    """Before the walk-on fill: your preferred walk-ons join (the undecided ones who didn't sign elsewhere)."""
    from recruiting import attach_class
    for team, rs in S(cycle)["pwo"].items():
        for r in rs:
            if r.signed or (r.committed_to is not None and r.committed_to is not team):
                continue
            r.signed = True
            r.committed_to = team
            p = r.player
            p.walk_on = True
            p.pwo = True
            attach_class(team, [r], cycle, rng, next_year)
            p.events[next_year].append("Preferred walk-on")


def pwo_scholarships(league):
    """Walk-ons who became real players earn a scholarship."""
    for t in league.teams:
        for p in t.roster:
            if getattr(p, "pwo", False) and getattr(p, "walk_on", False) and p.overall >= 68:
                p.walk_on = False
                p.events[league.year].append("Earned a scholarship (walk-on)")
                import hotseat
                if hotseat.is_human(league, t):
                    with hotseat.acting_as(league, t):
                        league.__dict__.setdefault("career_log", []).append(
                            (league.year, f"Walk-on {p.position} {p.name} earned a scholarship."))


# ═══ Hit or bust ════════════════════════════════════════════════════════════

HIT_AT = {5: 78, 4: 72, 3: 67, 2: 62, 1: 58}
BUST_AT = {5: 68, 4: 63, 3: 55, 2: 50, 1: 45}


def verdict(entry, league):
    p = entry["player"]
    yrs = league.year - entry["year"]
    here = any(p is q for q in getattr(p.team, "roster", [])) if getattr(p, "team", None) else False
    ovr = p.overall
    st = entry["stars"]
    if yrs < 1:
        return "too early", ovr
    if ovr >= HIT_AT.get(st, 70) or (st <= 3 and ovr >= 74):
        return ("steal" if st <= 3 else "hit"), ovr
    if yrs >= 2 and ovr < BUST_AT.get(st, 55):
        return "bust", ovr
    if not here and yrs < 4:
        return "gone", ovr
    return "developing" if yrs < 3 else "contributor", ovr


def _negative_recruiting(cycle, week):
    """Other staffs tell your targets what's wrong with you."""
    lg = cycle.league
    mine = getattr(lg, "user_team", None)
    if mine is None or getattr(cycle, "compressed", False) or week < 2:
        return
    rng = random.Random(f"neg:{lg.seed}:{lg.year}:{week}")
    c = mine.coach
    heat = getattr(c, "seat", 0) if c is not None else 0
    losing = mine.losses - mine.wins
    hits = 0
    for r in mine.recruiting_targets:
        if hits >= 4 or r.signed or (r.committed_to is not None and r.committed_to is not mine):
            continue
        rivals = [t for t in r.top_schools(3) if t is not mine]
        if not rivals or r.interest.get(mine, 0) < 15:
            continue
        rv = rivals[0]
        pitch = None
        if heat >= 62 and rng.random() < 0.22:
            pitch = f"{rv.school} is telling {r.player.first_name} you won't be the coach there in a year."
        elif losing >= 3 and rng.random() < 0.18:
            pitch = f"{rv.school} keeps bringing up your record with {r.player.first_name}."
        elif crowded_mult(cycle, mine, r) < 1 and rng.random() < 0.25:
            pitch = f"{rv.school} asked {r.player.first_name} why he'd go somewhere that's already loaded at {r.position}."
        else:
            room = [p for p in mine.players_at(r.position) if p.year <= 1 and p.overall >= r.projection()]
            if len(room) >= 2 and rng.random() < 0.15:
                pitch = f"{rv.school} is telling {r.player.first_name} he'll sit behind {room[0].last_name} for years."
        if pitch is None:
            continue
        hits += 1
        r.interest[mine] = clamp(r.interest.get(mine, 0) - rng.uniform(2.5, 6), 0, 100)
        say(cycle, mine, r, pitch)
        S(cycle)["neg"][mine].append((week, r, pitch))
    if hits:
        S(cycle)["weekly_note"][mine].append(f"Negative recruiting: rival staffs went after {hits} of your targets.")

def _bidding_wars(cycle, week):
    """Late in the cycle, collectives fight over the best kids — including the ones you're paying."""
    import finance as fi
    lg = cycle.league
    mine = getattr(lg, "user_team", None)
    if mine is None or week < 11 or getattr(cycle, "compressed", False):
        return
    bids = S(cycle)["bids"]
    for r in mine.recruiting_targets:
        if r.signed or r.stars < 4 or r.committed_to not in (None, mine):
            continue
        ours = fi.offer_to(cycle, mine, r)
        if not ours:
            continue
        rivals = [t for t in r.top_schools(3) if t is not mine and t in r.offers]
        if not rivals:
            continue
        rv = rivals[0]
        if r.interest.get(rv, 0) < r.interest.get(mine, 0) - 12:
            continue
        if bids.get(id(r), -9) >= week - 1:
            continue
        theirs = fi.offer_to(cycle, rv, r)
        if theirs >= ours * 1.1:
            continue
        new = fi._round(max(ours * 1.15, theirs * 1.2), 5_000)
        if new - theirs > fi.available(lg, rv) or rv.coach is None:
            continue
        ok, _ = fi.make_offer(cycle, rv, r, new)
        if ok:
            bids[id(r)] = week
            txt = (f"BIDDING WAR: {rv.school}'s collective raised its NIL offer to {r.player.name} to "
                   f"{fi.money(new)}/yr. You're at {fi.money(ours)}.")
            say(cycle, mine, r, txt)
            S(cycle)["weekly_note"][mine].append(txt)

def _run_human(cycle, week, user_team):
    """One coach's standing orders, coordinators and the note about both."""
    summ = run_queue(cycle, user_team)
    touched = {id(e["r"]) for e in queue(cycle, user_team) if e.get("last") == (cycle.league.year, week)}
    summ["auto"] = run_autopilot(cycle, user_team, touched)
    summ["week"] = week
    S(cycle)["summary"][user_team] = summ
    if summ["ran"] or summ["cut"] or summ["auto"]:
        hrs = sum(c for _, _, c, _ in summ["ran"])
        S(cycle)["weekly_note"][user_team].append(
            f"Standing orders: {len(summ['ran'])} ran ({hrs}h)"
            + (f", {len(summ['cut'])} cut for hours ({', '.join(n for n, _, _ in summ['cut'][:4])})" if summ["cut"] else "")
            + (f"; coordinators worked {len(summ['auto'])} more" if summ["auto"] else "") + ".")
