"""
netplay/client.py — one player's side of an online world.

    c = Client("192.168.1.20:8766")
    c.join("Troy", code="4821", school="Auburn")     # raises JoinError with the host's reason
    league = c.fetch_world()                         # the host's world, pointed at your program
    c.post_orders(capture.take(league, league.user_team))
    c.ready(True)
    for e in c.events(wait=20): ...

The seat (token, world, host) is kept in online.json next to the game, so a player who
drops off the Wi-Fi or restarts rejoins the same seat with Client.resume().
"""
import json
import os
import time
import urllib.error
import urllib.request

from netplay import protocol, sync

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAT_FILE = os.path.join(HERE, "online.json")
TIMEOUT = 15


class JoinError(Exception):
    """The host said no (the message is the reason, ready to show)."""


class HostGone(Exception):
    """Couldn't reach the host."""


def _addr(address):
    address = str(address).strip()
    if "://" in address:
        address = address.split("://", 1)[1]
    if ":" not in address:
        address += f":{protocol.DEFAULT_PORT}"
    return "http://" + address.rstrip("/")


class Client:
    def __init__(self, address):
        self.base = _addr(address)
        self.address = self.base[len("http://"):]
        self.token = None
        self.world = None
        self.school = None
        self.name = None
        self.rev = 0                       # the rev of the world this client holds
        self.last_event = 0
        self.stats = {}                    # measured: last snapshot bytes and seconds
        self.last_results = {}             # school -> did his game come out the same on the host

    # ── plumbing ────────────────────────────────────────────────────────────
    def _call(self, method, path, body=None, timeout=TIMEOUT, raw=False):
        data = protocol.dumps(body) if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                if raw:
                    return r.status, payload, dict(r.headers)
                return protocol.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            try:
                return protocol.loads(e.read())
            except ValueError:
                return {"error": f"host answered {e.code}"}
        except (urllib.error.URLError, OSError) as e:
            raise HostGone(f"Can't reach the host at {self.address} ({getattr(e, 'reason', e)}).") from None

    # ── joining ─────────────────────────────────────────────────────────────
    def status(self):
        return self._call("GET", "/status")

    def join(self, name, code=None, school=None):
        import title
        st = self.status()
        req = {"name": name, "code": str(code or ""), "game_version": title.VERSION, "proto": protocol.PROTO,
               "universe_hash": sync.universe_hash(st.get("universe")), "school": school}
        if self.token:
            req.update(token=self.token, world=self.world)
        out = self._call("POST", "/join", req)
        if "error" in out:
            raise JoinError(out["error"])
        self.token, self.world = out["token"], out["world"]
        self.name, self.school = out["seat"]["name"], out["seat"]["school"]
        self.save_seat()
        return out

    def save_seat(self):
        seats = _read_seats()
        seats[self.address] = {"token": self.token, "world": self.world, "name": self.name, "school": self.school}
        try:
            with open(SEAT_FILE, "w", encoding="utf-8") as f:
                json.dump(seats, f, indent=1)
        except OSError:
            pass                            # not fatal: the player just joins with the code next time

    @classmethod
    def resume(cls, address):
        """A client for a host this copy has joined before (None if it hasn't)."""
        c = cls(address)
        seat = _read_seats().get(c.address)
        if not seat:
            return None
        c.token, c.world, c.name, c.school = seat["token"], seat["world"], seat.get("name"), seat.get("school")
        c.join(c.name)                      # same seat; raises JoinError if the world changed
        return c

    # ── the world ───────────────────────────────────────────────────────────
    def fetch_world(self, force=False):
        """The host's world if it's newer than ours (None if we're up to date), localized."""
        t0 = time.time()
        code, blob, headers = self._call("GET", f"/world?since={0 if force else self.rev}", raw=True, timeout=120)
        if code == 204:
            return None
        t1 = time.time()
        league = sync.load(blob)
        t2 = time.time()
        self.rev = int(headers.get("X-Rev") or 0)
        self.stats = {"bytes": len(blob), "transfer_s": round(t1 - t0, 2), "load_s": round(t2 - t1, 2)}
        mine = next((s for s in (league.__dict__.get("online") or {}).get("seats", {}).values()
                     if s.get("name") == self.name), None)
        if mine is not None and mine.get("school") != self.school:
            self.school = mine.get("school")           # your coach took another job (or lost his)
            self.save_seat()
        if self.school:
            sync.localize(league, self.school)
        return league

    def programs(self):
        return self._call("GET", "/programs")

    def pick(self, school, coach="adopt", form=None):
        """Pick a program in the lobby: coach "adopt" (the sitting coach) or "new" (form)."""
        out = self._call("POST", "/seat", {"token": self.token, "school": school, "coach": coach, "form": form})
        if "error" in out:
            raise JoinError(out["error"])
        self.school = out["school"]
        self.save_seat()
        return out

    def wait_start(self, wait=20):
        """Blocks up to `wait` seconds; True once the host has started the world."""
        for e in self.events(wait=wait):
            if e["kind"] == "start":
                return True
        return bool(self.status().get("started"))

    def post_orders(self, orders, moments=None):
        """{ok, warnings, lines} or {error}. 'stale' means fetch the world first. moments: the
        career's conversations since the last post (netplay/moments.py), applied after the orders."""
        if not orders and not moments:
            return {"ok": True, "warnings": [], "lines": []}
        return self._call("POST", "/orders", {"token": self.token, "rev": self.rev, "orders": orders,
                                              "moments": moments or []})

    def report(self, game):
        """Your finished game: authoritative result/box score plus postgame moments."""
        out = self._call("POST", "/report", {"token": self.token, "rev": self.rev, "game": game})
        if "error" in out:
            raise JoinError(out.get("message") or out["error"])
        return out

    def screen(self, since=0, wait=0):
        return self._call("GET", f"/screen?token={self.token}&since={since}&wait={wait}", timeout=wait + TIMEOUT)

    def answer(self, text):
        return self._call("POST", "/answer", {"token": self.token, "text": text})

    def ready(self, flag=True):
        out = self._call("POST", "/ready", {"token": self.token, "ready": bool(flag)})
        if "error" in out:
            raise JoinError(out.get("message") or out["error"])
        return out

    def events(self, wait=0):
        """New events since the last call (blocks up to `wait` seconds when there are none)."""
        out = self._call("GET", f"/events?since={self.last_event}&wait={wait}", timeout=wait + TIMEOUT)
        self.last_event = out.get("last", self.last_event)
        return out.get("events", [])


def _read_seats():
    try:
        with open(SEAT_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}
