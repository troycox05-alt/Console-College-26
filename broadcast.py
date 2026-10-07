"""
broadcast.py — When every game kicks off.

assign(league, week, games) gives each game a date, a day, a kickoff time (Eastern)
and a window, then returns the games in the order they're played.

  Weeknights   Thursday and Friday nights every week (extra on opening week),
               a Labor Day game, Lake Country Lights on Tuesday/Wednesday in November, and
               Thanksgiving Thursday / Black Friday on Rivalry Week
  Saturday     Noon, 3:30, and primetime; the biggest game gets the national
               primetime window. West Coast teams play late (10:30 ET), and
               Hawaii kicks off at midnight Eastern. Nobody out West plays at
               9 a.m. local.
  Postseason   championship weekend, bowls on their dates, the playoff windows,
               and the title game on a Monday night
"""
import world
import random
from datetime import date, timedelta

from recruiting_data import STATES

TZ_BY_STATE = {  # hours behind Eastern
    **{s: 0 for s in ("CT", "DE", "FL", "GA", "IN", "KY", "MA", "MD", "ME", "MI", "NC", "NH", "NJ", "NY", "OH", "PA",
                      "RI", "SC", "VA", "VT", "WV", "DC")},
    **{s: 1 for s in ("AL", "AR", "IA", "IL", "KS", "LA", "MN", "MO", "MS", "ND", "NE", "OK", "SD", "TN", "TX", "WI")},
    **{s: 2 for s in ("AZ", "CO", "ID", "MT", "NM", "UT", "WY")},
    **{s: 3 for s in ("CA", "NV", "OR", "WA")},
    "HI": 6,
}
STATE_ABBR = {v[0]: k for k, v in STATES.items()}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
POWER = world.POWER
# Rivalry Week's holiday games, the conferences that play Thursday/Friday nights, and the rivalry
# that gets the noon showcase window on its Saturday.
THANKSGIVING = {frozenset(("Mississippi", "Mississippi State"))}
BLACK_FRIDAY = {frozenset(p) for p in (("Iowa", "Nebraska"), ("Arkansas", "Missouri"), ("Arizona", "Arizona State"),
                                       ("Colorado", "Utah"))}
WEEKNIGHT_CONFS = ("Coastal Plains", "Federal", "Crossroads", "Seaboard", "High Country", "Continental", "Golden West")
NOON_SHOWCASE = ("Michigan", "Ohio State")


def tz_of(game):
    """Hours behind Eastern where the game is played."""
    if game.neutral and game.venue and ", " in game.venue:
        tail = game.venue.split(", ")[-1].strip()
        code = STATE_ABBR.get(tail, tail if len(tail) == 2 else None)
        if code in TZ_BY_STATE:
            return TZ_BY_STATE[code]
    return TZ_BY_STATE.get(getattr(game.home, "home_state", None), 0)


def season_saturday(year, week):
    """Week 1's Saturday is the first Saturday of September."""
    d = date(year, 9, 1)
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d + timedelta(weeks=week - 1)


def clock(minutes):
    if minutes >= 23 * 60 + 59:
        return "11:59 PM"
    h, m = divmod(minutes, 60)
    ampm = "AM" if h < 12 else "PM"
    h = h % 12 or 12
    return f"{h}:{m:02d} {ampm}" if m else ("Noon" if (h, ampm) == (12, "PM") else f"{h} {ampm}")


def when(game, short=False):
    """'Sat, Sep 5 · 7:30 PM ET' — and the window if it has a name."""
    d = getattr(game, "date", None)
    k = getattr(game, "kick", None)
    if d is None or k is None:
        return ""
    day = f"{DAYS[d.weekday()]}, {d.strftime('%b')} {d.day}"
    t = clock(k)
    s = f"{day} · {t}" + ("" if t == "Noon" else " ET")
    if not short and getattr(game, "window", None):
        s += f" · {game.window}"
    return s


def time_words(game):
    """How the Campus Countdown crew says it: '7:30 tonight', '3:30 this afternoon', 'noon'."""
    k = getattr(game, "kick", None)
    if k is None:
        return "later today"
    t = clock(k).replace(" PM", "").replace(" AM", "")
    if k >= 23 * 60:
        return "midnight Eastern"
    if k >= 17 * 60:
        return f"{t} tonight"
    if k >= 13 * 60:
        return f"{t} this afternoon"
    return "noon" if k == 12 * 60 else f"{t} this morning"


def at_time(game):
    """time_words() ready for a sentence: 'at noon', 'at 7:30 tonight', 'later today'."""
    w = time_words(game)
    return f"at {w}" if w[0].isdigit() or w.startswith(("noon", "midnight")) else w


def _interest(league, g):
    R = league.rankings
    ra, rh = R.rank_of(g.away), R.rank_of(g.home)
    s = (26 - ra if ra else 0) + (26 - rh if rh else 0) + (15 if ra and rh else 0)
    from commentary import rivalry_name
    if rivalry_name(g.home, g.away):
        s += 12
    s += (g.home.prestige + g.away.prestige) / 12
    if getattr(g.away, "fcs", False) or getattr(g.home, "fcs", False):
        s -= 30
    return s


def _set(g, day_date, kick, window):
    g.date, g.kick, g.window = day_date, kick, window


def assign(league, week, games):
    if not games:
        return games
    rng = random.Random(f"slots:{league.seed}:{league.year}:{week}")
    if week > 13:
        _postseason(league, week, games, rng)
    else:
        _regular(league, week, games, rng)
    games.sort(key=lambda g: (g.date, g.kick, -_interest(league, g)))
    return games


def _regular(league, week, games, rng):
    sat = season_saturday(league.year, week)
    thu, fri = sat - timedelta(days=2), sat - timedelta(days=1)
    left = sorted(games, key=lambda g: -_interest(league, g))
    fbs_only = [g for g in left if not getattr(g.away, "fcs", False)]

    def take(pred, n):
        out = [g for g in left if pred(g)][:n]
        for g in out:
            left.remove(g)
        return out

    rivalry_week = week == 13
    if rivalry_week:
        from season import RIVALRY_WEEK
        riv = {frozenset(p) for p in RIVALRY_WEEK}
        is_riv = lambda g: frozenset((g.home.school, g.away.school)) in riv
        thanksgiving = set(THANKSGIVING)
        black_friday = set(BLACK_FRIDAY)
        pair = lambda g: frozenset((g.home.school, g.away.school))
        for g in take(lambda g: pair(g) in thanksgiving, 1):
            _set(g, thu, 19 * 60 + 30, "Thanksgiving Night")
        for i, g in enumerate(take(lambda g: pair(g) in black_friday, 4)):
            _set(g, fri, (12 * 60, 15 * 60 + 30, 19 * 60 + 30, 22 * 60)[i], "Black Friday")
        for g in take(lambda g: g.home.conference == world.WEEKNIGHT_CONF and g.conference_game, 2):
            _set(g, fri, 12 * 60, "Black Friday")
    if week == 1:
        big = [g for g in fbs_only if g.home.conference in POWER and g.away.conference in POWER
               and g.home.conference != g.away.conference]
        if big:
            g = big[0]
            if g in left:
                left.remove(g)
                _set(g, sat + timedelta(days=2), 20 * 60, "Labor Day")
        if len(big) > 1 and big[1] in left:
            left.remove(big[1])
            _set(big[1], sat + timedelta(days=1), 19 * 60 + 30, "Sunday Night")
        small = lambda g: (not getattr(g.away, "fcs", False) and _interest(league, g) < 45
                           and not league.rankings.rank_of(g.home) and not league.rankings.rank_of(g.away)
                           and not {g.home.conference, g.away.conference} & set(world.BIG_TWO))
        for i, g in enumerate(take(lambda g: small(g) and tz_of(g) <= 1, 5)):
            _set(g, thu, (19 * 60, 19 * 60 + 30, 20 * 60, 19 * 60 + 30, 21 * 60)[i], "Thursday Night")
        for i, g in enumerate(take(small, 3)):
            _set(g, fri, 19 * 60 + 30 + (30 * tz_of(g)), "Friday Night")
    elif not rivalry_week:
        if 10 <= week <= 12:
            mac = take(lambda g: g.home.conference == world.WEEKNIGHT_CONF and g.conference_game, 4)
            for i, g in enumerate(mac):
                _set(g, sat - timedelta(days=4 if i < 2 else 3), 19 * 60, "Lake Country Lights")
        weeknight = lambda g: (g.home.conference in WEEKNIGHT_CONFS and not getattr(g.away, "fcs", False)
                               and 20 <= _interest(league, g) < 48
                               and not (league.rankings.rank_of(g.home) and league.rankings.rank_of(g.away)))
        for i, g in enumerate(take(lambda g: weeknight(g) and tz_of(g) <= 1, rng.choice((1, 2)))):
            _set(g, thu, 19 * 60 + 30, "Thursday Night")
        for i, g in enumerate(take(weeknight, rng.choice((1, 2, 2, 3)))):
            _set(g, fri, (19 * 60 if tz_of(g) <= 1 else 22 * 60), "Friday Night")

    # Saturday: the national primetime game first, then the marquee afternoon, then everybody else.
    if rivalry_week:                                   # the showcase rivalry is a noon kickoff
        for g in take(lambda g: {g.home.school, g.away.school} == set(NOON_SHOWCASE), 1):
            _set(g, sat, 12 * 60, "High Noon")
    for g in take(lambda g: tz_of(g) <= 2, 1):         # national primetime: the best game that can kick at 7:30 ET
        _set(g, sat, 19 * 60 + 30, "Primetime")
    for g in take(lambda g: True, 1):
        _set(g, sat, 15 * 60 + 30 if tz_of(g) <= 3 else 22 * 60 + 30, "Marquee")
    if not any(getattr(x, "window", None) == "High Noon" and x.date == sat for x in games):
        for g in take(lambda g: tz_of(g) <= 1, 1):
            _set(g, sat, 12 * 60, "High Noon")
    for g in list(left):
        tz = tz_of(g)
        if getattr(g.home, "home_state", None) == "HI" or tz >= 6:
            _set(g, sat, 23 * 60 + 59, "Island Time")
            continue
        if tz == 3:
            opts = [(15 * 60 + 30, 3), (19 * 60, 3), (22 * 60 + 30, 4)]
        elif tz == 2:
            opts = [(15 * 60 + 30, 3), (19 * 60, 3), (21 * 60 + 30, 3)]
        else:
            sec_night = g.home.conference == world.NIGHT_CONF
            opts = [(12 * 60, 3 if not sec_night else 2), (15 * 60 + 30, 3),
                    (19 * 60, 2 if not sec_night else 4), (19 * 60 + 30, 1), (20 * 60, 1)]
            if getattr(g.away, "fcs", False) or getattr(g.home, "fcs", False):
                opts = [(12 * 60, 4), (13 * 60, 2), (15 * 60 + 30, 2), (19 * 60, 1)]
        kick = rng.choices([o[0] for o in opts], weights=[o[1] for o in opts])[0]
        window = "Late Night" if kick >= 22 * 60 else None
        _set(g, sat, kick, window)


def _postseason(league, week, games, rng):
    import postseason as ps
    dates = ps.postseason_dates(league.year)
    if week == 14:
        ccg = sorted(games, key=lambda g: -_interest(league, g))
        fri = dates["ccg"] - timedelta(days=1)
        slots = [(dates["ccg"], 20 * 60), (dates["ccg"], 16 * 60), (dates["ccg"], 12 * 60), (dates["ccg"], 20 * 60),
                 (dates["ccg"], 16 * 60), (dates["ccg"], 12 * 60), (fri, 20 * 60), (fri, 19 * 60),
                 (dates["ccg"], 15 * 60 + 30), (dates["ccg"], 19 * 60)]
        for g, (d, k) in zip(ccg, slots + [(dates["ccg"], 12 * 60)] * 20):
            _set(g, d, k, "Championship Saturday" if d == dates["ccg"] else "Championship Friday")
        return
    for g in games:
        d = getattr(g, "date", None) or dates["ccg"]
        gt = g.game_type
        if gt == "National Championship":
            _set(g, d, 19 * 60 + 30, "National Championship")
        elif gt == "NP Semifinal":
            _set(g, d, 19 * 60 + 30, "Playoff Semifinal")
        elif gt == "NP Quarterfinal":
            same_day = [x for x in games if x.game_type == gt and x.date == d]
            k = (12 * 60, 16 * 60, 20 * 60)[same_day.index(g) % 3] if len(same_day) > 1 else 19 * 60 + 30
            _set(g, d, k, "Playoff Quarterfinal")
        elif gt == "NP First Round":
            same_day = [x for x in games if x.game_type == gt and x.date == d]
            k = (20 * 60, 12 * 60, 16 * 60)[same_day.index(g) % 3] if len(same_day) > 1 else 20 * 60
            _set(g, d, k, "Playoff First Round")
        else:
            same_day = [x for x in games if x.game_type == "Bowl" and x.date == d]
            k = (12 * 60, 15 * 60 + 30, 19 * 60 + 30, 21 * 60)[same_day.index(g) % 4]
            _set(g, d, k, None)
