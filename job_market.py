"""
job_market.py — Going after a head coaching job that hasn't called you (Coach Career and
Commissioner Mode).

A job is OPEN (no head coach, or an interim finishing the year) or COULD OPEN (the coach is on a
hot seat close to his AD's firing line). Every AD ranks the coaches he could hire the same way the
carousel does (carousel.candidate_score): results for the level, ratings and fit, his AD style.
Your STANDING for a job is where you'd land on that list:

    their first call · on the shortlist · in the conversation · a long shot · not on their list

PURSUING a job (up to three a winter) tells your agent to make the call. When the carousel reaches
that opening, the AD decides: the higher you'd rank, the likelier an offer; a job you're overqualified
for listens harder, and a coach going home to his alma mater gets a long look. An offer is only ever
an offer: no human coach is hired without saying yes.

Coach Career: Coaches menu → Pursue a job, any time; the offers arrive with the rest of your calls.
Commissioner Mode: members rank up to three jobs on the website; the offseason market walks the open
jobs in prestige order, sends each AD's offers to the members who'd rank high enough, takes the
answer from their code (or asks you), and keeps going while each move opens another chair.
"""
import random

STANDING = ((1, "their first call"), (3, "on the shortlist"), (6, "in the conversation"), (12, "a long shot"))
OFFER_ODDS = {1: 0.9, 2: 0.7, 3: 0.6, 4: 0.4, 5: 0.35, 6: 0.3}
MAX_PURSUITS = 3
COULD_OPEN_MARGIN = 10          # seat within this many points of the AD's firing line


def _rng(league, *parts):
    return random.Random(":".join(str(p) for p in ("jobs", league.seed, league.year) + parts))


def is_open(team):
    import carousel as cz
    return team.coach is None or cz.is_interim(team.coach)


def open_jobs(league):
    return sorted((t for t in league.teams if is_open(t) and not getattr(t, "fcs", False)), key=lambda t: -t.prestige)


def could_open(league):
    """Sitting coaches near their AD's line, hottest first."""
    import carousel as cz
    out = []
    for t in league.teams:
        c = t.coach
        if c is None or cz.is_interim(c) or getattr(t, "fcs", False):
            continue
        gap = cz.fire_line(t) - getattr(c, "seat", 0)
        if gap <= COULD_OPEN_MARGIN:
            out.append((gap, t))
    out.sort(key=lambda x: x[0])
    return [t for _, t in out]


def _competition(league, team):
    """The scores of everyone else the AD would consider (CPU coaches only: people are judged one by one)."""
    import carousel as cz
    import staff
    rng = _rng(league, "field", team.school)
    sitting = [t.coach for t in league.teams if t.coach is not None and t is not team and not cz.is_interim(t.coach)
               and t.prestige < team.prestige - 3 and t.coach.history and not cz.human(t.coach)]
    pool = [c for c in league.coach_pool if c.status == "unemployed" and not cz.human(c)]
    try:
        coords = staff.head_coach_candidates(league, team)
    except Exception:                                   # noqa: BLE001 — a staff list that can't build just means fewer names
        coords = []
    import finance
    cap = finance.HC_CAP * finance.budget(team) * 1.1
    out = []
    for c in pool + sitting + coords:                         # only the names he could actually land
        if finance.asking(league, c, "HC") > cap or not cz.will_accept(c, team, league, rng):
            continue
        out.append(cz.candidate_score(team, c, league, rng, sitting=c in sitting))
    return sorted(out, reverse=True)


def standing(league, team, coach, field=None):
    """(rank, word): where this coach would land on the AD's list for this job."""
    import carousel as cz
    field = field if field is not None else _competition(league, team)
    me = cz.candidate_score(team, coach, league, _rng(league, "me", team.school, coach.name),
                            sitting=coach.team is not None)
    rank = 1 + sum(1 for s in field if s > me)              # a person can take less than his price: no budget gate
    word = next((w for cut, w in STANDING if rank <= cut), "not on their list")
    return rank, word


def _going_home(team, coach):
    return team.school == getattr(coach, "alma_mater", None)


def decide(league, team, coach, field=None):
    """The AD's answer to a coach who went after his job: (offer terms or None, why)."""
    import finance
    if not is_open(team):
        return None, "the job didn't open"
    if coach.team is team:
        return None, "that's already his job"
    rank, word = standing(league, team, coach, field)
    odds = OFFER_ODDS.get(rank, 0.15 if rank <= 10 else 0.03)
    if _going_home(team, coach):
        odds = min(0.95, odds + 0.25)
    if coach.team is not None and coach.team.prestige >= team.prestige + 10:
        odds = min(0.95, odds + 0.15)                  # a coach from a bigger job gets a long look
    if _rng(league, "decide", team.school, coach.name).random() >= odds:
        return None, f"{team.school} went another way (he was {word})"
    return finance.hc_offer(league, team, coach, _rng(league, "terms", team.school, coach.name)), f"he was {word}"


# ═══ Coach Career: your agent ═══════════════════════════════════════════════

def pursuits(coach, year):
    book = coach.__dict__.setdefault("pursuits", {})
    return book.setdefault(year, [])


def career_offers(league, coach, rng=None):
    """At the carousel: the jobs you went after that opened, as offers (team, "pursued"), with their terms.
    The ones that passed are noted for the offer screen."""
    out, notes = [], []
    terms = league.__dict__.setdefault("_user_offer_terms", {})
    for school in pursuits(coach, league.year):
        team = next((t for t in league.teams if t.school == school), None)
        if team is None:
            continue
        if team.coach is not None and not getattr(team.coach, "interim", None):
            notes.append(f"{school}: the job never opened")
            continue
        offer, why = decide(league, team, coach)
        if offer is None:
            notes.append(f"{school}: {why}")
            continue
        terms[school] = offer
        out.append((team, "pursued"))
    league.__dict__["_pursuit_notes"] = notes
    return out


def pursue_screen(league):
    """Coaches menu → Pursue a job: open jobs and hot seats with your standing; pick up to three."""
    from ui import C, ask, clear, pad, paint, rule, title_bar, truncate
    coach = getattr(league, "user_coach", None)
    if coach is None:
        return
    msg = ""
    while True:
        mine = pursuits(coach, league.year)
        jobs = [(t, "open") for t in open_jobs(league)] + [(t, "could open") for t in could_open(league)[:20]]
        jobs = [(t, k) for t, k in jobs if t is not coach.team][:30]
        clear()
        print(title_bar("PURSUE A JOB  ·  YOUR AGENT", sub=f"{len(mine)} of {MAX_PURSUITS} calls made"))
        print(paint("   Tell your agent which jobs to go after. When the carousel reaches an opening you pursued, the AD\n"
                    "   decides: the higher you'd rank on his list, the likelier the offer. Offers come with your other calls.",
                    C.GRAY))
        print()
        print(paint(f"   {'#':>3}  {'PROGRAM':<24}{'CONF':<15}{'PRES':>5}  {'JOB':<12}{'YOUR STANDING':<26}", C.GRAY, C.BOLD))
        for i, (t, kind) in enumerate(jobs, 1):
            _rank, word = standing(league, t, coach)
            mark = paint(" ◆ pursuing", C.BGREEN, C.BOLD) if t.school in mine else ""
            print(f"   {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(truncate(t.school, 23), 24)}{pad(truncate(t.conference, 14), 15)}"
                  f"{round(t.prestige):>5}  {pad(kind, 12)}{pad(word, 26)}{mark}")
        if not jobs:
            print(paint("   No jobs are open or close to opening right now.", C.GRAY))
        if msg:
            print(paint(f"\n   {msg}", C.BCYAN))
            msg = ""
        print(rule())
        c = ask("A # to pursue (again to drop it), Enter = back:").strip()
        if not c:
            return
        if c.isdigit() and 1 <= int(c) <= len(jobs):
            t = jobs[int(c) - 1][0]
            if t.school in mine:
                mine.remove(t.school)
                msg = f"Your agent won't call {t.school}."
            elif len(mine) >= MAX_PURSUITS:
                msg = "Three calls is the limit. Drop one first."
            else:
                mine.append(t.school)
                msg = f"Your agent will call {t.school} when the job opens."


# ═══ Commissioner Mode: the members' market ════════════════════════════════

def member_jobs(league, member):
    import commissioner as cm
    for t in league.teams:
        row = cm.team_row(league, t)
        if row.get("owner") == member:
            return list((row.get("orders") or {}).get("jobs", {}).get("want", []))
    return list(cm.state(league)["members"].get(member, {}).get("jobs", []))


def _answer(league, member, team, offer, ranked, fired):
    """A member's answer to an offer: from his code when he ranked the job; otherwise you're asked
    (the desk passes a callback), and with nobody to ask a fired member takes it and others pass."""
    import commissioner as cm
    import finance
    if team.school in ranked:
        return True, "it was on his list"
    text = (f"{team.school} offers @{member} its head coaching job: {finance.terms(offer)}. "
            + ("He's out of work." if fired else "He didn't list it."))
    ans = cm.ask(league, "offer", text, ["Accept for him", "Decline for him"], default=0 if fired else 1, team=team)
    return ans == 0, "you answered for him"


def commissioner_market(league, rng=None):
    """The offseason market for members (runs inside the carousel, before the CPU fills its openings).
    1. Members fired this winter lose their programs (and the inbox hears about it).
    2. Open jobs in prestige order: each AD considers the members who are out of work or who ranked his job.
       The best-placed one gets an offer if the AD wants him; the member's answer comes from his code.
    3. A move opens his old chair; the walk repeats until nobody moves."""
    import carousel as cz
    import commissioner as cm
    moves = []
    for t in cm.player_teams(league):                           # 1. this winter's firings
        row = cm.team_row(league, t)
        member = row["owner"]
        if t.coach is None and row.get("coach_name"):
            name = row["coach_name"]
            cm.release(league, t, "fired")
            cm.add_inbox(league, "fired", f"{t.school}'s AD fired @{member}. He's on the market with his coach, {name}: "
                         f"any open job can call him, and you'll answer for him.", team=t, options=["Got it"])
    declined = set()
    for _round in range(12):
        moved = False
        seekers = []
        for member in cm.state(league)["members"]:
            c = cm.member_coach(league, member)
            if c is None or c.status == "retired":
                continue
            ranked = member_jobs(league, member)
            fired = c.team is None
            if fired or ranked:
                seekers.append((member, c, ranked, fired))
        if not seekers:
            break
        for team in open_jobs(league):
            if team.coach is not None and not cz.is_interim(team.coach):
                continue
            field = None
            best = None
            for member, c, ranked, fired in seekers:
                if (member, team.school) in declined or c.team is team:
                    continue
                if not fired and team.school not in ranked:
                    continue
                if field is None:
                    field = _competition(league, team)
                offer, _why = decide(league, team, c, field)
                if offer is None:
                    continue
                pref = ranked.index(team.school) if team.school in ranked else 9
                rank, _w = standing(league, team, c, field)
                key = (rank, pref)
                if best is None or key < best[0]:
                    best = (key, member, c, ranked, fired, offer)
            if best is None:
                continue
            _key, member, c, ranked, fired, offer = best
            yes, how = _answer(league, member, team, offer, ranked, fired)
            if not yes:
                declined.add((member, team.school))
                cm.add_inbox(league, "offer", f"@{member} turned down {team.school} ({how}).", team=team, options=["Got it"])
                continue
            old = c.team
            if old is not None:
                cm.release(league, old, "left")
            if team.coach is not None and cz.is_interim(team.coach):
                cz.end_interim(league, team)
            cz.hire(league, team, c, "poach" if old is not None else "pool", offer)
            if cm.is_player_team(league, team):
                cm.release(league, team, "left")
            cm.claim(league, team, member)
            cm.take_over(league, team, member, "adopt")
            cm.state(league)["members"].setdefault(member, {})["jobs"] = []
            cm.add_inbox(league, "hired", f"@{member} takes the {team.school} job ({how}): {__import__('finance').terms(offer)}."
                         + (f" {old.school} is open (CPU) now." if old is not None else ""), team=team, options=["Got it"])
            moves.append((member, old.school if old else None, team.school))
            moved = True
            break                                               # the board changed: walk it again from the top
        if not moved:
            break
    return moves


def member_contract(league, team, coach, rng, expiring, reason):
    """A member's AD wants to talk contract: the offer goes to the Commissioner Inbox (his code's standing
    answer decides it, or you do); a coach whose deal runs out on a hot seat isn't renewed."""
    import carousel as cz
    import commissioner as cm
    import finance
    member = getattr(coach, "commish_member", None)
    k = finance.contract(coach)
    if expiring and coach.seat >= cz.fire_line(team) - 12:
        cz._news(league, "fired", f"{team.school} lets {coach.name}'s contract run out — no buyout")
        cz.vacate(league, team, "fired")
        return
    if reason is None and not (not expiring and k and k["end"] == league.year + 1 and coach.seat <= 35):
        return
    offer = finance.hc_offer(league, team, coach, rng, extension=True)
    if k and not expiring:
        offer["salary"] = finance._round(min(max(offer["salary"], k["salary"] * 1.05), finance.HC_CAP * finance.budget(team)), 25_000)
        offer["years"] = min(8, max(offer["years"], k["end"] - league.year + 2))
    row = cm.team_row(league, team)
    pref = ((row.get("orders") or {}).get("jobs") or {}).get("extend", "ask")
    text = (f"{team.school}'s AD offers @{member} {'a new contract' if expiring else 'an extension'}"
            f"{' ' + reason if reason else ''}: {finance.terms(offer)}.")
    if pref in ("yes", "no"):
        ans = 0 if pref == "yes" else 1
        cm.note(league, "contract", text + (" Signed (his standing answer)." if ans == 0 else " Turned down (his standing answer)."), team=team)
    else:
        ans = cm.ask(league, "contract", text, ["Sign it", "Turn it down"], default=0, team=team)
    if ans == 0:
        finance.sign(league, team, coach, offer, start=league.year + 1)
    else:
        if expiring:
            cz._news(league, "retired", f"{coach.name} and {team.school} part ways as his contract runs out")
            cz.vacate(league, team, "left")


# ═══ The website ════════════════════════════════════════════════════════════

def public_jobs(league):
    import knowledge as kn
    import scout
    rows = []
    for t in open_jobs(league):
        c = t.coach
        rows.append({"id": kn.slug(t.school), "kind": "open", "prestige": round(t.prestige),
                     "note": f"{c.name} is the interim" if c is not None else "no head coach",
                     "roster": scout._w(scout.TEAM, t.team_ovr)})
    import carousel as cz
    for t in could_open(league)[:25]:
        rows.append({"id": kn.slug(t.school), "kind": "could open", "prestige": round(t.prestige),
                     "note": f"{t.coach.name}: {cz.seat_label(round(t.coach.seat))}", "roster": scout._w(scout.TEAM, t.team_ovr)})
    return rows


def private_jobs(league, team):
    """One member's standing for every open or could-open job, plus what he's told the commissioner."""
    import commissioner as cm
    import knowledge as kn
    c = team.coach
    row = cm.team_row(league, team)
    j = (row.get("orders") or {}).get("jobs") or {}
    out = {"want": [kn.slug(x) for x in j.get("want", [])], "extend": j.get("extend", "ask"), "standing": {}}
    if c is None:
        return out
    fields = league.__dict__.setdefault("_job_fields", {})           # one AD list per job per export
    for t in open_jobs(league) + could_open(league)[:25]:
        if t is team:
            continue
        if t.school not in fields:
            fields[t.school] = _competition(league, t)
        _rank, word = standing(league, t, c, fields[t.school])
        out["standing"][kn.slug(t.school)] = word
    return out
