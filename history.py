"""
history.py — Look anything up in this world's past.

Every game ever played here (every archived season, plus this season so far) is indexed once into flat records —
year, week, kind, both schools, both conferences, both head coaches, both poll ranks at kickoff, the score — and every
player's stat line is indexed by name. A Query then picks a SUBJECT and filters the games:

  subject     a team, a head coach, a conference, or a player
              (+ "at school ..." for a coach or player; + "with coach ..." for a team)
  opponent    a team, a head coach, a conference, and/or a poll tier (Top 25, Top 10, unranked)
  games       seasons from-to; regular season / conference / non-conference / postseason / bowls / playoff /
              conference title games; home / away / neutral; close games (8 or fewer); wins / losses;
              the subject's own rank tier

Examples: Auburn vs Alabama · Auburn vs Alabama while Golesh coached Auburn · Kirby Smart vs Dan Lanning wherever
they coached · a player against Top 25 teams (anywhere, or only at one school) · Texas vs the SEC · the Big Ten vs
the SEC · a coach's record in bowls · a team in close games.

Head coaches per game are recorded from v27 on; earlier seasons fall back to who coached the school that season.
"""
from collections import Counter

KINDS = ["all", "regular", "conference", "nonconf", "postseason", "bowls", "playoff", "ccg"]
KIND_NAMES = {"all": "all games", "regular": "regular season", "conference": "conference games",
              "nonconf": "non-conference", "postseason": "postseason", "bowls": "bowls", "playoff": "playoff",
              "ccg": "conference title games"}
RANKS = ["any", "top25", "top10", "unranked"]
RANK_NAMES = {"any": "any", "top25": "Top 25", "top10": "Top 10", "unranked": "unranked"}
SITES = ["any", "home", "away", "neutral"]
RESULTS = ["any", "wins", "losses"]
SUBJECTS = ["team", "coach", "conf", "player"]
SUBJECT_NAMES = {"team": "Team", "coach": "Head coach", "conf": "Conference", "player": "Player"}


class Rec:
    """One game, both sides."""
    __slots__ = ("year", "week", "gtype", "label", "h", "a", "hconf", "aconf", "hs", "as_", "hr", "ar",
                 "confg", "neutral", "hhc", "ahc", "src", "fcs_h", "fcs_a")

    def side(self, home):
        """(school, conf, score, rank, coach) for one side."""
        if home:
            return self.h, self.hconf, self.hs, self.hr, self.hhc
        return self.a, self.aconf, self.as_, self.ar, self.ahc


def _kind_ok(r, kind):
    if kind == "all":
        return True
    gt = (r.gtype or "Regular Season")
    if kind == "regular":
        return gt == "Regular Season"
    if kind == "conference":
        return bool(r.confg) and gt == "Regular Season"
    if kind == "nonconf":
        return not r.confg and gt == "Regular Season"
    if kind == "postseason":
        return gt != "Regular Season"
    if kind == "bowls":
        return gt == "Bowl"
    if kind == "playoff":
        return "CFP" in gt or "Playoff" in gt or "National Championship" in gt
    if kind == "ccg":
        return "Conference" in gt and "Championship" in gt
    return True


def _rank_ok(rank, tier):
    if tier == "any":
        return True
    if tier == "unranked":
        return not rank
    if tier == "top25":
        return bool(rank) and rank <= 25
    if tier == "top10":
        return bool(rank) and rank <= 10
    return True


# ═══ The index ══════════════════════════════════════════════════════════════
_CACHE = {}


def _coach_book(league):
    """{(school, year): head coach} from every coach's season records — for games played before coaches were
    stamped on each game. A season split by a firing goes to whoever coached more of it."""
    best = {}
    pool = []
    for t in league.teams:
        if t.coach is not None:
            pool.append(t.coach)
    pool += list(getattr(league, "coach_pool", []) or []) + list(getattr(league, "retired_coaches", []) or [])
    for c in pool:
        for h in getattr(c, "history", None) or []:
            k = (h.get("school"), h.get("year"))
            g = h.get("w", 0) + h.get("l", 0)
            if k[0] and (k not in best or g > best[k][1]):
                best[k] = (c.name, g)
    return {k: v[0] for k, v in best.items()}


def _rec(g, year, live, book):
    r = Rec()
    r.year, r.week = year, g.week
    r.gtype = g.game_type
    r.label = getattr(g, "display_name", None) or getattr(g, "bowl_name", None) or \
        (g.game_type if g.game_type != "Regular Season" else f"Week {g.week}")
    r.h, r.a = g.home.school, g.away.school
    r.hconf = "FCS" if getattr(g.home, "fcs", False) else getattr(g.home, "conference", "")
    r.aconf = "FCS" if getattr(g.away, "fcs", False) else getattr(g.away, "conference", "")
    r.fcs_h, r.fcs_a = getattr(g.home, "fcs", False), getattr(g.away, "fcs", False)
    r.hs, r.as_ = g.home_score, g.away_score
    ranks = getattr(g, "ranks", None) or {}
    r.hr, r.ar = ranks.get(g.home), ranks.get(g.away)
    r.confg = bool(getattr(g, "conference_game", False))
    r.neutral = bool(getattr(g, "neutral", False))
    hc = getattr(g, "hc", None) or {}
    r.hhc = hc.get(g.home) or book.get((r.h, year))
    r.ahc = hc.get(g.away) or book.get((r.a, year))
    if live and not r.hhc:
        r.hhc = getattr(getattr(g.home, "coach", None), "name", None)
    if live and not r.ahc:
        r.ahc = getattr(getattr(g.away, "coach", None), "name", None)
    r.src = g
    return r


def index(league):
    """(games, players): every game as a Rec (oldest first) and {player name: [(rec, home?, pos, class, line)]}."""
    arc = getattr(league, "archive", {}) or {}
    live = [g for w in sorted(league.schedule) for g in league.schedule[w] if g.played]
    key = (id(league), tuple(sorted(arc)), league.year, len(live))
    hit = _CACHE.get("key")
    if hit == key:
        return _CACHE["games"], _CACHE["players"]
    book = _coach_book(league)
    games = []
    for yr in sorted(arc):
        for g in arc[yr]:
            games.append(_rec(g, yr, False, book))
    for g in live:
        games.append(_rec(g, league.year, True, book))
    games.sort(key=lambda r: (r.year, r.week))
    players = {}
    for r in games:
        box = getattr(r.src, "box", None)
        stats = getattr(box, "stats", None) if box is not None else None
        if not stats:
            continue
        for p, line in stats.items():
            try:
                side_team = box.team_of(p)
            except Exception:
                continue
            home = getattr(side_team, "school", None) == r.h
            players.setdefault(p.name, []).append((r, home, p.position, getattr(p, "class_label", ""), line))
    _CACHE.clear()
    _CACHE.update(key=key, games=games, players=players)
    return games, players


def names(league):
    """Everything you can look up: schools, coaches, conferences, players."""
    games, players = index(league)
    schools, coaches, confs = set(), set(), set()
    for r in games:
        schools.update((r.h, r.a))
        confs.update(c for c in (r.hconf, r.aconf) if c)
        coaches.update(c for c in (r.hhc, r.ahc) if c)
    return sorted(schools), sorted(coaches), sorted(confs), players


# ═══ The query ══════════════════════════════════════════════════════════════
class Query:
    def __init__(self, **kw):
        self.subj_type = "team"
        self.subj = None
        self.subj_school = None          # coach / player: only while at this school
        self.subj_coach = None           # team: only while this man coached it
        self.subj_rank = "any"
        self.opp_school = None
        self.opp_coach = None
        self.opp_conf = None
        self.opp_rank = "any"
        self.year_from = None
        self.year_to = None
        self.kind = "all"
        self.site = "any"
        self.close = False
        self.result = "any"
        self.__dict__.update(kw)

    def copy(self):
        return Query(**dict(self.__dict__))

    def describe(self):
        """A one-line title: 'Auburn vs Alabama · Top 25 · bowls · 2027-2031'."""
        s = self.subj or "—"
        if self.subj_type == "coach":
            s = f"Coach {s}"
        if self.subj_school and self.subj_type in ("coach", "player"):
            s += f" (at {self.subj_school})"
        if self.subj_coach and self.subj_type == "team":
            s += f" (under {self.subj_coach})"
        opp = [x for x in (self.opp_school, ("Coach " + self.opp_coach) if self.opp_coach else None, self.opp_conf) if x]
        if self.opp_rank != "any":
            opp.append(RANK_NAMES[self.opp_rank] + (" teams" if self.opp_rank != "unranked" else " teams"))
        out = s + (" vs " + " · ".join(opp) if opp else "")
        bits = []
        if self.kind != "all":
            bits.append(KIND_NAMES[self.kind])
        if self.site != "any":
            bits.append(self.site)
        if self.close:
            bits.append("close games")
        if self.result != "any":
            bits.append(self.result)
        if self.subj_rank != "any":
            bits.append(f"while {RANK_NAMES[self.subj_rank]}")
        if self.year_from or self.year_to:
            bits.append(f"{self.year_from or '…'}–{self.year_to or '…'}")
        return out + ("  ·  " + " · ".join(bits) if bits else "")


class Hit:
    """One game from the subject's side."""
    __slots__ = ("r", "home", "school", "opp", "opp_conf", "pf", "pa", "rank", "opp_rank", "coach", "opp_coach",
                 "line", "pos", "cls")

    @property
    def won(self):
        return self.pf > self.pa

    @property
    def site(self):
        return "neutral" if self.r.neutral else "home" if self.home else "away"


def _hit(r, home, line=None, pos=None, cls=None):
    h = Hit()
    h.r, h.home = r, home
    h.school, conf, h.pf, h.rank, h.coach = r.side(home)
    h.opp, h.opp_conf, h.pa, h.opp_rank, h.opp_coach = r.side(not home)
    h.line, h.pos, h.cls = line, pos, cls
    return h


def _rest_ok(q, h):
    if q.subj_school and q.subj_type in ("coach", "player") and h.school != q.subj_school:
        return False
    if q.subj_coach and q.subj_type == "team" and h.coach != q.subj_coach:
        return False
    if q.opp_school and h.opp != q.opp_school:
        return False
    if q.opp_coach and h.opp_coach != q.opp_coach:
        return False
    if q.opp_conf and h.opp_conf != q.opp_conf:
        return False
    if not _rank_ok(h.opp_rank, q.opp_rank) or not _rank_ok(h.rank, q.subj_rank):
        return False
    if q.year_from and h.r.year < q.year_from:
        return False
    if q.year_to and h.r.year > q.year_to:
        return False
    if not _kind_ok(h.r, q.kind):
        return False
    if q.site != "any" and h.site != q.site:
        return False
    if q.close and abs(h.pf - h.pa) > 8:
        return False
    if q.result == "wins" and not h.won:
        return False
    if q.result == "losses" and h.won:
        return False
    return True


def run(league, q):
    """Every game that matches, oldest first, as Hits from the subject's side."""
    games, players = index(league)
    out = []
    if not q.subj:
        return out
    if q.subj_type == "player":
        for r, home, pos, cls, line in players.get(q.subj, []):
            h = _hit(r, home, line, pos, cls)
            if _rest_ok(q, h):
                out.append(h)
        return out
    for r in games:
        for home in (True, False):
            school, conf, _, _, coach = r.side(home)
            if q.subj_type == "team" and school != q.subj:
                continue
            if q.subj_type == "coach" and coach != q.subj:
                continue
            if q.subj_type == "conf" and conf != q.subj:
                continue
            h = _hit(r, home)
            if _rest_ok(q, h):
                out.append(h)
                break                                   # one row per game (conference vs itself counts once)
    return out


# ═══ Summaries ══════════════════════════════════════════════════════════════
def summary(hits):
    """Record, points, streaks, the biggest win and the worst loss, first and last meeting."""
    s = {"g": len(hits), "w": sum(1 for h in hits if h.won), "pf": sum(h.pf for h in hits), "pa": sum(h.pa for h in hits)}
    s["l"] = s["g"] - s["w"]
    if not hits:
        return s
    cur, n = None, 0
    for h in reversed(hits):
        if cur is None:
            cur = h.won
        if h.won != cur:
            break
        n += 1
    s["streak"] = ("W" if cur else "L") + str(n)
    best = run_ = 0
    for h in hits:
        run_ = run_ + 1 if h.won else 0
        best = max(best, run_)
    s["best_streak"] = best
    wins = [h for h in hits if h.won]
    losses = [h for h in hits if not h.won]
    s["big_win"] = max(wins, key=lambda h: h.pf - h.pa) if wins else None
    s["bad_loss"] = max(losses, key=lambda h: h.pa - h.pf) if losses else None
    s["first"], s["last"] = hits[0], hits[-1]
    s["ranked_w"] = sum(1 for h in hits if h.won and h.opp_rank and h.opp_rank <= 25)
    s["ranked_g"] = sum(1 for h in hits if h.opp_rank and h.opp_rank <= 25)
    s["close_w"] = sum(1 for h in hits if h.won and abs(h.pf - h.pa) <= 8)
    s["close_g"] = sum(1 for h in hits if abs(h.pf - h.pa) <= 8)
    return s


def totals(hits):
    """A player's stat lines added up (longest plays kept as the longest)."""
    t = Counter()
    for h in hits:
        for k, v in (h.line or {}).items():
            if k.endswith("_long"):
                t[k] = max(t[k], v)
            else:
                t[k] += v
    return t


def impact(line):
    """How big a day was (for 'best game')."""
    g = line or {}
    return (g.get("pass_yds", 0) * .04 + (g.get("rush_yds", 0) + g.get("rec_yds", 0)) * .1
            + 6 * (g.get("pass_td", 0) + g.get("rush_td", 0) + g.get("rec_td", 0)) - 3 * g.get("pass_int", 0)
            + g.get("tkl", 0) * .8 + g.get("sack", 0) * 3 + g.get("int", 0) * 5 + g.get("ff", 0) * 3
            + g.get("fg_made", 0) * 2)


def statline(line):
    """'22/31, 287 yds, 3 TD, 1 INT · 6-41' — whatever he did."""
    g = line or {}
    parts = []
    if g.get("pass_att"):
        parts.append(f"{g.get('pass_cmp', 0)}/{g['pass_att']}, {g.get('pass_yds', 0)} yds, {g.get('pass_td', 0)} TD"
                     + (f", {g['pass_int']} INT" if g.get("pass_int") else ""))
    if g.get("rush_att"):
        parts.append(f"{g['rush_att']}-{g.get('rush_yds', 0)} rush" + (f", {g['rush_td']} TD" if g.get("rush_td") else ""))
    if g.get("rec"):
        parts.append(f"{g['rec']}-{g.get('rec_yds', 0)} rec" + (f", {g['rec_td']} TD" if g.get("rec_td") else ""))
    if g.get("tkl") or g.get("sack") or g.get("int"):
        d = [f"{g.get('tkl', 0)} tkl"]
        if g.get("tfl"):
            d.append(f"{g['tfl']} TFL")
        if g.get("sack"):
            d.append(f"{g['sack']} sk")
        if g.get("int"):
            d.append(f"{g['int']} INT")
        if g.get("pbu"):
            d.append(f"{g['pbu']} PBU")
        parts.append(", ".join(d))
    if g.get("fg_att") or g.get("xp_att"):
        parts.append(f"FG {g.get('fg_made', 0)}/{g.get('fg_att', 0)}, XP {g.get('xp_made', 0)}/{g.get('xp_att', 0)}")
    if g.get("punts"):
        parts.append(f"{g['punts']} punts, {g.get('punt_yds', 0) / g['punts']:.1f} avg")
    return " · ".join(parts) or "—"


def group(hits, by):
    """Break the games down: by opponent, opponent's coach, opponent's conference, season, or the subject's school /
    coach. -> [(label, w, l, pf, pa)] most games first."""
    keyf = {"opp": lambda h: h.opp, "opp_coach": lambda h: h.opp_coach or "—", "opp_conf": lambda h: h.opp_conf or "—",
            "season": lambda h: str(h.r.year), "school": lambda h: h.school, "coach": lambda h: h.coach or "—"}[by]
    d = {}
    for h in hits:
        k = keyf(h)
        w, l, pf, pa = d.get(k, (0, 0, 0, 0))
        d[k] = (w + h.won, l + (not h.won), pf + h.pf, pa + h.pa)
    rows = [(k,) + v for k, v in d.items()]
    if by == "season":
        rows.sort(key=lambda x: x[0], reverse=True)
    else:
        rows.sort(key=lambda x: (-(x[1] + x[2]), -x[1], x[0]))
    return rows
