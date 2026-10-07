"""
stadium_screens.py — The stadium, part by part, and the toughest places to play.

  stadium_screen()    every part of one program's stadium: what it is, what the
                      next tier costs and does, and (yours) breaking ground
  toughest_screen()   the Toughest Places to Play: live this season, and every
                      final list from the seasons before
"""
import finance as fi
import stadium as sd
from ui import C, WIDTH, ask, clear, pad, paint, pause, rule, section, title_bar, truncate


def _pips(key, tier):
    top = sd.max_tier(key)
    col = C.BGREEN if tier == top else C.BCYAN if tier >= top * 0.6 else C.BYELLOW if tier > sd.PARTS[key]["min"] \
        else C.GRAY
    return paint("■" * tier, col) + paint("□" * (top - tier), C.GRAY)


def _effect(key, tier=None, short=True):
    """What one tier of a part does, in a few words."""
    p = sd.PARTS[key]
    bits = []
    if p["seats"]:
        bits.append(f"+{p['seats']:,} seats")
    fx = p["fx"]
    if fx.get("noise"):
        bits.append("louder" if fx["noise"] < 1 else "much louder")
    if key == "club_seats":
        bits.append("club money")
    if key == "suites":
        bits.append("suite leases")
    if fx.get("concess"):
        bits.append("concessions")
    if key == "video_board":
        bits.append("ad money")
    if fx.get("comfort") and not short:
        bits.append("fuller stands")
    if fx.get("fans"):
        bits.append("fan base grows")
    if fx.get("recruit", 0) >= 1 or fx.get("visit"):
        bits.append("recruiting")
    if fx.get("edge"):
        bits.append("home edge")
    if fx.get("vis"):
        bits.append("visitors rattled")
    if fx.get("night"):
        bits.append("night games")
    if key == "surface":
        bits.append("fewer injuries")
    return ", ".join(bits[:3] if short else bits)


def _mine(league, team):
    import ad_mode
    return (getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is team) \
        or ad_mode.is_mine(league, team)


def summary_lines(league, team):
    """The stadium in three lines (used here and on the facilities screen)."""
    st = sd.ensure(team)
    nr = sd.noise_rating(team)
    g = sd.grade(team)
    rk = sd.rank_of(league, team)
    out = [f"   {paint('Capacity', C.GRAY)} {paint(f'{team.capacity:,}', C.BWHITE, C.BOLD)}"
           + (paint(f" (+{team.capacity - team.base_capacity:,} built)", C.GRAY)
              if team.capacity > team.base_capacity else "")
           + f"   {paint('Noise', C.GRAY)} {paint(sd.noise_word(nr), C.BYELLOW, C.BOLD)} ({nr}/10)"
           + f"   {paint('Grade', C.GRAY)} {paint(g, C.BWHITE, C.BOLD)}/10 {paint(sd.grade_word(g), C.GRAY)}",
           f"   {paint('Recruiting appeal', C.GRAY)} {sd.recruit_score(team)}/100"
           f"   {paint('Fan base', C.GRAY)} ~{sd.fanbase(team) // 1000 * 1000:,}"
           + (paint("  (more seats than fans)", C.BRED) if team.capacity > sd.fanbase(team) * 1.15 else
              paint("  (they'd fill more seats)", C.BGREEN) if sd.fanbase(team) > team.capacity * 1.05 else "")
           + (f"   {paint('Toughest places', C.GRAY)} No. {rk}" if rk else "")]
    bl = sd.bonds_left(team, league.year)
    out.append(f"   {paint('Stadium fund', C.GRAY)} {paint(fi.money(sd.fund(team)), C.BGREEN, C.BOLD)}"
               + paint(f"  (boosters give ~{fi.money(sd.donations(league, team))} a year)", C.GRAY)
               + (f"   {paint('Bonds', C.GRAY)} {fi.money(bl)} still owed" if bl else ""))
    pr = st.get("project")
    if pr:
        left = sum(a for y, a, w in team.fac_spend if w.startswith("stadium:") and "deposit" not in w
                   and y > league.year) + bl
        out.append(f"   {paint('UNDER CONSTRUCTION', C.BMAGENTA, C.BOLD)} {sd.PARTS[pr['key']]['name']} → "
                   f"{sd.tier_name(pr['key'], pr['tier'])} · opens for the {pr['done'] + 1} season"
                   + paint(f" · {fi.money(left)} still to pay", C.GRAY))
    return out


def stadium_screen(league, team):
    mine = _mine(league, team)
    msg = ""
    while True:
        clear()
        color = league.conference_color(team.conference)
        st = sd.ensure(team)
        p = st["parts"]
        print(title_bar(f"{team.stadium.upper()}  ·  {team.school.upper()}  ·  {league.year}", color))
        for ln in summary_lines(league, team):
            print(ln)
        n = 0
        keys = {}
        for group, parts in sd.GROUPS:
            print(section(group, color))
            for k in parts:
                n += 1
                keys[str(n)] = k
                lv = p[k]
                tag = paint(f"[{n:>2}]", C.BYELLOW, C.BOLD) if mine else paint(f" {n:>2} ", C.GRAY)
                cur = sd.tier_name(k, lv)
                if sd.PARTS[k]["seats"]:
                    cur += paint(f" {sd.seats_of(team, k) // 100 / 10:.1f}k", C.GRAY) if lv or k == "lower_bowl" else ""
                if lv >= sd.max_tier(k):
                    nxt = paint("maxed out", C.BGREEN)
                elif st.get("project") and st["project"]["key"] == k:
                    nxt = paint(f"building → opens {st['project']['done'] + 1}", C.BMAGENTA)
                else:
                    t = lv + 1
                    need = sd.missing(team, k, t)
                    yrs = sd.PARTS[k]["build"][t]
                    cost = paint(pad(fi.money(sd.price(team, k, t)), 7, "right"), C.BWHITE if not need else C.GRAY)
                    nxt = f"{cost} {paint(f'{yrs}yr', C.GRAY)} " + \
                        (paint("needs " + sd.PARTS[need[0][0]]["name"].lower(), C.GRAY) if need
                         else paint(_effect(k), C.BCYAN))
                print(f"   {tag} {pad(sd.PARTS[k]['name'], 21)} {pad(_pips(k, lv), 7)} "
                      f"{pad(truncate(cur, 36) if not sd.PARTS[k]['seats'] else cur, 32)} {nxt}")
        if msg:
            print(paint(f"\n   {msg}", C.BYELLOW))
            msg = ""
        print(rule())
        extra = f"{paint('[H]', C.GRAY)} history   {paint('[T]', C.GRAY)} toughest places to play   {paint('[B]', C.GRAY)} back"
        if mine:
            print(f"   {paint('[1-' + str(n) + ']', C.BYELLOW)} a part — what it does, and build the next tier   {extra}")
            print(f"   {paint('[D]', C.BYELLOW)} move NIL money into the stadium fund   "
                  + paint(f"(available now {fi.money(fi.available(league, team))})", C.GRAY))
        else:
            print(f"   {paint('[1-' + str(n) + ']', C.GRAY)} a part   {extra}   " + paint("The AD runs this building plan.", C.GRAY))
        c = ask("Select:").strip().lower()
        if c in keys:
            msg = part_screen(league, team, keys[c], mine) or ""
        elif c == "d" and mine:
            amt = fi.parse_money(ask(f"How much? (e.g. 500k, 1.5m — you have {fi.money(fi.available(league, team))} "
                                     "available; it comes out of next season's NIL pool)"))
            if amt and amt > fi.available(league, team):
                import budget_fix
                budget_fix.cover(league, team, amt, f"stadium fund deposit: {fi.money(amt)}")
            if amt:
                ok, msg = sd.deposit(league, team, amt)
        elif c == "h":
            history_screen(league, team)
        elif c == "t":
            toughest_screen(league)
        else:
            return


def part_screen(league, team, key, mine):
    """One part: every tier, what it does, and breaking ground on the next one."""
    clear()
    color = league.conference_color(team.conference)
    P = sd.PARTS[key]
    lv = sd.parts(team)[key]
    print(title_bar(f"{team.stadium.upper()}  ·  {P['name'].upper()}", color))
    print(paint(f"   {P['blurb']}", C.GRAY))
    print(paint(f"   Each tier: {_effect(key, short=False)}.", C.BCYAN))
    if key == "surface":
        print(paint("   Home-game injury rate: " + ", ".join(f"{sd.tier_name(key, t).lower()} {sd.INJURY[t]:.2f}x"
                                                            for t in range(1, sd.max_tier(key) + 1)), C.GRAY))
    print()
    for t in range(P["min"], sd.max_tier(key) + 1):
        here = paint(" ◀ now", C.BGREEN, C.BOLD) if t == lv else ""
        cost = "" if t <= P["min"] else f"{fi.money(sd.price(team, key, t)):>7}  {P['build'][t]} season{'s' if P['build'][t] != 1 else ' '}"
        need = sd.PARTS[key]["req"].get(t, [])
        req = paint("  needs " + ", ".join(sd.tier_name(k, v) for k, v in need), C.GRAY) \
            if need else ""
        seats = paint(f"  {t * P['seats']:,} seats", C.GRAY) if P["seats"] and t else ""
        col = C.BWHITE if t == lv else C.GRAY if t < lv else C.WHITE
        print(f"   {paint(pad(str(t), 3), col)}{pad(paint(sd.tier_name(key, t), col, C.BOLD if t == lv else ''), 34)}"
              f"{pad(cost, 22)}{seats}{req}{here}")
    print()
    if not mine:
        pause()
        return ""
    if lv >= sd.max_tier(key):
        pause("As good as it gets. Press Enter...")
        return ""
    t = lv + 1
    print(section(f"BUILD: {sd.tier_name(key, t).upper()}  ·  {fi.money(sd.price(team, key, t))}", color))
    print(paint(f"   Stadium fund: {fi.money(sd.fund(team))}. The fund pays first; the rest comes out of the NIL pool "
                "as it's built,\n   or from a bond the fund pays back every offseason (if the fund runs dry, "
                "the NIL pool covers it).", C.GRAY))
    labels = {"fund": "Pay from the stadium fund", "build": "Fund + NIL pool as it's built"}
    labels.update({n: f"Fund + bond over {n} seasons (+{int(x * 100)}%)" for n, x in sd.BOND_TERMS.items()})
    opts = {}
    for i, plan in enumerate(sd.plans(team, key, t), 1):
        ok_p, _, (down, sc), why_p = sd.can_build(league, team, key, plan)
        rest = sum(a for _, a in sc)
        if not sc:
            how = f"{fi.money(down)} now"
        elif plan == "build":
            how = f"{fi.money(down)} now + {fi.money(sc[0][1])}/season of NIL {sc[0][0]}–{sc[-1][0]}"
        else:
            how = f"{fi.money(down)} now + {fi.money(sc[0][1])}/season from the fund {sc[0][0]}–{sc[-1][0]}"
        mark = paint(f"[{i}]", C.BYELLOW, C.BOLD) if ok_p else paint(f" {i} ", C.GRAY)
        print(f"   {mark} {pad(labels[plan], 40)} {pad(fi.money(down + rest), 8, 'right')}   {paint(how, C.GRAY)}"
              + ("" if ok_p else paint(f"\n        can't: {why_p}", C.BRED)))
        if ok_p:
            opts[str(i)] = plan
    yrs = P["build"][t]
    print(paint(f"\n   It opens for the {league.year + yrs} season. One stadium project at a time.", C.GRAY))
    if P["seats"] and team.capacity + P["seats"] > sd.fanbase(team) * 1.1:
        print(paint(f"   Heads up: your fan base is about {sd.fanbase(team) // 1000 * 1000:,}. Seats nobody buys are "
                    "quiet seats — and no ticket money.", C.BRED))
    if not opts:
        pause()
        return ""
    c = ask("Build it? Pick a way to pay (Enter = not now):").strip()
    if c in opts:
        ok, m = sd.build(league, team, key, opts[c], who="you")
        return m
    return ""


def history_screen(league, team):
    clear()
    color = league.conference_color(team.conference)
    st = sd.ensure(team)
    print(title_bar(f"{team.stadium.upper()}  ·  HISTORY", color))
    print(section("PROJECTS", color))
    for yr, what in reversed(st["log"][-15:]):
        print(f"   {paint(str(yr), C.GRAY)}  {what}")
    if not st["log"]:
        print(paint("   Nothing built yet.", C.GRAY))
    print()
    print(section("AT HOME", color))
    print(paint(f"   {'YEAR':<7}{'HOME':<8}{'RANKED W':<10}{'AVG CROWD':<12}{'FULL':<8}", C.GRAY))
    for yr, w, l, rk, att, fill in reversed(st["home_log"]):
        print(f"   {yr:<7}{f'{w}-{l}':<8}{rk:<10}{att:<12,}{fill * 100:.0f}%")
    w, l, rk, att, fill = sd.season_home(league, team)
    if w + l and not (st["home_log"] and st["home_log"][-1][0] == league.year):
        print(paint(f"   {league.year:<7}{f'{w}-{l}':<8}{rk:<10}{att:<12,}{fill * 100:.0f}%   (so far)", C.BCYAN))
    print(paint(f"\n   Home win streak: {sd.home_streak(league, team)}", C.GRAY))
    pause()


# ═══ Toughest places to play ═══════════════════════════════════════════════

def _move(now, before, has_prev=True):
    if not has_prev:
        return paint("   —", C.GRAY)
    if before is None:
        return paint("  NEW", C.BGREEN) if now <= 25 else paint("   —", C.GRAY)
    d = before - now
    return paint(f"  ▲{d:<2}", C.BGREEN) if d > 0 else paint(f"  ▼{-d:<2}", C.BRED) if d < 0 else paint("   —", C.GRAY)


def toughest_screen(league):
    show = 25
    while True:
        clear()
        rows = sd.ranking(league)
        hist = getattr(league, "tough_hist", {})
        prev_year = max((y for y in hist if y < league.year), default=None)
        prev = {row[0]: i for i, row in enumerate(hist.get(prev_year, []), 1)} if prev_year else {}
        stage = "PRESEASON" if league.week == 0 and not league.season_complete else \
            "FINAL" if league.season_complete else f"AFTER WEEK {league.week}"
        print(title_bar(f"TOUGHEST PLACES TO PLAY  ·  {league.year}  ·  {stage}"))
        print(paint("   The building's noise, the crowd, the home record (this season counts double, plus the last "
                    "three),\n   ranked teams sent home beaten, the home streak and the tradition. "
                    + (f"Movement is from the final {prev_year} list." if prev_year else ""), C.GRAY))
        print(paint(f"   {'RK':<4}{'MOVE':<6}{'TEAM':<19}{'STADIUM':<17}{'CAP':>8}  {'NOISE':<10}{'CROWD':<13}"
                    f"{'HOME':<6}{'3-YR':<7}{'SCORE':>5}", C.GRAY, C.BOLD))
        you = _you(league)
        for i, (t, score, p) in enumerate(rows[:show], 1):
            color = league.conference_color(t.conference)
            name = paint(truncate(t.school, 18), color, C.BOLD)
            if t is you:
                name = paint("▶ ", C.BYELLOW) + paint(truncate(t.school, 16), color, C.BOLD)
            crowd = f"{p['att'] // 1000}k {min(100, p['fill'] * 100):.0f}%"
            h, h3 = p["home"], p["home3"]
            print(f"   {paint(f'{i:<4}', C.BYELLOW if i <= 5 else C.BWHITE)}{pad(_move(i, prev.get(t.school), bool(prev)), 6)}"
                  f"{pad(name, 19)}{paint(pad(truncate(t.stadium, 16), 17), C.GRAY)}{t.capacity:>8,}  "
                  f"{pad(sd.noise_word(p['noise']), 10)}{pad(crowd, 13)}{pad(f'{h[0]}-{h[1]}', 6)}"
                  f"{pad(f'{h3[0]}-{h3[1]}', 7)}{paint(f'{score:>5.1f}', C.BWHITE, C.BOLD)}")
        if you is not None and all(t is not you for t, _, _ in rows[:show]):
            i = next(n for n, (t, _, _) in enumerate(rows, 1) if t is you)
            t, score, p = rows[i - 1]
            print(paint(f"   ...\n   {i:<4}{pad('', 6)}{pad(truncate(t.school, 18), 19)}"
                        f"{pad(truncate(t.stadium, 16), 17)}{t.capacity:>8,}  {pad(sd.noise_word(p['noise']), 10)}"
                        f"{pad(str(p['att'] // 1000) + 'k ' + str(round(min(100, p['fill'] * 100))) + '%', 13)}"
                        f"{pad(str(p['home'][0]) + '-' + str(p['home'][1]), 6)}"
                        f"{pad(str(p['home3'][0]) + '-' + str(p['home3'][1]), 7)}{score:>5.1f}", C.BCYAN))
        print(rule())
        print(f"   {paint('[#]', C.BYELLOW)} a team's breakdown   {paint('[A]', C.BYELLOW)} "
              f"{'top 25' if show > 25 else 'all FBS'}   {paint('[Y]', C.BYELLOW)} past seasons   {paint('[B]', C.GRAY)} back")
        c = ask("Select:").strip().lower()
        if c.isdigit() and 1 <= int(c) <= len(rows):
            breakdown(league, *rows[int(c) - 1])
        elif c == "a":
            show = 25 if show > 25 else len(rows)
        elif c == "y":
            past_lists(league)
        else:
            return


def _you(league):
    if getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is not None:
        return league.user_team
    import ad_mode
    if getattr(league, "mode", None) == "ad" and ad_mode.active(league):
        return ad_mode.my_team(league)
    return getattr(league, "follow_team", None)


def breakdown(league, team, score, p):
    clear()
    color = league.conference_color(team.conference)
    rk = sd.rank_of(league, team)
    print(title_bar(f"No. {rk}  ·  {team.stadium.upper()}  ·  {team.school.upper()}", color))
    rows = [("The building", p["building"], 20, f"{sd.noise_word(p['noise'])} — {p['noise']}/10 on noise"),
            ("The crowd", p["crowd"], 20, f"about {p['att']:,} a game, {min(100, p['fill'] * 100):.0f}% full"),
            ("Home record", p["record"], 35, f"{p['home'][0]}-{p['home'][1]} this season · "
                                             f"{p['home3'][0]}-{p['home3'][1]} over four"),
            ("Ranked scalps", p["scalps"], 12, f"{p['ranked']} ranked visitor{'s' if p['ranked'] != 1 else ''} beaten "
                                               "here in four seasons"),
            ("Home streak", p["streak"], 8, f"{p['run']} straight at home"),
            ("Tradition", p["tradition"], 5, "the history of the place")]
    print()
    for label, v, mx, note in rows:
        filled = int(round(v / mx * 20))
        print(f"   {pad(label, 15)}{paint('━' * filled, C.BCYAN, C.BOLD)}{paint('─' * (20 - filled), C.GRAY)} "
              f"{paint(f'{v:4.1f}', C.BWHITE, C.BOLD)}/{mx:<3} {paint(note, C.GRAY)}")
    print(f"\n   {pad('TOTAL', 15)}{' ' * 21}{paint(f'{score:.1f}', C.BYELLOW, C.BOLD)}/100")
    print()
    for ln in summary_lines(league, team):
        print(ln)
    loud = sorted((k for k in sd.ORDER if sd.PARTS[k]["fx"].get("noise") and sd.parts(team)[k] > sd.PARTS[k]["min"]),
                  key=lambda k: -sd.PARTS[k]["fx"]["noise"] * (sd.parts(team)[k] - sd.PARTS[k]["min"]))[:3]
    if loud:
        print(paint("   What makes it loud: " + ", ".join(sd.tier_name(k, sd.parts(team)[k]).lower() for k in loud), C.GRAY))
    vl = sd.parts(team)["visitor_locker"]
    if vl:
        print(paint(f"   Visitors dress in the {sd.tier_name('visitor_locker', vl).lower()}.", C.GRAY))
    print(paint("\n   [S] the stadium, part by part   [Enter] back", C.GRAY))
    if ask("Select:").strip().lower() == "s":
        stadium_screen(league, team)


def past_lists(league):
    hist = getattr(league, "tough_hist", {})
    if not hist:
        clear()
        print(title_bar("TOUGHEST PLACES TO PLAY  ·  PAST SEASONS"))
        print(paint("\n   No finished seasons yet. The first final list is kept when this season ends.", C.GRAY))
        pause()
        return
    years = sorted(hist)
    y = years[-1]
    while True:
        clear()
        print(title_bar(f"TOUGHEST PLACES TO PLAY  ·  {y} FINAL"))
        before = {r[0]: i for i, r in enumerate(hist.get(y - 1, []), 1)}
        print(paint(f"   {'RK':<4}{'MOVE':<6}{'TEAM':<22}{'NOISE':<11}{'HOME':<7}{'CROWD':>9}{'SCORE':>8}", C.GRAY, C.BOLD))
        for i, (school, score, noise, home, att) in enumerate(hist[y][:25], 1):
            print(f"   {paint(f'{i:<4}', C.BYELLOW if i <= 5 else C.BWHITE)}"
                  f"{pad(_move(i, before.get(school)) if (y - 1) in hist else paint('   —', C.GRAY), 6)}"
                  f"{pad(truncate(school, 21), 22)}{pad(sd.noise_word(noise), 11)}{pad(f'{home[0]}-{home[1]}', 7)}"
                  f"{att:>9,}{score:>8.1f}")
        print(rule())
        print(paint(f"   Seasons kept: {', '.join(str(x) for x in years)}   [P] previous  [N] next  [B] back", C.GRAY))
        c = ask("Select (or type a year):").strip().lower()
        if c == "p" and years.index(y) > 0:
            y = years[years.index(y) - 1]
        elif c == "n" and years.index(y) < len(years) - 1:
            y = years[years.index(y) + 1]
        elif c.isdigit() and int(c) in hist:
            y = int(c)
        elif c in ("b", ""):
            return
