"""
title.py — The front door: the title screen and main menu, building a new world,
and the menu you get when you leave a game.

  MAIN MENU     [1] Continue (your latest save, with who and where)
                [2] New Game       [3] Load Game      [4] Settings
                [5] Manual         [6] About          [Q] Quit
  NEW WORLD     a progress screen while four years of history run
  DASHBOARD Q   autosaves and returns to this title screen; [Q] here quits the program
"""
import time

from ui import BRAND, C, MUTED, WIDTH, ask, center, clear, logo_lines, pad, paint, pause, title_bar, truncate

VERSION = "v51.22"
TAGLINE = "R E C R U I T   ·   C O A C H   ·   B U I L D   A   D Y N A S T Y"


def _ago(ts):
    s = max(0, time.time() - ts)
    if s < 90:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)} min ago"
    if s < 86400:
        return f"{int(s // 3600)} hr ago"
    if s < 86400 * 2:
        return "yesterday"
    return time.strftime("%b %d", time.localtime(ts))


def _row(k, label, desc="", enabled=True, color=None):
    """One main-menu line, centered in a 72-wide column."""
    if not enabled:
        badge, lab, d = paint(f"[{k}]", "\033[38;5;239m"), paint(pad(label, 16), "\033[38;5;239m"), \
            paint(desc, "\033[38;5;239m")
    else:
        badge = paint(f"[{k}]", color or __import__("ui").ACCENT, C.BOLD)
        lab = paint(pad(label, 16), C.BWHITE, C.BOLD)
        d = paint(desc, MUTED)
    return " " * 16 + badge + "   " + lab + d


def main_menu_screen():
    """The title screen. Returns ('continue', league) · ('load', league) · ('new', None) · ('online', None)
    · ('quit', None)."""
    import saves
    msg = ""
    while True:
        found = saves.list_saves()
        latest = found[0] if found else None
        try:
            import theme
            if latest and latest.get("team"):
                theme.set_current(latest["team"], persist=False)
        except Exception:
            pass
        clear()
        print()
        for ln in logo_lines():
            print(ln)
        print()
        print(center(paint(TAGLINE, "\033[38;5;242m")))
        print()
        print(center(paint("─" * 72, "\033[38;5;238m")))
        if latest:
            who = saves._who(latest) or latest["name"]
            print(_row("1", "Continue", truncate(f"{who}", 52), color=C.BGREEN))
            print(" " * 38 + paint(truncate(f"{latest['status']} · saved {_ago(latest['saved_at'])}", 52), "\033[38;5;240m"))
        else:
            print(_row("1", "Continue", "no saved games yet", enabled=False))
            print()
        print(_row("2", "New Game", "coach a program, run one as AD, or watch it all"))
        print(_row("3", "Load Game", f"{len(found)} saved game{'s' if len(found) != 1 else ''}" if found
                   else "nothing saved yet", enabled=bool(found)))
        print(_row("4", "Settings", "universe, the show, the sideline, difficulty, routines"))
        print(_row("5", "Manual", "everything, start to finish — searchable"))
        print(_row("6", "About", "how it works, playing in a window, your saves"))
        print(_row("7", "Online", "friends on the same Wi-Fi, one shared world"))
        print(_row("Q", "Quit", "", color=C.BRED))
        print(center(paint("─" * 72, "\033[38;5;238m")))
        print(center(paint(msg, C.BYELLOW) if msg else paint(f"{VERSION}  ·  138 FBS programs  ·  every snap simulated",
                                                              "\033[38;5;240m")))
        msg = ""
        c = ask("Select:").strip().lower()
        if c in ("1", "c", "continue") or (c == "" and latest):
            if not latest:
                msg = "No saved games yet — [2] starts one."
                continue
            print(paint(f"\n   Loading {latest['name']}…", MUTED), flush=True)
            try:
                return "continue", saves.load(latest["path"])
            except saves.SaveError as e:
                msg = str(e)
        elif c in ("2", "n", "new"):
            return "new", None
        elif c in ("3", "l", "load"):
            if not found:
                msg = "Nothing to load yet."
                continue
            league = saves.load_screen()
            if league is not None:
                return "load", league
        elif c in ("4", "s", "settings"):
            import settings
            settings.settings_menu(None)
        elif c in ("5", "m", "?", "manual"):
            import manual
            manual.manual_screen(None)
        elif c in ("6", "a", "about"):
            about()
        elif c in ("7", "o", "online"):
            return "online", None
        elif c in ("q", "quit", "exit"):
            return "quit", None


def about():
    clear()
    print(title_bar("ABOUT", sub=f"{BRAND} {VERSION}"))
    print()
    rows = [
        ("The game", "An immersion-first college football simulation. Every snap of every game is played out; "
                     "every roster was recruited, developed and shuffled by the portal before you arrived."),
        ("Three ways", "Coach Career (build a coach, take a job, try not to get fired) · Athletic Director "
                       "(hire, fire, build, sell tickets) · Spectator (watch the whole sport, bet at The Window)."),
        ("In a window", "play.py (or play.bat / play.command) opens the same game in its own window: every key "
                        "is a button, player names are links, and a live sidebar follows your season."),
        ("Your saves", "Kept in the saves/ folder next to the game. The game autosaves whenever the calendar "
                       "moves and when you quit. [V] on the dashboard saves under any name."),
        ("Help", "The manual is one key away everywhere: [?] on the dashboard, [5] here. It's searchable."),
        ("Names", "Settings → Rename the Campus Countdown cast has a fictional crew and show name for sharing the game."),
    ]
    import textwrap
    for head, body in rows:
        lines = textwrap.wrap(body, WIDTH - 22)
        print("   " + paint(pad(head, 16), C.BYELLOW, C.BOLD) + paint(lines[0], C.BWHITE))
        for ln in lines[1:]:
            print(" " * 19 + paint(ln, C.BWHITE))
        print()
    print(paint(f"   {BRAND} {VERSION} · Python 3.8+ · no internet needed, nothing leaves your computer.", MUTED))
    pause()


def building_screen():
    """New world: returns the progress callback League() calls once a year of history is done."""
    clear()
    print(title_bar("NEW GAME · BUILDING YOUR WORLD", sub="ABOUT HALF A MINUTE"))
    print()
    print(paint("   Every roster on campus in 2026 got there the same way yours will: four years of recruiting", C.BWHITE))
    print(paint("   classes, transfers and player development run before you arrive.", C.BWHITE))
    print()
    state = {"n": 0}
    beats = ("recruiting classes sign · rosters take shape", "the transfer portal opens · players move",
             "players develop · coaches get hired and fired", "one more season before you arrive")

    def progress(year, target):
        total = 4
        state["n"] += 1
        done = min(total, state["n"])
        barw = 32
        fill = int(barw * done / total)
        bar = paint("━" * fill, C.BYELLOW, C.BOLD) + paint("─" * (barw - fill), "\033[38;5;238m")
        print(f"   {paint(str(year), C.BWHITE, C.BOLD)}   {bar}   " + paint(beats[(done - 1) % 4], MUTED), flush=True)
    return progress


def world_ready(league):
    print()
    print(paint("   ✓ ", C.BGREEN, C.BOLD) + paint(f"The {league.year} season is ready.", C.BWHITE, C.BOLD), flush=True)
    time.sleep(0.6)


def leave_menu(league):
    """[Q] on the dashboard. Returns 'stay', 'menu' or 'quit' (both leaving ones autosave)."""
    import saves
    while True:
        clear()
        print(title_bar("LEAVE THE GAME?"))
        print()
        print(paint(f"   {league.status}", C.BWHITE, C.BOLD))
        print(paint("   Your world is saved automatically when you leave — pick up right here from Continue.", MUTED))
        print()
        from ui import menu_item
        print(menu_item("M", "Main menu", "save and go back to the title screen", label_w=16))
        print(menu_item("S", "Save as…", "keep a copy under its own name first", label_w=16))
        print(menu_item("Q", "Quit", "save and close the game", color=C.BRED, label_w=16))
        print(menu_item("B", "Keep playing", "", color=C.GRAY, label_w=16))
        c = ask("Select:").strip().lower()
        if c in ("b", "", "back"):
            return "stay"
        if c == "s":
            saves.save_screen(league)
        elif c in ("m", "q"):
            clear()
            print(paint("\n   Saving…", MUTED), flush=True)
            saves.autosave(league)
            return "menu" if c == "m" else "quit"


def goodbye():
    clear()
    print()
    for ln in logo_lines():
        print(ln)
    print()
    print(center(paint("See you on Saturday.", C.BYELLOW, C.BOLD)))
    print()
