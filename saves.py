"""
saves.py — Save and load your world.

Saves live in the saves/ folder next to the game, one file per save
(*.ccsave). Each file is a small header — who, where, when — followed by the
whole league, so the load screen can list saves without reading every world.

  Autosave    written whenever the calendar moves (a week, the offseason),
              right after you choose how to play, and when you quit
  Save Game   [V] on any dashboard tab, under any name you like
  Load Game   the main menu, or tab 8 SYSTEM → [L] (X# deletes a save)

Saves are Python pickles: only load files you made yourself.
"""
import os
import pickle
import re
import sys
import time

from ui import C, MUTED, WIDTH, ask, clear, pad, paint, pause, rule, title_bar, truncate

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
EXT = ".ccsave"
AUTOSAVE = "Autosave"
MAGIC = "console-college-save"
FORMAT = 1                     # bump when a save from an older build can't be loaded as-is
RECURSION_FLOOR = 20000        # rosters, histories and box scores nest deep


class SaveError(Exception):
    pass


# ═══ Files ══════════════════════════════════════════════════════════════════

def _slug(name):
    s = re.sub(r"[^A-Za-z0-9 _-]+", "", name).strip().replace(" ", "_")
    return s[:60] or "save"


def path_for(name):
    return os.path.join(SAVE_DIR, _slug(name) + EXT)


def exists(name):
    return os.path.exists(path_for(name))


def _header(league, name):
    me = getattr(league, "user_coach", None)
    team = me.team.school if me is not None and me.team is not None else None
    return {
        "magic": MAGIC, "format": FORMAT, "name": name, "saved_at": time.time(),
        "year": league.year, "week": league.week, "status": league.status,
        "mode": getattr(league, "mode", None), "coach": me.name if me is not None else None,
        "team": team, "seed": league.seed, "universe": getattr(league, "universe", None),
        "python": ".".join(str(v) for v in sys.version_info[:3]),
        "hotseat": __import__("hotseat").who(league),
        "build": __import__("title").VERSION,
        "commish": (league.__dict__.get("commish") or {}).get("league_id"),
    }


def save(league, name=AUTOSAVE):
    """Write the whole league. Written to a temp file first, so a crash
    mid-save never wipes out the last good one."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    path = path_for(name)
    tmp = path + ".tmp"
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, RECURSION_FLOOR))
    try:
        with open(tmp, "wb") as f:
            pickle.dump(_header(league, name), f, protocol=pickle.HIGHEST_PROTOCOL)
            pickle.dump(league, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, path)
    except (OSError, pickle.PicklingError, RecursionError, TypeError, AttributeError) as e:
        raise SaveError(f"Couldn't save: {e}") from e
    finally:
        sys.setrecursionlimit(limit)
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    return path


def read_header(path):
    try:
        with open(path, "rb") as f:
            header = pickle.load(f)
    except Exception:
        return None
    if not isinstance(header, dict) or header.get("magic") != MAGIC:
        return None
    header["path"] = path
    return header


def list_saves():
    """Every readable save, newest first."""
    if not os.path.isdir(SAVE_DIR):
        return []
    found = []
    for fn in os.listdir(SAVE_DIR):
        if fn.endswith(EXT):
            h = read_header(os.path.join(SAVE_DIR, fn))
            if h is not None:
                found.append(h)
    return sorted(found, key=lambda h: -h["saved_at"])


def load(path):
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, RECURSION_FLOOR))
    try:
        with open(path, "rb") as f:
            header = pickle.load(f)
            if not isinstance(header, dict) or header.get("magic") != MAGIC:
                raise SaveError("That file isn't a Console College save.")
            if header.get("format", 0) > FORMAT:
                raise SaveError("That save was made by a newer version of the game.")
            league = pickle.load(f)
    except SaveError:
        raise
    except Exception as e:
        raise SaveError(f"Couldn't load that save: {e}") from e
    finally:
        sys.setrecursionlimit(limit)
    _after_load(league)
    return league


def _after_load(league):
    """Restore the little bit of state that lives outside the league object."""
    for t in getattr(league, "teams", []):
        t.fix_numbers()                        # older saves could have two players in one jersey
    import season
    season._YEAR[0] = league.year
    import universe
    legacy = getattr(league, "universe", None) is None
    for msg in universe.apply_for(league):      # the universe this world was built in
        print(paint(f"   {msg}", C.BYELLOW))
    if legacy:
        universe.migrate_legacy(league)         # saves from before universes: the renamed internal words
    import custom_teams
    custom_teams.register_all(league)  # custom programs back in the game's tables (or none: back to stock)
    import carousel
    carousel.migrate(league)          # fills in anything an older save is missing
    import traits
    traits.dedupe_league(league)      # nobody carries the same trait twice
    import coach_profile
    from coaches_data import COACH_OVERRIDES
    for t in getattr(league, "teams", []):
        for c in (getattr(t, "coach", None), getattr(t, "oc", None), getattr(t, "dc", None)):
            if c is not None:
                coach_profile.shape(c, pinned=COACH_OVERRIDES.get(getattr(c, "name", ""), {}).keys())
    import rivalries
    rivalries.rebuild(league)         # older saves: read the archive into the series book
    import dynasty
    dynasty.ensure_all(league)        # older saves: prestige gets its brand half
    import compliance
    compliance.migrate(league)        # older saves: the compliance book starts empty
    import records
    records.migrate(league)           # older saves: the record book starts this season
    import halloffame
    halloffame.migrate(league)
    import guide
    guide.migrate(league)             # older saves: past the first week
    import hotseat
    hotseat.after_load(league)        # restore each Hot Seat coach's private state
    import commissioner
    commissioner.migrate(league)      # Commissioner Mode: bring the league block up to this build


def autosave(league):
    """Quietly keep the autosave current. Never lets a save problem end the game."""
    if league.__dict__.get("online_client"):
        return True                      # a copy of someone else's online world: the host keeps it
    try:
        save(league, AUTOSAVE)
        return True
    except SaveError as e:
        print(paint(f"\n   Autosave failed — {e}", C.BRED))
        pause()
        return False


# ═══ Screens ════════════════════════════════════════════════════════════════

def _when(ts):
    return time.strftime("%b %d, %Y  %I:%M %p", time.localtime(ts))


def _ago(ts):
    s = max(0, time.time() - ts)
    if s < 90:
        return "just now"
    if s < 3600:
        return f"{int(s // 60)} min ago"
    if s < 86400:
        return f"{int(s // 3600)} hr ago"
    return time.strftime("%b %d, %Y", time.localtime(ts))


def _who(h):
    if h.get("hotseat"):
        return h["hotseat"]
    if h.get("mode") == "career" and h.get("coach"):
        return f"Coach {h['coach']}" + (f" · {h['team']}" if h.get("team") else "")
    if h.get("mode") == "spectator":
        return "Spectator"
    if h.get("mode") == "ad":
        return "Athletic Director"
    if h.get("mode") == "commissioner":
        return "Commissioner league"
    return ""


def _save_line(i, h):
    auto = h["name"].lower() == AUTOSAVE.lower()
    where = h["status"].replace(" Season ·", " ·")
    top = (f"   {pad(paint(f'[{i}]', C.BYELLOW, C.BOLD), 6)}{pad(paint(truncate(h['name'], 34), C.BWHITE, C.BOLD), 36)}"
           f"{pad(paint(truncate(where, 30), C.BCYAN), 32)}{paint(_ago(h['saved_at']), MUTED)}")
    sub = f"         {pad(paint(truncate(_who(h) or 'World ' + str(h['seed']), 66), MUTED), 68)}" + \
        (paint("autosave", "\033[38;5;240m") if auto else "")
    return top + "\n" + sub


def default_name(league):
    me = getattr(league, "user_coach", None)
    stamp = f"{league.year} Wk{league.week}" if league.week else f"{league.year} Pre"
    if getattr(league, "mode", None) == "career" and me is not None:
        who = me.team.school if me.team is not None else me.name
        return f"{who} {stamp}"
    if getattr(league, "mode", None) == "commissioner":
        return f"League {stamp}"
    return f"World {league.seed} {stamp}"


def save_screen(league):
    from ui import footer, key, back_key
    if league.__dict__.get("online_client"):
        print(paint("\n   This is the host's world: the host saves it. Your seat rejoins with the code's address.", C.BYELLOW))
        pause()
        return
    clear()
    print(title_bar("SAVE GAME", sub="SAVES"))
    print()
    print(paint(f"   {league.status}", C.BWHITE, C.BOLD) + paint(f"   ·   {_who(_header(league, ''))}", MUTED))
    found = list_saves()
    if found:
        print(paint("\n   ON FILE", MUTED, C.BOLD))
        for h in found[:6]:
            print(paint(f"     {pad(truncate(h['name'], 22), 24)}{pad(truncate(h['status'], 24), 26)}{_ago(h['saved_at'])}",
                        "\033[38;5;246m"))
    suggestion = default_name(league)
    footer(key("Enter", f"save as '{suggestion}'", C.BGREEN), key("type", "a name of your own"), back_key("Cancel"))
    name = ask("Name this save:")
    if name.lower() in ("b", "back"):
        return
    name = name or suggestion
    if name.lower() == AUTOSAVE.lower():
        print(paint("\n   That name is reserved for the autosave. Pick another.", C.BYELLOW))
        pause()
        return
    if exists(name):
        if ask(f"'{name}' already exists. Overwrite it? (y/N)").lower() not in ("y", "yes"):
            return
    print(paint("\n   Saving…", MUTED), flush=True)
    try:
        path = save(league, name)
    except SaveError as e:
        print(paint(f"   {e}", C.BRED))
    else:
        print(paint(f"   ✓ Saved as '{name}'", C.BGREEN, C.BOLD) + paint(f"   ({os.path.relpath(path)})", MUTED))
    pause()


def delete(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def load_screen():
    """Pick a save. Returns the loaded league, or None."""
    from ui import footer, key, back_key
    msg = ""
    while True:
        clear()
        found = list_saves()
        print(title_bar("LOAD GAME", sub=f"{len(found)} SAVED GAME{'S' if len(found) != 1 else ''}"))
        print()
        if not found:
            print(paint("   No saves yet. They'll show up here once you've played a week.", C.GRAY))
            pause()
            return None
        print(paint(f"   {'':6}{'SAVE':<36}{'WHERE':<32}SAVED", MUTED, C.BOLD))
        print("   " + rule(width=WIDTH - 4))
        for i, h in enumerate(found, 1):
            print(_save_line(i, h))
        if msg:
            print(paint("\n   " + msg, C.BYELLOW))
            msg = ""
        footer(key("#", "load", C.BGREEN), key("X#", "delete a save", C.BRED), back_key())
        choice = ask("Load which save?").lower()
        if choice in ("b", "back", ""):
            return None
        if choice.startswith("x") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(found):
            h = found[int(choice[1:]) - 1]
            if ask(f"Delete '{h['name']}' for good? Type DELETE to confirm:").strip().upper() == "DELETE":
                msg = f"Deleted '{h['name']}'." if delete(h["path"]) else "Couldn't delete that file."
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(found):
            h = found[int(choice) - 1]
            print(paint(f"\n   Loading {h['name']}…", MUTED), flush=True)
            try:
                return load(h["path"])
            except SaveError as e:
                msg = str(e)
