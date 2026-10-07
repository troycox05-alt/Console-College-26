"""
archive.py — Every finished season's games and box scores, kept for good.

When a season ends, each game is copied into a compact record before the new
schedule replaces it: the teams and players are stored as light "stubs"
(names, numbers, positions) rather than live objects, so an old box score
still shows the roster that actually played that day — not who's on the
team now — and the save doesn't carry around every graduated player's whole
career. About 2-3 MB of save file per season.

    league.archive = {2026: [ArchivedGame, ...], 2027: [...], ...}
"""
from collections import Counter


class TeamStub:
    """Just enough of a team to print a scoreboard and a box score."""

    def __init__(self, team):
        self.school = team.school
        self.nickname = team.nickname
        self.abbr = team.abbr
        self.conference = team.conference
        self.fcs = getattr(team, "fcs", False)
        self.stadium = getattr(team, "stadium", "")

    @property
    def full_name(self):
        return f"{self.school} {self.nickname}"


class PlayerStub:
    """A player as he was in that game."""

    def __init__(self, p):
        self.first_name, self.last_name = p.first_name, p.last_name
        self.position, self.number = p.position, p.number
        self.class_label = p.class_label

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def short_name(self):
        return f"{self.first_name[0]}. {self.last_name}"


class ArchivedBox:
    """The parts of a GameSim a box score prints."""

    def __init__(self, sim, teams, players):
        t = teams.get
        self.home, self.away = t(sim.home), t(sim.away)
        self.line = {t(k): list(v) for k, v in sim.line.items()}
        self.score = {t(k): v for k, v in sim.score.items()}
        self.team_stats = {t(k): Counter(v) for k, v in sim.team_stats.items()}
        self.scoring = [(q, clk, t(team, team), desc) for q, clk, team, desc in sim.scoring]
        self.ot_round = sim.ot_round
        self.timeline = list(getattr(sim, "timeline", []) or [])
        self._home = set()
        self.stats = {}
        for p, line in sim.stats.items():
            stub = players.setdefault(id(p), PlayerStub(p))
            self.stats[stub] = Counter(line)
            if sim.team_of(p) is sim.home:
                self._home.add(stub)
        self.injuries = []
        for q, clk, team, p, desc, sev, gms in getattr(sim, "injuries", []):
            stub = players.setdefault(id(p), PlayerStub(p))
            self.injuries.append((q, clk, t(team, team), stub, desc, sev, gms))

    def team_of(self, stub):
        return self.home if stub in self._home else self.away


class ArchivedGame:
    archived = True
    played = True

    def __init__(self, g, year, teams, players):
        import postseason as ps
        self.year, self.week = year, g.week
        self.home, self.away = teams[g.home], teams[g.away]
        self.home_score, self.away_score = g.home_score, g.away_score
        self.game_type = g.game_type
        self.bowl_name = g.bowl_name
        self.display_name = getattr(g, "display_name", None)
        self.neutral = getattr(g, "neutral", False)
        self.conference_game = g.conference_game
        self.ranks = {teams[k]: v for k, v in getattr(g, "ranks", {}).items() if k in teams and v}
        self.seeds = {teams[k]: v for k, v in (getattr(g, "seeds", None) or {}).items() if k in teams}
        self.hc = {teams[k]: v for k, v in (getattr(g, "hc", None) or {}).items() if k in teams and v}
        self.banner = ps.banner(g) if ps.is_postseason(g) else None
        self.site = ps.site_line(g)
        self.box = ArchivedBox(g.box, teams, players) if g.box is not None else None

    @property
    def winner(self):
        return self.home if self.home_score > self.away_score else self.away

    @property
    def loser(self):
        return self.away if self.winner is self.home else self.home

    def opponent_of(self, team):
        return self.away if team is self.home else self.home

    def score_for(self, team):
        return self.home_score if team is self.home else self.away_score


def store_season(league):
    """Copy the finished season into the archive. Called once, at the start of
    the offseason, before the new schedule replaces this one."""
    games = [g for w in sorted(league.schedule) for g in league.schedule[w] if g.played]
    if not games:
        return                                    # burn-in years: nothing was played
    arc = league.__dict__.setdefault("archive", {})
    if league.year in arc:
        return
    teams, players = {}, {}
    for g in games:
        for t in (g.home, g.away):
            if t not in teams:
                teams[t] = TeamStub(t)
    arc[league.year] = [ArchivedGame(g, league.year, teams, players) for g in games]


def seasons(league):
    return sorted(getattr(league, "archive", {}), reverse=True)


def games_for(league, year, school=None, week=None):
    out = getattr(league, "archive", {}).get(year, [])
    if school is not None:
        out = [g for g in out if school in (g.home.school, g.away.school)]
    if week is not None:
        out = [g for g in out if g.week == week]
    return out


def team_stub(league, year, school):
    for g in games_for(league, year, school):
        return g.home if g.home.school == school else g.away
    return None
