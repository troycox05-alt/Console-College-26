"""
dynasty.py — The changing of the guard.

A program's standing used to be mostly fixed at the start of the world. Now it
has two halves, and both move:

  LEGACY  (tradition)  the decades. It drifts every season toward the program's
                       last dozen years of results — a decade of winning adds real
                       points, a decade of losing takes them away — but slowly,
                       so the blue bloods are still the blue bloods for a while.

  BRAND   (0-100)      the last five seasons, most recent counting most: wins,
                       final poll finish, playoff trips and wins, titles, league
                       titles, bowl wins. It moves fast. Recruits, transfers and
                       the recruiting boards all read it.

  Prestige = brand .30 + tradition .18 + coach .12 + facilities .12 + AD .09
             + academics .095 + campus .095 (+ the Pro League-draft bonus). On day one it
             equals the old number exactly; after that it's earned.

Money moves with it (finance.adjust_budgets), and every winter a few things
can happen to a program that nobody plans for:

  BOOSTER WINDFALL  a mega-donor or a new collective: a big, lasting budget jump
                    and a facilities push. Rare; likelier at a rising program.
  CAB SANCTIONS    very rare: a postseason ban, a recruiting penalty for two
                    years, and a hit to the brand.

The Parity Report (Media Center) tracks how much the top of the sport turns over.
"""
import random

from ui import C, clear, pad, paint, pause, rule, section, title_bar, truncate

WINDFALL_ODDS = 0.009          # per program per winter
SANCTION_ODDS = 0.0028


def initial_brand(team):
    """The value that makes the new prestige formula equal the old one on day one."""
    from models import Team
    r = team.ratings
    old = sum(r[k] * w for k, w in Team.PRESTIGE_WEIGHTS.items())
    rest = sum(r[k] * w for k, w in Team.PRESTIGE_WEIGHTS_BRAND.items())
    return max(15.0, min(99.0, (old - rest) / Team.BRAND_WEIGHT))


def ensure(team):
    if getattr(team, "fcs", False):
        return
    if getattr(team, "brand", None) is None:
        team.brand = initial_brand(team)
        team.brand_start = team.brand
        team.tradition_start = team.ratings["tradition"]
        team.prestige_start = team.prestige
        team.season_scores = []


def ensure_all(league):
    for t in league.teams:
        ensure(t)


# ═══ A season, as a number ═════════════════════════════════════════════════

def season_score(league, team):
    g = team.wins + team.losses
    pct = team.wins / g if g else 0.5
    s = 25 + pct * 55
    ach = set(getattr(team, "achievements", []))
    if "National Champion" in ach:
        s += 16
    elif "National Runner-Up" in ach:
        s += 9
    elif "Playoff Semifinalist" in ach:
        s += 6
    elif "NP Appearance" in ach:
        s += 4
    if f"{team.conference} Champion" in ach:
        s += 4
    if any(a.endswith(" Champion") and ("Bowl" in a or "Classic" in a) for a in ach):
        s += 2
    rk = league.rankings.rank_of(team) if getattr(league, "rankings", None) else None
    if rk:
        s += (26 - rk) * 0.45
    return max(0.0, min(100.0, s))


def update(league):
    """After the season, before the carousel's next hires and signing day read prestige."""
    year = league.year
    if year < 2026:
        return                                    # the years before your world: no games, no brand
    polls = league.__dict__.setdefault("final_polls", {})
    if getattr(league, "rankings", None):
        polls[year] = [t.school for t in league.rankings.top(25)]
    for t in league.teams:
        ensure(t)
        if t.wins + t.losses == 0:
            continue
        s = season_score(league, t)
        t.season_scores = [x for x in t.season_scores if x[0] != year] + [(year, s)]
        recent = [v for _, v in t.season_scores[-5:]]
        w = list(range(1, len(recent) + 1))                       # oldest 1 … newest 5
        target = sum(a * b for a, b in zip(recent, w)) / sum(w)
        t.brand_prev = t.brand
        t.brand = max(10.0, min(99.0, t.brand + (target - t.brand) * 0.45))
        # Legacy: the last dozen years, with the years before your world counted at the old tradition.
        long = [v for _, v in t.season_scores[-12:]]
        long_avg = (sum(long) + t.ratings["tradition"] * (12 - len(long))) / 12
        drift = (long_avg - t.ratings["tradition"]) * 0.09
        t.tradition_f = getattr(t, "tradition_f", float(t.ratings["tradition"])) + drift
        t.tradition_f = max(25.0, min(99.0, t.tradition_f))
        t.ratings["tradition"] = int(round(t.tradition_f))


# ═══ The unplanned ═════════════════════════════════════════════════════════

def _news(league, text):
    league.__dict__.setdefault("dynasty_news", {}).setdefault(league.year, []).append(text)


def news_for(league, year):
    return list(getattr(league, "dynasty_news", {}).get(year, []))


def shocks(league, rng):
    """Booster windfalls. Called once a winter. (CAB sanctions come out of compliance.py now: real cases, not dice.)"""
    import finance
    if league.year < 2026:
        return
    rng = random.Random(f"shocks:{league.seed}:{league.year}")
    for t in league.teams:
        ensure(t)
        rising = max(0.0, t.brand - getattr(t, "brand_prev", t.brand))
        mid = 1.4 if 45 <= t.prestige <= 78 else 0.7
        style = t.ad.get("style") if isinstance(getattr(t, "ad", None), dict) else None
        odds = WINDFALL_ODDS * mid * (1 + rising / 6) * (1.6 if style in ("booster", "brand") else 1.0)
        if getattr(t, "windfall_year", -99) >= league.year - 8:
            odds = 0
        if rng.random() < odds:
            b = finance.budget(t)
            bump = rng.uniform(0.25, 0.6)
            t.budget = int(round(b * (1 + bump) / 100_000) * 100_000)
            t.budget_base = max(getattr(t, "budget_base", b), t.budget / 1.3)
            t.windfall_year = league.year
            t.brand = min(99.0, t.brand + 4)
            import facilities
            f = facilities.ensure(t)
            k = min(f, key=f.get)
            if k == "stadium":
                import stadium
                stadium.gift(t, 3, rng)                    # a donor pays for three stadium upgrades
            else:
                f[k] = min(10, f[k] + 2)
            facilities.sync_rating(t)
            donor = rng.choice(("a billionaire alum", "a sportswear founder", "an oil family",
                                "a tech founder who never finished his degree", "a new NIL collective",
                                "a hedge-fund booster", "a car-dealership dynasty", "a shipping magnate"))
            what = (f"the {facilities.SHORT.get(k, k).lower()} facilities get rebuilt." if k != "stadium"
                    else f"{t.stadium} gets a round of upgrades.")
            _news(league, f"BOOSTERS: {donor} makes {t.school} a priority — the football budget jumps "
                          f"{bump * 100:.0f}% to {finance.money(t.budget)}, and {what}")


def banned(league, team):
    s = getattr(team, "sanctions", None)
    return bool(s) and (s.get("ban") == league.year or league.year in (s.get("bans") or ()))


def recruiting_penalty(league, team):
    s = getattr(team, "sanctions", None)
    if s and s.get("year", 0) < league.year + 1 and s.get("until", 0) >= league.year:
        return s.get("recruit_mult", 1.0)
    return 1.0


# ═══ The Parity Report ═════════════════════════════════════════════════════

def parity_numbers(league, years):
    polls = getattr(league, "final_polls", {})
    top10, cfp, champs = set(), set(), set()
    for y in years:
        top10 |= set(polls.get(y, [])[:10])
    for t in league.teams:
        for r in t.historical_records:
            if r[0] in years and len(r) > 5 and "NP Appearance" in r[5]:
                cfp.add(t.school)
            if r[0] in years and len(r) > 5 and "National Champion" in r[5]:
                champs.add(t.school)
    return top10, cfp, champs


def parity_screen(league):
    clear()
    print(title_bar("THE PARITY REPORT"))
    polls = getattr(league, "final_polls", {})
    years = sorted(polls)
    print(paint("   How much the top of the sport turns over. (A rough real-world guide: about 40 programs\n"
                "   cycle through final top-10s over twenty years.)", C.GRAY))
    print()
    if not years:
        print(paint("   Nothing yet — the report starts with the first final poll.", C.GRAY))
        pause()
        return
    print(section("BY DECADE", C.BYELLOW))
    print(paint(f"   {'SEASONS':<14}{'TOP-10 TEAMS':>13}{'PLAYOFF TEAMS':>15}{'CHAMPIONS':>11}", C.GRAY))
    start = years[0]
    while start <= years[-1]:
        span = [y for y in years if start <= y < start + 10]
        a, b, c = parity_numbers(league, span)
        print(f"   {f'{span[0]}-{span[-1]}':<14}{len(a):>13}{len(b):>15}{len(c):>11}")
        start += 10
    a, b, c = parity_numbers(league, years)
    print(f"   {paint('All-time', C.BWHITE):<23}{len(a):>13}{len(b):>15}{len(c):>11}")
    print()
    for t in league.teams:
        ensure(t)
    moved = sorted(league.teams, key=lambda t: t.prestige - getattr(t, "prestige_start", t.prestige))
    print(section("BIGGEST RISERS SINCE 2026 (PRESTIGE)", C.BGREEN))
    for t in reversed(moved[-8:]):
        d = t.prestige - t.prestige_start
        extra = f"brand {t.brand:.0f} · tradition {t.ratings['tradition']}"
        print(f"   {pad(t.school, 22)}{t.prestige_start:>4} → {t.prestige:<4}{paint(f'{d:+d}', C.BGREEN)}"
              f"   {paint(extra, C.GRAY)}")
    print()
    print(section("BIGGEST FALLERS SINCE 2026", C.BRED))
    for t in moved[:8]:
        d = t.prestige - t.prestige_start
        print(f"   {pad(t.school, 22)}{t.prestige_start:>4} → {t.prestige:<4}{paint(f'{d:+d}', C.BRED)}"
              f"   {paint(f'brand {t.brand:.0f}', C.GRAY)}")
    print()
    print(section("MOST PRESTIGIOUS NOW", C.BCYAN))
    top = sorted(league.teams, key=lambda t: -t.prestige)[:12]
    start_rank = {t.school: i for i, t in enumerate(sorted(league.teams, key=lambda t: -t.prestige_start), 1)}
    for i, t in enumerate(top, 1):
        print(f"   {paint(f'{i:>2}.', C.GRAY)} {pad(t.school, 22)}{t.prestige:>4}   "
              f"{paint(f'(No. {start_rank[t.school]} in 2026)', C.GRAY)}")
    shocks_list = [(y, n) for y in sorted(getattr(league, "dynasty_news", {})) for n in league.dynasty_news[y]]
    if shocks_list:
        print()
        print(section("BOOSTERS & SANCTIONS", C.BMAGENTA))
        for y, n in shocks_list[-8:]:
            print(f"   {paint(str(y), C.GRAY)}  {truncate(n, 108)}")
    pause()
