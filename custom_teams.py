"""
custom_teams.py — Custom programs: team files (JSON), and putting them in a world.

A TEAM FILE is one program, everything the game keeps about it:

    {
      "format": "console-college-team", "version": 1,
      "school": "Sacramento Valley", "nickname": "Condors", "abbr": "SVU", "short_name": "Sac Valley",
      "conference": "High Country", "division": null, "chant": "Fly, Condors!",
      "home_state": "CA", "town": "Sacramento, California", "altitude": 30,
      "stadium": {"name": "Condor Field", "capacity": 32000, "indoor": false, "parts": {"lower_bowl": 4, ...}},
      "ratings": {"offense": 60, "defense": 58, "coach": 66, "athletic_director": 62, "facilities": 64,
                  "academics": 70, "tradition": 40, "campus": 72},
      "facilities": {"recruiting": 5, "training": 5, "stadium": 4},
      "budget": 42000000,
      "coach": {"name": "...", "age": 48, "overall": 66, "offense_scheme": "Spread RPO",
                "defense_scheme": "4-2-5 Quarters", "aggression": 55, "personality": "builder",
                "alma_mater": "...", "ratings": {"recruiting": 64, "passing_dev": 66, ...}},
      "coordinators": {"oc": {"name": "...", "overall": 62, "offense_scheme": "..."},
                       "dc": {"name": "...", "overall": 60, "defense_scheme": "..."}},
      "ad": {"name": "...", "style": "patient"},
      "rival": "Fresno State", "trophy": "the Valley Oar",
      "lore": ["Any line the booth can use about the program."],
      "tailgate": ["tri-tip", "Santa Maria tri-tip, red oak, nothing else."],
      "replaces": "Kent State",               # optional: take that program's place
      "roster": [ {player}, ... ]            # optional: without it the program recruits one
    }

A player: first_name, last_name, position, number, year (0-3 = FR-SR), redshirt, height (inches),
weight, home_state, hs_stars, potential (1-99), prof_ceiling, fundamentals {strength, speed, quickness,
iq, injury, playmaker}, proficiency {position: 0.1-1.2} (or just his own position), traits [keys].
Anything missing is filled in; anything out of range is pulled back into range (with a warning).

Where files live: the custom_teams/ folder next to the game. Export any program from the team
builder to get a complete file to start from.

IN A NEW WORLD (main menu -> New -> custom teams): a file joins its conference or replaces a
program, before the pre-2026 years are played, so it arrives with a real history. A file with a
roster keeps that roster exactly (it's put back after the burn-in).

IN A SAVE (team page -> [J]): edit any program in place, or load a file over one. The schedule
slot, the recruits and the history stay; the old name stays in the old box scores.

The game's own tables that are keyed by school (abbreviations, home states, towns, rivals,
trophies, altitude, lore, tailgate food) are filled in from the file every time the world is
built or loaded (league.custom_specs), so a custom program is at home everywhere.
"""
import copy
import json
import os
import random
import re

from models import POSITIONS, Team, Coach, Player, FUNDAMENTALS

FORMAT = "console-college-team"
VERSION = 1
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_teams")

OFF_SCHEMES = ("Spread RPO", "Pro Style", "West Coast", "Air Raid", "Smashmouth", "Triple Option", "Power Spread",
               "Veer & Shoot")
DEF_SCHEMES = ("4-2-5 Quarters", "4-3 Zone", "Pressure 3-4", "Multiple Man", "3-3-5 Stack", "Tite Front")
STATES = ("AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
          "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
          "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY")


class SpecError(ValueError):
    pass


def _init_snapshot():
    try:
        _snapshot()
    except Exception:
        pass


def _clamp(v, lo, hi, default):
    try:
        v = type(default)(v) if not isinstance(default, bool) else bool(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v)) if not isinstance(v, bool) else v


# ═══ Reading and checking a file ═════════════════════════════════════════════

def default_spec(school="New School"):
    return {
        "format": FORMAT, "version": VERSION, "school": school, "nickname": "Pioneers", "abbr": "",
        "short_name": "", "conference": "Independent", "division": None, "chant": "Go Pioneers!",
        "home_state": "TX", "town": "", "altitude": None,
        "stadium": {"name": f"{school} Stadium", "capacity": 30000, "indoor": False, "parts": {}},
        "ratings": {k: 55 for k in Team.RATING_KEYS},
        "facilities": {}, "budget": None,
        "coach": {"name": "Pat Doe", "age": 48, "overall": None, "offense_scheme": "Spread RPO",
                  "defense_scheme": "4-2-5 Quarters", "aggression": 50, "personality": None, "alma_mater": None,
                  "ratings": {}},
        "coordinators": {}, "ad": {"name": "", "style": ""},
        "rival": None, "trophy": None, "lore": [], "tailgate": None, "replaces": None, "roster": None,
    }


def normalize(spec, league_schools=None, conferences=None):
    """A complete, in-range spec, and a list of what was fixed. Raises SpecError
    only for what can't be fixed (no school name, not a team file)."""
    if not isinstance(spec, dict):
        raise SpecError("That file isn't a team (expected a JSON object).")
    if spec.get("format") not in (None, FORMAT):
        raise SpecError(f"Not a Console College team file (format: {spec.get('format')!r}).")
    out = default_spec(str(spec.get("school") or "").strip() or "New School")
    warn = []
    if not str(spec.get("school") or "").strip():
        raise SpecError("A team file needs a \"school\".")
    for k in ("nickname", "chant", "abbr", "short_name", "town", "trophy"):
        if spec.get(k) is not None:
            out[k] = str(spec[k]).strip()
    out["school"] = str(spec["school"]).strip()[:40]
    if not out["abbr"]:
        out["abbr"] = make_abbr(out["school"])
    out["abbr"] = out["abbr"].upper()[:5]
    out["conference"] = str(spec.get("conference") or "Independent")
    if conferences and out["conference"] not in conferences:
        # a file written for another universe: its name for this conference (universe display terms)
        import world
        alias = {**{v: k for k, v in world.TERMS.items()}, **world.TERMS}.get(out["conference"])
        if alias in conferences:
            out["conference"] = alias
    if conferences and out["conference"] not in conferences:
        warn.append(f"Unknown conference {out['conference']!r}: the program plays as an Independent.")
        out["conference"] = "Independent"
    out["division"] = spec.get("division") or None
    st = str(spec.get("home_state") or "TX").upper()
    if st not in STATES:
        warn.append(f"Unknown home state {st!r}; using TX.")
        st = "TX"
    out["home_state"] = st
    if spec.get("altitude") is not None:
        out["altitude"] = _clamp(spec["altitude"], 0, 12000, 0)
    s = spec.get("stadium") or {}
    out["stadium"] = {"name": str(s.get("name") or f"{out['school']} Stadium")[:60],
                      "capacity": _clamp(s.get("capacity", 30000), 5000, 115000, 30000),
                      "indoor": bool(s.get("indoor", False)),
                      "parts": {}}
    import stadium as stad
    for part, lvl in (s.get("parts") or {}).items():
        if part in stad.PARTS:
            info = stad.PARTS[part]
            out["stadium"]["parts"][part] = _clamp(lvl, info.get("min", 0), len(info["tiers"]) - 1, info.get("min", 0))
        else:
            warn.append(f"Unknown stadium part {part!r} ignored.")
    r = spec.get("ratings") or {}
    for k in Team.RATING_KEYS:
        out["ratings"][k] = _clamp(r.get(k, 55), 1, 99, 55)
    for k, v in (spec.get("facilities") or {}).items():
        if k in ("recruiting", "training", "stadium"):
            out["facilities"][k] = _clamp(v, 1, 10, 5)
    if spec.get("budget") is not None:
        out["budget"] = _clamp(spec["budget"], 5_000_000, 400_000_000, 40_000_000)
    c = spec.get("coach") or {}
    oc = out["coach"]
    oc["name"] = str(c.get("name") or oc["name"]).strip()[:40]
    oc["age"] = _clamp(c.get("age", 48), 28, 80, 48)
    oc["overall"] = _clamp(c["overall"], 20, 99, 60) if c.get("overall") is not None else None
    oc["offense_scheme"] = c.get("offense_scheme") if c.get("offense_scheme") in OFF_SCHEMES else "Spread RPO"
    oc["defense_scheme"] = c.get("defense_scheme") if c.get("defense_scheme") in DEF_SCHEMES else "4-2-5 Quarters"
    oc["aggression"] = _clamp(c.get("aggression", 50), 1, 100, 50)
    import carousel
    oc["personality"] = c.get("personality") if c.get("personality") in carousel.PERSONALITIES else None
    oc["alma_mater"] = c.get("alma_mater") or None
    oc["ratings"] = {k: _clamp(v, 20, 99, 60) for k, v in (c.get("ratings") or {}).items() if k in Coach.RATING_KEYS}
    for role, scheme_key, schemes in (("oc", "offense_scheme", OFF_SCHEMES), ("dc", "defense_scheme", DEF_SCHEMES)):
        cc = (spec.get("coordinators") or {}).get(role)
        if cc and cc.get("name"):
            out["coordinators"][role] = {"name": str(cc["name"])[:40], "overall": _clamp(cc.get("overall", 60), 20, 99, 60),
                                         scheme_key: cc.get(scheme_key) if cc.get(scheme_key) in schemes else None}
    a = spec.get("ad") or {}
    out["ad"] = {"name": str(a.get("name") or ""), "style": a.get("style") if a.get("style") in carousel.AD_STYLES else ""}
    out["rival"] = spec.get("rival") or None
    if out["rival"] and league_schools is not None and out["rival"] not in league_schools:
        warn.append(f"Rival {out['rival']!r} isn't in this world; no rival set.")
        out["rival"] = None
    out["lore"] = [str(x)[:220] for x in (spec.get("lore") or []) if str(x).strip()][:20]
    t = spec.get("tailgate")
    out["tailgate"] = [str(t[0])[:40], str(t[1])[:200]] if isinstance(t, (list, tuple)) and len(t) == 2 else None
    out["replaces"] = spec.get("replaces") or None
    if spec.get("roster"):
        roster, w = normalize_roster(spec["roster"])
        out["roster"] = roster
        warn += w
    return out, warn


def normalize_roster(rows):
    out, warn = [], []
    used = set()
    if not isinstance(rows, list):
        return None, ["\"roster\" should be a list of players; ignored."]
    for i, d in enumerate(rows, 1):
        if not isinstance(d, dict) or d.get("position") not in POSITIONS:
            warn.append(f"Roster entry {i}: no valid position; skipped.")
            continue
        pos = d["position"]
        p = {"first_name": str(d.get("first_name") or "Player")[:20], "last_name": str(d.get("last_name") or str(i))[:24],
             "position": pos, "year": _clamp(d.get("year", 0), 0, 3, 0), "redshirt": bool(d.get("redshirt", False)),
             "height": _clamp(d.get("height", 74), 64, 84, 74), "weight": _clamp(d.get("weight", 220), 150, 380, 220),
             "home_state": d.get("home_state") if d.get("home_state") in STATES else None,
             "hs_stars": _clamp(d.get("hs_stars", 3), 0, 5, 3), "potential": _clamp(d.get("potential", 50), 1, 99, 50),
             "prof_ceiling": _clamp(d.get("prof_ceiling", 1.0), 0.6, 1.2, 1.0),
             "fundamentals": {}, "proficiency": {}, "traits": [], "number": None}
        f = d.get("fundamentals") or {}
        for k in FUNDAMENTALS:
            p["fundamentals"][k] = _clamp(f.get(k, 60), 15, 99, 60)
        prof = d.get("proficiency") or {}
        if isinstance(prof, (int, float)):
            prof = {pos: prof}
        for k, v in prof.items():
            if k in POSITIONS:
                p["proficiency"][k] = _clamp(v, 0.1, 1.2, 0.8)
        p["proficiency"].setdefault(pos, 0.85)
        from traits import PLAYER_TRAITS
        p["traits"] = [t for t in (d.get("traits") or []) if t in PLAYER_TRAITS][:3]
        n = d.get("number")
        if isinstance(n, int) and 0 <= n <= 99 and n not in used:
            p["number"] = n
            used.add(n)
        if d.get("_ref") is not None:
            p["_ref"] = d["_ref"]
        for k in ("morale", "nil"):
            if d.get(k) is not None:
                p[k] = _clamp(d[k], 0, 100 if k == "morale" else 5_000_000, 50 if k == "morale" else 0)
        out.append(p)
    from roster import ROSTER_SIZE
    need = {pos: n for pos, n in ROSTER_SIZE.items()}
    for p in out:
        need[p["position"]] = need.get(p["position"], 0) - 1
    short = {pos: n for pos, n in need.items() if n > 0}
    if short:
        warn.append("Walk-ons fill the rest of the roster: " + ", ".join(f"{n} {pos}" for pos, n in short.items()) + ".")
    return out, warn


def make_abbr(school):
    words = re.findall(r"[A-Za-z]+", school)
    if len(words) >= 2:
        return "".join(w[0] for w in words)[:4].upper()
    return school[:4].upper()


def load_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_files():
    if not os.path.isdir(DIR):
        return []
    out = []
    for fn in sorted(os.listdir(DIR)):
        if fn.lower().endswith(".json"):
            path = os.path.join(DIR, fn)
            try:
                d = load_file(path)
                out.append((path, d.get("school", fn), d))
            except (OSError, ValueError):
                out.append((path, f"{fn} (unreadable)", None))
    return out


def save_file(spec, name=None):
    os.makedirs(DIR, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", (name or spec["school"]).lower()).strip("_") or "team"
    path = os.path.join(DIR, f"{slug}.json")
    clean = copy.deepcopy(spec)
    for d in clean.get("roster") or []:
        d.pop("_ref", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    return path


# ═══ From a live program ═════════════════════════════════════════════════════

def player_dict(p):
    d = {"first_name": p.first_name, "last_name": p.last_name, "position": p.position, "number": p.number,
         "year": p.year, "redshirt": p.redshirt, "height": p.height, "weight": p.weight,
         "home_state": p.home_state, "hs_stars": p.hs_stars, "potential": p.potential,
         "prof_ceiling": p.prof_ceiling, "fundamentals": dict(p.fundamentals),
         "proficiency": {k: v for k, v in p.proficiency.items() if v >= 0.3 or k == p.position},
         "traits": list(p.traits), "morale": round(getattr(p, "morale", 50)), "nil": getattr(p, "nil", 0),
         "overall": p.overall}
    return d


def from_team(league, team, roster=True):
    """Everything the game keeps about a program, as a team file."""
    import campus_towns
    import weather
    import carousel
    import rivalries
    import tailgate
    import team_lore
    from recruiting_data import TEAM_STATES
    c = team.coach
    spec = default_spec(team.school)
    spec.update({
        "school": team.school, "nickname": team.nickname, "abbr": team.abbr,
        "short_name": _short(team.school), "conference": team.conference, "division": team.division,
        "chant": team.chant, "home_state": getattr(team, "home_state", None) or TEAM_STATES.get(team.school, "TX"),
        "town": campus_towns.TOWNS.get(team.school, ""), "altitude": weather.ALTITUDE.get(team.school),
        "stadium": {"name": team.stadium, "capacity": getattr(team, "base_capacity", team.capacity),
                    "indoor": any(w in team.stadium for w in weather.INDOOR),
                    "parts": dict((getattr(team, "stad", None) or {}).get("parts", {}))},
        "ratings": dict(team.ratings),
        "facilities": dict(getattr(team, "fac", {}) or {}),
        "budget": getattr(team, "budget", None),
        "ad": {"name": team.ad.get("name", ""), "style": team.ad.get("style", "")} if getattr(team, "ad", None) else
              {"name": "", "style": ""},
        "rival": carousel.PRIMARY_RIVAL.get(team.school),
        "lore": [x[2] for x in team_lore.TEAM_LORE.get(team.school, []) if len(x) >= 3],
        "tailgate": list(tailgate.SCHOOL_COOKING[team.school]) if team.school in tailgate.SCHOOL_COOKING else None,
        "replaces": None,
    })
    if spec["rival"]:
        spec["trophy"] = rivalries.TROPHIES.get(frozenset((team.school, spec["rival"])))
    if c is not None:
        spec["coach"] = {"name": c.name, "age": getattr(c, "age", 48), "overall": c.overall,
                         "offense_scheme": c.offense_scheme, "defense_scheme": c.defense_scheme,
                         "aggression": c.aggression, "personality": getattr(c, "personality", None),
                         "alma_mater": getattr(c, "alma_mater", None), "ratings": dict(c.ratings)}
    for role, scheme_key in (("oc", "offense_scheme"), ("dc", "defense_scheme")):
        cc = getattr(team, role, None)
        if cc is not None:
            spec["coordinators"][role] = {"name": cc.name, "overall": cc.overall, scheme_key: getattr(cc, scheme_key)}
    if roster:
        ordered = sorted(team.roster, key=lambda p: (POSITIONS.index(p.position), -p.overall))
        spec["roster"] = []
        for p in ordered:
            d = player_dict(p)
            d["_ref"] = id(p)                  # in a save: this is that player (never written to a file)
            spec["roster"].append(d)
    else:
        spec["roster"] = None
    return spec


def _short(school):
    from ui import SHORT_NAMES
    return SHORT_NAMES.get(school, "")


# ═══ The game's school-keyed tables ══════════════════════════════════════════

def register(spec, renames=None):
    """Fill in every table the game looks schools up in."""
    import campus_towns
    import weather
    import carousel
    import rivalries
    import tailgate
    import team_lore
    import ui
    from teams_data import ABBREVIATIONS
    from recruiting_data import TEAM_STATES
    s = spec["school"]
    ABBREVIATIONS[s] = spec["abbr"] or make_abbr(s)
    if spec.get("short_name"):
        ui.SHORT_NAMES[s] = spec["short_name"]
    TEAM_STATES[s] = spec["home_state"]
    if spec.get("town"):
        campus_towns.TOWNS[s] = spec["town"]
    if spec.get("altitude") is not None:
        weather.ALTITUDE[s] = spec["altitude"]
    if spec.get("rival"):
        carousel.PRIMARY_RIVAL[s] = spec["rival"]
        if spec.get("trophy"):
            rivalries.TROPHIES[frozenset((s, spec["rival"]))] = spec["trophy"]
    if spec.get("lore"):
        team_lore.TEAM_LORE[s] = [("any", "A", line) for line in spec["lore"]]
    if spec.get("tailgate"):
        tailgate.SCHOOL_COOKING[s] = tuple(spec["tailgate"])
    if spec.get("stadium", {}).get("indoor"):
        name = spec["stadium"]["name"]
        if not any(w in name for w in weather.INDOOR):
            weather.INDOOR = tuple(weather.INDOOR) + (name,)
    for old, new in (renames or {}).items():
        _remap(old, new)


def _remap(old, new):
    """Another program takes old's place: rivals, trophies and protected games follow."""
    import carousel
    import rivalries
    for k, v in list(carousel.PRIMARY_RIVAL.items()):
        if v == old:
            carousel.PRIMARY_RIVAL[k] = new
    if old in carousel.PRIMARY_RIVAL and new not in carousel.PRIMARY_RIVAL:
        carousel.PRIMARY_RIVAL[new] = carousel.PRIMARY_RIVAL[old]
    for pair, name in list(rivalries.TROPHIES.items()):
        if old in pair:
            other = [x for x in pair if x != old]
            if other:
                rivalries.TROPHIES[frozenset((new, other[0]))] = name
    carousel.PROTECTED[:] = [tuple(new if x == old else x for x in pair) for pair in carousel.PROTECTED]
    for k, v in list(carousel.SIGNATURE.items()):
        if v and len(v) >= 3 and v[2] == old:
            carousel.SIGNATURE[k] = (v[0], v[1], new)


def _tables():
    import campus_towns
    import weather
    import carousel
    import rivalries
    import tailgate
    import team_lore
    import ui
    from teams_data import ABBREVIATIONS
    from recruiting_data import TEAM_STATES
    return {"abbr": (ABBREVIATIONS, None), "short": (ui.SHORT_NAMES, None), "states": (TEAM_STATES, None),
            "towns": (campus_towns.TOWNS, None), "alt": (weather.ALTITUDE, None),
            "rival": (carousel.PRIMARY_RIVAL, None), "trophies": (rivalries.TROPHIES, None),
            "lore": (team_lore.TEAM_LORE, None), "cooking": (tailgate.SCHOOL_COOKING, None),
            "signature": (carousel.SIGNATURE, None), "protected": (carousel.PROTECTED, None)}


_SNAPSHOT = {}


def _snapshot():
    if not _SNAPSHOT:
        import weather
        for k, (tbl, _) in _tables().items():
            _SNAPSHOT[k] = copy.copy(tbl)
        _SNAPSHOT["indoor"] = tuple(weather.INDOOR)


def reset_tables():
    """Back to the game's own data (a new world, or loading a different save)."""
    _snapshot()
    import weather
    for k, (tbl, _) in _tables().items():
        orig = _SNAPSHOT[k]
        if isinstance(tbl, dict):
            tbl.clear()
            tbl.update(orig)
        else:
            tbl[:] = list(orig)
    weather.INDOOR = _SNAPSHOT["indoor"]


def register_all(league):
    """On load, and when a world is built: every custom program, back in the tables."""
    reset_tables()
    for spec in getattr(league, "custom_specs", {}).values():
        register(spec)
    for old, new in getattr(league, "custom_renames", {}).items():
        _remap(old, new)


# ═══ A new world ═════════════════════════════════════════════════════════════

def world_rows(teams_rows, specs):
    """teams_data rows for a new world: files that replace a program take its row,
    the rest join. Returns (rows, renames)."""
    rows = list(teams_rows)
    renames = {}
    for spec in specs:
        r = spec["ratings"]
        row = (spec["school"], spec["nickname"], spec["stadium"]["name"], spec["stadium"]["capacity"],
               spec["conference"], spec["division"], spec["chant"],
               *[r[k] for k in Team.RATING_KEYS])
        idx = next((i for i, x in enumerate(rows) if x[0] == spec["school"]), None)
        if idx is None and spec.get("replaces"):
            idx = next((i for i, x in enumerate(rows) if x[0] == spec["replaces"]), None)
            if idx is not None:
                renames[spec["replaces"]] = spec["school"]
                if not spec.get("conference") or spec["conference"] == "Independent":
                    row = row[:4] + (rows[idx][4], rows[idx][5]) + row[6:]
                    spec["conference"], spec["division"] = rows[idx][4], rows[idx][5]
        if idx is None:
            rows.append(row)
        else:
            rows[idx] = row
    return rows, renames


def coach_name_for(spec):
    return spec["coach"]["name"]


def finish_world(league, specs, renames):
    """After the burn-in and the carousel: the file's coach, staff, AD, facilities,
    money and stadium, and its roster if it brought one."""
    league.custom_specs = {s["school"]: copy.deepcopy(s) for s in specs}
    league.custom_renames = dict(renames)
    for spec in specs:
        team = next((t for t in league.teams if t.school == spec["school"]), None)
        if team is not None:
            apply_details(league, team, spec, roster=bool(spec.get("roster")))


# ═══ Putting a file on a program ═════════════════════════════════════════════

def apply_details(league, team, spec, roster=True):
    """Everything but the name: coach, staff, AD, facilities, money, stadium, roster."""
    import carousel
    team.nickname, team.chant = spec["nickname"], spec["chant"]
    team.home_state = spec["home_state"]
    team.stadium = spec["stadium"]["name"]
    team.capacity = team.base_capacity = spec["stadium"]["capacity"]
    if spec["stadium"]["parts"] and getattr(team, "stad", None):
        team.stad.setdefault("parts", {}).update(spec["stadium"]["parts"])
    team.ratings.update(spec["ratings"])
    if spec["facilities"] and getattr(team, "fac", None) is not None:
        team.fac.update(spec["facilities"])
    if spec.get("budget"):
        team.budget = spec["budget"]
    if spec["ad"].get("name") and getattr(team, "ad", None) is not None:
        team.ad["name"] = spec["ad"]["name"]
    if spec["ad"].get("style") and getattr(team, "ad", None) is not None:
        team.ad["style"] = spec["ad"]["style"]
    c = team.coach
    cs = spec["coach"]
    if c is not None and not getattr(c, "is_user", False):
        if cs["name"] and cs["name"] != c.name:
            c.name = cs["name"]
            team.coach_log.append((league.year, c.name))
        c.age = cs["age"]
        if cs["overall"] is not None:
            c.overall = cs["overall"]
            c.ceiling = max(getattr(c, "ceiling", c.overall), c.overall + 1)
        c.offense_scheme, c.defense_scheme, c.aggression = cs["offense_scheme"], cs["defense_scheme"], cs["aggression"]
        if cs["personality"]:
            c.personality = cs["personality"]
        if cs["alma_mater"]:
            c.alma_mater = cs["alma_mater"]
        c.ratings.update(cs["ratings"])
        c.__dict__.setdefault("fit_with", {})[team.school] = c.__dict__.get("fit_with", {}).get(team.school, 0.0)
    for role, scheme_key in (("oc", "offense_scheme"), ("dc", "defense_scheme")):
        cc = spec["coordinators"].get(role)
        cur = getattr(team, role, None)
        if cc and cur is not None:
            cur.name, cur.overall = cc["name"], cc["overall"]
            if cc.get(scheme_key):
                setattr(cur, scheme_key, cc[scheme_key])
    if roster and spec.get("roster"):
        replace_roster(league, team, spec["roster"])
    team.fix_numbers()
    import depth
    team.__dict__.pop("depth_order", None)
    try:
        if depth.yours(league, team):
            depth.staff_sort_yours(league, team)
        else:
            depth.sort_team(league, team, preseason=True)
    except Exception:
        pass


def build_player(d, rng, used_numbers, used_names):
    from roster import _pick_number
    p = Player(first_name=d["first_name"], last_name=d["last_name"], position=d["position"], year=d["year"],
               number=d["number"] if d.get("number") is not None and d["number"] not in used_numbers
               else _pick_number(rng, d["position"], used_numbers),
               height=d["height"], weight=d["weight"], fundamentals=d["fundamentals"],
               proficiency={**{k: 0.2 for k in POSITIONS}, **d["proficiency"]}, redshirt=d["redshirt"],
               hs_stars=d["hs_stars"], potential=d["potential"], prof_ceiling=d["prof_ceiling"],
               seasons_developed=d["year"])
    used_numbers.add(p.number)
    used_names.add((p.first_name, p.last_name))
    p.home_state = d.get("home_state")
    p.traits = list(d.get("traits") or [])
    if not p.traits:
        from traits import assign_player_traits
        assign_player_traits(p, rng)
    if d.get("morale") is not None:
        p.morale = d["morale"]
    if d.get("nil") is not None:
        p.nil = d["nil"]
    return p


def _update_player(p, d):
    """An edit to a player who's already on the roster: his stats, history and career stay."""
    p.first_name, p.last_name = d["first_name"], d["last_name"]
    p.position, p.year, p.redshirt = d["position"], d["year"], d["redshirt"]
    p.height, p.weight = d["height"], d["weight"]
    p.home_state = d.get("home_state") or p.home_state
    p.hs_stars, p.potential, p.prof_ceiling = d["hs_stars"], d["potential"], d["prof_ceiling"]
    p.fundamentals.update(d["fundamentals"])
    for k, v in d["proficiency"].items():
        p.proficiency[k] = v
    if d.get("traits") is not None:
        p.traits = list(d["traits"])
    if d.get("number") is not None:
        p.number = d["number"]
    if d.get("morale") is not None:
        p.morale = d["morale"]
    if d.get("nil") is not None:
        p.nil = d["nil"]


def replace_roster(league, team, rows):
    """The file's roster, exactly; walk-ons fill any holes to a full roster. Players the
    file points back to (an edit in a save) are updated in place, keeping their careers."""
    import roster as ros
    rng = random.Random(f"custom:{team.school}:{league.year}")
    used_numbers, used_names = set(), set()
    live = {id(p): p for p in team.roster}
    keep = set()
    for d in rows:
        ref = d.get("_ref")
        if ref in live:
            _update_player(live[ref], d)
            keep.add(ref)
    for p in list(team.roster):
        if id(p) not in keep:
            team.roster.remove(p)
            p.team = None
        else:
            used_numbers.add(p.number)
            used_names.add((p.first_name, p.last_name))
    for d in rows:
        if d.get("_ref") in keep:
            continue
        p = build_player(d, rng, used_numbers, used_names)
        p.history.append((league.year, p.overall))
        p.events[league.year].append(f"On the {team.school} roster")
        team.add_player(p)
    ros.sign_class(team, rng, league.year)          # walk-ons to a full roster, if the file was short
    team.recruiting_targets = []


def apply_to_team(league, team, spec, roster=True):
    """Load a file over a program in a save (rename included)."""
    old = team.school
    if spec["school"] != old:
        if any(t.school == spec["school"] for t in league.teams if t is not team):
            raise SpecError(f"There's already a {spec['school']} in this world.")
        rename(league, team, spec["school"])
    team.conference = spec["conference"] if spec["conference"] else team.conference
    team.division = spec["division"]
    apply_details(league, team, spec, roster=roster)
    stored = copy.deepcopy(spec)
    stored["roster"] = None                         # the roster lives on the team now
    league.__dict__.setdefault("custom_specs", {})[team.school] = stored
    register(stored)


def rename(league, team, new):
    """A program changes its name. Everything that's keyed by it follows; the old box
    scores keep the old name, because that's who played."""
    old = team.school
    team.school = new
    renames = league.__dict__.setdefault("custom_renames", {})
    renames[old] = new
    specs = league.__dict__.setdefault("custom_specs", {})
    if old in specs:
        specs[new] = specs.pop(old)
    _remap(old, new)
    from teams_data import ABBREVIATIONS
    from recruiting_data import TEAM_STATES
    if old in TEAM_STATES:
        TEAM_STATES.setdefault(new, TEAM_STATES[old])
    ABBREVIATIONS.setdefault(new, ABBREVIATIONS.get(old, make_abbr(new)))
    for c in [x for x in [team.coach, getattr(team, "oc", None), getattr(team, "dc", None)] if x is not None]:
        fw = c.__dict__.get("fit_with")
        if fw and old in fw:
            fw[new] = fw.pop(old)
        k = getattr(c, "contract", None)
        if isinstance(k, dict) and k.get("school") == old:
            k["school"] = new
    import carousel
    for c in carousel.all_coaches(league) + list(getattr(league, "coach_pool", [])) + \
            list(getattr(league, "retired_coaches", [])):
        for h in getattr(c, "history", []) or []:
            if h.get("school") == old:
                h["school"] = new
    series = getattr(league, "series", None)
    if isinstance(series, dict):
        for k in list(series):
            parts = k.split("|")
            if old in parts:
                import rivalries
                a, b = [new if x == old else x for x in parts]
                series[rivalries._key(a, b)] = series.pop(k)
    b = league.__dict__.get("record_book")
    if b is not None:
        for store in (b.game, b.season, b.team_game, b.team_season):
            if old in store:
                store[new] = store.pop(old)
        if old in b.streaks:
            b.streaks[new] = b.streaks.pop(old)
        for f in b.files.values():
            for yr in f["years"].values():
                if yr["school"] == old:
                    yr["school"] = new
    h = league.__dict__.get("hall")
    if h is not None:
        if old in h.program:
            h.program[new] = h.program.pop(old)
        if old in h.pending:
            h.pending[new] = h.pending.pop(old)


def add_to_world_check(league, spec):
    """Problems with putting this file in a new world (None if it's fine)."""
    return None


_init_snapshot()
