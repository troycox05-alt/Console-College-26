"""Coach-safe plain-text snapshot of the user's program for use with an AI assistant."""
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(HERE, "exports")
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _clean(v):
    if v is None:
        return ""
    return _ANSI.sub("", str(v)).strip()


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(s)).strip("_") or "team"


def _section(lines, title):
    lines.extend(["", title, "=" * len(title)])


def _kv(lines, key, value, indent=""):
    if value not in (None, "", [], {}, ()): 
        lines.append(f"{indent}{key}: {_clean(value)}")


def _pretty_obj(lines, obj, indent="  "):
    """Readable generic dump for already coach-safe knowledge data."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v in (None, "", [], {}, ()): 
                continue
            label = str(k).replace("_", " ").replace("Id", " ID").title()
            if isinstance(v, (dict, list, tuple)):
                lines.append(f"{indent}{label}:")
                _pretty_obj(lines, v, indent + "  ")
            else:
                lines.append(f"{indent}{label}: {_clean(v)}")
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            if isinstance(v, (dict, list, tuple)):
                lines.append(indent + "-")
                _pretty_obj(lines, v, indent + "  ")
            else:
                lines.append(f"{indent}- {_clean(v)}")
    else:
        lines.append(indent + _clean(obj))


def _player(lines, p):
    head = f"#{p.get('num', '')} {p.get('n', 'Player')} — {p.get('p', '')} {p.get('yr', '')}".strip()
    lines.extend(["", head, "-" * min(78, len(head))])
    bio = [x for x in (p.get("ht"), (str(p.get("wt")) + " lbs" if p.get("wt") else ""), p.get("homeName")) if x]
    if bio:
        lines.append("Bio: " + " · ".join(map(str, bio)))
    _kv(lines, "Depth", p.get("depth"))
    _kv(lines, "Starter", "yes" if p.get("starter") else "no")
    _kv(lines, "Staff evaluation", p.get("eval"))
    _kv(lines, "Development grade", p.get("dev"))
    _kv(lines, "Potential", p.get("potential"))
    _kv(lines, "Durability", p.get("durability"))
    _kv(lines, "Offseasons developed", p.get("developed"))
    _kv(lines, "This week's practice", p.get("practice"))
    _kv(lines, "Practice form", p.get("week"))
    _kv(lines, "Staff report", p.get("comments"))
    _kv(lines, "Trend", p.get("trend"))
    if p.get("best"):
        lines.append("Best skills: " + ", ".join(p["best"]))
    if p.get("worst"):
        lines.append("Needs work: " + ", ".join(p["worst"]))
    if p.get("skills"):
        lines.append("Position skills (staff's eye): " + "; ".join(f"{a}: {b}" for a, b in p["skills"]))
    if p.get("athlete"):
        lines.append("Athletic fundamentals (staff's eye): " + "; ".join(f"{a}: {b}" for a, b in p["athlete"]))
    if p.get("alt"):
        lines.append("Other position fits: " + "; ".join(f"{a}: {b}" for a, b in p["alt"]))
    if p.get("traits"):
        lines.append("Traits: " + ", ".join(map(str, p["traits"])))
    if p.get("explain"):
        lines.append("Trait detail: " + "; ".join(" — ".join(map(str, x)) for x in p["explain"]))
    if p.get("persona"):
        lines.append("Personality: " + "; ".join(" — ".join(map(str, x)) for x in p["persona"]))
    _kv(lines, "Morale", f"{p.get('morale')} ({p.get('mood')})" if p.get("morale") is not None else "")
    if p.get("lately"):
        lines.append("Morale notes: " + "; ".join(map(str, p["lately"])))
    _kv(lines, "Academics", p.get("school"))
    _kv(lines, "Injury", p.get("inj"))
    if p.get("nil"):
        _kv(lines, "NIL", p.get("nil"))
    if p.get("transfer"):
        _kv(lines, "Transferred from", p.get("transfer"))
    if p.get("portal") and any(p["portal"]):
        lines.append("Transfer watch: " + " — ".join(str(x) for x in p["portal"] if x))
    if p.get("staff"):
        lines.append("Depth-room staff view:")
        _pretty_obj(lines, p["staff"], "  ")
    _kv(lines, "Current stats", p.get("stats"))
    if p.get("season"):
        lines.append("Season stat detail:")
        _pretty_obj(lines, p["season"], "  ")
    if p.get("career"):
        lines.append("Career stat detail:")
        _pretty_obj(lines, p["career"], "  ")
    if p.get("timeline"):
        lines.append("Career timeline:")
        for y in p["timeline"]:
            bits = [str(y.get("y", ""))]
            if y.get("looked"): bits.append("staff view: " + str(y["looked"]))
            if y.get("stats"): bits.append(str(y["stats"]))
            if y.get("gp") is not None: bits.append(f"{y['gp']} GP")
            lines.append("  - " + " · ".join(bits))
            for e in y.get("events") or []:
                lines.append("      * " + _clean(e))


def _box(lines, box, team_school):
    if not box:
        return
    teams = box.get("teams") or []
    if not any(t.get("school") == team_school for t in teams):
        return
    label = box.get("label") or f"Week {box.get('w', '')}"
    score = " — ".join(f"{t.get('school')} {t.get('score')}" for t in teams)
    lines.extend(["", f"{label}: {score}", "-" * min(78, len(label) + len(score) + 2)])
    if box.get("name"): lines.append("Game: " + str(box["name"]))
    if box.get("att"): lines.append("Attendance: " + f"{box['att']:,}")
    if box.get("team"):
        lines.append("Team stats:")
        for r in box["team"]:
            if len(r) >= 3:
                lines.append(f"  {r[0]}: {teams[0].get('school')} {r[1]} | {teams[1].get('school')} {r[2]}")
    if box.get("scoring"):
        lines.append("Scoring summary:")
        for r in box["scoring"]:
            lines.append("  - " + " · ".join(_clean(x) for x in r[:4]))
    for cat in box.get("cats") or []:
        lines.append(cat.get("name", "Stats") + ":")
        cols = cat.get("cols") or []
        for ti, rows in enumerate(cat.get("rows") or []):
            if not rows: continue
            school = teams[ti].get("school", "") if ti < len(teams) else ""
            lines.append("  " + school)
            for r in rows:
                vals = [f"{c}={v}" for c, v in zip(cols, r[3:])]
                lines.append(f"    {r[1]} ({r[2]}): " + ", ".join(vals))


def build(league, team):
    """Build plain text strictly from the coach-safe knowledge layer."""
    import knowledge
    private = knowledge.team_private(league, team)
    boxes, _logs = knowledge.box_scores(league)
    lines = ["CONSOLE COLLEGE — TEAM CONTEXT", "=" * 30,
             f"Team: {team.full_name}", f"Season: {league.year}", f"Current point: {league.week_name(league.week)}",
             "", "VISIBILITY NOTE", "---------------",
             "This file contains only information available to this coaching staff. Player ability is expressed through the staff's eye, practice/film reads, public production and other Coach Career-visible information — never underlying player ratings."]

    _section(lines, "PROGRAM / AD / GOALS")
    for key in ("program", "coach", "card"):
        if private.get(key):
            lines.append(key.upper() + ":")
            _pretty_obj(lines, private[key], "  ")
    report = (private.get("reports") or {}).get("program")
    if report:
        lines.extend(["", report])

    _section(lines, "FULL COACHING STAFF")
    staff_report = (private.get("reports") or {}).get("staff")
    if staff_report:
        lines.append(staff_report)
    # The rendered staff-room report is the authoritative detailed view. Avoid
    # dumping the internal staff-market payload here; it is much larger and not
    # a screen the coach actually sees as one object.

    _section(lines, "FULL ROSTER — COACH'S EYE")
    for p in private.get("roster") or []:
        _player(lines, p)

    _section(lines, "ROSTER MANAGEMENT / RETENTION / FORMATION SUBS")
    planned = [p for p in team.roster if p.__dict__.get("redshirt_plan") == league.year]
    if planned:
        lines.append("Preseason redshirt protection:")
        for p in planned:
            lines.append(f"  - {p.position} #{p.number} {p.name} ({p.class_label})")
    else:
        lines.append("Preseason redshirt protection: none currently marked.")
    retained = [p for p in team.roster if p.__dict__.get("role_promise") or p.__dict__.get("retention_conversation")]
    if retained:
        lines.append("Retention / role promises:")
        try:
            import retention
            for p in retained:
                bits = [f"{p.position} #{p.number} {p.name}"]
                d = retention.promise_status(league, p)
                if d:
                    bits.append(f"promise: {d.get('label')} ({d.get('status','').replace('_',' ')}, {d.get('avg',0):.1f}/game)")
                if p.__dict__.get("retention_conversation"):
                    bits.append("retention conversation held")
                lines.append("  - " + " · ".join(bits))
        except Exception:
            pass
    fs = team.__dict__.get("formation_subs") or {}
    if fs.get("personnel") or fs.get("plays"):
        lines.append("Formation/play substitutions:")
        for bucket, label in (("personnel", "Personnel"), ("plays", "Play")):
            for name, mp in (fs.get(bucket) or {}).items():
                desc = ", ".join(f"{role}={p.name}" for role, p in mp.items() if p in team.roster)
                if desc:
                    lines.append(f"  - {label} {name}: {desc}")

    _section(lines, "CURRENT PRACTICE / DEPTH CONTEXT")
    _pretty_obj(lines, private.get("practice") or {}, "")
    if private.get("gameday"):
        lines.append("\nGame-day / depth context:")
        _pretty_obj(lines, private["gameday"], "  ")

    _section(lines, "SCHEDULE / SCORES")
    for wk in sorted(league.schedule):
        for g in league.schedule.get(wk) or []:
            if team not in (g.home, g.away):
                continue
            opp = g.opponent_of(team)
            site = "vs" if g.home is team or g.neutral else "at"
            if g.played:
                result = "W" if g.score_for(team) > g.score_for(opp) else "L"
                lines.append(f"- {league.week_name(wk)}: {site} {opp.school} — {result} {g.score_for(team)}-{g.score_for(opp)}")
            else:
                lines.append(f"- {league.week_name(wk)}: {site} {opp.school} — upcoming")

    _section(lines, "BOX SCORES")
    found = False
    for wk in sorted(boxes):
        for box in boxes[wk]:
            if box and any(t.get("school") == team.school for t in box.get("teams", [])):
                found = True
                _box(lines, box, team.school)
    if not found:
        lines.append("No completed box scores yet.")

    _section(lines, "YOUR WEEK-BY-WEEK COACHING DECISIONS")
    try:
        from export_sheets import _decisions
        decisions = _decisions(league, team)
    except Exception:
        decisions = list(getattr(league, "decision_log", []) or [])
    for d in decisions:
        if d.get("year") != league.year:
            continue
        lines.append(f"\nWeek {d.get('week')} vs {d.get('opp')}: {d.get('result')} {d.get('score')}")
        for k in ("focus", "routine", "plan_off", "plan_def", "script", "plan_by", "pts", "margin"):
            _kv(lines, k.replace("_", " ").title(), d.get(k), "  ")
        if d.get("calls"):
            lines.append("  Headset calls:")
            for c in d["calls"]:
                lines.append("    - " + " · ".join(_clean(c.get(k)) for k in ("q", "clock", "kind", "text", "yours", "result") if c.get(k) not in (None, "")))
    if not any(d.get("year") == league.year for d in decisions):
        lines.append("No completed weekly decision logs yet this season.")

    _section(lines, "RECRUITING / PORTAL / OFFSEASON CONTEXT")
    rec = private.get("recruiting") or {}
    if rec:
        lines.append("\nRecruiting:")
        for k in ("hours", "nilLeft", "classSize"):
            if rec.get(k) not in (None, "", [], {}):
                _kv(lines, k.replace("nilLeft", "NIL available").replace("classSize", "Class size").title(), rec.get(k), "  ")
        if rec.get("class"):
            lines.append("  Current class:")
            _pretty_obj(lines, rec["class"], "    ")
        if rec.get("lastWeek"):
            lines.append("  Last recruiting week:")
            _pretty_obj(lines, rec["lastWeek"], "    ")
        if rec.get("queue"):
            lines.append("  Planned recruiting actions:")
            _pretty_obj(lines, rec["queue"], "    ")
        board_ids = set(rec.get("board") or [])
        board = [r for r in rec.get("known") or [] if r.get("id") in board_ids]
        if board:
            lines.append("  Active board detail (only what your staff has learned):")
            _pretty_obj(lines, board, "    ")
    for key, label in (("jobs", "Job market"), ("money", "Money / NIL"),
                       ("seasonEnd", "Season-end NIL"), ("portal", "Portal"),
                       ("rosterWeek", "Roster management"), ("spring", "Spring practice / A-Day")):
        if private.get(key):
            lines.append("\n" + label + ":")
            _pretty_obj(lines, private[key], "  ")
    for key in ("budget", "facilities", "portal"):
        report = (private.get("reports") or {}).get(key)
        if report:
            lines.extend(["", report])

    _section(lines, "LOCKER ROOM / PROGRAM NOTES")
    locker = (private.get("reports") or {}).get("locker")
    if locker:
        lines.append(locker)
    career_log = list(getattr(league, "career_log", []) or [])
    if career_log:
        lines.append("\nCareer log:")
        for e in career_log[-80:]:
            lines.append("- " + _clean(e))

    lines.extend(["", "END OF TEAM CONTEXT", f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    return "\n".join(lines).rstrip() + "\n"


def export(league, team=None):
    team = team or getattr(league, "user_team", None)
    if team is None:
        raise ValueError("No user team is loaded.")
    os.makedirs(EXPORT_DIR, exist_ok=True)
    filename = f"team_context_{_slug(team.school)}_{league.year}_week_{league.week}.txt"
    path = os.path.join(EXPORT_DIR, filename)
    text = build(league, team)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, len(text.splitlines())
