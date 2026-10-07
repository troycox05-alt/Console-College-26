"""
orders.py — Commissioner Mode orders: the codes players submit, and what they do.

A player's decisions for one cycle travel as a single line of text, an ORDER CODE:

    CC1.<payload>.<signature>

  payload    base64url( zlib( JSON ) ): league id, team, cycle number, and the orders
  signature  HMAC-SHA256 over "CC1.<payload>" with that team's secret, first 16 bytes

The secret lives only in the save (and, from Phase 3, inside that team's encrypted
website bundle), so a code can't be edited by hand, signed for another team, or
replayed in a later cycle. Releasing a team rotates its secret.

ORDER SECTIONS (Phase 2: everything a regular-season week needs)

  "rec"    recruiting
           "drop": [rid]            take recruits off the board
           "add":  [rid]            put recruits on the board (40 max)
           "q":    [[rid, action, rule, n, pitch], ...]   the standing-orders queue, in order
                    action: evaluate contact offer position_coach campus_visit in_home close
                    rule:   once weekly biweekly until weeks   (n = how many weeks, for "weeks")
                    pitch:  auto, or one of the recruiting priorities
           "auto": {"OC": [on, hours], "DC": [on, hours]}   coordinators work their side
           "ov":   [[rid, week]]    official visit at your home game that week
           "nil":  [[rid, dollars]] NIL offer (0 withdraws)
           "prom": [[rid, kind]]    a promise: start / play / develop
           "pwo":  [rid]            preferred walk-on invite (Week 8 on)
           "now":  [[rid, action, pitch]]   an action done right away from his card (pitch "-" = generic)
           "camp": [rid]            the summer camp invite list (once a summer)
           "acts": [[kind, rid, ...]]   now / ov / nil / prom / pwo moves, in the order they were made
                                    (online play: a visit can depend on the NIL offer before it)
  "depth"  {"QB": [pid, ...], "RB": "staff", ...}   your order at a position, or hand it back
  "plan"   {"focus": practice focus or "staff", "off": key or "film", "def": key or "film",
            "script": 0/1}
  "calls"  {"off": "HC"|"OC", "def": "HC"|"DC"}     who calls plays
  "coach"  {"tree": [[perk, group]], "dev": [[key, points]]}   skill-tree perks and coach development
  "ans"    reserved: answers to Commissioner Inbox items (Phase 4-5)

rid / pid are permanent player ids (records.pid): a recruit keeps his id when he signs.

STANDING ORDERS: the queue, autopilot, depth chart, game plan and play-calling stay in force
until a later code replaces them. One-time moves (board changes, visits, NIL, promises,
walk-ons) happen when the code is imported.
"""
import base64
import hashlib
import hmac
import json
import zlib

PREFIX = "CC1"
VERSION = 1
SIG_BYTES = 16
MAX_QUEUE = 80
BOARD_MAX = 40
ACT_KINDS = ("now", "ov", "nil", "prom", "pwo")
SECTIONS = ("rec", "depth", "plan", "calls", "formations", "retain", "jobs", "staff", "money", "nil", "portal", "roster", "spring", "coach", "ans")


class CodeError(Exception):
    """A code that can't be accepted at all. The message is shown on the import report."""


# ═══ Ids ════════════════════════════════════════════════════════════════════

def pid(league, player):
    import records
    return records.pid(league, player)


def ensure_ids(league):
    """Give every roster player and every recruit a permanent id, in a fixed order, so the
    ids the website shows are the ids the next import reads."""
    for t in league.teams:
        for p in t.roster:
            pid(league, p)
    for r in league.recruiting.pool:
        pid(league, r.player)


def recruit_map(league):
    return {pid(league, r.player): r for r in league.recruiting.pool}


def roster_map(league, team):
    return {pid(league, p): p for p in team.roster}


# ═══ The codec ══════════════════════════════════════════════════════════════

def _b64e(b):
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(secret_hex, text):
    return _b64e(hmac.new(bytes.fromhex(secret_hex), text.encode("ascii"), hashlib.sha256).digest()[:SIG_BYTES])


def encode(league_id, school, cycle, orders, secret_hex):
    """Build a signed code. (The website does the same thing in the browser.)"""
    payload = {"v": VERSION, "l": league_id, "t": school, "c": int(cycle), "o": orders}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = _b64e(zlib.compress(raw, 9))
    head = f"{PREFIX}.{body}"
    return f"{head}.{_sign(secret_hex, head)}"


def peek(code):
    """Read a code's payload WITHOUT trusting it (no signature check). Raises CodeError."""
    code = "".join(str(code or "").split())                 # pasted with line breaks or spaces
    parts = code.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        raise CodeError("not a Console College order code")
    try:
        payload = json.loads(zlib.decompress(_b64d(parts[1])).decode("utf-8"))
    except Exception:                                   # noqa: BLE001 — any decode failure means a damaged code
        raise CodeError("damaged code: it can't be read (was part of it cut off?)") from None
    if not isinstance(payload, dict) or not {"l", "t", "c", "o"} <= set(payload):
        raise CodeError("damaged code: pieces are missing")
    return code, parts, payload


def verify(league, code):
    """Check a code against this league. Returns (team, payload). Raises CodeError with the reason."""
    import commissioner as cm
    code, parts, payload = peek(code)
    st = cm.state(league)
    if payload.get("v", 0) > VERSION:
        raise CodeError("made by a newer website than this game understands")
    if payload["l"] != st["league_id"]:
        raise CodeError("made for a different league")
    team = next((t for t in league.teams if t.school == payload["t"]), None)
    if team is None:
        raise CodeError(f"unknown program '{payload['t']}'")
    row = cm.team_row(league, team)
    if not row.get("owner"):
        raise CodeError(f"{team.school} is a CPU team; it has no player to take orders from")
    expected = _sign(row["secret"], f"{parts[0]}.{parts[1]}")
    if not hmac.compare_digest(expected, parts[2]):
        raise CodeError("signature doesn't match: the code was edited, or it was made for another team "
                        "or a previous owner")
    want = st["cycle"]["n"] + 1
    if int(payload["c"]) != want:
        when = "an earlier" if int(payload["c"]) < want else "a later"
        raise CodeError(f"made for cycle {payload['c']} ({when} cycle); this cycle is {want}")
    if not isinstance(payload["o"], dict):
        raise CodeError("damaged code: the orders aren't readable")
    return team, payload


# ═══ Validation ═════════════════════════════════════════════════════════════

def _int(v, lo=None, hi=None):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    if lo is not None and v < lo:
        return None
    if hi is not None and v > hi:
        return None
    return v


def validate(league, team, orders):
    """(clean orders, warnings). Bad items are dropped with a warning; the rest stands."""
    clean, warn = {}, []
    if not isinstance(orders, dict):
        return {}, ["orders weren't a list of sections; nothing applied"]
    for k in orders:
        if k not in SECTIONS:
            warn.append(f"unknown section '{k}' ignored")
    if "rec" in orders:
        sec, w = _v_rec(league, team, orders["rec"])
        warn += [f"recruiting: {x}" for x in w]
        if sec:
            clean["rec"] = sec
    if "depth" in orders:
        moves = orders.get("roster", {}).get("move") if isinstance(orders.get("roster"), dict) else None
        sec, w = _v_depth(league, team, orders["depth"], moves)
        warn += [f"depth chart: {x}" for x in w]
        if sec:
            clean["depth"] = sec
    if "plan" in orders:
        sec, w = _v_plan(orders["plan"])
        warn += [f"game plan: {x}" for x in w]
        if sec:
            clean["plan"] = sec
    if "calls" in orders:
        sec, w = _v_calls(team, orders["calls"])
        warn += [f"play-calling: {x}" for x in w]
        if sec:
            clean["calls"] = sec
    if "formations" in orders:
        sec, w = _v_formations(league, team, orders["formations"])
        warn += [f"formation subs: {x}" for x in w]
        if sec is not None:
            clean["formations"] = sec
    if "retain" in orders:
        sec, w = _v_retain(league, team, orders["retain"])
        warn += [f"retention: {x}" for x in w]
        if sec is not None:
            clean["retain"] = sec
    if "jobs" in orders:
        sec, w = _v_jobs(league, team, orders["jobs"])
        warn += [f"jobs: {x}" for x in w]
        if sec is not None:
            clean["jobs"] = sec
    if "coach" in orders:
        sec, w = _v_coach(orders["coach"])
        warn += [f"coach: {x}" for x in w]
        if sec:
            clean["coach"] = sec
    for key, fn in (("staff", _v_staff), ("money", _v_money), ("nil", _v_nil), ("portal", _v_portal), ("roster", _v_roster),
                    ("spring", _v_spring)):
        if key in orders:
            sec, w = fn(league, team, orders[key])
            warn += [f"{key}: {x}" for x in w]
            if sec is not None:
                clean[key] = sec
    if "ans" in orders and isinstance(orders["ans"], dict):
        clean["ans"] = {str(k): str(v) for k, v in orders["ans"].items()}
    return clean, warn


def _v_rec(league, team, sec):
    import recruit_plus
    from recruiting_data import ACTIONS, PRIORITIES
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    rmap = recruit_map(league)
    out, warn = {}, []

    def rec(rid, what):
        r = rmap.get(_int(rid))
        if r is None:
            warn.append(f"{what}: recruit #{rid} isn't in this class")
        elif r.signed:
            warn.append(f"{what}: {r.player.name} has already signed")
            return None
        return r

    for key in ("drop", "add", "pwo"):
        if key in sec:
            ids = []
            for rid in (sec[key] or [])[:BOARD_MAX * 2]:
                r = rec(rid, {"drop": "drop", "add": "add to board", "pwo": "walk-on"}[key])
                if r is not None and _int(rid) not in ids:
                    ids.append(_int(rid))
            out[key] = ids
    if "q" in sec:
        q = []
        for item in (sec["q"] or [])[:MAX_QUEUE]:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                warn.append("queue: an order wasn't readable")
                continue
            rid, act = item[0], str(item[1])
            rule = str(item[2]) if len(item) > 2 else "weekly"
            n = _int(item[3] if len(item) > 3 else 0, 0, 20) or 0
            pitch = str(item[4]) if len(item) > 4 else "auto"
            r = rec(rid, "queue")
            if r is None:
                continue
            if act not in ACTIONS:
                warn.append(f"queue: '{act}' isn't a recruiting action ({r.player.name})")
                continue
            if rule not in recruit_plus.QUEUE_RULES:
                warn.append(f"queue: '{rule}' isn't a repeat rule; using weekly ({r.player.name})")
                rule = "weekly"
            if rule == "weeks" and n < 1:
                n = 1
            if pitch != "auto" and pitch not in PRIORITIES:
                warn.append(f"queue: unknown pitch '{pitch}'; using the best known ({r.player.name})")
                pitch = "auto"
            q.append([_int(rid), act, rule, n, pitch])
        if len(sec["q"] or []) > MAX_QUEUE:
            warn.append(f"queue: only the first {MAX_QUEUE} orders are kept")
        out["q"] = q
    if "now" in sec:
        now = []
        for item in (sec["now"] or [])[:MAX_QUEUE]:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                warn.append("action: not readable")
                continue
            r = rec(item[0], "action")
            if r is None:
                continue
            act, pitch = str(item[1]), str(item[2]) if len(item) > 2 else "auto"
            if act not in ACTIONS:
                warn.append(f"action: '{act}' isn't a recruiting action ({r.player.name})")
                continue
            if pitch not in ("auto", "-") and pitch not in PRIORITIES:
                pitch = "auto"
            now.append([_int(item[0]), act, pitch])
        out["now"] = now
    if "camp" in sec:
        camp = []
        for rid in (sec["camp"] or [])[:recruit_plus.CAMP_MAX]:
            if rec(rid, "camp") is not None and _int(rid) not in camp:
                camp.append(_int(rid))
        out["camp"] = camp
    if "auto" in sec and isinstance(sec["auto"], dict):
        auto = {}
        for role in ("OC", "DC"):
            v = sec["auto"].get(role)
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                auto[role] = [bool(v[0]), _int(v[1], 0, 60) or 0]
        out["auto"] = auto
    if "ov" in sec:
        ov = []
        for item in (sec["ov"] or [])[:20]:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and rec(item[0], "official visit") is not None:
                wk = _int(item[1], 1, 13)
                if wk is None:
                    warn.append(f"official visit: week {item[1]} isn't a regular-season week")
                    continue
                ov.append([_int(item[0]), wk])
        out["ov"] = ov
    if "nil" in sec:
        nil = []
        for item in (sec["nil"] or [])[:40]:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and rec(item[0], "NIL") is not None:
                amt = _int(item[1], 0, 50_000_000)
                if amt is None:
                    warn.append(f"NIL: '{item[1]}' isn't an amount")
                    continue
                nil.append([_int(item[0]), amt])
        out["nil"] = nil
    if "prom" in sec:
        import promises
        prom = []
        for item in (sec["prom"] or [])[:10]:
            if isinstance(item, (list, tuple)) and len(item) >= 2 and rec(item[0], "promise") is not None:
                if str(item[1]) not in promises.KINDS:
                    warn.append(f"promise: '{item[1]}' isn't a kind of promise (start, play, develop)")
                    continue
                prom.append([_int(item[0]), str(item[1])])
        out["prom"] = prom
    if "acts" in sec:
        acts = []
        for item in (sec["acts"] or [])[:MAX_QUEUE]:
            if not isinstance(item, (list, tuple)) or len(item) < 2 or item[0] not in ACT_KINDS:
                warn.append(f"move {item!r} isn't readable")
                continue
            kind = item[0]
            one, w = _v_rec(league, team, {kind: [item[1]] if kind == "pwo" else [list(item[1:])]})
            warn += w
            if one.get(kind):
                got = one[kind][0]
                acts.append([kind] + (got if isinstance(got, list) else [got]))
        out["acts"] = acts
    return out, warn


def _v_depth(league, team, sec, moves=None):
    """moves: this same code's position changes ([pid, pos]); they're applied first."""
    from models import POSITIONS
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    roster = roster_map(league, team)
    moving = {}
    for m in moves or []:
        if isinstance(m, (list, tuple)) and len(m) == 2:
            moving[_int(m[0])] = m[1]
    out, warn = {}, []
    for pos, v in sec.items():
        if pos not in POSITIONS:
            warn.append(f"'{pos}' isn't a position")
            continue
        if v == "staff" or v is None or v == []:
            out[pos] = "staff"
            continue
        if not isinstance(v, (list, tuple)):
            warn.append(f"{pos}: not readable")
            continue
        ids, seen = [], set()
        for x in v:
            p = roster.get(_int(x))
            if p is None:
                warn.append(f"{pos}: player #{x} isn't on your roster")
                continue
            if moving.get(_int(x), p.position) != pos:
                warn.append(f"{pos}: {p.name} plays {p.position} (position changes happen in roster week)")
                continue
            if id(p) in seen:
                continue
            seen.add(id(p))
            ids.append(_int(x))
        if ids:
            out[pos] = ids
    return out, warn


def _v_plan(sec):
    import sideline
    import week
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out, warn = {}, []
    f = sec.get("focus", "staff")
    if f != "staff" and f not in week.FOCUS:
        warn.append(f"'{f}' isn't a practice focus; the staff's call instead")
        f = "staff"
    o = sec.get("off", "film")
    if o != "film" and o not in sideline.OFF_KEYS:
        warn.append(f"'{o}' isn't an offensive key; the film's read instead")
        o = "film"
    d = sec.get("def", "film")
    if d != "film" and d not in sideline.DEF_KEYS:
        warn.append(f"'{d}' isn't a defensive key; the film's read instead")
        d = "film"
    out.update(focus=f, off=o, **{"def": d}, script=bool(sec.get("script")))
    return out, warn


def _v_calls(team, sec):
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out, warn = {}, []
    for side, coord in (("off", "OC"), ("def", "DC")):
        v = sec.get(side)
        if v is None:
            continue
        if v not in ("HC", coord):
            warn.append(f"{side}: '{v}' should be HC or {coord}")
            continue
        if v == coord and getattr(team, "oc" if coord == "OC" else "dc", None) is None:
            warn.append(f"no {coord} on staff, so you call the {'offense' if side == 'off' else 'defense'}")
            v = "HC"
        out[side] = v
    return out, warn


def _v_formations(league, team, sec):
    import formation_subs
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    roster = roster_map(league, team)
    out, warn = {"personnel": {}, "plays": {}}, []
    for bucket in ("personnel", "plays"):
        src = sec.get(bucket) or {}
        if not isinstance(src, dict):
            continue
        for key, mp in src.items():
            if bucket == "personnel" and str(key) not in formation_subs.PACKAGES:
                continue
            if not isinstance(mp, dict):
                continue
            good = {}
            for role, raw in mp.items():
                p = roster.get(_int(raw))
                if role not in formation_subs.ROLES or p is None:
                    warn.append(f"{key}/{role}: player is not on your roster")
                    continue
                if p.position not in formation_subs.ROLE_POS.get(role, ()):
                    warn.append(f"{key}/{role}: {p.name} does not fit that role")
                    continue
                good[role] = _int(raw)
            if good:
                out[bucket][str(key)] = good
    return out, warn


def _v_retain(league, team, sec):
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    roster = roster_map(league, team)
    out, warn = {}, []
    for raw, row in sec.items():
        p = roster.get(_int(raw))
        if p is None or not isinstance(row, dict):
            continue
        clean = {}
        if isinstance(row.get("role_promise"), dict):
            clean["role_promise"] = dict(row["role_promise"])
        if isinstance(row.get("retention_conversation"), dict):
            clean["retention_conversation"] = dict(row["retention_conversation"])
        if "retention_hold" in row:
            try: clean["retention_hold"] = max(.25, min(2.5, float(row["retention_hold"])))
            except (TypeError, ValueError): pass
        if "morale" in row:
            try: clean["morale"] = max(0.0, min(100.0, float(row["morale"])))
            except (TypeError, ValueError): pass
        if "redshirt_plan" in row:
            y = _int(row["redshirt_plan"], 1900, 3000)
            if y is not None: clean["redshirt_plan"] = y
        out[_int(raw)] = clean
    return out, warn


def _v_coach(sec):
    """{"tree": [[perk, group or None]], "dev": [[key, points]]}"""
    import coach_dev
    import skills
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out, warn = {}, []
    tree = []
    for item in (sec.get("tree") or [])[:12]:
        if isinstance(item, (list, tuple)) and item and item[0] in skills.PERKS:
            group = item[1] if len(item) > 1 and item[1] in skills.GROUPS else None
            tree.append([item[0], group])
        else:
            warn.append(f"tree: {item!r} isn't a perk")
    dev = []
    for item in (sec.get("dev") or [])[:20]:
        n = _int(item[1], 1, 50) if isinstance(item, (list, tuple)) and len(item) == 2 else None
        if n and item[0] in coach_dev.KEYS:
            dev.append([item[0], n])
        else:
            warn.append(f"development: {item!r} ignored")
    if tree:
        out["tree"] = tree
    if dev:
        out["dev"] = dev
    return out, warn


def _v_jobs(league, team, sec):
    """{"want": [up to 3 program ids, best first], "extend": "yes" | "no" | "ask"}"""
    import knowledge
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    by_id = {knowledge.slug(t.school): t.school for t in league.teams}
    want, warn = [], []
    for x in (sec.get("want") or [])[:3]:
        school = by_id.get(str(x))
        if school is None:
            warn.append(f"'{x}' isn't a program")
        elif school == team.school:
            warn.append("that's your own job")
        elif school not in want:
            want.append(school)
    if len(sec.get("want") or []) > 3:
        warn.append("only the first three jobs count")
    ext = sec.get("extend", "ask")
    if ext not in ("yes", "no", "ask"):
        warn.append(f"extend '{ext}' should be yes, no or ask")
        ext = "ask"
    return {"want": want, "extend": ext}, warn


STAFF_KEYS = ("OC", "DC", "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")


def _v_staff(league, team, sec):
    """{"fire": [chairs], "lists": {chair: {"names": [...10], "max": {...}} | {"names": [...], "premium": 0|15|30}}}"""
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out, warn = {"fire": [], "lists": {}}, []
    for k in sec.get("fire") or []:
        if k not in STAFF_KEYS:
            warn.append(f"'{k}' isn't a staff chair")
        elif not league.season_complete:
            warn.append(f"letting a coach go waits for the offseason ({k} kept)")
        else:
            out["fire"].append(k)
    for k, v in (sec.get("lists") or {}).items():
        if k not in STAFF_KEYS or not isinstance(v, dict):
            warn.append(f"list for '{k}' ignored")
            continue
        names = [str(x)[:60] for x in (v.get("names") or [])][:10]
        if k in ("OC", "DC"):
            m = v.get("max") or {}
            out["lists"][k] = {"names": names, "max": {"salary": _int(m.get("salary"), 0, 20_000_000) or 0,
                                                       "years": _int(m.get("years"), 1, 6) or 3,
                                                       "calls": 1 if m.get("calls") else 0, "title": 1 if m.get("title") else 0,
                                                       "out": 1 if m.get("out") else 0}}
        else:
            prem = _int(v.get("premium"), 0, 30) or 0
            out["lists"][k] = {"names": names, "premium": 30 if prem >= 30 else 15 if prem >= 15 else 0}
    return out, warn


def _v_money(league, team, sec):
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out, warn = {}, []
    if sec.get("facility") in ("recruiting", "training"):
        out["facility"] = sec["facility"]
    elif sec.get("facility"):
        warn.append(f"facility '{sec['facility']}' should be recruiting or training")
    roster = roster_map(league, team)
    out["restructure"] = [x for x in (sec.get("restructure") or [])[:6] if x in roster]
    out["coordcut"] = [x for x in (sec.get("coordcut") or []) if x in ("OC", "DC")]
    out["poscut"] = [x for x in (sec.get("poscut") or []) if x in STAFF_KEYS[2:]]
    out["stretch"] = bool(sec.get("stretch"))
    return out, warn


def _v_nil(league, team, sec):
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    roster = roster_map(league, team)
    out, warn = {"nil": [], "draft": []}, []
    for item in (sec.get("nil") or [])[:10]:
        if isinstance(item, list) and len(item) == 2 and item[0] in roster and item[1] in ("pay", "counter", "refuse"):
            out["nil"].append([item[0], item[1]])
        else:
            warn.append(f"NIL answer {item!r} ignored")
    for item in (sec.get("draft") or [])[:12]:
        if isinstance(item, list) and len(item) == 2 and item[0] in roster and item[1] in ("stay", "go", "neutral"):
            out["draft"].append([item[0], item[1]])
        else:
            warn.append(f"draft answer {item!r} ignored")
    return out, warn


def _pairs(items, ok, limit):
    out = []
    for x in (items or [])[:limit]:
        if isinstance(x, list) and len(x) == 2 and ok(x):
            out.append([x[0], x[1]])
    return out


def _v_portal(league, team, sec):
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    out = {"keep": _pairs(sec.get("keep"), lambda x: isinstance(x[0], int) and isinstance(x[1], (int, float)), 6),
           "offer": _pairs(sec.get("offer"), lambda x: isinstance(x[0], int) and isinstance(x[1], (int, float)), 8)}
    return out, []


def _v_roster(league, team, sec):
    from models import POSITIONS
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    roster = roster_map(league, team)
    out = {"move": _pairs(sec.get("move"), lambda x: x[0] in roster and x[1] in POSITIONS, 8),
           "cut": [x for x in (sec.get("cut") or [])[:15] if x in roster]}
    warn = [] if len(out["cut"]) == len(sec.get("cut") or []) else ["some cuts weren't on your roster"]
    return out, warn


def _v_spring(league, team, sec):
    import comm_offseason
    from models import POSITIONS
    if not isinstance(sec, dict):
        return None, ["not readable; skipped"]
    emp = sec.get("emphasis") if sec.get("emphasis") in comm_offseason.EMPHASES else "fundamentals"
    return {"emphasis": emp, "focus": [p for p in (sec.get("focus") or [])[:3] if p in POSITIONS]}, []


# ═══ Applying ═══════════════════════════════════════════════════════════════

def standing(league, team):
    import commissioner as cm
    return cm.team_row(league, team).setdefault("orders", {})


def apply(league, team, clean):
    """Put a team's validated orders into the world. Returns lines describing what happened."""
    lines = []
    st = standing(league, team)
    if "rec" in clean:
        lines += _apply_rec(league, team, clean["rec"])
    if "roster" in clean:                                       # position changes before the depth chart that uses them
        import comm_offseason
        lines += ["roster: " + x for x in comm_offseason.roster_orders(league, team, clean["roster"])]
    if "depth" in clean:
        locks = dict(st.get("depth") or {})
        for pos, v in clean["depth"].items():
            if v == "staff":
                locks.pop(pos, None)
            else:
                locks[pos] = v
        st["depth"] = locks
        apply_depth(league, team)
        lines.append(f"depth chart: {len(locks)} position{'s' if len(locks) != 1 else ''} set by you")
    if "plan" in clean:
        st["plan"] = dict(clean["plan"])
        lines.append("game plan: " + describe_plan(clean["plan"]))
    if "calls" in clean:
        calls = dict(st.get("calls") or {})
        calls.update(clean["calls"])
        st["calls"] = calls
        apply_calls(league, team)
        lines.append(f"play-calling: offense {calls.get('off', '—')}, defense {calls.get('def', '—')}")
    if "formations" in clean:
        roster = roster_map(league, team)
        fs = {"personnel": {}, "plays": {}}
        for bucket in ("personnel", "plays"):
            for key, mp in clean["formations"].get(bucket, {}).items():
                fs[bucket][key] = {role: roster[pid] for role, pid in mp.items() if pid in roster}
        team.formation_subs = fs
        lines.append("formation subs: saved packages applied")
    if "retain" in clean:
        roster = roster_map(league, team)
        # This section is the client's complete standing state for these coach-managed fields.
        for pid_, p in roster.items():
            row = clean["retain"].get(pid_, {})
            for k in ("role_promise", "retention_conversation", "retention_hold", "redshirt_plan"):
                if k in row:
                    setattr(p, k, row[k])
                else:
                    p.__dict__.pop(k, None)
            if "morale" in row:
                p.morale = row["morale"]
        lines.append("retention/redshirt plans: updated")
    if "jobs" in clean:
        st["jobs"] = dict(clean["jobs"])
        lines.append("jobs: " + (", ".join(clean["jobs"]["want"]) or "not looking")
                     + f"; extension offers: {clean['jobs']['extend']}")
    if "staff" in clean:
        import member_offseason as mo
        cur = st.setdefault("staff", {"lists": {}})
        cur.setdefault("lists", {}).update(clean["staff"]["lists"])
        if clean["staff"]["fire"]:
            cur["fire"] = list(dict.fromkeys(clean["staff"]["fire"]))     # carried out when the staff carousel opens
            lines.append("staff: letting go when the carousel opens: " + ", ".join(cur["fire"]))
        if clean["staff"]["lists"]:
            lines.append("staff: search lists for " + ", ".join(sorted(clean["staff"]["lists"])))
    if "money" in clean:
        import member_offseason as mo
        lines += ["money: " + x for x in mo.money(league, team, clean["money"])]
    if "nil" in clean:
        import member_offseason as mo
        lines += ["season end: " + x for x in mo.answer_nil(league, team, clean["nil"])]
    if "portal" in clean:
        import comm_offseason
        lines += ["portal: " + x for x in comm_offseason.portal_orders(league, team, clean["portal"])]
    if "spring" in clean:
        st["spring"] = dict(clean["spring"])
        lines.append(f"spring: {clean['spring']['emphasis']}" + (f", focus {', '.join(clean['spring']['focus'])}" if clean["spring"]["focus"] else ""))
    if "coach" in clean and team.coach is not None:
        import coach_dev
        import skills
        for k, group in clean["coach"].get("tree", []):
            ok, text = skills.buy(league, team.coach, k, group)
            lines.append(("skill tree: " if ok else "skill tree refused: ") + str(text))
        for k, n in clean["coach"].get("dev", []):
            got, _, text = coach_dev.buy(league, team.coach, k, n)
            lines.append(f"development: {text}")
    if "ans" in clean:
        st.setdefault("answers", {}).update(clean["ans"])
    return lines


def _apply_rec(league, team, sec):
    import recruit_plus
    cycle = league.recruiting
    rmap = recruit_map(league)
    lines = []
    for rid in sec.get("drop", []):
        r = rmap.get(rid)
        if r is not None and r in team.recruiting_targets:
            cycle.drop_target(team, r)
    for rid in sec.get("add", []):
        r = rmap.get(rid)
        if r is not None and not cycle.add_target(team, r) and r not in team.recruiting_targets:
            lines.append(f"board full (40): {r.player.name} not added")
    if "q" in sec:
        q = recruit_plus.queue(cycle, team)
        q.clear()
        for rid, act, rule, n, pitch in sec["q"]:
            r = rmap.get(rid)
            if r is not None:
                recruit_plus.add_order(cycle, team, r, act, rule=rule, n=n, pitch=pitch)
        lines.append(f"standing orders: {len(q)} in the queue")
    acts = sec.get("acts", [])
    # NIL, a promise or a visit needs a scholarship offer. If this same code queues the offer,
    # make it now (it costs this week's hours, as it would at the top of the queue).
    needs = {rid for key in ("nil", "prom", "ov") for rid, *_ in sec.get(key, [])}
    needs |= {a[1] for a in acts if a[0] in ("nil", "prom", "ov")}
    queued = {rid for rid, act, *_ in sec.get("q", []) if act == "offer"}
    offered_first = {a[1] for a in acts if a[0] == "now" and a[2] == "offer"}
    for rid in sorted((needs & queued) - offered_first):
        r = rmap.get(rid)
        if r is not None and team not in r.offers and not r.signed:
            ok, msg = cycle.apply_action(team, r, "offer", pitch="auto", source="orders")
            if ok:
                lines.append(f"offer made now (your NIL/promise/visit needed it): {r.player.name}")
    if "auto" in sec:
        ap = recruit_plus.autopilot(cycle, team)
        for role, (on, hours) in sec["auto"].items():
            ap[role] = {"on": bool(on), "hours": int(hours)}
    for kind in ("now", "ov", "nil", "prom", "pwo"):
        for item in sec.get(kind, []):
            lines += _one_move(league, team, rmap, kind, item if isinstance(item, list) else [item])
    for a in acts:                                               # in the order the coach made them
        lines += _one_move(league, team, rmap, a[0], a[1:])
    if sec.get("camp"):
        picks = [rmap[rid] for rid in sec["camp"] if rid in rmap]
        out, msg = recruit_plus.run_camp(cycle, team, picks)
        lines.append(f"camp: {len(out)} came through" if out else f"camp: {msg}")
    return lines


def _one_move(league, team, rmap, kind, args):
    """One recruiting move made during the week: an action, a visit, NIL, a promise, a walk-on."""
    import finance
    import promises
    import recruit_plus
    cycle = league.recruiting
    r = rmap.get(args[0])
    if r is None:
        return []
    if kind == "now":
        ok, msg = cycle.apply_action(team, r, args[1], pitch=None if args[2] == "-" else args[2])
        if ok and r not in team.recruiting_targets:
            cycle.add_target(team, r)                   # working a recruit puts him on your board
        return [("recruiting: " if ok else "recruiting refused: ") + msg]
    if kind == "ov":
        game = next((g for g in league.schedule.get(args[1], []) if g.home is team and not g.played), None)
        if game is None:
            return [f"official visit: no home game left in Week {args[1]} for {r.player.name}"]
        ok, msg = recruit_plus.invite(cycle, team, r, game)
        return [("official visit: " if ok else "official visit refused: ") + msg]
    if kind == "nil":
        ok, msg = finance.make_offer(cycle, team, r, args[1])
        return [("NIL: " if ok else "NIL refused: ") + msg]
    if kind == "prom":
        ok, msg = promises.make(league, team, r, args[1])
        return [("promise: " if ok else "promise refused: ") + msg]
    if kind == "pwo":
        ok, msg = recruit_plus.add_pwo(cycle, team, r)
        return [("walk-on: " if ok else "walk-on refused: ") + msg]
    return []


def apply_depth(league, team):
    """Put the player's locked positions on top of whatever the staff sorted."""
    locks = standing(league, team).get("depth") or {}
    if not locks:
        return
    roster = roster_map(league, team)
    order = team.__dict__.setdefault("depth_order", {})
    for pos, ids in locks.items():
        mine = [roster[i] for i in ids if i in roster and roster[i].position == pos]
        rest = [p for p in order.get(pos, []) if p not in mine and p in team.roster and p.position == pos]
        extra = sorted((p for p in team.roster if p.position == pos and p not in mine and p not in rest),
                       key=lambda p: -p.overall)
        order[pos] = mine + rest + extra


def apply_calls(league, team):
    calls = standing(league, team).get("calls") or {}
    if not calls:
        return
    import staff
    off = calls.get("off")
    dfn = calls.get("def")
    if off == "OC" and getattr(team, "oc", None) is None:
        off = "HC"
    if dfn == "DC" and getattr(team, "dc", None) is None:
        dfn = "HC"
    staff.set_calls(team, off=off, df=dfn)


def describe_plan(plan):
    import sideline
    import week
    f = "the staff's focus" if plan.get("focus") == "staff" else week.FOCUS[plan["focus"]][0]
    o = "the film's read" if plan.get("off") == "film" else sideline.OFF_KEYS[plan["off"]][0]
    d = "the film's read" if plan.get("def") == "film" else sideline.DEF_KEYS[plan["def"]][0]
    return f"{f}; offense: {o}; defense: {d}" + ("; openers scripted" if plan.get("script") else "")


def apply_plan(league, team):
    """Before the week's games: the team's standing game plan against this week's opponent.
    No plan on file = Balanced practice and the film's read."""
    import sideline
    import week
    g = week.next_game(league, team)
    if g is None:
        return
    plan = standing(league, team).get("plan") or {"focus": "balanced", "off": "film", "def": "film", "script": False}
    r = {"focus": plan.get("focus", "balanced"), "off": plan.get("off", "film"), "def": plan.get("def", "film"),
         "script": plan.get("script", False), "name": "orders"}
    focus, gp = week.routine_setup(league, team, g, r)
    sideline.set_plan(team, league.year, league.week + 1, gp["off"], gp["def"], gp["script"])
    week.apply_prep(league, team, focus, silent=True, routine="orders")
