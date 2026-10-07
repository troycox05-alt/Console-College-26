"""
netplay/replay.py — your game, coached on your computer, played the same on the host.

In a career you coach your own game live. Online you still do: your copy plays it, exactly as
the career does (the same broadcast, the same headset, halftime, big moments). The host's
world stays the official one because a game is reproducible: every copy seeds the game the
same way (league.play_game), the commentary has its own dice, and everything you typed
during the game is recorded. The host plays your game again with those keystrokes and your
game settings, on its own thread, with the output thrown away, and gets the same game.
A fingerprint of the result (signature) is compared, so a game that ever came out different
is caught and reported, never silently kept.

    with recording(league, g, info): league.play_game(g, narr)    # the client
    keys = info["keys"]
    with replaying(keys, settings_dict): league.play_game(g, narr) # the host's worker thread
"""
import builtins
import hashlib
import io
import random
import sys
import threading
import time

_tl = threading.local()
_installed = {"done": False}


class _ThreadOut:
    """sys.stdout that a thread can point elsewhere (the host's replay thread prints nowhere;
    the host's own screen, on the main thread, is untouched)."""
    def __init__(self, real):
        self._real = real

    def write(self, s):
        remote = getattr(_tl, "remote", None)
        if remote is not None and getattr(_tl, "feed", None) is None:
            remote.write(s)                              # a player's screen, drawn on his computer
        out = getattr(_tl, "out", None)
        return (out or self._real).write(s)

    def flush(self):
        out = getattr(_tl, "out", None)
        return (out or self._real).flush()

    def __getattr__(self, name):
        return getattr(self._real, name)


def install():
    """Once per run, before any online game: thread-aware output and input."""
    if _installed["done"]:
        return
    _installed["done"] = True
    sys.stdout = _ThreadOut(sys.stdout)
    real_input = builtins.input

    def _input(prompt=""):
        feed = getattr(_tl, "feed", None)
        remote = getattr(_tl, "remote", None)
        if feed is None and remote is not None:
            return remote.ask(str(prompt))           # the player answers on his own keyboard
        if feed is None and getattr(_tl, "host", False):
            return ""                                # the host's world never waits on a keyboard: the default
        if feed is not None:                         # a replay: the coach's answers, in order
            out = getattr(_tl, "out", None)
            if out is not None:
                out.write(str(prompt))
            if feed:
                return feed.pop(0)
            _tl.ran_out = True
            return ""
        ans = real_input(prompt)
        rec = getattr(_tl, "rec", None)
        if rec is not None:
            rec.append(ans)
        return ans
    builtins.input = _input


class recording:
    """Everything typed inside goes into info["keys"]."""
    def __init__(self, info):
        self.info = info

    def __enter__(self):
        install()
        self.info["keys"] = []
        _tl.rec = self.info["keys"]
        return self.info

    def __exit__(self, *exc):
        _tl.rec = None
        return False


class replaying:
    """Inside, this thread reads `keys` as its input, the coach's game settings as its
    settings, and prints nowhere. .ran_out says if the game asked for more than was typed."""
    def __init__(self, keys, game_settings=None):
        self.keys = list(keys or [])
        self.game_settings = game_settings
        self.ran_out = False

    def __enter__(self):
        install()
        import settings
        self._settings = settings.use(self.game_settings or {})
        self._settings.__enter__()
        _tl.feed, _tl.out, _tl.ran_out = self.keys, io.StringIO(), False
        return self

    def __exit__(self, *exc):
        self.ran_out = bool(getattr(_tl, "ran_out", False))
        _tl.feed, _tl.out = None, None
        self._settings.__exit__(*exc)
        return False


class host_thread:
    """The host's world working (a week, a coach's orders): its screens go nowhere and any
    question it asks takes its default, so the host's own screen and keyboard stay his."""
    def __enter__(self):
        install()
        self.prev = (getattr(_tl, "out", None), getattr(_tl, "host", False))
        _tl.out = self.prev[0] or io.StringIO()
        _tl.host = True
        return self

    def __exit__(self, *exc):
        _tl.out, _tl.host = self.prev
        return False


# ═══ A player's screen, run on the host ═════════════════════════════════════
# Some career moments can't be replayed: they happen in the middle of the host's world work
# (the phone ringing in the carousel, the AD's contract talk, the offseason's decisions).
# Those run on the host, as that coach, and their screen is drawn on his computer: what the
# host's code prints goes to his client, and what he types comes back. Same screens as a
# career, live. One BRIDGE per player (by name).

BRIDGES = {}
WAIT_ANSWER = 900                     # seconds a question waits for a player before its default


class Bridge:
    def __init__(self, name):
        import queue
        self.name = name
        self.lock = threading.Condition()
        self.chunks = []                 # [(n, text)]
        self.n = 0
        self.live = False                # a question has been asked in this session
        self.waiting = False
        self.answers = queue.Queue()
        self.on_live = None              # host hook: tell the room

    def begin(self):
        import queue
        with self.lock:
            self.chunks, self.live, self.waiting = [], False, False
            while True:
                try:
                    self.answers.get_nowait()
                except queue.Empty:
                    break

    def end(self):
        with self.lock:
            if self.live:
                self._add("\x00END")
            self.live, self.waiting = False, False
            self.lock.notify_all()

    def _add(self, text):
        self.n += 1
        self.chunks.append((self.n, text))
        del self.chunks[:-400]

    def write(self, s):
        with self.lock:
            self._add(s)
            if self.live:
                self.lock.notify_all()

    def ask(self, prompt):
        import queue
        with self.lock:
            self._add(prompt)
            first = not self.live
            self.live, self.waiting = True, True
            self.lock.notify_all()
        if first and self.on_live:
            self.on_live(self.name)
        try:
            ans = self.answers.get(timeout=WAIT_ANSWER)
        except queue.Empty:
            ans = ""
        with self.lock:
            self.waiting = False
        return ans

    def answer(self, text):
        self.answers.put(str(text))

    def since(self, n, wait=0):
        end = time.time() + max(0.0, min(float(wait), 25))
        with self.lock:
            while True:
                out = [(k, t) for k, t in self.chunks if k > n] if self.live else []
                left = end - time.time()
                if out or left <= 0 or not self.live and n:
                    return {"chunks": out, "waiting": self.waiting, "live": self.live, "last": self.n}
                self.lock.wait(left)


class as_player:
    """Inside: this host thread's screen and keyboard are this player's (if he has a bridge)."""
    def __init__(self, name):
        self.bridge = BRIDGES.get(name)

    def __enter__(self):
        self.prev = getattr(_tl, "remote", None)
        if self.bridge is not None and getattr(_tl, "host", False):
            self.bridge.begin()
            _tl.remote = self.bridge
        return self

    def __exit__(self, *exc):
        if self.bridge is not None and getattr(_tl, "remote", None) is self.bridge:
            self.bridge.end()
        _tl.remote = self.prev
        return False


def narr_rng(league, g):
    """The commentary's own dice in an online world (the game's dice stay the game's)."""
    if not (league.__dict__.get("online") or {}).get("started"):
        return league.rng
    return random.Random(f"booth:{league.seed}:{league.year}:{league.week}:{g.home.school}:{g.away.school}")


def online(league):
    return bool((league.__dict__.get("online") or {}).get("started"))


def both_human(league, g):
    """Two players' programs meet: neither takes the headset (the staffs call it from the game plans)."""
    import commissioner as cm
    on = league.__dict__.get("online") or {}
    humans = {s.get("school") for s in on.get("seats", {}).values() if s.get("school")}
    if humans:
        return g.home.school in humans and g.away.school in humans
    return cm.is_player_team(league, g.home) and cm.is_player_team(league, g.away)


def signature(g):
    """A fingerprint of a played game: the score, the snaps, every player's numbers, the scoring."""
    b = g.box

    def nm(x):
        return getattr(x, "name", None) or getattr(x, "school", None) or str(x)
    stats = sorted((nm(k), sorted((kk, vv) for kk, vv in v.items() if isinstance(vv, (int, float))))
                   for k, v in (getattr(b, "stats", None) or {}).items())
    scoring = [(q, c, nm(t), str(w)) for q, c, t, w in (getattr(b, "scoring", None) or [])]
    raw = repr((g.home_score, g.away_score, getattr(b, "plays_run", 0), stats, scoring))
    return f"{g.away_score}-{g.home_score}:" + hashlib.sha256(raw.encode()).hexdigest()[:16]
