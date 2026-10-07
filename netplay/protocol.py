"""
netplay/protocol.py — what host and clients say to each other (Online LAN mode).

Plain HTTP on the home network, JSON both ways, except the world itself, which travels as
a compressed snapshot (see sync.py). One host, any number of clients; the host's world is
the only truth.

  POST /join    {name, code, game_version, proto, universe_hash, world?, token?, school?}
                -> {token, seat, world, rev}  or  {error}
  GET  /world?since=<rev>          -> the snapshot (application/octet-stream, X-Rev header),
                                      or 204 when the client is already up to date
  GET  /status                     -> {world, rev, game_version, universe, year, week, seats: [...]}
  GET  /programs                   -> {programs: [{school, conf, prestige, coach, interim, taken}], started}
  POST /seat    {token, school, coach: "adopt"|"new", form?} -> {ok, school, coach}   (pick a program)
  POST /orders  {token, rev, orders} -> {ok, warnings, lines}  (orders.py sections; after START)
  POST /ready   {token, ready}     -> {ok}
  GET  /events?since=<n>&wait=<s>  -> {events: [{n, kind, ...}], last}   (long poll)

/answer and /chat arrive with Phases 4 and 7.
"""
import json
import secrets

PROTO = 1
DEFAULT_PORT = 8766
MAX_BODY = 4 * 1024 * 1024            # includes a submitted JSON box score; anything bigger is refused
MAX_WAIT = 25                         # longest a long poll is held, seconds
NAME_MAX = 24


def new_code():
    """The 4-digit join code the host reads out to the room."""
    return f"{secrets.randbelow(10000):04d}"


def new_token():
    return secrets.token_hex(16)


def dumps(obj):
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def loads(raw):
    obj = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    if not isinstance(obj, dict):
        raise ValueError("expected a JSON object")
    return obj


def clean_name(name):
    name = " ".join(str(name or "").split())[:NAME_MAX]
    return name or "Coach"


FORM_KEYS = ("first", "last", "age", "background", "offense", "defense", "fourth", "blitz")


def clean_form(form):
    """The new-coach form (the career creation answers), as plain short strings."""
    form = form if isinstance(form, dict) else {}
    return {k: str(form.get(k) or "")[:30] for k in FORM_KEYS if form.get(k) not in (None, "")}


def join_refusal(req, host):
    """Why this join can't be accepted (a sentence for the player), or None.
    host: {code, game_version, universe, universe_hash, world}. The client learns the universe
    from /status first and hashes its own file of that name (sync.universe_hash)."""
    if int(req.get("proto") or 0) != PROTO:
        return "That copy of the game speaks a different online protocol. Update both copies to the same build."
    if str(req.get("game_version")) != str(host["game_version"]):
        return (f"Version mismatch: the host runs {host['game_version']}, you run {req.get('game_version')}. "
                f"Everyone needs the same build.")
    if str(req.get("universe_hash") or "") != str(host["universe_hash"] or ""):
        if req.get("universe_hash") == "missing":
            return (f"This world is built in the '{host['universe']}' universe and that file isn't in your "
                    f"universes folder. Copy it over from the host.")
        return (f"Your copy of the '{host['universe']}' universe file is different from the host's. "
                f"Copy the host's file over yours.")
    if req.get("world") and req["world"] != host["world"]:
        return "That seat belongs to a different world. Join as a new coach instead."
    if not req.get("token") and str(req.get("code") or "").strip() != host["code"]:
        return "Wrong join code."
    return None
