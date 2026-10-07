"""
coach_dev.py — Your coach gets better one way: you pay for it.

CPU coaches grow on their own (carousel.progress). Yours doesn't. What you
earn on the job — salary at the end of each season, and contract bonuses —
lands in your bank, and the bank buys development: clinics, film study, a
personal analyst, a recruiting coordinator of your own, a quarterback guru you
fly in for spring ball. Buyout checks count toward career earnings but not the
bank, and you can only spend while you have a job — getting fired from a big
school is not a windfall.

PRICES  (30,000 x 1.09^(rating - 50) per point; Coach Skill x1.5)
      rating 50 -> $30K      60 -> $71K      69 -> $154K
      rating 70 -> $168K     79 -> $365K
      rating 80 -> $398K     89 -> $865K
      rating 90 -> $942K     99 -> $2.05M
  A first job in the Mid-American pays about $0.7-1.3M a year — roughly 8-15
  points a year while your ratings are in the 50s and 60s. A $10M job at a
  blue blood still only buys a handful of points once you're in the 90s.

LIMITS
  One offseason of work is one offseason of work: each rating can go up at most
  +3 in a calendar year, Coach Skill +2. Unspent money carries over.
  Nothing ever goes down on its own.
"""
from ui import C, ask, bar, clear, pad, paint, pause, rating, rule, section, title_bar
from netplay import capture

import finance as fi

KEYS = ("overall",) + ("recruiting", "passing_dev", "offense_dev", "trench_dev", "db_dev", "special_dev")
LABELS = {"overall": "Coach Skill (game day)", "recruiting": "Recruiting", "passing_dev": "Passing Dev (QB/WR)",
          "offense_dev": "Gen. Offense Dev (RB/TE)", "trench_dev": "Trench Dev (OL/DL)",
          "db_dev": "Def. Back Dev (LB/CB/S)", "special_dev": "Special Dev (K/P)"}
WHAT = {"overall": "clinics, film study, a game-management analyst", "recruiting": "a personal recruiting staff",
        "passing_dev": "a quarterback guru for spring ball", "offense_dev": "skill-position clinics",
        "trench_dev": "an offensive line consultant", "db_dev": "a secondary specialist",
        "special_dev": "a kicking consultant"}
YEAR_CAP = {"overall": 2}
DEFAULT_CAP = 3
START_BANK = 250_000          # what you bring to your first job
MAX_RATING = 99


def value(coach, key):
    return coach.overall if key == "overall" else coach.ratings[key]


def price(coach, key):
    """What the next point costs."""
    r = value(coach, key)
    p = 30_000 * 1.09 ** (r - 50)
    if key == "overall":
        p *= 1.5
    return int(round(p / 1000) * 1000)


def bought_this_year(league, coach, key):
    log = coach.__dict__.setdefault("dev_log", {})
    return log.get(league.year, {}).get(key, 0)


def room(league, coach, key):
    return YEAR_CAP.get(key, DEFAULT_CAP) - bought_this_year(league, coach, key)


@capture.hook("coach", "dev", capture.b_dev, ok=capture.dev_bought)
def buy(league, coach, key, n=1):
    """Buy up to n points. Returns (points bought, dollars spent, message)."""
    got = spent = 0
    if coach.team is None:
        return 0, 0, "You need a job to develop."
    for _ in range(n):
        if room(league, coach, key) <= 0:
            break
        if value(coach, key) >= MAX_RATING:
            break
        cost = price(coach, key)
        if cost > getattr(coach, "bank", 0):
            break
        coach.bank -= cost
        spent += cost
        got += 1
        if key == "overall":
            coach.overall += 1
            coach.ceiling = max(getattr(coach, "ceiling", 0), coach.overall)
            if coach.team is not None:
                coach.team.ratings["coach"] = coach.overall
        else:
            coach.ratings[key] += 1
        log = coach.dev_log.setdefault(league.year, {})
        log[key] = log.get(key, 0) + 1
    coach.dev_spent = getattr(coach, "dev_spent", 0) + spent
    if got:
        return got, spent, f"{LABELS[key]} +{got} for {fi.money(spent)}."
    if room(league, coach, key) <= 0:
        return 0, 0, f"That's all the {LABELS[key].split(' (')[0]} work one year allows."
    if value(coach, key) >= MAX_RATING:
        return 0, 0, "Can't get any better than that."
    return 0, 0, f"Not enough in the bank — the next point costs {fi.money(price(coach, key))}."


def ensure(coach):
    """Older careers: whatever you've earned so far is in the bank."""
    if "bank" not in coach.__dict__:
        coach.bank = getattr(coach, "career_earnings", 0) + START_BANK


def develop_screen(league):
    coach = league.user_coach
    ensure(coach)
    if coach.team is None:
        clear()
        print(title_bar("DEVELOP YOUR COACH"))
        print(paint(f"\n   You're out of work. Development is paid for on the job — land one first.", C.BYELLOW))
        print(paint(f"   Bank: {fi.money(coach.bank)} (waiting for you when you're hired).", C.GRAY))
        pause()
        return
    msg = ""
    while True:
        clear()
        print(title_bar("DEVELOP YOUR COACH"))
        k = fi.contract(coach)
        pay = f"{fi.money(k['salary'])}/yr" if k else "no salary right now"
        print(f"   {paint('Bank', C.GRAY)} {paint(fi.money(coach.bank), C.BGREEN, C.BOLD)}   "
              f"{paint('Salary', C.GRAY)} {pay} (paid after every season)   "
              f"{paint('Spent on yourself', C.GRAY)} {fi.money(getattr(coach, 'dev_spent', 0))}")
        print(paint("   Your salary goes into this bank after every season (bonuses too). You only get better by paying\n"
                    "   for it. Each rating: +3 a year at most (Coach Skill +2). Coach Skill is game day: in-game\n"
                    "   adjustments and reads, and your staff's eye for talent. Every first job starts with $250K.", C.GRAY))
        print()
        print(paint(f"   {'#':>2}  {'RATING':<28}{'NOW':>4}   {'':<22}{'NEXT POINT':>11}  {'LEFT THIS YEAR':>14}",
                    C.GRAY, C.BOLD))
        for i, key in enumerate(KEYS, 1):
            v = value(coach, key)
            left = room(league, coach, key)
            cost = price(coach, key)
            afford = C.BGREEN if cost <= coach.bank and left > 0 and v < MAX_RATING else C.GRAY
            print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {pad(LABELS[key], 28)}{rating(v):>4}   "
                  f"{bar(v, 20)}  {pad(paint(fi.money(cost), afford), 11, 'right')}  "
                  f"{pad(str(max(0, left)), 14, 'right')}")
        print(rule())
        if msg:
            print(paint("   " + msg, C.BCYAN, C.BOLD))
        print(paint("   [#] buy one point   [#x3] buy up to three   [B] back", C.GRAY))
        choice = ask("Select:").strip().lower()
        if choice in ("", "b"):
            return
        n = 1
        if "x" in choice:
            choice, _, times = choice.partition("x")
            n = int(times) if times.isdigit() else 1
        if choice.isdigit() and 1 <= int(choice) <= len(KEYS):
            key = KEYS[int(choice) - 1]
            got, _, msg = buy(league, coach, key, n)
            if got:
                msg += f" ({WHAT[key]})"
            if got and got < n:                                   # "up to three" stopped early: say why
                if room(league, coach, key) <= 0:
                    why = "that's the most one year allows"
                elif value(coach, key) >= MAX_RATING:
                    why = "maxed out"
                else:
                    why = f"the next point costs {fi.money(price(coach, key))}, more than the bank"
                msg += f" Stopped at {got}: {why}."
            if got:
                league.__dict__.setdefault("career_log", []).append((league.year, "Development: " + msg))
