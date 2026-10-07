"""
bots.py — Synthetic league members, for testing a Commissioner league before real people join.

Every player team gets a bot with a habit:
  diligent   sends a full code every cycle: a fresh board, a queue that fits the week's hours,
             visits and NIL for the recruits it's winning, a game plan picked from the film
  casual     sends a code most cycles, keeps last week's queue and changes the game plan
  lazy       sends a code about half the time
  ghost      sends codes for a while, then disappears (the inactivity prompt's test)

The bots read the world the way the website's export does, so their codes look like real ones and
are signed with each team's own key. They're for dry runs only: write_csv() makes the same CSV a
Google Form would, and order_import takes it from there.

    python bots.py SAVE.ccsave imports/bots_cycleN.csv      (one cycle's codes for a save)
"""
import csv
import datetime
import random

HABITS = (("diligent", 0.55), ("casual", 0.25), ("lazy", 0.15), ("ghost", 0.05))


def habit(lg, team):
    """Each team's bot keeps one habit for the whole league."""
    rng = random.Random(f"bot-habit:{lg.seed}:{team.school}")
    x, acc = rng.random(), 0.0
    for name, p in HABITS:
        acc += p
        if x < acc:
            return name
    return "diligent"


def sends(lg, team, n):
    """Does this team's bot send a code for cycle n?"""
    h = habit(lg, team)
    rng = random.Random(f"bot-send:{lg.seed}:{team.school}:{n}")
    if h == "diligent":
        return rng.random() < 0.97
    if h == "casual":
        return rng.random() < 0.85
    if h == "lazy":
        return rng.random() < 0.5
    return n < 4                                   # ghost: gone after the first few cycles


def _hours(lg, team):
    import knowledge
    h = knowledge._hours_next(lg, team)
    return max(0, h["total"] - h["used"])


def bot_orders(lg, team, rng=None):
    """A plausible week of orders for one team: what a decent human would do from the website."""
    import orders
    import recruit_plus as rp
    import recruiting_screens as rs
    import sideline
    import week
    rng = rng or random.Random(f"bot:{lg.seed}:{team.school}:{lg.year}:{lg.week}")
    cyc = lg.recruiting
    rmap = orders.recruit_map(lg)
    inv = {id(r): k for k, r in rmap.items()}
    h = habit(lg, team)
    o = {}
    if h in ("diligent", "ghost") or rng.random() < 0.4:
        hours = _hours(lg, team)
        open_ = [r for r in cyc.pool if not r.signed and (r.committed_to is None or r.committed_to is team)]
        scored = []
        needs, commits = cyc._needs(team), cyc.commitments(team)
        real_needs, real_commits = cyc._needs, cyc.commitments
        cyc._needs = lambda t, _f=real_needs: needs if t is team else _f(t)          # one read per team, not per recruit
        cyc.commitments = lambda t, _f=real_commits: commits if t is team else _f(t)
        try:
            for r in open_:
                score, _why = rs.suggestion(lg, team, r)
                st = r.interest.get(team, 0)
                lead = 6 if r.leader() is team else 0
                scored.append((score + st / 12 + lead, r))
        finally:
            del cyc._needs, cyc.commitments                    # back to the class's own methods
        scored.sort(key=lambda x: -x[0])
        keep = [r for r in team.recruiting_targets if not r.signed and r.committed_to in (None, team)
                and r.interest.get(team, 0) >= 25]
        board = (keep + [r for _, r in scored if r not in keep])[:orders.BOARD_MAX - 4]
        cur = set(map(id, team.recruiting_targets))
        q, spent = [], 0

        def add(r, act, rule="once", n=0):
            nonlocal spent
            cost = rp.action_cost(team, act)
            if spent + cost > hours:
                return False
            q.append([inv[id(r)], act, rule, n, "auto"])
            spent += cost
            return True
        top = board[:18]
        for r in top:
            if r.committed_to is team:
                continue
            if r.scout.get(team, 0) == 0:
                add(r, "evaluate")
        for r in top[:14]:
            if team not in r.offers and r.committed_to is None:
                add(r, "offer")
        for r in sorted(top, key=lambda r: -r.interest.get(team, 0))[:12]:
            if r.committed_to is team:
                continue
            if r.leader() is team and r.interest.get(team, 0) >= 45:
                add(r, "close", "until")
            elif r.interest.get(team, 0) >= 30:
                add(r, "in_home" if r.stars >= 4 and rng.random() < 0.4 else "position_coach")
            else:
                add(r, "contact", "weekly")
        o["rec"] = {"add": [inv[id(r)] for r in board if id(r) not in cur],
                    "drop": [inv[id(r)] for r in team.recruiting_targets if r not in board and r.committed_to is not team],
                    "q": q, "auto": {"OC": [1, 8], "DC": [1, 8]}}
        visits = []
        homes = [g.week for wk in range(lg.week + 1, 14) for g in lg.schedule.get(wk, []) if g.home is team and not g.played]
        if homes:
            for r in sorted(top, key=lambda r: -r.interest.get(team, 0))[:3]:
                ok, _ = rp.can_invite(cyc, team, r, enforce=False)
                if ok and team in r.offers and r.interest.get(team, 0) >= 30:
                    visits.append([inv[id(r)], homes[0]])
        if visits:
            o["rec"]["ov"] = visits
    g = week.next_game(lg, team)
    if g is not None:
        opp = g.opponent_of(team)
        rec_off, rec_def, _ = sideline.recommend(team, opp)
        follow = h == "diligent" or rng.random() < 0.6
        o["plan"] = {"focus": rng.choice(["balanced", "gameplan", "situational"]) if follow else "staff",
                     "off": rec_off if follow else "film", "def": rec_def if follow else "film", "script": int(rng.random() < 0.2)}
        o["calls"] = {"off": rng.choice(["HC", "OC"]), "def": rng.choice(["HC", "DC"])}
    return o


def write_csv(lg, path, n=None, only=None):
    """One cycle's Google Form export: a row per bot that sends a code this cycle."""
    import commissioner as cm
    import orders
    st = cm.state(lg)
    n = n or st["cycle"]["n"] + 1
    t0 = datetime.datetime(2026, 1, 1, 12, 0, 0) + datetime.timedelta(days=n)     # noqa: DTZ001 — a form stamp, no zone
    rows = []
    for i, team in enumerate(sorted(cm.player_teams(lg), key=lambda t: t.school)):
        if only is not None and team.school not in only:
            continue
        if only is None and not sends(lg, team, n):
            continue
        sec = cm.team_row(lg, team)["secret"]
        code = orders.encode(st["league_id"], team.school, n, bot_orders(lg, team), sec)
        rows.append([(t0 + datetime.timedelta(minutes=i)).strftime("%m/%d/%Y %H:%M:%S"), team.school, code])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Timestamp", "Your team", "Paste your order code"])
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(100000)
    import saves
    league = saves.load(sys.argv[1])
    print(write_csv(league, sys.argv[2]), "codes written")
