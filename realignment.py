"""
realignment.py — Schools change leagues, slowly, for the reasons they really do.

Every offseason (from the winter after 2026 on) the league office runs the math:

  SCHOOL VALUE  what a program is worth to a TV partner: its brand (tradition
                and prestige), how it's winning lately (the last four seasons,
                titles, playoff trips), the size of its home TV market, and how
                many people fill its stadium.

  CONFERENCE    each league has a media deal that pays every member the same
  PAYOUT        amount a year. Deals run for years at a time; when one comes up
                for renewal the new number is set by what the membership is
                worth then (the average member, and the league's biggest brands).
                A league that loses its brands gets a smaller check next time.

  INVITATIONS   a league with room invites a school that would raise its value;
                a league that's losing members backfills from the leagues below it.
                The school says yes if the money is enough better to pay the exit
                fee and still come out ahead — travel to a far-off league, leaving
                its rivals behind, and a proud independent's pride all argue
                against it. Leaving a Power league costs a lot more than leaving
                a Group of Five one, which is why big moves are rare.

Moves are announced one winter and take effect the season after next, so every
school plays one lame-duck year in its old league. Power leagues cap at 20,
everybody else at 14, and nobody drops below 8 without backfilling. The four
Power leagues stay the Power leagues — who's in them is what changes.

In Athletic Director mode, an invitation to your school is your call.

    league.realign = {"payout": {conf: dollars}, "renews": {conf: year},
                      "pending": [move], "history": [move], "news": {year: [text]},
                      "offer": move-or-None}
"""
import world
import math
import random

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

M = 1_000_000
POWER = world.POWER
FIRST_YEAR = 2027                  # the first offseason that can announce a move (after the 2026 season)
LEAD = 2                           # announced after season Y, playing in the new league in Y+2
MAX_POWER, MAX_OTHER, MIN_SIZE = 20, 14, 8
MAX_ANNOUNCED = 3                  # moves announced in one winter, league-wide

# What each league pays every member a year when your world begins (approximate 2026 media money).
START_PAYOUT = {"Continental": 60 * M, "SCC": 55 * M, "Seaboard": 40 * M, "Meridian": 32 * M, "Golden West": 10 * M,
                "Federal": 7 * M, "High Country": 5 * M, "Coastal Plains": 3 * M, "Crossroads": 1.5 * M,
                "Lake Country": 1.5 * M, "Independent": 2 * M}
INDEPENDENT_DEALS = {"South Bend": 25 * M}          # its own national TV deal
# When each league's current deal ends (staggered like the real ones).
START_RENEWAL = {"Continental": 2030, "SCC": 2034, "Seaboard": 2036, "Meridian": 2031, "Golden West": 2031, "Federal": 2031,
                 "High Country": 2032, "Coastal Plains": 2031, "Crossroads": 2029, "Lake Country": 2027, "Independent": 2029}
DEAL_YEARS = (6, 8, 10)
# Exit fees, as years of the old payout (grant of rights in the Power leagues).
EXIT_YEARS = {"SCC": 3.0, "Continental": 3.0, "Seaboard": 3.0, "Meridian": 2.0}
EXIT_YEARS_OTHER = 1.0

# TV households, roughly: state population in millions.
STATE_POP = {
    "AL": 5.1, "AR": 3.1, "AZ": 7.4, "CA": 39.0, "CO": 5.9, "CT": 3.6, "DE": 1.0, "FL": 22.6, "GA": 11.0,
    "HI": 1.4, "IA": 3.2, "ID": 2.0, "IL": 12.5, "IN": 6.9, "KS": 2.9, "KY": 4.5, "LA": 4.6, "MA": 7.0,
    "MD": 6.2, "ME": 1.4, "MI": 10.0, "MN": 5.7, "MO": 6.2, "MS": 2.9, "MT": 1.1, "NC": 10.8, "ND": 0.8,
    "NE": 2.0, "NH": 1.4, "NJ": 9.3, "NM": 2.1, "NV": 3.2, "NY": 19.6, "OH": 11.8, "OK": 4.0, "OR": 4.2,
    "PA": 13.0, "RI": 1.1, "SC": 5.4, "SD": 0.9, "TN": 7.1, "TX": 30.5, "UT": 3.4, "VA": 8.7, "VT": 0.6,
    "WA": 7.8, "WI": 5.9, "WV": 1.8, "WY": 0.6,
}


def state(league):
    st = league.__dict__.get("realign")
    if st is None:
        st = league.realign = {"payout": {}, "renews": {}, "pending": [], "history": [], "news": {},
                               "offer": None}
    for conf in {t.conference for t in league.teams} | set(START_PAYOUT):
        st["payout"].setdefault(conf, START_PAYOUT.get(conf, 3 * M))
        st["renews"].setdefault(conf, START_RENEWAL.get(conf, league.year + 6))
    return st


def payout(league, conf, school=None):
    if conf == "Independent" and school in INDEPENDENT_DEALS:
        return INDEPENDENT_DEALS[school]
    return state(league)["payout"].get(conf, 3 * M)


def is_power(conf):
    return conf in POWER


# ═══ What a school is worth ════════════════════════════════════════════════

def school_value(league, t):
    """0-100ish: brand, recent winning, market, crowd."""
    brand = t.ratings["tradition"] * 0.45 + t.prestige * 0.25
    recs = [r for r in getattr(t, "historical_records", []) if r[0] >= 2026][-4:]
    if recs:
        pct = sum(r[1] for r in recs) / max(1, sum(r[1] + r[2] for r in recs))
        wins = pct * 100
        hard = 0
        for r in recs:
            ach = r[5] if len(r) > 5 else []
            hard += 6 * ("National Champion" in ach) + 3 * ("NP Appearance" in ach) \
                + 1.5 * any(a.endswith(" Champion") and "National" not in a and "Bowl" not in a for a in ach)
    else:
        wins = t.ratings["tradition"] * 0.8
        hard = 0
    pop = STATE_POP.get(getattr(t, "home_state", None) or "", 3.0)
    market = 10 * math.log10(max(0.5, pop)) * 2.2              # 0.6M ≈ 0, 40M ≈ 35
    crowd = min(110_000, t.capacity) / 110_000 * 20
    return brand * 0.55 + wins * 0.20 + hard + market * 0.35 + crowd * 0.35


def conference_value(league, conf, members=None, values=None):
    members = members if members is not None else league.conference_teams(conf)
    if not members:
        return 0.0
    vals = sorted(((values or {}).get(t.school) or school_value(league, t) for t in members), reverse=True)
    top = vals[:4]
    return sum(vals) / len(vals) * 0.7 + sum(top) / len(top) * 0.3


def _deal_for(value, conf):
    """A new TV deal, per member per year, from what the league is worth.
    Calibrated so the 2026 leagues would sign roughly the deals they have."""
    base = 1.5 * M * math.exp((value - 31) * 0.125)
    if is_power(conf):
        base += 18 * M                                 # the playoff access the Power leagues guarantee
    return int(max(1 * M, min(95 * M, base)) // 100_000 * 100_000)


# ═══ Geography ═════════════════════════════════════════════════════════════

def _region(t):
    from recruiting_data import STATES
    s = getattr(t, "home_state", None)
    return STATES.get(s, ("", ""))[1] if s else ""


def _fit(t, members):
    """How well a school fits a league on the map: 1.0 = in the footprint, 0 = across the country."""
    from recruiting_data import REGION_NEIGHBORS
    if not members:
        return 0.5
    r = _region(t)
    same = sum(_region(m) == r for m in members) / len(members)
    near = sum(_region(m) in REGION_NEIGHBORS.get(r, ()) for m in members) / len(members)
    return min(1.0, same + near * 0.5)


def _division_for(league, t, conf):
    divs = [d for d in league.divisions(conf) if d]
    if not divs:
        return None
    east = _region(t) in ("Southeast", "Northeast")
    for d in divs:
        if ("East" in d) == east:
            return d
    return min(divs, key=lambda d: sum(1 for m in league.conference_teams(conf) if m.division == d))


# ═══ The offseason ═════════════════════════════════════════════════════════

def _news(st, year, text):
    st["news"].setdefault(year, []).append(text)


def _pending_out(st):
    return {m["school"] for m in st["pending"]}


def _projected(league, st):
    """Conference -> members once everything announced has happened."""
    out = {}
    moving = {m["school"]: m["to"] for m in st["pending"]}
    for t in league.teams:
        out.setdefault(moving.get(t.school, t.conference), []).append(t)
    return out


def offseason(league, rng, next_year):
    """Run once per winter, before next season's schedule is built.
    `league.year` is still the season that just ended."""
    if next_year < FIRST_YEAR:
        return []
    st = state(league)
    rng = random.Random(f"realign:{league.seed}:{league.year}")
    year = league.year
    by_school = {t.school: t for t in league.teams}

    # 0. An invitation the AD never answered: the board decides on its staff's advice.
    offer = st.get("offer")
    if offer and offer["year"] < year:
        decide_offer(league, bool(offer.get("rec")))

    # 1. Moves that were announced two winters ago happen now.
    done = []
    for m in [m for m in st["pending"] if m["effective"] <= next_year]:
        t = by_school.get(m["school"])
        st["pending"].remove(m)
        if t is None:
            continue
        old = t.conference
        _move(league, t, m["to"])
        m["done"] = True
        st["history"].append(m)
        done.append(m)
        _news(st, year, f"{t.school} officially joins the {m['to']} for the {next_year} season"
                        f" after {m.get('years_in', '?')} years in the {old}.")

    # 2. TV deals that expire this winter are renegotiated.
    values = {t.school: school_value(league, t) for t in league.teams}
    for conf in sorted({t.conference for t in league.teams}):
        if conf == "Independent" or st["renews"].get(conf, 9999) > next_year:
            continue
        members = _projected(league, st).get(conf, [])
        old = st["payout"].get(conf, 3 * M)
        new = _deal_for(conference_value(league, conf, members, values), conf)
        new = int((old * 0.35 + new * 0.65) // 100_000 * 100_000)     # deals don't swing all the way at once
        st["payout"][conf] = new
        length = rng.choice(DEAL_YEARS)
        st["renews"][conf] = next_year + length
        from finance import money
        change = (new - old) / old if old else 0
        verb = ("lands a huge raise" if change >= 0.25 else "gets a raise" if change >= 0.05
                else "takes a pay cut" if change <= -0.05 else "renews flat")
        _news(st, year, f"TV: the {conf} {verb} — a new {length}-year media deal pays {money(new)} per school "
                        f"a year (was {money(old)}).")

    # 3. Invitations. Richest leagues shop first; a league about to fall below
    #    eight goes shopping no matter what.
    announced = []
    proj = _projected(league, st)
    order = sorted((c for c in proj if c != "Independent"), key=lambda c: -payout(league, c))
    for conf in order:
        if len(announced) >= MAX_ANNOUNCED:
            break
        members = proj.get(conf, [])
        cap = MAX_POWER if is_power(conf) else MAX_OTHER
        short = len(members) < MIN_SIZE
        if len(members) >= cap:
            continue
        appetite = 0.9 if short else (0.14 if is_power(conf) else 0.08)
        if len(members) < 10 and not is_power(conf):
            appetite = max(appetite, 0.35)
        if rng.random() > appetite:
            continue
        cv = conference_value(league, conf, members, values)
        pay = payout(league, conf)
        cands = []
        for t in league.teams:
            if t in members or t.school in _pending_out(st) or t.school in {m["school"] for m in announced}:
                continue
            if any(h["school"] == t.school and h["effective"] > next_year - 6 for h in st["history"]):
                continue                                       # just moved; nobody's leaving again yet
            if year - st.setdefault("refused", {}).get(f"{t.school}|{conf}", -99) < 6:
                continue                                       # told us no not long ago
            v = values[t.school]
            fit = _fit(t, members)
            # The league only wants you if you make it better (or it needs bodies).
            bar = cv - (8 if short else 0) - (3 if len(members) < 10 else 0)
            if v < bar:
                continue
            their = payout(league, t.conference, t.school)
            if their >= pay and not short:
                continue
            if fit < 0.15 and not short:
                continue
            cands.append((v + fit * 12 - (their / M) * 0.05, t))
        if not cands:
            continue
        cands.sort(key=lambda x: -x[0])
        for _, t in cands[:3]:
            yes, why = _decide(league, t, conf, members, rng)
            if st.get("offer") is None and _is_user_ad_school(league, t):
                st["offer"] = {"school": t.school, "from": t.conference, "to": conf, "year": year,
                               "effective": next_year + LEAD - 1, "why": why, "rec": yes}
                _news(st, year, f"The {conf} has formally invited {t.school}. The decision is the AD's.")
                break
            if yes:
                m = _announce(league, st, t, conf, next_year, why)
                announced.append(m)
                proj = _projected(league, st)
                break
            _news(st, year, f"{t.school} turns down an invitation from the {conf} — {why}.")
            st.setdefault("refused", {})[f"{t.school}|{conf}"] = year
            break

    # 4. Everybody at least eight strong. If a league is still short, it takes the
    #    best Group of Five school that will come (and one always will).
    proj = _projected(league, st)
    for conf, members in sorted(proj.items()):
        if conf == "Independent":
            continue
        tries = 0
        while len(members) < MIN_SIZE and tries < 6:
            tries += 1
            pool = [t for t in league.teams if t.conference not in POWER and t.conference != conf
                    and t.school not in _pending_out(st)
                    and len(proj.get(t.conference, [])) > MIN_SIZE
                    and payout(league, t.conference, t.school) <= payout(league, conf) * 1.25]
            if not pool:
                break
            t = max(pool, key=lambda t: values[t.school] + _fit(t, members) * 15)
            m = _announce(league, st, t, conf, next_year, "a league that needed members, and a bigger check")
            announced.append(m)
            proj = _projected(league, st)
            members = proj.get(conf, [])
    _tell_the_coach(league, st, done, announced)
    return done + announced


def _tell_the_coach(league, st, done, announced):
    """Coach Career: your AD lets you know when your school is on the move."""
    me = getattr(league, "user_coach", None)
    if getattr(league, "mode", None) != "career" or me is None or me.team is None:
        return
    import people
    team = me.team
    from finance import money
    for m in announced:
        if m["school"] == team.school:
            people.choice(league, f"AD {team.ad['name']}", "Athletic Director", f"We're joining the {m['to']}",
                          f"Coach, it's official: we leave the {m['from']} for the {m['to']} in {m['effective']}. "
                          f"That's {money(payout(league, m['to']))} a school a year in media money, and half of the "
                          f"difference is coming to football. How do you want to sell it?",
                          [(f"Recruit the {m['to']} footprint now.", {"recruits": 3, "chem": -1},
                            "Your staff hits the road in the new footprint. The current players feel a little "
                            "like the old news."),
                           ("Tell the players first. This is theirs.", {"chem": 3},
                            "The team heard it from you before the internet."),
                           ("Ask for more than half of that money for football.",
                            {"money": 300_000, "seat": 2, "money_what": f"the {m['to']} move"},
                            "He found more. He didn't love being asked on the day of the announcement.")],
                          color=C.BYELLOW, due=(league.year + 1, 1))
    for m in done:
        if m["school"] == team.school:
            people.choice(league, f"AD {team.ad['name']}", "Athletic Director", f"Welcome to the {m['to']}",
                          f"New league, new schedule. The budget is up to date. Let's show them we belong.",
                          [("We belong. Circle the league opener.", {"recruits": 1.5, "seat": -1, "chem": -1},
                            "Big words for the new neighborhood. The players feel the weight of them."),
                           ("It'll take a year to learn this league.", {"chem": 1, "seat": 1},
                            "Honest. He wanted more confidence.")],
                          color=C.BYELLOW, due=(league.year + 1, 1))


def _is_user_ad_school(league, t):
    if getattr(league, "mode", None) != "ad" or getattr(league, "autosim", False):
        return False
    ad = getattr(league, "ad_user", None) or {}
    return ad.get("team") is t


def _decide(league, t, conf, members, rng):
    """Does the school say yes? Returns (yes, reason)."""
    from carousel import PRIMARY_RIVAL
    old = t.conference
    mine = payout(league, old, t.school)
    theirs = payout(league, conf)
    exit_fee = mine * (EXIT_YEARS.get(old, EXIT_YEARS_OTHER))
    horizon = 8                                            # years the board looks ahead
    gain = (theirs - mine) * horizon - exit_fee
    score = gain / M
    fit = _fit(t, members)
    score -= (1 - fit) * 25                               # flights, missed class, angry Olympic-sport coaches
    rival = PRIMARY_RIVAL.get(t.school)
    rival_team = next((x for x in league.teams if x.school == rival), None)
    if rival_team is not None and rival_team.conference == old and rival_team not in members:
        score -= 12                                        # it'd survive as a non-conference game, but still
    if old == "Independent":
        score -= 110 + t.ratings["tradition"] * 0.6         # independence is part of who they are
        if t.school in INDEPENDENT_DEALS:
            score -= 150                                   # its own TV deal, its own schedule, its own identity
    if is_power(conf) and not is_power(old) and t.school not in INDEPENDENT_DEALS:
        score += 25                                        # the playoff door and recruiting pitch that come with it
    if is_power(old) and not is_power(conf):
        score -= 80
    score += rng.gauss(0, 12)
    if score > 0:
        why = ("the money" if theirs - mine > 15 * M else "a bigger media check" if theirs > mine
               else "a better fit")
        if is_power(conf) and not is_power(old):
            why = "a seat at the Power table"
        return True, why
    if old == "Independent":
        return False, "independence isn't for sale"
    if rival_team is not None and rival_team.conference == old:
        return False, f"it won't leave {rival} behind"
    if fit < 0.4:
        return False, "too far from home"
    return False, "the money doesn't cover the exit fee"


def _announce(league, st, t, conf, next_year, why):
    hist = getattr(t, "conf_history", None) or [(2026, t.conference)]
    years_in = league.year - hist[-1][0] + 1
    m = {"school": t.school, "from": t.conference, "to": conf, "announced": league.year,
         "effective": next_year + LEAD - 1, "why": why, "years_in": years_in}
    st["pending"].append(m)
    from finance import money
    _news(st, league.year, f"REALIGNMENT: {t.school} will leave the {t.conference} for the {conf} in "
                           f"{m['effective']} — {why}. ({money(payout(league, t.conference, t.school))} a year now, "
                           f"{money(payout(league, conf))} in the {conf}.)")
    return m


def _move(league, t, conf):
    """Change leagues: standings, divisions, the money."""
    import finance
    old = t.conference
    before = payout(league, old, t.school)
    t.conference = conf
    t.division = _division_for(league, t, conf)
    hist = t.__dict__.setdefault("conf_history", [(2026, old)])
    hist.append((league.year + 1, conf))
    # A traditional rivalry doesn't die because the leagues changed: it becomes a protected game.
    from season import RIVALRY_WEEK
    from carousel import PRIMARY_RIVAL
    import rivalries
    keep = state(league).setdefault("protected", [])
    for o in league.teams:
        if o is t or o.conference != old:
            continue
        pair = tuple(sorted((t.school, o.school)))
        traditional = (frozenset(pair) in {frozenset(p) for p in RIVALRY_WEEK} or rivalries.trophy(*pair)
                       or (PRIMARY_RIVAL.get(t.school) == o.school and PRIMARY_RIVAL.get(o.school) == t.school))
        if traditional and pair not in keep and sum(t.school in p for p in keep) < 2:
            keep.append(pair)
    # Roughly half of a media check is football money.
    b = finance.budget(t)
    t.budget = int(max(3 * M, b + (payout(league, conf) - before) * 0.5) // 100_000 * 100_000)


def decide_offer(league, accept):
    """Athletic Director mode: your answer to an invitation."""
    st = state(league)
    offer = st.get("offer")
    if not offer:
        return None
    st["offer"] = None
    t = next((x for x in league.teams if x.school == offer["school"]), None)
    if t is None or t.conference != offer["from"]:
        return None
    if accept:
        m = {"school": t.school, "from": t.conference, "to": offer["to"], "announced": offer["year"],
             "effective": offer["effective"], "why": "the athletic director's call",
             "years_in": league.year - (getattr(t, "conf_history", None) or [(2026, t.conference)])[-1][0] + 1}
        st["pending"].append(m)
        _news(st, offer["year"], f"REALIGNMENT: {t.school} accepts the {offer['to']}'s invitation and will join "
                                 f"in {offer['effective']}.")
        return m
    _news(st, offer["year"], f"{t.school} declines the {offer['to']}'s invitation.")
    return False


def conference_on(t, year):
    """Which league a school was in for a given season."""
    hist = getattr(t, "conf_history", None)
    if not hist:
        return t.conference
    conf = hist[0][1]
    for y, c in hist:
        if y <= year:
            conf = c
    return conf


def news_for(league, year):
    return list(state(league)["news"].get(year, []))


# ═══ Screens ══════════════════════════════════════════════════════════════

def offer_screen(league):
    """Athletic Director mode: an invitation to your school."""
    st = state(league)
    offer = st.get("offer")
    if not offer:
        return
    from finance import money
    clear()
    print(title_bar("AN INVITATION"))
    print()
    mine = payout(league, offer["from"], offer["school"])
    theirs = payout(league, offer["to"])
    fee = mine * EXIT_YEARS.get(offer["from"], EXIT_YEARS_OTHER)
    print(f"   The {paint(offer['to'], C.BYELLOW, C.BOLD)} commissioner is on the phone. They want {offer['school']}"
          f" in {offer['effective']}.")
    print()
    print(f"   {paint('Media money', C.GRAY):<24} {money(mine)} a year now  →  {paint(money(theirs), C.BGREEN, C.BOLD)} a year")
    print(f"   {paint('Exit fee', C.GRAY):<24} {money(fee)}  (paid once, on the way out)")
    members = league.conference_teams(offer["to"])
    print(f"   {paint('New neighbors', C.GRAY):<24} " + ", ".join(t.school for t in sorted(members, key=lambda t: -t.prestige)[:8])
          + ("…" if len(members) > 8 else ""))
    print(f"   {paint('Your staff says', C.GRAY):<24} " + ("take it" if offer["rec"] else "think hard")
          + f" — {offer['why']}")
    print(paint("\n   You'd play one more season in your current league first. Half the new money reaches football.", C.GRAY))
    c = ask("[A] Accept   [D] Decline   (Enter = decide later, before next winter):").strip().lower()
    if c == "a":
        decide_offer(league, True)
        print(paint(f"\n   Done. {offer['school']} is headed to the {offer['to']}.", C.BGREEN))
        pause()
    elif c == "d":
        decide_offer(league, False)
        print(paint("\n   You stay put. The commissioner says the door won't stay open forever.", C.BYELLOW))
        pause()


def realignment_screen(league):
    """Media Center: who's where, who's moving, and what every league is paid."""
    from finance import money
    st = state(league)
    clear()
    print(title_bar("CONFERENCE REALIGNMENT"))
    print()
    print(section("THE LEAGUES", C.BYELLOW))
    print(paint(f"   {'LEAGUE':<18}{'SCHOOLS':>8}   {'PAYOUT/SCHOOL':>14}   {'DEAL RUNS TO':>12}   VALUE", C.GRAY))
    values = {t.school: school_value(league, t) for t in league.teams}
    for conf in sorted({t.conference for t in league.teams}, key=lambda c: -payout(league, c)):
        n = len(league.conference_teams(conf))
        cv = conference_value(league, conf, None, values)
        renew = st["renews"].get(conf, "")
        print(f"   {pad(paint(conf, league.conference_color(conf), C.BOLD), 18)}{n:>8}   "
              f"{money(payout(league, conf)):>14}   {str(renew):>12}   {cv:5.1f}")
    print()
    if st["pending"]:
        print(section("ANNOUNCED MOVES", C.BMAGENTA))
        for m in sorted(st["pending"], key=lambda m: (m["effective"], m["school"])):
            print(f"   {pad(m['school'], 22)}{pad(m['from'], 16)}→  {pad(m['to'], 16)}{m['effective']}  "
                  f"{paint(m['why'], C.GRAY)}")
        print()
    if st["history"]:
        print(section("MOVES SINCE 2026", C.BCYAN))
        for m in sorted(st["history"], key=lambda m: -m["effective"])[:15]:
            print(f"   {paint(str(m['effective']), C.GRAY)}  {pad(m['school'], 22)}{pad(m['from'], 16)}→  {m['to']}")
        print()
    if not st["pending"] and not st["history"]:
        print(paint("   The map hasn't moved yet. Media deals come up for renewal over the next decade —\n"
                    "   that's when leagues go shopping.", C.GRAY))
        print()
    print(section("MOST VALUABLE PROGRAMS (TV)", C.BGREEN))
    top = sorted(league.teams, key=lambda t: -values[t.school])[:12]
    for i, t in enumerate(top, 1):
        print(f"   {paint(f'{i:>2}.', C.GRAY)} {pad(t.school, 22)}{pad(paint(t.conference, league.conference_color(t.conference)), 18)}"
              f"{values[t.school]:5.1f}")
    pause()
