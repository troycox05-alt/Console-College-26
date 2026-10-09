"""
play.py — Console College in its own desktop window.

    python play.py            the desktop window (needs pywebview: pip install pywebview)
    python play.py --browser  the same thing in your web browser, no install needed

The game itself doesn't change. It runs exactly as it does in a terminal; this
launcher just gives it a better home:

  • every [R]-style hotkey on screen is a button you can click
  • almost every name is a link (links.py) that opens its page in a card
  • a sidebar with your season at a glance — next game, results, standings, the poll,
    your lineup, injuries, leaders, recruiting, news — and one-click shortcuts
  • scroll back through earlier screens, zoom, light/dark theme, sounds

How it works: the game runs on a background thread. Everything it prints goes
to a small local web server (127.0.0.1 only — nothing leaves your computer),
and the window reads from it. What you click or type goes back as the line the
game was waiting for. Your saves and settings are the same files as always.
"""
import builtins
import json
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(HERE, "gui")
PREFS = os.path.join(HERE, "gui_prefs.json")
sys.path.insert(0, HERE)


# ═══ The bridge: the game's print/input/clear, rerouted ═════════════════════

def _tr(text):
    """Translate display terms for the active universe."""
    u = sys.modules.get("universe")
    return u.translate(text) if u is not None else text


class _CaptureDone(Exception):
    pass

class Chan:
    """One place the game can wait for a player: the main game thread, or (LAN, everyone at once) one coach's
    own thread. Each has its own line queue, so two coaches can each be mid-prompt at the same moment."""
    __slots__ = ("q", "waiting", "prompt", "owner", "seat")

    def __init__(self):
        self.q = queue.Queue()
        self.waiting = False
        self.prompt = ""
        self.owner = None           # LAN: who may answer ('seat', name) | ('slot', n) | None (the host)
        self.seat = None            # LAN: the seat whose state this prompt belongs to


class Bridge:
    MAX_EVENTS = 4000

    def __init__(self):
        self.lock = threading.Lock()
        self.events = []            # [(seq, kind, text, audience)]
        self.seq = 0
        self.main = Chan()          # the main game thread's prompt
        self.chans = {}             # LAN, everyone at once: seat name -> that coach's thread's prompt
        self.lines = self.main.q    # what the player sent (the main channel's queue)
        self.wait_seq = 0           # bumps every time the game stops for input (the sidebar's cache key)
        self.begin_block = None     # LAN: let another coach's thread run while this one waits
        self.end_block = None
        self.done = False
        self.local = threading.local()   # a side capture (player cards opened from the window)
        self.aud_fn = None          # LAN: who may SEE what's printed right now ('*' or a seat name)
        self.owner_fn = None        # LAN: who may ANSWER the prompt that's up

    def push(self, kind, text="", aud=None):
        if aud is None:
            aud = self.aud_fn() if self.aud_fn is not None else "*"
        with self.lock:
            self.seq += 1
            self.events.append((self.seq, kind, text, aud))
            if len(self.events) > self.MAX_EVENTS:
                # keep everything since the last clear, and a little before it
                cut = len(self.events) - self.MAX_EVENTS // 2
                self.events = self.events[cut:]

    @property
    def waiting(self):
        return self.main.waiting

    @property
    def prompt(self):
        return self.main.prompt

    @property
    def prompt_owner(self):
        return self.main.owner

    def chan(self, key):
        with self.lock:
            ch = self.chans.get(key)
            if ch is None:
                ch = self.chans[key] = Chan()
            return ch

    def close(self):
        """The window closed: wake every waiting thread so the game can end."""
        self.main.q.put(None)
        for ch in list(self.chans.values()):
            ch.q.put(None)

    def since(self, n, sees=None):
        """Events after n. In LAN mode `sees(aud)` keeps only what this device may see."""
        with self.lock:
            first = self.events[0][0] if self.events else self.seq + 1
            out = [e for e in self.events if e[0] > n and (sees is None or sees(e[3]))]
            return out, first, self.seq

    # ── stand-ins ──
    def write(self, text):
        cap = getattr(self.local, "buf", None)
        if cap is not None:
            cap.append(text)
            return len(text)
        if text:
            self.push("out", text)
        return len(text)

    def clear(self):
        cap = getattr(self.local, "buf", None)
        if cap is not None:
            cap.clear()
            return
        self.push("clear")

    def wipe(self):
        """Hot Seat's pass-the-controller screen: forget every earlier screen, here and in the window, so the
        next coach can't scroll back to the last one's board."""
        if getattr(self.local, "buf", None) is not None:
            return
        if self.aud_fn is None:
            with self.lock:
                self.events = []
        else:                                            # LAN: forget only this seat's screens, not the others'
            aud = self.aud_fn()
            if aud != "*":
                with self.lock:
                    self.events = [e for e in self.events if e[3] != aud]
        self.push("wipe")

    def input(self, prompt=""):
        if getattr(self.local, "buf", None) is not None:
            self.local.asks = getattr(self.local, "asks", 0) + 1
            if self.local.asks > 6:
                raise _CaptureDone()
            return ""                                   # a side capture never waits
        prompt = _tr(str(prompt))
        key = getattr(self.local, "chan", None)         # a coach's own thread has its own channel
        ch = self.main if key is None else self.chan(key)
        if key is not None:
            ch.owner, ch.seat = ("seat", key), key
        else:
            ch.owner = self.owner_fn() if self.owner_fn is not None else None
            ch.seat = ch.owner[1] if ch.owner and ch.owner[0] == "seat" else None
        if prompt:
            self.push("out", prompt)
        ch.prompt = prompt
        self.wait_seq += 1
        ch.waiting = True
        self.push("wait", prompt)
        d = self.begin_block() if self.begin_block is not None else 0     # let the other coaches' threads run
        try:
            line = ch.q.get()
        finally:
            ch.waiting = False
            if self.end_block is not None:
                self.end_block(d)                       # ... and take the game back, as this coach
        if line is None:                                # the window closed
            raise EOFError
        self.push("echo", line + "\n")
        return line

    def capture(self, fn):
        """Run fn() on this thread with its printing kept aside; return the text."""
        self.local.buf = []
        try:
            fn()
        except Exception as e:                           # a card that fails shouldn't take the game down
            self.local.buf.append(f"\n  (couldn't open that: {e})\n")
        finally:
            text = "".join(self.local.buf)
            self.local.buf = None
        return text


class _Out:
    """sys.stdout for the game."""

    encoding = "utf-8"

    def __init__(self, bridge):
        self.b = bridge

    def write(self, text):
        return self.b.write(str(text))

    def flush(self):
        pass

    def isatty(self):
        return False

    def reconfigure(self, **_):
        pass


BRIDGE = Bridge()


LAN = None                           # (the old Hot Seat network mode was removed; always None)


def _view_hook(kind, text):
    if getattr(BRIDGE.local, "buf", None) is not None:
        return                       # a captured pop-up (a player card): its screen isn't the game's screen
    BRIDGE.push(kind, text)


def install():
    """Must run before any game module is imported."""
    builtins.input = BRIDGE.input
    sys.stdout = _Out(BRIDGE)
    import ui
    ui.clear = BRIDGE.clear          # every `from ui import clear` made after this gets the window version
    ui.WINDOW[0] = True              # footers are marked (the window keeps them on screen)
    ui.wipe_history = BRIDGE.wipe    # Hot Seat: the pass screen forgets what came before it
    ui.CLIP[0] = lambda text: BRIDGE.push("clip", text)   # Copy team context: the page puts it on the clipboard
    import webview
    webview.HOOK[0] = _view_hook                                   # native web screens (webview.py)
    import faces
    faces.TRUECOLOR = True           # the window draws 24-bit color (and the faces' half-blocks) itself


# ═══ What the sidebar shows ═════════════════════════════════════════════════

_players = {}


def league():
    try:
        import scout
        return scout._LG[0]
    except Exception:
        return None


_last_state = {"ready": False}
_state_cache = {}                     # LAN: each coach's sidebar is cached on its own


def channel_for(c):
    """The prompt (Chan) this device may answer right now, or None. A coach answers his own thread's prompt;
    the main thread's prompt goes to whoever it's addressed to; the host covers a coach nobody connected holds."""
    if LAN is None:
        return BRIDGE.main if BRIDGE.main.waiting else None
    mine = c.get("seat")
    if mine:
        ch = BRIDGE.chans.get(mine)
        if ch is not None and ch.waiting:
            return ch
    for name, ch in list(BRIDGE.chans.items()):
        if ch.waiting and LAN.can_answer(c, ("seat", name)):
            return ch
    if BRIDGE.main.waiting and LAN.can_answer(c, BRIDGE.main.owner):
        return BRIDGE.main
    return None


def _as(ch, fn):
    """Run fn() with the game lock held and the answering coach's state on the league (LAN, everyone at once)."""
    return fn()


def state(c=None):
    """The sidebar's data. Built only while the game is waiting for you (nothing is moving);
    while it's busy, the last picture stands."""
    lg = league()
    if lg is None:
        return {"ready": False}
    try:
        import hotseat
        if hotseat.covered():
            return {"ready": False}                         # Hot Seat hand-off: nothing of the last coach's on show
    except Exception:
        pass
    ch = channel_for(c) if c is not None else (BRIDGE.main if BRIDGE.main.waiting else None)
    key = (c or {}).get("seat") if LAN is not None else None
    last = _state_cache.get(key, {"ready": False})
    if ch is None and last.get("ready"):
        return dict(last, busy=True)
    if last.get("ready") and last.get("_seq") == BRIDGE.wait_seq:
        return last                                         # nothing can have changed: the game hasn't moved

    def build():
        out = _state(lg)
        out["_seq"] = BRIDGE.wait_seq
        try:
            import gui_data
            out.update(gui_data.snapshot(lg))
        except Exception as e:
            out["error"] = str(e)
        return out
    out = _as(ch, build)
    _state_cache[key] = out
    return out


def action(aid, c=None):
    """A sidebar shortcut: a few keys typed for you — only from the dashboard."""
    lg = league()
    ch = channel_for(c) if c is not None else (BRIDGE.main if BRIDGE.main.waiting else None)
    if lg is None or ch is None:
        return {"ok": False, "text": "Shortcuts work from the dashboard — finish what's on screen first."}

    def find():
        if not getattr(lg, "_gui_at_dash", None):
            return None
        import gui_data
        return next((a for a in gui_data.actions(lg) if a["id"] == aid), None)
    if _as(ch, lambda: getattr(lg, "_gui_at_dash", None)) is None:
        return {"ok": False, "text": "Shortcuts work from the dashboard — finish what's on screen first."}
    act = _as(ch, find)
    if act is None:
        return {"ok": False, "text": "That isn't available right now."}
    for k in act["keys"]:
        ch.q.put(k)
    return {"ok": True}


def _state(lg):
    import dashboard
    import people
    import scout
    out = {"ready": True}
    try:
        import links
        out["linkKey"] = links.index(lg)[0]
    except Exception:
        pass
    try:
        team = dashboard.focus_team(lg)
        career = getattr(lg, "mode", None) == "career"
        rk = lg.rankings.rank_of(team)
        out.update(school=team.school, mascot=getattr(team, "nickname", ""), record=team.record,
                   conf=team.conf_record if hasattr(team, "conf_record") else "",
                   conference="FCS" if getattr(team, "fcs", False) else team.conference,
                   rank=rk, year=lg.year, when=lg.week_name(lg.week) if hasattr(lg, "week_name") else "",
                   mode="Coach Career" if career else "Athletic Director" if getattr(lg, "mode", "") == "ad"
                   else "Spectator")
        if callable(out["conf"]):
            out["conf"] = out["conf"]()
        if callable(out["record"]):
            out["record"] = out["record"]()
        g = dashboard.next_game(lg, team)
        if g is not None:
            opp = g.opponent_of(team)
            site = "vs" if g.neutral or g.home is team else "at"
            import carousel as cz
            try:
                wp = cz.win_prob(team, opp, 0 if g.neutral else (1 if g.home is team else -1))
                wp = min(0.99, max(0.01, wp))
                odds = scout.odds(wp, lg, team).replace("you're ", "").replace("you win this ", "").replace(" of the time", "")
            except Exception:
                wp, odds = None, ""
            ork = lg.rankings.rank_of(opp)
            out["next"] = {"site": site, "opp": (f"#{ork} " if ork else "") + opp.school,
                           "week": lg.week_name(g.week) if hasattr(lg, "week_name") else f"Week {g.week}",
                           "odds": odds, "wp": wp if not scout.hidden(lg, team) else None}
        c = getattr(lg, "user_coach", None) if career else None
        if c is not None:
            import skills
            out["coach"] = {"name": c.name, "seat": round(getattr(c, "seat", 0)),
                            "points": skills._st(c).get("points", 0)}
            out["inbox"] = people.unread(lg)
            out["waiting"] = len(people.waiting(lg))
        # names the window can turn into links: your roster and your next opponent's
        teams = [team] + ([g.opponent_of(team)] if g is not None else [])
        names = []
        _players.clear()
        for t in teams:
            for p in getattr(t, "roster", []):
                _players[str(id(p))] = p
                names.append({"id": str(id(p)), "name": p.name, "short": p.short_name, "pos": p.position,
                              "num": p.number, "mine": t is team})
        out["players"] = names
    except Exception as e:                              # the game is mid-update; try again next poll
        out["error"] = str(e)
    return out


def links_list():
    """Everything on screen that can be clicked (links.py)."""
    lg = league()
    if lg is None:
        return {"key": "", "list": []}
    try:
        import links
        key, lst = links.index(lg)
        return {"key": key, "list": lst}
    except Exception as e:
        return {"key": "", "list": [], "error": str(e)}


def card(pid, c=None):
    lg = league()
    ch = channel_for(c) if c is not None else (BRIDGE.main if BRIDGE.main.waiting else None)
    if pid and not pid.isdigit() and lg is not None:
        if ch is None:
            return {"ok": False, "text": "Hang on — the game is busy. Try again in a second."}
        import links
        fn = links.render(lg, pid)
        if fn is None:
            return {"ok": False, "text": "That isn't around anymore."}
        return {"ok": True, "text": _as(ch, lambda: BRIDGE.capture(fn))}
    p = _players.get(pid)
    if p is None and lg is not None:                    # a player from elsewhere in the sidebar (Heisman watch...)
        p = next((x for t in lg.teams for x in t.roster if str(id(x)) == pid), None)
    if p is None or lg is None:
        return {"ok": False, "text": "That player isn't around anymore."}
    if ch is None:
        return {"ok": False, "text": "Hang on — the game is busy. Try again in a second."}
    import screens
    out = {"ok": True, "text": _as(ch, lambda: BRIDGE.capture(lambda: screens.player_card(lg, p)))}
    try:
        import webview
        out["data"] = webview.player_data(lg, p)          # the web app draws the card from this
    except Exception:
        pass
    return out


def load_prefs():
    try:
        with open(PREFS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_prefs(d):
    try:
        with open(PREFS, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError:
        pass


# ═══ The local server ═══════════════════════════════════════════════════════

TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".png": "image/png", ".ico": "image/x-icon",
         ".svg": "image/svg+xml"}


_LAN_PREFS = {}                       # LAN: each device keeps its own zoom/theme/tab (in memory, seeded from the file)
_API = ("/poll", "/state", "/prefs", "/send", "/card", "/action", "/copy", "/claim", "/release")


def _owner_name(owner):
    if owner is None:
        return "the host"
    kind, who = owner
    return who if kind == "seat" else f"player {who}"


def lan_info(c):
    """What this device's page needs to know about the table (LAN mode)."""
    import hotseat
    names = hotseat.lan_names()
    LAN.reconcile(names)
    can = channel_for(c) is not None
    unclaimed = [n for n in names if LAN.holder(n) is None or not LAN.alive(LAN.holder(n))]
    return {"on": True, "you": c["seat"], "slot": c["slot"], "host": c["host"], "can": can,
            "table": LAN.table(names), "unclaimed": unclaimed, "setup": not names,
            "working": [] if can else hotseat.working_names(),
            "waitfor": None if (can or not BRIDGE.main.waiting) else _owner_name(BRIDGE.main.owner)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _client(self):
        """LAN: the device behind this request (None = refused; the 403 has been sent)."""
        if LAN is None:
            return {"slot": 1, "seat": None, "host": True, "seen": time.time()}
        q = self.path.split("?", 1)[1] if "?" in self.path else ""
        code = self.headers.get("X-Code") or ""
        token = self.headers.get("X-Token") or ""
        if not code:
            for part in q.split("&"):
                if part.startswith("code="):
                    code = part[5:]
        if code != LAN.code or not token:
            self._json({"ok": False, "error": "code"}, 403)
            return None
        return LAN.hello(token)

    def _answerer_ok(self, c):
        return channel_for(c) is not None

    def _json(self, obj, code=200):
        data = _tr(json.dumps(obj)).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        c = None
        if path in _API:
            c = self._client()
            if c is None:
                return
        if path == "/poll":
            q = self.path.split("since=")[-1].split("&")[0] if "since=" in self.path else "0"
            n = int(q) if q.isdigit() else 0
            if LAN is None:
                evs, first, last = BRIDGE.since(n)
                return self._json({"events": [[s, k, t] for s, k, t, _ in evs], "first": first, "last": last,
                                   "waiting": BRIDGE.waiting, "done": BRIDGE.done})
            evs, first, last = BRIDGE.since(n, lambda aud: LAN.sees(c, aud))
            return self._json({"events": [[s, k, t] for s, k, t, _ in evs], "first": first, "last": last,
                               "waiting": self._answerer_ok(c), "done": BRIDGE.done,
                               "lan": lan_info(c)})
        if path == "/state":
            if LAN is not None and not self._answerer_ok(c):    # LAN: only a coach at a prompt gets a sidebar
                return self._json({"ready": False, "waitfor": _owner_name(BRIDGE.main.owner)})
            return self._json(state(c if LAN is not None else None))
        if path == "/prefs":
            if LAN is not None:
                return self._json(_LAN_PREFS.get(self.headers.get("X-Token") or "", load_prefs()))
            return self._json(load_prefs())
        if path == "/links":
            return self._json(links_list())
        if path == "/":
            path = "/index.html"
        f = os.path.normpath(os.path.join(GUI, path.lstrip("/")))
        if not f.startswith(GUI) or not os.path.isfile(f):
            self.send_response(404)
            self.end_headers()
            return
        with open(f, "rb") as fh:
            data = fh.read()
        if f.endswith((".html", ".js")):
            data = _tr(data.decode("utf-8")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(os.path.splitext(f)[1], "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = self.path.split("?")[0]
        body = self._body()
        c = None
        if path in _API:
            c = self._client()
            if c is None:
                return
        if path == "/claim" and LAN is not None:
            import hotseat
            ok = LAN.claim(self.headers.get("X-Token") or "", str(body.get("seat", "")), hotseat.lan_names())
            return self._json({"ok": ok})
        if path == "/release" and LAN is not None:
            LAN.release(self.headers.get("X-Token") or "")
            return self._json({"ok": True})
        if LAN is not None and path in ("/send", "/card", "/action") and not self._answerer_ok(c):
            return self._json({"ok": False, "text": "It isn't your turn."})
        if path == "/send":
            ch = channel_for(c) if LAN is not None else BRIDGE.main
            ch.q.put(str(body.get("line", "")))
            return self._json({"ok": True})
        if path == "/card":
            return self._json(card(str(body.get("id", "")), c if LAN is not None else None))
        if path == "/action":
            return self._json(action(str(body.get("id", "")), c if LAN is not None else None))
        if path == "/prefs":
            if LAN is not None:
                _LAN_PREFS[self.headers.get("X-Token") or ""] = body
            else:
                save_prefs(body)
            return self._json({"ok": True})
        if path == "/copy":
            if LAN is not None and not c["host"]:
                return self._json({"ok": False})          # the clipboard belongs to the host's machine
            try:
                import screen_copy
                ok = screen_copy.copy(str(body.get("text", "")))
            except Exception:
                ok = False
            return self._json({"ok": ok})
        self._json({"ok": False}, 404)


def serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, url


# ═══ The game thread ════════════════════════════════════════════════════════

def run_game():
    try:
        import main
        main.main()
    except (EOFError, KeyboardInterrupt):
        pass
    except SystemExit:
        pass
    except Exception:
        import traceback
        tb = traceback.format_exc()
        BRIDGE.crashed = tb
        try:                                             # the host's logs (Railway: Deploy Logs) get it too
            sys.__stderr__.write("\n=== CONSOLE COLLEGE CRASH ===\n" + tb + "\n")
            sys.__stderr__.flush()
        except Exception:
            pass
        BRIDGE.push("out", "\n\n  Something went wrong:\n\n" + tb, aud="*")
        BRIDGE.push("out", "\n  Your last autosave is safe. Close the window and start again.\n", aud="*")
    finally:
        BRIDGE.done = True
        BRIDGE.push("done", aud="*")


def _need_pywebview():
    sys.__stdout__.write(
        "\n  Console College's desktop window needs one small package, pywebview.\n"
        "  Install it with:   python -m pip install pywebview\n\n")
    try:
        ans = input("  Install it now? [Y/n] ").strip().lower()
    except EOFError:
        ans = "n"
    if ans in ("", "y", "yes"):
        import subprocess
        r = subprocess.run([sys.executable, "-m", "pip", "install", "pywebview"])
        if r.returncode == 0:
            sys.__stdout__.write("\n  Installed. Starting the game...\n")
            return True
    sys.__stdout__.write("\n  No problem — opening the game in your web browser instead.\n")
    return False



def main():
    browser = "--browser" in sys.argv
    webview = None
    if not browser:
        try:
            import webview                                   # noqa: F401
        except ImportError:
            if _need_pywebview():
                try:
                    import importlib
                    importlib.invalidate_caches()
                    import webview                           # noqa: F811
                except ImportError:
                    webview = None
            if webview is None:
                browser = True

    install()
    srv, url = serve()
    game = threading.Thread(target=run_game, name="game", daemon=True)
    game.start()

    if browser:
        import webbrowser
        sys.__stdout__.write(f"\n  Console College is running at {url}\n  (keep this window open while you play)\n")
        webbrowser.open(url)
        try:
            while game.is_alive():
                time.sleep(0.5)
            time.sleep(3)                                     # let the window read the goodbye
        except KeyboardInterrupt:
            pass
        return

    win = webview.create_window("Console College", url, width=1440, height=920, min_size=(960, 620),
                                background_color="#0b0f14", confirm_close=True, text_select=True)

    def watch():
        game.join()
        time.sleep(2.5)
        try:
            win.destroy()
        except Exception:
            pass
    threading.Thread(target=watch, daemon=True).start()
    webview.start()
    BRIDGE.close()                                           # window closed: let every game thread end
    os._exit(0)


if __name__ == "__main__":
    main()
