"""
impact.py — How much one player's game actually mattered.

Shared by the broadcast's player of the game, the Players of the Week, and the
Golden Helmet race, so the same performance is judged the same way everywhere.
Efficiency counts, not just volume: 300 yards on 52 attempts with two picks is
not 300 yards on 29 attempts, and a back's 110 yards on 31 carries is not his
110 on 14. Turnovers and sacks cost you. Defenders and kickers can win it,
but they need a game that changed the result.
"""


def offense_impact(c):
    att, cmp_, yds = c["pass_att"], c["pass_cmp"], c["pass_yds"]
    v = 0.0
    if att:
        ypa = yds / att
        v += yds * 0.065 + c["pass_td"] * 4.4 - c["pass_int"] * 5.0 - c["sacked"] * 0.7
        v += (cmp_ / att - 0.58) * att * 0.35            # completing throws
        v += (ypa - 6.5) * att * 0.12                    # and making them count
    carries = c["rush_att"]
    if carries:
        v += c["rush_yds"] * 0.105 + c["rush_td"] * 4.6
        if carries >= 8:
            v += (c["rush_yds"] / carries - 4.6) * carries * 0.22
        if c["rush_yds"] >= 100:
            v += 2.0                                     # a hundred-yard day carries an offense
    # A yard is a yard: receivers and backs are weighed on the same scale (catches get
    # a little for moving the chains), so a 78-yard receiver doesn't beat a 103-yard back.
    v += c["rec_yds"] * 0.11 + c["rec_td"] * 5.0 + c["rec"] * 0.35
    v -= c["fumbles"] * 3.5
    v += (c["kr_td"] + c["pr_td"]) * 6 + (c["kr_yds"] + c["pr_yds"]) * 0.03
    return v


def defense_impact(c):
    return (c["tkl"] * 0.7 + max(0, c["tkl"] - 10) * 0.3 + c["tfl"] * 2.0 + c["sack"] * 4.0 + c["int"] * 6.5 + c["pbu"] * 1.4
            + c["ff"] * 4.5 + c["fr"] * 3.0 - c["missed_tkl"] * 0.4)


def kicking_impact(c):
    miss_fg = c["fg_att"] - c["fg_made"]
    miss_xp = c["xp_att"] - c["xp_made"]
    v = c["fg_made"] * 2.6 + max(0, c["fg_long"] - 45) * 0.25 - miss_fg * 3.0 - miss_xp * 2.0
    return v if c["fg_att"] >= 3 else min(v, 4.0)       # a kicker needs a real day to win anything


def game_impact(c):
    """Total single-game value, all phases."""
    return offense_impact(c) + defense_impact(c) * 0.95 + kicking_impact(c)


def player_of_the_game(sim):
    """(player, team, side) — the player who decided this game. Voters and
    broadcasters give it to someone on the winning side unless a loser was
    clearly the best player on the field."""
    home, away = sim.home, sim.away
    winner = home if sim.score[home] > sim.score[away] else away if sim.score[away] > sim.score[home] else None
    best, best_v = None, -1e9
    for p, c in sim.stats.items():
        team = sim.team_of(p)
        v = game_impact(c)
        if winner is not None and team is not winner:
            v *= 0.72
        if v > best_v:
            best, best_v = (p, team), v
    if best is None:
        return None, None, None
    p, t = best
    c = sim.stats[p]
    side = "def" if defense_impact(c) * 0.95 > offense_impact(c) and defense_impact(c) > kicking_impact(c) else \
        "st" if kicking_impact(c) > max(offense_impact(c), defense_impact(c)) else "off"
    return p, t, side
