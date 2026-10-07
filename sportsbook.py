"""
sportsbook.py — The Window: a sportsbook for Spectator mode (the engine).

The screens are in book_screens.py. This file sets the numbers, takes the
bets and pays them out.

THE BANKROLL
  You start a spectator save with a bankroll (you pick it the first time you
  walk up to the window: $1,000, $10,000 or $100,000). Every bet comes out of
  it; every winner goes back in. Broke? You can take a reload — it's counted.

HOW THE BOOK SETS A LINE
  The book keeps a power number for every team:
      1.71 points per point of team rating, run through a curve fitted to how
      games actually end (so favorites cover about half the time at every size)
    + what the season has taught it (every result moves a team toward what it
      has actually shown: a lot in September, less by November; half of it
      carries into next season)
    + a little public money: the big brands get shaded about a point,
      because that's who the public bets
  The home team gets the same edge everywhere (about 3.5 points — the book
  doesn't know which buildings are really loud). The gap becomes a margin on a
  curve fitted to how games actually play out (moderate favorites win by more
  than a straight line says; mismatches flatten out). Spread = that margin, to
  the half point. Moneylines come from the same number (about 18 points of
  noise either way) with the vig on both sides. Totals come from the two
  offenses and defenses, and the weather that week.
  Every game on the schedule has a line all season (look-ahead lines). They
  move every week as teams play, get hurt and get healthy. A bet locks the
  number you took; My Bets shows where the line is now.

THE MARKETS
  Game lines      spread, moneyline, total · first-half spread and total ·
                  team totals
  Props           featured games: QB passing yards, RB rushing yards, WR
                  receiving yards (over/under), anytime touchdown scorer
  Parlays         2-12 legs; one side and one total per game; pushes drop out
  Teasers         6 points, 2-4 legs of spreads and totals (-120, +160, +260)
  The Boost       one boosted two-team parlay a week ($50 max)
  Futures         national champion · conference champions · make the playoff
                  (yes/no) · the Golden Helmet · regular-season win totals (preseason
                  only). Odds come from simulating the rest of the season with
                  the book's numbers, and they move every week.

SETTLEMENT
  Bets are graded the moment the game is final (a parlay loses the moment one
  leg does). Futures pay when they're decided: win totals after Week 13,
  conference titles on championship Saturday, the playoff field on Selection
  Day, the Golden Helmet and the national title when the season ends. A player prop
  on a player who doesn't play is void (your money back).
"""
import math
import random
from collections import Counter

PTS_PER_OVR = 1.71
HFA = 2.5                # home field, on the rating scale (it comes out near 3.5 points)
SIG = 18.0               # the noise around a margin (blowouts and upsets both happen)
# Margins aren't a straight line in the rating gap: a moderate favorite wins by more than a line
# says, and a mismatch flattens out (starters sit, the backups kneel). This curve maps the
# rating-scale gap to the median margin, fitted over 2,288 simulated games so favorites cover
# about half the time at every size of spread.
CURVE_X = (0, 1.6, 4.8, 7.2, 10.1, 13.6, 17, 20, 24, 28.4, 33, 39, 49, 70)
CURVE_Y = (0, 2.6, 8, 12.5, 17, 21.5, 25, 27.5, 29.5, 30.5, 31.5, 34, 39, 50)
H1_SIDE, H1_TOTAL = 0.5, 0.48
ADJ_CAP = 14.0
ADJ_PRIOR = 7.0          # how many games of evidence the ratings are worth before a team has played:
                         # the book moves fast in September and settles down by November
BANKROLLS = (1_000, 10_000, 100_000)
DEFAULT_BANK = 10_000
RELOAD = 1_000
TEASER_PTS = 6
TEASER_ODDS = {2: -120, 3: 160, 4: 260}
MAX_LEGS = 12
PARLAY_CAP = 250_000
BOOST_MAX = 50
REG = 13

SIDE_KINDS = ("spread", "ml", "h1_spread")
TOTAL_KINDS = ("total", "h1_total", "tt")
GAME_KINDS = SIDE_KINDS + TOTAL_KINDS + ("prop",)


# ═══ Odds arithmetic ════════════════════════════════════════════════════════

def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def dec(a):
    """American → decimal."""
    return 1 + a / 100 if a > 0 else 1 + 100 / -a


def american(d):
    """Decimal → American (rounded like a book)."""
    if d >= 2:
        a = (d - 1) * 100
    else:
        a = -100 / (d - 1)
    return _round_am(a)


def _round_am(a):
    step = 5 if abs(a) < 200 else 10 if abs(a) < 1000 else 50 if abs(a) < 5000 else 500
    a = int(round(a / step) * step)
    if -100 < a < 100:
        a = 100 if a >= 0 else -100
    return a


def price(p):
    """A probability (vig already in it) → American odds."""
    p = max(0.0005, min(0.9995, p))
    return _round_am(-p / (1 - p) * 100 if p >= 0.5 else (1 - p) / p * 100)


def implied(a):
    return 1 / dec(a)


def half(x):
    """To the nearest half point."""
    return round(x * 2) / 2


def fmt_odds(a):
    if a is None:
        return "—"
    return "EVEN" if a == 100 else (f"+{a}" if a > 0 else str(a))


def fmt_line(x):
    if x is None:
        return "—"
    if x == 0:
        return "PK"
    s = f"{x:+.1f}"
    return s[:-2] if s.endswith(".0") else s


def fmt_num(x):
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def money(x, sign=False):
    neg = x < 0
    x = abs(x)
    s = f"${x:,.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    if neg:
        return "−" + s
    return ("+" + s) if sign and x > 0 else s


# ═══ The book ══════════════════════════════════════════════════════════════

class Leg:
    """One pick. kind: spread · ml · total · h1_spread · h1_total · tt · prop · future."""

    def __init__(self, kind, game=None, team=None, side=None, line=None, odds=-110, label="",
                 player=None, stat=None, sub=None, year=None, conf=None):
        self.kind, self.game, self.team, self.side = kind, game, team, side
        self.line, self.odds, self.label = line, odds, label
        self.player, self.stat, self.sub, self.year, self.conf = player, stat, sub, year, conf
        self.status = None                # won · lost · push · void
        self.closing = None               # the line when the game kicked off (spread/total legs)

    def key(self):
        return (self.kind, id(self.game), id(self.team), self.side, id(self.player), self.stat, self.sub,
                self.conf, self.line)

    def family(self):
        if self.kind in SIDE_KINDS:
            return "side"
        if self.kind in TOTAL_KINDS:
            return "total"
        return self.kind


class Bet:
    def __init__(self, kind, legs, stake, odds, year, week, boosted=False):
        self.kind = kind                  # straight · parlay · teaser · future · boost
        self.legs = legs
        self.stake = round(stake, 2)
        self.odds = odds                  # American, as placed
        self.year, self.week = year, week
        self.status = "open"
        self.payout = 0.0                 # what came back (stake included)
        self.settled = None               # (year, week) when graded
        self.boosted = boosted
        self.id = None

    @property
    def to_win(self):
        return round(self.stake * (dec(self.odds) - 1), 2)

    @property
    def net(self):
        return round(self.payout - self.stake, 2) if self.status != "open" else 0.0

    def title(self):
        if self.kind == "parlay":
            return f"{len(self.legs)}-leg parlay"
        if self.kind == "teaser":
            return f"{len(self.legs)}-team teaser (+{TEASER_PTS})"
        if self.kind == "boost":
            return "The Boost"
        return self.legs[0].label


class Book:
    def __init__(self, league, bank=DEFAULT_BANK):
        self.bank = float(bank)
        self.start = float(bank)
        self.reloads = 0
        self.bets = []                    # every bet ever placed
        self.next_id = 1
        self.ledger = [(league.year, "Start", self.bank)]
        self.unseen = []                  # bets settled since you last looked
        self.slip = []
        self.year = league.year
        self.adj, self.tadj = {}, {}
        self.hist = {}                    # game -> [(stamp label, home spread, total)]
        self.cache = {}                   # game -> (stamp, line dict)
        self.ats, self.ou = {}, {}        # team -> [w, l, p]
        self.ats_history = {}             # year -> {school: (w, l, p)}
        self.futures = None               # (stamp, markets)
        self.futures_open = {}            # (market, team/player key) -> first price seen this season
        self.props = {}                   # stamp -> {game: [legs]}
        self.boost = None
        self.welcomed = False
        self.seasons = {}                 # year -> net

    # ── money ──────────────────────────────────────────────────────────────
    @property
    def open_bets(self):
        return [b for b in self.bets if b.status == "open"]

    @property
    def settled_bets(self):
        return [b for b in self.bets if b.status != "open"]

    def at_risk(self):
        return sum(b.stake for b in self.open_bets)

    def to_win_open(self):
        return sum(b.to_win for b in self.open_bets)


def get(league, create=True):
    """The league's book (Spectator mode only)."""
    if getattr(league, "mode", None) != "spectator":
        return None
    b = league.__dict__.get("book")
    if b is None and create:
        b = league.book = Book(league)
        refresh_all(league, b)
    if b is not None and b.year != league.year:
        new_season(league, b)
    return b


# ═══ The numbers ═══════════════════════════════════════════════════════════

def _ovr(league, t):
    import carousel as cz
    return cz._ovr(league, t)


def _unit(league, t):
    """(offense, defense) ratings, cached for the week."""
    key = (league.year, league.week)
    c = league.__dict__.get("_book_units")
    if c is None or c[0] != key:
        c = league._book_units = (key, {})
    d = c[1]
    if t not in d:
        d[t] = (t.offense_ovr, t.defense_ovr)
    return d[t]


def shade(t):
    """Public money: the big brands get bet, so the book shades them."""
    if getattr(t, "fcs", False):
        return 0.0
    try:
        return max(0.0, min(1.2, (t.prestige - 78) * 0.07))
    except Exception:
        return 0.0


def power(book, league, t):
    return PTS_PER_OVR * _ovr(league, t) + book.adj.get(t, 0.0) + shade(t)


def curve(x):
    sgn = 1 if x >= 0 else -1
    x = abs(x)
    for i in range(len(CURVE_X) - 1):
        if x <= CURVE_X[i + 1]:
            t = (x - CURVE_X[i]) / (CURVE_X[i + 1] - CURVE_X[i])
            return sgn * (CURVE_Y[i] + t * (CURVE_Y[i + 1] - CURVE_Y[i]))
    return sgn * (CURVE_Y[-1] + (x - CURVE_X[-1]) * 0.5)


def margin(book, league, h, a, site=1, public=True, extra=0.0):
    """The book's expected margin for h over a (site: 1 = h at home, 0 = neutral, -1 = h on the road)."""
    lin = PTS_PER_OVR * (_ovr(league, h) - _ovr(league, a)) + HFA * site + extra
    m = curve(lin) + book.adj.get(h, 0.0) - book.adj.get(a, 0.0)
    if public:
        m += shade(h) - shade(a)
    return m


def expected(book, league, g, weather=True):
    """(home margin, total) as the book sees it."""
    h, a = g.home, g.away
    m = margin(book, league, h, a, 0 if g.neutral else 1)
    ho, hd = _unit(league, h)
    ao, ad = _unit(league, a)
    tot = 30.1 + 0.81 * (ho + ao) - 0.70 * (hd + ad) + 0.28 * abs(_ovr(league, h) - _ovr(league, a))
    tot += book.tadj.get(h, 0.0) + book.tadj.get(a, 0.0) + book.__dict__.get("tbias", 0.0)
    if weather and g.week == league.week + 1:
        try:
            import weather as wx
            f = wx.forecast(g, league)
            tot -= {3: 4.5, 2: 2.0}.get(f.get("severity", 0), 0.0)
        except Exception:
            pass
    return m, max(28.0, min(95.0, tot))


def _stamp(league):
    return (league.year, league.week)


def make_line(book, league, g):
    m, tot = expected(book, league, g)
    sp = -half(m)                                   # the home team's number
    total = half(tot)
    p_home = phi(m / SIG)
    ml = None
    if 0.035 < p_home < 0.965:                      # past that, the moneyline's off the board
        ml = (price(1 - p_home + 0.0225), price(p_home + 0.0225))     # (away, home)
    h1 = -half(m * H1_SIDE)
    h1t = half(tot * H1_TOTAL)
    tt = (half((tot - m) / 2), half((tot + m) / 2))                   # (away, home)
    return {"spread": sp, "total": total, "ml": ml, "h1": h1, "h1t": h1t, "tt": tt, "m": m, "p_home": p_home}


def open_for_betting(league, g):
    """Until kickoff (a week's games kick off one at a time)."""
    return not g.played and not g.__dict__.get("_kicked") and g.week >= max(1, league.week)


def line(book, league, g):
    """The current line for a game (the closing line once it's kicked off)."""
    st = _stamp(league)
    c = book.cache.get(g)
    if c is not None and (c[0] == st or not open_for_betting(league, g)):
        return c[1]
    if not open_for_betting(league, g):
        return c[1] if c else None
    ln = make_line(book, league, g)
    book.cache[g] = (st, ln)
    h = book.hist.setdefault(g, [])
    label = "Open" if not h else ("Preseason" if league.week == 0 else league.week_name(league.week))
    if not h or h[-1][1] != ln["spread"] or h[-1][2] != ln["total"]:
        h.append((label, ln["spread"], ln["total"]))
    return ln


def opening(book, g):
    h = book.hist.get(g)
    return h[0] if h else None


def upcoming_weeks(league):
    return [w for w in sorted(league.schedule) if w > league.week and any(not g.played for g in league.schedule[w])]


def games_in(league, week):
    return [g for g in league.schedule.get(week, []) if not g.played]


def refresh_all(league, book):
    """Every game still to be played gets this week's number (the look-ahead lines move)."""
    for w in upcoming_weeks(league):
        for g in league.schedule[w]:
            if not g.played:
                line(book, league, g)


# ═══ Props ═════════════════════════════════════════════════════════════════

def featured(book, league, week, n=8):
    """The week's marquee games (and your team's)."""
    gs = games_in(league, week)
    rk = league.rankings.rank_of

    def score(g):
        r = [x for x in (rk(g.home), rk(g.away)) if x]
        base = sum(30 - x for x in r) + (15 if len(r) == 2 else 0)
        ln = line(book, league, g)
        close = max(0, 14 - abs(ln["spread"])) if ln else 0
        return base + close + (_ovr(league, g.home) + _ovr(league, g.away)) * 0.3
    out = sorted(gs, key=lambda g: -score(g))[:n]
    ft = getattr(league, "follow_team", None)
    mine = next((g for g in gs if ft in (g.home, g.away)), None)
    if mine is not None and mine not in out:
        out.append(mine)
    return out


def _starter(team, pos, key=None):
    try:
        grp = team.starters().get(pos, [])
    except Exception:
        return None
    grp = [p for p in grp if getattr(p, "inj_games", 0) <= 0]
    if not grp:
        return None
    return max(grp, key=key) if key else grp[0]


# Yardage is skewed (a few huge days pull the average up), so a fair over/under sits at the
# median, below the average. Measured over full seasons of featured games.
PROP_MEDIAN = {"pass_yds": 0.97, "rush_yds": 0.97, "rec_yds": 0.66}


def _hook(x, lo):
    """A prop number: always on the half yard, so there's no push."""
    return math.floor(max(lo, x)) + 0.5


def _blend(prior, total, games, k=3.0):
    if games <= 0:
        return prior
    return (prior * k + total) / (k + games)


def _run_rate(team):
    try:
        import staff
        import playbook as pb
        return pb.OFFENSE_SCHEMES[staff.play_caller(team, "off").offense_scheme]["run"]
    except Exception:
        return 0.5


def props_for(book, league, g):
    """Player props for one game (featured games only)."""
    st = _stamp(league)
    cache = book.props.setdefault(st, {})
    if g in cache:
        return cache[g]
    legs = []
    for t in (g.away, g.home):
        opp = g.opponent_of(t)
        _, od = _unit(league, opp)
        rr = _run_rate(t)
        qb = _starter(t, "QB")
        rb = _starter(t, "RB")
        wr = _starter(t, "WR", key=lambda p: p.overall)
        if qb is not None:
            gp = qb.games_played
            prior = (185 + (qb.overall - 65) * 3.2) * (1.35 - rr) / 0.85 + (70 - od) * 2.2
            proj = _blend(prior, qb.season_stats.get("pass_yds", 0), gp) * PROP_MEDIAN["pass_yds"]
            ln = _hook(proj, 80)
            for side in ("over", "under"):
                legs.append(Leg("prop", g, t, side, ln, -115, f"QB {qb.last_name} {side} {fmt_num(ln)} pass yds",
                                player=qb, stat="pass_yds"))
        if rb is not None:
            prior = (48 + (rb.overall - 65) * 1.6) * (0.5 + rr) + (70 - od) * 0.9
            proj = _blend(prior, rb.season_stats.get("rush_yds", 0), rb.games_played) * PROP_MEDIAN["rush_yds"]
            ln = _hook(proj, 20)
            for side in ("over", "under"):
                legs.append(Leg("prop", g, t, side, ln, -115, f"RB {rb.last_name} {side} {fmt_num(ln)} rush yds",
                                player=rb, stat="rush_yds"))
        if wr is not None:
            prior = (42 + (wr.overall - 65) * 1.5) * (1.4 - rr) + (70 - od) * 0.8
            proj = _blend(prior, wr.season_stats.get("rec_yds", 0), wr.games_played) * PROP_MEDIAN["rec_yds"]
            ln = _hook(proj, 15)
            for side in ("over", "under"):
                legs.append(Leg("prop", g, t, side, ln, -115, f"WR {wr.last_name} {side} {fmt_num(ln)} rec yds",
                                player=wr, stat="rec_yds"))
        for p, prior in ((rb, 0.55), (wr, 0.42)):
            if p is None:
                continue
            tds = sum(p.season_stats.get(k, 0) for k in ("rush_td", "rec_td", "kr_td", "pr_td"))
            rate = _blend(prior, tds, p.games_played) * 0.84
            m, _ = expected(book, league, g)
            rate *= 1 + (m if t is g.home else -m) / 60          # favorites score more
            pr = 1 - math.exp(-max(0.05, min(1.3, rate)))
            legs.append(Leg("prop", g, t, "td", None, price(min(0.78, pr * 1.08)), f"{p.position} {p.last_name} anytime TD",
                            player=p, stat="td"))
    cache[g] = legs
    return legs


# ═══ Game markets ══════════════════════════════════════════════════════════

def game_legs(book, league, g):
    """Every game-line market for one game, in display order."""
    ln = line(book, league, g)
    if ln is None:
        return {}
    a, h = g.away, g.home
    sp = ln["spread"]
    out = {
        "sa": Leg("spread", g, a, None, -sp, -110, f"{a.school} {fmt_line(-sp)}"),
        "sh": Leg("spread", g, h, None, sp, -110, f"{h.school} {fmt_line(sp)}"),
        "o": Leg("total", g, None, "over", ln["total"], -110, f"Over {fmt_num(ln['total'])} ({a.abbr}-{h.abbr})"),
        "u": Leg("total", g, None, "under", ln["total"], -110, f"Under {fmt_num(ln['total'])} ({a.abbr}-{h.abbr})"),
        "h1a": Leg("h1_spread", g, a, None, -ln["h1"], -110, f"1H {a.school} {fmt_line(-ln['h1'])}"),
        "h1h": Leg("h1_spread", g, h, None, ln["h1"], -110, f"1H {h.school} {fmt_line(ln['h1'])}"),
        "h1o": Leg("h1_total", g, None, "over", ln["h1t"], -110, f"1H Over {fmt_num(ln['h1t'])} ({a.abbr}-{h.abbr})"),
        "h1u": Leg("h1_total", g, None, "under", ln["h1t"], -110, f"1H Under {fmt_num(ln['h1t'])} ({a.abbr}-{h.abbr})"),
        "tao": Leg("tt", g, a, "over", ln["tt"][0], -110, f"{a.school} team total over {fmt_num(ln['tt'][0])}"),
        "tau": Leg("tt", g, a, "under", ln["tt"][0], -110, f"{a.school} team total under {fmt_num(ln['tt'][0])}"),
        "tho": Leg("tt", g, h, "over", ln["tt"][1], -110, f"{h.school} team total over {fmt_num(ln['tt'][1])}"),
        "thu": Leg("tt", g, h, "under", ln["tt"][1], -110, f"{h.school} team total under {fmt_num(ln['tt'][1])}"),
    }
    if ln["ml"]:
        out["ma"] = Leg("ml", g, a, None, None, ln["ml"][0], f"{a.school} moneyline")
        out["mh"] = Leg("ml", g, h, None, None, ln["ml"][1], f"{h.school} moneyline")
    for lg_ in out.values():
        lg_.year = league.year
    return out


# ═══ Futures (a Monte Carlo of the rest of the season) ═════════════════════

def _reg_games(league):
    return [g for w in range(1, REG + 1) for g in league.schedule.get(w, [])]


def _conf_of(t):
    return getattr(t, "conference", None)


def simulate(book, league, n=320, seed=None):
    """Play the rest of the season n times with the book's numbers."""
    rng = random.Random(seed if seed is not None else f"book:{league.seed}:{league.year}:{league.week}")
    fbs = [t for t in league.teams if not getattr(t, "fcs", False)]
    pw = {t: power(book, league, t) for t in fbs}
    for g in _reg_games(league):
        for t in (g.home, g.away):
            if t not in pw:
                pw[t] = power(book, league, t)
    wins0, cw0, cl0, ls0 = Counter(), Counter(), Counter(), Counter()
    remaining = []
    for g in _reg_games(league):
        if g.played:
            wins0[g.winner] += 1
            ls0[g.loser] += 1
            if g.conference_game:
                cw0[g.winner] += 1
                cl0[g.loser] += 1
        else:
            m = margin(book, league, g.home, g.away, 0 if g.neutral else 1)
            remaining.append((g.home, g.away, phi(m / SIG), g.conference_game))
    confs = {}
    for t in fbs:
        c = _conf_of(t)
        if c and c != "Independent":
            confs.setdefault(c, []).append(t)
    # what's already decided
    ccg = {}
    for g in league.schedule.get(14, []):
        name = getattr(g, "bowl_name", "") or ""
        if name.endswith(" Championship"):
            ccg[name[:-len(" Championship")]] = g
    champs = dict(getattr(league, "conf_champs", {}) or {}) if league.week >= 14 else {}
    seeds = list(getattr(league, "playoff_seeds", []) or []) if league.week >= 14 else []
    cfp_played = {}
    for w in range(15, 19):
        for g in league.schedule.get(w, []):
            if g.game_type in ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship") and g.played:
                cfp_played[frozenset((g.home, g.away))] = g.winner
    title, conf_t, cfp, wins = Counter(), {c: Counter() for c in confs}, Counter(), {t: Counter() for t in fbs}

    def play(a, b, home=None):
        key = frozenset((a, b))
        if key in cfp_played:
            return cfp_played[key]
        m = margin(book, league, a, b, 1 if home is a else -1 if home is b else 0)
        return a if rng.random() < phi(m / SIG) else b

    for _ in range(n):
        w, lo, cw, cl = Counter(wins0), Counter(ls0), Counter(cw0), Counter(cl0)
        for h, a, p, cg in remaining:
            if rng.random() < p:
                win, los = h, a
            else:
                win, los = a, h
            w[win] += 1
            lo[los] += 1
            if cg:
                cw[win] += 1
                cl[los] += 1
        for t in fbs:
            wins[t][w[t]] += 1
        cchamp = {}
        for c, ts in confs.items():
            if c in champs:
                cchamp[c] = champs[c]
                continue
            g = ccg.get(c)
            if g is not None:
                cchamp[c] = g.winner if g.played else play(g.home, g.away)
                continue
            order = sorted(ts, key=lambda t: (-(cw[t] - cl[t]), -w[t], -pw[t] - rng.random() * 3))
            if len(order) >= 2:
                cchamp[c] = play(order[0], order[1])
            elif order:
                cchamp[c] = order[0]
        for c, t in cchamp.items():
            conf_t[c][t] += 1
        if seeds:
            field = seeds
        else:
            rank = lambda t: (lo[t], -w[t], -pw[t] - rng.random() * 2)
            auto = sorted(set(cchamp.values()), key=rank)[:5]
            rest = sorted((t for t in fbs if t not in auto), key=rank)[:7]
            field = sorted(auto + rest, key=rank)
        for t in field:
            cfp[t] += 1
        s = {i + 1: t for i, t in enumerate(field[:12])}
        if len(s) < 12:
            continue
        r1 = {8: play(s[8], s[9], s[8]), 7: play(s[7], s[10], s[7]), 6: play(s[6], s[11], s[6]), 5: play(s[5], s[12], s[5])}
        qf = [play(s[1], r1[8]), play(s[4], r1[5]), play(s[2], r1[7]), play(s[3], r1[6])]
        sf = [play(qf[0], qf[1]), play(qf[2], qf[3])]
        title[play(sf[0], sf[1])] += 1
    return {"n": n, "title": title, "conf": conf_t, "cfp": cfp, "wins": wins, "confs": confs}


def markets_open(league):
    """Which futures can still be bet."""
    wk = league.week
    done = league.season_complete
    return {"title": not done and not _nc_started(league), "conf": wk < 14, "cfp": wk < 14, "heisman": wk < 14,
            "wins": wk == 0}


def _nc_started(league):
    return any(g.game_type == "National Championship" and g.week <= league.week for w in league.schedule
               for g in league.schedule[w])


def _fut_price(p, hold):
    return price(min(0.97, p * hold + 0.0015))


def futures(book, league):
    """All the futures markets, priced (cached for the week)."""
    st = _stamp(league)
    if book.futures and book.futures[0] == st:
        return book.futures[1]
    mc = simulate(book, league)
    n = mc["n"]
    fbs = [t for t in league.teams if not getattr(t, "fcs", False)]
    title = sorted(((t, mc["title"][t] / n) for t in fbs), key=lambda x: -x[1])
    title_rows = [(t, _fut_price(max(p, 0.0008), 1.25), p) for t, p in title if p > 0 or _ovr(league, t) >= 70]
    conf_rows = {}
    for c, cnt in mc["conf"].items():
        rows = sorted(((t, cnt[t] / n) for t in mc["confs"][c]), key=lambda x: -x[1])
        conf_rows[c] = [(t, _fut_price(max(p, 0.002), 1.15), p) for t, p in rows]
    cfp_rows = []
    for t in fbs:
        p = mc["cfp"][t] / n
        if 0.01 <= p <= 0.99:
            cfp_rows.append((t, price(p + 0.0225), price(1 - p + 0.0225), p))
    cfp_rows.sort(key=lambda x: -x[3])
    win_rows = []
    for t in fbs:
        dist = mc["wins"][t]
        tot = sum(dist.values()) or 1
        best = None
        for L in [x + 0.5 for x in range(0, 13)]:
            over = sum(c for k, c in dist.items() if k > L) / tot
            if best is None or abs(over - 0.5) < abs(best[1] - 0.5):
                best = (L, over)
        L, over = best
        if 0.03 < over < 0.97:
            win_rows.append((t, L, price(over + 0.0225), price(1 - over + 0.0225), over))
    win_rows.sort(key=lambda x: (-x[1], x[0].school))
    heis = heisman_rows(book, league)
    mk = {"title": title_rows, "conf": conf_rows, "cfp": cfp_rows, "wins": win_rows, "heisman": heis}
    for t, a, _ in title_rows:
        book.futures_open.setdefault(("title", t), a)
    for c, rows in conf_rows.items():
        for t, a, _ in rows:
            book.futures_open.setdefault(("conf", t), a)
    for p, a, _ in heis:
        book.futures_open.setdefault(("heisman", p), a)
    book.futures = (st, mk)
    return mk


def heisman_rows(book, league):
    r = league.rankings
    cands = []
    if getattr(r, "heisman", None):
        for i, (p, score, blurb) in enumerate(r.heisman[:15]):
            cands.append((p, (16 - i) ** 2.4))
    else:
        pool = []
        for t in league.teams:
            if getattr(t, "fcs", False):
                continue
            tp = power(book, league, t)
            for pos, bonus in (("QB", 4), ("RB", 0), ("WR", -1)):
                p = _starter(t, pos, key=lambda x: x.overall)
                if p is not None:
                    pool.append((p, p.overall + bonus + tp / PTS_PER_OVR * 0.6))
        pool.sort(key=lambda x: -x[1])
        top = pool[0][1] if pool else 0
        cands = [(p, math.exp((s - top) / 2.2)) for p, s in pool[:20]]
    tot = sum(w for _, w in cands) or 1
    return [(p, _fut_price(w / tot, 1.3), w / tot) for p, w in cands]


def future_leg(league, sub, target, odds, side=None, line=None):
    yr = league.year
    if sub == "title":
        return Leg("future", team=target, odds=odds, sub="title", year=yr, label=f"{target.school} to win the national title")
    if sub == "conf":
        return Leg("future", team=target, odds=odds, sub="conf", conf=target.conference, year=yr,
                   label=f"{target.school} to win the {target.conference}")
    if sub == "cfp":
        return Leg("future", team=target, odds=odds, sub="cfp", side=side, year=yr,
                   label=f"{target.school} to {'make' if side == 'yes' else 'miss'} the Playoff")
    if sub == "wins":
        return Leg("future", team=target, odds=odds, sub="wins", side=side, line=line, year=yr,
                   label=f"{target.school} {side} {fmt_num(line)} wins")
    if sub == "heisman":
        return Leg("future", player=target, team=getattr(target, "team", None), odds=odds, sub="heisman", year=yr,
                   label=f"{target.name} to win the Golden Helmet")
    raise ValueError(sub)


# ═══ The Boost ═════════════════════════════════════════════════════════════

def weekly_boost(book, league):
    wk = league.week + 1
    if book.boost and book.boost["stamp"] == _stamp(league):
        return book.boost
    picks = []
    for g in featured(book, league, wk, n=12):
        ln = line(book, league, g)
        if not ln or not ln["ml"]:
            continue
        for key, t, a in (("mh", g.home, ln["ml"][1]), ("ma", g.away, ln["ml"][0])):
            if -300 <= a <= -130:
                picks.append((abs(a + 200), g, key))
    picks.sort(key=lambda x: x[0])
    legs, used = [], set()
    for _, g, key in picks:
        if g in used:
            continue
        legs.append(game_legs(book, league, g)[key])
        used.add(g)
        if len(legs) == 2:
            break
    if len(legs) < 2:
        book.boost = {"stamp": _stamp(league), "legs": None}
        return book.boost
    d = dec(legs[0].odds) * dec(legs[1].odds)
    norm = american(d)
    boosted = american(1 + (d - 1) * 1.3)
    book.boost = {"stamp": _stamp(league), "legs": legs, "was": norm, "odds": boosted, "taken": False}
    return book.boost


# ═══ Taking a bet ══════════════════════════════════════════════════════════

def still_open(league, leg):
    if leg.kind == "future":
        mo = markets_open(league)
        key = {"title": "title", "conf": "conf", "cfp": "cfp", "wins": "wins", "heisman": "heisman"}[leg.sub]
        return mo.get(key, False) and leg.year == league.year
    return leg.game is not None and open_for_betting(league, leg.game)


def parlay_problem(legs):
    """Why these legs can't be parlayed (or None)."""
    if len(legs) < 2:
        return "A parlay needs at least two legs."
    if len(legs) > MAX_LEGS:
        return f"{MAX_LEGS} legs at most."
    seen = set()
    for lg_ in legs:
        if lg_.kind == "future":
            return "Futures can't go in a parlay."
        if lg_.kind == "prop":
            k = (id(lg_.game), "prop", id(lg_.player), lg_.stat)
        else:
            k = (id(lg_.game), lg_.family())
        if k in seen:
            return "One side and one total per game (the book won't take two of the same thing from one game)."
        seen.add(k)
    return None


def teaser_problem(legs):
    if not 2 <= len(legs) <= 4:
        return "Teasers are 2 to 4 legs."
    games = set()
    for lg_ in legs:
        if lg_.kind not in ("spread", "total"):
            return "Teasers take full-game spreads and totals only."
        k = (id(lg_.game), lg_.kind)
        if k in games:
            return "One spread and one total per game."
        games.add(k)
    return None


def parlay_odds(legs):
    d = 1.0
    for lg_ in legs:
        d *= dec(lg_.odds)
    return american(d), d


def teased(leg):
    """A copy of a spread/total leg moved six points your way."""
    t = Leg(leg.kind, leg.game, leg.team, leg.side, None, -110, "", year=leg.year)
    if leg.kind == "spread":
        t.line = leg.line + TEASER_PTS
        t.label = f"{leg.team.school} {fmt_line(t.line)} (teased)"
    else:
        t.line = leg.line - TEASER_PTS if leg.side == "over" else leg.line + TEASER_PTS
        t.label = f"{leg.side.title()} {fmt_num(t.line)} (teased) ({leg.game.away.abbr}-{leg.game.home.abbr})"
    return t


def _copy(leg):
    c = Leg(leg.kind, leg.game, leg.team, leg.side, leg.line, leg.odds, leg.label, player=leg.player, stat=leg.stat,
            sub=leg.sub, year=leg.year, conf=leg.conf)
    return c


def place(book, league, kind, legs, stake, boosted_odds=None, acct=None):
    """Take the bet. Returns (bet, None) or (None, why not). acct: whose money (you, or a regular)."""
    acct = acct or book
    stake = round(float(stake), 2)
    if stake < 1:
        return None, "The minimum is $1."
    if stake > acct.bank + 1e-9:
        return None, f"You have {money(acct.bank)}."
    for lg_ in legs:
        if not still_open(league, lg_):
            return None, f"That market is closed: {lg_.label}."
    legs = [_copy(x) for x in legs]
    if kind == "parlay":
        why = parlay_problem(legs)
        if why:
            return None, why
        odds, d = parlay_odds(legs)
        if stake * (d - 1) > PARLAY_CAP:
            return None, f"The book caps parlay winnings at {money(PARLAY_CAP)}."
    elif kind == "teaser":
        why = teaser_problem(legs)
        if why:
            return None, why
        legs = [teased(x) for x in legs]
        odds = TEASER_ODDS[len(legs)]
    elif kind == "boost":
        if stake > BOOST_MAX:
            return None, f"The Boost is {money(BOOST_MAX)} max."
        odds = boosted_odds
    else:
        if len(legs) != 1:
            return None, "One leg per straight bet."
        odds = legs[0].odds
        kind = "future" if legs[0].kind == "future" else "straight"
    wk = league.week + 1 if not league.season_complete else league.week
    b = Bet(kind, legs, stake, odds, league.year, wk, boosted=kind == "boost")
    b.id = book.next_id
    book.next_id += 1
    acct.bank = round(acct.bank - stake, 2)
    acct.bets.append(b)
    return b, None


# ═══ Grading ═══════════════════════════════════════════════════════════════

def _h1(g, t):
    box = getattr(g, "box", None)
    ln = getattr(box, "line", None) if box is not None else None
    if not ln or t not in ln or len(ln[t]) < 2:
        return None
    return sum(ln[t][:2])


def _cmp(val, line, side):
    if val is None:
        return "void"
    if val == line:
        return "push"
    return "won" if (val > line) == (side == "over") else "lost"


def grade_leg(league, leg):
    """won · lost · push · void, or None if it isn't decided yet."""
    if leg.kind == "future":
        return _grade_future(league, leg)
    g = leg.game
    if g is None or not g.played or g.home_score is None:
        return None
    if leg.kind in ("spread", "ml"):
        t = leg.team
        m = g.score_for(t) - g.score_for(g.opponent_of(t))
        if leg.kind == "ml":
            return "won" if m > 0 else "lost"
        v = m + leg.line
        return "push" if v == 0 else "won" if v > 0 else "lost"
    if leg.kind == "total":
        return _cmp(g.home_score + g.away_score, leg.line, leg.side)
    if leg.kind == "tt":
        return _cmp(g.score_for(leg.team), leg.line, leg.side)
    if leg.kind == "h1_spread":
        a, b = _h1(g, leg.team), _h1(g, g.opponent_of(leg.team))
        if a is None or b is None:
            return "void"
        v = a - b + leg.line
        return "push" if v == 0 else "won" if v > 0 else "lost"
    if leg.kind == "h1_total":
        a, b = _h1(g, g.home), _h1(g, g.away)
        return _cmp(None if a is None or b is None else a + b, leg.line, leg.side)
    if leg.kind == "prop":
        box = getattr(g, "box", None)
        st = getattr(box, "stats", {}) if box is not None else {}
        c = st.get(leg.player)
        if c is None:
            return "void"                               # he didn't play
        if leg.stat == "td":
            return "won" if sum(c.get(k, 0) for k in ("rush_td", "rec_td", "kr_td", "pr_td")) > 0 else "lost"
        return _cmp(c.get(leg.stat, 0), leg.line, leg.side)
    return None


def _grade_future(league, leg):
    if leg.year != league.year:
        return "void"
    if leg.sub == "wins":
        games = [g for g in league.team_games(leg.team) if g.game_type == "Regular Season"]
        if not games or not all(g.played for g in games):
            return None
        w = sum(1 for g in games if g.winner is leg.team)
        return _cmp(w, leg.line, leg.side)
    if leg.sub == "conf":
        champs = getattr(league, "conf_champs", {}) or {}
        if league.week < 14 or leg.conf not in champs:
            return None if not league.season_complete else "lost"
        return "won" if champs[leg.conf] is leg.team else "lost"
    if leg.sub == "cfp":
        seeds = getattr(league, "playoff_seeds", None) or []
        if league.week < 14 or not seeds:
            return None
        made = leg.team in seeds
        return "won" if made == (leg.side == "yes") else "lost"
    if leg.sub == "title":
        rec = league.champion_of(league.year)
        if rec is None:
            if league.season_complete:
                return "void"
            # eliminated? a playoff team that lost, or a team that missed the field
            seeds = getattr(league, "playoff_seeds", None) or []
            if league.week >= 14 and seeds and leg.team not in seeds:
                return "lost"
            for w in range(15, 19):
                for g in league.schedule.get(w, []):
                    if g.played and g.game_type.startswith(("NP", "National")) and g.loser is leg.team:
                        return "lost"
            return None
        return "won" if rec.champion == leg.team.school else "lost"
    if leg.sub == "heisman":
        if not league.season_complete:
            return None
        h = league.rankings.heisman
        return "won" if h and h[0][0] is leg.player else "lost"
    return None


def settle(book, league):
    """Grade every open bet that can be graded — yours and the regulars'. Returns yours settled now."""
    done = _settle_acct(book, league, book)
    theirs = []
    for r in book.__dict__.get("regulars") or []:
        theirs += [(r, b) for b in _settle_acct(book, league, r)]
    if theirs:
        import regulars
        regulars.after_settle(book, league, theirs)
    return done


def _settle_acct(book, league, acct):
    done = []
    for b in acct.open_bets:
        for lg_ in b.legs:
            if lg_.status is None:
                lg_.status = grade_leg(league, lg_)
                if lg_.status is not None and lg_.kind in ("spread", "total") and lg_.game is not None:
                    c = book.cache.get(lg_.game)
                    if c:
                        ln = c[1]
                        lg_.closing = (ln["spread"] if lg_.team is lg_.game.home else -ln["spread"]) \
                            if lg_.kind == "spread" else ln["total"]
        st = [lg_.status for lg_ in b.legs]
        if b.kind in ("straight", "future"):
            s = st[0]
            if s is None:
                continue
            b.status = s
            b.payout = round(b.stake * dec(b.odds), 2) if s == "won" else b.stake if s in ("push", "void") else 0.0
        elif "lost" in st:
            b.status, b.payout = "lost", 0.0
        elif any(x is None for x in st):
            continue
        else:
            won = [lg_ for lg_ in b.legs if lg_.status == "won"]
            if b.kind == "teaser":
                if len(won) >= 2:
                    b.status, b.payout = "won", round(b.stake * dec(TEASER_ODDS[len(won)]), 2)
                else:
                    b.status, b.payout = "push", b.stake
            elif b.kind == "boost":
                if len(won) == len(b.legs):
                    b.status, b.payout = "won", round(b.stake * dec(b.odds), 2)
                elif not won:
                    b.status, b.payout = "push", b.stake
                else:
                    d = 1.0
                    for lg_ in won:
                        d *= dec(lg_.odds)
                    b.status, b.payout = "won", round(b.stake * d, 2)
            else:
                if not won:
                    b.status, b.payout = "push", b.stake
                else:
                    d = 1.0
                    for lg_ in won:
                        d *= dec(lg_.odds)
                    b.status, b.payout = "won", round(b.stake * d, 2)
        if b.status != "open":
            b.settled = (league.year, league.week)
            acct.bank = round(acct.bank + b.payout, 2)
            if acct is book:
                book.unseen.append(b)
            done.append(b)
            acct.seasons[b.year] = round(acct.seasons.get(b.year, 0.0) + b.net, 2)
    return done


# ═══ The calendar ══════════════════════════════════════════════════════════

def before_week(league):
    """Right before a week's games: their lines close."""
    book = get(league, create=False)
    if book is None:
        return
    if book.year != league.year:
        new_season(league, book)
    for g in games_in(league, league.week + 1):
        line(book, league, g)


def after_week(league, games):
    """After the last whistle: records against the number, the book learns, bets pay, lines move."""
    book = get(league, create=False)
    if book is None:
        return
    for g in games:
        if not g.played:
            continue
        c = book.cache.get(g)
        if c is None:
            continue
        ln = c[1]
        m = g.home_score - g.away_score
        ats = m + ln["spread"]
        tot = g.home_score + g.away_score
        for t, v in ((g.home, ats), (g.away, -ats)):
            r = book.ats.setdefault(t, [0, 0, 0])
            r[0 if v > 0 else 1 if v < 0 else 2] += 1
            o = book.ou.setdefault(t, [0, 0, 0])
            o[0 if tot > ln["total"] else 1 if tot < ln["total"] else 2] += 1
        miss = max(-24, min(24, m - ln["m"]))
        seen = book.__dict__.setdefault("seen", {})
        for t, sgn in ((g.home, 1), (g.away, -1)):
            n = seen.get(t, 0)
            book.adj[t] = max(-ADJ_CAP, min(ADJ_CAP, book.adj.get(t, 0.0) + sgn * miss / (n + ADJ_PRIOR)))
            seen[t] = n + 1
        tmiss = max(-24, min(24, tot - ln["total"]))
        # The scoring climate, tracked at the median (a few shootouts shouldn't drag the number up).
        book.tbias = max(-12.0, min(12.0, book.__dict__.get("tbias", 0.0) + 0.1 * ((tmiss > 0) - (tmiss < 0))))
        for t in (g.home, g.away):
            n = seen.get(t, 1) - 1
            book.tadj[t] = max(-ADJ_CAP, min(ADJ_CAP, book.tadj.get(t, 0.0) + tmiss / 2 / (n + ADJ_PRIOR + 3)))
    settle(book, league)
    book.ledger.append((league.year, league.week_name(league.week), book.bank))
    for r in book.__dict__.get("regulars") or []:
        r.ledger.append(r.bank + sum(b.stake for b in r.open_bets))
    refresh_all(league, book)
    import regulars
    regulars.place_week(book, league)               # the regulars make next week's picks


def new_season(league, book):
    """A new year at the window: fresh numbers, the bankroll carries over."""
    for acct in [book] + list(book.__dict__.get("regulars") or []):
        for b in acct.open_bets:                   # nothing should be left; refund anything that is
            for lg_ in b.legs:
                if lg_.status is None:
                    lg_.status = "void"
            b.status, b.payout = "void", b.stake
            b.settled = (book.year, "end")
            acct.bank = round(acct.bank + b.stake, 2)
            if acct is book:
                book.unseen.append(b)
    import regulars
    regulars.season_end(book, book.year)            # the table's winner gets a star
    book.ats_history[book.year] = {t.school: tuple(v) for t, v in book.ats.items()}
    book.year = league.year
    book.adj = {t: v * 0.5 for t, v in book.adj.items()}       # half carries over (programs are programs)
    book.seen = {}
    book.tadj = {t: v * 0.5 for t, v in book.tadj.items()}
    book.hist, book.cache, book.ats, book.ou = {}, {}, {}, {}
    book.futures, book.futures_open, book.props, book.boost = None, {}, {}, None
    book.slip = []
    book.ledger.append((league.year, "Preseason", book.bank))
    refresh_all(league, book)
    regulars.place_week(book, league)               # preseason futures and Week 1


def reload(book, league):
    book.bank = round(book.bank + RELOAD, 2)
    book.reloads += 1
    book.ledger.append((league.year, "Reload", book.bank))


# ═══ Summaries ════════════════════════════════════════════════════════════

def record(bets):
    w = sum(1 for b in bets if b.status == "won")
    l = sum(1 for b in bets if b.status == "lost")
    p = sum(1 for b in bets if b.status in ("push", "void"))
    risked = sum(b.stake for b in bets if b.status in ("won", "lost"))
    net = sum(b.net for b in bets)
    return w, l, p, risked, net


def my_action(book, g):
    """Your open bets that touch this game."""
    return [b for b in book.open_bets if any(lg_.game is g for lg_ in b.legs)]


def clv(book, league, leg):
    """How the number has moved since you bet it (+ = in your favor), in points."""
    if leg.kind not in ("spread", "total") or leg.game is None:
        return None
    c = book.cache.get(leg.game)
    if not c:
        return None
    ln = c[1]
    if leg.kind == "spread":
        now = ln["spread"] if leg.team is leg.game.home else -ln["spread"]
        return leg.line - now
    return (leg.line - ln["total"]) if leg.side == "under" else (ln["total"] - leg.line)
