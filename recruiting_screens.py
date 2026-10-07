"""
recruiting_screens.py — The recruiting interface.

You never see a recruit's real rating. You see a range that narrows as your
staff does its homework, a word instead of a number for where you stand, and
priorities that stay hidden as "???" until you've spent the time to learn
them. Hours are the constraint on every screen: the header always tells you
what you have left this week, and actions you can't afford are grayed out.
"""
from collections import Counter

from recruiting_data import (ACTIONS, CLASS_SIZE, PERSONALITIES, PRIORITY_LABELS, STATES)
from recruiting import STAR_TALENT
from roster import ROSTER_SIZE
from ui import (C, short_name, WIDTH, ask, bar, chip, clear, columns, command_bar, key, meter, pad, paint, panel, pause, rule,
                section, stars, title_bar, truncate)

STANDING_COLOR = {"LEADING": C.BGREEN, "IN GOOD SHAPE": C.BGREEN, "IN THE MIX": C.BYELLOW,
                  "ON THE FRINGE": C.YELLOW, "LONG SHOT": C.GRAY}


def _context(league):
    """Whose recruiting you're looking at, and whether you can touch it.
    Your board is yours alone — no staff, AI or otherwise, ever adds to it."""
    from screens import pick_team
    mode = getattr(league, "mode", None)
    if mode == "career":
        team = league.user_team
        if team is not None:
            return team, False
        print(paint("\n  You're not coaching anywhere right now. Pick a board to look at:", C.BYELLOW))
        return pick_team(league), True
    if mode == "spectator":
        import dashboard
        return dashboard.focus_team(league), True
    team = getattr(league, "user_team", None)
    if team is None:
        print(paint("\n  Which program are you recruiting for?", C.BYELLOW))
        team = pick_team(league)
        if team is None:
            return None, True
        league.user_team = team
    return team, False


def _hub_panels(league, team):
    cycle = league.recruiting
    commits = cycle.commitments(team)
    import finance as fi
    import compliance
    cap = compliance.class_cap(team, league)
    avg = sum(r.stars for r in commits) / len(commits) if commits else 0
    hrs, tot = cycle.remaining_hours(team), cycle.hours_for(team)
    rank = cycle.class_rank(team)
    status = [f"{paint('CLASS RANK', C.GRAY)}  "
              + (paint('#' + str(rank), C.BYELLOW, C.BOLD) if rank else paint('Unranked', C.GRAY)),
              f"{paint('COMMITS', C.GRAY)}     {paint(f'{len(commits)}/{cap}', C.BWHITE, C.BOLD)}  "
              f"{meter(len(commits), 14, maximum=cap, color=C.BGREEN)}"
              + (paint('  (CAB scholarship cuts)', C.BRED) if cap < CLASS_SIZE else ''),
              (f"{paint('AVG STARS', C.GRAY)}   {paint(f'{avg:.2f}', C.BYELLOW, C.BOLD)} {stars(round(avg))}" if commits
               else f"{paint('AVG STARS', C.GRAY)}   {paint('—', C.GRAY)}"),
              (f"{paint('HOURS', C.GRAY)}       {paint('contact period', C.BYELLOW, C.BOLD)}" if tot == 0 and league.week == 0 else
               f"{paint('HOURS', C.GRAY)}       {paint(f'{hrs}/{tot}', C.BWHITE, C.BOLD)}  "
               f"{meter(hrs, 14, maximum=max(1, tot), color=C.BCYAN)}"),
              ("" if tot == 0 and league.week == 0 else
               f"{paint('', C.GRAY)}            {paint(cycle.hours_explained(team, short=True), C.GRAY)}"),
              f"{paint('NIL FREE', C.GRAY)}    {paint(fi.money(fi.available(league, team)), C.BGREEN, C.BOLD)}",
              f"{paint('BOARD', C.GRAY)}       {len(team.recruiting_targets)}/40 targets"]
    needs = cycle._needs(team)
    signed = Counter(r.position for r in commits)
    on_board = Counter(r.position for r in team.recruiting_targets if r.committed_to is not team)
    need_lines = []
    for pos in ROSTER_SIZE:
        want = needs.get(pos, 0)
        if want <= 0:
            continue
        got = signed[pos]
        col = C.BGREEN if got >= want else C.BYELLOW if got else C.BRED
        need_lines.append(f"{paint(pad(pos, 4), C.BCYAN)}{pad(f'{got}/{want}', 5)}{meter(got, 6, maximum=want, color=col)}"
                          + paint(f" {on_board[pos]}●" if on_board[pos] else "", C.BYELLOW))
    if not need_lines:
        need_lines = [paint("Every room is full.", C.GRAY)]
    half = (len(need_lines) + 1) // 2
    need_rows = [pad(a, 22) + (b if b else "") for a, b in zip(need_lines[:half], need_lines[half:] + [""])]
    total = sum(v for v in needs.values() if v > 0)
    flex = max(0, cap - total)
    need_rows = need_rows[:5] + [paint(f"{total} to fill · {flex} flex (best available) · ● on board", C.GRAY)]
    board = cycle.board_for(team)
    hot = []
    for r in board[:6]:
        st = r.standing(team)
        hot.append(f"{pad(truncate(r.name, 18), 19)}{paint(pad(r.position, 3), C.BCYAN)} "
                   f"{paint(pad('★' * r.stars, 5), C.BYELLOW)}{paint(truncate(st, 13), STANDING_COLOR[st])}")
    if not hot:
        hot = [paint("Your board is empty.", C.BYELLOW), paint("Open the Recruit Finder [F] —", C.GRAY),
               paint("it suggests players who fit.", C.GRAY)]
    return (panel("CLASS STATUS", status, 38, height=7, color=C.BYELLOW),
            panel("POSITION NEEDS  (signed / needed)", need_rows, 61, height=7),
            panel("TOP OF YOUR BOARD", hot, 50, height=7),
            news_panel(league, 49))


def news_panel(league, w):
    lines = []
    for wk, kind, text in league.recruiting.news[:7]:
        col = C.BGREEN if kind == "commit" else C.BRED if kind == "decommit" else C.BCYAN
        lines.append(paint("● ", col) + text)
    if not lines:
        lines = [paint("No news yet.", C.GRAY)]
    return panel("RECRUITING WIRE", lines, w, height=7)


def recruiting_menu(league):
    """The recruiting hub: your class at a glance, and every recruiting tool."""
    import guide
    guide.tip(league, "recruiting")
    team, readonly = _context(league)
    if team is None:
        return
    league._recruit_readonly = readonly
    while True:
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"{team.school.upper()} RECRUITING  ·  {league.year + 1} CLASS  ·  {league.status}", color))
        a, b, c, d = _hub_panels(league, team)
        for ln in columns(a, b):
            print(ln)
        for ln in columns(c, d):
            print(ln)
        print(paint(f"  Hours this week — {league.recruiting.hours_explained(team)}", C.GRAY))
        if league.week == 0:
            print(paint("  CONTACT PERIOD — evaluation, calls/texts and offers only. Position coach and in-person visits open Week 1.",
                        C.BYELLOW))
        import recruit_plus as rp
        if not readonly:
            steps, _ = rp.plan(league.recruiting, team)
            runs = sum(1 for _, _, _, x in steps if x)
            cut = sum(1 for _, s, _, _ in steps if s.startswith("cut"))
            n_ov = sum(1 for r in league.recruiting.pool for t, w in rp.ov_of(r).items()
                       if t is team and w >= league.week and not r.signed)
            print(paint(f"  Standing orders: {len(rp.queue(league.recruiting, team))} in the queue · {runs} will run this week"
                        + (f" · {cut} will be cut" if cut else "") + f"   ·   Official visits booked: {n_ov}", C.BCYAN))
        items = [key("F", "Recruit finder"), key("G", "Suggested for you"), key("1", "My board"),
                 key("2", "My class"), key("3", "National rankings"), key("4", "Recruiting news"),
                 key("5", "Final class rankings"), key("6", "Budget & NIL")]
        if not readonly:
            items += [key("Q", "Standing orders", C.BGREEN), key("V", "Official visits", C.BGREEN),
                      key("W", "War room", C.BGREEN), key("H", "Hit or bust"),
                      key("O", "Overtime (+10 hrs, risky)", C.BRED), key("T", "Back channel (tampering)", C.BRED)]
            if league.week == 0:
                items.append(key("C", "Summer camp", C.BGREEN))
            if league.week >= 8:
                items.append(key("L", "Preferred walk-ons"))
        if readonly:
            items.append(paint("VIEW ONLY — this board belongs to another staff", C.GRAY))
        items.append(key("B", "back", C.GRAY))
        for ln in command_bar(items):
            print(ln)
        choice = ask("Select:").lower()
        if choice in ("o", "t") and not readonly:
            import gray_area
            (gray_area.overtime if choice == "o" else gray_area.tamper)(league, team)
            continue
        if choice == "f":
            finder(league, team)
        elif choice == "g":
            finder(league, team, suggested=True)
        elif choice == "1":
            board_screen(league, team)
        elif choice == "2":
            class_view(league, team)
        elif choice == "3":
            finder(league, team, preset="rank")
        elif choice == "4":
            news_screen(league)
        elif choice == "5":
            final_rankings(league, team)
        elif choice in ("6", "7", "$"):
            import finance_screens
            finance_screens.budget_screen(league, team)
        elif not readonly and choice in ("q", "v", "w", "h", "c", "l"):
            import recruit_ui as ru
            if choice == "q":
                ru.queue_screen(league, team)
            elif choice == "v":
                ru.visits_screen(league, team)
            elif choice == "w":
                ru.war_room(league, team)
            elif choice == "h":
                ru.hit_or_bust(league, team)
            elif choice == "c":
                note = ru.camp_screen(league, team)
                if note:
                    print(paint("  " + note, C.BCYAN))
                    pause()
            elif choice == "l":
                ru.walkons_screen(league, team)
        else:
            return


def _needs_line(league, team):
    needs = league.recruiting._needs(team)
    signed = Counter(r.position for r in league.recruiting.commitments(team))
    short = [f"{pos} {needs[pos] - signed[pos]}" for pos in ROSTER_SIZE
             if needs.get(pos, 0) - signed[pos] > 0]
    return "Still need: " + ", ".join(short) if short else "Class needs are covered"


# ═══ The recruit finder ══════════════════════════════════════════════════════

REGIONS = sorted({v[1] for v in STATES.values()})
SORTS = {"rank": "national rank", "stars": "stars", "proj": "your projection", "interest": "his interest in you",
         "near": "closest to campus", "fit": "suggested fit"}


def _home_state(team):
    from recruiting_data import TEAM_STATES
    return TEAM_STATES.get(team.school)


def _scheme_fit(team, pos):
    """How your schemes sell this position: + means recruits want to play it here."""
    from recruiting import DEF_SCHEME_FIT, OFF_SCHEME_FIT, _schemes
    off, df = _schemes(team)
    return OFF_SCHEME_FIT.get(off, {}).get(pos, 0) + DEF_SCHEME_FIT.get(df, {}).get(pos, 0)


def suggestion(league, team, r):
    """How well a recruit fits your program right now, and why. Built only from
    what your staff can see: public stars, your scouting, your needs, your schemes,
    where he's from and how he's responding to you. Returns (score, [reasons])."""
    cycle = league.recruiting
    needs = cycle._needs(team)
    signed = Counter(x.position for x in cycle.commitments(team))
    on_board = Counter(x.position for x in team.recruiting_targets if x.committed_to is None)
    reasons, score = [], 0.0
    gap = needs.get(r.position, 0) - signed[r.position]
    if gap > 0:
        urgent = 1.5 if r.position == "QB" else 0.0          # the room that decides seasons
        score += 3 + urgent + min(3, gap) - min(4, on_board[r.position] * 1.0)   # spread the board across needs
        reasons.append(("NEED " + r.position, C.BRED))
    if r.position == getattr(team, "priority_pos", None):
        score += 1.5
        reasons.append(("STAFF PRIORITY", C.BMAGENTA))
    tier = team.prestige / 20
    diff = r.stars - tier
    if -1.2 <= diff <= 0.6:
        score += 2
    elif diff > 0.6:
        score += 1.5 - (diff - 0.6) * 3
        reasons.append(("REACH", C.BMAGENTA))
    else:
        score -= 1
    lo, hi = r.scouting_range(team)
    score += max(-1.0, min(2.0, ((lo + hi) / 2 - 45) / 8))  # a better prospect is a better suggestion
    home = _home_state(team)
    if home and r.home_state == home:
        score += 1.4
        reasons.append(("IN-STATE", C.BCYAN))
    elif home and STATES[r.home_state][1] == STATES[home][1]:
        score += 0.8
        reasons.append(("REGION", C.CYAN))
    elif home and r.position not in ("K", "P"):
        score -= 0.5
        reasons.append(("OUT OF REGION", C.GRAY))
    fit = _scheme_fit(team, r.position)
    if fit >= 6:                                             # the scheme screen's "recruits want to play X here"
        score += 0.8
        reasons.append(("SCHEME FIT", C.BGREEN))
    elif fit <= -4:
        score -= 0.8
        reasons.append(("HARD SELL", C.BYELLOW))
    interest = r.interest.get(team, 0)
    if interest >= 25:
        score += 2 + (interest - 25) / 15
        reasons.append(("INTERESTED", C.BGREEN))
    if r.scout[team] >= 1 and (lo + hi) / 2 >= STAR_TALENT.get(min(5, r.stars + 1), 99) - 3:
        score += 2
        reasons.append(("SLEEPER", C.BYELLOW))
    if r.committed_to is not None:
        score -= 4
        reasons.append(("COMMITTED", C.GRAY))
    return score, reasons


def _spread(ranked, per_page=18, cap=4):
    """Keep a suggested list mixed: no more than `cap` players at one position on a page,
    so adding one player doesn't flip the next page to seven of the same thing."""
    out, waiting = [], list(ranked)
    while waiting:
        page, rest, counts = [], [], Counter()
        for r in waiting:
            if len(page) < per_page and counts[r.position] < cap:
                page.append(r)
                counts[r.position] += 1
            else:
                rest.append(r)
        if not page:
            page, rest = rest[:per_page], rest[per_page:]
        out += page
        waiting = rest
    return out


def _filtered(league, team, f):
    cycle = league.recruiting
    home = _home_state(team)
    out = []
    q = f.get("name", "").lower()
    for r in cycle.pool:
        if r.signed:
            continue
        if f["pos"] and r.position != f["pos"]:
            continue
        if not (f["min_stars"] <= r.stars <= f["max_stars"]):
            continue
        if f["state"] and r.home_state != f["state"]:
            continue
        if f["region"] and STATES[r.home_state][1] != f["region"]:
            continue
        if f["status"] == "open" and r.committed_to is not None:
            continue
        if f["status"] == "soft" and r.committed_to is not None and r.lead_margin() >= 12:
            continue
        if f["status"] == "mine" and r.committed_to is not team:
            continue
        if f["top"] and r.national_rank > f["top"]:
            continue
        if f["proj"] and r.scouting_range(team)[1] < f["proj"]:
            continue
        if f["interest"] and r.interest.get(team, 0) < 15:
            continue
        if f["need"]:
            needs = cycle._needs(team)
            if needs.get(r.position, 0) - sum(1 for x in cycle.commitments(team) if x.position == r.position) <= 0:
                continue
        if f["hide_board"] and r in team.recruiting_targets:
            continue
        if f["near"] and home and STATES[r.home_state][1] != STATES[home][1]:
            continue
        if q and q not in r.name.lower():
            continue
        out.append(r)
    s = f["sort"]
    if s == "rank":
        out.sort(key=lambda r: r.national_rank)
    elif s == "stars":
        out.sort(key=lambda r: (-r.stars, r.national_rank))
    elif s == "proj":
        out.sort(key=lambda r: (-sum(r.scouting_range(team)), r.national_rank))
    elif s == "interest":
        out.sort(key=lambda r: (-r.interest.get(team, 0), r.national_rank))
    elif s == "near":
        out.sort(key=lambda r: (0 if r.home_state == home else 1 if home and STATES[r.home_state][1] == STATES[home][1]
                                else 2, r.national_rank))
    else:
        scored = {r: suggestion(league, team, r)[0] for r in out}
        out.sort(key=lambda r: (-scored[r], r.national_rank))
        if not f["pos"]:
            out = _spread(out[:120]) + out[120:]
        if not (f["pos"] or f["state"] or f["region"] or f["name"]):
            out = out[:60]                                   # a suggestion list, not the whole country
    return out


def _new_filters(preset=None):
    f = {"pos": None, "min_stars": 1, "max_stars": 5, "state": None, "region": None, "status": "any",
         "top": None, "proj": None, "interest": False, "need": False, "hide_board": False, "near": False,
         "name": "", "sort": "rank"}
    if preset == "suggested":
        f.update(sort="fit", status="open", hide_board=True)
    return f


def _filter_chips(f):
    chips = []
    if f["pos"]:
        chips.append(f["pos"])
    if (f["min_stars"], f["max_stars"]) != (1, 5):
        chips.append(f"{f['min_stars']}-{f['max_stars']}★" if f["min_stars"] != f["max_stars"] else f"{f['min_stars']}★")
    if f["state"]:
        chips.append(f["state"])
    if f["region"]:
        chips.append(f["region"])
    if f["status"] != "any":
        chips.append({"open": "UNCOMMITTED", "soft": "OPEN OR SOFT", "mine": "MY COMMITS"}[f["status"]])
    if f["top"]:
        chips.append(f"TOP {f['top']}")
    if f["proj"]:
        chips.append(f"PROJ {__import__('scout').ovr_plain(f['proj'])}+")
    if f["interest"]:
        chips.append("INTERESTED IN ME")
    if f["need"]:
        chips.append("NEEDS ONLY")
    if f["near"]:
        chips.append("MY REGION")
    if f["hide_board"]:
        chips.append("NOT ON BOARD")
    if f["name"]:
        chips.append(f'"{f["name"]}"')
    return " ".join(chip(c, C.BCYAN) for c in chips) if chips else paint("no filters — everybody", C.GRAY)


def _filter_menu(league, f):
    while True:
        clear()
        print(title_bar("RECRUIT FINDER  ·  FILTERS", C.BCYAN))
        rows = [
            ("1", "Position", f["pos"] or "any"),
            ("2", "Stars", f"{f['min_stars']} to {f['max_stars']}"),
            ("3", "Home state", f["state"] or "any"),
            ("4", "Region", f["region"] or "any"),
            ("5", "Status", {"any": "everybody", "open": "uncommitted", "soft": "uncommitted or soft commits",
                             "mine": "committed to me"}[f["status"]]),
            ("6", "National rank", f"top {f['top']}" if f["top"] else "any"),
            ("7", "Your projection at least", __import__('scout').ovr_plain(f["proj"]) if f["proj"] else "any"),
            ("8", "Showing interest in you", "yes" if f["interest"] else "don't care"),
            ("9", "Only positions I still need", "on" if f["need"] else "off"),
            ("10", "Only my region (shortcut)", "on" if f["near"] else "off"),
            ("11", "Hide players on my board", "yes" if f["hide_board"] else "no"),
            ("12", "Name contains", f["name"] or "—"),
        ]
        lines = [f"{pad(key(k, label), 34)}{paint(v, C.BWHITE, C.BOLD)}" for k, label, v in rows]
        for ln in panel("FILTERS", lines, 70, color=C.BCYAN):
            print("   " + ln)
        for ln in command_bar([key("#", "change"), key("R", "reset all"), key("Enter", "search", C.BGREEN)]):
            print(ln)
        c = ask("Change which filter?").strip().lower()
        if c == "":
            return
        if c == "r":
            keep = f["sort"]
            f.clear()
            f.update(_new_filters())
            f["sort"] = keep
        elif c == "1":
            v = ask("Position (QB RB WR TE OL DL LB CB S K P, Enter = any):").strip().upper()
            f["pos"] = v if v in ROSTER_SIZE else None
        elif c == "2":
            v = ask("Stars — one number (4) or a range (3-5):").strip()
            try:
                lo, _, hi = v.partition("-")
                lo = int(lo)
                hi = int(hi) if hi else lo
                f["min_stars"], f["max_stars"] = max(1, min(lo, hi)), min(5, max(lo, hi))
            except ValueError:
                f["min_stars"], f["max_stars"] = 1, 5
        elif c == "3":
            v = ask("Two-letter state (TX, FL, ...; Enter = any):").strip().upper()
            f["state"] = v if v in STATES else None
        elif c == "4":
            for i, reg in enumerate(REGIONS, 1):
                print(f"   {key(str(i), reg)}")
            v = ask("Region # (Enter = any):").strip()
            f["region"] = REGIONS[int(v) - 1] if v.isdigit() and 1 <= int(v) <= len(REGIONS) else None
        elif c == "5":
            order = ["any", "open", "soft", "mine"]
            f["status"] = order[(order.index(f["status"]) + 1) % len(order)]
        elif c == "6":
            v = ask("Top how many nationally (e.g. 100; Enter = any):").strip()
            f["top"] = int(v) if v.isdigit() else None
        elif c == "7":
            import scout
            if scout.hidden():
                v = ask("Minimum projection: [1] backup [2] rotation [3] starter [4] quality starter [5] star "
                        "(Enter = any):").strip()
                f["proj"] = {"1": 56, "2": 64, "3": 70, "4": 76, "5": 82}.get(v)
            else:
                v = ask("Minimum projection, by your scouting (e.g. 70; Enter = any):").strip()
                f["proj"] = int(v) if v.isdigit() else None
        elif c == "8":
            f["interest"] = not f["interest"]
        elif c == "9":
            f["need"] = not f["need"]
        elif c == "10":
            f["near"] = not f["near"]
        elif c == "11":
            f["hide_board"] = not f["hide_board"]
        elif c == "12":
            f["name"] = ask("Name contains (Enter = clear):").strip()


def finder(league, team, suggested=False, preset=None):
    """Search the whole national pool. Filter, sort, open a card, add to your board."""
    cycle = league.recruiting
    readonly = getattr(league, "_recruit_readonly", False)
    f = _new_filters("suggested" if suggested else None)
    if preset == "rank":
        f["sort"] = "rank"
    page, per = 0, 18
    msg = ""
    results, stale = None, True
    while True:
        if stale or results is None:
            results = _filtered(league, team, f)            # row numbers hold still until you change something
            stale = False
        pages = max(1, (len(results) + per - 1) // per)
        page = max(0, min(page, pages - 1))
        chunk = results[page * per:(page + 1) * per]
        clear()
        title = "SUGGESTED FOR YOU" if f["sort"] == "fit" and not f["pos"] else "RECRUIT FINDER"
        what = f"  ·  {f['pos']}" if f["pos"] else ""
        print(title_bar(f"{title}{what}  ·  {team.school.upper()}  ·  {len(results):,} MATCHES", C.BCYAN))
        print(f"  {paint('FILTERS', C.GRAY)} {_filter_chips(f)}")
        print(f"  {paint('SORT', C.GRAY)} {chip(SORTS[f['sort']].upper(), C.BYELLOW)}   "
              f"{paint('HOURS', C.GRAY)} {cycle.remaining_hours(team)}   "
              f"{paint('BOARD', C.GRAY)} {len(team.recruiting_targets)}/40   "
              f"{paint('page', C.GRAY)} {page + 1}/{pages}")
        print()
        hdr = f"  {'#':>3}  {'RK':>4}  {'PLAYER':<20}{'POS':<4}{'STARS':<6}{'HOME':<5}{'PROJ':<9}{'STANDING':<15}{'STATUS':<14}"
        print(paint(hdr + ("WHY" if f["sort"] == "fit" else ""), C.GRAY, C.BOLD))
        for i, r in enumerate(chunk, page * per + 1):
            lo, hi = r.scouting_range(team)
            st = r.standing(team) if r.interest.get(team) else "NO CONTACT"
            import recruit_plus as rp
            pc = rp.public_commit(r, team)
            if r.committed_to is team:
                status = paint("◆ YOURS", C.BGREEN, C.BOLD)
            elif pc:
                status = paint(f"◆ {truncate(pc.abbr if hasattr(pc, 'abbr') else pc.school, 11)}", C.BRED)
            else:
                status = paint("open", C.GRAY)
            board = paint("●", C.BYELLOW) if r in team.recruiting_targets else " "
            row = (f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}{board} {paint(f'{r.national_rank:>4}', C.GRAY)}  "
                   f"{pad(truncate(r.name, 19), 20)}{paint(pad(r.position, 4), C.BCYAN)}"
                   f"{pad(paint('★' * r.stars, C.BYELLOW), 6)}"
                   f"{paint(pad({'juco': 'JC', 'intl': 'INT'}.get(getattr(r, 'kind', 'hs') if hasattr(r, 'kind') else 'hs', r.home_state), 5), C.BMAGENTA if getattr(r, 'kind', 'hs') in ('juco', 'intl') else C.GRAY)}"
                   f"{pad(__import__('scout').proj_short(lo, hi), 9)}{pad(paint(truncate(st, 14), STANDING_COLOR.get(st, C.GRAY)), 15)}"
                   f"{pad(status, 14)}")
            if f["sort"] == "fit":
                _, why = suggestion(league, team, r)
                room, tags = 14, []                      # one line per recruit: only the reasons that fit
                for t, col in why[:4]:
                    if len(t) + 1 > room:
                        continue
                    tags.append(paint(t, col, C.BOLD))
                    room -= len(t) + 1
                row += " ".join(tags)
            print(row)
        if not chunk:
            print(paint("\n   Nobody matches. Loosen a filter [F] or reset [R].", C.BYELLOW))
        print(paint("\n  ● on your board   ◆ committed   JC junior college   INT international   PROJ is your staff's read\n"
                    "  NO CONTACT: he hasn't heard from you yet — a call or an offer puts you on his list", C.GRAY))
        import scout as _sc
        if _sc.hidden(league):
            print(paint(f"  PROJ: {_sc.LEGEND}", C.GRAY))
        items = [key("#", "open card"), key("A#", "add (A3 or A1,4,7)", C.BGREEN), key("F", "filters"),
                 key("S", "sort"), key("G", "suggested"), key("R", "reset"), key("N/P", "page"), key("B", "back", C.GRAY)]
        if readonly:
            items = [key("#", "open card"), key("F", "filters"), key("S", "sort"), key("N/P", "page"),
                     key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        if msg:
            print(paint("  " + msg, C.BGREEN, C.BOLD))
            msg = ""
        c = ask("Select:").strip().lower()
        if c in ("", "b"):
            return
        if c == "n":
            page += 1
        elif c == "p":
            page -= 1
        elif c == "f":
            _filter_menu(league, f)
            page, stale = 0, True
        elif c == "s":
            order = list(SORTS)
            f["sort"] = order[(order.index(f["sort"]) + 1) % len(order)]
            page, stale = 0, True
        elif c == "g":
            f.update(sort="fit", status="open", hide_board=True)
            page, stale = 0, True
        elif c == "r":
            f.clear()
            f.update(_new_filters())
            page, stale = 0, True
        elif c.startswith("a") and not readonly:
            added, full = [], False
            for part in c[1:].replace(" ", "").split(","):
                if part.isdigit() and 1 <= int(part) <= len(results):
                    r = results[int(part) - 1]
                    if cycle.add_target(team, r):
                        added.append(r.name)
                    elif len(team.recruiting_targets) >= 40:
                        full = True
            msg = (f"Added to your board: {', '.join(added)}. (They stay on this list, marked ●, until you"
                   f" change a filter.)" if added else "") + ("  Your board is full (40)." if full else "")
        elif c.isdigit() and 1 <= int(c) <= len(results):
            recruit_card(league, team, results[int(c) - 1])
        else:
            msg = "Type a row number, A and row numbers (A3 or A1,4,7), or a letter from the bar."


def big_board(league, team):
    finder(league, team, preset="rank")


# ═══ Your board ══════════════════════════════════════════════════════════════

def board_screen(league, team):
    import guide
    guide.tip(league, "board")
    cycle = league.recruiting
    readonly = getattr(league, "_recruit_readonly", False)
    msg = ""
    sort = "rank"
    while True:
        clear()
        board = cycle.board_for(team)
        if sort == "pos":
            order = list(ROSTER_SIZE)
            board.sort(key=lambda r: (order.index(r.position), r.national_rank))
        elif sort == "standing":
            board.sort(key=lambda r: (-r.interest.get(team, 0), r.national_rank))
        color = league.conference_color(team.conference)
        import finance as fi
        print(title_bar(f"{team.school.upper()}  ·  RECRUITING BOARD  ·  {len(board)}/40", color))
        hrs, tot = cycle.remaining_hours(team), cycle.hours_for(team)
        print(f"  {paint('HOURS', C.GRAY)} {paint(f'{hrs}/{tot}', C.BWHITE, C.BOLD)} {meter(hrs, 16, maximum=max(1, tot), color=C.BCYAN)}"
              f"   {paint('NIL FREE', C.GRAY)} {paint(fi.money(fi.available(league, team)), C.BGREEN, C.BOLD)}"
              f"   {paint(_needs_line(league, team), C.GRAY)}")
        print(paint(f"  {cycle.hours_explained(team)}", C.GRAY))
        print()
        if not board:
            lines = [paint("Nobody on your board yet — and nobody will be until you put them there.", C.BYELLOW),
                     "", paint("Open the Recruit Finder [F]: filter by position, stars, state, region, your", C.GRAY),
                     paint("projection and interest, or let it suggest players who fit your needs [G].", C.GRAY)]
            for ln in panel("EMPTY BOARD", lines, 96, color=C.BYELLOW):
                print("  " + ln)
        else:
            # Every row fits the 100-column screen: 2 + 4 + 5 + 19 + 4 + 6 + 9 + 9 + 14 + 3 + 7 + 3 + 15 = 100.
            print(paint(f"  {'#':>3} {'RK':>4} {'PLAYER':<19}{'POS':<4}{'STARS':<6}{'PROJ':<9}{'INTEREST':<9}{'STANDING':<14}"
                        f"{'OF':<3}{'NIL':>6} {'':<3}{'LEADER'}", C.GRAY, C.BOLD))
            for i, r in enumerate(board, 1):
                lo, hi = r.scouting_range(team)
                st = r.standing(team) if r.interest.get(team) else "NO CONTACT"
                import recruit_plus as rp
                pcom = rp.public_commit(r, team)
                if pcom:
                    kind = (" " + ("E" if rp.g(r, "early") else "H" if rp.g(r, "commit_kind") == "hard" else "S")
                            if pcom is team else "")
                    lead = paint(f"◆ {short_name(pcom.school, 13 - len(kind))}", C.BGREEN if pcom is team else C.BRED, C.BOLD)
                    lead += paint(kind, C.GRAY)
                else:
                    ld = r.leader()
                    lead = paint(short_name(ld.school, 15), C.BGREEN if ld is team else C.GRAY) if ld else paint("open", C.GRAY)
                flags = ("Q" if any(e["r"] is r for e in rp.queue(cycle, team)) else "") + ("V" if team in rp.ov_of(r) else "")
                offer = paint("✔", C.BGREEN, C.BOLD) if team in r.offers else paint("—", C.GRAY)
                print(f"  {paint(f'{i:>3}', C.BYELLOW, C.BOLD)} {paint(f'{r.national_rank:>4}', C.GRAY)} "
                      f"{pad(truncate(r.name, 18), 19)}{paint(pad(r.position, 4), C.BCYAN)}"
                      f"{pad(paint('★' * r.stars, C.BYELLOW), 6)}{pad(__import__('scout').proj_short(lo, hi), 9)}"
                      f"{meter(r.interest.get(team, 0), 8, color=STANDING_COLOR.get(st, C.GRAY))} "
                      f"{pad(paint(truncate(st, 13), STANDING_COLOR.get(st, C.GRAY)), 14)}{pad(offer, 3)}"
                      f"{pad(_nil_cell(cycle, team, r), 6, 'right')} {paint(pad(flags, 3), C.BYELLOW)}{lead}")
        print(paint("  ◆ committed: H hard · S soft · E signed early   Q in your standing orders   V visit booked",
                    C.GRAY))
        items = [key("#", "open card"), key("F", "find recruits", C.BGREEN), key("G", "suggested"),
                 key("Q#", "queue an order"), key("$#", "NIL offer"), key("D#", "drop"),
                 key("S", "sort: " + {"rank": "national rank", "pos": "position", "standing": "your standing"}[sort]),
                 key("B", "back", C.GRAY)]
        if readonly:
            items = [key("#", "open card"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        if msg:
            print(paint("  " + msg, C.BCYAN, C.BOLD))
            msg = ""
        choice = ask("Select:").lower()
        if readonly and choice and choice[0] in "fgd$q":
            continue
        if choice.startswith("$") and choice[1:].isdigit():
            idx = int(choice[1:]) - 1
            if 0 <= idx < len(board):
                import finance_screens
                print(paint(f"   {board[idx].name} — {board[idx].stars}-star {board[idx].position}", C.BWHITE, C.BOLD))
                res = finance_screens.nil_prompt(league, team, board[idx])
                if res:
                    msg = res[1]
            continue
        if choice.startswith("q") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(board):
            import recruit_ui as ru
            msg = ru.add_order_flow(league, team, board[int(choice[1:]) - 1])
            continue
        if choice.startswith("d") and choice[1:].isdigit():
            idx = int(choice[1:]) - 1
            if 0 <= idx < len(board):
                cycle.drop_target(team, board[idx])
                msg = f"Dropped {board[idx].name}."
        elif choice == "f":
            finder(league, team)
        elif choice == "g":
            finder(league, team, suggested=True)
        elif choice == "s":
            sort = {"rank": "pos", "pos": "standing", "standing": "rank"}[sort]
        elif choice.isdigit() and 1 <= int(choice) <= len(board):
            recruit_card(league, team, board[int(choice) - 1])
        else:
            return


# ═══ The recruit card ════════════════════════════════════════════════════════

def recruit_card(league, team, recruit):
    cycle = league.recruiting
    readonly = getattr(league, "_recruit_readonly", False)
    msg = ""
    while True:
        clear()
        r = recruit
        lo, hi = r.scouting_range(team)
        color = C.BYELLOW if r.stars >= 4 else C.BCYAN
        print(title_bar(f"{r.name.upper()}  ·  {r.position}  ·  {r.stars}-STAR  ·  NATIONAL #{r.national_rank}", color))
        on_board = r in team.recruiting_targets
        tag = chip("ON YOUR BOARD", C.BYELLOW) if on_board else ""
        if r.committed_to is team:
            tag += " " + chip("COMMITTED TO YOU", C.BGREEN)
        elif r.committed_to:
            tag += " " + chip(f"COMMITTED: {r.committed_to.school.upper()}", C.BRED)
        size = f"{r.player.height // 12}'{r.player.height % 12}\" · {r.player.weight} lbs"
        import recruit_plus as rp
        pc = rp.public_commit(r, team)
        if r.committed_to is team and rp.commit_word(r):
            tag += " " + chip(rp.commit_word(r).upper(), C.BGREEN)
        elif pc is not None and r.committed_to is not team:
            tag = tag.replace(chip(f"COMMITTED: {r.committed_to.school.upper()}", C.BRED),
                              chip(f"{rp.commit_word(r).split(' ·')[0].upper()}: {pc.school.upper()}", C.BRED))
        elif pc is None and r.committed_to is not None and r.committed_to is not team:
            tag = tag.replace(chip(f"COMMITTED: {r.committed_to.school.upper()}", C.BRED), "")   # a silent commit
        size = size + f" · {rp.origin_line(r)}"
        first_line = (f"{stars(r.stars)}  {paint(STATES[r.home_state][0], C.BWHITE)}  "
                      f"{paint(size, C.GRAY)}")
        rec, line = rp.senior_season(r, league.week)
        pv = rp.pipeline_of(team, r)
        cb = rp.crystal(r, league.recruiting)
        extras = [paint("SENIOR SEASON ", C.GRAY) + line if rp.g(r, "kind", "hs") == "hs" else paint(line, C.GRAY)]
        if pv:
            extras.append(paint(f"PIPELINE {rp.g(r, 'hs', '')}: {rp.pipe_word(pv)}", C.BGREEN))
        if cb:
            extras.append(paint("CRYSTAL BALL ", C.GRAY) + paint(f"{cb[0].school} {cb[1]}%", C.BGREEN if cb[0] is team else C.BYELLOW))
        conns = rp.class_connections(cycle, team, r, 2)
        if conns:
            social = "; ".join(f"{x[1].player.name} — {x[2]}" for x in conns)
            extras.append(paint("CLASS CONNECTION ", C.GRAY) + paint(social, C.BMAGENTA))
        mom = rp.class_momentum(cycle, team)
        if mom >= 18 and r.committed_to is not team:
            extras.append(paint("CLASS MOMENTUM ", C.GRAY) + paint(f"{rp.momentum_word(mom)} ({mom:.0f}/100)", C.BGREEN))
        if not r.signed and r.committed_to is not team and r.interest.get(team, 0) >= 30:
            import recruiting as _rc
            blocked = _rc.block_reason(league, team, r, league.recruiting._class_of(team))
            if blocked:
                extras.append(paint(f"⚠ YOU CAN'T SIGN HIM RIGHT NOW: {blocked}", C.BRED, C.BOLD))
            elif r.committed_to is None and r.leader() is team:
                left = rp.room_left(league.recruiting, team, r.position)
                ahead = sum(1 for k in rp._leaning(league.recruiting).get((team, r.position), ())
                            if k < r.national_rank)
                if ahead >= left:
                    extras.append(paint(f"⚠ ROOM IS TIGHT AT {r.position}: {left} spot{'s' if left != 1 else ''} left, "
                                        f"{ahead} higher-ranked uncommitted kid{'s' if ahead != 1 else ''} leaning your way "
                                        f"pick first on signing day", C.BYELLOW, C.BOLD))
        ov = rp.ov_of(r)
        extras.append(paint(f"OFFICIAL VISITS {len(ov)}/{rp.OV_MAX}", C.GRAY)
                      + (": " + ", ".join(f"{t.school} (Wk {w})" for t, w in sorted(ov.items(), key=lambda x: x[1]))
                         if ov else ""))
        import faces
        if faces.enabled():
            import faces_ui
            for ln in faces_ui.recruit_header(r, first_line, ([tag.strip()] if tag.strip() else []) + extras, color):
                print(ln)
        else:
            print("  " + first_line + "   " + tag)
            print("  " + "   ".join(extras[:2]))
            print("  " + "   ".join(extras[2:]))
        print()
        # left: scouting and what he wants
        known = rp.known(r, team)
        import scout
        left = [f"{paint('PROJECTION', C.GRAY)}  {paint(scout.proj(lo, hi), C.BWHITE, C.BOLD)}",
                (bar((lo + hi) // 2, 36) if not scout.hidden() else
                 paint(f"  scouted {r.scout[team]}/3 · tighter = better known", C.GRAY)), "",
                paint("WHAT HE WANTS", C.GRAY)]
        for i, pr_ in enumerate(r.priorities):
            if pr_ in known:
                left.append(f" {i + 1}. {paint(PRIORITY_LABELS[pr_], C.BWHITE, C.BOLD)}")
            else:
                left.append(paint(f" {i + 1}. ???  (evaluate, or pitch it and see)", C.GRAY))
        if r.scout[team] >= 2:
            left.append(paint(f"Reads as: {PERSONALITIES[r.personality]['label']}", C.GRAY))
        # right: the race
        st = r.standing(team)
        right = [f"{paint('YOU', C.GRAY)}  {paint(st, STANDING_COLOR[st], C.BOLD)}   "
                 f"{paint('offer', C.GRAY)} {paint('YES', C.BGREEN, C.BOLD) if team in r.offers else paint('no', C.BRED)}"
                 f"   {paint('offers out', C.GRAY)} {len(r.offers)}", ""]
        tops = r.top_schools(5)
        top_val = max((r.interest[t] for t in tops), default=1) or 1
        for t in tops:
            name = paint(pad(truncate(t.school, 16), 17), C.BWHITE if t is team else C.GRAY, C.BOLD if t is team else "")
            col = C.BGREEN if t is team else league.conference_color(t.conference)
            right.append(f"{name}{meter(r.interest[t], 18, maximum=max(top_val, 1), color=col)}"
                         + paint(f" {r.interest[t]:>3.0f}", C.GRAY)
                         + (paint(" ◆", C.BGREEN) if r.committed_to is t and rp.public_commit(r, team) is t else ""))
        if not tops:
            right.append(paint("Nobody's in on him yet.", C.GRAY))
        elif top_val < 25 and r.committed_to is None:
            right.append(paint("Early days: interest 0-100, and nobody has a real hold yet.", C.GRAY))
        for ln in columns(panel("SCOUTING REPORT", left, 46, height=9), panel("THE RACE", right, 53, height=9)):
            print(ln)
        import finance_screens
        for ln in panel("NIL", finance_screens.nil_lines(league, team, r), 100, color=C.BGREEN, title_color=C.BGREEN):
            print(ln)
        # actions
        hrs = cycle.remaining_hours(team)
        acts = []
        keys = list(ACTIONS)
        for i, k in enumerate(keys, 1):
            label, cost, effect, rel, scout = ACTIONS[k]
            afford = hrs >= cost and not readonly
            acts.append(key(str(i), f"{label} ({cost}h)", dim=not afford))
        print(f"  {paint('STAFF HOURS LEFT', C.GRAY)} {paint(str(hrs), C.BWHITE, C.BOLD)}")
        import promises
        pr = promises.of(r)
        mine_pr = pr if pr and pr.get("school") == team.school else None
        if mine_pr:
            print(f"  {paint('YOUR PROMISE', C.GRAY)} {paint(promises.KINDS[mine_pr['kind']][0], C.BYELLOW, C.BOLD)}")
        print(f"  {paint('HIS ROOM', C.GRAY)} {paint(promises.room_line(team, r), C.GRAY)}")
        story = rp.log_of(cycle, team, r)[-3:]
        for wk, line in reversed(story):
            print(paint(f"  {'Wk ' + str(wk) if wk else 'Summer':<8}{truncate(line, 88)}", C.BMAGENTA if "BIDDING" in line
                        or "telling" in line or "record" in line or "loaded" in line or "sit behind" in line else C.GRAY))
        nq = sum(1 for e in rp.queue(cycle, team) if e["r"] is r)
        extra = [key("Q", f"queue an order{f' ({nq} queued)' if nq else ''}", C.BGREEN),
                 key("V", "official visit", dim=team in rp.ov_of(r) or readonly),
                 key("N", "NIL offer"), key("M", "make a promise", dim=bool(mine_pr) or readonly),
                 key("T", "remove from board" if on_board else "add to board", C.BGREEN),
                 key("B", "back", C.GRAY)]
        if readonly:
            acts, extra = [], [paint("VIEW ONLY", C.GRAY), key("B", "back", C.GRAY)]
        for ln in command_bar(acts + extra):
            print(ln)
        if msg:
            print(paint("  " + msg, C.BCYAN, C.BOLD))
            msg = ""
        choice = ask("Select:").lower()
        if readonly or choice in ("", "b"):
            return
        if choice == "n":
            res = finance_screens.nil_prompt(league, team, r)
            if res:
                msg = res[1]
        elif choice == "m":
            msg = _promise_prompt(league, team, r)
        elif choice == "q":
            import recruit_ui as ru
            msg = ru.add_order_flow(league, team, r)
        elif choice == "v":
            import recruit_ui as ru
            msg = ru.plan_visit(league, team, r)
        elif choice == "w":
            ok, msg = rp.add_pwo(cycle, team, r)
        elif choice == "t":
            if on_board:
                cycle.drop_target(team, r)
                msg = "Off your board."
            else:
                msg = "Added to your board." if cycle.add_target(team, r) else "Your board is full (40)."
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            act = keys[int(choice) - 1]
            pitch = None
            if act in rp.PITCH_ACTIONS and team in r.offers and not r.signed \
                    and cycle.remaining_hours(team) >= rp.action_cost(team, act):
                import recruit_ui as ru
                pitch = ru.ask_pitch(league, team, r) or "auto"
            ok, text = cycle.apply_action(team, r, act, pitch=pitch)
            if ok and r not in team.recruiting_targets:
                cycle.add_target(team, r)                   # working a recruit puts him on your board
            msg = text
        else:
            return


def _promise_prompt(league, team, r):
    """[M] on a recruit card: what you tell him about his future."""
    import promises
    why_not = promises.precheck(league, team, r)
    if why_not:
        return why_not
    rec = promises.record(team)
    print()
    print(paint(f"  What do you promise {r.player.first_name}?  "
                f"(your record: {rec['kept']} kept, {rec['broken']} broken)", C.BWHITE, C.BOLD))
    print(paint("  " + promises.room_line(team, r, n=6), C.GRAY))
    kinds = list(promises.KINDS)
    for i, k in enumerate(kinds, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {promises.KINDS[k][0]}")
        print("       " + promises.hint(team, r, k))
    c = ask("Promise (Enter = none):").strip()
    if not (c.isdigit() and 1 <= int(c) <= len(kinds)):
        return ""
    ok, text = promises.make(league, team, r, kinds[int(c) - 1])
    return text


def _nil_cell(cycle, team, recruit):
    import finance as fi
    amt = fi.offer_to(cycle, team, recruit)
    return paint(fi.money(amt), C.BGREEN) if amt else paint("—", C.GRAY)


def class_view(league, team):
    clear()
    cycle = league.recruiting
    commits = cycle.commitments(team)
    color = league.conference_color(team.conference)
    print(title_bar(f"{team.school.upper()} · {league.year + 1} RECRUITING CLASS", color))
    avg = sum(r.stars for r in commits) / len(commits) if commits else 0
    import compliance
    import recruit_plus as rp
    mom = rp.class_momentum(cycle, team)
    print(f"   {paint('Commitments', C.GRAY)} {len(commits)}/{compliance.class_cap(team, league)}    "
          f"{paint('Average', C.GRAY)} {avg:.2f}★    "
          f"{paint('National class rank', C.GRAY)} {('#' + str(cycle.class_rank(team))) if cycle.class_rank(team) else 'Unranked'}")
    print(f"   {paint('Class momentum', C.GRAY)} {paint(rp.momentum_word(mom).upper(), C.BGREEN if mom >= 38 else C.BYELLOW)} "
          f"{mom:.0f}/100    {paint('Commitments create more pull when targets know the players joining you.', C.GRAY)}")
    print(paint(f"   {_needs_line(league, team)}", C.GRAY))
    print()
    if not commits:
        print(paint("   No commitments yet.", C.GRAY))
        pause()
        return
    by_pos = {}
    for r in commits:
        by_pos.setdefault(r.position, []).append(r)
    for pos in ROSTER_SIZE:
        group = by_pos.get(pos)
        if not group:
            continue
        print(f"   {paint(pad(pos, 5), C.BCYAN)}"
              + "   ".join(f"{paint(truncate(r.name, 18), C.BWHITE)} "
                           f"{paint(str(r.stars) + '★', C.BYELLOW)} ({r.home_state})" for r in group[:3]))
        for extra in range(3, len(group), 3):
            print("        " + "   ".join(f"{paint(truncate(r.name, 18), C.BWHITE)} "
                                          f"{paint(str(r.stars) + '★', C.BYELLOW)} ({r.home_state})"
                                          for r in group[extra:extra + 3]))
    print()
    top = sorted(league.teams, key=lambda t: -cycle.class_score(t))[:10]
    print(section("NATIONAL CLASS RANKINGS", C.BCYAN))
    for i, t in enumerate(top, 1):
        k = cycle.commitments(t)
        a = sum(r.stars for r in k) / len(k) if k else 0
        mark = paint(" ←", C.BYELLOW) if t is team else ""
        print(f"   {paint(f'{i:<3}', C.BYELLOW if i <= 5 else C.BWHITE)}"
              f"{pad(truncate(t.school, 22), 24)}{len(k):>3} {'commit ' if len(k) == 1 else 'commits'}   {a:.2f}★{mark}")
    pause()


def final_rankings(league, team=None, report=None, year=None):
    """End-of-cycle national class rankings — who won signing day.

    Works off a finished signing class when one is handed in (straight out of
    the offseason), and off the current board otherwise."""
    cycle = league.recruiting
    if report is not None:
        classes = {t: report.classes.get(t, []) for t in league.teams}
        label = f"{year or league.year} SIGNING DAY"
    else:
        classes = {t: cycle.commitments(t) for t in league.teams}
        label = f"{league.year + 1} CLASS RANKINGS · IN PROGRESS"
    from recruiting import class_points
    order = sorted(league.teams, key=lambda t: -class_points(classes[t]))
    page = 0
    while True:
        clear()
        print(title_bar(label))
        print(paint(f"   {'RK':<5}{'TEAM':<24}{'CONF':<16}{'SIGNEES':<9}{'AVG':<7}{'5★':<4}{'4★':<4}"
                    f"{'TOP SIGNEE'}", C.GRAY))
        block = order[page * 25:(page + 1) * 25]
        for i, t in enumerate(block, page * 25 + 1):
            k = classes[t]
            if not k:
                continue
            avg = sum(r.stars for r in k) / len(k)
            fives = sum(1 for r in k if r.stars == 5)
            fours = sum(1 for r in k if r.stars == 4)
            best = max(k, key=lambda r: (r.stars, -r.national_rank))
            mark = paint(" ←", C.BYELLOW) if t is team else ""
            color = league.conference_color(t.conference)
            print(f"   {paint(f'{i:<4}', C.BYELLOW if i <= 5 else C.BWHITE)} "
                  f"{pad(paint(truncate(t.school, 22), color, C.BOLD), 24)}"
                  f"{paint(pad(t.conference, 16), C.GRAY)}{pad(str(len(k)), 9)}"
                  f"{pad(f'{avg:.2f}', 7)}{pad(str(fives), 4)}{pad(str(fours), 4)}"
                  f"{paint(f'{best.stars}★ {truncate(best.name, 18)} ({best.position})', C.GRAY)}{mark}")
        if team is not None and team not in block:
            rank = order.index(team) + 1
            k = classes[team]
            avg = sum(r.stars for r in k) / len(k) if k else 0
            print(paint(f"\n   Your class: #{rank}  {team.school}  ·  {len(k)} signees  ·  {avg:.2f} stars", C.BYELLOW))
        print(paint(f"\n   [N] next 25   [P] previous   [B] back", C.GRAY))
        choice = ask("Select:").lower()
        if choice == "n" and (page + 1) * 25 < len(order):
            page += 1
        elif choice == "p" and page:
            page -= 1
        else:
            return


def news_screen(league):
    clear()
    cycle = league.recruiting
    print(title_bar(f"{league.year + 1} RECRUITING NEWS"))
    if not cycle.news:
        print(paint("\n   Quiet so far. The board heats up once teams start offering.", C.GRAY))
        pause()
        return
    for week, kind, text in cycle.news[:26]:
        tag = {"commit": paint("COMMIT", C.BGREEN), "flip": paint("FLIP  ", C.BRED), "visit": paint("VISIT ", C.BCYAN),
               "rating": paint("RATING", C.BYELLOW), "cb": paint("CRYSTL", C.BMAGENTA)}.get(kind, paint("NEWS  ", C.GRAY))
        print(f"   {paint(f'Wk {week:<3}', C.GRAY)}{tag}  {text}")
    pause()
