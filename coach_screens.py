"""
coach_screens.py — Looking at the sport through its coaches.

  Coaches menu      all head coaches (sortable), the hot seat, the carousel,
                    the candidate pool, and search (including retired coaches)
  Coach profile     bio, ratings, seat, program goals, splits for this job and
                    his career, and a season-by-season history across jobs
  Program page      a team's AD, its three goals, and its coaching history
"""
import carousel as cz
from ui import short_name, C, WIDTH, ask, bar, clear, pad, paint, pause, rating, rule, section, title_bar, truncate

PAGE = 25


def _pct(w, l):
    return f"{w / (w + l):.3f}"[1:] if w + l else " —  "


def _wl(w, l):
    return f"{w}-{l}" if w or l else "—"          # no games on the books yet


def seat_color(heat):
    return C.BRED if heat >= 70 else C.BYELLOW if heat >= 50 else C.BGREEN if heat < 25 else C.BWHITE


def seat_tag(coach):
    heat = getattr(coach, "seat", 0)
    return paint(f"{cz.seat_label(heat):<9}", seat_color(heat))


def _tenure_years(league, coach):
    if not coach.hired_year:
        return 0
    return max(0, league.year - coach.hired_year + (0 if league.week == 0 and league.year < coach.hired_year else 1))


# ═══ Menu ═══════════════════════════════════════════════════════════════════

def coaches_menu(league):
    while True:
        clear()
        print(title_bar("COACHES"))
        coaches = cz.all_coaches(league)
        hot = sum(c.seat >= 70 for c in coaches)
        print(paint(f"   {len(coaches)} FBS head coaches  ·  {hot} on a hot seat  ·  "
                    f"{len([c for c in league.coach_pool if c.status == 'unemployed'])} candidates available", C.GRAY))
        print()
        items = [("1", "All Head Coaches"), ("2", "Hot Seat Rankings"), ("3", "Coaching Carousel (changes by year)"),
                 ("4", "Candidate Pool"), ("5", "Find a Coach"), ("6", "Coordinators"),
                 ("7", "Rising Coordinators (head coach material)"), ("A", "Athletic Directors (the AD market)")]
        me = getattr(league, "user_coach", None)
        if me is not None and getattr(league, "mode", None) == "career" and me.status != "retired":
            items.append(("8", "Pursue a job (your agent)"))
        for key, label in items:
            print(f"   {paint(f'[{key}]', C.BYELLOW, C.BOLD)}  {label}")
        print(f"   {paint('[B]', C.GRAY, C.BOLD)}  Back")
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        if choice == "1":
            coach_list(league, coaches, "ALL HEAD COACHES", sort="o")
        elif choice == "2":
            coach_list(league, coaches, "HOT SEAT RANKINGS", sort="s")
        elif choice == "3":
            carousel_news(league)
        elif choice == "4":
            pool = [c for c in league.coach_pool if c.status == "unemployed"]
            coach_list(league, pool, "CANDIDATE POOL", sort="o", pool=True)
        elif choice == "5":
            find_coach(league)
        elif choice == "6":
            coordinator_list(league, rising=False)
        elif choice == "7":
            coordinator_list(league, rising=True)
        elif choice == "a":
            import ad_market
            ad_market.screen(league)
        elif choice == "8" and any(k == "8" for k, _ in items):
            import job_market
            job_market.pursue_screen(league)


# ═══ Lists ══════════════════════════════════════════════════════════════════

SORTS = {
    "o": ("overall", lambda c: -c.overall),
    "s": ("seat", lambda c: -getattr(c, "seat", 0)),
    "w": ("career win %", lambda c: -(sum(s["w"] for s in c.history) /
                                     max(1, sum(s["w"] + s["l"] for s in c.history)))),
    "a": ("age", lambda c: c.age),
    "t": ("tenure", lambda c: (c.hired_year or 9999)),
    "r": ("recruiting", lambda c: -c.ratings["recruiting"]),
}


def coach_list(league, coaches, title, sort="o", pool=False):
    page = 0
    while True:
        rows = sorted(coaches, key=SORTS[sort][1])
        pages = max(1, (len(rows) + PAGE - 1) // PAGE)
        page = min(page, pages - 1)
        clear()
        print(title_bar(f"{title}  ·  BY {SORTS[sort][0].upper()}  ·  PAGE {page + 1}/{pages}"))
        if pool:
            print(paint(f"   {'#':>3}  {'COACH':<22}{'AGE':>4}  {'OVR':>3}  {'RCRT':>4}  {'PERSONALITY':<11}  BACKGROUND",
                        C.GRAY, C.BOLD))
        else:
            print(paint(f"   {'#':>3}  {'COACH':<22}{'SCHOOL':<18}{'AGE':>4}  {'OVR':>3}  {'RCRT':>4}  {'SINCE':>5}  "
                        f"{'TENURE':>7}  {'CAREER':>7}  {'SEAT':<9}  AD", C.GRAY, C.BOLD))
        start = page * PAGE
        for i, c in enumerate(rows[start:start + PAGE], start + 1):
            if pool:
                bg = c.origin if not c.history else f"fired by {c.history[-1]['school']} ({cz._record(c)} career)"
                print(f"   {paint(f'{i:>3}', C.GRAY)}  {pad(truncate(c.name, 21), 22)}{c.age:>4}  {rating(c.overall)}  "
                      f" {rating(c.ratings['recruiting'])}  {pad(truncate(cz.PERSONALITIES[c.personality][0], 11), 11)}  "
                      f"{paint(truncate(bg, 52), C.GRAY)}")
            else:
                ten = cz.splits(cz.tenure_seasons(c))
                car = cz.splits(c.history)
                if not (c.history and c.history[-1].get("year") == league.year):      # this season isn't booked yet
                    for d in (ten, car):
                        d["w"], d["l"] = d["w"] + c.team.wins, d["l"] + c.team.losses
                team = c.team
                color = league.conference_color(team.conference)
                ad = cz.AD_STYLES[team.ad["style"]][0]
                print(f"   {paint(f'{i:>3}', C.GRAY)}  {pad(truncate(c.name, 21), 22)}"
                      f"{pad(paint(short_name(team.school, 17), color), 18)}{c.age:>4}  {rating(c.overall)}  "
                      f" {rating(c.ratings['recruiting'])}  {c.hired_year or '—':>5}  "
                      f"{_wl(ten['w'], ten['l']):>7}  {_wl(car['w'], car['l']):>7}  {seat_tag(c)}  "
                      f"{paint(ad, C.GRAY)}")
        print(rule())
        print(paint("   Records are tracked from 2026 on.  " if not pool else "   ", C.GRAY) +
              "  ".join(f"{paint(f'[{k.upper()}]', C.BYELLOW)} {v[0]}" for k, v in SORTS.items() if not (pool and k in "st")))
        print(f"   {paint('[N]', C.BYELLOW)} next page  {paint('[P]', C.BYELLOW)} previous  "
              f"{paint('[#]', C.BYELLOW)} open a coach  {paint('[B]', C.GRAY, C.BOLD)} back")
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        if choice == "n":
            page = (page + 1) % pages
        elif choice == "p":
            page = (page - 1) % pages
        elif choice in SORTS:
            sort, page = choice, 0
        elif choice.isdigit() and 1 <= int(choice) <= len(rows):
            coach_view(league, rows[int(choice) - 1])


def find_coach(league):
    q = ask("Coach or school name:").lower().strip()
    if not q:
        return
    import staff
    everyone = cz.all_coaches(league) + staff.coordinators(league) + league.coach_pool + league.retired_coaches
    hits = [c for c in everyone if q in c.name.lower() or (c.team and q in c.team.school.lower())
            or any(q in s["school"].lower() for s in c.history)]
    if not hits:
        print(paint("   Nobody by that name.", C.BYELLOW))
        pause()
        return
    if len(hits) == 1:
        coach_view(league, hits[0])
        return
    clear()
    print(title_bar(f"SEARCH: {q.upper()}"))
    for i, c in enumerate(hits[:30], 1):
        where = c.team.school if c.team else ("retired" if c.status == "retired" else "available")
        if getattr(c, "role", "HC") in ("OC", "DC") and c.team:
            where = f"{c.team.school} {c.role}"
        print(f"   {paint(f'{i:>2}', C.GRAY)}  {pad(c.name, 24)}{pad(where, 20)}{paint(cz._record(c), C.GRAY)}")
    choice = ask("Open #:")
    if choice.isdigit() and 1 <= int(choice) <= len(hits[:30]):
        coach_view(league, hits[int(choice) - 1])


def coordinator_list(league, rising=False):
    """Every OC and DC. 'Rising' sorts by head-coach buzz: resume, stage, age."""
    import staff
    coords = staff.coordinators(league)
    if rising:
        # Head-coach material: real buzz, still young enough to be "rising", and room left to grow.
        coords = [c for c in coords if c.age <= 50 and staff.buzz_score(c) >= 7
                  and (c.ceiling >= 80 or c.overall >= 78) and c.ceiling - c.overall >= 3]
        coords.sort(key=lambda c: -staff.buzz_score(c))
        coords = coords[:25]
        title = "RISING COORDINATORS  ·  BY BUZZ ▼"
    else:
        coords.sort(key=lambda c: -c.overall)
        title = "COORDINATORS  ·  BY OVR ▼"
    page = 0
    per = 25
    pages = max(1, (len(coords) + per - 1) // per)
    while True:
        page = max(0, min(page, pages - 1))
        clear()
        print(title_bar(f"{title}  ·  PAGE {page + 1}/{pages}" if pages > 1 else title))
        if not coords:
            print()
            print(paint("   No coordinators have built head-coach buzz yet — check back after a few weeks of games.",
                        C.GRAY))
            pause()
            return
        print(paint(f"   {'#':>3}  {'COACH':<22}{'JOB':<24}{'OVR':>4}{'CEIL':>6}{'AGE':>5}  {'LAST UNIT':<22}{'BUZZ'}",
                    C.GRAY, C.BOLD))
        chunk = coords[page * per:(page + 1) * per]
        for i, c in enumerate(chunk, page * per + 1):
            last = c.coord_history[-1] if c.coord_history else None
            unit = (f"#{last['rank']} {'offense' if last['role'] == 'OC' else 'defense'} ({last['year']})"
                    if last else "first year as coord.")
            job = f"{truncate(c.team.school, 17)} {c.role}"
            print(f"   {i:>3}  {pad(truncate(c.name, 21), 22)}{pad(job, 24)}{rating(c.overall):>4}"
                  f"{c.ceiling:>6}{c.age:>5}  {pad(unit, 22)}{_buzz(staff.buzz_score(c), c)}")
        nav = ("[N] next  " if page + 1 < pages else "") + ("[P] previous  " if page > 0 else "")
        choice = ask(f"# to open a coach, {nav}Enter to go back:").lower()
        if choice in ("", "b"):
            return
        if choice == "n":
            page += 1
        elif choice == "p":
            page -= 1
        elif choice.isdigit() and 1 <= int(choice) <= len(coords):
            coach_view(league, coords[int(choice) - 1])
            page = (int(choice) - 1) // per                # back to the page he's on


# ═══ Coach profile ══════════════════════════════════════════════════════════

def coach_view(league, coach, scout=False):
    """A coach's page. scout=True is the hiring view: only what an AD can see — the résumé."""
    import resume
    import staff
    clear()
    team = coach.team
    role = staff.role_of(coach)
    where = team.full_name if team else ("Retired" if coach.status == "retired" else "Available — not coaching")
    if role in ("OC", "DC") and team is not None:
        where = f"{team.school} {staff.ROLE_NAMES[role]}"
    print(title_bar(f"{coach.name.upper()}  ·  {where.upper()}"))
    import faces
    hero = faces.enabled() and not scout
    if hero:
        import faces_ui
        for ln in faces_ui.coach_hero(league, coach, role, where, color=league.team_color(team) if team is not None else C.BCYAN):
            print(ln)
        print()
    pname = cz.PERSONALITIES[coach.personality][0]
    pblurb = cz.personality_blurb(coach)
    upside = coach.ceiling - coach.overall
    potential = "Maxed out" if upside <= 1 else "Some room" if upside <= 5 else "High" if upside <= 12 else "Very high"
    info = [("Age", str(coach.age)),
            ("Personality", f"{pname} — {paint(pblurb, C.GRAY)}"),
            ("Alma mater", getattr(coach, "alma_mater", None) or "—"),
            ("Background", staff.background_text(coach)),
            ("At this job since", str(coach.hired_year) if team and coach.hired_year and role == "HC"
             else str(getattr(coach, "coord_since", "—")) if team else "—"),
            ]
    if role == "OC":
        info.append(("His offense", coach.offense_scheme))
    elif role == "DC":
        info.append(("His defense", coach.defense_scheme))
    else:
        info.append(("Offense / Defense", f"{coach.offense_scheme} · {coach.defense_scheme}"))
    fourth = "conservative" if coach.aggression < 42 else "aggressive" if coach.aggression >= 68 else "balanced"
    info.append(("Aggression", f"{coach.aggression}  {paint('(' + fourth + ' on fourth down)', C.GRAY)}"))
    if role in ("OC", "DC") and team is not None:
        side = "off" if role == "OC" else "def"
        caller = staff.play_caller(team, side)
        mine = getattr(team.coach, "is_user", False)
        if caller is coach:
            info.append(("His job", f"Calls the {'offense' if side == 'off' else 'defense'} and runs his scheme on Saturday."))
        else:
            info.append(("His job", f"{'You call' if mine else team.coach.name.split()[-1] + ' calls'} the "
                                    f"{'offense' if side == 'off' else 'defense'}, so his scheme sits on the shelf."))
            info.append(("", f"{coach.name.split()[-1]} develops his side's players and recruits his region; "
                             f"his traits count at half strength."))
        if team.coach is not None and team.coach.name not in getattr(coach, "staff_ties", set()):
            since = getattr(coach, "coord_since", None)
            if since is not None and since >= getattr(team.coach, "hired_year", 0):
                info.append(("Hired by", "the previous head coach, last winter, days before the change — "
                                         "he came with the job"))
            else:
                info.append(("Hired by", "the previous head coach — he came with the job"))
        if mine:
            info.append(("Changes", paint("play calling: tab 6 COACH → [S] My staff · fire or extend: offseason staff review",
                                          C.GRAY)))
    from traits import explain
    explained = explain(coach)
    if not explained:
        info.append(("Traits", "—"))
    for i, (label, what) in enumerate(explained):
        info.append(("Traits" if i == 0 else "", f"{paint(label, C.BWHITE, C.BOLD)} — {paint(what, C.GRAY)}"))
    import finance as fi
    k = fi.contract(coach)
    if k and team is not None:
        info.append(("Contract", f"{fi.deal_line(k, league)}  {paint('· ' + fi.money(fi.deal_total(k, league), exact=True) + ' total · owed if fired ' + fi.money(fi.owed(coach, league), exact=True), C.GRAY)}"))
        for line in fi.clause_lines(k, coach, league):
            info.append(("", paint(line, C.GRAY)))
    if getattr(coach, "career_earnings", 0):
        info.append(("Career earnings", fi.money(coach.career_earnings)))
    lineage = getattr(coach, "tree", None)
    if not isinstance(lineage, str):                  # your coach's "tree" is his skill tree, not a mentor
        lineage = (getattr(coach, "mentors", None) or [None])[-1]
    if lineage:
        info.append(("Coaching tree", f"{lineage}" + paint("  (worked under him)", C.GRAY)))
    rep_ = resume.reputation(coach, league)
    info.append(("Résumé", f"{resume.letter(rep_)}  {paint('(how the profession sees his record — not a rating)', C.GRAY)}"))
    if any(s_.get("class_rank") for s_ in coach.history[-4:]):
        info.append(("His classes", resume.letter(resume.recruit_rep(coach))))
    if role in ("OC", "DC"):
        info.append(("Recruits", f"the {getattr(coach, 'recruit_region', '—')}"))
        info.append(("Head coach buzz", _buzz(staff.buzz_score(coach), coach)))
    shown_in_hero = {"Age", "Offense / Defense", "Aggression", "His offense", "His defense"} if hero else set()
    for k, v in info:
        if k in shown_in_hero:
            continue
        print(f"   {paint(f'{k:<19}', C.GRAY)}{v}")
    print()
    if scout:
        print(section("WHAT YOU CAN'T SEE", C.BCYAN))
        print(paint("   Nobody hiring a coach sees his ratings or his ceiling. You have his record, the level he did it\n"
                    "   at, his classes, his units and how he interviews. You find out what he is when he coaches.", C.GRAY))
        if getattr(coach, "coord_history", None):
            print()
            _print_resume(coach)
        if coach.history:
            print()
            print(section("HEAD COACHING RECORD", C.BCYAN))
            for s_ in coach.history[-8:]:
                bits = [b for b, k in (("title", "title"), ("playoff", "cfp"), ("conf champ", "conf_champ"),
                                         ("bowl win", "bowl_win")) if s_.get(k)]
                fr = f"#{s_['final_rank']}" if s_.get("final_rank") else ""
                cls = f"class #{s_['class_rank']}" if s_.get("class_rank") else ""
                print(f"   {s_['year']}  {pad(s_['school'], 20)}{s_['w']:>2}-{s_['l']:<2}  {pad(fr, 5)}{pad(cls, 11)}"
                      f"{paint(', '.join(bits), C.BGREEN)}")
        pause()
        return
    print(section("RATINGS", C.BCYAN))
    print(f"   {'Overall':<26}{rating(coach.overall)}  {bar(coach.overall, 20)}   "
          f"{paint('Potential: ', C.GRAY)}{potential}")
    for k in coach.ratings:
        label = type(coach).RATING_LABELS[k]
        tag = "strength" if k in getattr(coach, "_rating_strengths", []) else "weakness" if k in getattr(coach, "_rating_weaknesses", []) else ""
        suffix = paint(f"  {tag}", C.BGREEN if tag == "strength" else C.BRED) if tag else ""
        print(f"   {label:<26}{rating(coach.ratings[k])}  {bar(coach.ratings[k], 20)}{suffix}")
    import coach_profile
    prof = coach_profile.ensure_sideline(coach)
    hi, lo = coach_profile.strengths_weaknesses(coach)
    print()
    print(section("SIDELINE PROFILE", C.BCYAN))
    print(paint("   How this staff actually works on Saturdays and with players.", C.GRAY))
    for k in coach_profile.SIDELINE_KEYS:
        v = prof[k]
        tag = "strength" if k in hi and v > coach.overall else "weakness" if k in lo and v < coach.overall else ""
        suffix = paint(f"  {tag}", C.BGREEN if tag == "strength" else C.BRED) if tag else ""
        print(f"   {coach_profile.SIDELINE_LABELS[k]:<26}{rating(v)}  {bar(v, 20)}{suffix}")
    if role == "HC" or coach.history:
        m = staff.mentor(coach)
        print(f"   {'Coordinator influence':<26}{rating(m)}  {bar(m, 20)}   {paint(staff.mentor_word(m), C.GRAY)}")

    if getattr(coach, "coord_history", None):
        print()
        _print_resume(coach)
    elif role in ("OC", "DC"):
        print()
        print(section("COORDINATOR RESUME", C.BCYAN))
        print(paint("   First coordinator job — no unit history yet. His numbers start this season.", C.GRAY))

    if team is not None and role == "HC":
        print()
        print(section("THE SEAT", C.BRED))
        heat = coach.seat
        style, blurb, rules = cz.AD_STYLES[team.ad["style"]]
        from ui import heat_meter
        print(f"   {paint(f'{cz.seat_label(heat):<10}', seat_color(heat), C.BOLD)} "
              f"{paint('cool', C.BGREEN)} {heat_meter(heat, 30)} {paint('hot', C.BRED)}  {heat}/100"
              + paint("  (70+ is hot)", C.GRAY))
        pulse = rules.get("pulse", 1.0)
        mood = "every Saturday is a referendum" if pulse >= 1.25 else "reacts to every result" if pulse >= 1.1 \
            else "doesn't overreact to one game" if pulse <= 0.8 else "watches the whole season"
        print(paint(f"   AD {team.ad['name']} · {style}: {blurb}. Fires around {int(cz.fire_line(team))}; {mood}.", C.GRAY))
        if league.week and team.wins + team.losses and not cz.is_interim(coach):
            xw, n = cz.expectation(league, team, coach)
            print(paint(f"   This season: {team.wins}-{team.losses} with a roster and schedule that projected "
                        f"{xw:.1f} wins so far.", C.GRAY))
        import finance as fi
        k = fi.contract(coach)
        if k:
            owed = fi.owed(coach, league)
            print(paint(f"   Deal through {k['end']}; firing him now would cost {fi.money(owed, exact=True)}"
                        f" ({owed / max(1, fi.budget(team)) * 100:.0f}% of the football program's yearly budget).", C.GRAY))
        events = getattr(coach, "seat_events", [])
        if events and league.week:
            start = getattr(coach, "seat_start", heat)
            move = heat - start
            print(paint(f"   This season: started at {start}, "
                        f"{'up' if move > 0 else 'down' if move < 0 else 'no change'}"
                        f"{' ' + str(abs(move)) if move else ''}. Lately: "
                        + "; ".join(why for _, _, why in events[-4:]), C.GRAY))
        _yearly = [e for e in coach.seat_log if len(e) == 3]
        if _yearly:
            yr, _, reasons = _yearly[-1]
            ledger = [(p, w) for p, w in getattr(coach, "seat_ledger", []) if w]
            if ledger:
                print(paint(f"   The AD's ledger after {yr}:", C.GRAY))
                for p, w in sorted(ledger, key=lambda x: -abs(x[0]))[:6]:
                    col = C.BRED if p > 0 else C.BGREEN
                    print(f"     {paint(f'{p:+5.0f}', col)}  {paint(w, C.GRAY)}")
            elif reasons:
                print(paint("   Seat based on: " + "; ".join(reasons), C.GRAY))
        print()
        print(section(f"{team.school.upper()} GOALS", C.BYELLOW))
        _print_goals(league, team, coach)

    if role in ("OC", "DC") and not coach.history:
        pause()
        return
    print()
    print(section("RECORD", C.BGREEN))
    ten = cz.splits(cz.tenure_seasons(coach))
    car = cz.splits(coach.history)
    label = f"AT {team.school.upper()}" if team else "—"
    print(paint(f"   {'':<14}{label:>20}{'CAREER':>20}", C.GRAY, C.BOLD))
    for name, (w, l) in (("Overall", ("w", "l")), ("Conference", ("cw", "cl")), ("vs Top 25", ("t25w", "t25l")),
                         ("Road", ("rw", "rl")), ("Postseason", ("pw", "pl"))):
        t_rec = f"{_wl(ten[w], ten[l])} ({_pct(ten[w], ten[l])})"
        c_rec = f"{_wl(car[w], car[l])} ({_pct(car[w], car[l])})"
        print(f"   {name:<14}{t_rec:>20}{c_rec:>20}")
    honors = []
    for k, lbl in (("titles", "national title"), ("cfp", "NP appearance"), ("confs", "conference title"),
                   ("bowls", "bowl game")):
        if car[k]:
            honors.append(f"{car[k]} {lbl}{'s' if car[k] > 1 else ''}")
    if honors:
        print(paint("   Career: " + " · ".join(honors), C.BYELLOW))

    print()
    print(section("SEASON BY SEASON", C.BCYAN))
    if not coach.history:
        print(paint("   No seasons on record yet (records start in 2026).", C.GRAY))
    else:
        print(paint(f"   {'YEAR':<6}{'SCHOOL':<18}{'W-L':>6}{'CONF':>7}{'T25':>6}{'ROAD':>6}{'RANK':>6}"
                    f"{'ROSTER':>8}{'CLASS':>7}  {'POSTSEASON':<30}{'SEAT':>5}", C.GRAY, C.BOLD))
        for s in reversed(coach.history):
            heat = s.get("seat", 0)
            rank = f"#{s['final_rank']}" if s["final_rank"] else "—"
            cls = f"#{s['class_rank']}" if s.get("class_rank") else "—"
            print(f"   {s['year']:<6}{pad(truncate(s['school'], 17), 18)}{_wl(s['w'], s['l']):>6}"
                  f"{_wl(s['cw'], s['cl']):>7}{_wl(s['t25w'], s['t25l']):>6}{_wl(s['rw'], s['rl']):>6}{rank:>6}"
                  f"{s['roster']:>8}{cls:>7}  {pad(truncate(s['post'] or '—', 29), 30)}"
                  f"{paint(f'{heat:>5}', seat_color(heat))}")
    moves = career_moves(league, coach)
    if moves:
        print()
        print(section("CAREER MOVES", C.BMAGENTA))
        for yr, text in moves[-10:]:
            print(f"   {paint(str(yr), C.GRAY)}  {text}")
    if ask("\n   [F] full career, a page at a time (every season, every job, every move) · Enter = back:").strip().lower() == "f":
        import history_book
        history_book.coach_career(league, coach)


OUT_WORDS = {"fired": "fired", "left": "left for another job", "retired": "retired", "nfl": "left for the Pro League",
             "not retained": "contract not renewed"}


def career_moves(league, coach):
    """Every job change, and why: fired, not renewed, poached, pushed out, promoted, retired."""
    out = []
    for yr in sorted(getattr(league, "carousel_moves", {})):
        for m in sorted(league.carousel_moves[yr], key=lambda m: m.get("side") == "in"):   # left, then hired
            if m.get("coach") != coach.name:
                continue
            if m["side"] == "out":
                why = m.get("note") or OUT_WORDS.get(m.get("kind"), m.get("kind", ""))
                if m.get("kind") == "fired" and not m.get("note"):
                    why = "fired"
                at = m.get("at")
                rec = f" ({at['w']}-{at['l']} there)" if isinstance(at, dict) and at.get("w", 0) + at.get("l", 0) else ""
                dest = f" → {m['dest']}" if m.get("dest") else ""
                out.append((yr, f"Left {m['school']}{rec} — {why}{dest}"))
            else:
                how = {"poach": "hired away", "pool": "hired", "coordinator": "promoted from coordinator",
                       "first": "first head job"}.get(m.get("how"), "hired")
                src = m.get("source") or ""
                out.append((yr, f"{how.capitalize()} by {m['school']}" + (f" — was {src}" if src else "")))
    return out


def _buzz(score, coach):
    if coach.age > 60:
        return paint("a lifer — not looking to run a program", C.GRAY)
    if score >= 12:
        return paint("hot name: calls coming", C.BGREEN, C.BOLD)
    if score >= 7:
        return paint("on the lists", C.BGREEN)
    if score >= 2:
        return paint("building a resume", C.GRAY)
    return paint("needs a better unit first", C.GRAY)


def _print_resume(coach):
    """Year by year, the unit he ran: points, yards, passing, rushing — or what
    his defense allowed — with national ranks, and how it did against its talent."""
    print(section("COORDINATOR RESUME", C.BCYAN))
    print(paint(f"   {'YEAR':<6}{'SCHOOL':<17}{'ROLE':<5}{'PPG':>11}{'YPG':>13}{'PASS':>13}{'RUSH':>13}"
                f"{'UNIT':>7}{'TALENT':>8}", C.GRAY, C.BOLD))
    for s in reversed(coach.coord_history):
        allowed = s["role"] == "DC"
        def cell(v, r, w):
            return pad(f"{v:.1f} " + paint(f"#{r:<3}", C.GRAY), w, "right")
        beat = s["exp"] - s["rank"]
        col = C.BGREEN if beat >= 15 else C.BRED if beat <= -15 else C.WHITE
        unit = pad(paint("#" + str(s["rank"]), col, C.BOLD), 7, "right")
        talent = pad("#" + str(s["exp"]), 8, "right")
        print(f"   {s['year']:<6}{pad(truncate(s['school'], 16), 17)}{s['role']:<5}"
              f"{cell(s['ppg'], s['ppg_rank'], 11)}{cell(s['ypg'], s['ypg_rank'], 13)}"
              f"{cell(s['pass'], s['pass_rank'], 13)}{cell(s['rush'], s['rush_rank'], 13)}{unit}{talent}")
    print(paint("   Defenses show what they allowed. UNIT = how the whole unit ranked nationally; TALENT = how its\n"
                "   roster ranked. Beat your talent rank and you get noticed.", C.GRAY))


def cz_trait(key):
    from traits import COACH_TRAITS
    return COACH_TRAITS[key][0] if key in COACH_TRAITS else key


def _print_goals(league, team, coach):
    for g in getattr(team, "goals", []):
        status, info = cz.goal_status(team, coach, g, league.year)
        if status == "met":
            tag = paint(f"MET {info}", C.BGREEN, C.BOLD)
        elif status == "failed":
            tag = paint("MISSED", C.BRED, C.BOLD)
        else:
            left = info
            tag = paint(f"{left} of {g.window} left", C.BYELLOW) if left and g.window > 1 else \
                paint("this season", C.BYELLOW) if left else paint("—", C.GRAY)
        why = f"({g.why})" if getattr(g, "why", "") else ""
        from ui import visible_len
        line = f"   {pad(g.label, 64)} {tag}"
        if why and visible_len(line) + len(why) + 2 <= 100:
            print(line + paint("  " + why, C.GRAY))
        else:
            print(line)
            if why:
                print(paint(f"      {why}", C.GRAY))


# ═══ Carousel news ══════════════════════════════════════════════════════════

KIND_COLORS = {"fired": C.BRED, "retired": C.GRAY, "poached": C.BYELLOW, "hired": C.BGREEN,
               "extended": C.BCYAN, "vote": C.BCYAN, "ad": C.BMAGENTA, "goals": C.GRAY, "budget": C.BGREEN}


def carousel_news(league):
    years = sorted(league.carousel, reverse=True)
    clear()
    print(title_bar("THE COACHING CAROUSEL"))
    if not any(league.carousel.values()):
        print(paint("   No coaching changes yet. The carousel spins after the season.", C.GRAY))
        pause()
        return
    for yr in years:
        items = league.carousel[yr]
        if not items:
            continue
        counts = {k: sum(1 for kind, _ in items if kind == k) for k in KIND_COLORS}
        when = (f"THE {yr} SEASON SO FAR" if yr == league.year and not league.season_complete else f"THE {yr} SEASON")
        print(section(f"{when}  ·  " + "  ".join(f"{v} {k}" for k, v in counts.items() if v),
                      C.BYELLOW))
        for kind, text in items:
            print(f"   {paint(f'{kind.upper():<8}', KIND_COLORS.get(kind, C.GRAY), C.BOLD)} {text}")
        print()
    with_report = [yr for yr in years if cz.carousel_moves(league, yr)]
    if not with_report:
        pause()
        return
    choice = ask(f"Type a year for its full report with records ({', '.join(map(str, with_report))}), "
                 f"or Enter to go back:")
    if choice.isdigit() and int(choice) in with_report:
        carousel_report(league, int(choice))


# ═══ Carousel report (end of season, and by year from the Coaches menu) ════

OUT_TAGS = {"fired": ("FIRED", C.BRED), "retired": ("RETIRED", C.GRAY), "left": ("LEFT", C.BYELLOW),
            "nfl": ("TO THE Pro League", C.BMAGENTA)}
CAROUSEL_PER_PAGE = 7
CONF_SHORT = {"High Country": "HCC", "Crossroads": "XRC", "Federal": "FED", "Coastal Plains": "CPC",
              "Lake Country": "LCC", "Golden West": "GWC", "Continental": "CONT", "Seaboard": "SEA",
              "Meridian": "MER", "Independent": "Ind"}


def _book_line(label, b, conf_label):
    """'At Nashville 24-26 .480   SCC 12-20   vs Top 25 3-14   4 seasons'"""
    if not b or b["seasons"] == 0:
        return f"        {pad(paint(label, C.GRAY), 22)}{paint('no FBS head coaching record', C.GRAY)}"
    w, l = b["w"], b["l"]
    extras = []
    if b["confs"]:
        extras.append(f"{b['confs']} conf title{'s' if b['confs'] > 1 else ''}")
    if b["cfp"]:
        extras.append(f"{b['cfp']} NP")
    if b["titles"]:
        extras.append(paint(f"{b['titles']} natl title{'s' if b['titles'] > 1 else ''}", C.BYELLOW, C.BOLD))
    seasons = f"{b['seasons']} season{'s' if b['seasons'] != 1 else ''}"
    conf_rec = f"{CONF_SHORT.get(conf_label, conf_label)} {_wl(b['cw'], b['cl'])}"
    top25 = "vs Top 25 " + _wl(b["t25w"], b["t25l"])
    return (f"        {pad(paint(label, C.GRAY), 22)}{pad(paint(_wl(w, l), C.BWHITE, C.BOLD), 7)}"
            f"{paint(_pct(w, l), C.GRAY)}   {pad(conf_rec, 16)}"
            f"{pad(top25, 17)}{paint(seasons, C.GRAY)}"
            + (paint('  ·  ', C.GRAY) + ', '.join(extras) if extras else ""))


def _same(a, b):
    return a and b and all(a[k] == b[k] for k in ("w", "l", "cw", "cl", "t25w", "t25l", "seasons"))


def _out_block(league, m):
    tag, color = OUT_TAGS.get(m["kind"], (m["kind"].upper(), C.GRAY))
    why = {"fired": f"fired after {m['tenure']} season{'s' if m['tenure'] != 1 else ''}",
           "retired": f"retired after {m['tenure']} season{'s' if m['tenure'] != 1 else ''}",
           "left": f"left for {m['dest']}" if m.get("dest") else "left",
           "nfl": "left to become a Pro League head coach"}.get(m["kind"], m["kind"])
    if m.get("note"):
        why += f" — {m['note']}"
    you = paint("  (you)", C.BMAGENTA, C.BOLD) if m.get("user") else ""
    lines = [f"   {pad(paint('OUT', color, C.BOLD), 5)}{paint(m['coach'], C.BWHITE, C.BOLD)}, {m['age']}{you}  "
             f"{paint('·', C.GRAY)} {paint(why, color)}",
             _book_line(f"At {truncate(m['school'], 18)}", m["at"], m["conf"])]
    if _same(m["at"], m["career"]):
        lines.append(f"        {pad(paint('Career', C.GRAY), 22)}{paint('all of it at ' + m['school'], C.GRAY)}")
    else:
        lines.append(_book_line("Career", m["career"], "Conf"))
    return lines


def _unit_line(e):
    """'2027 OC at Georgia: 38.2 ppg (#4) · 468 ypg (#6) · unit #5 (talent #12)'"""
    what = "ppg" if e["role"] == "OC" else "ppg allowed"
    return (f"{e['year']} {e['role']} at {e['school']}: {e['ppg']:.1f} {what} (#{e['ppg_rank']}) · "
            f"{e['ypg']:.0f} ypg (#{e['ypg_rank']}) · unit #{e['rank']} (talent #{e['exp']})")


def _in_block(league, m):
    you = paint("  (you)", C.BMAGENTA, C.BOLD) if m.get("user") else ""
    if m.get("how") == "coordinator":
        lines = [f"   {pad(paint('IN', C.BGREEN, C.BOLD), 5)}{paint(m['coach'], C.BWHITE, C.BOLD)}, {m['age']}  "
                 f"{paint('·', C.GRAY)} {paint('promoted to head coach', C.BGREEN)}{paint('  ·  ', C.GRAY)}"
                 f"was {m['source']}"]
        for e in reversed(m.get("coord_book", [])[-2:]):
            lines.append(f"        {paint(_unit_line(e), C.GRAY)}")
        if not m.get("coord_book"):
            lines.append(f"        {paint('first year as a coordinator', C.GRAY)}")
        return lines
    if m.get("how") == "poach" and m.get("from_school"):
        how = paint("hired away from ", C.BGREEN) + paint(m["from_school"], C.BWHITE)
    else:
        how = paint("hired", C.BGREEN) + paint("  ·  ", C.GRAY) + _origin_text(m["source"])
        if m.get("second_chance"):
            how += paint("  ·  second chance", C.BCYAN, C.BOLD)
    lines = [f"   {pad(paint('IN', C.BGREEN, C.BOLD), 5)}{paint(m['coach'], C.BWHITE, C.BOLD)}, {m['age']}{you}  "
             f"{paint('·', C.GRAY)} {how}"]
    if m.get("from_school"):
        conf = m.get("from_conf") or "Conf"
        lines.append(_book_line(f"At {truncate(m['from_school'], 18)}", m["prev"], conf))
        if _same(m["prev"], m["career"]):
            lines.append(f"        {pad(paint('Career', C.GRAY), 22)}{paint('all of it at ' + m['from_school'], C.GRAY)}")
        else:
            lines.append(_book_line("Career", m["career"], "Conf"))
    else:
        lines.append(f"        {pad(paint('Career', C.GRAY), 22)}{paint('first FBS head coaching job', C.BCYAN)}")
    return lines


def _origin_text(src):
    """'Kansas offensive coordinator' → 'was Kansas offensive coordinator'."""
    if src.startswith(("fired by", "out of coaching", "first FBS")):
        return src
    if "High School" in src:
        return f"was head coach at {src}"
    return f"was {src}"


def carousel_report(league, year, title=None):
    """Every program that changed coaches, what it lost and what it hired —
    records overall, in conference, and against the Top 25."""
    moves = cz.carousel_moves(league, year)
    news = league.carousel.get(year, [])
    head = title or f"COACHING CAROUSEL  ·  AFTER THE {year} SEASON"
    if not moves:
        clear()
        print(title_bar(head))
        print(paint("\n   No head coaching changes this year. Every AD stood pat.", C.GRAY))
        _carousel_extras(news)
        pause()
        staff_report(league, year)
        return
    by_school = {}
    for m in moves:
        by_school.setdefault(m["school"], {"out": [], "in": [], "conf": m["conf"], "prestige": m["prestige"]})
        by_school[m["school"]][m["side"]].append(m)
    order = sorted(by_school.items(), key=lambda kv: -kv[1]["prestige"])
    counts = {k: sum(1 for m in moves if m["side"] == "out" and m["kind"] == k) for k in OUT_TAGS}
    hires = [m for m in moves if m["side"] == "in"]
    first_timers = sum(1 for m in hires if not m.get("from_school"))
    summary = "  ·  ".join(p for p in (
        f"{counts['fired']} fired" if counts["fired"] else "", f"{counts['retired']} retired" if counts["retired"] else "",
        f"{counts['left']} left for another job" if counts["left"] else "",
        f"{counts['nfl']} to the Pro League" if counts["nfl"] else "",
        f"{len(hires)} hires ({first_timers} first-time head coaches)" if hires else "",
        f"{sum(1 for m in hires if m.get('second_chance'))} second chances"
        if any(m.get("second_chance") for m in hires) else "") if p)
    pages = [order[i:i + CAROUSEL_PER_PAGE] for i in range(0, len(order), CAROUSEL_PER_PAGE)]
    for n, page in enumerate(pages, 1):
        clear()
        print(title_bar(head + (f"  ·  {n}/{len(pages)}" if len(pages) > 1 else "")))
        print(paint(f"   {len(order)} programs changed coaches  ·  {summary}", C.GRAY))
        print(paint("   Records are head coaching records in FBS since 2026.", C.GRAY))
        for school, d in page:
            team = next((t for t in league.teams if t.school == school), None)
            color = league.conference_color(d["conf"])
            tags = [OUT_TAGS.get(m["kind"], ("", C.GRAY)) for m in d["out"]]
            tag_txt = "  ".join(paint(t, c, C.BOLD) for t, c in tags) or paint("OPENING FILLED", C.GRAY)
            print()
            print(f" {pad(paint(school.upper(), C.BWHITE, C.BOLD), 26)}{pad(paint(d['conf'], color), 16)}"
                  f"{paint('prestige', C.GRAY)} {rating(round(team.prestige)) if team else '—'}   {tag_txt}")
            for m in d["out"]:
                _print_block(m, _out_block(league, m), "out")
            for m in d["in"]:
                _print_block(m, _in_block(league, m), "in")
            if not d["in"]:
                print(paint("   IN   (still open)", C.GRAY))
        if n < len(pages):
            print(rule())
            if ask("Enter for more, S to skip the rest:").lower() == "s":
                break
    _carousel_extras(news)
    pause()
    staff_report(league, year)


def _print_block(m, lines, side):
    """One coach who left or arrived: his face beside his record when portraits are enabled."""
    import faces
    if not faces.enabled():
        for ln in lines:
            print(ln)
        return
    import faces_ui
    expr = "neutral"
    if side == "out" and m.get("kind") == "fired":
        expr = "sad"
    elif side == "in":
        expr = "smile"
    face = faces.name_portrait(m["coach"], school=m["school"], role="coach", age=m.get("age"), expr=expr, mini=True)
    lines = [ln[3:] if ln.startswith("   ") else ln for ln in lines]
    for ln in faces_ui.beside(face, lines, indent=2, gap=1):
        print(ln)


def staff_report(league, year):
    """The coordinator carousel: who left, who was fired, who got hired, and from where."""
    import staff
    moves = [m for m in staff.staff_moves(league, year)]
    if not moves:
        return
    by = {}
    for m in moves:
        by.setdefault(m["school"], {"prestige": m["prestige"], "conf": m["conf"], "moves": []})["moves"].append(m)
    order = sorted(by.items(), key=lambda kv: -kv[1]["prestige"])
    ins = [m for m in moves if m["side"] == "in"]
    fired = sum(1 for m in moves if m["side"] == "out" and m.get("why") == "fired")
    cleaned = sum(1 for m in moves if m["side"] == "out" and m.get("why") == "cleaned out")
    promoted = sum(1 for m in moves if m["side"] == "out" and m.get("why") == "promoted")
    hs = sum(1 for m in ins if "High School" in (m.get("source") or ""))
    per = 9
    pages = [order[i:i + per] for i in range(0, len(order), per)]
    why_txt = {"fired": ("FIRED", C.BRED), "cleaned out": ("NEW HC", C.BYELLOW), "retired": ("RETIRED", C.GRAY),
               "promoted": ("PROMOTED", C.BGREEN), "left": ("LEFT", C.BYELLOW)}
    for n, page in enumerate(pages, 1):
        clear()
        print(title_bar(f"COORDINATOR CAROUSEL  ·  AFTER THE {year} SEASON"
                        + (f"  ·  {n}/{len(pages)}" if len(pages) > 1 else "")))
        print(paint(f"   {len(ins)} coordinator hires  ·  {promoted} promoted to head coach  ·  {fired} fired  ·  "
                    f"{cleaned} let go by a new head coach  ·  {hs} straight from high school", C.GRAY))
        for school, d in page:
            print()
            print(f" {paint(school.upper(), C.BWHITE, C.BOLD)}  {paint(d['conf'], league.conference_color(d['conf']))}")
            for m in sorted(d["moves"], key=lambda m: (m["role"], m["side"] != "out")):
                last = m.get("last")
                unit = (f"#{last['rank']} {'offense' if last['role'] == 'OC' else 'defense'} in {last['year']}"
                        if last else "")
                if m["side"] == "out":
                    tag, col = why_txt.get(m.get("why"), (m.get("why", "").upper(), C.GRAY))
                    dest = f" → {m['dest']}" if m.get("dest") else ""
                    print(f"   {m['role']}  {pad(paint('OUT', col, C.BOLD), 4)} {pad(paint(tag, col), 9)} "
                          f"{pad(truncate(m['coach'], 21), 22)}{paint(unit + dest, C.GRAY)}")
                else:
                    src = m.get("source") or ""
                    how = paint("hired away from ", C.BGREEN) if m.get("how") == "hired away" else paint("hired · ", C.BGREEN)
                    src_txt = src if m.get("how") == "hired away" else src
                    print(f"   {m['role']}  {pad(paint('IN', C.BGREEN, C.BOLD), 4)} {pad(rating(m['overall']), 9)} "
                          f"{pad(truncate(m['coach'], 21), 22)}{how}{paint(truncate(src_txt, 48), C.GRAY)}"
                          + (paint(f"  ({unit})", C.GRAY) if unit else ""))
        if n < len(pages):
            print(rule())
            if ask("Enter for more, S to skip the rest:").lower() == "s":
                return
    pause()


def _carousel_extras(news):
    extras = [(k, t) for k, t in news if k in ("vote", "ad", "extended", "budget")]
    if extras:
        print()
        print(section("ALSO AROUND THE SPORT", C.BCYAN))
        for kind, text in extras:
            label = {"vote": "BACKED", "ad": "NEW AD", "extended": "EXTENDED", "budget": "BUDGET"}[kind]
            print(f"   {paint(f'{label:<8}', KIND_COLORS.get(kind, C.GRAY), C.BOLD)} {text}")


# ═══ Program page (from the team view) ══════════════════════════════════════

def program_view(league, team):
    clear()
    print(title_bar(f"{team.full_name.upper()}  ·  PROGRAM"))
    style, blurb, rules = cz.AD_STYLES[team.ad["style"]]
    print(f"   {paint('Athletic Director', C.GRAY)}  {team.ad['name']}  "
          f"({style} — {paint(blurb, C.GRAY)})   {paint(__import__('ad_market').traits_label(team.ad), C.GRAY)}")
    c = team.coach
    print(f"   {paint('Head Coach       ', C.GRAY)}  {c.name}, {c.age}  ·  OVR {rating(c.overall)}  ·  "
          f"since {c.hired_year}  ·  seat {seat_tag(c)}")
    import finance as fi
    print(f"   {paint('Football budget  ', C.GRAY)}  {fi.money(fi.budget(team))}/yr  ·  head coach "
          f"{fi.money(fi.salary(c))}  ·  NIL on the roster {fi.money(fi.roster_nil(team))}  ·  "
          f"{paint('AD deals: ' + fi.AD_CONTRACT[team.ad['style']]['blurb'], C.GRAY)}")
    print()
    print(section("PROGRAM GOALS", C.BYELLOW))
    import textwrap
    for ln in textwrap.wrap(cz.ad_judging(team), 94):
        print(paint("   " + ln, C.GRAY))
    _print_goals(league, team, c)
    print()
    print(section("COACHING HISTORY", C.BCYAN))
    for since, name in reversed(getattr(team, "coach_log", [])):
        print(f"   {since}   {name}")
    print()
    print(f"   {paint('[C]', C.BYELLOW)} Head coach profile   {paint('[B]', C.GRAY, C.BOLD)} Back")
    if ask("Select:").lower() == "c":
        coach_view(league, c)
