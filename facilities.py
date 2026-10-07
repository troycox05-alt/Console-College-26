"""
facilities.py — What a program has built, and who shows up to see it.

THREE FACILITIES, each rated 1 (crumbling) to 10 (elite)
  Recruiting   the football building, the recruiting lounge, the gameday
               suite. Every pitch to a recruit lands a little harder (0.94x at 1,
               1.12x at 10), and it's most of what a kid means by "facilities".
  Training     weight room, sports science, nutrition, indoor practice. Players
               develop faster every offseason (0.94x at 1, 1.08x at 10).
  Stadium      built piece by piece — see stadium.py. A lower bowl, end zone
               stands, upper decks, suites, a video board, the locker rooms, the
               recruiting lounge... every part adds seats, noise, money or a
               recruiting edge. Its 1-10 grade here is what the parts add up to.

Every program starts somewhere different. Recruiting and training upgrades are
one-time purchases out of next season's player-NIL pool, one project a season,
and each level costs more than the last. Stadium projects run on their own
(one at a time, some take years, some are paid with bonds). Every offseason
things wear: a facility can slip a level, a stadium part can age a tier. The
CPU manages its own; you manage yours.

ATTENDANCE
  Every home game draws a crowd: the program's fan base, how the season is
  going (a good program playing badly empties seats), last season, the poll,
  the opponent, and the stadium itself. Rivalry games and big home openers
  sell out. The crowd is the home-field advantage: a packed, loud building is
  worth more than a half-empty one.
"""
import world
import random

from finance import M, available, class_target, money

KINDS = ("recruiting", "training", "stadium")
LABELS = {"recruiting": "Recruiting Facilities", "training": "Training Facilities", "stadium": "Stadium"}
SHORT = {"recruiting": "Recruiting", "training": "Training", "stadium": "Stadium"}
BLURB = {"recruiting": "every recruiting pitch lands harder; what recruits mean by 'facilities'",
         "training": "players develop faster every offseason",
         "stadium": "built part by part: seats, noise, premium money, what recruits see on a game-day visit"}

# Cost of reaching each level (one-time). The stadium costs twice as much.
LEVEL_COST = {2: 0.3, 3: 0.5, 4: 0.8, 5: 1.2, 6: 1.8, 7: 2.7, 8: 4.0, 9: 6.0, 10: 9.0}
STADIUM_MULT = 2.0
DEGRADE_BASE = 0.02          # yearly chance a facility slips a level: 2% + 0.8% per level (10% at elite)
DEGRADE_PER_LEVEL = 0.008
SEATS_PER_LEVEL = 0.03       # a stadium upgrade adds 3% more seats (at least 1,500)
PREMIUM_PER_FAN = 5.0        # $ per fan per home game for each stadium level above where the program started
TICKET = 45.0                # $ per new seat actually sold
HOME_GAMES = 6

GRADES = ((9, "Elite"), (7, "Great"), (5, "Solid"), (3, "Aging"), (1, "Poor"))


def grade(level):
    return next(w for lo, w in GRADES if level >= lo)


def cost(kind, level_to):
    base = LEVEL_COST.get(level_to, 0) * M
    return int(base * (STADIUM_MULT if kind == "stadium" else 1))


# ═══ State ══════════════════════════════════════════════════════════════════

def ensure(team):
    """Seed a program's facilities the first time they're needed (new worlds and old saves)."""
    fac = getattr(team, "fac", None)
    if fac:
        if not getattr(team, "stad", None):
            import stadium
            stadium.ensure(team)                 # an old save: break the stadium into parts
        return fac
    r = random.Random(f"facilities:{team.school}")
    base = 1 + (team.ratings.get("facilities", 70) - 50) / 5.3     # the old 50-99 rating, spread over 1-10
    cap = getattr(team, "capacity", 40000)
    stadium = 2 + min(7.5, cap / 13500) + (team.prestige - 60) / 25
    fac = {"recruiting": base + r.gauss(0, 0.9), "training": base + r.gauss(-0.3, 0.9),
           "stadium": stadium + r.gauss(0, 0.7)}
    fac = {k: int(max(1, min(10, round(v)))) for k, v in fac.items()}
    team.fac = fac
    team.fac_start = dict(fac)                   # what the budget was built around
    team.base_capacity = cap
    team.fac_log = []                            # (year, what happened)
    team.fac_spend = []                          # (season it comes out of, amount, what)
    import stadium
    stadium.ensure(team)                         # the stadium's parts; its grade becomes fac["stadium"]
    sync_rating(team)
    return fac


def level(team, kind):
    f = ensure(team)
    if kind == "stadium" and not getattr(team, "stad", None):
        import stadium
        stadium.ensure(team)                     # an old save: break the stadium into parts now
    return f[kind]


def ensure_all(league):
    import stadium
    for t in league.teams:
        ensure(t)
        stadium.ensure(t)


def sync_rating(team):
    """The old single 'facilities' rating (prestige, recruiting score, broadcast chatter)
    follows the three real ones."""
    f = team.fac
    avg = f["recruiting"] * 0.4 + f["training"] * 0.3 + f["stadium"] * 0.3
    team.ratings["facilities"] = int(round(max(1, min(99, 50 + (avg - 1) * 5.3))))     # same 50-99 scale as before


def spend_in(team, year):
    return sum(a for y, a, _ in getattr(team, "fac_spend", []) if y == year)


# ═══ Effects ════════════════════════════════════════════════════════════════

def pitch_value(team):
    """0-100 'facilities' as a recruit weighs it: the football building, the weight room, the stadium."""
    f = ensure(team)
    import stadium
    return int(round((f["recruiting"] * 0.5 + f["training"] * 0.25) * 10 + stadium.recruit_score(team) * 0.25))


def recruiting_mult(team):
    import stadium
    return 0.92 + level(team, "recruiting") * 0.02 + (stadium.recruit_score(team) - 50) * 0.0008


def training_rating(team):
    """The 0-100 number development.py expects (0.936x at level 1 ... 1.08x at 10)."""
    return level(team, "training") * 10


# ═══ Attendance ═════════════════════════════════════════════════════════════

def _is_home_opener(league, game):
    for g in league.team_games(game.home):
        if g is game:
            return True
        if g.home is game.home and not g.neutral and (g.played or g.week < game.week):
            return False
    return False


def forecast(league, game, rng=None):
    """(attendance, capacity, fill 0-1, why) for a game. With rng, the real turnout
    (a little noise); without, the expected one."""
    from commentary import rivalry_name
    h, a = game.home, game.away
    R = league.rankings
    if game.neutral:
        cap = {1: 62000, 2: 42000, 3: 30000}.get(getattr(game, "tier", None), 72000) \
            if game.game_type == "Bowl" else 74000
        if game.game_type in ("National Championship", "NP Semifinal", "NP Quarterfinal"):
            fill, why = 1.0, "sold out"
        else:
            draw = (h.prestige + a.prestige) / 2
            fill = 0.62 + (draw - 60) * 0.008 + (0.05 if R.rank_of(h) or R.rank_of(a) else 0)
            why = "neutral site"
        if rng is not None:
            fill += rng.gauss(0, 0.03)
        fill = max(0.4, min(1.0, fill))
        return int(cap * fill), cap, fill, why
    if getattr(h, "fcs", False):
        cap = h.capacity
        fill = 0.7
        return int(cap * fill), cap, fill, ""
    ensure(h)
    import stadium
    stadium.ensure(h)
    cap = h.capacity
    fans = stadium.fanbase(h)                      # the crowd a full-interest Saturday brings
    fill = 0.55 + (h.prestige - 60) * 0.006 + (h.ratings.get("tradition", 60) - 60) * 0.003
    why = []
    games = h.wins + h.losses
    pct = h.wins / games if games else None
    if pct is not None and games >= 2:
        fill += (pct - 0.5) * 0.30
        if h.prestige >= 70 and pct < 0.5 and games >= 3:
            fill -= 0.08                           # a program that expects to win, losing: empty seats
            why.append("a disappointing season")
        elif pct >= 0.75:
            why.append("a winning season")
    last = getattr(h, "last_win_pct", None)
    if last is not None and game.week <= 5:
        fill += (last - 0.5) * 0.12
    hr, ar = R.rank_of(h), R.rank_of(a)
    if hr:
        fill += 0.10 if hr <= 10 else 0.06
    if ar:
        fill += 0.12 if ar <= 10 else 0.08
        why.append(f"No. {ar} {a.school} in town")
    if getattr(a, "fcs", False):
        fill -= 0.10
    elif a.conference in world.POWER or a.school == world.FLAGSHIP_INDEPENDENT:
        fill += 0.03
    if game.week >= 11 and pct is not None and pct < 0.5:
        fill -= 0.05                               # cold November, nothing to play for
    fill += stadium.comfort(h)                     # concourses, the plaza, the board: a Saturday people like
    wx = getattr(game, "wx", None)
    if wx and not wx.get("indoor"):
        import weather
        hit = weather.turnout_hit(wx, stadium.parts(h).get("canopy", 0))
        if pct is not None and pct < 0.5:
            hit *= 1.5                             # nobody sits in the rain to watch a losing team
        fill -= hit
        if hit >= 0.04:
            why.append(weather.label(wx).lower() + " kept some fans home")
    import ad_mode
    fill += ad_mode.fill_shift(league, game)       # your fans' mood and your ticket prices (AD mode)
    if getattr(game, "kick", None) is not None and game.kick >= 18 * 60:
        fill += 0.03 + stadium.night_bonus(h)      # a night game (under the LED show, an event)
    if rng is not None:
        fill += rng.gauss(0, 0.035)
    # "fill" so far is turnout: the share of the fan base that comes. The games that always sell
    # pull in more than the usual crowd — enough to sell out a stadium the fan base can fill.
    big = False
    if rivalry_name(h, a):
        big, why = True, ["rivalry game"]
    elif game.game_type != "Regular Season":
        big, why = True, ["postseason"]
    elif _is_home_opener(league, game):
        if h.prestige >= 55 or ar:
            big, why = True, ["home opener"]
        else:
            fill += 0.12
            why.append("home opener")
    turnout = max(0.28, min(1.2, fill))            # above 1: more want in than usually come
    if big:
        turnout = max(turnout, 1.12)
    demand = fans * turnout
    att = min(cap, demand)
    fill = att / cap
    if demand >= cap * 0.985:
        fill = 1.0
        att = cap * (rng.uniform(1.0, 1.025) if rng is not None else 1.0)   # announced crowds run over capacity
    elif fill < 0.55 and cap > fans * 1.15:
        why.append("more seats than fans")
    return int(att), cap, fill, ", ".join(why)


def set_attendance(league, game):
    """Called at kickoff: the real crowd for this game."""
    rng = random.Random(f"att:{league.year}:{game.week}:{game.home.school}:{game.away.school}")
    att, cap, fill, why = forecast(league, game, rng)
    game.attendance, game.capacity, game.fill, game.crowd_why = att, cap, fill, why
    game.sellout = fill >= 0.985
    import stadium
    game.stadium_level = stadium.noise_rating(game.home) if not game.neutral and not getattr(game.home, "fcs", False) else 5
    import ad_mode
    game.stadium_level += ad_mode.noise_shift(league, game)


def crowd_noise(game):
    """0.3 (sparse) .. ~1.3 (100,000 packed into an elite building): how much the crowd is worth."""
    att = getattr(game, "attendance", None)
    if att is None:
        return 1.0
    fill = getattr(game, "fill", 0.85)
    size = 0.6 + 0.4 * min(1.4, att / 65000)
    return max(0.25, fill ** 1.5 * size + (getattr(game, "stadium_level", 5) - 5) * 0.03)


def attendance_line(game):
    att = getattr(game, "attendance", None)
    if att is None:
        return ""
    if getattr(game, "sellout", False):
        return f"Attendance {att:,} (sellout)"
    return f"Attendance {att:,} ({getattr(game, 'fill', 0) * 100:.0f}% full)"


# ═══ Money ══════════════════════════════════════════════════════════════════

def season_revenue(league, team):
    """(total, premium, new seats) the stadium brought in this season beyond what the budget assumed:
    new seats sold, and premium (club seats, suites, concessions, video-board ads) from parts built since."""
    import stadium
    ensure(team)
    total, parts = stadium.revenue(league, team)
    seats = parts.get("new seats", 0)
    return total, total - seats, seats


def can_upgrade(league, team, kind):
    """(ok, cost, reason)."""
    f = ensure(team)
    if kind == "stadium":
        return False, 0, "the stadium is built part by part — open the stadium screen"
    if f[kind] >= 10:
        return False, 0, "already elite — as good as it gets"
    done = [y for y, _, what in getattr(team, "fac_spend", []) if what.startswith("upgrade") and y == league.year + 1
            and "stadium" not in what]
    if done:
        return False, 0, "one construction project a season — you already have one underway"
    c = cost(kind, f[kind] + 1)
    import skills
    if skills.team_has(team, "groundbreaker"):
        c = int(c * 0.85)                                 # Groundbreaker (coaching tree)
    left = available(league, team)
    if left < c:
        return False, c, f"it costs {money(c)} and you have {money(left)} available"
    return True, c, ""


def upgrade(league, team, kind, who="the AD"):
    ok, c, why = can_upgrade(league, team, kind)
    if not ok:
        return False, why
    f = team.fac
    f[kind] += 1
    team.fac_spend.append((league.year + 1, c, f"upgrade {SHORT[kind].lower()} to {f[kind]}"))
    if kind == "stadium":
        add = max(1500, int(team.capacity * SEATS_PER_LEVEL / 100) * 100)
        team.capacity += add
        extra = f", adding {add:,} seats (capacity {team.capacity:,})"
    else:
        extra = ""
    team.fac_log.append((league.year, f"{LABELS[kind]} upgraded to {f[kind]} ({grade(f[kind])}) for {money(c)}{extra}"))
    sync_rating(team)
    return True, f"{LABELS[kind]} upgraded to level {f[kind]} ({grade(f[kind])}) for {money(c)}{extra}."


# ═══ The offseason ═════════════════════════════════════════════════════════

def end_of_season(league, rng):
    """Gate money in, wear and tear, and the CPU's building projects."""
    import carousel as cz
    ensure_all(league)
    import ad_mode
    you = getattr(league, "user_team", None) if getattr(league, "mode", None) == "career" else ad_mode.my_team(league)
    if getattr(league, "autosim", False):
        you = None                                     # simming seasons: the AD runs the building plan
    import hotseat
    humans = hotseat.humans(league) if getattr(league, "mode", None) == "career" and not getattr(league, "autosim", False) else []
    for team in league.teams:
        total, prem, seats = season_revenue(league, team)
        if total:
            team.__dict__.setdefault("income", []).append(
                {"what": "stadium revenue (premium seating and new seats)", "amount": total, "year": league.year + 1})
            if team is you or any(team is h for h in humans):
                with hotseat.acting_as(league, team):
                    league.__dict__.setdefault("career_log", []).append(
                        (league.year, f"Stadium revenue: {money(total)} added to next season's budget."))
        for kind in ("recruiting", "training"):          # the stadium wears part by part (stadium.py)
            lv = team.fac[kind]
            import skills
            if skills.team_has(team, "blueprint"):
                continue                                   # Blueprint (coaching tree): nothing slips
            if lv > 1 and rng.random() < (DEGRADE_BASE + DEGRADE_PER_LEVEL * lv) * ad_mode.degrade_mult(league, team, kind):
                team.fac[kind] = lv - 1
                team.fac_log.append((league.year, f"{LABELS[kind]} slipped to {lv - 1} ({grade(lv - 1)}) — wear and tear"))
                if team is you or any(team is h for h in humans):
                    with hotseat.acting_as(league, team):
                        league.__dict__.setdefault("career_log", []).append(
                            (league.year, f"{LABELS[kind]} slipped to level {lv - 1}."))
        sync_rating(team)
    import stadium
    stadium.end_of_season(league, rng, you)             # home records, the fan base, wear, projects that open
    import commissioner as cm
    for team in league.teams:
        if team is not you:
            if not (cm.active(league) and cm.is_player_team(league, team)):
                _ai_build(league, team, rng, cz)             # members build facilities from their own orders
            _ai_stadium(league, team, rng, cz)               # (the stadium stays the AD's call for now)
        sync_rating(team)


AD_BUILD = {"booster": 1.6, "brand": 1.4, "big_game": 1.2, "win_now": 1.1, "politician": 1.1, "recruiting": 1.0,
            "conference": 1.0, "patient": 1.0, "traditionalist": 0.9, "turnaround": 1.1, "analytics": 0.9, "budget": 0.6}


def _ai_build(league, team, rng, cz):
    """An AD's building plan: bring anything below where the program belongs up to standard,
    only with money the recruiting class won't miss."""
    f = team.fac
    style = (getattr(team, "ad", None) or {}).get("style", "conference")
    appetite = AD_BUILD.get(style, 1.0)
    target = team.prestige / 10 + (appetite - 1) * 2
    import finance as fi_
    still_owed = max(0, class_target(league, team) - fi_.committed_nil(league.recruiting, team)
                     - fi_.open_nil(league.recruiting, team))
    spare = available(league, team) - still_owed * 0.95        # never out of the class's money
    if spare <= 0 or rng.random() > 0.55 * appetite:
        return
    wants = sorted(("recruiting", "training"), key=lambda k: (f[k] - target) + rng.random() * 0.8)
    for kind in wants:
        if f[kind] >= 10 or f[kind] >= target + 0.5:
            continue
        c = cost(kind, f[kind] + 1)
        if c <= spare:
            ok, msg = upgrade(league, team, kind)
            if ok and f[kind] >= 8:
                cz._news(league, "facilities", f"{team.school} {msg[0].lower() + msg[1:]}")
            return


def _ai_stadium(league, team, rng, cz):
    """The stadium plan: seats when it sells out, otherwise the parts the AD cares about."""
    import stadium
    style = (getattr(team, "ad", None) or {}).get("style", "conference")
    appetite = AD_BUILD.get(style, 1.0)
    if rng.random() > 0.8 * appetite:
        return
    k = stadium.ai_build(league, team, rng, appetite)
    if k and (stadium.PARTS[k]["seats"] >= 4000 or k == "canopy"):
        pr = team.stad["project"]
        cz._news(league, "facilities", f"{team.school} breaks ground on {stadium.tier_name(k, pr['tier']).lower()} "
                                       f"at {team.stadium} — it opens in {pr['done'] + 1}")
