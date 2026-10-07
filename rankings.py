"""
rankings.py — The Top 25 poll and the Golden Helmet race.

POLL
Modeled on how human voters actually behave, not on a pure power rating:

  * A preseason poll is built from program prestige, returning talent and
    last year's finish, so week one starts with names, not numbers.
  * Sixty-two voters each keep a rating for every team. Every result moves
    it by how surprising it was: a G5 team that beats No. 4 jumps (and gets
    votes); a blue blood that beats an FCS team doesn't move at all.
  * Ballots add a résumé on top: the loss column, ranked wins (which stay on
    the résumé), an unbeaten record, schedule strength, a G5 discount.
  * Voters disagree a little and each has a soft spot, so the points —
    25 for first down to 1 — decide the order, first-place votes are real,
    and teams with points below 25th are "also receiving votes".
  * A team on a bye doesn't move unless the teams around it do.
  * Week to week, voters start from last week's ballot and react to the news
    (Rankings._sticky): who a loss came to and by how much, the second and third
    losses, the ranked scalps, the upset that puts a team on the ballot.
  * No vote during bowl season: the poll after the conference title games stands
    until the final poll, where the champion is No. 1 and the runner-up No. 2.

HEISMAN
A running straw poll of the best individual seasons. Production drives it,
weighted by position the way voters actually weight it (quarterbacks first,
then running backs, then receivers, with defenders needing a huge year).
Team success matters — voters don't crown players on losing teams — and a
big Saturday moves a candidate up the board.
"""
from collections import Counter

TOP_N = 25
HEISMAN_N = 10
STICKINESS = 0.55          # how much of last week's ballot carries over
MAX_RISE = 7               # spots a team can climb in one week
MAX_FALL = 14
FROZEN_FROM = 15           # no AP poll during bowl season...
FINAL_WEEK = 18            # ...until the final one, after the national championship

POS_WEIGHT = {"QB": 0.92, "RB": 1.0, "WR": 0.95, "TE": 0.9}
POWER_LEAGUES = {"SCC", "Continental", "Seaboard", "Meridian", "Independent"}


def _power(team):
    """A quick strength estimate: roster quality plus what they've done."""
    games = team.wins + team.losses
    if not games:
        return team.team_ovr + team.prestige * 0.15
    margin = (team.points_for - team.points_against) / games
    return team.team_ovr + team.prestige * 0.15 + max(-21, min(21, margin)) * 0.55


class Rankings:
    """The Top 25 and the Golden Helmet straw poll, updated week to week."""

    def __init__(self, league):
        self.league = league
        self.scores = {}            # team -> ballot score
        self.order = []             # teams, best first
        self.last_order = []
        self.week = 0
        self.heisman = []           # [(player, score, blurb)]
        self.last_heisman = []
        self.heisman_scores = Counter()
        self.preseason()

    # ── poll ─────────────────────────────────────────────────────────────
    # A voter pool, not a formula. Every voter carries a rating for every team —
    # where they started it in August, moved by every result against what was
    # expected (an upset of a top-5 team is a huge swing; beating an FCS team is
    # nothing) — and fills out a ballot from that rating plus a résumé: losses,
    # quality wins, an unbeaten record, the schedule. Voters disagree a little;
    # the points decide the order, and everybody with points below 25th is
    # "receiving votes".
    VOTERS = 62
    HOME_EDGE = 2.5

    def preseason(self):
        """Built on prestige, roster and last year's finish."""
        for team in self.league.teams:
            hist = getattr(team, "last_season", None)
            finish = 0
            if hist:
                wins, losses = hist
                finish = (wins - losses) * 1.6
            self.scores[team] = (team.team_ovr * 1.6 + team.prestige * 0.9 + finish
                                 + self.league.rng.gauss(0, 2.0))
        # Last January's title game: voters open with the champion near the top and the
        # runner-up not far behind, whatever the roster turnover.
        champs = [c for c in getattr(self.league, "champions", []) if c.season == self.league.year - 1]
        if champs:
            ranked = sorted(self.scores.values(), reverse=True)
            for school, floor, ceiling in ((champs[-1].champion, 4, 1), (champs[-1].runner_up, 9, 4)):
                t = next((x for x in self.league.teams if x.school == school), None)
                if t is not None and len(ranked) > floor and self.scores[t] < ranked[floor - 1]:
                    lo, hi = ranked[floor - 1], ranked[ceiling]          # somewhere in the top few, not a lock for No. 1
                    self.scores[t] = lo + (hi - lo) * self.league.rng.uniform(0.15, 0.95)
        # The voters' rating: the preseason ballot on a points-of-margin scale.
        vals = sorted(self.scores.values())
        lo, hi = vals[0], vals[-1]
        self.rating = {t: 40 + (self.scores[t] - lo) / max(1.0, hi - lo) * 50 for t in self.league.teams}
        self.quality = Counter()          # résumé credit for ranked wins (fades a little each week)
        self.points, self.first_place, self.others = {}, {}, []
        self.order = sorted(self.league.teams, key=lambda t: -self.rating[t])
        self.last_order = list(self.order)
        self.week = 0
        self._vote(0)
        self.preseason_ranks = {t.school: i for i, t in enumerate(self.order[:TOP_N], 1)}   # Campus Countdown remembers August
        self._preseason_watch()

    def _preseason_watch(self):
        """August's Golden Helmet watch list: the best quarterbacks and backs on the best teams.
        Week 1's movement is measured from it, and it carries a fading head start."""
        cands = []
        for t in self.order[:30]:
            r = self.order.index(t) + 1
            for p in t.roster:
                if p.position in ("QB", "RB", "WR"):
                    s = (p.overall - 70) * self.HEISMAN_POS.get(p.position, 0.5) + max(0, 26 - r) * 0.25
                    cands.append((s, p))
        cands.sort(key=lambda x: -x[0])
        top = [p for s, p in cands[:HEISMAN_N] if s > 0]
        self.watch = {p: 6.0 - i * 0.4 for i, p in enumerate(top)}
        self.heisman = [(p, 0.0, "preseason watch list") for p in top]
        self.last_heisman = list(top)

    def _rating_of(self, team):
        r = self.__dict__.setdefault("rating", {})
        if team not in r:
            r[team] = 30.0 if getattr(team, "fcs", False) else 45.0
        return r[team]

    def update(self, week, games):
        """Re-vote after a week of games."""
        if "rating" not in self.__dict__:                     # a save from before the voter pool
            vals = sorted(self.scores.values()) or [0, 1]
            lo, hi = vals[0], vals[-1]
            self.rating = {t: 40 + (self.scores.get(t, lo) - lo) / max(1.0, hi - lo) * 50 for t in self.league.teams}
            self.quality, self.points, self.first_place, self.others = Counter(), {}, {}, []
        if not FROZEN_FROM <= week < FINAL_WEEK:
            self.last_order = list(self.order)          # (during the bowls, last week stays the title-game week)
        previous = {t: self.rank_of(t) for t in self.league.teams}
        k = 3.2                                                # voters move a step at a time
        for t in list(self.quality):
            self.quality[t] *= 0.96
        for g in games:
            if not g.played or g.winner is None:
                continue
            a, b = g.home, g.away
            ra, rb = self._rating_of(a), self._rating_of(b)
            edge = 0 if g.neutral else self.HOME_EDGE
            p_home = 1 / (1 + 10 ** (-(ra + edge - rb) / 12))
            margin = g.score_for(a) - g.score_for(b)
            home_won = margin > 0
            mov = min(1.6, 0.7 + abs(margin) / 25)             # a blowout says more, up to a point
            delta = k * mov * ((1 if home_won else 0) - p_home)
            self.rating[a] = ra + delta
            self.rating[b] = rb - delta
            winner, loser = g.winner, g.loser
            lr = previous.get(loser)
            if lr and not getattr(winner, "fcs", False):
                self.quality[winner] += (26 - lr) * 0.16       # a ranked scalp stays on the résumé
                if previous.get(winner) is None and lr <= 12:
                    self.quality[winner] += (13 - lr) * 0.45   # the upset of the week: everybody saw it
            if lr is None and previous.get(winner) and getattr(loser, "fcs", False):
                self.rating[winner] -= 0.5                     # nobody's impressed by an FCS win
        if FROZEN_FROM <= week < FINAL_WEEK:
            # The AP doesn't vote during bowl season: the poll after the conference title
            # games stands until the final poll, after the national championship.
            self.__dict__.setdefault("held", []).extend(g for g in games if g.played)
        elif week >= FINAL_WEEK:
            self._vote(week)
            post = list(self.__dict__.pop("held", [])) + [g for g in games if g.played]
            self._sticky(previous, [g for g in post if g.game_type in ("Bowl", "NP First Round")], final=True)
            self._final(post)
        else:
            self._vote(week)
            self._sticky(previous, games)
        self.week = week
        self._log_heisman_games(week, games)
        self._update_heisman(week)

    def _sticky(self, previous, games, final=False):
        """How AP voters actually move teams. Every voter starts from last week's ballot
        and reacts to what happened, so the order is last week's plus the week's news:

          a ranked team that wins holds its spot (and climbs as teams above it lose);
          a win over a ranked team buys a few spots, a top-5 scalp a few more;
          a loss costs spots by who it was to: a close loss to a better team, two or three;
            a loss to a lower-ranked team, five to eight; a loss to an unranked team,
            seven or more (most teams below No. 15 fall out); to an FCS team, the poll;
          the second loss costs more than the first, the third more again;
          an unranked team that beats a top-12 team usually enters, in the teens or low 20s;
          other newcomers enter toward the bottom, and nobody climbs ten spots for a routine win.

        The voters' own ratings (the raw vote) pull a little each week — more in September,
        when they're still fixing their preseason ballots."""
        import random
        rng = random.Random(f"sticky:{self.league.seed}:{self.league.year}:{self.week}:{len(games)}")
        info = {}
        for g in games:
            if not g.played or g.winner is None:
                continue
            for t in (g.home, g.away):
                o = g.opponent_of(t)
                home = g.home is t and not g.neutral
                info[t] = (g.winner is t, o, abs(g.score_for(g.home) - g.score_for(g.away)), home,
                           g.game_type)
        new = {t: i + 1 for i, t in enumerate(self.order)}
        wk = self.week + 1 if not final else FINAL_WEEK
        pull = (-4.0, 2.0) if wk <= 4 else (-2.5, 1.2)
        key = {}
        for t in self.league.teams:
            n, p = new[t], previous.get(t)
            res = info.get(t)
            if p is None:
                k = n
                if res and res[0]:
                    won, o, margin, home, gt = res
                    orank = previous.get(o)
                    if orank and orank <= 12 and t.losses <= 2:
                        floor = 9 + orank * 0.4 + 1.5 * t.losses + (1.5 if t.conference not in POWER_LEAGUES else 0)
                        k = min(max(n, floor), 21.5)        # the upset everybody saw: onto most ballots
                    elif n <= TOP_N:
                        k = max(n, 18 if self.quality[t] < 3 else 20 - min(5.0, self.quality[t] * 0.6))
                elif res:                                     # lost: nobody enters the poll on a loss
                    k = max(n, TOP_N + 1.5)
                else:
                    k = max(n, 21)
                key[t] = k
                continue
            drift = max(pull[0], min(pull[1], 0.2 * (n - p)))
            if res is None:                                   # a bye: hold, give or take
                key[t] = p + 0.3 + max(-1.0, min(0.6 if p <= 4 else 1.0, 0.1 * (n - p)))
                continue
            won, o, margin, home, gt = res
            orank = previous.get(o)
            fcs = getattr(o, "fcs", False)
            if won:
                bonus = 0.6
                if orank:
                    bonus += 1.2 + (26 - orank) * 0.12 + max(0, 6 - orank) * 0.8 + (0.5 if not home else 0)
                if gt == "Conference Championship":
                    bonus += 1.5
                if margin >= 21 and not fcs and (orank or o.win_pct >= 0.5):
                    bonus += 0.4
                if margin <= 3 and not orank:
                    bonus -= 0.8 if o.win_pct < 0.5 or fcs else 0.4   # sweating out a bad team
                if fcs:
                    bonus -= 0.4
                # however big the win, a team climbs past at most four or five teams that
                # didn't lose (the rest of a climb comes from the teams above it losing)
                key[t] = max(p - bonus + drift, p - min(4.5, 1.0 + bonus * 0.6))
            else:
                m = min(35, margin)
                if fcs:
                    drop = 16
                elif orank and orank < p:                     # lost to a better team
                    drop = 1.5 + 0.1 * m + (0.8 if home else 0)
                elif orank:                                   # lost to a lower-ranked team
                    drop = 3 + min(6.0, 0.25 * (orank - p)) + 0.12 * m
                else:                                         # lost to an unranked team
                    drop = 7 + 0.12 * m + (2.0 if o.win_pct < 0.5 else 0)
                drop += {0: 0, 1: 0, 2: 2.5, 3: 4.5}.get(t.losses, 7.0)
                if gt == "Conference Championship" and orank and orank < p + 8:
                    drop *= 0.6                               # a title-game loss to a good team is forgiven a little
                drop *= rng.uniform(0.85, 1.15)
                key[t] = p + drop + max(-2.0, min(2.0, 0.15 * (n - p - drop)))
        order = sorted(self.league.teams, key=lambda t: (key[t], new[t]))
        pts = sorted((self.points.get(t, 0) for t in self.league.teams), reverse=True)
        self.points = {t: pts[i] for i, t in enumerate(order) if pts[i] > 0}
        self.order = order
        self.others = [(t, self.points[t]) for t in order[TOP_N:] if self.points.get(t, 0) > 0]

    def _final(self, post):
        """The final poll: the champion is No. 1 and the runner-up No. 2, then the playoff
        teams by how far they went (semifinal losers, then quarterfinal losers), then
        everybody else as the voters have them."""
        lost_in = {}
        champ = runner = None
        for g in post:
            if g.game_type == "National Championship":
                champ, runner = g.winner, g.loser
            elif g.game_type in ("NP Semifinal", "NP Quarterfinal"):
                lost_in[g.loser] = g.game_type
        if champ is None:
            return
        pos = {t: i for i, t in enumerate(self.order)}
        sf = sorted((t for t, r in lost_in.items() if r == "NP Semifinal"), key=lambda t: pos.get(t, 999))
        qf = sorted((t for t, r in lost_in.items() if r == "NP Quarterfinal"), key=lambda t: pos.get(t, 999))
        head = [champ, runner] + sf + qf
        self.order = head + [t for t in self.order if t not in head]
        pts = sorted(self.points.values(), reverse=True)
        self.points = {t: pts[i] for i, t in enumerate(self.order) if i < len(pts) and pts[i] > 0}
        self.first_place = {champ: self.VOTERS}
        self.others = [(t, self.points[t]) for t in self.order[TOP_N:] if self.points.get(t, 0) > 0]

    def _resume(self, team):
        """What a voter adds to (or takes off) his rating when he writes the ballot."""
        games = team.wins + team.losses
        s = self._rating_of(team) + self.quality[team]
        prev = self.rank_of(team) if getattr(self, "week", 0) else None
        if prev:
            s += (26 - prev) * 0.55                           # last week's ballot is where every voter starts
        if games:
            s -= team.losses * 6.0                              # the loss column is what voters read first
            if team.losses >= 3:
                s -= (team.losses - 2) * 4.0                    # three losses and you're out of the conversation
            if team.losses >= 4:
                s -= 5.0                                        # four, and you're off nearly every ballot
            if team.losses == 0 and games >= 3:
                s += 2.5 + games * 0.25                        # and they protect the unbeaten
            played = [g.opponent_of(team) for g in self.league.team_games(team) if g.played]
            if played:
                sos = sum(self._rating_of(o) for o in played) / len(played)
                s += (sos - 60) * 0.12
        if team.conference not in POWER_LEAGUES:
            s -= 3.0 if team.losses else 1.5                   # an unbeaten G5 team still gets looked at
        return s

    def _vote(self, week):
        import random
        rng = random.Random(f"poll:{self.league.seed}:{self.league.year}:{week}")
        base = {t: self._resume(t) for t in self.league.teams}
        contenders = sorted(self.league.teams, key=lambda t: -base[t])[:45]
        buzz = [t for t in self.league.teams if self.quality[t] >= 3 and t not in contenders]
        contenders += buzz                                     # a big upset gets a team onto some ballots
        pts, firsts = Counter(), Counter()
        for v in range(self.VOTERS):
            homer = rng.choice(contenders)                     # every voter has a soft spot somewhere
            line = base[contenders[min(len(contenders) - 1, 22)]]
            def ballot_score(t):
                v = base[t] + rng.gauss(0, 1.6 + 0.04 * (base[contenders[0]] - base[t])) + (1.5 if t is homer else 0)
                if t in buzz and rng.random() < 0.3:
                    v = max(v, line + rng.uniform(-1.5, 1.0))   # some voters reward the upset with a spot
                return v
            ballot = sorted(contenders, key=lambda t: -ballot_score(t))[:TOP_N]
            for i, t in enumerate(ballot):
                pts[t] += TOP_N - i
            firsts[ballot[0]] += 1
        self.points, self.first_place = dict(pts), dict(firsts)
        ranked = sorted(self.league.teams, key=lambda t: (-pts.get(t, 0), -base[t]))
        self.order = ranked
        self.others = [(t, pts[t]) for t in ranked[TOP_N:] if pts.get(t, 0) > 0]
        self.scores = {t: base[t] for t in self.league.teams}

    def rank_of(self, team):
        try:
            i = self.order.index(team)
        except ValueError:
            return None
        return i + 1 if i < TOP_N else None

    def previous_rank(self, team):
        try:
            i = self.last_order.index(team)
        except ValueError:
            return None
        return i + 1 if i < TOP_N else None

    def top(self, n=TOP_N):
        return self.order[:n]

    # ── heisman ──────────────────────────────────────────────────────────
    # How the real vote works, roughly: it's a quarterback's award unless someone
    # else has a historic year; voters want efficiency and volume, on a team that
    # wins; they remember the big Saturdays against ranked teams and on TV; the
    # late season counts more than September; and the preseason favorite gets a
    # head start that disappears if he doesn't produce.
    HEISMAN_POS = {"QB": 1.0, "RB": 0.86, "WR": 0.80, "TE": 0.62}
    HEISMAN_DEF = 0.5

    def _log_heisman_games(self, week, games):
        """Every candidate's game, judged on impact and remembered with its stakes."""
        from impact import game_impact
        log = self.__dict__.setdefault("heisman_log", {})
        for g in games:
            box = getattr(g, "box", None)
            if box is None or not g.played:
                continue
            ranks = getattr(g, "ranks", {}) or {}
            for p, c in box.stats.items():
                if p.position in ("OL", "K", "P"):
                    continue
                team = box.team_of(p)
                opp = g.opponent_of(team)
                v = game_impact(c)
                if v <= 0 and not log.get(p):
                    continue
                big = bool(ranks.get(opp)) or g.game_type != "Regular Season"
                won = g.winner is team
                # Strength of schedule: FCS stats barely count; a weak FBS opponent counts less.
                if getattr(opp, "fcs", False):
                    v *= 0.3
                else:
                    v *= max(0.55, min(1.15, 0.55 + (opp.team_ovr - 55) / 45))
                log.setdefault(p, []).append((week, v, big, won))

    def _candidate_score(self, player, team):
        s = player.season_stats
        pos = player.position
        games = self.__dict__.get("heisman_log", {}).get(player, [])
        if not games:
            if not player.games_played:
                return 0.0
            from impact import game_impact                 # a save from before the game log: use the season line
            games = [(max(1, self.week // 2), game_impact(s), False, True)]
        # Late-season games count more; a big win against a ranked team is a "Golden Helmet moment".
        resume = 0.0
        for wk, v, big, won in games:
            w = 1 + 0.035 * max(0, wk - 1)
            if big:
                w *= 1.35 if won else 1.1
            resume += v * w
        # Efficiency on top of the game-by-game resume, the way voters read a stat line.
        if pos == "QB" and s["pass_att"] >= 60:
            ypa = s["pass_yds"] / s["pass_att"]
            rating = ((8.4 * s["pass_yds"] + 330 * s["pass_td"] + 100 * s["pass_cmp"] - 200 * s["pass_int"])
                      / s["pass_att"])                     # CAB passer rating
            resume *= max(0.75, min(1.25, 1 + (rating - 150) / 250))
            resume += (ypa - 7.5) * 4
        elif pos == "RB" and s["rush_att"] >= 40:
            resume *= max(0.85, min(1.15, 1 + (s["rush_yds"] / s["rush_att"] - 5.2) / 12))
        prod = resume * (self.HEISMAN_POS.get(pos, self.HEISMAN_DEF))
        # Two-way or return-game juice gets noticed.
        if pos in ("WR", "CB", "S") and (s["kr_td"] + s["pr_td"]):
            prod *= 1.06
        if team.conference not in POWER_LEAGUES:
            prod *= 0.8                                   # tougher road to New York from the G5
        # Team success is a multiplier, not a bonus: nobody wins it on a .500 team.
        n = max(1, team.wins + team.losses)
        pct = team.wins / n
        factor = 0.55 + 0.45 * pct
        if team.losses >= 3:
            factor *= 0.9 ** (team.losses - 2)
        rank = self.rank_of(team)
        if rank:
            factor *= 1 + (26 - rank) * 0.008              # up to +20% for No. 1: voters watch the top teams
        else:
            factor *= 0.85
        # Preseason hype, fading by midseason: last year's production and profile.
        hype = 0.0
        last = player.yearly_stats.get(self.league.year - 1) if hasattr(player, "yearly_stats") else None
        if last and self.week <= 7:
            from impact import offense_impact, defense_impact
            base = offense_impact(last) + defense_impact(last) * 0.6
            hype = base * 0.04 * (7 - self.week) / 7
        watch = getattr(self, "watch", {}).get(player)
        if watch and self.week <= 6:
            hype += watch * (7 - self.week) / 7              # the August favorite doesn't vanish after one game
        return prod * factor + hype

    def _update_heisman(self, week):
        self.last_heisman = [p for p, _, _ in self.heisman]      # week 1 moves from the preseason list
        board = []
        for team in self.league.teams:
            for p in team.roster:
                if not p.games_played or p.position in ("OL", "K", "P"):
                    continue
                score = self._candidate_score(p, team)
                if score > 0:
                    board.append((score, p, team))
        board.sort(key=lambda x: -x[0])
        # Voters split a team's vote: the second man from one roster is discounted, the third more.
        seen = Counter()
        adj = []
        for score, p, team in board[:60]:
            adj.append((score * (1.0, 0.8, 0.6, 0.45)[min(3, seen[team])], p, team))
            seen[team] += 1
        adj.sort(key=lambda x: -x[0])
        self.heisman = [(p, round(score, 1), self.blurb(p)) for score, p, team in adj[:HEISMAN_N]]

    def heisman_movement(self, player):
        if player not in self.last_heisman:
            return None
        return self.last_heisman.index(player) + 1

    @staticmethod
    def blurb(p):
        s = p.season_stats
        if p.position == "QB":
            return (f"{s['pass_cmp']}/{s['pass_att']}, {s['pass_yds']:,} yds, {s['pass_td']} TD, "
                    f"{s['pass_int']} INT" + (f", {s['rush_yds']} rush yds" if s["rush_yds"] >= 100 else ""))
        if p.position == "RB":
            return (f"{s['rush_att']} car, {s['rush_yds']:,} yds, {s['rush_td']} TD"
                    + (f", {s['rec']} rec" if s["rec"] >= 10 else ""))
        if p.position in ("WR", "TE"):
            return f"{s['rec']} rec, {s['rec_yds']:,} yds, {s['rec_td']} TD"
        return f"{s['tkl']} tkl, {s['tfl']} TFL, {s['sack']} sacks, {s['int']} INT"


def rank_prefix(rankings, team, width=False):
    """'#7 ' for ranked teams, blank otherwise — for use in listings."""
    if rankings is None:
        return "    " if width else ""
    r = rankings.rank_of(team)
    if r is None:
        return "    " if width else ""
    return f"#{r:<2} " if width else f"#{r} "
