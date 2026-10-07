"""
netplay/capture.py — the order-capture seam (Online LAN mode, Phase 0).

On a client, what the player DOES has to become orders the host can apply (orders.py
sections). Two ways in, chosen per decision:

  ONE-TIME ACTIONS are recorded as they happen, in order (rec "acts": a visit can depend on
  the NIL offer made just before it), by a decorator on the function that does
  them (one line at each decision point):

      @capture.hook("rec", "acts", capture.b_nil)     # -> ["nil", rid, amount]
      def make_offer(cycle, team, recruit, amount): ...

  The build function runs only after a successful call ((ok, msg) with ok true, unless the
  hook says otherwise) and only for the team this client coaches. While a hooked function
  runs, everything inside it is muted, so the outer decision is the only thing recorded
  (an NIL offer made from inside an inbox answer is the answer, not a second order).

  STANDING STATE (the board, the queue, coordinator autopilot, the depth chart, position
  changes, the game plan, play-calling) is HARVESTED: begin() keeps a baseline when a world
  arrives, take() compares the world with it. Every screen that edits the depth chart or
  the board is covered without a hook in each one.

  OPAQUE entry points (@capture.opaque("inbox")) are decisions that travel as answers to
  host-side items (Phase 4): they mute everything inside and are noted, not sent.

Offline nothing is on: every hook is one global check and a direct call.
"""
import functools
import inspect

_S = {"on": False, "team": None, "mute": 0, "events": {}, "base": None, "seen": [], "seq": 0}


# ═══ Switching it on ════════════════════════════════════════════════════════

def begin(league, team):
    """Start capturing for this client's program. Call after every world (snapshot) loads."""
    _S.update(on=True, team=team, mute=0, events={}, seen=[])
    _S["base"] = _standing(league, team)


def stop():
    _S.update(on=False, team=None, mute=0, events={}, base=None, seen=[])


def enabled():
    return _S["on"]


def _mine(team):
    # The very object, not the school name: the host's own copy of this program (same process,
    # another league) is a different object, so the host applying orders never records them.
    return _S["on"] and not _S["mute"] and team is not None and team is _S["team"]


class _Muted:
    def __enter__(self):
        _S["mute"] += 1

    def __exit__(self, *exc):
        _S["mute"] -= 1
        return False


def muted():
    """Nothing inside is recorded: the client applying orders to its own copy, a sim, a replay."""
    return _Muted()


# ═══ Recording ══════════════════════════════════════════════════════════════

# How a repeated item combines: "buy 3 more of the same" is one line.
_MERGE = {("coach", "dev")}


def record(section, key, value):
    """Add one item to the pending orders. key None = the section is a dict to update."""
    if not _S["on"] or _S["mute"]:
        return
    _S["seq"] += 1
    sec = _S["events"].setdefault(section, {})
    if key is None:
        sec.update(value)
        return
    items = sec.setdefault(key, [])
    if (section, key) in _MERGE and items and items[-1][0] == value[0]:
        items[-1] = [value[0], items[-1][1] + value[1]]
        return
    items.append(value)


def note(kind, detail=""):
    """A decision that isn't an order yet (it will be an answer to a host item)."""
    if _S["on"]:
        _S["seen"].append((kind, detail))


def seen():
    return list(_S["seen"])


def _ok(res):
    if isinstance(res, tuple) and res:
        return bool(res[0])
    return bool(res)


def hook(section, key, build, ok=_ok):
    """Decorator: after a successful call, build(result, *args) -> (team, value) or None."""
    def deco(fn):
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(*a, **k):
            if not _S["on"] or _S["mute"]:
                return fn(*a, **k)
            _S["mute"] += 1
            try:
                res = fn(*a, **k)
            finally:
                _S["mute"] -= 1
            if ok(res):
                bound = sig.bind(*a, **k)
                bound.apply_defaults()
                got = build(res, **bound.arguments)
                if got is not None and _mine(got[0]):
                    record(section, key, got[1])
            return res
        return wrapper
    return deco


def opaque(kind):
    """Decorator: a decision answered on its own screen (inbox, podium). Everything inside is
    muted; the moment is noted for Phase 4, when it travels as an answer."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **k):
            if not _S["on"] or _S["mute"]:
                return fn(*a, **k)
            _S["mute"] += 1
            try:
                res = fn(*a, **k)
            finally:
                _S["mute"] -= 1
            note(kind, getattr(fn, "__name__", ""))
            return res
        return wrapper
    return deco


# ═══ Harvesting standing state ══════════════════════════════════════════════

def _pid(league, p):
    import records
    return records.pid(league, p)


def _depth_ids(league, team):
    """The positions this coach (or a screen) has set, as each room reads now."""
    order = team.__dict__.get("depth_order") or {}
    return {pos: [_pid(league, p) for p in team.players_at(pos)] for pos in order}


def _queue(league, team):
    import recruit_plus
    q = recruit_plus.queue(league.recruiting, team)
    return [[_pid(league, e["r"].player), e["a"], e["rule"], int(e.get("n") or 0), e.get("pitch") or "auto"] for e in q]


def _auto(league, team):
    import recruit_plus
    ap = recruit_plus.autopilot(league.recruiting, team)
    return {role: [bool(ap[role]["on"]), int(ap[role]["hours"])] for role in ("OC", "DC")}


def _plan(league, team):
    """This week's plan as an order: practice focus, both game-plan keys, scripted openers."""
    import sideline
    wk = league.week + 1
    gp = sideline.plan_of(team, league.year, wk)
    wp = getattr(team, "week_prep", None) or {}
    hs = league.__dict__.get("_hub_state") or {}
    if wp.get("year") == league.year and wp.get("week") == wk:
        focus = wp.get("focus")
    elif hs.get("yw") == (league.year, wk):
        focus = hs.get("focus")
    else:
        focus = None
    if gp is None and focus is None:
        return None
    return {"focus": focus or "staff", "off": gp["off"] if gp else "film", "def": gp["def"] if gp else "film",
            "script": bool(gp.get("script")) if gp else False}


def _calls(team):
    import staff
    c = staff.calls(team)
    return {"off": c.get("off"), "def": c.get("def")}


def _formations(league, team):
    d = team.__dict__.get("formation_subs") or {}
    def one(src):
        return {str(k): {str(role): _pid(league, p) for role, p in (mp or {}).items() if p in team.roster}
                for k, mp in (src or {}).items()}
    return {"personnel": one(d.get("personnel")), "plays": one(d.get("plays"))}


def _retention(league, team):
    out = {}
    for p in team.roster:
        row = {}
        for k in ("role_promise", "retention_conversation"):
            v = p.__dict__.get(k)
            if isinstance(v, dict):
                row[k] = dict(v)
        if "retention_hold" in p.__dict__:
            row["retention_hold"] = float(p.__dict__["retention_hold"])
        if "morale" in p.__dict__:
            row["morale"] = float(p.__dict__["morale"])
        if "redshirt_plan" in p.__dict__:
            row["redshirt_plan"] = p.__dict__["redshirt_plan"]
        if row:
            out[str(_pid(league, p))] = row
    return out


def _standing(league, team):
    return {"board": [_pid(league, r.player) for r in team.recruiting_targets],
            "q": _queue(league, team), "auto": _auto(league, team),
            "depth": _depth_ids(league, team),
            "pos": {_pid(league, p): p.position for p in team.roster},
            "plan": _plan(league, team), "calls": _calls(team),
            "formations": _formations(league, team), "retain": _retention(league, team)}


def take(league, team):
    """The orders made since begin() (or the last take): one-time actions plus whatever
    standing state changed. Resets, so the next take only carries what's new."""
    if not _S["on"] or team is not _S["team"]:
        return {}
    base = _S["base"] or _standing(league, team)
    now = _standing(league, team)
    out = {sec: {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
                 for k, v in d.items()} for sec, d in _S["events"].items()}
    rec = out.setdefault("rec", {})
    add = [x for x in now["board"] if x not in base["board"]]
    drop = [x for x in base["board"] if x not in now["board"]]
    if add:
        rec["add"] = add
    if drop:
        rec["drop"] = drop
    if now["q"] != base["q"]:
        rec["q"] = now["q"]
    if now["auto"] != base["auto"]:
        rec["auto"] = now["auto"]
    if not rec:
        out.pop("rec")
    moves = [[pid, pos] for pid, pos in now["pos"].items() if base["pos"].get(pid) not in (None, pos)]
    if moves:
        out.setdefault("roster", {})["move"] = moves
    depth = dict(out.get("depth") or {})
    for pos in set(now["depth"]) | set(base["depth"]):
        if pos not in now["depth"]:                         # a screen reset the room to the staff's sort
            depth[pos] = "staff"
        elif now["depth"][pos] != base["depth"].get(pos):
            depth[pos] = now["depth"][pos]
    if depth:
        out["depth"] = depth
    if now["plan"] is not None and now["plan"] != base["plan"]:
        out["plan"] = now["plan"]
    if now["calls"] != base["calls"]:
        out["calls"] = {k: v for k, v in now["calls"].items() if v}
    if now.get("formations") != base.get("formations"):
        out["formations"] = now.get("formations")
    if now.get("retain") != base.get("retain"):
        out["retain"] = now.get("retain")
    _S["events"] = {}
    _S["base"] = now
    return out


# ═══ What each hooked decision becomes ══════════════════════════════════════
# build(result, **the call's arguments) -> (team, value). Named for the hook lines.

def b_action(res, self, team, recruit, action, enforce=True, pitch=None, source=None):
    """A recruiting action from a recruit's card, done now (the queue and autopilot pass a source)."""
    if source is not None or not enforce:
        return None
    return team, ["now", _pid(self.league, recruit.player), action, pitch or "-"]


def b_nil(res, cycle, team, recruit, amount):
    return team, ["nil", _pid(cycle.league, recruit.player), max(0, int(amount))]


def b_withdraw(res, cycle, team, recruit):
    return team, ["nil", _pid(cycle.league, recruit.player), 0]


def b_promise(res, league, team, recruit, kind):
    return team, ["prom", _pid(league, recruit.player), kind]


def b_visit(res, cycle, team, r, game, enforce=True):
    return team, ["ov", _pid(cycle.league, r.player), game.week]


def b_pwo(res, cycle, team, r):
    return team, ["pwo", _pid(cycle.league, r.player)]


def b_camp(res, cycle, team, recruits):
    return team, {"camp": [_pid(cycle.league, r.player) for r in recruits]}


def camp_held(res):
    return isinstance(res, tuple) and "already" not in str(res[1])


def b_tree(res, league, coach, key, group=None):
    return coach.team, [key, group]


def b_dev(res, league, coach, key, n=1):
    return coach.team, [key, int(res[0])]


def dev_bought(res):
    return isinstance(res, tuple) and res[0] > 0
