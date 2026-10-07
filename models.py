"""
models.py — Core data models for Console College: Player and Team.

PLAYERS
  Six fundamentals (1-100):
    strength, speed, quickness, iq, injury, playmaker
    * "injury" is durability: higher = more resistant to injury. It does not
      feed the overall rating, it will drive injury rolls later.

  Position proficiency (0.1 - 1.2) for EVERY position:
    How well the player turns his fundamentals into production at that spot.
    1.0 = a natural fit, >1.0 = a savant at the position, 0.1 = hopeless.
    A 95-speed player with 0.40 CB proficiency plays CB like a ~38-speed guy.

  Overall at a position = (position-weighted fundamentals) x proficiency.

  Recruiting / development fields:
    hs_stars          star rating coming out of high school (1-5)
    potential         1-100 development speed (shown as a letter grade)
    prof_ceiling      best proficiency he can ever reach at his position
    seasons_developed offseasons of development he's been through

COACHES
  Head coaches carry six ratings: recruiting plus five development ratings
  (passing QB/WR, general offense RB/TE, trench OL/DL, defensive back
  LB/CB/S, special K/P) that drive offseason progression — see development.py.
"""
from __future__ import annotations

from collections import Counter, defaultdict

FUNDAMENTALS = ("strength", "speed", "quickness", "iq", "injury", "playmaker")
FUNDAMENTAL_ABBR = {
    "strength": "STR", "speed": "SPD", "quickness": "QCK",
    "iq": "IQ", "injury": "INJ", "playmaker": "PLY",
}
FUNDAMENTAL_NAMES = {
    "strength": "Strength", "speed": "Speed", "quickness": "Quickness",
    "iq": "Football IQ", "injury": "Durability", "playmaker": "Playmaker",
}

POSITIONS = ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P")
POSITION_NAMES = {
    "QB": "Quarterback", "RB": "Running Back", "WR": "Wide Receiver",
    "TE": "Tight End", "OL": "Offensive Line", "DL": "Defensive Line",
    "LB": "Linebacker", "CB": "Cornerback", "S": "Safety",
    "K": "Kicker", "P": "Punter",
}
OFFENSE = ("QB", "RB", "WR", "TE", "OL")
DEFENSE = ("DL", "LB", "CB", "S")
SPECIAL = ("K", "P")

# How much each fundamental matters at each position (injury excluded).
POSITION_WEIGHTS = {
    "QB": {"strength": .05, "speed": .10, "quickness": .15, "iq": .45, "playmaker": .25},
    "RB": {"strength": .20, "speed": .30, "quickness": .25, "iq": .10, "playmaker": .15},
    "WR": {"strength": .05, "speed": .35, "quickness": .25, "iq": .10, "playmaker": .25},
    "TE": {"strength": .30, "speed": .20, "quickness": .15, "iq": .15, "playmaker": .20},
    "OL": {"strength": .55, "speed": .05, "quickness": .15, "iq": .25, "playmaker": .00},
    "DL": {"strength": .45, "speed": .15, "quickness": .25, "iq": .10, "playmaker": .05},
    "LB": {"strength": .25, "speed": .20, "quickness": .20, "iq": .25, "playmaker": .10},
    "CB": {"strength": .05, "speed": .35, "quickness": .30, "iq": .15, "playmaker": .15},
    "S":  {"strength": .15, "speed": .25, "quickness": .20, "iq": .25, "playmaker": .15},
    "K":  {"strength": .45, "speed": .00, "quickness": .05, "iq": .30, "playmaker": .20},
    "P":  {"strength": .45, "speed": .00, "quickness": .05, "iq": .30, "playmaker": .20},
}

PROFICIENCY_MIN = 0.1
PROFICIENCY_MAX = 1.2

CLASS_YEARS = ("FR", "SO", "JR", "SR")

# Which head-coach development rating drives each position.
DEV_KEY_BY_POSITION = {
    "QB": "passing_dev", "WR": "passing_dev",
    "RB": "offense_dev", "TE": "offense_dev",
    "OL": "trench_dev", "DL": "trench_dev",
    "LB": "db_dev", "CB": "db_dev", "S": "db_dev",
    "K": "special_dev", "P": "special_dev",
}

# Base 4-3 personnel, used for depth charts and unit ratings.
STARTING_LINEUP = {
    "QB": 1, "RB": 1, "WR": 3, "TE": 1, "OL": 5,
    "DL": 4, "LB": 3, "CB": 2, "S": 2,
    "K": 1, "P": 1,
}


class Player:
    def __init__(self, first_name, last_name, position, year, number,
                 height, weight, fundamentals, proficiency, redshirt=False,
                 hs_stars=3, potential=50, prof_ceiling=1.0, seasons_developed=0):
        self.first_name = first_name
        self.last_name = last_name
        self.position = position          # primary position
        self.year = year                  # 0=FR 1=SO 2=JR 3=SR
        self.redshirt = redshirt
        self.hs_stars = hs_stars          # recruiting rating coming out of high school
        self.potential = potential        # 1-100, how fast he develops (hidden-ish)
        self.prof_ceiling = prof_ceiling  # the most efficient he can ever get at his position
        self.seasons_developed = seasons_developed  # offseasons of development completed
        self.history = []                 # [(season_year, overall)] — freshman year, then each offseason
        self.number = number
        self.height = height              # inches
        self.weight = weight              # lbs
        self.fundamentals = dict(fundamentals)
        self.proficiency = {p: _clamp_prof(proficiency.get(p, PROFICIENCY_MIN)) for p in POSITIONS}
        self.team = None
        self.home_state = None            # where he was recruited from
        self.fit_bonus = 1.0              # how well his school matched what he wanted
        self.recruit_rank = None
        self.walk_on = False
        self.transfers = 0                # how many times he's moved
        self.nil = 0                      # NIL deal, dollars per year, paid while he's on this roster
        self.prev_school = None
        self.traits = []
        self.season_stats = Counter()     # this season's box score totals
        self.career_stats = Counter()
        self.yearly_stats = {}            # year -> Counter() of season stats
        self.events = defaultdict(list)   # year -> list of event strings (e.g. "Signed with Alabama", "Redshirted")
        self.games_played = 0
        self.career_games = 0
        # Experience is earned by actually playing, not simply aging. It affects game-to-game
        # steadiness/composure, while talent and fundamentals remain the player's ceiling.
        self.experience = 0
        self.inj_games = 0                # games still to miss (99 = season)
        self.inj_desc = None
        self.inj_week = 0

    # ── Identity ──────────────────────────────────────────────────────────
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def short_name(self):
        return f"{self.first_name[0]}. {self.last_name}"

    @property
    def class_label(self):
        return ("RS-" if self.redshirt else "") + CLASS_YEARS[self.year]

    @property
    def height_str(self):
        return f"{self.height // 12}'{self.height % 12}\""

    # ── Ratings ───────────────────────────────────────────────────────────
    def proficiency_at(self, pos):
        return self.proficiency.get(pos, PROFICIENCY_MIN)

    def applied(self, fundamental, pos=None):
        """A fundamental as it actually shows up on the field at a position."""
        pos = pos or self.position
        if fundamental == "injury":
            return self.fundamentals["injury"]  # durability doesn't depend on position
        return round(self.fundamentals[fundamental] * self.proficiency_at(pos))

    def overall_at(self, pos=None):
        pos = pos or self.position
        raw = sum(self.fundamentals[f] * w for f, w in POSITION_WEIGHTS[pos].items())
        return max(1, min(99, round(raw * self.proficiency_at(pos))))

    @property
    def overall(self):
        return self.overall_at(self.position)

    def best_positions(self, n=3):
        return sorted(POSITIONS, key=self.overall_at, reverse=True)[:n]

    def best_alternate(self):
        """Best position other than the primary one, with overall there."""
        alts = [p for p in POSITIONS if p != self.position]
        pos = max(alts, key=self.overall_at)
        return pos, self.overall_at(pos)

    @property
    def experience_rating(self):
        """1-99 game experience. Old saves derive a conservative baseline from games played."""
        raw = getattr(self, "experience", None)
        if raw is None:
            raw = min(99, round(8 + getattr(self, "career_games", 0) * 4.0 + getattr(self, "games_played", 0) * 3.0))
        return max(1, min(99, int(raw)))

    @property
    def experience_label(self):
        x = self.experience_rating
        if x >= 85: return "Veteran"
        if x >= 68: return "Settled"
        if x >= 48: return "Comfortable"
        if x >= 28: return "Developing"
        return "Raw"

    def add_game_experience(self, amount=1):
        """A dressed/used player gains comfort fastest early in his career, then tapers."""
        x = self.experience_rating
        gain = max(1, round(amount * (1.8 if x < 30 else 1.4 if x < 55 else 1.0 if x < 75 else .6)))
        self.experience = min(99, x + gain)

    @property
    def potential_grade(self):
        p = self.potential
        for cut, grade in ((88, "A+"), (78, "A"), (68, "B+"), (58, "B"), (48, "C+"), (38, "C"), (25, "D")):
            if p >= cut:
                return grade
        return "F"

    @property
    def durability(self):
        inj = self.fundamentals["injury"]
        if inj >= 90:
            return "Iron Man"
        if inj >= 78:
            return "Durable"
        if inj >= 62:
            return "Average"
        if inj >= 48:
            return "Nicked Up Often"
        return "Injury Prone"

    def __repr__(self):
        return f"<Player #{self.number} {self.name} {self.position} OVR {self.overall}>"


class Coach:
    RATING_KEYS = ("recruiting", "passing_dev", "offense_dev", "trench_dev", "db_dev", "special_dev")
    RATING_LABELS = {
        "recruiting": "Recruiting",
        "passing_dev": "Passing Dev (QB/WR)",
        "offense_dev": "Gen. Offense Dev (RB/TE)",
        "trench_dev": "Trench Dev (OL/DL)",
        "db_dev": "Def. Back Dev (LB/CB/S)",
        "special_dev": "Special Dev (K/P)",
    }

    def __init__(self, name, overall, ratings, offense_scheme="Pro Style",
                 defense_scheme="4-3 Zone", aggression=50):
        self.name = name
        self.overall = overall            # general coaching skill (the team's Coach Skill)
        self.ratings = {k: int(ratings[k]) for k in self.RATING_KEYS}
        self.offense_scheme = offense_scheme
        self.defense_scheme = defense_scheme
        self.aggression = aggression      # 1-100: 4th downs, blitz rate
        self.traits = []
        self.team = None

    def dev_rating_for(self, pos):
        return self.ratings[DEV_KEY_BY_POSITION[pos]]

    def __repr__(self):
        return f"<Coach {self.name}>"


class Team:
    RATING_KEYS = ("offense", "defense", "coach", "athletic_director",
                   "facilities", "academics", "tradition", "campus")
    RATING_LABELS = {
        "offense": "Offense Skill",
        "defense": "Defense Skill",
        "coach": "Coach Skill",
        "athletic_director": "Athletic Director",
        "facilities": "Facilities",
        "academics": "Academics",
        "tradition": "Tradition",
        "campus": "Campus",
    }
    PRESTIGE_WEIGHTS = {
        "tradition": .25, "coach": .15, "facilities": .15, "offense": .10,
        "defense": .10, "athletic_director": .10, "academics": .075, "campus": .075,
    }

    def __init__(self, school, nickname, stadium, capacity, conference,
                 division, chant, ratings):
        self.school = school
        self.nickname = nickname
        self.stadium = stadium
        self.capacity = capacity
        self.conference = conference
        self.division = division
        self.chant = chant
        self.ratings = {k: int(ratings[k]) for k in self.RATING_KEYS}
        self.roster: list[Player] = []
        self.coach: Coach | None = None
        self.fcs = False
        self.home_state = None
        self.recruiting_targets = []      # Recruit objects this staff is working
        self.last_win_pct = None          # previous season, feeds recruiting momentum

        self.wins = 0
        self.losses = 0
        self.conf_wins = 0
        self.conf_losses = 0
        self.points_for = 0
        self.points_against = 0

        self.last_season = None           # (wins, losses) from a year ago
        self.historical_records = []      # [(year, wins, losses, conf_wins, conf_losses, [achievements])]
        self.achievements = []            # Milestones won this year (e.g. "SCC Champion", "National Champion")

    # ── Identity ──────────────────────────────────────────────────────────
    @property
    def full_name(self):
        return f"{self.school} {self.nickname}"

    @property
    def abbr(self):
        from teams_data import ABBREVIATIONS
        return ABBREVIATIONS.get(self.school, self.school[:4].upper())

    @property
    def conference_label(self):
        return f"{self.conference} ({self.division})" if self.division else self.conference

    # With a brand (dynasty.py): legacy and the last five seasons both count, and both move.
    PRESTIGE_WEIGHTS_BRAND = {
        "tradition": .18, "coach": .12, "facilities": .12, "athletic_director": .09,
        "academics": .095, "campus": .095,
    }
    BRAND_WEIGHT = .30

    @property
    def prestige(self):
        # Programs that produce Pro League draft picks get a bonus that fades over three drafts.
        brand = self.__dict__.get("brand")
        if brand is None:
            return round(sum(self.ratings[k] * w for k, w in self.PRESTIGE_WEIGHTS.items())
                         + getattr(self, "draft_bonus", 0))
        return round(sum(self.ratings[k] * w for k, w in self.PRESTIGE_WEIGHTS_BRAND.items()) + brand * self.BRAND_WEIGHT
                     + getattr(self, "draft_bonus", 0))

    def set_coach(self, coach):
        coach.team = self
        self.coach = coach

    @property
    def recruiting_score(self):
        """0-100 pull on recruits: coach, program prestige, facilities, momentum."""
        momentum = self.__dict__.get("brand")            # the last five seasons (dynasty.py)
        if momentum is None:
            momentum = self.ratings["tradition"] if self.last_win_pct is None else self.last_win_pct * 100
        import staff
        import compliance
        integrity = compliance.rep_pull(self)             # families notice who runs a clean shop (±2)
        if "brand" in self.__dict__:
            return (staff.recruiting_rating(self) * .36 + self.prestige * .26
                    + self.ratings["facilities"] * .13 + momentum * .25) + integrity
        return (staff.recruiting_rating(self) * .40 + self.prestige * .30
                + self.ratings["facilities"] * .15 + momentum * .15) + integrity

    # ── Roster ────────────────────────────────────────────────────────────
    def add_player(self, player):
        player.team = self
        if any(p.number == player.number for p in self.roster):
            player.number = self.open_number(player.position, player)   # a transfer's old number is taken here
        self.roster.append(player)

    def open_number(self, position, player=None):
        """A jersey number nobody on this roster wears, from the range his position usually wears."""
        import random as _random
        from roster import NUMBERS
        used = {p.number for p in self.roster if p is not player}
        rng = _random.Random(f"jersey:{self.school}:{getattr(player, 'first_name', '')}:{getattr(player, 'last_name', '')}")
        for lo, hi in NUMBERS.get(position, [(0, 99)]):
            free = [n for n in range(lo, hi + 1) if n not in used]
            if free:
                return rng.choice(free)
        free = [n for n in range(0, 100) if n not in used]
        return rng.choice(free) if free else player.number

    def fix_numbers(self):
        """One jersey, one player: whoever arrived later (or is lower on the depth chart) gets a new number."""
        seen = {}
        for p in sorted(self.roster, key=lambda x: (-x.year, -x.overall)):
            if p.number in seen:
                p.number = self.open_number(p.position, p)
            seen[p.number] = p

    def players_at(self, pos):
        """Players whose primary position is pos, best first — unless the head coach
        has set his own depth chart, in which case his order comes first."""
        order = self.__dict__.get("depth_order", {}).get(pos)
        if not order:
            return sorted((p for p in self.roster if p.position == pos), key=lambda p: p.overall, reverse=True)
        room = [p for p in self.roster if p.position == pos]
        ids = {id(p) for p in room}
        mine, seen = [], set()
        for p in order:
            if id(p) in ids and id(p) not in seen:
                mine.append(p)
                seen.add(id(p))
        if len(mine) == len(room):
            return mine                                     # the chart covers the room: no re-rating needed
        rest = sorted((p for p in room if id(p) not in seen), key=lambda p: p.overall, reverse=True)
        return mine + rest

    def available_at(self, pos):
        """Healthy players at a position, best first."""
        return [p for p in self.players_at(pos) if getattr(p, "inj_games", 0) <= 0]

    def injured(self):
        return sorted((p for p in self.roster if getattr(p, "inj_games", 0) > 0), key=lambda p: -p.overall)

    def starters(self):
        """Healthy starters (injuries lower a team's rating until players return)."""
        out = {}
        for pos, n in STARTING_LINEUP.items():
            ranked = self.players_at(pos)                  # one sort per position, not two
            healthy = [p for p in ranked if getattr(p, "inj_games", 0) <= 0 and not p.__dict__.get("redshirt_plan")]
            protected = [p for p in ranked if getattr(p, "inj_games", 0) <= 0 and p.__dict__.get("redshirt_plan")]
            hurt = [p for p in ranked if getattr(p, "inj_games", 0) > 0]
            out[pos] = (healthy + protected + hurt)[:n]
        return out

    def unit_overall(self, positions, starters=None):
        starters = starters if starters is not None else self.starters()
        players = [pl for pos in positions for pl in starters[pos]]
        if not players:
            return 0
        return round(sum(pl.overall for pl in players) / len(players))

    @property
    def offense_ovr(self):
        return self.unit_overall(OFFENSE)

    @property
    def defense_ovr(self):
        return self.unit_overall(DEFENSE)

    @property
    def team_ovr(self):
        s = self.starters()                                # once, shared by all three units
        return round(self.unit_overall(OFFENSE, s) * .46 + self.unit_overall(DEFENSE, s) * .46
                     + self.unit_overall(SPECIAL, s) * .08)

    def reset_record(self):
        self.last_win_pct = self.win_pct if (self.wins + self.losses) else self.last_win_pct
        if self.wins + self.losses:
            self.last_season = (self.wins, self.losses)
        self.wins = self.losses = self.conf_wins = self.conf_losses = 0
        self.points_for = self.points_against = 0
        self.achievements = []

    def find_player(self, number):
        for p in self.roster:
            if p.number == number:
                return p
        return None

    # ── Records ───────────────────────────────────────────────────────────
    @property
    def record(self):
        return f"{self.wins}-{self.losses}"

    @property
    def conf_record(self):
        return f"{self.conf_wins}-{self.conf_losses}"

    @property
    def win_pct(self):
        games = self.wins + self.losses
        return self.wins / games if games else 0.0

    @property
    def conf_win_pct(self):
        games = self.conf_wins + self.conf_losses
        return self.conf_wins / games if games else 0.0

    def __repr__(self):
        return f"<Team {self.full_name} ({self.conference})>"


def _clamp_prof(value):
    return round(max(PROFICIENCY_MIN, min(PROFICIENCY_MAX, value)), 2)
