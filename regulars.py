"""
regulars.py — The regulars at The Window: a dozen people who bet every Saturday.

They're former players and former coaches (made-up people — nobody real), and
each one bets his own way, off the same numbers you see. They place their
tickets as soon as a week's lines settle, so you can see what they're on all
week — and tail or fade them.

  THE FILM ROOM    a former defensive coordinator. Builds his own line: the
                   ratings, how loud the building really is (the book gives
                   everyone 2.5), and who's coaching. Bets when he's 2+ off.
  THE MODEL        a former grad-assistant analyst. Same kind of number, but
                   bets moneylines, sized by Kelly.
  CHALK            a former star quarterback. Favorites, and favorite parlays.
  THE DOG POUND    a former walk-on. Big underdogs, road dogs, the odd longshot.
  THE HOMER        bets his old school every week, and their conference title.
  FADE THE PUBLIC  a former head coach who hated the big brands. When a
                   blue blood is favored, he takes the other side.
  UNDER THE WEATHER a former defensive line coach. Unders — in the rain, the
                   wind, and when two good defenses meet.
  POINTS PLEASE    a former Air Raid coordinator. Overs, tempo teams.
  THE LOTTERY      a former kicker. Parlays, teasers, the Boost. Small money,
                   big dreams.
  HOT HAND         a former TV analyst. Rides teams covering the number, fades
                   the ones that aren't.
  THE BOOSTER      a former athletic director. Futures, and one big ticket on
                   the biggest game of the week.
  YARDS GUY        a former running back. Player props — the overs, and who's
                   scoring.

The leaderboard ranks everybody (you too) by what they've won this season, and
all-time. A season's winner gets a star. Go broke and you re-up with $1,000 —
it's counted against you.
"""
import random

import sportsbook as sb

REUP = 1_000


class Regular:
    def __init__(self, key, name, nick, bio, school, bank, color_seed=0):
        self.key = key                  # the strategy
        self.name, self.nick, self.bio, self.school = name, nick, bio, school
        self.bank = float(bank)
        self.start = float(bank)
        self.reloads = 0
        self.bets = []
        self.seasons = {}
        self.ledger = [bank]
        self.titles = []                # seasons he won the table
        self.seed = color_seed

    @property
    def open_bets(self):
        return [b for b in self.bets if b.status == "open"]

    @property
    def settled_bets(self):
        return [b for b in self.bets if b.status != "open"]

    @property
    def net(self):
        return round(self.bank + sum(b.stake for b in self.open_bets) - self.start - self.reloads * REUP, 2)

    def season_net(self, year):
        return self.seasons.get(year, 0.0)

    def unit(self, pct):
        return max(5.0, round(self.bank * pct / 5) * 5) if self.bank >= 5 else 0.0


# ═══ Who they are ══════════════════════════════════════════════════════════

TYPES = {
    "sharp":  ("THE FILM ROOM", "coach", "defensive coordinator",
               "Builds his own number: the ratings, how loud the building really is (the book gives every home team "
               "2.5), and who's on the headset. Bets when he's a point and a half off the book.",
               "The book doesn't watch film. I do."),
    "quant":  ("THE MODEL", "coach", "graduate assistant (analytics)",
               "Turns his own number into a win probability and bets moneylines where the price is wrong, "
               "sized by the Kelly criterion (a quarter of it).",
               "It's not a hunch if it's a spreadsheet."),
    "chalk":  ("CHALK", "player", "quarterback",
               "Favorites. Ranked teams laying points at home, and two- and three-team moneyline parlays of "
               "teams that shouldn't lose.",
               "I didn't lose much when I played. I don't bet on guys who do."),
    "dogs":   ("THE DOG POUND", "player", "walk-on safety",
               "Underdogs of a touchdown or more, especially on the road, and a small moneyline flyer on a big dog.",
               "Nobody gave me a chance either."),
    "homer":  ("THE HOMER", "player", "linebacker",
               "His old school, every week, no matter the number. Their conference title in the preseason.",
               "Once a {mascot}, always a {mascot}."),
    "fade":   ("FADE THE PUBLIC", "coach", "head coach",
               "When a blue blood is favored, the public is on it and the number is inflated. He takes the "
               "other side.",
               "Thirty years of losing recruits to those people. I'll take their money instead."),
    "under":  ("UNDER THE WEATHER", "coach", "defensive line coach",
               "Unders: rain, snow and wind, and two good defenses. Stays away from shootout offenses.",
               "Defense travels. So does a cold front."),
    "over":   ("POINTS PLEASE", "coach", "offensive coordinator (Air Raid)",
               "Overs when fast offenses meet, and when a bad defense is on the field.",
               "Nobody paid to watch a punt."),
    "lotto":  ("THE LOTTERY", "player", "placekicker",
               "One long parlay a week, a teaser, and the Boost. Small money, big dreams.",
               "Four-hundred-to-one. You gotta be in it."),
    "trend":  ("HOT HAND", "player", "wide receiver (now on TV)",
               "Rides teams that keep covering and fades teams that keep failing to. Trends are real until they aren't.",
               "Momentum is a stat. I don't care what the nerds say."),
    "whale":  ("THE BOOSTER", "coach", "athletic director",
               "Futures — long shots for the title, the Golden Helmet — and one big straight bet on the game of the week.",
               "I've written bigger checks for worse reasons."),
    "props":  ("YARDS GUY", "player", "running back",
               "Player props in the featured games: yardage overs on the stars, and who scores.",
               "Give the ball to the best player. Every time."),
}

NICKS = {"sharp": ("Film", "Tape", "Professor"), "quant": ("Decimal", "Spreadsheet", "Doc"),
         "chalk": ("Chalk", "Golden Arm", "Money"), "dogs": ("Walk-On", "Scraps", "Longshot"),
         "homer": ("True Blue", "Lifer", "Big"), "fade": ("Old Man", "Sour", "Colonel"),
         "under": ("Frost", "Muddy", "Big Cold"), "over": ("Airmail", "Shootout", "Tempo"),
         "lotto": ("Leg", "Two-Step", "Lucky"), "trend": ("Hot Hand", "TV", "Streak"),
         "whale": ("Checkbook", "Moneybags", "Boss"), "props": ("Workhorse", "Bell Cow", "Tank")}


def _bio(rng, league, key, school):
    kind, role = TYPES[key][1], TYPES[key][2]
    yr = league.year
    if kind == "player":
        a = yr - rng.randint(8, 34)
        tail = rng.choice(("a two-year starter", "an honorable-mention All-American", "a team captain",
                           "a fifth-round pick who lasted two Pro League seasons", "a walk-on who earned a scholarship",
                           "a four-year letterman", "the MVP of a bowl nobody remembers"))
        return f"Former {school.school} {role} ({a}-{str(a + 3)[-2:]}), {tail}."
    a = yr - rng.randint(12, 40)
    b = a + rng.randint(6, 18)
    w, l = rng.randint(40, 110), rng.randint(30, 90)
    if role == "head coach":
        return f"Former {school.school} head coach ({a}-{b}, {w}-{l}). Retired to the rail."
    return f"Former {role} at {school.school} and three other stops ({a}-{b})."


def create(book, league):
    """The table, the first time you walk up (they start with what you started with)."""
    rng = random.Random(f"regulars:{league.seed}")
    fbs = [t for t in league.teams if not getattr(t, "fcs", False)]
    used = set()
    regs = []
    for key in TYPES:
        school = rng.choice(fbs)
        name = __import__("names").full_name(rng, avoid=used)
        used.add(name.split()[-1])
        nick = rng.choice(NICKS[key])
        regs.append(Regular(key, name, nick, _bio(rng, league, key, school), school, book.start, rng.randint(0, 99)))
    book.regulars = regs
    book.table_champs = {}
    book.ticker = []
    return regs


def ensure(book, league):
    if not book.__dict__.get("regulars"):
        create(book, league)
        place_week(book, league)
    return book.regulars


def display_name(r):
    first, _, last = r.name.partition(" ")
    return f'{first} "{r.nick}" {last}'


# ═══ How they see a game ══════════════════════════════════════════════════

def true_margin(league, g, book=None):
    """The film room's number: the market's read of both teams without the public money,
    with the real building (the book gives every home team the same edge) and the real coaching."""
    import stadium
    h, a = g.home, g.away
    extra = 0.0
    site = 0
    if not g.neutral:
        try:
            noise = stadium.noise_rating(h) if not getattr(h, "fcs", False) else 3.0
        except Exception:
            noise = 5.0
        extra += 0.9 + 0.33 * noise                   # in place of the book's flat home field
    try:
        extra += 0.03 * (h.ratings.get("coach", 60) - a.ratings.get("coach", 60))
    except Exception:
        pass
    if book is None:
        return sb.curve(sb.PTS_PER_OVR * (sb._ovr(league, h) - sb._ovr(league, a)) + extra)
    return sb.margin(book, league, h, a, site, public=False, extra=extra)


def _book_margin(ln):
    return -ln["spread"]


def _legs(book, league, g):
    return sb.game_legs(book, league, g)


def _fast(t):
    try:
        import staff
        import playbook as pb
        return pb.OFFENSE_SCHEMES[staff.play_caller(t, "off").offense_scheme]["tempo"] <= 24
    except Exception:
        return False


def _prestige(t):
    try:
        return t.prestige
    except Exception:
        return 50


# ═══ The strategies: each returns [(kind, [legs], stake)] ════════════════════

def pick_sharp(r, book, league, games):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln:
            continue
        edge = true_margin(league, g, book) - _book_margin(ln)
        if abs(edge) >= 1.5:
            lg = _legs(book, league, g)["sh" if edge > 0 else "sa"]
            out.append((abs(edge), ("straight", [lg], r.unit(0.03 if abs(edge) >= 2.5 else 0.02))))
    return [x for _, x in sorted(out, key=lambda x: -x[0])[:6]]


def pick_quant(r, book, league, games):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln or not ln["ml"]:
            continue
        p = sb.phi(true_margin(league, g, book) / sb.SIG)
        legs = _legs(book, league, g)
        for code, q in (("mh", p), ("ma", 1 - p)):
            if code not in legs:
                continue
            d = sb.dec(legs[code].odds)
            edge = q * d - 1
            if edge > 0.04:
                kelly = edge / (d - 1)
                stake = min(r.bank * 0.04, r.bank * kelly * 0.25)
                if stake >= 5:
                    out.append((edge, ("straight", [legs[code]], round(stake / 5) * 5)))
    return [x for _, x in sorted(out, key=lambda x: -x[0])[:6]]


def pick_chalk(r, book, league, games, rng):
    out, favs = [], []
    rk = league.rankings.rank_of
    for g in games:
        ln = sb.line(book, league, g)
        if not ln or not ln["ml"]:
            continue
        legs = _legs(book, league, g)
        for code, t, a in (("mh", g.home, ln["ml"][1]), ("ma", g.away, ln["ml"][0])):
            if -450 <= a <= -150 and rk(t):
                favs.append(legs[code])
        if rk(g.home) and -10 <= ln["spread"] <= -3:
            out.append(("straight", [legs["sh"]], r.unit(0.025)))
    rng.shuffle(favs)
    for n in (2, 3):
        if len(favs) >= n:
            out.append(("parlay", favs[:n], r.unit(0.02)))
            favs = favs[n:]
    return out[:5]


def pick_dogs(r, book, league, games, rng):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln or getattr(g.home, "fcs", False) or getattr(g.away, "fcs", False):
            continue
        legs = _legs(book, league, g)
        if ln["spread"] >= 7 and ln["spread"] <= 24:                       # a road dog
            out.append((ln["spread"] + 2, ("straight", [legs["sa"]], r.unit(0.02))))
        elif ln["spread"] <= -7 and ln["spread"] >= -21:
            out.append((-ln["spread"], ("straight", [legs["sh"]], r.unit(0.02))))
    out = [x for _, x in sorted(out, key=lambda x: -x[0])[:4]]
    flyers = []
    for g in games:
        ln = sb.line(book, league, g)
        if ln and ln["ml"]:
            legs = _legs(book, league, g)
            for code, a in (("ma", ln["ml"][0]), ("mh", ln["ml"][1])):
                if 250 <= a <= 550 and code in legs:
                    flyers.append(legs[code])
    if flyers:
        out.append(("straight", [rng.choice(flyers)], r.unit(0.006)))
    return out


def pick_homer(r, book, league, games):
    t = r.school
    for g in games:
        if t in (g.home, g.away):
            legs = _legs(book, league, g)
            code = "sh" if g.home is t else "sa"
            out = [("straight", [legs[code]], r.unit(0.05))]
            ml = "mh" if g.home is t else "ma"
            if ml in legs and legs[ml].odds > 0:
                out.append(("straight", [legs[ml]], r.unit(0.015)))       # he believes
            return out
    return []


def pick_fade(r, book, league, games):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln:
            continue
        legs = _legs(book, league, g)
        if ln["spread"] < 0 and _prestige(g.home) >= 84 and _prestige(g.away) < 80 and ln["spread"] >= -24:
            out.append(("straight", [legs["sa"]], r.unit(0.025)))
        elif ln["spread"] > 0 and _prestige(g.away) >= 84 and _prestige(g.home) < 80 and ln["spread"] <= 24:
            out.append(("straight", [legs["sh"]], r.unit(0.025)))
    return out[:5]


def pick_under(r, book, league, games):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln:
            continue
        score = 0.0
        try:
            import weather
            f = weather.forecast(g, league)
            score += {3: 3.0, 2: 1.5}.get(f.get("severity", 0), 0.0)
        except Exception:
            pass
        _, hd = sb._unit(league, g.home)
        _, ad = sb._unit(league, g.away)
        score += max(0, (hd + ad) / 2 - 72) / 3
        if _fast(g.home) and _fast(g.away):
            score -= 2
        if score >= 1.5:
            out.append((score, ("straight", [_legs(book, league, g)["u"]], r.unit(0.025))))
    return [x for _, x in sorted(out, key=lambda x: -x[0])[:4]]


def pick_over(r, book, league, games):
    out = []
    for g in games:
        ln = sb.line(book, league, g)
        if not ln:
            continue
        score = (1.5 if _fast(g.home) else 0) + (1.5 if _fast(g.away) else 0)
        _, hd = sb._unit(league, g.home)
        _, ad = sb._unit(league, g.away)
        score += max(0, 66 - min(hd, ad)) / 4
        if score >= 2.5:
            out.append((score, ("straight", [_legs(book, league, g)["o"]], r.unit(0.02))))
    return [x for _, x in sorted(out, key=lambda x: -x[0])[:4]]


def pick_lotto(r, book, league, games, rng):
    out = []
    pool = []
    for g in games:
        ln = sb.line(book, league, g)
        if ln:
            legs = _legs(book, league, g)
            pool.append(legs[rng.choice(("sa", "sh", "o", "u"))])
    rng.shuffle(pool)
    n = rng.randint(4, 7)
    if len(pool) >= n:
        out.append(("parlay", pool[:n], r.unit(0.008)))
    spreads = [x for x in pool[n:] if x.kind in ("spread", "total")]
    if len(spreads) >= 3:
        out.append(("teaser", spreads[:3], r.unit(0.012)))
    bo = sb.weekly_boost(book, league)
    if bo.get("legs"):
        out.append(("boost", bo["legs"], min(sb.BOOST_MAX, r.unit(0.01))))
    return out


def pick_trend(r, book, league, games):
    out = []
    for g in games:
        legs = _legs(book, league, g)
        if not legs:
            continue
        for t, code, other in ((g.home, "sh", "sa"), (g.away, "sa", "sh")):
            w, l, _ = book.ats.get(t, [0, 0, 0])
            if w + l >= 4:
                pct = w / (w + l)
                if pct >= 0.7:
                    out.append((pct, ("straight", [legs[code]], r.unit(0.025))))
                elif pct <= 0.3:
                    out.append((1 - pct, ("straight", [legs[other]], r.unit(0.02))))
    seen, picks = set(), []
    for _, x in sorted(out, key=lambda x: -x[0]):
        gid = id(x[1][0].game)
        if gid not in seen:
            seen.add(gid)
            picks.append(x)
    return picks[:5]


def pick_whale(r, book, league, games, rng):
    out = []
    if games:
        g = sb.featured(book, league, games[0].week, n=1)
        g = g[0] if g else None
        if g is not None and sb.line(book, league, g):
            ln = sb.line(book, league, g)
            legs = _legs(book, league, g)
            out.append(("straight", [legs["sh" if ln["spread"] <= 0 else "sa"]], r.unit(0.06)))
    return out


def pick_props(r, book, league, games, rng):
    out = []
    wk = games[0].week if games else None
    if wk != league.week + 1:
        return out
    for g in sb.featured(book, league, wk, n=5):
        for lg in sb.props_for(book, league, g):
            if (lg.side == "over" and lg.stat in ("rush_yds", "rec_yds")) or (lg.stat == "td" and lg.odds >= -130):
                out.append(lg)
    rng.shuffle(out)
    return [("straight", [x], r.unit(0.01)) for x in out[:5]]


def futures_picks(r, book, league, rng):
    """Preseason (and a little in-season) futures."""
    try:
        mk = sb.futures(book, league)
    except Exception:
        return []
    mo = sb.markets_open(league)
    out = []
    if r.key == "whale":
        if mo["title"]:
            longs = [(t, a) for t, a, _ in mk["title"] if 1200 <= a <= 8000]
            rng.shuffle(longs)
            for t, a in longs[:3 if league.week == 0 else 1]:
                out.append(("straight", [sb.future_leg(league, "title", t, a)], r.unit(0.015)))
        if mo["heisman"] and league.week == 0 and mk["heisman"]:
            p, a, _ = rng.choice(mk["heisman"][2:10] or mk["heisman"])
            out.append(("straight", [sb.future_leg(league, "heisman", p, a)], r.unit(0.01)))
        if mo["wins"]:
            row = next((x for x in mk["wins"] if x[0] is r.school), None)
            if row:
                out.append(("straight", [sb.future_leg(league, "wins", row[0], row[2], "over", row[1])], r.unit(0.02)))
    elif r.key == "homer" and league.week == 0:
        conf = mk["conf"].get(r.school.conference)
        row = next((x for x in (conf or []) if x[0] is r.school), None)
        if row and mo["conf"]:
            out.append(("straight", [sb.future_leg(league, "conf", row[0], row[1])], r.unit(0.03)))
        w = next((x for x in mk["wins"] if x[0] is r.school), None)
        if w and mo["wins"]:
            out.append(("straight", [sb.future_leg(league, "wins", w[0], w[2], "over", w[1])], r.unit(0.03)))
    elif r.key == "chalk" and league.week == 0 and mo["title"] and mk["title"]:
        t, a, _ = mk["title"][0]
        out.append(("straight", [sb.future_leg(league, "title", t, a)], r.unit(0.03)))
    elif r.key == "quant" and league.week == 0 and mo["wins"]:
        # win totals with the most juice on one side — he trusts the simulation more than the price
        rows = sorted(mk["wins"], key=lambda x: -abs(x[4] - 0.5))[:2]
        for t, L, o, u, p in rows:
            side, price = ("over", o) if p > 0.5 else ("under", u)
            out.append(("straight", [sb.future_leg(league, "wins", t, price, side, L)], r.unit(0.015)))
    return out


STRATS = {"sharp": pick_sharp, "quant": pick_quant, "chalk": pick_chalk, "dogs": pick_dogs, "homer": pick_homer,
          "fade": pick_fade, "under": pick_under, "over": pick_over, "lotto": pick_lotto, "trend": pick_trend,
          "whale": pick_whale, "props": pick_props}
NEEDS_RNG = {"chalk", "dogs", "lotto", "whale", "props"}


def place_week(book, league):
    """Everybody makes their picks for the coming week (once)."""
    regs = book.__dict__.get("regulars") or []
    if not regs or league.season_complete:
        return
    wk = league.week + 1
    key = (league.year, wk)
    if book.__dict__.get("regulars_week") == key:
        return
    book.regulars_week = key
    games = [g for g in sb.games_in(league, wk) if sb.open_for_betting(league, g)]
    for r in regs:
        if r.bank < 10 and not r.open_bets:
            r.bank += REUP
            r.reloads += 1
            _tick(book, league, f"{display_name(r)} re-upped with {sb.money(REUP)}. It happens.")
        rng = random.Random(f"reg:{league.seed}:{r.name}:{league.year}:{wk}")
        picks = []
        if league.week == 0 or (r.key == "whale" and wk in (5, 9)):
            picks += futures_picks(r, book, league, rng)
        if games:
            fn = STRATS[r.key]
            picks += fn(r, book, league, games, rng) if r.key in NEEDS_RNG else fn(r, book, league, games)
        for kind, legs, stake in picks:
            stake = min(stake, r.bank)
            if stake < 5:
                break
            sb.place(book, league, kind, legs, stake, boosted_odds=(sb.weekly_boost(book, league).get("odds")
                                                                     if kind == "boost" else None), acct=r)
    placed = [(b.stake, r, b) for r in regs for b in r.open_bets if b.week == wk and b.kind != "future"]
    if placed:
        stake, r, b = max(placed, key=lambda x: x[0])
        _tick(book, league, f"Biggest ticket at the window for {league.week_name(wk)}: {display_name(r)}, "
                            f"{sb.money(stake)} on {b.title()}.")


# ═══ The table ════════════════════════════════════════════════════════════

def you_net(book):
    return round(book.bank + book.at_risk() - book.start - book.reloads * sb.RELOAD, 2)


def standings(book, league, season=True):
    """[(name, net, account or None for you)] best first."""
    rows = []
    yr = league.year
    for r in book.__dict__.get("regulars") or []:
        rows.append((display_name(r), r.season_net(yr) if season else r.net, r))
    rows.append(("YOU", book.seasons.get(yr, 0.0) if season else you_net(book), None))
    rows.sort(key=lambda x: -x[1])
    return rows


def your_rank(book, league, season=True):
    rows = standings(book, league, season)
    for i, (_, _, acct) in enumerate(rows, 1):
        if acct is None:
            return i, len(rows)
    return None, len(rows)


def _tick(book, league, text):
    t = book.__dict__.setdefault("ticker", [])
    t.append((league.year, league.week_name(league.week) if league.week else "Preseason", text))
    del t[:-40]


def after_settle(book, league, settled):
    """The rail talks: the big hits, the bad weeks."""
    by = {}
    for r, b in settled:
        by.setdefault(r, []).append(b)
    for r, bets in by.items():
        net = sum(b.net for b in bets)
        big = max(bets, key=lambda b: b.net)
        w = sum(1 for b in bets if b.status == "won")
        l = sum(1 for b in bets if b.status == "lost")
        if w >= 4 and l == 0:
            _tick(book, league, f"{display_name(r)} went {w}-0. {TYPES[r.key][4].format(mascot=getattr(r.school, 'nickname', ''))}")
        elif l >= 4 and w == 0:
            _tick(book, league, f"{display_name(r)} went 0-{l}. He's not talking.")
        if big.net >= max(400, r.start * 0.05) and big.kind in ("parlay", "teaser", "boost", "future"):
            _tick(book, league, f"{display_name(r)} cashed {big.title().lower()} at {sb.fmt_odds(big.odds)}: "
                                f"{sb.money(big.net, sign=True)}.")
        elif big.net >= max(400, r.start * 0.06):
            _tick(book, league, f"{display_name(r)} hit {big.title()} for {sb.money(big.net, sign=True)}.")
        if net <= -r.start * 0.08:
            _tick(book, league, f"Rough week for {display_name(r)}: {sb.money(net)}.")


def season_end(book, league_year):
    """Crown the season's winner before the new year starts."""
    regs = book.__dict__.get("regulars") or []
    if not regs:
        return
    rows = [(r.season_net(league_year), r) for r in regs] + [(book.seasons.get(league_year, 0.0), None)]
    best = max(rows, key=lambda x: x[0])
    champs = book.__dict__.setdefault("table_champs", {})
    champs[league_year] = ("YOU" if best[1] is None else display_name(best[1]), best[0])
    if best[1] is not None:
        best[1].titles.append(league_year)
    else:
        book.__dict__.setdefault("titles", []).append(league_year)


def tail_legs(book, league, b, fade=False):
    """Today's version of someone else's ticket (or its opposite): legs for your slip."""
    out = []
    for lg in b.legs:
        if lg.game is None or not sb.open_for_betting(league, lg.game):
            continue
        legs = sb.game_legs(book, league, lg.game)
        g = lg.game
        code = None
        if lg.kind == "spread":
            home = lg.team is g.home
            code = "sh" if home != fade else "sa"
        elif lg.kind == "ml":
            home = lg.team is g.home
            code = "mh" if home != fade else "ma"
        elif lg.kind == "total":
            code = "o" if (lg.side == "over") != fade else "u"
        elif lg.kind == "prop" and not fade:
            match = [x for x in sb.props_for(book, league, g) if x.player is lg.player and x.stat == lg.stat
                     and x.side == lg.side]
            if match:
                out.append(match[0])
            continue
        if code and code in legs:
            out.append(legs[code])
    return out
