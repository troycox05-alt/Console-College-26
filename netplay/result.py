"""Portable client game results for Online LAN mode.

A connected coach's Saturday game is authoritative.  The client sends a JSON-safe
box score plus the small amount of roster state changed by the game; the host loads
that result into the matching game instead of replaying/simulating it again.
"""
from collections import Counter


class ImportedBox:
    """The GameSim-shaped part of a submitted result used by box-score/story code."""
    def __init__(self, game, data, players):
        self.game = game
        self.home, self.away = game.home, game.away
        teams = {self.home.school: self.home, self.away.school: self.away}
        self.line = {teams[k]: list(v) for k, v in data.get("line", {}).items() if k in teams}
        self.score = {teams[k]: v for k, v in data.get("score", {}).items() if k in teams}
        self.team_stats = {teams[k]: Counter(v) for k, v in data.get("team_stats", {}).items() if k in teams}
        self.stats = {}
        self._team = {}
        for row in data.get("stats", []):
            p = players.get(row.get("pid"))
            t = teams.get(row.get("team"))
            if p is not None and t is not None:
                self.stats[p] = Counter(row.get("line") or {})
                self._team[p] = t
        self.scoring = []
        for q, clk, school, desc in data.get("scoring", []):
            t = teams.get(school)
            if t is not None:
                self.scoring.append((q, clk, t, desc))
        self.injuries = []
        for row in data.get("injuries", []):
            p = players.get(row.get("pid"))
            t = teams.get(row.get("team"))
            if p is not None and t is not None:
                self.injuries.append((row.get("q"), row.get("clk"), t, p, row.get("desc"),
                                      row.get("sev"), row.get("games")))
        self.ot_round = int(data.get("ot_round") or 0)
        self.timeline = [tuple(x) for x in data.get("timeline", [])]
        self.wx = data.get("wx")
        self.plays_run = int(data.get("plays_run") or 0)

    def other(self, team):
        """Match GameSim.other(): return the opponent for either team."""
        return self.away if team is self.home else self.home

    def team_of(self, player):
        return self._team.get(player)


def _plain(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items() if isinstance(k, (str, int, float, bool))}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return str(value)


def pack(league, game):
    """JSON-safe authoritative result for one finished client game."""
    import records
    b = game.box
    teams = (game.home, game.away)
    stats = []
    if b is not None:
        for p, line in b.stats.items():
            t = b.team_of(p) if hasattr(b, "team_of") else (game.home if p in game.home.roster else game.away)
            stats.append({"pid": records.pid(league, p), "team": t.school, "line": dict(line)})
    injuries = []
    for q, clk, t, p, desc, sev, games in (getattr(b, "injuries", None) or []):
        injuries.append({"q": q, "clk": clk, "team": t.school, "pid": records.pid(league, p),
                         "desc": desc, "sev": sev, "games": games})
    roster = []
    for t in teams:
        for p in t.roster:
            roster.append({"pid": records.pid(league, p), "season_stats": dict(p.season_stats),
                           "games_played": p.games_played, "inj_games": p.inj_games,
                           "inj_desc": p.inj_desc, "inj_week": p.inj_week})
    box = {
        "line": {t.school: list(b.line[t]) for t in teams},
        "score": {t.school: b.score[t] for t in teams},
        "team_stats": {t.school: dict(b.team_stats[t]) for t in teams},
        "stats": stats, "scoring": [[q, clk, t.school, str(desc)] for q, clk, t, desc in b.scoring],
        "injuries": injuries, "ot_round": getattr(b, "ot_round", 0),
        "timeline": list(getattr(b, "timeline", []) or []), "wx": _plain(getattr(b, "wx", None)),
        "plays_run": getattr(b, "plays_run", 0),
    }
    attrs = {}
    for k in ("attendance", "capacity", "fill", "crowd_why", "wx", "kick"):
        if hasattr(game, k):
            attrs[k] = _plain(getattr(game, k))
    return {"home": game.home.school, "away": game.away.school,
            "home_score": game.home_score, "away_score": game.away_score,
            "box": box, "roster": roster, "attrs": attrs}


def apply(league, game, data):
    """Load a submitted client result into the host world and run normal postgame books."""
    import records
    import season
    if not isinstance(data, dict) or data.get("home") != game.home.school or data.get("away") != game.away.school:
        raise ValueError("submitted game does not match the host matchup")
    players = {records.pid(league, p): p for t in (game.home, game.away) for p in t.roster}
    game.home_score = int(data.get("home_score"))
    game.away_score = int(data.get("away_score"))
    for k, v in (data.get("attrs") or {}).items():
        if k in ("attendance", "capacity", "fill", "crowd_why", "wx", "kick"):
            setattr(game, k, v)
    game._kicked = True
    game.box = ImportedBox(game, data.get("box") or {}, players)
    season.record_result(game)
    # Copy the exact postgame player totals/status from the kickoff snapshot's client copy.
    for row in data.get("roster", []):
        p = players.get(row.get("pid"))
        if p is None:
            continue
        p.season_stats = Counter(row.get("season_stats") or {})
        p.games_played = int(row.get("games_played") or 0)
        p.inj_games = int(row.get("inj_games") or 0)
        p.inj_desc = row.get("inj_desc")
        p.inj_week = int(row.get("inj_week") or 0)
    # These normally happen in League.play_game after simulation.  The simulation itself was remote.
    import weather
    import rivalries
    import classics
    weather.record(league, game)
    rivalries.record(league, game)
    classics.consider(league, game)
    records.after_game(league, game)
    return game
