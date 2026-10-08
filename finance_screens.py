"""
finance_screens.py — The money screens.

  budget_screen()    one program's budget: the staff's contracts, buyouts, the
                     NIL on the roster, and what's left for the next class
  payroll()          every player on the roster and what he's paid a year
  league_budgets()   every FBS program side by side
  nil_prompt()       putting NIL money on a recruit (from his recruiting card)
"""
import carousel as cz
import finance as fi
import staff
from recruiting_data import PERSONALITIES
from ui import C, WIDTH, ask, bar, clear, pad, paint, pause, rating, rule, section, title_bar, truncate


_WV = {"sec": "", "rows": []}


def _sec(text, color):
    _WV["sec"] = text
    return section(text, color)


def _row(label, who, amount, note="", color=C.BWHITE, exact=True):
    """Two decimals on millions, so the pieces add up to the totals on screen."""
    _WV["rows"].append({"sec": _WV["sec"], "label": label, "who": who, "amount": fi.money(amount, exact=exact),
                        "note": note, "neg": amount < 0, "tone": {C.BRED: "bad", C.BGREEN: "good", C.BCYAN: "info"}.get(color, "")})
    return (f"   {paint(pad(label, 16), C.GRAY)}{pad(truncate(who, 34), 35)}"
            f"{pad(paint(fi.money(amount, exact=exact), color, C.BOLD), 10, 'right')}   {paint(note, C.GRAY)}")


def budget_screen(league, team):
    while True:
        clear()
        color = league.conference_color(team.conference)
        yr = league.year
        b = fi.budget(team)
        style = team.ad.get("style", "conference")
        print(title_bar(f"{team.school.upper()} FOOTBALL BUDGET  ·  {yr}", color))
        print(f"   {paint('Annual budget', C.GRAY)}  {paint(fi.money(b), C.BGREEN, C.BOLD)}  "
              f"{paint(f'fixed for {yr} · #{fi.budget_rank(league, team)} of {len(league.teams)} nationally', C.GRAY)}   "
              f"{paint('AD ' + team.ad['name'] + ' (' + cz.AD_STYLES[style][0] + '): ' + fi.AD_CONTRACT[style]['blurb'], C.GRAY)}")
        tr = fi.budget_trend(team)
        if tr:
            yr_, new, pct, why = tr
            col = C.BGREEN if pct > 0 else C.BRED
            print(f"   {paint('Last change', C.GRAY)}  {paint(f'{pct:+.1f}%', col, C.BOLD)} for {yr_}"
                  f"{paint(' — ' + why if why else '', C.GRAY)}   "
                  f"{paint('started at ' + fi.money(getattr(team, 'budget_base', fi.budget(team))), C.GRAY)}")
        else:
            print(paint("   Budgets grow when programs win (up to 1.5x) and shrink after years of losing and "
                        "coaching churn (down to 0.7x).", C.GRAY))
        print()

        # ── this season ──────────────────────────────────────────────────
        _WV["rows"] = []
        print(section(f"THIS SEASON  ·  {yr}", color))
        _WV["sec"] = f"This season · {yr}"
        spent = 0
        for label, c in (("Head coach", team.coach), ("Off. coord.", getattr(team, "oc", None)),
                         ("Def. coord.", getattr(team, "dc", None))):
            if c is None:
                print(_row(label, "— open —", 0))
                continue
            k = fi.contract(c)
            pay = k["salary"] if k else 0
            spent += pay
            note = (f"deal runs {k['start']}–{k['end']}" + (" · expires after this season" if k["end"] <= yr else "")) if k else ""
            you = "  (you)" if getattr(c, "is_user", False) else ""
            print(_row(label, c.name + you, pay, note, exact=True))
        ops = int(b * fi.OPS_SHARE)
        spent += ops
        print(_row("Operations", "support staff, travel, medical", ops,
                   f"{int(fi.OPS_SHARE * 100)}% off the top of every budget"))
        outs = fi.active_buyouts(team, yr)
        owed_now = fi.buyouts_in(team, yr)
        spent += owed_now
        if owed_now:
            n = sum(1 for o in outs if o["start"] <= yr)
            print(_row("Buyouts", f"{n} former coach{'es' if n != 1 else ''}", owed_now,
                       "money owed to coaches the school fired", C.BRED))
        for what, amt in team.__dict__.get("books", {}).get(yr, []):
            if amt:
                spent += amt
                print(_row("Other", truncate(what, 26), amt, truncate(what, 40) if len(what) > 26 else ""))
        paid = [p for p in team.roster if fi.player_nil(p)]
        nil_now = fi.roster_nil(team)
        spent += nil_now
        print(_row("Player NIL", f"{len(paid)} of {len(team.roster)} players", nil_now))
        print("   " + paint("─" * 70, C.GRAY))
        left = b - spent
        pct = spent / b * 100 if b else 0
        print(f"   {paint(pad('Spent', 16), C.GRAY)}{pad('', 28)}{pad(paint(fi.money(spent, exact=True), C.BWHITE, C.BOLD), 10, 'right')}"
              f"   {bar(min(100, pct), 24, color=C.BRED if pct > 100 else C.BGREEN)} {pct:.0f}% of the budget")
        print(f"   {paint(pad('Unspent' if left >= 0 else 'OVER BUDGET', 16), C.GRAY)}{pad('', 28)}"
              f"{pad(paint(fi.money(left, exact=True), C.BGREEN if left >= 0 else C.BRED, C.BOLD), 10, 'right')}")

        # ── the next class ───────────────────────────────────────────────
        cycle = league.recruiting
        print()
        print(section(f"NIL FOR NEXT SEASON  ·  THE {yr + 1} CLASS", color))
        _WV["sec"] = f"NIL for next season · the {yr + 1} class"
        pool = fi.nil_pool(league, team)
        ret = fi.roster_nil(team, returning=True)
        seniors = nil_now - ret
        com = fi.committed_nil(cycle, team)
        opn = fi.open_nil(cycle, team)
        n_com = sum(1 for r in fi.offers_by(cycle, team) if r.committed_to is team)
        n_open = sum(1 for r in fi.offers_by(cycle, team) if r.committed_to is not team and not r.signed)
        avail = fi.available(league, team)
        inc = fi.income_in(team, yr + 1)
        if inc:
            print(_row("Income", "stadium revenue, release fees", inc, "added to next year's pool", C.BGREEN))
        import facilities as fa
        build = fa.spend_in(team, yr + 1)
        if build:
            import stadium as sd
            stad = sd.payments(team, yr + 1)
            print(_row("Facilities", "construction" + (" & stadium payments" if stad else ""), -build,
                       ("stadium projects and bonds run several seasons — " if stad else "one-time — ")
                       + "[F] facilities", C.BRED))
        print(_row("Budget left", "after operations, staff & buyouts", pool, "the whole player pool"))
        print(_row("Returning", "players coming back", -ret,
                   f"{fi.money(seniors)} comes off with the seniors" if seniors else ""))
        print(_row("Committed", f"{n_com} commit{'s' if n_com != 1 else ''} with NIL", -com))
        print(_row("Open offers", f"{n_open} recruit{'s' if n_open != 1 else ''} deciding", -opn,
                   "held until they pick"))
        print("   " + paint("─" * 70, C.GRAY))
        print(_row("AVAILABLE", "to offer recruits", avail, "the most you can put on the table", C.BGREEN if avail >= 0 else C.BRED))
        tgt = fi.class_target(league, team)
        print(_row("Suggested", "plan to spend about", tgt,
                   f"keeps ~{fi.money(max(0, avail - tgt))} back for raises and buildings", C.BCYAN))
        print(paint("   Every deal is paid every year the player is on the roster.", C.GRAY))

        # ── who gets paid ───────────────────────────────────────────────
        top = sorted(paid, key=lambda p: -fi.player_nil(p))[:10]
        if top:
            print()
            print(section("TOP NIL DEALS ON THE ROSTER", color))
            for a, bb in zip(top[0::2], top[1::2] + [None]):
                print("   " + pad(_player_cell(a), 48) + (_player_cell(bb) if bb else ""))
            if __import__('scout').hidden(league):
                print(paint(f"   Staff read: {__import__('scout').LEGEND}", C.GRAY))
        if outs:
            print()
            print(section("BUYOUTS OWED  ·  paid every year through the end of his old deal", C.BRED))
            for o in outs:
                span = f"{o['start']}–{o['end']}"
                print(f"   {pad(o['name'], 24)}{pad(staff.ROLE_SHORT.get(o['role'], o['role']), 4)}"
                      f"{paint(fi.money(o['per_year']), C.BRED)}/yr  {paint(span, C.GRAY)}")
        print(rule())
        print(f"   {paint('[P]', C.BYELLOW)} full payroll   {paint('[L]', C.BYELLOW)} every program's budget   "
              f"{paint('[F]', C.BYELLOW)} facilities   {paint('[R]', C.BYELLOW)} find money / rebalance   "
              f"{paint('[B]', C.GRAY)} back")
        import webview
        if webview.on():
            try:
                import scout
                webview.emit("budget", {
                    "school": team.school, "year": yr, "budget": fi.money(b), "rank": fi.budget_rank(league, team),
                    "of": len(league.teams), "ad": f"{team.ad['name']} ({cz.AD_STYLES[style][0]})",
                    "adBlurb": fi.AD_CONTRACT[style]["blurb"],
                    "trend": (f"{tr[2]:+.1f}% for {tr[0]}" + (f" — {tr[3]}" if tr[3] else "")) if tr else "",
                    "trendUp": bool(tr and tr[2] > 0), "spent": fi.money(spent, exact=True), "pct": round(pct),
                    "left": fi.money(left, exact=True), "over": left < 0, "available": fi.money(avail),
                    "rows": list(_WV["rows"]), "color": webview._color(league, team),
                    "top": [{"id": webview.pid(p), "name": p.name, "pos": p.position, "yr": p.class_label,
                             "ovr": webview.plain(scout.ovr_short(p)), "nil": fi.money(fi.player_nil(p))} for p in top],
                    "buyouts": [{"name": o["name"], "role": staff.ROLE_SHORT.get(o["role"], o["role"]),
                                 "per": fi.money(o["per_year"]), "span": f"{o['start']}–{o['end']}"} for o in outs]})
            except Exception:
                pass
        choice = ask("Select:").strip().lower()
        if choice == "r":
            import budget_fix
            if budget_fix.interactive(league, team):
                budget_fix.screen(league, team)
        elif choice == "f":
            facilities_screen(league, team)
        elif choice == "p":
            payroll(league, team)
        elif choice == "l":
            league_budgets(league, team)
        else:
            return


def _player_cell(p):
    return (f"{paint(pad(p.position, 3), C.BCYAN)} {paint(f'#{p.number:<3}', C.GRAY)}"
            f"{pad(truncate(p.name, 19), 20)}{paint(pad(p.class_label, 6), C.GRAY)}{__import__('scout').ovr_short(p)}  "
            f"{paint(fi.money(fi.player_nil(p)), C.BGREEN, C.BOLD)}")


def payroll(league, team):
    """Every player and what he makes, biggest deals first."""
    players = sorted(team.roster, key=lambda p: (-fi.player_nil(p), -p.overall))
    page, per = 0, 30
    while True:
        clear()
        color = league.conference_color(team.conference)
        total = fi.roster_nil(team)
        print(title_bar(f"{team.school.upper()} · NIL PAYROLL · {fi.money(total)}/YR", color))
        import scout
        read = "READ" if scout.hidden(league) else "OVR"
        print(paint(f"   {'POS':<5}{'#':<5}{'NAME':<24}{'YR':<7}{read:<4}  {'DEV':<4}{'HS':<6}{'NIL / YR':>10}   "
                    f"{'SHARE':>6}  {'THRU':<6}NOTE", C.GRAY, C.BOLD))
        chunk = players[page * per:(page + 1) * per]
        from screens import _dev_grade, _transfer_from
        from ui import stars
        for p in chunk:
            amt = fi.player_nil(p)
            share = f"{amt / total * 100:.1f}%" if total and amt else "—"
            money_txt = paint(fi.money(amt), C.BGREEN, C.BOLD) if amt else paint("—", C.GRAY)
            thru = str(league.year + max(0, 3 - p.year)) if amt else ""
            tr = _transfer_from(p)
            note = ("walk-on" if getattr(p, "walk_on", False) else "") if not amt else ""
            if not amt and not note:
                note = "no deal"
            name = truncate(p.name, 20 if tr else 22) + (paint(" ⇄", C.BCYAN) if tr else "")
            print(f"   {paint(pad(p.position, 5), C.BCYAN)}{paint(pad(str(p.number), 5), C.GRAY)}"
                  f"{pad(name, 24)}{pad(p.class_label, 7)}{pad(scout.ovr_short(p), 4)}  {pad(_dev_grade(p), 4)}"
                  f"{pad(stars(p.hs_stars), 6)}"
                  f"{pad(money_txt, 10, 'right')}   {paint(pad(share, 6, 'right'), C.GRAY)}  {paint(pad(thru, 6), C.GRAY)}"
                  f"{paint(note, C.GRAY)}")
        pages = max(1, (len(players) + per - 1) // per)
        if read == "READ":
            print(paint(f"\n   READ = your staff's read: {scout.LEGEND}", C.GRAY), end="")
        print(paint(f"\n   Page {page + 1}/{pages}.  ⇄ transfer · THRU = the last season he can be paid (eligibility runs out)."
                    f"\n   NIL deals are fixed once signed. Seniors' deals come off after the season; a player who enters"
                    f"\n   the portal takes nothing with him.", C.GRAY))
        import webview
        if webview.on():
            try:
                webview.emit("payroll", {"school": team.school, "total": fi.money(total), "page": page + 1, "pages": pages,
                                         "rows": [{"id": webview.pid(p), "pos": p.position, "num": p.number, "name": p.name,
                                                   "yr": p.class_label, "ovr": webview.plain(scout.ovr_short(p)),
                                                   "nil": fi.money(fi.player_nil(p)) if fi.player_nil(p) else "",
                                                   "share": f"{fi.player_nil(p) / total * 100:.1f}%" if total and fi.player_nil(p) else "",
                                                   "thru": str(league.year + max(0, 3 - p.year)) if fi.player_nil(p) else "",
                                                   "tr": bool(_transfer_from(p)), "walkon": bool(getattr(p, "walk_on", False))}
                                                  for p in chunk]})
            except Exception:
                pass
        choice = ask("[N] next  [P] previous  [B] back:").strip().lower()
        if choice == "n" and page + 1 < pages:
            page += 1
        elif choice == "p" and page:
            page -= 1
        else:
            return


def league_budgets(league, team=None):
    sort = "b"
    page, per = 0, 25
    while True:
        clear()
        keys = {"b": lambda t: -fi.budget(t), "c": lambda t: -fi.salary(t.coach),
                "n": lambda t: -fi.roster_nil(t), "a": lambda t: -fi.available(league, t)}
        order = sorted(league.teams, key=keys.get(sort, keys["b"]))
        print(title_bar(f"EVERY PROGRAM'S FOOTBALL BUDGET  ·  {league.year}"))
        print(paint(f"   {'RK':<4}{'TEAM':<22}{'CONF':<15}{'BUDGET':>8}  {'HEAD COACH':<20}{'SALARY':>8}  "
                    f"{'STAFF':>7}  {'ROSTER NIL':>10}  {'FREE NIL':>9}", C.GRAY, C.BOLD))
        for i, t in enumerate(order[page * per:(page + 1) * per], page * per + 1):
            mark = paint(" ←", C.BYELLOW) if t is team else ""
            col = league.conference_color(t.conference)
            av = fi.available(league, t)
            print(f"   {paint(pad(str(i), 4), C.GRAY)}{pad(paint(truncate(t.school, 20), col, C.BOLD), 22)}"
                  f"{paint(pad(truncate(t.conference, 14), 15), C.GRAY)}"
                  f"{pad(paint(fi.money(fi.budget(t)), C.BWHITE, C.BOLD), 8, 'right')}  "
                  f"{pad(truncate(t.coach.name if t.coach else '—', 19), 20)}"
                  f"{pad(fi.money(fi.salary(t.coach)), 8, 'right')}  {pad(fi.money(fi.staff_cost(t)), 7, 'right')}  "
                  f"{pad(fi.money(fi.roster_nil(t)), 10, 'right')}  "
                  f"{pad(paint(fi.money(av), C.BGREEN if av > 0 else C.GRAY), 9, 'right')}{mark}")
        pages = (len(order) + per - 1) // per
        print(paint(f"\n   Page {page + 1}/{pages}.  FREE NIL = what's left to offer the next class.", C.GRAY))
        print(paint("   Sort: [1] budget  [2] coach salary  [3] roster NIL  [4] free NIL    [N]/[P] page   [B] back",
                    C.GRAY))
        choice = ask("Select:").strip().lower()
        if choice in ("1", "2", "3", "4"):
            sort = "bcna"[int(choice) - 1]
            page = 0
        elif choice == "n" and page + 1 < pages:
            page += 1
        elif choice == "p" and page:
            page -= 1
        else:
            return


# ═══ NIL on a recruit ═══════════════════════════════════════════════════════

def nil_lines(league, team, recruit):
    """The NIL section of a recruit's card."""
    cycle = league.recruiting
    mine = fi.offer_to(cycle, team, recruit)
    others = {t: a for t, a in fi.offers_for(cycle, recruit).items() if t is not team}
    out = [f"   {paint('Market for a ' + str(recruit.stars) + '-star', C.GRAY)}  about "
           f"{fi.money(fi.market(recruit.stars))}/yr {paint('(budgets like yours pay ~' + fi.money(fi.market(recruit.stars) * fi.pay_scale(team)) + ')', C.GRAY)}",
           f"   {paint('Your NIL offer', C.GRAY)}  "
           + (paint(fi.money(mine) + '/yr', C.BGREEN, C.BOLD) if mine else paint('none', C.GRAY))
           + f"   {paint('Free to offer', C.GRAY)} {fi.money(fi.available(league, team))}"]
    if others:
        best_t = max(others, key=others.get)
        out.append(f"   {paint('Other NIL offers', C.GRAY)}  {len(others)}  ·  reportedly as high as "
                   f"{fi.money(others[best_t])}/yr ({best_t.school})")
    else:
        out.append(paint("   Nobody else has put NIL money on the table.", C.GRAY))
    if recruit.scout[team] >= 1:
        out.append(paint(f"   {fi.appetite_word(recruit)}.", C.GRAY))
    else:
        out.append(paint("   Evaluate him to find out how much money matters to him.", C.GRAY))
    return out


def nil_prompt(league, team, recruit):
    """Set (or change, or pull) a NIL offer. Returns a message."""
    cycle = league.recruiting
    mine = fi.offer_to(cycle, team, recruit)
    if team not in recruit.offers and not mine:
        from recruiting_data import ACTIONS
        cost = next((v[1] for k, v in ACTIONS.items() if "offer" in v[0].lower()), 3)
        when = "" if cycle.hours_for(team) else ", from Week 1"
        return (False, f"{recruit.name} has no scholarship offer from you yet — NIL goes on top of one. "
                       f"Extending an offer costs {cost}h{when}.")
    print()
    print(paint(f"   Market for a {recruit.stars}-star is about {fi.money(fi.market(recruit.stars))}/yr (a budget like yours "
                f"usually pays ~{fi.money(fi.market(recruit.stars) * fi.pay_scale(team))}). "
                f"Free to offer: {fi.money(fi.available(league, team) + mine)}"
                + (f" (counting the {fi.money(mine)} you already offered)" if mine else "") + ".", C.GRAY))
    print(paint("   Money makes you louder in his ear every week. It won't sign a kid who doesn't want your school.",
                C.GRAY))
    print(paint("   Every deal is paid every year he's on the roster — a $50K deal is about $200K over four years.",
                C.GRAY))
    if recruit.scout[team] < 1:
        print(paint("   You haven't evaluated him yet, so you don't know how much money matters to him.", C.BYELLOW))
    raw = ask("NIL per year (e.g. 250k, 1.2m, 0 to pull it, Enter to cancel):").strip()
    if not raw:
        return None
    amt = fi.parse_money(raw)
    if amt is None:
        return (False, "That isn't an amount.")
    if amt == 0:
        return fi.withdraw(cycle, team, recruit)
    amt = fi._round(amt, 1_000)
    if amt - mine > fi.available(league, team):
        import budget_fix
        if not budget_fix.cover(league, team, amt - mine, f"NIL for {recruit.name}: {fi.money(amt)}/yr"):
            return (False, f"You only have {fi.money(fi.available(league, team) + mine)} to offer.")
    return fi.make_offer(cycle, team, recruit, amt)


# ═══ Facilities ═════════════════════════════════════════════════════════════

def _pips(level):
    return paint("■" * level, C.BGREEN if level >= 9 else C.BCYAN if level >= 7 else C.BYELLOW if level >= 5
                 else C.BRED) + paint("□" * (10 - level), C.GRAY)


def season_crowds(league, team):
    """(home games, average attendance, average fill, sellouts) this season."""
    gs = [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played
          and getattr(g, "attendance", None)]
    if not gs:
        return 0, 0, 0.0, 0
    return (len(gs), sum(g.attendance for g in gs) // len(gs), sum(g.fill for g in gs) / len(gs),
            sum(1 for g in gs if getattr(g, "sellout", False)))


def facilities_screen(league, team):
    """The football building, the weight room, and the stadium (part by part)."""
    import facilities as fa
    import stadium as sd
    import stadium_screens
    import ad_mode
    mine = (getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is team) \
        or ad_mode.is_mine(league, team)
    msg = ""
    while True:
        clear()
        color = league.conference_color(team.conference)
        f = fa.ensure(team)
        sd.ensure(team)
        print(title_bar(f"{team.school.upper()} FACILITIES  ·  {league.year}", color))
        print(paint("   Levels run 1 (crumbling) to 10 (elite). An upgrade is a one-time cost out of next season's "
                    "player-NIL pool;\n   one project a season. Every offseason each facility has a small chance to "
                    "slip a level.", C.GRAY))
        print()
        keys = {"1": "recruiting", "2": "training"}
        for k, kind in keys.items():
            lv = f[kind]
            nxt = fa.cost(kind, lv + 1) if lv < 10 else None
            price = paint(f"next level {fi.money(nxt)}", C.BWHITE) if nxt else paint("maxed out", C.BGREEN)
            tag = paint(f"[{k}]", C.BYELLOW, C.BOLD) if mine else paint(f" {k} ", C.GRAY)
            print(f"   {tag} {pad(fa.LABELS[kind], 22)} {_pips(lv)}  {pad(str(lv), 3)}"
                  f"{paint(pad(fa.grade(lv), 7), C.BOLD)} {price}")
            if kind == "recruiting":
                eff = f"pitches land at {fa.recruiting_mult(team):.2f}x · 'facilities' to a recruit: {fa.pitch_value(team)}/100"
            else:
                eff = f"player development {0.92 + fa.training_rating(team) / 100 * 0.16:.2f}x every offseason"
            print(paint(f"         {fa.BLURB[kind]}", C.GRAY))
            print(paint(f"         now: {eff}", C.BCYAN))
        g = f["stadium"]
        print(f"   {paint('[S]', C.BYELLOW, C.BOLD)} {pad(team.stadium, 22)} {_pips(g)}  {pad(str(g), 3)}"
              f"{paint(pad(fa.grade(g), 7), C.BOLD)} "
              + paint(f"{sum(1 for k in sd.ORDER if sd.parts(team)[k] > sd.PARTS[k]['min'])} of {len(sd.ORDER)} parts built "
                      "— the stadium screen", C.BWHITE))
        print(paint(f"         {fa.BLURB['stadium']}", C.GRAY))
        for ln in stadium_screens.summary_lines(league, team):
            print("      " + ln)
        print()
        n, avg, fill, sold = season_crowds(league, team)
        print(section("THE CROWD", color))
        if n:
            print(f"   {n} home game{'s' if n != 1 else ''} · average {avg:,} ({fill * 100:.0f}% full) · "
                  f"{sold} sellout{'s' if sold != 1 else ''}")
            total, parts = sd.revenue(league, team)
            if total:
                print(f"   Stadium revenue so far: {paint(fi.money(total), C.BGREEN, C.BOLD)} "
                      + paint("(" + ", ".join(f"{k} {fi.money(v)}" for k, v in parts.items())
                              + ") — added to next season's budget", C.GRAY))
        else:
            print(paint("   No home games yet this season.", C.GRAY))
        print(paint("   Bigger, fuller, louder crowds are a bigger home-field edge. Rivalry games and big home openers "
                    "sell out\n   (if the fan base is big enough); losing — especially where they expect to win — "
                    "empties seats.", C.GRAY))
        log = sorted(getattr(team, "fac_log", [])[-5:] + sd.ensure(team)["log"][-5:], key=lambda x: x[0])[-6:]
        if log:
            print()
            print(section("RECENT PROJECTS", color))
            for yr, what in reversed(log):
                print(f"   {paint(str(yr), C.GRAY)}  {what}")
        print()
        print(f"   {paint('Available for projects', C.GRAY)}  "
              f"{paint(fi.money(fi.available(league, team)), C.BGREEN, C.BOLD)}  "
              f"{paint('(the same money that pays recruits — a class usually takes ' + fi.money(fi.class_target(league, team)) + ')', C.GRAY)}")
        if msg:
            print(paint(f"   {msg}", C.BYELLOW))
            msg = ""
        print(rule())
        if mine:
            print(f"   {paint('[1-2]', C.BYELLOW)} build the next level   {paint('[S]', C.BYELLOW)} stadium   "
                  f"{paint('[T]', C.BYELLOW)} toughest places to play   {paint('[B]', C.GRAY)} back")
        else:
            print(paint("   The AD runs this program's building plan.   [S] stadium   [T] toughest places   [B] back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c == "s":
            stadium_screens.stadium_screen(league, team)
        elif c == "t":
            stadium_screens.toughest_screen(league)
        elif mine and c in keys:
            kind = keys[c]
            ok, price, why = fa.can_upgrade(league, team, kind)
            if not ok and "available" in why:
                import budget_fix
                if budget_fix.cover(league, team, price, f"{fa.LABELS[kind]} upgrade: {fi.money(price)}"):
                    ok, price, why = fa.can_upgrade(league, team, kind)
            if not ok:
                msg = f"Can't build that: {why}."
                continue
            yes = ask(f"Upgrade {fa.LABELS[kind]} to level {f[kind] + 1} for {fi.money(price)}? (y/n)").strip().lower()
            if yes in ("y", "yes"):
                ok, msg = fa.upgrade(league, team, kind, who="you")
        else:
            return
