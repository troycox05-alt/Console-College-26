"""
team_builder.py — Build a program, or rebuild one (team page -> [J]; New world -> custom teams).

Every section of a team file (see custom_teams.py) has a screen:

    1 Identity      school, nickname, abbreviation, short name, chant, conference, home state, town, altitude
    2 Stadium       name, capacity, indoor, every part of the building
    3 Ratings       the eight program ratings (offense, defense, coach, AD, facilities, academics, tradition, campus)
    4 Money         facility levels and the athletic budget
    5 Head coach    name, age, skill, schemes, aggression, personality, alma mater, the six development ratings
    6 Coordinators  OC and DC: name, skill, scheme
    7 AD            name and style
    8 Identity+     primary rival, the trophy, lines for the broadcast booth, the tailgate dish
    9 Roster        every player: add, edit, remove, or generate a whole roster from the ratings

In a save, [A] applies it to the program in place; anywhere, [S] saves it as a team file
in custom_teams/ to share or use in a new world.
"""
import copy
import random

import custom_teams as ct
from models import POSITIONS, Team, Coach, FUNDAMENTALS
from ui import (C, ask, back_key, clear, confirm, footer, key, menu_item, pad, paint, pause, section, title_bar,
                truncate)

W = dict(label_w=22, value_w=0)


def _conferences():
    from league import CONF_INFO
    return sorted(set(CONF_INFO) | {"Independent"})


def _schools(league=None):
    if league is not None:
        return [t.school for t in league.teams]
    from teams_data import TEAMS
    return [r[0] for r in TEAMS]


# ── little prompts ───────────────────────────────────────────────────────────
def _text(label, cur, maxlen=40, allow_blank=False):
    v = ask(f"{label} [{cur or ''}]:").strip()
    if not v:
        return None if allow_blank else cur
    return v[:maxlen]


def _num(label, cur, lo, hi):
    v = ask(f"{label} ({lo}-{hi}) [{cur}]:").strip().replace(",", "").replace("$", "")
    if not v:
        return cur
    try:
        n = float(v) if isinstance(cur, float) else int(float(v))
    except ValueError:
        return cur
    return max(lo, min(hi, n))


def _pick(label, options, cur=None, cols=3):
    print()
    for i, o in enumerate(options, 1):
        mark = paint("●", C.BGREEN) if o == cur else " "
        end = "\n" if i % cols == 0 else ""
        print(f"  {mark}{i:>3}. {pad(truncate(str(o), 24), 26)}", end=end)
    print()
    v = ask(f"{label} (number, Enter keeps {cur}):").strip()
    if v.isdigit() and 1 <= int(v) <= len(options):
        return options[int(v) - 1]
    return cur


def _money(x):
    return f"${x / 1e6:.1f}M" if x else "auto"


# ── the builder ──────────────────────────────────────────────────────────────
def edit_spec(spec, league=None, live_team=None):
    """Edit a team file in place. Returns "save", "apply" or None (cancelled)."""
    orig = copy.deepcopy(spec)
    while True:
        clear()
        head = f"{spec['school']} {spec['nickname']}"
        print(title_bar(f"TEAM BUILDER · {head.upper()}", sub="EDITING IN A SAVE" if live_team else "TEAM FILE"))
        r = spec["ratings"]
        c = spec["coach"]
        print()
        print(menu_item("1", "Identity", f"{spec['abbr'] or ct.make_abbr(spec['school'])} · {spec['conference']} · "
                                         f"{spec['home_state']} · \"{truncate(spec['chant'], 24)}\""))
        print(menu_item("2", "Stadium", f"{spec['stadium']['name']} · {spec['stadium']['capacity']:,}"
                                        + (" · indoor" if spec["stadium"]["indoor"] else "")))
        print(menu_item("3", "Program ratings", " ".join(f"{k[:3].upper()} {r[k]}" for k in Team.RATING_KEYS)))
        fac = spec["facilities"]
        print(menu_item("4", "Facilities & money", " · ".join(f"{k} {v}" for k, v in fac.items()) or "facility levels auto"
                        + f" · budget {_money(spec.get('budget'))}"))
        print(menu_item("5", "Head coach", f"{c['name']} · age {c['age']} · {c['offense_scheme']} / {c['defense_scheme']}"))
        co = spec["coordinators"]
        print(menu_item("6", "Coordinators", " · ".join(f"{k.upper()} {v['name']}" for k, v in co.items()) or "auto"))
        print(menu_item("7", "Athletic director", f"{spec['ad'].get('name') or 'auto'} · {spec['ad'].get('style') or 'auto'}"))
        print(menu_item("8", "Rival, trophy, lore", f"rival {spec.get('rival') or '—'} · {len(spec.get('lore') or [])} "
                                                  f"booth lines · tailgate {'yes' if spec.get('tailgate') else '—'}"))
        n = len(spec["roster"]) if spec.get("roster") else 0
        print(menu_item("9", "Roster", f"{n} players" if n else "none: the program recruits its own"))
        if not live_team:
            print(menu_item("R", "Replaces", spec.get("replaces") or "nobody — joins its conference as a new program"))
        print()
        items = [key("S", "save as a team file", C.BGREEN)]
        if live_team is not None:
            items.insert(0, key("A", f"apply to {live_team.school}", C.BGREEN))
        items += [key("X", "discard changes", C.BRED), back_key("Done")]
        footer(*items)
        ch = ask("Select:").strip().lower()
        if ch in ("b", ""):
            return "done"
        if ch == "x":
            spec.clear()
            spec.update(orig)
            return None
        if ch == "s":
            path = ct.save_file(spec)
            print(paint(f"\n   Saved: {path}", C.BGREEN))
            pause()
        elif ch == "a" and live_team is not None:
            return "apply"
        elif ch == "1":
            _identity(spec, league)
        elif ch == "2":
            _stadium(spec)
        elif ch == "3":
            _ratings(spec)
        elif ch == "4":
            _money_screen(spec)
        elif ch == "5":
            _coach(spec)
        elif ch == "6":
            _coordinators(spec)
        elif ch == "7":
            _ad(spec)
        elif ch == "8":
            _flavor(spec, league)
        elif ch == "9":
            roster_editor(spec, league)
        elif ch == "r" and not live_team:
            opts = ["(nobody — a new program)"] + _schools(league)
            v = _pick("Replace which program", opts, spec.get("replaces") or opts[0])
            spec["replaces"] = None if v == opts[0] else v


def _identity(spec, league):
    while True:
        clear()
        print(title_bar("TEAM BUILDER · IDENTITY"))
        rows = [("1", "School", spec["school"]), ("2", "Nickname", spec["nickname"]),
                ("3", "Abbreviation", spec["abbr"]), ("4", "Short name", spec.get("short_name") or "—"),
                ("5", "Chant", spec["chant"]), ("6", "Conference", spec["conference"]),
                ("7", "Division", spec.get("division") or "—"), ("8", "Home state", spec["home_state"]),
                ("9", "Town", spec.get("town") or "—"), ("0", "Altitude (ft)", spec.get("altitude") or "state default")]
        print()
        for k, label, v in rows:
            print(menu_item(k, label, str(v)))
        footer(key("#", "change"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "1":
            old = spec["school"]
            spec["school"] = _text("School", spec["school"])
            if spec["school"] != old:                     # placeholders follow the name; your own choices stay
                if spec["abbr"] in ("", ct.make_abbr(old)):
                    spec["abbr"] = ct.make_abbr(spec["school"])
                if spec["stadium"]["name"] == f"{old} Stadium":
                    spec["stadium"]["name"] = f"{spec['school']} Stadium"
        elif c == "2":
            spec["nickname"] = _text("Nickname", spec["nickname"])
        elif c == "3":
            spec["abbr"] = (_text("Abbreviation (2-5 letters)", spec["abbr"], 5) or "").upper()
        elif c == "4":
            spec["short_name"] = _text("Short name (13 letters or less)", spec.get("short_name"), 13) or ""
        elif c == "5":
            spec["chant"] = _text("Chant", spec["chant"], 60)
        elif c == "6":
            spec["conference"] = _pick("Conference", _conferences(), spec["conference"])
        elif c == "7":
            spec["division"] = _text("Division (blank for none)", spec.get("division"), 20, allow_blank=True)
        elif c == "8":
            v = (_text("Home state (two letters)", spec["home_state"], 2) or "").upper()
            if v in ct.STATES:
                spec["home_state"] = v
        elif c == "9":
            spec["town"] = _text("Town (City, State)", spec.get("town"), 50)
        elif c == "0":
            spec["altitude"] = _num("Altitude in feet", spec.get("altitude") or 0, 0, 12000)


def _stadium(spec):
    import stadium as stad
    s = spec["stadium"]
    while True:
        clear()
        print(title_bar("TEAM BUILDER · STADIUM"))
        print()
        print(menu_item("N", "Name", s["name"]))
        print(menu_item("C", "Capacity", f"{s['capacity']:,}"))
        print(menu_item("I", "Indoor", "yes" if s["indoor"] else "no"))
        print(section("THE BUILDING (level for each part; blank = the game decides)", C.BCYAN))
        for i, part in enumerate(stad.ORDER, 1):
            info = stad.PARTS[part]
            lvl = s["parts"].get(part)
            tier = info["tiers"][lvl] if lvl is not None and lvl < len(info["tiers"]) else "auto"
            print(menu_item(str(i), info["name"], f"{lvl if lvl is not None else '-'} · {tier}"))
        footer(key("#", "set a part"), key("N/C/I", "name, capacity, indoor"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "n":
            s["name"] = _text("Stadium name", s["name"], 60)
        elif c == "c":
            s["capacity"] = _num("Capacity", s["capacity"], 5000, 115000)
        elif c == "i":
            s["indoor"] = not s["indoor"]
        elif c.isdigit() and 1 <= int(c) <= len(stad.ORDER):
            part = stad.ORDER[int(c) - 1]
            info = stad.PARTS[part]
            top = len(info["tiers"]) - 1
            for lv, name in enumerate(info["tiers"]):
                print(f"     {lv}. {name}")
            v = ask(f"Level ({info.get('min', 0)}-{top}, blank = auto):").strip()
            if v == "":
                s["parts"].pop(part, None)
            elif v.isdigit():
                s["parts"][part] = max(info.get("min", 0), min(top, int(v)))


def _ratings(spec):
    r = spec["ratings"]
    while True:
        clear()
        print(title_bar("TEAM BUILDER · PROGRAM RATINGS", sub="1-99"))
        print(paint("\n   Offense and defense set the roster's talent (a new world's rosters land on them);"
                    "\n   the rest drive recruiting pull, prestige, money and the coaching carousel.\n", C.GRAY))
        for i, k in enumerate(Team.RATING_KEYS, 1):
            from ui import rating
            print(menu_item(str(i), Team.RATING_LABELS[k], rating(r[k])))
        footer(key("#", "change"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c.isdigit() and 1 <= int(c) <= len(Team.RATING_KEYS):
            k = Team.RATING_KEYS[int(c) - 1]
            r[k] = _num(Team.RATING_LABELS[k], r[k], 1, 99)


def _money_screen(spec):
    f = spec["facilities"]
    while True:
        clear()
        print(title_bar("TEAM BUILDER · FACILITIES & MONEY"))
        print()
        for i, k in enumerate(("recruiting", "training", "stadium"), 1):
            print(menu_item(str(i), f"{k.title()} facilities", f"{f.get(k, 'auto')} (1-10)"))
        print(menu_item("4", "Athletic budget", _money(spec.get("budget"))))
        footer(key("#", "change"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c in ("1", "2", "3"):
            k = ("recruiting", "training", "stadium")[int(c) - 1]
            f[k] = _num(f"{k.title()} facilities", f.get(k, 5), 1, 10)
        elif c == "4":
            v = _num("Budget in dollars", spec.get("budget") or 40_000_000, 5_000_000, 400_000_000)
            spec["budget"] = v


def _coach(spec):
    import carousel
    c = spec["coach"]
    while True:
        clear()
        print(title_bar("TEAM BUILDER · HEAD COACH"))
        print()
        rows = [("1", "Name", c["name"]), ("2", "Age", c["age"]), ("3", "Coach skill", c.get("overall") or "from ratings"),
                ("4", "Offense", c["offense_scheme"]), ("5", "Defense", c["defense_scheme"]),
                ("6", "Aggression", f"{c['aggression']} (4th downs, blitzing)"),
                ("7", "Personality", c.get("personality") or "the game decides"),
                ("8", "Alma mater", c.get("alma_mater") or "the game decides")]
        for k, label, v in rows:
            print(menu_item(k, label, str(v)))
        print(section("DEVELOPMENT AND RECRUITING (blank = from coach skill)", C.BCYAN))
        for i, k in enumerate(Coach.RATING_KEYS):
            print(menu_item("abcdef"[i].upper(), Coach.RATING_LABELS[k], str(c["ratings"].get(k, "auto"))))
        footer(key("#", "change"), back_key())
        ch = ask("Select:").strip().lower()
        if ch in ("b", ""):
            return
        if ch == "1":
            c["name"] = _text("Name", c["name"])
        elif ch == "2":
            c["age"] = _num("Age", c["age"], 28, 80)
        elif ch == "3":
            c["overall"] = _num("Coach skill", c.get("overall") or 60, 20, 99)
        elif ch == "4":
            c["offense_scheme"] = _pick("Offense", list(ct.OFF_SCHEMES), c["offense_scheme"], cols=2)
        elif ch == "5":
            c["defense_scheme"] = _pick("Defense", list(ct.DEF_SCHEMES), c["defense_scheme"], cols=2)
        elif ch == "6":
            c["aggression"] = _num("Aggression", c["aggression"], 1, 100)
        elif ch == "7":
            c["personality"] = _pick("Personality", list(carousel.PERSONALITIES), c.get("personality"))
        elif ch == "8":
            c["alma_mater"] = _text("Alma mater", c.get("alma_mater"), 40)
        elif ch in "abcdef" and len(ch) == 1:
            k = Coach.RATING_KEYS["abcdef".index(ch)]
            c["ratings"][k] = _num(Coach.RATING_LABELS[k], c["ratings"].get(k, 60), 20, 99)


def _coordinators(spec):
    co = spec["coordinators"]
    while True:
        clear()
        print(title_bar("TEAM BUILDER · COORDINATORS", sub="BLANK NAME = THE GAME HIRES ONE"))
        print()
        for k, role, sk in (("1", "oc", "offense_scheme"), ("2", "dc", "defense_scheme")):
            cur = co.get(role)
            desc = f"{cur['name']} · skill {cur['overall']} · {cur.get(sk) or 'head coach scheme'}" if cur else "auto"
            print(menu_item(k, "Offensive coordinator" if role == "oc" else "Defensive coordinator", desc))
        footer(key("#", "change"), back_key())
        ch = ask("Select:").strip().lower()
        if ch in ("b", ""):
            return
        if ch in ("1", "2"):
            role, sk, schemes = (("oc", "offense_scheme", ct.OFF_SCHEMES), ("dc", "defense_scheme", ct.DEF_SCHEMES))[int(ch) - 1]
            cur = co.get(role) or {"name": "", "overall": 60, sk: None}
            name = _text("Name (blank = auto)", cur["name"], 40, allow_blank=True)
            if not name:
                co.pop(role, None)
                continue
            cur["name"] = name
            cur["overall"] = _num("Skill", cur["overall"], 20, 99)
            cur[sk] = _pick("Scheme", list(schemes), cur.get(sk), cols=2)
            co[role] = cur


def _ad(spec):
    import carousel
    a = spec["ad"]
    clear()
    print(title_bar("TEAM BUILDER · ATHLETIC DIRECTOR"))
    a["name"] = _text("AD name (blank = the game picks)", a.get("name"), 40, allow_blank=True) or ""
    print()
    for k in carousel.AD_STYLES:
        style, blurb, _ = carousel.AD_STYLES[k]
        print(f"   {paint(style, C.BWHITE):<30} {paint(truncate(blurb, 70), C.GRAY)}")
    a["style"] = _pick("Style", list(carousel.AD_STYLES), a.get("style") or None) or ""


def _flavor(spec, league):
    while True:
        clear()
        print(title_bar("TEAM BUILDER · RIVAL, TROPHY, LORE"))
        print()
        print(menu_item("1", "Primary rival", spec.get("rival") or "—"))
        print(menu_item("2", "Rivalry trophy", spec.get("trophy") or "—"))
        tg = spec.get("tailgate")
        print(menu_item("3", "Tailgate dish", f"{tg[0]}: {truncate(tg[1], 50)}" if tg else "—"))
        print(section("LINES FOR THE BROADCAST BOOTH", C.BCYAN))
        for i, ln in enumerate(spec.get("lore") or [], 1):
            print(paint(f"    {i:>2}. {truncate(ln, 96)}", C.GRAY))
        footer(key("1-3", "change"), key("A", "add a booth line"), key("D", "delete a line"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "1":
            opts = ["(none)"] + sorted(s for s in _schools(league) if s != spec["school"])
            v = _pick("Rival", opts, spec.get("rival") or "(none)", cols=4)
            spec["rival"] = None if v == "(none)" else v
        elif c == "2":
            spec["trophy"] = _text("Trophy (e.g. the Valley Oar)", spec.get("trophy"), 50, allow_blank=True)
        elif c == "3":
            dish = _text("Dish", tg[0] if tg else "", 40, allow_blank=True)
            spec["tailgate"] = [dish, _text("How they make it", tg[1] if tg else "", 200)] if dish else None
        elif c == "a":
            ln = ask("Line:").strip()
            if ln:
                spec.setdefault("lore", []).append(ln[:220])
        elif c == "d":
            v = ask("Delete line #:").strip()
            if v.isdigit() and 1 <= int(v) <= len(spec.get("lore") or []):
                spec["lore"].pop(int(v) - 1)


# ── roster ───────────────────────────────────────────────────────────────────
def _ovr(d):
    from models import POSITION_WEIGHTS
    raw = sum(d["fundamentals"][f] * w for f, w in POSITION_WEIGHTS[d["position"]].items())
    return max(1, min(99, round(raw * d["proficiency"].get(d["position"], 0.85))))


CLS = ["FR", "SO", "JR", "SR"]


def generate_roster_rows(spec, year=2026):
    """A whole roster from the file's ratings, the way a new world builds one."""
    from roster import generate_roster
    from league import make_coach
    row = {k: spec["ratings"][k] for k in Team.RATING_KEYS}
    t = Team(spec["school"], spec["nickname"], spec["stadium"]["name"], spec["stadium"]["capacity"],
             spec["conference"], spec.get("division"), spec["chant"], row)
    t.set_coach(make_coach(spec["coach"]["name"], t))
    generate_roster(t, random.Random(f"build:{spec['school']}"), year)
    rows, _ = ct.normalize_roster([ct.player_dict(p) for p in t.roster])
    return rows


def roster_editor(spec, league=None):
    pos_filter = None
    while True:
        rows = spec.get("roster") or []
        clear()
        print(title_bar(f"TEAM BUILDER · ROSTER · {spec['school'].upper()}", sub=f"{len(rows)} PLAYERS"))
        if not rows:
            print(paint("\n   No roster in this file: the program will recruit and develop its own (in a new world),"
                        "\n   or keep the one it has (in a save). [G] builds one from the ratings to edit.\n", C.GRAY))
        shown = [(i, d) for i, d in enumerate(rows) if pos_filter in (None, d["position"])]
        for n, (i, d) in enumerate(shown, 1):
            yr = CLS[d["year"]] + ("*" if d["redshirt"] else " ")
            print(f"  {n:>3}. {pad(paint(d['position'], C.BCYAN), 4)}#{str(d.get('number') or '-'):<3} "
                  f"{pad(truncate(d['first_name'] + ' ' + d['last_name'], 24), 25)}{yr}  "
                  f"{paint(str(_ovr(d)), C.BWHITE, C.BOLD):>3}  {'★' * d['hs_stars']}")
        footer(key("#", "edit"), key("N", "new player"), key("D", "delete"), key("P", "filter position"),
               key("G", "generate a whole roster"), key("C", "clear roster"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c.isdigit() and 1 <= int(c) <= len(shown):
            player_editor(shown[int(c) - 1][1])
        elif c == "n":
            pos = _pick("Position", list(POSITIONS), pos_filter or "QB", cols=6)
            d = {"first_name": "New", "last_name": "Player", "position": pos, "year": 0, "redshirt": False,
                 "height": 74, "weight": 220, "home_state": spec["home_state"], "hs_stars": 3, "potential": 55,
                 "prof_ceiling": 1.0, "fundamentals": {f: 60 for f in FUNDAMENTALS}, "proficiency": {pos: 0.85},
                 "traits": [], "number": None}
            spec["roster"] = rows + [d]
            player_editor(d)
        elif c == "d":
            v = ask("Delete #:").strip()
            if v.isdigit() and 1 <= int(v) <= len(shown):
                rows.remove(shown[int(v) - 1][1])
        elif c == "p":
            v = _pick("Show position", ["(all)"] + list(POSITIONS), pos_filter or "(all)", cols=6)
            pos_filter = None if v == "(all)" else v
        elif c == "g":
            if not rows or confirm("Replace the roster with a generated one?"):
                spec["roster"] = generate_roster_rows(spec, getattr(league, "year", 2026))
        elif c == "c" and confirm("Clear the whole roster (the program recruits its own)?"):
            spec["roster"] = None


def player_editor(d):
    from traits import PLAYER_TRAITS
    while True:
        clear()
        print(title_bar(f"PLAYER · {d['first_name']} {d['last_name']}".upper(), sub=f"{d['position']} · OVR {_ovr(d)}"))
        print()
        rows = [("1", "First name", d["first_name"]), ("2", "Last name", d["last_name"]),
                ("3", "Position", d["position"]), ("4", "Number", d.get("number") or "any"),
                ("5", "Class", CLS[d["year"]] + (" (redshirt)" if d["redshirt"] else "")),
                ("6", "Height / weight", f"{d['height'] // 12}'{d['height'] % 12}\" · {d['weight']} lbs"),
                ("7", "Home state", d.get("home_state") or "—"), ("8", "HS stars", d["hs_stars"]),
                ("9", "Potential", f"{d['potential']} (how fast he develops)"),
                ("0", "Proficiency", f"{d['proficiency'].get(d['position'], 0.85):.2f} at {d['position']} · "
                                     f"ceiling {d['prof_ceiling']:.2f}")]
        for k, label, v in rows:
            print(menu_item(k, label, str(v)))
        print(section("FUNDAMENTALS", C.BCYAN))
        for i, f in enumerate(FUNDAMENTALS):
            print(menu_item("abcdef"[i].upper(), f.title(), str(d["fundamentals"][f])))
        print(menu_item("T", "Traits", ", ".join(PLAYER_TRAITS[t][0] for t in d["traits"] if t in PLAYER_TRAITS) or "—"))
        footer(key("#", "change"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "1":
            d["first_name"] = _text("First name", d["first_name"], 20)
        elif c == "2":
            d["last_name"] = _text("Last name", d["last_name"], 24)
        elif c == "3":
            new = _pick("Position", list(POSITIONS), d["position"], cols=6)
            if new != d["position"]:
                d["proficiency"].setdefault(new, max(0.3, d["proficiency"].get(new, 0.5)))
                d["position"] = new
        elif c == "4":
            d["number"] = _num("Number", d.get("number") or 0, 0, 99)
        elif c == "5":
            d["year"] = CLS.index(_pick("Class", CLS, CLS[d["year"]], cols=4))
            d["redshirt"] = confirm("Redshirted?", d["redshirt"])
        elif c == "6":
            d["height"] = _num("Height in inches", d["height"], 64, 84)
            d["weight"] = _num("Weight", d["weight"], 150, 380)
        elif c == "7":
            v = (_text("Home state", d.get("home_state"), 2) or "").upper()
            d["home_state"] = v if v in ct.STATES else d.get("home_state")
        elif c == "8":
            d["hs_stars"] = _num("Stars", d["hs_stars"], 0, 5)
        elif c == "9":
            d["potential"] = _num("Potential", d["potential"], 1, 99)
        elif c == "0":
            d["proficiency"][d["position"]] = _num(f"Proficiency at {d['position']}",
                                                   float(d["proficiency"].get(d["position"], 0.85)), 0.1, 1.2)
            d["prof_ceiling"] = _num("Ceiling", float(d["prof_ceiling"]), 0.6, 1.2)
        elif c in "abcdef" and len(c) == 1:
            f = FUNDAMENTALS["abcdef".index(c)]
            d["fundamentals"][f] = _num(f.title(), d["fundamentals"][f], 15, 99)
        elif c == "t":
            keys = list(PLAYER_TRAITS)
            print()
            for i, k in enumerate(keys, 1):
                mark = paint("●", C.BGREEN) if k in d["traits"] else " "
                print(f"  {mark}{i:>3}. {pad(PLAYER_TRAITS[k][0], 24)}", end="\n" if i % 4 == 0 else "")
            v = ask("\nToggle trait # (up to 3):").strip()
            if v.isdigit() and 1 <= int(v) <= len(keys):
                k = keys[int(v) - 1]
                if k in d["traits"]:
                    d["traits"].remove(k)
                elif len(d["traits"]) < 3:
                    d["traits"].append(k)


# ── entry points ─────────────────────────────────────────────────────────────
def team_menu(league, team):
    """Team page -> [J]."""
    while True:
        clear()
        print(title_bar(f"TEAM BUILDER · {team.school.upper()}"))
        print()
        print(menu_item("E", "Edit this program", "every field, including the roster; applied in place"))
        print(menu_item("X", "Export to a team file", "custom_teams/ — share it, edit it, use it in a new world"))
        print(menu_item("L", "Load a team file over this program", "the schedule, recruits and history stay"))
        print(menu_item("N", "Build a new team file", "from scratch, for a new world"))
        files = ct.list_files()
        print(paint(f"\n   {len(files)} team file{'s' if len(files) != 1 else ''} in {ct.DIR}", C.GRAY))
        footer(back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "e":
            spec = ct.from_team(league, team)
            if edit_spec(spec, league, live_team=team) == "apply":
                _apply(league, team, spec)
        elif c == "x":
            path = ct.save_file(ct.from_team(league, team))
            print(paint(f"\n   Exported {team.school}, roster and all: {path}", C.BGREEN))
            pause()
        elif c == "l":
            spec = pick_file(league)
            if spec is not None:
                keep = not spec.get("roster") or not confirm(
                    f"The file has a roster ({len(spec['roster'])} players). Replace {team.school}'s roster with it?")
                _apply(league, team, spec, roster=not keep)
        elif c == "n":
            spec, _ = ct.normalize(ct.default_spec("New School"))
            edit_spec(spec, league)


def _apply(league, team, raw, roster=True):
    try:
        spec, warn = ct.normalize(raw, league_schools={t.school for t in league.teams} | {raw.get("school")},
                                  conferences=set(_conferences()))
    except ct.SpecError as e:
        print(paint(f"\n   {e}", C.BRED))
        pause()
        return
    for w in warn:
        print(paint(f"   • {w}", C.BYELLOW))
    if spec["conference"] != team.conference and league.week and not league.season_complete:
        print(paint(f"   • {spec['school']} moves to the {spec['conference']}; this season's schedule stays as it is.",
                    C.BYELLOW))
    mine = team is getattr(league, "user_team", None)
    if mine and spec["coach"]["name"] != getattr(team.coach, "name", ""):
        print(paint("   • That's your program: you stay the head coach.", C.BYELLOW))
    if not confirm(f"Apply to {team.school}?", True):
        return
    try:
        ct.apply_to_team(league, team, spec, roster=roster)
    except ct.SpecError as e:
        print(paint(f"\n   {e}", C.BRED))
        pause()
        return
    print(paint(f"\n   Done. {team.school} {team.nickname} is updated.", C.BGREEN))
    pause()


def pick_file(league=None):
    files = ct.list_files()
    clear()
    print(title_bar("TEAM FILES", sub=ct.DIR))
    if not files:
        print(paint(f"\n   No team files yet. Put .json files in {ct.DIR},\n   or export a program from its team page "
                    "([J] -> [X]) to get one to start from.\n", C.GRAY))
        pause()
        return None
    print()
    for i, (path, name, d) in enumerate(files, 1):
        extra = ""
        if d:
            extra = f"{d.get('conference', '?')} · roster: {len(d['roster']) if d.get('roster') else 'no'}"
            if d.get("replaces"):
                extra += f" · replaces {d['replaces']}"
        print(menu_item(str(i), truncate(str(name), 24), extra))
    footer(key("#", "pick"), back_key())
    c = ask("Select:").strip()
    if c.isdigit() and 1 <= int(c) <= len(files) and files[int(c) - 1][2] is not None:
        return copy.deepcopy(files[int(c) - 1][2])
    return None


def new_world_setup():
    """Main menu -> New: add or swap in custom programs before the world is built.
    Returns a list of normalized specs (maybe empty)."""
    chosen = []
    while True:
        clear()
        print(title_bar("NEW WORLD · CUSTOM PROGRAMS", sub="OPTIONAL"))
        print(paint("\n   Add your own programs, or put one in place of a real one. They're built with the world, so they\n"
                    "   arrive with four years of recruiting history (or the exact roster in the file).\n", C.GRAY))
        if chosen:
            print(section("IN THIS WORLD", C.BGREEN))
            for i, s in enumerate(chosen, 1):
                how = f"replaces {s['replaces']}" if s.get("replaces") else f"joins the {s['conference']}"
                print(menu_item(str(i), s["school"], f"{how} · roster: {len(s['roster']) if s.get('roster') else 'recruited'}"))
        else:
            print(paint("   None yet: the real 138.", C.GRAY))
        footer(key("F", "add a team file"), key("N", "build a new one"), key("#", "edit / remove one"),
               key("G", "go: build the world", C.BGREEN), back_key("Cancel"))
        c = ask("Select:").strip().lower()
        if c in ("b",):
            return None
        if c in ("g", ""):
            return chosen
        if c == "f":
            raw = pick_file()
            if raw is not None:
                _add(chosen, raw)
        elif c == "n":
            spec, _ = ct.normalize(ct.default_spec("New School"))
            edit_spec(spec)
            _add(chosen, spec)
        elif c.isdigit() and 1 <= int(c) <= len(chosen):
            s = chosen[int(c) - 1]
            v = ask("[E] edit  [R] remove:").strip().lower()
            if v == "r":
                chosen.remove(s)
            elif v == "e":
                edit_spec(s)
                chosen[int(c) - 1] = _check(s) or s


def _check(raw):
    try:
        spec, warn = ct.normalize(raw, league_schools=set(_schools()) | {raw.get("school")},
                                  conferences=set(_conferences()))
    except ct.SpecError as e:
        print(paint(f"\n   {e}", C.BRED))
        pause()
        return None
    if warn:
        for w in warn:
            print(paint(f"   • {w}", C.BYELLOW))
        pause()
    return spec


def _add(chosen, raw):
    spec = _check(raw)
    if spec is None:
        return
    if any(s["school"] == spec["school"] for s in chosen):
        print(paint(f"\n   {spec['school']} is already in.", C.BYELLOW))
        pause()
        return
    if spec["school"] in _schools() and not spec.get("replaces"):
        spec["replaces"] = spec["school"]           # same name as a real program: it's a rebuild of that one
    chosen.append(spec)
