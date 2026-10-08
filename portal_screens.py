"""
portal_screens.py — Your transfer portal window.

After everyone enters and before anyone lands, you work the board. The portal is a
negotiation, not a lottery: every player left for a reason, wants something specific,
and is weighing real offers from real programs. Your job is to find the ones your
program can actually sell to, sell them the right thing, and close before someone else does.

  Contact          4 hrs   where you stand, his second priority, and when he'll decide
  Pitch            8 hrs   pick an angle. It works if (a) he cares about it and (b) your
                           program can back it up. Repeating an angle wears thin.
  Official visit  16 hrs   one per player: a big jump, bigger if your campus sells
  Push to commit   4 hrs   once a week: if you're leading, he can sign right now
  Offer a spot     free    he can only choose you if you've offered (8 per window)
  NIL offer        free    money on top of the spot; held against your budget until he picks
  Keep him        10 hrs   one of YOUR players who entered: talk, a raise, or a promise

Staff hours come fresh every portal week, so the deadline weeks and the post-spring
window are real chances, not leftovers.
"""
import random

import finance as fi
import portal as po
from portal import MAX_INCOMING, base_interest, team_needs
from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

COST = {"contact": 4, "pitch": 8, "visit": 16, "push": 4, "keep": 10}
PAGE = 18

# The cases you can make, and which of his priorities each one answers.
ANGLES = (
    ("playing_time", "Day-one starter"),
    ("winning", "Win now"),
    ("development", "NFL development"),
    ("scheme_fit", "Built for our system"),
    ("proximity", "Closer to home"),
    ("program", "The program"),
    ("money", "The NIL deal"),
)
ANGLE_WORD = dict(ANGLES)
FATIGUE = (1.0, 0.6, 0.35, 0.2)          # the same pitch, again: it lands softer every time


def _level(x):
    return "Very high" if x >= 0.85 else "High" if x >= 0.65 else "Medium" if x >= 0.4 else "Low" if x >= 0.2 else "Very low"


def _letter(g):
    return "A" if g >= 85 else "B" if g >= 70 else "C" if g >= 55 else "D" if g >= 40 else "F"


def _gcol(g):
    return C.BGREEN if g >= 70 else C.BYELLOW if g >= 55 else C.BRED


# ═══ Reads (cached for the week: they're expensive and should stay steady) ════

_CACHE = {}


def _week(league):
    try:
        import offseason_cal
        return int(offseason_cal._state(league).get("week") or 0)
    except Exception:
        return 0


def _cached(key, fn):
    if key not in _CACHE:
        if len(_CACHE) > 4000:
            _CACHE.clear()
        _CACHE[key] = fn()
    return _CACHE[key]


def _market(league, entry):
    """Stable public read of the player's market: heat plus his current top five."""
    def calc():
        scored = []
        for t in league.teams:
            if t is entry.origin:
                continue
            r = random.Random(f"portal-market:{league.seed}:{league.year}:{entry.player.name}:{t.school}")
            scored.append((po.player_choice(league, league.recruiting, t, entry, r), t))
        scored.sort(key=lambda x: -x[0])
        top = [t for _, t in scored[:5]]
        if not scored:
            return "Quiet", top, 0
        best = scored[0][0]
        serious = sum(1 for score, _ in scored if score >= best * .90)
        heat = "National frenzy" if serious >= 8 else "Heavy" if serious >= 5 else "Active" if serious >= 3 else "Light"
        return heat, top, serious
    return _cached(("mkt", league.year, _week(league), entry.player.name, entry.origin.school), calc)


def grades(league, team, entry, report=None):
    """0-100: how strong your case is on each angle, for this player, right now."""
    def calc():
        ps = po.pitch_scores(league, team, po._as_recruit(entry))
        g = {k: ps.get(k, 50) for k in ("playing_time", "winning", "development", "scheme_fit", "proximity")}
        need = team_needs(team)[entry.position]
        if need[0] > 0:
            g["playing_time"] = max(g["playing_time"], 92)          # an actual hole: he starts
        elif entry.overall > need[1] + 3:
            g["playing_time"] = max(g["playing_time"], 75)          # he'd win the job
        g["program"] = (ps.get("facilities", 50) + ps.get("tradition", 50) + ps.get("campus", 50)) / 3
        return g
    g = dict(_cached(("grd", league.year, _week(league), team.school, entry.player.name), calc))
    mine = (report.nil.get((team, entry), 0) if report is not None else 0)
    mkt = max(1, fi.transfer_market(entry.player))
    r = mine / mkt
    g["money"] = 100 if r >= 1.25 else 85 if r >= 1.0 else 70 if r >= 0.8 else 55 if r >= 0.55 else 35 if r > 0 else 10
    return g


def _care(entry, angle, revealed):
    if angle == getattr(entry, "priority", None):
        return 1.0
    if angle == po.second_priority(entry):
        return 0.65
    return 0.3


def _ai_field(league, report, team, entry):
    """The other staffs that would really bid on him, and what they'd put on the table."""
    def calc():
        import staff
        from roster import ROSTER_SIZE
        out = []
        cyc = league.recruiting
        users = po._users(report)
        for t in league.teams:
            if t is team or t is entry.origin or t in users:
                continue
            if len(t.roster) >= sum(ROSTER_SIZE.values()):
                continue
            needs = _cached(("need", league.year, _week(league), t.school, len(t.roster)),
                            lambda t=t: team_needs(t, cyc._class_of(t)))
            v = po.transfer_value(league, t, entry, needs) + po._film_read(t, entry)
            if v <= 0:
                continue
            appeal = v * (0.6 + staff.recruiting_rating(t) / 200) * (0.7 + t.prestige / 140)
            out.append((appeal, t, v))
        out.sort(key=lambda x: -x[0])
        field = []
        for appeal, t, v in out[:5]:
            room = fi.portal_room(league, t, report)
            cash = fi.ai_portal_offer(league, t, entry, appeal, room, po._Mid)
            field.append((t, po.steady_choice(league, t, entry), cash))
        return field
    return _cached(("field", id(report), _week(league), team.school, entry.player.name, len(report.moves)), calc)


def standing(league, report, user, entry):
    """Your staff's read on where you stand: (your place, field size, leader, your score / leader's)."""
    team = user["team"]
    field = _ai_field(league, report, team, entry)
    mine_cash = report.nil.get((team, entry), 0)
    best_cash = max([c for _, _, c in field] + [mine_cash, 0])
    money_x = 2.0 if getattr(entry, "priority", None) == "money" else 1.0
    scores = [(ch * fi.portal_pull(c, best_cash, entry.player) ** money_x, t) for t, ch, c in field]
    me = (po.steady_choice(league, team, entry) * po.user_mult(team, user["interest"].get(entry, 0))
          * fi.portal_pull(mine_cash, best_cash, entry.player) ** money_x * (1 + po.tamper_pull(entry, team)))
    scores.append((me, team))
    scores.sort(key=lambda x: -x[0])
    place = next(i for i, (_, t) in enumerate(scores, 1) if t is team)
    leader = scores[0][1] if scores[0][1] is not team else (scores[1][1] if len(scores) > 1 else None)
    other = scores[1][0] if place == 1 and len(scores) > 1 else scores[0][0]
    return place, len(scores), leader, me / other if other else 9.9


def _standing_word(place, n, ratio):
    if place == 1:
        return paint("Leader" + (" — clear" if ratio >= 1.12 else " — barely"), C.BGREEN, C.BOLD)
    if ratio >= 0.9:
        return paint(f"#{place} of {n} — close", C.BYELLOW, C.BOLD)
    return paint(f"#{place} of {n} — behind", C.BRED)


def _timeline(league, report, entry):
    dw = (report.__dict__.get("decision_week") or {}).get(entry)
    ow = _week(league)
    if dw is None or not ow:
        return "decides when the window closes", C.GRAY
    if dw <= ow:
        return "deciding THIS week", C.BRED
    if dw == ow + 1:
        return "deciding next week", C.BYELLOW
    return "taking his time", C.BGREEN


# ═══ The window ═══════════════════════════════════════════════════════════════

def _mine(league, report):
    """This coach's portal-window data; in Hot Seat, the coach currently on the keyboard."""
    t = getattr(league, "user_team", None)
    for u in getattr(report, "users", None) or []:
        if u["team"] is t:
            return u
    return getattr(report, "user", None) or {}


def _spring(report):
    return "spring" in str(report.__dict__.get("window_name", "")).lower()


def _landed(report, team):
    return [e for e in report.by_team_in.get(team, []) if e.destination is team]


def _slots(report, user):
    return MAX_INCOMING - len(_landed(report, user["team"])) - len([e for e in user["offers"] if e.destination is None])


def portal_window(league, report):
    team = league.user_team
    if team is None:
        return
    users = report.__dict__.setdefault("users", [])
    user = next((u for u in users if u.get("team") is team), None)
    ow = _week(league)
    weekly = league.recruiting.hours_for(team)
    new_week = False
    if user is None:
        # Opening week is the big contact period. The post-spring window is smaller, so the
        # staff can give it a bigger share of its time.
        hours = int(weekly * (2.6 if _spring(report) else 3.0))
        user = {"team": team, "offers": set(), "interest": {}, "known": {}, "visited": set(), "hours": hours,
                "kept": [], "lost_keep": [], "portal_week": ow, "pitched_week": {}}
        users.append(user)
    elif user.get("portal_week") != ow:
        user["hours"] = user.get("hours", 0) + int(weekly * 1.6)    # fresh hours for the follow-up weeks
        user["portal_week"] = ow
        new_week = True
    for k, v in (("pitched_week", {}), ("angles", {}), ("pushed", {}), ("talked", {}), ("log", {}), ("seen_moves", 0)):
        user.setdefault(k, v)
    report.user = user
    if new_week:
        _briefing(league, report, user)
    user["seen_moves"] = len(report.moves)
    rng = random.Random(f"portalwin:{league.seed}:{league.year}:{ow}:{team.school}")
    view = {"pos": None, "fits": False, "sort": "ovr", "page": 0, "targets": False}
    while True:
        clear()
        needs = team_needs(team)
        leaving = [e for e in report.entries if e.origin is team and e.player not in team.roster
                   and "winter window" not in (e.reason or "")]
        print(title_bar(f"TRANSFER PORTAL  ·  {report.__dict__.get('window_name', 'Portal Window').upper()}  ·  {team.school.upper()}"))
        n_off = len([e for e in user["offers"] if e.destination is None])
        print(f"   {paint('Hours', C.GRAY)} {paint(str(user['hours']), C.BWHITE, C.BOLD)}   "
              f"{paint('Spots', C.GRAY)} {paint(f'{_slots(report, user)} open', C.BWHITE, C.BOLD)} "
              f"{paint('(' + str(len(_landed(report, team))) + ' signed · ' + str(n_off) + ' offers)', C.GRAY)}   "
              f"{paint('Leaving', C.GRAY)} {paint(str(len(leaving)), C.BRED, C.BOLD)}   "
              f"{paint('NIL free', C.GRAY)} {paint(fi.money(fi.portal_room(league, team, report)), C.BGREEN, C.BOLD)}")
        holes = [p for p, (short, q, room) in needs.items() if short > 0]
        if holes:
            print(paint(f"   Starting holes: {', '.join(holes)}", C.BYELLOW))
        _staff_board(league, report, team, needs)
        print(rule())
        pool = [e for e in report.entries if e.origin is not team and e.destination is None
                and (view["pos"] is None or e.position == view["pos"])]
        if view["fits"]:
            pool = [e for e in pool if needs[e.position][0] > 0 or e.overall > needs[e.position][1]]
        if view["targets"]:
            pool = [e for e in pool if e in user["known"] or e in user["offers"]]
        if view["sort"] == "soon":
            order = {"deciding THIS week": 0, "deciding next week": 1}
            pool.sort(key=lambda e: (order.get(_timeline(league, report, e)[0], 2), -e.overall))
        elif view["sort"] == "fit":
            pool.sort(key=lambda e: -po.transfer_value(league, team, e, needs))
        else:
            pool.sort(key=lambda e: -e.overall)
        pages = max(1, (len(pool) + PAGE - 1) // PAGE)
        view["page"] = min(view["page"], pages - 1)
        tags = [t for t, on in (("your targets", view["targets"]), ("fits your needs", view["fits"]),
                                (view["pos"] or "", view["pos"]),
                                ({"soon": "deciding soonest", "fit": "best fit"}.get(view["sort"], ""), view["sort"] != "ovr")) if on]
        if tags:
            print(paint("   Showing: " + " · ".join(tags), C.BCYAN))
        print(paint(f"   {'#':>3}  {'PLAYER':<20}{'POS':<4}{'OVR':>4}  {'YR':<6}{'FROM':<15}{'WANTS':<17}{'YOU':<22}", C.GRAY, C.BOLD))
        for i, e in enumerate(pool[view["page"] * PAGE:(view["page"] + 1) * PAGE], view["page"] * PAGE + 1):
            if e in user["known"]:
                pl, n, ld, ratio = standing(league, report, user, e)
                you = _standing_word(pl, n, ratio)
                tl, tc = _timeline(league, report, e)
                if tl == "deciding THIS week":
                    you += paint(" ⏱", C.BRED)
            else:
                heat = _market(league, e)[0]
                you = paint(f"? · {heat.lower()}", C.GRAY)
            mark = paint(" ✓", C.BGREEN) if e in user["offers"] else ""
            print(f"   {paint(f'{i:>3}', C.BYELLOW)}  {pad(truncate(e.player.name, 19), 20)}{e.position:<4}"
                  f"{__import__('scout').ovr_short(e.overall)}  {e.player.class_label:<6}{pad(truncate(e.origin.school, 14), 15)}"
                  f"{paint(pad(truncate(po.PRIORITY_WORD.get(getattr(e, 'priority', ''), e.reason), 16), 17), C.BYELLOW)}"
                  f"{you}{mark}")
        if not pool:
            print(paint("   Nobody on the board matches that view.", C.GRAY))
        print(rule())
        print(f"   {paint('[#]', C.BYELLOW)} work a player   {paint('[T]', C.BYELLOW)} {'all players' if view['targets'] else 'my targets'}   "
              f"{paint('[H]', C.BYELLOW)} {'everyone' if view['fits'] else 'fits my needs'}   {paint('[S]', C.BYELLOW)} sort   "
              f"{paint('[F]', C.BYELLOW)} position   {paint('[N/P]', C.BYELLOW)} page {view['page'] + 1}/{pages}")
        print(f"   {paint('[Y]', C.BYELLOW)} your players who entered ({len(leaving)})   "
              f"{paint('[D]', C.BGREEN, C.BOLD)} done for this week")
        _wv_board(league, report, user, team, needs, holes, leaving, pool, view, pages, tags)
        c = ask("Select:").strip().lower()
        if c == "d":
            return
        if c == "n":
            view["page"] = (view["page"] + 1) % pages
        elif c == "p":
            view["page"] = (view["page"] - 1) % pages
        elif c == "t":
            view["targets"] = not view["targets"]; view["page"] = 0
        elif c == "h":
            view["fits"] = not view["fits"]; view["page"] = 0
        elif c == "s":
            view["sort"] = {"ovr": "fit", "fit": "soon", "soon": "ovr"}[view["sort"]]; view["page"] = 0
        elif c == "f":
            pos = ask("Position (QB RB WR TE OL DL LB CB S K P, Enter = all):").strip().upper()
            view["pos"] = pos if pos else None
            view["page"] = 0
        elif c == "y":
            keep_screen(league, report, user, leaving, rng)
        elif c.isdigit() and 1 <= int(c) <= len(pool):
            player_card(league, report, user, pool[int(c) - 1])


def _wv_who(league, report, user, e):
    if e not in user["known"]:
        return {"known": False, "heat": _market(league, e)[0]}
    pl, n, ld, ratio = standing(league, report, user, e)
    return {"known": True, "place": pl, "of": n, "ratio": round(ratio, 2), "leader": ld.school if ld else "",
            "timeline": _timeline(league, report, e)[0]}


def _wv_board(league, report, user, team, needs, holes, leaving, pool, view, pages, tags):
    import webview
    if not webview.on():
        return
    try:
        rows = []
        for i, e in enumerate(pool[view["page"] * PAGE:(view["page"] + 1) * PAGE], view["page"] * PAGE + 1):
            r = {"i": i, "name": e.player.name, "pos": e.position, "ovr": webview.plain(__import__("scout").ovr_short(e.overall)),
                 "yr": e.player.class_label, "from": e.origin.school,
                 "wants": po.PRIORITY_WORD.get(getattr(e, "priority", ""), e.reason), "offered": e in user["offers"],
                 "nil": fi.money(report.nil[(team, e)]) if report.nil.get((team, e)) else ""}
            r.update(_wv_who(league, report, user, e))
            rows.append(r)
        pool_all = [e for e in report.entries if e.origin is not team and e.destination is None]
        short = sorted(((po.transfer_value(league, team, e, needs), e) for e in pool_all), key=lambda x: -x[0])
        webview.emit("portal", {
            "window": report.__dict__.get("window_name", "Portal Window"), "school": team.school,
            "hours": user["hours"], "slots": _slots(report, user), "signed": len(_landed(report, team)),
            "offers": len([e for e in user["offers"] if e.destination is None]), "leaving": len(leaving),
            "nil": fi.money(fi.portal_room(league, team, report)), "holes": holes,
            "short": [f"{e.player.name} ({e.position} {e.overall})" for v, e in short[:3] if v > 20],
            "view": tags, "targets": view["targets"], "fits": view["fits"],
            "sort": {"ovr": "overall", "fit": "best fit", "soon": "deciding soonest"}[view["sort"]],
            "page": view["page"] + 1, "pages": pages, "rows": rows})
    except Exception:
        pass


def _staff_board(league, report, team, needs):
    """The staff's short list: the best fits for this roster still on the board."""
    pool = [e for e in report.entries if e.origin is not team and e.destination is None]
    scored = sorted(((po.transfer_value(league, team, e, needs), e) for e in pool), key=lambda x: -x[0])
    top = [e for v, e in scored[:3] if v > 20]
    if top:
        print(paint("   Staff short list: ", C.GRAY) + ", ".join(
            paint(f"{truncate(e.player.name, 18)} ({e.position} {e.overall})", C.BWHITE) for e in top))


def _briefing(league, report, user):
    """A new portal week: what happened to your board since you last looked."""
    team = user["team"]
    lines = []
    for e, t in report.moves[user.get("seen_moves", 0):]:
        if t is team:
            continue
        if e in user["known"] or e in user["offers"]:
            lines.append(paint(f"   ✗ {e.player.name} ({e.position} {e.overall}) committed to {t.school}.", C.BRED))
    for e, t, wk in report.__dict__.get("backouts", []):
        if wk == user.get("portal_week") - 1 or wk == user.get("portal_week"):
            col = C.BRED if t is team else C.BCYAN
            lines.append(paint(f"   ↺ {e.player.name} backed off {t.school} — he's available again.", col))
    hot = [e for e in report.entries if e.destination is None and e in user["known"]
           and _timeline(league, report, e)[0] == "deciding THIS week"]
    for e in hot[:6]:
        pl, n, ld, ratio = standing(league, report, user, e)
        lines.append(f"   ⏱ {e.player.name} ({e.position} {e.overall}) decides this week — you're "
                     + _standing_word(pl, n, ratio) + (paint(f"; {ld.school} is the one to beat", C.GRAY) if pl > 1 and ld else ""))
    if not lines:
        return
    clear()
    print(title_bar(f"PORTAL WEEK BRIEFING  ·  {team.school.upper()}"))
    print(paint(f"   Your staff has {user['hours']} hours this week.", C.GRAY))
    print()
    for ln in lines:
        print(ln)
    pause()


# ═══ One player ═══════════════════════════════════════════════════════════════

def player_card(league, report, user, e):
    team = user["team"]
    msg = []
    while True:
        if e.destination is not None:
            return
        clear()
        p = e.player
        print(title_bar(f"{p.name.upper()}  ·  {e.position}  ·  {e.origin.school.upper()}"))
        known = e in user["known"]
        visited = e in user["visited"]
        g = grades(league, team, e, report)
        blk = []
        blk.append(f"   {__import__('scout').ovr(e.overall)} overall   {p.class_label}   from {getattr(p, 'home_state', '') or '—'}")
        blk.append(paint(f"   Left because: {e.reason}", C.GRAY))
        blk.append(paint(f"   Wants most: {po.PRIORITY_WORD.get(getattr(e, 'priority', ''), 'a fresh start')}", C.BYELLOW, C.BOLD)
                   + (paint(f"   ·  also: {po.PRIORITY_WORD.get(po.second_priority(e), '—')}", C.BYELLOW) if known else
                      paint("   ·  also: ? (contact him)", C.GRAY)))
        heat, top5, serious = _market(league, e)
        if known:
            pl, n, ld, ratio = standing(league, report, user, e)
            tl, tc = _timeline(league, report, e)
            blk.append(f"   You: " + _standing_word(pl, n, ratio)
                       + (paint(f"   {ld.school} " + ("leads" if pl > 1 else "is next"), C.GRAY) if ld else "")
                       + paint(f"   ·  {tl}", tc, C.BOLD))
            blk.append(f"   Your work on him: {paint(_level(user['interest'].get(e, 0)), C.BCYAN, C.BOLD)}"
                       + (paint("  ·  visited", C.BMAGENTA) if visited else ""))
        else:
            blk.append(paint(f"   Market: {heat} — {serious} serious. Contact him to learn where you stand.", C.BMAGENTA))
        mine = report.nil.get((team, e), 0)
        blk.append(f"   {paint('NIL market', C.GRAY)} ~{fi.money(fi.transfer_market(p))}/yr   "
                   f"{paint('Yours', C.GRAY)} " + (paint(fi.money(mine) + '/yr', C.BGREEN, C.BOLD) if mine else paint('none', C.GRAY))
                   + f"   {paint('Free', C.GRAY)} {fi.money(fi.portal_room(league, team, report))}")
        need = team_needs(team)[e.position]
        if need[0] > 0:
            blk.append(paint(f"   He'd start for you — you have a hole at {e.position}.", C.BGREEN))
        elif e.overall > need[1]:
            blk.append(paint(f"   He'd push your starter at {e.position} ({need[1]:.0f} overall).", C.BYELLOW))
        else:
            blk.append(paint(f"   He'd be depth at {e.position} — your starters average {need[1]:.0f}.", C.GRAY))
        import faces
        if faces.enabled():
            import faces_ui
            for ln in faces_ui.beside(faces.player_portrait(p, team=e.origin, year=faces.class_year(p.class_label), mini=True), blk, indent=0, gap=1):
                print(ln)
        else:
            for ln in blk:
                print(ln)
        # Your case, angle by angle.
        print(rule())
        used = user["angles"].get(e, {})
        cells = []
        for i, (k, label) in enumerate(ANGLES, 1):
            star = "★" if k == getattr(e, "priority", None) else ("☆" if known and k == po.second_priority(e) else " ")
            n_used = used.get(k, 0)
            cells.append(f"   {paint(f'[P{i}]', C.BYELLOW)}{star}{pad(label, 21)}{paint(_letter(g[k]), _gcol(g[k]), C.BOLD)}"
                         + (paint(f" ×{n_used}", C.GRAY) if n_used else "   "))
        print(paint("   YOUR CASE TO HIM", C.GRAY, C.BOLD) + paint("   ★ what he wants most  ☆ his second priority  — pitch where you're strong", C.GRAY))
        for a, b in zip(cells[0::2], cells[1::2] + [""]):
            print(pad(a, 50) + b)
        shown_msgs = msg[-3:]
        for m in shown_msgs:
            print(m)
        msg = []
        print(rule())
        slots = _slots(report, user)
        contact_lbl = "Contacted ✓" if known else f"Contact ({COST['contact']})"
        visit_lbl = "Visited ✓" if visited else f"Official visit ({COST['visit']})"
        print(f"   {paint('[1]', C.BYELLOW)} {contact_lbl}   "
              f"{paint('[P#]', C.BYELLOW)} Pitch ({COST['pitch']})   "
              f"{paint('[V]', C.BYELLOW)} {visit_lbl}   "
              f"{paint('[C]', C.BGREEN, C.BOLD)} Push to commit ({COST['push']})")
        offer_lbl = "Withdraw offer" if e in user["offers"] else f"Offer a spot ({slots} open)"
        print(f"   {paint('[O]', C.BGREEN)} {offer_lbl}   "
              f"{paint('[N]', C.BGREEN)} NIL offer   {paint('[B]', C.GRAY)} back      {paint(str(user['hours']), C.BWHITE, C.BOLD)} hrs left")
        import webview
        if webview.on():
            try:
                d = {"name": p.name, "pos": e.position, "ovr": webview.plain(__import__("scout").ovr(e.overall)),
                     "yr": p.class_label, "home": getattr(p, "home_state", "") or "", "from": e.origin.school,
                     "reason": e.reason, "wants": po.PRIORITY_WORD.get(getattr(e, "priority", ""), "a fresh start"),
                     "also": po.PRIORITY_WORD.get(po.second_priority(e), "") if known else "",
                     "heat": heat, "serious": serious, "work": _level(user["interest"].get(e, 0)) if known else "",
                     "visited": visited, "offered": e in user["offers"], "slots": slots,
                     "market": fi.money(fi.transfer_market(p)), "mine": fi.money(mine) if mine else "",
                     "free": fi.money(fi.portal_room(league, team, report)), "fit": webview.plain(blk[-1]),
                     "hours": user["hours"], "cost": COST, "pushedThisWeek": user["pushed"].get(e) == user.get("portal_week"),
                     "angles": [{"key": f"p{i}", "label": label, "grade": _letter(g[k]), "g": round(g[k]),
                                 "star": k == getattr(e, "priority", None),
                                 "second": bool(known and k == po.second_priority(e)), "used": used.get(k, 0)}
                                for i, (k, label) in enumerate(ANGLES, 1)],
                     "msgs": [webview.plain(m) for m in shown_msgs]}
                d.update(_wv_who(league, report, user, e))
                webview.emit("pcard", d)
            except Exception:
                pass
        c = ask("Select:").strip().lower().replace(" ", "")
        if c in ("b", ""):
            return
        if c == "n":
            _nil_offer(league, report, team, e)
            continue
        if c == "o":
            if e in user["offers"]:
                user["offers"].discard(e)
                report.nil.pop((team, e), None)                # no spot, no money
            elif slots <= 0:
                msg.append(paint(f"   No spots left — {MAX_INCOMING} per window, counting the players you've signed.", C.BRED))
            else:
                user["offers"].add(e)
                msg.append(paint("   Spot offered. He can choose you now.", C.BGREEN))
            continue
        if c in ("1", "contact"):
            if known:
                msg.append(paint("   You already have a line to him. Pitch, visit, or push.", C.GRAY))
            elif _spend(user, "contact", msg):
                user["known"][e] = base_interest(league, team, e)
                tl, tc = _timeline(league, report, e)
                msg.append(paint(f"   Got him on the phone. He also cares about {po.PRIORITY_WORD.get(po.second_priority(e))}. "
                                 f"Timeline: {tl}.", C.BCYAN))
            continue
        if c.startswith("p") and c[1:].isdigit() and 1 <= int(c[1:]) <= len(ANGLES):
            if not known:
                msg.append(paint("   Contact him first — you need to know what he's hearing.", C.BRED))
            elif _spend(user, "pitch", msg):
                msg.append(_pitch(league, report, user, e, ANGLES[int(c[1:]) - 1][0], g))
            continue
        if c in ("v", "3"):
            if not known:
                msg.append(paint("   Contact him first.", C.BRED))
            elif visited:
                msg.append(paint("   He's already been on campus.", C.GRAY))
            elif _spend(user, "visit", msg):
                msg.append(_visit(league, report, user, e, g))
            continue
        if c == "c":
            if e not in user["offers"]:
                msg.append(paint("   Offer him a spot first — you can't ask for a commitment without one.", C.BRED))
            elif user["pushed"].get(e) == user.get("portal_week"):
                msg.append(paint("   You already asked this week. Pushing again will only annoy him.", C.GRAY))
            elif _spend(user, "push", msg):
                user["pushed"][e] = user.get("portal_week")
                if _push(league, report, user, e):
                    pause()
                    return
                msg.append(paint("   " + user["log"].get(e, ""), C.BRED))
            continue


def _spend(user, action, msg):
    if user["hours"] < COST[action]:
        msg.append(paint(f"   Not enough hours — that takes {COST[action]}, you have {user['hours']}.", C.BRED))
        return False
    user["hours"] -= COST[action]
    return True


def _add(user, e, amount):
    user["interest"][e] = max(0.0, min(1.0, user["interest"].get(e, 0) + amount))


def _pitch(league, report, user, e, angle, g):
    """One pitch. It works when he cares about it AND your program can back it up."""
    import staff
    team = user["team"]
    care = _care(e, angle, None)
    grade = g[angle] / 100
    used = user["angles"].setdefault(e, {})
    n = used.get(angle, 0)
    used[angle] = n + 1
    staff_x = 0.85 + staff.recruiting_rating(team) / 400
    fatigue = FATIGUE[min(n, len(FATIGUE) - 1)]
    if angle == "money" and not report.nil.get((team, e)):
        _add(user, e, -0.02)
        return paint("   You talked money without putting any on the table. He noticed. (Make a NIL offer first.)", C.BRED)
    if care >= 0.65 and grade < 0.40:
        _add(user, e, -0.04)
        return paint("   " + _why(league, team, e, angle, g, bad=True) + " It hurt your case.", C.BRED)
    gain = care * (0.32 * grade - 0.07) * staff_x * fatigue
    _add(user, e, gain)
    word = "Landed." if gain >= 0.14 else "It helped." if gain >= 0.06 else "He heard you out." if gain > 0.015 else "It barely registered."
    col = C.BGREEN if gain >= 0.06 else C.BYELLOW if gain > 0.015 else C.GRAY
    tail = "" if fatigue == 1.0 else paint("  (he's heard this one before)", C.GRAY)
    return paint(f"   {word} " + _why(league, team, e, angle, g), col) + tail


def _why(league, team, e, angle, g, bad=False):
    """What he actually hears — built from your program's real situation."""
    need = team_needs(team)[e.position]
    grade = g[angle]
    if angle == "playing_time":
        if need[0] > 0:
            return f"You have an open starting spot at {e.position} — he can see himself in it."
        if e.overall > need[1] + 3:
            return f"Your {e.position} starters average {need[1]:.0f}; he believes he wins that job."
        return f"He looked at your {e.position} room ({need[2]} deep) and doesn't see the path." if grade < 55 else \
            f"He'd have to compete at {e.position}, but he likes his odds."
    if angle == "winning":
        w = getattr(team, "wins", None)
        rec = f"{team.wins}-{team.losses}" if w is not None and hasattr(team, "losses") else ""
        rank = league.rankings.rank_of(team)
        if rank and grade >= 70:
            return f"A top-{max(5, rank)} program sells itself."
        return (f"Your {rec} season was a hard sell." if rec else "Your recent results are a hard sell.") if grade < 55 \
            else (f"Coming off {rec}, he believes you're close." if rec else "He believes you're headed up.")
    if angle == "development":
        return "Your staff's track record with his position is the real thing." if grade >= 70 else \
            "Your development record at his spot is just average." if grade >= 50 else \
            "He doesn't see your staff getting players to the next level."
    if angle == "scheme_fit":
        return "Your system fits what he does best." if grade >= 70 else \
            "Your scheme asks things of him he isn't built for." if grade < 50 else "He can play in your system."
    if angle == "proximity":
        home = getattr(e.player, "home_state", "") or "home"
        return f"Playing in front of family back in {home} matters to him." if grade >= 70 else \
            f"You're a long way from {home}." if grade < 45 else f"You're within driving distance of {home}."
    if angle == "program":
        return "The facilities, the stadium, the tradition — he's impressed." if grade >= 70 else \
            "Your program doesn't have the shine he's looking for." if grade < 50 else "He respects the program."
    if angle == "money":
        return "Your NIL number is the best one he's seen." if grade >= 85 else \
            "Your NIL offer is competitive." if grade >= 60 else "Your NIL offer is light compared to the market."
    return "He listened."


def _visit(league, report, user, e, g):
    user["visited"].add(e)
    gain = 0.16 + 0.14 * g["program"] / 100 + (0.06 if g.get(getattr(e, "priority", ""), 0) >= 70 else 0)
    _add(user, e, gain)
    if g["program"] >= 70:
        return paint("   Big weekend. The facility tour and the players' host night got him.", C.BGREEN)
    if g["program"] >= 50:
        return paint("   Solid visit. He left knowing exactly what you're offering.", C.BGREEN)
    return paint("   The visit helped, but your campus didn't wow him. Win him on the pitch.", C.BYELLOW)


def _push(league, report, user, e):
    """Ask him to commit. If you're out in front, he can end it now."""
    team = user["team"]
    pl, n, ld, ratio = standing(league, report, user, e)
    r = random.Random(f"push:{league.seed}:{league.year}:{e.player.name}:{user.get('portal_week')}:{team.school}")
    tl = _timeline(league, report, e)[0]
    soon = 0.12 if tl == "deciding THIS week" else 0.0
    if pl == 1 and ratio >= 1.10:
        odds = 0.9
    elif pl == 1:
        odds = 0.55 + soon
    elif ratio >= 0.92:
        odds = 0.18 + soon
    else:
        odds = 0.0
    if r.random() < odds:
        nil = report.nil.pop((team, e), 0)
        user["offers"].discard(e)
        po.sign(report, e, team, nil)
        try:
            report.__dict__.setdefault("commit_log", []).append((user.get("portal_week"), e, team))
        except Exception:
            pass
        print(paint(f"\n   ✍  {e.player.name} commits to {team.school}!", C.BGREEN, C.BOLD))
        print(paint(f"   {e.position} · {e.overall} overall" + (f" · NIL {fi.money(nil)}/yr" if nil else ""), C.GRAY))
        return True
    _add(user, e, -0.02)
    if ld is not None and pl > 1:
        user["log"][e] = f"Not yet — {ld.school} is still in front. Keep working him."
    else:
        user["log"][e] = "He wants to take his time. You're in a good spot — don't let up."
    return False


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


# ═══ Your own players in the portal ═══════════════════════════════════════════

def _keep_odds(league, team, e, raise_amt=0, promise=False):
    import staff
    odds = 0.40 + (0.2 if e.depth <= 1 else 0) + staff.recruiting_rating(team) / 350
    wants_time = getattr(e, "priority", None) == "playing_time" or "playing" in e.reason or "depth" in e.reason
    if wants_time:
        odds -= 0.15
        if promise:
            odds += 0.35                   # a real role is what he left for
    elif promise:
        odds += 0.08
    if getattr(e, "priority", None) == "winning" and team.win_pct >= 0.6:
        odds += 0.1
    if raise_amt > 0:
        mult = 2.0 if getattr(e, "priority", None) == "money" else 1.0
        odds += 0.3 * mult * min(1.0, raise_amt / max(1, fi.transfer_market(e.player))) * fi.player_appetite(e.player)
    return max(0.03, min(0.95, odds))


def _odds_word(x):
    return paint("very likely", C.BGREEN, C.BOLD) if x >= 0.75 else paint("good chance", C.BGREEN) if x >= 0.55 else \
        paint("coin flip", C.BYELLOW) if x >= 0.4 else paint("long shot", C.BRED)


def keep_screen(league, report, user, leaving, rng):
    team = user["team"]
    while True:
        clear()
        print(title_bar(f"YOUR PLAYERS IN THE PORTAL  ·  {team.school.upper()}"))
        out = [e for e in leaving if e.player not in team.roster and e.destination is None]
        gone = [e for e in leaving if e.destination is not None and e.destination is not team]
        if not out and not user["kept"] and not gone:
            print(paint("   Nobody from your roster entered the portal.", C.GRAY))
            pause()
            return
        for i, e in enumerate(out, 1):
            talked = user["talked"].get(e) == user.get("portal_week")
            print(f"   {paint(f'{i:>2}', C.BYELLOW)}  {pad(truncate(e.player.name, 21), 22)}{e.position:<4}{__import__('scout').ovr_short(e.overall)}  "
                  f"{e.player.class_label:<6}{paint(pad(truncate(e.reason, 30), 31), C.GRAY)}"
                  f"{paint('wants ' + po.PRIORITY_WORD.get(getattr(e, 'priority', ''), '?'), C.BYELLOW)}"
                  + (paint('  · talked this week', C.GRAY) if talked else ''))
        for p in user["kept"]:
            print(f"   {paint('  ✓', C.BGREEN)}  {pad(p.name, 22)}{p.position:<4}{__import__('scout').ovr_short(p.overall)}  "
                  f"{paint('withdrew — staying', C.BGREEN)}")
        for e in gone:
            print(f"   {paint('  ✗', C.BRED)}  {pad(e.player.name, 22)}{e.position:<4}{__import__('scout').ovr_short(e.overall)}  "
                  f"{paint('committed to ' + e.destination.school, C.BRED)}")
        print(rule())
        import webview
        if webview.on():
            webview.emit("pkeep", {"school": team.school, "hours": user["hours"], "cost": COST["keep"],
                                   "out": [{"i": i, "name": e.player.name, "pos": e.position, "yr": e.player.class_label,
                                            "ovr": webview.plain(__import__("scout").ovr_short(e.overall)), "reason": e.reason,
                                            "wants": po.PRIORITY_WORD.get(getattr(e, "priority", ""), "?"),
                                            "talked": user["talked"].get(e) == user.get("portal_week")}
                                           for i, e in enumerate(out, 1)],
                                   "kept": [p.name for p in user["kept"]],
                                   "gone": [{"name": e.player.name, "to": e.destination.school} for e in gone]})
        c = ask(f"Talk to # ({COST['keep']} hrs, {user['hours']} left) — Enter = back:").strip()
        if not c.isdigit() or not 1 <= int(c) <= len(out):
            return
        e = out[int(c) - 1]
        if user["talked"].get(e) == user.get("portal_week"):
            print(paint("   You already sat down with him this week.", C.GRAY))
            pause()
            continue
        if user["hours"] < COST["keep"]:
            print(paint("   Not enough hours left.", C.BRED))
            pause()
            continue
        before = getattr(e.player, "nil_before_portal", 0)
        room = fi.portal_room(league, team, report)
        print()
        print(paint(f"   He left because: {e.reason}. What he wants: {po.PRIORITY_WORD.get(getattr(e, 'priority', ''), '—')}.", C.BYELLOW))
        print(paint(f"   Just talking: {_strip(_odds_word(_keep_odds(league, team, e)))}   "
                    f"with a starting-role promise: {_strip(_odds_word(_keep_odds(league, team, e, promise=True)))}", C.GRAY))
        print(paint(f"   He was making {fi.money(before)}/yr. Market: ~{fi.money(fi.transfer_market(e.player))}. Free: {fi.money(room)}.", C.GRAY))
        promise = ask("Promise him a starting role? Break it and he's gone next year. (y/N):").strip().lower() == "y"
        raw = ask("New NIL figure to stay (Enter = keep his old deal):").strip()
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
        user["talked"][e] = user.get("portal_week")
        odds = _keep_odds(league, team, e, new_amt - before, promise)
        if rng.random() < odds:
            report.entries.remove(e)
            if e in report.by_team_out[team]:
                report.by_team_out[team].remove(e)
            team.add_player(e.player)
            e.player.nil = new_amt                                    # he stays, on the deal that kept him
            if promise:
                e.player.promise = "made"                             # depth chart has to back it up next year
            user["kept"].append(e.player)
            print(paint(f"   {e.player.name} is pulling his name out of the portal. He's staying.", C.BGREEN, C.BOLD))
        else:
            print(paint(f"   {e.player.name} appreciated the talk. He's still in the portal — try again next week.", C.BRED))
        pause()


def _strip(s):
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def window_results(league, report):
    """After the portal resolves: how your window went."""
    user = _mine(league, report) or None
    if user is None:
        return
    team = user["team"]
    clear()
    print(title_bar(f"PORTAL RESULTS  ·  {team.school.upper()}"))
    landed = [e for e in report.entries if e.destination is team]
    missed = [e for e in set(user["offers"]) | set(user.get("known", {})) if e.destination is not team
              and e.origin is not team and (e in user["offers"] or user["interest"].get(e, 0) > 0)]
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
        for e in sorted(missed, key=lambda x: -x.overall):
            where = e.destination.school if e.destination else "stayed unsigned"
            deal = report.__dict__.get("deals", {}).get(e, 0)
            extra = f" ({fi.money(deal)}/yr)" if deal and e.destination else ""
            print(f"   {pad(e.player.name, 22)}{e.position:<5}{__import__('scout').ovr_short(e.overall)}  chose {where}{extra}")
    if user["kept"]:
        print()
        print(section("TALKED OUT OF LEAVING", C.BCYAN))
        for p in user["kept"]:
            print(f"   {pad(p.name, 22)}{p.position:<5}{__import__('scout').ovr_short(p.overall)}"
                  + (paint("  promised a starting role", C.BYELLOW) if getattr(p, "promise", None) == "made" else ""))
    pause()
