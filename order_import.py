"""
order_import.py — Commissioner Mode: one file of codes in, one report out, then apply.

THE FILE
  Put it in the game's `imports` folder. A Google Form's responses downloaded as CSV work
  as they are (any column holding the codes is found automatically; a Timestamp column,
  if there is one, decides which code is newest). A plain .txt with one code per line
  works too.

THE REPORT (nothing is applied until you confirm)
  accepted    the newest valid code per team, with a one-line summary and any warnings
  rejected    every code that failed, and why (edited, wrong team, wrong league, old cycle...)
  superseded  older codes from a team that submitted again
  missing     player teams with no code this cycle (their standing orders keep running)

APPLYING
  A snapshot is saved before and after, so an import can always be rolled back. Teams are
  applied in alphabetical order, so the same file on the same snapshot always gives the
  same world.
"""
import csv
import datetime
import os

import orders

FOLDER = "imports"
STAMP_FORMATS = ("%m/%d/%Y %H:%M:%S", "%Y/%m/%d %I:%M:%S %p %Z", "%Y/%m/%d %I:%M:%S %p", "%Y-%m-%d %H:%M:%S",
                 "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M:%S")


def folder():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def list_files():
    path = folder()
    files = [f for f in os.listdir(path) if f.lower().endswith((".csv", ".txt"))]
    return sorted(files, key=lambda f: -os.path.getmtime(os.path.join(path, f)))


def _stamp(text):
    text = (text or "").strip()
    for fmt in STAMP_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt)       # noqa: DTZ007 — form stamps carry no zone; only order matters
        except ValueError:
            continue
    return None


def read_codes(path):
    """[(row number, timestamp or None, code text)] from a CSV or a text file."""
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        text = f.read()
    if path.lower().endswith(".txt"):
        for i, line in enumerate(text.splitlines(), 1):
            if orders.PREFIX + "." in line:
                out.append((i, None, line.strip()))
        return out
    rows = list(csv.reader(text.splitlines()))
    if not rows:
        return out
    start = 0 if any(orders.PREFIX + "." in c for c in rows[0]) else 1      # a header row, or straight to data
    header = [h.strip().lower() for h in rows[0]] if start else []
    ts_col = next((i for i, h in enumerate(header) if "timestamp" in h or h in ("time", "submitted")), None)
    for idx in range(start, len(rows)):
        row, n = rows[idx], idx + 1
        cells = [c for c in row if orders.PREFIX + "." in c]
        if not cells:
            continue
        code = max(cells, key=len)                            # the code cell (a team-name column is shorter)
        when = _stamp(row[ts_col]) if ts_col is not None and ts_col < len(row) else None
        out.append((n, when, code.strip()))
    return out


def summarize(clean):
    bits = []
    rec = clean.get("rec") or {}
    if "q" in rec:
        bits.append(f"queue {len(rec['q'])}")
    if rec.get("add") or rec.get("drop"):
        bits.append(f"board +{len(rec.get('add', []))}/-{len(rec.get('drop', []))}")
    for k, word in (("ov", "visits"), ("nil", "NIL"), ("prom", "promises"), ("pwo", "walk-ons")):
        if rec.get(k):
            bits.append(f"{word} {len(rec[k])}")
    if "auto" in rec:
        on = [r for r, v in rec["auto"].items() if v[0]]
        bits.append("autopilot " + ("/".join(on) if on else "off"))
    if "depth" in clean:
        bits.append(f"depth {len(clean['depth'])} pos")
    if "plan" in clean:
        p = clean["plan"]
        bits.append(f"plan {p['focus']}/{p['off']}/{p['def']}")
    if "calls" in clean:
        bits.append("calls " + "/".join(f"{k}:{v}" for k, v in clean["calls"].items()))
    return " · ".join(bits) or "no changes (standing orders continue)"


def build_report(league, path):
    import commissioner as cm
    rows = read_codes(path)
    cycle = cm.state(league)["cycle"]["n"] + 1
    report = {"file": os.path.basename(path), "cycle": cycle, "accepted": {}, "rejected": [], "superseded": [],
              "missing": [], "rows": len(rows), "applied": False}
    newest = {}
    for n, when, code in rows:
        try:
            team, payload = orders.verify(league, code)
        except orders.CodeError as e:
            guess = None
            try:
                guess = orders.peek(code)[2].get("t")
            except orders.CodeError:
                pass
            report["rejected"].append({"row": n, "team": guess, "reason": str(e)})
            continue
        key = (when or datetime.datetime.min, n)           # noqa: DTZ901 — naive on both sides
        prev = newest.get(team.school)
        if prev is not None:
            if key >= prev[0]:
                report["superseded"].append({"row": prev[1], "team": team.school})
            else:
                report["superseded"].append({"row": n, "team": team.school})
                continue
        newest[team.school] = (key, n, team, payload)
    for school in sorted(newest):
        _, n, team, payload = newest[school]
        clean, warn = orders.validate(league, team, payload["o"])
        report["accepted"][school] = {"row": n, "member": cm.owner(league, team), "orders": clean,
                                      "warnings": warn, "summary": summarize(clean)}
    report["missing"] = sorted(t.school for t in cm.player_teams(league) if t.school not in report["accepted"])
    return report


def commit(league, report):
    """Apply an accepted report. Snapshots before and after. Returns the per-team result lines."""
    import commissioner as cm
    st = cm.state(league)
    if report["cycle"] != st["cycle"]["n"] + 1:
        raise RuntimeError("the league moved on since this report was built; build it again")
    cm.snapshot(league, f"before import {report['file']} (cycle {report['cycle']})")
    cm.fresh_reads(league)
    results = {}
    for school in sorted(report["accepted"]):
        team = next(t for t in league.teams if t.school == school)
        entry = report["accepted"][school]
        results[school] = orders.apply(league, team, entry["orders"])
        row = cm.team_row(league, team)
        row["last_cycle"] = report["cycle"]
    report["applied"] = True
    st["imports"].append({"cycle": report["cycle"], "file": report["file"], "rows": report["rows"],
                          "accepted": sorted(report["accepted"]), "rejected": report["rejected"],
                          "missing": report["missing"],
                          "results": {s: lines for s, lines in results.items() if lines},
                          "warnings": {s: e["warnings"] for s, e in report["accepted"].items() if e["warnings"]}})
    del st["imports"][:-40]
    if report["rejected"]:
        lines = [f"row {x['row']}: {x.get('team') or 'unknown team'}: {x['reason']}" for x in report["rejected"][:12]]
        more = len(report["rejected"]) - len(lines)
        cm.add_inbox(league, "import", f"{len(report['rejected'])} code{'s' if len(report['rejected']) != 1 else ''} in "
                     f"{report['file']} didn't import. " + "; ".join(lines) + (f"; and {more} more" if more > 0 else "")
                     + ". Ask those members to build their code again, or enter it with [M].", options=["Got it"])
    cm.log(league, f"Imported {report['file']}: {len(report['accepted'])} accepted, "
                   f"{len(report['rejected'])} rejected, {len(report['missing'])} missing.")
    cm.snapshot(league, f"after import {report['file']} (cycle {report['cycle']})")
    return results


def apply_manual(league, team, orders_dict, how="manual"):
    """Commissioner-entered orders for one team (from a Discord message, a late code...)."""
    import commissioner as cm
    clean, warn = orders.validate(league, team, orders_dict)
    cm.snapshot(league, f"before manual orders for {team.school}")
    cm.fresh_reads(league)
    lines = orders.apply(league, team, clean)
    cm.team_row(league, team)["last_cycle"] = cm.state(league)["cycle"]["n"] + 1
    cm.log(league, f"{how} orders for {team.school}: {summarize(clean)}")
    return clean, warn, lines
