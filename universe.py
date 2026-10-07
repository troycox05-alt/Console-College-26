"""
universe.py — Universes: which teams, coaches, rivalries, bowls and names a world uses.

The game ships with its own universe: original programs, coaches, rivalries,
trophies, bowls, an award and a pregame show, built on real states, towns and
stadium sizes. A UNIVERSE FILE (universes/*.json) swaps any of it out. Make one
to play with real teams, a fantasy league, or a single changed coach.

    {
      "format": "console-college-universe", "version": 1,
      "name": "My Universe", "description": "one line for the settings screen",
      "tables": {"teams_data.TEAMS": [...], "coaches_data.HEAD_COACHES": {...}, ...},
      "terms":  {"Golden Helmet": "Big Trophy", ...}
    }

TABLES  any of the game tables listed in TABLES below, by "module.NAME". A table
        that's left out keeps the built-in version. Tuples are written as lists;
        dictionaries whose keys aren't text, and sets, are written as
        {"__pairs__": [[key, value], ...]}, {"__set__": [...]} and
        {"__frozenset__": [...]}. Export any universe from Settings -> Universe
        to get a complete file to start from.
TERMS   display-only swaps: wherever the game prints the first phrase, you see
        the second (award, show, playoff, governing body, pro league...). Only
        affects what's shown; saves and rules keep the built-in words.

Settings -> Universe picks the universe for NEW worlds. A save always remembers
the universe it was built in and switches back to it when it's loaded. Saves
made before universes existed were built from real-world data and load with the
"real_2026" universe if it's in the universes/ folder.
"""
import copy
import json
import os
import re
import sys

FORMAT = "console-college-universe"
VERSION = 1
HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "universes")
DEFAULT = "default"                 # the built-in universe (no file)
LEGACY = "real_2026"                # what saves from before universes were built with

# Every table a universe can replace, by module and name.
TABLES = [
    "world.POWER", "world.BIG_TWO", "world.NIGHT_CONF", "world.WEEKNIGHT_CONF", "world.WEST_COAST_CONF",
    "world.FLAGSHIP_INDEPENDENT", "world.MAYO_BOWL", "world.SHOW_NAME", "world.UNIVERSE_NAME",
    "teams_data.TEAMS", "teams_data.ABBREVIATIONS",
    "coaches_data.HEAD_COACHES", "coaches_data.COACH_OVERRIDES", "coaches_data.COACH_STYLES",
    "coach_facts.FACTS", "coach_facts.ALMA", "coach_facts.STOPS", "coach_facts.RECENT_WINNERS",
    "fcs_data.FCS_TEAMS", "fcs_data.FCS_STATES",
    "campus_towns.TOWNS", "recruiting_data.TEAM_STATES",
    "league.CONFERENCES",
    "team_lore.TEAM_LORE",
    "rivalries.TROPHIES", "commentary.RIVALRIES", "commentary.KNOWN_ACRONYMS",
    "carousel.KNOWN_ALMA", "carousel.PRIMARY_RIVAL", "carousel.PROTECTED", "carousel.NY6", "carousel.SIGNATURE",
    "carousel.KNOWN",
    "staff.KNOWN_MENTORS",
    "season.BIG_CONFERENCES", "season.POWER_INDEPENDENTS", "season.P4_REQUIRED", "season.FCS_ODDS",
    "season.NEUTRAL_SITES", "season.RIVALRY_WEEK", "season.EARLY_RIVALRIES", "season.FIXED_WEEKS",
    "broadcast.THANKSGIVING", "broadcast.BLACK_FRIDAY", "broadcast.WEEKNIGHT_CONFS", "broadcast.NOON_SHOWCASE",
    "realignment.START_PAYOUT", "realignment.INDEPENDENT_DEALS", "realignment.START_RENEWAL",
    "realignment.EXIT_YEARS",
    "rankings.POWER_LEAGUES", "halloffame.REGIONS", "coach_screens.CONF_SHORT",
    "postseason.CFP_BOWLS", "postseason.CFP_ROTATION", "postseason._ALT_ROTATION", "postseason.TITLE_SITES",
    "postseason._TITLE_ROTATION", "postseason.CCG_SITES", "postseason.BOWLS", "postseason.BOWL_LORE",
    "postseason.REAL_CHAMPIONS",
    "gameday_history.REAL_HOSTS", "gameday_cast.CAST",
    "tailgate.EAT_THE_OPPONENT", "tailgate.SCHOOL_COOKING",
    "draft.NFL_TEAMS",
    "weather.SCHOOL_CLIMATE", "weather.ALTITUDE", "weather.CITY_STATE", "weather.INDOOR",
    "stadium.KNOWN_PARTS",
    "ui._SHORTEN", "ui.SHORT_NAMES", "ui._SQUEEZE",
    "career.OFFENSE_NOTES", "career.DEFENSE_COMPS",
]

_defaults = {}                      # "module.NAME" -> deep copy of the built-in value
_current = [DEFAULT]
_term_re = [None]
_ANSI_SPLIT = re.compile(r"(\x1b\[[0-9;?]*[A-Za-z])")


# ═══ Reading and writing JSON ═══════════════════════════════════════════════

def _enc(v):
    if isinstance(v, dict):
        if all(isinstance(k, str) for k in v):
            return {k: _enc(x) for k, x in v.items()}
        return {"__pairs__": [[_enc(k), _enc(x)] for k, x in v.items()]}
    if isinstance(v, frozenset):
        return {"__frozenset__": sorted((_enc(x) for x in v), key=repr)}
    if isinstance(v, set):
        return {"__set__": sorted((_enc(x) for x in v), key=repr)}
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    return v


def _hashable(v):
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    return v


def _sample(like):
    """One example element of a built-in table, to learn its shape from."""
    if isinstance(like, dict):
        return next(iter(like.values()), None)
    if isinstance(like, (list, tuple, set, frozenset)):
        return next(iter(like), None)
    return None


def _dec(v, like=None, inner=False):
    if isinstance(v, dict):
        if "__pairs__" in v:
            lk = next(iter(like), None) if isinstance(like, dict) else None
            out = {}
            for k, x in v["__pairs__"]:
                out[_hashable(_dec(k, lk, True))] = _dec(x, _sample(like), True)
            return out
        if "__frozenset__" in v:
            return frozenset(_hashable(_dec(x, _sample(like), True)) for x in v["__frozenset__"])
        if "__set__" in v:
            return {_hashable(_dec(x, _sample(like), True)) for x in v["__set__"]}
        s = _sample(like)
        return {k: _dec(x, s, True) for k, x in v.items()}
    if isinstance(v, list):
        items = [_dec(x, _sample(like), True) for x in v]
        if isinstance(like, tuple):
            return tuple(items)
        if isinstance(like, list):
            return items
        # no built-in example to go by: rows of plain values read as tuples, like the game's own data
        if inner and all(not isinstance(x, (list, dict, set, frozenset)) for x in items):
            return tuple(items)
        return items
    return v


# ═══ The tables ═════════════════════════════════════════════════════════════

def _split(key):
    mod, name = key.split(".", 1)
    return mod, name


def _module(mod):
    __import__(mod)
    return sys.modules[mod]


def _capture():
    if _defaults:
        return
    for key in TABLES:
        mod, name = _split(key)
        _defaults[key] = copy.deepcopy(getattr(_module(mod), name))


def _game_modules():
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None) or ""
        if f and os.path.dirname(os.path.abspath(f)) == HERE:
            yield m


def _set(key, new):
    mod, name = _split(key)
    m = _module(mod)
    old = getattr(m, name)
    if isinstance(old, dict) and isinstance(new, dict):
        old.clear()
        old.update(new)
        return
    if isinstance(old, list) and isinstance(new, list):
        old[:] = new
        return
    if isinstance(old, set) and isinstance(new, (set, frozenset)):
        old.clear()
        old.update(new)
        return
    setattr(m, name, new)
    if isinstance(old, (tuple, frozenset)):        # `from x import NAME` copies elsewhere point at the old one
        for gm in _game_modules():
            for attr, val in list(vars(gm).items()):
                if val is old and gm is not m:
                    setattr(gm, attr, new)


def _after():
    """Tables built from other tables when the game started."""
    import league
    league.CONF_INFO.clear()
    league.CONF_INFO.update({short: (full, color) for short, full, color in league.CONFERENCES})
    import preseason
    import season
    preseason.LOCKED.clear()
    preseason.LOCKED.update({frozenset(p) for p in season.RIVALRY_WEEK} | set(season.FIXED_WEEKS)
                            | set(season.EARLY_RIVALRIES))
    import custom_teams
    custom_teams._SNAPSHOT.clear()                 # custom programs snapshot this universe's tables next time


# ═══ Files ══════════════════════════════════════════════════════════════════

def path_for(name):
    return os.path.join(DIR, name + ".json")


def list_files():
    """[(name, title, description)] for every universe file in universes/."""
    out = []
    if os.path.isdir(DIR):
        for f in sorted(os.listdir(DIR)):
            if f.endswith(".json"):
                name = f[:-5]
                try:
                    with open(os.path.join(DIR, f), encoding="utf-8") as fh:
                        d = json.load(fh)
                    if d.get("format") != FORMAT:
                        continue
                    out.append((name, d.get("name") or name, d.get("description") or ""))
                except (OSError, ValueError):
                    continue
    return out


def read(name):
    with open(path_for(name), encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format") != FORMAT:
        raise ValueError(f"{name}.json isn't a Console College universe file.")
    return data


def exists(name):
    return name == DEFAULT or os.path.exists(path_for(name))


# ═══ Switching universes ════════════════════════════════════════════════════

def current():
    return _current[0]


def title(name=None):
    name = name or _current[0]
    if name == DEFAULT:
        return "Console College (built-in)"
    try:
        return read(name).get("name") or name
    except (OSError, ValueError):
        return name


def apply(name=DEFAULT):
    """Make `name` the universe the game's tables hold. Returns a list of problems (empty = fine).
    A missing or broken file falls back to the built-in universe."""
    _capture()
    problems = []
    for key in TABLES:
        _set(key, copy.deepcopy(_defaults[key]))
    terms = {}
    if name != DEFAULT:
        try:
            data = read(name)
        except (OSError, ValueError) as e:
            problems.append(f"Couldn't read universe '{name}': {e}. Using the built-in universe.")
            name = DEFAULT
            data = {}
        for key, val in (data.get("tables") or {}).items():
            if key not in _defaults:
                problems.append(f"Unknown table in universe file: {key} (ignored)")
                continue
            try:
                _set(key, _dec(val, _defaults[key]))
            except Exception as e:                        # a bad table: keep the built-in one
                _set(key, copy.deepcopy(_defaults[key]))
                problems.append(f"{key}: {e} (kept the built-in table)")
        terms = {str(k): str(v) for k, v in (data.get("terms") or {}).items()}
    import world
    world.TERMS.clear()
    world.TERMS.update(terms)
    _compile_terms()
    _after()
    _current[0] = name
    return problems


def for_league(league):
    """The universe a save was built in (saves from before universes: the real-world one)."""
    name = getattr(league, "universe", None)
    if name is None:
        name = _guess_universe(league)
        league.universe = name
    return name


def _conference_names(name):
    """Conference short names a universe defines (None if it can't be read)."""
    _capture()
    if name == DEFAULT:
        rows = _defaults["league.CONFERENCES"]
    else:
        try:
            rows = (read(name).get("tables") or {}).get("league.CONFERENCES")
        except (OSError, ValueError):
            return None
        if rows is None:
            rows = _defaults["league.CONFERENCES"]
    return {r[0] for r in rows}


def _guess_universe(league):
    """A save with no universe on record. Most are from before universes existed (real-world
    data), but a world built outside the normal New Game path can be missing it too, so go
    by the conferences its teams actually play in rather than assuming."""
    confs = [getattr(t, "conference", None) for t in getattr(league, "teams", [])]
    best, best_share = None, 0.0
    for cand in ([LEGACY] if exists(LEGACY) else []) + [DEFAULT]:
        names = _conference_names(cand)
        if not names or not confs:
            continue
        share = sum(1 for c in confs if c in names) / len(confs)
        if share > best_share:
            best, best_share = cand, share
    if best is not None and best_share >= 0.8:
        return best
    return LEGACY if exists(LEGACY) else DEFAULT


def apply_for(league):
    """Loading a save: switch to its universe. Returns problems."""
    name = for_league(league)
    if not exists(name):
        return [f"This save was built in the '{name}' universe, but universes/{name}.json is missing. "
                f"Names and lore will be the built-in ones until you put it back."] + apply(DEFAULT)
    return apply(name) if name != _current[0] else []


def export(path, name="My Universe", description=""):
    """Write every table as it is right now (the universe in use, custom programs aside)."""
    _capture()
    import world
    data = {"format": FORMAT, "version": VERSION, "name": name, "description": description, "tables": {},
            "terms": dict(world.TERMS)}
    for key in TABLES:
        mod, nm = _split(key)
        data["tables"][key] = _enc(getattr(_module(mod), nm))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    return path


# ═══ Display terms ══════════════════════════════════════════════════════════

def _compile_terms():
    import world
    if not world.TERMS:
        _term_re[0] = None
        return
    keys = sorted(world.TERMS, key=len, reverse=True)
    _term_re[0] = re.compile("|".join(r"(?<![A-Za-z])" + re.escape(k) + r"(?![a-z])" for k in keys))


def translate(text):
    """What's printed, with the universe's display terms swapped in."""
    rx = _term_re[0]
    if rx is None or not text or not isinstance(text, str):
        return text
    import world
    if "\x1b" not in text:
        return rx.sub(lambda m: world.TERMS[m.group(0)], text)
    # color codes end in a letter ("\x1b[0m"): translate the words between them, not across them
    parts = _ANSI_SPLIT.split(text)
    return "".join(p if p.startswith("\x1b") else rx.sub(lambda m: world.TERMS[m.group(0)], p) for p in parts)


# ═══ Saves from before universes ════════════════════════════════════════════

# Words the game used to keep in a save that it now spells the built-in way. Saves made
# before v29 are walked once on load and these are swapped (exact matches only).
LEGACY_STRINGS = {
    "CFP First Round": "NP First Round", "CFP Quarterfinal": "NP Quarterfinal", "CFP Semifinal": "NP Semifinal",
    "CFP Appearance": "NP Appearance", "Heisman Trophy": "Golden Helmet", "Big Noon": "High Noon",
    "MACtion": "Lake Country Lights",
}


def migrate_legacy(league):
    seen = set()

    def fix(v):
        if isinstance(v, str):
            return LEGACY_STRINGS.get(v, v)
        if isinstance(v, (int, float, bool)) or v is None:
            return v
        if id(v) in seen:
            return v
        if isinstance(v, tuple):
            new = tuple(fix(x) for x in v)
            return v if all(a is b for a, b in zip(new, v)) else (type(v)(*new) if hasattr(v, "_fields") else new)
        seen.add(id(v))
        if isinstance(v, list):
            for i, x in enumerate(v):
                y = fix(x)
                if y is not x:
                    v[i] = y
        elif isinstance(v, dict):
            for k in list(v):
                x = v[k]
                y = fix(x)
                k2 = fix(k)
                if k2 is not k:
                    del v[k]
                    v[k2] = y
                elif y is not x:
                    v[k] = y
        elif isinstance(v, set):
            new = {fix(x) for x in v}
            if new != v:
                v.clear()
                v.update(new)
        elif hasattr(v, "__dict__") and not isinstance(v, type) and type(v).__module__ != "builtins":
            for k, x in list(vars(v).items()):
                y = fix(x)
                if y is not x:
                    try:
                        setattr(v, k, y)
                    except AttributeError:
                        pass
        return v

    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 200000))
    try:
        fix(league)
    finally:
        sys.setrecursionlimit(limit)
