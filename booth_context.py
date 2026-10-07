"""
booth_context.py — What the booth knows about the day: form, rivalry heat, upset alerts,
trap games, bowl math, revenge, and the playoff race. Each function takes the narrator
and the sim and returns a short exchange [(speaker, line)] or None. Nothing here touches
the game.
"""
import random


def _p(nar, *opts):
    return nar.rng.choice(opts)


def _form(team):
    st = team.__dict__.get("tmom")
    return st[2] if st else []


def _streak(res):
    if not res:
        return None, 0
    n = 1
    while n < len(res) and res[-n - 1] == res[-1]:
        n += 1
    return res[-1], n


NUM = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def form(nar, sim):
    """Who came in hot, who came in cold."""
    if nar.post:
        return None
    for t in sorted(sim.teams, key=lambda x: random.random()):
        res = _form(t)
        kind, n = _streak(res)
        if kind == "W" and n >= 3:
            return [("P", _p(nar, f"{t.school} came in on a {NUM.get(n, n)}-game winning streak.",
                             f"{t.school} has won {NUM.get(n, n)} straight coming into today.",
                             f"Nobody's beaten {t.school} since {_ago(n)}.")),
                    ("A", _p(nar, "You can see it in how they carry themselves. They expect to win now.",
                             "Winning becomes a habit. They don't panic when it gets tight.",
                             "That's a confident group. The question is whether somebody's finally punched them.",
                             "When you're rolling like that, the close ones start going your way."))]
        if kind == "L" and n >= 3:
            return [("P", _p(nar, f"{t.school} has dropped {NUM.get(n, n)} in a row.",
                             f"It's been a rough stretch for {t.school}: {NUM.get(n, n)} straight losses coming in.")),
                    ("A", _p(nar, "The tape tells you they're pressing. Guys trying to make every play themselves.",
                             "Losing streaks are as much between the ears as anything. One good quarter can change it.",
                             "You find out who your leaders are in a stretch like this.",
                             "They need something good to happen early, just to exhale."))]
        if len(res) >= 4 and res[-4:].count("W") == 3 and res[-1] == "W" and res[-2] == "L":
            return [("A", _p(nar, f"{t.school} answered that loss the right way last week. That's a sign of a mature team.",
                             f"Credit {t.school} — they didn't let one bad Saturday turn into two."))]
    return None


def _ago(n):
    return {3: "three weeks ago", 4: "about a month ago", 5: "early in the year"}.get(n, "the start of the year")


def rivalry_heat(nar, sim):
    """Throw the records out."""
    if not getattr(sim, "rivalry", False) or nar._used.get("rivalry_heat", 0) >= 2:
        return None
    nar._used["rivalry_heat"] = nar._used.get("rivalry_heat", 0) + 1
    dog, fav = sorted(sim.teams, key=lambda x: x.team_ovr)
    gap = fav.team_ovr - dog.team_ovr
    if gap >= 4:
        return [("P", _p(nar, f"On paper, {fav.school} should handle this one.",
                         f"{fav.school} came in as the clear favorite.",
                         f"Everybody picked {fav.school} this week.")),
                ("A", _p(nar, f"Paper doesn't play in rivalry games. {dog.school} has been waiting all year for this one.",
                         f"Throw the records out. {dog.school}'s season can be made in one afternoon.",
                         f"This is {dog.school}'s bowl game, their Super Bowl. Expect their best four quarters of the year.",
                         f"The favorite has everything to lose today. {dog.school} has nothing to lose, and that's dangerous."))]
    return [("A", _p(nar, "These two genuinely do not like each other. Every snap's got a little extra on it.",
                     "Rivalry football. The hits are a half-second later and a little harder.",
                     "You can tell the players grew up hearing about this game. It means more.",
                     "Twelve months of bragging rights on the line. Nobody in this building is sitting down."))]


def upset_alert(nar, sim):
    """An underdog in front in the second half."""
    if sim.quarter < 3:
        return None
    ranks = getattr(sim.game, "ranks", {}) or {}
    for t in sim.teams:
        o = sim.other(t)
        r_o, r_t = ranks.get(o), ranks.get(t)
        lead = sim.score[t] - sim.score[o]
        if lead > 0 and r_o and (not r_t or r_t - r_o >= 8):
            if nar._used.get("upset_alert"):
                return None
            nar._used["upset_alert"] = True
            tag = f"No. {r_o} {o.school}"
            return [("P", _p(nar, f"Upset alert. {t.school} leads {tag} in the {_q(sim)}.",
                             f"Somebody tell the rest of the country: {t.school} is in front of {tag}.",
                             f"{tag} is in real trouble here.")),
                    ("A", _p(nar, f"{t.school} isn't hanging around anymore. They believe they can win this game.",
                             f"The longer this stays close, the tighter {o.school} is going to play.",
                             "This is how upsets happen. The favorite keeps waiting for the run, and it never comes.",
                             f"{o.school} has been in this spot before. Now we find out what they're made of."))]
    return None


def _q(sim):
    return {3: "third quarter", 4: "fourth quarter"}.get(sim.quarter, "second half")


def trap(nar, sim):
    """A heavy favorite that's sleepwalking."""
    if sim.quarter not in (2, 3):
        return None
    fav, dog = sorted(sim.teams, key=lambda x: -x.team_ovr)
    if fav.team_ovr - dog.team_ovr < 8 or sim.score[fav] > sim.score[dog] + 3:
        return None
    if nar._used.get("trap"):
        return None
    nar._used["trap"] = True
    nxt = ""
    try:
        if nar.league is not None:
            import week as wk
            g = wk.next_game(nar.league, fav)
            if g is not None and g is not sim.game:
                opp = g.opponent_of(fav)
                if nar.league.rankings.rank_of(opp):
                    nxt = f" with {opp.school} on deck next week"
    except Exception:                                      # noqa: BLE001
        nxt = ""
    return [("P", f"{fav.school} has not put this one away{nxt}."),
            ("A", _p(nar, "Classic trap game. You can't coach against human nature; kids look ahead.",
                     f"{dog.school} is playing with nothing to lose, and {fav.school} looks like it's waiting for it to be easy.",
                     "This is the kind of game that costs you a season if you don't respect it.",
                     "Flat. That's the word. They came out flat and they haven't found a spark yet."))]


def bowl_math(nar, sim):
    """Six wins, or the season's over."""
    if nar.post or sim.game.week < 8:
        return None
    for t in sim.teams:
        if getattr(t, "fcs", False):
            continue
        if t.wins == 5 and t.losses >= 3:
            return [("P", f"{t.school} is sitting on five wins."),
                    ("A", _p(nar, "Win today and they're bowl eligible. That's fifteen extra practices and a trip for "
                                  "the seniors.",
                             "Six is the magic number. Get there today and the season keeps going into December.",
                             "For a program like this, a bowl game matters. The extra practices alone are worth it."))]
        if t.losses == 6 and t.wins >= 3:
            return [("A", _p(nar, f"{t.school} has six losses. One more and there's no bowl.",
                             f"Lose today and {t.school}'s season ends in November. Every snap matters to them."))]
    return None


def revenge(nar, sim):
    """They lost this one last year and haven't forgotten."""
    if nar.league is None:
        return None
    try:
        import rivalries
        s = rivalries.series(nar.league, sim.home.school, sim.away.school)
        last = s.last
    except Exception:                                      # noqa: BLE001
        return None
    if last is None or nar.league.year - last.year != 1 or nar._used.get("revenge"):
        return None
    nar._used["revenge"] = True
    return [("P", f"Last year it was {last.winner} {last.wscore}, {last.loser} {last.lscore}."),
            ("A", _p(nar, f"You'd better believe {last.loser} has had this one circled since the day the schedule came out.",
                     f"I talked to a couple of {last.loser} players this week. They remember every detail of that game.",
                     f"{last.loser} has been living with that one for twelve months. Today's their shot."))]


def race(nar, sim):
    """November: the playoff and conference races."""
    if nar.post or nar.league is None or sim.game.week < 9:
        return None
    try:
        import committee
        cm = committee.get(nar.league)
        if not cm.released:
            return None
        for t in sim.teams:
            r = cm.rank_of(t)
            if r and r <= 14:
                if r <= 4:
                    tail = _p(nar, "Win out and they're getting a bye. Lose, and it gets complicated fast.",
                              "They control their own destiny. That's all you can ask for in November.")
                elif r <= 12:
                    tail = _p(nar, "They're in the field right now. A loss today and they're sweating out Selection Day.",
                              "Every week now is an elimination game for a team in that spot.")
                else:
                    tail = _p(nar, "They need help, but a win today keeps them on the board.",
                              "They're on the outside looking in. Style points matter today.")
                return [("P", f"{t.school} came in at No. {r} in the playoff rankings."), ("A", tail)]
    except Exception:                                      # noqa: BLE001
        return None
    return None


TOPICS = (form, rivalry_heat, upset_alert, trap, bowl_math, revenge, race)
