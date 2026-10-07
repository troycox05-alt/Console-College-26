"""
ad_trust.py — Your AD remembers (Career mode).

Your seat is how hot things are right now. Trust, 0 to 100, is what's
underneath it: how much your athletic director believes you, built from
everything that's happened between the two of you.

WHAT BUILDS IT                          WHAT COSTS IT
  keeping your word (promises that        breaking it (a promise that rode on a
  rode on a game or a season)             game or a season, and didn't happen)
  answers he likes, in his inbox and      answers he doesn't like
  at the podium                           asking him for money — every time
  meeting the goals he set                missing them
                                          leaving him on read

WHAT IT DOES
  The same loss reads differently. A trusting AD gives you rope — bad results
  heat your seat less, and he says so. A wary one reads every loss as a
  pattern — results heat it more, and good ones count for less.
  When you ask for money, trust decides how much he finds.
  His messages sound like it ("You've earned some rope with me" / "I've heard
  promises before"), and trust shows next to his name in your inbox and on
  your career page, with the last few things that moved it.

THE BAR GOES UP
  Trust is hard to max out: the closer he is to all-in, the less each good
  moment adds. And every December he resets his expectations a little — last
  year's goodwill fades toward neutral, so a great stretch has to keep going.

A NEW AD STARTS OVER
  Trust belongs to one AD. Take a new job, or have your AD replaced, and it
  starts fresh — a little lower if he inherited you rather than hired you.
"""
START = 50


def _key(team):
    return f"{team.school}|{team.ad.get('name', '?')}"


def record(coach, team, league=None):
    book = coach.__dict__.setdefault("ad_trust", {})
    k = _key(team)
    if k not in book:
        inherited = team.ad.get("inherited") and (team.ad.get("since") or 0) > (coach.hired_year or 0)
        book[k] = {"v": float(START - (6 if inherited else 0)), "log": [],
                   "since": getattr(league, "year", None), "inherited": bool(inherited)}
    return book[k]


def get(coach, team=None):
    team = team or getattr(coach, "team", None)
    if team is None or not getattr(team, "ad", None):
        return float(START)
    return record(coach, team)["v"]


def change(league, d, why):
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None or not d:
        return
    rec = record(coach, team, league)
    import skills
    if skills.has(coach, "trusted_voice"):
        d *= 1.3 if d > 0 else 0.7              # Trusted Voice (coaching tree)
    if d > 0:
        d *= max(0.1, 1 - rec["v"] / 110)       # the last points are the hardest to earn
    floor = 40.0 if skills.has(coach, "face") else 0.0      # Face of the Program
    rec["v"] = max(floor, min(100.0, rec["v"] + d))
    rec["log"].append((league.year, league.week, round(d, 1), why))
    del rec["log"][:-8]


def word(v):
    return ("all in on you" if v >= 80 else "solid" if v >= 62 else "steady" if v >= 45 else
            "wary" if v >= 30 else "skeptical" if v >= 15 else "done with you")


def color(v):
    from ui import C
    return C.BGREEN if v >= 62 else C.BWHITE if v >= 45 else C.BYELLOW if v >= 30 else C.BRED


def heat_factor(coach, team, swing):
    """How much a result moves the seat, given the trust underneath it (user coach only)."""
    if "ad_trust" not in coach.__dict__:
        return 1.0
    t = get(coach, team)
    if swing > 0:                        # bad news
        return 1.25 - t / 100 * 0.5     # trust 100 → 0.75x, trust 0 → 1.25x
    return 0.75 + t / 100 * 0.5         # good news counts for more with a trusting AD


def money_factor(coach, team):
    return 0.5 + get(coach, team) / 100


def voice(coach, team, bad=True):
    """A sentence that shows he remembers."""
    t = get(coach, team)
    if bad:
        return (" You've earned some rope with me. Don't make me regret it." if t >= 72 else
                " I've heard promises before, Coach." if t < 32 else "")
    return (" I told the board you were the right hire. This is why." if t >= 72 else
            " About time." if t < 32 else "")


def lines(coach, team, n=4):
    rec = record(coach, team)
    return [(d, why) for _, _, d, why in rec["log"][-n:]]


def new_season(league):
    """December: last year's goodwill fades a little toward neutral (and so do grudges)."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None or "ad_trust" not in coach.__dict__:
        return
    rec = record(coach, team, league)
    before = rec["v"]
    rec["v"] += (58 - rec["v"]) * 0.2
    rec["log"].append((league.year, league.week, round(rec["v"] - before, 1), "the bar goes up every year"))
    del rec["log"][:-8]
