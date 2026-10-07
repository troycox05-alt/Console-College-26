"""
commentary.py — The broadcast booth.

Two broadcasters call the game the way a TV booth does: the play-by-play
voice describes what happens in plain football language, and the analyst
explains why — who got beat, who made the play, what the defense was
trying to do. Between plays they talk: stat lines, injuries, what each team
needs with the clock and score, coaching tendencies, the crowd, the
rivalry, and callbacks to players who keep showing up.

Every line is built from what actually happened on the field (the engine
records carriers, tacklers and why they made the tackle, pressure,
coverage, air yards, broken tackles, and so on) plus the game state.
Topics have cooldowns so the booth doesn't repeat itself.

Play and coverage names are hidden by default; toggle "coach's view" at any
quarter break to see both calls on every snap.

Booths and broadcasters are fictional.
"""
import world
import random
import re
import textwrap
import time
from collections import Counter

from booth_lines import LINES, TAKES
import postseason as ps
from traits import COACH_TRAITS
from booth_banter import BANTER, WAR_STORIES, WEATHER, WEATHER_OPEN
from team_lore import TEAM_LORE
from ui import C, WIDTH, paint, pad, rule

BOOTHS = [
    {"pbp": "Dale Whitmore", "color": "Jackie Ruiz", "bio": "former All-American linebacker", "role": "linebacker",
     "td": ["TOUCHDOWN, {team}!", "He's in! Touchdown, {team}!"],
     "big": ["Oh, what a play!", "Are you kidding me?!"], "open": "Good evening, everybody, from {venue}."},
    {"pbp": "Hank Delacroix", "color": "Marcus Pell", "bio": "former quarterback and offensive coordinator", "role": "quarterback",
     "td": ["He's IN! Six for {team}!", "Touchdown {team}!"],
     "big": ["Look out!", "Oh my!"], "open": "What a setting here at {venue}."},
    {"pbp": "Tom Brandvold", "color": "Keisha Grant", "bio": "former sideline reporter turned analyst", "role": "reporter",
     "td": ["Touchdown {team} — and this place is shaking!", "TOUCHDOWN, {team}!"],
     "big": ["Wow!", "What a play!"], "open": "Hello again from {venue}, where the tailgates have been going since sunrise."},
    {"pbp": "Rusty Oakes", "color": "Dan Sutter", "bio": "former offensive lineman", "role": "lineman",
     "td": ["Ohhh, SIX! {team} strikes!", "Touchdown, {team}!"],
     "big": ["Hang on now!", "Oh, baby!"], "open": "Welcome in to {venue}. Grab a seat, this should be a good one."},
    {"pbp": "Gil Navarro", "color": "Bree Hollis", "bio": "former defensive coordinator", "role": "coordinator",
     "td": ["Into the end zone — touchdown {team}!", "Touchdown, {team}!"],
     "big": ["Oh, look at this!", "What an effort!"], "open": "Good afternoon from {venue}."},
    {"pbp": "Walt Kimbrough", "color": "Nate Ferris", "bio": "former All-Conference safety", "role": "safety",
     "td": ["TOUCHDOWN! {team} finds paydirt!", "Touchdown, {team}!"],
     "big": ["Whoa!", "Big play!"], "open": "Hi everybody, and welcome to {venue}."},
]

SPEEDS = {"1": ("Slow", 2.6), "2": ("Normal", 1.3), "3": ("Fast", 0.4), "4": ("Instant", 0.0)}

RIVALRIES = {
    ('Alabama', 'East Alabama'): 'the Iron and Pine',
    ('Michigan', 'Ohio State'): 'the Toledo War',
    ('Oklahoma', 'Texas'): 'the Midway Melee',
    ('Florida', 'Georgia'): 'the St. Marys Classic',
    ('Hudson', 'Chesapeake'): 'the Cannon and Anchor',
    ('Mississippi State', 'Mississippi'): 'the Magnolia Cup',
    ('Washington', 'Washington State'): 'the Snoqualmie Showdown',
    ('Georgia', 'Atlanta'): 'the Peachtree Grudge',
    ('Upcountry', 'South Carolina'): 'the Statehouse Feud',
    ('Florida', 'Florida State'): 'the Turnpike Tussle',
    ('Michigan', 'Michigan State'): 'the battle for the Mitten',
    ('Indiana', 'Tippecanoe'): 'the battle for the Copper Kettle',
    ('Minnesota', 'Wisconsin'): 'the battle for the Northwoods Saw',
    ('Provo', 'Utah'): 'the Wasatch War',
    ('Arizona', 'Arizona State'): 'the Canyon State Cup',
    ('Pittsburgh', 'West Virginia'): 'the Coal Country Clash',
    ('California', 'Palo Alto'): 'the Bay Classic',
    ('Iowa', 'Iowa State'): 'the Tall Corn game',
    ('Kansas', 'Kansas State'): 'the Kaw Valley Clash',
    ('Alabama', 'Tennessee'): 'the October Feud',
    ('Texas', 'Brazos'): 'the Hill Country Clash',
    ('East Alabama', 'Georgia'): 'the Chattahoochee Classic',
    ('Kentucky', 'Louisville'): 'the Bluegrass Bell game',
    ('Virginia', 'Blacksburg'): 'the Blue Ridge Divide',
    ('Durham', 'North Carolina'): 'the Ten-Mile War',
    ('Los Angeles', 'Southern California'): 'the Sunset Showdown',
    ('Oregon', 'Oregon State'): 'the Willamette War',
    ('Nebraska', 'Iowa'): 'the Missouri Crossing',
}

OFF_STYLE = {
    "Air Raid": "throw it all over the field", "Spread RPO": "spread you out and make your linebackers guess",
    "Pro Style": "line up and play balanced, physical football", "West Coast": "move the chains with quick, short throws",
    "Smashmouth": "run it right at you", "Triple Option": "grind you down with the option",
    "Power Spread": "spread you out, then hit you with downhill runs", "Veer & Shoot": "stretch you vertically and play fast",
}
DEF_STYLE = {
    "4-3 Zone": "keep everything in front of them", "4-2-5 Quarters": "take away the big play and rally to the ball",
    "Pressure 3-4": "bring pressure from everywhere", "3-3-5 Stack": "disguise things and bring pressure from odd angles",
    "Multiple Man": "play tight man coverage and challenge receivers", "Tite Front": "clog the middle and make you earn every yard",
}
EDGE_RUNS = {"outside_zone", "toss", "pin_pull", "crack_toss", "jet", "reverse", "speed_option"}
CLASS_WORDS = ("freshman", "sophomore", "junior", "senior")
POS_WORDS = {"QB": "quarterback", "RB": "running back", "WR": "receiver", "TE": "tight end", "OL": "lineman",
             "DL": "defensive lineman", "LB": "linebacker", "CB": "cornerback", "S": "safety", "K": "kicker",
             "P": "punter"}
NUM_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
STAR_WORDS = {3: "three-star", 4: "four-star", 5: "five-star"}


def num_words(x):
    """2 → 'two', 1.5 → 'one and a half' (split sacks and tackles for loss)."""
    whole = int(x)
    return NUM_WORDS[min(whole, 10)] + (" and a half" if x % 1 else "")


class _Blanks(dict):
    def __missing__(self, key):
        return ""


def clock_str(seconds):
    return f"{int(seconds) // 60:d}:{int(seconds) % 60:02d}"


def ordinal(n):
    """1st, 2nd, 3rd, 4th ... 11th, 12th, 13th ... 21st, 22nd."""
    n = int(n)
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


_WORD_ORD = {"one": "first", "two": "second", "three": "third", "four": "fourth", "five": "fifth",
             "six": "sixth", "seven": "seventh", "eight": "eighth", "nine": "ninth", "ten": "tenth"}


def fix_ordinals(text):
    """A template's '{n}th' filled with a number or a word: 'threeth' → 'third', '3th' → '3rd'."""
    def word(m):
        w = _WORD_ORD[m.group(1).lower()]
        return w.capitalize() if m.group(1)[0].isupper() else w
    # Only the forms that aren't words ("threeth"); "fourth", "sixth" and "tenth" are fine as they are.
    text = re.sub(r"\b(one|two|three|five|eight)th\b", word, text, flags=re.I)
    return re.sub(r"\b(\d+)th\b", lambda m: ordinal(m.group(1)), text)


def ordinal_word(n):
    """'first', 'second', 'third' ... for the booth ('his third touchdown pass')."""
    words = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
             8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}
    return words.get(int(n), ordinal(n))


def down_distance(sim):
    return f"{ordinal(sim.down)} & {'Goal' if sim.togo >= 100 - sim.yardline else sim.togo}"


def _dd_words(down, togo, yardline):
    d = ("", "First", "Second", "Third", "Fourth")[min(down, 4)]
    if togo >= 100 - yardline:
        return f"{d} and goal"
    return f"{d} and {'inches' if togo < 1 else togo}"


def _yds(n):
    n = abs(int(n))
    return "a yard" if n == 1 else f"{n} yards"


def rivalry_name(a, b):
    return RIVALRIES.get((a.school, b.school)) or RIVALRIES.get((b.school, a.school))


def _grammar(text):
    """Yardage that reads like a person said it: '1 yard', 'loses a yard', no '-3 yards' returns."""
    text = re.sub(r"(returns it|brings it back|picks up) -(\d+) yards?", lambda m: f"is dropped for a loss of {m.group(2)}", text)
    text = re.sub(r"(returns it|brings it back|picks up) 0 yards", "is swarmed right where he caught it", text)
    text = re.sub(r"\b(?<![-\d])1 yards\b", "1 yard", text)
    text = re.sub(r"\b1-yards\b", "1-yard", text)
    text = re.sub(r"Gain of 0\b", "No gain", text)
    text = re.sub(r"Goal to go\. 1 yard to paydirt", "Goal to go from the 1", text)
    return text


_VOWEL_LETTERS = set("AEFHILMNORSX")          # letters whose names start with a vowel sound: "an SCC", "an FBS"
_CONSONANT_SOUND = ("uni", "unan", "use", "usu", "uti", "ute", "uto", "eu", "one", "once", "ufo", "utah", "ubiq",
                    "ura", "uri", "usa")
_SILENT_H = ("hour", "honest", "honor", "honour", "heir")
# Said letter by letter. Anything else in an all-caps sign is read as a word.
KNOWN_ACRONYMS = {'ACL', 'AP', 'CAB', 'CB', 'CMU', 'DL', 'ECU', 'EMU', 'ER', 'FAU', 'FBS', 'FCS', 'GPS', 'HBCU', 'LA', 'LB', 'LV', 'MRI', 'MVP', 'NC', 'NIL', 'NIU', 'NJ', 'NP', 'OL', 'OT', 'QB', 'RB', 'RPO', 'RV', 'SCC', 'SUV', 'TE', 'TV', 'WMU', 'WR'}


def _wants_an(word, shouting=False):
    w = word.strip("\"'“”‘’(")
    if not w:
        return None
    if w[0].isdigit():
        n = re.match(r"\d+", w).group(0)
        return n[0] == "8" or n in ("11", "18") or (len(n) in (5, 6) and n[:2] in ("11", "18"))
    letters = re.sub(r"[^A-Za-z]", "", w)
    if not letters:
        return None
    # An acronym is said letter by letter: a Seaboard game, an SCC title, a Orlando win. In an
    # all-caps sign or chant every word is capitalized, so only known acronyms count
    # there: "AN SCC TITLE", but "A MAP" and "AN AGGIE".
    if letters.isupper() and 2 <= len(letters) <= 5:
        if letters in KNOWN_ACRONYMS:
            return letters[0] in _VOWEL_LETTERS
        if not shouting:
            return letters[0] in _VOWEL_LETTERS
    low = letters.lower()
    if low.startswith(_SILENT_H):
        return True
    if low.startswith(_CONSONANT_SOUND):
        return False
    return low[0] in "aeiou"


def articles(text):
    """'a Seaboard game' → 'a Seaboard game'; 'A AGGIE' → 'AN AGGIE'; 'an Utah' → 'a Utah'."""
    letters = re.sub(r"[^A-Za-z]", "", text)
    shouting = len(letters) > 8 and letters.isupper()

    def fix(m):
        art, word = m.group(1), m.group(2)
        before = text[:m.start()].rstrip()
        prev = before.split()[-1] if before.split() else ""
        loud = prev.isupper() and len(re.sub(r"[^A-Za-z]", "", prev)) > 1 and word.isupper()
        if art == "A" and not (shouting or loud) and before and before[-1].isalnum():
            return m.group(0)                       # "Plan A is", "Group A and" — a letter, not an article
        if loud:
            an = _wants_an(word, True)
            if an is None or not an:
                return m.group(0)
            return f"AN {word}"
        an = _wants_an(word, shouting or (art.isupper() and len(art) > 1) or (art == "A" and word.isupper()
                                                                                and len(word) > 5))
        if an is None:
            return m.group(0)
        if art.lower() == "a" and an:
            new = "AN" if (art == "A" and (shouting or word.isupper() and len(word) > 5)) else ("An" if art == "A" else "an")
        elif art.lower() == "an" and not an:
            new = "A" if art[0] == "A" else "a"
        else:
            return m.group(0)
        return f"{new} {word}"

    return re.sub(r"\b(a|A|an|An|AN)\s+([\"'“‘(]?[A-Za-z0-9][\w'&\-]*)", fix, text)


_RECENT = {"banter": [], "stories": {}}     # shared across broadcasts so the booth doesn't retell a story


# Things a booth says once a game: next week's schedule, the marquee game, last week.
ONCE = {"_t_next_marquee", "_t_next_week", "_t_last_week", "_t_program", "_t_coach_trait", "_t_form",
        "_t_bowl_math", "_t_revenge", "_t_race"}


class Narrator:
    def __init__(self, booth_index=0, delay=1.3, rng=None, league=None):
        self.booth = BOOTHS[booth_index % len(BOOTHS)]
        self.P = self.booth["pbp"].split()[-1]
        self.A = self.booth["color"].split()[-1]
        self.delay = delay
        self.rng = rng or random.Random()
        self.muted = False
        self.show_calls = False
        self.cool = {}                 # topic -> snap number last used
        self.last_chat = -99
        self.introduced = set()
        self.hot = Counter()           # notable plays per player, for callbacks
        self.cur = None
        self.snap = 0
        self.lead_changes = 0
        self._leader = None
        self._used = {}
        self.explosives = Counter()      # 20+ yard plays, by team
        self.rz_trips = Counter()
        self.rz_tds = Counter()
        self._rz_flag = None
        self.drive_log = {}              # team -> list of drive results
        self.streak = None               # (team, kind, count)
        self.biggest_lead = Counter()
        self.fourth_tries = Counter()
        self._ot_first = None
        self._ot_possession = 0
        self._game_over = False
        self._last_qb = {}
        self.league = league             # optional: rankings, history, standings for context
        self.gtype = "Regular Season"
        self.weather = {}
        self._ms_done = set()            # (player id, milestone) already called
        self._must = False               # True while the plays themselves are being called
        self._last_speaker = None
        self._run = [None, 0, 0]         # [team, points, score at last check] unanswered scoring run
        self._last_pts = {}

    # ── output ────────────────────────────────────────────────────────────
    def _log_play(self, text):
        """The play-by-play the tablet shows: what the booth called on each snap, newest last."""
        ctx = self.__dict__.get("_ctx")
        if ctx is None or not text:
            return
        t = articles(_grammar(text)).strip()
        t = t[:1].upper() + t[1:]
        log = self.__dict__.setdefault("play_log", [])
        if self.__dict__.get("_ctx_open"):                   # inside a snap: everything said about it is one entry
            if log and log[-1]["snap"] == self.snap and log[-1]["down"] is not None:
                log[-1]["text"] += " " + t
            else:
                log.append({"q": ctx[0], "clock": ctx[1], "down": ctx[2], "togo": ctx[3], "yl": ctx[4], "off": ctx[5],
                            "snap": self.snap, "text": t})
        else:                                                # between snaps: a kickoff, a review, a coin toss
            sim = self.__dict__.get("_sim")
            q, clock = (sim.quarter, sim.clock) if sim is not None else (ctx[0], ctx[1])
            log.append({"q": q, "clock": clock, "down": None, "togo": None, "yl": None, "off": ctx[5],
                        "snap": self.snap, "text": t})
        del log[:-40]

    def _speak(self, who, text, *styles, must=False):
        if who == "P" and text and (must or self._must):
            self._log_play(text)
        if self.muted or not text:
            return
        # A sentence never starts lowercase ("It's good. tied at 31" → "Tied at 31"); ellipses stay as they are.
        text = re.sub(r"(?<!\.)(?<!vs)([.!?]) ([a-z])", lambda m: f"{m.group(1)} {m.group(2).upper()}", text)
        text = text[:1].upper() + text[1:]
        text = _grammar(text)
        text = articles(text)
        text = self._time_words(text)
        if not must and not self._must:
            text = self._fresh_only(text)
            if not text:
                return
        self._last_speaker = who
        name = self.P if who == "P" else self.A
        head = f"{name}:".ljust(len(max(self.P, self.A, key=len)) + 2)
        lines = textwrap.wrap(text, WIDTH - len(head) - 4) or [""]
        color = C.BWHITE if who == "P" else C.BCYAN
        print("  " + paint(head, C.BOLD, color) + (paint(lines[0], *styles) if styles else lines[0]))
        for ln in lines[1:]:
            print("  " + " " * len(head) + (paint(ln, *styles) if styles else ln))
        self.wait(1.0 if who == "A" else 0.7)

    def pbp(self, text, *styles, must=False):
        self._speak("P", text, *styles, must=must)

    def analyst(self, text, *styles, must=False):
        self._speak("A", text, *styles, must=must)

    # Things the booth says between plays can't come back word for word: a sentence
    # of any length can't repeat within a quarter's worth of snaps, and a long one
    # (a plug, a take, a story) can't repeat at all. The calls of the plays themselves
    # are exempt — "Incomplete" is allowed to happen twice.
    REPEAT_SNAPS = 45

    def _fresh_only(self, text):
        said = self.__dict__.setdefault("_said", {})
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
        keep = []
        for part in parts:
            key = re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
            if len(key) >= 18:
                last = said.get(key)
                window = 10 ** 9 if len(key) >= 40 else self.REPEAT_SNAPS
                if last is not None and self.snap - last < window:
                    continue
                said[key] = self.snap
            keep.append(part)
        return " ".join(keep).strip()

    def _time_words(self, text):
        """'All afternoon' at a night game is 'all night' — the booth knows what time it is."""
        cached = getattr(self, "_tod_cache", None)
        if not cached:
            return text
        tod = cached[1]
        if tod in ("evening", "night"):
            text = re.sub(r"\ball afternoon\b", "all night", text)
            text = re.sub(r"\bthis afternoon\b", "tonight", text)
            text = re.sub(r"\ball day\b", "all night", text)
        else:
            text = re.sub(r"(?<!Later )(?<!later )\btonight\b", "today", text)
            text = re.sub(r"\ball night\b", "all day", text)
            text = re.sub(r"\bthis evening\b", "today", text)
        return text

    def note(self, text):
        if not self.muted:
            print("  " + paint(text, C.GRAY))

    def out(self, text="", *styles, indent=4):
        if self.muted:
            return
        text = articles(text)                   # the crowd's chant too: "TO BE AN AGGIE"
        for line in textwrap.wrap(text, WIDTH - indent - 2) or [""]:
            print(" " * indent + (paint(line, *styles) if styles else line))

    def wait(self, scale=1.0):
        if not self.muted and self.delay:
            time.sleep(self.delay * scale)

    def scoreline(self, sim):
        a, h = sim.away, sim.home
        return f"{a.abbr} {sim.score[a]}  {h.abbr} {sim.score[h]}"

    def chance(self, p):
        return self.rng.random() < p

    def pick(self, *options):
        return self.rng.choice(options)

    def line(self, key, _avoid=(), **kw):
        if "score" in kw and isinstance(kw["score"], str) and kw["score"]:
            kw.setdefault("Score", kw["score"][0].upper() + kw["score"][1:])
        return self._draw(LINES, key, kw, _avoid)

    def take(self, key, _avoid=(), **kw):
        return self._draw(TAKES, key, kw, _avoid)

    def road_words(self, sim, team):
        """Phrases a take can't use for this team: no 'on the road' for the home side."""
        if team is sim.away and not sim.neutral:
            return ()
        return ("on the road",)

    def _draw(self, bank, key, kw, avoid=()):
        """Pull a phrasing, avoiding the ones used most recently for this key."""
        pool = bank.get(key)
        if not pool:
            return ""
        late = ("this time of year", "November", "down the stretch", "this late in the")
        wk = getattr(self, "_week", 13)
        if wk < 9:
            avoid = tuple(avoid) + late                 # it's September: nobody's in the stretch run
        if avoid:
            pool = [p for p in pool if not any(a in p for a in avoid)]
            if not pool:
                return ""
        blanks = [k for k, v in kw.items() if v in ("", None)]
        if blanks:
            clean = [p for p in pool if not any("{" + b + "}" in p for b in blanks)]
            if clean:
                pool = clean
        used = self._used.setdefault(key, [])
        fresh = [p for p in pool if p not in used] or pool
        choice = self.rng.choice(fresh)
        used.append(choice)
        while len(used) > max(2, len(pool) - 1):
            used.pop(0)
        return fix_ordinals(choice.format_map(_Blanks(kw)))

    # ── reading the game ──────────────────────────────────────────────────
    def ctx(self, sim, off=None):
        off = off or sim.offense
        df = sim.other(off)
        diff = sim.score[off] - sim.score[df]
        return {
            "ot": sim.quarter > 4,
            "diff": diff,
            "one_score": abs(diff) <= 8,
            "blowout": abs(diff) >= 21,
            "late": sim.quarter == 4 and sim.clock <= 300,
            "final_minute": sim.quarter == 4 and sim.clock <= 60,
            "half_end": sim.quarter == 2 and sim.clock <= 120,
            "ytg_end": 100 - sim.yardline,
            "red_zone": 100 - sim.yardline <= 20,
            "backed_up": sim.yardline <= 10,
            "off": off, "df": df,
        }

    def ot_stakes(self, sim, off):
        """In overtime, what this possession actually needs to do."""
        diff = sim.score[off] - sim.score[sim.other(off)]
        second = self._ot_possession >= 2
        if not second:
            return self.line("ot_win_score", nick=off.nickname) if sim.ot_round >= 3 else ""
        if diff < 0:
            if diff <= -7:
                return self.line("ot_must_td")
            if diff == -3:
                return self.line("ot_tie_fg")
            return self.line("ot_must_td")
        return self.line("ot_win_score", nick=off.nickname)

    def ot_decisive(self, sim):
        """True when a stop or score right now ends the game."""
        return sim.quarter > 4 and self._ot_possession >= 2 and sim.score[sim.home] != sim.score[sim.away]

    def _walkoff(self, sim, how):
        if self._game_over:
            return
        lead = sim.score[sim.home] - sim.score[sim.away]
        if lead == 0:
            return
        winner = sim.home if lead > 0 else sim.away
        if sim.quarter > 4 and not self.ot_decisive(sim):
            return
        if sim.quarter <= 4 and not (sim.quarter == 4 and sim.clock <= 0):
            return
        self.pbp(self.line("walkoff_stop" if how == "stop" else "walkoff_score", team=winner.school),
                 C.BOLD, C.BYELLOW)
        self._game_over = True

    # ── names & places ────────────────────────────────────────────────────
    def name(self, p):
        """Full name (with a little bio) the first time, last name after."""
        if p is None:
            return "somebody"
        if id(p) in self.introduced:
            return self.ln(p)
        self.introduced.add(id(p))
        return f"{p.first_name} {p.last_name}"

    def ln(self, p):
        """What the booth calls him after the introduction: his last name — unless
        somebody else in this game has it too, and then it's both names, every time."""
        if p is None:
            return ""
        last = p.last_name
        if last in getattr(self, "_shared_last", ()):
            return f"{p.first_name} {last}"
        return last

    def _find_shared_names(self, sim):
        seen, shared = set(), set()
        for t in sim.teams:
            for p in t.roster:
                (shared if p.last_name in seen else seen).add(p.last_name)
        self._shared_last = shared

    def bio(self, p):
        cls = ("redshirt " if getattr(p, "redshirt", False) else "") + CLASS_WORDS[min(p.year, 3)]
        out = f"the {p.height // 12}-{p.height % 12}, {p.weight}-pound {cls} {POS_WORDS.get(p.position, '')}".strip()
        t = getattr(p, "team", None)
        if t is not None and p in (getattr(t, "captains", None) or []) and getattr(t, "captains_year", 0) == \
                (self.league.year if self.league else getattr(t, "captains_year", 0)):
            out += ", one of the team captains"
        return out

    def spot(self, sim, yl, team):
        yl = int(round(yl))
        if yl <= 0:
            return "his own end zone"
        if yl >= 100:
            return "the end zone"
        if yl == 50:
            return "midfield"
        if yl < 50:
            return f"the {team.school} {yl}"
        return f"the {sim.other(team).school} {100 - yl}"

    def score_words(self, sim):
        a, h = sim.away, sim.home
        sa, sh = sim.score[a], sim.score[h]
        if sa == sh:
            return f"tied at {sa}" if sa else "scoreless"
        lead, trail = (a, h) if sa > sh else (h, a)
        return f"{lead.school} {max(sa, sh)}, {trail.school} {min(sa, sh)}"

    def time_words(self, sim):
        if sim.quarter > 4:
            return "in overtime"
        q = ("", "first", "second", "third", "fourth")[sim.quarter]
        if sim.quarter == 4 and sim.clock < 300:
            return f"with {clock_str(sim.clock)} to play"
        if sim.quarter == 2 and sim.clock < 180:
            return f"with {clock_str(sim.clock)} left in the half"
        if sim.clock > 600:
            return f"early in the {q} quarter"
        if sim.clock > 300:
            return f"midway through the {q}"
        return f"late in the {q} quarter"

    def stat(self, sim, p, key):
        return sim.stats.get(p, Counter())[key]

    def mark_hot(self, p):
        if p is not None:
            self.hot[id(p)] += 1
            return self.hot[id(p)]
        return 0

    def ticker(self, sim):
        if self.muted or getattr(self, "_quiet_ticker", False):
            return
        import fieldview
        if fieldview.mode() in fieldview.TABLET_MODES and sim.offense is not None:
            import tabletview
            tabletview.show(sim, narr=self)                # the whole tablet, once per snap
            return
        q = f"Q{sim.quarter}" if sim.quarter <= 4 else f"OT{sim.ot_round}"
        clk = f" {clock_str(sim.clock):>5}" if sim.quarter <= 4 else ""
        spot = sim.spot()
        print()
        print("  " + paint(f"{q}{clk} · {self.scoreline(sim)} · {down_distance(sim)}, {spot}", C.GRAY))
        import fieldview
        fieldview.show(sim, indent=2)                     # the field, with the ball on it

    # ── context from the wider world ──────────────────────────────────────
    @property
    def post(self):
        return self.gtype != "Regular Season"

    def rank(self, team):
        return self.league.rankings.rank_of(team) if self.league is not None else None

    def rname(self, team):
        r = self.rank(team)
        return f"No. {r} {team.school}" if r else team.school

    def _streak(self, team):
        """(kind, n): current win or loss streak this season, games already played."""
        if self.league is None:
            return None, 0
        games = [g for g in self.league.team_games(team) if g.played]
        kind, n = None, 0
        for g in reversed(games):
            k = "W" if g.winner is team else "L"
            if kind is None:
                kind = k
            if k != kind:
                break
            n += 1
        return kind, n

    def _mvp(self, sim, team, defense=False):
        best, score, line = None, 0, ""
        for p, c in sim.stats.items():
            if sim.team_of(p) is not team:
                continue
            from impact import defense_impact, offense_impact
            v = defense_impact(c) if defense else offense_impact(c)
            if v > score:
                best, score = p, v
        if best is None:
            return None, ""
        c = sim.stats[best]
        if defense:
            bits = [f"{c['tkl']} tackles"]
            for k, lbl in (("sack", "sack"), ("int", "interception"), ("tfl", "tackle for loss"), ("ff", "forced fumble")):
                if c[k]:
                    bits.append(f"{c[k]:g} {lbl}{'s' if c[k] != 1 else ''}")
            return best, ", ".join(bits)
        if c["pass_att"] >= 10:
            line = f"{c['pass_cmp']} of {c['pass_att']} for {c['pass_yds']} yards and {c['pass_td']} touchdown{'s' if c['pass_td'] != 1 else ''}"
            if c["pass_int"]:
                line += f", {c['pass_int']} interception{'s' if c['pass_int'] != 1 else ''}"
            if c["rush_yds"] >= 50:
                line += f", plus {c['rush_yds']} on the ground"
        elif c["rush_att"] >= c["rec"]:
            line = f"{c['rush_att']} carries, {c['rush_yds']} yards, {c['rush_td']} touchdown{'s' if c['rush_td'] != 1 else ''}"
        else:
            line = f"{c['rec']} catches, {c['rec_yds']} yards, {c['rec_td']} touchdown{'s' if c['rec_td'] != 1 else ''}"
        return best, line

    def _play_caller_note(self, team):
        """Who has the play sheet — worth knowing before kickoff."""
        import staff
        oc, dc = staff.play_caller(team, "off"), staff.play_caller(team, "def")
        hc = team.coach
        if oc is hc and dc is hc:
            return f"{hc.name} calls both sides for {team.school} — the offense and the defense. That's rare."
        if oc is hc:
            return self.pick(f"{hc.name} calls his own offense at {team.school}; {dc.name} runs the defense.",
                             f"Keep an eye on the {team.school} sideline — {hc.name} has the offensive play sheet himself.")
        if dc is hc:
            return self.pick(f"{hc.name} is a defensive guy and he calls that side himself. {oc.name} has the offense.",
                             f"{team.school}'s defense is {hc.name}'s baby — he calls it. His OC, {oc.name}, runs the offense.")
        return self.pick(f"{hc.name} is a CEO-type head coach. {oc.name} calls the offense, {dc.name} the defense.",
                         f"At {team.school}, the coordinators call it: {oc.name} on offense, {dc.name} on defense.")

    def _crowd_call(self, g, h, vname):
        """Say something about who showed up — a packed house, or a lot of empty seats."""
        att, fill = getattr(g, "attendance", None), getattr(g, "fill", None)
        if att is None or fill is None or getattr(g, "neutral", False):
            return ""
        why = getattr(g, "crowd_why", "") or ""
        if getattr(g, "sellout", False):
            if "rivalry" in why:
                return self.pick(f"Not an empty seat in {vname}. It's a rivalry game — it always sells.",
                                 f"{att:,} packed in. Rivalry week sells itself.")
            if "home opener" in why:
                return self.pick(f"Home opener, and they've sold every seat — {att:,} in {vname}.",
                                 f"A sellout for the opener. {att:,} strong. This place has been waiting all summer.")
            return self.pick(f"A sellout crowd of {att:,}. It's going to be loud.",
                             f"{att:,} — every seat in {vname} is taken.", "Sold out. Standing room only.") \
                if self.chance(0.7) else ""
        if fill < 0.62:
            if "disappointing" in why:
                return self.pick(f"A lot of empty seats in {vname} today — about {att:,} in a building that holds "
                                 f"{g.capacity:,}. The fans are telling you how they feel about this season.",
                                 f"You can hear individual voices in the stands. {att:,} here. When {h.school} "
                                 f"loses, people stay home.")
            return self.pick(f"A modest crowd — about {att:,} in a stadium that holds {g.capacity:,}.",
                             f"Plenty of room in {vname} today. The announced crowd is {att:,}.") \
                if self.chance(0.6) else ""
        if fill < 0.8 and self.chance(0.35):
            st = getattr(h, "stad", None)
            where = "the upper deck" if st and st["parts"].get("upper_deck") else "the end zones" \
                if st and st["parts"].get("end_zones") else "the corners"
            return f"A decent crowd, {att:,}, but there are some gaps in {where}."
        return ""

    def _stadium_call(self, g, h, vname):
        """Something new in the building this year, or a place with a reputation."""
        if getattr(g, "neutral", False) or self.post or not getattr(h, "stad", None) or self.league is None:
            return ""
        import stadium as sd
        yr = self.league.year
        new = [k for k, y in h.stad.get("opened", {}).items() if y == yr]
        homes = [x for x in sd.home_games(self.league, h)]
        if new and len(homes) <= 1:
            k = max(new, key=lambda k: sd.PARTS[k]["cost"][h.stad["parts"][k]])
            name = sd.tier_name(k, h.stad["parts"][k]).lower()
            if sd.PARTS[k]["seats"]:
                return self.pick(f"First look at the new {name} at {vname} — capacity is up to {h.capacity:,} now.",
                                 f"They finished the {name} over the summer. {vname} holds {h.capacity:,} today.")
            return self.pick(f"New this year at {vname}: the {name}. {h.school} has been building.",
                             f"You'll notice the {name} — that's new this season at {vname}.")
        rk = sd.rank_of(self.league, h)
        if rk and rk <= 10 and self.chance(0.35):
            return self.pick(f"{vname} is on everybody's list of the toughest places to play — No. {rk} right now.",
                             f"Ask any visiting coach: {vname} is one of the ten hardest places in the country to win.")
        if h.stad["parts"].get("visitor_locker") and self.chance(0.25):
            return self.pick(f"{g.away.school} dressed in the visitors' locker room here. Nobody enjoys that.",
                             "The visiting locker room here is famous for all the wrong reasons.")
        return ""

    def _tod(self, sim):
        cached = getattr(self, "_tod_cache", None)
        if cached and cached[0] is sim.game:
            return cached[1]                            # one kickoff, one time of day, all game
        k = getattr(sim.game, "kick", None)
        if k is None:
            tod = "evening" if sim.game.game_type in ("National Championship", "NP Semifinal") else \
                self.pick("afternoon", "evening", "afternoon")
        else:
            tod = "morning" if k < 12 * 60 else "afternoon" if k < 17 * 60 else "evening" if k < 22 * 60 else "night"
        self._tod_cache = (sim.game, tod)
        return tod

    def _post_kw(self, sim):
        g = sim.game
        a, h = sim.away, sim.home
        venue_full = g.venue or h.stadium
        venue = venue_full.split(",")[0]
        site = ", ".join(venue_full.split(", ")[1:]) or venue
        conf = (g.bowl_name or "").replace(" Championship", "")
        tsite = ps.title_site(self.league.year if self.league else 2026)
        return dict(a=a.school, h=h.school, bowl=g.display_name or g.bowl_name or "", venue=venue,
                    site=site.split(",")[0], conf=conf, date=ps.short_date(g.next_date),
                    next=g.next_game or "", title_site=tsite[1].split(",")[0], tod=self._tod(sim),
                    year=self.league.year if self.league else "", seed_a=ps.seed_of(g, a) or "",
                    seed_h=ps.seed_of(g, h) or "")

    # ── pregame ───────────────────────────────────────────────────────────
    def pregame(self, sim):
        a, h = sim.away, sim.home
        g = sim.game
        self.gtype = getattr(g, "game_type", "Regular Season")
        self._find_shared_names(sim)
        self._week = getattr(g, "week", 13)     # what time of year it is, for lines that care
        self._set_weather(sim)                  # before a word is said about the evening
        neutral = getattr(g, "neutral", False)
        venue = (g.venue if (neutral or self.post) else h.stadium) or h.stadium
        vname = venue.split(",")[0]
        att = getattr(g, "attendance", None)
        if att is None:                                      # an old box or a game played outside play_game
            if neutral:
                cap = {1: 62000, 2: 42000, 3: 30000}.get(g.tier, 72000) if self.gtype == "Bowl" else 74000
            else:
                cap = h.capacity
            att = int(cap * self.rng.uniform(0.86, 1.02))
        vs = "vs" if neutral else "at"
        riv = rivalry_name(a, h)
        seed = lambda t: (f"({ps.seed_of(g, t)}) " if self.gtype in ps.CFP_TYPES and ps.seed_of(g, t) else "")
        print()
        print(rule("═", C.BYELLOW))
        if self.post:
            print(pad(paint(ps.banner(g), C.BOLD, C.BYELLOW), WIDTH, "center"))
        print(pad(paint(f"{seed(a)}{a.school} {a.nickname}  {vs}  {seed(h)}{h.school} {h.nickname}", C.BOLD, C.BWHITE),
                  WIDTH, "center"))
        import broadcast
        when = f"  ·  {broadcast.when(g)}" if getattr(g, "kick", None) is not None else \
            (f"  ·  {ps.date_words(g.date)}" if getattr(g, "date", None) else "")
        sold = "  (sellout)" if getattr(g, "sellout", False) else \
            (f"  ({g.fill * 100:.0f}% full)" if getattr(g, "fill", None) is not None and g.fill < 0.985 else "")
        print(pad(paint(f"{venue}{when}  ·  Attendance {att:,}{sold}", C.GRAY), WIDTH, "center"))
        print(pad(paint(f"In the booth: {self.booth['pbp']} & {self.booth['color']}", C.GRAY), WIDTH, "center"))
        print(rule("═", C.BYELLOW))
        print()

        kw = self._post_kw(sim) if self.post else {}
        key = {"National Championship": "open_title", "NP Semifinal": "open_sf", "NP Quarterfinal": "open_qf",
               "NP First Round": "open_fr", "Conference Championship": "open_ccg", "Bowl": "open_bowl"}.get(self.gtype)
        if key:
            if self.gtype == "NP First Round":
                kw["venue"] = h.stadium
            opener = self.line(key, **kw)
        elif self.chance(0.4):
            opener = self.booth["open"].format(venue=vname)
        else:
            opener = self.line("open_regular", venue=vname, tod=self._tod(sim))
            if self.weather.get("kind") in ("rain", "cold", "snow", "storm", "wind") and "beautiful" in opener:
                opener = f"Good {self._tod(sim)}, everybody, from {vname}."
        if riv:
            opener += (f" It's {riv}, and it doesn't get much bigger than this." if not self.post
                       else f" And it's a postseason edition of {riv}.")
        self.pbp(opener)
        crowd = self._crowd_call(g, h, vname)
        if crowd:
            self.analyst(crowd)
        note = self._stadium_call(g, h, vname)
        if note:
            self.pbp(note)
        if self.chance(0.55):
            self.analyst(self._play_caller_note(self.rng.choice((a, h))))

        if not neutral:
            if not (self.chance(0.55) and self._lore(sim, h, ("pregame",))):
                self.chance(0.7) and self._lore(sim, h, ("home", "any"))
        elif self.chance(0.6):
            self._lore(sim, self.rng.choice((a, h)), ("any",))
        import rivalries
        for who, text in rivalries.pregame_lines(self.league, a, h, self.rng)[:3]:
            (self.pbp if who == "P" else self.analyst)(text)
        lore = ps.BOWL_LORE.get(g.bowl_name) if self.post else None
        if lore:
            self.analyst(self.rng.choice(lore))

        if self.post:
            self._post_pregame(sim)
        else:
            self._regular_pregame(sim)

        roll = self.rng.random()
        if roll < 0.5:
            self._coach_profiles(sim)
        elif roll < 0.8:
            self.pbp(self.line("coach_sideline", a=a.school, h=h.school, ac=a.coach.name, hc=h.coach.name,
                               arec=a.record, hrec=h.record))
        if self.chance(0.35) or self.weather["kind"] in ("rain", "cold", "snow", "storm", "wind", "hot"):
            ex = self.rng.choice(WEATHER_OPEN[self.weather["kind"]])
            self._used["weather"] = [id(ex)]
            for who, text in ex:
                (self.pbp if who == "P" else self.analyst)(self._fill(sim, text))
        if self.weather.get("storm"):
            self.pbp(f"What's left of Tropical Storm {self.weather['storm']} is right on top of us. Wind and rain, "
                     f"and it isn't going anywhere tonight.")
        self.pbp(self.line("handoff_to_analyst", color=self.booth["color"], bio=self.booth["bio"], A=self.A))
        self.analyst(self._preview(sim))
        for t in (a, h):
            hurt = [p for p in t.injured() if p in t.players_at(p.position)[:2]][:2]
            if hurt:
                who = " and ".join(f"{POS_WORDS[p.position]} {p.name}" for p in hurt)
                self.pbp(self.line("injury_news", team=t.school, who=who))
        if getattr(a, "fcs", False) or getattr(h, "fcs", False):
            small, big = (a, h) if getattr(a, "fcs", False) else (h, a)
            self.analyst(self.line("fcs_take", small=small.school, big=big.school))
        if neutral and not self.post:
            self.analyst(self.line("neutral_take"))
        elif att >= 80000:
            self.analyst(self.line("big_crowd", att=f"{att:,}"))
        if self.gtype in ("Bowl", "National Championship", "NP Semifinal") and self.chance(0.6):
            self.analyst(self.line("seniors"))
        if self.gtype == "National Championship":
            self.analyst(self.line("title_pregame"))
        self.wait(3.0)

    def _regular_pregame(self, sim):
        a, h = sim.away, sim.home
        rec = lambda t: t.record if (t.wins + t.losses) else "0-0"
        if a.wins + a.losses + h.wins + h.losses == 0:
            self.pbp(f"Season opener for both {a.school} and {h.school}.")
        else:
            ra, rh = self.rank(a), self.rank(h)
            both = bool(ra and rh) and self.chance(0.6)
            names = (a.school, h.school) if both else (self.rname(a), self.rname(h))
            self.pbp(self.line("records_line", a=names[0], h=names[1], ra=rec(a), rh=rec(h)))
            if both:
                self.pbp(self.line("rank_both", a=a.school, h=h.school, ra=ra, rh=rh))
        ra, rh = self.rank(a), self.rank(h)
        if ra and rh:
            if ra <= 10 and rh <= 10:
                self.analyst(self.line("rank_top10"))
        elif (ra or rh) and self.chance(0.5):
            un = h if ra else a
            self.analyst(self.line("rank_upset_chance", team=un.school))
        said = 0
        for t in (a, h):
            if said >= 1:
                break
            kind, n = self._streak(t)
            if t.losses == 0 and t.wins >= 4 and self.chance(0.7):
                self.pbp(self.line("unbeaten", team=t.school, rec=t.record))
                said += 1
            elif kind == "W" and n >= 4 and self.chance(0.6):
                self.pbp(self.line("streak_win", team=t.school, n=n))
                said += 1
            elif kind == "L" and n >= 3 and self.chance(0.6):
                self.pbp(self.line("streak_loss", team=t.school, n=n))
                said += 1
        for t in (a, h):
            if t.wins == 5 and sim.game.week <= 13 and self.chance(0.7):
                self.analyst(self.line("bowl_one_away", team=t.school))
                break
        if sim.game.week >= 7 and self.chance(0.5):
            for t in (a, h):
                r = self.rank(t)
                if r and r <= 12:
                    self.analyst(self.line("playoff_in", team=t.school, r=r))
                    break
        if sim.game.conference_game and a.conf_wins + a.conf_losses >= 3 and self.chance(0.5):
            t = max((a, h), key=lambda x: (x.conf_win_pct, x.conf_wins))
            if t.conf_losses <= 1:
                self.analyst(self.line("conf_race", team=t.school, crec=t.conf_record, conf=t.conference))

    def _post_pregame(self, sim):
        g, a, h = sim.game, sim.away, sim.home
        L = self.league
        kw = self._post_kw(sim)
        if self.gtype in ps.CFP_TYPES and kw["seed_a"]:
            self.pbp(self.line("seed_matchup", a=a.school, h=h.school, seed_a=kw["seed_a"], seed_h=kw["seed_h"]))
        self.pbp(f"{a.school} is {a.record}, {h.school} is {h.record}.")
        if L is not None:
            for t in (a, h):
                path = ps.path_lines(L, t, g.week)
                if path and self.gtype in ps.CFP_TYPES and self.chance(0.8):
                    how = path[-1] if len(path) == 1 else f"{path[-2]}, then {path[-1]}"
                    self.pbp(self.line("path", team=t.school, how=how))
                if self.gtype == "NP Quarterfinal" and ps.seed_of(g, t) and ps.seed_of(g, t) <= 4:
                    self.analyst(self.line("bye_rest", team=t.school))
                if ps.defending_champion(L) == t.school:
                    self.analyst(self.line("defending", team=t.school))
        if self.gtype == "National Championship" and L is not None:
            for t in (a, h):
                won = ps.titles_for(L, t.school)
                if won:
                    self.pbp(self.line("title_history_has", team=t.school, n=len(won), s="s" if len(won) > 1 else "",
                                       last=won[-1]))
                else:
                    self.pbp(self.line("title_history_none", team=t.school))
        elif self.gtype == "Conference Championship":
            self.analyst(self.line("ccg_stakes", team=h.school, conf=kw["conf"]))
        elif self.gtype == "Bowl":
            if a.conference != h.conference and self.chance(0.6):
                self.pbp(self.line("bowl_matchup_conf", ca=a.conference, ch=h.conference))
            for t in (a, h):
                if t.wins + 1 >= 9 and self.chance(0.5):
                    self.analyst(self.line("bowl_stakes_win", team=t.school, n=t.wins + 1))
                    break
                if t.losses >= 6 and t.wins == t.losses:
                    self.analyst(self.line("bowl_stakes_even", team=t.school))
                    break
        elif self.gtype == "NP First Round" and self.chance(0.7):
            self.analyst(self.line("fr_home", h=h.school))
        if g.next_game and self.gtype in ps.CFP_TYPES and self.gtype != "National Championship":
            self.pbp(self.line("next_round", next=g.next_game, date=ps.short_date(g.next_date)))

    def _trait_for(self, coach):
        """One reputation line per coach per game — the booth doesn't say it three times."""
        from traits import speakable_traits
        said = self.__dict__.setdefault("_traits_said", set())
        if coach.name in said:
            return None
        traits = speakable_traits(coach)
        if not traits:
            return None
        said.add(coach.name)
        return self.rng.choice(traits)

    def _coach_kw(self, off, df):
        import staff
        oc, dc = staff.play_caller(off, "off"), staff.play_caller(df, "def")     # whoever holds the play sheet
        os_, ds_ = oc.offense_scheme, dc.defense_scheme
        kw = dict(oc=oc.name, dc=dc.name, ot=off.school, dt=df.school, os=os_, ds=ds_,
                  ostyle=OFF_STYLE.get(os_, "move the ball"),
                  dstyle=DEF_STYLE.get(ds_, "play fast"))
        from traits import COACH_SPEECH
        for pre, coach in (("o", oc), ("d", dc)):
            t = self._trait_for(coach) if not ("onoun" in kw and pre == "d") else None
            if t:
                noun, clause = COACH_SPEECH[t]
                kw.update({f"{pre}noun": noun, f"{pre}clause": clause,
                           f"{pre.upper()}clause": clause[:1].upper() + clause[1:],
                           f"{pre}label": noun})         # older templates still key on "label"
        return kw

    def _coach_intro(self, off, df):
        kw = self._coach_kw(off, df)
        roll = self.rng.random()
        if roll < 0.25 and ("onoun" in kw or "dnoun" in kw):
            needs = lambda t, pre: f"{{{pre}noun" in t or f"{{{pre}clause" in t or f"{{{pre.upper()}clause" in t
            pool = [t for t in LINES["coach_intro_trait"]
                    if (not needs(t, "o") or "onoun" in kw) and (not needs(t, "d") or "dnoun" in kw)]
            if pool:
                return self.rng.choice(pool).format_map(_Blanks(kw))
        if roll < 0.37 and off.coach.aggression >= 70:
            return self.line("coach_intro_aggr", **kw)
        if roll < 0.37 and off.coach.aggression <= 38:
            return self.line("coach_intro_cons", **kw)
        return self.line("coach_intro", **kw)

    def _preview(self, sim):
        a, h = sim.away, sim.home
        gaps = []
        for off, df in ((a, h), (h, a)):
            gaps.append((off.offense_ovr - df.defense_ovr, off, df))
        diff, off, df = max(gaps, key=lambda g: abs(g[0]))
        qa, qh = sim.qb_of(a), sim.qb_of(h)
        self.introduced.update({id(qa), id(qh)})
        coach_line = self._coach_intro(off, df)
        kw = dict(ot=off.school, dt=df.school, qa=qa.name, qh=qh.name)
        if abs(diff) < 3:
            opener, tail = self.line("preview_open_even", **kw), self.line("preview_even", **kw)
        elif diff > 0:
            opener, tail = self.line("preview_open_off", **kw), self.line("preview_off_edge", **kw)
        else:
            opener, tail = self.line("preview_open_def", **kw), self.line("preview_def_edge", **kw)
        order = self.rng.random()
        if order < 0.5:
            return f"{opener} {coach_line} {tail}"
        if order < 0.8:
            return f"{coach_line} {opener} {tail}"
        return f"{opener} {tail} {coach_line}"

    def coin_toss(self, sim, winner):
        self.pbp(f"{winner.school} wins the toss and defers. {sim.other(winner).school} will get the ball first.")

    # ── kicks ─────────────────────────────────────────────────────────────
    def kick(self, sim, lines):
        seen = self.__dict__.setdefault("_kick_said", set())
        lines = [("Touchback." if "Touchback" in ln else "") if ln in seen else ln for ln in lines]
        seen.update(lines)
        lines = [ln for ln in lines if ln]
        text = " ".join(lines)
        text = re.sub(r"#\d+ ", "", text).replace(" on kick coverage", "").replace("...", "… ")
        text = re.sub(r"…\s+…", "…", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"  +", " ", text)
        self.pbp(text, must=True)

    def special_snap(self, sim):
        """A punt or a field goal: show the spot it's snapped from (the ticker)."""
        if not self.muted and not getattr(self, "_quiet_ticker", False) and sim.quarter <= 4:
            self.ticker(sim)

    # ── before the snap ───────────────────────────────────────────────────
    def pre_snap(self, sim, call, personnel, dcall):
        self.snap += 1
        off, df = sim.offense, sim.defense
        self._sim = sim
        self._ctx = (sim.quarter, sim.clock, sim.down, sim.togo, sim.yardline, off.abbr)
        self._ctx_open = True
        self.cur = (call, personnel, dcall, off, df)
        if self.muted or getattr(self, "_quiet_ticker", False):
            return
        self.ticker(sim)
        if self.show_calls:
            self.note(f"[coach's view] {off.abbr}: {call.name} ({personnel})  ·  {df.abbr}: {dcall.name}")
        if call.kind == "kneel":
            return
        rng = self.rng
        ytg = 100 - sim.yardline
        drive = sim.drive
        first = drive is not None and drive["plays"] == 0
        diff = sim.score[off] - sim.score[df]
        qb_now = sim.qb_of(off)
        said = self.__dict__.setdefault("_qb_said", {})
        if self._last_qb.get(off) not in (None, qb_now) and said.get(off) is not qb_now:
            said[off] = qb_now                         # one voice announces it, once
            self.pbp(self.line("qb_change", qb=self.name(qb_now), team=off.school))
        self._last_qb[off] = qb_now
        say = []
        if sim.quarter > 4 and first:
            self._ot_possession += 1
            say.append(self.line("ot_offense", team=off.school))
            stakes = self.ot_stakes(sim, off)
            if stakes:
                say.append(stakes)
        elif first and self.chance(0.7):
            need = ""
            if sim.quarter == 4 and diff < 0 and sim.clock < 360:
                need = (", needing at least a field goal" if diff >= -3 else ", needing a touchdown" if diff >= -8
                        else ", needing two scores" if diff >= -16 else "")
            say.append(self.line("drive_start", team=off.school,
                                 spot=self.spot(sim, sim.yardline, off), need=need))
        if sim.down == 4:
            say.append(self.line("fourth_call", togo=sim.togo, team=off.school))
            if self.chance(0.7):
                self.pbp(" ".join(say))
                self.analyst(self._fourth_down_take(sim, off))
                return
        elif sim.down == 3:
            say.append((f"{_dd_words(3, sim.togo, sim.yardline)}. " +
                        self._third_down_stakes(sim, off, df, diff)).strip())
        elif sim.togo >= ytg and sim.down == 1:
            say.append(self.line("goal_to_go", n=ytg))
        elif sim.yardline <= 8 and self.chance(0.5):
            say.append(self.line("backed_up", team=off.school, n=sim.yardline, qb=self.ln(sim.qb_of(off))))
        elif (sim.quarter in (2, 4)) and sim.clock < 120 and diff <= 0 and self.chance(0.6):
            say.append(self.line("hurry_up", qb=self.ln(sim.qb_of(off)), clock=clock_str(sim.clock), team=off.school))
        elif sim.quarter == 4 and diff > 0 and sim.clock < 360 and self.chance(0.35):
            say.append(self.line("milking", team=off.school, clock=clock_str(sim.clock), qb=self.ln(sim.qb_of(off))))
        elif self.chance(0.1) and not say:
            dd = _dd_words(sim.down, sim.togo, sim.yardline)
            say.append(self.line("dd_note", dd=dd, dd_lower=dd.lower(), team=off.school,
                                 spot=self.spot(sim, sim.yardline, off)))
        if self.chance(0.18) and len(say) < 2:
            say.append(self._formation(sim, off, personnel))
        if dcall.rush >= 6 and self.chance(0.6):
            say.append(self.line("blitz_look", opp=df.school))
        elif dcall.name == "Prevent" and self.chance(0.7):
            say.append(self.line("prevent_look", opp=df.school))
        elif dcall.box >= 8 and sim.togo <= 3 and sim.down >= 3 and self.chance(0.6):
            self.pbp(" ".join(say))
            self.analyst(self.line("box_stack_take"))
            return
        if say:
            self.pbp(" ".join(s for s in say if s))

    def _formation(self, sim, off, personnel):
        return self.line(f"formation_{personnel}", qb=self.ln(sim.qb_of(off)), team=off.school)

    def _third_down_stakes(self, sim, off, df, diff):
        ts = sim.team_stats[off]
        if sim.quarter > 4:
            if self._ot_possession >= 2 and diff < 0:
                return self.pick("They have to keep this drive alive.", "Fail here and it's over.",
                                 f"{df.school} is one stop from winning it.")
            return self.pick("Big down in overtime.", "You can't waste a possession here.")
        if sim.quarter == 4 and diff > 0 and sim.clock < 150:
            return f"Convert here and {off.school} can just about run it out."
        if sim.quarter == 4 and -16 <= diff < 0 and sim.clock < 360:
            early = sim.drive is not None and sim.drive["plays"] <= 2
            return self.pick("This is a must.", f"Huge down for {off.school}.",
                             *((f"{off.school} can't go three-and-out here.",) if early else ()))
        if ts["third_att"] >= 4 and self.snap - self.cool.get("3d", -99) > 40 and self.chance(0.3):
            self.cool["3d"] = self.snap
            self.cool["_t_thirddown"] = self.snap
            c, t_ = ts["third_conv"], ts["third_att"]
            return self.pick(f"{off.school} is {c} of {t_} on third down today.",
                             f"They've converted {c} of {t_} third downs.",
                             f"{c} for {t_} on third down so far for {off.school}.",
                             f"Third-down numbers for {off.school}: {c} of {t_}.")
        if sim.togo >= 9:
            return self.line("third_long", opp=df.school)
        if sim.togo <= 2:
            return self.line("third_short")
        return self.line("third_medium") if self.chance(0.8) else ""

    def _fourth_down_take(self, sim, off):
        coach = off.coach
        if sim.quarter > 4:
            return self.take("fourth_go_ot")
        if sim.quarter == 4 and sim.score[off] < sim.score[sim.other(off)] and sim.clock < 360:
            return self.take("fourth_go_desperate")
        if coach.aggression >= 70:
            return self.take("fourth_go_aggressive", coach=coach.name)
        if coach.aggression <= 40:
            return self.take("fourth_go_surprise", coach=coach.name)
        return self.take("fourth_go_neutral", coach=coach.name)

    # ── the play ──────────────────────────────────────────────────────────
    def play(self, sim, r, before):
        self._play(sim, r, before)
        notes = getattr(r, "sl_notes", None)            # the sideline: a declined flag, a replay review
        if notes and not self.muted and self.cur is not None:
            for n in notes:
                self.pbp(n, must=True)
        self._ctx_open = False                           # the snap is over; what's said next is between plays

    def _play(self, sim, r, before):
        if self.muted or self.cur is None:
            return
        call, personnel, dcall, off, df = self.cur
        down, togo, yl = before[0], before[1], before[2]
        if r.kind == "kneel":
            qb = self.ln(sim.qb_of(off))
            # "That'll do it" only when the kneels left can really run out the clock.
            ends = sim.quarter in (2, 4) and sim.clock <= 43 * max(1, 5 - sim.down)
            # "victory formation" is for the end of the game; before the half it's just a knee
            self.pbp(self.line("kneel" if ends else "kneel_mid", qb=qb,
                               _avoid=("Victory formation", "Let the clock do the rest") if sim.quarter == 2 else ()))
            return
        self._before_down = down
        if r.penalty:
            return self._penalty(sim, r, off, df, yl)
        if r.sack:
            text = self._sack_call(sim, r, off, yl)
        elif r.turnover == "int":
            text = self._int_call(sim, r, off, df, yl)
        elif r.kind == "pass":
            text = self._pass_call(sim, r, call, off, yl)
        else:
            text = self._run_call(sim, r, call, off, yl)

        if r.turnover == "fumble":
            fd = dict(r.color).get("fumble", {})
            forcer, rec_ = fd.get("forcer"), getattr(r, "recoverer", None)
            if forcer is not None and rec_ is not None and fd.get("forced", True):
                text += (f" {self.ln(forcer)} knocks it loose... and {self.ln(rec_)} recovers for {df.school}!"
                         if rec_ is not forcer else f" {self.ln(forcer)} strips it and recovers it himself!")
            else:
                text += " " + self.line("fumble_call", opp=df.school)
        elif getattr(r, "overturned", None) == "fumble":
            text += f" The ball's OUT — and {df.school} comes up with it! Ruled a fumble on the field..."
        elif "own fumble" in " ".join(r.lines):
            text += " The ball came loose — but he fell on it himself. Whew."
        elif not (r.td or r.turnover or r.safety):
            text += " " + self._after(sim, r, off, down, togo)
        if r.yards >= 20 and not r.penalty:
            self.explosives[off] += 1
        if r.sack:
            self.__dict__.setdefault("_sack_log", []).append((sim.plays_run, df))
        # Who just made a play — the only players a bio or a backstory can be about right now.
        feat = []
        if r.yards >= 6 or r.td or r.big:
            feat += [x for x in (r.carrier, None if r.incomplete else r.target) if x is not None]
        if (r.sack or r.turnover or r.yards <= 0) and r.tackler is not None:
            feat.append(r.tackler)
        if r.turnover == "int" and r.defender is not None:
            feat.append(r.defender)
        self._featured = (self.snap, list(dict.fromkeys(feat)))
        # A red-zone trip is a possession that gets inside the 20 — counted once per drive.
        # A touchdown counts toward the red zone only if it came on one of those trips.
        key = (off, id(sim.drive)) if sim.drive is not None else None
        inside = yl >= 80 or (not r.td and sim.offense is off and sim.yardline >= 80)
        if key is not None and inside and self._rz_flag != key:
            self._rz_flag = key
            self.rz_trips[off] += 1
        if r.td and key is not None and self._rz_flag == key:
            self.rz_tds[off] += 1
        if down == 4 and r.kind in ("run", "pass", "sack"):
            self.fourth_tries[off] += 1
        for t in sim.teams:
            self.biggest_lead[t] = max(self.biggest_lead[t], sim.score[t] - sim.score[sim.other(t)])
        self._td_narrated = bool(r.td)
        if r.safety:                                   # call it on the play, not two lines later
            text += " " + self.pick("He's down in the end zone — SAFETY!", "Taken down in the end zone! That's a SAFETY!",
                                    "Brought down in his own end zone — SAFETY!")
            self._safety_called = True
        self.pbp(text.strip(), *((C.BOLD,) if (r.big or r.turnover or r.safety) else ()), must=True)
        if not r.safety:
            self._react(sim, r, call, dcall, off, df, down, togo)
        if r.td:
            self._td_count(sim, r)
        if not r.turnover:
            self._milestones(sim, r)
        if r.turnover and self.ot_decisive(sim):
            self._walkoff(sim, "stop")
        if not (r.td or r.turnover or r.safety):
            self._chatter(sim)

    def _after(self, sim, r, off, down, togo):
        if sim.offense is not off:            # turnover on downs is announced separately
            return ""
        if sim.quarter in (2, 4) and sim.clock <= 0:
            return ""                          # the clock ran out on that play: there's no "third and 21"
        if r.first_down:
            if r.yards - togo <= 1:
                return self.line("first_down_barely", team=off.school)
            if down == 4:
                return self.line("first_down_fourth", team=off.school)
            return self.line("first_down_third" if down >= 3 else "first_down", team=off.school)
        if sim.down == 4:
            miss = sim.togo
            if r.yards <= 0:                           # no gain (an incompletion, a stuff): nothing "just short"
                return self.line("short_of_sticks", togo=sim.togo)
            if miss <= 1:
                return self.line("short_of_sticks_inches", togo=sim.togo)
            if miss <= 2:
                return self.line("short_of_sticks_near", togo=sim.togo)
            if miss >= 8 or (togo and r.yards < togo / 2):
                return self.line("short_of_sticks_far", togo=sim.togo)
            return self.line("short_of_sticks", togo=sim.togo)
        if sim.down == 3 and self.chance(0.6):
            return self.line("sets_up_third", togo=sim.togo)
        return ""

    # runs
    def _run_call(self, sim, r, call, off, yl):
        c, t = r.carrier, r.tackler
        qb = sim.qb_of(off)
        if c is None:
            c = qb
        cn = self.name(c)
        if c is not qb and c.last_name == qb.last_name:
            cn = f"{c.first_name} {c.last_name}"
        qn = self.ln(qb) if qb.last_name != c.last_name or c is qb else f"{qb.first_name} {qb.last_name}"
        concept = call.concept if call.kind == "run" else ""
        side = f" to the {r.side}" if r.side in ("left", "right") else ""
        kw = dict(car=cn, qb=qn, side=side, team=off.school)
        if r.read == "rpo_give" and r.read_key is not None:
            start = self.line("rpo_read_give" if getattr(r, "read_correct", True) else "rpo_read_give_wrong",
                              lb=self.ln(r.read_key), **kw)
        elif r.scramble:
            start = self.line("run_scramble", **kw)
        elif concept == "qb_sneak":
            start = self.line("run_sneak", **kw)
        elif concept == "reverse":
            start = self.line("run_reverse", **kw)
        elif concept == "jet":
            start = self.line("run_jet", **kw)
        elif concept == "midline":
            # Midline is give-or-keep, straight up the middle. There is no pitch.
            start = self.line("run_midline_keep" if c is qb else "run_midline_give", **kw)
        elif concept == "triple" and r.option == "give":
            start = self.line("run_triple_dive", **kw)
        elif concept in ("zone_read", "speed_option", "triple") and c is qb:
            start = self.line("run_qb_keep", **kw)
        elif concept in ("speed_option", "triple") and c is not qb:
            start = self.line("run_pitch", **kw)
        elif c is qb:
            start = self.line("run_qb_designed", **kw)
        elif concept == "draw":
            start = self.line("run_draw", **kw)
        elif concept in EDGE_RUNS:
            start = self.line("run_edge", **kw)
        else:
            start = self.line("run_inside", **kw)
        mid = ""
        if r.missed and r.yards >= 4:
            if start and start[-1] in "!.":
                start = start[:-1]
            mid = self.line("broken_tackle", tk=self.ln(r.missed[0]))
        gain = self._gain(sim, r, c, t, off, yl)
        if not mid and gain[:1].islower() and start.endswith("."):
            start = start[:-1] + "..."            # "They run the quarterback... and he's wrapped up"
        if mid and gain[:1].isupper():
            gain = gain[0].lower() + gain[1:]
        if not mid and gain[:1].islower() and start[-1:] in ".!":
            start = start[:-1] + "..."
        return f"{start}{mid} {gain}"

    def _gain(self, sim, r, carrier, tackler, off, yl):
        g = r.yards
        kw = dict(tk=self.ln(tackler) if tackler else "", n=abs(g), yds=_yds(g), yds_cap=_yds(g).capitalize(),
                  end=self.spot(sim, yl + g, off), team=off.school,
                  oob=" and out of bounds" if r.out_of_bounds else "")
        if r.td:
            return self.line("gain_td_long" if g >= 20 else "gain_td_short", **kw)
        if not kw["tk"] and not r.safety:                 # nobody credited with the tackle
            key = ("gain_loss" if g < 0 else "gain_stuff" if g == 0 else "gain_short" if g <= 3 else
                   "gain_medium" if g <= 9 else "gain_long" if g <= 19 else "gain_breakaway")
            return self.line(key + "_notk", **kw)
        if r.safety:
            return self.line("safety_call", **kw)
        if g < 0:
            return self.line("gain_loss", **kw)
        if g == 0:
            return self.line("gain_stuff", **kw)
        if g <= 3:
            return self.line("gain_short", **kw)
        if g <= 9:
            return self.line("gain_medium", **kw)
        if g <= 19:
            return self.line("gain_long", **kw)
        return self.line("gain_breakaway", **kw)

    # passes
    def _throw_words(self, r):
        route, air = r.route or "", r.air_yards if r.air_yards is not None else 5
        if route in ("screen", "bubble"):
            return "on the screen"
        if route in ("flat", "swing", "angle"):
            return self.line("throw_flat")
        if route in ("slant", "drag", "whip", "cross"):
            return self.line("throw_short_in")
        if route in ("hitch", "stick", "snag", "sit", "curl", "pop"):
            return self.line("throw_underneath")
        if route in ("quick out", "out", "deep out", "comeback"):
            return self.line("throw_sideline")
        if route in ("dig", "leak"):
            return self.line("throw_middle")
        if route == "seam":
            return self.line("throw_seam")
        if route == "post" or air >= 30:
            return self.line("throw_deep_middle")
        return self.line("throw_deep_side")

    def _drop_back(self, sim, r, call, qb):
        n = self.name(qb)
        if call.name == "Flea Flicker":
            return f"Handoff... pitched BACK to {n} — flea flicker!"
        if call.passer == "RB":
            return f"Toss to {n}... he pulls up — halfback pass!"
        if call.screen:
            return self.line("drop_screen", qb=n)
        if call.play_action:
            return self.line("drop_play_action", qb=n)
        if call.name == "Hail Mary":
            return f"Here it is. {n} drops back..."
        return self.line("drop_back", qb=n)

    def _pocket(self, r):
        if r.qb_moved == "escape":
            return self.line("pocket_escape")
        if r.qb_moved == "climb":
            return self.line("pocket_climb")
        if r.qb_moved == "slide":
            return self.line("pocket_slide")
        if r.pressured:
            return self.line("pocket_pressure")
        return ""

    def _read_words(self, r, rn):
        """Connect the call to the result: what the quarterback saw before he threw it."""
        if r.read in ("rpo_throw",) and r.read_key is not None:
            key = "rpo_read_throw" if getattr(r, "read_correct", True) else "rpo_read_throw_wrong"
            return self.line(key, lb=self.ln(r.read_key))
        if r.read in ("checkdown", "progression") and r.first_look:
            frec, froute, fdef = r.first_look
            route = froute if froute not in ("screen", "bubble") else "first read"
            return self.line("read_checkdown" if r.read == "checkdown" else "read_progression",
                             route=route, first=self.ln(frec), dfn=self.ln(fdef) if fdef else "", rec=rn)
        return ""

    def _pass_call(self, sim, r, call, off, yl):
        qb, rec = r.passer or sim.qb_of(off), r.target
        start = self._drop_back(sim, r, call, qb)
        pocket = self._pocket(r)
        rn = self.name(rec) if rec else "his man"
        where = self._throw_words(r)
        if call.name == "Hail Mary":
            throw = "HE HEAVES IT to the end zone..."
        elif where == "the screen":
            throw = self.line("throw_screen", rec=rn)
        else:
            throw = self.line("throw_verb", where=where, rec=rn)
        read = self._read_words(r, rn)
        if r.read == "checkdown" and where != "the screen" and call.name != "Hail Mary":
            throw = self.line("throw_checkdown", rec=rn)
        head = " ".join(x for x in (start, read, pocket, throw) if x)
        if r.incomplete and r.inc_reason == "overturned":
            return f"{head} {rn} goes up for it in traffic and comes down with it — ruled a catch on the field..."
        if r.incomplete:
            key = {"pbu": "inc_pbu", "drop": "inc_drop", "under": "inc_under", "over": "inc_over",
                   "behind": "inc_behind", "fingertips": "inc_fingertips", "low": "inc_low",
                   "away": "inc_away"}.get(r.inc_reason, "inc_over")
            tail = self.line(key, def_=self.ln(r.defender) if r.defender else "",
                             **{"def": self.ln(r.defender) if r.defender else ""})
            if r.inc_reason == "away":
                return f"{start} {pocket or 'nobody open...'} {tail}"
            return f"{head} {tail}"
        air = r.air_yards if r.air_yards is not None else 0
        if r.td:
            if call.name == "Hail Mary":
                return f"{head} a crowd of bodies... CAUGHT! {self.ln(rec).upper()}! TOUCHDOWN!"
            if air >= 100 - yl - 1:
                grab = "makes a great grab in traffic" if r.contested else "is wide open"
                return f"{head} " + self.line("catch_td", rec=self.ln(rec), grab=grab)
            return f"{head} " + self.line("catch_td_yac", rec=self.ln(rec))
        air = min(air, r.yards) if r.yards < air else air     # never caught past where he was tackled
        catch_spot = self.spot(sim, yl + air, off)             # behind the line when it was (screens)
        yac = r.yards - air
        t = self.ln(r.tackler) if r.tackler else ""
        if r.tackler is not None and rec is not None and t == self.ln(rec):
            t = f"{r.tackler.first_name} {self.ln(r.tackler)}"
        kw = dict(rec=self.ln(rec), spot=catch_spot, tk=t, n=r.yards, yds_cap=_yds(r.yards).capitalize(),
                  end=self.spot(sim, yl + r.yards, off), yac=_yds(yac),
                  gain_txt="No gain" if r.yards == 0 else f"Loss of {-r.yards}")
        catch = self.line("catch_contested" if r.contested else "catch_plain", **kw)
        late = sim.quarter in (2, 4) and sim.clock <= 240
        if not t:
            run = self.line("catch_notk_yac" if yac >= 3 else "catch_notk", **kw)
            big = self.booth["big"][0] + " " if r.yards >= 30 else ""
            return f"{head} {big}{catch}{run}"
        if r.missed and yac >= 6:
            run = self.line("yac_break", tk=self.ln(r.missed[0]), tk2=t, **{k: v for k, v in kw.items() if k != "tk"})
        elif yac >= 10:
            run = self.line("yac_run", **kw)
        elif r.out_of_bounds and r.yards > 0:
            run = self.line("catch_oob_yac" if yac >= 3 else "catch_oob",
                            _avoid=() if late else ("stop the clock", "stops the clock"), **kw)
        elif r.yards <= 0 or (yac <= 0 and air <= 0):
            run = self.line("catch_stopped", **kw)
        elif yac <= 1:
            run = self.line("catch_tackled", **kw)             # "wraps him up immediately" — and he did
        else:
            run = self.line("catch_tackled_yac", **kw)         # the yards after the catch, said out loud
        big = self.booth["big"][0] + " " if r.yards >= 30 else ""
        return f"{head} {big}{catch}{run}"

    def _sack_call(self, sim, r, off, yl):
        qb = r.passer or sim.qb_of(off)
        t = r.tackler
        cnt = self.mark_hot(t)
        again = f"{self.ln(t)} AGAIN!" if cnt >= 2 else f"{self.name(t)}!"
        mate = getattr(r, "sack_mate", None)
        if mate is not None:
            self.mark_hot(mate)
            again = f"{self.name(t)} and {self.name(mate)} get there together!"
        start = self.line("drop_back", qb=self.name(qb))
        return start + " " + self.line("sack_call", mid=self.line("sack_mid"), who=again,
                                       end=self.spot(sim, yl + r.yards, off), n=-r.yards)

    def _int_call(self, sim, r, off, df, yl):
        qb, rec, d = r.passer or sim.qb_of(off), r.target, r.defender
        self.mark_hot(d)
        start = self._drop_back(sim, r, self.cur[0], qb)
        where = self._throw_words(r)
        ret = r.return_yards
        tail = f" He brings it back {ret} yards!" if ret >= 10 else ""
        call = self.line("int_call", **{"def": self.name(d)})
        return f"{start} {self._pocket(r)} throws {where}... {call}{tail}".replace("  ", " ")

    def _penalty(self, sim, r, off, df, yl):
        name, team, yards, auto, replay = r.penalty
        who = r.flag_player
        num = f"number {who.number}, {self.ln(who)}" if who else "the offense"
        if name == "False Start":
            self.pbp(self.line("false_start", who=num, team=off.school), must=True)
            if sim.home is df and not sim.neutral and self.chance(0.5):
                self.analyst(self.line("false_start_crowd"))
        elif name == "Offside":
            auto = sim.down == 1 and getattr(self, "_before_down", 1) != 1
            self.pbp(self.line("offside", who=num, opp=df.school) + (" And that's a first down." if auto else ""),
                     must=True)
        elif name == "Holding" and getattr(r, "flag_choice", None) == "accepted":
            self.pbp(f"Flag on the play — holding, {num}. {df.school} takes the penalty: ten yards, and they'll "
                     f"replay the down.", must=True)
        elif name == "Holding":
            self.pbp(self.line("holding", who=num, team=off.school), must=True)
            if self.chance(0.5):
                self.analyst(self.line("holding_take"))
        elif name == "Defensive Holding":
            self.pbp(f"Flag downfield — defensive holding, {num}. {off.school} takes the ten yards and an automatic "
                     f"first down.", must=True)
        elif name == "Pass Interference":
            self.pbp(self.line("pi", who=num, team=off.school), must=True)
            if self.chance(0.6):
                self.analyst(self.line("pi_take"))

    # ── analyst reactions ─────────────────────────────────────────────────
    TACKLE_PLAIN = (
        ("unblocked", ("Nobody blocked {t}. {d} had an extra man down there and {o} didn't have anybody left for him.",
                       "{t} was unaccounted for. Free runner, easy tackle.",
                       "Count the numbers — {d} had one more than {o} could block, and it was {t}.")),
        ("slipped through untouched", ("{t} came through clean — nobody even got a hand on him at the second level.",
                                       "Nobody touched {t}. He walked right into the backfield.")),
        ("knifed", ("{t} was in the backfield before the handoff. He won that before the play started.",
                    "Great get-off by {t}. He knifed through the gap like it wasn't there.",
                    "{t} timed the snap perfectly. That's a disruptive player.")),
        ("shed", ("Watch {t} — he takes on the block, throws the lineman aside, and makes the tackle. That's strong.",
                  "{t} stacked and shed. Textbook.", "Heavy hands from {t}. He disengaged and made the play.",
                  "{t} got blocked and made the tackle anyway. That's a man.")),
        ("second level", ("{t} beat the block from the lineman trying to climb up to him. That's why he's free.",
                          "The guard never got to {t} at the second level.",
                          "{t} scraped over the top before the lineman could climb.")),
        ("fought off", ("{t} fought through the block to get in on it.", "Relentless from {t}. He kept working.")),
        ("backside", ("{t} never quit on that play. Ran it down from the back side.",
                      "Backside pursuit — {t} chased it all the way down.", "{t} came from the back side to finish it.",
                      "Credit {t} — he was on the far side of the formation and still got there.",
                      "Pursuit angles. {t} took a good one from the back side.")),
        ("came downhill", ("Great job by {t} coming downhill and squaring him up. No hesitation.",
                           "{t} trusted his read and triggered. That's how you fill a gap.",
                           "Downhill, square, wrap. {t} made it look easy.")),
        ("set the edge", ("{t} kept contain right there. Forced it back inside where he had help.",
                          "{t} set a hard edge. Nothing got outside of him.",
                          "That's edge discipline from {t}. He turned it back in.")),
        ("ran him down", ("Look at the speed on {t} to run him down!", "{t} closed like he was shot out of a cannon.")),
        ("chased him down", ("That's effort. {t} tracked him all the way across the field.",
                             "{t} would not give up on that play. Great hustle.")),
        ("hip pocket", ("{t} was right in his pocket the whole route. Nowhere to go after the catch.",
                        "Blanket coverage by {t}. Caught it, and got hit immediately.")),
        ("drove on the throw", ("{t} read the quarterback and closed fast. Good eyes.",
                                "{t} broke on it as the ball was thrown. That's anticipation.",
                                "He saw the quarterback's shoulders and drove on it. Nice play by {t}.")),
        ("rallied", ("Good hustle by {t} to get over there and clean it up.", "{t} rallies to the ball. That's coaching.")),
        ("spying", ("They had {t} shadowing the quarterback the whole way. That's why he had nowhere to run.",
                    "{t} was the spy on that play, and he did his job.")),
        ("sniffed out the screen", ("{t} smelled the screen the whole way. He never bit on the fake.",
                                    "{t} saw the linemen release and knew exactly what was coming.",
                                    "Screen diagnosed. {t} was there before the blockers.")),
        ("stayed home", ("He stayed home and didn't bite on the misdirection. Disciplined football.",
                         "{t} played his assignment. Didn't chase the motion.")),
        ("last man", ("{t} saved a touchdown right there. That's the only reason it's not seven.",
                      "Last line of defense, and {t} got him down. Huge.")),
        ("wrong decision", ("That's the wrong read. The defender did his job and made him pay for it.",
                            "He made the wrong choice there and {t} was waiting.")),
    )

    def _react(self, sim, r, call, dcall, off, df, down, togo):
        tags = dict(r.color)
        line = None
        if r.sack:
            d = tags.get("sack", {})
            tk = self.ln(r.tackler) if r.tackler else ""
            if getattr(r, "sack_mate", None) is not None:
                line = self.take("sack_shared")
            elif d.get("flusher") is not None:
                line = self.take("sack_flush", fl=self.ln(d["flusher"]), tk=tk)
            elif d.get("coverage"):
                line = self.take("sack_coverage", opp=df.school)
            elif d.get("beaten") is None:
                line = self.take("sack_unblocked", tk=tk)
            else:
                sacks_now = self.stat(sim, r.tackler, "sack")
                line = self.take("sack_beaten", _avoid=() if sacks_now >= 2 else ("all day",),
                                 tk=tk, blk=self.ln(d["beaten"]))
            sacks = self.stat(sim, r.tackler, "sack")
            if sacks >= 2 and getattr(r, "sack_mate", None) is None:
                n = NUM_WORDS[min(int(sacks), 10)] + (" and a half" if sacks % 1 else "")
                line += f" That's {n} sacks now for {self.ln(r.tackler)}."
                self._ms_done.add((id(r.tackler), "sack3"))   # the milestone doesn't repeat it
            if getattr(r, "sack_mate", None) is not None:
                line = f"{self.ln(r.tackler)} and {self.ln(r.sack_mate)} split that one. " + line
        elif r.turnover == "int":
            d = tags.get("int", {})
            if d.get("pressured"):
                line = self.take("int_pressure")
            elif d.get("sep", 1) < 0.8:
                line = self.take("int_forced")
            else:
                line = self.take("int_read", **{"def": self.ln(r.defender) if r.defender else "he"})
        elif r.turnover == "fumble":
            line = self.take("fumble")
        elif "drop" in tags:
            line = self.take("drop")
        elif "hot_read" in tags and not r.incomplete:
            line = self.take("hot_read")
        elif "screen_vs_blitz" in tags:
            line = self.take("screen_vs_blitz")
        elif "trick" in tags and r.yards >= 10:
            line = self.take("trick")
        elif "trick_busted" in tags:
            line = self.take("trick_busted")
        elif "read_right" in tags:
            line = self.take("read_right")
        elif "read_wrong" in tags:
            line = self.take("read_wrong_keep" if (r.carrier is not None and r.carrier.position == "QB")
                             else "read_wrong_give")
        elif "breakaway" in tags:
            line = self.take("breakaway")
        elif r.td and r.kind == "pass":
            if dcall.shell == 0:
                line = self.take("td_cover0")
            elif r.contested:
                line = self.take("td_contested", rec=self.ln(r.target))
            elif (r.route or "") in ("screen", "bubble", "flat", "swing", "angle", "hitch", "stick", "snag", "sit", "pop",
                                     "slant", "drag", "whip", "cross", "in", "quick in", "quick out") \
                    or (r.air_yards if r.air_yards is not None else 0) < 18:
                line = self.take("td_short") if "td_short" in LINES else self.take("td_open")
            else:
                line = self.take("td_open")
        elif r.tackle_why:
            why = r.tackle_why.lower()
            # Credit a defender for winning the play only when the defense did win it: a
            # stop short of the sticks or a short gain. Effort (running a man down) can be
            # praised after a big gain — he kept it from being bigger.
            won = not getattr(r, "first_down", False) and not r.td and (
                r.yards <= 2 or (down >= 3 and r.yards < togo))
            effort = {"backside", "ran him down", "chased him down", "last man"}
            if getattr(r, "out_of_bounds", False):
                why = ""                                    # he went out of bounds: nobody made a tackle
            for key, template in self.TACKLE_PLAIN:
                if key in why and ((key in effort and r.yards >= 6) or (key not in effort and won)):
                    if self.snap - self.cool.get("why:" + key, -99) < 30:
                        return
                    self.cool["why:" + key] = self.snap
                    line = self.rng.choice(template).format(t=self.ln(r.tackler) if r.tackler else "he",
                                                            d=df.school, o=off.school)
                    break
            if line and not (r.yards <= 0 or r.yards >= 12 or down >= 3):
                if not self.chance(0.3):
                    line = None
        if not line:
            return
        if self.chance(0.85 if (r.big or r.turnover or r.sack or down >= 3) else 0.4):
            self.analyst(line)
            if r.tackler is not None and r.yards < 0 and not r.sack:
                n = self.mark_hot(r.tackler)
                tfl = self.stat(sim, r.tackler, "tfl")
                if n >= 3 and tfl >= 2 and self.chance(0.4):
                    self.analyst(f"That's {num_words(tfl)} tackles for loss now. {self.ln(r.tackler)} has lived in that backfield today.")

    # ── between-play conversation ─────────────────────────────────────────
    def _chatter(self, sim, force=False):
        if self.muted:
            return
        if not force:
            if self.snap - self.last_chat < 3 or self.chance(0.6):
                return
            from playbook import is_hurry
            if is_hurry(sim) and not self.chance(0.25):
                return
        topics = [self._t_qb, self._t_rusher, self._t_receiver, self._t_defender, self._t_situation,
                  self._t_coach, self._t_crowd, self._t_injury, self._t_thirddown, self._t_turnovers,
                  self._t_bio, self._t_rivalry, self._t_drive, self._t_ground,
                  self._t_explosives, self._t_redzone, self._t_streak, self._t_penalties,
                  self._t_possession, self._t_firstdowns, self._t_protection, self._t_special,
                  self._t_matchup, self._t_stakes, self._t_backup, self._t_comeback, self._t_pace,
                  self._t_youth, self._t_fourth_downs, self._t_postseason, self._t_lore, self._t_ranking,
                  self._t_heisman, self._t_transfer, self._t_hometown, self._t_season_line, self._t_coach_trait,
                  self._t_conf_race, self._t_around_league, self._t_around_league, self._t_later,
                  self._t_next_week, self._t_last_week, self._t_poll, self._t_program, self._t_recruiting,
                  self._t_banter, self._t_banter, self._t_war_story, self._t_weather,
                  self._t_adjust, self._t_adjust, self._t_adjust, self._t_hot_seat, self._t_unbeaten,
                  self._t_playoff_picture, self._t_next_marquee, self._t_lore, self._t_lore, self._t_lore,
                  self._t_lore, self._t_form, self._t_rivalry_heat, self._t_rivalry_heat, self._t_upset_alert,
                  self._t_upset_alert, self._t_trap, self._t_bowl_math, self._t_revenge, self._t_race]
        self.rng.shuffle(topics)
        for topic in topics:
            key = topic.__name__
            if self.snap - self.cool.get(key, -99) < 30:
                continue
            once = self._used.setdefault("once", set())
            if key in ONCE and key in once:
                continue
            lines = topic(sim)
            if lines:
                once.add(key)
                self.cool[key] = self.snap
                self.last_chat = self.snap
                for who, text in lines:
                    (self.pbp if who == "P" else self.analyst)(text)
                return

    def _leaders(self, sim, team, key, floor, skip_pos=()):
        best, val = None, floor - 1
        for p, c in sim.stats.items():
            if c[key] > val and sim.team_of(p) is team and p.position not in skip_pos:
                best, val = p, c[key]
        return (best, val) if best is not None else (None, 0)

    def _t_qb(self, sim):
        for team in (sim.offense,):                    # only the quarterback who's on the field
            qb = sim.qb_of(team)
            c = sim.stats.get(qb, Counter())
            if c["pass_att"] < 9:
                continue
            pct = c["pass_cmp"] / c["pass_att"]
            line = f"{self.ln(qb)} is {c['pass_cmp']} of {c['pass_att']} for {c['pass_yds']}"
            if c["pass_td"]:
                line += f" and {NUM_WORDS[min(c['pass_td'], 10)]} touchdown{'s' if c['pass_td'] > 1 else ''}"
            if c["pass_int"]:
                line += f", with {NUM_WORDS[min(c['pass_int'], 10)]} interception{'s' if c['pass_int'] > 1 else ''}"
            line += "."
            if pct >= 0.72:
                take = self.take("qb_hot")
            elif pct < 0.5:
                take = self.take("qb_cold")
            elif c["pass_int"]:
                take = self.take("qb_int")
            elif c["pass_yds"] >= 220:
                take = self.take("qb_big")
            else:
                take = self.take("qb_fine")
            return [("P", line), ("A", take)]
        return None

    def _t_rusher(self, sim):
        for team in (sim.offense,):                    # only the back who's on the field
            rb, carries = self._leaders(sim, team, "rush_att", 9, skip_pos=("QB",))
            if not rb:
                continue
            yds = self.stat(sim, rb, "rush_yds")
            avg = yds / max(1, carries)
            line = self.pick(f"{self.ln(rb)} is up to {carries} carries for {yds} yards.",
                             f"{carries} carries, {yds} yards for {self.ln(rb)} so far.",
                             f"{self.ln(rb)}: {yds} yards on {carries} totes.")
            if avg >= 5.5:
                take = self.take("rb_hot", rb=self.ln(rb))
            elif avg < 3.2:
                take = self.take("rb_cold", rb=self.ln(rb))
            elif carries >= 20:
                take = self.take("rb_workhorse")
            else:
                take = self.take("rb_grind")
            return [("P", line), ("A", take)]
        return None

    def _t_receiver(self, sim):
        team = sim.offense
        wr, recs = self._leaders(sim, team, "rec", 4)
        if not wr:
            return None
        yds = self.stat(sim, wr, "rec_yds")
        qb = self.ln(sim.qb_of(team))
        return [("P", self.pick(f"{self.ln(wr)} has been {qb}'s guy today — {recs} catches, {yds} yards.",
                                f"{recs} catches now for {self.ln(wr)}, {yds} yards.",
                                f"They keep finding {self.ln(wr)} — {recs} grabs, {yds} yards.",
                                f"{self.ln(wr)} is up to {yds} receiving yards on {recs} catches.")),
                ("A", self.take("wr_take", opp=sim.other(team).school))]

    def _t_defender(self, sim):
        for team in (sim.defense,):                    # only the defense that's on the field
            sk, n = self._leaders(sim, team, "sack", 2)
            if sk:
                words = NUM_WORDS[min(int(n), 10)] + (" and a half" if n % 1 else "")
                just = bool(sacks_log := getattr(self, "_sack_log", [])) and sacks_log[-1][0] == sim.plays_run
                return [("P", f"{self.ln(sk)} has {words} sacks today."),
                        ("A", self.take("sack_leader", _avoid=() if just else ("nothing's working",)))]
            tk, n = self._leaders(sim, team, "tkl", 11)
            if tk:
                return [("P", self.pick(f"{self.ln(tk)} is everywhere — {n} tackles.",
                                        f"{n} tackles already for {self.ln(tk)}.")),
                        ("A", self.take("tackle_leader"))]
        return None

    def _t_situation(self, sim):
        off, df = sim.offense, sim.defense
        diff = sim.score[off] - sim.score[df]
        if sim.quarter == 4 and sim.clock < 420:
            need = "a touchdown" if diff < -3 else ("a field goal to tie" if diff == -3 else "points")
            if diff < 0:
                return [("P", f"{off.school} down {abs(diff)} with {clock_str(sim.clock)} to play, "
                              f"{sim.timeouts[off]} timeout{'s' if sim.timeouts[off] != 1 else ''} left."),
                        ("A", self.take("sit_trail", need=need))]
            if diff > 0:
                return [("P", f"{off.school} up {diff}, {clock_str(sim.clock)} left."),
                        ("A", self.take("sit_lead", df=df.school))]
            return [("P", f"All tied up, {clock_str(sim.clock)} to go."), ("A", self.take("sit_tied"))]
        if sim.quarter == 2 and sim.clock < 240:
            return [("P", f"{clock_str(sim.clock)} left in the half."), ("A", self.take("half_end"))]
        return None

    def _t_coach(self, sim):
        if sim.quarter >= 3:
            return None                                   # the scheme intro is a first-half thing
        import staff
        team = self.rng.choice(sim.teams)
        coach = team.coach
        caller = staff.play_caller(team, "off")
        style = OFF_STYLE.get(caller.offense_scheme, "move the football")
        if caller is coach:
            line = self.pick(f"You know what you're getting from {coach.name} — he calls it himself, and they want to {style}.",
                             f"{coach.name}'s {caller.offense_scheme} offense wants to {style}.",
                             f"{team.school} under {coach.name}: they want to {style}.")
        else:
            line = self.pick(f"{coach.name} hands the offense to his coordinator, {caller.name}. It's a {caller.offense_scheme} "
                             f"attack — they want to {style}.",
                             f"{caller.name} calls the plays for {team.school}. His {caller.offense_scheme} wants to {style}.")
        if coach.aggression >= 72:
            take = self.take("coach_aggr")
        elif coach.aggression <= 38:
            take = self.take("coach_cons")
        else:
            take = f"Defensively they like to {DEF_STYLE.get(staff.play_caller(team, 'def').defense_scheme, 'play sound football')}."
        return [("P", line), ("A", take)]

    def _t_crowd(self, sim):
        if sim.neutral:
            return None
        h = sim.home
        if sim.score[h] < sim.score[sim.away] and sim.momentum.value < 10:
            return None
        if sim.momentum.value > 25 or self.chance(0.35):
            # the noise is for the road offense: with the home team on offense, it's just a loud building
            avoid = ("road team", "home defense", "for the offense") if getattr(sim, "offense", None) is h else ()
            take = self.line("crowd_take", _avoid=avoid, chant=h.chant)
            return [("P", self.line("crowd_pbp", stadium=h.stadium))] + ([("A", take)] if take else [])
        return None

    def _t_injury(self, sim):
        hurt = [i for i in sim.injuries if i[5] != "shaken"]
        if not hurt:
            return None
        seen = self._used.setdefault("injury_notes", [])
        pending = [i for i in hurt if id(i[3]) not in seen]
        if not pending:
            return None
        q, clk, team, p, desc, sev, games = pending[-1]
        seen.append(id(p))
        nxt = next((x for x in sim.depth[team][p.position] if x is not p), None)
        line = self.pick(f"Still no {self.ln(p)} for {team.school} — {desc}.",
                         f"{team.school} has been without {self.ln(p)} since he went down with {desc}.")
        take = (self.pick(f"That's a big loss. {nxt.name} has to carry it now, and that's a real drop-off.",
                          f"{nxt.name} is doing his best, but you notice {self.ln(p)} isn't out there.")
                if nxt else "They're thin at that spot now.")
        if games >= 99:
            take = self.pick("Tough way for it to end. That's his season.", "You hate it. His year is over.")
        return [("P", line), ("A", take)]

    def _t_thirddown(self, sim):
        off = sim.offense
        ts = sim.team_stats[off]
        if ts["third_att"] < 6:
            return None
        pct = 100 * ts["third_conv"] / ts["third_att"]
        take = self.take("third_good" if pct >= 50 else "third_bad")
        return [("P", f"{off.school} is {ts['third_conv']} of {ts['third_att']} on third down."), ("A", take)]

    def _t_turnovers(self, sim):
        a, h = sim.away, sim.home
        ta, th = sim.team_stats[a]["turnovers"], sim.team_stats[h]["turnovers"]
        if ta + th == 0 or abs(ta - th) < 2:
            return None
        loser, winner = (a, h) if ta > th else (h, a)
        return [("P", f"Turnover margin: {winner.school} plus {abs(ta - th)}."),
                ("A", self.take("turnover_take", loser=loser.school))]

    def featured(self, sim):
        """Players who made the play just called (empty if the moment has passed)."""
        snap, who = getattr(self, "_featured", (-1, []))
        return list(who) if snap == self.snap else []

    def _t_bio(self, sim):
        pool = [p for p in self.featured(sim) if p.position in ("QB", "RB", "WR", "TE", "LB", "S", "CB", "DL")]
        if not pool:
            return None                         # a bio belongs right after he does something
        p = self.rng.choice(pool)
        stars = STAR_WORDS.get(getattr(p, "hs_stars", 3))
        line = f"{p.name}, {self.bio(p)}"
        if stars:
            line += f", a {stars} kid coming out of high school"
        line += "."
        return [("A", line + " " + self.take("bio_take"))]

    def _t_rivalry(self, sim):
        a, h = sim.away, sim.home
        if self.league is not None and not self._used.get("series_callback") and self.chance(0.5):
            import rivalries
            said = rivalries.ingame_line(self.league, sim, self.rng)
            if said:
                self._used["series_callback"] = True
                return [said]
        riv = rivalry_name(a, h)
        if riv and self.chance(0.6):
            return [("A", self.take("rivalry_take", riv=riv)), ("P", self.take("rivalry_pbp"))]
        if a.conference == h.conference and not self.post and self.chance(0.5) \
                and not self._used.get("conf_plug"):
            self._used["conf_plug"] = True           # once a game
            if a.wins + a.losses == 0:
                first = f"It's the {a.conference} opener for both of these teams."
            else:
                first = f"A {a.conference} game, and both of these teams still have plenty in front of them."
            take = self.take("conf_take")
            return [("P", first)] + ([("A", take)] if take else [])
        return None

    def _t_explosives(self, sim):
        for team in (sim.offense, sim.defense):
            n = self.explosives[team]
            if n >= 3:
                return [("P", f"{team.school} already has {NUM_WORDS[min(n, 10)]} plays of twenty yards or more."),
                        ("A", self.take("explosive_take", opp=sim.other(team).school))]
        return None

    def _t_redzone(self, sim):
        for team in (sim.offense, sim.defense):
            trips = self.rz_trips[team]
            if trips >= 3:
                tds = self.rz_tds[team]
                if tds * 2 <= trips:
                    n_trips = NUM_WORDS[min(trips, 10)]
                    if tds == 0:
                        line = f"{team.school} has been inside the 20 {n_trips} times and hasn't scored a touchdown."
                    else:
                        td_words = f"{NUM_WORDS[min(tds, 10)]} touchdown{'s' if tds != 1 else ''}"
                        line = (f"{team.school} has been inside the 20 {n_trips} times — "
                                f"{'only ' if tds < trips - 1 else ''}{td_words} to show for it.")
                    return [("P", line), ("A", self.take("rz_bad"))]
                return [("P", f"{team.school} is {NUM_WORDS[min(tds, 10)]} for {NUM_WORDS[min(trips, 10)]} in the red zone."),
                        ("A", self.take("rz_good", _avoid=self.road_words(sim, team)))]
        return None

    def _t_streak(self, sim):
        if not self.streak:
            return None
        team, kind, n = self.streak
        if n < 3:
            return None
        if kind == "scores":
            return [("P", f"That's {NUM_WORDS[min(n, 10)]} straight scoring drives for {team.school}."),
                    ("A", self.take("streak_scores", opp=sim.other(team).school))]
        return [("P", f"{team.school} has gone {NUM_WORDS[min(n, 10)]} straight drives without points."),
                ("A", self.take("streak_empty"))]

    def _t_penalties(self, sim):
        for team in (sim.offense, sim.defense):
            ts = sim.team_stats[team]
            if ts["penalties"] >= 6:
                return [("P", f"{team.school} has {ts['penalties']} penalties for {ts['pen_yds']} yards."),
                        ("A", self.take("pen_take", _avoid=self.road_words(sim, team)))]
        return None

    def _t_possession(self, sim):
        a, h = sim.away, sim.home
        ta, th = sim.team_stats[a]["top"], sim.team_stats[h]["top"]
        if abs(ta - th) < 360 or ta + th < 900:
            return None
        lead = a if ta > th else h
        mins = abs(ta - th) // 60
        return [("P", f"{lead.school} has held the ball almost {mins} minutes longer today."), ("A", self.take("top_take"))]

    def _t_firstdowns(self, sim):
        a, h = sim.away, sim.home
        fa, fh = sim.team_stats[a]["first_downs"], sim.team_stats[h]["first_downs"]
        if fa + fh < 14 or abs(fa - fh) < 5:
            return None
        lead = a if fa > fh else h
        return [("P", f"First downs: {max(fa, fh)} for {lead.school}, {min(fa, fh)} for {sim.other(lead).school}."),
                ("A", self.take("fd_take"))]

    def _t_protection(self, sim):
        for team in (sim.offense, sim.defense):
            allowed = sum(sim.stats[p]["sacked"] for p in sim.stats if sim.team_of(p) is team)
            if allowed >= 3:
                return [("P", f"{self.ln(sim.qb_of(team))} has been sacked {NUM_WORDS[min(allowed, 10)]} times."),
                        ("A", self.take("prot_take"))]
        return None

    def _t_special(self, sim):
        for team in (sim.offense, sim.defense):
            p = sim.depth[team]["P"][0]
            punts = sim.stats.get(p, Counter())["punts"]
            if punts >= 4:
                avg = sim.stats[p]["punt_yds"] / punts
                return [("P", f"{self.ln(p)} has punted {punts} times, averaging {avg:.0f}."), ("A", self.take("punter_take"))]
            k = sim.depth[team]["K"][0]
            att = sim.stats.get(k, Counter())["fg_att"]
            if att >= 2:
                made = sim.stats[k]["fg_made"]
                return [("P", f"{self.ln(k)} is {made} for {att} on field goals."), ("A", self.take("kicker_take"))]
        return None

    def _t_matchup(self, sim):
        off, df = sim.offense, sim.defense
        wr = sim.depth[off]["WR"][0]
        cb = sim.depth[df]["CB"][0]
        if sim.team_of(wr) is not off or sim.team_of(cb) is not df:
            return None                                # never a matchup between teammates
        edge = sim.prof(wr)["route"] - sim.prof(cb)["cover"]
        if abs(edge) < 6:
            return None
        if edge > 0:
            return [("A", self.pick(f"Keep an eye on {self.ln(wr)} against {self.ln(cb)}. That's the matchup {off.school} "
                                    f"wants all day, and they should keep going back to it.",
                                    f"{self.ln(wr)} has a real edge on {self.ln(cb)}. I'd be throwing that way every chance I got."))]
        return [("A", self.pick(f"{self.ln(cb)} has been sticky on {self.ln(wr)} all afternoon. They may just take him "
                                f"away and make somebody else beat them.",
                                f"{self.ln(cb)} is winning that matchup with {self.ln(wr)}. {off.school} needs a second option."))]

    # The day's context (booth_context.py): form, rivalry heat, upset alerts, trap games, bowl math,
    # revenge, the playoff race.
    def _t_form(self, sim):
        import booth_context
        return booth_context.form(self, sim)

    def _t_rivalry_heat(self, sim):
        import booth_context
        return booth_context.rivalry_heat(self, sim)

    def _t_upset_alert(self, sim):
        import booth_context
        return booth_context.upset_alert(self, sim)

    def _t_trap(self, sim):
        import booth_context
        return booth_context.trap(self, sim)

    def _t_bowl_math(self, sim):
        import booth_context
        return booth_context.bowl_math(self, sim)

    def _t_revenge(self, sim):
        import booth_context
        return booth_context.revenge(self, sim)

    def _t_race(self, sim):
        import booth_context
        return booth_context.race(self, sim)

    def _t_stakes(self, sim):
        if self.post:
            return None
        a, h = sim.away, sim.home
        if a.wins + a.losses < 3:
            return None
        best = max((a, h), key=lambda t: t.wins)
        if best.wins >= 7:
            return [("P", f"{best.school} came in at {best.record}, still with plenty in front of them."),
                    ("A", self.take("stakes_good"))]
        worst = min((a, h), key=lambda t: t.wins)
        if worst.losses >= 6:
            return [("P", f"{worst.school} is {worst.record} and playing for pride at this point."),
                    ("A", self.take("stakes_bad"))]
        return None

    def _t_backup(self, sim):
        for team in (sim.offense, sim.defense):
            hurt = [i for i in sim.injuries if i[2] is team and i[5] != "shaken"]
            if not hurt:
                continue
            p = hurt[-1][3]
            fill = next((x for x in sim.depth[team][p.position] if x is not p), None)
            if fill is None:
                continue
            stat = sim.stats.get(fill, Counter())
            work = stat["rush_att"] + stat["rec"] + stat["tkl"]
            if work >= 4:
                return [("P", f"{self.ln(fill)} has stepped in for {self.ln(p)} and held his own."),
                        ("A", self.take("backup_take"))]
        return None

    def _t_comeback(self, sim):
        for team in sim.teams:
            deficit = self.biggest_lead[sim.other(team)]
            now = sim.score[team] - sim.score[sim.other(team)]
            if deficit >= 14 and now >= 0:
                return [("P", f"{team.school} trailed by {deficit} in this football game."), ("A", self.take("comeback_take"))]
        return None

    def _t_pace(self, sim):
        if sim.plays_run < 60:
            return None
        pace = sim.plays_run
        if pace >= 110 and sim.quarter <= 3:
            return [("P", f"We've already had {pace} plays in this football game."),
                    ("A", self.pick("Both offenses are playing fast, and the defenses are gassed.",
                                    "At this pace, whoever has the ball last probably wins.",
                                    "The scoreboard operator is earning his money today."))]
        if pace <= 80 and sim.quarter >= 4:
            return [("P", "This one has moved quickly — both teams staying on the ground."),
                    ("A", self.pick("Few possessions, so every one of them matters more.",
                                    "Short game. One mistake is magnified."))]
        return None

    def _t_youth(self, sim):
        for p in self.featured(sim):
            c = sim.stats.get(p, Counter())
            if p.year > 1:
                continue
            if c["rec_yds"] >= 50 or c["rush_yds"] >= 50 or c["tkl"] >= 6:
                cls = CLASS_WORDS[min(p.year, 3)]
                return [("A", self.pick(f"And that's a {cls}. {p.name} has been thrown right into it and he hasn't blinked.",
                                        f"Remember, {p.name} is only a {cls}. The future is bright there.",
                                        f"A {cls} playing like a veteran — {p.name} looks like he belongs."))]
        return None

    def _t_fourth_downs(self, sim):
        for team in (sim.offense, sim.defense):
            n = self.fourth_tries[team]
            if n >= 2:
                return [("P", f"{team.school} has gone for it on fourth down {NUM_WORDS[min(n, 10)]} times today."),
                        ("A", self.take("fourth_take", coach=team.coach.name))]
        return None

    def _t_drive(self, sim):
        d = sim.drive
        if not d or d["plays"] < 7:
            return None
        yards = sim.yardline - d["start"]
        if yards < 35:
            return None                                   # seven plays for twenty yards isn't a "long drive"
        return [("P", f"That's {d['plays']} plays on this drive, {yards} yards."), ("A", self.take("drive_take"))]

    def _t_ground(self, sim):
        off = sim.offense
        ts = sim.team_stats[off]
        if ts["rush_yds"] < 1 or sim.plays_run < 25:
            return None
        if ts["rush_yds"] >= 120:
            return [("P", f"{off.school} is up over {ts['rush_yds'] // 10 * 10} yards on the ground."),
                    ("A", self.take("ground_good"))]
        if ts["rush_yds"] < 40 and sim.quarter >= 3:
            return [("P", f"{off.school} has only {ts['rush_yds']} yards rushing."), ("A", self.take("ground_bad"))]
        return None

    # ── coach profiles ────────────────────────────────────────────────────
    NUMW = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}

    def _coach_facts(self, team):
        """(descriptor, [facts]) about a head coach: titles, last season, reputation, habits."""
        coach = team.coach
        desc, facts = "", []
        if self.league is not None:
            won = [c.season for c in self.league.champions if c.coach == coach.name]
            if len(won) >= 2:
                desc = f"{self.NUMW.get(len(won), len(won))}-time national champion "
                facts.append(f"won national titles in {', '.join(str(y) for y in won)}")
            elif won:
                desc = "national champion "
                facts.append(f"won the national title in {won[0]}")
        hist = [s for s in getattr(coach, "history", []) if s["school"] == team.school]
        if hist:
            w, l = sum(s["w"] for s in hist), sum(s["l"] for s in hist)
            facts.append(f"is {w}-{l} since taking over here in {coach.hired_year}")
        elif getattr(coach, "hired_year", None) == (self.league.year if self.league else None):
            facts.append("is in his first season on the job")
        last = getattr(team, "last_season", None)
        if last and last[0] + last[1]:
            w, l = last
            if w >= 11:
                facts.append(f"is coming off a {w}-{l} season")
            elif l >= 8:
                facts.append(f"is trying to move past a {w}-{l} season a year ago")
            else:
                facts.append(f"went {w}-{l} last year")
        r = coach.ratings
        if r["recruiting"] >= 88:
            facts.append(self.pick("is one of the best recruiters in the country",
                                   "can walk into any living room in America and win it"))
        if r["passing_dev"] >= 88:
            facts.append(self.pick("has a reputation for developing quarterbacks",
                                   "turns quarterbacks into pros"))
        if r["trench_dev"] >= 88:
            facts.append("builds lines — his fronts are always tough")
        if r["db_dev"] >= 88:
            facts.append("produces defensive backs like a factory")
        try:
            from playbook import signature_plays
            off_sig, def_sig = signature_plays(coach)
            if off_sig:
                facts.append(f"loves to dial up his {self.rng.choice(off_sig)} concept")
        except Exception:
            pass
        if coach.aggression >= 75:
            facts.append("goes for it on fourth down about as often as anybody")
        elif coach.aggression <= 35:
            facts.append("almost never gambles on fourth down")
        from traits import COACH_SPEECH, speakable_traits
        said = getattr(self, "_traits_said", set())
        traits = speakable_traits(coach) if coach.name not in said else []
        if traits:
            t = self.rng.choice(traits)
            facts.append(("trait", coach.name, f"is known as {COACH_SPEECH[t][0]} — {COACH_SPEECH[t][1]}"))
        return desc, facts

    def _coach_profiles(self, sim):
        a, h = sim.away, sim.home
        teams = [a, h] if self.chance(0.6) else [self.rng.choice((a, h))]
        for t in teams:
            desc, facts = self._coach_facts(t)
            side = "home" if (t is h and not sim.neutral) else ("visiting" if not sim.neutral else f"{t.school}")
            line = self.line("coach_profile", side=side, desc=desc, Desc=desc[:1].upper() + desc[1:],
                             coach=t.coach.name, team=t.school)
            if facts and self.chance(0.85):
                fact = self.rng.choice(facts)
                if isinstance(fact, tuple):                 # a reputation: say it once this game
                    self.__dict__.setdefault("_traits_said", set()).add(fact[1])
                    fact = fact[2]
                follow = self.line("coach_fact", coach=t.coach.last_name if hasattr(t.coach, "last_name")
                                   else t.coach.name.split()[-1], fact=fact)
                line = f"{line} {follow}"
            self.pbp(line)

    # ── what the coaches are changing ─────────────────────────────────────
    def _t_adjust(self, sim):
        now = sim.plays_run
        sacks = getattr(self, "_sack_log", [])
        for team in (sim.offense, sim.defense):
            plan = sim.plan[team]
            seen = self._used.setdefault(("adj", id(team)), 0)
            fresh = plan.notes[seen:]
            self._used[("adj", id(team))] = len(plan.notes)
            for snap, key, detail in reversed(fresh):
                if key.startswith("half_") or key == "sudden_change":
                    continue                              # "take a shot" can only be said before the snap
                if key.startswith(("break_tendency", "beat_box")) and (team is not sim.offense or now - snap > 1):
                    continue                              # about the play that just happened, or not at all
                if now - snap > 14:
                    continue                              # old news — the game has moved on since
                recent = sum(1 for n, t in sacks if t is team and now - n <= 15)
                if key == "blitz_less" and recent:
                    continue                              # they just got home; nothing has "dried up"
                if key == "blitz_more" and not recent:
                    continue                              # "it's working" needs something that worked
                pool = f"adj_{key}"
                if pool in LINES:
                    return [("A", self.line(pool, team=team.school, opp=sim.other(team).school, detail=detail))]
        return None

    def _halftime_adjustments(self, sim):
        said = 0
        prompts = (f"What are you looking for after the break, {self.A}?", "And coming out of the locker room?",
                   f"{self.A}, what changes in the second half?", "What about the other sideline?",
                   "And on the other side?")
        for team in sim.teams:
            for snap, key, detail in sim.plan[team].notes:
                if key == "half_run":
                    att = sum(c["rush_att"] for p_, c in sim.stats.items() if sim.team_of(p_) is team)
                    yds = sum(c["rush_yds"] for p_, c in sim.stats.items() if sim.team_of(p_) is team)
                    if att < 6 or yds / att < 4.0:
                        continue                          # "their best stuff" has to be true
                if snap == -1 and key.startswith("half_") and said < 2 and self.chance(0.8):
                    # Two voices: the play-by-play man tees up each thought, so the analyst
                    # never runs three lines in a row.
                    self.pbp(prompts[self.rng.randrange(3)] if said == 0 else prompts[3 + self.rng.randrange(2)])
                    self.analyst(self.line(f"adj_{key}", team=team.school, opp=sim.other(team).school))
                    said += 1

    # ── the season around this game ───────────────────────────────────────
    def _t_hot_seat(self, sim):
        if self.post or self.league is None:
            return None
        for t in sim.teams:
            heat = getattr(t.coach, "seat", None)
            hot = heat >= 62 if heat is not None else (t.losses >= t.wins + 2 and t.prestige >= 70)
            if t.wins + t.losses >= 3 and hot:
                return [("P", self.line("hot_seat", coach=t.coach.name, team=t.school, rec=t.record)),
                        ("A", self.line("hot_seat_take"))]
        return None

    def _t_unbeaten(self, sim):
        if self.post or self.league is None or sim.game.week < 5:
            return None
        n = sum(1 for t in self.league.teams if t.losses == 0 and t.wins > 0)
        if not 1 <= n <= 12:
            return None
        return [("P", self.line("unbeaten_count", n=NUM_WORDS[n] if n <= 10 else n)),
                ("A", self.line("unbeaten_take"))]

    def _t_playoff_picture(self, sim):
        if self.post or self.league is None or sim.game.week < 6:
            return None
        for t in sim.teams:
            r = self.rank(t)
            if r and r <= 11:
                return [("A", self.line("playoff_in", team=t.school, r=r))]
            if r and r <= 16:
                return [("A", self.line("playoff_bubble", team=t.school, r=r))]
        return None

    def _t_next_marquee(self, sim):
        if self.post or self.league is None or sim.game.week >= 13:
            return None
        R = self.league.rankings
        nxt = self.league.schedule.get(sim.game.week + 1, [])
        best, score = None, 99
        for g in nxt:
            ra, rh = R.rank_of(g.away), R.rank_of(g.home)
            if ra and rh and ra + rh < score:
                best, score = g, ra + rh
        if best is None or sim.game.home in (best.home, best.away) or sim.game.away in (best.home, best.away):
            return None
        return [("P", self.line("next_marquee", a=self.rname(best.away), h=self.rname(best.home)))]

    def _scoreboard(self, sim):
        """A quick ticker of finals from around the country, shown at breaks."""
        if self.league is None or self.muted:
            return
        games = [g for g in self._week_games(sim) if g.played and self._game_state(sim, g)[0] != "later"]
        told = self._used.setdefault("ticker_told", [])
        games = [g for g in games if id(g) not in told]
        if not games:
            return
        R = self.league.rankings
        def interest(g):
            ra, rh = R.rank_of(g.away) or 99, R.rank_of(g.home) or 99
            return min(ra, rh) + (0 if g.game_type in ps.POSTSEASON_TYPES else 5)
        pick = sorted(games, key=interest)[:4]
        told.extend(id(g) for g in pick)
        self.pbp(self.line("ticker_intro"))
        for g in pick:
            w, l = g.winner, g.loser
            tag = lambda t: f"#{R.rank_of(t)} " if R.rank_of(t) else ""
            label = f"  ({g.display_name})" if g.game_type in ps.POSTSEASON_TYPES and g.display_name else ""
            state, q, sa, sh = self._game_state(sim, g)
            if state == "live":                           # still going: the score right now
                self.note(f"     {q:<5}  {tag(g.away)}{g.away.school} {sa}, {tag(g.home)}{g.home.school} {sh}")
                continue
            ot = " OT" if g.box is not None and getattr(g.box, "ot_round", 0) else ""
            self.note(f"     FINAL{ot}  {tag(w)}{w.school} {g.score_for(w)}, {tag(l)}{l.school} {g.score_for(l)}{label}")
        g = pick[0]
        if self._game_state(sim, g)[0] != "final":
            return
        rl = R.rank_of(g.loser)
        if rl and (not R.rank_of(g.winner) or R.rank_of(g.winner) > rl):
            self.analyst(self.line("league_upset_take"))

    # ── milestones and runs ───────────────────────────────────────────────
    def _milestones(self, sim, r):
        who = [x for x in (r.carrier, r.target, r.passer, r.tackler) if x is not None]
        for p in who:
            c = sim.stats.get(p)
            if not c:
                continue
            season = p.season_stats
            checks = (("rush100", c["rush_yds"] >= 100), ("rec100", c["rec_yds"] >= 100),
                      ("pass300", c["pass_yds"] >= 300), ("passtd3", c["pass_td"] >= 3),
                      ("sack3", c["sack"] >= 3),
                      ("season_rush", season["rush_yds"] < 1000 <= season["rush_yds"] + c["rush_yds"]),
                      ("season_rec", season["rec_yds"] < 1000 <= season["rec_yds"] + c["rec_yds"]),
                      ("season_pass", season["pass_yds"] < 3000 <= season["pass_yds"] + c["pass_yds"]))
            for key, hit in checks:
                if hit and (id(p), key) not in self._ms_done:
                    self._ms_done.add((id(p), key))
                    self.pbp(self.line(f"ms_{key}", p=self.ln(p), n=NUM_WORDS[min(c["pass_td"], 10)]))
                    # The milestone IS the stat line — no "100 yards on 21 totes" right behind it.
                    topic = {"rush100": "_t_rusher", "season_rush": "_t_rusher", "rec100": "_t_receiver",
                             "season_rec": "_t_receiver", "pass300": "_t_qb", "passtd3": "_t_qb",
                             "season_pass": "_t_qb", "sack3": "_t_defender"}.get(key)
                    if topic:
                        self.cool[topic] = self.snap
                    self.last_chat = self.snap
                    if key.startswith("season") or self.chance(0.4):
                        self.analyst(self.line("ms_take"))
                    return

    def _td_count(self, sim, r):
        p = r.carrier if r.kind == "run" else r.target
        if p is None:
            return
        c = sim.stats.get(p)
        if not c:
            return
        tds = c["rush_td"] + c["rec_td"]
        key = {2: "ms_td2", 3: "ms_td3"}.get(tds)
        if key and (id(p), key) not in self._ms_done and self.chance(0.8):
            self._ms_done.add((id(p), key))
            self.analyst(self.line(key, p=self.ln(p)))

    def _track_run(self, sim, team):
        """Unanswered points: called after every score."""
        pts = sim.score[team]
        if self._run[0] is team:
            self._run[1] = self._run[1] + (pts - self._run[2])
        else:
            self._run = [team, pts - (self._last_pts.get(team, 0)), pts]
        self._run[2] = pts
        self._last_pts = dict(sim.score)
        n = self._run[1]
        if n >= 14 and n != self._used.get("run_said") and self.chance(0.7):
            self._used["run_said"] = n
            self.pbp(self.line("unanswered", team=team.school, n=n))
            if self.chance(0.6):
                # "the game has flipped" only if the run took them from behind
                was_behind = pts - n < sim.score[sim.other(team)]
                self.analyst(self.line("unanswered_take", _avoid=() if was_behind else ("flipped", "changes games"),
                                       team=team.school, opp=sim.other(team).school))

    # ── team lore ─────────────────────────────────────────────────────────
    def _lore(self, sim, team, moments, cap=6):
        """Say one unused line about this team for these moments. Home-only
        moments are skipped unless the team is actually at home."""
        lines = TEAM_LORE.get(team.school)
        if not lines:
            return False
        at_home = team is sim.home and not sim.neutral
        said = self._used.setdefault("lore_said", [])
        if len(said) >= cap and "any" in moments:
            return False
        pool = [(m, who, text) for m, who, text in lines if m in moments and text not in said
                and (m == "any" or at_home)]
        if not pool:
            return False
        m, who, text = self.rng.choice(pool)
        said.append(text)
        (self.pbp if who == "P" else self.analyst)(self._fill(sim, text))
        return True

    def _t_lore(self, sim):
        teams = list(sim.teams)
        self.rng.shuffle(teams)
        for t in teams:
            lines = TEAM_LORE.get(t.school)
            if not lines:
                continue
            said = self._used.setdefault("lore_said", [])
            if len(said) >= 6:
                return None
            at_home = t is sim.home and not sim.neutral
            pool = [(who, text) for m, who, text in lines if m in ("any", "home") and text not in said
                    and (m == "any" or at_home)]
            if pool:
                who, text = self.rng.choice(pool)
                said.append(text)
                return [(who, self._fill(sim, text))]
        return None

    # ── booth conversation helpers ────────────────────────────────────────
    def _fill(self, sim, text):
        h, a = sim.home, sim.away
        g = sim.game
        from recruiting_data import STATES
        month = (g.date.strftime("%B") if getattr(g, "date", None) else
                 ("September", "September", "September", "September", "October", "October", "October",
                  "October", "November", "November", "November", "November", "November")[min(g.week, 13) - 1])
        kw = dict(P=self.P, A=self.A, home=h.school, away=a.school, hnick=h.nickname, anick=a.nickname,
                  stadium=(g.venue.split(",")[0] if (sim.neutral or self.post) and g.venue else h.stadium),
                  state=STATES.get(getattr(h, "home_state", None), ("home",))[0], month=month,
                  hcoach=h.coach.name, acoach=a.coach.name, temp=self.weather.get("temp", ""),
                  sky=self.weather.get("sky", ""), tod=self._tod(sim), wind=self.weather.get("wind", ""),
                  dir=self.weather.get("dir", ""), field=self.weather.get("field", ""),
                  storm=self.weather.get("storm", ""), feels=self.weather.get("feels", ""))
        return text.format_map(_Blanks(kw))


    @staticmethod
    def _wx_kind(c, wx):
        """The booth's word for a quarter's conditions."""
        if c is None or wx.get("indoor"):
            return "dome"
        if c["p"]:
            if wx.get("storm") or (wx.get("kind") == "storms" and c["p"] >= 2):
                return "storm"
            return "snow" if c["type"] in ("snow", "mix") else "rain"
        if c["wind"] >= 20:
            return "wind"
        if c["temp"] >= 86:
            return "hot"
        if c["temp"] <= 42:
            return "cold"
        return "mild"

    def _set_weather(self, sim):
        """Kickoff conditions, from the game's real weather (weather.py)."""
        import weather
        wx = getattr(sim, "wx", None) or weather.truth(sim.game)
        if wx.get("indoor"):
            self.weather = {"kind": "dome", "temp": 72, "sky": "indoors"}
            return
        c = wx["q"][0]
        self.weather = {"kind": self._wx_kind(c, wx), "temp": c["temp"], "sky": wx.get("sky", "clear"),
                        "wind": c["wind"], "dir": weather.compass(c["dir"]), "field": weather.field_words(c),
                        "storm": wx.get("storm") or "", "feels": weather.feels(c)}

    def weather_turn(self, sim, change, c):
        """The weather changed with the quarter."""
        if self.muted:
            return
        import weather
        wx = sim.wx
        kind = self._wx_kind(c, wx)
        pw = weather.precip_words(c)
        lines = {
            "start": [f"And here comes the {pw.split()[-1] if pw else 'rain'} — it's started to come down.",
                      f"The {pw.split()[-1] if pw else 'rain'} has arrived. {weather.precip_words(c).capitalize()} now.",
                      "The weather that was supposed to hold off didn't. It's coming down now."],
            "stop": ["The precipitation has let up. Still a wet ball, but the worst of it is over.",
                     "It's stopped coming down. The field's going to take a while to dry out, though."],
            "harder": [f"It's really coming down now — {pw}.", "The weather's getting worse, not better."],
            "turn": [f"That rain has turned to {c['type'] if c['type'] != 'mix' else 'sleet'}.",
                     "Temperature's dropped enough that it's changing over — look at that."],
            "wind": [f"The wind has really picked up — {weather.compass(c['dir'])} at {c['wind']}, gusting to {c['gust']}.",
                     f"Flags are standing straight out now. The wind's up to {c['wind']} miles an hour."],
            "colder": [f"The temperature has dropped fast — it's {c['temp']} degrees now.",
                       f"You can feel it turn. {c['temp']} degrees and falling."],
        }[change]
        self.pbp(self.rng.choice(lines))
        follow = {"snow": "Ball security. Footing. Kickers are going to hate this.",
                  "rain": "Every ball carrier needs two hands on it now.",
                  "storm": "This is miserable. Hang on to the football.",
                  "wind": "Watch which way the teams are going now — the kicking game just changed.",
                  "cold": "The ball gets hard in this. Watch for drops."}.get(kind)
        if follow and self.chance(0.7):
            self.analyst(follow)
        fl = weather.field_words(c)
        if fl in ("sloppy", "muddy", "snow-covered") and self.chance(0.6):
            self.analyst(f"The field is {fl}. Nobody's cutting on that.")

    def weather_delay(self, sim, mins):
        if self.muted:
            return
        q = sim.quarter
        print()
        print(rule("─", C.BYELLOW))
        print(f"  {paint('⚡ WEATHER DELAY', C.BYELLOW, C.BOLD)}    {self.scoreline(sim)}")
        print(rule("─", C.BYELLOW))
        self.pbp(self.rng.choice((
            "Lightning in the area — the officials are clearing the field. Everybody into the locker rooms.",
            "There's the horn. Lightning strike within eight miles, and we are in a weather delay.",
            "They're sending everybody inside. Lightning. The fans are being told to take shelter.")), must=True)
        self.analyst(self.rng.choice((
            f"Thirty minutes from the last strike before they can come back out. This one ends up about "
            f"{mins} minutes.",
            f"It's a momentum killer — whoever had it just lost it. We'll be back in about {mins} minutes.",
            "Both staffs get to regroup. It's like a second halftime.")), must=True)
        self.pbp(self.rng.choice((f"And we're back, after a delay of {mins} minutes. The teams have had a quick warmup.",
                                  f"{mins} minutes later, we're ready to go again. What's left of the crowd is back in its seats.")), must=True)

    def _say_exchange(self, sim, exchange):
        return [(who, self._fill(sim, text)) for who, text in exchange]

    def _t_banter(self, sim):
        if sim.quarter == 4 and abs(sim.score[sim.home] - sim.score[sim.away]) <= 8:
            return None                       # nobody chats about hot dogs in a one-score fourth quarter
        if self.ot_decisive(sim) or sim.quarter > 4:
            return None
        recent = _RECENT["banter"]
        pool = [i for i in range(len(BANTER)) if i not in recent]
        if not pool:
            return None
        i = self.rng.choice(pool)
        recent.append(i)
        del recent[:-max(1, len(BANTER) * 2 // 3)]         # the oldest ones come back around eventually
        return self._say_exchange(sim, BANTER[i])

    def _t_war_story(self, sim):
        if sim.quarter == 4 and abs(sim.score[sim.home] - sim.score[sim.away]) <= 8:
            return None
        stories = WAR_STORIES.get(self.booth.get("role"), [])
        recent = _RECENT["stories"].setdefault(self.booth.get("role"), [])
        used = self._used.setdefault("stories", [])
        pool = [i for i in range(len(stories)) if i not in recent and i not in used]
        if not pool:
            return None
        i = self.rng.choice(pool)
        used.append(i)
        recent.append(i)
        del recent[:-max(1, len(stories) - 1)]
        return self._say_exchange(sim, stories[i])

    def _t_weather(self, sim):
        if not getattr(self, "weather", None) or sim.quarter < 2 or self.weather["kind"] == "dome":
            return None
        import weather
        c = weather.now(sim)
        kind = self._wx_kind(c, sim.wx) if c is not None else self.weather["kind"]
        if c is not None:
            self.weather.update(temp=c["temp"], wind=c["wind"], dir=weather.compass(c["dir"]),
                                field=weather.field_words(c), feels=weather.feels(c))
        pool = [e for e in WEATHER[kind] if id(e) not in self._used.get("weather", [])]
        if not pool:
            return None
        ex = self.rng.choice(pool)
        self._used.setdefault("weather", []).append(id(ex))
        return self._say_exchange(sim, ex)

    # ── around the league ─────────────────────────────────────────────────
    def _game_state(self, sim, g):
        """('final'|'live'|'later', quarter label, away pts, home pts) for another game this week,
        judged against the clock in this one: a 1 PM kick isn't final at 1:40."""
        me = sim.game
        if getattr(g, "date", None) is None or getattr(me, "date", None) is None or getattr(me, "kick", None) is None \
                or getattr(g, "kick", None) is None:
            return ("final", "", 0, 0)
        if g.date != me.date:
            return ("final", "", 0, 0) if g.date < me.date else ("later", "", 0, 0)
        q = min(sim.quarter, 4)
        game_secs = (q - 1) * 900 + (900 - sim.clock)
        now = me.kick + game_secs / 3600 * 180 + (20 if q >= 3 else 0)       # real minutes since midnight
        el = now - g.kick
        if el < 0:
            return ("later", "", 0, 0)
        if el >= 210:
            return ("final", "", 0, 0)
        played = min(3600, max(0, (el - (20 if el > 100 else 0)) / 180 * 3600))
        qn = min(4, int(played // 900) + 1)
        pts = {g.away: 0, g.home: 0}
        for sq, clk, team, desc in getattr(getattr(g, "box", None), "scoring", []) or []:
            if (sq - 1) * 900 + (900 - clk) > played:
                break
            t = team if team in pts else next((x for x in pts if getattr(x, "school", None) == team), None)
            if t is None:
                continue
            d = str(desc)
            pts[t] += 3 if "FG" in d else 2 if d.startswith("Safety") else 8 if "2-pt good" in d else \
                6 if ("2-pt failed" in d or "missed" in d.lower()) else 7
        return ("live", ("1st", "2nd", "3rd", "4th")[qn - 1], pts[g.away], pts[g.home])

    def _week_games(self, sim):
        if self.league is None:
            return []
        return [g for g in self.league.schedule.get(sim.game.week, []) if g is not sim.game]

    def _t_around_league(self, sim):
        games = [g for g in self._week_games(sim) if g.played]
        if not games:
            return None
        told = self._used.setdefault("league_told", [])
        games = [g for g in games if id(g) not in told]
        if not games:
            return None
        R = self.league.rankings
        # previous week's poll is what the audience knows; rank_of is current until the week ends
        def rk(t):
            return R.rank_of(t)
        mine = set(sim.teams)
        confs = {t.conference for t in sim.teams}
        scored = []
        for g in games:
            w, l = g.winner, g.loser
            rw, rl = rk(w), rk(l)
            kw = dict(w=w.school, l=l.school, ws=g.score_for(w), ls=g.score_for(l), rw=rw or "", rl=rl or "",
                      bowl=g.display_name or g.bowl_name or "", conf=w.conference, team="")
            if g.game_type in ps.POSTSEASON_TYPES:
                scored.append((5 if g.game_type in ps.CFP_TYPES else 2, "league_post", None, kw, g))
            elif rl and (not rw or rw > rl):
                scored.append((10 - rl / 5, "league_upset", "league_upset_take", kw, g))
            elif g.conference_game and w.conference in confs and not self.post:
                team = next(t for t in sim.teams if t.conference == w.conference)
                kw["team"] = team.school
                scored.append((6, "league_conf", None, kw, g))
            elif g.box is not None and getattr(g.box, "ot_round", 0):
                scored.append((4, "league_ot", None, kw, g))
            elif rw:
                scored.append((5 - rw / 10, "league_ranked_win", "league_ranked_win_take", kw, g))
            elif abs(g.home_score - g.away_score) <= 3:
                scored.append((2, "league_close", None, kw, g))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        pick = scored[:3]
        told.extend(id(x[4]) for x in pick)
        first = pick[0]
        lines = [("P", self.line("league_intro") + " " + self.line(first[1], **first[3]))]
        if len(pick) > 1 and self.chance(0.6):
            lines[0] = ("P", lines[0][1] + " " + self.line(pick[1][1], **pick[1][3]))
        take = first[2]
        if take:
            lines.append(("A", self.line(take)))
        # Golden Helmet leader elsewhere
        board = self.league.rankings.heisman[:3]
        for p, _, _ in board:
            if p.team in mine:
                continue
            g = next((x for x in games if p.team in (x.home, x.away) and x.box is not None), None)
            if g is not None and self.chance(0.5):
                c = g.box.stats.get(p)
                if c:
                    line = self._stat_phrase(p, c)
                    if line:
                        lines.append(("P", self.line("league_heisman", p=p.name, line=line, team=p.team.school)))
                        lines.append(("A", self.line("league_heisman_take")))
                        break
        return lines

    @staticmethod
    def _stat_phrase(p, c):
        if p.position == "QB" and c["pass_att"]:
            n = c["pass_td"]
            return f"{c['pass_yds']} passing yards and {n} touchdown{'' if n == 1 else 's'}"
        if c["rush_att"] >= 8:
            return f"{c['rush_yds']} rushing yards"
        if c["rec"]:
            return f"{c['rec']} catches for {c['rec_yds']} yards"
        if c["tkl"]:
            return f"{c['tkl']} tackles and {c['sack']:g} sack{'' if c['sack'] == 1 else 's'}"
        return ""

    def _t_later(self, sim):
        games = [g for g in self._week_games(sim) if not g.played]
        R = self.league.rankings if self.league else None
        if not games or R is None:
            return None
        def weight(g):
            ra, rh = R.rank_of(g.away), R.rank_of(g.home)
            return (1 if g.game_type in ps.CFP_TYPES else 0, (ra is not None) + (rh is not None), -((ra or 99) + (rh or 99)))
        g = max(games, key=weight)
        if weight(g)[1] == 0 and weight(g)[0] == 0:
            return None
        told = self._used.setdefault("later_told", [])
        if id(g) in told:
            return None
        told.append(id(g))
        mine, theirs = getattr(sim.game, "date", None), getattr(g, "date", None)
        if mine is not None and theirs is not None and theirs != mine:
            text = self.line("league_later_day", a=self.rname(g.away), h=self.rname(g.home), day=theirs.strftime("%A"))
        else:
            text = self.line("league_later", a=self.rname(g.away), h=self.rname(g.home))
        if g.neutral:
            text = text.replace(" at ", " vs. ").replace(" visits ", " against ")
        return [("P", text),
                ("A", self.line("league_later_take"))]

    def _t_next_week(self, sim):
        if self.post or self.league is None or sim.game.week >= 13:
            return None
        t = self.rng.choice(sim.teams)
        nxt = next((g for g in self.league.team_games(t) if g.week > sim.game.week and not g.played), None)
        if nxt is None:
            return None
        opp = nxt.opponent_of(t)
        verb = "plays" if nxt.neutral else ("hosts" if nxt.home is t else "visits")
        # Scale the take to the opponent: ranked or better → big; FCS or clearly worse → easy.
        gap = opp.team_ovr - t.team_ovr
        ranked = self.rank(opp)
        if getattr(opp, "fcs", False) or (gap <= -8 and not ranked):
            take = "next_week_take_easy"
        elif ranked or gap >= 3 or rivalry_name(t, opp):
            take = "next_week_take_big"
        else:
            take = "next_week_take"
        return [("P", self.line("next_week", team=t.school, verb=verb, opp=self.rname(opp))),
                ("A", self.line(take))]

    def _t_last_week(self, sim):
        if self.league is None or sim.quarter > 2:
            return None
        t = self.rng.choice(sim.teams)
        prev = [g for g in self.league.team_games(t) if g.played and g.week < sim.game.week]
        if not prev:
            return None
        g = prev[-1]
        opp = g.opponent_of(t)
        won = g.winner is t
        s_ = f"{g.score_for(t)}-{g.score_for(opp)}"
        return [("P", self.line("last_week", team=t.school, result="beat" if won else "lost to", opp=opp.school, s=s_,
                                kind="win" if won else "loss", prep="over" if won else "to")),
                ("A", self.line("last_week_take_w" if won else "last_week_take_l"))]

    def _t_poll(self, sim):
        if self.league is None or self.post or self.league.rankings.week == 0:
            return None
        top = self.league.rankings.top(4)
        kw = {f"t{i + 1}": t.school for i, t in enumerate(top)}
        return [("P", self.line("poll_top", **kw)), ("A", self.line("poll_top_take", **kw))]

    def _t_program(self, sim):
        if getattr(self, "_program_said", False) or sim.down >= 3 or (sim.quarter == 4 and sim.clock < 600):
            return None                                   # once a game, and never over a big down
        t = sim.home if not sim.neutral else self.rng.choice(sim.teams)
        self._program_said = True
        opts = []
        if t.ratings["facilities"] >= 88:
            opts.append("program_facilities")
        if t.ratings["tradition"] >= 88:
            opts.append("program_tradition")
        if t.ratings["academics"] >= 88:
            opts.append("program_academics")
        if not opts:
            return None
        return [("A", self.line(self.rng.choice(opts), team=t.school))]

    def _t_recruiting(self, sim):
        cyc = getattr(self.league, "recruiting", None) if self.league else None
        if cyc is None:
            return None
        t = self.rng.choice(sim.teams)
        try:
            n, r = len(cyc.commitments(t)), cyc.class_rank(t)
        except Exception:
            return None
        if n < 5 or not r or r > 30:
            return None
        return [("P", self.line("recruiting", team=t.school, n=n, r=r, yr=self.league.year + 1)),
                ("A", self.line("recruiting_take"))]

    # ── wider context ─────────────────────────────────────────────────────
    def _t_postseason(self, sim):
        if not self.post:
            return None
        kw = self._post_kw(sim)
        lead_team = max(sim.teams, key=lambda t: sim.score[t])
        kw["lead"] = lead_team.school if sim.score[sim.home] != sim.score[sim.away] else "either team"
        mins = max(1, ((4 - min(sim.quarter, 4)) * 900 + sim.clock) // 60) if sim.quarter <= 4 else 1
        kw["mins"] = mins
        key = {"National Championship": "ps_title_chat", "NP Semifinal": "ps_sf_chat", "NP Quarterfinal": "ps_qf_chat",
               "NP First Round": "ps_fr_chat", "Conference Championship": "ps_ccg_chat",
               "Bowl": "ps_bowl_chat"}[self.gtype]
        if sim.quarter < 2:
            return None
        take = self.line(key, **kw)
        return [("A" if self.gtype == "Bowl" else "P", take)]

    def _t_lore(self, sim):
        lore = ps.BOWL_LORE.get(sim.game.bowl_name) if self.post else None
        if not lore or len(lore) < 2 or sim.quarter < 2:
            return None
        return [("A", self.rng.choice(lore))]

    def _t_ranking(self, sim):
        if self.post or self.league is None:
            return None
        for t in (sim.home, sim.away):
            r = self.rank(t)
            if not r:
                continue
            diff = sim.score[t] - sim.score[sim.other(t)]
            if diff < 0 and sim.quarter >= 3:
                return [("P", self.pick(f"No. {r} {t.school} is in trouble here.",
                                        f"{t.school} came in ranked {r}th in the country and is trailing."
                                        if r > 3 else f"The No. {r} team in the country is trailing.")),
                        ("A", self.pick("Voters are watching. A loss here costs them a lot more than a few spots.",
                                        "This is how playoff résumés get dented.",
                                        f"{sim.other(t).school} smells it. That's a ranked scalp on the line."))]
            if diff >= 14 and self.chance(0.5):
                return [("A", self.pick(f"This is what a No. {r} team is supposed to look like.",
                                        f"{t.school} playing like it wants to move up from No. {r}."))]
        return None

    def _t_heisman(self, sim):
        if self.league is None:
            return None
        board = self.league.rankings.heisman[:5]
        for i, (p, score, blurb) in enumerate(board, 1):
            if p.team in sim.teams:
                return [("P", self.line("heisman", p=p.name, n=i, blurb=blurb)),
                        ("A", self.line("heisman_take", team=p.team.school))]
        return None

    def _t_transfer(self, sim):
        movers = [p for p in self.featured(sim) if getattr(p, "prev_school", None)]
        if not movers:
            return None
        p = self.rng.choice(movers)
        return [("A", self.line("transfer", p=p.name, school=p.prev_school))]

    def _t_hometown(self, sim):
        from recruiting_data import STATES
        pool = [p for p in self.featured(sim) if getattr(p, "home_state", None) in STATES]
        team = sim.team_of(pool[0]) if pool else sim.offense
        if not pool:
            return None
        p = self.rng.choice(pool)
        team = sim.team_of(p)
        state = STATES[p.home_state][0]
        key = "home_state_local" if p.home_state == getattr(team, "home_state", None) else "home_state_far"
        if key == "home_state_far" and self.chance(0.5):
            return None
        return [("A", self.line(key, p=p.name, state=state, team=team.school))]

    def _t_season_line(self, sim):
        team = sim.offense
        qb = sim.qb_of(team)
        rb = sim.depth[team]["RB"][0] if sim.depth[team]["RB"] else None
        wr = sim.depth[team]["WR"][0] if sim.depth[team]["WR"] else None
        opts = []
        if qb.season_stats["pass_yds"] >= 800:
            opts.append(self.line("season_qb", p=qb.name if id(qb) not in self.introduced else self.ln(qb),
                                  yds=f"{qb.season_stats['pass_yds']:,}", td=qb.season_stats["pass_td"]))
        if rb is not None and rb.season_stats["rush_yds"] >= 400:
            opts.append(self.line("season_rb", p=self.ln(rb), yds=f"{rb.season_stats['rush_yds']:,}",
                                  td=rb.season_stats["rush_td"]))
        if wr is not None and wr.season_stats["rec_yds"] >= 400:
            opts.append(self.line("season_wr", p=self.ln(wr), rec=wr.season_stats["rec"],
                                  yds=f"{wr.season_stats['rec_yds']:,}"))
        return [("P", self.rng.choice(opts))] if opts else None

    def _t_coach_trait(self, sim):
        team = self.rng.choice(sim.teams)
        coach = team.coach
        from traits import COACH_SPEECH
        t = self._trait_for(coach)
        if not t:
            return None
        noun, clause = COACH_SPEECH[t]
        return [("A", self.line("coach_trait", coach=coach.name, noun=noun, clause=clause,
                                Clause=clause[:1].upper() + clause[1:]))]

    def _t_conf_race(self, sim):
        if self.post or not sim.game.conference_game:
            return None
        for t in sim.teams:
            if t.conf_wins + t.conf_losses >= 3 and t.conf_losses <= 1:
                return [("P", self.line("conf_race", team=t.school, crec=t.conf_record, conf=t.conference)),
                        ("A", self.take("conf_take"))]
        return None

    # ── scores & specials ─────────────────────────────────────────────────
    def score(self, sim, team, kind, pts):
        if kind == "SAFETY":
            if getattr(self, "_safety_called", False):
                self._safety_called = False
                self.pbp(f"Two points for {team.school}. {self.score_words(sim)}.", must=True)
            else:
                self.pbp(f"SAFETY! Two points for {team.school}. {self.score_words(sim)}.", must=True)
            self.analyst(self.line("safety_take"))
            return
        if not getattr(self, "_td_narrated", False):
            self.pbp(self.rng.choice(self.booth["td"]).format(team=team.school), C.BOLD, C.BYELLOW, must=True)
        self._td_narrated = False
        if team is sim.home and not sim.neutral:
            self.out(f'The crowd: "{team.chant}"', C.GRAY, indent=6)
            first = sim.score[team] <= 8 and not self._used.get("first_home_td")
            self._used["first_home_td"] = True
            if first and self._lore(sim, team, ("first_td",)):
                pass
            elif self.chance(0.45):
                self._lore(sim, team, ("td",))
        lead = max(sim.score, key=lambda t: sim.score[t]) if sim.score[sim.home] != sim.score[sim.away] else None
        if lead is not None and lead is not self._leader and self._leader is not None:
            self.lead_changes += 1
            self.pbp(self.line("lead_change", score=self.score_words(sim), team=team.school), must=True)
        self._leader = lead
        self._track_run(sim, team)
        self._walkoff(sim, "score")
        if sim.quarter == 4 and sim.clock < 180 and not self._game_over and self.chance(0.8):
            self.analyst(self.line("late_td_take", clock=clock_str(sim.clock)))

    def extra_point(self, sim, team, good, text):
        if good:
            sw = self.score_words(sim)
            self.note(f"   Extra point is good. {sw[:1].upper() + sw[1:]}.")
        else:
            self.pbp(self.line("xp_miss", score=self.score_words(sim)), must=True)

    def two_point(self, sim, team):
        self.pbp(f"{team.school} is going for two.", must=True)
        self._quiet_ticker = True

    def two_point_result(self, sim, team, good, r):
        self._quiet_ticker = False
        if sim.quarter > 4:
            self._ot_possession += 1
        who = r.target or r.carrier
        if r.kind == "pass" and who is not None:
            attempt = f"The throw is for {self.ln(who)}"
        elif who is not None:
            attempt = f"They give it to {self.ln(who)}"
        else:
            attempt = "The snap"
        tail = ("and he's IN! Two-point conversion is good. " if good
                else f"— and he's stopped short{'! ' + self.ln(r.tackler) + ' with the stop. ' if r.tackler else '! '}")
        self.pbp(f"{attempt} {tail}{self.score_words(sim)}.", must=True)

    def field_goal(self, sim, good, text, dist):
        k = sim.depth[sim.offense]["K"][0]
        lead = f"{self.name(k)} on for a {dist}-yarder."
        if good:
            self.pbp(f"{lead} " + self.line("fg_good", score=self.score_words(sim)), must=True)
            self._track_run(sim, sim.offense)
            self._walkoff(sim, "score")
        else:
            why = "blocked" if "BLOCKED" in text else ("wide left" if "wide left" in text else
                                                        "wide right" if "wide right" in text else "short")
            self.pbp(f"{lead} The kick... NO GOOD, {why}!", C.BOLD, must=True)
            if self.ot_decisive(sim):
                self.analyst(self.take("stop_ot"))
                self._walkoff(sim, "stop")
            if not self._game_over:
                self.analyst(self.line("fg_miss_take", dist=dist))

    def drive_end(self, sim, d):
        res = d.get("result", "")
        log = self.drive_log.setdefault(d["team"], [])
        log.append(res)
        scored = res in ("Touchdown", "Field Goal")
        run = 1
        for prev in reversed(log[:-1]):
            if (prev in ("Touchdown", "Field Goal")) == scored:
                run += 1
            else:
                break
        self.streak = (d["team"], "scores" if scored else "empty", run)
        mins = f"{d['time'] // 60}:{d['time'] % 60:02d}"
        if res == "Touchdown":
            self.note(f"   {d['plays']} plays, {d['yards']} yards, {mins}.")
            if d["plays"] >= 10 and self.chance(0.6):
                self.analyst(self.line("long_td_drive", plays=d["plays"]))
        elif res == "Field Goal":
            self.note(f"   {d['plays']} plays, {d['yards']} yards, {mins}.")
        elif res == "Punt" and d["plays"] <= 3:
            if self.chance(0.6) and getattr(self, "_mom_3o", -9) != self.snap:
                self.pbp(self.line("three_and_out"))

    def timeout(self, sim, team):
        left = sim.timeouts[team]
        self.pbp(self.line("timeout_last" if left == 0 else "timeout", team=team.school, left=left), must=True)
        if self.chance(0.45):
            self._chatter(sim, force=True)

    def turnover_on_downs(self, sim):
        self.pbp(self.line("tod_call", team=sim.offense.school), C.BOLD, must=True)
        ctx = self.ctx(sim)
        if self.ot_decisive(sim):
            self.analyst(self.take("stop_ot"))
            self._walkoff(sim, "stop")
            return
        if ctx["ot"]:
            self.analyst(self.line("tod_ot"))
        elif ctx["blowout"]:
            self.analyst(self.take("stop_blowout"))
        elif ctx["late"] and ctx["one_score"]:
            self.analyst(self.take("stop_late"))
        elif sim.yardline >= 60:
            self.analyst(self.line("tod_short_field", team=sim.offense.school))
        else:
            self.analyst(self.take("stop_early"))

    def defensive_td(self, sim, team):
        self.pbp(self.line("defensive_td"), C.BOLD, must=True)

    def starters_out(self, sim, team, level=3):
        if self.muted:
            return
        self.analyst(self.line("starters_out", team=team.school))

    def second_team_in(self, sim, team, level=1):
        if self.muted:
            return
        if level >= 2:
            qb = sim.lineup_depth(team)["QB"][0]
            self.analyst(self.pick(f"{team.school} is putting in the backup quarterback, {qb.name}. The rest of the "
                                   "starters are coming out a few at a time.",
                                   f"Here's {qb.name} at quarterback for {team.school} — the starter's day is done."))
        else:
            self.analyst(self.pick(f"{team.school} is rotating some second-teamers in at receiver and on defense. "
                                   "The quarterback and the line stay in for now.",
                                   f"You're starting to see some backups for {team.school} — the starters are still "
                                   "in at quarterback and up front."))

    def starters_back(self, sim, team, level=0):
        if self.muted:
            return
        self.analyst(self.pick(f"And {team.school} is sending the starters back in. That lead isn't safe anymore.",
                               f"{team.school} has seen enough — the first team is back on the field."))

    def injury(self, sim, p, team, desc, severity, games, starter):
        if self.muted:
            return
        if severity == "shaken":
            self.pbp(self.line("injury_shaken", p=self.ln(p), team=team.school), must=True)
            self.__dict__.setdefault("_hurt_shaken", set()).add(id(p))   # follow up when he's back
            return
        self.pbp(self.line("injury_down", p=self.ln(p), team=team.school), C.BRED, must=True)
        if games >= 99:
            self.analyst(self.line("injury_season", desc=desc))
        elif starter:
            nxt = next((x for x in sim.depth[team][p.position] if x is not p), None)
            nxt_txt = self.pick(f"Next man up is {nxt.name}.", f"{nxt.name} will step in.",
                                f"{nxt.name} is getting loose on the sideline.") if nxt else ""
            self.analyst(self.line("injury_starter", desc=desc, next=nxt_txt))
        self.__dict__.setdefault("_hurt", set()).add(id(p))
        if games >= 99:
            status = "is out for the season"
        elif games <= 0:
            status = "won't return today, but should be back next week"
        else:
            status = f"will miss about {games} week{'s' if games != 1 else ''}"
        self.note(f"   Word from the sideline: {self.ln(p)} ({desc}) {status}.")
        self.wait(2.4)

    def player_returns(self, sim, p):
        if self.muted:
            return
        if id(p) in getattr(self, "_hurt_shaken", set()):
            self._hurt_shaken.discard(id(p))
            self.note(f"   Good news for {sim.team_of(p).school}: {self.ln(p)} is back in after that scare.")
        elif self.chance(0.5):
            self.note(f"   {self.ln(p)} is back in for {sim.team_of(p).abbr}.")

    def momentum(self, sim, team, event):
        if self.muted or self._game_over:
            return                       # no "they'll make them pay" after the last play
        if self.snap - getattr(self, "_last_mom", -99) < 12 and event not in ("pick_six", "goal_line_stand", "turnover"):
            return
        if abs(sim.score[team] - sim.score[sim.other(team)]) >= 21:
            return                       # nobody talks momentum in a blowout
        self._last_mom = self.snap
        if event == "three_and_out":
            self._mom_3o = self.snap                  # the drive summary won't say it again
        crowd = team is sim.home and not sim.neutral
        key = f"mom_{event}" if f"mom_{event}" in LINES else "mom_default"
        margin = sim.score[team] - sim.score[sim.other(team)]
        # "Taken this thing over" belongs to the team that's ahead.
        control = ("taken this thing over", "in control", "taken control", "'s game right now", "dictating",
                   "has the edge", "Advantage", "totally flipped", "flipped this whole game")
        avoid = control if margin < 0 else ("taken this thing over", "in control", "taken control", "seized") if margin <= 7 else ()
        line = self.line(key, _avoid=avoid, team=team.school, nick=team.nickname)
        if not line and margin < 0:
            line = self.line("mom_trailing", team=team.school)
        if not line:
            return
        if crowd and self.chance(0.4):
            line += " " + self.line("mom_crowd")
        if sim.momentum.leader() is team:
            self.analyst(line)

    # ── breaks ────────────────────────────────────────────────────────────
    def momentum_meter(self, sim):
        v = sim.momentum.value
        width = 21
        pos = int(round((v + 100) / 200 * (width - 1)))
        bar = "".join("●" if i == pos else ("│" if i == width // 2 else "─") for i in range(width))
        who = sim.momentum.leader()
        label = f"with {who.school}" if who else "even"
        return (f"{paint('MOMENTUM', C.GRAY)}  {sim.away.abbr:>5} {paint(bar, C.BYELLOW)} {sim.home.abbr:<5}"
                f"  {paint(label, C.GRAY)}")

    def quarter_end(self, sim):
        if getattr(self, "skip_q", None) is not None and sim.quarter >= self.skip_q:
            self.muted = False                    # the quarter you skipped is over: back on the air
            self.skip_q = None
        if self.muted:
            return
        q = sim.quarter
        label = {1: "End of the first quarter", 2: "Halftime", 3: "End of the third quarter",
                 4: "End of regulation"}.get(q, "End of the quarter")
        print()
        print(rule("─", C.GRAY))
        print(f"  {paint(label, C.BOLD, C.BWHITE)}    {self.scoreline(sim)}")
        print(f"  {self.momentum_meter(sim)}")
        print(rule("─", C.GRAY))
        if q in (1, 3):
            self.pbp(self.line("quarter_break", label=label, score=self.score_words(sim)))
            self._lore(sim, sim.home, ("q1",) if q == 1 else ("q3",))
            if self.chance(0.55):
                self._scoreboard(sim)
            self._chatter(sim, force=True)
        if q == 4 and sim.score[sim.home] == sim.score[sim.away]:
            self.pbp("We're tied at the end of regulation.")
        if q == 2:
            return                                # the halftime show has its own break, after the talk
        self._break(sim)

    def halftime(self, sim):
        if self.muted:
            return
        self.pbp(self.line("halftime_open", score=self.score_words(sim)))
        for team in sim.teams:
            qb = sim.qb_of(team)
            c = sim.stats.get(qb, Counter())
            rb, car = self._leaders(sim, team, "rush_att", 4, skip_pos=("QB",))
            bits = []
            if c["pass_att"]:
                bits.append(f"{self.ln(qb)} {c['pass_cmp']} of {c['pass_att']}, {c['pass_yds']} yards"
                            + (f", {c['pass_int']} INT" if c["pass_int"] else ""))
            if rb:
                bits.append(f"{self.ln(rb)} {car} carries for {self.stat(sim, rb, 'rush_yds')}")
            if bits:
                self.note(f"   {team.abbr}: " + "; ".join(bits) + ".")
        trailing = min(sim.teams, key=lambda t: sim.score[t])
        ts = sim.team_stats[trailing]
        if ts["turnovers"] >= 2:
            fix = "stop turning it over. You can't spot a team two possessions and expect to win."
        elif ts["third_att"] and ts["third_conv"] / ts["third_att"] < 0.35:
            fix = "convert on third down. Their defense has been on the field all half."
        elif ts["rush_yds"] < 50:
            fix = "run the football. They're too one-dimensional right now."
        else:
            fix = "finish drives. They've moved it, they just haven't come away with points."
        self.analyst(self.pick(f"{trailing.school} has twenty minutes in the locker room to figure out how to {fix}",
                               f"If I'm {trailing.school}, the halftime message is simple: {fix}",
                               f"The adjustment for {trailing.school}? {fix[0].upper() + fix[1:]}"))
        self._halftime_adjustments(sim)
        if self.chance(0.6):
            self._scoreboard(sim)
        if self.post and self.chance(0.6):
            topic = self._t_postseason(sim)
            if topic:
                (self.pbp if topic[0][0] == "P" else self.analyst)(topic[0][1])
        self._break(sim, upcoming=3)

    def _break(self, sim=None, upcoming=None):
        """Between quarters (and at the half): keep going, skip ahead, or change the pace.
        Skipping while you're coaching hands the headset to your staff for that stretch."""
        if self.muted or self.delay is None:
            return
        speed_now = next((name for k, (name, d) in SPEEDS.items() if abs(d - self.delay) < 1e-9), "custom")
        ctl = getattr(sim, "ctl", None) if sim is not None else None
        q = sim.quarter if sim is not None else 0
        if upcoming is not None:
            q = upcoming - 1                      # at the half the clock already says Q3; Q3 is next
        nxt = {1: "Q2", 2: "Q3", 3: "Q4"}.get(q)
        opts = ["[Enter] go on"]
        if nxt:
            opts.append(f"[Q] skip {nxt}")
        opts += ["[S] skip to final", f"[1-4] speed slow→instant (now {speed_now})", "[C] calls"]
        if ctl is not None:
            opts.append("[B] big moments only" if ctl.mode == "full" else "[E] every snap")
        while True:
            try:
                choice = input(paint("\n  " + "   ".join(opts) + "  > ", C.GRAY)).strip().lower()
            except EOFError:
                return
            if choice in SPEEDS:
                self.delay = SPEEDS[choice][1]
                print(paint(f"  Speed: {SPEEDS[choice][0]}.", C.GRAY))
                continue
            break
        if choice == "s":
            self.muted = True
            if ctl is not None:
                ctl.auto_until = lambda s_: False                  # the staff finishes it
        elif choice == "q" and nxt:
            self.muted = True
            self.skip_q = q + 1
            if ctl is not None:
                ctl.auto_until = lambda s_, t=q + 1: s_.quarter > t
        elif choice == "f":
            self.delay = 0.0
        elif choice == "c":
            self.show_calls = not self.show_calls
        elif choice == "b" and ctl is not None and ctl.mode == "full":
            ctl.mode = "moments"
            print(paint("  You'll get the headset back when it matters.", C.BYELLOW))
        elif choice == "e" and ctl is not None and ctl.mode == "moments":
            ctl.mode = "full"
            print(paint("  Every snap is yours again.", C.BYELLOW))

    def overtime_start(self, sim, first):
        self._ot_first = first
        self._ot_possession = 0
        self.pbp(self.line("ot_start", team=first.school))
        self.analyst(self.line("ot_start_take"))

    def ot_round(self, sim):
        self._ot_possession = 0
        if sim.ot_round >= 3:
            self.pbp(f"Third overtime — now it's two-point plays, back and forth, until somebody blinks.")
        elif sim.ot_round == 2:
            self.pbp("Second overtime. Touchdowns must be followed by two-point tries now.")

    def final(self, sim):
        if self.muted:
            self.muted = False
        home_win = sim.score[sim.home] > sim.score[sim.away]
        win = sim.home if home_win else sim.away
        lose = sim.other(win)
        g = sim.game
        print()
        print(rule("═", C.BYELLOW))
        print(pad(paint("FINAL" + (" · " + ps.banner(g) if self.post else ""), C.BOLD, C.BYELLOW), WIDTH, "center"))
        print(pad(paint(f"{sim.away.school} {sim.score[sim.away]}   —   {sim.home.school} {sim.score[sim.home]}",
                        C.BOLD, C.BWHITE), WIDTH, "center"))
        print(rule("═", C.BYELLOW))
        margin = abs(sim.score[sim.home] - sim.score[sim.away])
        hi, lo = max(sim.score.values()), min(sim.score.values())
        riv = rivalry_name(sim.home, sim.away)
        tail = f" in {riv}" if riv else ""
        # records after this game (the result is recorded once the sim returns)
        wrec, lrec = f"{win.wins + 1}-{win.losses}", f"{lose.wins}-{lose.losses + 1}"

        if sim.ot_round:
            rounds = ("", "", "double ", "triple ", "quadruple ")[min(sim.ot_round, 4)]
            self.pbp(self.pick(f"{win.school} survives {rounds}overtime{tail}, {hi}-{lo}!",
                               f"It took {rounds}overtime, but {win.school} wins it{tail}, {hi}-{lo}!",
                               f"{win.school} outlasts {lose.school} in {rounds}overtime{tail}, {hi}-{lo}!"))
        elif margin <= 3:
            self.pbp(self.pick(f"{win.school} holds on{tail}, {hi}-{lo}. What a football game.",
                               f"{win.school} escapes{tail}, {hi}-{lo}! Right down to the wire.",
                               f"By the skin of their teeth — {win.school} wins it{tail}, {hi}-{lo}."))
        elif margin <= 8:
            self.pbp(self.pick(f"{win.school} holds on{tail}, {hi}-{lo}.",
                               f"{win.school} gets it done{tail}, {hi}-{lo}.",
                               f"A hard-fought one, and {win.school} wins it{tail}, {hi}-{lo}."))
        elif margin >= 28:
            self.pbp(self.pick(f"{win.school} rolls{tail}, {hi}-{lo}.",
                               f"A dominant day for {win.school}{tail}. Final, {hi}-{lo}.",
                               f"{win.school} in a rout{tail}, {hi}-{lo}."))
        else:
            self.pbp(self.pick(f"{win.school} takes it{tail}, {hi}-{lo}.",
                               f"Final score{tail}: {win.school} {hi}, {lose.school} {lo}.",
                               f"{win.school} wins it{tail}, {hi}-{lo}."))

        import rivalries
        for who, text in rivalries.final_lines(self.league, win, lose, hi, lo, self.rng):
            (self.pbp if who == "P" else self.analyst)(text)
        kw = self._post_kw(sim) if self.post else {}
        if self.post:
            kw.update(w=win.school, l=lose.school, W=win.school.upper(), rec=wrec, coach=win.coach.name)
            self._final_post(sim, win, lose, wrec, lrec, kw)
        else:
            if win.team_ovr + 5 < lose.team_ovr:
                self.analyst(self.take("upset_take", win=win.school))
            from impact import player_of_the_game
            pog, pt, _ = player_of_the_game(sim)
            star = self._star(sim, pt if pt is not None else win)
            if star:
                if pt is lose:
                    first_word = star.split(" ", 1)[0]
                    lower_ok = first_word in ("Defensively,",) or not first_word[:1].isupper() or \
                        first_word.lower() in ("defensively,", "the")
                    star = "In a losing effort, too — " + (star[0].lower() + star[1:] if lower_ok else star)
                self.analyst(star)
            rl = self.rank(lose)
            if rl and self.chance(0.8):
                self.analyst(self.pick(f"No. {rl} {lose.school} goes down. That's going to shake up the poll.",
                                       f"A ranked team falls. {lose.school} will pay for that one on Sunday.",
                                       f"{lose.school} was No. {rl} coming in. Not anymore, probably."))
            if home_win and not sim.neutral and (riv or margin <= 3 or (rl and win.team_ovr < lose.team_ovr))\
                    and self.chance(0.7):
                self.pbp(self.pick(f"And they're coming out of the stands at {win.stadium}.",
                                   f"The students are storming the field at {win.stadium}!",
                                   f"{win.stadium} is going to be loud for a while."))
            if home_win and not sim.neutral:
                self._lore(sim, win, ("win",))
            if win.wins + 1 == 6 and g.week <= 13:
                self.pbp(self.line("bowl_clinched", team=win.school))
            if g.conference_game and self.chance(0.5):
                cw = win.conf_wins + 1
                self.pbp(f"{win.school} moves to {wrec}, {cw}-{win.conf_losses} in {win.conference} play.")
            else:
                self.pbp(f"{win.school} moves to {wrec}; {lose.school} falls to {lrec}.")
        place = (g.venue or "").split(",")[0] if (sim.neutral or self.post) else sim.home.stadium
        self.pbp(self.pick(f"For {self.booth['color']}, I'm {self.booth['pbp']}. So long from {place}.",
                           f"{self.booth['pbp']} and {self.booth['color']} "
                           f"{'saying goodnight' if (getattr(g, 'kick', None) or 20 * 60) >= 17 * 60 else 'signing off'}"
                           f" from {place}.",
                           f"That's all from {place}. For {self.booth['color']}, I'm {self.booth['pbp']}."))

    def _final_post(self, sim, win, lose, wrec, lrec, kw):
        g, gt, L = sim.game, self.gtype, self.league
        if gt == "National Championship":
            self.pbp(self.line("final_title", **kw), C.BOLD, C.BYELLOW)
            self.pbp(self.line("confetti"))
            self.analyst(self.line("final_title_take"))
            prior = [y for y in ps.titles_for(L, win.school) if y < (L.year if L else 0)] if L else []
            if L is not None:
                if prior:
                    yrs = ", ".join(str(y) for y in prior[-3:])
                    self.pbp(self.line("final_title_history_again", w=win.school, n=len(prior) + 1, years=yrs))
                else:
                    self.pbp(self.line("final_title_history_first", w=win.school))
            self.analyst(self.line("final_title_coach", coach=win.coach.name))
            self.pbp(self.line("final_title_record", w=win.school, rec=wrec))
            self._mvps(sim, win)
            self.analyst(self.line("final_title_loser", l=lose.school))
            return
        if gt == "NP Semifinal":
            self.pbp(self.line("final_sf", **kw), C.BOLD, C.BGREEN)
            self._mvps(sim, win, defense=False)
            self.pbp(self.line("final_elim", l=lose.school, rec=lrec))
        elif gt == "NP Quarterfinal":
            self.pbp(self.line("final_qf", **kw), C.BOLD, C.BGREEN)
            self._mvps(sim, win, defense=False)
            self.pbp(self.line("final_elim", l=lose.school, rec=lrec))
        elif gt == "NP First Round":
            self.pbp(self.line("final_fr", **kw), C.BOLD, C.BGREEN)
            if g.waiting is not None:
                self.analyst(self.pick(f"Now it's {g.waiting.school} in the {g.next_game}. That's a whole different animal.",
                                       f"Next up: {g.waiting.school}, rested and waiting.",
                                       f"Enjoy it tonight. {g.waiting.school} is waiting in the {g.next_game}."))
            self.pbp(self.line("final_elim", l=lose.school, rec=lrec))
        elif gt == "Conference Championship":
            self.pbp(self.line("final_ccg", **kw), C.BOLD, C.BYELLOW)
            self.analyst(self.line("final_ccg_take"))
            self._mvps(sim, win, defense=False)
        elif gt == "Bowl":
            self.pbp(self.line("final_bowl", **kw), C.BOLD, C.BYELLOW)
            if g.bowl_name == world.MAYO_BOWL:
                self.pbp(self.line("mayo", coach=win.coach.name))
            elif g.bowl_name == "Sunnyside Tarts Bowl":
                self.pbp(self.line("poptart"))
            self._mvps(sim, win, defense=False)
            self.analyst(self.line("final_bowl_take"))
        if win.team_ovr + 5 < lose.team_ovr:
            self.analyst(self.take("upset_take", win=win.school))

    def _mvps(self, sim, team, defense=True):
        p, line = self._mvp(sim, team)
        if p is not None:
            self.pbp(self.line("mvp", p=p.name, line=line))
        if defense:
            d, dline = self._mvp(sim, team, defense=True)
            if d is not None and d is not p:
                self.pbp(self.line("mvp_def", p=d.name, line=dline))

    def _star(self, sim, team):
        """The player who decided it for this team — judged on impact, not the first big stat line."""
        from impact import defense_impact, game_impact, offense_impact
        best, best_v = None, 4.0
        for p, c in sim.stats.items():
            if sim.team_of(p) is team:
                v = game_impact(c)
                if v > best_v:
                    best, best_v = p, v
        if best is None:
            return None
        p, c = best, sim.stats[best]
        if defense_impact(c) * 0.95 > offense_impact(c):
            bits = []
            if c["sack"] >= 1:
                bits.append(f"{num_words(c['sack'])} sack{'s' if c['sack'] != 1 else ''}")
            if c["int"]:
                bits.append(f"{NUM_WORDS[min(c['int'], 10)]} interception{'s' if c['int'] != 1 else ''}")
            if c["ff"]:
                bits.append("a forced fumble")
            bits.append(f"{c['tkl']} tackles")
            return f"Defensively, {p.name} took over — {', '.join(bits)}."
        if c["pass_att"] >= 10:
            td = c["pass_td"]
            tds = f" and {NUM_WORDS[min(td, 10)]} touchdown{'s' if td != 1 else ''}" if td else ""
            run = f", plus {c['rush_yds']} on the ground" if c["rush_yds"] >= 50 else ""
            ints = (f", {NUM_WORDS[min(c['pass_int'], 10)]} pick{'s' if c['pass_int'] > 1 else ''}"
                    if c["pass_int"] else "")
            return f"{p.name} was the difference — {c['pass_cmp']} of {c['pass_att']}, {c['pass_yds']} yards{tds}{ints}{run}."
        if c["rush_att"] >= c["rec"]:
            return f"{p.name} carried them, {c['rush_att']} times for {c['rush_yds']} yards" + \
                (f" and {NUM_WORDS[min(c['rush_td'], 10)]} score{'s' if c['rush_td'] != 1 else ''}."
                 if c["rush_td"] else ".")
        return f"{p.name} was unguardable today — {c['rec']} catches for {c['rec_yds']}" + \
            (f" and {NUM_WORDS[min(c['rec_td'], 10)]} touchdown{'s' if c['rec_td'] != 1 else ''}." if c["rec_td"] else ".")


def _name(p):
    return p.short_name


def box_score_lines(sim):
    a, h = sim.away, sim.home
    L = []
    cols = max(len(sim.line[a]), 4)
    header = "".join(pad(str(i + 1) if i < 4 else f"OT{i - 3 if i > 4 else ''}", 5, "right") for i in range(cols))
    L.append("  " + pad("", 22) + paint(header + pad("T", 6, "right"), C.GRAY))
    for t in (a, h):
        qs = "".join(pad(str(x), 5, "right") for x in sim.line[t])
        L.append("  " + pad(paint(t.school, C.BOLD), 22) + qs + paint(pad(str(sim.score[t]), 6, "right"), C.BOLD))
    L.append("")

    try:
        from impact import player_of_the_game
        pog, pt, side = player_of_the_game(sim) if sim.score[a] != sim.score[h] or sim.stats else (None, None, None)
    except Exception:
        pog = None
    if pog is not None:
        c = sim.stats[pog]
        if side == "def":
            bits = [f"{c['tkl']} tkl"] + [f"{c[k]:g} {lbl}" for k, lbl in (("tfl", "TFL"), ("sack", "sk"), ("int", "INT"),
                                                                           ("ff", "FF"), ("pbu", "PBU")) if c[k]]
            line = ", ".join(bits)
        elif side == "st":
            line = f"FG {c['fg_made']}/{c['fg_att']}" + (f", long {c['fg_long']}" if c["fg_made"] else "")
        elif c["pass_att"] >= 10:
            line = f"{c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} yds, {c['pass_td']} TD, {c['pass_int']} INT" + \
                (f"; {c['rush_att']}-{c['rush_yds']} rushing" if c["rush_yds"] >= 40 else "")
        elif c["rush_att"] >= c["rec"]:
            line = f"{c['rush_att']} car, {c['rush_yds']} yds, {c['rush_td']} TD" + \
                (f"; {c['rec']} rec, {c['rec_yds']} yds" if c["rec"] >= 3 else "")
        else:
            line = f"{c['rec']} rec, {c['rec_yds']} yds, {c['rec_td']} TD"
        L.append(paint("  PLAYER OF THE GAME  ", C.BYELLOW, C.BOLD) + paint(f"{pog.name}", C.BWHITE, C.BOLD)
                 + paint(f"  {pt.abbr} {pog.position}  ·  {line}", C.GRAY))
        L.append("")

    g_ = getattr(sim, "game", None)
    if g_ is not None and getattr(g_, "attendance", None):
        import facilities
        L.append(paint(f"  {facilities.attendance_line(g_)}", C.GRAY))
        L.append("")
    wx = getattr(sim, "wx", None)
    if wx:
        import weather
        if wx.get("indoor"):
            L.append(paint("  Conditions  Indoors", C.GRAY))
        else:
            L.append(paint("  Conditions  ", C.GRAY) + weather.summary(wx) + paint(f"  —  {weather.headline(wx)}", C.GRAY))
            qs = []
            for i, c in enumerate(wx["q"][:4]):
                pw = weather.precip_words(c)
                qs.append(f"Q{i + 1} {c['temp']}°" + (f" {pw.split()[-1]}" if pw else "") +
                          (f" wind {c['wind']}" if c["wind"] >= 15 else ""))
            L.append(paint("              " + "  ·  ".join(qs), C.GRAY))
            if wx.get("delay"):
                L.append(paint(f"              Lightning delay: {wx['delay']['mins']} minutes in the "
                               f"{('first', 'second', 'third', 'fourth')[wx['delay']['q'] - 1]} quarter", C.BYELLOW))
        L.append("")
    L.append(paint("  TEAM STATS", C.BCYAN))
    ts_a, ts_h = sim.team_stats[a], sim.team_stats[h]
    rows = [
        ("First downs", "first_downs"), ("Total yards", "total_yds"), ("Yards/play", None), ("Success rate", None),
        ("Passing", "pass_yds"), ("Rushing", "rush_yds"), ("Explosive plays", "explosive_plays"),
        ("  10+ yd runs", "runs_10_plus"), ("  20+ yd passes", "passes_20_plus"),
        ("Sacked-yds lost", None), ("Turnovers", "turnovers"),
        ("  Interceptions thrown", None), ("  Fumbles lost", None), ("Punts-avg", None), ("Returns-yds", None),
        ("Penalties-yds", None), ("3rd down", None), ("4th down", None), ("Red-zone TD", None), ("Time of possession", None),
    ]

    def side_total(t, key):
        return sum(c[key] for p, c in sim.stats.items() if (sim.team_of(p) if hasattr(sim, "team_of") else
                                                            (a if p in a.roster else h)) is t)

    L.append("  " + pad("", 22) + pad(a.abbr, 10, "right") + pad(h.abbr, 10, "right"))
    for label, key in rows:
        if key:
            va, vh = str(ts_a[key]), str(ts_h[key])
        elif label.startswith("Yards/play"):
            va = f"{ts_a['total_yds'] / ts_a['plays']:.1f}" if ts_a['plays'] else "0.0"
            vh = f"{ts_h['total_yds'] / ts_h['plays']:.1f}" if ts_h['plays'] else "0.0"
        elif label.startswith("Success"):
            va = f"{100 * ts_a['successful_plays'] / ts_a['plays']:.1f}%" if ts_a['plays'] else "0.0%"
            vh = f"{100 * ts_h['successful_plays'] / ts_h['plays']:.1f}%" if ts_h['plays'] else "0.0%"
        elif label.startswith("Sacked"):
            va, vh = (f"{side_total(t, 'sacked')}-{abs(sim.team_stats[t].get('sack_yds', 0))}" for t in (a, h))
        elif "Interceptions" in label:
            va, vh = (str(side_total(t, "pass_int")) for t in (a, h))
        elif "Fumbles" in label:
            va, vh = (str(max(0, sim.team_stats[t]["turnovers"] - side_total(t, "pass_int"))) for t in (a, h))
        elif label.startswith("Punts"):
            def punting(t):
                n, y = side_total(t, "punts"), side_total(t, "punt_yds")
                return f"{n}-{y / n:.1f}" if n else "0"
            va, vh = punting(a), punting(h)
        elif label.startswith("Returns"):
            def rets(t):
                n = side_total(t, "kr") + side_total(t, "pr")
                return f"{n}-{side_total(t, 'kr_yds') + side_total(t, 'pr_yds')}"
            va, vh = rets(a), rets(h)
        elif label.startswith("Pen"):
            va, vh = f"{ts_a['penalties']}-{ts_a['pen_yds']}", f"{ts_h['penalties']}-{ts_h['pen_yds']}"
        elif label.startswith("3rd"):
            va, vh = f"{ts_a['third_conv']}/{ts_a['third_att']}", f"{ts_h['third_conv']}/{ts_h['third_att']}"
        elif label.startswith("4th"):
            va, vh = f"{ts_a['fourth_conv']}/{ts_a['fourth_att']}", f"{ts_h['fourth_conv']}/{ts_h['fourth_att']}"
        elif label.startswith("Red-zone"):
            va, vh = f"{ts_a['red_zone_td']}/{ts_a['red_zone_att']}", f"{ts_h['red_zone_td']}/{ts_h['red_zone_att']}"
        else:
            va, vh = clock_str(ts_a["top"]), clock_str(ts_h["top"])
        L.append("  " + pad(label, 22) + pad(va, 10, "right") + pad(vh, 10, "right"))
    L.append("")

    def team_of(p):
        # The box score knows who played for whom that day; the current roster may not.
        if hasattr(sim, "team_of"):
            return sim.team_of(p)
        return a if p in a.roster else h

    by_team = {a: [], h: []}
    for p, c in sim.stats.items():
        by_team[team_of(p)].append((p, c))

    for t in (a, h):
        L.append(paint(f"  {t.school.upper()}", C.BOLD, C.BWHITE))
        entries = by_team[t]
        passers = sorted([e for e in entries if e[1]["pass_att"]], key=lambda e: -e[1]["pass_att"])
        for p, c in passers[:2]:
            L.append(f"    {paint('PASS', C.GRAY)} {pad(_name(p), 18)} {c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} yds, "
                     f"{c['pass_td']} TD, {c['pass_int']} INT" + (f", sacked {c['sacked']}x" if c["sacked"] else ""))
        rushers = sorted([e for e in entries if e[1]["rush_att"]], key=lambda e: -e[1]["rush_yds"])
        # Quarterbacks are always named: sack yardage lives on their line (CAB rules).
        shown = [e for e in rushers if e[0].position != "QB"][:3] + [e for e in rushers if e[0].position == "QB"]
        shown.sort(key=lambda e: -e[1]["rush_yds"])
        for p, c in shown:
            sk = f" (incl. {c['sacked']} sacks)" if p.position == "QB" and c["sacked"] else ""
            L.append(f"    {paint('RUSH', C.GRAY)} {pad(_name(p), 18)} {c['rush_att']} car, {c['rush_yds']} yds, "
                     f"{c['rush_td']} TD, long {c['rush_long']}{sk}")
        rest = [e for e in rushers if e not in shown]
        if rest:                                   # everyone else, so the lines add up to the team total
            L.append(f"    {paint('RUSH', C.GRAY)} {pad(f'Others ({len(rest)})', 18)} "
                     f"{sum(c['rush_att'] for _, c in rest)} car, {sum(c['rush_yds'] for _, c in rest)} yds, "
                     f"{sum(c['rush_td'] for _, c in rest)} TD")
        catchers = sorted([e for e in entries if e[1]["rec"]], key=lambda e: -e[1]["rec_yds"])
        for p, c in catchers[:4]:
            L.append(f"    {paint('REC ', C.GRAY)} {pad(_name(p), 18)} {c['rec']} rec ({c['targets']} tgt), {c['rec_yds']} yds, "
                     f"{c['rec_td']} TD, long {c['rec_long']}")
        rest = catchers[4:]
        if rest:
            L.append(f"    {paint('REC ', C.GRAY)} {pad(f'Others ({len(rest)})', 18)} "
                     f"{sum(c['rec'] for _, c in rest)} rec, {sum(c['rec_yds'] for _, c in rest)} yds, "
                     f"{sum(c['rec_td'] for _, c in rest)} TD")
        # The same three defensive lines for both teams: top tacklers, every sack, every pick.
        tacklers = sorted([e for e in entries if e[1]["tkl"]], key=lambda e: (-e[1]["tkl"], -e[1]["tfl"]))
        for p, c in tacklers[:4]:
            extra = [f"{c[k]:g} {lbl}" for k, lbl in (("tfl", "TFL"), ("pbu", "PBU"), ("ff", "FF")) if c[k]]
            L.append(f"    {paint('TKL ', C.GRAY)} {pad(_name(p) + ' ' + p.position, 18)} {c['tkl']} tkl"
                     + (", " + ", ".join(extra) if extra else ""))
        sackers = sorted([e for e in entries if e[1]["sack"]], key=lambda e: -e[1]["sack"])
        if sackers:
            L.append(f"    {paint('SACK', C.GRAY)} " + ", ".join(f"{_name(p)} {c['sack']:g}" for p, c in sackers))
        else:
            L.append(f"    {paint('SACK', C.GRAY)} " + paint("none", C.GRAY))
        picks = [e for e in entries if e[1]["int"]]
        if picks:
            L.append(f"    {paint('INT ', C.GRAY)} " + ", ".join(f"{_name(p)} {c['int']}" for p, c in picks))
        kickers = [e for e in entries if e[1]["fg_att"] or e[1]["xp_att"]]
        for p, c in kickers[:1]:
            L.append(f"    {paint('KICK', C.GRAY)} {pad(_name(p), 18)} FG {c['fg_made']}/{c['fg_att']}"
                     + (f" (long {c['fg_long']})" if c["fg_made"] else "") + f", XP {c['xp_made']}/{c['xp_att']}")
        for p, c in [e for e in entries if e[1]["punts"]][:1]:
            L.append(f"    {paint('PUNT', C.GRAY)} {pad(_name(p), 18)} {c['punts']} punts, {c['punt_yds']} yds, "
                     f"{c['punt_yds'] / c['punts']:.1f} avg")
        for p, c in sorted([e for e in entries if e[1]["kr"]], key=lambda e: -e[1]["kr_yds"])[:2]:
            L.append(f"    {paint('KR  ', C.GRAY)} {pad(_name(p), 18)} {c['kr']} ret, {c['kr_yds']} yds"
                     + (f", {c['kr_td']} TD" if c["kr_td"] else ""))
        for p, c in sorted([e for e in entries if e[1]["pr"]], key=lambda e: -e[1]["pr_yds"])[:2]:
            L.append(f"    {paint('PR  ', C.GRAY)} {pad(_name(p), 18)} {c['pr']} ret, {c['pr_yds']} yds"
                     + (f", {c['pr_td']} TD" if c["pr_td"] else ""))
        L.append("")

    L.append(paint("  SCORING SUMMARY", C.BCYAN))
    for q, clk, team, desc in sim.scoring:
        when = f"Q{q}" if q <= 4 else "OT"
        L.append(f"    {pad(when, 4)} {pad(clock_str(clk) if q <= 4 else '', 6)} {pad(team.abbr, 6)} {desc}")
    if not sim.scoring:
        L.append("    (no scoring)")
    injuries = [i for i in getattr(sim, "injuries", []) if i[5] != "shaken"]
    if injuries:
        L.append("")
        L.append(paint("  INJURIES", C.BCYAN))
        for q, clk, team, p, desc, sev, games in injuries:
            when = f"Q{q}" if q <= 4 else "OT"
            from injuries import outlook
            gm = getattr(sim, "game", None)
            wk = getattr(gm, "week", None) if gm is not None else None
            status = outlook(games, wk if (wk or 0) <= 13 else None)
            L.append(f"    {pad(when, 4)} {pad(team.abbr, 6)} {pad(_name(p) + ' ' + p.position, 20)} {desc} — {status}")
    return L
