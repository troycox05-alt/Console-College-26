"""
team_momentum.py — A team's run of form over a season (not the in-game swing; that's momentum.py).

Every result moves it: a win nudges it up, a loss down, an upset or a statement win more,
a blowout loss more. It fades fast (about a third of it each week), so it reflects the
last three or four games, and it starts every season at zero.

What it does on Saturday, in rating points (the same scale as game-day form):
  * at most +1.2 for a red-hot team and -1.0 for a reeling one: worth a field goal or so
  * a hot team playing a much weaker opponent gets half of it (the trap game)
  * a reeling team in a rivalry game or against a ranked opponent gets half the drag
    (nothing to lose)
So it tips close games; it never makes anyone unbeatable or winless.
"""

MAX_UP, MAX_DOWN = 1.2, 1.0
DECAY = 0.65

WORDS = ((0.55, "Red-hot", "▲▲"), (0.22, "Rolling", "▲"), (-0.22, "Steady", "•"), (-0.55, "Sliding", "▼"),
         (-9.0, "Reeling", "▼▼"))


def value(team):
    st = team.__dict__.get("tmom")
    return st[1] if st else 0.0


def word(team):
    v = value(team)
    for cut, w, arrow in WORDS:
        if v >= cut:
            return w, arrow
    return "Steady", "•"


def _reset_if_new(league, team):
    st = team.__dict__.get("tmom")
    if not st or st[0] != league.year:
        team.__dict__["tmom"] = [league.year, 0.0, []]       # year, value, last results (for the screens)
    return team.__dict__["tmom"]


def after_games(league, games):
    """finish_week: every finished game moves both teams."""
    for g in games:
        if not g.played or g.home_score is None:
            continue
        for t in (g.home, g.away):
            if getattr(t, "fcs", False):
                continue
            opp = g.away if t is g.home else g.home
            st = _reset_if_new(league, t)
            won = g.winner is t
            margin = g.score_for(t) - g.score_for(opp)
            gap = (opp.team_ovr - t.team_ovr) / 10                 # how much better the opponent was
            r_opp = league.rankings.rank_of(opp)
            hit = 0.24 if won else -0.24
            if won:
                hit += max(0.0, gap) * 0.18 + (0.12 if r_opp and r_opp <= 10 else 0.06 if r_opp else 0)
                hit += 0.06 if margin >= 21 else 0
            else:
                hit -= max(0.0, -gap) * 0.18                       # lost to a worse team
                hit -= 0.08 if margin <= -21 else 0
                if margin >= -3 and r_opp and r_opp <= 10:
                    hit += 0.14                                     # a near miss against a top-10 team isn't a slide
            st[1] = max(-1.0, min(1.0, st[1] * DECAY + hit))
            st[2] = (st[2] + ["W" if won else "L"])[-6:]


def lift(team, opp, year=None, opp_ranked=False):
    """Rating points this team carries into a game."""
    if getattr(team, "fcs", False):
        return 0.0
    st = team.__dict__.get("tmom")
    if not st or (year is not None and st[0] != year):
        return 0.0                                                  # a new season starts level
    v = st[1]
    if v > 0:
        out = v * MAX_UP
        if opp is not None and team.team_ovr - opp.team_ovr >= 8:
            out *= 0.5                                              # the trap game
        return out
    out = v * MAX_DOWN
    if opp is not None:
        rival = False
        try:
            import rivalries
            rival = rivalries.is_rivalry(team, opp)
        except Exception:                                          # noqa: BLE001, S110
            pass
        if rival or opp_ranked:
            out *= 0.5                                              # nothing to lose
    return out


def line(team):
    """'Rolling ▲ (W W L W W)' for a team page."""
    st = team.__dict__.get("tmom")
    w, arrow = word(team)
    form = " ".join(st[2][-5:]) if st and st[2] else ""
    return f"{w} {arrow}" + (f"  (last {len(st[2][-5:])}: {form})" if form else "")
