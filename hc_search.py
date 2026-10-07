"""
hc_search.py — The head coaching search, up close.

THE SEARCH TRACKER. Every opening's search is logged as it happens: the shortlist each
AD worked from, who interviewed, who said no (and why), whose school matched to keep
him, and who got the job. The coaching carousel phase of the offseason calendar shows it
after the hires and fires ([T] on the carousel screen opens it again).

YOUR INTERVIEWS. When schools call you ([I#] on the offers screen), you sit down with the
athletic director. He asks three questions, and the answers he wants depend on who he is
(a Win-Now AD wants to hear "year one"; a Patient one wants a plan). Nail it and the offer
gets better (more money, an extra year); whiff and it can get worse — or get pulled.
Each school interviews you once.
"""
import random

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

QUESTIONS = [
    ("When do we compete for the conference?",
     [("Year one. I don't do rebuilds.", {"now"}), ("Give me two years and I'll build it to last.", {"build"}),
      ("When the roster's ready — I won't cut corners getting there.", {"process"})]),
    ("How are you going to recruit?",
     [("Every top kid in the country hears from us.", {"splash", "recruit"}),
      ("Our state first. Build the fence.", {"local", "fit"}),
      ("Find three-stars and develop them into pros.", {"develop", "process"})]),
    ("What happens to the current staff?",
     [("I'm bringing my own people.", {"own", "now"}), ("Everybody gets a fair evaluation.", {"fit", "process"}),
      ("The ones who recruit stay.", {"recruit"})]),
    ("What's the biggest game on our schedule?",
     [("The rival. Every year.", {"rival"}), ("The next one.", {"conf", "process"}),
      ("The one in January.", {"splash", "now"})]),
    ("What do you need from us to win?",
     [("Money for players. NIL wins now.", {"splash", "now"}), ("Facilities and patience.", {"build", "develop"}),
      ("Nothing. Let me coach.", {"fit", "own"})]),
]

LIKES = {"patient": {"build", "process", "fit", "develop"}, "win_now": {"now", "own", "splash"},
         "big_game": {"rival", "splash", "now"}, "conference": {"conf", "now", "fit"},
         "analytics": {"process", "develop", "fit"}, "booster": {"rival", "splash", "now", "own"},
         "turnaround": {"build", "develop", "now"}, "recruiting": {"recruit", "splash", "local"},
         "traditionalist": {"rival", "local", "fit"}, "budget": {"build", "develop", "fit", "process"},
         "brand": {"splash", "recruit", "now"}, "politician": {"rival", "now", "splash"}}


# ═══ The tracker ════════════════════════════════════════════════════════════

def log(league, team, **kw):
    book = league.__dict__.setdefault("hc_search_log", {}).setdefault(league.year, {})
    entry = book.setdefault(team.school, {"school": team.school, "prestige": round(team.prestige), "short": [],
                                          "no": [], "matched": [], "hired": None})
    for k, v in kw.items():
        if isinstance(entry.get(k), list):
            entry[k].append(v)
        else:
            entry[k] = v


def tracker(league, year=None):
    year = year or league.year
    book = league.__dict__.get("hc_search_log", {}).get(year, {})
    clear()
    print(title_bar(f"HEAD COACH SEARCH TRACKER  ·  {year}-{str(year + 1)[2:]}"))
    if not book:
        print(paint("\n   No searches this year.", C.GRAY))
        pause()
        return
    rows = sorted(book.values(), key=lambda e: -e["prestige"])
    for e in rows:
        print(f"\n   {paint(e['school'].upper(), C.BWHITE, C.BOLD)}" + paint(f"   prestige {e['prestige']}", C.GRAY))
        if e["short"]:
            print(paint("     Shortlist: " + ", ".join(e["short"][:4]), C.GRAY))
        for name, why in e["no"][:3]:
            print(paint(f"     ✗ {name} {why}", C.BRED))
        for name in e["matched"][:2]:
            print(paint(f"     ↺ {name}'s school matched — he stays", C.BYELLOW))
        if e["hired"]:
            print(paint(f"     ✓ Hired: {e['hired']}", C.BGREEN))
    pause()


# ═══ Your interviews ════════════════════════════════════════════════════════

def interview(league, team, coach, offer):
    """Sit down with the AD. Returns the (possibly changed) offer."""
    done = league.__dict__.setdefault("_hc_interviews", {})
    if done.get(team.school) == league.year:
        print(paint(f"   You've already interviewed with {team.school}.", C.BYELLOW))
        pause()
        return offer
    done[team.school] = league.year
    import carousel as cz
    import finance as fi
    style = team.ad.get("style", "patient")
    likes = LIKES.get(style, set())
    r = random.Random(f"hcint:{team.school}:{league.year}")
    qs = r.sample(QUESTIONS, 3)
    hits = 0
    clear()
    print(title_bar(f"INTERVIEW  ·  {team.school.upper()}"))
    print(paint(f"\n   The athletic director ({cz.AD_STYLES[style][0]}: {cz.AD_STYLES[style][1].lower()}) "
                f"meets you at a hotel near the airport.", C.GRAY))
    for q, answers in qs:
        print(paint(f"\n   \"{q}\"", C.BWHITE, C.BOLD))
        for i, (a, _) in enumerate(answers, 1):
            print(f"     {paint(f'[{i}]', C.BYELLOW)} {a}")
        ch = ask("Your answer:").strip()
        pick = answers[int(ch) - 1] if ch.isdigit() and 1 <= int(ch) <= len(answers) else answers[0]
        if pick[1] & likes:
            hits += 1
            print(paint("     He nods and writes something down.", C.BGREEN))
        else:
            print(paint("     He doesn't write anything down.", C.GRAY))
    offer = dict(offer)
    if hits == 3:
        offer["salary"] = int(offer["salary"] * 1.12)
        offer["years"] = offer.get("years", 5) + 1
        verdict = ("He stands up and shakes your hand for a long time. The offer goes up — more money and an "
                   "extra year.", C.BGREEN)
    elif hits == 2:
        offer["salary"] = int(offer["salary"] * 1.05)
        verdict = ("A good conversation. The offer goes up a little.", C.BGREEN)
    elif hits == 1:
        verdict = ("Polite. The offer stands as it was.", C.GRAY)
    else:
        if r.random() < 0.4:
            offer["pulled"] = True
            verdict = ("He thanks you for your time. An hour later his office calls: they're going another "
                       "direction. The offer is pulled.", C.BRED)
        else:
            offer["salary"] = int(offer["salary"] * 0.94)
            verdict = ("It didn't land. The offer is still there, for a little less.", C.BYELLOW)
    print(paint(f"\n   {verdict[0]}", verdict[1], C.BOLD))
    if not offer.get("pulled"):
        print(paint(f"   Their offer: {fi.terms(offer)}", C.BWHITE))
    pause()
    return offer
