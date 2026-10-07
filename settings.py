"""
settings.py — Player settings, saved to settings.json next to the game.

  Campus Countdown cast names    rename any of the regulars (blank = back to default)
  Campus Countdown show          on / off
  Campus Countdown speed         instant / fast / normal
  Auto copy output      on / off — every screen goes to the clipboard (and last_screen.txt)
                        each time the game waits for you, so a chatbot can play along
  Show what answers do  on / off — the upside/cost line under inbox replies and press answers
  Game view             tablet (auto / wide / compact) · field only · slim field · off — drawn before every snap
  Halftime adjustments  on / off — stop at the half of your games for your second-half plan
  Sideline              the tablet, series check-ins, the people moments, the situational calls
  Difficulty            Freshman / Varsity / All-American / Golden Helmet (Coach Career; kept on your coach)
  Default routine       the weekly routine the week hub opens with (see week.py)
  Guided first week     on / off — your staff explains each screen the first time (guide.py)
"""
import json
import os
import threading

from gameday_cast import CAST, ORDER
from ui import C, ask, clear, paint, pause, rule, title_bar, truncate

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
SPEEDS = {"instant": 0.0, "fast": 0.35, "normal": 1.1}
DEFAULTS = {"universe": "real_2026", "gameday": True, "gameday_speed": "fast", "cast_names": {}, "auto_copy": False, "week_hub": True,
            "reply_hints": True, "halftime": True, "field_view": "auto", "guided_week": True,
            "faces": True, "team_theme": True}

# What counts as a "big moment" (Play the big moments). Every trigger can be switched
# off, and the ones with a number can be tuned.
MOMENT_DEFAULTS = {
    "overtime": True,
    "crunch_time": True, "crunch_minutes": 6, "crunch_margin": 8,   # 4th quarter, one-score game
    "fourth_down": True,                                           # a real go-for-it decision
    "two_minute": True,                                            # end of the first half
    "red_zone": True, "red_zone_yards": 8,                         # your offense near their goal line
    "goal_line_stand": True,                                       # their offense at your 5, second half
    "fourth_down_stop": True,                                      # they go for it in a close second half
    "blowout_margin": 22,                                          # past this, the staff plays it out
}
MOMENT_LABELS = [
    ("overtime", "Overtime", None), ("crunch_time", "Crunch time (late, close 4th quarter)", "crunch_minutes"),
    ("fourth_down", "Fourth-down decisions on offense", None), ("two_minute", "Two-minute drill before half", None),
    ("red_zone", "Red zone / goal to go on offense", "red_zone_yards"),
    ("goal_line_stand", "Goal-line stands on defense", None), ("fourth_down_stop", "Their fourth downs, late", None),
]

_cache = None
_local = threading.local()          # online: a game replayed on the host reads its coach's settings


def load():
    global _cache
    over = getattr(_local, "override", None)
    if over is not None:
        return over
    if _cache is None:
        _cache = dict(DEFAULTS)
        try:
            with open(PATH) as f:
                _cache.update(json.load(f))
        except (OSError, ValueError):
            pass
    return _cache


class use:
    """with settings.use(d): this thread reads d as the settings (never saved)."""
    def __init__(self, d):
        self.d = dict(DEFAULTS, **(d or {}))

    def __enter__(self):
        _local.override = self.d

    def __exit__(self, *exc):
        _local.override = None
        return False


def save():
    if getattr(_local, "override", None) is not None:
        return                       # someone else's settings, borrowed for a replay
    try:
        with open(PATH, "w") as f:
            json.dump(load(), f, indent=2)
    except OSError:
        pass


def moments():
    m = dict(MOMENT_DEFAULTS)
    m.update(load().get("moments", {}))
    return m


def _chip(v, word=None):
    from ui import on_off
    if isinstance(v, str):
        return on_off(v != "off", v.upper(), v.upper())
    return on_off(v)


def moments_menu():
    from ui import back_key, footer, key, menu_item, section
    while True:
        m = moments()
        clear()
        print(title_bar("SETTINGS · BIG MOMENTS", sub="SETTINGS"))
        print(paint("\n   In Play the big moments, the staff calls the game until one of these happens — then it's yours.\n",
                    C.GRAY))
        for i, (k, label, num) in enumerate(MOMENT_LABELS, 1):
            extra = ""
            if num == "crunch_minutes":
                extra = f"last {m['crunch_minutes']} min, within {m['crunch_margin']} pts · [M] minutes · [P] points"
            elif num == "red_zone_yards":
                extra = f"inside the {m['red_zone_yards']} · [Y] change"
            print(menu_item(str(i), label, extra, value=_chip(m[k]), label_w=40, value_w=6))
        print()
        print(menu_item("L", "Blowout cutoff", f"the staff plays it out at {m['blowout_margin']}+ "
                                                "(never in crunch time or overtime)", value=paint(str(m["blowout_margin"]),
                                                                                                   C.BWHITE, C.BOLD),
                        label_w=40, value_w=6))
        footer(key("#", "turn on/off"), key("R", "reset to defaults"), back_key())
        c = ask("Select:").strip().lower()
        store = load().setdefault("moments", {})
        if c in ("b", ""):
            return
        if c.isdigit() and 1 <= int(c) <= len(MOMENT_LABELS):
            k = MOMENT_LABELS[int(c) - 1][0]
            store[k] = not m[k]
        elif c in ("m", "p", "y", "l"):
            k, lo, hi = {"m": ("crunch_minutes", 1, 15), "p": ("crunch_margin", 0, 21),
                         "y": ("red_zone_yards", 3, 25), "l": ("blowout_margin", 8, 50)}[c]
            v = ask(f"New value ({lo}-{hi}):").strip()
            if v.isdigit() and lo <= int(v) <= hi:
                store[k] = int(v)
        elif c == "r":
            load()["moments"] = {}
        save()


def sideline_menu():
    import sideline
    from ui import back_key, footer, key, menu_item
    rows = [("sideline_tablet", "The tablet", "momentum, what's working, their tendencies, your coordinator, hot and cold"),
            ("sideline_checkins", "Series check-ins", "every series · only when the staff has something · off"),
            ("sideline_people", "The people", "trainer's reports, the quarterback, a word with a player after a bad play"),
            ("sideline_calls", "Situational calls", "the try, kickoffs, flags, challenges, icing, overtime (off = the staff)")]
    while True:
        s = load()
        clear()
        print(title_bar("SETTINGS · SIDELINE", sub="SETTINGS"))
        print(paint("\n   What the head coach handles on game day (Coach every snap, and the big moments).\n", C.GRAY))
        for i, (k, label, blurb) in enumerate(rows, 1):
            v = s.get(k, sideline.DEFAULTS[k])
            print(menu_item(str(i), label, blurb, value=_chip(v), label_w=20, value_w=10))
        footer(key("#", "change"), back_key())
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c.isdigit() and 1 <= int(c) <= len(rows):
            k = rows[int(c) - 1][0]
            v = s.get(k, sideline.DEFAULTS[k])
            if isinstance(v, str):
                order = ["every", "notable", "off"]
                s[k] = order[(order.index(v) + 1) % 3] if v in order else "notable"
            else:
                s[k] = not v
            save()


def cast_name(key):
    return load()["cast_names"].get(key) or CAST[key]["name"]


def last_name(key):
    name = cast_name(key)
    return name.replace('"', "").split()[-1] if name else key


def settings_menu(league=None):
    """Every setting, grouped. Works from the main menu (no world loaded) and in a game."""
    from ui import back_key, footer, key, menu_item, section
    import difficulty
    import week
    while True:
        s = load()
        clear()
        print(title_bar("SETTINGS", sub="SAVED AUTOMATICALLY"))
        coach = getattr(league, "user_coach", None) if getattr(league, "mode", None) == "career" else None
        r = week.default_routine()
        W = dict(label_w=24, value_w=11)
        print()
        import universe
        print(section("WORLD", C.BYELLOW))
        here = getattr(league, "universe", None) if league is not None else None
        print(menu_item("U", "Universe", "teams, coaches, rivalries and names for new worlds"
                        + (f" (this save: {truncate(universe.title(here), 22)})" if here else ""),
                        value=paint(truncate(universe.title(s.get("universe", "default")).replace(" (built-in)", ""), 11),
                                    C.BWHITE, C.BOLD), **W))
        print()
        print(section("GAME DAY", C.BYELLOW))
        print(menu_item("1", "Campus Countdown show", "the Saturday-morning show before each week", value=_chip(s["gameday"]), **W))
        print(menu_item("2", "Campus Countdown speed", "how fast the show plays", value=paint(s["gameday_speed"].title(), C.BWHITE,
                                                                                     C.BOLD), **W))
        print(menu_item("3", "Campus Countdown cast", "rename the crew, or use the alternate one", value="", **W))
        print(menu_item("4", "Halftime adjustments", "stop at the half for your second-half plan",
                        value=_chip(s.get("halftime", True)), **W))
        print(menu_item("5", "Big moments", "what brings you in during Play the big moments", value="", **W))
        print(menu_item("6", "Sideline", "tablet, check-ins, people moments, situational calls", value="", **W))
        import fieldview
        print(menu_item("F", "Game view", "tablet (field, play-by-play, stats), field only, or off",
                        value=paint(fieldview.MODE_WORDS[fieldview.mode()], C.BWHITE, C.BOLD), **W))
        print()
        print(section("YOUR WEEK · COACH CAREER", C.BYELLOW))
        print(menu_item("7", "Week hub", "film, inbox, practice and presser before each game",
                        value=_chip(s.get("week_hub", True)), **W))
        print(menu_item("8", "Default routine", "what the hub opens with, and what sim weeks use",
                        value=paint(truncate(r["name"], 10) if r else "none", C.BWHITE, C.BOLD), **W))
        print(menu_item("9", "Show what answers do", "the upside/cost line under replies and answers",
                        value=_chip(s.get("reply_hints", True)), **W))
        print(menu_item("W", "Weekly wrap", "after each game: poll, hot seat, recruiting, injuries, storylines",
                        value=_chip(s.get("weekly_wrap", True)), **W))
        print(menu_item("G", "Guided first week", "your staff explains each screen the first time you open it",
                        value=_chip(s.get("guided_week", True)), **W))
        print(menu_item("D", "Difficulty", "Freshman · Varsity · All-American · Golden Helmet"
                        if coach is not None else "set when you create a coach",
                        value=paint(difficulty.name(coach), C.BWHITE, C.BOLD) if coach is not None
                        else paint("—", C.GRAY), **W))
        print()
        print(section("TOOLS", C.BYELLOW))
        print(menu_item("V", "Show faces", "portraits on player, coach and recruit screens",
                        value=_chip(s.get("faces", True)), **W))
        print(menu_item("T", "Team colors", "screens and menus wear the team's colors",
                        value=_chip(s.get("team_theme", True)), **W))
        print(menu_item("C", "Auto copy output", "every screen to the clipboard (for chatbots)",
                        value=_chip(s.get("auto_copy", False)), **W))
        print(menu_item("X", "Download team context", "write a coach-safe .txt packet for your current program",
                        value=paint("READY" if getattr(league, "user_team", None) is not None else "—", C.BWHITE, C.BOLD), **W))
        footer(key("#", "change a setting"), back_key())
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        if choice == "u":
            universe_menu(league)
        elif choice == "1":
            s["gameday"] = not s["gameday"]
            save()
        elif choice == "2":
            order = list(SPEEDS)
            s["gameday_speed"] = order[(order.index(s["gameday_speed"]) + 1) % len(order)]
            save()
        elif choice == "3":
            rename_cast()
        elif choice == "4":
            s["halftime"] = not s.get("halftime", True)
            save()
        elif choice == "5":
            moments_menu()
        elif choice == "6":
            sideline_menu()
        elif choice == "f":
            import fieldview
            order = list(fieldview.MODES)
            s["field_view"] = order[(order.index(fieldview.mode()) + 1) % len(order)]
            save()
        elif choice == "7":
            s["week_hub"] = not s.get("week_hub", True)
            save()
        elif choice == "w":
            s["weekly_wrap"] = not s.get("weekly_wrap", True)
            save()
        elif choice == "8":
            default_routine_menu()
        elif choice == "9":
            s["reply_hints"] = not s.get("reply_hints", True)
            save()
        elif choice == "g":
            s["guided_week"] = not s.get("guided_week", True)
            save()
            g = getattr(league, "__dict__", {}).get("guide") if league is not None else None
            if g is not None:
                if not s["guided_week"]:
                    g["done"] = True
                elif league.year == g.get("start") and league.week < 2:
                    g["done"] = False                   # still your first week: pick up where it left off
            if s["guided_week"] and (g is None or g.get("done")):
                print(paint("\n   Guide on. It walks you through the first week of your next career.", C.GRAY))
                pause()
        elif choice == "d":
            difficulty.menu(league)
        elif choice == "v":
            s["faces"] = not s.get("faces", True)
            save()
        elif choice == "t":
            s["team_theme"] = not s.get("team_theme", True)
            save()
            import theme
            if s["team_theme"]:
                theme.init()
            else:
                theme.clear()
        elif choice == "c":
            s["auto_copy"] = not s.get("auto_copy", False)
            save()
            import screen_copy
            if s["auto_copy"]:
                tool = screen_copy.clipboard_tool()
                where = (f"the clipboard (via {tool[0]})" if tool else
                         "last_screen.txt only — no clipboard tool found (install xclip, xsel or wl-copy)")
                print(paint(f"\n   Auto copy is ON. Every screen goes to {where},", C.BGREEN))
                print(paint(f"   and is also saved to {screen_copy.LAST_SCREEN}.", C.GRAY))
                print(paint("   Paste it into your chatbot, ask what to do, type the answer here.", C.GRAY))
                pause()
        elif choice == "x":
            team = getattr(league, "user_team", None) if league is not None else None
            if team is None:
                print(paint("\n   Load a Coach Career first. Team Context only exports what your current coach knows.", C.BYELLOW))
                pause()
                continue
            try:
                import team_context
                path, n = team_context.export(league, team)
                print(paint(f"\n   Team context downloaded: {path}", C.BGREEN))
                print(paint(f"   {n:,} lines · coach-safe view only · no hidden player ratings.", C.GRAY))
            except Exception as e:
                print(paint(f"\n   Couldn't write the team context file: {e}", C.BRED))
            pause()


def universe_menu(league=None):
    """Pick the universe new worlds are built in, or export one to edit."""
    import os
    import universe
    from ui import back_key, footer, key, menu_item
    while True:
        s = load()
        clear()
        print(title_bar("SETTINGS · UNIVERSE", sub="WHICH WORLD NEW GAMES USE"))
        print(paint("\n   A universe is the set of programs, coaches, rivalries, trophies, bowls and names a world is\n"
                    "   built from. New worlds use the one picked here; a save always keeps its own.\n", C.GRAY))
        opts = [(universe.DEFAULT, "Console College (built-in)", "original programs, coaches and names")]
        opts += [(n, t, d) for n, t, d in universe.list_files()]
        for i, (n, t, d) in enumerate(opts, 1):
            mark = paint("  ◀ new worlds", C.BGREEN) if n == s.get("universe", universe.DEFAULT) else ""
            print(menu_item(str(i), truncate(t, 30), truncate(d, 44), label_w=32) + mark)
        here = getattr(league, "universe", None) if league is not None else None
        if here:
            print(paint(f"\n   This save was built in: {universe.title(here)}", C.GRAY))
        print(paint(f"\n   Universe files live in {universe.DIR}", C.GRAY))
        print()
        print(menu_item("X", "Export", "write the universe in use now to a file you can edit", label_w=32))
        footer(key("#", "use for new worlds"), back_key())
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        if choice.isdigit() and 1 <= int(choice) <= len(opts):
            s["universe"] = opts[int(choice) - 1][0]
            save()
            print(paint(f"   New worlds will use: {opts[int(choice) - 1][1]}", C.BGREEN))
            pause()
        elif choice == "x":
            name = ask("File name (no extension, Enter = cancel):").strip()
            if not name:
                continue
            slug = "".join(ch for ch in name if ch.isalnum() or ch in "_-") or "my_universe"
            os.makedirs(universe.DIR, exist_ok=True)
            path = universe.export(universe.path_for(slug), name=name,
                                   description=f"exported from {universe.title()}")
            print(paint(f"   Wrote {path}", C.BGREEN))
            pause()


def default_routine_menu():
    """Pick the routine the week hub opens with (and sim weeks use)."""
    import week
    from ui import back_key, footer, key, menu_item
    s = load()
    clear()
    print(title_bar("SETTINGS · DEFAULT WEEKLY ROUTINE", sub="SETTINGS"))
    print(paint("\n   The week hub opens with it loaded (practice focus, game plan, openers); sim weeks and a hub\n"
                "   turned off use it too. Save your own from the week hub ([Y]).\n", C.GRAY))
    lst = week.routine_list()
    for i, (k, r) in enumerate(lst, 1):
        star = paint("★ default", C.BGREEN, C.BOLD) if k == s.get("routine_default") else ""
        print(menu_item(str(i), r["name"], r["blurb"], value=star, label_w=18, value_w=10))
    print(menu_item("0", "None", "your usual practice focus, and the staff's plan", label_w=18, value_w=10,
                    value="" if s.get("routine_default") else paint("★ default", C.BGREEN, C.BOLD)))
    footer(key("#", "make it the default"), back_key())
    c = ask("Default:").strip()
    if c == "0":
        s.pop("routine_default", None)
        save()
    elif c.isdigit() and 1 <= int(c) <= len(lst):
        s["routine_default"] = lst[int(c) - 1][0]
        save()


# A second made-up crew and show name, if you want a change from the universe's own.
FICTIONAL_CAST = {"host": "Dean Marchetti", "film": "Cole Harwood", "coach": "Walt Brennaman",
                  "boom": "Rowdy Pruett", "defender": "Marcus Oliphant"}
FICTIONAL_SHOW = "Saturday Kickoff"


def show_name():
    """What the Saturday morning show is called (the universe's name for it unless you rename it)."""
    import world
    return load().get("show_name") or world.SHOW_NAME


def rename_cast():
    while True:
        from ui import back_key, footer, menu_item
        from ui import key as _key
        clear()
        print(title_bar("SETTINGS · THE GAMEDAY CAST", sub="SETTINGS"))
        print(paint(f"\n   The show: {show_name()}\n", C.GRAY))
        for i, k in enumerate(ORDER, 1):
            c = CAST[k]
            custom = k in load()["cast_names"]
            print(menu_item(str(i), cast_name(k), c["role"] + (" · renamed" if custom else ""), label_w=24))
        print()
        print(menu_item("F", "Alternate crew", f"a different made-up crew and show ({FICTIONAL_SHOW})",
                        label_w=24))
        print(menu_item("R", "Restore defaults", "the universe's own crew and show name", label_w=24))
        footer(_key("#", "rename (blank = default)"), back_key())
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        if choice == "f":
            load()["cast_names"] = dict(FICTIONAL_CAST)
            load()["show_name"] = FICTIONAL_SHOW
            save()
            continue
        if choice == "r":
            load()["cast_names"] = {}
            load().pop("show_name", None)
            save()
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(ORDER):
            key = ORDER[int(choice) - 1]
            new = ask(f"New name for {cast_name(key)}:")
            names = load()["cast_names"]
            if new:
                names[key] = new
            else:
                names.pop(key, None)
            save()
            print(paint(f"   Saved: {cast_name(key)}", C.BGREEN))
            pause()
