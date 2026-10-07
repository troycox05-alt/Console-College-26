"""
portal_screens.py — Your transfer portal window.

After everyone enters and before anyone lands, you get a window of hours:

  Contact        8 hrs   learn how interested he is in your program
  Pitch         12 hrs   raise his interest
  Official visit 22 hrs  raise it a lot (once per player)
  Offer a spot   free    he can only choose you if you've offered — up to 8 offers
  NIL offer      free    money on top of the spot; held against your budget until he picks
  Keep him       16 hrs  one of YOUR players who entered: try to talk him into withdrawing
                         (a NIL raise helps)

Your staff stops bidding on its own; the players you land are the ones you went after.
"""
import random

import finance as fi
from portal import MAX_INCOMING, base_interest, team_needs
from ui import C, WIDTH, ask, clear, pad, paint, pause, rating, rule, section, title_bar, truncate

COST = {"contact": 8, "pitch": 12, "visit": 22, "keep": 16}
PAGE = 20


def _level(x):
    return "Very high" if x >= 0.85 else "High" if x >= 0.65 else "Medium" if x >= 0.4 else "Low" if x >= 0.2 else "Very low"


def _market(league, entry):
    """Stable public read of the player's market: heat plus his current top five."""
    import portal
    scored = []
    for t in league.teams:
        if t is entry.origin:
            continue
        r = random.Random(f"portal-market:{league.seed}:{league.year}:{entry.player.name}:{t.school}")
        scored.append((portal.player_choice(league, league.recruiting, t, entry, r), t))
    scored.sort(key=lambda x: -x[0])
    top = [t for _, t in scored[:5]]
    if not scored:
        return "Quiet", top, 0
    best = scored[0][0]
    serious = sum(1 for score, _ in scored if score >= best * .90)
    heat = "National frenzy" if serious >= 8 else "Heavy" if serious >= 5 else "Active" if serious >= 3 else "Light"
    return heat, top, serious


def _mine(league, report):
    """This coach's portal-window data; in Hot Seat, the coach currently on the keyboard."""
    t = getattr(league, "user_team", None)
    for u in getattr(report, "users", None) or []:
        if u["team"] is t:
            return u
    return getattr(report, "user", None) or {}


def portal_window(league, report):
    team = league.user_team
    if team is None:
        return
    # Phase 2: the portal is open for multiple offseason weeks. Keep the same
    # board, offers, visits and knowledge when the coach comes back next week.
    users = report.__dict__.setdefault("users", [])
    user = next((u for u in users if u.get("team") is team), None)
    try:
        import offseason_cal
        ow = int(offseason_cal._state(league).get("week") or 0)
    except Exception:
        ow = 0
    if user is None:
        hours = league.recruiting.hours_for(team) * 2
        user = {"team": team, "offers": set(), "interest": {}, "known": {}, "visited": set(), "hours": hours,
                "kept": [], "lost_keep": [], "portal_week": ow, "pitched_week": {}}
        users.append(user)
    elif user.get("portal_week") != ow:
        # Opening week is the big contact period; later weeks add a smaller
        # fresh allotment for follow-ups and late entries.
        user["hours"] = user.get("hours", 0) + league.recruiting.hours_for(team)
        user["portal_week"] = ow
    user.setdefault("pitched_week", {})
    report.user = user
    rng = random.Random(f"portalwin:{league.seed}:{league.year}:{ow}")
    leaving = [e for e in report.entries if e.origin is team]
    pos_filter, page = None, 0
    while True:
        clear()
        needs = team_needs(team)
        print(title_bar(f"TRANSFER PORTAL WINDOW  ·  {team.school.upper()}"))
        print(f"   {paint('Hours left', C.GRAY)} {paint(str(user['hours']), C.BWHITE, C.BOLD)}   "
              f"{paint('Offers out', C.GRAY)} {paint(str(len(user['offers'])) + '/' + str(MAX_INCOMING), C.BWHITE, C.BOLD)}   "
              f"{paint('Entrants', C.GRAY)} {len(report.entries)}   "
              f"{paint('Leaving you', C.GRAY)} {paint(str(len([e for e in leaving if e.player not in team.roster])), C.BRED, C.BOLD)}   "
              f"{paint('NIL free', C.GRAY)} {paint(fi.money(fi.portal_room(league, team, report)), C.BGREEN, C.BOLD)}")
        holes = [p for p, (short, q, room) in needs.items() if short > 0]
        if holes:
            print(paint(f"   Starting holes: {', '.join(holes)}", C.BYELLOW))
        print(rule())
        pool = [e for e in report.entries if e.origin is not team and e.destination is None
                and (pos_filter is None or e.position == pos_filter)]
        pool.sort(key=lambda e: -e.overall)
        pages = max(1, (len(pool) + PAGE - 1) // PAGE)
        page = min(page, pages - 1)
        print(paint(f"   {'#':>3}  {'PLAYER':<22}{'POS':<5}{'OVR':>4}  {'YR':<7}{'FROM':<18}{'WANTS':<30}"
                    f"{'MARKET':>14}  INTEREST", C.GRAY, C.BOLD))
        for i, e in enumerate(pool[page * PAGE:(page + 1) * PAGE], page * PAGE + 1):
            known = user["known"].get(e)
            interest = user["interest"].get(e, 0)
            tag = paint(_level(min(1, known + interest * 0.5)), C.BCYAN) if known is not None else paint("?", C.GRAY)
            heat, top5, serious = _market(league, e)
            market = f"{heat} · {serious}"
            mark = paint(" ✓ offered", C.BGREEN) if e in user["offers"] else ""
            if report.nil.get((team, e)):
                mark += paint(f" · {fi.money(report.nil[(team, e)])} NIL", C.BGREEN)
            if e in user["visited"]:
                mark += paint(" · visited", C.BMAGENTA)
            print(f"   {paint(f'{i:>3}', C.BYELLOW)}  {pad(truncate(e.player.name, 21), 22)}{e.position:<5}"
                  f"{__import__('scout').ovr_short(e.overall)}  {e.player.class_label:<7}{pad(truncate(e.origin.school, 17), 18)}"
                  f"{paint(pad(truncate(__import__('portal').PRIORITY_WORD.get(getattr(e, 'priority', ''), e.reason), 29), 30), C.BYELLOW)}"
                  f"{pad(market, 14, 'right')}  "
                  f"{tag}{mark}")
        print(rule())
        print(f"   {paint('[#]', C.BYELLOW)} work on a player   {paint('[Y]', C.BYELLOW)} your players who entered   "
              f"{paint('[F]', C.BYELLOW)} filter by position   {paint('[N/P]', C.BYELLOW)} page {page + 1}/{pages}   "
              f"{paint('[D]', C.BGREEN, C.BOLD)} done — close the window")
        c = ask("Select:").strip().lower()
        if c == "d":
            return
        if c == "n":
            page = (page + 1) % pages
        elif c == "p":
            page = (page - 1) % pages
        elif c == "f":
            pos = ask("Position (QB RB WR TE OL DL LB CB S K P, Enter = all):").strip().upper()
            pos_filter = pos if pos else None
            page = 0
        elif c == "y":
            keep_screen(league, report, user, leaving, rng)
        elif c.isdigit() and 1 <= int(c) <= len(pool):
            player_card(league, report, user, pool[int(c) - 1])


def player_card(league, report, user, e):
    team = user["team"]
    while True:
        clear()
        p = e.player
        print(title_bar(f"{p.name.upper()}  ·  {e.position}  ·  {e.origin.school.upper()}"))
        blk = []
        blk.append(f"   {__import__('scout').ovr(e.overall)} overall   {p.class_label}   from {getattr(p, 'home_state', '') or '—'}")
        blk.append(paint(f"   Left because: {e.reason}", C.GRAY))
        import portal as _po
        blk.append(paint(f"   What he wants most: {_po.PRIORITY_WORD.get(getattr(e, 'priority', ''), 'a fresh start')} — sell him on that.", C.BYELLOW, C.BOLD))
        heat, top5, serious = _market(league, e)
        blk.append(paint(f"   Market interest: {heat} — {serious} serious team" + ("s" if serious != 1 else "") + ".", C.BMAGENTA))
        blk.append(paint("   Current Top 5: " + (", ".join(t.school for t in top5) if top5 else "No clear leaders yet"), C.BMAGENTA))
        known = user["known"].get(e)
        if known is not None:
            level = _level(min(1, known + user["interest"].get(e, 0) * 0.5))
            blk.append(f"   Interest in {team.school}: {paint(level, C.BCYAN, C.BOLD)}")
        else:
            blk.append(paint("   Interest in you: unknown — contact him to find out.", C.GRAY))
        mine = report.nil.get((team, e), 0)
        blk.append(f"   {paint('NIL market', C.GRAY)} about {fi.money(fi.transfer_market(e.player))}/yr   "
                   f"{paint('Your NIL offer', C.GRAY)} " + (paint(fi.money(mine) + '/yr', C.BGREEN, C.BOLD) if mine else paint('none', C.GRAY))
                   + f"   {paint('Free to offer', C.GRAY)} {fi.money(fi.portal_room(league, team, report))}")
        if known is not None:
            a = fi.player_appetite(p)
            blk.append(paint("   " + ("Money matters a lot to him." if a >= 1.25 else "Money is part of it." if a >= 0.85 else "Money isn't what he's chasing."), C.GRAY))
        need = team_needs(team)[e.position]
        if need[0] > 0:
            blk.append(paint(f"   He'd start for you — you have a hole at {e.position}.", C.BGREEN))
        elif e.overall > need[1]:
            blk.append(paint(f"   He'd push your starter at {e.position} ({need[1]} overall).", C.BYELLOW))
        import faces
        if faces.enabled():
            import faces_ui
            for ln in faces_ui.beside(faces.player_portrait(p, team=e.origin, year=faces.class_year(p.class_label), mini=True), blk, indent=0, gap=1):
                print(ln)
        else:
            for ln in blk:
                print(ln)
        print(rule())
        print(f"   {paint('[1]', C.BYELLOW)} Contact ({COST['contact']} hrs)   {paint('[2]', C.BYELLOW)} Pitch ({COST['pitch']} hrs)   "
              f"{paint('[3]', C.BYELLOW)} Official visit ({COST['visit']} hrs)   "
              f"{paint('[O]', C.BGREEN)} {'Withdraw offer' if e in user['offers'] else 'Offer a roster spot'}   "
              f"{paint('[N]', C.BGREEN)} NIL offer   {paint('[B]', C.GRAY)} back      hours left: {user['hours']}")
        c = ask("Select:").strip().lower()
        if c == "b" or c == "":
            return
        if c == "n":
            _nil_offer(league, report, team, e)
            continue
        if c == "o":
            if e in user["offers"]:
                user["offers"].discard(e)
                report.nil.pop((team, e), None)                # no spot, no money
            elif len(user["offers"]) >= MAX_INCOMING:
                print(paint(f"   You can only have {MAX_INCOMING} offers out.", C.BRED))
                pause()
            else:
                user["offers"].add(e)
            continue
        action = {"1": "contact", "2": "pitch", "3": "visit"}.get(c)
        if action is None:
            continue
        if action == "contact" and e in user["known"]:
            print(paint("   You already have contact established. Use a pitch or visit to move the recruitment.", C.GRAY))
            pause()
            continue
        if action in ("pitch", "visit") and e not in user["known"]:
            print(paint("   Establish contact first. You need to know where you stand before spending bigger resources.", C.BRED))
            pause()
            continue
        if action == "pitch" and user["pitched_week"].get(e) == user.get("portal_week"):
            print(paint("   Your staff already made its full pitch to him this portal week. Follow up next week or use a visit.", C.GRAY))
            pause()
            continue
        if user["hours"] < COST[action]:
            print(paint("   Not enough hours left.", C.BRED))
            pause()
            continue
        if action == "visit" and e in user["visited"]:
            print(paint("   He's already been on campus.", C.GRAY))
            pause()
            continue
        user["hours"] -= COST[action]
        if action == "contact" or e not in user["known"]:
            user["known"][e] = base_interest(league, team, e)
        if action == "pitch":
            user["interest"][e] = min(1.0, user["interest"].get(e, 0) + 0.12)
            user["pitched_week"][e] = user.get("portal_week")
        elif action == "visit":
            user["interest"][e] = min(1.0, user["interest"].get(e, 0) + 0.28)
            user["visited"].add(e)


def _nil_offer(league, report, team, e):
    if e not in report.__dict__.get("user", {}).get("offers", set()):
        print(paint("   Offer him a roster spot first — the money goes on top of the spot.", C.BRED))
        pause()
        return
    mine = report.nil.get((team, e), 0)
    room = fi.portal_room(league, team, report) + mine
    print(paint(f"   Market for him: about {fi.money(fi.transfer_market(e.player))}/yr.  You can offer up to "
                f"{fi.money(room)}.  Money moves him; it won't sign him by itself.", C.GRAY))
    raw = ask("NIL per year (e.g. 150k, 1.1m, 0 to pull it, Enter to cancel):").strip()
    if not raw:
        return
    amt = fi.parse_money(raw)
    if amt is None:
        return
    amt = fi._round(amt, 1_000)
    if amt > room:
        import budget_fix
        budget_fix.cover(league, team, amt, f"NIL for transfer {e.player.name}: {fi.money(amt)}/yr",
                         free_fn=lambda: fi.portal_room(league, team, report) + mine)
        room = fi.portal_room(league, team, report) + mine
    if amt > room:
        print(paint(f"   You only have {fi.money(room)} to offer.", C.BRED))
        pause()
        return
    if amt <= 0:
        report.nil.pop((team, e), None)
    else:
        report.nil[(team, e)] = amt


def keep_screen(league, report, user, leaving, rng):
    team = user["team"]
    while True:
        clear()
        print(title_bar(f"YOUR PLAYERS IN THE PORTAL  ·  {team.school.upper()}"))
        out = [e for e in leaving if e.player not in team.roster]
        if not out and not user["kept"]:
            print(paint("   Nobody from your roster entered the portal.", C.GRAY))
            pause()
            return
        for i, e in enumerate(out, 1):
            print(f"   {paint(f'{i:>2}', C.BYELLOW)}  {pad(e.player.name, 22)}{e.position:<5}{__import__('scout').ovr_short(e.overall)}  "
                  f"{e.player.class_label:<7}{paint(e.reason, C.GRAY)}")
        for p in user["kept"]:
            print(f"   {paint('  ✓', C.BGREEN)}  {pad(p.name, 22)}{p.position:<5}{__import__('scout').ovr_short(p.overall)}  "
                  f"{paint('withdrew — staying', C.BGREEN)}")
        print(rule())
        c = ask(f"Talk to # ({COST['keep']} hrs, {user['hours']} left) — Enter = back:").strip()
        if not c.isdigit() or not 1 <= int(c) <= len(out):
            return
        e = out[int(c) - 1]
        if user["hours"] < COST["keep"]:
            print(paint("   Not enough hours left.", C.BRED))
            pause()
            continue
        # A raise can help keep him — money he'd be paid out of next season's budget.
        before = getattr(e.player, "nil_before_portal", 0)
        room = fi.portal_room(league, team, report)
        print(paint(f"   He was making {fi.money(before)}/yr here. Market for him: about "
                    f"{fi.money(fi.transfer_market(e.player))}. Free to offer: {fi.money(room)}.", C.GRAY))
        raw = ask("Offer a new NIL figure to stay (Enter = keep his old deal):").strip()
        new_amt = before
        if raw:
            v = fi.parse_money(raw)
            if v is not None and v - before > room:
                import budget_fix
                budget_fix.cover(league, team, v - before, f"a raise to keep {e.player.name}",
                                 free_fn=lambda: fi.portal_room(league, team, report))
                room = fi.portal_room(league, team, report)
            if v is not None and v - before <= room:
                new_amt = fi._round(max(0, v), 1_000)
            elif v is not None:
                print(paint(f"   You don't have that much free — sticking with {fi.money(before)}.", C.BRED))
        user["hours"] -= COST["keep"]
        # Easier to keep a starter who left over a coaching change than a backup who wants to play.
        import staff
        odds = 0.35 + (0.2 if e.depth <= 1 else 0) + staff.recruiting_rating(team) / 400
        if "playing" in e.reason or "depth" in e.reason:
            odds -= 0.15
        raise_amt = new_amt - before
        if raise_amt > 0:
            odds += 0.3 * min(1.0, raise_amt / fi.transfer_market(e.player)) * fi.player_appetite(e.player)
        if rng.random() < odds:
            report.entries.remove(e)
            report.by_team_out[team].remove(e)
            team.add_player(e.player)
            e.player.nil = new_amt                                    # he stays, on the deal that kept him
            user["kept"].append(e.player)
            print(paint(f"   {e.player.name} is pulling his name out of the portal. He's staying.", C.BGREEN, C.BOLD))
        else:
            print(paint(f"   {e.player.name} appreciated the talk. He's still leaving.", C.BRED))
        pause()


def window_results(league, report):
    """After the portal resolves: how your window went."""
    user = _mine(league, report) or None
    if user is None:
        return
    team = user["team"]
    clear()
    print(title_bar(f"PORTAL RESULTS  ·  {team.school.upper()}"))
    landed = [e for e in report.entries if e.destination is team]
    missed = [e for e in user["offers"] if e.destination is not team]
    print(section(f"YOU LANDED {len(landed)}", C.BGREEN))
    for e in landed:
        deal = report.__dict__.get("deals", {}).get(e, 0)
        print(f"   {pad(e.player.name, 22)}{e.position:<5}{__import__('scout').ovr_short(e.overall)}  from {pad(e.origin.school, 20)}"
              + (paint(f"NIL {fi.money(deal)}/yr", C.BGREEN) if deal else paint("no NIL", C.GRAY)))
    if not landed:
        print(paint("   Nobody this time.", C.GRAY))
    if missed:
        print()
        print(section("GOT AWAY", C.BRED))
        for e in missed:
            where = e.destination.school if e.destination else "stayed unsigned"
            deal = report.__dict__.get("deals", {}).get(e, 0)
            extra = f" ({fi.money(deal)}/yr)" if deal and e.destination else ""
            print(f"   {pad(e.player.name, 22)}{e.position:<5}{__import__('scout').ovr_short(e.overall)}  chose {where}{extra}")
    if user["kept"]:
        print()
        print(section("TALKED OUT OF LEAVING", C.BCYAN))
        for p in user["kept"]:
            print(f"   {pad(p.name, 22)}{p.position:<5}{__import__('scout').ovr_short(p.overall)}")
    pause()
