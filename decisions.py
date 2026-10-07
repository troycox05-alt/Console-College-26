"""
decisions.py — What a call on the headset was actually worth.

The postgame grade used to count how often you agreed with the fourth-down
chart and the staff. Follow the chart every time and you got an A, even on the
days the chart was wrong for the situation. Now every graded call is priced in
WIN CHANCE at the moment you made it, and the grade asks one question: how much
of it did you give away?

THE MODEL (calibrated to this game's engine: 1,500 simulated games)
  A drive from a spot       touchdown / field goal / nothing, by where it starts
                            (own 25: TD 24%, FG 7% · midfield: 51%, 9% · their 25:
                            71%, 13% · their 5: 94%)
  The rest of the game      about one possession every 150 seconds, alternating;
                            each worth ~2.3 points with a wide spread, tilted by how
                            the two teams stack up (2.5 points of margin per point of
                            team overall, 3.5 for home field, plus the day's form)
  Fourth down               conversion by distance (1-2 yds 81% · 3: 73% · 4: 60% ·
                            5: 47% · 7-9: ~26% · 10+: 16%), nudged by the matchup;
                            field goals use your kicker's own make chance
  The try                   the kick ~96%, two points ~68% from the 3 (in this game,
                            going for two is worth more than people think)
  Kickoffs                  onside ~14% (expected), surprise ~45% (less once they've
                            seen one)

  The chart is a rule of thumb. The model knows the score, the clock, your kicker
  and the matchup. When they disagree, the model is the one that grades you.

HOW A CALL IS SCORED
  cost = best option's win chance − your option's win chance
  within 1.2 points of win chance  → the right call, +1
  a close call (every option within 1.2 points)  → anything goes; it isn't graded
  beyond that                      → 0 at about 2 points given away, −1 at about 4
  late calls and bigger decisions weigh a little more, and a call where the chart
  itself was wrong counts double — following it there costs you twice, and beating
  it earns twice. A game where no call had anything riding on it gets no grade.
  The headset also shows what your calls were worth against simply following the
  chart every time.
  Letters: A+ 0.9 · A 0.8 · A- 0.7 · B+ 0.6 · B 0.5 · B- 0.4 · C+ 0.3 · C 0.15 · C- 0 ·
  D -0.3 · F below (the weighted average of the calls' scores).
  The result never matters: a good call that fails is still a good call.
"""
import math

TOL = 0.012                  # win chance within this of the best option: the right call
FULL = 0.03                  # beyond the tolerance: +1 → 0 over the first point, → -1 by this much
SECS_PER_POSS = 150.0        # about 24 possessions a game
PTS_PER_DRIVE = 2.3
VAR_PER_DRIVE = 15.2         # scaled so a whole game's margin has the spread the engine shows (~19)
OVR_SLOPE = 2.5              # points of margin per point of team overall (per game)
FORM_SLOPE = 1.7             # points of margin per rating point of the day's form
HOME_EDGE = 3.5

# Drive outcomes by where the drive starts (own-goal yardline) — interpolated.
_TD = ((0, 0.19), (25, 0.24), (35, 0.36), (45, 0.47), (55, 0.54), (65, 0.61), (75, 0.71), (85, 0.79),
       (95, 0.92), (100, 0.95))
_FG = ((0, 0.05), (25, 0.07), (45, 0.08), (55, 0.11), (65, 0.14), (80, 0.13), (92, 0.06), (100, 0.03))
_CONV = {1: 0.81, 2: 0.80, 3: 0.72, 4: 0.60, 5: 0.48, 6: 0.39, 7: 0.30, 8: 0.26, 9: 0.24, 10: 0.17}
TWO_PT = 0.68
ONSIDE = 0.14


def _interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def drive(y, secs):
    """(p_td, p_fg) for a possession starting at y (own-goal yards) with secs on the clock."""
    y = max(1, min(99, y))
    td, fg = _interp(_TD, y), _interp(_FG, y)
    if secs is not None and secs < 400:
        need = 12 + (100 - y) * 1.5                        # a hurry-up drive: about 1.5 s a yard
        f = max(0.0, min(1.0, secs / need))
        td_eff = td * f
        need_fg = 6 + max(0, 65 - y) * 1.5
        f2 = max(0.0, min(1.0, secs / need_fg)) if need_fg > 0 else 1.0
        fg = min(1 - td_eff, (fg + (td - td_eff) * 0.6) * f2)
        td = td_eff
    return td, fg


def conv(togo, edge=0.0):
    p = _CONV.get(min(10, max(1, togo)), 0.17)
    if togo >= 15:
        p = 0.10
    return max(0.05, min(0.92, p + edge))


class State:
    """Everything the win-chance model needs, from one team's point of view."""

    def __init__(self, sim, team):
        self.team = team
        opp = sim.other(team)
        self.lead = sim.score[team] - sim.score[opp]
        self.ot = sim.quarter > 4
        self.ot_second = bool(getattr(sim, "ot_second", False))
        q, clock = sim.quarter, sim.clock
        self.secs = 0 if self.ot else (4 - q) * 900 + clock
        ovr = lambda t: 50 if getattr(t, "fcs", False) else getattr(t, "team_ovr", 70)
        mu = OVR_SLOPE * (ovr(team) - ovr(opp))
        form = getattr(sim, "form", {}) or {}
        mu += FORM_SLOPE * (form.get(team, 0.0) - form.get(opp, 0.0))
        if not getattr(sim, "neutral", False):
            mu += HOME_EDGE if sim.home is team else -HOME_EDGE
        self.mu = mu                                       # per 60 minutes
        self.edge = max(-0.08, min(0.08, (ovr(team) - ovr(opp)) * 0.008))   # a better unit converts more


def _spp(secs):
    """Seconds a possession takes: about 150, less late (timeouts, the sideline, hurry-up)."""
    return 150.0 if secs >= 900 else 105.0 + 45.0 * max(0.0, secs - 300) / 600 if secs > 300 else 105.0


def _dist(td, fg):
    return ((7, td), (3, fg), (0, 1 - td - fg))


def wp(st, lead, ours, y, secs=None):
    """Win chance for st.team: the score is `lead`, and a possession starts at y (own-goal
    yards for whoever has it) — ours or theirs — with secs left."""
    secs = st.secs if secs is None else max(0, secs)
    if st.ot:
        return _wp_ot(st, lead, ours, y)
    td, fg = drive(y, secs)
    spp = _spp(secs)
    rest = max(0.0, secs - spp * 0.6)
    n = rest / spp
    sign = 1 if ours else -1
    shift = st.mu * secs / 3600.0
    if n > 3.5:                                            # plenty of game left: the normal curve
        n_next = (n + 1) / 2
        n_after = n - n_next
        n_us, n_them = (n_after, n_next) if ours else (n_next, n_after)
        mean = (n_us - n_them) * PTS_PER_DRIVE + shift
        sd = math.sqrt((n_us + n_them) * VAR_PER_DRIVE)
        return sum(p * _phi((lead + sign * pts + mean) / sd) for pts, p in _dist(td, fg) if p > 0)
    # Late: the possessions that are left, one at a time.
    dist = {}
    for pts, p in _dist(td, fg):
        if p > 0:
            m = lead + sign * pts
            dist[m] = dist.get(m, 0.0) + p
    side = -sign                                           # whoever gets it next
    i = 0
    while n - i > 0:
        happen = min(1.0, n - i)
        t_left = max(0.0, rest - i * spp)
        dtd, dfg = drive(28, t_left)
        nd = {}
        for m, p in dist.items():
            if happen < 1.0:
                nd[m] = nd.get(m, 0.0) + p * (1 - happen)
            need = -m * side                               # what this side needs to tie or lead
            td_, fg_ = (dtd * 0.9, min(1 - dtd * 0.9, dfg + 0.12 * min(1.0, t_left / 60))) if 0 <= need <= 3 \
                else (dtd, dfg)                             # a field goal is all it needs: it plays for one
            for pts, q in _dist(td_, fg_):
                if q > 0:
                    mm = m + side * pts
                    nd[mm] = nd.get(mm, 0.0) + p * happen * q
        dist = nd
        side = -side
        i += 1
    return sum(p * _phi((m + shift) / 0.6) for m, p in dist.items())


def _wp_ot(st, lead, ours, y):
    """Overtime (every possession from the 25): this possession if it's ours, then theirs
    if they haven't had theirs yet. A tie after both goes to another round (a coin flip)."""
    step = lambda m: 1.0 if m > 0 else 0.0 if m < 0 else 0.5
    otd, ofg = drive(75, None)
    reply = _dist(otd, ofg)
    if ours:
        td, fg = drive(y, None)
        tot = 0.0
        for pts, p in _dist(td, fg):
            m = lead + pts
            tot += p * (step(m) if st.ot_second else sum(q * step(m - rp) for rp, q in reply))
        return tot
    if st.ot_second:
        return step(lead)
    return sum(q * step(lead - rp) for rp, q in reply)


def after_score(st, lead, secs):
    """We just scored (lead includes it): they get the ball at their 25."""
    return wp(st, lead, False, 25, secs)


# ═══ The calls ═══════════════════════════════════════════════════════════════

def _fg_prob(sim, dist, team, pat=False):
    try:
        import weather
        from engine import chance
        k = sim.depth[team]["K"][0]
        old = sim.__dict__.get("_ctx")
        sim._ctx = "kick"
        try:
            kp = sim.prof(k)
        finally:
            if old is None:
                sim.__dict__.pop("_ctx", None)
            else:
                sim._ctx = old
        w_rng, w_acc = weather.fg_mods(sim, team)
        if pat:
            x = max(2.4, min(4.6, 3.4 + (kp["kick_acc"] - 60) / 20))
            x = max(1.8, x + w_acc * 0.5)
            return chance(x) * 0.994
        lim = 48 + (kp["kick_power"] - 60) * 0.3 + w_rng
        x = (kp["kick_acc"] - 60) / 15 + (50 - dist) / 8 + 0.2 - max(0, dist - lim) * 0.4 + w_acc
        return chance(x) * 0.988
    except Exception:
        if pat:
            return 0.96
        return max(0.02, min(0.97, 1 / (1 + math.exp(-((50 - dist) / 8 + 0.9)))))


def fourth_down(sim, fake_p=None, pick=None):
    """{'go', 'fg', 'punt' (, 'fake')}: win chance for the offense after each."""
    team = sim.offense
    st = State(sim, team)
    y, togo = sim.yardline, sim.togo
    secs = st.secs - 6
    out = {}
    goal = y + togo >= 100
    p = conv(togo, st.edge)

    def go_value(prob):
        if goal:
            ok = after_score(st, st.lead + 7, secs)
        else:
            ok = wp(st, st.lead, True, min(99, y + togo + 3), secs)
        fail = wp(st, st.lead, False, max(1, 100 - y), secs)
        return prob * ok + (1 - prob) * fail

    out["go"] = go_value(p)
    dist = 100 - y + 17
    if dist <= 65 or pick == "fg":
        pm = _fg_prob(sim, dist, team)
        made = after_score(st, st.lead + 3, st.secs - 5)
        miss = wp(st, st.lead, False, max(20, 100 - (y - 7)), st.secs - 5)
        out["fg"] = pm * made + (1 - pm) * miss
    land = y + 40
    opp_y = 15 if land > 90 else 100 - land
    out["punt"] = wp(st, st.lead, False, opp_y, st.secs - 8)
    if fake_p is not None:
        out["fake"] = go_value(fake_p)
    return out


def the_try(sim, team):
    """{'kick', 'two'} after a touchdown (the six is already on the board)."""
    st = State(sim, team)
    pk = _fg_prob(sim, 20, team, pat=True)
    p2 = max(0.4, min(0.85, TWO_PT + st.edge))
    v = lambda d: after_score(st, st.lead + d, st.secs)
    return {"kick": pk * v(1) + (1 - pk) * v(0), "two": p2 * v(2) + (1 - p2) * v(0)}


def kickoff(sim, kicking, seen=0):
    """{'deep', 'squib', 'onside', 'surprise'}: win chance for the kicking team."""
    st = State(sim, kicking)
    secs = st.secs
    surprise = max(0.2, 0.45 - 0.2 * seen)
    deep = 0.985 * wp(st, st.lead, False, 24, secs - 6) + 0.015 * wp(st, st.lead - 7, True, 25, secs - 12)
    return {"deep": deep,
            "squib": wp(st, st.lead, False, 30, secs - 4),
            "onside": ONSIDE * wp(st, st.lead, True, 46, secs - 3) + (1 - ONSIDE) * wp(st, st.lead, False, 54, secs - 3),
            "surprise": surprise * wp(st, st.lead, True, 44, secs - 3) + (1 - surprise) * wp(st, st.lead, False, 56, secs - 3)}


def per_point(sim, team):
    """How much a point is worth in win chance right now (for calls priced in points)."""
    st = State(sim, team)
    ours = sim.offense is team
    y = sim.yardline
    return max(0.002, (wp(st, st.lead + 1, ours, y) - wp(st, st.lead - 1, ours, y)) / 2)


def overtime():
    """Defense first: you know what you need. A small edge, not a big one."""
    return {"defense": 0.515, "offense": 0.485}


# ═══ Scoring a call ══════════════════════════════════════════════════════════

def score(e):
    """(score -1..1, weight, cost, spread) for a log entry with 'vals' and 'pick', or None."""
    vals, pick = e.get("vals"), e.get("pick")
    if not vals or pick not in vals:
        return None
    best = max(vals.values())
    cost = max(0.0, best - vals[pick])
    spread = best - min(vals.values())
    over = cost - TOL
    s = 1.0 if over <= 0 else 1.0 - 100 * over if over <= 0.01 else max(-1.0, -(over - 0.01) / (FULL - 0.01))
    w = e.get("weight", 1.0) * (0.6 + min(0.9, spread * 10))
    cp = e.get("chart_pick")
    if cp in vals and best - vals[cp] > TOL:
        w *= 2.0                   # the chart was wrong here: the calls that test judgment count double
    return s, w, cost, spread


def best_of(vals):
    return max(vals, key=vals.get) if vals else None


def verdict(e):
    """('right' | 'close' | 'beat' | 'cost', cost) for the headset log."""
    sc = score(e)
    if sc is None:
        return None, 0.0
    s, w, cost, spread = sc
    if cost <= TOL:
        if spread <= TOL:
            return "close", cost
        if e.get("chart_pick") is not None and e.get("chart_pick") != e["pick"]:
            return "beat", cost
        return "right", cost
    return "cost", cost


def pct(x):
    return f"{x * 100:.0f}%"
