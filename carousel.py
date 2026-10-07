"""
carousel.py — Coaches as careers, and the programs that hire and fire them.

Every head coach has an age, a personality, a ceiling, a seat that heats and
cools, and a season-by-season history that follows him from job to job.
Every program has an athletic director with a style and three goals it
measures its coach against. After each season:

  1. The season goes in every coach's book: overall, conference, vs the
     Top 25 (ranked at kickoff), on the road, postseason, final rank, roster.
  2. Goals are graded, and the AD judges the season his way. Seats move.
  3. Coaches develop — success grows them fastest, up to a personal ceiling —
     and age. Old coaches retire.
  4. Hot seats get fired. Aggressive ADs try to poach a rising star.
  5. Openings are filled, biggest jobs first. ADs hire by their style;
     sitting coaches say yes or no by their personality, and every coach
     who leaves opens another job. A pool of fired coaches, coordinators
     and high school coaches is always waiting.

Nothing here touches a game directly. A coach changes a program the way a
real one does: recruiting, development, the portal, and game planning.
"""
import world
import random

from names import FIRST_NAMES, LAST_NAMES, full_name
from recruiting_data import STATES

# ═══ Personalities ══════════════════════════════════════════════════════════
# leave:    how tempted he is by a better job
# min_jump: how much more prestige a job needs before he'll listen
# settle:   years at a job before he'll consider leaving at all
# regional: won't leave his part of the country     elite: only listens to jobs this prestigious
# alma:     his old school can have him any time     fixer: takes smaller jumps into programs that are down
# seat_flight: jumps before he's pushed              retire_shift: years off (or on) his retirement age

PERSONALITIES = {
    "climber":   ("Climber", "Always looking at the next rung", {"leave": 1.7, "min_jump": 6, "settle": 2}),
    "loyalist":  ("Loyalist", "Wants to finish where he is", {"leave": 0.25, "min_jump": 22, "settle": 6}),
    "mercenary": ("Mercenary", "Goes wherever the biggest stage is", {"leave": 2.3, "min_jump": 3, "settle": 1}),
    "builder":   ("Builder", "Loves a rebuild, moves on once it's built", {"leave": 1.0, "min_jump": 10, "settle": 4}),
    "homebody":  ("Homebody", "Won't leave his part of the country", {"leave": 0.9, "min_jump": 8, "settle": 3,
                                                                        "regional": True}),
    "journeyman": ("Journeyman", "Keeps a moving truck on speed dial", {"leave": 1.6, "min_jump": 1, "settle": 2}),
    "alma_mater": ("Alma Mater Guy", "Would walk across the country for his old school",
                   {"leave": 0.6, "min_jump": 14, "settle": 3, "alma": True}),
    "blue_blood": ("Blue-Blood Chaser", "Only picks up the phone for the biggest jobs",
                   {"leave": 2.0, "min_jump": 4, "settle": 2, "elite": 82}),
    "fixer":     ("Fixer", "Can't resist a program that's down", {"leave": 1.2, "min_jump": 8, "settle": 3, "fixer": True}),
    "survivor":  ("Survivor", "Jumps before he's pushed", {"leave": 1.1, "min_jump": 10, "settle": 2,
                                                          "seat_flight": True}),
    "short_timer": ("Short-Timer", "Could walk away from coaching any year",
                    {"leave": 1.0, "min_jump": 8, "settle": 3, "retire_shift": -6}),
    "lifer":     ("Lifer", "Will coach until they take the whistle from him",
                  {"leave": 0.7, "min_jump": 12, "settle": 4, "retire_shift": 6}),
}
PERSONALITY_WEIGHTS = {"climber": 18, "loyalist": 12, "mercenary": 8, "builder": 16, "homebody": 12,
                       "journeyman": 7, "alma_mater": 6, "blue_blood": 5, "fixer": 7, "survivor": 7,
                       "short_timer": 5, "lifer": 6}

# Where real coaches played or went to school (for the Alma Mater Guy, and the profile page).
KNOWN_ALMA = {}       # coach name -> alma mater, for named coaches (a universe file can fill it in)

# ═══ Athletic directors ═════════════════════════════════════════════════════
# fire_at: seat heat that gets a coach fired   grace: years before he's judged fully
# heat:    how hard results move the seat      w: what the AD weighs in a season
# hire:    what the AD looks for in a coach    pulse: how hard a single Saturday moves the seat in-season
# rival:   weight on the rivalry game          process: credits roster growth
# improve: credits year-over-year win gains    recruit: judges the recruiting classes
# home:    judges the home record              patience: gives long-tenured coaches rope
# buyout:  hates paying to fire (or to poach)  brand: wants to be ranked, on TV, every week

AD_STYLES = {
    "patient":    ("Patient", "Gives a coach time to build",
                   {"fire_at": 88, "grace": 3, "heat": 0.75, "hire": "fit",
                    "w": {"overall": 1.0, "top25": 0.5, "conf": 0.9, "road": 0.4}}),
    "win_now":    ("Win-Now", "Results this season, or else",
                   {"fire_at": 70, "grace": 1, "heat": 1.3, "hire": "proven",
                    "w": {"overall": 1.5, "top25": 0.8, "conf": 0.8, "road": 0.5}}),
    "big_game":   ("Big-Game Hunter", "Judges coaches by ranked wins and rivals",
                   {"fire_at": 78, "grace": 2, "heat": 1.05, "hire": "splash", "rival": 1.4,
                    "w": {"overall": 0.8, "top25": 1.7, "conf": 0.6, "road": 0.5}}),
    "conference": ("Conference First", "Win the league and everything else follows",
                   {"fire_at": 80, "grace": 2, "heat": 1.0, "hire": "proven",
                    "w": {"overall": 0.8, "top25": 0.6, "conf": 1.7, "road": 0.5}}),
    "analytics":  ("Analytics", "Trusts roster growth and recruiting over one scoreboard",
                   {"fire_at": 82, "grace": 3, "heat": 0.85, "hire": "rising", "process": 1.0,
                    "w": {"overall": 0.9, "top25": 0.5, "conf": 0.7, "road": 0.6}}),
    "booster":    ("Booster-Driven", "Answers to the money, and the money is impatient",
                   {"fire_at": 74, "grace": 2, "heat": 1.2, "hire": "splash", "rival": 1.8, "pulse": 1.3,
                    "w": {"overall": 1.0, "top25": 1.0, "conf": 0.6, "road": 0.9}}),
    "turnaround": ("Turnaround", "Wants to see the arrow pointing up every year",
                   {"fire_at": 80, "grace": 2, "heat": 0.9, "hire": "rising", "improve": 1.0,
                    "w": {"overall": 1.0, "top25": 0.5, "conf": 0.8, "road": 0.5}}),
    "recruiting": ("Recruiting-First", "Talent wins games; he grades the classes",
                   {"fire_at": 82, "grace": 3, "heat": 0.85, "hire": "recruiter", "recruit": 1.0, "pulse": 0.85,
                    "w": {"overall": 0.9, "top25": 0.6, "conf": 0.7, "road": 0.4}}),
    "traditionalist": ("Traditionalist", "Beat the rival, win at home, stay out of the papers",
                   {"fire_at": 80, "grace": 2, "heat": 1.0, "hire": "fit", "rival": 1.6, "home": 1.0,
                    "patience": 1.0, "w": {"overall": 0.9, "top25": 0.6, "conf": 1.0, "road": 0.3}}),
    "budget":     ("Budget Hawk", "Hates writing buyout checks — in either direction",
                   {"fire_at": 90, "grace": 3, "heat": 0.8, "hire": "rising", "buyout": 1.0, "pulse": 0.8,
                    "w": {"overall": 1.0, "top25": 0.4, "conf": 0.9, "road": 0.5}}),
    "brand":      ("Brand Builder", "Wants the program ranked and on TV every Saturday night",
                   {"fire_at": 76, "grace": 2, "heat": 1.1, "hire": "splash", "brand": 1.0, "pulse": 1.2,
                    "w": {"overall": 0.9, "top25": 1.4, "conf": 0.6, "road": 0.6}}),
    "politician": ("Fan Pulse", "Governs by message board and talk radio",
                   {"fire_at": 76, "grace": 1, "heat": 1.15, "hire": "splash", "rival": 1.5, "pulse": 1.5,
                    "w": {"overall": 1.1, "top25": 0.9, "conf": 0.6, "road": 0.8}}),
}
for _key, _pulse in (("patient", 0.75), ("win_now", 1.2), ("big_game", 1.05), ("conference", 1.0), ("analytics", 0.7)):
    AD_STYLES[_key][2]["pulse"] = _pulse
AD_WEIGHTS = {"patient": 14, "win_now": 13, "big_game": 11, "conference": 11, "analytics": 9, "booster": 11,
              "turnaround": 8, "recruiting": 7, "traditionalist": 9, "budget": 7, "brand": 7, "politician": 6}

# ═══ Program goals ══════════════════════════════════════════════════════════
# Each goal asks for something at least once every `window` seasons.


# The one game each program measures itself by.
PRIMARY_RIVAL = {
    "East Alabama": "Alabama", "Alabama": "East Alabama", "Georgia": "Florida", "Florida": "Georgia",
    "Ohio State": "Michigan", "Michigan": "Ohio State", "Texas": "Oklahoma", "Oklahoma": "Texas",
    "Brazos": "Texas", "Bayou State": "Alabama", "Mississippi": "Mississippi State", "Mississippi State": "Mississippi",
    "Tennessee": "Alabama", "Kentucky": "Louisville", "Louisville": "Kentucky", "South Carolina": "Upcountry",
    "Upcountry": "South Carolina", "Florida State": "Florida", "Miami": "Florida State", "Los Angeles": "Southern California",
    "Southern California": "Los Angeles", "South Bend": "Southern California", "Oregon": "Washington", "Washington": "Oregon",
    "Pennsylvania": "Ohio State", "Michigan State": "Michigan", "Iowa": "Iowa State", "Iowa State": "Iowa",
    "Wisconsin": "Minnesota", "Minnesota": "Wisconsin", "Nebraska": "Iowa", "Indiana": "Tippecanoe",
    "Tippecanoe": "Indiana", "Atlanta": "Georgia", "Virginia": "Blacksburg", "Blacksburg": "Virginia",
    "Durham": "North Carolina", "North Carolina": "NC State", "NC State": "North Carolina",
    "Pittsburgh": "West Virginia", "West Virginia": "Pittsburgh", "California": "Palo Alto",
    "Palo Alto": "California", "Arizona": "Arizona State", "Arizona State": "Arizona", "Provo": "Utah",
    "Utah": "Provo", "Kansas": "Kansas State", "Kansas State": "Kansas", "Oklahoma State": "Oklahoma",
    "Arkansas": "Bayou State", "Missouri": "Arkansas", "Nashville": "Tennessee", "Waco": "Fort Worth", "Fort Worth": "Dallas",
    "Dallas": "Fort Worth", "Hudson": "Chesapeake", "Chesapeake": "Hudson", "Illinois": "Lakeshore", "Lakeshore": "Illinois", "Colorado": "Utah",
}
# Cross-conference rivalries the schedule protects every year.
PROTECTED = [("Upcountry", "South Carolina"), ("Florida", "Florida State"), ("Georgia", "Atlanta"),
             ("Kentucky", "Louisville"), ("Iowa", "Iowa State"), ("South Bend", "Southern California"), ("Fort Worth", "Dallas"),
             ("Pittsburgh", "West Virginia"), ("Washington", "Washington State"), ("Oregon", "Oregon State")]



NY6 = {'Arroyo Bowl', 'Crescent Bowl', 'Coral Bowl', 'Lone Star Classic', 'Sonoran Bowl', 'Piedmont Bowl'}
POWER = world.POWER


class Goal:
    """Something a program wants at least once every `window` seasons."""

    LABELS = {
        "beat_rival": "Beat {p}", "ccg": "Reach the conference title game", "conf_title": "Win the conference",
        "wins": "Win {p}+ games", "cfp": "Make the National Playoff", "title": "Win a national title",
        "bowl": "Go to a bowl game", "winning": "Post a winning season", "top25": "Finish in the Top 25",
        "top10": "Finish in the Top 10", "recruit": "Sign a top-{p} recruiting class",
        "bowl_win": "Win a bowl game", "ny6": "Reach a Six Classics bowl", "cfp_win": "Win a playoff game",
        "ranked_wins": "Beat {p} ranked teams in a season", "state": "Win every in-state game",
        "p4_win": "Beat a Power 4 opponent", "home": "Go unbeaten at home", "road": "Post a winning road record",
        "conf_record": "Post a winning conference record", "roster": "Build a roster rated {p}+",
        "improve": "Win more games than the year before", "nonconf": "Go unbeaten outside the conference",
        "close": "Post a winning record in one-score games", "ppg": "Average {p}+ points a game",
        "papg": "Hold opponents under {p} points a game", "ranked_road": "Win at a ranked opponent's stadium",
        "no_blowouts": "Get through a season without losing by 21+",
    }

    def __init__(self, kind, window, param=None, why=""):
        self.kind, self.window, self.param, self.why = kind, window, param, why

    @property
    def short(self):
        if self.kind == "roster":
            import scout
            if scout.hidden():                        # Coach Career: your staff's word, not the number
                return f"Build a roster your staff rates {scout._w(scout.TEAM, self.param or 0)} or better"
        return self.LABELS[self.kind].format(p=self.param)

    @property
    def label(self):
        """'Win a bowl game · window: 3 seasons' — the goal, and how long he has to do it once."""
        every = "every season" if self.window == 1 else f"window: {self.window} seasons"
        return f"{self.short} · {every}"

    SPOKEN = {
        "winning": "finish over .500", "close": "start closing out the tight ones",
        "conf_record": "win more league games than we lose", "roster": "build a real roster, top to bottom",
        "bowl": "get to a bowl game", "bowl_win": "win a bowl game", "recruit": "sign a top-{p} class",
        "home": "protect our stadium — no home losses", "improve": "win more than we did last year",
        "no_blowouts": "stop getting blown out", "ccg": "play in the conference title game",
        "conf_title": "win the league", "top25": "finish ranked", "p4_win": "beat a Power 4 team",
        "ppg": "put up {p} a game", "papg": "hold people under {p}", "road": "win on the road",
        "nonconf": "go unbeaten outside the league", "beat_rival": "beat {p}", "wins": "win {p} games",
    }

    @property
    def spoken(self):
        """How an AD says it out loud, not how the contract reads."""
        t = self.SPOKEN.get(self.kind)
        return t.format(p=self.param) if t else self.short[0].lower() + self.short[1:]

    @property
    def compact(self):
        """For offer cards: 'Beat a Power 4 opponent (1 in 2 yrs)'."""
        return f"{self.short} ({'every year' if self.window == 1 else f'at least once in {self.window} yrs'})"

    def achieved(self, s):
        k, p = self.kind, self.param
        return {
            "beat_rival": lambda: p in s.get("beat", []),
            "ccg": lambda: s.get("ccg", False), "conf_title": lambda: s.get("conf_champ", False),
            "wins": lambda: s["w"] >= p, "cfp": lambda: s.get("cfp", False), "title": lambda: s.get("title", False),
            "bowl": lambda: s.get("bowl", False) or s.get("cfp", False), "winning": lambda: s["w"] > s["l"],
            "top25": lambda: bool(s.get("final_rank")),
            "top10": lambda: bool(s.get("final_rank")) and s["final_rank"] <= 10,
            "recruit": lambda: bool(s.get("class_rank")) and s["class_rank"] <= p,
            "bowl_win": lambda: s.get("bowl_win", False) or s.get("cfp_win", False),
            "ny6": lambda: s.get("ny6", False), "cfp_win": lambda: s.get("cfp_win", False),
            "ranked_wins": lambda: s["t25w"] >= p,
            "state": lambda: s.get("instate_games", 0) > 0 and s.get("instate_losses", 1) == 0,
            "p4_win": lambda: s.get("p4_wins", 0) > 0, "home": lambda: s.get("hl", 1) == 0 and s.get("hw", 0) > 0,
            "road": lambda: s["rw"] > s["rl"], "conf_record": lambda: s["cw"] > s["cl"],
            "roster": lambda: s.get("roster", 0) >= p,
            "improve": lambda: s.get("prev_w") is not None and s["w"] > s["prev_w"],
            "nonconf": lambda: s.get("ncw", 0) + s.get("ncl", 1) > 0 and s.get("ncl", 1) == 0,
            "close": lambda: s.get("close_w", 0) > s.get("close_l", 0),
            "ppg": lambda: s.get("g", 0) > 0 and s["pf"] / s["g"] >= p,
            "papg": lambda: s.get("g", 0) > 0 and s["pa"] / s["g"] < p,
            "ranked_road": lambda: s.get("t25_road_w", 0) > 0,
            "no_blowouts": lambda: "blowout_l" in s and s.get("g", 0) > 0 and s["blowout_l"] == 0,
        }[k]()

    def applies(self, s):
        """Could this goal even be met this season? (A rival you didn't play doesn't count.)"""
        if self.kind == "beat_rival":
            return self.param in s.get("opps", [])
        if self.kind == "state":
            return s.get("instate_games", 0) > 0
        if self.kind == "p4_win":
            return s.get("p4_games", 0) > 0
        if self.kind == "improve":
            return s.get("prev_w") is not None
        if self.kind == "nonconf":
            return s.get("ncw", 0) + s.get("ncl", 0) > 0
        if self.kind == "close":
            return s.get("close_w", 0) + s.get("close_l", 0) > 0
        return True


# Program-specific ambitions — the thing people at that school actually talk about.
SIGNATURE = {
    "Ohio State": ("beat_rival", 1, "Michigan"), "Michigan": ("beat_rival", 2, "Ohio State"),
    "Alabama": ("title", 4, None), "Georgia": ("title", 5, None), "Texas": ("beat_rival", 1, "Oklahoma"),
    "Oklahoma": ("beat_rival", 2, "Texas"), "South Bend": ("wins", 3, 11), "Southern California": ("top10", 3, None),
    "Miami": ("top10", 3, None), "Indiana": ("cfp", 3, None), "Nashville": ("bowl_win", 3, None),
    "Kansas State": ("beat_rival", 1, "Kansas"), "Iowa": ("conf_record", 1, None),
    "Wisconsin": ("conf_record", 1, None), "Lakeshore": ("bowl", 3, None), "Boise State": ("ny6", 4, None),
    "Provo": ("ranked_wins", 3, 2), "Hudson": ("beat_rival", 1, "Chesapeake"), "Chesapeake": ("beat_rival", 1, "Hudson"),
    "Appalachian State": ("p4_win", 2, None), "Shenandoah": ("p4_win", 2, None), "New Orleans": ("ny6", 5, None),
    "Memphis": ("p4_win", 2, None), "Orlando": ("ranked_wins", 3, 1), "Florida State": ("state", 2, None),
    "Upcountry": ("state", 1, None), "East Alabama": ("beat_rival", 3, "Alabama"), "Brazos": ("beat_rival", 3, "Texas"),
    "Florida": ("state", 3, None), "Bayou State": ("title", 5, None), "Oregon": ("cfp_win", 3, None),
    "Pennsylvania": ("cfp_win", 3, None), "Utah": ("home", 2, None), "Washington": ("beat_rival", 3, "Oregon"),
    "Tennessee": ("beat_rival", 3, "Alabama"), "Kentucky": ("bowl_win", 2, None),
    "Mississippi": ("ppg", 2, 34), "Kansas": ("improve", 2, None), "Durham": ("close", 2, None),
    "Minnesota": ("no_blowouts", 2, None), "Front Range": ("ranked_road", 4, None),
}

# Which goals each AD style reaches for when it's his turn to set them.
AD_GOAL_TASTE = {
    "patient": ("winning", "bowl", "conf_record", "roster", "recruit", "improve"),
    "win_now": ("wins", "cfp", "top25", "top10", "bowl_win", "ppg"),
    "big_game": ("beat_rival", "ranked_wins", "top25", "cfp_win", "ny6", "ranked_road"),
    "conference": ("ccg", "conf_title", "conf_record", "wins", "close"),
    "analytics": ("recruit", "roster", "top25", "wins", "papg", "close"),
    "booster": ("beat_rival", "road", "home", "bowl_win", "state", "nonconf"),
    "turnaround": ("improve", "winning", "bowl", "conf_record", "close"),
    "recruiting": ("recruit", "roster", "top25", "wins"),
    "traditionalist": ("beat_rival", "home", "state", "conf_record", "no_blowouts"),
    "budget": ("winning", "bowl", "conf_record", "nonconf", "improve"),
    "brand": ("top25", "top10", "ranked_wins", "ny6", "ppg", "ranked_road"),
    "politician": ("beat_rival", "nonconf", "home", "no_blowouts", "bowl_win", "ppg"),
}


def _rival_of(team, league=None):
    """The rival a program measures itself against — only if they actually play."""
    r = PRIMARY_RIVAL.get(team.school)
    if not r or league is None:
        return [r] if r else []
    other = next((t for t in league.teams if t.school == r), None)
    if other is None:
        return []
    if other.conference == team.conference or (team.school, r) in PROTECTED or (r, team.school) in PROTECTED:
        return [r]
    return []


def _tier(team):
    p = team.prestige
    return 5 if p >= 88 else 4 if p >= 78 else 3 if p >= 68 else 2 if p >= 58 else 1


def _instate_fbs(team, league):
    return [t for t in league.teams if t is not team and t.home_state == team.home_state]


def _goal_menu(team, league, tier):
    """Every goal that makes sense for a program at this level."""
    power = team.conference in POWER or team.school == world.FLAGSHIP_INDEPENDENT
    conf = team.conference != "Independent"
    rival = (_rival_of(team, league) or [None])[0]
    m = []
    if tier == 5:
        m += [Goal("cfp", 2), Goal("conf_title", 3) if conf else Goal("wins", 3, 11), Goal("title", 5),
              Goal("top10", 2), Goal("cfp_win", 3), Goal("ranked_wins", 2, 3), Goal("recruit", 2, 10),
              Goal("wins", 2, 11), Goal("nonconf", 1), Goal("ranked_road", 2), Goal("ppg", 2, 35),
              Goal("papg", 2, 20), Goal("no_blowouts", 2)]
        if rival:
            m += [Goal("beat_rival", 2, rival)]
    elif tier == 4:
        m += [Goal("ccg", 3) if conf else Goal("cfp", 4), Goal("wins", 3, 10), Goal("top25", 2), Goal("cfp", 4),
              Goal("ny6", 4), Goal("ranked_wins", 2, 2), Goal("recruit", 2, 20), Goal("bowl_win", 2),
              Goal("nonconf", 2), Goal("close", 2), Goal("ranked_road", 3), Goal("ppg", 2, 32), Goal("papg", 2, 22)]
        if rival:
            m += [Goal("beat_rival", 3, rival)]
    elif tier == 3:
        m += [Goal("bowl", 2), Goal("wins", 3, 9) if power else Goal("ccg", 3), Goal("top25", 4),
              Goal("bowl_win", 3), Goal("conf_record", 2), Goal("ranked_wins", 3, 1), Goal("recruit", 3, 35),
              Goal("road", 2), Goal("improve", 2), Goal("close", 2), Goal("no_blowouts", 2), Goal("papg", 2, 25)]
        if rival:
            m += [Goal("beat_rival", 3, rival)]
    elif tier == 2:
        m += [Goal("bowl", 2), Goal("winning", 2), Goal("bowl_win", 3), Goal("conf_record", 2),
              Goal("home", 3), Goal("recruit", 3, 55), Goal("improve", 2), Goal("no_blowouts", 3),
              Goal("ppg", 3, 28)]
        m += [Goal("ccg", 4)] if not power else [Goal("wins", 4, 8)]
        if not power:
            m += [Goal("p4_win", 3)]
        if rival:
            m += [Goal("beat_rival", 4, rival)]
    else:
        m += [Goal("bowl", 3), Goal("winning", 3), Goal("conf_record", 3), Goal("home", 4),
              Goal("recruit", 3, 70), Goal("roster", 3, 62), Goal("p4_win", 4), Goal("ccg", 5),
              Goal("improve", 2), Goal("close", 3), Goal("no_blowouts", 3)]
    if len(_instate_fbs(team, league)) >= 2 and tier >= 3:
        m += [Goal("state", 3)]
    return m


def fresh_roster_goal(g, team):
    """A roster goal is the next rung above today's roster (a goal you've already met
    isn't a goal). The rungs are the staff's words, so it can be tracked in Coach Career."""
    import scout
    if (g.param or 0) > team.team_ovr:
        return
    cuts = [cut for cut, _ in scout.TEAM if cut > team.team_ovr]
    g.param = max(62, min(cuts) if cuts else int(team.team_ovr) + 3)


def refresh_roster_goals(team):
    for g in getattr(team, "goals", []):
        if g.kind == "roster":
            fresh_roster_goal(g, team)


def assign_goals(team, league, rng, reason="initial"):
    """Three goals: the program's signature ambition (if it has one), then the AD's
    priorities from what fits this program, then whatever fits best."""
    tier = getattr(team, "goal_tier", None) or _tier(team)
    team.goal_tier = tier
    menu = _goal_menu(team, league, tier)
    taste = AD_GOAL_TASTE[team.ad["style"]]
    goals = []
    sig = SIGNATURE.get(team.school)
    if sig:
        kind, window, param = sig
        if kind != "beat_rival" or param in _rival_of(team, league):
            goals.append(Goal(kind, window, param, why="program tradition"))
    rng.shuffle(menu)
    liked = [g for g in menu if g.kind in taste]
    rng.shuffle(liked)
    menu = liked[:2] + [g for g in menu if g not in liked[:2]]      # the AD's two priorities, then the rest
    for g in menu:
        if len(goals) >= 3:
            break
        if any(x.kind == g.kind for x in goals):
            continue
        g.why = "AD priority" if g.kind in taste else "program standard"
        if g.kind == "roster":
            fresh_roster_goal(g, team)
        goals.append(g)
    team.goals = goals[:3]
    team.goals_set = league.year
    return team.goals


def review_goals(team, league, rng, coach=None):
    """Raise the bar after sustained success, lower it after sustained failure,
    and occasionally let the AD reshuffle priorities."""
    coach = coach or team.coach
    recent = [s for s in coach.history if s["school"] == team.school][-3:] if coach else []
    tier = getattr(team, "goal_tier", _tier(team))
    changed = None
    if len(recent) >= 3:
        met = sum(any(g.achieved(s) for g in team.goals) for s in recent)
        pct = sum(s["w"] for s in recent) / max(1, sum(s["w"] + s["l"] for s in recent))
        if pct >= 0.75 and tier < 5 and met >= 2:
            tier, changed = tier + 1, "raised the bar"
        elif pct <= 0.35 and tier > 1:
            tier, changed = tier - 1, "reset expectations"
    if changed or rng.random() < 0.15 or league.year - getattr(team, "goals_set", league.year) >= 6:
        team.goal_tier = max(1, min(5, tier if changed else max(tier, _tier(team) - 1)))
        old = [g.label for g in team.goals]
        assign_goals(team, league, rng)
        team.goals_set = league.year + 1              # new goals start with next season
        if [g.label for g in team.goals] != old:
            why = changed or "new priorities"
            _news(league, "goals", f"{team.school} AD {team.ad['name']} {why}: " +
                  "; ".join(g.short.lower() for g in team.goals))


def goal_status(team, coach, goal, year):
    """('met', year) / ('failed', None) / ('pending', seasons left) for the current tenure."""
    tenure = [s for s in coach.history if s["school"] == team.school and s["year"] >= getattr(team, "goals_set", 0)]
    chances = [s for s in tenure if goal.applies(s)]
    hits = [s["year"] for s in chances[-goal.window:] if goal.achieved(s)]
    if hits:
        return "met", hits[-1]
    if len(chances) >= goal.window:
        return "failed", None
    return "pending", goal.window - len(chances)

KNOWN = {}            # coach name -> (age in 2026, first season), for named coaches
from coach_facts import RECENT_WINNERS as _RECENT_WINNERS, FACTS as _FACTS, ALMA as _ALMA, stops_for as _stops_for
KNOWN.update(_FACTS)
for _n, _a in _ALMA.items():
    KNOWN_ALMA.setdefault(_n, _a)


# ── How good a coach can become — elite is rare ──────────────────────────────
ELITE_SOFT_CAP = 88            # past this, only a rare few keep climbing


def age_room(age):
    """How much a coach this old can still grow. Young coaches: no limit but their
    talent. By the mid-fifties a ceiling is a few points; past sixty, what you see."""
    if age <= 38:
        return 99
    return max(0, int(round(12 * (60 - age) / 22)))


def fit_ceiling(coach):
    """A ceiling converges on the coach as he ages."""
    age = getattr(coach, "age", None)
    if age is None or getattr(coach, "ceiling", None) is None or getattr(coach, "is_user", False):
        return
    cap = coach.overall + age_room(age)
    coach.ceiling = max(coach.overall, min(coach.ceiling, cap))


# What a coach can become, whatever he is today. Most coaches top out as ordinary head coaches —
# plenty finish a long career in the 60s — some become good ones, a few very good, and real
# greatness is rare: about one in thirty.
POTENTIAL_TIERS = ((0.03, 92, 3.0),     # elite
                   (0.13, 84, 3.0),     # very good
                   (0.42, 76, 3.5),     # good
                   (1.00, 67, 5.0))     # ordinary


def roll_ceiling(ovr, rng, room=4.0):
    """His ceiling, drawn from the potential tiers. A young coordinator (room > 8) gets a
    slightly better draw; a coach who's already past his tier keeps only a sliver of room."""
    r = rng.random() * (0.85 if room > 8 else 1.0)
    for cut, mean, sd in POTENTIAL_TIERS:
        if r < cut:
            target = rng.gauss(mean, sd)
            break
    c = max(target, ovr + rng.uniform(1, 3))
    if c > ELITE_SOFT_CAP and target < ELITE_SOFT_CAP:
        c = ELITE_SOFT_CAP + (c - ELITE_SOFT_CAP) * 0.3      # past the soft cap, only a real talent keeps climbing
    return int(min(99, max(ovr + 1, round(c))))


def perceived(coach, league=None):
    """What an AD thinks a coach is. The less he's done as a head coach, the
    bigger the miss can be — the hot coordinator who can't run a program, the
    quiet guy nobody noticed."""
    err = getattr(coach, "hype", None)
    if err is None:
        err = coach.hype = random.Random(f"hype:{coach.name}").gauss(0, 1)
    seasons = len(getattr(coach, "history", []) or [])
    sd = 7.0 if seasons == 0 else 5.0 if seasons <= 2 else 3.0 if seasons <= 5 else 1.5
    return coach.overall + err * sd


FIT_SD = 0.6      # rating points; worth about a point on the scoreboard either way (1.8 was worth ~3.5, every week)


def roll_fit(coach, team, league):
    """Some coaches and places just click; some don't. Hidden, and it shows on Saturdays."""
    fit = coach.__dict__.setdefault("fit_with", {})
    if team.school not in fit:
        fit[team.school] = round(random.Random(f"fit:{coach.name}:{team.school}:{league.year}").gauss(0, FIT_SD), 2)
    return fit[team.school]


def _seeded(coach, salt):
    return random.Random(f"{salt}:{coach.name}")


def init_coach(coach, year, rng=None, origin=None):
    """Give a coach an age, a personality, a ceiling, and an empty book."""
    r = _seeded(coach, "career")
    age, hired = KNOWN.get(coach.name, (None, None))
    coach.age = age or int(max(34, min(70, r.gauss(50, 7))))
    coach.hired_year = hired or year - r.choice((0, 0, 1, 1, 2, 2, 3, 3, 4, 5, 6, 8))
    keys, weights = zip(*PERSONALITY_WEIGHTS.items())
    coach.personality = r.choices(keys, weights=weights)[0]
    coach.ceiling = max(coach.overall + 1, roll_ceiling(coach.overall, r))
    coach.seat = int(max(5, min(62, r.gauss(32, 12))))
    coach.history = []             # one dict per season, every job he's had
    coach.seat_log = []            # (year, heat, [reasons])
    coach.origin = origin or "FBS head coach"
    coach.status = "employed"      # employed / unemployed / retired
    coach.pool_years = 0
    coach.hot_years = 0
    coach.retire_age = int(max(56, min(80, r.gauss(66, 4)
                                    + PERSONALITIES[coach.personality][2].get("retire_shift", 0))))
    coach.alma_mater = _alma_for(coach)
    coach.__dict__.pop("fade_age", None)
    longevity(coach)
    if not getattr(coach, "stops", None):
        real = _stops_for(coach.name)
        if real:
            coach.stops = real
    fit_ceiling(coach)


def _is_real_hc(coach):
    from coaches_data import HEAD_COACHES
    return coach.name in HEAD_COACHES.values()


def _alma_for(coach):
    if coach.name in KNOWN_ALMA:
        return KNOWN_ALMA[coach.name]
    if _is_real_hc(coach):
        return None                                   # a real coach: don't make one up
    from teams_data import TEAMS
    return _seeded(coach, "alma").choice([row[0] for row in TEAMS])


def init_program(team, rng):
    ad_rng = random.Random(f"ad:{team.school}")
    style = ad_rng.choices(list(AD_WEIGHTS), weights=list(AD_WEIGHTS.values()))[0]
    team.ad = {"name": full_name(ad_rng), "style": style,
               "inherited": False, "since": 2026 - ad_rng.randint(0, 8)}
    import ad_market
    ad_market.fill(team.ad, team, team.school)
    team.coach_changed = False
    team.coach_log = []            # [(first season, coach name)]


def setup(league):
    """Called once when a new world is built."""
    league.coach_pool = []         # coaches without a job (fired, coordinators, high school)
    league.retired_coaches = []
    league.carousel = {}           # year -> list of (kind, text) news items
    for team in league.teams:
        init_program(team, league.rng)
        init_coach(team.coach, league.year)
        roll_fit(team.coach, team, league)
        team.coach_log.append((team.coach.hired_year, team.coach.name))
        assign_goals(team, league, league.rng)
    refresh_pool(league, league.rng, first=True)
    import staff
    staff.setup(league)
    staff.seed_past(league)        # coordinators arrive with careers and last year's units
    from names import dedupe_roster
    nrng = random.Random(f"names:{league.seed}")
    for team in league.teams + list(getattr(league, "fcs_teams", [])):
        staff_names = {c.name.split()[-1] for c in (team.coach, getattr(team, "oc", None), getattr(team, "dc", None))
                       if c is not None}
        dedupe_roster(team, nrng, reserved=staff_names)   # one Brown per locker room, and not the DC's name
    for team in league.teams:
        settle_homebody(team.coach)
    seed_preseason_seats(league)   # nobody starts a season with a blank reputation
    import finance
    finance.ensure_all(league)     # budgets, and a contract for everybody on a staff


def seed_preseason_seats(league):
    """Day one of a new world: seats start where the offseason talk would put them —
    what the program expects against the roster he's got, and how long he's had."""
    teams = [t for t in league.teams if t.coach is not None]
    n = len(teams)
    by_prestige = {t: i for i, t in enumerate(sorted(teams, key=lambda t: -t.prestige))}
    by_roster = {t: i for i, t in enumerate(sorted(teams, key=lambda t: -t.team_ovr))}
    for team in teams:
        c = team.coach
        r = _seeded(c, f"seat:{league.seed}")
        tenure = league.year - (c.hired_year or league.year)
        gap = (by_roster[team] - by_prestige[team]) / n          # + : the roster's worse than the name
        style = AD_STYLES[team.ad["style"]][2]
        heat = 35 + gap * 150 + r.gauss(0, 14)
        if tenure >= 3:
            heat += min(4, tenure - 2) * 3 * (1 if gap > 0 else -1)   # long enough to own the roster
        heat *= style.get("heat", 1.0)
        if by_roster[team] < 12 and gap <= 0.05:
            heat = min(heat, 18)                                   # a contender with a contender's roster
        rec = getattr(c, "ratings", {}).get("recruiting", 0)
        if rec >= 90 and tenure >= 1:
            heat = min(heat, 20)                                   # an elite recruiter isn't on anybody's list
        if c.name in _RECENT_WINNERS:
            heat = min(heat, 12)                                   # coming off a title or a playoff run
        if tenure == 0:
            heat = min(heat, r.uniform(4, 14))                     # the honeymoon
        elif tenure == 1:
            heat = min(heat, 45)
        # Hot, but never already past this AD's firing line: a coach gets his season to save himself.
        c.seat = int(max(3, min(90, max(55, fire_line(team) - 4), round(heat))))
        why = []
        if tenure == 0:
            why.append("first season on the job")
        elif gap >= 0.12:
            why.append(f"roster ranks #{by_roster[team] + 1} at a program that expects top-{max(10, by_prestige[team] + 1)}")
        elif gap <= -0.12:
            why.append(f"roster (#{by_roster[team] + 1}) better than the program's history")
        if tenure >= 4 and gap > 0.03:
            why.append(f"year {tenure + 1} — it's his roster now")
        c.seat_log.append((league.year - 1, c.seat, why or ["preseason expectations (no games yet)"]))



def stamp_ranks(league, game):
    """Record both teams' poll rank at kickoff (called before every game)."""
    game.ranks = {t: league.rankings.rank_of(t) for t in (game.home, game.away)}


def season_line(league, team):
    """Everything that happened to this team this season, as the AD sees it."""
    s = {"year": league.year, "school": team.school, "conf": team.conference,
         "w": team.wins, "l": team.losses, "cw": team.conf_wins, "cl": team.conf_losses,
         "t25w": 0, "t25l": 0, "rw": 0, "rl": 0, "hw": 0, "hl": 0, "pw": 0, "pl": 0, "beat": [], "lost_to": [],
         "opps": [], "final_rank": league.rankings.rank_of(team), "roster": team.team_ovr, "class_rank": None,
         "ccg": False, "conf_champ": False, "cfp": False, "cfp_win": False, "ny6": False, "bowl": False,
         "bowl_win": False, "title": False, "post": "", "instate_games": 0, "instate_losses": 0,
         "p4_games": 0, "p4_wins": 0, "close_w": 0, "close_l": 0,
         "ncw": 0, "ncl": 0, "pf": 0, "pa": 0, "g": 0, "t25_road_w": 0, "blowout_l": 0, "prev_w": None}
    prev = [r for r in getattr(team, "historical_records", []) if r[0] == league.year - 1]
    if prev:
        s["prev_w"] = prev[-1][1]
    for g in league.team_games(team):
        if not g.played:
            continue
        opp = g.opponent_of(team)
        won = g.winner is team
        s["g"] += 1
        s["pf"] += g.score_for(team)
        s["pa"] += g.score_for(opp)
        if not won and g.score_for(opp) - g.score_for(team) >= 21:
            s["blowout_l"] += 1
        if g.game_type == "Regular Season" and not g.conference_game:
            s["ncw" if won else "ncl"] += 1
        if getattr(g, "ranks", {}).get(opp):
            s["t25w" if won else "t25l"] += 1
            if won and g.away is team and not g.neutral:
                s["t25_road_w"] += 1
        if not g.neutral:
            if g.away is team:
                s["rw" if won else "rl"] += 1
            else:
                s["hw" if won else "hl"] += 1
        (s["beat"] if won else s["lost_to"]).append(opp.school)
        s["opps"].append(opp.school)
        if abs(g.home_score - g.away_score) <= 8:
            s["close_w" if won else "close_l"] += 1
        if getattr(opp, "home_state", None) == team.home_state and not getattr(opp, "fcs", False):
            s["instate_games"] += 1
            s["instate_losses"] += not won
        if opp.conference in POWER or opp.school == world.FLAGSHIP_INDEPENDENT:
            s["p4_games"] += 1
            s["p4_wins"] += won
        gt = g.game_type
        if gt != "Regular Season":
            s["pw" if won else "pl"] += 1
        if gt == "Conference Championship":
            s["ccg"], s["conf_champ"] = True, won
            s["post"] = f"{'Won' if won else 'Lost'} {g.bowl_name}"
        elif gt == "Bowl":
            s["bowl"], s["bowl_win"] = True, won
            s["post"] = f"{'Won' if won else 'Lost'} {g.bowl_name}"
        elif gt in ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship"):
            s["cfp"] = True
            s["cfp_win"] = s["cfp_win"] or won
            if gt != "NP First Round":
                s["ny6"] = True
            s["title"] = gt == "National Championship" and won
            s["post"] = "National Champion" if s["title"] else (f"Lost {ps_round(gt)}" if not won else s["post"])
    if s["conf_champ"] and s["cfp"] and not s["title"]:
        s["post"] += f" · {team.conference} champ"
    return s


def ps_round(gt):
    return {"NP First Round": "NP first round", "NP Quarterfinal": "NP quarterfinal",
            "NP Semifinal": "NP semifinal", "National Championship": "national title game"}.get(gt, gt)


def league_ovrs(league):
    """Every program's team rating, sorted. Compute it once and pass it to
    expected_pct when judging many teams — rating all 138 rosters is the slow part."""
    return sorted(t.team_ovr for t in league.teams)


def expected_pct(team, league, ovrs=None):
    """What a reasonable AD expects: half program stature, half roster talent."""
    ovrs = ovrs if ovrs is not None else league_ovrs(league)
    mine = team.team_ovr
    talent = ovrs.index(min(ovrs, key=lambda v: abs(v - mine))) / max(1, len(ovrs) - 1)
    stature = (team.prestige - 43) / 51
    return max(0.2, min(0.85, 0.2 + 0.62 * (0.5 * talent + 0.5 * stature)))


# ═══ Judging a season ═══════════════════════════════════════════════════════
# ADs don't react to one year. They look at the trend — this season counts
# half, the two before it the rest — and they know a new coach needs time.

FIRST_JUDGED = {"patient": 4, "win_now": 3, "big_game": 3, "conference": 3, "analytics": 4, "booster": 3,
                "turnaround": 3, "recruiting": 4, "traditionalist": 3, "budget": 4, "brand": 3, "politician": 2}


def _season_perf(s, ad):
    pct = lambda w, l: w / (w + l) if w + l else None
    exp = s.get("exp", 0.5)
    parts = {"overall": (pct(s["w"], s["l"]), exp), "conf": (pct(s["cw"], s["cl"]), exp - 0.03),
             "top25": (pct(s["t25w"], s["t25l"]), max(0.1, exp - 0.32)), "road": (pct(s["rw"], s["rl"]), exp - 0.08)}
    num = den = 0.0
    for k, (got, want) in parts.items():
        if got is not None:
            num += ad["w"][k] * (got - want)
            den += ad["w"][k]
    return num / den if den else 0.0


def _ovr(league, team):
    """Team ratings, cached for the week — rating a roster is the slow part."""
    key = (league.year, league.week)
    cache = league.__dict__.get("_ovr_week")
    if cache is None or cache[0] != key:
        cache = league._ovr_week = (key, {})
    d = cache[1]
    if team not in d:
        d[team] = 50 if getattr(team, "fcs", False) else team.team_ovr
    return d[team]


def win_prob(team, opp, site, league=None):
    """Before kickoff, how likely this team was to win (site: 1 home, -1 road, 0 neutral)."""
    if league is not None:
        a, o = _ovr(league, team), _ovr(league, opp)
    else:
        a, o = team.team_ovr, (50 if getattr(opp, "fcs", False) else opp.team_ovr)
    d = a - o + 2.0 * site
    return 1 / (1 + 10 ** (-d / 11))


def expected_wins(league, team):
    """Game by game: how many games this roster should have won against the
    schedule it actually played. The honest baseline for a coach."""
    xw, n = 0.0, 0
    for g in league.team_games(team):
        if not g.played:
            continue
        opp = g.opponent_of(team)
        site = 0 if g.neutral else (1 if g.home is team else -1)
        xw += win_prob(team, opp, site, league)
        n += 1
    return xw, n


def expectation(league, team, coach, ovrs=None):
    """Expected wins this season, as the AD sees them. Early on he judges the
    coach against the roster he inherited; the longer the coach has been there,
    the more the AD expects what the program's stature says it should win —
    by year four it's his roster."""
    xw, n = expected_wins(league, team)
    if not n:
        return 0.0, 0
    stature = expected_pct(team, league, ovrs) * n
    tenure = league.year - (coach.hired_year or league.year) + 1
    w = {1: 0.15, 2: 0.25, 3: 0.35}.get(tenure, 0.5)
    import difficulty
    bar = difficulty.expect(coach) * n / 12               # your difficulty: how demanding the AD is
    return max(0.0, min(n, (1 - w) * xw + w * stature + bar)), n


def _class_expectation(team, league):
    """Where a program this size should be signing its class."""
    order = sorted((t for t in league.teams), key=lambda t: -t.prestige)
    return order.index(team) + 1


def judge(league, team, coach, s, rng):
    """Move the seat after a season. Returns (delta, reasons). Every piece is a
    line in the AD's ledger, so the Hot Seat screen can say why."""
    style = team.ad["style"]
    ad = AD_STYLES[style][2]
    ledger = []

    def add(pts, why=None):
        if pts:
            ledger.append((pts, why))

    # 1. Results against expectation, this year and the two before it.
    mine = [h for h in coach.history if h["school"] == team.school][-3:]
    gaps = [h["w"] - h.get("xw", h["exp"] * (h["w"] + h["l"])) for h in reversed(mine)]
    weights = (0.55, 0.28, 0.17)[:len(gaps)]
    gap = sum(w * g for w, g in zip(weights, gaps)) / sum(weights)
    add(-gap * 7.5 * ad["heat"],
        f"won {gaps[0]:+.1f} games vs. what the roster and schedule said" if abs(gaps[0]) >= 1 else None)
    if len(gaps) >= 2:
        trend = gaps[0] - gaps[1]
        if trend >= 2:
            add(-5, "program is trending up")
        elif trend <= -2:
            add(5, "program is trending down")

    # 2. The AD's own lens on the season.
    perf = _season_perf(s, ad)
    add(-perf * 25 * ad["heat"])

    # 3. Goals: a few points each way, capped so a checklist can't run a program.
    met = missed = 0
    for goal in getattr(team, "goals", []):
        if not goal.applies(s):
            continue
        status, _ = goal_status(team, coach, goal, league.year)
        if goal.achieved(s):
            met += 1
            ledger.append((-5, f"met goal: {goal.short.lower()}"))
        elif status == "failed":
            misses = coach.__dict__.setdefault("missed", {})
            key = (team.school, goal.kind, goal.param)
            if league.year - misses.get(key, -99) >= goal.window:
                misses[key] = league.year
                missed += 1
                ledger.append((8, f"missed goal: {goal.short.lower()}"))
    over = sum(p for p, w in ledger if w and w.startswith("met goal")) + 12
    if over < 0:
        ledger.append((-over, None))                               # goal credit caps at -12
    over = sum(p for p, w in ledger if w and w.startswith("missed goal")) - 20
    if over > 0:
        ledger.append((-over, None))                               # ...and blame at +20

    # 4. The rival and the postseason.
    rw = ad.get("rival", 1.0)
    rival = PRIMARY_RIVAL.get(team.school)
    if rival in s["beat"]:
        add(-3 * rw, f"beat {rival}" if rw > 1.2 else None)
    elif rival in s["lost_to"]:
        add(4 * rw, f"lost to {rival}" if rw > 1.2 else None)
    if s["title"]:
        add(-35, "won the national title")
    elif s["cfp"]:
        add(-10, "made the playoff")
    if s["conf_champ"]:
        add(-7, f"won the {team.conference}")
    exp_pct = s.get("exp", 0.5)
    if not s["bowl"] and not s["cfp"] and exp_pct >= 0.55:
        add(5, "no bowl game")

    # 5. Recruiting: every AD looks at the class; the Recruiting-First AD lives by it.
    cr = s.get("class_rank") or next((h.get("class_rank") for h in reversed(mine) if h.get("class_rank")), None)
    if cr:
        want = _class_expectation(team, league)
        diff = (cr - want) / 15                                    # 15 spots worse than a program this size = +1
        add(max(-6, min(6, diff * 3 * (1.0 + ad.get("recruit", 0) * 1.5))),
            "recruiting well above the program's weight" if diff <= -1.3 else
            "recruiting below the program's weight" if diff >= 1.3 else None)

    # 6. Style extras the old verdict had.
    if ad.get("home") and s["hw"] + s["hl"]:
        if s["hl"] == 0:
            add(-4, "unbeaten at home")
        elif s["hl"] > s["hw"]:
            add(5, "losing at home")
    if ad.get("brand"):
        if s["final_rank"]:
            add(-5, "finished ranked")
        elif _tier(team) >= 3:
            add(4, "invisible nationally")
    if ad.get("process") and len(mine) >= 2:
        growth = mine[-1]["roster"] - mine[-2]["roster"]
        add(-growth * 1.5, "roster is getting better" if growth >= 2 else None)

    # 7. Money and patience in the stands.
    import finance
    k = finance.contract(coach)
    if k and gap < -0.5:
        pay = k["salary"] / (finance.HC_SHARE * finance.budget(team))
        if pay >= 1.15:
            add(min(6, (pay - 1) * 12), "paid like a winner, not winning like one")
    losing = 0
    for h in reversed([h for h in coach.history if h["school"] == team.school]):
        if h["w"] < h["l"]:
            losing += 1
        else:
            break
    if losing >= 2:
        add(3 * (losing - 1), f"{losing} straight losing seasons — the stands are emptying")

    delta = sum(p for p, _ in ledger)
    reasons = [w for p, w in sorted(ledger, key=lambda x: -abs(x[0])) if w]

    # 8. Who gets rope.
    tenure = league.year - (coach.hired_year or league.year) + 1
    if tenure < FIRST_JUDGED[style] and delta > 0:
        delta *= 0.35 if tenure <= 1 else 0.6
        reasons.append("still building")
    if delta > 0 and any(h["title"] or h["cfp"] for h in mine[:-1]) and not s["cfp"]:
        delta *= 0.7
        reasons.append("recent playoff credit")
    if ad.get("patience") and delta > 0 and len([h for h in coach.history if h["school"] == team.school]) >= 6:
        delta *= 0.7
        reasons.append("has earned some rope")
    if team.ad.get("inherited") and delta > 0:
        delta *= 1.2                                  # a new AD didn't hire him
        reasons.append("new AD didn't hire him")
    delta += (45 - coach.seat) * 0.2                 # memories fade toward neutral
    coach.seat_ledger = [(round(p, 1), w) for p, w in ledger if abs(p) >= 1]
    return delta, reasons


def ad_judging(team, short=False):
    """How this AD watches you, in one line — and how that squares with the goals.
    The style is the mood (how loud one Saturday is, how short the leash);
    the goals are the floor he measures over their windows."""
    style, blurb, rules = AD_STYLES[team.ad["style"]]
    pulse = rules.get("pulse", 1.0)
    mood = ("judges you every Saturday" if pulse >= 1.25 else "reacts to every result" if pulse >= 1.1
            else "doesn't overreact to one game" if pulse <= 0.8 else "watches the whole season")
    leash = "short leash" if rules["fire_at"] <= 74 else "long leash" if rules["fire_at"] >= 86 else "normal leash"
    grace = rules.get("grace", 2)
    if short:
        return f"{style} AD: {mood}, {leash}, judges the goals from year {grace + 1}."
    return (f"{style} AD — {blurb[0].lower() + blurb[1:]}. He {mood} ({leash}). Every season moves your seat, "
            f"but he won't judge you on the goals until year {grace + 1} — hit each one at least once in its window.")


def seat_label(heat):
    if heat >= 85:
        return "Scorching"
    if heat >= 70:
        return "Hot"
    if heat >= 50:
        return "Warm"
    if heat >= 20:
        return "Stable"
    return "Ice cold"


# ═══ The seat during the season ═════════════════════════════════════════════
# The verdict still comes after the season (judge, above). But nobody waits
# until December to talk about it: every Saturday moves the seat. The live
# seat is where the coach started the season, moved by how the year is going
# against what his AD expected, plus the games people remember — the rival,
# the bad loss, the upset, the losing streak. The AD's "pulse" sets how loud
# one Saturday is, and a coach's traits can make it louder or quieter.

def start_season_seats(league):
    """Week 1: every seat starts where last season's verdict left it."""
    for team in league.teams:
        c = team.coach
        if c is None:
            continue
        c.seat_start = c.seat
        c.seat_events = []
        c.seat_prev = getattr(c, "seat_last", c.seat)   # so August's moves still show on the dashboard
        c.__dict__.setdefault("seat_last", c.seat)


def _seat_events(league, g, team):
    """What people will remember about this game, as (heat, why) pairs."""
    opp = g.opponent_of(team)
    won = g.winner is team
    ad = AD_STYLES[team.ad["style"]][2]
    out = []
    mine, theirs = g.score_for(team), g.score_for(opp)
    ranks = getattr(g, "ranks", {})
    my_rank, opp_rank = ranks.get(team), ranks.get(opp)
    rw = ad.get("rival", 1.0)
    if PRIMARY_RIVAL.get(team.school) == opp.school:
        out.append((-4 * rw, f"beat {opp.school}") if won else (5 * rw, f"lost to {opp.school}"))
    if not won:
        if getattr(opp, "fcs", False):
            out.append((10, f"lost to FCS {opp.school}"))
        elif (team.conference in POWER or team.school == world.FLAGSHIP_INDEPENDENT) and \
                opp.conference not in POWER and opp.school != world.FLAGSHIP_INDEPENDENT:
            out.append((4, f"lost to Group of Five {opp.school}"))
        if my_rank and not opp_rank:
            out.append((3, f"upset by unranked {opp.school}"))
        if theirs - mine >= 28 and not (opp_rank and opp_rank <= 10):
            out.append((3, f"blown out by {opp.school}, {theirs}-{mine}"))
        streak = 0
        for past in reversed([x for x in league.team_games(team) if x.played]):
            if past.winner is team:
                break
            streak += 1
        if streak in (3, 5, 7):
            out.append((3, f"{streak}-game losing streak"))
    else:
        if opp_rank:
            big = 1.4 if ad.get("hire") == "splash" or team.ad["style"] == "big_game" else 1.0
            road = 1.3 if g.away is team and not g.neutral else 1.0
            out.append((-3 * big * road, f"beat No. {opp_rank} {opp.school}"))
        if g.game_type in ("Bowl", "NP First Round", "NP Quarterfinal", "NP Semifinal",
                           "National Championship"):
            out.append((-3, f"won the {g.display_name if getattr(g, 'display_name', None) else g.bowl_name}"))
    return out


def live_seat(league, team, ovrs=None):
    """Where the seat is right now."""
    from traits import mod as trait_mod
    c = team.coach
    base = getattr(c, "seat_start", c.seat)
    ad = AD_STYLES[team.ad["style"]][2]
    games = team.wins + team.losses
    swing = 0.0
    if games >= 2:
        xw, n = expectation(league, team, c, ovrs)
        swing -= (team.wins - xw) * 6.5 * ad["heat"]
    swing += sum(d for _, d, _ in getattr(c, "seat_events", []))
    swing *= ad.get("pulse", 1.0)
    import ad_trust
    swing *= ad_trust.heat_factor(c, team, swing)     # your AD's trust in you (Career mode)
    import skills
    if skills.has(c, "teflon") and swing > 0:
        swing *= 0.8                                  # Teflon (coaching tree)
    if skills.has(c, "lightning_rod"):
        swing *= 1.25                                 # Lightning Rod (coaching tree): both ways
    if swing > 0:
        import difficulty
        swing *= difficulty.heat(c)                   # your difficulty (Career mode)
        swing *= trait_mod(c, "heat")
        tenure = league.year - (c.hired_year or league.year) + 1
        if tenure < FIRST_JUDGED.get(team.ad["style"], 3):
            swing *= 0.4 if tenure <= 1 else 0.6      # the same patience the verdict gives a new coach
    heat = base + swing
    # The top and bottom of the scale are hard to reach: once the seat is on fire
    # (or ice cold) it takes a lot more to move it further. Only the movement is
    # damped — a seat that started at 9 doesn't drift back up to 12 on its own.
    top, bottom = max(80, base), min(15, base)
    if heat > top:
        heat = top + (heat - top) * 0.45
    elif heat < bottom:
        heat = bottom - (bottom - heat) * 0.45
    if league.year - (c.hired_year or league.year) + 1 <= 1:
        heat = min(heat, 45)                          # nobody's getting fired in year one
    return int(max(0, min(100, round(heat))))


def weekly_seats(league, games):
    """After every week's games: log what happened, then move every seat."""
    for g in games:
        if not g.played:
            continue
        for team in (g.home, g.away):
            if getattr(team, "fcs", False) or team.coach is None:
                continue
            c = team.coach
            events = c.__dict__.setdefault("seat_events", [])
            for heat, why in _seat_events(league, g, team):
                events.append((league.week, heat, why))
    ovrs = league_ovrs(league)
    for team in league.teams:
        c = team.coach
        if c is None:
            continue
        if is_interim(c):
            continue
        c.__dict__.setdefault("seat_start", c.seat)
        c.seat_prev = getattr(c, "seat_last", c.seat)   # last week's reading, so in-week moves (a presser,
        c.seat = live_seat(league, team, ovrs)          # an inbox answer) count in the dashboard's ▲/▼
        c.seat_last = c.seat
    midseason_firings(league)


def seat_word(coach, weeks=2, league=None):
    """The most recent thing people are saying about his seat, if anything."""
    events = getattr(coach, "seat_events", [])
    if not events:
        return None
    last_week = events[-1][0]
    recent = [e for e in events if e[0] >= last_week - weeks + 1]
    return max(recent, key=lambda e: abs(e[1]))[2] if recent else None


def fire_line(team):
    """The seat heat that gets a coach fired at this school."""
    ad = AD_STYLES[team.ad["style"]][2]
    import ad_market
    return ad["fire_at"] - (team.ratings["athletic_director"] - 70) * 0.1 - (6 if team.ad.get("inherited") else 0) \
        + ad_market.fire_shift(team)


def min_tenure(team):
    style = team.ad["style"]
    return FIRST_JUDGED[style] - (1 if style in ("win_now", "booster") else 0)


def is_interim(coach):
    return bool(getattr(coach, "interim", None))


def human(coach):
    """A coach a person runs: yours in Coach Career, or a Discord member's in Commissioner Mode.
    Other schools can't hire him away, and he doesn't retire on the game's say-so."""
    return getattr(coach, "is_user", False) or bool(getattr(coach, "commish_member", None))


def upgrade_margin(league, team, coach):
    """Before firing a borderline coach an AD looks at who he could actually
    hire. How much better is the best realistic candidate than what he has?"""
    import staff
    rng = random.Random(f"market:{team.school}:{league.year}")
    pool = [c for c in league.coach_pool if c.status == "unemployed" and not human(c)]
    sitting = [t.coach for t in league.teams if t.coach is not None and t is not team and not is_interim(t.coach)
               and t.prestige < team.prestige - 3 and t.coach.history and not human(t.coach)]
    cands = pool + sitting + staff.head_coach_candidates(league, team)
    if not cands:
        return 0.0
    best = max(candidate_score(team, c, league, rng, sitting=c.team is not None) for c in cands)
    return best - candidate_score(team, coach, league, rng)


# ═══ Firing during the season ═══════════════════════════════════════════════
# Most ADs wait for the season to end. The impatient ones don't: once a season
# is clearly gone and the seat is past the line, they make the change in
# October and hand the team to a coordinator for the rest of the year.

MIDSEASON_TEMPER = {"politician": 1.1, "win_now": 1.0, "booster": 1.0, "brand": 0.8, "big_game": 0.7,
                    "conference": 0.5, "turnaround": 0.4, "traditionalist": 0.4, "recruiting": 0.25,
                    "analytics": 0.2, "patient": 0.15, "budget": 0.1}
MIDSEASON_WEEKS = (5, 11)


def midseason_firings(league):
    if not (MIDSEASON_WEEKS[0] <= league.week <= MIDSEASON_WEEKS[1]) or not hasattr(league, "carousel"):
        return
    import finance
    rng = random.Random(f"midseason:{league.seed}:{league.year}:{league.week}")
    for team in league.teams:
        c = team.coach
        if c is None or getattr(team, "fcs", False) or getattr(c, "is_user", False) or is_interim(c):
            continue
        import ad_mode
        if ad_mode.is_mine(league, team):
            continue                                    # that call is yours
        games = team.wins + team.losses
        if games < 5:
            continue
        tenure = league.year - (c.hired_year or league.year) + 1
        if tenure < max(2, min_tenure(team)) or any(h.get("title") for h in c.history[-4:]):
            continue
        line = fire_line(team)
        if c.seat < line - 2 or (team.wins / games > 0.4 and c.seat < 96):
            continue
        share = finance.owed(c, league) / max(1, finance.budget(team))
        if share >= (0.12 if AD_STYLES[team.ad["style"]][2].get("buyout") else 0.35):
            continue                                    # a mid-season firing on a huge buyout is a hard sell
        odds = 0.22 * MIDSEASON_TEMPER.get(team.ad["style"], 0.4) * (1 + max(0, c.seat - line) / 12)
        if rng.random() < odds:
            fire_midseason(league, team, rng)


def fire_midseason(league, team, rng):
    import staff
    c = team.coach
    s = season_line(league, team)
    xw, n = expectation(league, team, c)
    s["xw"], s["exp"], s["partial"] = round(xw, 2), round(xw / n, 3) if n else 0.5, True
    s["seat"] = c.seat
    c.history.append(s)                                  # the games he coached count on his record
    w, l = team.wins, team.losses
    text = (f"{team.school} fires {c.name} in the middle of the season ({w}-{l}) — "
            f"{'the season was gone' if w <= l else 'the AD had seen enough'}")
    news = league.__dict__.setdefault("midseason_news", {}).setdefault(league.year, [])
    vacate(league, team, "fired")
    c._last_exit["note"] = f"fired {w}-{l} into the season"
    # The interim: the coordinator with the better résumé (or a staff analyst if there's nobody).
    cands = [x for x in (getattr(team, "oc", None), getattr(team, "dc", None)) if x is not None]
    if cands:
        interim = max(cands, key=lambda x: (staff.resume_score(x), x.overall))
    else:
        interim = _new_candidate(league, rng, "coord")
        interim.status = "employed"
    interim.interim = team.school
    interim._pre_interim = {"hired_year": getattr(interim, "hired_year", None)}
    interim.__dict__.setdefault("history", [])
    interim.__dict__.setdefault("seat_log", [])
    interim.hired_year = league.year
    interim.seat = interim.seat_start = interim.seat_prev = 40
    interim.seat_events, interim.hot_years = [], 0
    team.coach = interim
    interim.team = team
    team.ratings["coach"] = interim.overall
    team.interim_split = (w, l)
    news.append(("fired", text))
    news.append(("hired", f"{team.school} names {interim.name} interim head coach"))
    league.carousel.setdefault(league.year, []).extend(news[-2:])


def end_interim(league, team):
    """Season's over: the interim goes back to his old job (he's a candidate for the real one)."""
    c = team.coach
    w0, l0 = getattr(team, "interim_split", (0, 0))
    c.interim_record = (team.wins - w0, team.losses - l0)
    c.interim_at, c.interim_year = team.school, league.year
    c.hired_year = c._pre_interim.get("hired_year")
    c.interim = None
    team.coach = None
    team.coach_changed = True
    team.interim_split = None


# ═══ Growth, age, retirement ════════════════════════════════════════════════

def progress(coach, perf_bonus, rng):
    """Coaches get a little better every year, a lot better when they win,
    and never past their ceiling. After 62 they start to slip."""
    gain = 0.2 + perf_bonus * 0.6
    if coach.overall >= 85:
        gain -= 0.5                               # the last steps to greatness are the hardest
    fade = longevity(coach)
    if coach.age >= fade:                          # the game passes everybody by eventually — some sooner
        gain -= rng.uniform(0.3, 1.3) * getattr(coach, "fade_rate", 1.0) * (1 + (coach.age - fade) / 7)
    step = round(gain + rng.gauss(0, 0.9))
    old = coach.overall
    coach.overall = int(max(35, min(coach.ceiling, coach.overall + step)))
    fit_ceiling(coach)
    real = coach.overall - old
    for k in coach.ratings:
        bump = real + round(rng.gauss(0, 0.8))
        if k == "recruiting" and perf_bonus > 1:
            bump += 1
        coach.ratings[k] = int(max(25, min(99, coach.ratings[k] + bump)))
    if real:                                       # his sideline grows (or fades) with him
        import coach_profile
        prof = coach_profile.ensure_sideline(coach)
        for k in prof:
            prof[k] = int(max(25, min(97, prof[k] + real)))
    if coach.team is not None and getattr(coach, "role", "HC") == "HC":
        coach.team.ratings["coach"] = coach.overall
    return real


def retire_odds(coach, fired=False, title=False, tenure=0):
    """Every coach has an age he has in mind. The odds climb as he nears it,
    faster after a firing, and a title near the end is a natural goodbye."""
    target = getattr(coach, "retire_age", 67)
    gap = coach.age - target
    if gap < -8:
        base = 0.001
    elif gap < -3:
        base = 0.012
    elif gap < 0:
        base = 0.05
    elif gap < 3:
        base = 0.22
    else:
        base = 0.45
    if fired:
        base = base * 2.5 + (0.15 if coach.age >= 60 else 0)
    if title and gap >= -3:
        base += 0.25                                 # go out on top
    if tenure >= 15 and gap >= -2:
        base += 0.06                                 # the long goodbye
    return min(0.92, base)

HS_SUFFIX = ("Central", "North", "South", "East", "West", "Memorial", "Christian", "Catholic", "Prep")
ROLES = ("offensive coordinator", "defensive coordinator", "assistant head coach")


def _new_candidate(league, rng, kind):
    from league import make_coach
    from models import Team
    from traits import assign_coach_traits
    import staff
    name = full_name(rng, avoid=staff.coach_surnames(league))
    if kind == "hs":
        ovr, age = rng.randint(46, 62), rng.randint(32, 48)
        state = rng.choice(list(STATES))
        origin = f"{rng.choice(LAST_NAMES)} {rng.choice(HS_SUFFIX)} High School ({state})"
        ceiling = roll_ceiling(ovr, rng, room=12)
    elif kind == "coord":
        ovr, age = rng.randint(56, 74), rng.randint(33, 55)
        src = rng.choice(league.teams)
        origin = f"{src.school} {rng.choice(ROLES)}"
        ceiling = roll_ceiling(ovr, rng, room=8)
    else:  # FCS head coach
        ovr, age = rng.randint(55, 72), rng.randint(38, 60)
        src = rng.choice(league.fcs_teams) if league.fcs_teams else None
        origin = f"{src.school} head coach (FCS)" if src else "FCS head coach"
        ceiling = roll_ceiling(ovr, rng, room=6)
    shell = Team("—", "—", "—", 0, "—", None, "", {k: 60 for k in Team.RATING_KEYS})
    shell.ratings["coach"] = ovr
    coach = make_coach(name, shell)
    coach.team = None
    assign_coach_traits(coach, rng)
    init_coach(coach, league.year, origin=origin)
    coach.age, coach.ceiling, coach.status = age, max(ceiling, ovr + 2), "unemployed"
    fit_ceiling(coach)
    coach.hired_year = None
    coach.kind = kind
    return coach


def refresh_pool(league, rng, first=False):
    """Every offseason: old candidates drift away, a fresh crop appears."""
    keep = []
    for c in league.coach_pool:
        c.pool_years += 1
        if c.age >= 64 and rng.random() < 0.35:
            c.status = "retired"
            league.retired_coaches.append(c)
            continue
        if c.pool_years >= 3 and getattr(c, "kind", "fired") != "fired":
            continue                         # took another job outside college football
        if c.status == "retired":
            continue
        keep.append(c)
    league.coach_pool = keep
    # Real coordinators are the candidates now (staff.py). High school coaches only
    # come in as Group of Five coordinators; FCS head coaches still get calls.
    for kind, n in (("fcs", 8),):
        for _ in range(n):
            league.coach_pool.append(_new_candidate(league, rng, kind))


# ═══ Hiring ═════════════════════════════════════════════════════════════════


# ═══ Hiring ═════════════════════════════════════════════════════════════════

def region_of(team):
    return STATES.get(getattr(team, "home_state", None), ("", ""))[1]


def home_region(coach):
    """The part of the country a Homebody won't leave: where he's settled."""
    reg = getattr(coach, "home_region", None)
    if reg:
        return reg
    if coach.team is not None and region_of(coach.team):
        return region_of(coach.team)
    from recruiting_data import TEAM_STATES
    st = TEAM_STATES.get(getattr(coach, "alma_mater", None) or "")
    return STATES.get(st, ("", ""))[1] or None


def personality_blurb(coach):
    """'Won't leave the Midwest' — the personality line, with the specifics filled in."""
    name, blurb, _ = PERSONALITIES[coach.personality]
    if coach.personality == "homebody":
        reg = home_region(coach)
        if reg:
            states = sorted(k for k, v in STATES.items() if v[1] == reg)
            return f"Won't leave the {reg} ({', '.join(states[:9])}{'…' if len(states) > 9 else ''})"
    return blurb


def settle_homebody(coach, rng=None):
    """A Homebody's whole life is in one region: his job, where he played, where he recruits."""
    if getattr(coach, "personality", None) != "homebody":
        return
    from recruiting_data import TEAM_STATES
    from teams_data import TEAMS
    reg = region_of(coach.team) if coach.team is not None else home_region(coach)
    if not reg:
        return
    coach.home_region = reg
    alma = getattr(coach, "alma_mater", None)
    if coach.name not in KNOWN_ALMA and not _is_real_hc(coach) and STATES.get(TEAM_STATES.get(alma or ""), ("", ""))[1] != reg:
        local = sorted(row[0] for row in TEAMS if STATES.get(TEAM_STATES.get(row[0], ""), ("", ""))[1] == reg)
        if local:
            coach.alma_mater = (rng or _seeded(coach, "alma-home")).choice(local)
    if hasattr(coach, "recruit_region"):
        coach.recruit_region = reg


def track_record(coach, league):
    """Results against expectations at his jobs, last four seasons, shrunk
    toward zero when there isn't much to go on."""
    recent = coach.history[-4:]
    if not recent:
        return 0.0
    tot = 0.0
    for s in recent:
        g = s["w"] + s["l"]
        tot += (s["w"] / g if g else 0.5) - s.get("exp", 0.5)
        tot += 0.06 * s.get("cfp", False) + 0.12 * s.get("title", False) + 0.03 * s.get("conf_champ", False)
    return (tot / len(recent)) * (len(recent) / (len(recent) + 1.5))


def level_of(coach, league):
    """The biggest stage a coach has proven himself on."""
    levels = [league_team_prestige(league, s["school"]) for s in coach.history]
    levels += [league_team_prestige(league, s["school"]) - 12 for s in getattr(coach, "coord_history", [])]
    if levels:
        return max(levels)
    if getattr(coach, "is_user", False) and getattr(coach, "prestige_start", None):
        import coach_prestige
        return coach_prestige.level(coach)["level"]       # before your first season, your name is your level
    kind = getattr(coach, "kind", "")
    return {"hs": 35, "coord": 62, "fcs": 45}.get(kind, 55)


def candidate_score(team, coach, league, rng, sitting=False):
    """How an AD rates a candidate — from his résumé only. Nobody hiring sees a rating
    or a ceiling: results against expectations, the level he did it at, rings, classes,
    a coordinator's units, and the interview. The AD's eye, style and character tilt it."""
    import ad_market
    import resume

    style = AD_STYLES[team.ad["style"]][2]["hire"]
    track = track_record(coach, league)
    step = team.prestige - level_of(coach, league)           # how big a jump this would be
    seen = resume.read(team, coach, league, rng)              # his read of the paper (and the interview)
    rec = resume.recruit_rep(coach)
    score = seen * 1.05 + rec * 0.15 + track * 60
    score -= max(0, step - 12) * (1.4 if team.prestige >= 78 else 0.7)
    if coach.history and track < -0.05:
        score -= 12                                          # he lost where he was
    if coach.team is not None and region_of(coach.team) == region_of(team):
        score += 3                                            # knows the recruiting ground
    if style == "proven":
        score += min(6, len(coach.history)) * 1.5 + track * 40
        if not coach.history:
            score -= 10
    elif style == "rising":
        score += max(0, 46 - coach.age) * 0.5 + resume.trend(coach) * 6 - max(0, coach.age - 46) * 0.8
    elif style == "splash":
        score += (6 if sitting else 0) + max(0, seen - 80) * 0.6
    elif style == "fit":
        if coach.team is not None and region_of(coach.team) == region_of(team):
            score += 5                                        # a coach who fits the place
    elif style == "recruiter":
        score += (rec - 60) * 0.5                             # a closer: look at his classes
    score += second_chance_bonus(team, coach, league, track)
    import staff
    score += staff.hc_bonus(team, coach, league)
    score += _fit_for_program(team, coach, league, track)
    if AD_STYLES[team.ad["style"]][2].get("buyout") and sitting:
        score -= 8                                            # somebody else's buyout is still a buyout
    if getattr(coach, "alma_mater", None) == team.school:
        score += 4                                            # one of their own
    score -= max(0, coach.age - 60) * 2.5
    score += ad_market.taste(team, coach, league)            # who this AD is
    return score


def _fit_for_program(team, coach, league, track):
    """What this program needs right now, and whether this coach has done it
    at this level: a talent-poor roster wants a recruiter, a talented one that
    underachieved wants a better coach on Saturdays, a Power job wants somebody
    who has already worked on a Power stage."""
    bonus = 0.0
    ovrs = getattr(league, "_ovrs_cache", None)
    if ovrs is None or ovrs[0] != league.year:
        ovrs = league._ovrs_cache = (league.year, league_ovrs(league))
    vals = ovrs[1]
    mine = _ovr(league, team)
    talent = sum(1 for v in vals if v < mine) / max(1, len(vals) - 1)
    stature = (team.prestige - 43) / 51
    if stature - talent >= 0.15:
        import resume
        bonus += (resume.recruit_rep(coach) - 62) * 0.35            # rebuild the roster first: who has signed classes?
    if talent - stature >= 0.1:
        import resume
        bonus += (resume.reputation(coach, league) - 72) * 0.25      # the talent's there; coach it up
    power = team.conference in POWER or team.school == world.FLAGSHIP_INDEPENDENT
    if coach.history:
        lvl = level_of(coach, league)
        if lvl >= team.prestige - 15 and track >= 0.05:
            bonus += 6                                               # he's won a job like this one
    elif getattr(coach, "role", "HC") in ("OC", "DC") and coach.team is not None:
        coach_power = coach.team.conference in POWER or coach.team.school == world.FLAGSHIP_INDEPENDENT
        if power and coach_power:
            bonus += 3
        elif power and not coach_power:
            bonus -= 5                                               # never worked the Power level
    if getattr(coach, "interim_at", None) == team.school and getattr(coach, "interim_year", None) == league.year:
        w, l = getattr(coach, "interim_record", (0, 0))
        bonus += 3 + ((w / (w + l)) - 0.5) * 20 if w + l else 3     # the players played for him
    return bonus


def is_second_chance(team, coach, league):
    """A coach out of work who has already run a clearly bigger program."""
    return (coach.team is None and bool(coach.history)
            and level_of(coach, league) - team.prestige >= SECOND_CHANCE_DROP)


def second_chance_bonus(team, coach, league, track):
    """Smaller programs love a big name who got fired somewhere bigger: he's
    recruited at that level, he's run a real program, the old school is still
    paying him, and the fired part was about expectations there, not here."""
    if not is_second_chance(team, coach, league):
        return 0.0
    drop = level_of(coach, league) - team.prestige
    bonus = min(14.0, drop * 0.45)                           # a name from a bigger stage
    if drop > 25:
        bonus -= (drop - 25) * 0.6                           # ...but he'll be gone the first time a big job calls
    if any(h.get("cfp") or h.get("conf_champ") or h.get("title") for h in coach.history):
        bonus += 6                                            # he's won big before
    if -0.15 < track < -0.05:
        bonus += 8                                            # most of the "lost where he was" penalty goes away
    elif track <= -0.15:
        bonus -= 6                                            # he didn't just miss expectations — he sank
    ad = AD_STYLES[team.ad["style"]][2]
    if ad["hire"] == "splash" or ad.get("brand"):
        bonus += 5                                            # name recognition sells tickets
    if ad.get("buyout"):
        bonus += 3                                            # and his old school is still paying him
    if ad["hire"] == "rising":
        bonus -= 4                                            # some ADs want the next guy, not the last one
    return bonus


def will_accept(coach, team, league, rng, offer=None):
    import finance
    ratio = finance.money_ratio(league, coach, offer, "HC") if offer is not None else 1.0
    if getattr(coach, "role", "HC") in ("OC", "DC"):
        import staff
        if ratio < 0.8:
            return False                             # a head coaching job, but not for that money
        return staff.will_take_head_job(coach, team, league, rng)
    traits = PERSONALITIES.get(coach.personality, PERSONALITIES["builder"])[2]
    going_home = traits.get("alma") and team.school == getattr(coach, "alma_mater", None)
    if coach.status == "unemployed":
        if ratio < 0.55 and not going_home:
            return False                             # he'd rather sit out than work for that
        drop = level_of(coach, league) - team.prestige
        if coach.history and drop > 25 and not going_home and coach.age < 64:
            # A coach just fired from a big job takes an analyst or coordinator
            # job and waits for a better call before he'd go that far down.
            if rng.random() < (0.9 if getattr(coach, "pool_years", 0) == 0 else 0.55):
                return False
        best = level_of(coach, league) if coach.history else 0
        # Fired head coaches will step down a long way to get back on a sideline —
        # unless they're near the end, when the phone call has to be worth it.
        floor = (38 if coach.age < 60 else 26) if coach.history else 22
        return going_home or team.prestige >= best - floor or coach.pool_years >= 1
    if going_home:
        return rng.random() < 0.9                    # the call he's waited for his whole career
    cur = coach.team
    if traits.get("elite") and team.prestige < traits["elite"]:
        return False
    tenure = league.year - (coach.hired_year or league.year) + 1
    if tenure < traits["settle"] and coach.seat < 65:
        return False
    if ratio < 0.85:
        return False                                 # nobody moves for less than he's worth
    jump = team.prestige - cur.prestige
    need = traits["min_jump"] - (10 if coach.seat >= 65 else 0)
    need -= clamp_money(ratio) * 12 * finance.money_weight(coach)   # a big enough check shrinks the step up
    if traits.get("seat_flight") and coach.seat >= 50:
        need -= 10                                   # gone before the AD can make the call
    down = team.win_pct if team.wins + team.losses else (getattr(team, "last_win_pct", None) or 0.5)
    if traits.get("fixer") and down < 0.45:
        need -= 8                                    # a program that's down is his favorite kind
    if jump < need:
        return False
    if traits.get("regional") and region_of(team) != region_of(cur):
        return False
    odds = 0.35 * traits["leave"] + jump / 60
    if traits.get("seat_flight") and coach.seat >= 50:
        odds *= 1.5
    if coach.age >= 62:
        odds *= 0.35
    return rng.random() < min(0.95, odds)


def clamp_money(ratio):
    """How far above (or below) his asking price an offer is, capped both ways."""
    return max(-0.3, min(0.8, ratio - 1.0))


def league_team_prestige(league, school):
    return next((t.prestige for t in league.teams if t.school == school), 60)


def _news(league, kind, text):
    league.carousel.setdefault(league.year, []).append((kind, text))


def _record(c):
    w = sum(s["w"] for s in c.history)
    l = sum(s["l"] for s in c.history)
    return f"{w}-{l}"


def _honors(c):
    t = sum(s["title"] for s in c.history)
    cf = sum(s["cfp"] for s in c.history)
    bits = []
    if t:
        bits.append(f"{t} national title{'s' if t > 1 else ''}")
    if cf:
        bits.append(f"{cf} NP trip{'s' if cf > 1 else ''}")
    return (", " + ", ".join(bits)) if bits else ""


# ─── The carousel ledger ─────────────────────────────────────────────────────
# Every departure and hire is logged with the coach's numbers at that moment,
# so the carousel report can show exactly what each program walked away from
# and what it bought. Records count seasons played in this world (2026 on).

def _book(coach, school=None):
    """A coach's splits at one school (or across his career if school is None)."""
    seasons = [s for s in coach.history if school is None or s["school"] == school]
    out = splits(seasons)
    out["seasons"] = len(seasons)
    return out


def _move(league, **kw):
    kw["week"] = league.week
    league.__dict__.setdefault("carousel_moves", {}).setdefault(league.year, []).append(kw)
    return kw


def carousel_moves(league, year):
    return getattr(league, "carousel_moves", {}).get(year, [])


def _rep(c, league):
    import resume
    return resume.reputation(c, league)


def longevity(coach):
    """When the game starts to pass him by, and how fast. Hidden. Most coaches start
    slipping in their early sixties; some are done at 56; a few are still great at 72."""
    if "fade_age" not in coach.__dict__:
        r = random.Random(f"fade:{coach.name}")
        x = r.random()
        if x < 0.10:
            fade = r.gauss(72, 2.5)                  # ageless
        elif x < 0.27:
            fade = r.gauss(56, 2)                    # time catches up early
        else:
            fade = r.gauss(62.5, 2.5)
        coach.fade_age = round(max(52, min(78, fade)))
        coach.fade_rate = round(r.uniform(0.6, 1.6), 2)
        if coach.fade_age >= 69 and hasattr(coach, "retire_age"):
            coach.retire_age = min(82, coach.retire_age + 5)    # still loves it, still good at it
    return coach.fade_age


def _pro_pull(c):
    """How hard the Pro League chases a college coach: the ones who just won it all get the calls."""
    recent = c.history[-3:]
    titles = sum(1 for s in recent if s.get("title"))
    cfp = sum(1 for s in recent if s.get("cfp"))
    return min(0.16, 0.012 + 0.05 * titles + 0.012 * cfp + (0.015 if c.overall >= 92 else 0.0))


def vacate(league, team, why):
    coach = team.coach
    team.coach = None
    team.coach_changed = True
    if coach is not None:
        import finance
        finance.release(league, team, coach, fired=why == "fired")   # fired with years left: the school keeps paying
        kind = "nfl" if why == "retired" and getattr(coach, "origin", "") == "left for the Pro League" else why
        coach._last_exit = _move(
            league, side="out", kind=kind, school=team.school, conf=team.conference, prestige=team.prestige,
            coach=coach.name, age=coach.age, user=getattr(coach, "is_user", False),
            tenure=len([s for s in coach.history if s["school"] == team.school]),
            at=_book(coach, team.school), career=_book(coach), dest=None, note="")
        if getattr(coach, "is_user", False) and why == "fired":
            import hotseat
            with hotseat.acting_as_coach(league, coach):
                league.__dict__.setdefault("career_log", []).append((league.year, f"Fired by {team.school}."))
                league.user_team = None
        coach.team = None
        coach.status = "unemployed"
        coach.pool_years = 0
        coach.kind = "fired"
        if why == "fired":
            league.coach_pool.append(coach)


def hire(league, team, coach, how, offer=None):
    import ad_market
    ad_market.note_hire(league, team, coach)
    import skills
    skills.new_job(coach)                              # your coach only: a free reset of the coaching tree
    import finance
    if offer is None:
        offer = finance.hc_offer(league, team, coach)
    deal = f" — {finance.terms(offer)}"
    was = coach.team
    last = coach.history[-1] if coach.history else None
    coord_role = getattr(coach, "role", "HC") if getattr(coach, "role", "HC") in ("OC", "DC") else None
    if coord_role:
        import staff
        book = getattr(coach, "coord_history", [])
        _move(league, side="in", kind="hired", school=team.school, conf=team.conference, prestige=team.prestige,
              coach=coach.name, age=coach.age, user=False, how="coordinator",
              source=f"{was.school} {staff.ROLE_NAMES[coord_role]}", from_school=None, from_conf=None,
              second_chance=False, prev=None, career=_book(coach), coord_role=coord_role,
              coord_book=book[-3:])
        staff.leave_for_head_job(league, was, coach, team)
        _news(league, "hired", f"{team.school} hires {coach.name}, {was.school}'s {staff.ROLE_NAMES[coord_role]}{deal}")
        coach.origin = f"{was.school} {staff.ROLE_NAMES[coord_role]}"
        coach.role = "HC"
        coach.team = None
        _seat_the_coach(league, team, coach, offer)
        return
    if was is not None:
        src, src_school, src_conf = f"{was.school} head coach", was.school, was.conference
    elif last is not None:
        src, src_school, src_conf = f"out of coaching — last at {last['school']} ({last['year']})", \
            last["school"], last.get("conf", "")
    else:
        src, src_school, src_conf = getattr(coach, "origin", "") or "first FBS head coaching job", None, None
    fired_here = next((m for m in carousel_moves(league, league.year)
                       if m["side"] == "out" and m["coach"] == coach.name and m["kind"] == "fired"), None)
    if fired_here is not None and was is None:
        src = f"fired by {fired_here['school']} this offseason"
    _move(league, side="in", kind="hired", school=team.school, conf=team.conference, prestige=team.prestige,
          coach=coach.name, age=coach.age, user=getattr(coach, "is_user", False), how=how,
          source=src, from_school=src_school, from_conf=src_conf,
          second_chance=is_second_chance(team, coach, league) if was is None else False,
          prev=_book(coach, src_school) if src_school else None, career=_book(coach))
    if was is not None:
        fee = finance.charge_release(league, was, team, coach)      # leaving early isn't free
        vacate(league, was, "left")
        coach._last_exit["dest"] = team.school
        paid = f"; {team.school} pays {was.school} a {finance.money(fee)} release fee" if fee else ""
        _news(league, "poached", f"{coach.name} leaves {was.school} for {team.school}{deal}{paid}")
    else:
        if coach in league.coach_pool:
            league.coach_pool.remove(coach)
        src = coach.origin if not coach.history else f"formerly {coach.history[-1]['school']}, {_record(coach)}"
        _news(league, "hired", f"{team.school} hires {coach.name} ({src}){deal}")
    _seat_the_coach(league, team, coach, offer)


def _seat_the_coach(league, team, coach, offer=None):
    import finance
    coach.role = "HC"
    finance.sign(league, team, coach, offer or finance.hc_offer(league, team, coach), start=league.year + 1)
    team.set_coach(coach)
    coach.status = "employed"
    coach.hired_year = league.year + 1
    coach.seat = int(max(10, min(30, 20 + (random.Random(coach.name).random() - 0.5) * 10)))
    coach.seat += int((offer or {}).get("pressure", 0))          # a hard negotiation is remembered
    coach.hot_years = 0
    team.ratings["coach"] = coach.overall
    roll_fit(coach, team, league)                     # does he fit the place? Saturdays will tell
    team.coach_changed = True
    team.coach_log.append((league.year + 1, coach.name))
    team.ad["inherited"] = False
    import ad_mode
    if ad_mode.is_mine(league, team):
        team.goals_set = league.year + 1               # your goals stand; the new coach is measured from year one
        return
    review_goals(team, league, random.Random(f"{team.school}{league.year}"), coach)


def _ai_fill_one(league, team, rng):
    """Fill one opening the way an AI AD would (used when you hand your search to a firm)."""
    team.__dict__["_force_ai_fill"] = True
    try:
        fill_openings(league, rng, only=team)
    finally:
        team.__dict__.pop("_force_ai_fill", None)


def _auto_offer(league, offers, fired_now):
    """While seasons are simming: stay put unless you're out of work (or a clearly bigger
    job calls), then take the best offer."""
    me = league.user_coach
    if not offers:
        return None
    # Offers come as (team, kind) pairs — kind "poach" means they'd push their own coach out.
    pairs = [o if isinstance(o, tuple) else (o, "open") for o in offers]
    best, kind = max(pairs, key=lambda tk: tk[0].prestige)
    if me.team is None or fired_now or best.prestige >= me.team.prestige + 10:
        if kind == "poach" and best.coach is not None and best.coach is not me:
            _news(league, "fired", f"{best.school} moves on from {best.coach.name} to hire {me.name}")
            vacate(league, best, "fired")
        return best
    return None


def off_market(coach, league):
    """A coach nobody else can hire away this winter: he just took a new job, or just signed to stay."""
    if coach is None:
        return True
    return getattr(coach, "_retained", None) == league.year or coach.hired_year == league.year + 1 \
        or getattr(coach, "interim", None)


def fill_openings(league, rng, only=None):
    import ad_mode
    mine = ad_mode.my_team(league)
    for _ in range(400):
        reserved = set(getattr(league, "_reserved_user_jobs", set()) or set())
        if getattr(league, "mode", None) == "online":
            for private in ((league.__dict__.get("online") or {}).get("career") or {}).values():
                reserved.update(private.get("_reserved_user_jobs", set()) or set())
        open_jobs = sorted((t for t in league.teams if t.coach is None
                            and t.school not in reserved
                            and (t is not mine or getattr(t, "_force_ai_fill", False))
                            and (only is None or t is only)), key=lambda t: -t.prestige)
        if not open_jobs:
            return
        team = open_jobs[0]
        sitting = [t.coach for t in league.teams
                   if t.coach is not None and t.prestige < team.prestige - 3 and t.coach.history
                   and not human(t.coach)
                   and not off_market(t.coach, league)]      # he just signed to stay, or just got here
        pool = [c for c in league.coach_pool if c.status == "unemployed" and not human(c)
                and getattr(c, "_last_exit", {}).get("school") != team.school]   # nobody rehires the coach he just fired
        import staff
        coords = staff.head_coach_candidates(league, team)
        ranked = sorted(((candidate_score(team, c, league, rng, sitting=c.team is not None and c in sitting), c)
                         for c in pool + sitting + coords), key=lambda x: -x[0])
        hired = False
        import finance
        # A real search: bigger jobs interview more people, and nobody interviews
        # a coach the budget can't pay.
        import ad_market
        cap = finance.HC_CAP * finance.budget(team) * 1.1 * ad_market.pay_mult(team)
        ranked = [(sc, c) for sc, c in ranked if finance.asking(league, c, "HC") <= cap]
        # ...and a sitting coach's release fee has to fit the budget too.
        splash = AD_STYLES[team.ad["style"]][2]["hire"] == "splash"
        fee_cap = finance.budget(team) * (0.3 if splash else 0.15) * ad_market.pay_mult(team)
        ranked = [(sc, c) for sc, c in ranked
                  if c.team is None or getattr(c, "role", "HC") != "HC" or finance.release_fee(c, league) <= fee_cap]
        shortlist = 20 if team.prestige >= 80 else 14 if team.prestige >= 62 else 10
        import hc_search
        for _, c in ranked[:4]:
            hc_search.log(league, team, short=_who(c))
        for _, c in ranked[:shortlist]:
            offer = finance.hc_offer(league, team, c, rng)
            if will_accept(c, team, league, rng, offer):
                if c.team is not None and getattr(c, "role", "HC") == "HC" and \
                        (ad_mode.keep_coach_prompt(league, c, offer) if ad_mode.is_mine(league, c.team)
                         else finance.retention_counter(league, c, offer, rng)):
                    hc_search.log(league, team, matched=_who(c))
                    continue                             # his AD matched; on to the next name
                who = _who(c)
                hire(league, team, c, "pool" if c.team is None else "poach", offer)
                hc_search.log(league, team, hired=who)
                hired = True
                break
            elif any(c is x for _, x in ranked[:4]):
                why = ("wanted more than they'd pay" if finance.asking(league, c, "HC") > offer["salary"]
                       else "is staying put" if c.team is not None and getattr(c, "role", "HC") == "HC"
                       else "is waiting for a bigger job" if c.team is not None
                       else "turned it down")
                hc_search.log(league, team, no=(_who(c), why))
        if not hired:
            c = next((c for _, c in ranked if c.team is None), None) or \
                next((c for _, c in ranked if getattr(c, "role", "HC") in ("OC", "DC")), None) or \
                _new_candidate(league, rng, "fcs")
            who = _who(c)
            hire(league, team, c, "pool")
            import hc_search
            hc_search.log(league, team, hired=who + " (fallback)")


def _who(c):
    """'Name (OC, Georgia)' / 'Name (Boise State HC)' / 'Name (out of work)'."""
    role = getattr(c, "role", "HC")
    if c.team is not None:
        return f"{c.name} ({c.team.school} {role})"
    return f"{c.name} (out of work)" if c.history else f"{c.name} ({getattr(c, 'origin', 'new')})"


# ═══ The offseason ══════════════════════════════════════════════════════════

AD_TURNOVER = 0.07
SECOND_CHANCE_DROP = 8          # prestige gap that makes a fired coach a "second chance" hire


# Where head coaches should sit, by percentile (v48).
TARGET_HC = ((0.0, 50), (0.10, 57), (0.25, 63), (0.50, 70), (0.75, 77), (0.90, 83), (0.97, 89), (1.0, 94))


def _interp(q, table):
    for (q0, v0), (q1, v1) in zip(table, table[1:]):       # noqa: RUF007 — Python 3.8
        if q <= q1:
            return v0 + (v1 - v0) * ((q - q0) / max(1e-9, q1 - q0))
    return table[-1][1]


def rebalance_coaches(league, force=False, weight=1.0, threshold=76, reroll=True):
    """v48: in long-running worlds every coach had grown into the 90s. Put the head coaches
    back on a realistic curve (keeping the order: the best are still the best), move every
    coordinator and pool coach by the same mapping, and re-roll ceilings from the new tiers."""
    import staff
    hcs = [t.coach for t in league.teams if t.coach is not None and not getattr(t, "fcs", False)
           and not getattr(t.coach, "is_user", False)]
    if not hcs:
        return 0
    old = sorted(c.overall for c in hcs)
    med = old[len(old) // 2]
    if med <= threshold and not force:
        return 0                                    # this world is fine as it is
    n = len(old)

    def mapped(v):
        below = sum(1 for x in old if x < v)
        same = sum(1 for x in old if x == v)
        q = (below + same / 2) / n
        return round(_interp(q, TARGET_HC))
    rng = random.Random(f"rebalance:{league.seed}:{league.year}")
    seen = set()
    pools = hcs + staff.coordinators(league) + list(getattr(league, "staff_pool", [])) + list(getattr(league, "coach_pool", []))
    moved = 0
    import coach_profile
    for c in pools:
        if c is None or id(c) in seen or getattr(c, "is_user", False):
            continue
        seen.add(id(c))
        target = mapped(c.overall) if c in hcs else mapped(c.overall + 4) - 4
        if weight >= 1.0:
            target = min(c.overall, target)                   # the one-time fix only ever brings coaches down
        step = (target - c.overall) * weight
        new = int(round(c.overall + (min(step, 1.5) if step > 0 else step)))
        d = new - c.overall
        if d:
            c.overall = new
            for k in c.ratings:
                c.ratings[k] = int(max(25, min(99, c.ratings[k] + d)))
            prof = coach_profile.ensure_sideline(c)
            for k in prof:
                prof[k] = int(max(25, min(97, prof[k] + d)))
            moved += 1
        if reroll:
            c.ceiling = max(c.overall + 1, roll_ceiling(c.overall, rng, room=11 if getattr(c, "age", 50) <= 40 else 4))
        elif d:
            c.ceiling = max(c.overall + 1, getattr(c, "ceiling", c.overall + 1) + d)
        fit_ceiling(c)
    for t in league.teams:
        if t.coach is not None:
            t.ratings["coach"] = t.coach.overall
    return moved


def migrate(league):
    """Bring an older save up to date."""
    if not league.__dict__.get("_coach_v48"):
        league._coach_v48 = True
        rebalance_coaches(league, force=True, weight=0.0)          # every ceiling re-rolled from the new tiers...
        rebalance_coaches(league, reroll=False)                    # ...and a world full of 90s brought back to earth
    for team in league.teams:
        team.ad.setdefault("inherited", False)
        team.ad.setdefault("since", league.year - 5)
        if not hasattr(team, "goal_tier") or not all(hasattr(g, "applies") for g in team.goals):
            team.goal_tier = _tier(team)
            team.goals_set = league.year - 1
            assign_goals(team, league, random.Random(team.school))
    for c in all_coaches(league) + league.coach_pool:
        if not hasattr(c, "retire_age"):
            c.retire_age = int(max(58, min(78, random.Random(f"ret:{c.name}").gauss(66, 4))))
        c.__dict__.setdefault("hot_years", 0)
        if not getattr(c, "alma_mater", None):
            c.alma_mater = _alma_for(c)
    if not league.__dict__.get("_fit_rescaled"):          # v24: coach fit rolled at 1.8, now FIT_SD
        for c in all_coaches(league) + league.coach_pool:
            fit = c.__dict__.get("fit_with")
            if fit:
                for school in fit:
                    fit[school] = round(fit[school] * FIT_SD / 1.8, 2)
        league._fit_rescaled = True
    import staff
    staff.setup(league)
    import finance
    finance.ensure_all(league)
    import ad_market
    ad_market.ensure(league)
    for c in all_coaches(league) + league.coach_pool:
        longevity(c)


# What a run of seasons pushes an AD toward. Points build slowly and fade; only a
# lasting pattern (three-ish seasons) changes how he runs the place.
def _ad_pressures(league, team):
    recs = [(r[1], r[2]) for r in getattr(team, "historical_records", [])[-2:]] + [(team.wins, team.losses)]
    pcts = [w / (w + l) for w, l in recs if w + l]
    if not pcts:
        return {}
    last = pcts[-1]
    s = getattr(team, "_season_line", None) or {}
    p = {}
    if last < 0.45:
        p["win_now"] = p.get("win_now", 0) + 1.0
        p["politician"] = p.get("politician", 0) + 0.5
    if len(pcts) >= 2 and all(x < 0.5 for x in pcts[-2:]):
        p["booster"] = p.get("booster", 0) + 0.6
        p["turnaround"] = p.get("turnaround", 0) + 0.5
    if last >= 0.75:
        p["brand"] = p.get("brand", 0) + 0.8
        p["big_game"] = p.get("big_game", 0) + 0.5
    if 0.5 <= last < 0.72:
        p["patient"] = p.get("patient", 0) + 0.5
        p["conference"] = p.get("conference", 0) + 0.4
    if s.get("conf_champ"):
        p["conference"] = p.get("conference", 0) + 0.8
    import finance
    if finance.buyouts_in(team, league.year + 1) > finance.budget(team) * 0.1:
        p["budget"] = p.get("budget", 0) + 1.2
    if finance.available(league, team) < 0:
        p["budget"] = p.get("budget", 0) + 0.8
    return p


def drift_ads(league, rng):
    import ad_mode
    for team in league.teams:
        if ad_mode.is_mine(league, team) or not getattr(team, "ad", None) or team.ad.get("user"):
            continue
        d = team.ad.setdefault("drift", {})
        for k in list(d):
            d[k] *= 0.7                                          # old lessons fade
        for k, v in _ad_pressures(league, team).items():
            d[k] = d.get(k, 0) + v
        cur = team.ad["style"]
        best = max(d, key=d.get, default=None)
        if best and best != cur and d[best] >= 2.4 and d[best] > d.get(cur, 0) + 1.2 and rng.random() < 0.5:
            old = AD_STYLES[cur][0]
            team.ad["style"] = best
            team.ad["drift"] = {}
            team.ad.setdefault("style_log", []).append((league.year, cur, best))
            _news(league, "ad", f"{team.school} AD {team.ad['name']} has changed his approach: "
                                f"{old} → {AD_STYLES[best][0]} ({AD_STYLES[best][1].lower()})")


def end_of_season(league, rng):
    """Run once when the season is over, before the portal and signing day."""
    if not any(t.wins + t.losses for t in league.teams):
        return                                         # burn-in years: no games, no verdicts
    migrate(league)
    league.carousel[league.year] = list(getattr(league, "midseason_news", {}).get(league.year, []))
    moves = league.__dict__.setdefault("carousel_moves", {})
    moves[league.year] = [m for m in moves.get(league.year, []) if m.get("week", 0) > 0]   # keep mid-season exits

    import staff
    staff.setup(league)                                # older saves: give every program its coordinators
    import finance
    finance.ensure_all(league)
    finance.pay_season(league)                         # this season's paychecks; finished buyouts come off the books
    staff.record_seasons(league, rng)                  # every unit graded before anybody moves

    # 1. The book, the verdict, the growth.
    ovrs = league_ovrs(league)
    for team in league.teams:
        coach = team.coach
        if is_interim(coach):
            end_interim(league, team)                  # the job opens; the interim is a candidate for it
            continue
        coach.seat = getattr(coach, "seat_start", coach.seat)   # the verdict starts from where the year began
        coach.seat_events = []
        s = season_line(league, team)
        team._season_line = s
        xw, n = expectation(league, team, coach, ovrs)
        s["xw"] = round(xw, 2)
        s["exp"] = round(xw / n, 3) if n else round(expected_pct(team, league, ovrs), 3)
        coach.history.append(s)
        import history_book
        history_book.book_season(league, team, s, coach)   # the program keeps its own copy of the season
        delta, reasons = judge(league, team, coach, s, rng)
        if delta > 0:
            import difficulty
            delta *= difficulty.heat(coach)            # your difficulty (Career mode)
        coach.seat = int(max(0, min(100, round(coach.seat + delta))))
        s["seat"] = coach.seat
        coach.seat_log.append((league.year, coach.seat, reasons))
        coach.seat_start = coach.seat_prev = coach.seat
        g = s["w"] + s["l"]
        perf = (s["w"] / g if g else 0.5) - s["exp"]
        bonus = max(-1.0, perf * 8) + 1.2 * s["cfp"] + 2.0 * s["title"] + 0.6 * s["conf_champ"] + 0.3 * s["bowl"]
        # Your coach only develops through what you pay for (coach_dev.py); CPU coaches grow on their own.
        s["growth"] = 0 if getattr(coach, "is_user", False) else progress(coach, bonus, rng)
        extras = finance.season_clauses(league, team, coach, s)           # bonuses earned, rollover year
        team.coach_changed = False
        if getattr(coach, "is_user", False):
            import career
            import hotseat
            with hotseat.acting_as_coach(league, coach):
                if extras:
                    league.__dict__.setdefault("career_log", []).append((league.year, "Contract: " + ", ".join(extras) + "."))
                career.earn_traits(league, coach, s)

    finance.adjust_budgets(league)                     # winning brings money; years of losing take it away
    drift_ads(league, rng)                             # ADs change a little with what they live through
    import facilities
    facilities.end_of_season(league, rng)              # gate money in, wear and tear, the CPU's building projects

    # The profession doesn't inflate: if the middle of the pack has crept above where it belongs,
    # everybody's measured against a tougher field — the best stay the best, the 90s stay rare.
    rebalance_coaches(league, force=True, weight=0.3, reroll=False)

    # 2. Everybody gets a year older.
    for c in [t.coach for t in league.teams if t.coach is not None] + league.coach_pool:
        c.age += 1

    # 3. Retirements, and the occasional star who leaves for the Pro League.
    for team in league.teams:
        c = team.coach
        if c is None or human(c):
            continue
        tenure = league.year - (c.hired_year or league.year) + 1
        if rng.random() < retire_odds(c, title=c.history[-1]["title"], tenure=tenure):
            c.status = "retired"
            league.retired_coaches.append(c)
            _news(league, "retired", f"{c.name} retires at {c.age} after {tenure} season{'s' if tenure != 1 else ''} "
                                     f"at {team.school} ({_record(c)} since 2026{_honors(c)})")
            vacate(league, team, "retired")
        elif c.age < 58 and c.overall >= 86 and rng.random() < _pro_pull(c):
            c.status = "retired"
            league.retired_coaches.append(c)
            c.origin = "left for the Pro League"
            _news(league, "retired", f"{c.name} leaves {team.school} to become a Pro League head coach")
            vacate(league, team, "retired")

    # 4. The AD market: presidents judge their ADs, old ones retire, good ones at small
    #    schools get hired away. A new AD brings new priorities, and no loyalty to the coach.
    import ad_market
    import ad_mode
    ad_market.offseason(league, rng)

    # 5. Firings. Two hot years in a row, or one disaster, and the AD is ready to
    #    move — but first he checks the price (the buyout) and the market (is
    #    anyone out there actually better?). A coach at the end of his deal with a
    #    warm seat can simply not be renewed, which costs nothing.
    for team in league.teams:
        c = team.coach
        if c is None:
            continue
        if ad_mode.is_mine(league, team):
            verdict = ad_mode.carousel_verdict(league, team)       # your call, made on the report card
            if verdict:
                c.hot_years = 0
                mine_ = [h for h in c.history if h["school"] == team.school]
                rec_ = f"{sum(s['w'] for s in mine_)}-{sum(s['l'] for s in mine_)} there"
                if verdict == "fired":
                    owed = finance.owed(c, league)
                    _news(league, "fired", f"{team.school} AD {team.ad['name']} fires {c.name} ({rec_}"
                                           f"{'; owes ' + finance.money(owed) if owed else ''})")
                else:
                    _news(league, "fired", f"{team.school} lets {c.name}'s contract run out ({rec_}) — no buyout")
                vacate(league, team, "fired")
                if verdict != "fired":
                    c._last_exit["note"] = "contract not renewed"
            continue
        style = team.ad["style"]
        ad = AD_STYLES[style][2]
        user = getattr(c, "is_user", False)
        tenure = league.year - (c.hired_year or league.year) + 1
        line = fire_line(team)
        c.hot_years = c.hot_years + 1 if c.seat >= line else 0
        recent_title = any(h["title"] for h in c.history[-4:])
        disaster = c.seat >= line + 12
        mine = [h for h in c.history if h["school"] == team.school]
        improving = len(mine) >= 2 and mine[-1]["w"] - mine[-2]["w"] >= 3
        eligible = tenure >= min_tenure(team) or (tenure >= 2 and c.seat >= 97)
        if not eligible or (recent_title and c.seat < 98):
            continue
        if tenure >= 3 and len(mine) >= 2 and all(h["w"] / max(1, h["w"] + h["l"]) <= 0.25 for h in mine[-2:]):
            disaster = True                                              # can't be defended
        k = finance.contract(c)
        expiring = k is not None and k["end"] <= league.year
        why = None
        if c.hot_years >= 2 or disaster:
            share = finance.owed(c, league) / max(1, finance.budget(team))
            last = mine[-1] if mine else {"w": 0, "l": 1}
            dreadful = last["w"] / max(1, last["w"] + last["l"]) <= 0.35
            if not user and share >= 0.5 and not dreadful:
                _news(league, "vote", f"{team.school} can't swallow a {finance.money(finance.owed(c, league))} "
                                      f"buyout — {c.name} stays")
                continue
            if not disaster and not user and share >= (0.12 if ad.get("buyout") else 0.3):
                _news(league, "vote", f"{team.school} AD {team.ad['name']} keeps {c.name} rather than pay "
                                      f"a {finance.money(finance.owed(c, league))} buyout")
                continue
            if not disaster and mine and mine[-1]["w"] >= mine[-1]["l"] + 3 and rng.random() < 0.7:
                _news(league, "vote", f"{team.school} AD {team.ad['name']} keeps {c.name} after a "
                                      f"{mine[-1]['w']}-{mine[-1]['l']} season")
                c.seat = max(0, c.seat - 6)
                continue
            if improving and not disaster and rng.random() < 0.6:
                _news(league, "vote", f"{team.school} AD {team.ad['name']} backs {c.name} for another year "
                                      f"after a turnaround season")
                c.seat = max(0, c.seat - 8)
                continue
            if not disaster and not user and c.seat < line + 6 and upgrade_margin(league, team, c) < 4 \
                    and rng.random() < 0.65:
                _news(league, "vote", f"{team.school} AD {team.ad['name']} keeps {c.name} — "
                                      f"nobody available is clearly better")
                c.seat = max(0, c.seat - 4)
                continue
            why = "fired"
        elif expiring and not user and c.seat >= line - 12 and tenure >= min_tenure(team) \
                and not (mine and mine[-1]["w"] >= mine[-1]["l"] + 3):
            why = "not retained"                                         # the deal ran out; so did the patience
        if why is None:
            continue
        fired_c = c
        rec_all = (f"{sum(s['w'] for s in mine)}-{sum(s['l'] for s in mine)} there")
        if why == "fired":
            owed = finance.owed(c, league)
            _news(league, "fired", f"{team.school} fires {c.name} after {tenure} season"
                                   f"{'s' if tenure != 1 else ''} ({c.history[-1]['w']}-{c.history[-1]['l']} this year, "
                                   f"{rec_all}{'; owes ' + finance.money(owed) if owed else ''})")
        else:
            _news(league, "fired", f"{team.school} lets {c.name}'s contract run out ({c.history[-1]['w']}-"
                                   f"{c.history[-1]['l']} this year, {rec_all}) — no buyout")
        vacate(league, team, "fired")
        if why == "not retained":
            fired_c._last_exit["note"] = "contract not renewed"
        if not human(fired_c) and rng.random() < retire_odds(fired_c, fired=True):
            fired_c.status = "retired"
            fired_c._last_exit["note"] = f"retired from coaching at {fired_c.age}"
            league.coach_pool.remove(fired_c)
            league.retired_coaches.append(fired_c)
            _news(league, "retired", f"{fired_c.name} retires from coaching at {fired_c.age}")

    # 5b. Contracts: expiring deals are redone. Yours comes to you. (Early extensions for coaches
    #     who are doing the job wait until the hiring market is done — see 7b.)
    finance.renewals(league, rng, phase="expiring")

    # 6. Poaching: an aggressive AD with a lukewarm coach goes after a star.
    # Only a coach who is already in trouble — a hot seat, a mediocre year, no
    # recent title — and only for a clearly better, proven coach the school can
    # afford to buy out. It's rare, and it should be.
    for team in sorted(league.teams, key=lambda t: -t.prestige):
        c = team.coach
        if c is None or AD_STYLES[team.ad["style"]][2]["hire"] != "splash" or is_interim(c):
            continue
        if getattr(c, "is_user", False) or ad_mode.is_mine(league, team) or team.coach_changed:
            continue
        if league.year - (c.hired_year or league.year) + 1 < 3 or c.seat < fire_line(team) - 8:
            continue
        mine_ = [h for h in c.history if h["school"] == team.school]
        if not mine_ or mine_[-1]["w"] > mine_[-1]["l"] + 3 or any(h.get("title") or h.get("cfp") for h in mine_[-3:]):
            continue                                           # a winning coach doesn't get pushed out
        if finance.owed(c, league) > finance.budget(team) * 0.25:
            continue
        stars = [t.coach for t in league.teams if t.coach is not None and not human(t.coach)
                 and not ad_mode.is_mine(league, t) and t.prestige < team.prestige - 8
                 and not off_market(t.coach, league) and not t.coach_changed
                 and len(t.coach.history) >= 3 and track_record(t.coach, league) >= 0.14
                 and _rep(t.coach, league) >= _rep(c, league) + 5
                 and track_record(t.coach, league) >= track_record(c, league) + 0.1]
        if not stars or rng.random() > 0.35:
            continue
        star = max(stars, key=lambda x: track_record(x, league) + _rep(x, league) / 200)
        offer = finance.hc_offer(league, team, star, rng)
        if will_accept(star, team, league, rng, offer):
            _news(league, "fired", f"{team.school} moves on from {c.name} to make a splash hire")
            vacate(league, team, "fired")
            c._last_exit["note"] = "pushed out for a splash hire"
            hire(league, team, star, "poach", offer)

    # 7. Every human coach's phone rings first. Then every other open job is filled.
    def _phone():
        me = getattr(league, "user_coach", None)
        hook = getattr(league, "user_offer_hook", None)
        if getattr(league, "autosim", False) and hook is not None:
            hook = _auto_offer
        if me is not None and me.status != "retired" and hook is not None:
            import career
            fired_now = me.status == "unemployed" and me.history and me.history[-1]["year"] == league.year \
                and not league.__dict__.pop("_user_walked", False)
            offers = career.offers(league, rng)
            if offers or fired_now or me.status == "unemployed":
                import hotseat
                # Phase 2: in a normal one-coach career, let the job search live on
                # the offseason calendar instead of resolving the entire phone call here.
                staged = False
                try:
                    import offseason_cal
                    staged = offseason_cal.active(league) and hotseat.state(league) is None
                except Exception:
                    staged = False
                if staged:
                    terms = dict(getattr(league, "_user_offer_terms", {}) or {})
                    league.__dict__["_offseason_user_job_market"] = {
                        "offers": list(offers), "fired_now": bool(fired_now), "terms": terms,
                        "interviewed": False, "resolved": False,
                    }
                    reserved = league.__dict__.setdefault("_reserved_user_jobs", set())
                    for o in offers:
                        t, kind = o if isinstance(o, tuple) else (o, "opening")
                        if kind in ("opening", "pursued") and t.coach is None:
                            reserved.add(t.school)
                    league.__dict__.pop("_user_offer_terms", None)
                    return
                hotseat.maybe_pass(league, "YOUR PHONE IS RINGING")
                choice = hook(league, offers, fired_now)
                if choice is not None:
                    was = me.team
                    offer = getattr(league, "_user_offer_terms", {}).get(choice.school)
                    hire(league, choice, me, "poach" if was else "pool", offer)
                    league.__dict__.setdefault("career_log", []).append((league.year, f"Took the head coaching job at {choice.school}"
                                                           f"{' (left ' + was.school + ')' if was else ''}"
                                                           f"{' — ' + finance.terms(offer) if offer else ''}."))
                league.__dict__.pop("_user_offer_terms", None)
    import hotseat
    hotseat.each_seat(league, _phone)
    if getattr(league, "mode", None) == "commissioner":
        import job_market
        job_market.commissioner_market(league, rng)      # members' moves first, while the jobs are open
    mine_t = ad_mode.my_team(league)
    for _ in range(3):                                 # your search first; a chain of hires can open it again
        if mine_t is not None and mine_t.coach is None:
            if not ad_mode.coach_search(league, rng):
                _ai_fill_one(league, mine_t, rng)      # the search firm's pick
        fill_openings(league, rng)
        if mine_t is None or mine_t.coach is not None:
            break
    # 7b. The market has settled. ADs whose coach is still theirs lock him up early.
    finance.renewals(league, rng, phase="early")
    defer_staff = bool((league.__dict__.get("online") or {}).get("defer_staff_offseason"))
    if not defer_staff:
        staff.offseason(league, rng)                   # then every staff is rebuilt
    finance.ensure_all(league)                         # anybody who slipped through gets paper
    for team in league.teams:
        if not team.coach_changed and not ad_mode.is_mine(league, team):
            review_goals(team, league, rng)
    refresh_pool(league, rng)
    import career
    import hotseat
    hotseat.each_seat(league, lambda: career.after_carousel(league))

def record_classes(league, signing):
    """After signing day: put each coach's recruiting class rank in his book."""
    from recruiting import class_points
    classes = getattr(signing, "classes", {}) or {}
    scores = sorted(((t, class_points(classes.get(t, []))) for t in league.teams), key=lambda x: -x[1])
    rank = {t: i for i, (t, _) in enumerate(scores, 1)}
    for team in league.teams:
        # The class belongs to the season just played — find the book entry for this school.
        for c in [team.coach] + league.coach_pool:
            if c and c.history and c.history[-1]["school"] == team.school \
                    and c.history[-1]["year"] == league.year and c.history[-1]["class_rank"] is None:
                c.history[-1]["class_rank"] = rank[team]
                if getattr(c, "is_user", False):
                    import career
                    import hotseat
                    with hotseat.acting_as_coach(league, c):
                        career.earn_class_traits(league, c, rank[team])
                break


# ═══ Numbers for the screens ════════════════════════════════════════════════

def splits(seasons):
    tot = {"w": 0, "l": 0, "cw": 0, "cl": 0, "t25w": 0, "t25l": 0, "rw": 0, "rl": 0, "pw": 0, "pl": 0,
           "titles": 0, "cfp": 0, "confs": 0, "bowls": 0}
    for s in seasons:
        for k in ("w", "l", "cw", "cl", "t25w", "t25l", "rw", "rl", "pw", "pl"):
            tot[k] += s[k]
        tot["titles"] += s["title"]
        tot["cfp"] += s["cfp"]
        tot["confs"] += s["conf_champ"]
        tot["bowls"] += s["bowl"]
    return tot


def tenure_seasons(coach):
    if coach.team is None:
        return []
    return [s for s in coach.history if s["school"] == coach.team.school]


def all_coaches(league):
    return [t.coach for t in league.teams if t.coach is not None]


def name_interim(league, team):
    """A head coach leaves in the middle of the year (you retired): the coordinator with the better résumé takes
    over until the season ends, exactly like a mid-season firing. Without this the program has nobody on the
    headset for its next game."""
    import staff
    if team.coach is not None:
        return
    rng = random.Random(f"interim:{league.seed}:{league.year}:{league.week}:{team.school}")
    cands = [x for x in (getattr(team, "oc", None), getattr(team, "dc", None)) if x is not None]
    if cands:
        interim = max(cands, key=lambda x: (staff.resume_score(x), x.overall))
    else:
        interim = _new_candidate(league, rng, "coord")
        interim.status = "employed"
    interim.interim = team.school
    interim._pre_interim = {"hired_year": getattr(interim, "hired_year", None)}
    interim.__dict__.setdefault("history", [])
    interim.__dict__.setdefault("seat_log", [])
    interim.hired_year = league.year
    interim.seat = interim.seat_start = interim.seat_prev = 40
    interim.seat_events, interim.hot_years = [], 0
    team.coach = interim
    interim.team = team
    team.ratings["coach"] = interim.overall
    team.interim_split = (team.wins, team.losses)
    text = f"{team.school} names {interim.name} interim head coach"
    league.__dict__.setdefault("midseason_news", {}).setdefault(league.year, []).append(("hired", text))
    if hasattr(league, "carousel"):
        league.carousel.setdefault(league.year, []).append(("hired", text))
