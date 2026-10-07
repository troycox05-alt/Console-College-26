"""
staff_room.py — Your whole staff on one screen (Coach Career): coordinators and the
eight position coaches. Fire anyone, hire into any open chair, promote a position
coach to coordinator on his side of the ball.
"""
import random

import poscoach
import staff
from ui import C, ask, clear, pad, paint, pause, rating, rule, title_bar, truncate


def _log(league, text):
    league.__dict__.setdefault("career_log", []).append((league.year, text))


def _side_avg(c, role):
    keys = staff.SIDE_KEYS[role]
    return round(sum(c.ratings[k] for k in keys) / len(keys))


def _show(league, team):
    clear()
    print(title_bar(f"STAFF ROOM  ·  {team.school.upper()}", sub=f"Head coach {team.coach.name}"))
    import finance as fi
    print(paint(f"   {'#':>2}  {'ROLE':<17}{'COACH':<24}{'AGE':>4}{'OVR':>5}{'DEV':>5}{'REC':>5}{'EVAL':>6}  {'POTENTIAL':<10}"
                f"{'PAY':>7}", C.GRAY, C.BOLD))
    for i, role in enumerate(("OC", "DC"), 1):
        c = getattr(team, "oc" if role == "OC" else "dc", None)
        label = "Off. coordinator" if role == "OC" else "Def. coordinator"
        if c is None:
            print(f"   {i:>2}  {pad(label, 17)}{paint('— open —', C.BRED, C.BOLD)}")
            continue
        caller = paint(" calls plays", C.BCYAN) if staff.calls(team)["off" if role == "OC" else "def"] == role else ""
        if c.__dict__.get("ahc_title"):
            caller += paint(" · AHC", C.BYELLOW)
        print(f"   {i:>2}  {pad(label, 17)}{pad(truncate(c.name, 23), 24)}{c.age:>4}{pad(rating(c.overall), 5, 'right')}"
              f"{pad(rating(_side_avg(c, role)), 5, 'right')}{pad(rating(c.ratings['recruiting']), 5, 'right')}"
              f"{'':>6}  {pad(staff.potential_word(c), 10)}{pad(fi.money(fi.salary(c)) if fi.contract(c) else '—', 7, 'right')}"
              f"{caller}")
    print(rule())
    room = poscoach.staff_of(team)
    for i, g in enumerate(poscoach.GROUPS, 3):
        c = room.get(g)
        label = poscoach.TITLE[g].capitalize()
        if c is None:
            print(f"   {i:>2}  {pad(label, 17)}{paint('— open —', C.BRED, C.BOLD)}")
            continue
        yrs = max(0, league.year + 1 - (c.since or league.year + 1))
        poscoach.fields(c)
        flag = paint(" !", C.BRED, C.BOLD) if c.unhappy else ""
        print(f"   {i:>2}  {pad(label, 17)}{pad(truncate(c.name, 21) + flag, 24)}{c.age:>4}{pad(rating(c.overall), 5, 'right')}"
              f"{pad(rating(c.dev), 5, 'right')}{pad(rating(c.rec), 5, 'right')}{pad(rating(c.eye), 6, 'right')}  "
              f"{pad(poscoach.potential(c), 10)}{pad(fi.money(poscoach.salary(c, team)), 7, 'right')}  "
              f"{paint(c.kind, C.BCYAN)} {paint('· ' + truncate(poscoach.spec_line(c), 16), C.BYELLOW)} "
              f"{paint(f'· {yrs} yr' + ('s' if yrs != 1 else ''), C.GRAY)}")
    d = poscoach.payroll_delta(team)
    print(paint(f"\n   Position coach payroll: {fi.money(abs(d))} {'over' if d >= 0 else 'under'} a standard room "
                f"({'less' if d >= 0 else 'more'} money for players).", C.BYELLOW if d > 0 else C.BGREEN))
    print(paint("   ! = unsettled (his coordinator was let go): he may walk, and works a little less hard until he's settled.",
                C.GRAY))
    print(paint("   DEV: how much his players improve.  REC: pull with recruits at his positions.  EVAL: how well he\n"
                "   reads his room (sharper practice reports and depth charts).  Coordinators' DEV is their side of the ball.",
                C.GRAY))
    print(rule())
    print(f"   {paint('[F#]', C.BRED)} fire   {paint('[H#]', C.BGREEN)} hire into an open chair   "
          f"{paint('[P#]', C.BYELLOW)} promote a position coach to coordinator   {paint('[V#]', C.BYELLOW)} profile")
    print(f"   {paint('[N1/N2]', C.BYELLOW)} negotiate a coordinator's deal (extension, pay it back, a title)")
    print(f"   {paint('[C]', C.BYELLOW)} play-calling & autopilot   {paint('[Enter]', C.GRAY)} done")


def _slot(n):
    if n in (1, 2):
        return ("coord", "OC" if n == 1 else "DC")
    if 3 <= n <= 2 + len(poscoach.GROUPS):
        return ("pos", poscoach.GROUPS[n - 3])
    return (None, None)


def _hire_coord(league, team, role):
    import staff_screens
    rng = random.Random(f"room:{team.school}:{role}:{league.year}:{league.week}")
    import staff_carousel
    ranked = staff_carousel.Carousel(league, rng, show=False).coord_cands(team, role)
    # The search (coord_search.py) judges interest and builds the board itself.
    picked = staff_screens.pick(league, team, role, ranked)
    import staff_carousel
    if picked is None:                                    # "let your AD hire": he actually does
        before = getattr(team, "oc" if role == "OC" else "dc", None)
        staff_carousel.Carousel(league, rng, show=False).fill_coord(team, role)
        after = getattr(team, "oc" if role == "OC" else "dc", None)
        if after is not None and after is not before:
            _log(league, f"Your AD hired {after.name} as {staff.ROLE_NAMES[role]}.")
            print(paint(f"   Your AD hires {after.name} as {staff.ROLE_NAMES[role]}.", C.BGREEN))
            pause()
        return
    c, offer = picked
    car = staff_carousel.Carousel(league, rng, show=True)
    car.me = team
    car.hire_coord(team, role, c, offer)                  # he may want to bring his guys
    n = 0
    while car.queue and n < 15:                           # anyone he pulled away gets replaced
        t, k, x = car.next()
        n += 1
        if t is team or car.filled(t, k, x):
            continue
        car.fill_coord(t, x) if k == "coord" else car.fill_pos(t, x)


def _hire_pos(league, team, group, accept=None, refill=True):
    rng = random.Random(f"room:{team.school}:{group}:{league.year}:{league.week}:{len(league.__dict__.get('pos_pool', []))}")
    # The board includes long shots so the market feels real; choosing one begins a pursuit,
    # it no longer means he automatically signs.
    import hiring_market
    cands = [c for c in poscoach.candidates(league, team, group, rng)
             if hiring_market.pos_interest(league, team, c) >= 7]
    while True:
        clear()
        print(title_bar(f"HIRE A {poscoach.TITLE[group].upper()} COACH  ·  {team.school.upper()}"))
        import finance as fi
        print(paint(f"   Money free for staff & NIL: {fi.money(fi.available(league, team))}", C.GRAY))
        print(paint(f"   {'#':>2}  {'COACH':<22}{'AGE':>4}{'OVR':>5}  {'INTEREST':<15}{'ASKS':>7}  {'NOW'}", C.GRAY, C.BOLD))
        for i, c in enumerate(cands, 1):
            now = (f"{c.school} {poscoach.TITLE[c.group]}" if c.school else
                   c.origin if getattr(c, "_fresh", False) else "out of work")
            interest = hiring_market.word(hiring_market.pos_interest(league, team, c))
            print(f"   {i:>2}  {pad(truncate(c.name, 21), 22)}{c.age:>4}{pad(rating(c.overall), 5, 'right')}  "
                  f"{pad(interest, 15)}{pad(paint(fi.money(poscoach.salary(c, team)), C.BGREEN), 7, 'right')}  "
                  f"{paint(truncate(now, 27), C.GRAY)}")
            detail = (f"{c.kind} · {poscoach.spec_line(c)} · DEV {rating(c.dev)} · REC {rating(c.rec)} · "
                      f"EVAL {rating(c.eye)} · {poscoach.rep_word(c)}")
            print(paint("        " + truncate(detail, 88), C.GRAY))
        print(paint("\n   The board is a list of leads, not automatic hires. Pursuing one starts an interview and offer.",
                    C.GRAY))
        ch = ask("Pursue # · [I#] interview only (Enter = cancel):").strip().lower()
        if not ch:
            return None
        if ch.startswith("i") and ch[1:].isdigit() and 1 <= int(ch[1:]) <= len(cands):
            interview(league, team, cands[int(ch[1:]) - 1])
            continue
        if ch.isdigit() and 1 <= int(ch) <= len(cands):
            c = cands[int(ch) - 1]
            if accept is not None:
                ok, why = accept(c)
                if not ok:
                    print(paint(f"   {why}", C.BRED))
                    cands.remove(c)
                    pause()
                    continue
            # Contact -> interview -> offer. A listing is not a signing anymore.
            if not hiring_market.negotiate_pos(league, team, c):
                continue
            import finance as fi
            mult = float(c.__dict__.pop("hire_pay_mult", 1.0))
            base_pay = poscoach.salary(c, team)
            offered_pay = int(base_pay * mult)
            extra = offered_pay - poscoach.POS_SHARE * fi.budget(team)
            if extra > fi.available(league, team):
                import budget_fix
                if not budget_fix.cover(league, team, extra, f"{c.name}'s salary: {fi.money(offered_pay)}"):
                    print(paint("   Not enough money to pay him.", C.BRED))
                    pause()
                    continue
            src = c.school
            poscoach.hire(league, team, group, c, refill=refill)
            if mult > 1.0:
                c.bonus = int(max(0, offered_pay - base_pay))
            _log(league, f"Hired {c.name} as {poscoach.TITLE[group]} coach.")
            print(paint(f"   {c.name} is your {poscoach.TITLE[group]} coach.", C.BGREEN))
            pause()
            return c, src


def _fire_coord(league, team, role, quiet=False):
    import finance as fi
    c = getattr(team, "oc" if role == "OC" else "dc", None)
    if c is None:
        return True
    cost = fi.owed(c, league)
    note = f" You'll owe him {fi.money(cost)} over the rest of his deal." if cost else ""
    if ask(f"Let {staff.ROLE_NAMES[role]} {c.name} go?{note} (y/n)").lower() not in ("y", "yes"):
        return False
    staff.fire(league, team, role, "fired")
    _log(league, f"Let {staff.ROLE_NAMES[role]} {c.name} go.")
    _show_fallout(c)
    return True


def manage(league, team=None):
    team = team or getattr(league, "user_team", None)
    if team is None or team.coach is None:
        print(paint("\n   You're not coaching anywhere right now.", C.GRAY))
        pause()
        return
    poscoach.ensure(league)
    while True:
        _show(league, team)
        ch = ask("Your call:").strip().lower()
        if not ch:
            return
        if ch == "c":
            import staff_screens
            staff_screens.my_staff(league)
            continue
        act, num = ch[0], ch[1:]
        if not num.isdigit():
            continue
        kind, key = _slot(int(num))
        if kind is None:
            continue
        if act == "n" and kind == "coord":
            c = getattr(team, "oc" if key == "OC" else "dc", None)
            if c is not None:
                import negotiate
                negotiate.coordinator(league, team, key, c)
            continue
        if act == "v" and kind == "coord":
            c = getattr(team, "oc" if key == "OC" else "dc", None)
            if c is not None:
                import coach_screens
                coach_screens.coach_view(league, c)
        elif act == "v":
            c = poscoach.staff_of(team).get(key)
            if c is not None:
                profile(league, team, c)
        elif act == "f":
            if kind == "coord":
                _fire_coord(league, team, key)
            else:
                c = poscoach.staff_of(team).get(key)
                if c is not None and ask(f"Let {c.name} go? (y/n)").lower() in ("y", "yes"):
                    poscoach.fire(league, team, key)
                    _log(league, f"Let {poscoach.TITLE[key]} coach {c.name} go.")
                    _show_fallout(c)
        elif act == "h":
            if kind == "coord":
                if getattr(team, "oc" if key == "OC" else "dc", None) is not None:
                    print(paint("   That chair is filled — fire him first, or promote someone into it.", C.BYELLOW))
                    pause()
                else:
                    _hire_coord(league, team, key)
            else:
                if poscoach.staff_of(team).get(key) is not None:
                    print(paint("   That chair is filled — fire him first.", C.BYELLOW))
                    pause()
                else:
                    _hire_pos(league, team, key)
        elif act == "p" and kind == "pos":
            pc = poscoach.staff_of(team).get(key)
            if pc is None:
                continue
            role = poscoach.SIDE[key]
            if not _fire_coord(league, team, role):
                continue
            c = poscoach.promote(league, team, key)
            _log(league, f"Promoted {pc.name} from {poscoach.TITLE[key]} coach to {staff.ROLE_NAMES[role]}.")
            print(paint(f"   {c.name} is your new {staff.ROLE_NAMES[role]}. His old room is open.", C.BGREEN))
            if ask("Hire his replacement now? (y/n)").lower() in ("y", "yes"):
                _hire_pos(league, team, key)


def _show_fallout(c):
    lines = c.__dict__.pop("_fallout", None) or []
    if lines:
        print(paint("\n   The fallout:", C.BRED, C.BOLD))
        for t in lines:
            print(paint(f"   · {t}", C.BYELLOW))
        pause()


def interview(league, team, c):
    """What a sit-down with a position coach candidate tells you."""
    poscoach.fields(c)
    clear()
    print(title_bar(f"INTERVIEW  ·  {c.name.upper()}  ·  {poscoach.TITLE[c.group].upper()}"))
    notes = {"Developer": "Talks for twenty minutes about footwork and individual drills. A teacher.",
             "Recruiter": "Knows every high school coach in his region by first name. Brought a list.",
             "Technician": "Breaks down your film better than your coordinator did. Detail guy.",
             "Players' coach": "His former players call him. Kids will run through a wall for him.",
             "Climber": "Asks how soon a coordinator job could open. Ambitious — he won't stay long.",
             "Loyalist": "Asks who your coordinator is. He goes where his guy goes."}
    print(paint(f"\n   {c.kind}: {notes.get(c.kind, '')}", C.BWHITE))
    print(paint(f"   Specialty: {poscoach.spec_line(c)} — {poscoach.SPEC_NOTE.get(c.spec, '')}.   "
                f"Track record: {poscoach.rep_word(c)}.", C.BYELLOW))
    print(f"\n   Development {paint(poscoach.word(c.dev), C.BCYAN)}   ·   Recruiting {paint(poscoach.word(c.rec), C.BCYAN)}"
          f"   ·   Evaluation {paint(poscoach.word(c.eye), C.BCYAN)}   ·   Upside {paint(poscoach.potential(c), C.BCYAN)}")
    if c.region:
        print(paint(f"   Recruits the {c.region} hardest.", C.GRAY))
    coord = staff.side_coach(team, "QB" if poscoach.SIDE[c.group] == "OC" else "LB")
    if c.ties:
        mine = coord is not None and coord.name in c.ties
        print(paint(f"   Has worked under: {', '.join(sorted(c.ties))}"
                    + ("  — including your coordinator." if mine else ""), C.BGREEN if mine else C.GRAY))
    pause()


def profile(league, team, c):
    poscoach.fields(c)
    clear()
    print(title_bar(f"{c.name.upper()}  ·  {team.school.upper()} {poscoach.TITLE[c.group].upper()} COACH"))
    print(f"\n   {paint(c.kind, C.BCYAN, C.BOLD)} — {poscoach.KIND_NOTE.get(c.kind, '')}.   Age {c.age}.   "
          f"Recruits the {c.region or 'whole country'} hardest.")
    print(f"   Specialty: {paint(poscoach.spec_line(c), C.BYELLOW, C.BOLD)} — {poscoach.SPEC_NOTE.get(c.spec, '')}.   "
          f"Reputation: {paint(poscoach.rep_word(c), C.BGREEN)}")
    if c.room_log:
        print(paint("   Room growth by season (his room vs. the national average for that room):", C.GRAY))
        for y, school, g, avg in c.room_log[-4:]:
            d = g - avg
            print(f"     {y}  {pad(school, 18)}{g:+.1f} OVR   (nation {avg:+.1f})   "
                  + paint(f"{d:+.1f}", C.BGREEN if d >= 0 else C.BRED))
    print(f"   Development {rating(c.dev)} ({poscoach.word(c.dev)})   Recruiting {rating(c.rec)} ({poscoach.word(c.rec)})   "
          f"Evaluation {rating(c.eye)} ({poscoach.word(c.eye)})   Upside: {poscoach.potential(c)}")
    m = poscoach.room_mult(team, "CB" if c.group == "DB" else c.group)
    print(paint(f"   His room grows {abs(round((m - 1) * 100))}% {'faster' if m >= 1 else 'slower'} than an average "
                f"coach's would make it.", C.BGREEN if m >= 1 else C.BRED))
    if c.unhappy:
        print(paint(f"   Unsettled since {c.unhappy[1]} was let go.", C.BRED))
    signed = [p for p in team.roster if p.__dict__.get("signed_pos") == c.name]
    if signed:
        print(paint(f"\n   Players he signed ({len(signed)}): " + ", ".join(p.name for p in signed[:8])
                    + ("..." if len(signed) > 8 else ""), C.GRAY))
    if c.ties:
        print(paint(f"   His coordinators (he'd follow them): {', '.join(sorted(c.ties))}", C.GRAY))
    if c.history:
        print(paint("   Career: " + " · ".join(f"{y} {s} {g}" for y, s, g in c.history[-5:]), C.GRAY))
    else:
        print(paint(f"   Came from: {c.origin}", C.GRAY))
    pause()
