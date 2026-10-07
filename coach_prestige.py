"""
coach_prestige.py — How big a name you are when you walk in the door (Coach Career).

Chosen once, when you create your coach, right after difficulty. It is your reputation, not your
ability: your ratings still come from your background, and every coach starts from the same level.
What it changes is who calls with your first job, and what they'll pay.

                 Who calls (FBS programs by prestige, No. 1 = most prestigious)   First contract
  Unknown        the bottom 45 (No. 94 and below): the bottom of the G5          first-timer money (x0.88, capped)
  Rising         No. 55-105: the top of the G5 and the bottom of the Power 4     x0.94, a slightly higher cap
  Established    No. 25-70: solid Power 4 programs                               x1.00, a higher cap
  Elite          the top 30: blue bloods and perennial contenders                x1.06, no first-timer cap

  Pay still scales with your ratings against the size of the job, so a first-year coach at a
  blue blood earns blue-blood dollars but not a proven winner's share of the budget.
  The AD also sizes you up by it when you negotiate: a bigger name asks for more and gets
  turned down less. Once you've coached a season, your record does all the talking.

The catch is the job itself. An Elite coach with first-year ratings inherits a blue blood's roster,
a blue blood's AD and a blue blood's goals. Win, or the seat heats like anyone else's.
"""
from ui import C, ask, clear, paint, title_bar

LEVELS = {
    "unknown":     {"name": "Unknown", "ranks": (94, 138), "pay": 0.88, "cap": 0.75, "level": 55, "leverage": 0.0,
                    "blurb": "Nobody's heard of you. Four small schools will take the chance.",
                    "calls": "the bottom of the G5"},
    "rising":      {"name": "Rising", "ranks": (55, 105), "pay": 0.94, "cap": 0.85, "level": 64, "leverage": 0.03,
                    "blurb": "The coordinator everyone's talking about. Good G5 jobs and a Power 4 rebuild call.",
                    "calls": "the top of the G5 and the bottom of the Power 4"},
    "established": {"name": "Established", "ranks": (25, 70), "pay": 1.0, "cap": 0.95, "level": 74, "leverage": 0.06,
                    "blurb": "A name ADs trust. Solid Power 4 programs want you.",
                    "calls": "solid Power 4 programs"},
    "elite":       {"name": "Elite", "ranks": (1, 30), "pay": 1.06, "cap": None, "level": 84, "leverage": 0.10,
                    "blurb": "The hire that makes headlines. Blue bloods call, and they expect titles.",
                    "calls": "blue bloods and perennial contenders"},
}
ORDER = list(LEVELS)
DEFAULT = "unknown"


def key_of(coach):
    k = getattr(coach, "prestige_start", None)
    return k if k in LEVELS else DEFAULT


def level(coach):
    return LEVELS[key_of(coach)]


def offer_pool(league, coach):
    """The FBS programs whose ADs might call a first-time head coach with this name."""
    low = sorted((t for t in league.teams if not getattr(t, "fcs", False)), key=lambda t: t.prestige)
    if key_of(coach) == "unknown":
        return low[:45]                                      # exactly the old pool, in the old order
    lo, hi = level(coach)["ranks"]
    top = low[::-1]
    pool = top[lo - 1:hi]
    return pool if len(pool) >= 4 else low[:45]


def _row(i, k):
    lv = LEVELS[k]
    lo, hi = lv["ranks"]
    where = f"No. {lo}-{hi}" if k != "unknown" else "No. 94 and below"
    print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {paint(lv['name'], C.BWHITE, C.BOLD)}")
    print(paint(f"        {lv['blurb']}", C.GRAY))
    print(paint(f"        who calls: {lv['calls']} ({where} in prestige)", C.BCYAN))


def choose(cur=None, sub=None):
    """The picker. Returns a level key (Enter = Unknown, the classic start)."""
    clear()
    print(title_bar("HOW BIG IS YOUR NAME?", sub=sub))
    print(paint("\n   Your reputation decides who calls with your first job and what they'll pay. It isn't your\n"
                "   ability: your ratings come from your background either way. A big name gets a big job, and a big\n"
                "   job's AD expects big results from year one.\n", C.GRAY))
    for i, k in enumerate(ORDER, 1):
        _row(i, k)
        print()
    c = ask(f"Prestige (Enter = {LEVELS[cur or DEFAULT]['name']}):").strip()
    if c.isdigit() and 1 <= int(c) <= len(ORDER):
        return ORDER[int(c) - 1]
    return cur or DEFAULT
