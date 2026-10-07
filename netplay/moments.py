"""
netplay/moments.py — the career's own conversations, carried to the host.

Some things a coach does aren't orders: reading and answering his inbox, the Thursday press
conference, the postgame podium. Online they happen on his copy, on the same screens as a
career. Each one is a MOMENT: the function is marked @moments.moment("name"), and on a
client it runs as always while everything typed is recorded. The host then runs the same
function as that coach (seat.acting_as), fed the same keystrokes, so the same answers land
in the official world (the questions and the mail are seeded, so they're the same there).

A moment inside a moment is part of the outer one (an inbox reply that opens the NIL screen
is one moment). While a moment runs, order capture is muted: its effects travel with it.
"""
import functools

from netplay import capture, replay

REGISTRY = {}
_S = {"items": [], "depth": 0, "hold": False}
ON_DONE = [None]                 # a client hands finished moments to the host right away (lobby)


def recording(league):
    return bool(league.__dict__.get("online_client")) and capture.enabled() and not _S["depth"]


def moment(name):
    def deco(fn):
        REGISTRY[name] = fn

        @functools.wraps(fn)
        def wrapper(league, *args, **kw):
            if not recording(league):
                return fn(league, *args, **kw)
            try:
                refs = {"a": [encode(league, a) for a in args], "k": {k: encode(league, v) for k, v in kw.items()}}
            except ValueError:                      # something this build can't name: stays local
                capture.note(name, "not sent")
                return fn(league, *args, **kw)
            info = {}
            _S["depth"] += 1
            try:
                with capture.muted(), replay.recording(info):
                    res = fn(league, *args, **kw)
            finally:
                _S["depth"] -= 1
            extra = None
            if name == "offseason":
                try:
                    from netplay import offseason
                    extra = {"fingerprint": offseason.fingerprint(league)}
                except Exception:
                    extra = None
            _S["items"].append([name, refs, info.get("keys", []), _game_settings(), extra])
            if ON_DONE[0] is not None and not _S["hold"]:
                ON_DONE[0](league)
            return res
        return wrapper
    return deco


def take():
    out, _S["items"] = _S["items"], []
    return out


def hold(flag):
    """Saturday: keep moments (the postgame podium) for the game report."""
    _S["hold"] = bool(flag)


def _game_settings():
    import settings
    return {k: v for k, v in settings.load().items() if isinstance(v, (str, int, float, bool, dict, list))}


# ═══ Naming things the same on both sides ═══════════════════════════════════

def encode(league, x):
    from models import Team
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, Team):
        return {"t": x.school}
    if isinstance(x, dict) and "subject" in x and "sender" in x:          # an inbox message
        import people
        box = people.inbox(league)
        for i, m in enumerate(box):
            if m is x:
                return {"m": i, "s": x["subject"][:40]}
        raise ValueError("message not in the inbox")
    if hasattr(x, "home") and hasattr(x, "away") and hasattr(x, "week"):  # a game
        return {"g": [x.week, x.home.school, x.away.school]}
    raise ValueError(f"can't name {type(x).__name__}")


def decode(league, x):
    if not isinstance(x, dict):
        return x
    if "t" in x:
        return next(t for t in league.teams if t.school == x["t"])
    if "m" in x:
        import people
        m = people.inbox(league)[int(x["m"])]
        if m["subject"][:40] != x.get("s"):
            raise ValueError("the inbox differs")
        return m
    if "g" in x:
        wk, h, a = x["g"]
        return next(g for g in league.schedule.get(wk, []) if g.home.school == h and g.away.school == a)
    raise ValueError("unreadable reference")


HOME = {"mail": "people", "read": "people", "answer": "people", "presser": "presser", "postgame": "postgame",
        "offseason": "netplay.offseason"}


def apply(league, team, items):
    """On the host: this coach's moments, in order, as him. Returns notes for the log."""
    import importlib
    from netplay import seat
    for mod in set(HOME.values()):
        importlib.import_module(mod)                # every moment registered, even on a host that never showed one
    notes = []
    with seat.acting_as(league, team):
        for item in items or []:
            try:
                name, refs, keys, st = item[:4]
                extra = item[4] if len(item) > 4 else None
                fn = REGISTRY[name]
                args = [decode(league, r) for r in refs["a"]]
                kw = {k: decode(league, v) for k, v in refs["k"].items()}
                with replay.replaying(keys, st) as rp:
                    fn(league, *args, **kw)
                if rp.ran_out:
                    notes.append(f"{name}: asked for more than was typed (Enter used)")
                if name == "offseason" and extra and extra.get("fingerprint"):
                    from netplay import offseason
                    got = offseason.fingerprint(league, getattr(league, "user_team", None))
                    if got != extra["fingerprint"]:
                        notes.append(f"{name}: team-state fingerprint differs ({extra['fingerprint']} != {got})")
            except Exception as e:                  # noqa: BLE001 — one bad moment never stops the week
                notes.append(f"{item[0] if item else '?'}: skipped ({type(e).__name__}: {e})")
    return notes
