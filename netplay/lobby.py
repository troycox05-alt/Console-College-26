"""
netplay/lobby.py — Online (LAN) from the title screen: host a world or join one, pick your
program, and play from your own copy of the shared world.

    run()            the Online menu: [H] host a world, [J] join a world
    pick_program()   the open programs; take over the sitting coach or bring your own
    session()        your dashboard on your copy of the host's world
"""
import textwrap

from ui import C, ask, clear, key, pad, paint, pause, title_bar, truncate
from netplay import capture, protocol

SESSION = {"client": None, "host": None}


def active(league):
    """This dashboard is an online client's."""
    return SESSION["client"] is not None and league is not None and league.__dict__.get("online_client")


# ═══ The Online menu ════════════════════════════════════════════════════════

def run():
    while True:
        clear()
        print(title_bar("ONLINE · SAME WI-FI", sub="ONLINE"))
        print(paint("\n   Friends on the same home network share one world. Each of you runs the game on your own\n"
                    "   computer and coaches a different program; one of you hosts, and the host's world is the\n"
                    "   official one. Everyone needs the same version of the game.", C.GRAY))
        print()
        print("   " + key("H", "Host a world") + paint("   build or load a world, read out the address and code", C.GRAY))
        print("   " + key("J", "Join a world") + paint("   type the host's address and code", C.GRAY))
        print("   " + key("B", "Back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c in ("", "b"):
            return
        if c == "h":
            host_flow()
        elif c == "j":
            join_flow()


def _ask_name(default=""):
    n = ask(f"Your name (what the others see{', Enter = ' + default if default else ''}):").strip()
    return protocol.clean_name(n or default)


# ═══ Hosting ════════════════════════════════════════════════════════════════

def host_flow():
    import saves
    clear()
    print(title_bar("HOST A WORLD", sub="ONLINE"))
    print()
    print("   " + key("N", "A new world") + paint("   about a minute to build", C.GRAY))
    print("   " + key("L", "Load a save") + paint("   any save: a career's world becomes everyone's", C.GRAY))
    c = ask("Which world? (B = back):").strip().lower()
    if c == "n":
        import main
        league = main.new_world()
    elif c == "l":
        league = saves.load_screen()
    else:
        return
    if league is None:
        return
    name = _ask_name("Host")
    from netplay.client import Client, HostGone, JoinError
    from netplay.host import Host
    try:
        host = Host(league, port=protocol.DEFAULT_PORT).start()
    except OSError as e:
        print(paint(f"\n   Couldn't open port {protocol.DEFAULT_PORT} ({e}). Is another copy already hosting?", C.BRED))
        pause()
        return
    SESSION["host"] = host
    try:
        me = Client(f"127.0.0.1:{host.port}")              # the host plays as a client like everyone else
        me.join(name, code=host.code)
        if not pick_program(me):
            return
        if _host_lobby(host, me):
            session(me)
    except (JoinError, HostGone) as e:
        print(paint(f"\n   {e}", C.BRED))
        pause()
    finally:
        host.stop()
        SESSION["host"] = None


def _seat_lines(st):
    rows = []
    for s in st.get("seats", []):
        who = paint(pad(s["name"], 18), C.BWHITE, C.BOLD)
        prog = paint(s["school"], C.BGREEN) if s.get("school") else paint("picking a program…", C.GRAY)
        how = paint("  · own coach" if s.get("coach") == "new" else "", C.GRAY)
        rows.append(f"   {who}{prog}{how}")
    return rows or [paint("   Nobody yet.", C.GRAY)]


def _host_lobby(host, me):
    """Returns True when the world starts."""
    msg = ""
    while True:
        clear()
        print(title_bar("YOUR WORLD IS OPEN", sub="ONLINE · HOST"))
        print()
        print(paint("   Tell the others:", C.GRAY))
        print(paint(f"      Address  {host.address()}", C.BYELLOW, C.BOLD))
        print(paint(f"      Code     {host.code}", C.BYELLOW, C.BOLD))
        print(paint("   The first time you host, your computer may ask to let Python accept connections:\n"
                    "   allow it on private (home) networks.", C.GRAY))
        print()
        print(paint("   IN THE ROOM", C.BCYAN, C.BOLD))
        for ln in _seat_lines(host.status()):
            print(ln)
        print()
        if msg:
            print(paint("   " + msg, C.BYELLOW))
            msg = ""
        print("   " + key("Enter", "refresh") + "  " + key("P", "change my program") + "  "
              + key("S", "START the world", C.BGREEN) + "  " + key("B", "close it", C.GRAY))
        c = ask("Lobby:").strip().lower()
        if c == "b":
            return False
        if c == "p":
            pick_program(me)
        elif c == "s":
            why = host.start_world()
            if why is None:
                return True
            msg = why


# ═══ Joining ════════════════════════════════════════════════════════════════

def join_flow():
    from netplay.client import Client, HostGone, JoinError
    last = _last_address()
    a = ask(f"Host's address{' (Enter = ' + last + ')' if last else ''}:").strip() or last
    if not a:
        return
    try:
        try:
            c = Client.resume(a)                             # this copy has a seat there already
        except JoinError:
            c = None                                         # a different world now: join fresh
        if c is not None:
            print(paint(f"\n   Welcome back, {c.name}" + (f" — {c.school}." if c.school else "."), C.BGREEN))
            pause()
        else:
            code = ask("Join code (4 digits):").strip()
            c = Client(a)
            c.join(_ask_name(), code=code)
        _remember_address(c.address)
        if not c.school and not pick_program(c):
            return
        if c.status().get("started") or _join_lobby(c):
            session(c)
    except (JoinError, HostGone) as e:
        print(paint(f"\n   {e}", C.BRED))
        pause()


def _join_lobby(c):
    """Waiting for the host to start. Returns True when it has."""
    while True:
        st = c.status()
        if st.get("started"):
            return True
        clear()
        print(title_bar("WAITING FOR THE HOST", sub="ONLINE"))
        print()
        for ln in _seat_lines(st):
            print(ln)
        print(paint("\n   The host starts the world when everyone's picked.", C.GRAY))
        print("   " + key("W", "wait for the start", C.BGREEN) + "  " + key("Enter", "refresh") + "  "
              + key("P", "change my program") + "  " + key("B", "leave", C.GRAY))
        k = ask("Lobby:").strip().lower()
        if k == "b":
            return False
        if k == "p":
            pick_program(c)
        elif k == "w":
            print(paint("   Waiting… (it starts the moment the host presses START)", C.GRAY), flush=True)
            for _ in range(30):                              # up to ten minutes
                if c.wait_start(wait=20):
                    return True


def _last_address():
    from netplay import client
    return client._read_seats().get("_last", {}).get("address", "")


def _remember_address(address):
    from netplay import client
    import json
    seats = client._read_seats()
    seats["_last"] = {"address": address}
    try:
        with open(client.SEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(seats, f, indent=1)
    except OSError:
        pass


# ═══ Picking a program ══════════════════════════════════════════════════════

def pick_program(c):
    """Choose a program and who coaches it. Returns True once a pick is in."""
    from netplay.client import JoinError
    shown = []
    msg = ""
    while True:
        rows = c.programs().get("programs", [])
        clear()
        print(title_bar("PICK YOUR PROGRAM", sub="ONLINE"))
        if c.school:
            print(paint(f"\n   Your pick: {c.school}", C.BGREEN, C.BOLD))
        print(paint("\n   Type a school or part of one (or a conference), # to choose, Enter = back.", C.GRAY))
        for i, r in enumerate(shown, 1):
            coach = "interim coach" if r["interim"] else (r["coach"] or "open")
            tag = paint(f"  · {r['taken']}", C.BRED) if r["taken"] else ""
            print(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)} {pad(truncate(r['school'], 26), 27)}"
                  f"{paint(pad(r['conf'], 12), C.GRAY)}{pad(truncate(coach, 24), 25)}"
                  f"{paint('prestige ' + str(r['prestige']), C.GRAY)}{tag}")
        if msg:
            print(paint("\n   " + msg, C.BYELLOW))
            msg = ""
        q = ask("Program:").strip()
        if not q:
            return bool(c.school)
        if q.isdigit() and 1 <= int(q) <= len(shown):
            r = shown[int(q) - 1]
            if r["taken"] and r["school"] != c.school:
                msg = f"{r['school']} is {r['taken']}'s."
                continue
            how, form = _who_coaches(r)
            if how is None:
                continue
            try:
                c.pick(r["school"], how, form)
                return True
            except JoinError as e:
                msg = str(e)
            continue
        ql = q.lower()
        shown = [r for r in rows if ql in r["school"].lower() or ql == r["conf"].lower()][:30]
        if not shown:
            msg = f"No program matches '{q}'."


def _who_coaches(r):
    print()
    can_adopt = r["coach"] and not r["interim"]
    if can_adopt:
        print("   " + key("1", f"Coach as {r['coach']}") + paint("   the sitting head coach, his staff and his deal", C.GRAY))
    print("   " + key("2", "Bring your own coach") + paint("   build him like a new career", C.GRAY))
    k = ask("Who's on the headset? (Enter = back):").strip()
    if k == "1" and can_adopt:
        return "adopt", None
    if k == "2":
        return "new", coach_form()
    return None, None


def coach_form():
    """The Coach Career questions, answered here and built on the host (the same answers
    make the same coach). Returns the form dict."""
    import career
    import playbook as pb
    clear()
    print(title_bar("YOUR COACH", sub="ONLINE"))
    form = {"first": ask("First name (Enter = Chris):").strip(), "last": ask("Last name (Enter = Walker):").strip(),
            "age": ask("Age (30-60, Enter for 38):").strip()}
    print()
    for k, (label, blurb, *_rest) in career.BACKGROUNDS.items():
        print(f"   {key(k, label)}  " + paint(blurb, C.GRAY))
    form["background"] = ask("Background (Enter = 1):").strip() or "1"
    for title, names, field in (("Offense", list(pb.OFFENSE_SCHEMES), "offense"),
                                ("Defense", list(pb.DEFENSE_SCHEMES), "defense")):
        print()
        print("   " + "   ".join(f"{paint(f'[{i}]', C.BYELLOW, C.BOLD)} {n}" for i, n in enumerate(names, 1)))
        form[field] = ask(f"{title} (Enter = your background's):").strip()
    print()
    for k, (label, _) in career.PHILOSOPHY.items():
        print(f"   {key(k, label)}  " + paint(textwrap.shorten(career.PHILOSOPHY_NOTES[k], 80), C.GRAY))
    form["fourth"] = ask("Fourth downs (Enter = 2):").strip() or "2"
    for k, (label, _) in career.BLITZ.items():
        print(f"   {key(k, label)}  " + paint(textwrap.shorten(career.BLITZ_NOTES[k], 80), C.GRAY))
    form["blitz"] = ask("Pressure (Enter = 2):").strip() or "2"
    return protocol.clean_form(form)


# ═══ Playing ════════════════════════════════════════════════════════════════

def session(c):
    """Your dashboard on your copy of the host's world."""
    print(paint("\n   Getting the world from the host…", C.GRAY), flush=True)
    league = c.fetch_world(force=True)
    if league is None or league.user_team is None:
        print(paint("   The host's world didn't arrive. Try joining again.", C.BRED))
        pause()
        return
    SESSION["client"] = c
    from netplay import moments, replay
    replay.install()                                  # your game's keystrokes can be recorded
    moments.ON_DONE[0] = flush                        # an answered message reaches the host right away
    capture.begin(league, league.user_team)
    try:
        import screens
        screens.main_menu(league)
    finally:
        moments.ON_DONE[0] = None
        moments.take()
        capture.stop()
        SESSION["client"] = None


def flush(league):
    """Send what you've done so far (orders, then the moment just finished) to the host."""
    from netplay import moments
    from netplay.client import HostGone
    c = SESSION["client"]
    if c is None:
        return
    items = moments.take()
    try:
        res = c.post_orders(capture.take(league, league.user_team), items)
    except HostGone:
        moments._S["items"][:0] = items
        raise
    if "error" in res:
        moments._S["items"][:0] = items               # kept: they go with the next post
