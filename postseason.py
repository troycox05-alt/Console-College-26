"""
postseason.py — Everything that makes a December or January game *mean* something.

  * Real venues and approximate dates for every bowl, the NP rotation, the
    title game site, and the conference championship games.
  * Week labels for weeks 14-18.
  * The national champion history — the real BCS and Playoff eras (1998-2025)
    as the record book you inherit, plus every title won in your world.
  * Helpers that describe a postseason game: its banner, its stakes, how each
    team got here. The preview screen and the broadcast booth both use them.
"""
import world
from datetime import date, timedelta

# ─── Calendar ───────────────────────────────────────────────────────────────

WEEK_LABELS = {
    14: "Conference Championships",
    15: "NP First Round",
    16: "Bowl Season & NP Quarterfinals",
    17: "NP Semifinals",
    18: "National Championship",
}
WEEK_SHORT = {14: "CCG", 15: "NP R1", 16: "Bowls/QF", 17: "NP SF", 18: "Title"}

CFP_TYPES = ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship")
POSTSEASON_TYPES = CFP_TYPES + ("Conference Championship", "Bowl")


def week_label(week):
    return WEEK_LABELS.get(week, f"Week {week}")


def _first_saturday_of_december(year):
    d = date(year, 12, 1)
    while d.weekday() != 5:
        d += timedelta(days=1)
    return d


def _semifinal_thursday(year):
    """The semifinals land on the Thursday/Friday that falls Jan 8-14."""
    d = date(year + 1, 1, 8)
    while d.weekday() != 3:
        d += timedelta(days=1)
    return d


def postseason_dates(season):
    ccg = _first_saturday_of_december(season)
    sf = _semifinal_thursday(season)
    return {
        "ccg": ccg,
        "first_round": [ccg + timedelta(days=13), ccg + timedelta(days=14)],   # Fri + Sat
        "sf": [sf, sf + timedelta(days=1)],
        "title": sf + timedelta(days=11),                                      # the Monday after
    }


def date_words(d):
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y") if d else ""


def short_date(d):
    return d.strftime("%b ") + str(d.day) if d else ""


# ─── Venues ─────────────────────────────────────────────────────────────────

# The six Six Classics bowls that host the quarterfinals and semifinals.
CFP_BOWLS = {'Arroyo Bowl': ('Arroyo Stadium', 'Pasadena, CA', 'Arroyo Bowl'),
 'Crescent Bowl': ('Crescent City Dome', 'New Orleans, LA', 'Crescent Bowl'),
 'Coral Bowl': ('Gardens Stadium', 'Miami Gardens, FL', 'Coral Bowl'),
 'Lone Star Classic': ('Arlington Dome', 'Arlington, TX', 'Lone Star Classic'),
 'Sonoran Bowl': ('Glendale Dome', 'Glendale, AZ', 'Sonoran Bowl'),
 'Piedmont Bowl': ('Atlanta Dome', 'Atlanta, GA', 'Piedmont Bowl')}

# The 2026-27 rotation. Beyond that the rotation alternates.
# (quarterfinals with (month, day), semifinals in bracket order)
CFP_ROTATION = {2026: ([('Arroyo Bowl', 1, 1), ('Lone Star Classic', 1, 1), ('Piedmont Bowl', 1, 1), ('Sonoran Bowl', 12, 30)],
        ['Coral Bowl', 'Crescent Bowl'])}
_ALT_ROTATION = [([('Arroyo Bowl', 1, 1), ('Crescent Bowl', 12, 31), ('Coral Bowl', 12, 31), ('Lone Star Classic', 1, 1)],
  ['Sonoran Bowl', 'Piedmont Bowl']),
 ([('Arroyo Bowl', 1, 1), ('Lone Star Classic', 1, 1), ('Piedmont Bowl', 1, 1), ('Sonoran Bowl', 12, 31)],
  ['Coral Bowl', 'Crescent Bowl'])]


def cfp_rotation(season):
    if season in CFP_ROTATION:
        return CFP_ROTATION[season]
    return _ALT_ROTATION[season % 2]


# National championship game sites (keyed by season); later years rotate
# through the big pro stadiums.
TITLE_SITES = {2025: ('Gardens Stadium', 'Miami Gardens, FL'), 2026: ('Spring Mountain Stadium', 'Las Vegas, NV')}
_TITLE_ROTATION = [('Crescent City Dome', 'New Orleans, LA'),
 ('South Loop Stadium', 'Houston, TX'),
 ('Atlanta Dome', 'Atlanta, GA'),
 ('Inglewood Stadium', 'Inglewood, CA'),
 ('Indianapolis Dome', 'Indianapolis, IN'),
 ('Arlington Dome', 'Arlington, TX')]


def title_site(season):
    return TITLE_SITES.get(season) or _TITLE_ROTATION[season % len(_TITLE_ROTATION)]


# Conference championship games. None = hosted by the higher seed on campus.
CCG_SITES = {'SCC': ('Atlanta Dome', 'Atlanta, GA'),
 'Continental': ('Indianapolis Dome', 'Indianapolis, IN'),
 'Seaboard': ('Uptown Stadium', 'Charlotte, NC'),
 'Meridian': ('Arlington Dome', 'Arlington, TX'),
 'Lake Country': ('Detroit Dome', 'Detroit, MI')}

# name: (stadium, city, tier, (month, day)) — tier 1 bowls get the best teams.
# Dates are the usual slot; they drift a day or two year to year in real life.
BOWLS = {
    'Grove Bowl': ('Orlando Downtown Stadium', 'Orlando, FL', 1, (12, 31)),
    'Bayshore Bowl': ('Hillsborough Stadium', 'Tampa, FL', 1, (12, 31)),
    'Mission Bowl': ('Bexar Dome', 'San Antonio, TX', 1, (12, 29)),
    'St. Johns Bowl': ('St. Johns Riverfront Stadium', 'Jacksonville, FL', 1, (12, 30)),
    'Sunnyside Tarts Bowl': ('Orlando Downtown Stadium', 'Orlando, FL', 1, (12, 28)),
    'Harbor Bowl': ('Mission Valley Stadium', 'San Diego, CA', 1, (12, 27)),
    'Neon Bowl': ('Spring Mountain Stadium', 'Las Vegas, NV', 1, (12, 27)),
    'Gulf Coast Bowl': ('South Loop Stadium', 'Houston, TX', 1, (12, 31)),
    'Honky Tonk Bowl': ('Nashville Riverfront Stadium', 'Nashville, TN', 1, (12, 30)),
    'Franklin Mountain Bowl': ('Franklin Mountain Stadium', 'El Paso, TX', 2, (12, 31)),
    'Bluff City Bowl': ('Bluff City Stadium', 'Memphis, TN', 2, (12, 30)),
    "Grandma Pearl's Mayo Bowl": ('Uptown Stadium', 'Charlotte, NC', 2, (1, 2)),
    'Five Boroughs Bowl': ('Bronx Ballpark', 'Bronx, NY', 2, (12, 27)),
    'Annapolis Bowl': ('Severn Stadium', 'Annapolis, MD', 2, (12, 28)),
    'Back Bay Bowl': ('Back Bay Ballpark', 'Boston, MA', 2, (12, 28)),
    'Old Pueblo Bowl': ('Santa Catalina Stadium', 'Tucson, AZ', 2, (12, 28)),
    'Hometown Heroes Bowl': ('Turtle Creek Stadium', 'Dallas, TX', 2, (1, 2)),
    'Service Bowl': ('Trinity River Stadium', 'Fort Worth, TX', 2, (12, 27)),
    'Magic City Bowl': ('Red Mountain Stadium', 'Birmingham, AL', 2, (12, 27)),
    'Valley of the Franklin Mountain Bowl': ('Phoenix Ballpark', 'Phoenix, AZ', 2, (12, 26)),
    'Woodward Bowl': ('Detroit Dome', 'Detroit, MI', 2, (12, 26)),
    'Red River Bowl': ('Shreveport Stadium', 'Shreveport, LA', 2, (12, 28)),
    'Pacific Coast Bowl': ('Inglewood Stadium', 'Inglewood, CA', 3, (12, 19)),
    'Diamond Head Bowl': ('Mānoa Stadium', 'Honolulu, HI', 3, (12, 24)),
    'Hillsborough Bowl': ('Hillsborough Stadium', 'Tampa, FL', 3, (12, 20)),
    'High Desert Bowl': ('Sandia Stadium', 'Albuquerque, NM', 3, (12, 19)),
    'Spud Bowl': ('Table Rock Stadium', 'Boise, ID', 3, (12, 23)),
    'Hope Bowl': ('Orlando Downtown Stadium', 'Orlando, FL', 3, (12, 19)),
    'Grand Strand Bowl': ('Waccamaw Stadium', 'Conway, SC', 3, (12, 22)),
    'French Market Bowl': ('Crescent City Dome', 'New Orleans, LA', 3, (12, 19)),
    'Azalea Bowl': ('Mobile Bay Stadium', 'Mobile, AL', 3, (12, 18)),
    'Collin County Bowl': ('Frisco Park', 'Frisco, TX', 3, (12, 17)),
    'Gold Coast Bowl': ('Boca Inlet Stadium', 'Boca Raton, FL', 3, (12, 18)),
    'Capitol City Bowl': ('Montgomery Bowl Stadium', 'Montgomery, AL', 3, (12, 16)),
    'Nassau Bowl': ('Nassau National Stadium', 'Nassau, Bahamas', 3, (12, 21)),
}

# One or two things the booth knows about a bowl.
BOWL_LORE = {'Arroyo Bowl': ['The Arroyo Bowl is the oldest bowl game there is, and it plays like it.',
                 "Late in the afternoon the sun drops behind the Arroyo hills, and there's no prettier setting in "
                 'the sport.',
                 "You grow up watching this game on New Year's Day. Every kid on both sidelines has dreamed of the "
                 'Arroyo Bowl.'],
 'Crescent Bowl': ["The Crescent Bowl goes back to the 1930s, and it's lived under the dome for decades.",
                   'New Orleans in January — the French Quarter was packed with both fan bases last night.'],
 'Coral Bowl': ['The Coral Bowl first kicked off in the 1930s. South Florida in January.',
                'South Florida warmth for this one. Neither team minds trading a winter coat for this.'],
 'Lone Star Classic': ['The Lone Star Classic is a Texas institution, and it carries weight in this state.',
                       'That video board above the field in Arlington is about as big as some high school stadiums.'],
 'Sonoran Bowl': ['The Sonoran Bowl has hosted some of the most famous finishes in the sport.',
                  "Desert game, roof closed, and a building that's seen more than its share of classics."],
 'Piedmont Bowl': ['Atlanta has turned into the capital of big-game college football, and the Piedmont Bowl is a big '
                   'reason why.',
                   "The Atlanta Dome's roof opens like a camera lens, but it'll stay shut tonight."],
 'Grove Bowl': ['The Grove Bowl has been one of the best non-playoff bowls for years.'],
 'St. Johns Bowl': ['The St. Johns Bowl is one of the old-line bowls in the South.'],
 'Franklin Mountain Bowl': ['One of the oldest bowls in the country.',
                            'Look at the Franklin Mountains behind the stadium. They play this one with a view.'],
 'Bluff City Bowl': ['The Bluff City Bowl has been around since the 1950s. Memphis loves its football.'],
 "Grandma Pearl's Mayo Bowl": ['And yes — the winning coach here gets a bucket of mayonnaise dumped over his head. '
                               "Somebody's getting doused tonight."],
 'Sunnyside Tarts Bowl': ["The Sunnyside Tarts Bowl, where the giant toaster-pastry mascot's fate is… well, you'll "
                          'see after the game.'],
 'Five Boroughs Bowl': ["Football in a big-league ballpark in the Bronx in late December. It's cold, it's New York, "
                        'and the players love it.'],
 'Back Bay Bowl': ['Football in an old Boston ballpark. That big wall in left field is sitting right behind one end '
                   'zone.'],
 'Spud Bowl': ["Table Rock's sky-colored field. First-time viewers always need a second to adjust."],
 'Diamond Head Bowl': ['Christmas Eve in Honolulu. Not a bad way for either team to spend the holiday.'],
 'Nassau Bowl': ["Football in Nassau. Both teams have had a week in the islands — now it's time to work."],
 'Harbor Bowl': ['The Harbor Bowl has a reputation for wild, high-scoring games. San Diego in December.'],
 'Neon Bowl': ['The Neon Bowl has grown into one of the better matchups of bowl season.'],
 'Mission Bowl': ['The Bexar Dome in San Antonio — the Mission Bowl almost always delivers.']}

# ─── National champion history before 2026 (empty in the built-in universe) ────
# (season, champion, runner-up, champ score, runner-up score, champ record, coach, site, note)
REAL_CHAMPIONS = []          # the built-in universe's history starts in 2026 (a universe file can fill this in)


class ChampionRecord:
    def __init__(self, season, champion, runner_up, score, opp_score, record, coach, site, note="", real=True):
        self.season = season
        self.champion = champion          # school name
        self.runner_up = runner_up
        self.score = score
        self.opp_score = opp_score
        self.record = record
        self.coach = coach
        self.site = site
        self.note = note
        self.real = real                  # True = real history you inherited


def seed_history():
    return [ChampionRecord(*row) for row in REAL_CHAMPIONS]


def titles_for(league, school):
    """Seasons this school won it, oldest first."""
    return [c.season for c in getattr(league, "champions", []) if c.champion == school]


def title_game_appearances(league, school):
    return [c.season for c in getattr(league, "champions", []) if school in (c.champion, c.runner_up)]


def defending_champion(league):
    champs = [c for c in getattr(league, "champions", []) if c.season < league.year]
    return max(champs, key=lambda c: c.season).champion if champs else None


# ─── Describing a game ──────────────────────────────────────────────────────

def is_postseason(game):
    return getattr(game, "game_type", "Regular Season") in POSTSEASON_TYPES


def round_name(game):
    gt = getattr(game, "game_type", "Regular Season")
    return {"NP First Round": "First Round", "NP Quarterfinal": "Quarterfinal",
            "NP Semifinal": "Semifinal", "National Championship": "National Championship"}.get(gt, gt)


def banner(game):
    """The big line at the top of a preview or a broadcast."""
    gt = getattr(game, "game_type", "Regular Season")
    bowl = getattr(game, "bowl_name", None)
    display = getattr(game, "display_name", None) or bowl
    if gt == "National Championship":
        return "COLLEGE FOOTBALL PLAYOFF NATIONAL CHAMPIONSHIP"
    if gt == "NP Semifinal":
        return f"NP SEMIFINAL  ·  {display.upper()}"
    if gt == "NP Quarterfinal":
        return f"NP QUARTERFINAL  ·  {display.upper()}"
    if gt == "NP First Round":
        return "COLLEGE FOOTBALL PLAYOFF  ·  FIRST ROUND"
    if gt == "Conference Championship":
        return f"{bowl.upper()} GAME"
    if gt == "Bowl":
        return (display or "Bowl Game").upper()
    return ""


def site_line(game):
    venue = getattr(game, "venue", None) or f"{game.home.stadium}"
    when = date_words(getattr(game, "date", None))
    return f"{venue}" + (f"  ·  {when}" if when else "")


def seed_of(game, team):
    return (getattr(game, "seeds", None) or {}).get(team)


def _score_str(g, team):
    return f"{g.score_for(team)}-{g.score_for(g.opponent_of(team))}"


def path_lines(league, team, before_week):
    """How a team got here this postseason: 'Won the SCC Championship 27-24 over Alabama'."""
    out = []
    for w in range(14, before_week):
        for g in league.schedule.get(w, []):
            if team not in (g.home, g.away) or not g.played:
                continue
            opp = g.opponent_of(team)
            won = g.winner is team
            s = _score_str(g, team)
            gt = g.game_type
            if gt == "Conference Championship":
                out.append(f"won the {g.bowl_name} {s} over {opp.school}" if won
                           else f"lost the {g.bowl_name} {s} to {opp.school}")
            elif gt in CFP_TYPES and won:
                seed = seed_of(g, opp)
                tag = f"({seed}) " if seed else ""
                where = {"NP First Round": "in the first round",
                         "NP Quarterfinal": f"in the {g.display_name} quarterfinal",
                         "NP Semifinal": f"in the {g.display_name} semifinal"}.get(gt, "")
                out.append(f"beat {tag}{opp.school} {s} {where}".strip())
    return out


def team_tags(league, game, team):
    """Short labels for a team in a postseason game: seed, champion, bye, defending champ."""
    tags = []
    seed = seed_of(game, team)
    if seed and seed <= 4 and game.game_type in ("NP Quarterfinal",):
        tags.append("first-round bye")
    champs = getattr(league, "conf_champs", {})
    if champs.get(team.conference) is team:
        tags.append(f"{team.conference} champion")
    if defending_champion(league) == team.school:
        tags.append("defending national champion")
    return tags


def stakes_lines(league, game):
    """What the winner gets — the line that tells you why this game exists."""
    gt = game.game_type
    h, a = game.home, game.away
    if gt == "National Championship":
        lines = [f"Winner is the {league.year} national champion."]
        for t in (a, h):
            won = titles_for(league, t.school)
            if won:
                lines.append(f"{t.school}: {len(won)} title{'s' if len(won) > 1 else ''} since 1998, last in {won[-1]}.")
            else:
                lines.append(f"{t.school}: chasing its first national title of the BCS/Playoff era.")
        return lines
    if gt == "NP Semifinal":
        return [f"Winner plays for the national championship at {game.next_site} on "
                f"{short_date(game.next_date)}{_partner_words(game)}."]
    if gt == "NP Quarterfinal":
        return [f"Winner advances to the {game.next_game} semifinal on {short_date(game.next_date)}"
                f"{_partner_words(game)}."]
    if gt == "NP First Round":
        top = getattr(game, "waiting", None)
        who = f"({seed_of_team(league, top)}) {top.school}" if top else "a top-four seed"
        return [f"Winner goes to the {game.next_game} quarterfinal on {short_date(game.next_date)} to face {who}. "
                f"Loser's season is over."]
    if gt == "Conference Championship":
        conf = game.bowl_name.replace(" Championship", "")
        line = f"Winner is the {conf} champion"
        line += (" and gets serious consideration for an automatic NP bid."
                 if conf in world.POWER
                 else " — and one of the five NP bids for conference champions if it's among the highest-ranked.")
        return [line, f"{a.school} {a.conf_record} in league play · {h.school} {h.conf_record}"]
    if gt == "Bowl":
        bits = []
        if a.conference != h.conference:
            bits.append(f"{a.conference} vs. {h.conference}.")
        for t in (a, h):
            w, l = t.wins, t.losses
            if w + 1 >= 10:
                bits.append(f"A win gives {t.school} {w + 1} wins.")
            elif l >= 5:
                bits.append(f"{t.school} is trying to finish above .500.")
        return [" ".join(bits)] if bits else ["Last game of the season for both teams."]
    return []


def seed_of_team(league, team):
    return (getattr(league, "playoff_seed_map", None) or {}).get(team)


def _seeded(game, team):
    s = seed_of(game, team)
    return f"({s}) {team.school}" if s else team.school


def _partner_words(game):
    """' against (2) Ohio State' once the other side of the bracket is known,
    otherwise ' against the winner of (3) X vs. (6) Y'."""
    p = getattr(game, "partner", None)
    if p is None:
        return ""
    if p.played:
        w = p.winner
        return f" against {_seeded(p, w)}, who won the {p.display_name or 'other game'}"
    return f" against the winner of {_seeded(p, p.away)} vs. {_seeded(p, p.home)}"
