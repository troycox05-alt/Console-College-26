"""
netplay/turn.py — [A] on an online dashboard: your week, the way a Coach Career plays it.

    fall camp (Week 0) -> your bowl week -> the week hub (film, inbox, practice, presser, plan)
    -> READY (your orders go to the host) -> everyone's ready: KICKOFF
    -> Saturday on your copy: the show, your game your way (sim, big moments, every snap,
       watch), everyone else's games -> your game goes to the host
    -> the host plays the official week -> the week's results, your Weekly Wrap, the Recap

Everything on screen is the career's own code. The only new screens are the two waits:
for everyone to be ready, and for everyone to finish their games.
"""
import time

from ui import C, ask, clear, paint, pause, title_bar
from netplay import capture, lobby, replay

WAIT_SLICE = 45            # seconds a wait screen sits before offering its choices again


def play(league):
    """The new world after a played week, or None (stay on this one)."""
    import preseason
    import screens
    from netplay import offseason
    if offseason.active(league):
        return offseason.play(league)
    if league.season_complete:
        return offseason.play(league)
    if preseason.needed(league):
        if not preseason.hub(league):                 # fall camp first, then straight into Week 1
            return None
    return _week(league, screens)


def _week(league, screens):
    import career_plus
    import week
    c = lobby.SESSION["client"]
    if career_plus.mine(league):
        career_plus.bowl_week(league, week.next_game(league, league.user_team))
    if not week.hub(league):                          # your week first: film, inbox, practice, the presser
        return None
    from netplay import moments
    res = c.post_orders(capture.take(league, league.user_team), moments.take())
    if "error" in res:
        print(paint(f"\n   {res.get('message') or res['error']}", C.BRED))
        pause()
        if res.get("error") == "stale":
            return c.fetch_world(force=True)
        return None
    _notices(res)
    c.ready(True)
    k = _wait(c, "kickoff", "EVERYONE'S GETTING READY", _ready_lines)
    if k is None:
        return None
    return _saturday(c, k, screens)


def _notices(res):
    """Show exceptional host-side validation/replay notes; ordinary applied-order lines stay quiet."""
    notes = [str(x) for x in (res.get("warnings") or []) if str(x).strip()]
    if not notes:
        return
    print(paint("\n   ONLINE NOTE", C.BYELLOW, C.BOLD))
    for note in notes[:8]:
        print(paint("   " + note, C.BYELLOW))
    if len(notes) > 8:
        print(paint("   …and %d more." % (len(notes) - 8), C.BYELLOW))
    pause()


# ═══ Saturday on your copy ══════════════════════════════════════════════════

def _saturday(c, league, screens):
    import broadcast
    import career_plus
    import gameday_show
    from commentary import SPEEDS, Narrator
    from screens import REGULAR_SEASON_WEEKS
    from netplay import moments
    capture.begin(league, league.user_team)
    moments.hold(True)                                # the postgame podium goes with your game
    snap = career_plus.before(league)                 # what the Weekly Wrap compares against
    order = {(h, a): i for i, (h, a) in enumerate(league.online.get("kick_order") or [])}
    games = sorted(league.schedule.get(league.week, []), key=lambda g: order.get((g.home.school, g.away.school), 999))
    if league.week <= REGULAR_SEASON_WEEKS:
        sat = broadcast.season_saturday(league.year, league.week)
        before = [g for g in games if g.date < sat]
    else:
        before = []
    state = {"last": None, "auto": True}
    show_done = False
    mine = None
    for i, g in enumerate(games, 1):
        if not show_done and g not in before:
            gameday_show.run_show(league, games)
            show_done = True
        screens._play_one(league, g, i, len(games), state, SPEEDS, Narrator)
        if league.user_team in (g.home, g.away):
            mine = g
    moments.hold(False)
    if mine is not None and mine.__dict__.get("_net") is not None:
        from netplay import result
        info = dict(mine._net, result=result.pack(league, mine), moments=moments.take())
        c.report(info)
    new = _wait(c, "week", "THE REST OF YOUR WORLD IS PLAYING", _played_lines, can_unready=False)
    if new is None:
        return None
    ng = _games_of(new, games)
    _remap(snap, league, new)
    screens.week_results(new, ng)
    career_plus.wrap(new, snap, ng)                   # Coach Career: what your week changed
    if new.week == 14:
        career_plus.selection_show(new)               # Selection Day: the field and the bowls
    import recap
    recap.after_week(new, ng)
    return new


def _games_of(new, games):
    by = {(g.home.school, g.away.school): g for g in new.schedule.get(new.week, [])}
    return [by[(g.home.school, g.away.school)] for g in games if (g.home.school, g.away.school) in by]


def _remap(snap, old, new):
    """The Weekly Wrap's 'before' was taken on the kickoff copy; point it at the new world's
    recruits and players (same people, new objects)."""
    if not snap:
        return
    import records
    rmap = {records.pid(new, r.player): r for r in new.recruiting.pool}
    tmap = {t.school: t for t in new.teams}
    recs = {}
    for r, was, led, cto in snap.get("recs", {}).values():
        nr = rmap.get(records.pid(old, r.player))
        if nr is not None:
            recs[id(nr)] = (nr, was, led, tmap.get(getattr(cto, "school", None)))
    snap["recs"] = recs
    hurt_ids = snap.get("hurt") or set()
    old_hurt = {records.pid(old, p) for p in old.user_team.roster if id(p) in hurt_ids}
    snap["hurt"] = {id(p) for p in new.user_team.roster if records.pid(new, p) in old_hurt}


# ═══ Waiting ════════════════════════════════════════════════════════════════

def _ready_lines(st):
    out = []
    for s in st.get("seats", []):
        if not s.get("school"):
            continue
        mark = paint("✓ ready", C.BGREEN, C.BOLD) if s.get("ready") else paint("… planning", C.GRAY)
        out.append(f"   {s['name']:<18}{s['school']:<22}{mark}")
    return out


def _played_lines(st):
    out = []
    expect, done = set(st.get("expect", [])), set(st.get("played", []))
    for s in st.get("seats", []):
        if not s.get("school"):
            continue
        if s["school"] in expect:
            mark = paint("✓ game finished", C.BGREEN, C.BOLD) if s["school"] in done else paint("… playing", C.GRAY)
        else:
            mark = paint("no game this week", C.GRAY)
        out.append(f"   {s['name']:<18}{s['school']:<22}{mark}")
    return out


def _arrived(c, st, kind):
    """The host has moved on: kicked off (kind "kickoff") or played the week ("week")."""
    want = "games" if kind == "kickoff" else "planning"
    return st.get("phase") == want and int(st.get("rev") or 0) > c.rev


def _wait(c, kind, title, lines, can_unready=True):
    """Sit on the wait screen until the host has kicked off / played the week; returns the new
    world, or None if you chose not to wait (not ready after all)."""
    host = lobby.SESSION.get("host")
    c.events()                                        # from here on, only news
    deadline = time.time() + WAIT_SLICE
    while True:
        st = c.status()
        if c.name in st.get("screens", []):
            remote_session(c)                          # the host's world needs you: your screen, live
            continue
        if _arrived(c, st, kind):
            if kind == "week":
                c.last_results = st.get("results") or {}
            w = c.fetch_world()
            if w is not None:
                return w
        clear()
        print(title_bar(title, sub="ONLINE"))
        print()
        for ln in lines(st):
            print(ln)
        if st.get("online_error"):
            print(paint("\n   Host worker error: " + str(st["online_error"]), C.BRED))
            if host is not None:
                print(paint("   You can use Force to retry this step once the cause is clear.", C.GRAY))
        print(paint("\n   This screen moves on by itself." + (" (Ctrl+C for options.)" if can_unready or host else ""),
                    C.GRAY), flush=True)
        try:
            left = deadline - time.time()
            if left > 0:
                c.events(wait=min(20, left))           # wakes on any news: someone ready, a game done
                continue
        except KeyboardInterrupt:
            pass
        opts = ["[Enter] keep waiting"]
        if can_unready:
            opts.append("[U] not ready after all")
        if host is not None:
            opts.append("[F] don't wait: play it now")
        k = ask("  ·  ".join(opts) + ":").strip().lower()
        deadline = time.time() + WAIT_SLICE
        if k == "u" and can_unready:
            if not _arrived(c, c.status(), kind):
                c.ready(False)
                return None
        if k == "f" and host is not None:
            host.force()


def remote_session(c):
    """A career moment running in the host's world (the phone ringing, a contract talk): its
    screens are drawn here as the host's code draws them, and what you type goes back."""
    import sys
    n = 0
    while True:
        r = c.screen(n, wait=20)
        for k, text in r.get("chunks", []):
            n = k
            if text == "\x00END":
                return
            sys.stdout.write(text)
        sys.stdout.flush()
        if not r.get("live"):
            return
        if r.get("waiting") and n >= int(r.get("last") or 0):
            c.answer(input(""))
