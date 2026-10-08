"""
gameday_show.py — Campus Countdown, every Saturday morning, before the games.

  1. Pick a site: the biggest ranked matchup, rivalries, upset stakes, first-time
     hosts — and not the same campus too often.
  2. Build the show from the season: records, ranks, streaks, stats, the
     Golden Helmet race, hot seats, program goals, and the crowd on the lawn.
  3. Every analyst picks the slate with his own model; the guest picker picks
     with his heart; the coach puts on the headgear. Picks are graded after
     the games and kept as a season-long standings race.

The show draws its own random numbers, so watching it never changes a result.
"""
import random
import textwrap
import time

import gameday_cast as gc
import gameday_history
import settings
from ui import C, WIDTH, ask, clear, pad, paint, rule, title_bar

LABEL_W = 12
COLORS = {"host": C.BWHITE, "film": C.BCYAN, "coach": C.BYELLOW, "boom": C.BMAGENTA, "defender": C.BGREEN,
          "crowd": C.BRED, "reporter": C.GRAY, "guest": C.BYELLOW, "player": C.BWHITE}


class Skip(Exception):
    pass


def _merge_content():
    """Fold the Phase 2 pools (gameday_more.py) into the base pools, once."""
    import gameday_scenes as sc
    import gameday_more as more
    if getattr(sc, "_merged", False):
        return
    for src in (more.STORY_MORE, more.STORY_MORE_2):
        for k, v in src.items():
            sc.STORY.setdefault(k, []).extend(v)
    for k, v in more.OPENERS_MORE.items():
        sc.OPENERS.setdefault(k, []).extend(v)
    for k, v in more.SIGNS_MORE.items():
        sc.SIGNS.setdefault(k, []).extend(v)
    for k, v in more.CAST_SIGNS_MORE.items():
        sc.SIGNS["cast"].setdefault(k, []).extend(v)
    for k, v in more.SIGN_REPLIES_MORE.items():
        sc.SIGN_REPLIES.setdefault(k, []).extend(v)
    for k, v in more.REASONS_MORE.items():
        sc.REASONS.setdefault(k, []).extend(v)
    sc.COACH_STORIES.extend(more.COACH_STORIES_MORE)
    sc.CROWD_CHALLENGES.extend(more.CROWD_CHALLENGES_MORE)
    gc.BANTER.extend(more.BANTER_MORE)
    gc.GUEST_PICKERS.extend(more.GUESTS_MORE)
    for k, qs in more.INTERVIEW_QUESTIONS_MORE.items():
        more.INTERVIEW_MORE[k][0].extend(qs)
    more.FOLLOWUP_ANSWERS.extend(more.FOLLOWUP_ANSWERS_MORE)
    more.INTERVIEW_CLOSERS.extend(more.INTERVIEW_CLOSERS_MORE)
    import gameday_extra as ex
    for k, v in ex.INTERVIEW_QA_EXTRA.items():
        more.INTERVIEW_QA.setdefault(k, []).extend(v)
    gc.BANTER.extend(ex.BANTER_EXTRA)
    # more versions of the thinner storylines
    import gameday_variety as gv
    for k, v in gv.STORY_VARIETY.items():
        sc.STORY.setdefault(k, []).extend(v)
    sc._merged = True


# ═══ State kept on the league ═══════════════════════════════════════════════

def straight_quotes(text):
    """Curly quotes don't render in every terminal: one style, straight, everywhere."""
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')


def _state(league):
    if not hasattr(league, "gameday"):
        league.gameday = {"records": {}, "pending": [], "visits": {}, "log": []}
    return league.gameday


def standings(league, year=None):
    rec = _state(league)["records"].get(year or league.year, {})
    keys = list(gc.ORDER)
    return sorted(((k, *rec.get(k, [0, 0])) for k in keys), key=lambda x: (-x[1], x[2]))


def grade(league, games):
    """After the games: grade every pick that was made this week."""
    import gameday_dossier
    gameday_dossier.record_h2h(league, games)
    st = _state(league)
    rec = st["records"].setdefault(league.year, {})
    keep = []
    hits = {}
    for key, game, team in st["pending"]:
        if not game.played:
            keep.append((key, game, team))
            continue
        r = rec.setdefault(key, [0, 0])
        won = game.winner is team
        r[0 if won else 1] += 1
        other = game.away if team is game.home else game.home
        ro, rt = getattr(game, "ranks", {}).get(other), getattr(game, "ranks", {}).get(team)
        if won and ro and (not rt or rt > ro):
            hits[key] = team.school                 # hit an underdog: next week, he'll mention it
    st["pending"] = keep
    st["last_hits"] = hits


# ═══ What the tape actually shows ═══════════════════════════════════════════

def season_snaps(league, team):
    """(games played this season, snaps on both sides of the ball in them)."""
    n, snaps = 0, 0
    for g in league.team_games(team):
        if not g.played or g.box is None:
            continue
        n += 1
        ts = getattr(g.box, "team_stats", {})
        snaps += sum(ts[t]["plays"] for t in ts)
    return n, snaps


def film_line(league, teams, you=None):
    """A film-junkie answer that fits the calendar. Early in the season 'every snap
    they've played this year' is one game — so say the number (it sounds obsessive,
    not trivial) and lean on last season until there's real tape."""
    games, snaps = 0, 0
    for t in teams:
        g, s = season_snaps(league, t)
        games = max(games, g)
        snaps += s
    both = len(teams) > 1
    if games == 0 or snaps == 0:
        return (f"I've watched every snap both of these teams played last season{', ' + you if you else ''}."
                if both else "Film, film, and more film. I've seen every snap from their last season.")
    if games < 3:
        return (f"I've watched all {snaps} snaps these two have played this year{', ' + you if you else ''}. "
                f"Twice. And all of last season, for context." if both else
                f"Film, film, and more film. I've seen all {snaps} snaps they've played this year. Twice. "
                f"Then I went back to last season.")
    return (f"I've watched all {snaps} snaps these two teams have played this year{', ' + you if you else ''}."
            if both else f"Film, film, and more film. I've seen all {snaps} snaps they've played this year. Twice.")


def signature_clip(league, team):
    """The one clip a player would show a recruit — from a real game in this save
    when there is one, from last season when there isn't, and general if neither."""
    best, score = None, -1
    for g in league.team_games(team):
        if not g.played or g.winner is not team:
            continue
        opp = g.opponent_of(team)
        margin = g.score_for(team) - g.score_for(opp)
        ranked = (getattr(g, "ranks", {}) or {}).get(opp)
        close = margin <= 8
        v = (30 - ranked if ranked else 0) + (20 if close else 0)
        if v > score and (ranked or close):
            best, score = (opp.school, ranked, close, g.week), v
    if best:
        opp, ranked, close, wk = best
        who = f"No. {ranked} {opp}" if ranked else opp
        if close:
            return f"The fourth-quarter drive against {who}. Every guy did his job on every play."
        return f"The way we played against {who}. Every guy did his job on every play."
    try:
        import archive
        last = [g for g in archive.games_for(league, league.year - 1, team.school)
                if g.winner.school == team.school and g.score_for(g.winner) - g.score_for(g.loser) <= 8]
    except Exception:
        last = []
    if last:
        return f"The fourth-quarter drive against {last[-1].loser.school} last year. Every guy did his job on every play."
    return "A fourth-quarter drive we had last year. Every guy did his job on every play."


# ═══ Choosing the site ══════════════════════════════════════════════════════

def _is_fbs_game(g):
    return not getattr(g.home, "fcs", False) and not getattr(g.away, "fcs", False)


def interest(league, g):
    R = league.rankings
    ra, rh = R.rank_of(g.away), R.rank_of(g.home)
    score = (26 - ra if ra else 0) + (26 - rh if rh else 0)
    if ra and rh:
        score += 15
    from commentary import rivalry_name
    if rivalry_name(g.home, g.away):
        score += 10
    score += (g.home.prestige + g.away.prestige) / 20
    score += {"National Championship": 200, "NP Semifinal": 120, "NP Quarterfinal": 80,
              "NP First Round": 40, "Conference Championship": 30}.get(g.game_type, 0)
    return score


def choose_site(league, games):
    st = _state(league)
    games = [g for g in games if not g.played]
    options = [g for g in games if _is_fbs_game(g) and g.game_type != "Bowl"] or [g for g in games if _is_fbs_game(g)]
    best, best_score = None, -1e9
    for g in options:
        s = interest(league, g)
        visits = st["visits"].get(g.home.school, [])
        if any(y == league.year for y, _ in visits) and not g.neutral:
            s -= 40                                    # already been there this year
        elif any(y == league.year - 1 for y, _ in visits):
            s -= 12
        elif not visits and not g.neutral and not gameday_history.hosted_before(g.home.school):
            s += 6                                     # never hosted (in this world or real life): a new crowd
        hot = max(getattr(g.home.coach, "seat", 0), getattr(g.away.coach, "seat", 0))
        if hot >= 75:
            s += 4                                     # a job on the line is a story
        if s > best_score:
            best, best_score = g, s
    return best


def slate(league, games, featured, n=7):
    others = sorted((g for g in games if g is not featured and _is_fbs_game(g) and not g.played),
                    key=lambda g: -interest(league, g))
    return [featured] + others[:n - 1]


# ═══ Picking games ══════════════════════════════════════════════════════════

def _qb(team):
    import gameday_dossier
    return gameday_dossier._qb(team)


def _features(g):
    """Everything an analyst might weigh, from the home team's point of view."""
    h, a = g.home, g.away
    qh, qa = _qb(h), _qb(a)
    pct = lambda t: t.win_pct if (t.wins + t.losses) else 0.5
    return {"talent": (h.team_ovr - a.team_ovr) / 8,
            "qb": ((qh.overall if qh else 60) - (qa.overall if qa else 60)) / 10,
            "defense": (h.defense_ovr - a.defense_ovr) / 8,
            "coach": (getattr(h.coach, "overall", 70) - getattr(a.coach, "overall", 70)) / 12,
            "home": 0.0 if g.neutral else 0.7,
            "form": (pct(h) - pct(a)) * 2.2}


def pick(league, key, g, weights=None, lean=None):
    """Returns (team picked, confidence 0-1, reason key). The reason is whatever
    actually drove this analyst's number — or his personality, if it flipped."""
    w = weights or gc.CAST[key]["weights"]
    lean = lean if weights else gc.CAST[key]["lean"]
    rng = random.Random(f"{league.seed}:{league.year}:{g.week}:{key}:{g.home.school}")
    f = _features(g)
    parts = {k: w[k] * f[k] for k in w}
    score = sum(parts.values()) + rng.gauss(0, 0.45)
    flipped = None
    if lean == "contrarian" and abs(score) > 1.3 and rng.random() < 0.22:
        score, flipped = -score, "contrarian"
    elif lean == "upset" and abs(score) < 1.6 and rng.random() < 0.32:
        score, flipped = -score, "upset"
    team = g.home if score > 0 else g.away
    sign = 1 if team is g.home else -1
    if flipped == "upset":
        # A flip toward the better-ranked team isn't an upset pick, whatever the model said.
        other = g.away if team is g.home else g.home
        rt, ro = league.rankings.rank_of(team), league.rankings.rank_of(other)
        if rt and (not ro or rt < ro):
            flipped = None
    reason = flipped or max(parts, key=lambda k: parts[k] * sign)
    if reason == "home" and (g.neutral or team is not g.home):
        reason = max((k for k in parts if k != "home"), key=lambda k: parts[k] * sign)
    return team, min(0.95, 0.5 + abs(score) / 5), reason


def guest_pick(league, g, bias, rng):
    f = _features(g)
    edge = sum(f.values())
    if bias == "home":
        return g.home
    if bias == "heart":
        return g.home if edge > -2.2 else g.away
    if bias == "chalk":
        return g.home if edge > 0 else g.away
    if bias == "upset":
        return g.away if edge > 0 else g.home
    return rng.choice((g.home, g.away))


def predict_score(g, winner, rng):
    other = g.away if winner is g.home else g.home
    base = lambda off, dfn, home: 24 + (off.offense_ovr - dfn.defense_ovr) * 0.5 + (2 if home else 0)
    w = base(winner, other, winner is g.home and not g.neutral) + rng.randint(-3, 5)
    l = base(other, winner, other is g.home and not g.neutral) + rng.randint(-5, 3)
    w, l = int(max(10, w)), int(max(3, l))
    if w <= l:
        w = l + rng.choice((3, 4, 7))
    return w, l


# ═══ The show ═══════════════════════════════════════════════════════════════

def first_name(key):
    """First name for the entertainer; 'Coach' for the coach (nobody calls him by his first name on the air)."""
    if key == "coach":
        return "Coach"
    name = settings.cast_name(key).replace('"', "").split()
    return name[0] if name else key


class Show:
    def __init__(self, league, games):
        import gameday_dossier as gd
        _merge_content()
        self.league = league
        self.games = games
        self.rng = random.Random(f"gameday:{league.seed}:{league.year}:{league.week}")
        self.speed = settings.SPEEDS[settings.load()["gameday_speed"]]
        self.g = choose_site(league, games)
        self.h, self.a = self.g.home, self.g.away
        self.H, self.A, self.stories = gd.dossier(league, self.g)
        self.skipping_to_picks = False
        self.table, self.why = {}, {}
        st = _state(league)
        self.used = st.setdefault("used", {}).setdefault(league.year, set())
        self.show_used = set()
        self.told = set()                         # (storyline, team) already discussed this show
        self.F = self._facts()
        # Everybody's pick is settled before the show starts, so nothing they say
        # during the show can contradict it.
        self.slate = slate(league, games, self.g)
        # Fans and guests on the show never share a surname with anybody playing or
        # coaching in the games the show talks about (no Butler in the lot and at QB).
        taken = set()
        follow = getattr(league, "follow_team", None) or getattr(league, "user_team", None)
        if follow is not None:
            taken |= {p.last_name for p in follow.roster}     # nobody on the show shares a name with your team
        for gg in [self.g] + list(self.slate):
            for t in (gg.home, gg.away):
                taken |= {p.last_name for p in t.roster}
                taken |= {c.name.split()[-1] for c in (t.coach, getattr(t, "oc", None), getattr(t, "dc", None))
                          if c is not None}
        self.taken_surnames = taken
        conf = {}
        for gg in self.slate:
            for k in gc.ORDER:
                team, c_, why = pick(league, k, gg)
                self.table[(k, gg)] = team
                self.why[(k, gg)] = why
                conf[(k, gg)] = c_
        # The big one is rarely unanimous: most weeks somebody on the desk takes the other side.
        g0 = self.g
        picks0 = {self.table[(k, g0)] for k in gc.ORDER if (k, g0) in self.table}
        if len(picks0) == 1 and self.rng.random() < 0.75:
            k = min((k for k in gc.ORDER if k != "coach"), key=lambda k: conf.get((k, g0), 1))
            mine = self.table[(k, g0)]
            other = g0.away if mine is g0.home else g0.home
            self.table[(k, g0)] = other
            ro, rm = league.rankings.rank_of(other), league.rankings.rank_of(mine)
            self.why[(k, g0)] = "upset" if (rm and (not ro or ro > rm)) else "talent"
        self.headgear_sign = None                 # a sign the coach's final pick can call back to

    # ── memory: nothing twice in a season ───────────────────────────────
    def fresh(self, pool, tag, reuse=False):
        """Pick something from `pool` that hasn't been used this season. With
        reuse, an exhausted pool starts over from the oldest item."""
        ids = [(f"{tag}:{i}", item) for i, item in enumerate(pool)]
        unused = [x for x in ids if x[0] not in self.used]
        recent = _state(self.league).setdefault("fresh_recent", {})
        now = self.league.year * 20 + self.league.week
        if not unused and reuse and ids:
            for uid, _ in ids:
                if uid not in self.show_used:
                    self.used.discard(uid)
            # Starting over: whatever aired in the last three weeks still rests.
            unused = [x for x in ids if x[0] not in self.used and now - recent.get(x[0], -999) >= 3] or \
                [x for x in ids if x[0] not in self.used]
        if not unused:
            return None
        uid, item = self.rng.choice(unused)
        recent[uid] = now
        self.used.add(uid)
        self.show_used.add(uid)
        return item

    def vary(self, tag, options, cool=4, **kw):
        """One of several ways to say the same thing. Nothing twice in a show, and a
        phrasing rests `cool` weeks before it comes back (across seasons too)."""
        rec = _state(self.league).setdefault("recent", {}).setdefault(tag, {})
        now = self.league.year * 20 + self.league.week
        shown = self.__dict__.setdefault("_vary_show", set())
        ok = [i for i in range(len(options)) if (tag, i) not in shown and now - rec.get(i, -999) >= cool]
        if not ok:
            ok = [min((i for i in range(len(options)) if (tag, i) not in shown),
                      key=lambda i: rec.get(i, -999), default=0)]
        i = self.rng.choice(ok)
        rec[i] = now
        shown.add((tag, i))
        return self.fill(options[i], **kw)

    def bit(self, tag, cool=3):
        """A recurring bit (a story, a sign reply, a tailgate line) rests `cool` weeks
        after it airs. True if it's fresh enough to run today."""
        rec = _state(self.league).setdefault("bits", {})
        now = self.league.year * 20 + self.league.week
        if now - rec.get(tag, -999) < cool:
            return False
        rec[tag] = now
        return True

    # ── the facts every line can use ────────────────────────────────────
    def _facts(self):
        import campus_towns
        from recruiting_data import STATES
        from commentary import rivalry_name
        L, g, h, a, H, A = self.league, self.g, self.h, self.a, self.H, self.A
        rn = lambda X: f"No. {X['rank']} {X['school']}" if X["rank"] else X["school"]
        rival = next((x for x in (getattr(h, "goals", []) or []) if x.kind == "beat_rival"), None)
        from carousel import PRIMARY_RIVAL
        rival_name = PRIMARY_RIVAL.get(h.school) or (rival.param if rival else a.school)
        if g.neutral and g.venue:
            town = g.venue.split(", ")[1] if ", " in g.venue else g.venue
            stadium = g.venue.split(",")[0]
        else:
            town = campus_towns.town(h.school, full=False)
            stadium = h.stadium
        head = _singular(h.nickname if not g.neutral else self.rng.choice((h, a)).nickname)
        F = {"H": rn(H), "A": rn(A), "h": h.school, "a": a.school, "hn": h.nickname, "an": a.nickname,
             "town": town, "state": STATES.get(h.home_state, ("",))[0], "stadium": stadium,
             "hrec": h.record, "arec": a.record, "hc": h.coach.name, "ac": a.coach.name,
             "hqb": H["qb"].name if H["qb"] else h.school, "aqb": A["qb"].name if A["qb"] else a.school,
             "chant": h.chant, "riv": rivalry_name(h, a) or "", "rival": rival_name,
             "round": L.week_name(L.week), "last_year": "",
             "head": head, "HEAD": head.upper(), "RIVAL": rival_name.upper(),
             "TOWN": town.upper(), "HN": h.nickname.upper(), "AN": a.nickname.upper(),
             "QB": (H["qb"].last_name if H["qb"] else h.school).upper()}
        F["A_UP"] = a.school.upper()
        F["coach_cast"] = settings.last_name("coach")
        import broadcast
        F["kick"] = broadcast.time_words(g)
        F["kick_clock"] = broadcast.clock(g.kick).replace("Noon", "noon") if getattr(g, "kick", None) is not None else "prime-time"
        F["film_snaps"] = film_line(L, (h, a), you=settings.last_name("host"))
        self.opening = (H["w"] + H["l"] == 0 and A["w"] + A["l"] == 0)
        for k in gc.ORDER:
            # On the air they call each other by first names ("Pat, what've you got?");
            # the signs in the crowd use last names ("HOWARD STILL OWES ME...").
            F[k] = first_name(k)
            F[f"{k}_first"] = first_name(k)
            F[f"{k}_last"] = settings.last_name(k)
            F[f"{k}_full"] = settings.cast_name(k).replace('"', "")
            F[k.upper()] = settings.last_name(k).upper()
        return F

    def fill(self, text, **extra):
        F = dict(self.F)
        F.update(extra)
        # signs use {A}/{H} in capitals for school names
        return text.format_map(_Fmt(F))

    # ── output ──────────────────────────────────────────────────────────
    def name(self, key):
        if key == "crowd":
            return "THE CROWD"
        if key in gc.CAST:
            return settings.last_name(key)
        return "FAN" if key == "fan" else key

    def say(self, key, text, label=None):
        if self.skipping_to_picks:
            return
        lab = label or self.name(key)
        color = COLORS.get(key, C.BWHITE)
        show = settings.show_name()
        if show != "Campus Countdown":
            text = text.replace("Campus Countdown", show).replace("Campus Countdown", show)
        from commentary import articles
        text = articles(straight_quotes(text))
        body = textwrap.wrap(text, WIDTH - LABEL_W - 6) or [""]
        print(f"  {paint(pad(lab + ':', LABEL_W), color, C.BOLD)}{body[0]}")
        for line in body[1:]:
            print(" " * (LABEL_W + 2) + line)
        import webview
        webview.say(key, lab, text)
        if self.speed:
            time.sleep(self.speed * (0.6 + len(text) / 160))

    def play(self, scene, **extra):
        """Perform a whole scene, top to bottom."""
        for who, line in scene:
            if who == "crowd" and self.g.neutral and "\"" in line:
                line = "(both halves of the stadium answer each other)"
            self.say(who, self.fill(line, **extra))

    def crowd(self, pool):
        self.say("crowd", self.rng.choice(pool))

    def segment(self, title, first=False):
        """Move to the next part of the show — with a spoken hand-off, not a header."""
        if not first and self.speed:
            choice = ask(paint("[Enter] continue   [S] skip to the picks   [X] skip the show", C.GRAY)).lower()
            if choice == "x":
                raise Skip
            if choice == "s":
                self.skipping_to_picks = True
        if self.skipping_to_picks and title not in ("THE PICKS", "THE GUEST PICKER", "THE FINAL PICK"):
            return False
        self.skipping_to_picks = False
        print()
        if not first:
            import gameday_scenes as sc
            pool = sc.TRANSITIONS.get(title)
            if pool:
                self.play(self.fresh(pool, f"trans:{title}", reuse=True))
        return True

    def rn(self, t):
        r = self.league.rankings.rank_of(t)
        return f"No. {r} {t.school}" if r else t.school

    # ── the show ────────────────────────────────────────────────────────
    def run(self):
        L, g, h, a = self.league, self.g, self.h, self.a
        clear()
        print(title_bar(f"{settings.show_name().upper()}  ·  {L.week_name(L.week).upper()}  ·  {self.F['town'].upper()}"))
        print(pad(paint(f"{self.rn(a)} {'vs' if g.neutral else 'at'} {self.rn(h)}  ·  {self.F['stadium']}",
                        C.BWHITE, C.BOLD), WIDTH, "center"))
        print(rule("═", C.BYELLOW))
        print(paint(f"   Show speed: {settings.load()['gameday_speed'].title()}   (change it in Settings)", C.GRAY))
        import webview
        webview.show_open(settings.show_name(), L.week_name(L.week), self.F['town'],
                          f"{self.rn(a)} {'vs' if g.neutral else 'at'} {self.rn(h)}", self.F['stadium'])
        extras = self._pick_extras()
        try:
            self.cold_open()
            self.weather_report()
            self.signs()
            self.storylines()
            if extras:
                extras[0]()
            import gameday_context
            gameday_context.segment(self)           # the stories the whole sport is talking about
            self.around()
            import tailgate
            tailgate.segment(self)                  # Today's Tailgate
            self.interview()
            if len(extras) > 1:
                extras[1]()
            self.around_today()
            self.sideline()
            self.banter()
            self.picks()
            self.guest()
            self.final()
        except Skip:
            self.silent_picks()
            print(paint("\n   Skipped. The crew's picks are in the standings.", C.GRAY))
        st = _state(L)
        st["visits"].setdefault(h.school, []).append((L.year, L.week))
        st["last_featured"] = {"game": g, "year": L.year, "picks": {k: self.table.get((k, g)) for k in gc.ORDER}}
        print()
        print(rule("═", C.BYELLOW))
        ask(paint("Picks locked in. Kickoff is next — [Enter] to go to the games", C.BYELLOW))

    def weather_report(self):
        """What it's like on campus this morning, and the weather games around the country."""
        try:
            import weather
            f = weather.forecast(self.g, self.league, 0)
        except Exception:
            return
        if f["indoor"]:
            if self.rng.random() < 0.4:
                self.say("boom", "We're outside. They're playing tonight under a roof. I'm a little jealous, honestly.")
            return
        t = f["temp"]
        if f["pop"] >= 60 and f["ptype"] == "snow":
            self.say("host", f"It is snowing on {self.F['town']} this morning, and nobody here cares one bit.")
            self.say("coach", "Snow games are won in the trenches. Hang on to the ball, win the line, win the game.")
        elif f["pop"] >= 60:
            self.say("host", f"It's wet out here — {f['headline'].lower()}, {t} degrees. The crowd's in ponchos.")
            self.say("coach", "Rain changes the plan. Fewer shots downfield, more carries, two hands on the football.")
        elif f["wind"][1] >= 22:
            self.say("host", f"The wind is whipping across the set. Gusts up around {f['wind'][1]}.")
            self.say("coach", "Watch the coin toss. Whoever has the wind in the fourth quarter has something.")
        elif t >= 90:
            self.say("host", f"{t} degrees already, and it's not noon. Hydrate, people.")
        elif t <= 35:
            self.say("host", f"{t} degrees at the set this morning. I can't feel my feet.")
        elif self.rng.random() < 0.5:
            self.say("host", f"Couldn't ask for a better day for it — {t} degrees and {f['sky']} at kickoff.")
        others = []
        for g2 in self.league.schedule.get(self.league.week, []):
            if g2 is self.g or g2.played:
                continue
            f2 = weather.forecast(g2, self.league, 0)
            if f2["severity"] >= 3 and not f2["indoor"]:
                others.append((f2["severity"], g2, f2))
        others.sort(key=lambda x: -x[0])
        if others:
            sev, g2, f2 = others[0]
            self.say("film", f"And keep an eye on {g2.away.school} at {g2.home.school} — {f2['headline'].lower()}. "
                             f"That one could turn into a weather game.")

    def _pick_extras(self):
        st = _state(self.league)
        options = [self.film_room, self.defender_watch, self.coach_story, self.crowd_challenge]
        if st.get("last_featured") and st["last_featured"].get("year") == self.league.year and not self.opening:
            options.append(self.recap)
        if any(self._upset_candidates()):
            options.append(self.upset_alert)
        last = st.get("last_extras", [])
        fresh = [f for f in options if f.__name__ not in last] or options
        self.rng.shuffle(fresh)
        chosen = fresh[:2]
        st["last_extras"] = [f.__name__ for f in chosen]
        return chosen

    # ── segments ────────────────────────────────────────────────────────
    def cold_open(self):
        self.segment("COLD OPEN", first=True)
        L, kinds = self.league, [s["kind"] for s in self.stories]
        if L.week == 18:
            key = "title"
        elif L.week > 13:
            key = "postseason"
        elif L.week == 1:
            key = "opener"
        elif "rivalry" in kinds:
            key = "rivalry"
        elif "first_visit" in kinds:
            key = "first_visit"
        elif "return_visit" in kinds:
            key = "return_visit"
            visits = _state(L)["visits"].get(self.h.school, [])
            self.F["last_year"] = str(visits[-1][0]) if visits else ""
        else:
            key = "default"
        import gameday_scenes as sc
        pool = sc.OPENERS[key]
        if not self.F["last_year"]:                   # been here in real life, not in this save: no year to quote
            pool = [x for x in pool if not any("{last_year}" in ln for _, ln in x)] or sc.OPENERS["default"]
        scene = self.fresh(pool, f"open:{key}:{len(pool)}", reuse=key in ("title", "postseason")) or self.fresh(sc.OPENERS["default"], "open:default") \
            or self.rng.choice(sc.OPENERS["default"])
        self.play(scene)
        # Everybody at the desk gets introduced before anybody talks to him.
        F = self.F
        if self.opening or L.week <= 1 or self.rng.random() < 0.5:
            self.say("host", self.vary("roll_call", [
                "I'm {host_full}, alongside {film_full}, {defender_full}, {boom_full} — and Coach {coach_full}.",
                "{host_full} here with {film_full}, {defender_full}, {boom_full}, and Coach {coach_full}.",
                "The whole crew is here: {film_full}, {defender_full}, {boom_full} and Coach {coach_full}. I'm {host_full}.",
            ]))
        else:
            self.say("host", self.vary("roll_call_short", [
                "{film_first}, {defender_first}, {boom_first} and Coach {coach_last} — the whole gang's here.",
                "Everybody's here — {film_first}, {defender_first}, {boom_first}, and Coach {coach_last}.",
            ]))
        try:                                          # the host sets the scene with a local tradition
            import team_lore
            local = [t for m, w, t in team_lore.TEAM_LORE.get(self.h.school, []) if m in ("home", "pregame", "any")]
            if local and self.rng.random() < 0.85:
                line = self.rng.choice(local).replace("{school}", self.h.school).replace("{stadium}", self.h.stadium)
                self.say("host", self.rng.choice(["A little local flavor: ", "If you've never been here: ",
                                                  "What makes this place special — ", ""]) + line)
        except Exception:
            pass
        self.say("host", self.vary("kick_line", [
            "Kickoff here is {kick}.", "We've got a {kick_clock} kickoff here — and they're not going anywhere.",
            "Kickoff is {kick}, and this lawn is already full.", "Kickoff is {kick}. That's a lot of hours to stay this loud.",
            "{A} and {H} kick off {kick}.", "They'll kick it off {kick} — we've got you covered until then.",
            "And the game itself? {kick_cap}. Plenty of time to argue about it."],
            kick_cap=self.F["kick"][:1].upper() + self.F["kick"][1:]))
        self._last_night()

    def _last_night(self):
        """Thursday and Friday games this week have already been played."""
        import broadcast
        done = [g for g in self.games if g.played and _is_fbs_game(g)]
        if not done:
            return
        g = max(done, key=lambda x: interest(self.league, x))
        full = {"Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday", "Thu": "Thursday", "Fri": "Friday"}
        day = full.get(broadcast.DAYS[g.date.weekday()], "Friday")
        window = getattr(g, "window", None) or ""
        if window == "Thanksgiving Night":
            when = "On Thanksgiving night"
        elif window == "Black Friday":
            when = "On Black Friday"
        elif (self.g.date - g.date).days == 1:
            when = "Last night"
        else:
            when = f"{day} night"
        when_l = when[:1].lower() + when[1:] if when.startswith(("Last", "On")) else when
        w, l = g.winner, g.loser
        self.say("host", self.vary("last_night", [
            "{when}, {w} beat {l}, {s}.", "{when}, we got things started: {w} {s} over {l}.",
            "In case you missed it — {when_l}, {w} took care of {l}, {s}."],
            when=when, when_l=when_l, w=w.school, l=l.school, s=f"{g.score_for(w)}-{g.score_for(l)}"))
        margin = g.score_for(w) - g.score_for(l)
        close = (f"{l.school} will want that one back.", f"That one came down to the last few plays.",
                 "Good way to start the weekend.", f"I stayed up for all of it. {w.school} earned it.")
        comfy = (f"{w.school} looked sharp.", "Good way to start the weekend.",
                 f"{w.school} handled its business.", f"Not much drama, but {w.school} did what it had to.")
        rout = (f"{w.school} looked sharp.", f"That was over by halftime. {w.school} rolled.",
                f"{l.school} just didn't have it last night.", f"{w.school} made a statement.")
        self.say(self.rng.choice(("film", "defender", "boom")),
                 self.rng.choice(close if margin <= 8 else comfy if margin <= 17 else rout))

    def home_favored(self):
        import carousel as cz
        R = self.league.rankings
        rh, ra = R.rank_of(self.h), R.rank_of(self.a)
        if rh and (not ra or rh < ra):
            return True
        return cz.win_prob(self.h, self.a, 0 if self.g.neutral else 1) >= 0.5

    def signs(self):
        if not self.segment("THE SIGNS"):
            return
        import gameday_scenes as sc
        kinds = ["jab", "hype", "life", "cast", "rival", "headgear"]
        if self.F["rival"] in (self.a.school, self.h.school):
            kinds.remove("rival")                     # the rival is right here — the jab signs cover it
        if self.g.neutral:
            kinds.remove("headgear")
        self.rng.shuffle(kinds)
        leads = self.rng.sample(sc.SIGN_LEADS, 4)
        shown = 0
        import gameday_context
        topical = [x for x in gameday_context.context_signs(self) if f"csign:{x[0]}" not in self.used]
        if topical and self.rng.random() < 0.7:
            sign, reply = self.rng.choice(topical)
            self.used.add(f"csign:{sign}")
            self.say("host", f"{leads[0]} \"{sign}\"")
            self.play(reply)
            shown = 1
        for kind in kinds:
            if shown == 4:
                break
            if kind == "cast":
                who = self.rng.choice(list(sc.SIGNS["cast"]))
                entry = self.fresh(sc.SIGNS["cast"][who], f"sign:cast:{who}", reuse=True)
                sign, replies = entry if entry else (None, None)
            else:
                pool = sc.SIGNS[kind]
                if self.league.week > 13:
                    pool = [x for x in pool if "PLAYOFF" not in x]
                if self.home_favored():
                    pool = [x for x in pool if "ODDS" not in x and "UNDERDOG" not in x]   # not for the No. 1 team at home
                sign = self.fresh(pool, f"sign:{kind}:{len(pool)}", reuse=True)
                replies = sc.SIGN_REPLIES[kind]
            if sign is None:
                continue
            reader = "host" if kind != "cast" or who != "host" else "film"
            text = self.fill(sign, A=self.a.school.upper(), H=self.h.school.upper())
            if kind == "headgear":
                self.headgear_sign = text
            self.say(reader, f"{leads[shown]} \"{text}\"")
            # A reply that names somebody from a different sign ("Linda deserves better") needs that sign.
            fits = [r_ for r_ in replies if not any(n in " ".join(ln for _, ln in r_) and n.upper() not in text
                                                     for n in ("Linda", "Grandma", "midterm", "dog", "Mom"))]
            reply = self.rng.choice(fits or replies)
            self.play(reply)
            shown += 1

    STANCES = {
        "Every week I pick against {team}": ("boom", "against", "team"),
        "Can't stop it!": ("boom", "for", "team"),
        "YES. I believe in them.": ("boom", "for", "team"),
        "I've picked {dog} in my head all week": ("boom", "for", "dog"),
        "This is the one! This is the one": ("boom", "for", "dog"),
        "You hear that, {fav}?": ("boom", "for", "dog"),
        "I like {dog} a LITTLE more today": ("boom", "for", "dog"),
    }

    def scene_fits(self, scene, extra):
        """False if someone in this scene declares a pick he didn't make."""
        for _, line in scene:
            for marker, (who, side, field) in self.STANCES.items():
                if marker in line and field in extra:
                    school = extra[field]
                    picked = self.table.get((who, self.g))
                    if picked is None:
                        continue
                    if (side == "for") != (picked.school == school):
                        return False
        return True

    def storylines(self):
        if not self.segment("THE MATCHUP"):
            return
        import gameday_scenes as sc
        told = 0
        for story in self.stories:
            if told >= 4:
                break
            kind = story["kind"]
            if kind in ("first_visit", "return_visit") and told == 0 and len(self.stories) > 2:
                continue
            extra = {k: v for k, v in story.items() if k not in ("kind", "weight")}
            missing = [k for k, v in extra.items() if v is None]
            pool = [x for x in sc.STORY.get(kind, []) if self.scene_fits(x, extra)
                    and not any("{" + m + "}" in ln for m in missing for _, ln in x)]
            scene = self.fresh(pool, f"story:{kind}:{len(pool)}") if pool else None
            if scene is None:
                continue
            if told:
                print()
            self.told.add((kind, extra.get("team")))
            fields = sc.KEY_FIELDS.get(kind, ())
            first = scene[1][1] if scene and scene[0][0] == "if" else (scene[0][1] if scene else "")
            # If the scene assumes a fact it doesn't state, the host states it first.
            if fields and not any("{" + f + "}" in first for f in fields) and kind in sc.SETUPS \
                    and not any(extra.get(f) is None for f in fields):
                self.say("host", self.vary(f"setup:{kind}", sc.SETUPS[kind], **extra))
            self.play(scene, **extra)
            if kind == "upset_alert":
                import gameday_dossier as gd
                fav, dog = (self.a, self.h) if extra.get("fav") == self.a.school else (self.h, self.a)
                case = gd.upset_case(self.league, fav, dog, self.rng)
                self.say("film", self.rng.choice(("Here's the hole I found on tape. ", "How does it happen? ",
                                                  "If you want a reason: ")) + case[0][1])
                if len(case) > 1:
                    self.say("defender", case[1][1])
            told += 1
        if told == 0:
            self.say("host", f"{self.F['A']} {'vs' if self.g.neutral else 'at'} {self.F['H']}. {self.F['film']}, what do you see?")
            self.say("film", self.rng.choice(gc.KEYS["film"]).format(**self._edges()))

    def _edges(self):
        f = _features(self.g)
        e = lambda k: (self.h if f[k] > 0 else self.a).school
        return {"edge": e("talent"), "qb_edge": e("qb"), "coach_edge": e("coach"), "form_edge": e("form"),
                "def_edge": e("defense"), "h": self.h.school, "a": self.a.school}

    def film_room(self):
        if not self.segment("THE FILM ROOM"):
            return
        qb, X = (self.H["qb"], self.H) if self.rng.random() < 0.5 else (self.A["qb"], self.A)
        if qb is None:
            return
        s = qb.season_stats
        pct = s["pass_cmp"] / s["pass_att"] if s["pass_att"] else 0
        last = qb.yearly_stats.get(self.league.year - 1)
        if s["pass_att"] < 40 and self.opening:
            if last and last["pass_att"] >= 100:
                lp = last["pass_cmp"] / last["pass_att"]
                self.say("film", f"Let's start with {qb.name}. Last season: {last['pass_yds']:,} yards, {last['pass_td']} "
                                 f"touchdowns, {last['pass_int']} picks, {lp:.0%} completions.")
                self.say("film", self.rng.choice(("The question is whether he takes the next step. Everybody says he looked "
                                                  "sharper in camp.", "He's got a year of experience now. That changes everything "
                                                  "for a quarterback.")))
                self.say("defender", "Year two in a system — that's when quarterbacks get dangerous.")
            else:
                self.say("film", f"{qb.name} is the new starter at {X['school']}, and there isn't much tape on him.")
                self.say("film", self.rng.choice(("What I hear from camp: big arm, still learning when to take the checkdown.",
                                                  "The coaches rave about his command of the huddle. We'll see if it shows up.",
                                                  "He won the job in August. First starts are always nervous ones.")))
                self.say("coach", "First start, first series — you just want him to complete a pass and settle in.")
            return
        if s["pass_att"] >= 40:
            self.say("film", f"Let's talk about {qb.name}. He's completing {pct:.0%} of his passes — "
                             f"{s['pass_td']} touchdowns, {s['pass_int']} interceptions.")
            if s["pass_int"] <= 3:
                self.say("film", "What jumps off the tape is how he protects the football. He'll take a sack before he "
                                 "forces a throw.")
                self.say("defender", "Which drives defensive coordinators crazy. You can't get him to give you anything.")
            elif s["pass_int"] >= 8:
                self.say("film", "The interceptions are the story. He's trying to make the big play every time.")
                self.say("defender", "That's what a defense wants. Stay patient, and he'll give you one.")
            else:
                self.say("film", "He's better than people think on third down. That's where he wins.")
                self.say("coach", "That's the down that gets coaches fired. Good quarterbacks win third down.")
        else:
            self.say("film", f"{X['school']} is going to lean on the run game. {qb.name} is there to manage it.")
            self.say("boom", f"Manage it? Let the man THROW, {self.F['film_first']}!")
            self.say("film", f"I don't call the plays, {self.F['boom_first']}.")

    def defender_watch(self):
        if not self.segment("DEFENDER TO WATCH"):
            return
        X = self.H if self.rng.random() < 0.5 else self.A
        p = X["defender"]
        if p is None:
            return
        s = p.season_stats
        if s["tkl"] == 0 and self.opening:
            last = p.yearly_stats.get(self.league.year - 1)
            if last and last["tkl"]:
                bits = [f"{last['tkl']} tackles"] + ([f"{last['sack']:g} sacks"] if last["sack"] else []) + \
                       ([f"{last['int']} interceptions"] if last["int"] else [])
                self.say("defender", f"{p.name}, {X['school']}. Last year: {', '.join(bits)}.")
            else:
                self.say("defender", f"{p.name}, {X['school']}. He's the best defender on this field, and most people "
                                     f"outside that building don't know his name yet.")
            self.say("defender", self.rng.choice(("Preseason, everybody's healthy and fresh. He's going to be everywhere today.",
                                                  "Watch him in the first quarter. He sets the tone for that whole unit.")))
            return
        line = f"{p.name}, {X['school']}. {s['tkl']} tackles"  # answers the hand-off's question
        if s["sack"]:
            line += f", {s['sack']:g} sacks"
        if s["int"]:
            line += f", {s['int']} interceptions"
        self.say("defender", line + ".")
        self.say("defender", self.rng.choice((
            "He plays like he's mad at the football. I love that.",
            "Every snap, he's the first one to the ball. You can't teach that.",
            "Watch him before the snap. He's calling out the play before it happens.")))
        self.say(self.rng.choice(("film", "coach")), self.rng.choice((
            "Offenses are going to have to account for him on every play.",
            "If he has a big day, {a} is in trouble.".format(a=self.A["school"] if X is self.H else self.H["school"]),
            "That's a pro. You can see it.")))

    def coach_story(self):
        import gameday_scenes as sc
        scene = self.fresh(sc.COACH_STORIES, "coachstory")
        if scene is None or not self.segment("COACH'S CORNER"):
            return
        self.play(scene)

    def crowd_challenge(self):
        import gameday_scenes as sc
        if self.g.neutral:
            return
        scene = self.fresh(sc.CROWD_CHALLENGES, "crowdchallenge")
        if scene is None or not self.segment("BOOM'S CROWD CHALLENGE"):
            return
        self.play(scene)

    def recap(self):
        last = _state(self.league).get("last_featured")
        if last and last.get("year") != self.league.year:
            last = None
        if not last or not last["game"].played or not self.segment("LAST WEEK"):
            return
        g = last["game"]
        right = [k for k, t in last["picks"].items() if t is g.winner]
        wrong = [k for k, t in last["picks"].items() if t is not None and t is not g.winner]
        self.say("host", f"Last week we were in {g.home.school}'s house, and {g.winner.school} won "
                         f"{g.score_for(g.winner)}-{g.score_for(g.loser)}.")
        if right and wrong:
            self.say(right[0], self.rng.choice(("I'd just like to point out that I had that one.",
                                                "Called it. On air. It's on tape.")))
            self.say(wrong[0], self.rng.choice(("We don't need to relive it.", "Moving on.",
                                                "One week. Let it go.")))
        elif right:
            self.say("boom", "We ALL had it! Clean sweep!")
            self.say("film", "Even a broken clock...")
        else:
            self.say("host", "And not one of us had it.")
            self.say("coach", "That's football.")

    def _upset_candidates(self):
        """Ranked teams on the road against unranked ones — where the entertainer's
        own pick really is the upset (so the table can't contradict the segment)."""
        R = self.league.rankings
        return [g for g in self.games if g is not self.g and _is_fbs_game(g) and not g.played
                and R.rank_of(g.away) and not R.rank_of(g.home) and not g.neutral
                and self.table.get(("boom", g), pick(self.league, "boom", g)[0]) is g.home]

    def upset_alert(self):
        cands = self._upset_candidates()
        if not cands or not self.segment("UPSET ALERT"):
            return
        g = min(cands, key=lambda x: self.league.rankings.rank_of(x.away))
        self.__dict__.setdefault("discussed", []).append(g)       # his pick goes on the board
        r = self.league.rankings.rank_of(g.away)
        import broadcast
        self.say("host", f"No. {r} {g.away.school} goes to {g.home.school} — that one's {broadcast.at_time(g)}. "
                         f"{self.F['boom']}?")
        import gameday_dossier as gd
        case = gd.upset_case(self.league, g.away, g.home, self.rng)
        self.say("boom", self.rng.choice((f"{g.home.school.upper()}! I've got a feeling, {self.F['host']}!",
                                          f"I love {g.home.school} in this spot. Nobody's talking about them.")))
        self.say("host", self.rng.choice(("A feeling isn't a reason. Why?", "Give me a reason.", "Based on what?")))
        self.say("boom", case[0][1])
        # The film guy goes looking for the hole too — a different kind of reason than the entertainer's.
        other = next((c for c in case[1:] if c[0] != case[0][0]), None)
        if other:
            self.say("film", self.rng.choice(("I'll give you one more: ", "And here's what I saw on tape: ",
                                              "If it happens, here's how: ")) + other[1])
            self.say("coach", self.rng.choice((f"Still — {g.away.school} is the better team. They have to beat themselves.",
                                               "Those are real. Whether they're enough is a different question.",
                                               f"If {g.home.school} wins the turnover battle, I'll believe it.")))
        else:
            self.say("film", self.rng.choice((f"{g.home.school} does play well at home. I'll give him that.",
                                              f"{self.F['boom_first']}, {g.away.school} is better at almost every position.")))
        self.say("boom", "That's why they call it an UPSET.")

    def around(self):
        if not self.segment("AROUND THE LEAGUE"):
            return
        L = self.league
        if self.opening:
            return self._preseason()
        prev = [g for g in L.schedule.get(L.week - 1, []) if g.played]
        import gameday_league
        if gameday_league.recap_games(L):
            gameday_league.recap_block(self)          # last week's games that mattered, talked through
            prev = []                                 # (the one-line upset below is covered)
        upset = None
        for g in prev:
            rl, rw = getattr(g, "ranks", {}).get(g.loser), getattr(g, "ranks", {}).get(g.winner)
            if rl and (not rw or rw > rl) and (upset is None or rl < upset[0]):
                upset = (rl, g)
        if upset:
            rl, g = upset
            kw = {"l": g.loser.school, "w": g.winner.school, "r": rl,
                  "s": f"{g.score_for(g.winner)}-{g.score_for(g.loser)}"}
            self.say("host", self.vary("al_upset", [
                "Last week, No. {r} {l} went down to {w}, {s}.", "The upset of last week: {w} over No. {r} {l}, {s}.",
                "Remember last Saturday? {w} {s} over No. {r} {l}.", "No. {r} {l} lost last week — to {w}, {s}.",
                "We start with last week's stunner — {w} knocked off No. {r} {l}, {s}.",
                "Nobody saw it coming: {w} beat No. {r} {l} last week, {s}."], **kw))
            self.say("defender", self.vary("al_upset_take", ["{w} was the tougher team that day.",
                "I watched it. {l} never looked comfortable.", "That's why they play the games.",
                "{l} looked like they were thinking about the next game.", "{w} played like they believed it.",
                "Honestly, I saw it coming. {l} had been lucky for weeks.",
                "One of those days. {l} will learn from it.", "That's a loss that'll follow {l} all year."],
                w=g.winner.school, l=g.loser.school))
        unbeaten = sum(1 for t in L.teams if t.losses == 0 and t.wins > 0)
        if 0 < unbeaten <= 15 and L.week >= 4:
            self.say("host", self.vary("al_unbeaten", ["{n} unbeaten teams left.",
                "We're down to {n} unbeatens.", "Only {n} teams in the country without a loss.",
                "{n} undefeated teams remain.", "The unbeaten club is down to {n} members."], n=unbeaten))
            wk = self.league.week
            self.say("coach", self.rng.choice(
                ("That number will be cut in half by November.", "Unbeaten in September means nothing. Ask me in November.",
                 "Some of those are a lot more unbeaten than others.") if wk <= 5 else
                ("Some of those are a lot more unbeaten than others.", "Half of them haven't played anybody yet.",
                 "It gets harder every week from here.") if wk <= 9 else
                ("Getting through November unbeaten is the hardest thing in this sport.",
                 "Every one of those teams is one bad afternoon from joining everybody else.",
                 "That's a real accomplishment this late in the year.")))
        if L.rankings.heisman:
            p = L.rankings.heisman[0][0]
            s = p.season_stats
            if s["pass_yds"]:
                blurb = f"{s['pass_yds']:,} passing yards and {s['pass_td']} touchdowns"
            elif s["rush_yds"]:
                blurb = f"{s['rush_yds']:,} rushing yards and {s['rush_td']} touchdowns"
            else:
                blurb = f"{s['rec_yds']:,} receiving yards and {s['rec_td']} touchdowns"
            self.say("host", self.vary("al_heisman", [
                "The Golden Helmet race — {t}'s {p} is out front with {b}.", "Golden Helmet watch: {p} of {t}, {b}.",
                "Your Golden Helmet leader this week is {t}'s {p} — {b}.", "Nobody's caught {p} yet. {b} for {t}.",
                "{p} leads the Golden Helmet race. {b}.", "At the top of the Golden Helmet board: {p}, {t}. {b}."],
                t=p.team.school, p=p.name, b=blurb))
            self.say("film", self.vary("heis_take", ["It's his to lose right now.", "I'd vote for him today.",
                "The stats are great, but the tape is better.", "Nobody's close. Not yet.",
                "Two more big games and it's over.", "He's the best player in the country, and it isn't close.",
                "Watch the late-season games. That's where it gets decided.", "I'm not convinced it's over.",
                "He has to keep it up in November. Voters remember November."]))

    def around_today(self):
        """The rest of today's board — games the picks won't get to."""
        import gameday_league
        if not gameday_league.preview_games(self.league, self):
            return
        if not self.segment("AROUND THE COUNTRY"):
            return
        gameday_league.preview_block(self)

    def _preseason(self):
        """Week 1: nothing's been played, so it's the preseason poll, last year's
        champion, the coaching carousel and the Golden Helmet favorites."""
        L = self.league
        top = L.rankings.top(3)
        if top:
            self.say("host", self.vary("pre_poll", [
                "{t1} opens the season No. 1 in the country, with {t2} and {t3} right behind.",
                "The preseason poll has {t1} on top, then {t2} and {t3}.",
                "Everybody's chasing {t1} — the preseason No. 1 — with {t2} and {t3} next."],
                t1=top[0].school, t2=top[1].school, t3=top[2].school))
            self.say("film", self.rng.choice(("Preseason polls are guesses. Educated guesses, but guesses.",
                                              f"I'd have {top[1].school} first, but nobody asked me.",
                                              "Ask me again in October.")))
        champ = L.champion_of(L.year - 1) if hasattr(L, "champion_of") else None
        if champ:
            self.say("host", self.vary("pre_champ", [
                "{c} is the defending national champion.", "And don't forget — {c} won it all last season.",
                "The team everybody's trying to dethrone: defending champion {c}."], c=champ.champion))
            self.say("coach", self.rng.choice(("Defending a title is harder than winning one. Every week is somebody's "
                                               "Super Bowl.", "They've got a target on their back now. Everybody's best shot.")))
        news = getattr(L, "carousel", {}).get(L.year - 1, [])
        hires = [t for k, t in news if k in ("hired", "poached")]
        fired = [t for k, t in news if k == "fired"]
        if hires:
            self.say("host", f"It was a busy offseason on the coaching carousel — {len(hires)} new head coaches, "
                             f"{len(fired)} firings.")
            self.say("host", "One that caught everybody's eye: " + self.rng.choice(hires[:6]) + ".")
            self.say("defender", self.rng.choice(("New coaches get about three games of honeymoon. Then it's real.",
                                                  "Year one is about culture. The wins come later — if they come.")))
        cands = []
        for t in L.teams:
            for p in t.roster:
                last = p.yearly_stats.get(L.year - 1)
                if last and p.position in ("QB", "RB", "WR"):
                    v = last["pass_yds"] * 0.02 + last["pass_td"] * 2 + last["rush_yds"] * 0.05 + last["rec_yds"] * 0.05 \
                        + (last["rush_td"] + last["rec_td"]) * 2 + p.overall * 0.5 + (t.prestige - 60) * 0.3
                    cands.append((v, p, t))
        cands.sort(key=lambda x: -x[0])
        if cands:
            favs = ", ".join(f"{p.name} of {t.school}" for _, p, t in cands[:3])
            self.say("host", f"Your preseason Golden Helmet favorites: {favs}.")
            self.say(self.rng.choice(("film", "boom")), self.rng.choice((
                "Somebody not on that list wins it. Happens almost every year.", "I'd bet on the quarterback. I always do.")))

    def interview(self):
        if not self.segment("ONE-ON-ONE"):
            return
        import gameday_more as more
        import gameday_dossier as gd
        from recruiting_data import STATES
        X, Y = (self.H, self.A) if self.rng.random() < 0.6 else (self.A, self.H)
        p = X["star"]
        if p is None:
            return
        pos = {"QB": "quarterback", "RB": "running back", "WR": "receiver", "TE": "tight end", "LB": "linebacker",
               "DL": "defensive lineman", "CB": "cornerback", "S": "safety", "OL": "offensive lineman"}.get(p.position, "player")
        cls = {"FR": "freshman", "SO": "sophomore", "JR": "junior", "SR": "senior"}
        lab = p.class_label.upper()
        year = ("redshirt " if "RS" in lab else "") + cls.get(lab.replace("RS-", ""), "")
        who = self.rng.choice(("defender", "film"))
        team = X["team"]
        mates = [q for q in team.roster if q is not p and q.position == p.position] or \
                [q for q in team.roster if q is not p]
        mate = max(mates, key=lambda q: q.overall) if mates else None
        state = STATES.get(getattr(p, "home_state", None), (None,))[0]
        kw = {"opp": Y["school"], "stadium": self.F["stadium"], "stat": gd._stat_words(p), "home_state": state or "",
              "mate": mate.name if mate else "my center", "hc": team.coach.name, "riv": self.F["riv"],
              "film": self.F["film"], "town": self.F["town"]}
        self.say(who, self.vary("int_open", [
            "I sat down with {t}'s {y} {pos}, {p}.", "I spent some time this week with {p}, {t}'s {y} {pos}.",
            "{t}'s {y} {pos}, {p}, sat down with me earlier this week.",
            "Here's my conversation with {p} — {y} {pos} for {t}."],
            t=X["school"], y=year, pos=pos, p=p.name).replace("  ", " "))
        topics = list(more.INTERVIEW_QA)
        topics.remove("fun")
        if self.opening:
            topics.remove("season")
        if X["team"] is not self.h or self.g.neutral:
            topics.remove("crowd")
        if not state:
            topics.remove("home")
        if not self.F["riv"]:
            topics.remove("rival")
        if not getattr(team, "goals", None):
            topics.remove("goal")
        self.rng.shuffle(topics)
        import gameday_context
        special = gameday_context.interview_topics(self, p, team, Y["team"])
        self.rng.shuffle(special)
        special = special[:2]
        kw["film_prep"] = (f"Film. Hours of it. I've watched every snap {Y['school']} has played this year."
                           if season_snaps(self.league, Y["team"])[0] >= 3 else
                           f"Film, mostly. I watched everything {Y['school']} has put on tape.")
        kw["film_prep_fa"] = ("Every one. The big ones three times." if season_snaps(self.league, Y["team"])[0] >= 3
                              else "Every one. When there isn't much tape yet, you watch what there is until you know it cold.")
        kw["clip"] = signature_clip(self.league, team)
        kw["film_line"] = ("That's more than I watch some weeks." if who == "film"
                           else f"You and {self.F['film']} should talk.")
        played = sum(1 for gg in self.league.team_games(team) if gg.played)
        aware = lambda text: self._season_aware(text, played)
        honest = None                                # a reaction from the desk waits for the tape to end
        for q, answers in special:                   # the questions only this player gets asked this week
            answer, fq, fa = self.rng.choice(answers)
            self.say(who, aware(q))
            self.say("player", answer, label=p.last_name)
            if fq and self.rng.random() < 0.85:
                self.say(who, aware(fq))
                self.say("player", fa, label=p.last_name)
            if honest is None and self.rng.random() < 0.35:
                honest = self.rng.choice(("That's an honest answer.", "You don't always get that from a player.",
                                          "I like that. He didn't dodge it.", "That's a grown-up answer."))
        for t in topics[:4 - len(special)] + ["fun"]:
            if t not in more.INTERVIEW_QA:
                continue
            q, answers = self.fresh(more.INTERVIEW_QA[t], f"iqa:{t}", reuse=True)
            answer, fq, fa = self.fresh(answers, f"iqa:{t}:{q[:20]}", reuse=True)
            self.say(who, aware(q.format(**kw)))
            self.say("player", answer.format(**kw), label=p.last_name)
            if fq and self.rng.random() < 0.8:
                self.say(who, aware(fq.format(**kw)))
                self.say("player", fa.format(**kw), label=p.last_name)
        self.say(who, self.fresh(more.INTERVIEW_CLOSERS, "iclose", reuse=True))
        if honest:                                   # back live at the desk, after the clip
            self.say(self.rng.choice(("coach", "host", "film")), honest)
        self.say(self.rng.choice(("host", "coach")), self.vary("int_close", [
            "Good kid. You can tell he's been coached right.", "That's a leader talking.",
            "He sounds like a guy who's ready for this.", "I like that. No clichés — well, a few clichés.",
            "You can see why his teammates follow him.", "That's the kind of kid you want in your locker room.",
            "Calm. That's what I noticed. Calm.", "He's going to be fun to watch tonight.",
            "Every coach in America wants that answer from a player.", "Great interview. Now go win."]))

    @staticmethod
    def _season_aware(text, played):
        """Before a team has played, 'this season' is a question about his career."""
        if played:
            return text
        for a, b in (("from this season", "from your career"), ("this season", "so far in your career"),
                     ("your worst game this year", "your worst game"), ("this year", "so far"),
                     ("on film this year", "on film")):
            text = text.replace(a, b)
        return text

    def sideline(self):
        if not self.segment("FROM THE SIDELINE"):
            return
        import carousel as cz
        for X in (self.H, self.A):
            if any((k, X["school"]) in self.told for k in ("new_coach", "hot_seat", "coach_return")):
                continue                              # we already talked about this coach
            c = X["team"].coach
            hist = [s for s in getattr(c, "history", []) if s["school"] == X["school"]]
            kw = {"c": c.name, "t": X["school"], "y": c.hired_year, "r": X["record"]}
            if hist:
                w, l = sum(s["w"] for s in hist), sum(s["l"] for s in hist)
                kw["wl"] = f"{w}-{l}"
                line = self.vary("side_hist", ["{c} is {wl} at {t} since taking over in {y}.",
                    "{c}'s record at {t}: {wl} since {y}.", "Since {c} arrived in {y}, {t} is {wl}.",
                    "{c} has gone {wl} at {t}.", "{c}, in charge at {t} since {y}, is {wl} there."], **kw)
            elif self.opening and X["first_year"]:
                line = self.vary("side_open_new", ["{c} coaches his first game at {t} today.",
                    "Today is game one of the {c} era at {t}.", "{c}'s debut at {t} — the whole building wants to see what he's built."], **kw)
            elif self.opening:
                yrs = self.league.year - (c.hired_year or self.league.year) + 1
                kw["n"] = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}.get(yrs, f"{yrs}th")
                line = self.vary("side_open", ["{c} opens his {n} season at {t}.", "It's year {yrs} for {c} at {t}.",
                    "{c} is back for year {yrs} at {t}.", "Year {yrs} of the {c} era at {t} starts today."], yrs=yrs, **kw)
            elif X["first_year"]:
                line = self.vary("side_new", ["This is {c}'s first season at {t}. They're {r}.",
                    "{c} is in year one at {t}, and they're {r}.", "First-year coach {c} has {t} at {r}.",
                    "Year one for {c} at {t}: {r} so far."], **kw)
            else:
                line = self.vary("side_old", ["{c} has been at {t} since {y}. They're {r} this year.",
                    "{c}, at {t} since {y}, has them at {r}.", "{t} is {r} this season under {c}.",
                    "{c}'s team is {r}. He's been in charge since {y}.", "{c} took over at {t} in {y}. This year: {r}."],
                    **kw)
            if X["seat"] is not None and (X["w"] + X["l"] >= 3 or (self.opening and X["seat"] >= 60)) and (X["seat"] >= 50 or X["seat"] < 20 or self.rng.random() < 0.3):
                label = cz.seat_label(X["seat"]).lower()
                line += " " + self.vary("side_seat_" + label.replace(" ", "_"), [
                    "His seat is " + label + ".", "The seat? " + label[:1].upper() + label[1:] + ".",
                    "Around the building, his seat is described as " + label + ".",
                    "If you're wondering about his job security: " + label + "."])
            self.say("reporter", line, label="Reporter")
        goals = getattr(self.h, "goals", [])
        said_coach = not all(any((k, X["school"]) in self.told for k in ("new_coach", "hot_seat", "coach_return"))
                             for X in (self.H, self.A))
        if goals and (self.rng.random() < 0.7 or not said_coach):
            self.say("reporter", f"And {self.h.school}'s athletic director has three goals on the board for this "
                                 f"program: {'; '.join(g.short[:1].lower() + g.short[1:] for g in goals)}.", label="Reporter")

    def banter(self):
        ex = self.fresh(gc.BANTER, "banter")
        if ex is None or not self.segment("THE DESK"):
            return
        for key, line in ex:
            self.say(key, self.fill(line) if key != "crowd" else line)

    def picks(self):
        self.segment("THE PICKS")
        L = self.league
        # Every game the desk talked about gets a row — the slate, plus anything somebody
        # picked out loud earlier in the show — in kickoff order.
        games = [g for g in self.slate if g is not self.g]
        for g in getattr(self, "discussed", []):
            if g not in games and g is not self.g:
                games.append(g)
            for k in gc.ORDER:
                if (k, g) not in self.table:
                    self.table[(k, g)] = pick(L, k, g)[0]
        games.sort(key=lambda g: (getattr(g, "date", None) or 0, getattr(g, "kick", None) or 0))
        prow = []
        print()
        import broadcast
        from ui import short_name
        header = "".join(f"{settings.last_name(k).upper()[:11]:>12}" for k in gc.ORDER)
        print(paint(f"   {'KICKOFF':<13}{'':<35}{header}", C.GRAY, C.BOLD))
        for k in gc.ORDER:                          # the site game's picks are recorded now, revealed at the end
            if (k, self.g) in self.table:
                _state(L)["pending"].append((k, self.g, self.table[(k, self.g)]))

        def tag(t, width):
            r = L.rankings.rank_of(t)
            pre = f"#{r} " if r else ""
            return pre + short_name(t.school, width - len(pre))

        for g in games:
            cells = []
            for k in gc.ORDER:
                team = self.table[(k, g)]
                cells.append(f"{team.abbr:>12}")          # one style in every cell: BGSU, VT, BSU
                _state(L)["pending"].append((k, g, team))
            label = f"{tag(g.away, 16)} {'vs' if g.neutral else 'at'} {tag(g.home, 16)}"
            k = broadcast.clock(g.kick) if getattr(g, "kick", None) is not None else ""
            day = broadcast.DAYS[g.date.weekday()] if getattr(g, "date", None) and g.date != self.g.date else ""
            print(f"   {paint(pad((day + ' ' if day else '') + k, 13), C.GRAY)}{pad(label, 35)}{''.join(cells)}")
            prow.append({"kick": (day + " " if day else "") + k, "game": label, "picks": [c.strip() for c in cells]})
            if self.speed:
                time.sleep(self.speed * 0.6)
        print()
        print(paint(f"   {self.rn(self.g.away)} {'vs' if self.g.neutral else 'at'} {self.rn(self.g.home)}: "
                    f"the picks come at the end of the show.", C.GRAY))
        import webview
        webview.picks([settings.last_name(k) for k in gc.ORDER], prow,
                      f"{self.rn(self.g.away)} {'vs' if self.g.neutral else 'at'} {self.rn(self.g.home)}: "
                      f"the picks come at the end of the show.")
        rec = standings(L)
        if any(w + l for _, w, l in rec):
            line = "   ".join(f"{settings.last_name(k)} {w}-{l}" for k, w, l in rec)
            print(paint(f"\n   PICK STANDINGS   {line}", C.BYELLOW))
            hits = _state(L).get("last_hits", {})
            brag = [(k, s) for k, s in hits.items() if s]
            if brag and self.rng.random() < 0.8:
                k, school = self.rng.choice(brag)
                w_, l_ = next(((w, l) for kk, w, l in rec if kk == k), (0, 0))
                self.say("host", self.vary("brag", [
                    "{who} is {r} after hitting {school} last week.",
                    "Credit where it's due: {who} had {school} last week. {r} on the year.",
                    "{who}, {r}, still talking about that {school} pick."],
                    who=first_name(k), r=f"{w_}-{l_}", school=school))
                self.say(k, self.rng.choice(("I'll be talking about it all season.", "Nobody else had it.",
                                             "Just reading the tape.")))
            lead, last = rec[0], rec[-1]
            if lead[1] - last[1] >= 3 and self.rng.random() < 0.7:
                kw = {"lo": settings.last_name(last[0]), "lr": f"{last[1]}-{last[2]}",
                      "hi": settings.last_name(lead[0]), "hr": f"{lead[1]}-{lead[2]}"}
                speaker = lead[0] if lead[0] != last[0] else "host"
                self.say(speaker if speaker != "host" else "host", self.vary("needle", [
                    "{lo}, you're {lr}. {hi} is {hr}. Just saying.", "Friendly reminder: {hi} {hr}. {lo} {lr}.",
                    "{lo}, how's {lr} feel?", "Somebody on this desk is {lr}, and it isn't {hi}.",
                    "I'm {hr}, {lo}. What are you again?"] if speaker != "host" else [
                    "{lo}, you're {lr}. {hi} is {hr}.", "The standings: {hi} {hr}, and {lo} at {lr}.",
                    "{lo}, you're sitting at {lr}. That's last."], **kw))
                self.say(last[0], self.rng.choice(("It's a long season.", "I'm playing the long game.",
                                                   "Check back in December.")))

    def guest(self):
        if not self.segment("THE GUEST PICKER"):
            return
        from names import FIRST_NAMES, LAST_NAMES
        import gameday_more as more
        from recruiting_data import STATES
        region = STATES.get(self.h.home_state, ("", ""))[1]
        local = more.GUESTS_REGIONAL.get(region, [])
        entry = None
        if local and self.rng.random() < 0.45:
            entry = self.fresh(local, f"guest:{region}")
        entry = entry or self.fresh(gc.GUEST_PICKERS, "guest", reuse=True)
        who, line, bias = entry
        from names import full_name
        name = full_name(self.rng, avoid=self.taken_surnames)
        who = who.format(school=self.h.school, nick=self.h.nickname, state=self.F["state"])
        self.say("host", f"Our guest picker {who}. Say hello to {name}!")
        first = name.split()[0].upper()
        self.say("crowd", f"\"{first}! {first}! {first}!\"")
        team = guest_pick(self.league, self.g, bias, self.rng)
        label = name.split()[-1]
        others = [g for g in self.slate if g is not self.g][:3]
        if others:
            self.say("host", self.rng.choice(("Before the big one — give us a few others.",
                                              "Warm up for us. A few games first.")))
            said = []
            for g in others:
                t = guest_pick(self.league, g, bias, self.rng)
                said.append(t.school)
            self.say("guest", ", ".join(said[:-1]) + (" and " if len(said) > 1 else "") + said[-1] + ".", label=label)
            self.say(self.rng.choice(("boom", "film", "defender")), self.rng.choice((
                "Not bad. Not bad at all.", "That's a sharper card than mine.", "Some chalk, some guts. I like it.")))
        if team is not self.h and not self.g.neutral and ("{nick}" in line or "{school}" in line):
            # His line was about the home team; his pick isn't. Say the pick, not the line.
            line = self.rng.choice(("I know where I'm standing. I'm going the other way anyway.",
                                    "I love this place. I'm still picking with my head.",
                                    "Don't boo me. I've thought about this for a long time."))
        self.say("guest", line.format(nick=self.h.nickname, school=self.h.school), label=label)
        w, l = predict_score(self.g, team, random.Random(f"guest{self.g.home.school}{self.league.year}{self.g.week}"))
        self.say("guest", f"{team.school}! {w}-{l}!", label=label)
        self.crowd(gc.CROWD_ROAR if (team is self.h or self.g.neutral) else gc.CROWD_BOO)

    def reason(self, k, team):
        import gameday_scenes as sc
        why = self.why.get((k, self.g)) or pick(self.league, k, self.g)[2]
        X = self.H if team is self.h else self.A
        if why == "qb" and any(p.position == "QB" for p in X["hurt"]):
            why = "qb_backup"                    # the starter is out; the backup gets different words
        pool = sc.REASONS.get(why, sc.REASONS["talent"])
        if not any(gg.played for gg in self.league.team_games(team)):
            # No games yet: no "all year", no "they've been rolling".
            history = ("all year", "all season", "been rolling", "hotter team", "been the best", "this year")
            pool = [x for x in pool if not any(h in x for h in history)] or sc.REASONS["talent"]
        text = self.fresh(pool, f"reason:{why}:{len(pool)}", reuse=True)
        return text.format(team=team.school, qb=X["qb"].name if X["qb"] else team.school,
                           coach_name=team.coach.name)

    def final(self):
        self.segment("THE FINAL PICK")
        g, h, a = self.g, self.h, self.a
        vs = "vs" if g.neutral else "at"
        self.say("host", self.vary("final_open", [
            "{A} " + vs + " {H}. {film}, you're up.", "{film}, who've you got?",
            "The big one. {A} and {H}. {film}, start us off.", "Final pick time. {film}, go.",
            "Let's settle it. {A} " + vs + " {H}. {film}?", "{film}, you've been quiet all morning. Who wins?",
            "Okay, {film} — you've had all week. Let's hear it.", "The moment everybody came for. {film}?"]))
        for k in ("film", "defender", "boom"):
            team = self.table.get((k, g)) or pick(self.league, k, g)[0]
            w, l = predict_score(g, team, random.Random(f"{k}{g.home.school}{self.league.year}{g.week}"))
            why = self.reason(k, team)
            if why.endswith(f" {team.school}.") or why.endswith(f"{team.school}."):
                why = why[: why.rfind(team.school)].rstrip(" .") + "."
            self.say(k, f"{team.school}. {why} {w}-{l}.")
            if not g.neutral:
                self.crowd(gc.CROWD_ROAR if team is h else gc.CROWD_BOO)
        team = self.table.get(("coach", g)) or pick(self.league, "coach", g)[0]
        other = a if team is h else h
        self.say("host", self.vary("to_coach", ["Coach. It's all yours.", "Coach, bring us home.", "Coach — the moment.",
            "Coach, everybody here has been waiting for you.", "All right, Coach. Make them happy. Or don't.",
            "Coach {coach_last}, the floor is yours.", "Coach? {town} is waiting.", "Take us home, Coach."]))
        self.say("coach", self.vary("reach", [
            "(reaches under the desk, slowly)", "(stands, buttons his jacket, and says nothing for a long moment)",
            "(looks out at the crowd, then down at the desk)", "(pushes his chair back and takes a deep breath)",
            "(picks up a pen, taps it twice, and sets it down)", "(stares straight into the camera)",
            "(reaches for one headgear... then stops)", "(waves the crowd down, very slowly)"]))
        if not g.neutral:
            self.say("crowd", f"(chanting) \"{self.F['HEAD']} HEAD! {self.F['HEAD']} HEAD!\"")
        self.say("coach", self.reason("coach", team))
        if not g.neutral and team is h:
            self.say("coach", self.vary("home_pick", ["And I'm not about to disappoint all these nice people.",
                "So there's really only one thing to do in {town}.", "I've made a lot of decisions in my life. This one's easy.",
                "And these folks have been out here since four in the morning.", "So I'll make it official.",
                "And I'd like to get out of {town} alive.", "Which means there's only one head for me today.",
                "So let's give them what they came for."]))
            self.say("coach", self.vary("head_home", [
                "(pulls on the {head} head)", "(pulls the {head} head on with both hands)",
                "(lifts the {head} head high over his head, then puts it on)", "(the {head} head goes on — slowly)",
                "(puts on the {head} head and pumps a fist)", "(drops the {head} head onto his head in one motion)"],
                head=_singular(h.nickname)))
            self.say("crowd", self.vary("roar_final", ["(deafening)", "(the whole lawn explodes)",
                "(a noise you can feel in your chest)", "(people are hugging strangers)", "(absolute bedlam)",
                "(somebody fires a confetti cannon)"]))
            if self.headgear_sign:                      # the sign from the top of the show got its wish
                peace = "WORLD PEACE" in self.headgear_sign
                self.say("boom", self.rng.choice((
                    "WORLD PEACE, {host}! The sign was right! We did it!" if peace else
                    f"The sign said it this morning, {{host}}! \"{self.headgear_sign}\" He listened!",
                    "Somewhere out there, the sign guy is crying." if not peace else
                    "Somebody go find the WORLD PEACE sign guy. He needs to see this.")).format(host=self.F["host"]))
        elif not g.neutral:
            self.say("coach", self.rng.choice(("I'm sorry, folks. I really am.", "Don't throw anything.",
                                               "You'll forgive me by Tuesday.")))
            self.say("coach", self.vary("head_away", ["(pulls on the {head} head)",
                "(quietly puts on the {head} head)", "(the {head} head goes on, and he immediately ducks)",
                "(holds up the {head} head — and the boos start before it's on)"], head=_singular(team.nickname)))
            self.crowd(gc.CROWD_BOO)
            self.say("boom", self.rng.choice(("COACH! They're going to throw things at us!",
                                              "We have to leave through the back, don't we?")))
        else:
            self.say("coach", f"(pulls on the {_singular(team.nickname)} head)")
            self.say("crowd", "(half the crowd erupts)")
        self.say("host", self.vary("signoff", [
            "Coach {coach_last} takes {t}! That's Campus Countdown!", "{t} it is! We'll see you next week from somewhere new!",
            "The pick is {t}! That's Campus Countdown — enjoy the games!", "Coach says {t}! Thanks for having us, {town}!",
            "{t}! That does it for us. Enjoy the games, everybody!", "There's your pick — {t}! See you next Saturday!",
            "{t}, according to Coach! We're out of here. Have a great Saturday!",
            "And that is Campus Countdown from {town}! Coach has {t}!", "Coach says {t}! Enjoy the games — see you at {kick}!",
            "{t}, says Coach! Kickoff is {kick}. We'll see you next week!"], t=team.school))

    def silent_picks(self):
        L = self.league
        for g in slate(L, self.games, self.g):
            for k in gc.ORDER:
                if (k, g) not in self.table:
                    team, _, why = pick(L, k, g)
                    self.table[(k, g)] = team
                    _state(L)["pending"].append((k, g, team))


class _Fmt(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _singular(nick):
    words = nick.split()
    last = words[-1]
    if last.endswith("ies"):
        last = last[:-1]                     # Mammoths → Mammoth, Rockslides → Rockslide
    elif last.endswith("s") and not last.endswith("ss"):
        last = last[:-1]
    return " ".join(words[:-1] + [last])


def _abbr(team):
    s = team.school
    if len(s) <= 5:
        return s.upper()
    words = s.replace("(", "").replace(")", "").split()
    if len(words) > 1:
        return "".join(w[0] for w in words).upper()[:5]
    return s[:4].upper()


def quiet_show(league, games):
    """Campus Countdown without the broadcast: the crew still picks a campus and makes
    every pick (guest picker aside), so the site history and the season-long
    pick standings keep going when you sim weeks or turn the show off."""
    games = [g for g in games if not g.played]
    if not games:
        return None
    site = choose_site(league, games)
    if site is None:
        return None
    st = _state(league)
    table = {}
    for g in slate(league, games, site):
        for k in gc.ORDER:
            team, _, _why = pick(league, k, g)
            table[(k, g)] = team
            st["pending"].append((k, g, team))
    st["visits"].setdefault(site.home.school, []).append((league.year, league.week))
    st["last_featured"] = {"game": site, "year": league.year, "picks": {k: table.get((k, site)) for k in gc.ORDER}}
    return site


def run_show(league, games):
    if not games:
        return
    if not settings.load()["gameday"]:
        quiet_show(league, games)                  # show's off; the picks and the trip still happen
        return
    show = Show(league, games)
    if show.g is None:
        return
    show.run()
