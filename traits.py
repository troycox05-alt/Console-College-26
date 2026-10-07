"""
traits.py — Personality, and what it costs or buys.

Ratings say what a player can do. Traits say what he actually does with it:
who raises his game in November, who disappears, who never misses a snap,
who leaves the second he loses a job. Coaches get them too — the closer who
flips recruits in December, the developer whose three-stars turn into
seniors nobody can block, the hothead whose teams live on the edge.

Every trait is a small, named modifier. Nothing here swings a game on its
own; traits tilt the odds, and over a season or a career the tilt shows.
"""

# key -> (label, blurb, effects)
# Effects are read by the system that cares:
#   clutch    late, close-game rating multiplier
#   form      game-to-game variance multiplier (low = steady)
#   injury    injury-chance multiplier
#   develop   offseason growth multiplier
#   portal    transfer-entry odds multiplier
#   loyalty   how hard a coaching change hits him (high = stays put)
#   penalty   how often he draws the flag
# Team lifts — rating points added to his whole team's game-day form, summed
# across the starters who carry them (and the head coach):
#   team_lift every game          road / home   by venue
#   rival     rivalry games       late / early  November-and-after / September
#   big_game  vs a ranked opponent (coaches, and Big-Game Player / Flat-Track Bully)
#   weak      vs an opponent he should beat: unranked and clearly worse, or FCS
PLAYER_TRAITS = {
    "clutch":      ("Clutch", "Plays his best when it matters most", {"clutch": 1.05}),
    "frontrunner": ("Front-runner", "Great with a lead, fades when trailing", {"clutch": 0.95}),
    "steady":      ("Steady", "Same player every single Saturday", {"form": 0.55}),
    "streaky":     ("Streaky", "Capable of anything, good or bad", {"form": 1.6}),
    "iron":        ("Iron Man", "Never comes off the field", {"injury": 0.55}),
    "fragile":     ("Injury Prone", "Can't seem to stay healthy", {"injury": 1.7}),
    "gym_rat":     ("Gym Rat", "First one in, last one out", {"develop": 1.16, "practice": 0.3}),
    "coaster":     ("Coasts", "Talented, and knows it", {"develop": 0.86, "practice": -0.35}),
    "loyal":       ("Loyal", "Signed up for the whole thing", {"portal": 0.45, "loyalty": 1.6}),
    "mercenary":   ("Mercenary", "Playing time or he's gone", {"portal": 1.9, "loyalty": 0.5, "role": 1.4, "nil": 1.3}),
    "leader":      ("Team Leader", "The room follows him", {"team_lift": 0.4, "form": 0.85}),
    "headcase":    ("Head Case", "One bad play can spiral", {"form": 1.35, "penalty": 1.5}),

    # ── game day ────────────────────────────────────────────────────────
    "closer_p":    ("Closer", "Wants the ball in the last two minutes", {"clutch": 1.06, "form": 0.9}),
    "slow_start":  ("Slow Starter", "Takes a quarter to wake up", {"clutch": 1.03, "form": 1.15}),
    "big_game":    ("Big-Game Player", "Rises against ranked teams", {"big_game": 0.3}),
    "flat":        ("Flat-Track Bully", "Feasts on bad teams, quiet in big ones", {"weak": 0.3, "big_game": -0.3}),
    "warrior":     ("Warrior", "Plays hurt, and plays well hurt", {"injury": 0.8, "clutch": 1.03}),
    "cold":        ("Cold Blooded", "Pulse never changes", {"form": 0.6, "clutch": 1.04}),
    "emotional":   ("Emotional", "Rides every wave in the stadium", {"form": 1.45}),
    "disciplined": ("Disciplined", "Never beats himself", {"penalty": 0.55}),
    "chippy":      ("Chippy", "Plays right on the line", {"penalty": 1.8, "clutch": 1.02}),
    "gamer":       ("Gamer", "Practices poorly, plays great", {"form": 1.2, "clutch": 1.05, "practice": -0.6}),
    "practice_all":("Practice All-American", "Looks the part Monday to Friday", {"form": 1.1, "clutch": 0.95, "practice": 0.7}),
    "workhorse":   ("Workhorse", "Never asks out of the game", {"injury": 1.15, "clutch": 1.04}),

    # ── body and durability ─────────────────────────────────────────────
    "glass":       ("Glass", "One hit away, every week", {"injury": 2.1}),
    "rehab":       ("Fast Healer", "Back weeks before anybody expects", {"injury": 0.75, "develop": 1.04}),
    "conditioned": ("Conditioned", "Fourth quarter is his quarter", {"clutch": 1.04, "injury": 0.85}),
    "heavy_legs":  ("Wears Down", "Fades late in games and late in years", {"clutch": 0.95, "injury": 1.2}),

    # ── progression ─────────────────────────────────────────────────────
    "film_junkie": ("Film Junkie", "Knows the answer before the snap", {"develop": 1.14, "form": 0.9, "practice": 0.2}),
    "late_bloom":  ("Late Bloomer", "Everything clicks year three", {"develop": 1.2, "clutch": 0.97}),
    "raw":         ("Raw", "All the tools, none of the polish yet", {"develop": 1.12, "form": 1.25, "practice": -0.2}),
    "maxed":       ("Maxed Out", "Is what he is", {"develop": 0.75}),
    "coachable":   ("Coachable", "Fixes it the first time he's told", {"develop": 1.1, "loyalty": 1.2}),
    "stubborn":    ("Stubborn", "Does it his way", {"develop": 0.88, "penalty": 1.2}),
    "weight_room": ("Weight Room Rat", "Adds real strength every winter", {"develop": 1.12, "injury": 0.9}),

    # ── locker room and transfers ───────────────────────────────────────
    "captain":     ("Captain", "Holds the whole roster together", {"team_lift": 0.6, "form": 0.8, "loyalty": 1.4}),
    "homesick":    ("Homesick", "Always had one eye on home", {"portal": 1.5}),
    "patient":     ("Patient", "Will wait his turn for a job", {"portal": 0.5, "role": 0.6}),
    "impatient":   ("Impatient", "Won't sit a year for anybody", {"portal": 1.8, "role": 1.5}),
    "system_fit":  ("System Player", "Needs the right scheme around him", {"develop": 1.06, "portal": 1.25}),
    "grinder":     ("Grinder", "Outworks the room, every day", {"loyalty": 1.8, "portal": 0.4, "develop": 1.06, "practice": 0.3, "role": 0.7}),
    "spotlight":   ("Chasing Spotlight", "Wants the biggest stage he can find", {"portal": 1.6, "loyalty": 0.6}),
    "family_guy":  ("Family First", "Every decision runs through home", {"portal": 0.8, "loyalty": 1.3}),
    "quiet_pro":   ("Quiet Professional", "No drama, no headlines, just Saturdays", {"form": 0.75, "loyalty": 1.25}),
    "hothead":     ("Hothead", "One flag away from the bench", {"penalty": 2.0, "form": 1.25}),
    "underdog":    ("Chip On His Shoulder", "Recruited by nobody, remembers everybody", {"develop": 1.1, "clutch": 1.04}),
    "prodigy":     ("Prodigy", "Ready as a true freshman", {"develop": 1.08, "clutch": 1.03}),

    # ── the room ────────────────────────────────────────────────────────
    "mentor":      ("Mentor", "Takes every freshman under his wing", {"team_lift": 0.3, "loyalty": 1.2}),
    "diva":        ("Diva", "Needs the ball, and lets everybody know", {"team_lift": -0.3, "form": 1.2, "portal": 1.4, "role": 1.6, "nil": 1.3}),
    "humble":      ("Humble", "Hands the ball to the official and jogs back", {"form": 0.85, "penalty": 0.75, "role": 0.7, "chem": 0.8}),
    "showman":     ("Showman", "Every big play comes with a celebration", {"clutch": 1.03, "form": 1.15, "penalty": 1.35}),
    "tone_setter": ("Tone Setter", "The first hit of the game is always his", {"team_lift": 0.25, "penalty": 1.2}),
    "soft":        ("Shies From Contact", "Avoids the big collision when it counts", {"clutch": 0.96, "injury": 0.85}),

    # ── where and when ──────────────────────────────────────────────────
    "road_warrior": ("Road Warrior", "Loves a stadium full of people booing him", {"road": 0.4}),
    "homebody_p":  ("Home Cooking", "A different player in front of his own crowd", {"home": 0.4, "road": -0.3}),
    "rivalry":     ("Rivalry Guy", "Circled one game on the calendar in August", {"rival": 0.6}),
    "jitters":     ("Big-Game Jitters", "Tightens up when the lights get bright", {"clutch": 0.94, "form": 1.1}),
    "november":    ("November Player", "Gets better as the air gets colder", {"late": 0.5}),
    "early_bird":  ("Fast Starter", "Hot in September, gassed by Thanksgiving", {"early": 0.4, "late": -0.3}),

    # ── v28: practice habits, the room, off the field ───────────────────
    "vocal":       ("Vocal Leader", "Talks the whole huddle through it", {"team_lift": 0.2, "chem": 1.5}),
    "loner":       ("Lone Wolf", "Does his own thing, on his own time", {"chem": -1.2, "form": 0.9}),
    "student":     ("Honor Roll", "Never a worry in the classroom", {"trouble": -0.8, "develop": 1.04}),
    "eligibility": ("Academic Risk", "One bad semester from sitting", {"trouble": 1.2}),
    "team_first":  ("Team First", "Whatever the team needs, wherever", {"role": 0.55, "portal": 0.7, "chem": 0.8}),
    "stat_padder": ("Stat Chaser", "Counts his touches, and yours", {"role": 1.5, "portal": 1.3, "team_lift": -0.15, "trouble": 0.5}),
    "night_owl":   ("Night Owl", "The last one out of the bars", {"trouble": 1.0, "practice": -0.3, "injury": 1.08}),
    "early_riser": ("Early Riser", "In the building before the coaches", {"practice": 0.35, "develop": 1.04}),
    "unflappable": ("Unflappable", "Bad snap, bad call, same guy", {"clutch": 1.04, "form": 0.85}),
    "overthinker": ("Overthinker", "Perfect on Tuesday, tight on Saturday", {"practice": 0.4, "clutch": 0.95}),
    "motor":       ("Relentless Motor", "Every rep at full speed", {"practice": 0.45, "develop": 1.05, "injury": 1.06}),
    "low_motor":   ("Low Motor", "Turns it on when he feels like it", {"practice": -0.45, "develop": 0.9}),
    "short_memory":("Short Memory", "Forgets the last play before the next one", {"form": 0.85, "clutch": 1.02}),
    "dweller":     ("Dwells on Mistakes", "One drop becomes three", {"form": 1.25, "practice": -0.15}),
    "social_star": ("Social Media Star", "A million followers and counting", {"nil": 1.45, "portal": 1.2, "trouble": 0.5}),
    "private":     ("Private Guy", "No posts, no interviews, no problems", {"nil": 0.8, "form": 0.92, "trouble": -0.4}),
    "bloodline":   ("Football Bloodline", "His dad played on Sundays", {"develop": 1.06, "practice": 0.2, "role": 1.2}),
    "first_gen":   ("First-Generation Student", "Carrying a whole family's hopes", {"loyalty": 1.3, "trouble": -0.5, "nil": 1.1}),
    "competitor":  ("Hates to Lose", "Even the drills, even the card games", {"practice": 0.3, "team_lift": 0.15, "penalty": 1.1}),
    "content":     ("Content", "Happy just to be on the team", {"role": 0.65, "develop": 0.93}),
}

# Coach effects:
#   recruit_close  interest gained per contact
#   recruit_eval   scouting accuracy
#   develop        offseason growth for everyone on the roster
#   portal_hold    keeps his own players from entering
#   portal_shop    aggression working the portal
#   aggression     fourth downs and trick plays (on top of his rating)
#   discipline     penalties
COACH_TRAITS = {
    "closer":     ("The Closer", "Wins December", {"recruit_close": 1.25}),
    "evaluator":  ("Evaluator", "Finds players nobody else sees", {"recruit_eval": 1.5}),
    "developer":  ("Developer", "Three-stars leave as pros", {"develop": 1.12}),
    "ceo":        ("CEO", "Runs a program, delegates the rest", {"portal_hold": 1.3, "recruit_close": 0.9}),
    "players_coach": ("Players' Coach", "They'd run through a wall for him", {"portal_hold": 1.45}),
    "taskmaster": ("Taskmaster", "Hard on them, and it works", {"develop": 1.08, "portal_hold": 0.8}),
    "gambler":    ("Gambler", "Lives on the edge", {"aggression": 12}),
    "disciplinarian": ("Disciplinarian", "Clean, penalty-free football", {"discipline": 0.7}),
    "portal_king": ("Portal King", "Rebuilds a roster every winter", {"portal_shop": 1.5}),

    # ── recruiting ──────────────────────────────────────────────────────
    "in_state":   ("Fence Builder", "Nobody leaves his state", {"recruit_close": 1.15}),
    "national":   ("National Recruiter", "Signs players from everywhere", {"recruit_close": 1.1, "recruit_eval": 1.15}),
    "salesman":   ("Salesman", "Could sell sand in a desert", {"recruit_close": 1.3, "recruit_eval": 0.85}),
    "relationship": ("Relationship Guy", "Recruits families, not players", {"recruit_close": 1.2, "portal_hold": 1.2}),
    "misses":     ("Poor Evaluator", "Falls for the highlight tape", {"recruit_eval": 0.6, "recruit_close": 1.1}),
    "juco_king":  ("Junior College Pipeline", "Plugs holes fast", {"portal_shop": 1.35}),
    "hoarder":    ("Talent Hoarder", "Signs everybody, sorts it out later", {"recruit_close": 1.12, "portal_hold": 0.85}),

    # ── development and program ────────────────────────────────────────
    "qb_whisperer": ("QB Whisperer", "Quarterbacks get better here — +15% QB development", {"develop": 1.15}),
    "trench_guru": ("Trench Guru", "Builds lines that last — +15% OL/DL development", {"develop": 1.15}),
    "culture":    ("Culture Builder", "Nobody wants to leave", {"portal_hold": 1.5, "develop": 1.05}),
    "burnout":    ("Burns Them Out", "Gets everything, for two years", {"develop": 1.12, "portal_hold": 0.65}),
    "delegator":  ("Trusts His Staff", "Hires well and gets out of the way", {"develop": 1.07, "recruit_close": 1.05}),
    "micromanager": ("Micromanager", "Has a hand in everything", {"develop": 0.95, "discipline": 0.85}),

    # ── sideline ────────────────────────────────────────────────────────
    "riverboat":  ("Riverboat Gambler", "Fourth and four is a green light", {"aggression": 18}),
    "conservative": ("Conservative", "Takes the points, wins the field", {"aggression": -15}),
    "clock_master": ("Clock Manager", "Never wastes a timeout", {"discipline": 0.9}),
    "hothead_c":  ("Hothead", "His teams play angry, and flagged", {"discipline": 1.5, "aggression": 8}),
    "motivator":  ("Motivator", "Teams play over their heads for him", {"develop": 1.05, "portal_hold": 1.2}),
    "schemer":    ("Schemer", "Out-designs you on Saturday", {"aggression": 6, "develop": 1.04}),

    # ── the seat and the money ──────────────────────────────────────────
    "lightning_rod": ("Lightning Rod", "Every loss is a talk-radio segment", {"heat": 1.3, "recruit_close": 1.05}),
    "teflon":     ("Teflon", "Nothing sticks to him", {"heat": 0.7}),
    "booster_fav": ("Boosters' Favorite", "The money likes him, and pays for his roster",
                    {"heat": 0.8, "portal_shop": 1.2}),
    "old_school": ("Old School", "Won't touch the portal, won't throw it forty times",
                   {"portal_shop": 0.7, "aggression": -8, "discipline": 0.85}),

    # ── the big stage ───────────────────────────────────────────────────
    "big_game_c": ("Big-Game Coach", "His teams rise against ranked opponents", {"big_game": 0.8}),
    "choker":     ("Can't Win the Big One", "Tight when the stakes are highest", {"big_game": -0.8}),
    "rivalry_c":  ("Rivalry Specialist", "Owns the game that matters most", {"rival": 1.0}),
    "road_dog":   ("Road Dog", "His teams travel well", {"road": 0.8}),

    # ── v28: game day, the room, the media ──────────────────────────────
    "halftime":   ("Halftime Genius", "His teams come out of the locker room different", {"adjust": 0.6}),
    "rigid":      ("Rigid Game Plan", "Plan A, all four quarters", {"adjust": -0.5, "discipline": 0.9}),
    "off_guru":   ("Offensive Mind", "Sees the field like a quarterback", {"off_iq": 6}),
    "def_guru":   ("Defensive Mastermind", "Takes away what you do best", {"def_iq": 6}),
    "film_room":  ("Film Room Grinder", "Grades every snap himself", {"eye": 1.25, "adjust": 0.2}),
    "gut":        ("Goes With His Gut", "Trusts instinct over the tape", {"eye": 0.85, "aggression": 5}),
    "tight_ship": ("Runs a Tight Ship", "Curfews, bed checks, no exceptions", {"trouble": 0.55, "discipline": 0.85, "chem": -2}),
    "loose_ship": ("Loose Ship", "Grown men, treated like grown men", {"trouble": 1.45, "chem": 2.5}),
    "protector":  ("Protects His Players", "Never runs them into the ground", {"team_injury": 0.88, "relations": 0.3}),
    "grinds":     ("Grinds Them in Practice", "Full pads, every Tuesday, all year", {"team_injury": 1.12, "develop": 1.05}),
    "media_darling": ("Media Darling", "The cameras love him, and so do recruits", {"heat": 0.85, "recruit_close": 1.06}),
    "prickly":    ("Prickly with the Media", "Every presser is a standoff", {"heat": 1.15, "relations": -0.1}),
    "vet_trust":  ("Trusts His Veterans", "Seniors play — that's the deal", {"loyalty_hold": 1.0, "relations": 0.15}),
    "youth":      ("Plays the Kids", "Talent plays, whatever the class", {"develop": 1.04, "relations": -0.05}),
    "motivator_x": ("Fiery Speeches", "Can get them up for anybody", {"motivation": 0.4, "discipline": 1.1}),
    "flat_teams": ("Flat-Liner", "His teams don't get up for much", {"motivation": -0.35}),
}

_PLAYER_PAIRS = (("clutch", "frontrunner"), ("grinder", "coaster"), ("steady", "streaky"), ("iron", "fragile"),
                 ("gym_rat", "coaster"), ("loyal", "mercenary"), ("leader", "headcase"),
                 ("closer_p", "slow_start"), ("big_game", "flat"), ("cold", "emotional"),
                 ("disciplined", "chippy"), ("gamer", "practice_all"), ("warrior", "glass"),
                 ("rehab", "heavy_legs"), ("conditioned", "workhorse"),
                 ("film_junkie", "raw"), ("late_bloom", "maxed"), ("coachable", "stubborn"),
                 ("captain", "hothead"), ("patient", "impatient"), ("grinder", "spotlight"),
                 ("quiet_pro", "homesick"), ("underdog", "prodigy"),
                 ("weight_room", "system_fit"), ("family_guy", "mercenary"),
                 ("mentor", "diva"), ("humble", "showman"), ("tone_setter", "soft"),
                 ("road_warrior", "homebody_p"), ("rivalry", "jitters"), ("november", "early_bird"),
                 ("vocal", "loner"), ("student", "eligibility"), ("team_first", "stat_padder"),
                 ("early_riser", "night_owl"), ("unflappable", "overthinker"), ("motor", "low_motor"),
                 ("short_memory", "dweller"), ("private", "social_star"), ("bloodline", "first_gen"),
                 ("competitor", "content"))

# Coaches can't be both halves of any of these.
_COACH_PAIRS = (("riverboat", "conservative"), ("gambler", "conservative"), ("disciplinarian", "hothead_c"),
                ("evaluator", "misses"), ("culture", "burnout"), ("delegator", "micromanager"),
                ("players_coach", "taskmaster"), ("lightning_rod", "teflon"), ("big_game_c", "choker"),
                ("portal_king", "old_school"), ("juco_king", "old_school"), ("riverboat", "old_school"),
                ("halftime", "rigid"), ("film_room", "gut"), ("tight_ship", "loose_ship"), ("protector", "grinds"),
                ("media_darling", "prickly"), ("vet_trust", "youth"), ("motivator_x", "flat_teams"),
                ("off_guru", "def_guru"))
TRAIT_ODDS = 0.029          # per side of each pair — about 2.4 traits per player, capped at 3 (plus a personality)


# ═══ Personalities (v28) ════════════════════════════════════════════════════
# Every player has exactly one: the kind of person he is, under the traits.
# Effects use the same keys as traits (read through mod()), plus:
#   practice  how he looks Monday to Friday, in rating points of practice form (+ looks better)
#   role      how hard a depth-chart move hits his mood (x; 1.6 = takes it very personally)
#   chem      what he does to the locker room's temperature (points of chemistry baseline)
#   trouble   how often trouble finds him off the field (added to the trouble score)
#   nil       how much he wants paid (x on NIL demands)
# key -> (label, blurb, effects, weight)
PERSONAS = {
    "alpha":        ("Alpha", "Has to be the man, and plays like it", {"role": 1.6, "clutch": 1.03, "team_lift": 0.1, "nil": 1.15}, 7),
    "introvert":    ("Introvert", "Keeps to himself; lets the tape talk", {"form": 0.9, "trouble": -0.4, "nil": 0.85, "chem": -0.4}, 9),
    "joker":        ("Class Clown", "Keeps the room loose, sometimes too loose", {"chem": 2.2, "practice": -0.2, "penalty": 1.08}, 7),
    "scholar":      ("Student of the Game", "Reads defenses like textbooks", {"develop": 1.06, "practice": 0.25, "trouble": -0.7}, 7),
    "social":       ("Social Butterfly", "Knows everybody on campus, and every party", {"trouble": 1.3, "chem": 1.0, "practice": -0.2}, 6),
    "blue_collar":  ("Blue Collar", "Clocks in, clocks out, never complains", {"role": 0.6, "develop": 1.05, "form": 0.88, "nil": 0.8}, 9),
    "brand":        ("Brand Builder", "Thinks like a business, because he is one", {"nil": 1.5, "portal": 1.3, "loyalty": 0.8, "trouble": 0.3}, 6),
    "faith":        ("Faith & Family", "Grounded by what matters off the field", {"trouble": -1.0, "form": 0.88, "loyalty": 1.3, "chem": 1.0}, 7),
    "fierce":       ("Fierce Competitor", "Treats every rep like fourth-and-one", {"practice": 0.4, "clutch": 1.04, "penalty": 1.2, "role": 1.3}, 7),
    "sensitive":    ("Sensitive", "Feels every word a coach says", {"role": 1.7, "form": 1.15}, 6),
    "hometown":     ("Hometown Kid", "Playing for his whole town", {"home": 0.25, "loyalty": 1.5, "portal": 0.7}, 6),
    "free_spirit":  ("Free Spirit", "Marches to his own drum", {"form": 1.3, "practice": -0.15, "develop": 1.03, "trouble": 0.5}, 5),
    "perfectionist": ("Perfectionist", "Never satisfied, sometimes to a fault", {"practice": 0.5, "develop": 1.07, "clutch": 0.96}, 6),
    "laid_back":    ("Laid Back", "Nothing rattles him, nothing hurries him", {"form": 0.82, "practice": -0.3, "role": 0.7, "clutch": 1.02}, 7),
    "intense":      ("Intense", "Wired tight, all day, every day", {"practice": 0.3, "form": 1.18, "penalty": 1.22, "trouble": 0.4}, 6),
    "old_soul":     ("Old Soul", "Mature beyond his years", {"form": 0.86, "trouble": -0.7, "chem": 1.0, "develop": 1.03}, 6),
}

# Coaching styles: how a coach runs a room and a sideline. Every CPU coach has one.
#   adjust      halftime adjustments, rating points of second-half form
#   motivation  rating points of game-day form (getting them up)
#   relations   weekly morale drift for every player (points)
#   eye         how sharp his read of his own players is (x)
#   trouble     how often trouble finds his locker room (x)
#   chem        locker-room chemistry baseline (points)
#   team_injury injury rate for the whole roster (x)
#   lean        what he looks for when he sets a depth chart (see depth_staff.LEANS)
COACH_STYLES = {
    "fiery":      ("Fiery", "Loud, emotional, all in", {"motivation": 0.35, "discipline": 1.12, "relations": -0.05}, "toughness", 9),
    "stoic":      ("Stoic", "Never too high, never too low", {"discipline": 0.92, "adjust": 0.15, "motivation": -0.1}, "incumbent", 9),
    "professor":  ("Professor", "Teaches the game like a classroom", {"adjust": 0.35, "eye": 1.15, "motivation": -0.15}, "technician", 8),
    "father":     ("Father Figure", "Recruits the family, raises the player", {"relations": 0.35, "trouble": 0.8, "chem": 2, "portal_hold": 1.1}, "character", 8),
    "drill":      ("Drill Sergeant", "Discipline first, feelings later", {"discipline": 0.8, "relations": -0.3, "team_injury": 1.08, "trouble": 0.7}, "toughness", 7),
    "showman":    ("Showman", "Swagger, sound bites and a full stadium", {"recruit_close": 1.08, "heat": 1.1, "motivation": 0.15}, "upside", 7),
    "grinder_c":  ("Grinder", "Sleeps in the office in October", {"eye": 1.1, "develop": 1.04, "relations": -0.1}, "practice", 8),
    "players":    ("Players First", "His door, and his phone, are always open", {"relations": 0.3, "portal_hold": 1.15, "discipline": 1.08}, "incumbent", 8),
    "ceo_style":  ("Program CEO", "Hires the staff and lets them work", {"eye": 0.95, "recruit_close": 1.05}, "gameday", 7),
    "innovator":  ("Innovator", "Always a year ahead of the trend", {"adjust": 0.25, "aggression": 6, "discipline": 1.05}, "measurables", 7),
    "old_ball":   ("Old Ball Coach", "Run it, stop it, win the turnover battle", {"discipline": 0.9, "aggression": -6, "motivation": 0.1}, "veterans", 7),
    "talent_eval": ("Talent Hunter", "Plays the best player, whatever the class", {"eye": 1.2, "relations": -0.05}, "youth", 6),
}
STYLE_LEANS = {k: v[3] for k, v in COACH_STYLES.items()}


def _seed_pick(name, table, salt):
    import random as _r
    keys = list(table)
    weights = [table[k][-1] for k in keys]
    return _r.Random(f"{salt}:{name}").choices(keys, weights=weights)[0]


def persona(p):
    """The player's personality key (older saves: dealt from his name, so it never changes)."""
    v = p.__dict__.get("persona")
    if v not in PERSONAS:
        v = p.__dict__["persona"] = _seed_pick(getattr(p, "name", "?"), PERSONAS, "persona")
    return v


def style(c):
    """A coach's style key (None for your own coach — you are your style)."""
    if getattr(c, "is_user", False):
        return c.__dict__.get("style") if c.__dict__.get("style") in COACH_STYLES else None
    v = c.__dict__.get("style")
    if v not in COACH_STYLES:
        v = c.__dict__["style"] = _seed_pick(getattr(c, "name", "?"), COACH_STYLES, "style")
    return v


def tags(holder):
    """Traits plus the personality (players) or style (coaches): every key that describes him."""
    out = list(getattr(holder, "traits", ()) or ())
    if holder.__class__.__name__ == "Coach":
        s = style(holder)
        if s:
            out.append(s)
    elif hasattr(holder, "first_name"):
        out.append(persona(holder))
    return out


_FX_CACHE = {}


def _effects_of(holder):
    """[(key, effects)] for everything he carries — personality/style first. Cached by what he carries
    (two players with the same traits and personality carry the same effects)."""
    coach = holder.__class__.__name__ == "Coach"
    first = style(holder) if coach else (persona(holder) if hasattr(holder, "first_name") else None)
    sig = (coach, first, tuple(getattr(holder, "traits", ()) or ()))
    hit = _FX_CACHE.get(sig)
    if hit is not None:
        return hit
    if coach:
        out = [(first, COACH_STYLES[first][2])] if first else []
        out += [(t, COACH_TRAITS.get(t, ("", "", {}))[2]) for t in sig[2]]
    else:
        out = [(first, PERSONAS[first][2])] if first else []
        out += [(t, PLAYER_TRAITS.get(t, ("", "", {}))[2]) for t in sig[2]]
    _FX_CACHE[sig] = out
    return out


def assign_player_traits(player, rng):
    """Most players get one or two. They're drawn from opposing pairs, so
    nobody is both Iron Man and Injury Prone."""
    traits = []
    for a, b in _PLAYER_PAIRS:
        roll = rng.random()
        if roll < TRAIT_ODDS:
            traits.append(a)
        elif roll < 2 * TRAIT_ODDS:
            traits.append(b)
    rng.shuffle(traits)
    # Drop repeats (a trait can sit in more than one pair — Mercenary does) and
    # anything that contradicts a trait he already has.
    kept = []
    for t in traits:
        if t in kept:
            continue
        clash = any((t, k) in _PLAYER_PAIRS or (k, t) in _PLAYER_PAIRS for k in kept)
        if not clash:
            kept.append(t)
    player.traits = kept[:3]
    keys = list(PERSONAS)
    player.persona = rng.choices(keys, weights=[PERSONAS[k][3] for k in keys])[0]
    return player.traits


def assign_coach_traits(coach, rng):
    keys = list(COACH_TRAITS)
    rng.shuffle(keys)
    want = rng.choice((1, 2, 2, 3))
    kept = []
    for k in keys:
        if len(kept) >= want:
            break
        if any((k, x) in _COACH_PAIRS or (x, k) in _COACH_PAIRS for x in kept):
            continue
        kept.append(k)
    coach.traits = kept
    return coach.traits


# Coach traits whose effect only reaches one part of the roster.
POSITION_SCOPE = {"trench_guru": {"OL", "DL"}, "qb_whisperer": {"QB"}}


def mod(holder, key, default=1.0, position=None):
    """Combined multiplier for a trait effect, across everything he carries
    (his personality or coaching style included). With `position`,
    position-scoped coach traits (Trench Guru, QB Whisperer) only count for
    players at their positions; without it they don't count."""
    out = default
    coach = holder.__class__.__name__ == "Coach"
    for t, effects in _effects_of(holder):
        scope = POSITION_SCOPE.get(t) if coach else None
        if scope is not None and position not in scope:
            continue
        if key in effects:
            out = out * effects[key] if default == 1.0 else out + effects[key]
    return out


def _first(holder):
    """(label, blurb, effects) of his personality / style, or None."""
    if holder.__class__.__name__ == "Coach":
        st = style(holder)
        return COACH_STYLES[st][:3] if st else None
    if hasattr(holder, "first_name"):
        return PERSONAS[persona(holder)][:3]
    return None


def labels(holder):
    table = COACH_TRAITS if holder.__class__.__name__ == "Coach" else PLAYER_TRAITS
    first = _first(holder)
    return ([first[0]] if first else []) + [table[t][0] for t in getattr(holder, "traits", ()) if t in table]


def blurbs(holder):
    table = COACH_TRAITS if holder.__class__.__name__ == "Coach" else PLAYER_TRAITS
    first = _first(holder)
    return ([(first[0], first[1])] if first else []) + \
        [(table[t][0], table[t][1]) for t in getattr(holder, "traits", ()) if t in table]


def persona_label(holder):
    first = _first(holder)
    return first[0] if first else ""


def dedupe(holder):
    """Older saves: a player could have been dealt the same trait twice."""
    seen = []
    for t in getattr(holder, "traits", []):
        if t not in seen:
            seen.append(t)
    if len(seen) != len(getattr(holder, "traits", [])):
        holder.traits = seen


def dedupe_league(league):
    for team in league.teams + getattr(league, "fcs_teams", []):
        for p in team.roster:
            dedupe(p)
            top_up(p)
        for c in (team.coach, getattr(team, "oc", None), getattr(team, "dc", None)):
            if c is not None:
                dedupe(c)
    cycle = getattr(league, "recruiting", None)
    for r in getattr(cycle, "pool", []) or []:
        dedupe(r.player)


# What each effect actually does, in a phrase: (when the number goes up, when it goes down).
_EFFECT_WORDS = {
    "recruit_close": ("closes recruits better", "closes recruits worse"),
    "recruit_eval": ("sees a recruit's real talent more clearly", "misjudges recruits more often"),
    "develop": ("players improve faster each offseason", "players improve slower"),
    "portal_hold": ("fewer players transfer out", "more players transfer out"),
    "portal_shop": ("lands more portal transfers", "lands fewer portal transfers"),
    "aggression": ("goes for it on fourth down more", "punts and kicks more"),
    "discipline": ("his teams draw more penalties", "his teams draw fewer penalties"),
    "heat": ("his seat heats up faster", "his seat heats up slower"),
    "big_game": ("team plays better vs ranked teams", "team plays worse vs ranked teams"),
    "rival": ("team plays better in rivalry games", "team plays worse in rivalry games"),
    "road": ("team plays better on the road", "team plays worse on the road"),
    "home": ("better at home", "worse at home"),
    "team_lift": ("lifts the whole team", "drags the team down"),
    "clutch": ("better late in close games", "worse late in close games"),
    "form": ("swings more game to game", "more consistent game to game"),
    "injury": ("gets hurt more often", "gets hurt less often"),
    "portal": ("more likely to transfer", "less likely to transfer"),
    "loyalty": ("sticks around through a coaching change", "more likely to leave after a coaching change"),
    "penalty": ("draws more flags", "draws fewer flags"),
    "late": ("better in November", "worse in November"),
    "early": ("better in September", "worse in September"),
    "weak": ("better against teams he should beat", "worse against teams he should beat"),
    "practice": ("looks better in practice than he is", "looks worse in practice than he is"),
    "role": ("takes depth-chart moves hard", "takes depth-chart moves in stride"),
    "chem": ("warms up the locker room", "cools the locker room"),
    "trouble": ("finds trouble off the field", "stays out of trouble"),
    "nil": ("wants to get paid", "doesn't chase the money"),
    "adjust": ("better halftime adjustments", "slow to adjust at halftime"),
    "off_iq": ("sharper offensive game calls", "duller offensive game calls"),
    "def_iq": ("sharper defensive game calls", "duller defensive game calls"),
    "eye": ("reads his own players more accurately", "misreads his own players more often"),
    "motivation": ("teams come out fired up", "teams come out flat"),
    "relations": ("players' moods rise under him", "players' moods sag under him"),
    "team_injury": ("more injuries on his roster", "fewer injuries on his roster"),
    "loyalty_hold": ("his veterans keep their jobs", "veterans get no special treatment"),
}
# Added rating points (0 = no effect); everything else is a multiplier (1.0 = no effect).
_ADDITIVE = {"aggression", "road", "home", "team_lift", "big_game", "rival", "late", "early", "weak",
             "practice", "chem", "trouble", "adjust", "off_iq", "def_iq", "motivation", "relations", "loyalty_hold"}


def effect_text(effects):
    """{'road': 0.8} → 'team plays better on the road'."""
    parts = []
    for k, v in effects.items():
        words = _EFFECT_WORDS.get(k)
        if not words:
            continue
        neutral = 0 if k in _ADDITIVE else 1.0
        if v != neutral:
            parts.append(words[0] if v > neutral else words[1])
    return "; ".join(parts)


def explain(holder):
    """[(label, one-line explanation)] — what he's like, and what that does.
    His personality (players) or coaching style (coaches) comes first."""
    table = COACH_TRAITS if holder.__class__.__name__ == "Coach" else PLAYER_TRAITS
    rows = []
    first = _first(holder)
    if first:
        rows.append(first)
    rows += [table[t] for t in getattr(holder, "traits", ()) if t in table]
    out = []
    for label, blurb, effects in rows:
        what = effect_text(effects)
        if table is PLAYER_TRAITS:
            what = what.replace("players improve", "improves")
        sentences = [blurb] + [w for w in what.split("; ") if w]
        out.append((label, ". ".join(x[0].upper() + x[1:] for x in sentences) + "."))
    return out


# How a person would say it on the air: (who he is, what that means). "Bill O'Brien is
# a relationship guy — he recruits families, not players."
COACH_SPEECH = {
    "closer": ("a closer on the recruiting trail", "he wins December"),
    "evaluator": ("a terrific evaluator", "he finds players nobody else sees"),
    "developer": ("a developer", "his three-stars leave as pros"),
    "ceo": ("a CEO-type head coach", "he runs the program and delegates the rest"),
    "players_coach": ("a players' coach", "they'd run through a wall for him"),
    "taskmaster": ("a taskmaster", "he's hard on them, and it works"),
    "gambler": ("a gambler", "he lives on the edge"),
    "disciplinarian": ("a disciplinarian", "his teams play clean, penalty-free football"),
    "portal_king": ("a portal guy", "he rebuilds the roster every winter"),
    "in_state": ("a fence builder", "nobody good leaves his state"),
    "national": ("a national recruiter", "he signs players from everywhere"),
    "salesman": ("a salesman", "he could sell sand in a desert"),
    "relationship": ("a relationship guy", "he recruits families, not players"),
    "misses": ("a coach who likes a highlight tape", "his evaluations have been hit and miss"),
    "juco_king": ("a junior college guy", "he plugs holes fast"),
    "hoarder": ("a volume recruiter", "he signs everybody and sorts it out later"),
    "qb_whisperer": ("a quarterback whisperer", "quarterbacks get better under him"),
    "trench_guru": ("a trench guy", "he builds lines that last"),
    "culture": ("a culture builder", "nobody wants to leave his program"),
    "burnout": ("a demanding coach", "he gets everything out of them — for about two years"),
    "delegator": ("a coach who trusts his staff", "he hires well and gets out of the way"),
    "micromanager": ("a hands-on coach", "he has a hand in everything"),
    "riverboat": ("a riverboat gambler", "fourth and four is a green light"),
    "conservative": ("a conservative coach", "he takes the points and plays for field position"),
    "clock_master": ("a sharp clock manager", "he never wastes a timeout"),
    "hothead_c": ("a fiery coach", "his teams play angry, and sometimes that costs them flags"),
    "motivator": ("a motivator", "his teams play over their heads"),
    "schemer": ("a schemer", "he'll out-design you on Saturday"),
    "lightning_rod": ("a lightning rod", "every loss turns into a talk-radio segment"),
    "teflon": ("bulletproof with his fan base", "nothing seems to stick to him"),
    "booster_fav": ("the boosters' favorite", "the money likes him, and it pays for his roster"),
    "old_school": ("an old-school coach", "he won't live in the portal and won't throw it forty times"),
    "big_game_c": ("a big-game coach", "his teams rise against ranked opponents"),
    "choker": ("a coach still chasing the signature win", "the biggest games have been tough on him"),
    "rivalry_c": ("a rivalry specialist", "he owns the game that matters most"),
    "road_dog": ("a road-game specialist", "his teams travel well"),
    "halftime": ("a halftime-adjustment guy", "his teams come out of the locker room different"),
    "rigid": ("a stick-to-the-plan coach", "plan A, all four quarters"),
    "off_guru": ("an offensive mind", "he sees the field like a quarterback"),
    "def_guru": ("a defensive mastermind", "he takes away what you do best"),
    "film_room": ("a film-room grinder", "he grades every snap himself"),
    "gut": ("a gut-feel coach", "he trusts instinct over the tape"),
    "tight_ship": ("a tight-ship coach", "curfews, bed checks, no exceptions"),
    "loose_ship": ("a players-are-adults coach", "he treats grown men like grown men"),
    "protector": ("a coach who protects his players", "he never runs them into the ground"),
    "grinds": ("a demanding practice coach", "full pads every Tuesday, all year"),
    "media_darling": ("a media darling", "the cameras love him, and so do recruits"),
    "prickly": ("prickly with the media", "every presser is a standoff"),
    "vet_trust": ("a coach who trusts his veterans", "seniors play — that's the deal"),
    "youth": ("a coach who plays the kids", "talent plays, whatever the class"),
    "motivator_x": ("a fiery speech-giver", "he can get them up for anybody"),
    "flat_teams": ("an even-keeled coach", "his teams don't ride emotion"),
}
# Reputations that are knocks on a man. The booth doesn't pin these on real coaches.
NEGATIVE_COACH_TRAITS = {"choker", "misses", "burnout", "micromanager", "hothead_c", "lightning_rod", "rigid",
                         "prickly", "flat_teams", "loose_ship", "gut"}


def is_real_coach(coach):
    """A real head coach (from the 2026 data), not one this world invented."""
    try:
        from coaches_data import HEAD_COACHES
    except ImportError:
        return False
    return getattr(coach, "name", None) in set(HEAD_COACHES.values()) and not getattr(coach, "is_user", False)


def speakable_traits(coach):
    """Trait keys the booth can talk about for this coach."""
    out = [t for t in getattr(coach, "traits", []) if t in COACH_SPEECH]
    if is_real_coach(coach):
        out = [t for t in out if t not in NEGATIVE_COACH_TRAITS]
    return out


def dev_bonus(coach, position):
    """How much a coach's position-scoped traits add to his development rating
    at one position, in rating points (for display): +15% ≈ +8 points."""
    if coach is None:
        return 0
    return sum(8 for t in getattr(coach, "traits", ()) if position in POSITION_SCOPE.get(t, ()))


# The pairs added in v28: older saves deal them out once, so returning rosters get as varied as new ones.
_V28_PAIRS = _PLAYER_PAIRS[-10:]


def top_up(p):
    if p.__dict__.get("_v28"):
        return
    p.__dict__["_v28"] = True
    import random as _r
    rng = _r.Random(f"v28:{p.name}")
    persona(p)
    have = list(getattr(p, "traits", []) or [])
    if len(have) >= 3:
        return
    for a, b in _V28_PAIRS:
        roll = rng.random()
        t = a if roll < TRAIT_ODDS * 1.6 else b if roll < TRAIT_ODDS * 3.2 else None
        if t is None or t in have:
            continue
        if any((t, k) in _PLAYER_PAIRS or (k, t) in _PLAYER_PAIRS for k in have):
            continue
        have.append(t)
        if len(have) >= 3:
            break
    p.traits = have


def penalty_norm():
    """The league-wide average flag multiplier from traits and personalities (so they move flags between
    players without adding flags overall)."""
    tr = 1 + TRAIT_ODDS * sum(fx.get("penalty", 1.0) - 1 for _, _, fx in PLAYER_TRAITS.values())
    tot = sum(v[3] for v in PERSONAS.values())
    pe = sum(v[3] * v[2].get("penalty", 1.0) for v in PERSONAS.values()) / tot
    return tr * pe
