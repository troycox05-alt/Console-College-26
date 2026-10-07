"""
recruit_ui.py — The new recruiting screens.

  queue_screen      your standing orders, in order: what runs this week, what gets cut
  add_order_flow    put an order in the queue (from the queue or a recruit's card)
  visits_screen     official visits: upcoming, and the reports from the ones that happened
  plan_visit        book an official visit at one of your home games
  ask_pitch         what you sell him on in a call or a visit
  war_room          your ordered big board, tiers, class needs, a class goal, pipelines
  hit_or_bust       every class you've signed, graded
  camp_screen       the summer camp (preseason)
  walkons_screen    preferred walk-on invites (Week 8 on)
  signing_day_live  National Signing Day: hats on the table, one at a time
"""
import time
from collections import Counter

import recruit_plus as rp
from recruiting_data import ACTIONS, PRIORITY_LABELS, STATES
from roster import ROSTER_SIZE
from ui import (C, ask, chip, clear, columns, command_bar, key, meter, pad, paint, panel, pause, rule, section,
                title_bar, truncate)

ORDER_ACTIONS = ["contact", "position_coach", "in_home", "campus_visit", "close", "evaluate", "offer"]
RULE_KEYS = ["weekly", "until", "biweekly", "weeks", "once"]


def _stars(n):
    return paint("★" * n, C.BYELLOW)


def _status_color(s):
    return C.BGREEN if s == "runs" else C.BRED if s.startswith("cut") else C.GRAY


# ═══ Standing orders ════════════════════════════════════════════════════════

def queue_screen(league, team):
    cycle = league.recruiting
    msg = ""
    while True:
        clear()
        color = league.conference_color(team.conference)
        q = rp.queue(cycle, team)
        steps, left = rp.plan(cycle, team)
        hrs, tot = cycle.remaining_hours(team), cycle.hours_for(team)
        need = sum(c for _, s, c, run in steps if run)
        cut = [e for e, s, _, _ in steps if s.startswith("cut")]
        print(title_bar(f"STANDING ORDERS  ·  {team.school.upper()}  ·  {league.week_name(league.week) if league.week else 'PRESEASON'}", color))
        print(f"  {paint('HOURS LEFT', C.GRAY)} {paint(f'{hrs}/{tot}', C.BWHITE, C.BOLD)} "
              f"{meter(hrs, 16, maximum=max(1, tot), color=C.BCYAN)}   "
              f"{paint('QUEUE NEEDS', C.GRAY)} {paint(f'{need}h', C.BGREEN if not cut else C.BYELLOW, C.BOLD)}"
              + (paint(f"   {len(cut)} order{'s' if len(cut) != 1 else ''} will be CUT", C.BRED, C.BOLD) if cut else ""))
        print(paint("  The queue runs top to bottom at the end of the week with whatever hours you haven't spent.\n"
                    "  An order that doesn't fit is cut; a cheaper one further down still runs. Same recruit, as many times\n"
                    "  as you like. Pitches: 'best known' sells what your staff knows he wants.", C.GRAY))
        print()
        print(paint(f"  {'#':>3}  {'ACTION':<24}{'RECRUIT':<23}{'POS':<4}{'':<6}{'REPEATS':<27}{'HRS':>3}  THIS WEEK",
                    C.GRAY, C.BOLD))
        shown_line = False
        for i, (e, status, cost, runs) in enumerate(steps, 1):
            r = e["r"]
            if not runs and status.startswith("cut") and not shown_line:
                print(paint("  " + "─" * 30 + " the hours run out here " + "─" * 30, C.BRED))
                shown_line = True
            pitch = "" if e["a"] not in rp.PITCH_ACTIONS else \
                (" · best known" if e.get("pitch") in (None, "auto") else f" · {PRIORITY_LABELS.get(e['pitch'], '')[:12].lower()}")
            st = ("✔ runs" if runs else ("✘ " + status) if status.startswith("cut") else "· " + status)
            print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(truncate(ACTIONS[e['a']][0] + pitch, 23), 24)}"
                  f"{pad(truncate(r.player.name, 22), 23)}{paint(pad(r.position, 4), C.BCYAN)}{pad(_stars(r.stars), 6)}"
                  f"{pad(truncate(rp.rule_text(e), 26), 27)}{rp.action_cost(team, e['a']):>3}  "
                  f"{paint(truncate(st, 22), _status_color(status))}")
        if not q:
            print(paint("  The queue is empty. [A] adds an order — or [Q] on any recruit's card.", C.BYELLOW))
        summ = rp.S(cycle)["summary"].get(team)
        if summ and (summ["ran"] or summ["cut"] or summ["done"] or summ.get("auto")):
            print()
            print(section(f"LAST RUN  ·  {league.week_name(summ.get('week', 0))}", C.BCYAN))
            ran = f"{len(summ['ran'])} ran ({sum(c for _, _, c, _ in summ['ran'])}h)"
            print(f"   {paint(ran, C.BGREEN)}"
                  + (paint(f"   cut: {', '.join(f'{n} ({a})' for n, a, _ in summ['cut'][:5])}", C.BRED) if summ["cut"] else "")
                  + (paint(f"   finished: {', '.join(n for n, _ in summ['done'][:4])}", C.GRAY) if summ["done"] else ""))
            if summ.get("auto"):
                print(paint("   Coordinators: " + ", ".join(f"{role} {a.lower()} {n}" for role, n, a in summ["auto"][:6]), C.GRAY))
        ap = rp.autopilot(cycle, team)
        print(paint(f"\n  Coordinator autopilot (after the queue): OC — offense {'ON, up to ' + str(ap['OC']['hours']) + 'h' if ap['OC']['on'] else 'off'}"
                    f"   ·   DC — defense {'ON, up to ' + str(ap['DC']['hours']) + 'h' if ap['DC']['on'] else 'off'}", C.GRAY))
        items = [key("A", "add an order", C.BGREEN), key("M a b", "move a to b"), key("T#", "to top"),
                 key("C#", "copy"), key("E#", "change repeat"), key("X#", "remove"), key("R", "run it now"),
                 key("O", "coordinator autopilot"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        if msg:
            print(paint("  " + msg, C.BCYAN, C.BOLD))
            msg = ""
        raw = ask("Queue:").strip()
        c = raw.lower()
        parts = c.split()
        if c in ("", "b"):
            return
        if c == "a":
            msg = add_order_flow(league, team)
        elif c == "r":
            s = rp.run_queue(cycle, team)
            s["auto"] = []
            s["week"] = league.week
            rp.S(cycle)["summary"][team] = s
            msg = f"Ran {len(s['ran'])} order{'s' if len(s['ran']) != 1 else ''}" + \
                (f"; {len(s['cut'])} cut for hours" if s["cut"] else "") + "."
        elif c == "o":
            _autopilot_menu(league, team)
        elif len(parts) == 3 and parts[0] == "m" and parts[1].isdigit() and parts[2].isdigit():
            a, b = int(parts[1]) - 1, int(parts[2]) - 1
            if 0 <= a < len(q) and 0 <= b < len(q):
                q.insert(b, q.pop(a))
                msg = f"Moved order {a + 1} to {b + 1}."
        elif len(c) >= 2 and c[0] in "tcex" and c[1:].isdigit() and 1 <= int(c[1:]) <= len(q):
            i = int(c[1:]) - 1
            e = q[i]
            if c[0] == "t":
                q.insert(0, q.pop(i))
                msg = f"{e['r'].player.name} ({ACTIONS[e['a']][0].lower()}) is first in line."
            elif c[0] == "x":
                q.pop(i)
                msg = "Removed."
            elif c[0] == "c":
                q.insert(i + 1, dict(e, last=None, runs=0))
                msg = "Copied — the copy sits right below it."
            elif c[0] == "e":
                rule, n = _ask_rule()
                if rule:
                    e["rule"], e["n"] = rule, n
                    msg = f"Now: {rp.rule_text(e)}."
        else:
            msg = "Try A, M 3 1, T4, C2, E2, X5, R, O or B."


def _ask_rule():
    print()
    for i, k in enumerate(RULE_KEYS, 1):
        txt = rp.QUEUE_RULES[k].format(n="N")
        print(f"   {key(str(i), txt)}")
    c = ask("How often (Enter = every week):").strip()
    rule = RULE_KEYS[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(RULE_KEYS) else "weekly" if c == "" else None
    n = 0
    if rule == "weeks":
        v = ask("For how many weeks?").strip()
        n = int(v) if v.isdigit() and int(v) > 0 else 3
    return rule, n


def add_order_flow(league, team, recruit=None):
    cycle = league.recruiting
    if recruit is None:
        board = cycle.board_for(team)
        if not board:
            return "Your board is empty — add recruits from the finder first."
        clear()
        print(title_bar("ADD AN ORDER  ·  WHO?", C.BCYAN))
        for i, r in enumerate(board, 1):
            st = r.standing(team) if r.interest.get(team) else "NO CONTACT"
            n_q = sum(1 for e in rp.queue(cycle, team) if e["r"] is r)
            print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(truncate(r.player.name, 22), 23)}"
                  f"{paint(pad(r.position, 4), C.BCYAN)}{pad(_stars(r.stars), 6)}{pad(st, 15)}"
                  + ("offer ✔" if team in r.offers else paint("no offer", C.GRAY))
                  + (paint(f"   in the queue ×{n_q}", C.BYELLOW) if n_q else ""))
        c = ask("Recruit # (Enter = cancel):").strip()
        if not (c.isdigit() and 1 <= int(c) <= len(board)):
            return ""
        recruit = board[int(c) - 1]
    r = recruit
    print()
    print(paint(f"  {r.player.name} — {r.stars}★ {r.position}. What should the staff do?", C.BWHITE, C.BOLD))
    for i, a in enumerate(ORDER_ACTIONS, 1):
        label, cost = ACTIONS[a][0], rp.action_cost(team, a)
        note = paint("  (needs an offer first)", C.GRAY) if a not in ("offer", "evaluate") and team not in r.offers else ""
        print(f"   {key(str(i), f'{label} ({cost}h)')}{note}")
    c = ask("Action (Enter = cancel):").strip()
    if not (c.isdigit() and 1 <= int(c) <= len(ORDER_ACTIONS)):
        return ""
    action = ORDER_ACTIONS[int(c) - 1]
    rule, n = ("once", 0) if action == "offer" else _ask_rule()
    if not rule:
        return ""
    pitch = "auto"
    if action in rp.PITCH_ACTIONS:
        pitch = ask_pitch(league, team, r, prompt="Sell him on (Enter = the best thing we know he wants):") or "auto"
    q = rp.queue(cycle, team)
    where = ask(f"Where in the queue? (1-{len(q) + 1}, Enter = the bottom):").strip()
    at = int(where) - 1 if where.isdigit() else None
    e = rp.add_order(cycle, team, r, action, rule, n, pitch, at)
    return f"Queued: {ACTIONS[action][0].lower()} — {r.player.name}, {rp.rule_text(e)}."


def _autopilot_menu(league, team):
    ap = rp.autopilot(league.recruiting, team)
    while True:
        clear()
        print(title_bar("COORDINATOR AUTOPILOT", C.BCYAN))
        print(paint("\n  A coordinator can work his side of your board on his own — offers, film, calls, visits, closing —\n"
                    "  after your queue has run, using up to the hours you give him. He never touches a recruit your\n"
                    "  queue already worked that week.\n", C.GRAY))
        for i, (role, side) in enumerate((("OC", "offense (QB RB WR TE OL K P)"), ("DC", "defense (DL LB CB S)")), 1):
            cfg = ap[role]
            print(f"   {key(str(i), f'{role} — {side}')}   "
                  f"{paint('ON', C.BGREEN, C.BOLD) if cfg['on'] else paint('off', C.GRAY)}   up to {cfg['hours']}h a week")
        print(paint("\n   [1]/[2] switch on/off   [H1 12] give the OC 12 hours   [B] back", C.GRAY))
        c = ask("Autopilot:").strip().lower()
        parts = c.split()
        if c in ("1", "2"):
            role = "OC" if c == "1" else "DC"
            ap[role]["on"] = not ap[role]["on"]
        elif len(parts) == 2 and parts[0] in ("h1", "h2") and parts[1].isdigit():
            ap["OC" if parts[0] == "h1" else "DC"]["hours"] = max(1, min(60, int(parts[1])))
        else:
            return


# ═══ Pitches ════════════════════════════════════════════════════════════════

def ask_pitch(league, team, r, prompt="What do you sell him on? (Enter = best thing we know)"):
    """Returns a priority key, or None for 'let the staff pick'."""
    opts = rp.pitch_options(league.recruiting, team, r)
    kn = set(rp.known(r, team))
    print(paint(f"\n  The conversation with {r.player.first_name}:", C.BWHITE, C.BOLD))
    for i, (k, word) in enumerate(opts, 1):
        tag = paint("  ← he told you this matters", C.BGREEN) if k in kn else ""
        print(f"   {key(str(i), PRIORITY_LABELS[k])}  {paint(word, C.GRAY)}{tag}")
    c = ask(prompt).strip()
    if c.isdigit() and 1 <= int(c) <= len(opts):
        return opts[int(c) - 1][0]
    return None


# ═══ Official visits ════════════════════════════════════════════════════════

def plan_visit(league, team, r):
    cycle = league.recruiting
    ok, why = rp.can_invite(cycle, team, r)
    if not ok:
        return why
    games = rp.home_games_left(cycle, team)
    if not games:
        return "You don't have a home game left this season."
    print(paint(f"\n  Official visit for {r.player.name} ({len(rp.ov_of(r))}/{rp.OV_MAX} visits used"
                + (": " + ", ".join(t.school for t in rp.ov_of(r)) if rp.ov_of(r) else "") + "). Pick the Saturday:",
                C.BWHITE, C.BOLD))
    import broadcast
    for i, gm in enumerate(games, 1):
        opp = gm.away
        rk = league.rankings.rank_of(opp)
        from commentary import rivalry_name
        riv = rivalry_name(team, opp)
        kick = broadcast.when(gm) if getattr(gm, "kick", None) is not None else ""
        print(f"   {key(str(i), f'{league.week_name(gm.week)} vs ' + (f'#{rk} ' if rk else '') + opp.school)}"
              + paint(f"  {opp.record}" + (f" · {riv}" if riv else "") + (f" · {kick}" if kick else ""), C.GRAY))
    print(paint("   A win over a good team in front of a full house is what sells. A blowout loss doesn't.", C.GRAY))
    c = ask(f"Which game? ({rp.OV_COST} hours now; Enter = cancel)").strip()
    if not (c.isdigit() and 1 <= int(c) <= len(games)):
        return ""
    ok, text = rp.invite(cycle, team, r, games[int(c) - 1])
    return text


def visits_screen(league, team):
    cycle = league.recruiting
    while True:
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"OFFICIAL VISITS  ·  {team.school.upper()}", color))
        up = sorted(((w, r) for r in cycle.pool for t, w in rp.ov_of(r).items()
                     if t is team and w >= league.week and not r.signed), key=lambda x: x[0])
        up = [(w, r) for w, r in up if not any(v["r"] is r for v in rp.S(cycle)["visits"][team])]
        print(section("COMING UP", C.BCYAN))
        if not up:
            print(paint("   Nobody booked. [V] on a recruit's card (or [P] here) sets one up.", C.GRAY))
        by_week = {}
        for w, r in up:
            by_week.setdefault(w, []).append(r)
        for w, rs in by_week.items():
            gm = next((x for x in league.schedule.get(w, []) if x.home is team), None)
            opp = f" vs {gm.away.school}" if gm else ""
            print(f"   {paint(pad(league.week_name(w) + opp, 30), C.BWHITE, C.BOLD)}"
                  + ", ".join(f"{r.player.name} ({r.stars}★ {r.position})" for r in rs))
        print()
        print(section("HOW THEY WENT", C.BYELLOW))
        reps = list(reversed(rp.S(cycle)["visits"][team]))
        if not reps:
            print(paint("   No visits yet.", C.GRAY))
        for v in reps[:8]:
            r = v["r"]
            col = C.BGREEN if v["score"] >= 12 else C.BYELLOW if v["score"] >= 0 else C.BRED
            print(f"   {paint(pad(league.week_name(v['week']), 9), C.GRAY)}{paint(pad(r.player.name, 22), C.BWHITE, C.BOLD)}"
                  f"{paint(pad(v['grade'], 16), col, C.BOLD)}{paint(v['before'], C.GRAY)} → {paint(v['after'], col)}")
            for ln in v["lines"][:3]:
                print(paint(f"        {ln}", C.GRAY))
        items = [key("P", "plan a visit", C.BGREEN), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        c = ask("Visits:").strip().lower()
        if c == "p":
            board = [r for r in cycle.board_for(team) if not r.signed]
            for i, r in enumerate(board, 1):
                ok, why = rp.can_invite(cycle, team, r)
                print(f"  {paint(f'{i:>3}', C.BYELLOW if ok else C.GRAY, C.BOLD)}  {pad(r.player.name, 23)}"
                      f"{pad(r.position, 4)}{pad(_stars(r.stars), 6)}{paint(pad(r.standing(team), 15), C.GRAY)}"
                      + paint("" if ok else why, C.GRAY))
            v = ask("Recruit # (Enter = cancel):").strip()
            if v.isdigit() and 1 <= int(v) <= len(board):
                out = plan_visit(league, team, board[int(v) - 1])
                if out:
                    print(paint("   " + out, C.BCYAN))
                    pause()
        else:
            return


# ═══ The war room ═══════════════════════════════════════════════════════════

GOALS = {"top10": ("A top-10 class", lambda rank, *_: rank is not None and rank <= 10),
         "top25": ("A top-25 class", lambda rank, *_: rank is not None and rank <= 25),
         "fours": ("Sign three four-stars or better", lambda rank, com, *_: sum(1 for r in com if r.stars >= 4) >= 3),
         "needs": ("Fill every position need", lambda rank, com, needs: all(
             sum(1 for r in com if r.position == p) >= n for p, n in needs.items() if n > 0)),
         "conf": ("Best class in the conference", None)}


def _war_order(team, cycle):
    order = [r for r in team.__dict__.setdefault("war_order", []) if r in team.recruiting_targets]
    for r in cycle.board_for(team):
        if r not in order:
            order.append(r)
    team.war_order = order
    return order


def war_room(league, team):
    cycle = league.recruiting
    msg = ""
    tiers = team.__dict__.setdefault("war_tiers", {})
    while True:
        clear()
        color = league.conference_color(team.conference)
        order = _war_order(team, cycle)
        com = cycle.commitments(team)
        rank = cycle.class_rank(team)
        needs = cycle._needs(team)
        print(title_bar(f"WAR ROOM  ·  {team.school.upper()}  ·  {league.year + 1} CLASS", color))
        # needs strip
        got = Counter(r.position for r in com)
        cells = []
        for pos in ROSTER_SIZE:
            n = needs.get(pos, 0)
            if n <= 0:
                continue
            col = C.BGREEN if got[pos] >= n else C.BYELLOW if got[pos] else C.BRED
            cells.append(paint(f"{pos} {got[pos]}/{n}", col, C.BOLD))
        print("  " + paint("NEEDS ", C.GRAY) + "  ".join(cells))
        gk = getattr(team, "class_goal", None)
        if gk:
            label, test = GOALS[gk]
            if gk == "conf":
                mine = cycle.class_score(team)
                ok = all(cycle.class_score(t) <= mine for t in league.teams if t.conference == team.conference)
            else:
                ok = test(rank, com, needs)
            print(f"  {paint('CLASS GOAL', C.GRAY)} {paint(label, C.BWHITE, C.BOLD)}  "
                  + (paint("✔ on track", C.BGREEN, C.BOLD) if ok else paint("not there yet", C.BYELLOW)))
        print(f"  {paint('CLASS', C.GRAY)} {len(com)} commits · "
              + (f"No. {rank} nationally" if rank else "unranked") + "   "
              + paint("Your order is the order you work — nobody else sees it.", C.GRAY))
        print()
        print(paint(f"  {'#':>3}  {'TIER':<6}{'PLAYER':<22}{'POS':<4}{'':<6}{'PROJ':<8}{'STANDING':<15}{'STATUS':<18}"
                    f"{'CRYSTAL BALL':<18}{'OV':<4}Q", C.GRAY, C.BOLD))
        import scout
        for i, r in enumerate(order, 1):
            lo, hi = r.scouting_range(team)
            tier = tiers.get(id(r), 0)
            tcol = {1: C.BGREEN, 2: C.BCYAN, 3: C.GRAY}.get(tier, C.GRAY)
            pc = rp.public_commit(r, team)
            status = paint("◆ yours · " + rp.commit_word(r).split(" ·")[0], C.BGREEN) if r.committed_to is team else \
                paint(f"◆ {truncate(pc.school, 12)}", C.BRED) if pc else paint("open", C.GRAY)
            cb = rp.crystal(r, league.recruiting)
            cbt = paint(f"{truncate(cb[0].school, 11)} {cb[1]}%", C.BGREEN if cb[0] is team else C.GRAY) if cb else ""
            ov = "✔" if team in rp.ov_of(r) else ""
            nq = sum(1 for e in rp.queue(cycle, team) if e["r"] is r)
            st = r.standing(team) if r.interest.get(team) else "NO CONTACT"
            print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {paint(pad(('T' + str(tier)) if tier else '—', 6), tcol, C.BOLD)}"
                  f"{pad(truncate(r.player.name, 21), 22)}{paint(pad(r.position, 4), C.BCYAN)}{pad(_stars(r.stars), 6)}"
                  f"{pad(scout.proj_short(lo, hi), 8)}{pad(st, 15)}{pad(status, 18)}{pad(cbt, 18)}"
                  f"{pad(paint(ov, C.BGREEN), 4)}{paint(str(nq) if nq else '', C.BYELLOW)}")
        if not order:
            print(paint("  Your board is empty.", C.BYELLOW))
        pipes = sorted(rp.pipelines(team).items(), key=lambda x: -x[1])[:6]
        if pipes:
            print()
            print(section("PIPELINES", C.BCYAN))
            print("   " + "   ".join(f"{k.split('|')[0]} ({k.split('|')[1]}) {paint(rp.pipe_word(v), C.BGREEN if v >= 45 else C.GRAY)}"
                                     for k, v in pipes))
        items = [key("#", "card"), key("M a b", "move"), key("T#", "tier"), key("G", "class goal"),
                 key("H", "hit or bust"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        if msg:
            print(paint("  " + msg, C.BCYAN, C.BOLD))
            msg = ""
        c = ask("War room:").strip().lower()
        parts = c.split()
        if c in ("", "b"):
            return
        if len(parts) == 3 and parts[0] == "m" and parts[1].isdigit() and parts[2].isdigit():
            a, b = int(parts[1]) - 1, int(parts[2]) - 1
            if 0 <= a < len(order) and 0 <= b < len(order):
                order.insert(b, order.pop(a))
                team.war_order = order
        elif c.startswith("t") and c[1:].isdigit() and 1 <= int(c[1:]) <= len(order):
            r = order[int(c[1:]) - 1]
            tiers[id(r)] = (tiers.get(id(r), 0) + 1) % 4
        elif c == "g":
            ks = list(GOALS)
            for i, k in enumerate(ks, 1):
                print(f"   {key(str(i), GOALS[k][0])}")
            v = ask("Class goal (Enter = none):").strip()
            team.class_goal = ks[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(ks) else None
        elif c == "h":
            hit_or_bust(league, team)
        elif c.isdigit() and 1 <= int(c) <= len(order):
            import recruiting_screens
            recruiting_screens.recruit_card(league, team, order[int(c) - 1])


def hit_or_bust(league, team):
    clear()
    color = league.conference_color(team.conference)
    print(title_bar(f"HIT OR BUST  ·  {team.school.upper()}", color))
    book = [e for e in team.__dict__.get("signing_book", []) if not e.get("pwo")]
    if not book:
        print(paint("\n   No signing classes on the books yet. The first one arrives after signing day.", C.GRAY))
        pause()
        return
    graded = [(e,) + rp.verdict(e, league) for e in book]
    print(paint("   Hit: playing like his stars said (or better). Steal: a three-star or less who became a real player.\n"
                "   Bust: two years in and nowhere close. Graded on what he is now.", C.GRAY))
    print()
    print(section("BY STAR RATING", C.BCYAN))
    for s in (5, 4, 3, 2):
        g_ = [x for x in graded if x[0]["stars"] == s and x[1] != "too early"]
        if not g_:
            continue
        hits = sum(1 for x in g_ if x[1] in ("hit", "steal"))
        busts = sum(1 for x in g_ if x[1] == "bust")
        print(f"   {paint(pad(str(s) + '★', 4), C.BYELLOW, C.BOLD)}{len(g_):>3} signed   "
              f"{paint(f'{hits} hit', C.BGREEN)} ({hits * 100 // len(g_)}%)   {paint(f'{busts} bust', C.BRED)}")
    steals = sorted((x for x in graded if x[1] == "steal"), key=lambda x: -x[2])[:5]
    busts = sorted((x for x in graded if x[1] == "bust"), key=lambda x: (-x[0]["stars"], x[2]))[:5]
    import scout
    for title, rows, col in (("BEST STEALS", steals, C.BGREEN), ("BIGGEST MISSES", busts, C.BRED)):
        print()
        print(section(title, col))
        if not rows:
            print(paint("   None yet.", C.GRAY))
        for e, v, ovr in rows:
            p = e["player"]
            print(f"   {paint(str(e['year']), C.GRAY)}  {pad(p.name, 22)}{pad(e['pos'], 4)}{pad(_stars(e['stars']), 6)}"
                  f"now {scout.ovr_plain(ovr)}" + paint(f"  · {e['hs']}" if e.get("hs") else "", C.GRAY))
    print()
    print(section("BY CLASS", C.BYELLOW))
    for yr in sorted({e["year"] for e in book}, reverse=True)[:6]:
        g_ = [x for x in graded if x[0]["year"] == yr]
        cnt = Counter(v for _, v, _ in g_)
        print(f"   {yr}  {len(g_):>2} signed   " + "  ".join(f"{k} {n}" for k, n in cnt.most_common()))
    pause()


# ═══ Summer camp and walk-ons ═══════════════════════════════════════════════

def camp_screen(league, team):
    cycle = league.recruiting
    if league.week != 0:
        return "Camps are a summer thing — they happen in the preseason."
    if rp.S(cycle)["camp"].get(team):
        return "You've already held camp this summer."
    board = [r for r in cycle.board_for(team) if not r.signed]
    clear()
    print(title_bar(f"SUMMER CAMP  ·  {team.school.upper()}", C.BCYAN))
    print(paint(f"\n  Invite up to {rp.CAMP_MAX} from your board. They work out on campus in front of your staff:\n"
                "  you learn a lot more about them (and they about you). Kids from far away with big offers may pass.\n",
                C.GRAY))
    for i, r in enumerate(board, 1):
        print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(r.player.name, 23)}{paint(pad(r.position, 4), C.BCYAN)}"
              f"{pad(_stars(r.stars), 6)}{paint(rp.origin_line(r), C.GRAY)}")
    if not board:
        pause("Your board is empty — add recruits first. Press Enter...")
        return ""
    c = ask(f"Who's invited? (e.g. 1,3,5-9; Enter = the top {min(rp.CAMP_MAX, len(board))})").strip()
    picks = []
    if not c:
        picks = board[:rp.CAMP_MAX]
    else:
        for part in c.replace(" ", "").split(","):
            if "-" in part:
                a, _, b = part.partition("-")
                if a.isdigit() and b.isdigit():
                    picks += board[int(a) - 1:int(b)]
            elif part.isdigit() and 1 <= int(part) <= len(board):
                picks.append(board[int(part) - 1])
    out, note = rp.run_camp(cycle, team, picks)
    print()
    print(section("CAMP REPORT", C.BYELLOW))
    for r, v in out:
        col = C.BGREEN if "better" in v else C.BRED if "didn't" in v else C.GRAY
        print(f"   {pad(r.player.name, 23)}{pad(r.position, 4)}{paint(v, col)}")
    pause()
    return note


def walkons_screen(league, team):
    cycle = league.recruiting
    msg = ""
    while True:
        clear()
        print(title_bar(f"PREFERRED WALK-ONS  ·  {team.school.upper()}", C.BCYAN))
        mine = rp.pwo_list(cycle, team)
        print(paint(f"\n  No scholarship — a roster spot and a chance. They join after signing day if nobody else signs them.\n"
                    f"  The good ones earn a scholarship. You can bring in {rp.PWO_MAX}.  Invited: {len(mine)}", C.GRAY))
        for r in mine:
            print(f"   {paint('✔', C.BGREEN)} {pad(r.player.name, 23)}{pad(r.position, 4)}{pad(_stars(r.stars), 6)}"
                  + paint(rp.origin_line(r), C.GRAY))
        needs = cycle._needs(team)
        pool = [r for r in cycle.pool if not r.signed and r.committed_to is None and (r.stars <= 2 or rp.g(r, "kind") == "intl")
                and needs.get(r.position, 0) > 0 and r not in mine]
        pool.sort(key=lambda r: -(sum(r.scouting_range(team)) + r.interest.get(team, 0)))
        pool = pool[:20]
        print()
        print(section("CANDIDATES AT POSITIONS YOU NEED", C.BYELLOW))
        import scout
        for i, r in enumerate(pool, 1):
            lo, hi = r.scouting_range(team)
            print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(r.player.name, 23)}{paint(pad(r.position, 4), C.BCYAN)}"
                  f"{pad(_stars(r.stars), 6)}{pad(scout.proj_short(lo, hi), 8)}{paint(rp.origin_line(r), C.GRAY)}")
        if msg:
            print(paint("  " + msg, C.BCYAN, C.BOLD))
            msg = ""
        c = ask("Invite # (Enter = back):").strip()
        if c.isdigit() and 1 <= int(c) <= len(pool):
            ok, msg = rp.add_pwo(cycle, team, pool[int(c) - 1])
        else:
            return


# ═══ National Signing Day, live ═════════════════════════════════════════════

def signing_day_live(league, report, team=None):
    live = getattr(report, "live", None) or []
    if not live:
        return
    mine = [x for x in live if team is not None and (x["r"] in getattr(team, "recruiting_targets", [])
                                                     or x["pick"] is team or team in x["hats"])]
    national = [x for x in live if x not in mine and x["kind"] != "signed"]
    national.sort(key=lambda x: x["r"].national_rank)
    clear()
    print(title_bar(f"NATIONAL SIGNING DAY  ·  {report.year}  ·  LIVE", C.BYELLOW))
    c = ask("[W] watch it live (the hats, one at a time)   [Enter] just the results").strip().lower()
    slow = c == "w"
    clear()
    print(title_bar(f"NATIONAL SIGNING DAY  ·  {report.year}", C.BYELLOW))

    def beat(t):
        if slow:
            time.sleep(t)

    def show(x, yours):
        r = x["r"]
        head = f"{r.stars}★ {r.position} {r.player.name}  ·  {rp.origin_line(r)}"
        print("\n" + paint("   " + head, C.BWHITE, C.BOLD))
        if x["kind"] == "signed":
            col = C.BGREEN if x["pick"] is team else C.GRAY
            print(paint(f"      Signs with {x['pick'].school}, as expected.", col))
            return
        hats = x["hats"]
        print(paint("      On the table: " + "  ·  ".join(h.school for h in hats), C.GRAY), flush=True)
        beat(0.9)
        if x["kind"] == "flip":
            print(paint(f"      He was committed to {x['fav'].school}...", C.GRAY), flush=True)
            beat(0.9)
        print(paint("      He reaches for", C.GRAY), end="", flush=True)
        for _ in range(3):
            beat(0.45)
            print(paint(".", C.GRAY), end="", flush=True)
        beat(0.5)
        pick = x["pick"]
        col = C.BGREEN if pick is team else C.BRED if (team in hats and pick is not team) else C.BYELLOW
        word = "FLIPS TO " if x["kind"] == "flip" else ""
        print(" " + paint(f"{word}{pick.school.upper()}!", col, C.BOLD), flush=True)
        if x.get("why") and x["fav"] is not None and x["fav"] is not pick:
            who = "You" if x["fav"] is team else x["fav"].school
            print(paint(f"      {who} {'were' if who == 'You' else 'was'} his first choice — but {x['why']}.",
                        C.BRED if x["fav"] is team else C.GRAY, C.BOLD if x["fav"] is team else ""))
        elif x["fav"] is not None and x["fav"] is not pick and x["kind"] == "pick" and x["fav"] in hats:
            print(paint(f"      A surprise — {x['fav'].school} was the favorite.", C.GRAY))
        beat(0.6)

    if mine:
        print(section("YOUR BOARD", C.BCYAN))
        for x in sorted(mine, key=lambda x: (x["kind"] == "signed", x["r"].national_rank)):
            show(x, True)
    if national:
        print()
        print(section("AROUND THE COUNTRY", C.BYELLOW))
        for x in national[:8]:
            show(x, False)
    flips = getattr(report, "flips", [])
    if flips:
        print()
        print(paint(f"   {len(flips)} signing-day flip{'s' if len(flips) != 1 else ''} nationally: "
                    + ", ".join(f"{r.player.name} ({a.school} → {b.school})" for r, a, b in flips[:5]), C.BMAGENTA))
    lost = [(r, why) for r, fav, why in getattr(report, "blocked", []) if fav is team] + list(getattr(report, "cut", []))
    if lost:
        print()
        print(section("WHO YOU COULDN'T TAKE", C.BRED))
        for r, why in lost:
            print(paint(f"   {r.stars}★ {r.position} {r.player.name}: {why}.", C.BRED))
    pause()



def room_check(league, cycle, team, r, why, klass, leftovers):
    """Signing day: a kid who wants you most can't sign. Make room, offer, or let him go.
    Returns True if something changed."""
    import recruiting as rc
    clear()
    print(title_bar("SIGNING DAY  ·  DECISION", C.BRED))
    print(paint(f"\n   {r.stars}★ {r.position} {r.player.name} (No. {r.national_rank}) wants {team.school} more than anyone.",
                C.BWHITE, C.BOLD))
    print(paint(f"   But {why}.", C.BRED, C.BOLD))
    can_offer = team not in r.offers
    same = [x for x in klass if x.position == r.position]
    others = sorted(klass, key=lambda x: (x.stars, -x.national_rank))
    print()
    if can_offer:
        print(f"   {paint('[O]', C.BGREEN, C.BOLD)} offer him a scholarship now")
    if klass:
        print(f"   {paint('[D]', C.BYELLOW, C.BOLD)} drop a signee to make room "
              f"(he'll sign somewhere else){' — ' + str(len(same)) + ' at ' + r.position if same else ''}")
    print(f"   {paint('[Enter]', C.GRAY)} let him go")
    ch = ask("Your call:").strip().lower()
    if ch == "o" and can_offer:
        r.offers.add(team)
        print(paint(f"   Offer extended to {r.player.name}.", C.BGREEN))
        if rc.block_reason(league, team, r, klass, True) is None:
            pause()
            return True
        why = rc.block_reason(league, team, r, klass, True)
        print(paint(f"   Still a problem: {why}.", C.BYELLOW))
        ch = "d" if klass else ""
    if ch == "d" and klass:
        pool = same if "room left at" in (rc.block_reason(league, team, r, klass, True) or "") else others
        pool = pool or others
        for i, x in enumerate(pool[:15], 1):
            print(f"   {i:>2}  {x.stars}★ {pad(x.position, 4)}{pad(x.player.name, 24)}No. {x.national_rank}")
        sel = ask("Drop # (Enter = cancel):").strip()
        if sel.isdigit() and 1 <= int(sel) <= min(15, len(pool)):
            x = pool[int(sel) - 1]
            klass.remove(x)
            x.signed = False
            x.committed_to = None
            x.interest[team] = x.interest.get(team, 0) * 0.3
            if x in cycle.class_cache.get(team, []):
                cycle.class_cache[team].remove(x)
            leftovers.append(x)                               # he'll pick from his other schools
            league.__dict__.setdefault("career_log", []).append(
                (league.year, f"Signing day: dropped {x.player.name} to make room for {r.player.name}."))
            print(paint(f"   {x.player.name} is released from his signing. Room made.", C.BYELLOW))
            pause()
            return True
    return False
