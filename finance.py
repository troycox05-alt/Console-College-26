"""
finance.py — Money: every program's football budget, its coaching contracts,
and the NIL money it hands to players.

THE BUDGET
  Every FBS program gets one number to spend on football each year, set by the
  size of the program and its league. It moves once a year with results
  (adjust_budgets, below): winning grows it, years of losing and coaching churn
  shrink it. Out of it comes:
    the head coach's salary          about a fifth of a typical budget
    both coordinators' salaries      a few percent each
    buyouts                          money still owed to coaches the school fired
    player NIL                       everything that's left
  Every dollar the staff costs is a dollar that can't go to players.

CONTRACTS
  Coaches and coordinators sign for a salary and a number of years. The AD
  writes the offer, and his style decides its shape: a Booster-Driven AD
  backs up the truck for seven years, a Budget Hawk offers three short,
  cheap ones, a Recruiting-First AD keeps coach pay down to fund NIL.
  Bigger coaches get bigger offers from bigger schools. A coach compares the
  money to what he thinks he's worth — a Mercenary more than most — and a big
  enough check will move him for a smaller step up than he'd take otherwise.
  Fire a coach with years left and the school keeps paying him (the AD's
  buyout terms) every year until the deal would have ended.

NIL
  A scholarship offer comes first; NIL money goes on top of it. Money makes a
  program louder in a recruit's ear every week — how loud depends on how much
  money matters to him, how the offer compares to his market, and whether
  somebody else is offering more. It never decides a recruitment by itself: a
  kid who doesn't want your school won't sign for money alone. A signee's
  deal is paid every year he stays on the roster; leave through the portal
  and the deal ends. Open offers count against the pool until he picks,
  so nobody can promise more than they have.
"""
import world
import math
import random
from netplay import capture

M = 1_000_000
POWER_CONFS = world.POWER

HC_SHARE = 0.22             # a typical head coach's share of the budget
COORD_SHARE = 0.045         # ...and each coordinator's
HC_CAP = 0.30               # nobody pays a head coach more than this share
COORD_CAP = 0.075
CLASS_SHARE = 0.92          # a class gets about this share of the room the departing players leave
OPS_SHARE = 0.20            # support staff, travel, medical, operations: off the top of every budget
BUDGET_REF = 14_300_000     # a middle-of-FBS football budget: NIL deals scale from here
NIL_MARKET = {5: 900_000, 4: 300_000, 3: 70_000, 2: 20_000, 1: 8_000, 0: 0}
AI_NIL_PER_WEEK = 4           # new NIL offers an AI staff makes in a week (more in the compressed pre-2026 years)

# money: how far above (or below) the market the AD will go    years: typical contract length
# buyout: share of the remaining salary owed if he fires the coach    nil: how hard he spends on players
AD_CONTRACT = {
    "patient":        dict(money=1.00, years=6, buyout=0.70, nil=1.00, blurb="long, steady deals"),
    "win_now":        dict(money=1.12, years=4, buyout=0.55, nil=1.05, blurb="pays up, short leash"),
    "big_game":       dict(money=1.15, years=5, buyout=0.65, nil=1.00, blurb="pays for a big name"),
    "conference":     dict(money=1.00, years=5, buyout=0.65, nil=1.00, blurb="market-rate deals"),
    "analytics":      dict(money=0.92, years=4, buyout=0.55, nil=0.95, blurb="pays what the numbers say"),
    "booster":        dict(money=1.25, years=7, buyout=0.85, nil=1.20, blurb="the boosters write huge, long checks"),
    "turnaround":     dict(money=0.98, years=5, buyout=0.60, nil=1.00, blurb="middle-of-the-market deals"),
    "recruiting":     dict(money=0.88, years=5, buyout=0.60, nil=1.25, blurb="keeps coach pay down to fund NIL"),
    "traditionalist": dict(money=0.95, years=6, buyout=0.70, nil=0.95, blurb="long deals, modest money"),
    "budget":         dict(money=0.82, years=3, buyout=0.40, nil=0.85, blurb="cheap, short, small buyouts"),
    "brand":          dict(money=1.20, years=6, buyout=0.75, nil=1.10, blurb="pays for a name that sells"),
    "politician":     dict(money=1.10, years=4, buyout=0.60, nil=1.10, blurb="pays whatever quiets the callers"),
}
# The rest of a contract, by AD style.
#   raise     yearly escalator on the salary
#   incent    size of the bonus pool, as a share of salary (bowl, league title, playoff, national title)
#   offset    odds the deal has an offset clause: fire him, and whatever his next job pays comes off the buyout
#   release   what he (or his next school) owes if he leaves early: share of salary per year left, max 3 years
#   rollover  odds of a rollover clause: every 8-win season adds a year to the deal
CLAUSES = {
    "patient":        dict(raise_=0.03, incent=0.08, offset=0.30, release=0.50, rollover=0.40),
    "win_now":        dict(raise_=0.02, incent=0.25, offset=0.50, release=0.30, rollover=0.10),
    "big_game":       dict(raise_=0.03, incent=0.20, offset=0.30, release=0.40, rollover=0.20),
    "conference":     dict(raise_=0.03, incent=0.15, offset=0.40, release=0.40, rollover=0.30),
    "analytics":      dict(raise_=0.02, incent=0.12, offset=0.70, release=0.35, rollover=0.20),
    "booster":        dict(raise_=0.05, incent=0.15, offset=0.10, release=0.60, rollover=0.50),
    "turnaround":     dict(raise_=0.03, incent=0.15, offset=0.40, release=0.40, rollover=0.30),
    "recruiting":     dict(raise_=0.03, incent=0.10, offset=0.40, release=0.40, rollover=0.30),
    "traditionalist": dict(raise_=0.03, incent=0.10, offset=0.30, release=0.50, rollover=0.40),
    "budget":         dict(raise_=0.01, incent=0.20, offset=0.95, release=0.25, rollover=0.00),
    "brand":          dict(raise_=0.04, incent=0.18, offset=0.20, release=0.50, rollover=0.30),
    "politician":     dict(raise_=0.03, incent=0.20, offset=0.30, release=0.35, rollover=0.20),
}
BONUS_SPLIT = {"bowl": 0.10, "conf_title": 0.25, "cfp": 0.30, "title": 0.60}
BONUS_LABELS = {"bowl": "bowl game", "conf_title": "league title", "cfp": "playoff", "title": "national title"}
MONEY_WEIGHT = {"mercenary": 1.8, "climber": 1.3, "journeyman": 1.3, "blue_blood": 1.2, "survivor": 1.1,
                "loyalist": 0.5, "homebody": 0.7, "alma_mater": 0.6, "lifer": 0.8}
ASK_TILT = {"mercenary": 1.15, "blue_blood": 1.08, "climber": 1.05, "loyalist": 0.95, "homebody": 0.97}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def money(x, exact=False):
    """$9.5M, $850K, $45K. `exact` keeps a second decimal on millions ($1.98M) so
    a contract's pieces add up on screen."""
    x = int(round(x or 0))
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= M:
        if exact and x < 100 * M:
            return f"{sign}${x / M:.2f}M"          # always two places: $7.40M next to $5.58M
        return f"{sign}${x / M:.1f}M" if x < 100 * M else f"{sign}${x / M:.0f}M"
    if x >= 1000:
        return f"{sign}${x / 1000:.0f}K"
    return f"{sign}${x}"


def parse_money(text):
    """'250' / '250k' / '$1.2M' / '1,200,000' → dollars. Bare small numbers are thousands."""
    s = str(text).strip().lower().replace("$", "").replace(",", "")
    mult = 1
    if s.endswith("m"):
        mult, s = M, s[:-1]
    elif s.endswith("k"):
        mult, s = 1000, s[:-1]
    try:
        v = float(s)
    except ValueError:
        return None
    if mult == 1 and v < 10_000:
        mult = 1000
    return int(round(v * mult))


def _round(x, step=5_000):
    return int(round(x / step) * step)


# ═══ Budgets ════════════════════════════════════════════════════════════════

def budget_for_prestige(prestige, conference=None, school=""):
    """What a program this big spends on football a year."""
    power = conference in POWER_CONFS or school == world.FLAGSHIP_INDEPENDENT or (conference is None and prestige >= 66)
    if power:
        base = 20 + (prestige - 65) * 0.9
        if conference in world.BIG_TWO or school == world.FLAGSHIP_INDEPENDENT:
            base += 5
    else:
        base = 4 + max(0, prestige - 43) * 0.28 + (1 if conference == world.WEST_COAST_CONF else 0)
    return max(3.0, base) * M


def budget(team):
    """The program's annual football budget. Set once; it never moves."""
    b = getattr(team, "budget", None)
    if b is None:
        r = random.Random(f"budget:{team.school}")
        b = budget_for_prestige(team.prestige, team.conference, team.school) * r.uniform(0.93, 1.07)
        b = team.budget = int(round(b / 100_000) * 100_000)
    return b


def budget_rank(league, team):
    order = sorted(league.teams, key=lambda t: -budget(t))
    return order.index(team) + 1


# ═══ Contracts ══════════════════════════════════════════════════════════════

def contract(coach):
    return getattr(coach, "contract", None) if coach is not None else None


def salary(coach):
    k = contract(coach)
    return k["salary"] if k else 0


def total_value(offer):
    """Guaranteed money over the whole deal, escalator included (rounded, not cut)."""
    r = offer.get("raise", 0.0)
    return int(round(sum(offer["salary"] * (1 + r) ** i for i in range(offer["years"]))))


def terms(offer, total=True):
    """An offer on the table: its first-year salary, so raises read "to start"."""
    y = offer["years"]
    s = f"{y} yr{'s' if y != 1 else ''} · {money(offer['salary'], exact=True)}/yr"
    if offer.get("raise") and y > 1:
        s += " to start"
    return s + (f" · {money(total_value(offer), exact=True)} total" if total else "")


def salary_year(league):
    """The season a signed contract's "salary" is paying: raises land when a season's checks are cut."""
    return league.year + (1 if getattr(league, "season_complete", False) else 0)


def years_left(k, league):
    return max(0, k["end"] - salary_year(league) + 1)


def start_salary(k, league):
    """What a deal paid in its first year (the stored salary has had raises since)."""
    r = k.get("raise", 0.0) or 0.0
    done = max(0, min(salary_year(league), k["end"]) - k.get("start", salary_year(league)))
    return k["salary"] / (1 + r) ** done


def deal_total(k, league):
    """Every dollar of a signed deal, first year to last, raises included."""
    r = k.get("raise", 0.0) or 0.0
    return int(round(sum(start_salary(k, league) * (1 + r) ** i for i in range(k["years"]))))


def deal_line(k, league, pay=True):
    """A signed deal, one way everywhere: "4-yr deal (2025–28) · 3 yrs left · $5.80M/yr".
    The salary is always what he's paid this season."""
    y = k["years"]
    left = years_left(k, league)
    span = f"{k['start']}" if k["start"] == k["end"] else f"{k['start']}–{str(k['end'])[-2:]}"
    s = f"{y}-yr deal ({span}) · "
    s += f"{left} yr{'s' if left != 1 else ''} left" if left else "final year"
    if pay:
        s += f" · {money(k['salary'], exact=True)}/yr"
    return s


def clause_lines(offer, coach=None, league=None):
    """Everything past the salary and years, in words. With a coach and the league,
    the buyout and release lines carry what they'd cost right now."""
    out = []
    live = coach is not None and league is not None and contract(coach) is offer
    if offer.get("raise"):
        out.append(f"{offer['raise'] * 100:.0f}% raise each year")
    line = f"buyout {offer.get('buyout', 0.6) * 100:.0f}% of what's left if fired"
    if live:
        line += f" (now {money(owed(coach, league), exact=True)})"
    out.append(line + (" · offset: his next job's pay comes off it" if offer.get("offset") else " · offset: none"))
    if offer.get("release"):
        line = f"release: leaving early costs {offer['release'] * 100:.0f}% of salary per year left (max 3)"
        if live:
            line += f" — {money(release_fee(coach, league), exact=True)} right now"
        out.append(line)
    b = offer.get("bonuses") or {}
    if b:
        out.append("bonuses: " + ", ".join(f"{BONUS_LABELS[k]} {money(v)}" for k, v in b.items()))
    out.append("rollover: every 8-win season adds a year" if offer.get("rollover") else "rollover: none")
    return out


def _clauses(team, offer, rng, role="HC"):
    """Fill in the rest of the deal the way this AD writes them."""
    cl = CLAUSES.get(getattr(team, "ad", {}).get("style", "conference"), CLAUSES["conference"])
    offer["raise"] = round(cl["raise_"] + rng.choice((-0.01, 0, 0, 0.01)), 3) if cl["raise_"] else 0.0
    offer["raise"] = max(0.0, offer["raise"])
    offer["offset"] = rng.random() < cl["offset"]
    if role == "HC":
        offer["release"] = round(cl["release"] * rng.uniform(0.8, 1.2), 2)
        pool = offer["salary"] * cl["incent"]
        offer["bonuses"] = {k: _round(pool * v, 5_000) for k, v in BONUS_SPLIT.items() if pool * v >= 5_000}
        offer["rollover"] = rng.random() < cl["rollover"]
    else:
        offer["release"] = 0.25
        offer["bonuses"] = {}
        offer["rollover"] = False
    return offer


def _ad(team):
    style = getattr(team, "ad", {}).get("style", "conference")
    return AD_CONTRACT.get(style, AD_CONTRACT["conference"])


def hc_quality(coach, league, level):
    """How a coach stacks up against a job of this size: ratings, results, rings."""
    import carousel as cz
    import resume
    q = 1 + (resume.reputation(coach, league) - level) / 40         # paid on his résumé, like everybody
    if coach.history:
        q += cz.track_record(coach, league) * 1.2
        q += min(0.25, sum(s.get("title", 0) * 0.12 + s.get("cfp", 0) * 0.04 for s in coach.history[-5:]))
    return clamp(q, 0.6, 1.45)


def coord_quality(coach, level):
    import staff
    q = 1 + (staff.resume_prior(coach) - (level - 9)) / 40 + staff.resume_score(coach) * 0.012
    return clamp(q, 0.6, 1.5)


def hc_offer(league, team, coach, rng=None, extension=False):
    """What this school's AD offers this coach to be its head coach."""
    rng = rng or random.Random(f"hc:{team.school}:{coach.name}:{league.year}")
    ad = _ad(team)
    b = budget(team)
    q = hc_quality(coach, league, team.prestige)
    first_time = not coach.history and not extension
    rep = None
    if first_time and getattr(coach, "is_user", False):
        import coach_prestige
        rep = coach_prestige.level(coach)                  # your name when you walk in (Coach Career)
    if first_time:
        q *= rep["pay"] if rep else 0.88                   # a first-time head coach
    pay = HC_SHARE * b * q * ad["money"] * rng.uniform(0.94, 1.06)
    years = ad["years"] + rng.choice((-1, 0, 0, 1))
    if extension:
        seat = getattr(coach, "seat", 30)
        if seat >= 50:
            years, pay = min(years, 2), pay * 0.95           # a show-me extension
        elif seat <= 20:
            pay *= 1.06                                      # the AD wants to keep him
        pay = max(pay, salary(coach) * (1.0 if seat >= 50 else 1.04))
    if q >= 1.2:
        years += 1
    if coach.age >= 60:
        years -= 1
    if coach.age >= 66:
        years -= 1
    if coach.team is None and coach.history and not extension:
        years = min(years, 5)                                # a coach coming off a firing proves it first
    if not coach.history:
        years = min(years, 6)                                # nobody gives a first-timer eight years
        cap = rep["cap"] if rep else 0.75
        if cap is not None:
            pay = min(pay, HC_SHARE * b * cap)               # ...or top-of-market money (unless he's a big name)
    offer = {"salary": _round(min(pay, HC_CAP * b), 25_000), "years": int(clamp(years, 2, 8)),
             "buyout": ad["buyout"], "role": "HC"}
    return _clauses(team, offer, rng)


def coord_offer(league, team, coach, role, rng=None):
    rng = rng or random.Random(f"co:{team.school}:{coach.name}:{league.year}")
    ad = _ad(team)
    b = budget(team)
    pay = COORD_SHARE * b * coord_quality(coach, team.prestige) * math.sqrt(ad["money"]) * rng.uniform(0.94, 1.06)
    years = rng.choice((2, 2, 3, 3, 3, 4))
    offer = {"salary": _round(min(pay, COORD_CAP * b), 5_000), "years": years,
             "buyout": ad["buyout"], "role": role}
    return _clauses(team, offer, rng, role=role)


def asking(league, coach, role="HC", target=None):
    """What a coach thinks he's worth for a job in this role."""
    import carousel as cz
    tilt = ASK_TILT.get(getattr(coach, "personality", ""), 1.0)
    if role == "HC":
        level = cz.level_of(coach, league)
        value = HC_SHARE * budget_for_prestige(level) * hc_quality(coach, league, level)
    else:
        if coach.team is not None:
            level = coach.team.prestige
        elif getattr(coach, "coord_history", None):
            level = cz.league_team_prestige(league, coach.coord_history[-1]["school"]) - 4
        elif coach.history:
            level = cz.level_of(coach, league) - 10
        else:
            level = (target.prestige if target is not None else 55) - 8
        value = COORD_SHARE * budget_for_prestige(level) * coord_quality(coach, level)
    cur = contract(coach)
    if coach.team is not None and cur is not None:
        value = max(value, cur["salary"] * 1.05)             # nobody moves for a pay cut
    elif coach.team is None:
        value *= 0.6 if coach.history else 0.8               # out of work: take what's there
    return value * tilt


def money_ratio(league, coach, offer, role="HC", target=None):
    ask = asking(league, coach, role, target)
    return offer["salary"] / ask if ask else 2.0


def money_weight(coach):
    return MONEY_WEIGHT.get(getattr(coach, "personality", ""), 1.0)


def sign(league, team, coach, offer, start=None):
    """Put a contract on the books. If schools that fired him wrote an offset
    clause, what this job pays comes off what they still owe him."""
    start = league.year + 1 if start is None else start
    coach.contract = {"school": team.school, "role": offer.get("role", "HC"), "salary": int(offer["salary"]),
                      "years": int(offer["years"]), "start": start, "end": start + int(offer["years"]) - 1,
                      "buyout": offer.get("buyout", 0.6), "signed": league.year,
                      "raise": offer.get("raise", 0.0), "offset": offer.get("offset", False),
                      "release": offer.get("release", 0.0), "bonuses": dict(offer.get("bonuses") or {}),
                      "rollover": offer.get("rollover", False)}
    for t in league.teams:
        for b in getattr(t, "buyouts", []):
            if b.get("coach") is coach and b.get("offset") and b["start"] >= start and not b.get("offset_by"):
                cut = min(b["per_year"], int(offer["salary"]))
                if cut > 0:
                    b["per_year"] -= cut
                    b["offset_by"] = team.school
                    _books(t, league.year).append((f"offset: {coach.name}'s new job at {team.school} cuts his "
                                                   f"buyout by {money(cut)}/yr", 0))
    return coach.contract


def remaining_pay(k, league, team=None):
    """[(year, dollars)] still unpaid on a deal, raises included. Before the season
    this year counts in full; during it, only the games left; once the season's
    checks are cut (the offseason) it starts with next year."""
    if not k:
        return []
    done = getattr(league, "season_complete", False)
    first = max(k.get("start", league.year), league.year + (1 if done else 0))
    r = k.get("raise", 0.0) or 0.0
    out = []
    for i, y in enumerate(range(first, k["end"] + 1)):
        pay = k["salary"] * (1 + r) ** i
        if y == league.year and _in_season(league) and team is not None:
            pay *= 1 - min(1.0, (team.wins + team.losses) / 12)
        out.append((y, int(round(pay))))
    return out


def release_fee(coach, league):
    """What leaving early costs: his release clause on the years he's walking out on (max 3)."""
    k = contract(coach)
    if not k or not k.get("release"):
        return 0
    years = remaining_pay(k, league)[:3]
    return int(round(sum(p for _, p in years) * k["release"]))


def charge_release(league, old, new, coach):
    """A sitting coach leaves early: his new school pays his old one the release fee."""
    fee = release_fee(coach, league)
    if not fee or old is None or new is None:
        return 0
    y = league.year + 1
    new.__dict__.setdefault("buyouts", []).append(
        {"name": f"release fee for {coach.name} (to {old.school})", "role": "fee", "per_year": fee,
         "start": y, "end": y, "kind": "release"})
    old.__dict__.setdefault("income", []).append(
        {"what": f"release fee from {new.school} for {coach.name}", "amount": fee, "year": y})
    return fee


def income_in(team, year):
    return sum(i["amount"] for i in getattr(team, "income", []) if i["year"] == year)


def _books(team, year):
    """One-off lines on a season's books (paid a fired coach for the weeks he coached, bonuses...)."""
    return team.__dict__.setdefault("books", {}).setdefault(year, [])


def owed(coach, league):
    """What firing him right now would cost the school, in total."""
    k = contract(coach)
    if not k:
        return 0
    team = getattr(coach, "team", None)
    return int(round(sum(p for _, p in remaining_pay(k, league, team)) * k["buyout"]))


def _in_season(league):
    return 1 <= getattr(league, "week", 0) and not getattr(league, "season_complete", True)


def release(league, team, coach, fired=False):
    """A coach leaves the job. Fired with years left, the school keeps paying —
    a share of his salary every year the deal had left, paid year by year
    (and cut by an offset clause if he lands a new job). Fired during the
    season, he's paid for the weeks he coached and the buyout covers the rest
    of this year too."""
    k = contract(coach)
    if k is None:
        return
    if fired and team is not None:
        entries = team.__dict__.setdefault("buyouts", [])
        role = k.get("role", "HC")
        if _in_season(league):
            games = team.wins + team.losses
            share = min(1.0, games / 12)
            worked = int(k["salary"] * share)
            credit(coach, worked)
            _books(team, league.year).append((f"paid {coach.name} for the {games} games he coached", worked))
        # The same years, at the same raises, that owed() quoted: one check a year.
        for y, pay in remaining_pay(k, league, team):
            per = int(round(pay * k["buyout"]))
            if per > 0:
                entries.append({"name": coach.name, "role": role, "per_year": per, "start": y, "end": y,
                                "coach": coach, "offset": k.get("offset", False) and y > league.year})
    coach.contract = None


def buyouts_in(team, year):
    return sum(b["per_year"] for b in getattr(team, "buyouts", []) if b["start"] <= year <= b["end"])


def active_buyouts(team, year):
    return [b for b in getattr(team, "buyouts", []) if b["end"] >= year]


def _legacy(league, team, coach, role, rng):
    """A contract for a coach who's been in the job since before money was tracked."""
    offer = hc_offer(league, team, coach, rng) if role == "HC" else coord_offer(league, team, coach, role, rng)
    since = (coach.hired_year if role == "HC" else getattr(coach, "coord_since", None)) or league.year
    end = since + offer["years"] - 1
    while end < league.year:
        end += offer["years"]
    k = sign(league, team, coach, offer, start=end - offer["years"] + 1)
    # He's been on this deal a while: the salary on the books is this season's, raises and all.
    k["salary"] = int(round(k["salary"] * (1 + (k.get("raise") or 0.0)) ** max(0, league.year - k["start"])))
    k["current_pay"] = True


def _seed_roster_nil(league):
    """The players already on campus get the deals they'd have signed: most of the
    pool, split by what each was worth coming out of high school and what he's become."""
    for team in league.teams:
        room = nil_pool(league, team) * 0.9
        r = random.Random(f"seednil:{team.school}:{league.year}")
        paid = [p for p in team.roster if not getattr(p, "walk_on", False) and p.hs_stars >= 2]
        w = {p: market(p.hs_stars) * (0.6 + max(0, p.overall - 55) / 40) * r.uniform(0.7, 1.2) for p in paid}
        tot = sum(w.values()) or 1
        for p in paid:
            p.nil = _round(room * w[p] / tot)


def ensure_all(league):
    """Budgets for every program, contracts for everyone on a staff (new worlds and older saves)."""
    if not league.__dict__.get("_nil_seeded"):
        if not any(player_nil(p) for t in league.teams for p in t.roster):
            _contracts(league)
            _seed_roster_nil(league)
        league._nil_seeded = True
    _contracts(league)


def _contracts(league):
    for team in league.teams:
        budget(team)
        team.__dict__.setdefault("buyouts", [])
        for role, c in (("HC", team.coach), ("OC", getattr(team, "oc", None)), ("DC", getattr(team, "dc", None))):
            if c is None:
                continue
            c.__dict__.setdefault("career_earnings", 0)
            k = contract(c)
            if k is None or k.get("school") != team.school or k.get("role", "HC") != role:
                _legacy(league, team, c, role, random.Random(f"legacy:{team.school}:{c.name}:{role}"))
            elif not k.get("current_pay") and k.get("start", league.year) <= k.get("signed", 0):
                # Older saves: a deal already running when the world began stored its
                # first-year salary. Bring it up to this season's pay.
                k["salary"] = int(round(k["salary"] * (1 + (k.get("raise") or 0.0))
                                        ** max(0, k["signed"] - k["start"])))
                k["current_pay"] = True
            if k is not None and k.get("school") == team.school and "bonuses" not in k:   # before the fine print existed
                extra = _clauses(team, dict(k), random.Random(f"clauses:{team.school}:{c.name}"), role=role)
                for key in ("raise", "offset", "release", "bonuses", "rollover"):
                    k[key] = extra[key]


def credit(coach, amount, bank=True):
    """Money in a coach's pocket. What you earn on the job (salary, bonuses) also
    goes into the bank you develop with; buyout checks don't."""
    coach.career_earnings = getattr(coach, "career_earnings", 0) + int(amount)
    if bank and getattr(coach, "is_user", False):
        coach.bank = getattr(coach, "bank", 0) + int(amount)


def pay_season(league):
    """The season's paychecks (once per person — an interim is still paid as a
    coordinator), this year's buyout checks to the coaches who get them, then
    next year's raises and old buyouts off the books."""
    for team in league.teams:
        seen = set()
        for c in (team.coach, getattr(team, "oc", None), getattr(team, "dc", None)):
            if c is not None and id(c) not in seen:
                seen.add(id(c))
                credit(c, salary(c))
        for b in getattr(team, "buyouts", []):
            if b["start"] <= league.year <= b["end"] and b.get("coach") is not None and b["per_year"] > 0:
                credit(b["coach"], b["per_year"], bank=False)
        team.buyouts = [b for b in getattr(team, "buyouts", []) if b["end"] > league.year]
        team.income = [i for i in getattr(team, "income", []) if i["year"] > league.year]
    for team in league.teams:
        for c in (team.coach, getattr(team, "oc", None), getattr(team, "dc", None)):
            k = contract(c)
            if k and k.get("raise") and k["end"] > league.year and k["start"] <= league.year:
                k["salary"] = int(k["salary"] * (1 + k["raise"]))       # next year's escalator
            if k and k.get("_restore"):                                  # a one-year deferral is over
                k["salary"] += sum(a for y, a in k["_restore"] if y <= league.year)
                k["_restore"] = [(y, a) for y, a in k["_restore"] if y > league.year]
        for p in team.roster:
            back = p.__dict__.get("_nil_restore")
            if back:
                p.nil = (p.nil or 0) + sum(a for y, a in back if y <= league.year)
                p._nil_restore = [(y, a) for y, a in back if y > league.year]


def season_clauses(league, team, coach, s):
    """After the verdict: bonuses for what the season earned, and the rollover clause."""
    k = contract(coach)
    if not k:
        return []
    got = []
    b = k.get("bonuses") or {}
    earned = {"bowl": s.get("bowl") or s.get("cfp"), "conf_title": s.get("conf_champ"), "cfp": s.get("cfp"),
              "title": s.get("title")}
    total = 0
    for key, amt in b.items():
        if earned.get(key):
            total += amt
            got.append(BONUS_LABELS[key])
    if total:
        credit(coach, total)
        _books(team, league.year).append((f"bonuses to {coach.name}: {', '.join(got)}", total))
    if k.get("rollover") and s["w"] >= 8 and k["end"] - league.year < 6:
        k["end"] += 1
        k["years"] += 1
        got.append("rollover year")
    return got


# ═══ What the program spends ════════════════════════════════════════════════

def staff_cost(team):
    b = budget(team)
    coords = [getattr(team, "oc", None), getattr(team, "dc", None)]
    if team.coach is not None and any(team.coach is c for c in coords):
        hc = HC_SHARE * b                              # an interim: already paid as a coordinator; budget the real hire
    else:
        hc = salary(team.coach) if contract(team.coach) else HC_SHARE * b
    total = hc
    for c in coords:
        total += salary(c) if contract(c) else COORD_SHARE * b
    import poscoach
    total += poscoach.payroll_delta(team)              # position coaches above (or below) a standard room
    return int(total)


def player_nil(p):
    return getattr(p, "nil", 0) or 0


def roster_nil(team, returning=False):
    """NIL on the roster — all of it, or just what comes back next season."""
    return sum(player_nil(p) for p in team.roster if not (returning and p.year >= 3))


def nil_pool(league, team):
    """Everything the budget has left for players next season, before anyone's paid."""
    import facilities
    pool = (budget(team) * (1 - OPS_SHARE) - staff_cost(team) - buyouts_in(team, league.year + 1)
            + income_in(team, league.year + 1) - facilities.spend_in(team, league.year + 1))
    import skills
    if skills.team_has(team, "collective"):
        pool += budget(team) * (1 - OPS_SHARE) * 0.05   # Collective Ties (coaching tree)
    import compliance
    m = compliance.nil_mult(league, team)
    if m < 1.0:
        pool -= budget(team) * (1 - OPS_SHARE) * (1 - m)  # CAB booster/collective restrictions
    import difficulty
    k = difficulty.nil(team)
    if k != 1.0:
        pool += budget(team) * (1 - OPS_SHARE) * (k - 1)   # your difficulty: booster generosity
    return pool


# ── recruit offers ───────────────────────────────────────────────────────────

def _book(cycle):
    return cycle.__dict__.setdefault("nil", {})


def offers_by(cycle, team):
    return _book(cycle).get(team, {})


def offer_to(cycle, team, recruit):
    return _book(cycle).get(team, {}).get(recruit, 0)


def offers_for(cycle, recruit):
    """Every NIL offer this recruit holds, as {team: amount}."""
    book = _book(cycle)
    out = {}
    for t in recruit.interest:
        a = book.get(t, {}).get(recruit)
        if a:
            out[t] = a
    return out


def committed_nil(cycle, team):
    return sum(a for r, a in offers_by(cycle, team).items() if r.committed_to is team)


def open_nil(cycle, team):
    return sum(a for r, a in offers_by(cycle, team).items() if r.committed_to is not team and not r.signed)


def available(league, team, cycle=None):
    """What's left to offer recruits for next season."""
    cycle = cycle or league.recruiting
    # In the offseason, once the seniors are gone and everyone has moved up a
    # year, the whole roster is next season's roster.
    returning = not getattr(league, "nil_rolled", False)
    return int(nil_pool(league, team) - roster_nil(team, returning=returning)
               - committed_nil(cycle, team) - open_nil(cycle, team))


def class_target(league, team):
    """What the next class can be paid: the room the departing players leave (seniors,
    early draft picks), plus most of whatever the roster isn't using — a small cushion
    stays back for raises, buyouts and buildings."""
    returning = not getattr(league, "nil_rolled", False)
    room = nil_pool(league, team) - roster_nil(team, returning=returning)
    return max(0, room * CLASS_SHARE)


def market(stars):
    return NIL_MARKET.get(int(stars), 0)


def pay_scale(team):
    """Richer programs pay more for the same kid: a 4-star is worth more to a $50M budget."""
    return clamp((budget(team) / BUDGET_REF) ** 0.7, 0.45, 2.3)


def appetite(recruit):
    """How much money matters to him. Fixed for each kid."""
    r = random.Random(f"nil:{recruit.player.first_name}:{recruit.player.last_name}:{recruit.home_state}")
    tilt = {"showman": 1.35, "front_runner": 1.2, "homebody": 0.85, "loyal": 0.8,
            "family_first": 0.9}.get(recruit.personality, 1.0)
    return clamp(r.gauss(1.0, 0.3) * tilt, 0.25, 1.8)


def appetite_word(recruit):
    a = appetite(recruit)
    if a >= 1.25:
        return "Money matters a lot to him"
    if a >= 0.9:
        return "Money is part of the conversation"
    if a >= 0.6:
        return "Money isn't his first question"
    return "Barely talks about money"


def pull(cycle, team, recruit):
    """How much louder this program's NIL makes it in his ear (interest points)."""
    amt = offer_to(cycle, team, recruit)
    if not amt:
        return 0.0
    mkt = max(5_000, market(recruit.stars))
    best = max(offers_for(cycle, recruit).values(), default=amt)
    rel = amt / best if best else 1.0
    return appetite(recruit) * 10 * min(1.6, math.sqrt(amt / mkt)) * (0.35 + 0.65 * rel)


def _nudge(cycle, team, recruit, pts):
    from recruiting_data import OFFER_CEILING
    cur = recruit.interest.get(team, 0.0)
    if pts > 0:
        cur += pts * (1 - cur / 120)
    else:
        cur += pts
    cur = clamp(cur, 0, 100)
    if team not in recruit.offers:
        cur = min(cur, OFFER_CEILING)
    recruit.interest[team] = cur


@capture.hook("rec", "acts", capture.b_nil)
def make_offer(cycle, team, recruit, amount):
    """Put NIL money on the table (or change it). Returns (ok, message)."""
    amount = int(amount)
    if recruit.signed:
        return False, f"{recruit.name} has already signed."
    if team not in recruit.offers:
        return False, "Offer him a scholarship first — NIL money goes on top of an offer."
    if recruit.committed_to is not None and recruit.committed_to is not team:
        return False, f"He's committed to {recruit.committed_to.school}. Flip him first."
    before = offer_to(cycle, team, recruit)
    if amount <= 0:
        return withdraw(cycle, team, recruit)
    if amount - before > available(cycle.league, team, cycle):
        return False, f"You only have {money(available(cycle.league, team, cycle))} left to offer."
    old_pull = pull(cycle, team, recruit)
    _book(cycle).setdefault(team, {})[recruit] = amount
    gain = pull(cycle, team, recruit) - old_pull
    if gain > 0:
        _nudge(cycle, team, recruit, gain * 0.6)
    elif gain < 0:
        _nudge(cycle, team, recruit, gain * 0.5)
    if recruit not in cycle.by_team[team]:
        cycle.by_team[team].append(recruit)
    verb = "raised to" if before and amount > before else "cut to" if before else "offered"
    return True, f"NIL {verb} {money(amount)}/yr — {recruit.name}."


@capture.hook("rec", "acts", capture.b_withdraw)
def withdraw(cycle, team, recruit):
    if not offer_to(cycle, team, recruit):
        return False, "You don't have a NIL offer out to him."
    p = pull(cycle, team, recruit)
    del _book(cycle)[team][recruit]
    _nudge(cycle, team, recruit, -p * 0.5)                   # money talks, and it walks
    return True, f"NIL offer to {recruit.name} withdrawn."


def weekly(cycle):
    """Once a week: dead offers come off the books, live ones keep talking."""
    book = _book(cycle)
    for team, offers in book.items():
        for r in list(offers):
            if r.signed and r.committed_to is not team:
                del offers[r]
            elif r.committed_to is not None and r.committed_to is not team:
                del offers[r]                                # he picked somebody else; the money's free
    for team, offers in book.items():
        for r, amt in offers.items():
            if not r.signed:
                _nudge(cycle, team, r, pull(cycle, team, r) * 0.12)


def ai_nil(cycle, team, board):
    """An AI staff puts money behind the recruits it wants and has a shot at."""
    league = cycle.league
    avail = available(league, team, cycle)
    spent = committed_nil(cycle, team) + open_nil(cycle, team)
    room = min(avail, class_target(league, team) - spent)
    if room < 25_000:
        return
    mult = _ad(team)["nil"]
    mine = offers_by(cycle, team)
    cands = [r for r in board if not r.signed and team in r.offers and r not in mine
             and r.committed_to in (None, team) and r.interest.get(team, 0) >= 15]
    cands.sort(key=lambda r: (-r.stars, -r.interest.get(team, 0)))
    made = 0
    per_week = AI_NIL_PER_WEEK * (3 if getattr(cycle, "compressed", False) else 1)
    for r in cands:
        if made >= per_week or room < 15_000:
            break
        amt = market(r.stars) * mult * pay_scale(team) * cycle.rng.uniform(0.75, 1.3)
        if r.committed_to is team:
            amt *= 0.85
        amt = _round(amt)
        if amt > room:
            if room < market(r.stars) * pay_scale(team) * 0.5:
                continue
            amt = _round(room)
        if amt <= 0:
            continue
        ok, _ = make_offer(cycle, team, r, amt)
        if ok:
            room -= amt
            made += 1


# ═══ Renewals ═══════════════════════════════════════════════════════════════

EXTEND_TEMPER = {"booster": 1.3, "brand": 1.2, "big_game": 1.15, "politician": 1.1, "win_now": 0.9, "patient": 1.1,
                 "traditionalist": 1.1, "conference": 1.0, "turnaround": 1.0, "recruiting": 1.0, "analytics": 0.85,
                 "budget": 0.6}


def extension_case(league, team, coach):
    """Why this AD would redo his coach's deal now, or None.
    - the deal is running short and the coach is doing the job
    - a big season (title, playoff, league title, or 2+ wins over what he should have won)
    - bigger programs are going to come calling"""
    import carousel as cz
    k = contract(coach)
    if k is None or not coach.history or coach.history[-1]["school"] != team.school:
        return None
    left = k["end"] - league.year                       # seasons still on the deal after this one
    s = coach.history[-1]
    seat = getattr(coach, "seat", 50)
    if left <= 0:
        return "expiring"
    if seat > 35:
        return None
    gap = s["w"] - s.get("xw", s["w"])
    if s.get("title"):
        return "after winning the national title"
    if (s.get("cfp") or s.get("conf_champ") or gap >= 2.5) and left <= 3:
        return "after a big season"
    if left <= 1 and seat <= 25:
        return "before the deal gets short"
    if cz.track_record(coach, league) >= 0.12 and left <= 3 and any(
            t.prestige >= team.prestige + 8 and (t.coach is None or getattr(t.coach, "seat", 0) >= 60)
            for t in league.teams):
        return "to keep bigger programs away"
    return None


def extend(league, team, coach, rng, reason, offer=None, news=True):
    import carousel as cz
    offer = offer or hc_offer(league, team, coach, rng, extension=True)
    old = contract(coach)
    if old:
        offer["salary"] = max(offer["salary"], int(old["salary"] * (1.0 if reason == "expiring" else 1.05)))
        offer["years"] = max(offer["years"], old["end"] - league.year + 1)   # an extension adds years
        offer["salary"] = _round(min(offer["salary"], HC_CAP * budget(team)), 25_000)
    sign(league, team, coach, offer, start=league.year + 1)
    coach._retained = league.year                       # he just signed: off the market this winter
    if news and reason != "expiring":
        cz._news(league, "extended", f"{team.school} extends {coach.name} through {coach.contract['end']} "
                                     f"({terms(offer, total=False)}) {reason}")
    return offer


def renewals(league, rng, phase="all"):
    """phase "expiring" (after the firings, before the market): expiring deals are
    redone, and your own offer comes to you. phase "early" (after the market has
    settled): coaches still doing the job get extended early — after a big season,
    when the deal is getting short, or to keep a bigger school away. Nobody is
    extended and then hired away the same winter. Your coordinators' deals are
    yours to redo in the staff review."""
    import carousel as cz
    import staff
    import ad_mode
    for team in league.teams:
        c = team.coach
        if c is None or contract(c) is None or cz.is_interim(c):
            continue
        if ad_mode.is_mine(league, team):
            continue                                    # you extend (or don't) on the report card
        if phase == "early" and (getattr(c, "is_user", False) or team.coach_changed
                                 or c.hired_year == league.year + 1 or getattr(c, "_retained", None) == league.year):
            continue                                    # new this winter, already re-signed, or yours (done earlier)
        reason = extension_case(league, team, c)
        if phase == "expiring" and not getattr(c, "is_user", False) and reason != "expiring":
            continue                                    # early extensions wait for the market to settle
        if phase == "early" and reason == "expiring":
            continue
        if getattr(c, "commish_member", None) and getattr(league, "mode", None) == "commissioner":
            if phase == "early" or reason == "expiring" or contract(c)["end"] <= league.year or reason is not None:
                import job_market
                job_market.member_contract(league, team, c, rng, contract(c)["end"] <= league.year, reason)
            continue
        if getattr(c, "is_user", False):
            import hotseat
            k = contract(c)
            expiring = k["end"] <= league.year
            with hotseat.acting_as_coach(league, c):
                if expiring and c.seat >= cz.fire_line(team) - 12:
                    _user_not_renewed(league, team, c)
                elif reason is not None or (not expiring and k["end"] == league.year + 1 and c.seat <= 35):
                    hotseat.maybe_pass(league, "YOUR AD WANTS TO TALK CONTRACT")
                    _user_extension(league, team, c, rng, expiring, reason)
            continue
        if reason is None:
            continue
        base = {"expiring": 1.0, "after winning the national title": 1.0, "after a big season": 0.5,
                "to keep bigger programs away": 0.45, "before the deal gets short": 0.4}.get(reason, 0.4)
        odds = min(0.95, base * (1.0 if base >= 1 else EXTEND_TEMPER.get(team.ad["style"], 1.0)))
        if rng.random() < odds:
            extend(league, team, c, rng, reason)
    if phase == "early":
        return
    mine = staff.user_team(league)
    import hotseat
    mines = hotseat.humans(league) if hotseat.state(league) is not None else ([mine] if mine is not None else [])
    for team in league.teams:
        if any(team is m for m in mines):
            continue
        for role, attr in (("OC", "oc"), ("DC", "dc")):
            c = getattr(team, attr, None)
            k = contract(c)
            if c is not None and k is not None and k["end"] <= league.year:
                offer = coord_offer(league, team, c, role, rng)
                offer["salary"] = max(offer["salary"], int(k["salary"] * 1.03))
                sign(league, team, c, offer, start=league.year + 1)


def retention_counter(league, coach, offer, rng):
    """Another school is about to hire a sitting coach. If his AD wants to keep
    him, he matches most of the money; some coaches stay. Returns True if he stays."""
    import carousel as cz
    team = coach.team
    if team is None or getattr(coach, "is_user", False) or getattr(coach, "role", "HC") != "HC":
        return False
    if getattr(coach, "seat", 50) > 30 or team.ad.get("style") == "budget":
        return False
    match = _round(min(offer["salary"] * rng.uniform(0.85, 1.0), HC_CAP * budget(team)), 25_000)
    if match <= salary(coach):
        return False
    stay = {"loyalist": 0.7, "homebody": 0.6, "alma_mater": 0.75, "lifer": 0.55, "builder": 0.35,
            "fixer": 0.3, "survivor": 0.4, "climber": 0.15, "blue_blood": 0.1, "journeyman": 0.1,
            "mercenary": 0.0, "short_timer": 0.35}.get(getattr(coach, "personality", ""), 0.3)
    if getattr(coach, "personality", "") == "mercenary" and match >= offer["salary"]:
        stay = 0.8                                            # it was always about the money
    if rng.random() >= stay:
        return False
    years = _ad(team)["years"]
    extend(league, team, coach, rng, "", {"salary": match, "years": years, "buyout": _ad(team)["buyout"],
                                          "role": "HC"}, news=False)
    coach._retained = league.year                              # he's staying: off the market this winter
    cz._news(league, "extended", f"{coach.name} stays at {team.school} — a raise to {money(match)}/yr "
                                 f"through {coach.contract['end']} after another school came calling")
    return True


def _user_not_renewed(league, team, coach):
    import carousel as cz
    league.__dict__.setdefault("career_log", []).append((league.year, f"{team.school} didn't renew your contract."))
    cz._news(league, "fired", f"{team.school} lets {coach.name}'s contract run out — no buyout")
    cz.vacate(league, team, "fired")
    if league.career_log and league.career_log[-1][1] == f"Fired by {team.school}.":
        league.career_log.pop()                          # not fired — just not renewed


def _user_extension(league, team, coach, rng, expiring, reason=None):
    import career
    import carousel as cz
    offer = hc_offer(league, team, coach, rng, extension=True)
    old = contract(coach)
    if old and not expiring:
        offer["salary"] = _round(min(max(offer["salary"], old["salary"] * 1.05), HC_CAP * budget(team)), 25_000)
        offer["years"] = min(8, max(offer["years"], old["end"] - league.year + 2))   # at least a year past the old deal
    answer = career.extension_prompt(league, team, offer, expiring, reason)
    if answer == "pulled":
        league.__dict__.setdefault("career_log", []).append((league.year, f"Pushed too hard in contract talks at {team.school} — "
                                               f"the AD walked away."))
        if expiring:
            _user_not_renewed(league, team, coach)
        return
    if answer is not None:
        sign(league, team, coach, answer, start=league.year + 1)
        coach.seat = min(100, coach.seat + int(answer.get("pressure", 0)))
        coach.seat_start = coach.seat
        league.__dict__.setdefault("career_log", []).append((league.year, f"Signed a new deal with {team.school}: {terms(answer)}."))
    elif expiring:
        league.__dict__.setdefault("career_log", []).append((league.year, f"Let your contract at {team.school} run out."))
        league._user_walked = True
        cz._news(league, "retired", f"{coach.name} and {team.school} part ways as his contract runs out")
        cz.vacate(league, team, "left")


# ═══ Negotiating (you) ══════════════════════════════════════════════════════

GIVE_MONEY = {"booster": .85, "brand": .75, "big_game": .7, "politician": .65, "win_now": .6, "conference": .5,
              "patient": .45, "turnaround": .45, "traditionalist": .4, "analytics": .35, "recruiting": .3,
              "budget": .15}
GIVE_YEARS = {"patient": .8, "traditionalist": .8, "booster": .75, "brand": .6, "conference": .5, "turnaround": .5,
              "recruiting": .5, "big_game": .45, "analytics": .35, "politician": .35, "win_now": .2, "budget": .15}


def leverage(league, coach, n_offers=1):
    """Other offers and a winning record make an AD listen."""
    import carousel as cz
    lev = 0.07 * max(0, n_offers - 1)
    if coach.history:
        lev += max(0.0, cz.track_record(coach, league)) * 0.6
    elif getattr(coach, "is_user", False):
        import coach_prestige
        lev += coach_prestige.level(coach)["leverage"]      # a big name gets heard before he's coached a game
    return clamp(lev, 0.0, 0.3)


# How long an AD will keep talking before he gets annoyed, and how likely he is
# to walk away from the table at any point.
PATIENCE = {"booster": 3, "patient": 3, "traditionalist": 2, "brand": 2, "big_game": 2, "conference": 2,
            "turnaround": 2, "recruiting": 2, "analytics": 2, "win_now": 1, "politician": 1, "budget": 1}
PULL = {"win_now": .10, "budget": .10, "politician": .09, "analytics": .07, "booster": .03, "patient": .04}
GIVE_GUARANTEE = {"patient": .7, "traditionalist": .65, "booster": .7, "brand": .55, "conference": .45,
                  "turnaround": .45, "recruiting": .45, "big_game": .45, "analytics": .25, "politician": .35,
                  "win_now": .25, "budget": .1}
GIVE_RELEASE = {"budget": .6, "analytics": .55, "win_now": .5, "politician": .45, "conference": .45,
                "turnaround": .45, "recruiting": .4, "big_game": .35, "brand": .3, "booster": .3,
                "traditionalist": .25, "patient": .25}

# ask -> (label, how aggressive it is, seat pressure if he gives it)
ASKS = {
    "money10":    ("10% more money", 0.05, 3),
    "money20":    ("20% more money", 0.15, 6),
    "years":      ("more years", 0.05, 2),
    "guarantee":  ("a bigger buyout guarantee", 0.08, 3),
    "release":    ("a smaller release clause", 0.08, 2),
    "offset":     ("no offset clause", 0.06, 2),
    "incentives": ("less base, bigger bonuses", 0.0, -3),
}


def patience(team):
    return PATIENCE.get(getattr(team, "ad", {}).get("style", "conference"), 2)


def patience_word(team):
    return {1: "short", 2: "normal", 3: "long"}[patience(team)]


def counter(league, team, offer, want, rng, lev=0.0, extension=False):
    """You ask for something. The AD gives it, meets you halfway, says no — or
    gets up from the table. Every ask after his patience runs out makes that
    likelier, and every concession he does make is remembered: your seat
    starts warmer by the pressure you put on him.
    Returns (offer now on the table, outcome, what he says). Outcomes:
    "granted", "half", "refused", "pulled"."""
    style = getattr(team, "ad", {}).get("style", "conference")
    label, aggr, pressure = ASKS[want]
    new = dict(offer, negotiated=True)
    new["bonuses"] = dict(offer.get("bonuses") or {})
    n = offer.get("counters", 0)
    new["counters"] = n + 1
    over = max(0, n + 1 - patience(team))
    pull = clamp(PULL.get(style, .05) + aggr + 0.04 * n + 0.15 * over - 0.4 * lev, 0.0, 0.6)
    if want == "incentives":
        pull *= 0.3                                     # he likes this ask; he only walks if you've worn him out
    if rng.random() < pull:
        new["pulled"] = True
        walk = "tables the talks" if extension else "pulls the offer"
        return new, "pulled", f"doesn't like being squeezed — he {walk}"
    odds = {"money10": GIVE_MONEY.get(style, .5), "money20": GIVE_MONEY.get(style, .5) - 0.25,
            "years": GIVE_YEARS.get(style, .5), "guarantee": GIVE_GUARANTEE.get(style, .45),
            "release": GIVE_RELEASE.get(style, .4), "offset": 0.5 if style != "budget" else 0.1,
            "incentives": 0.95 if style in ("win_now", "budget", "analytics") else 0.8}[want]
    odds = clamp(odds + lev - 0.08 * n, 0.03, 0.97)
    roll = rng.random()
    cap = HC_CAP * budget(team)
    if want == "offset" and not offer.get("offset"):
        return new, "refused", "points out there's no offset clause in it"
    if roll < odds:
        outcome = "granted"
    elif want == "money20" and roll < odds + 0.25:
        outcome = "half"
    else:
        new["counters"] = n + 1
        return new, "refused", f"won't give you {label}"
    if want in ("money10", "money20"):
        bump = {"money10": 0.10, "money20": 0.20 if outcome == "granted" else 0.10}[want]
        new["salary"] = _round(min(offer["salary"] * (1 + bump), cap), 25_000)
        if new["salary"] <= offer["salary"]:
            return new, "refused", "is already at the most the budget allows"
        said = f"{'meets you halfway: ' if outcome == 'half' else ''}salary up to {money(new['salary'])}"
    elif want == "years":
        if offer["years"] >= 8:
            return new, "refused", "won't go past eight years"
        new["years"] = min(8, offer["years"] + rng.choice((1, 1, 2)))
        said = f"adds years — {new['years']} total"
    elif want == "guarantee":
        if offer.get("buyout", 0.6) >= 0.95:
            return new, "refused", "is already guaranteeing almost all of it"
        new["buyout"] = round(min(0.95, offer.get("buyout", 0.6) + 0.15), 2)
        said = f"guarantees {new['buyout'] * 100:.0f}% if he fires you"
    elif want == "release":
        new["release"] = round(offer.get("release", 0.4) * 0.5, 2)
        said = f"cuts your release clause to {new['release'] * 100:.0f}% a year"
    elif want == "offset":
        new["offset"] = False
        said = "drops the offset clause"
    else:  # incentives
        base = offer["salary"]
        new["salary"] = _round(base * 0.85, 25_000)
        pool = (base - new["salary"]) * 2.2 + sum(offer.get("bonuses", {}).values())
        new["bonuses"] = {k: _round(pool * v / sum(BONUS_SPLIT.values()) * 1.6, 5_000) for k, v in BONUS_SPLIT.items()}
        said = f"happily moves money into bonuses — base {money(new['salary'])}, bigger bonuses"
    new["pressure"] = offer.get("pressure", 0) + (pressure if outcome == "granted" else pressure // 2)
    return new, outcome, said


def nil_left_with(league, team, hc_salary):
    """What the budget would leave for players with this head coach salary —
    the same pool the budget screen shows (operations come off the top first)."""
    import facilities
    b = budget(team)
    coords = sum(salary(c) if contract(c) else COORD_SHARE * b
                 for c in (getattr(team, "oc", None), getattr(team, "dc", None)))
    import poscoach
    coords += poscoach.payroll_delta(team)
    return int(b * (1 - OPS_SHARE) - hc_salary - coords - buyouts_in(team, league.year + 1)
               + income_in(team, league.year + 1) - facilities.spend_in(team, league.year + 1))


def signing_day_deals(league, cycle, classes):
    """Signing day: an AI staff finishes its class's NIL — signees it never put
    money on get a deal out of whatever the class budget has left. (Your
    signees get exactly what you offered them.)"""
    import hotseat
    mines = hotseat.humans(league) if getattr(league, "mode", None) == "career" \
        and not getattr(league, "autosim", False) else []
    book = _book(cycle)
    for team, signees in classes.items():
        if any(team is m for m in mines) or not signees:
            continue
        offers = book.setdefault(team, {})
        spent = sum(offers.get(r, 0) for r in signees)
        room = min(available(league, team, cycle) + open_nil(cycle, team),   # lapsed offers free up here
                   class_target(league, team) - spent)
        # The rest of the class money is spread over the signees by what they're worth —
        # a staff doesn't leave its NIL budget sitting in the bank.
        unpaid = [r for r in signees if not offers.get(r) and r.stars >= 2]
        if room < 10_000 or not unpaid:
            continue
        w = {r: market(r.stars) * cycle.rng.uniform(0.8, 1.2) for r in unpaid}
        tot = sum(w.values()) or 1
        for r in unpaid:
            amt = _round(room * w[r] / tot)
            if amt > 0:
                offers[r] = amt


# ═══ NIL in the transfer portal ═════════════════════════════════════════════
# A transfer is paid for what he can do right now: his rating, and his
# position (quarterbacks cost the most). Money works the same way it does with
# recruits — it moves him, it doesn't decide for him — but portal players are
# older, have been paid before, and listen a little harder.

PORTAL_POS = {"QB": 1.8, "DL": 1.15, "OL": 1.1, "WR": 1.05, "CB": 1.05, "K": 0.35, "P": 0.3}


def transfer_market(player):
    """What a transfer like this is going for, per year."""
    v = 20_000 * math.exp((player.overall - 55) / 7.5) * PORTAL_POS.get(player.position, 1.0)
    return int(min(3_000_000, max(10_000, _round(v))))


def player_appetite(player):
    r = random.Random(f"nilp:{player.first_name}:{player.last_name}:{getattr(player, 'home_state', '')}")
    tilt = 1.3 if "mercenary" in getattr(player, "traits", []) else 0.8 if "loyal" in getattr(player, "traits", []) else 1.0
    return clamp(r.gauss(1.05, 0.3) * tilt, 0.3, 1.8)


def portal_room(league, team, report=None):
    """NIL left for transfers. Everybody on the roster now plays next season, the
    incoming class is already promised, and portal offers still out are held."""
    cycle = league.recruiting
    held = 0
    if report is not None:
        for (t, e), amt in getattr(report, "nil", {}).items():
            if t is team and e.destination is None:
                held += amt
    return int(nil_pool(league, team) - roster_nil(team) - committed_nil(cycle, team) - open_nil(cycle, team) - held)


def portal_pull(amount, best, player):
    """How much a NIL offer multiplies a program's appeal to a transfer."""
    if not amount:
        return 1.0
    mkt = transfer_market(player)
    rel = amount / best if best else 1.0
    return 1 + player_appetite(player) * 0.18 * math.sqrt(min(2.0, amount / mkt)) * (0.4 + 0.6 * rel)


def ai_portal_offer(league, team, entry, value, room, rng):
    """What an AI staff puts on the table for a transfer it's bidding on."""
    if room < 15_000:
        return 0
    amt = transfer_market(entry.player) * _ad(team)["nil"] * clamp(value / 40, 0.5, 1.5) * rng.uniform(0.85, 1.15)
    amt = _round(amt)
    if amt > room:
        amt = _round(room) if room >= amt * 0.4 else 0
    return max(0, amt)


# ═══ Budgets that move with the program ═════════════════════════════════════
# Winning brings money: donors give, the conference check grows, the AD asks
# for more and gets it. Losing year after year — and churning through coaches —
# does the opposite. Changes land once a year, after the season, and are
# bounded: a program can grow to 1.5x where it started or fall to 0.7x.

def adjust_budgets(league):
    import carousel as cz
    year = league.year
    fired_by = {}
    for y in range(year - 5, year + 1):
        for m in cz.carousel_moves(league, y):
            if m.get("side") == "out" and m.get("kind") == "fired":
                fired_by[m["school"]] = fired_by.get(m["school"], 0) + 1
    for team in league.teams:
        b = budget(team)
        base = team.__dict__.setdefault("budget_base", b)
        recs = [(r[1], r[2]) for r in getattr(team, "historical_records", [])[-2:]] + [(team.wins, team.losses)]
        pcts = [w / (w + l) for w, l in recs if w + l]
        if not pcts:
            continue
        avg = sum(pcts) / len(pcts)
        s = getattr(team, "_season_line", None) or {}
        if s.get("year") != year:
            s = {}                                   # an interim year: no line of this season's honors
        change, why = 0.0, []
        if avg >= 0.65:
            change += 0.02 + (avg - 0.65) * 0.2
            why.append("winning seasons")
        if s.get("title"):
            change += 0.05
            why.append("a national title")
        elif s.get("cfp"):
            change += 0.03
            why.append("a playoff run")
        if s.get("conf_champ"):
            change += 0.015
            why.append("a league title")
        # Winning above your weight: a program that keeps beating what a school its size
        # usually does starts drawing money (donors, TV windows, gate) even without titles.
        exp = 0.2 + team.prestige / 100 * 0.5            # prestige 45 -> .43, 60 -> .50, 80 -> .60
        if len(pcts) >= 2 and avg - exp >= 0.08:
            change += (avg - exp) * 0.25
            why.append("winning above its weight")
        if any(k in ("NP Appearance",) or "Bowl" in k for k in getattr(team, "achievements", [])) or \
                (team.wins >= 6 and year >= 2026 and team.wins + team.losses >= 12):
            change += 0.015
            why.append("a bowl season")
        if s.get("conf_champ") and team.conference not in POWER_CONFS:
            change += 0.015                              # a league title means more at a smaller school
        rec_all = recs
        losing = 0
        for (w_, l_), p in zip(reversed(rec_all), reversed(pcts)):
            if p < 0.5 and w_ < 6:                       # a 6-7 bowl team isn't a losing program
                losing += 1
            else:
                break
        if losing >= 3:
            change -= 0.03 + 0.01 * (losing - 3)
            why.append(f"{losing} straight losing seasons")
        fired = fired_by.get(team.school, 0)
        if fired >= 2 and avg < 0.5:
            change -= 0.02 * (fired - 1)
            why.append(f"{fired} coaches fired in six years")
        brand, start = team.__dict__.get("brand"), team.__dict__.get("brand_start")
        if brand is not None and start is not None:
            climb = (brand - start) / 100                  # a program that's become something draws money
            if climb >= 0.08:
                change += climb * 0.12
                why.append("a rising program")
            elif climb <= -0.1:
                change += climb * 0.08
                why.append("a fading program")
        import skills
        if skills.team_has(team, "fundraiser") and change > 0:
            change *= 1.5                                # Fundraiser (coaching tree)
            why.append("your fundraising")
        if skills.team_has(team, "blueprint") and change < 0:
            change = 0.0                                 # Blueprint (coaching tree): it never shrinks
        cap = 0.12 if skills.team_has(team, "fundraiser") else 0.08
        change = clamp(change * 0.7, -0.05, cap)        # budgets move, but a season at a time
        if abs(change) < 0.004:
            continue
        new = clamp(b * (1 + change), 0.6 * base, 2.0 * base)
        new = int(round(new / 100_000) * 100_000)
        if new == b:
            continue
        team.budget = new
        log = team.__dict__.setdefault("budget_log", [])
        log.append((year + 1, new, round((new / b - 1) * 100, 1), ", ".join(why)))
        del log[:-10]
        if abs(new / b - 1) >= 0.03:
            verb = "raises" if new > b else "cuts"
            cz._news(league, "budget", f"{team.school} {verb} its football budget to {money(new)} "
                                       f"({(new / b - 1) * 100:+.0f}%) after {', '.join(why)}")


def budget_trend(team):
    """The last change: (year, new budget, percent, why), or None."""
    log = getattr(team, "budget_log", [])
    return log[-1] if log else None
