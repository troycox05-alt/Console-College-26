"""In-season retention conversations and tracked role promises."""
from ui import C, ask, clear, pad, paint, pause, title_bar, truncate

PROMISES = {
    "package": ("Designed package", 8, "snaps", "at least 8 snaps per game over the next three games"),
    "rotation": ("Real rotation role", 18, "snaps", "at least 18 snaps per game over the next three games"),
    "featured": ("Featured touches", 6, "opps", "at least 6 carries/targets per game over the next three games"),
}


def _risk_rows(league, team):
    import portal
    import transfer_watch
    rows = list(transfer_watch._rows(league, team, True))
    have = {id(p) for _o, p, _n, _c in rows}
    for p in team.roster:
        if _promise(p) and id(p) not in have:
            odds = portal.entry_odds(team, p, portal.depth_chart_rank(team, p))
            rows.append((odds, p, "Promise tracked", C.BCYAN))
    rows.sort(key=lambda r: (-r[0], r[1].name))
    return rows


def concern(team, p):
    import transfer_watch
    why = transfer_watch._why(team, p)
    return why or "his camp wants a clearer path and a reason to believe his role is growing"


def _promise(p):
    d = p.__dict__.get("role_promise")
    return d if isinstance(d, dict) else None


def _current(p, metric):
    s = getattr(p, "season_stats", {}) or {}
    if metric == "snaps":
        return int(s.get("snaps", 0))
    return int(s.get("rush_att", 0)) + int(s.get("targets", 0))


def promise_status(league, p):
    d = _promise(p)
    if not d or (league is not None and d.get("year") != league.year):
        return None
    games = max(0, p.games_played - d.get("base_games", 0))
    metric = d.get("metric", "snaps")
    gained = max(0, _current(p, metric) - d.get("base_value", 0))
    avg = gained / max(1, games)
    target = d.get("target", 0)
    if games >= 3:
        status = "kept" if avg >= target else "broken"
    else:
        status = "on_track" if avg >= target or games == 0 else "behind"
    d["status"], d["avg"] = status, round(avg, 1)
    return d


def promise_modifier(league, p):
    d = promise_status(league, p)
    if not d:
        return 1.0
    return {"kept": .35, "on_track": .62, "behind": 1.15, "broken": 2.25}.get(d.get("status"), 1.0)



def portal_modifier(p):
    """Season-end retention effect, independent of a League pointer on Team."""
    d = promise_status(None, p)
    prom = {"kept": .35, "on_track": .72, "behind": 1.15, "broken": 2.25}.get((d or {}).get("status"), 1.0)
    hold = float(p.__dict__.get("retention_hold", 1.0))
    return max(.25, min(2.5, prom * hold))

def conversation_modifier(league, p):
    d = p.__dict__.get("retention_conversation") or {}
    if d.get("year") != league.year or league.week > d.get("until", -1):
        return 1.0
    return float(d.get("mult", 1.0))


def _make_promise(league, p, kind):
    label, target, metric, blurb = PROMISES[kind]
    p.role_promise = {"year": league.year, "week": league.week, "kind": kind, "label": label,
                      "target": target, "metric": metric, "base_games": p.games_played,
                      "base_value": _current(p, metric), "status": "on_track"}
    import morale
    morale.nudge(p, 8, "coach promised a real role", league)
    p.__dict__.setdefault("events", {}).setdefault(league.year, []).append(f"Coach promised: {label}")


def _conversation(league, team, p):
    import morale
    clear()
    print(title_bar(f"RETENTION CONVERSATION · {p.name.upper()}"))
    print(f"   {p.position} · {p.class_label} · #{p.number}   Morale {morale.get(p):.0f} ({morale.word(morale.get(p))})")
    print()
    print(paint("   What your staff believes is bothering him:", C.GRAY))
    print(f"   {concern(team, p)}")
    d = promise_status(league, p)
    if d:
        print(paint(f"\n   Existing promise: {d['label']} · {d.get('status','').replace('_',' ')} · current {d.get('avg',0):.1f}/game", C.BYELLOW))
    print()
    print(f"   {paint('[1]', C.BYELLOW)} Listen first — no grand promise; make sure he feels heard")
    print(f"   {paint('[2]', C.BYELLOW)} Reassure him — tell him there is a path, but don't guarantee snaps")
    print(f"   {paint('[3]', C.BYELLOW)} Make a specific role promise — stronger retention effect, but it is tracked")
    print(f"   {paint('[4]', C.BYELLOW)} Tell him to earn it — honest, but it may not calm him down")
    c = ask("Your approach (Enter = cancel):").strip()
    if c not in ("1", "2", "3", "4"):
        return
    mult, lift = {"1": (.90, 3), "2": (.78, 5), "3": (.62, 0), "4": (1.05, -2)}[c]
    if c == "3":
        kinds = ["package", "rotation"] + (["featured"] if p.position in ("RB", "WR", "TE") else [])
        print()
        for i, k in enumerate(kinds, 1):
            label, _target, _metric, blurb = PROMISES[k]
            print(f"   [{i}] {pad(label, 22)} {paint(blurb, C.GRAY)}")
        z = ask("Promise:").strip()
        if not z.isdigit() or not (1 <= int(z) <= len(kinds)):
            return
        _make_promise(league, p, kinds[int(z) - 1])
    else:
        morale.nudge(p, lift, "retention conversation", league)
    p.retention_conversation = {"year": league.year, "week": league.week, "until": league.week + 3, "mult": mult}
    p.retention_hold = max(.60, min(1.15, float(p.__dict__.get("retention_hold", 1.0)) * mult))
    p.__dict__.setdefault("retention_talks", []).append((league.year, league.week, c))
    pause("Conversation logged. Press Enter:")


def screen(league, team=None):
    team = team or getattr(league, "user_team", None)
    if team is None:
        return
    while True:
        clear()
        print(title_bar(f"RETENTION · {team.school.upper()} · IN-SEASON"))
        print(paint("   Your staff's read, not a certainty. Conversations can help; specific role promises are measured by actual usage.", C.GRAY))
        rows = _risk_rows(league, team)
        if not rows:
            print("\n   Nobody is raising a serious retention concern right now.")
            pause(); return
        print(paint(f"\n   {'#':>3}  {'POS':<4}{'PLAYER':<25}{'ROLE':<10}{'RISK':<20}PROMISE", C.GRAY, C.BOLD))
        import transfer_watch
        for i, (_odds, p, name, col) in enumerate(rows[:25], 1):
            d = promise_status(league, p)
            prom = (d["label"] + " · " + d.get("status", "").replace("_", " ")) if d else "—"
            print(f"   {i:>3}  {p.position:<4}{pad(truncate(p.name,24),25)}{pad(transfer_watch._role(team,p),10)}"
                  f"{paint(pad(name,20), col)}{paint(truncate(prom,32), C.BYELLOW if d else C.GRAY)}")
        c = ask("Player # to meet · Enter = back:").strip()
        if not c:
            return
        if c.isdigit() and 1 <= int(c) <= min(25, len(rows)):
            p = rows[int(c) - 1][1]
            talks = [x for x in p.__dict__.get("retention_talks", []) if x[0] == league.year]
            if talks and league.week - talks[-1][1] < 2:
                pause("You just met with him. Give the conversation some time. Press Enter:")
                continue
            _conversation(league, team, p)
