"""
sideline.py — Coaching the game from the sideline.

Picking plays is half the job. The other half happens between them, and it is
all here: what the staff sees, what you tell them, who plays, and the calls
nobody else on the headset gets to make.

THE TABLET (on every call screen)
  Momentum and the crowd · this drive · what's working and what isn't ·
  what they do in this down and distance · a line from your coordinator ·
  who's hot and who's cold · your standing orders.

SERIES ORDERS (between series, or [G] any time)
  Offense   Normal · Max protect · Quick game · Pound it · Tempo · Take shots
            + feed one player the ball
  Defense   Normal · Spy the QB · Two deep · Load the box · Pin your ears back ·
            Double their best receiver
  Orders stand until you change them. They shape what your staff calls, and
  most of them change the snap itself too (an extra blocker, a spy, a safety
  down in the box). The other sideline sees your tendencies and answers.

THE PEOPLE
  Trainer's report   a starter gets hurt: shut him down, tape it and send him
                     back (hobbled, and he can make it worse), or only if we need
                     him late
  The quarterback    two picks? go to the backup for a series, or for the day
  Leadership         after a pick, a fumble, a costly flag, a miss, a blown
                     coverage: arm around him, get in his face, let a captain
                     handle it, or sit him a series. Players are different —
                     the position coach tells you who he is.
  Stop the bleeding  a timeout when the building has turned on you settles it
  The crowd          at home on their third down: [C] get them up

THE CALLS THAT WERE THE STAFF'S
  Extra point or two · kickoff (deep, squib, onside, surprise onside) · fake
  punt / fake field goal · accept or decline a flag · the replay challenge
  (one a game, a second if you win it; a lost one costs a timeout) · ice the
  kicker · overtime: offense or defense first.

FRIDAY GAME PLAN (week hub → [G])
  One offensive key, one defensive key, and whether to script your openers.
  The staff says what the film shows; a key that fits the matchup is worth
  more than one that doesn't. Halftime tells you if it's working.

AFTER THE GAME
  The headset log: your fourth downs, tries, kicks, challenges and people
  calls, each priced in win chance at the moment you made it (decisions.py),
  what the chart said, and what happened. The grade is for the process: how
  much win chance your calls gave away — not whether they matched the chart,
  and not how they turned out. The podium may ask about the big one.

Settings → [6] Sideline turns each part on or off.
"""
import random
from dataclasses import replace

import decisions
from ui import C, WIDTH, ask, pad, paint, rule, truncate, visible_len

# ═══ Settings ════════════════════════════════════════════════════════════════
DEFAULTS = {"sideline_checkins": "notable",    # every | notable | off
            "sideline_tablet": True,
            "sideline_people": True,           # trainer, the QB, leadership moments
            "sideline_calls": True}            # tries, kickoffs, flags, challenges, icing, overtime


def opt(key):
    import settings
    return settings.load().get(key, DEFAULTS[key])


# ═══ Orders ══════════════════════════════════════════════════════════════════
OFF_ORDERS = {
    "none":    ("Normal", "the staff's plan, nothing extra"),
    "protect": ("Max protect", "a back stays in: more time, one fewer receiver"),
    "quick":   ("Quick game", "ball out fast: fewer sacks, fewer shots"),
    "pound":   ("Pound it", "run the ball: it wears on them — they'll load up"),
    "tempo":   ("Tempo", "no huddle: their defense can't sub or catch its breath — clock moves"),
    "shots":   ("Take shots", "go downfield: big plays, more sacks and picks"),
}
DEF_ORDERS = {
    "none":     ("Normal", "the staff's plan, nothing extra"),
    "spy":      ("Spy the QB", "a man on the quarterback: one fewer rusher"),
    "two_deep": ("Two deep", "safeties back: nothing over the top — softer against the run"),
    "load_box": ("Load the box", "a safety down: stop the run — exposed deep"),
    "ears":     ("Pin your ears back", "rush upfield: more pressure — draws and screens hurt"),
    "bracket":  ("Double their best WR", "two on him — everybody else is one-on-one"),
}

# ═══ Friday game plan ════════════════════════════════════════════════════════
OFF_KEYS = {
    "balanced": ("Balanced", "take what they give"),
    "run":      ("Establish the run", "lean on the ground game, win up front"),
    "deep":     ("Attack them deep", "our receivers against their corners"),
    "quick":    ("Quick game vs their rush", "ball out before the rush gets home"),
    "control":  ("Ball control", "long drives, keep their offense on the bench"),
}
DEF_KEYS = {
    "balanced": ("Balanced", "sound, nothing fancy"),
    "stop_run": ("Stop the run", "make them one-dimensional"),
    "wr1":      ("Take away their best receiver", "somebody else has to beat us"),
    "rush":     ("Get after their QB", "pressure him, live with some big plays"),
    "front":    ("Keep everything in front", "no big plays — they have to drive it"),
    "contain":  ("Contain the quarterback", "keep him in the pocket"),
}
SCRIPT_LIFT = 0.9          # rating points for the first ten scripted snaps
SCRIPT_COST = 0.1          # a practice period spent scripting

SEP_SHORT = ("short", "flat", "behind")


def _prof(p):
    from game_sim import build_profile
    cache = p.__dict__.setdefault("_sl_prof", {})
    key = getattr(p, "overall", 0)
    if cache.get("k") != key:
        cache.clear()
        cache["k"] = key
        cache["v"] = build_profile(p)
    return cache["v"]


def _avg(players, key):
    vals = [_prof(p)[key] for p in players if p is not None]
    return sum(vals) / len(vals) if vals else 60.0


def _starters(team):
    try:
        return team.starters()
    except Exception:
        return {}


def matchup(team, opp):
    """How our units stack up against theirs (rating-point edges, + is ours)."""
    s, o = _starters(team), _starters(opp)
    g = lambda d, pos, n=9: list(d.get(pos, []))[:n]
    run_o = _avg(g(s, "OL", 5), "block") * 0.6 + _avg(g(s, "RB", 1), "vision") * 0.4
    run_d = _avg(g(o, "DL", 4), "run_stop") * 0.6 + _avg(g(o, "LB", 3), "fit") * 0.4
    deep_o = _avg(g(s, "WR", 3), "route") * 0.5 + _avg(g(s, "WR", 3), "speed") * 0.5
    deep_d = _avg(g(o, "CB", 2), "cover") * 0.5 + _avg(g(o, "CB", 2), "speed") * 0.5
    prot = _avg(g(s, "OL", 5), "pass_block")
    rush = _avg(g(o, "DL", 4), "rush")
    their_run_o = _avg(g(o, "OL", 5), "block") * 0.6 + _avg(g(o, "RB", 1), "vision") * 0.4
    our_run_d = _avg(g(s, "DL", 4), "run_stop") * 0.6 + _avg(g(s, "LB", 3), "fit") * 0.4
    their_wrs = g(o, "WR", 3)
    wr1 = max(their_wrs, key=lambda p: _prof(p)["route"] + _prof(p)["speed"], default=None)
    wr_gap = (_prof(wr1)["route"] - _avg(their_wrs[1:], "route")) if wr1 is not None and len(their_wrs) > 1 else 0
    their_prot = _avg(g(o, "OL", 5), "pass_block")
    our_rush = _avg(g(s, "DL", 4), "rush")
    their_deep = _avg(their_wrs, "speed")
    our_deep_d = _avg(g(s, "CB", 2), "speed") * 0.5 + _avg(g(s, "S", 2), "cover") * 0.5
    qb = (g(o, "QB", 1) or [None])[0]
    qb_legs = _prof(qb)["speed"] if qb is not None else 55
    return {"run": run_o - run_d, "deep": deep_o - deep_d, "quick": rush - prot, "control": run_o - run_d - 2,
            "stop_run": their_run_o - our_run_d, "wr1": wr_gap, "rush": our_rush - their_prot,
            "front": their_deep - our_deep_d, "contain": qb_legs - 70, "wr1_player": wr1, "qb": qb}


def fit(edge):
    """A key's edge (rating points) → how much it's worth (0.4 - 1.5)."""
    return max(0.4, min(1.5, 1.0 + edge / 14))


def recommend(team, opp, m=None):
    """The staff's plan: (off key, def key, [lines of what the film shows])."""
    m = m or matchup(team, opp)
    off = max(("run", "deep", "quick", "control"), key=lambda k: m[k] + (0.5 if k == "run" else 0))
    if max(m["run"], m["deep"], m["quick"]) < -3:
        off = "quick" if m["quick"] > 2 else "control" if m["run"] > m["deep"] else "balanced"
    dfk = max(("stop_run", "wr1", "rush", "front", "contain"), key=lambda k: m[k] + (0.5 if k == "stop_run" else 0))
    if m[dfk] < 1:
        dfk = "balanced"
    lines = []
    if m["deep"] >= 4:
        lines.append("Their corners are the soft spot. Our receivers should win outside.")
    elif m["deep"] <= -4:
        lines.append("Their corners can run. Don't count on winning deep.")
    if m["run"] >= 4:
        lines.append("We should be able to run on that front.")
    elif m["run"] <= -4:
        lines.append("Their front is stout — running inside will be a fight.")
    if m["quick"] >= 4:
        lines.append("Their pass rush is the best thing they do. Get it out fast.")
    if m["stop_run"] >= 3:
        lines.append("They'll want to run the ball right at us.")
    if m["wr1"] >= 6 and m["wr1_player"] is not None:
        lines.append(f"{m['wr1_player'].name} is their best player on offense — by a lot.")
    if m["rush"] >= 4:
        lines.append("Our rushers should beat their tackles.")
    if m["contain"] >= 12:
        lines.append("Their QB can hurt you with his legs.")
    if m["front"] >= 4:
        lines.append("They have speed outside. Don't give up the big one.")
    if not lines:
        lines.append("Pretty even matchup on film. No glaring edge either way.")
    return off, dfk, lines[:4]


def set_plan(team, year, week, off, dfk, script):
    team.game_plan = {"year": year, "week": week, "off": off, "def": dfk, "script": bool(script)}


def plan_of(team, year, week):
    gp = getattr(team, "game_plan", None) or {}
    if gp.get("year") == year and gp.get("week") == week:
        return gp
    return None


def _init_plan(sim, team):
    """This game's plan: yours from Friday if you made one, otherwise the staff's read."""
    opp = sim.other(team)
    try:
        m = matchup(team, opp)
    except Exception:
        return {"off": "balanced", "def": "balanced", "script": False, "mult": {}, "mine": False, "wr1": None}
    g = sim.game
    try:
        from season import league_year
        year = league_year()
    except Exception:
        year = None
    mine = plan_of(team, year, getattr(g, "week", None))
    if mine is not None:
        off, dfk, script = mine["off"], mine["def"], mine.get("script", False)
    else:
        off, dfk, _ = recommend(team, opp, m)
        iq = getattr(sim.plan[team], "iq", 0.6)
        r = random.Random(f"gp:{team.school}:{opp.school}:{getattr(g, 'week', 0)}")
        import difficulty
        if r.random() > 0.35 + 0.5 * iq + difficulty.read_vs(opp):  # a staff that reads film less well
            off = r.choice(list(OFF_KEYS))
            dfk = r.choice(list(DEF_KEYS))
        script = False
    prep = getattr(team, "week_prep", None) or {}
    sharp = 1.25 if prep.get("focus") == "gameplan" else 1.0
    mult = {off: fit(m.get(off, 0)) * sharp if off != "balanced" else 0.0,
            dfk: fit(m.get(dfk, 0)) * sharp if dfk != "balanced" else 0.0}
    return {"off": off, "def": dfk, "script": script, "mult": mult, "mine": mine is not None,
            "edge": {off: m.get(off, 0), dfk: m.get(dfk, 0)}}


# ═══ The state ═══════════════════════════════════════════════════════════════

class Sideline:
    """Everything the sideline adds to one game. Lives on the GameSim as `sl`."""

    def __init__(self, sim):
        self.orders = {t: {"off": "none", "def": "none", "feed": None} for t in sim.teams}
        self.gp = {}
        self.poise = {}             # player -> rating points (rattled / picked up)
        self.hobble = {}            # player -> rating points lost playing hurt
        self.padj = {}              # the sum, read by GameSim.prof
        self.hurt_through = {}      # player -> (games, desc) he's playing through
        self.late_only = {}         # player -> (games, desc): back in the fourth quarter if it's close
        self.benched = {}           # player -> drives count at which he's back (None = the day)
        self.challenges = {t: 1 for t in sim.teams}
        self.fakes = {t: 0 for t in sim.teams}
        self.onsides = {t: 0 for t in sim.teams}
        self.crowd = None           # team getting the crowd up this snap
        self.crowd_uses = 0
        self.tb = {t: 0.0 for t in sim.teams}
        self.lift = {t: 0.0 for t in sim.teams}      # leadership, timeouts
        self.explosive = {t: 0 for t in sim.teams}
        self.touches = {}           # fed player -> touches since the order
        self.log = []               # your calls, for the postgame
        self.pending = None         # a fourth-down call waiting on its result
        self.moments = 0            # leadership moments shown (pacing)
        self.moment_q = {}          # quarter -> shown
        self.queue = []             # people things waiting for the next headset stop
        self.drops = {}
        self.checked = {}           # side -> drive already checked in on
        self.whisper = [None, 0]
        self.asked_qb = set()
        self.wr1 = {}               # team -> their offense's best receiver (for the WR1 key)
        self.sacks = {t: 0 for t in sim.teams}

    def __getstate__(self):
        """A saved game keeps the log and the plan, not the per-snap working memory."""
        return {"log": self.log, "late_headset": self.__dict__.get("late_headset", False),
                "script": self.__dict__.get("script"), "credit": self.__dict__.get("credit"),
                "gp": {t: {k: v for k, v in g.items() if k in ("off", "def", "script", "mine")} for t, g in self.gp.items()}}

    def __setstate__(self, state):
        self.__dict__.update(state)


def attach(sim):
    sl = Sideline(sim)
    sim.sl = sl
    for t in sim.teams:
        sl.gp[t] = _init_plan(sim, t)
        try:
            m = matchup(sim.other(t), t)
            sl.wr1[t] = m.get("wr1_player")           # t's own best receiver
        except Exception:
            sl.wr1[t] = None
        if sl.gp[t]["script"]:
            sim.form[t] -= SCRIPT_COST
    return sl


def _sl(sim):
    return sim.__dict__.get("sl")


def _refresh(sl, p):
    v = sl.poise.get(p, 0.0) + sl.hobble.get(p, 0.0)
    if v:
        sl.padj[p] = v
    else:
        sl.padj.pop(p, None)


def set_poise(sim, p, v):
    sl = _sl(sim)
    if sl is None:
        return
    sl.poise[p] = max(-3.0, min(3.0, v))
    _refresh(sl, p)
    sim._prof.clear()


# ═══ Engine hooks (cheap when nothing is set) ════════════════════════════════

def pre_snap(sim):
    """Once per snap, before the play: the side-specific lifts."""
    sl = _sl(sim)
    if sl is None:
        return
    off, df = sim.offense, sim.defense
    tb = {t: sl.lift.get(t, 0.0) for t in sim.teams}
    gp = sl.gp.get(off)
    sl.scripted = None
    if gp and gp.get("script") and sim.plan[off].faced < 10 and sim.quarter <= 2:
        tb[off] += SCRIPT_LIFT
        sl.scripted = off                                          # for the postgame credit
    if sl.orders[off]["off"] == "tempo" and sim.drive is not None and sim.drive.get("plays", 0) >= 4:
        tb[df] -= min(1.2, 0.25 * (sim.drive["plays"] - 3))          # no subs, no breath
    if sl.crowd is df:
        tb[df] += 0.6 * max(0.3, 1 - 0.2 * (sl.crowd_uses - 1))
    if tb != sl.tb:
        sl.tb = tb
        sim._prof.clear()


def post_snap(sim):
    sl = _sl(sim)
    if sl is not None:
        sl.crowd = None


def team_boost(sim, team):
    sl = sim.__dict__.get("sl")
    return sl.tb.get(team, 0.0) if sl is not None else 0.0


def player_adj(sim, p):
    sl = sim.__dict__.get("sl")
    if sl is None or not sl.padj:
        return 0.0
    return sl.padj.get(p, 0.0)


def adjust(sim, call, dcall):
    """Standing orders that change the snap itself."""
    sl = _sl(sim)
    if sl is None:
        return call, dcall
    o = sl.orders[sim.offense]["off"]
    d = sl.orders[sim.defense]["def"]
    if o == "protect" and call.kind == "pass" and not call.screen and not call.rpo and call.protection < 6 \
            and call.passer == "QB" and call.name != "Hail Mary":
        call = replace(call, protection=6)
    if d != "none" and dcall.name not in ("Goal Line", "Prevent") and call.kind != "kneel":
        if d == "spy" and "spy" not in dcall.tags:
            dcall = replace(dcall, tags=dcall.tags + ("spy",), rush=dcall.rush - 1 if dcall.rush > 4 else dcall.rush)
        elif d == "two_deep":
            dcall = replace(dcall, shell=max(2, dcall.shell), box=max(5, dcall.box - 1))
        elif d == "load_box":
            dcall = replace(dcall, box=min(9, dcall.box + 1))
        elif d == "bracket" and "bracket" not in dcall.tags:
            dcall = replace(dcall, tags=dcall.tags + ("bracket",), shell=max(1, dcall.shell))
    return call, dcall


def _key_mult(sim, team, side, key):
    sl = _sl(sim)
    gp = sl.gp.get(team) if sl else None
    if not gp or gp[side] != key:
        return 0.0
    m = gp["mult"].get(key, 0.0)
    if side == "off" and key == "run" and sim.quarter >= 3:
        m *= 0.6
    return m


def pressure_time(sim):
    """Seconds added to (or taken off) the time before the rush gets home."""
    sl = _sl(sim)
    if sl is None:
        return 0.0
    off, df = sim.offense, sim.defense
    t = 0.0
    o, d = sl.orders[off]["off"], sl.orders[df]["def"]
    if o == "quick":
        t += 0.15
    elif o == "shots":
        t -= 0.05
    if d == "ears":
        t -= 0.22
    t += 0.05 * _key_mult(sim, off, "off", "quick")
    t -= 0.14 * _key_mult(sim, df, "def", "rush")
    return t


def read_need(sim):
    """How open a man has to look before the QB lets it go (quick game: sooner)."""
    sl = _sl(sim)
    if sl is None:
        return 0.0
    o = sl.orders[sim.offense]["off"]
    return -0.25 if o == "quick" else 0.2 if o == "shots" else 0.0


def sep_bonus(sim, rec, route):
    """Separation from orders and the game plan, for one route."""
    sl = _sl(sim)
    if sl is None:
        return 0.0
    off, df = sim.offense, sim.defense
    o, d = sl.orders[off]["off"], sl.orders[df]["def"]
    s = 0.0
    deep = route.area == "deep"
    if deep:
        if o == "quick":
            s -= 0.4                                   # he isn't waiting for it
        elif o == "shots":
            s += 0.2
        if d == "load_box":
            s += 0.4
        elif d == "two_deep":
            s -= 0.3
        s += 0.25 * _key_mult(sim, off, "off", "deep")
        s -= 0.25 * _key_mult(sim, df, "def", "front")
        s += 0.1 * _key_mult(sim, df, "def", "stop_run")
    elif route.area in SEP_SHORT:
        s += 0.12 * _key_mult(sim, df, "def", "front")
        if d == "two_deep":
            s += 0.15
    wr1 = sl.wr1.get(off)
    if wr1 is not None:
        k = _key_mult(sim, df, "def", "wr1")
        if k:
            s += -0.35 * k if rec is wr1 else 0.08 * k
    fed = sl.orders[off]["feed"]
    if fed is not None and rec is fed:
        n = sl.touches.get(fed, 0)
        s -= min(0.6, max(0, n - 5) * 0.12)               # they've figured out who's getting it
    return s


def run_bonus(sim, concept, carrier=None):
    """Log-odds for the blockers from orders and the game plan."""
    sl = _sl(sim)
    if sl is None:
        return 0.0
    off, df = sim.offense, sim.defense
    o, d = sl.orders[off]["off"], sl.orders[df]["def"]
    b = 0.0
    if o == "pound" and sim.drive is not None and sim.drive.get("plays", 0) >= 2:
        b += 0.12
    if d == "ears" and concept in ("draw", "counter", "trap", "qb_draw", "zone_read"):
        b += 0.35
    elif d == "two_deep":
        b += 0.12
    b += 0.06 * _key_mult(sim, off, "off", "run") + 0.03 * _key_mult(sim, off, "off", "control")
    b -= 0.12 * _key_mult(sim, df, "def", "stop_run")
    if concept in ("draw", "qb_draw"):
        b += 0.15 * _key_mult(sim, df, "def", "rush")
    if carrier is not None and carrier.position == "QB":
        b -= 0.25 * _key_mult(sim, df, "def", "contain")
    return b


def feature_role(sim, runners):
    """The role of the player you told them to feed, if he's running a route."""
    sl = _sl(sim)
    if sl is None:
        return None
    fed = sl.orders[sim.offense]["feed"]
    if fed is None:
        return None
    for role, (p, _) in runners.items():
        if p is fed:
            return role
    return None


def feature_rb(sim, team, rb):
    """Feed the back: he gets the carry (no rotation)."""
    sl = _sl(sim)
    if sl is None:
        return rb
    fed = sl.orders[team]["feed"]
    if fed is not None and fed in rb and rb[0] is not fed:
        rb = list(rb)
        rb.remove(fed)
        rb.insert(0, fed)
    return rb


def crowd_bump(sim):
    sl = _sl(sim)
    if sl is None or sl.crowd is None or sl.crowd is not sim.defense:
        return 0.0
    return 0.02 * max(0.3, 1 - 0.2 * (sl.crowd_uses - 1))


def staff_lean(sim):
    """What your orders and plan do to the staff's play calls: (run shift, family multipliers)."""
    sl = _sl(sim)
    if sl is None:
        return 0.0, {}
    off = sim.offense
    o = sl.orders[off]["off"]
    run, fam = 0.0, {}
    if o == "pound":
        run += 0.18
    elif o == "quick":
        fam = {"quick": 1.6, "screen": 1.3, "deep": 0.5, "play_action": 0.8}
    elif o == "shots":
        run -= 0.08
        fam = {"deep": 1.7, "play_action": 1.4, "quick": 0.7}
    elif o == "protect":
        fam = {"play_action": 1.3, "deep": 1.2, "screen": 0.7}
    k = sl.gp.get(off, {}).get("off")
    m = _key_mult(sim, off, "off", k) if k else 0.0
    if k == "run":
        run += 0.03 * m
    elif k == "control":
        run += 0.05 * m
    elif k == "deep":
        fam = dict(fam, deep=fam.get("deep", 1.0) * (1 + 0.25 * m))
    elif k == "quick":
        fam = dict(fam, quick=fam.get("quick", 1.0) * (1 + 0.25 * m))
    return run, fam


def def_lean(sim):
    """(blitz multiplier) from the defense's orders and plan."""
    sl = _sl(sim)
    if sl is None:
        return 1.0
    df = sim.defense
    b = 1.0
    if sl.orders[df]["def"] == "ears":
        b *= 1.25
    elif sl.orders[df]["def"] in ("spy", "two_deep"):
        b *= 0.8
    b *= 1 + 0.2 * _key_mult(sim, df, "def", "rush")
    return b


def tempo(sim):
    """'hurry' / 'milk' / None from the offense's orders and plan."""
    sl = _sl(sim)
    if sl is None:
        return None
    off = sim.offense
    if sl.orders[off]["off"] == "tempo":
        return "hurry"
    if sl.gp.get(off, {}).get("off") == "control" and sim.score[off] >= sim.score[sim.other(off)] and sim.quarter >= 2:
        return "milk"
    return None


def on_new_drive(sim):
    """Benched players come back when their series is up."""
    sl = _sl(sim)
    if sl is None or not sl.benched:
        return
    n = len(sim.drives)
    back = [p for p, until in sl.benched.items() if until is not None and n >= until]
    for p in back:
        del sl.benched[p]
    if back:
        for t in {sim.team_of(p) for p in back}:
            sim._rebuild_depth(t)


def is_benched(sim, p):
    sl = sim.__dict__.get("sl")
    return sl is not None and p in sl.benched


# ═══ Symmetric game events ═══════════════════════════════════════════════════

RATTLE = {"headcase": 2.0, "diva": 1.4, "hothead": 1.3, "cold": 0.2, "quiet_pro": 0.5, "captain": 0.6}


def rattle(sim, p, how_bad=1.0):
    """A bad play costs a player a little until somebody gets to him."""
    sl = _sl(sim)
    if sl is None or p is None:
        return
    m = 1.0
    for t in getattr(p, "traits", []) or []:
        m *= RATTLE.get(t, 1.0)
    if getattr(p, "year", 2) <= 0:
        m *= 1.3
    set_poise(sim, p, sl.poise.get(p, 0.0) - 1.2 * how_bad * m)


def after_snap(sim, r, before, off):
    """Every snap (both teams): tracking, rattles, the fourth-down log, the people moments."""
    sl = _sl(sim)
    if sl is None:
        return
    df = sim.other(off)
    if sl.__dict__.get("scripted") is off and not r.penalty:
        sc = sl.__dict__.setdefault("script", {})
        sc["snaps"] = sc.get("snaps", 0) + 1
        sc["yards"] = sc.get("yards", 0) + (r.yards if not r.turnover else 0)
        sc["firsts"] = sc.get("firsts", 0) + bool(r.td or (r.yards >= before[1] and not r.turnover))
        sc["td"] = sc.get("td", 0) + bool(r.td and not r.turnover)
        sc["to"] = sc.get("to", 0) + bool(r.turnover)
        sl.scripted = None
    if r.yards >= 20 and not r.penalty and not r.turnover:
        sl.explosive[off] += 1
    if getattr(r, "sack", False) and not r.penalty:
        sl.sacks[df] += 1
    fed = sl.orders[off]["feed"]
    if fed is not None and (r.carrier is fed or r.target is fed):
        sl.touches[fed] = sl.touches.get(fed, 0) + 1
    bad = None
    if not r.penalty:
        if r.turnover == "int" and r.passer is not None:
            bad = ("int", r.passer)
        elif r.turnover == "fumble" and r.carrier is not None:
            bad = ("fumble", r.carrier)
        elif r.inc_reason == "drop" and r.target is not None:
            n = sl.drops[r.target] = sl.drops.get(r.target, 0) + 1
            if n >= 2:
                bad = ("drops", r.target)
        elif (r.yards >= 40 or (r.td and r.kind == "pass" and r.yards >= 20)) and r.defender is not None \
                and r.kind == "pass":
            bad = ("burned", r.defender)
    else:
        name, team, yards, *_ = r.penalty
        p = getattr(r, "flag_player", None)
        costly = before[0] >= 3 or 100 - before[2] <= 20 or name == "Pass Interference"
        if p is not None and (costly or "hothead" in (getattr(p, "traits", []) or [])):
            bad = ("flag", p, name)
    if bad is not None:
        rattle(sim, bad[1], 1.0 if bad[0] in ("int", "fumble", "burned") else 0.7)
        team = sim.team_of(bad[1])
        ctl = sim.ctl
        if ctl is not None and team is ctl.team and active(ctl) and opt("sideline_people"):
            sl.queue.append((bad[0], bad[1], bad[2] if len(bad) > 2 else None))
        else:
            _staff_handles(sim, bad[1])
    _resolve_pending(sim, r, before, off)
    ctl = sim.ctl
    if ctl is not None and active(ctl) and sim.quarter >= 4 and sim.clock <= 180:
        sl.late_headset = True                       # you had it at the end: the clock was yours
    if ctl is not None and active(ctl) and sl.queue and opt("sideline_people"):
        people_moment(sim, ctl)


def _staff_handles(sim, p):
    """No head coach in the moment: a captain or a position coach gets to him."""
    sl = _sl(sim)
    if sl is None or p is None:
        return
    team = sim.team_of(p)
    cap = _captain(team, exclude=p)
    fix = 0.8 if cap is not None else 0.5
    set_poise(sim, p, min(0.0, sl.poise.get(p, 0.0) + fix))


def _captain(team, exclude=None):
    for c in getattr(team, "captains", None) or []:
        if c is not exclude:
            return c
    return None


# ═══ The headset: who's listening ════════════════════════════════════════════

def active(ctl):
    """You have the headset right now (not handed to the staff, and in the moment)."""
    return ctl is not None and ctl.auto_until is None and (ctl.mode == "full" or ctl.in_moment)


def _staff_name(team, side):
    c = getattr(team, "oc" if side == "off" else "dc", None)
    if c is None:
        return "Staff"
    return ("OC " if side == "off" else "DC ") + c.name.split()[-1]


def _k(key, label, color=C.BYELLOW):
    return f"{paint('[' + key + ']', color, C.BOLD)} {label}"


def _clock(sec):
    return f"{sec // 60}:{sec % 60:02d}"


def _qc(sim):
    return (f"Q{sim.quarter}" if sim.quarter <= 4 else "OT") + " " + _clock(sim.clock)


def _log(sim, kind, text, staff=None, yours=None, chart=None, result=None, weight=1.0):
    sl = _sl(sim)
    if sl is None:
        return None
    e = {"q": sim.quarter, "clock": sim.clock, "kind": kind, "text": text, "staff": staff, "yours": yours,
         "chart": chart, "result": result, "weight": weight,
         "score": (sim.score[sim.ctl.team], sim.score[sim.other(sim.ctl.team)]) if sim.ctl else None}
    sl.log.append(e)
    return e


def _price(e, values, pick, words=None):
    """Put what every option was worth (win chance) on a log entry, for the grade."""
    if e is None:
        return
    try:
        vals = values()
    except Exception:
        return
    if pick not in vals:
        return
    e["vals"], e["pick"] = vals, pick
    if words:
        e["words"] = words


# ═══ The tablet ══════════════════════════════════════════════════════════════

FAM_SAY = {"run_inside": "Inside runs are", "run_outside": "Outside runs are", "screen": "The screens are",
           "quick": "The quick game is", "intermediate": "The intermediate stuff is", "deep": "The deep ball is",
           "play_action": "Play action is"}
FAM_WORDS = {"run_inside": "inside runs", "run_outside": "outside runs", "screen": "screens", "quick": "quick game",
             "intermediate": "intermediate throws", "deep": "deep shots", "play_action": "play action"}
SIT_WORDS = {"1st": "1st down", "2nd_long": "2nd & long", "2nd_short": "2nd & short", "3rd_long": "3rd & long",
             "3rd_short": "3rd & short", "red": "red zone"}


def momentum_bar(sim, team, width=21):
    m = sim.momentum
    v = m.value if team is sim.home else -m.value           # + = ours
    pos = int(round((v + 100) / 200 * (width - 1)))
    cells = []
    for i in range(width):
        if i == pos:
            cells.append(paint("●", C.BWHITE, C.BOLD))
        elif i < width // 2:
            cells.append(paint("━", C.BRED if i >= pos else C.GRAY))
        elif i > width // 2:
            cells.append(paint("━", C.BGREEN if i <= pos else C.GRAY))
        else:
            cells.append(paint("┃", C.GRAY))
    word = ("all ours" if v >= 55 else "ours" if v >= 15 else "all theirs" if v <= -55 else "theirs" if v <= -15
            else "even")
    col = C.BGREEN if v >= 15 else C.BRED if v <= -15 else C.GRAY
    return "them " + "".join(cells) + " us  " + paint(word, col, C.BOLD)


def crowd_words(sim, team):
    m = sim.momentum
    if m.neutral:
        return "neutral site"
    home = sim.home is team
    n = m.noise
    loud = "deafening" if n >= 1.15 else "loud" if n >= 0.9 else "into it" if n >= 0.6 else "quiet"
    if home:
        return f"our crowd: {loud}"
    return f"their crowd: {loud}"


def _line_of(sim, p):
    c = sim.stats.get(p) or {}
    if p.position == "QB":
        s = f"{c.get('pass_cmp', 0)}-{c.get('pass_att', 0)}, {c.get('pass_yds', 0)}"
        if c.get("pass_td"):
            s += f", {c['pass_td']} TD"
        if c.get("pass_int"):
            s += f", {c['pass_int']} INT"
        if c.get("rush_yds", 0) >= 20:
            s += f" · {c['rush_yds']} rush"
        return s
    if c.get("rush_att", 0) >= c.get("rec", 0):
        s = f"{c.get('rush_att', 0)} car, {c.get('rush_yds', 0)} yds"
    else:
        s = f"{c.get('rec', 0)} rec, {c.get('rec_yds', 0)} yds"
    if c.get("fumbles"):
        s += f", {c['fumbles']} fum"
    return s


def hot_cold(sim, team):
    """(hot player, cold player) among the skill guys today."""
    best, worst = None, None
    bv, wv = 0.0, 0.0
    for p, c in sim.stats.items():
        if sim.team_of(p) is not team or p.position not in ("QB", "RB", "WR", "TE"):
            continue
        if p.position == "QB":
            att = c.get("pass_att", 0)
            if att < 6:
                continue
            v = (c.get("pass_yds", 0) + 20 * c.get("pass_td", 0) - 45 * c.get("pass_int", 0)) / att - 6.5
            v *= 3
        else:
            touches = c.get("rush_att", 0) + c.get("rec", 0) + c.get("targets", 0) * 0.5
            if touches < 3:
                continue
            yds = c.get("rush_yds", 0) + c.get("rec_yds", 0)
            v = yds / max(1, c.get("rush_att", 0) + c.get("targets", 0)) - 5 - 12 * c.get("fumbles", 0) / touches
            v += 0.02 * yds
        if v > bv:
            best, bv = p, v
        if v < wv:
            worst, wv = p, v
    return (best if bv >= 2.5 else None), (worst if wv <= -2.5 else None)


def _fam_line(plan):
    good, bad = [], []
    for fam, (n, ok, yds) in sorted(plan.fam.items(), key=lambda x: -x[1][0]):
        if n < 3:
            continue
        rate = ok / n
        if rate >= 0.6:
            good.append(f"{FAM_WORDS.get(fam, fam)} {ok}/{n}")
        elif rate <= 0.3:
            bad.append(f"{FAM_WORDS.get(fam, fam)} {ok}/{n}")
    return good[:2], bad[:2]


def _def_line(plan):
    good, bad = [], []
    for fam, (n, yds, big) in sorted(plan.fam_allowed.items(), key=lambda x: -x[1][0]):
        if n < 3:
            continue
        avg = yds / n
        if avg <= 3.5 and big == 0:
            good.append(f"vs {FAM_WORDS.get(fam, fam)} {avg:.1f}/play")
        elif avg >= 7.5 or big >= 2:
            bad.append(f"{FAM_WORDS.get(fam, fam)} {avg:.1f}/play" + (f", {big} big" if big else ""))
    return good[:2], bad[:2]


def _looks(plan, sit):
    lk = getattr(plan, "looks", {}).get(sit)
    if not lk or lk[0] < 4:
        return None
    return lk


def _scheme_play(team, names):
    """The first of these plays your offense actually has in its book."""
    import staff
    import playbook as pb
    book = pb.OFFENSE_SCHEMES[staff.play_caller(team, "off").offense_scheme]["plays"]
    for n in names:
        if n in book:
            return n
    return names[0]


def whispers(sim, team, side):
    """What the coordinator says: [(priority, key, text)], best first."""
    import playbook as pb
    out = []
    opp = sim.other(team)
    plan, their = sim.plan[team], sim.plan[opp]
    sit = pb.situation(sim.down, sim.togo, sim.yardline)
    sw = SIT_WORDS.get(sit, sit)
    if side == "off":
        if sim.quarter == 2 and sim.clock <= 45 and sim.yardline < 60:
            if pb.should_kneel(sim) or sim.yardline < 25:
                out.append((9, "eoh", f"{_clock(sim.clock)} left, we're backed up. I'd take a knee and go in."))
            else:
                out.append((9, "eoh", f"{_clock(sim.clock)} and {sim.timeouts[team]} timeouts. Worth a shot or two."))
        lk = _looks(plan, sit)
        if lk:
            n, blz, man, two, box = lk
            if blz / n >= 0.5:
                pl = _scheme_play(team, ["Slants", "Bubble Screen", "RB Screen", "Quick Outs", "Stick"])
                out.append((8, "blitz:" + sit, f"They've sent pressure on {sw} {blz} of {n}. {pl} beats it."))
            elif man / n >= 0.65:
                pl = _scheme_play(team, ["Mesh", "Shallow Cross", "Double Moves", "Slants"])
                out.append((6, "man:" + sit, f"Man coverage on {sw}, {man} of {n}. Crossers beat it: {pl}."))
            elif two / n >= 0.6:
                out.append((6, "two:" + sit, f"Two high on {sw}, {two} of {n}. Run it, or hit the middle."))
            elif box / n >= 0.5:
                pl = _scheme_play(team, ["PA Boot", "Glance RPO", "PA Leak", "Pop Pass RPO", "Slants"])
                out.append((7, "box:" + sit, f"Eight in the box on {sw} ({box} of {n}). {pl} off it."))
        good, bad = _fam_line(plan)
        best = max(((f, r) for f, r in plan.fam.items() if r[0] >= 3 and r[1] / r[0] >= 0.6),
                   key=lambda x: x[1][1] / x[1][0], default=None)
        if best:
            out.append((4, "good:" + best[0], f"{FAM_SAY.get(best[0], best[0])} there all day. Keep going back to it."))
        worst = min(((f, r) for f, r in plan.fam.items() if r[0] >= 4 and r[1] / r[0] <= 0.25),
                    key=lambda x: x[1][1] / x[1][0], default=None)
        if worst:
            out.append((5, "bad:" + worst[0], f"{FAM_SAY.get(worst[0], worst[0])} getting us nowhere — "
                                              f"{worst[1][1]} for {worst[1][0]}. Go away from it."))
        tend = plan.tendency(sit)
        if tend is not None and sit in ("1st", "2nd_long", "2nd_short"):
            rec = plan.sit_self.get(sit, [0, 0])
            if tend >= 0.75:
                out.append((7, "tend", f"We've run on {sw} {rec[0]} of {rec[1]}. They know it — they're creeping up."))
            elif tend <= 0.25:
                out.append((7, "tend", f"We've thrown on {sw} {rec[1] - rec[0]} of {rec[1]}. A run here catches them."))
        for _, key, _d in reversed(their.notes[-4:]):
            said = {"load_box": "Their DC just brought a safety down. The box is loaded.",
                    "two_high": "They've gone two-deep. They're done getting beat over the top.",
                    "bracket": "They're doubling our best receiver now.",
                    "blitz_more": "Their blitzes are working and they know it. More coming.",
                    "blitz_less": "They've backed off the blitz."}.get(key)
            if said:
                out.append((5, "their:" + key, said))
                break
        if plan.sacks_taken >= 3:
            out.append((6, "sacks", f"That's {plan.sacks_taken} sacks. Get the ball out or keep a back in."))
    else:
        rr = plan.opp_run_rate(sit)
        rec = plan.sit_opp.get(sit)
        if rr is not None and rec and rec[1] >= 5:
            if rr >= 0.7:
                out.append((7, "orun:" + sit, f"They've run it on {sw} {rec[0]} of {rec[1]}. Load the box."))
            elif rr <= 0.25:
                out.append((7, "opass:" + sit, f"They've thrown on {sw} {rec[1] - rec[0]} of {rec[1]}. Drop into coverage."))
        if plan.deep_trouble():
            out.append((8, "deep", "They're beating us over the top. We need two deep."))
        elif plan.run_trouble():
            out.append((8, "runs", "They're running right through us. We need an extra man in the box."))
        v = plan.blitz_verdict()
        if v == 1:
            out.append((5, "bl+", "The pressure's getting home. Keep sending it."))
        elif v == -1:
            out.append((6, "bl-", "Our blitzes are getting burned. Back off."))
        qb = sim.qb_of(opp)
        qc = sim.stats.get(qb) or {}
        if qc.get("rush_yds", 0) >= 35:
            out.append((6, "spy", f"{qb.last_name} has {qc['rush_yds']} yards with his legs. Spy him."))
        hot, _ = hot_cold(sim, opp)
        if hot is not None and hot.position in ("WR", "TE") and (sim.stats.get(hot) or {}).get("rec_yds", 0) >= 70:
            out.append((6, "hot", f"{hot.last_name} is killing us. Put two on him."))
        for _, key, _d in reversed(their.notes[-4:]):
            said = {"quick_game": "Their OC's gone to the quick game. Our rush got to him.",
                    "abandon_run": "They've given up on the run.",
                    "lean_run": "They're leaning on the run — it's working for them.",
                    "lean_pass": "They're throwing it more. The run wasn't there.",
                    "beat_box": "They see the loaded box. Expect play action."}.get(key)
            if said:
                out.append((5, "their:" + key, said))
                break
    out.sort(key=lambda x: -x[0])
    return out


def pick_whisper(sim, team, side):
    sl = _sl(sim)
    ws = whispers(sim, team, side)
    if not ws:
        return None
    last, n = sl.whisper
    for pri, key, text in ws:
        if key == last and n >= 3:
            continue
        sl.whisper = [key, n + 1 if key == last else 1]
        return text
    return ws[0][2]


def tablet(sim, ctl, side):
    """The lines under the call header."""
    for ln in tablet_rows(sim, ctl, side):
        print(ln)


def tablet_rows(sim, ctl, side):
    """The tablet's lines, as a list (the tablet view lays them out itself)."""
    if not opt("sideline_tablet"):
        return []
    sl = _sl(sim)
    if sl is None:
        return []
    team = ctl.team
    opp = sim.other(team)
    plan = sim.plan[team]
    out = []
    crowd = crowd_words(sim, team)
    extra = ""
    if side == "def" and sim.home is team and not sim.momentum.neutral and sim.down >= 3:
        extra = "  " + paint("[C] get them up", C.BYELLOW)
    out.append("   " + momentum_bar(sim, team) + paint(f"   ·   {crowd}", C.GRAY) + extra)
    d = sim.drive or {}
    if d and d.get("plays", 0):
        yds = sim.yardline - d.get("start", sim.yardline)
        t = sim.team_stats[d["team"]]["top"] - d.get("top0", 0)
        who = "This drive" if side == "off" else "Their drive"
        dl = f"{who}: {d.get('plays', 0)} plays, {yds} yds, {_clock(max(0, t))}"
    else:
        dl = ""
    o = sl.orders[team]
    ords = OFF_ORDERS[o["off"]][0] if side == "off" else DEF_ORDERS[o["def"]][0]
    if side == "off" and o["feed"] is not None:
        ords += f" · feed {o['feed'].last_name}"
    ch = sl.challenges.get(team, 0)
    out.append("   " + paint(dl, C.GRAY) + ("   ·   " if dl else "") + paint("Orders: ", C.GRAY)
               + paint(ords, C.BWHITE if ords != "Normal" else C.GRAY) + paint(f"   ·   challenge: {'yes' if ch else 'used'}", C.GRAY))
    if side == "off":
        good, bad = _fam_line(plan)
    else:
        good, bad = _def_line(plan)
    if good or bad:
        seg = []
        if good:
            seg.append(paint("working: ", C.GRAY) + paint(" · ".join(good), C.BGREEN))
        if bad:
            seg.append(paint("not: " if side == "off" else "hurting us: ", C.GRAY) + paint(" · ".join(bad), C.BRED))
        out.append("   " + "   ".join(seg))
    import playbook as pb
    sit = pb.situation(sim.down, sim.togo, sim.yardline)
    if side == "off":
        lk = _looks(plan, sit)
        if lk:
            n, blz, man, two, box = lk
            bits = [f"blitz {blz} of {n}", f"man {man} of {n}"]
            if two:
                bits.append(f"two-deep {two}")
            if box:
                bits.append(f"8 in the box {box}")
            out.append("   " + paint(f"Their D on {SIT_WORDS.get(sit, sit)}: ", C.GRAY) + " · ".join(bits))
    else:
        rec = plan.sit_opp.get(sit)
        fams = getattr(plan, "opp_fam_sit", {}).get(sit)
        if rec and rec[1] >= 4:
            bits = [f"run {rec[0]} of {rec[1]}"]
            if fams:
                top = max(fams, key=fams.get)
                bits.append(f"mostly {FAM_WORDS.get(top, top)}")
            out.append("   " + paint(f"Their O on {SIT_WORDS.get(sit, sit)}: ", C.GRAY) + " · ".join(bits))
    w = pick_whisper(sim, team, side)
    if w:
        out.append("   " + paint(_staff_name(team, side) + ": ", C.BCYAN, C.BOLD) + paint(f"\"{w}\"", C.BCYAN))
    hot, cold = hot_cold(sim, team if side == "off" else opp)
    bits = []
    lab = "" if side == "off" else "their "
    if hot is not None:
        bits.append(paint(f"{lab}hot: ", C.GRAY) + paint(f"{hot.position} {hot.last_name} {_line_of(sim, hot)}",
                                                         C.BGREEN if side == "off" else C.BRED))
    if cold is not None:
        bits.append(paint(f"{lab}cold: ", C.GRAY) + paint(f"{cold.position} {cold.last_name} {_line_of(sim, cold)}",
                                                          C.BRED if side == "off" else C.BGREEN))
    hurt = [p for p in sl.hobble if sim.team_of(p) is team]
    if hurt:
        bits.append(paint("playing hurt: " + ", ".join(p.last_name for p in hurt[:2]), C.BYELLOW))
    if bits:
        out.append("   " + "   ".join(bits))
    v = sim.momentum.value if sim.home is team else -sim.momentum.value
    if v <= -45 and sim.timeouts[team] and sim.quarter <= 4:
        out.append("   " + paint("The building's turned on you. A timeout now would settle it down.", C.BYELLOW))
    return out


# ═══ Series check-ins ════════════════════════════════════════════════════════

def _last_drive_words(d, team):
    if d is None:
        return None
    who = "Our" if d["team"] is team else "Their"
    res = d.get("result", "")
    return f"{who} last series: {d.get('plays', 0)} plays, {d.get('yards', 0)} yds — {res.lower()}."


def maybe_checkin(sim, ctl, side):
    """At the first headset stop of a new series. Returns nothing; may change orders."""
    sl = _sl(sim)
    if sl is None or sim.drive is None:
        return
    key = id(sim.drive)
    if sl.checked.get(side) == key:
        return
    sl.checked[side] = key
    if sim.quarter > 4 or sim.drive.get("plays", 0) > 0:
        return                                   # only between series, not in the middle of a drive
    mode = opt("sideline_checkins")
    if mode == "off":
        return
    team = ctl.team
    issues = _player_issues(sim, team) if side == "off" else []
    ws = whispers(sim, team, side)
    last = sim.drives[-1] if sim.drives else None
    seen = sl.__dict__.setdefault("heard", set())
    fresh = [w for w in ws if w[0] >= 6 and w[1] not in seen and w[1] != "eoh"]
    bad_news = last is not None and (last.get("result") in ("Interception", "Fumble", "Downs", "Safety")
                                     or (last.get("result") == "Touchdown" and last["team"] is not team))
    half_start = (side, 1 if sim.quarter <= 2 else 2) not in sl.__dict__.get("plan_shown", set())
    notable = bool(issues) or bool(fresh) or bad_news or half_start
    for w in fresh:
        seen.add(w[1])
    if mode == "notable" and not notable:
        return
    checkin(sim, ctl, side, issues=issues, ws=ws, last=last)


def checkin(sim, ctl, side, issues=None, ws=None, last=None):
    sl = _sl(sim)
    team = ctl.team
    if issues is None:
        issues = _player_issues(sim, team) if side == "off" else []
    if ws is None:
        ws = whispers(sim, team, side)
    print()
    title = "OFFENSE · BETWEEN SERIES" if side == "off" else "DEFENSE · BETWEEN SERIES"
    print(paint("   ┌─ " + title + " " + "─" * max(4, 60 - len(title)), C.BCYAN))
    lw = _last_drive_words(last, team)
    if lw:
        print(paint("   │ " + lw, C.GRAY))
    gp = sl.gp.get(team)
    half = 1 if sim.quarter <= 2 else 2
    shown = sl.__dict__.setdefault("plan_shown", set())
    first = (side, half) not in shown
    shown.add((side, half))
    if gp and first:
        key = gp["off"] if side == "off" else gp["def"]
        table = OFF_KEYS if side == "off" else DEF_KEYS
        whose = "your" if gp.get("mine") else "the staff's"
        extra = " · openers scripted" if side == "off" and gp.get("script") and sim.quarter <= 2 else ""
        print(paint("   │ ", C.BCYAN) + paint(f"Game plan ({whose}): ", C.GRAY) + paint(table[key][0], C.BWHITE, C.BOLD)
              + paint(f" — {table[key][1]}{extra}", C.GRAY))
    who = _staff_name(team, side)
    shown = 0
    for pri, k, text in ws:
        if k == "eoh" or k.startswith(("blitz:", "man:", "two:", "box:", "orun:", "opass:")) and shown:
            continue
        print(paint("   │ ", C.BCYAN) + paint(who + ": ", C.BCYAN, C.BOLD) + paint(f"\"{text}\"", C.BCYAN))
        shown += 1
        if shown >= 2:
            break
    if not shown:
        print(paint("   │ ", C.BCYAN) + paint(who + ": ", C.BCYAN, C.BOLD) + paint("\"Nothing new. Plan's sound.\"", C.BCYAN))
    for text in issues:
        print(paint("   │ ", C.BCYAN) + paint(text, C.BYELLOW))
    orders_menu(sim, ctl, side, issues=bool(issues))
    print(paint("   └" + "─" * 64, C.BCYAN))


def orders_menu(sim, ctl, side, issues=False):
    sl = _sl(sim)
    team = ctl.team
    o = sl.orders[team]
    table = OFF_ORDERS if side == "off" else DEF_ORDERS
    keys = list(table)
    cur = o["off"] if side == "off" else o["def"]
    rec = _recommend_order(sim, team, side)
    cells = []
    for i, k in enumerate(keys, 1):
        label = table[k][0]
        tag = paint("*", C.BGREEN, C.BOLD) if k == cur else " "
        star = paint(" ←", C.BCYAN) if k == rec and k != cur else ""
        cells.append(f"{paint(f'[{i}]', C.BYELLOW, C.BOLD)}{tag}{label}{star}")
    from ui import visible_len
    import re as _re
    vis = lambda x: visible_len(_re.sub(r"\x1b\[[0-9;]*m", "", x))
    row, rows = [], []
    for c in cells:                                  # as many orders per line as fit inside the 100 columns
        if row and vis("   │ " + "  ".join(row + [c])) > 96:
            rows.append(row)
            row = []
        row.append(c)
    if row:
        rows.append(row)
    for r in rows:
        print(paint("   │ ", C.BCYAN) + "  ".join(r))
    extra = []
    if side == "off":
        extra.append(_k("F", "feed a player" + (f" (now: {o['feed'].last_name})" if o["feed"] else "")))
        if issues or _qb_options(sim, team):
            extra.append(_k("Q", "the quarterback"))
    extra.append(_k("?", "what they do"))
    extra.append(_k("Enter", "go", C.BGREEN))
    print(paint("   │ ", C.BCYAN) + "   ".join(extra) + paint(f"   (* now · ← staff)", C.GRAY))
    while True:
        c = ask("Orders:").strip().lower()
        if c == "":
            return
        if c == "?":
            for k in keys:
                print(paint(f"   │   {table[k][0]:<22}", C.BWHITE) + paint(table[k][1], C.GRAY))
            continue
        if c.isdigit() and 1 <= int(c) <= len(keys):
            k = keys[int(c) - 1]
            o["off" if side == "off" else "def"] = k
            sim._prof.clear()
            print(paint(f"   → {table[k][0]}. {table[k][1].capitalize()}.", C.BYELLOW))
            _log(sim, "orders", f"{'Offense' if side == 'off' else 'Defense'}: {table[k][0]}")
            continue
        if c == "f" and side == "off":
            feed_menu(sim, ctl)
            continue
        if c == "q" and side == "off":
            qb_menu(sim, ctl)
            continue
        print(paint("   A number, F, Q, ? or Enter.", C.GRAY))


def _recommend_order(sim, team, side):
    plan = sim.plan[team]
    if side == "off":
        if plan.sacks_taken >= 3:
            return "protect"
        if plan.heavy_box_rate() > 0.45:
            return "shots"
        if plan.blitz_rate() > 0.45:
            return "quick"
        lean = plan.run_lean()
        if lean >= 0.08:
            return "pound"
        return "none"
    if plan.deep_trouble():
        return "two_deep"
    if plan.run_trouble():
        return "load_box"
    opp = sim.other(team)
    qc = sim.stats.get(sim.qb_of(opp)) or {}
    if qc.get("rush_yds", 0) >= 35:
        return "spy"
    hot, _ = hot_cold(sim, opp)
    if hot is not None and hot.position in ("WR", "TE") and (sim.stats.get(hot) or {}).get("rec_yds", 0) >= 80:
        return "bracket"
    if plan.blitz_verdict() == 1:
        return "ears"
    return "none"


def feed_menu(sim, ctl):
    sl = _sl(sim)
    team = ctl.team
    d = sim.depth[team]
    cands = [p for p in d["RB"][:2] + d["WR"][:4] + d["TE"][:1] if p is not None]
    seen = []
    for p in cands:
        if p not in seen:
            seen.append(p)
    hot, _ = hot_cold(sim, team)
    for i, p in enumerate(seen, 1):
        tag = paint("  ← hot", C.BGREEN) if p is hot else ""
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(p.position + ' ' + p.name, 26)} "
              f"{paint(_line_of(sim, p) if sim.stats.get(p) else 'no touches yet', C.GRAY)}{tag}")
    print(f"   {paint('[0]', C.BYELLOW, C.BOLD)} nobody in particular")
    c = ask("Feed who? (Enter = no change):").strip()
    if c == "0":
        sl.orders[team]["feed"] = None
        print(paint("   → Spread it around.", C.BYELLOW))
    elif c.isdigit() and 1 <= int(c) <= len(seen):
        p = seen[int(c) - 1]
        sl.orders[team]["feed"] = p
        sl.touches[p] = 0
        print(paint(f"   → Get {p.last_name} the ball. (Keep it up and they'll key on him.)", C.BYELLOW))
        _log(sim, "feed", f"Fed {p.position} {p.name}")


# ── players ──────────────────────────────────────────────────────────────────

def _player_issues(sim, team):
    sl = _sl(sim)
    out = []
    qb = sim.depth[team]["QB"][0]
    c = sim.stats.get(qb) or {}
    ints = c.get("pass_int", 0)
    att = c.get("pass_att", 0)
    lvl = 2 if ints >= 3 else 1 if ints >= 2 or (att >= 14 and c.get("pass_cmp", 0) / att < 0.4) else 0
    if lvl and (qb, lvl) not in sl.asked_qb and len(sim.depth[team]["QB"]) > 1:
        sl.asked_qb.add((qb, lvl))
        why = f"{ints} picks" if ints >= 2 else f"{c.get('pass_cmp', 0)} of {att}"
        out.append(f"QB coach: \"{qb.last_name}'s got {why}. [Q] if you want to make a change.\"")
    starter = _benched_starter(sim, team)
    if starter is not None and sl.benched.get(starter) is None and (starter, "back") not in sl.asked_qb \
            and sim.quarter >= 3:
        sl.asked_qb.add((starter, "back"))
        out.append(f"QB coach: \"{starter.last_name} says he's ready. [Q] to put him back in.\"")
    return out


def _benched_starter(sim, team):
    sl = _sl(sim)
    for p in sl.benched:
        if sim.team_of(p) is team and p.position == "QB":
            return p
    return None


def _qb_options(sim, team):
    return len(sim.depth[team]["QB"]) > 1 or _benched_starter(sim, team) is not None


def qb_menu(sim, ctl):
    sl = _sl(sim)
    team = ctl.team
    qb = sim.depth[team]["QB"][0]
    back = _benched_starter(sim, team)
    nxt = sim.depth[team]["QB"][1] if len(sim.depth[team]["QB"]) > 1 else None
    print(f"   {paint('QB:', C.GRAY)} {qb.name} — {_line_of(sim, qb) if sim.stats.get(qb) else 'no throws yet'}")
    opts = []
    if back is not None:
        opts.append(("b", f"put {back.last_name} back in"))
    if nxt is not None and back is None:
        opts += [("1", f"{nxt.last_name} for a series"), ("2", f"{nxt.last_name} the rest of the day")]
    for k, t in opts:
        print(f"   {_k(k.upper(), t)}")
    c = ask("The quarterback (Enter = stick with him):").strip().lower()
    import morale
    if c == "b" and back is not None:
        del sl.benched[back]
        sim._rebuild_depth(team)
        morale.nudge(back, 1)
        print(paint(f"   → {back.last_name} is back in.", C.BYELLOW))
        _log(sim, "qb", f"Put {back.name} back in", result=None)
    elif c in ("1", "2") and nxt is not None and back is None:
        sl.benched[qb] = len(sim.drives) + 2 if c == "1" else None
        sim._rebuild_depth(team)
        morale.nudge(qb, -1 if c == "1" else -4, "benched in a game")
        set_poise(sim, qb, sl.poise.get(qb, 0.0) + 0.8)          # a series to breathe
        print(paint(f"   → {nxt.last_name} is in{' for a series' if c == '1' else ''}. "
                    f"{qb.last_name} {'takes a seat' if c == '1' else 'is done for the day'}.", C.BYELLOW))
        _log(sim, "qb", f"Benched QB {qb.name} " + ("for a series" if c == "1" else "for the game"),
             result=f"{nxt.last_name} in")
    elif ctl is not None:
        if sim.stats.get(qb, {}).get("pass_int", 0) >= 2:
            morale.nudge(qb, 1)
            _log(sim, "qb", f"Stuck with QB {qb.name}")


# ── leadership moments ──────────────────────────────────────────────────────

FACE_WORKS = {"gamer", "underdog", "warrior", "workhorse", "captain", "closer_p", "tone_setter", "grinder"}
FACE_BACKFIRES = {"headcase", "diva", "hothead", "spotlight", "impatient"}
ARM_WORKS = {"headcase", "diva", "family_guy", "humble", "loyal"}
ARM_WASTED = {"cold", "quiet_pro"}

WHAT = {"int": "threw a pick", "fumble": "put it on the ground", "drops": "has dropped two",
        "burned": "got beat deep", "flag": "drew a flag"}


def people_moment(sim, ctl):
    """The sideline after something went wrong: go talk to him."""
    sl = _sl(sim)
    while sl.queue:
        item = sl.queue.pop(0)
        kind, p, flag = item
        q = sim.quarter
        if sl.moment_q.get(q, 0) >= 2 or sl.moments >= 6:
            _staff_handles(sim, p)
            continue
        sl.moment_q[q] = sl.moment_q.get(q, 0) + 1
        sl.moments += 1
        traits = [t for t in (getattr(p, "traits", []) or [])]
        from traits import PLAYER_TRAITS
        what = WHAT[kind] + (f" ({flag.lower()})" if flag else "")
        print()
        print(paint("   ┌─ ON THE SIDELINE " + "─" * 46, C.BMAGENTA))
        after = {"int": "He's walking off with his head down.", "fumble": "He's walking off with his head down.",
                 "flag": "He's looking over at the sideline. He knows.", "burned": "He's jogging off, hands on his helmet.",
                 "drops": "He's staring at his hands."}[kind]
        print(paint("   │ ", C.BMAGENTA) + paint(f"{p.position} {p.name}", C.BWHITE, C.BOLD) + f" {what}. {after}")
        read = None
        for t in traits:
            if t in FACE_WORKS | FACE_BACKFIRES | ARM_WORKS | ARM_WASTED and t in PLAYER_TRAITS:
                read = f"{PLAYER_TRAITS[t][0]} — {PLAYER_TRAITS[t][1].lower()}."
                break
        yr = ("true freshman", "sophomore", "junior", "senior")[max(0, min(3, getattr(p, "year", 2)))]
        coach = "Position coach"
        plain = sim.rng.choice(("He'll bounce back.", "This isn't him — he's been steady all year.",
                                "Doesn't say much. Takes it hard.", "He's never been in a spot like this."))
        print(paint("   │ ", C.BMAGENTA) + paint(f"{coach}: ", C.BCYAN, C.BOLD)
              + paint(f"\"He's a {yr}. " + (read if read else plain) + "\"", C.BCYAN))
        cap = _captain(sim.team_of(p), exclude=p)
        opts = [("1", "put an arm around him"), ("2", "get in his face")]
        opts.append(("3", f"let {cap.last_name} handle it" if cap is not None else "let his teammates handle it"))
        can_sit = kind in ("fumble", "drops", "flag", "burned") and _can_bench(sim, p)
        if can_sit:
            opts.append(("4", "sit him a series"))
        print(paint("   │ ", C.BMAGENTA) + "   ".join(_k(k, t) for k, t in opts))
        c = ask("What do you do? (Enter = let it go):").strip()
        res = react(sim, ctl, p, c, kind, cap)
        print(paint("   │ ", C.BMAGENTA) + paint(res, C.BYELLOW))
        print(paint("   └" + "─" * 64, C.BMAGENTA))


def _can_bench(sim, p):
    team = sim.team_of(p)
    room = sim.depth[team].get(p.position, [])
    return p.position not in ("QB", "K", "P") and len(room) > {"RB": 1, "WR": 3, "TE": 1, "OL": 5, "DL": 4,
                                                              "LB": 3, "CB": 2, "S": 2}.get(p.position, 1)


def react(sim, ctl, p, c, kind, cap):
    sl = _sl(sim)
    import morale
    traits = set(getattr(p, "traits", []) or [])
    rng = sim.rng
    young = getattr(p, "year", 2) <= 1
    cur = sl.poise.get(p, 0.0)
    coach_tr = set(getattr(ctl.team.coach, "traits", []) or [])
    name = p.last_name
    if c == "1":
        gain = 1.3 + (0.9 if young or traits & ARM_WORKS else 0) - (0.9 if traits & ARM_WASTED else 0)
        set_poise(sim, p, cur + gain)
        morale.nudge(p, 1)
        out = (f"{name} nods. He needed that." if gain >= 1.8 else
               f"{name} shrugs it off — he didn't need the hug, but it didn't hurt." if gain < 1 else
               f"{name} takes a breath. He's back.")
        f_odds = max(0.1, min(0.9, 0.55 + (0.25 if traits & FACE_WORKS else 0) - (0.4 if traits & FACE_BACKFIRES else 0)
                              + (0.1 if coach_tr & {"motivator", "players_coach"} else 0) - (0.1 if young else 0)))
        face = f_odds * 2.4 - (1 - f_odds) * 1.1
        _log(sim, "people", f"Arm around {p.position} {p.name} after he {WHAT[kind]}", result=out,
             chart="good" if gain >= face - 0.35 else "bad", weight=0.3)
        return out
    if c == "2":
        odds = 0.55 + (0.25 if traits & FACE_WORKS else 0) - (0.4 if traits & FACE_BACKFIRES else 0) \
            + (0.1 if coach_tr & {"motivator", "players_coach"} else 0) - (0.1 if young else 0)
        if rng.random() < max(0.1, min(0.9, odds)):
            set_poise(sim, p, cur + 2.3)
            sl.lift[ctl.team] += 0.1                                    # the whole sideline heard it
            out = f"{name} gets it. He's got a look in his eye now."
            ok = True
        else:
            set_poise(sim, p, cur - 0.8)
            morale.nudge(p, -3, "chewed out on the sideline")
            out = f"That didn't land. {name} is pressing now, and he's not happy about it."
            ok = False
        arm = 1.3 + (0.9 if young or traits & ARM_WORKS else 0) - (0.9 if traits & ARM_WASTED else 0)
        odds_ = max(0.1, min(0.9, odds))
        face = odds_ * 2.4 - (1 - odds_) * 1.1                  # the poise, and the grudge if it misses
        e = _log(sim, "people", f"Got in {p.position} {p.name}'s face after he {WHAT[kind]}", result=out,
                 chart="good" if face >= max(arm, 1.0) - 0.35 else "bad", weight=0.3)
        if e is not None:
            e["ok"] = ok
        return out
    if c == "3":
        gain = 1.0 if cap is not None else 0.4
        if cap is not None and "captain" in (getattr(cap, "traits", []) or []):
            gain += 0.3
        set_poise(sim, p, cur + gain)
        out = f"{cap.last_name} grabs him by the facemask and says something. {name} nods." if cap is not None \
            else f"A couple of teammates slap his helmet. {name} is okay."
        _log(sim, "people", f"Let {'a captain' if cap else 'the players'} handle {p.name} after he {WHAT[kind]}")
        return out
    if c == "4" and _can_bench(sim, p):
        sl.benched[p] = len(sim.drives) + 2
        sim._rebuild_depth(sim.team_of(p))
        set_poise(sim, p, cur + 1.6)
        morale.nudge(p, -2, "benched a series")
        out = f"{name} sits a series. He'll be back — and he'll hold onto it."
        _log(sim, "people", f"Sat {p.position} {p.name} a series after he {WHAT[kind]}")
        return out
    _staff_handles(sim, p)
    return "You let it go. His position coach will get to him."


# ── the trainer ─────────────────────────────────────────────────────────────

def trainer(sim, p, team, severity, games, desc):
    """A starter just went down (not a season-ender). Returns True if he stays out (as rolled)."""
    ctl = sim.ctl
    sl = _sl(sim)
    if sl is None or ctl is None or team is not ctl.team or not opt("sideline_people") or ctl.auto_until is not None:
        return True
    if severity == "shaken" or games <= 0 or games > 3 or sim.quarter > 4:
        return True
    print()
    print(paint("   ┌─ TRAINER'S REPORT  " + _qc(sim) + " " + "─" * 36, C.BRED))
    print(paint("   │ ", C.BRED) + paint(f"{p.position} {p.name}", C.BWHITE, C.BOLD) + f" — {desc}.")
    tough = "warrior" in (getattr(p, "traits", []) or [])
    print(paint("   │ ", C.BRED) + paint("Trainer: ", C.BCYAN, C.BOLD) + paint(
        f"\"He can go, but he's not right. Maybe 80 percent. If he tweaks it, it's more than "
        f"{'a week' if games == 1 else f'{games} weeks'}.\"" + (" He wants back in. He always does." if tough else ""),
        C.BCYAN))
    print(paint("   │ ", C.BRED) + "   ".join([_k("1", "shut him down"), _k("2", "tape it, send him back"),
                                              _k("3", "only if we need him late")]))
    c = ask("Your call (Enter = shut him down):").strip()
    if c == "2":
        sl.hurt_through[p] = (games, desc)
        sl.hobble[p] = -4.0 if not tough else -2.5
        _refresh(sl, p)
        print(paint(f"   └ {p.last_name} gets taped up. He'll be back in a few plays.", C.BYELLOW))
        _log(sim, "trainer", f"Sent {p.position} {p.name} back in ({desc})", result="played through it")
        return False
    if c == "3":
        sl.late_only[p] = (games, desc)
        print(paint(f"   └ {p.last_name} stays on the bench unless it's close in the fourth.", C.BYELLOW))
        _log(sim, "trainer", f"Held {p.position} {p.name} for late ({desc})")
        return True
    print(paint(f"   └ {p.last_name} is done for the day.", C.BYELLOW))
    _log(sim, "trainer", f"Shut down {p.position} {p.name} ({desc})")
    return True


AGGRAVATE = 0.06


def aggravated(sim, p):
    """Playing hurt: every hit is a chance to make it worse."""
    sl = _sl(sim)
    if sl is None or p not in sl.hurt_through:
        return False
    if sim.rng.random() >= AGGRAVATE:
        return False
    games, desc = sl.hurt_through.pop(p)
    sl.hobble.pop(p, None)
    _refresh(sl, p)
    more = games * 2 + 1
    if sim.persist_injuries:
        p.inj_games, p.inj_desc, p.inj_week = more, desc + " (aggravated)", sim.game.week
    sim.out.add(p)
    team = sim.team_of(p)
    sim.injuries.append((sim.quarter, sim.clock, team, p, desc + " — aggravated", "out", more))
    sim._rebuild_depth(team)
    sim._n("injury", p, team, desc + " — aggravated it", "out", more, True)
    for e in reversed(sl.log):
        if e["kind"] == "trainer" and p.name in e["text"]:
            e["result"] = f"aggravated it — out {more} weeks"
            e["chart"] = "bad"
            break
    return True


def late_returns(sim):
    """Start of the fourth: the ones you held back come in if it's close."""
    sl = _sl(sim)
    if sl is None or not sl.late_only:
        return
    for p, (games, desc) in list(sl.late_only.items()):
        team = sim.team_of(p)
        if abs(sim.score[team] - sim.score[sim.other(team)]) <= 8:
            sim.out.discard(p)
            sl.hurt_through[p] = (games, desc)
            sl.hobble[p] = -4.0
            _refresh(sl, p)
            sim._rebuild_depth(team)
            if sim.narr is not None and not getattr(sim.narr, "muted", False):
                print(paint(f"   ▸ {p.position} {p.name} is coming back in. It's close, and he's taped up.", C.BYELLOW))
        del sl.late_only[p]


# ═══ Situational calls ═══════════════════════════════════════════════════════

def _calls_on(ctl):
    return active(ctl) and opt("sideline_calls")


def fourth_chart(sim):
    """What a fourth-down chart says: 'go' | 'fg' | 'punt'."""
    team = sim.offense
    ytg = 100 - sim.yardline
    togo = sim.togo
    d = sim.score[team] - sim.score[sim.other(team)]
    import playbook as pb
    in_range = ytg + 17 <= pb.fg_range(sim)
    left = pb.game_seconds_left(sim)
    if sim.quarter > 4:
        return "go" if d < -3 or togo <= 2 or not in_range else "fg"
    if sim.quarter == 4 and d < 0 and left < 300:
        if -3 <= d and in_range:
            return "fg"
        return "go"
    if sim.quarter == 4 and d > 0 and left < 150:
        return "punt" if not in_range else ("fg" if togo > 1 else "go")
    if ytg <= 5:
        limit = 2
    elif ytg <= 35:
        limit = 3 if ytg > 20 else 2
    elif ytg <= 50:
        limit = 4
    elif ytg <= 65:
        limit = 2
    elif ytg <= 75:
        limit = 1
    else:
        limit = 0
    if sim.quarter == 4 and d <= -9:
        limit += 2
    if togo <= limit:
        return "go"
    return "fg" if in_range else "punt"


CHOICE_WORDS = {"go": "go for it", "fg": "kick the field goal", "punt": "punt", "fake": "run a fake"}


def log_fourth(sim, ctl, action, staff_action):
    """A fourth-down call you made (or took from the staff)."""
    kind = lambda a: "go" if a[0] == "play" and getattr(a[1], "kind", "") != "kneel" else \
        "fake" if a[0] in ("fake_punt", "fake_fg") else a[0] if a[0] in ("punt", "fg") else "other"
    mine, staff = kind(action), kind(staff_action)
    if mine == "other":
        return
    chart = fourth_chart(sim)
    agree = mine == chart or (mine == "fake" and chart != "go")
    togo = "goal" if 100 - sim.yardline <= sim.togo else sim.togo
    spot = f"their {100 - sim.yardline}" if sim.yardline > 50 else "midfield" if sim.yardline == 50 else f"your {sim.yardline}"
    e = _log(sim, "fourth", f"4th & {togo} at {spot}: {CHOICE_WORDS[mine]}", staff=CHOICE_WORDS.get(staff),
             yours=mine, chart=CHOICE_WORDS[chart] if not agree else "✓", weight=1.5 if sim.quarter >= 4 else 1.0)
    sl = _sl(sim)
    if e is not None:
        e["agree"] = agree                                  # for the podium: did you go against the chart?
        e["chart_pick"] = chart
        _price(e, lambda: decisions.fourth_down(
            sim, fake_odds(sim, action[0]) if mine == "fake" else None, mine), mine)
        sl.pending = (e, sim.offense, len(sim.drives))


def _resolve_pending(sim, r, before, off):
    sl = _sl(sim)
    if sl is None or sl.pending is None:
        return
    e, team, _ = sl.pending
    sl.pending = None
    if r.td:
        e["result"] = "touchdown"
    elif r.turnover:
        e["result"] = "turned it over"
    elif sim.offense is team and sim.down == 1:
        e["result"] = "converted"
    else:
        e["result"] = "stopped"
    e["ok"] = e["result"] in ("touchdown", "converted")


def resolve_special(sim, kind, ok, detail=""):
    sl = _sl(sim)
    if sl is None or sl.pending is None:
        return
    e = sl.pending[0]
    sl.pending = None
    e["result"] = detail or ("good" if ok else "no good")
    e["ok"] = ok


# ── the try ──────────────────────────────────────────────────────────────────

def try_choice(sim, team, staff_two):
    """After your touchdown: kick or go for two. Returns (go_for_two, action or None)."""
    ctl = sim.ctl
    if ctl is None or team is not ctl.team or not _calls_on(ctl):
        return staff_two, None
    if sim.quarter > 4 and sim.ot_round >= 2:
        return True, None                                  # the rules: two from the second overtime on
    if ctl.mode == "moments" and sim.quarter < 4:
        return staff_two, None
    d = sim.score[team] - sim.score[sim.other(team)]
    chart = staff_two
    print()
    print(paint(f"   THE TRY  ·  {_qc(sim)}  ·  up {d}" if d > 0 else f"   THE TRY  ·  {_qc(sim)}  ·  "
                + (f"down {-d}" if d < 0 else "tied"), C.BMAGENTA, C.BOLD) + paint(
        "   staff: " + ("go for two" if staff_two else "kick it"), C.BCYAN))
    print("   " + "   ".join([_k("Enter", "staff's call", C.BGREEN), _k("K", "kick"), _k("2", "go for two"),
                              _k("R", "two, your run"), _k("P", "two, your pass")]))
    c = ask("The try:").strip().lower()
    two, action = staff_two, None
    if c == "k":
        two = False
    elif c == "2":
        two = True
    elif c in ("r", "p"):
        play = ctl.pick_play(sim, "run" if c == "r" else "pass")
        two = True
        if play is not None:
            action = (play, ctl.personnel(sim, play))
    if sim.quarter >= 3 or two:
        _log(sim, "two", f"Up {d}: " + ("went for two" if two else "kicked") if d > 0 else
             (f"Down {-d}: " if d < 0 else "Tied: ") + ("went for two" if two else "kicked"),
             staff="go for two" if staff_two else "kick", yours=two,
             chart="✓" if two == chart else ("go for two" if chart else "kick"), weight=1.2 if sim.quarter >= 4 else 0.6)
        sl = _sl(sim)
        if sl.log:
            sl.log[-1]["agree"] = two == chart
            sl.log[-1]["chart_pick"] = "two" if chart else "kick"
            _price(sl.log[-1], lambda: decisions.the_try(sim, team), "two" if two else "kick",
                   {"two": "go for two", "kick": "kick it"})
    return two, action


def log_try(sim, team, two, ok):
    sl = _sl(sim)
    ctl = sim.ctl
    if sl is None or ctl is None or team is not ctl.team or not sl.log:
        return
    e = sl.log[-1]
    if e["kind"] == "two" and e.get("result") is None:
        e["result"] = ("good" if ok else "no good")
        e["ok"] = ok


# ── kickoffs ─────────────────────────────────────────────────────────────────

def kick_choice(sim, kicking, safety=False):
    """Your kickoff: None (normal/staff), 'squib', 'onside', 'surprise'."""
    ctl = sim.ctl
    if ctl is None or kicking is not ctl.team or safety or not _calls_on(ctl) or sim.quarter > 4:
        return None
    rec = sim.other(kicking)
    d = sim.score[kicking] - sim.score[rec]
    expected = sim.quarter == 4 and -16 <= d < 0 and sim.clock < 150
    staff = "onside" if expected else "squib" if 0 < d <= 8 and (
        (sim.quarter == 4 and sim.clock < 120) or (sim.quarter == 2 and sim.clock < 30)) else "deep"
    if ctl.mode == "moments" and not expected and not (sim.quarter == 4 and sim.clock < 300):
        return None
    words = {"deep": "kick it deep", "squib": "squib it", "onside": "onside kick"}
    print()
    print(paint(f"   KICKOFF  ·  {_qc(sim)}", C.BMAGENTA, C.BOLD) + paint(f"   staff: {words[staff]}", C.BCYAN))
    opts = [_k("Enter", "staff's call", C.BGREEN), _k("D", "deep"), _k("S", "squib"), _k("O", "onside")]
    if not expected:
        opts.append(_k("X", "surprise onside"))
    print("   " + "   ".join(opts))
    c = ask("Kickoff:").strip().lower()
    pick = {"d": "deep", "s": "squib", "o": "onside", "x": "surprise"}.get(c, staff)
    if pick == "surprise" and expected:
        pick = "onside"
    if pick != "deep" or staff != "deep":
        _log(sim, "kick", f"{'Down ' + str(-d) if d < 0 else 'Up ' + str(d) if d > 0 else 'Tied'}: "
             + {"deep": "kicked deep", "squib": "squibbed", "onside": "onside kick", "surprise": "surprise onside"}[pick],
             staff=words[staff], yours=pick, chart="✓" if (pick == staff or pick == "surprise") else words[staff],
             weight=0.8)
        e = _sl(sim).log[-1]
        e["agree"] = pick == staff or pick == "surprise"
        e["chart_pick"] = staff
        seen = _sl(sim).onsides.get(kicking, 0)
        opts = ("deep", "squib", "onside") + (("surprise",) if not expected else ())
        _price(e, lambda: {k: v for k, v in decisions.kickoff(sim, kicking, seen).items() if k in opts}, pick,
               {"deep": "kick it deep", "squib": "squib it", "onside": "onside kick", "surprise": "surprise onside"})
    return None if pick == "deep" and staff == "deep" else pick


def log_kick(sim, kicking, recovered):
    sl = _sl(sim)
    if sl is None or not sl.log or sim.ctl is None or kicking is not sim.ctl.team:
        return
    e = sl.log[-1]
    if e["kind"] == "kick" and e.get("result") is None and e["yours"] in ("onside", "surprise"):
        e["result"] = "recovered" if recovered else "they covered it"
        e["ok"] = recovered


# ── fakes ────────────────────────────────────────────────────────────────────

def fake_odds(sim, kind):
    sl = _sl(sim)
    base = 0.55 + (0.1 if sim.togo <= 2 else 0) - (0.15 if sim.togo >= 5 else 0)
    if sl is not None:
        base -= 0.2 * sl.fakes.get(sim.offense, 0)            # they've seen one today
    if sim.quarter == 4 and sim.clock < 300:
        base -= 0.1                                           # everybody's alert late
    return max(0.15, min(0.8, base))


def fake_words(odds):
    return ("they're asleep on it" if odds >= 0.6 else "it's there" if odds >= 0.5 else
            "they'll be ready for it" if odds >= 0.35 else "they're sitting on it")


# ── flags ────────────────────────────────────────────────────────────────────

def _value(down, togo, yardline):
    """A rough worth of a spot to the offense (for accept / decline)."""
    if down > 4:
        return -2.5 + yardline * 0.02
    v = yardline * 0.07 - (down - 1) * 0.55 - min(togo, 25) * 0.07
    if down == 4:
        v -= 1.2
    return v


def flag_decision(sim, r, before):
    """A flag with a choice. The team that didn't foul decides. Mutates r if accepted."""
    fo = r.flag_option
    name, fouler, yards, auto_first, replay, who = fo
    chooser = sim.other(fouler)
    down, togo, yl = before[0], before[1], before[2]
    off = sim.offense
    # the play as it happened
    if r.turnover or r.td:
        return
    ny = yl + r.yards
    if r.yards >= togo:
        play_state = (1, min(10, 100 - ny), ny)
    else:
        play_state = (down + 1, togo - r.yards, ny)
    # the penalty
    py = max(1, min(99, yl + yards))
    if auto_first or togo - yards <= 0:
        pen_state = (1, min(10, 100 - py), py)
    else:
        pen_state = (down if replay else down + 1, togo - yards, py)
    pv, qv = _value(*play_state), _value(*pen_state)
    staff_accept = (qv > pv) if chooser is off else (qv < pv)
    ctl = sim.ctl
    accept = staff_accept
    if ctl is not None and chooser is ctl.team and _calls_on(ctl) and abs(pv - qv) < 1.6:
        def words(st):
            dn, tg, y = st
            if dn > 4:
                return "turnover on downs"
            return f"{('1st', '2nd', '3rd', '4th')[dn - 1]} & {tg if 100 - y > tg else 'goal'} at the {sim.spot(y)}"
        print()
        print(paint(f"   FLAG  ·  {name} on {fouler.school}" + (f" ({who.position} {who.last_name})" if who else ""),
                    C.BYELLOW, C.BOLD))
        side = "offense" if chooser is off else "defense"
        print(f"   {_k('A', 'accept')} → {words(pen_state)}      {_k('D', 'decline')} → {words(play_state)}"
              + paint(f"   (you're on {side}) · staff: {'accept' if staff_accept else 'decline'}", C.GRAY))
        c = ask("Accept or decline? (Enter = staff):").strip().lower()
        accept = True if c == "a" else False if c == "d" else staff_accept
        _log(sim, "flag", f"{name}: {'accepted' if accept else 'declined'}", staff="accept" if staff_accept else "decline",
             yours=accept, chart="✓" if accept == staff_accept else ("accept" if staff_accept else "decline"), weight=0.6)
        e = sim.sl.log[-1]
        e["agree"] = accept == staff_accept
        e["chart_pick"] = "accept" if staff_accept else "decline"
        sgn = 1 if chooser is off else -1
        _price(e, lambda: {"accept": sgn * qv * decisions.per_point(sim, chooser),
                           "decline": sgn * pv * decisions.per_point(sim, chooser)},
               "accept" if accept else "decline", {"accept": "accept", "decline": "decline"})
    r.flag_option = None
    if accept:
        sim.discard_stats()
        r.kind = "penalty"
        r.td = False
        r.sack = False
        r.first_down = False
        r.penalty = (name, fouler, yards, auto_first, replay)
        r.flag_player = who
        r.flag_choice = "accepted"
        r.say(f"Flag on the play — {name.lower()}{', ' + who.last_name if who else ''}. {chooser.school} accepts.")
    else:
        note = f"There's a flag — {name.lower()} on {fouler.school} — but {chooser.school} declines it."
        r.say(note)
        r.__dict__.setdefault("sl_notes", []).append(note)


# ── the replay challenge ────────────────────────────────────────────────────

def _close_call(sim, r, before):
    """Is this one worth a look? Returns (kind, wrong_on_the_field?) or None."""
    rng = sim.rng
    off = sim.offense
    if r.penalty or r.kind == "kneel":
        return None
    if r.complete and r.contested and not r.turnover and r.yards >= 8:
        if rng.random() < 0.3:
            return ("catch", rng.random() < 0.35)
    if r.turnover == "fumble" and r.return_yards < 100 - sim.yardline:
        if rng.random() < 0.35:
            return ("fumble", rng.random() < 0.35)
    if before[0] >= 3 and not r.td and not r.turnover and r.yards == before[1] - 1 and r.yards >= 0 \
            and not r.incomplete and not r.sack:
        if rng.random() < 0.5:
            return ("spot", rng.random() < 0.4)
    return None


_READS = ((0.75, 9.0), (0.55, 0.75), (0.42, 0.55), (-9.0, 0.42))   # the guy upstairs' words, as ranges


def _challenge_worth(sim, r, before, kind, read, iq, team):
    """What throwing the flag was worth, from what you were told (his words, not the replay)."""
    import math
    prior = 0.4 if kind == "spot" else 0.35
    sd = max(0.03, 0.18 * (1.3 - min(1.2, iq)))
    lo, hi = next((a, b) for a, b in _READS if read >= a)
    band = lambda mu: decisions._phi((hi - mu) / sd) - decisions._phi((lo - mu) / sd)
    pw, pr = prior * band(0.68), (1 - prior) * band(0.32)
    post = pw / (pw + pr) if pw + pr > 0 else prior
    if kind == "fumble":
        gain = 4.0
    elif kind == "catch":
        gain = 0.5 + max(0, r.yards) * 0.065
    else:
        gain = 4.0 if before[0] == 4 else 1.2
    cost = 0.9 if sim.quarter >= 4 else 0.5 if sim.quarter == 2 and sim.clock < 180 else 0.25
    pp = decisions.per_point(sim, team)
    return {"throw": (post * gain - (1 - post) * cost) * pp, "let": 0.0}


def challenge(sim, r, before):
    """After the whistle, before the next snap. May reverse the play (mutates r)."""
    sl = _sl(sim)
    if sl is None:
        return
    cc = _close_call(sim, r, before)
    if cc is None:
        return
    kind, wrong = cc
    off, df = sim.offense, sim.defense
    against = df if kind == "catch" else off        # who the call went against
    if sl.challenges.get(against, 0) <= 0 or sim.timeouts[against] <= 0 or sim.quarter > 4:
        return
    iq = getattr(sim.plan[against], "iq", 0.6)
    read = (0.68 if wrong else 0.32) + sim.rng.gauss(0, 0.18 * (1.3 - min(1.2, iq)))
    what = {"catch": "the catch", "fumble": "the fumble — his knee might have been down",
            "spot": "the spot — he might have had the first down"}[kind]
    ctl = sim.ctl
    if ctl is not None and against is ctl.team and _calls_on(ctl):
        conf = ("He's sure." if read >= 0.75 else "Good look — I'd throw it." if read >= 0.55 else
                "Coin flip." if read >= 0.42 else "I don't love it.")
        print()
        print(paint("   ┌─ CLOSE ONE " + "─" * 52, C.BYELLOW))
        print(paint("   │ ", C.BYELLOW) + f"The booth didn't buzz down. Your guy upstairs on {what}:")
        print(paint("   │ ", C.BYELLOW) + paint(f"\"{conf}\"", C.BCYAN) + paint(
            f"   (a lost challenge costs a timeout — you have {sim.timeouts[against]})", C.GRAY))
        c = ask("[Y] throw the flag · Enter = let it go:").strip().lower()
        go = c == "y"
        print(paint("   └" + "─" * 64, C.BYELLOW))
        worth = _challenge_worth(sim, r, before, kind, read, iq, against)
        if not go:
            e = _log(sim, "challenge", f"Let the {kind} stand",
                     result="replays later showed it was wrong" if wrong else "replays showed the call was right",
                     weight=0.6)
            _price(e, lambda: worth, "let", {"throw": "throw the flag", "let": "let it go"})
            if e is not None:
                e["ok"] = not wrong
            return
    else:
        big = kind == "fumble" or before[0] >= 3 or sim.quarter >= 4 or r.yards >= 15
        go = big and read >= 0.55
        if not go:
            return
    sl.challenges[against] -= 1
    lines = []
    if wrong:
        sl.challenges[against] += 1                           # a win keeps it (a second one)
        lines.append(f"{against.school} challenges... and after review, the ruling on the field is OVERTURNED.")
        lines.append(_overturn(sim, r, kind))
    else:
        sim.timeouts[against] -= 1
        lines.append(f"{against.school} challenges... the ruling on the field STANDS. That costs them a timeout.")
    r.say(" ".join(lines))
    r.__dict__.setdefault("sl_notes", []).extend(lines)
    if ctl is not None and against is ctl.team:
        e = _log(sim, "challenge", f"Challenged {'the ' + kind} ({_qc(sim)})",
                 result="overturned" if wrong else "stands — lost a timeout", weight=0.6)
        _price(e, lambda: worth, "throw", {"throw": "throw the flag", "let": "let it go"})
        if e is not None:
            e["ok"] = wrong


def _overturn(sim, r, kind):
    pend = sim.pending
    r.overturned = kind
    if kind == "catch":
        keep = {"pass_att", "targets", "tgt_d"}
        passer, target, defender = r.passer, r.target, r.defender
        sim.pending = [x for x in pend if x[1] in keep and x[0] in (passer, target, defender)]
        r.complete = False
        r.incomplete = True
        r.inc_reason = "overturned"
        r.yards = 0
        r.td = False
        r.carrier = None
        r.tackler = None
        r.out_of_bounds = False
        r.first_down = False
        return "Replay shows the ball hit the ground. Incomplete."
    elif kind == "fumble":
        sim.pending = [x for x in pend if x[1] not in ("fumbles", "ff", "fr")]
        r.turnover = None
        r.return_yards = 0
        return "His knee was down before the ball came out. The offense keeps it."
    elif kind == "spot":
        r.yards += 1
        if r.carrier is not None:
            key = "rush_yds" if r.kind == "run" else "rec_yds"
            sim.pending.append((r.carrier, key, 1, False))
            if r.kind == "pass" and r.passer is not None:
                sim.pending.append((r.passer, "pass_yds", 1, False))
        return "They move the ball forward. That's a FIRST DOWN."


# ── icing ────────────────────────────────────────────────────────────────────

def ice(sim, dist):
    """Before a field goal that matters: the defense can ice the kicker. Returns an accuracy penalty."""
    df, off = sim.defense, sim.offense
    if sim.timeouts[df] <= 0 or dist < 30:
        return 0.0
    d = sim.score[off] - sim.score[df]
    late = (sim.quarter == 4 and sim.clock <= 150 and -3 <= d <= 2) or (sim.quarter == 2 and sim.clock <= 15) \
        or sim.quarter > 4
    if not late:
        return 0.0
    ctl = sim.ctl
    k = sim.depth[off]["K"][0]
    if ctl is not None and df is ctl.team and _calls_on(ctl):
        print()
        print(paint(f"   THEIR FIELD GOAL  ·  {dist} yards  ·  {_qc(sim)}", C.BMAGENTA, C.BOLD)
              + paint(f"   {k.name}, {('freshman', 'sophomore', 'junior', 'senior')[max(0, min(3, k.year))]}", C.GRAY))
        c = ask(f"[T] ice him (timeouts: {sim.timeouts[df]}) · Enter = let him kick:").strip().lower()
        go = c == "t"
        if go:
            _log(sim, "ice", f"Iced their kicker ({dist} yds, {_qc(sim)})", weight=0.3)
    else:
        go = sim.rng.random() < 0.4 and sim.quarter >= 4
    if not go:
        return 0.0
    sim.timeouts[df] -= 1
    if sim.narr is not None:
        sim._n("kick", [f"{df.school} calls timeout — they're going to make {k.last_name} think about it."])
    tr = set(getattr(k, "traits", []) or [])
    pen = 0.3 * (1.5 if k.year <= 1 else 1.0) * (0.3 if tr & {"cold", "clutch"} else 1.0) \
        * (1.6 if "headcase" in tr else 1.0)
    return pen


def log_ice(sim, good):
    sl = _sl(sim)
    if sl is None or not sl.log:
        return
    e = sl.log[-1]
    if e["kind"] == "ice" and e.get("result") is None:
        e["result"] = "he made it anyway" if good else "he missed"
        e["ok"] = not good


# ── overtime ────────────────────────────────────────────────────────────────

def ot_choice(sim, winner):
    """The toss winner picks. Returns the team that goes on offense first."""
    ctl = sim.ctl
    loser = sim.other(winner)
    if ctl is not None and winner is ctl.team and ctl.auto_until is None and opt("sideline_calls"):
        print()
        print(paint("   OVERTIME  ·  You won the toss.", C.BMAGENTA, C.BOLD)
              + paint("   staff: defense first — know what you need", C.BCYAN))
        c = ask("[D] defense first · [O] offense first (Enter = defense):").strip().lower()
        first = winner if c == "o" else loser
        _log(sim, "ot", "Overtime: " + ("offense first" if c == "o" else "defense first"),
             chart="✓" if c != "o" else "defense first", weight=0.4)
        e = sim.sl.log[-1]
        e["agree"] = c != "o"
        e["chart_pick"] = "defense"
        _price(e, decisions.overtime, "offense" if c == "o" else "defense",
               {"defense": "defense first", "offense": "offense first"})
        return first
    return loser                                      # everybody takes the ball second


# ── the crowd, the timeout ─────────────────────────────────────────────────

def crowd_up(sim, ctl):
    sl = _sl(sim)
    team = ctl.team
    if sim.home is not team or sim.momentum.neutral:
        print(paint("   It's not your crowd.", C.GRAY))
        return False
    if sim.down < 3:
        print(paint("   Save it for third down.", C.GRAY))
        return False
    if sl.crowd is team:
        return False
    sl.crowd = team
    sl.crowd_uses += 1
    msg = ("You turn to the stands and wave both arms. The place ERUPTS." if sl.crowd_uses <= 2 else
           "You wave them up again. They're loud — not what they were." if sl.crowd_uses <= 4 else
           "You wave. They're tired of being asked.")
    print(paint("   " + msg, C.BYELLOW))
    return True


def settle(sim, team):
    """A timeout when the building has turned: the momentum cools off."""
    m = sim.momentum
    v = m.value if team is sim.home else -m.value
    if v <= -35:
        m.value *= 0.55
        return True
    return False


# ═══ Halftime & postgame ═════════════════════════════════════════════════════

def _team_line(sim, team):
    t = {"rush_att": 0, "rush_yds": 0, "pass_att": 0, "pass_yds": 0}
    for p, c in sim.stats.items():
        if sim.team_of(p) is team:
            for k in t:
                t[k] += c.get(k, 0)
    return t


def plan_check(sim, team):
    """[(label, verdict, color)] for your two keys."""
    sl = _sl(sim)
    if sl is None:
        return []
    gp = sl.gp.get(team)
    if not gp:
        return []
    opp = sim.other(team)
    me, them = _team_line(sim, team), _team_line(sim, opp)
    out = []
    ok = lambda b: ("working", C.BGREEN) if b is True else ("not working", C.BRED) if b is False else ("too early", C.GRAY)
    k = gp["off"]
    if k != "balanced":
        if k in ("run", "control"):
            v = None if me["rush_att"] < 8 else me["rush_yds"] / me["rush_att"] >= 4.5
            det = f"{me['rush_att']} carries, {me['rush_yds']} yds"
        elif k == "deep":
            v = None if sim.plan[team].faced < 12 else sl.explosive[team] >= 2
            det = f"{sl.explosive[team]} plays of 20+"
        else:
            v = None if me["pass_att"] < 8 else sim.plan[team].sacks_taken <= 1
            det = f"{sim.plan[team].sacks_taken} sacks allowed"
        w, c = ok(v)
        out.append((f"{OFF_KEYS[k][0]}", f"{w} ({det})", c))
    k = gp["def"]
    if k != "balanced":
        if k == "stop_run":
            v = None if them["rush_att"] < 8 else them["rush_yds"] / them["rush_att"] <= 4.0
            det = f"they have {them['rush_yds']} on {them['rush_att']}"
        elif k == "wr1":
            p = sl.wr1.get(opp)
            y = (sim.stats.get(p) or {}).get("rec_yds", 0) if p else 0
            v = None if sim.plan[team].opp_snaps < 12 else y <= 50
            det = f"{p.last_name if p else 'he'} has {y} yds"
        elif k == "rush":
            v = None if them["pass_att"] < 8 else sl.sacks[team] >= 2
            det = f"{sl.sacks[team]} sacks"
        elif k == "front":
            v = None if sim.plan[team].opp_snaps < 12 else sl.explosive[opp] <= 1
            det = f"{sl.explosive[opp]} plays of 20+ allowed"
        else:
            qb = sim.qb_of(opp)
            y = (sim.stats.get(qb) or {}).get("rush_yds", 0)
            v = None if sim.plan[team].opp_snaps < 12 else y <= 30
            det = f"their QB has {y} rushing"
        w, c = ok(v)
        out.append((f"{DEF_KEYS[k][0]}", f"{w} ({det})", c))
    return out


def grade(log, box=None, team=None):
    """A letter for the process: what each call was worth in win chance when you made it —
    not whether it matched the chart, and not how it turned out (see decisions.py)."""
    pts, wsum = 0.0, 0.0
    for e in log:
        sc = decisions.score(e)
        if sc is not None:
            s, w, _, spread = sc
            if spread <= decisions.TOL:
                continue                              # a close call: anything goes
            wsum += w
            pts += w * s
        elif e.get("chart") in ("good", "bad"):
            w = e.get("weight", 0.5)
            wsum += w
            pts += w if e["chart"] == "good" else -w
    notes = []
    if box is not None and team is not None:
        sl = box.__dict__.get("sl")
        opp = box.away if box.home is team else box.home
        lost_close = box.score[team] < box.score[opp] and box.score[opp] - box.score[team] <= 8
        tos = (getattr(box, "timeouts", None) or {}).get(team, 0)
        if lost_close and sl is not None and sl.__dict__.get("late_headset") and tos >= 2 and getattr(box, "ot_round", 0) == 0:
            notes.append(f"Lost a one-score game with {tos} timeouts in your pocket.")
            wsum += 1.0
            pts -= 1.0
    if wsum < 0.5:
        return None, notes
    s = pts / wsum                                   # -1 .. 1
    letter = ("A+" if s >= 0.9 else "A" if s >= 0.8 else "A-" if s >= 0.7 else "B+" if s >= 0.6 else
              "B" if s >= 0.5 else "B-" if s >= 0.4 else "C+" if s >= 0.3 else "C" if s >= 0.15 else
              "C-" if s >= 0.0 else "D" if s >= -0.3 else "F")
    return letter, notes


def tally(log):
    """What the priced calls add up to: {'n', 'right', 'close', 'costly', 'given', 'against', 'against_right',
    'chart_wrong'} — 'given' is the win chance given away, all told."""
    t = {"n": 0, "right": 0, "close": 0, "costly": 0, "given": 0.0, "against": 0, "against_right": 0,
         "chart_wrong": 0, "vs_chart": 0.0, "charted": 0}
    for e in log:
        v, cost = decisions.verdict(e)
        if v is None:
            continue
        t["n"] += 1
        if v == "cost":
            t["costly"] += 1
            t["given"] += cost
        elif v == "close":
            t["close"] += 1
        else:
            t["right"] += 1
        cp = e.get("chart_pick")
        if cp in e["vals"]:
            t["charted"] += 1
            t["vs_chart"] += e["vals"][e["pick"]] - e["vals"][cp]
        if cp is not None and cp != e["pick"] and not (cp in ("fg", "punt") and e["pick"] == "fake"):
            t["against"] += 1
            t["against_right"] += v != "cost"
        if cp is not None and cp in e["vals"] and e["vals"][decisions.best_of(e["vals"])] - e["vals"][cp] > decisions.TOL:
            t["chart_wrong"] += 1
    return t


KIND_LABEL = {"fourth": "4TH DOWN", "two": "THE TRY", "kick": "KICKOFF", "flag": "FLAG", "challenge": "CHALLENGE",
              "ice": "ICE", "ot": "OVERTIME", "trainer": "TRAINER", "qb": "QB", "people": "SIDELINE",
              "orders": "ORDERS", "feed": "FEED", "timeout": "TIMEOUT"}


def _words(e, k):
    if e.get("words") and k in e["words"]:
        return e["words"][k]
    return CHOICE_WORDS.get(k, k)


def _mark(e):
    """The verdict on one call, and (for a costly one or one that beat the chart) the numbers."""
    v, cost = decisions.verdict(e)
    if v is None:
        if e.get("chart") == "good":
            return paint(" ✓", C.BGREEN), None
        if e.get("chart") == "bad":
            return paint(" ✗", C.BRED), None
        return "", None
    vals = e["vals"]
    best = decisions.best_of(vals)
    detail = None
    if e["kind"] in ("fourth", "two", "kick", "ot"):
        order = sorted(vals, key=vals.get, reverse=True)
        detail = "win chance: " + " · ".join(f"{_words(e, k)} {decisions.pct(vals[k])}" for k in order)
    if v == "close":
        return paint(" ≈ close call", C.BCYAN), None
    if v == "beat":
        return paint(" ★ right call — the chart said " + _words(e, e["chart_pick"]), C.BGREEN, C.BOLD), detail
    if v == "right":
        return paint(" ✓ right call", C.BGREEN), None
    tail = " (the chart missed this one too)" if e.get("chart_pick") == e["pick"] else ""
    return paint(f" ✗ −{cost * 100:.1f}% · better: {_words(e, best)}{tail}", C.BRED), detail


def headset_log(g, team):
    """The postgame screen: your calls, what each was worth, what happened, and a grade."""
    box = getattr(g, "box", None)
    sl = box.__dict__.get("sl") if box is not None else None
    if sl is None or not getattr(sl, "log", None):
        return
    log = [e for e in sl.log if e["kind"] not in ("orders",)]
    orders = [e for e in sl.log if e["kind"] == "orders"]
    if not log and not orders:
        return
    from ui import clear, pause, title_bar
    clear()
    print(title_bar(f"THE HEADSET  ·  {team.school.upper()}'S CALLS"))
    print(paint("   Each call is priced in win chance at the moment you made it — the score, the clock, your kicker,\n"
                "   the matchup. How it turned out is shown, but it isn't graded.", C.GRAY))
    print()
    lines = 0
    for e in log[-16:]:
        q = f"Q{e['q']}" if e["q"] <= 4 else "OT"
        lab = KIND_LABEL.get(e["kind"], e["kind"].upper())
        mark, detail = _mark(e)
        res = e.get("result")
        rc = C.BGREEN if e.get("ok") is True else C.BRED if e.get("ok") is False else C.GRAY
        line = (f"   {paint(pad(q + ' ' + _clock(e['clock']), 10), C.GRAY)}{paint(pad(lab, 10), C.BYELLOW)}"
                f"{truncate(e['text'], 46)}" + (paint(f"  → {res}", rc) if res else ""))
        if visible_len(line + mark) <= WIDTH:
            print(line + mark)
        else:
            print(line)
            print(f"   {'':19}{mark}")
        if detail and lines < 8:
            print(paint(f"   {'':20}{detail}", C.GRAY))
            lines += 1
    if orders:
        print(paint(f"\n   Orders you gave: " + ", ".join(e["text"] for e in orders[-6:]), C.GRAY))
    letter, notes = grade(sl.log, box, team)
    for n in notes:
        print(paint("   " + n, C.BRED))
    fourth = [e for e in log if e["kind"] == "fourth" and e.get("yours") == "go"]
    conv = sum(1 for e in fourth if e.get("ok"))
    bits = []
    if fourth:
        bits.append(f"went for it {len(fourth)} time{'s' if len(fourth) != 1 else ''}, converted {conv}")
    ch = [e for e in log if e["kind"] == "challenge" and e.get("pick") == "throw"]
    if ch:
        bits.append(f"challenges {sum(1 for e in ch if e.get('ok'))}/{len(ch)}")
    if bits:
        print(paint("\n   " + " · ".join(bits), C.BWHITE))
    t = tally(sl.log)
    if t["n"]:
        parts = [f"{t['right']} right", f"{t['close']} close"] + (
            [f"{t['costly']} costly (−{t['given'] * 100:.1f}% win chance in all)"] if t["costly"] else [])
        print(paint(f"   The calls: {t['n']} priced · " + " · ".join(parts), C.BWHITE))
        if t["against"]:
            print(paint(f"   You went against the chart {t['against']} time{'s' if t['against'] != 1 else ''} — "
                        f"{t['against_right']} of them the numbers backed you.",
                        C.BGREEN if t["against_right"] == t["against"] else C.GRAY))
        if t["chart_wrong"]:
            print(paint(f"   The chart itself was wrong on {t['chart_wrong']} of today's calls — it doesn't know "
                        "the score, the clock or your kicker.", C.GRAY))
        if t["charted"]:
            v = t["vs_chart"] * 100
            print(paint("   Against simply following the chart and the staff every time: ", C.GRAY)
                  + paint(f"{v:+.1f}% win chance", C.BGREEN if v > 0.5 else C.BRED if v < -0.5 else C.BWHITE, C.BOLD)
                  + paint("  (what your own judgment added)" if v > 0.5 else "", C.GRAY))
    if not letter and t["n"]:
        print(paint("\n   No grade: none of today's calls had enough riding on it to count.", C.GRAY))
    if letter:
        col = C.BGREEN if letter[0] in "AB" else C.BYELLOW if letter[0] == "C" else C.BRED
        print("\n   " + paint("Process grade: ", C.GRAY) + paint(letter, col, C.BOLD)
              + paint("   (what your calls were worth when you made them — not the chart, not the scoreboard)", C.GRAY))
    pause()


def podium_questions(g, team, q):
    """A question about the call that decided it, if there was one."""
    box = getattr(g, "box", None)
    sl = box.__dict__.get("sl") if box is not None else None
    if sl is None:
        return
    won = g.winner is team
    late = [e for e in sl.log if e["kind"] in ("fourth", "two") and e["q"] >= 4 and e.get("result")]
    if not late:
        return
    e = late[-1]
    if e["kind"] == "fourth" and e.get("yours") == "go" and not e.get("ok") and not won:
        q(9, f"Walk us through going for it on {e['text'].split(':')[0]} in the fourth quarter.",
          [("confident", "I'd make that call again tomorrow. We play to win.", ("recruits", 1)),
           ("humble", "It didn't work. That's on me, not the players.", [("chem", 1), ("seat", -1)]),
           ("measured", "The numbers said go. Sometimes the numbers lose.", None)])
    elif e["kind"] == "fourth" and e.get("yours") in ("punt", "fg") and e.get("chart_pick", "go" if not e.get("agree") else None) == "go" and not won:
        q(8, f"Why not go for it on {e['text'].split(':')[0]}?",
          [("measured", "I trusted our defense to get the ball back. They almost did.", None),
           ("fiery", "Because I'm the head coach. Next question.", [("lift", 0.1), ("chem", -1)]),
           ("humble", "In hindsight, we should have gone. I'll own that.", [("chem", 1), ("seat", -1)])])
    elif e["kind"] == "fourth" and e.get("yours") == "go" and e.get("ok") and won:
        q(6, "That fourth-down call in the fourth quarter — was that ever in doubt?",
          [("confident", "Not for a second. I trust those guys up front.", [("recruits", 1.5), ("chem", 1)]),
           ("humble", "The players made the call look good.", ("chem", 2)),
           ("measured", "It was the right call. They executed it.", None)])
    elif e["kind"] == "two" and e.get("yours") is True and not e.get("ok") and not won:
        q(8, "You went for two and didn't get it. Do you regret that?",
          [("measured", "The chart says go. You live with it.", None),
           ("humble", "I'd like that one back.", [("chem", 1), ("seat", -1)]),
           ("fiery", "No. I'd do it again. We came to win the game.", ("lift", 0.1))])
