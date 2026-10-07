"""
netplay/sync.py — the world on the wire.

The host sends clients its whole league as a SNAPSHOT: pickle, then zlib. A client loads it
exactly the way a save loads (saves._after_load) and then points the one-coach screens at
its own program (localize).

SECURITY: unpickling runs code the data asks for. A client only ever loads snapshots from
the host it joined with the code, on the home network. The host never unpickles anything
a client sends (orders are JSON). Same rule as save files: only open what friends made.
"""
import pickle
import sys
import zlib

LEVEL = 6                       # zlib level: 9 is barely smaller and a lot slower on 15 MB


def snapshot(league):
    """bytes: the whole world, compressed. Gives every player and recruit his permanent id
    first, so the ids a client sends back are the ids the host reads."""
    import orders
    import saves
    orders.ensure_ids(league)
    on = league.__dict__.get("online") or {}
    seats = on.get("seats")
    if seats is not None:               # every client gets the world, nobody gets the others' tokens
        on["seats"] = {f"seat{i}": {k: v for k, v in s.items() if k in ("name", "school", "coach", "coach_name")}
                       for i, s in enumerate(seats.values(), 1)}
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, saves.RECURSION_FLOOR))
    try:
        raw = pickle.dumps(league, protocol=pickle.HIGHEST_PROTOCOL)
    finally:
        sys.setrecursionlimit(limit)
        if seats is not None:
            on["seats"] = seats
    return zlib.compress(raw, LEVEL)


def load(blob):
    """A league from snapshot bytes, with the same post-load fixes a save gets."""
    import io
    import contextlib
    import saves
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, saves.RECURSION_FLOOR))
    try:
        league = pickle.loads(zlib.decompress(blob))
    finally:
        sys.setrecursionlimit(limit)
    with contextlib.redirect_stdout(io.StringIO()):             # universe notes etc. aren't news here
        saves._after_load(league)
    return league


def world_id(league):
    """Which shared world this is: stays the same for its whole life, saved with it."""
    on = league.__dict__.setdefault("online", {})
    if not on.get("world"):
        import secrets
        on["world"] = f"W-{league.seed}-{secrets.token_hex(3)}"
    return on["world"]


def universe_name(league):
    import universe
    return str(getattr(league, "universe", None) or universe.DEFAULT)


def localize(league, school):
    """On a client: this copy is coached from `school`. The host's world is an online world
    with no single user; on the client it reads as your Coach Career, so the dashboard, inbox
    and every one-coach screen work as they always have. Nothing here goes back to the host."""
    team = next((t for t in league.teams if t.school == school), None)
    if team is None:
        return None
    league.mode = "career"
    league.user_team = team
    coach = team.coach
    if coach is not None:
        coach.is_user = True
        league.user_coach = coach
    league.__dict__["online_client"] = {"school": school}
    import career
    import portal_screens
    league.user_offer_hook = career.offer_prompt
    league.portal_hook = portal_screens.portal_window
    from netplay import seat
    seat.load_mine(league, school)               # your inbox, your hub, your log
    return team


def is_client_copy(league):
    """A client's copy of an online world: never autosaved over a single-player save."""
    return bool(league is not None and league.__dict__.get("online_client"))


def universe_hash(name):
    """A fingerprint of a universe file (both sides must hold the same one), "builtin" for the
    built-in universe, "missing" when this copy doesn't have the file."""
    import hashlib
    import universe
    if not name or name == universe.DEFAULT:
        return "builtin"
    try:
        with open(universe.path_for(name), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "missing"
