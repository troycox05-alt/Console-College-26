"""
staff_screens.py — Running your own staff in Coach Career mode.

Every offseason, after the head coaching carousel:
  • STAFF REVIEW — how each coordinator's unit did against its talent. Keep
    him or let him go. Take a new job and you decide which of the inherited
    coordinators stay.
  • HIRING — for every opening on your staff, the candidates who would
    actually take your job: coordinators from smaller programs, coaches out
    of work, fired head coaches, and new faces (high school and FCS coaches
    at Group of Five programs; position coaches and Pro League assistants at Power
    programs). Open anyone's resume before you decide.

Your coordinators can still be hired away — by bigger programs, or as head
coaches — and you'll hear about it. [A] hands the whole staff to your AD.
"""
from ui import C, WIDTH, ask, clear, pad, paint, pause, rating, rule, section, title_bar, truncate

import staff


def _side_labels(role):
    """The development ratings that matter for this job."""
    if role == "OC":
        return [("passing_dev", "PASS"), ("offense_dev", "SKILL"), ("trench_dev", "LINE")]
    return [("db_dev", "BACK7"), ("trench_dev", "LINE")]


def _unit(e):
    if not e:
        return paint("no college unit yet", C.GRAY)
    beat = e["exp"] - e["rank"]
    col = C.BGREEN if beat >= 15 else C.BRED if beat <= -15 else C.WHITE
    what = "offense" if e["role"] == "OC" else "defense"
    return (paint(f"#{e['rank']} {what}", col, C.BOLD) + paint(f" (talent #{e['exp']}) · {e['year']} at "
                                                             f"{truncate(e['school'], 16)}", C.GRAY))


def _unit_detail(e):
    if not e:
        return ""
    what = "ppg" if e["role"] == "OC" else "ppg allowed"
    return (f"{e['ppg']:.1f} {what} (#{e['ppg_rank']}) · {e['ypg']:.0f} ypg (#{e['ypg_rank']}) · "
            f"pass {e['pass']:.0f} (#{e['pass_rank']}) · rush {e['rush']:.0f} (#{e['rush_rank']})")


def _staff_block(league, team, role, c, inherited=False):
    import carousel as cz
    from traits import COACH_TRAITS
    label = staff.ROLE_NAMES[role].upper()
    if c is None:
        print(f"   {paint(role, C.BYELLOW, C.BOLD)}  {paint('— open —', C.GRAY)}")
        return
    lines = []
    pname = cz.PERSONALITIES.get(c.personality, ("—",))[0]
    tag = paint("  inherited", C.BYELLOW) if inherited else ""
    traits = ", ".join(COACH_TRAITS[t][0] for t in c.traits if t in COACH_TRAITS) or "—"
    lines.append(f"   {paint(role, C.BYELLOW, C.BOLD)}  {paint(c.name, C.BWHITE, C.BOLD)}, {c.age}   OVR {rating(c.overall)}  "
          f"{paint('potential: ' + staff.potential_word(c), C.GRAY)}   {paint(pname + ' · ' + traits, C.GRAY)}{tag}")
    last = c.coord_history[-1] if getattr(c, "coord_history", None) else None
    lines.append(f"       {_unit(last)}")
    if last:
        lines.append(paint(f"       {_unit_detail(last)}", C.GRAY))
    sides = "  ".join(f"{lbl} {rating(c.ratings[k])}" for k, lbl in _side_labels(role))
    scheme = c.offense_scheme if role == "OC" else c.defense_scheme
    mine = team.coach.offense_scheme if role == "OC" else team.coach.defense_scheme
    fit = paint("fits your scheme", C.BGREEN) if scheme == mine else paint(f"runs {scheme} (you: {mine})", C.BYELLOW)
    lines.append(f"       {sides}  REC {rating(c.ratings['recruiting'])}  "
          f"{paint('recruits the ' + str(getattr(c, 'recruit_region', '—')), C.GRAY)}   {fit}")
    import finance as fi
    k = fi.contract(c)
    if k:
        up = paint("  CONTRACT UP", C.BYELLOW, C.BOLD) if k["end"] <= league.year and league.season_complete else ""
        left = fi.years_left(k, league)
        lines.append(paint(f"       Contract: {fi.terms(k, total=False)} through {k['end']} "
                    f"({left} yr{'s' if left != 1 else ''} left) · "
                    f"owed if let go: {fi.money(fi.owed(c, league))}", C.GRAY) + up)
    buzz = staff.buzz_score(c)
    if buzz >= 12 and c.age <= 60:
        lines.append(paint("       Hot name — head coaching jobs may come calling.", C.BMAGENTA))
    import faces
    if faces.enabled():
        import faces_ui
        lines = [ln[3:] if ln.startswith("   ") else ln for ln in lines]       # the face takes the indent's room
        for ln in faces_ui.beside(faces.coach_portrait(c, mini=True), lines, indent=0, gap=1):
            print(ln)
    else:
        for ln in lines:
            print(ln)


def _news_for_you(league, team):
    """Coordinators you've already lost this winter."""
    out = []
    for m in staff.staff_moves(league, league.year):
        if m["school"] == team.school and m["side"] == "out":
            if m.get("why") == "promoted":
                out.append(f"Your {staff.ROLE_NAMES[m['role']]} {m['coach']} was hired as head coach at {m['dest']}.")
            elif m.get("why") == "retired":
                out.append(f"Your {staff.ROLE_NAMES[m['role']]} {m['coach']} retired.")
    return out


def _expiring(league, team):
    """Your coordinators whose deals are up: re-sign at what he's asking, or let him walk."""
    import finance as fi
    import random
    for role, attr in (("OC", "oc"), ("DC", "dc")):
        c = getattr(team, attr, None)
        k = fi.contract(c)
        if c is None or k is None or k["end"] > league.year:
            continue
        ask_pay = fi._round(max(k["salary"] * 1.03, fi.asking(league, c, role)), 5_000)
        years = random.Random(f"resign:{c.name}:{league.year}").choice((2, 3, 3, 4))
        clear()
        print(title_bar(f"CONTRACT UP  ·  {staff.ROLE_NAMES[role].upper()}"))
        print()
        _staff_block(league, team, role, c)
        print()
        print(paint(f"   {c.name}'s deal ({fi.money(k['salary'])}/yr) is up. He wants {fi.money(ask_pay)}/yr "
                    f"for {years} years to stay.", C.BYELLOW, C.BOLD))
        print(paint(f"   NIL money you have free right now: {fi.money(fi.available(league, team))}", C.GRAY))
        if ask("Re-sign him? (y/n)").lower() in ("y", "yes"):
            fi.sign(league, team, c, {"salary": ask_pay, "years": years, "buyout": k.get("buyout", 0.6), "role": role},
                    start=league.year + 1)
            league.__dict__.setdefault("career_log", []).append((league.year, f"Re-signed {staff.ROLE_NAMES[role]} {c.name} "
                                                   f"({years} yrs, {fi.money(ask_pay)}/yr)."))
        else:
            staff.fire(league, team, role, "contract up")
            league.__dict__.setdefault("career_log", []).append((league.year, f"Let {staff.ROLE_NAMES[role]} {c.name} walk when his contract ran out."))


def review(league, team):
    """Keep or let go. Returns when you're done."""
    import coach_screens
    import finance as fi
    import hiring_market
    coach = team.coach
    new_job = coach.hired_year == league.year + 1
    if not new_job:
        _expiring(league, team)
    inherited = {r: new_job and (getattr(team, "oc" if r == "OC" else "dc", None) is not None) and
                 coach.name not in _tie_names(getattr(team, "oc" if r == "OC" else "dc", None))
                 for r in ("OC", "DC")}
    while True:
        clear()
        print(title_bar(f"YOUR STAFF  ·  {team.school.upper()}  ·  AFTER THE {league.year} SEASON"))
        for line in _news_for_you(league, team):
            print(paint(f"   {line}", C.BYELLOW, C.BOLD))
        if new_job:
            print(paint(f"   You inherit {team.school}'s coordinators. Keep them, or bring in your own people.", C.BCYAN))
        print()
        for role in ("OC", "DC"):
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            _staff_block(league, team, role, c, inherited=inherited[role])
            print()
        print(rule())
        opts = []
        if team.oc is not None:
            opts.append(f"{paint('[1]', C.BRED)} let the OC go")
        if team.dc is not None:
            opts.append(f"{paint('[2]', C.BRED)} let the DC go")
        opts += [f"{paint('[V1]', C.BYELLOW)}/{paint('[V2]', C.BYELLOW)} full resume",
                 f"{paint('[A]', C.GRAY)} let your AD run the staff from now on",
                 f"{paint('[Enter]', C.BGREEN)} done"]
        print("   " + "   ".join(opts))
        choice = ask("Your call:").strip().lower()
        if choice == "":
            return
        if choice in ("1", "2"):
            role = "OC" if choice == "1" else "DC"
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            cost = fi.owed(c, league) if c is not None else 0
            note = f" You'll owe him {fi.money(cost)} over the rest of his deal." if cost else ""
            if c is not None and ask(f"Let {c.name} go?{note} (y/n)").lower() in ("y", "yes"):
                why = "cleaned out" if new_job else "fired"
                staff.fire(league, team, role, why)
                league.__dict__.setdefault("career_log", []).append((league.year, f"Let {staff.ROLE_NAMES[role]} {c.name} go."))
        elif choice in ("v1", "v2"):
            c = team.oc if choice == "v1" else team.dc
            if c is not None:
                coach_screens.coach_view(league, c)
        elif choice == "a":
            if ask("Your AD will hire and fire your coordinators from now on. Sure? (y/n)").lower() in ("y", "yes"):
                league.staff_autopilot = True
                return


def _tie_names(c):
    return getattr(c, "staff_ties", set()) if c is not None else set()


def pick(league, team, role, options):
    """Choose a coordinator. Returns (coach, offer), or None to let the AD choose.
    The search itself (calls, interviews, packages, counters, retention) is coord_search.py."""
    import coord_search
    return coord_search.pick(league, team, role, options)


def my_staff(league):
    """From the career screen: your coordinators, and the autopilot switch."""
    coach = league.user_coach
    team = coach.team
    while True:
        clear()
        print(title_bar("MY STAFF"))
        if team is None:
            print(paint("\n   You're not coaching anywhere right now.", C.GRAY))
            pause()
            return
        print()
        for role in ("OC", "DC"):
            _staff_block(league, team, role, getattr(team, "oc" if role == "OC" else "dc", None))
            print()
        import staff
        cl = staff.calls(team)
        for side, key, coord in (("Offense", "off", team.oc), ("Defense", "def", team.dc)):
            who = staff.play_caller(team, key)
            scheme = who.offense_scheme if key == "off" else who.defense_scheme
            tag = "you" if who is team.coach else f"{'OC' if key == 'off' else 'DC'} {who.name}"
            print(f"   {paint('PLAY-CALLING', C.GRAY)}  {paint(pad(side, 8), C.BCYAN)} {paint(tag, C.BWHITE, C.BOLD)}"
                  f"  ·  runs the {scheme}")
        print(paint("   Whoever calls a side runs his scheme on Saturday, gets most of the in-game adjustments,\n"
                    "   and sets what your staff recruits to. In your games you can still take any snap yourself.", C.GRAY))
        print()
        auto = getattr(league, "staff_autopilot", False)
        print(paint(f"   Staff decisions: {'your AD handles them' if auto else 'yours, every offseason'}.", C.GRAY))
        print(paint("   You can let coordinators go and hire replacements in the offseason staff review.", C.GRAY))
        print(rule())
        print(f"   {paint('[V1]', C.BYELLOW)}/{paint('[V2]', C.BYELLOW)} full resume   "
              f"{paint('[T]', C.BYELLOW)} {'take back your staff decisions' if auto else 'let your AD run the staff'}   "
              f"{paint('[O]', C.BYELLOW)} who calls offense   {paint('[D]', C.BYELLOW)} who calls defense   "
              f"{paint('[B]', C.GRAY)} back")
        choice = ask("Select:").strip().lower()
        if choice in ("v1", "v2"):
            c = team.oc if choice == "v1" else team.dc
            if c is not None:
                import coach_screens
                coach_screens.coach_view(league, c)
        elif choice == "t":
            league.staff_autopilot = not auto
        elif choice in ("o", "d"):
            key = "off" if choice == "o" else "def"
            coord = team.oc if key == "off" else team.dc
            role = "OC" if key == "off" else "DC"
            now = staff.calls(team)[key]
            if coord is None:
                print(paint(f"   You don't have a {role} right now — you're calling it either way.", C.BYELLOW))
                pause()
            else:
                staff.set_calls(team, **({"off": role if now == "HC" else "HC"} if key == "off"
                                         else {"df": role if now == "HC" else "HC"}))
        else:
            return
