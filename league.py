import random

from coaches_data import COACH_OVERRIDES, COACH_STYLES, HEAD_COACHES
from models import Coach, Team
from roster import generate_roster
from season import (GAMES_PER_TEAM, REGULAR_SEASON_WEEKS, build_schedule, matchup_order, play_week, run_offseason,
                    simulate_game, generate_postseason_week)
from fcs_data import FCS_STATES, FCS_TEAMS
from names import FIRST_NAMES, LAST_NAMES, full_name
from injuries import weekly_healing
from traits import assign_coach_traits
from rankings import Rankings
from recruiting import RecruitingCycle
from recruiting_data import TEAM_STATES
import season as _season
from teams_data import TEAMS
from ui import C
import postseason as ps
import carousel

# (short name, full name, display color) — also the display order.
CONFERENCES = [
    ("SCC", "Southern Crown Conference", C.BYELLOW),
    ("Continental", "Continental Conference", C.BBLUE),
    ("Seaboard", "Seaboard Conference", C.BCYAN),
    ("Meridian", "Meridian Conference", C.BRED),
    ("Federal", "Federal Conference", C.RED),
    ("Coastal Plains", "Coastal Plains Conference", C.YELLOW),
    ("Lake Country", "Lake Country Conference", C.GREEN),
    ("Crossroads", "Crossroads Conference", C.BLUE),
    ("Golden West", "Golden West Conference", C.BMAGENTA),
    ("High Country", "High Country Conference", C.CYAN),
    ("Independent", "Independents", C.BWHITE),
]
CONF_INFO = {short: (full, color) for short, full, color in CONFERENCES}


FCS_GAP = 5          # rating points off each FCS program's offense, defense and coach (was 2)


class League:
    EXPECTED_TEAMS = 138

    BURN_IN_YEARS = 4                    # 2022-2025 happen before you arrive
    BURN_IN_WEEKS = 6                    # recruiting cycles, run without games

    def __init__(self, seed=None, year=2026, burn_in=True, progress=None, custom=None):
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)
        start = year - (self.BURN_IN_YEARS if burn_in else 0)
        self.year = start
        _season._YEAR[0] = start
        self.week = 0
        self.teams = []
        import custom_teams
        custom_teams.reset_tables()               # nothing left over from another world this session
        custom = list(custom or [])
        rows, renames = custom_teams.world_rows(TEAMS, custom)
        for spec in custom:
            custom_teams.register(spec, renames)   # abbreviations, states, rivals... before anyone looks them up
        self.EXPECTED_TEAMS = len(rows)
        coach_names = {s["school"]: custom_teams.coach_name_for(s) for s in custom}
        for row in rows:
            (school, nickname, stadium, capacity, conf, division, chant, *vals) = row
            ratings = dict(zip(Team.RATING_KEYS, vals))
            team = Team(school, nickname, stadium, capacity, conf, division, chant, ratings)
            team.home_state = TEAM_STATES.get(team.school)
            team.set_coach(make_coach(coach_names.get(school) or HEAD_COACHES.get(school, "TBD"), team))
            assign_coach_traits(team.coach, self.rng)
            generate_roster(team, self.rng, start)
            self.teams.append(team)
        self.fcs_teams = []
        self.build_fcs()
        self.schedule = build_schedule(self, self.rng)
        self.rankings = Rankings(self)
        self.recruiting = RecruitingCycle(self)
        self.user_team = None            # the program you recruit for, if you've picked one
        self.mode = None                 # "career" or "spectator" (chosen at startup)
        self.user_coach = None           # your coach, in career mode
        self.last_portal = None          # most recent transfer window
        self.champions = ps.seed_history()   # national champions, real history first
        self.conf_champs = {}            # conference -> champion, set on Selection Day
        self.playoff_seeds = []
        self.playoff_seed_map = {}
        if burn_in:
            self._burn_in(year, progress)
        carousel.setup(self)             # coaches' careers and every program's AD and goals
        self._fit_rescaled = True        # coach fit already rolled at carousel.FIT_SD (see carousel.migrate)
        import dynasty
        dynasty.ensure_all(self)         # legacy + brand: prestige that moves from here on
        if custom:
            custom_teams.finish_world(self, custom, renames)   # the files' staffs, stadiums, money, rosters
        for t in self.teams:
            t.fix_numbers()              # one jersey, one player
        import depth
        depth.preseason(self)            # every staff sets its depth chart

    def _burn_in(self, target_year, progress=None):
        """Play out the years before the save starts.

        Nobody wants a league where every roster was generated yesterday, so
        the four classes already on campus got there the same way future ones
        will: recruited, developed, and shuffled by the transfer portal. No
        games are played — these are recruiting and roster cycles only, so the
        world you inherit has history in its rosters but no invented results."""
        while self.year < target_year:
            if progress:
                progress(self.year, target_year)
            self.recruiting.compressed = True     # no Saturdays to work around
            for i in range(1, self.BURN_IN_WEEKS + 1):
                # Spread the compressed cycle across a full calendar so late-season
                # urgency — sliding boards, the December commitment rush — still happens.
                week = round(i * REGULAR_SEASON_WEEKS / self.BURN_IN_WEEKS)
                self.week = week
                self.recruiting.weekly_tick(week)
            self.week = 0
            run_offseason(self, self.rng)
            self.rankings = Rankings(self)
            self.recruiting = RecruitingCycle(self)
        from roster import settle_to_ratings
        settle_to_ratings(self.teams)    # the rosters you inherit match the programs' ratings
        for team in self.teams:          # arrive with a clean slate
            team.reset_record()
            team.last_season = None
        self.week = 0
        self.rankings = Rankings(self)

    def build_fcs(self):
        """FCS guarantee-game opponents. Rebuilt fresh each season — they don't
        recruit, develop or appear in any standings."""
        self.fcs_teams = []
        for school, nickname, stadium, capacity, chant, *vals in FCS_TEAMS:
            ratings = dict(zip(Team.RATING_KEYS, vals))
            for k in ("offense", "defense", "coach"):      # FCS talent gap: a guarantee game is a
                ratings[k] = max(1, ratings[k] - FCS_GAP)     # payday for them, a win for you ~93% of the time
            team = Team(school, nickname, stadium, capacity, "FCS", None, chant, ratings)
            team.fcs = True
            team.home_state = FCS_STATES.get(school)
            name = full_name(self.rng)
            team.set_coach(make_coach(name, team))
            generate_roster(team, self.rng, self.year)
            from names import dedupe_roster
            dedupe_roster(team, self.rng, reserved={name.split()[-1]})
            self.fcs_teams.append(team)

    # ── Calendar ──────────────────────────────────────────────────────────
    @property
    def season_complete(self):
        return self.week >= 18  # Extended for postseason (13 Reg + 5 Post)

    @property
    def status(self):
        if self.week == 0:
            return f"{self.year} Season · Preseason"
        if self.season_complete:
            return f"{self.year} Season · Season Complete"
        games = self.schedule.get(self.week, [])
        done = bool(games) and all(g.played for g in games)      # between weeks: this one is in the books
        if self.week <= REGULAR_SEASON_WEEKS:
            if done:
                return f"{self.year} Season · Week {self.week} of {REGULAR_SEASON_WEEKS} complete"
            return f"{self.year} Season · Week {self.week} of {REGULAR_SEASON_WEEKS}"

        return f"{self.year} Season · {ps.week_label(self.week)}" + (" complete" if done else "")

    def week_name(self, week):
        """'Week 7' in the regular season, 'NP Semifinals' after it."""
        return f"Week {week}" if week <= REGULAR_SEASON_WEEKS else ps.week_label(week)

    def advance_week(self):
        games = self.start_week()
        for g in games:
            self.play_game(g)
        self.finish_week(games)
        return games

    def finish_week(self, games):
        """Everything that happens after the last whistle of a week."""
        import gameday_show
        gameday_show.grade(self, games)             # the Campus Countdown crew's picks
        for g in games:
            if g.game_type == "National Championship" and g.played:
                self._crown_champion(g)
        import team_momentum
        team_momentum.after_games(self, games)      # every result moves each team's run of form
        self.rankings.update(self.week, games)
        import committee
        committee.get(self).update(self, self.week)      # the Selection Committee, from week 9 on
        carousel.weekly_seats(self, games)          # every Saturday moves the hot seats
        self.recruiting.weekly_tick(self.week, user_team=None if getattr(self, "autosim", False)
                                    else getattr(self, "user_team", None))   # simming seasons: your staff recruits
        import week
        week.settle(self, games)                    # credit the week's work (sim weeks too)
        week.clear_prep(self)                       # the practice week is spent
        import ad_mode
        ad_mode.after_week(self, games)             # the fans and boosters react (Athletic Director mode)
        import personalities, world_rules
        if world_rules.enabled(self, "personalities"):
            personalities.weekly(self, games)           # the locker room: chemistry and incidents
        import compliance, world_rules
        if world_rules.enabled(self, "violations"):
            compliance.weekly(self, games)              # rule-breaking, investigations, grades, off-field trouble
        try:
            import depth_staff
            depth_staff.record_film(self, games)
        except Exception:
            pass
        import morale, world_rules
        if world_rules.enabled(self, "morale"):
            morale.weekly(self, games)                  # every player's mood: role, results, the room
        import development
        development.develop_in_season(self, games)  # a third of the year's growth happens week by week
        import depth
        depth.weekly(self)                          # staffs re-sort: who's developed, who's passed whom
        if not self.season_complete and self.week + 1 > REGULAR_SEASON_WEEKS:
            # Build next week's postseason games now, so the whole week before a
            # title game, a bowl or a playoff game knows who it's against.
            self._build_postseason(self.week + 1)
            import december
            december.after_week(self)               # bowl opt-outs around the country
        if self.season_complete:
            if world_rules.enabled(self, "personalities") or world_rules.enabled(self, "nil_pressure"):
                personalities.season_end(self)          # NIL raise demands; underclassmen weigh the draft
            import people
            import hotseat
            hotseat.each_seat(self, lambda: people.season_end(self))   # each human gets his own year-end mail
        import sportsbook
        sportsbook.after_week(self, games)          # the window (spectator mode): bets paid, lines move
        import career_plus
        career_plus.weekly(self, games)             # Coach Career: storylines, alerts, achievements

    def _build_postseason(self, week):
        """Each postseason week is built once, as soon as the week before it is final."""
        built = self.__dict__.setdefault("_ps_built", set())
        if (self.year, week) in built:
            return
        built.add((self.year, week))
        generate_postseason_week(self, week)

    def start_week(self):
        """Moves to the next week; returns its games in the order they kick off."""
        for t in self.teams:                        # nobody kicks off without a head coach
            if getattr(t, "coach", None) is None:
                try:
                    import carousel as _cz
                    _cz.name_interim(self, t)
                except Exception:
                    pass
        import sportsbook
        sportsbook.before_week(self)                # the window closes this week's lines
        import world_rules
        if world_rules.enabled(self, "injuries"):
            weekly_healing(self, self.week)
        self.week += 1
        if self.week == 1:
            import halloffame
            halloffame.finalize_pending(self)       # Hall of Fame selections you never made: the committee's go in
            carousel.start_season_seats(self)       # seats start where last winter's verdict left them
            import compliance
            if world_rules.enabled(self, "violations"):
                compliance.start_season(self)           # players held out by the CAB or the registrar
            import personalities
            crng = random.Random(f"captains:{self.seed}:{self.year}")
            for t in self.teams:
                personalities.name_captains(self, t, crng)   # the team votes in August

        if self.week > REGULAR_SEASON_WEEKS:
            self._build_postseason(self.week)       # normally already built the week before (see finish_week)

        import broadcast
        games = matchup_order(self.schedule.get(self.week, []))
        return broadcast.assign(self, self.week, games)        # in kickoff order

    def play_game(self, game, narrator=None):
        game._kicked = True                       # the window closes this game's lines
        for t in (game.home, game.away):          # a job that opened in the offseason and never got filled:
            if getattr(t, "coach", None) is None and t in self.teams:
                try:                              # the coordinator with the better résumé runs it, as an interim
                    import carousel as _cz
                    _cz.name_interim(self, t)
                except Exception:
                    pass
        on = self.__dict__.get("online")
        if on and on.get("started"):              # online: every copy plays this game the same way
            self.rng.seed(f"{self.seed}:{self.year}:{self.week}:{game.home.school}:{game.away.school}")
        carousel.stamp_ranks(self, game)          # poll rank at kickoff, for the AD's "vs Top 25"
        game.hc = {t: getattr(getattr(t, "coach", None), "name", None) for t in (game.home, game.away)}
        import facilities
        import weather, world_rules
        if world_rules.enabled(self, "weather"):
            weather.attach(self, game)                # the weather is what it is: stored on the game
        facilities.set_attendance(self, game)     # who showed up: the crowd is the home-field edge
        game._injuries_enabled = world_rules.enabled(self, "injuries")
        sim = simulate_game(game, self.rng, narrator)
        if world_rules.enabled(self, "weather"):
            weather.record(self, game)                # the weather book: the snow games, the cold ones
        import rivalries
        rivalries.record(self, game)              # every meeting goes in the series book
        import classics
        classics.consider(self, game)             # and the great ones go in the other book
        import records
        records.after_game(self, game)            # and the record book, if anyone broke one
        return sim

    def advance_offseason(self):
        report = run_offseason(self, self.rng)
        return self.after_offseason(report)

    def after_offseason(self, report):
        """The new year's housekeeping, once the offseason has run (all at once, or a stage per cycle)."""
        carousel.rebalance_coaches(self, force=True, weight=0.5, reroll=False)   # the new hires find their level
        import committee
        committee.get(self).new_season(self, self.year)  # terms end; retired coaches take the seats
        self.last_portal = report.portal         # kept so the portal screen has something to show
        import recap
        recap.capture(self, report)              # signing day, kept as text for the story kits
        import skills
        import hotseat
        hotseat.each_seat(self, lambda: skills.after_offseason(self, report))   # each human gets his own skill awards
        self.rankings = Rankings(self)           # fresh preseason poll for the new year
        self.recruiting = RecruitingCycle(self)  # and a brand new recruiting class
        self.conf_champs = {}
        self.playoff_seeds, self.playoff_seed_map = [], {}
        for team in self.teams:
            team.recruiting_targets = []
        import depth
        depth.preseason(self)                    # every staff builds its depth chart for the new season
        return report

    def team_games(self, team):
        return [g for week in sorted(self.schedule) for g in self.schedule[week]
                if team in (g.home, g.away)]

    def _crown_champion(self, g):
        if any(c.season == self.year for c in self.champions):
            return
        win, lose = g.winner, g.loser
        note = "OT" if g.box is not None and getattr(g.box, "ot_round", 0) else ""
        self.champions.append(ps.ChampionRecord(
            self.year, win.school, lose.school, g.score_for(win), g.score_for(lose), win.record,
            win.coach.name, f"{g.venue.split(',')[0]} · {', '.join(g.venue.split(', ')[1:])}", note, real=False))

    def champion_of(self, season):
        return next((c for c in self.champions if c.season == season), None)

    def conference_champions(self):
        """Title-game winners once they're decided; standings leaders before that."""
        champs = []
        for short, _, _ in CONFERENCES:
            if short == "Independent":
                continue
            if short in self.conf_champs:
                champs.append((short, self.conf_champs[short]))
                continue
            ccg = next((g for g in self.schedule.get(14, []) if g.bowl_name == f"{short} Championship"), None)
            if ccg is not None and ccg.played:
                champs.append((short, ccg.winner))
                continue
            standings = self.standings(short)
            if standings:
                champs.append((short, standings[0]))
        return champs

    # ── Conferences ───────────────────────────────────────────────────────
    @staticmethod
    def conference_color(conf):
        return CONF_INFO.get(conf, ("", C.WHITE))[1]

    @staticmethod
    def team_color(team):
        try:
            import theme
            c = theme.accent_for(team)
            if c is not None:
                return c
        except Exception:
            pass
        return CONF_INFO.get(team.conference, ("", C.WHITE))[1]

    @staticmethod
    def conference_full_name(conf):
        return CONF_INFO.get(conf, (conf, None))[0]

    def conference_teams(self, conf):
        return [t for t in self.teams if t.conference == conf]

    def divisions(self, conf):
        """Division names in listed order, or [None] if the league has none."""
        divs = []
        for t in self.conference_teams(conf):
            if t.division not in divs:
                divs.append(t.division)
        return divs

    def standings(self, conf, division=None):
        teams = [t for t in self.conference_teams(conf) if division is None or t.division == division]
        # With no games played yet, prestige breaks the tie (a "preseason" order).
        return sorted(teams, key=lambda t: (-t.conf_win_pct, -t.win_pct, -t.wins, -t.prestige, t.school))

    # ── Lookup ────────────────────────────────────────────────────────────
    def search(self, query):
        q = query.lower().strip()
        if not q:
            return []
        exact = [t for t in self.teams if q in (t.school.lower(), t.full_name.lower(), t.nickname.lower())]
        if exact:
            return exact
        return [t for t in self.teams if q in t.full_name.lower()]

    # ── Sanity check ──────────────────────────────────────────────────────
    def validate(self):
        problems = []
        if len(self.teams) != self.EXPECTED_TEAMS:
            problems.append(f"Expected {self.EXPECTED_TEAMS} teams, found {len(self.teams)}.")
        seen = set()
        for t in self.teams:
            if t.full_name in seen:
                problems.append(f"Duplicate team: {t.full_name}")
            seen.add(t.full_name)
            if t.conference not in CONF_INFO:
                problems.append(f"{t.full_name}: unknown conference '{t.conference}'")
            for k, v in t.ratings.items():
                if not 1 <= v <= 100:
                    problems.append(f"{t.full_name}: {k} rating {v} out of range")
            if t.coach is None or t.coach.name == "TBD":
                problems.append(f"{t.full_name}: no head coach")
        for t in self.teams:                       # every team plays a full slate
            games = len([g for g in self.team_games(t) if g.game_type == "Regular Season"])
            if games != GAMES_PER_TEAM:
                problems.append(f"{t.full_name}: {games} games scheduled, expected {GAMES_PER_TEAM}")
            homes = sum(1 for g in self.team_games(t) if g.game_type == "Regular Season" and g.home is t)
            if not 5 <= homes <= 8:
                problems.append(f"{t.full_name}: {homes} home games scheduled, expected 5-8")
        return problems


def make_coach(name, team):
    """Six ratings generated around Coach Skill, seeded by the coach's name,
    then pinned by COACH_OVERRIDES where he has a reputation."""
    rng = random.Random(f"coach:{name}")
    base = team.ratings["coach"]
    if base > 84:
        base = int(round(84 + (base - 84) * 0.55))       # truly elite coaches are rare
        team.ratings["coach"] = base
    ratings = {}
    for key in Coach.RATING_KEYS:
        spread = 8 if key == "recruiting" else 5
        ratings[key] = int(max(25, min(97, round(rng.gauss(base, spread)))))
    ratings.update(COACH_OVERRIDES.get(name, {}))

    off_s, def_s, aggr = COACH_STYLES.get(name, (None, None, None))
    off_s = off_s or rng.choices(["Spread RPO", "Pro Style", "West Coast", "Air Raid", "Smashmouth"],
                                    weights=[35, 25, 15, 15, 10])[0]
    def_s = def_s or rng.choices(["4-2-5 Quarters", "4-3 Zone", "Pressure 3-4", "Multiple Man", "3-3-5 Stack"],
                                    weights=[30, 25, 20, 15, 10])[0]
    aggr = aggr if aggr is not None else int(max(10, min(95, rng.gauss(55, 14))))
    c = Coach(name, base, ratings, off_s, def_s, aggr)
    import coach_profile
    coach_profile.shape(c, pinned=COACH_OVERRIDES.get(name, {}).keys())
    c.ratings.update(COACH_OVERRIDES.get(name, {}))
    return c
