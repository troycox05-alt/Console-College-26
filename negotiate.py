"""
negotiate.py — Sit down with someone and make a deal (Coach Career).

From FIND THE MONEY ([N#] on a player or a coordinator, [D] for your own deal), every
offer is shown with how it's likely to land before you make it. Each kind of offer can be
made once a year per person; a near miss gets a counteroffer you can take or leave.

PLAYERS (his NIL deal)
  Straight cut      25% less, nothing back                     hardest sell
  Pay it back       take 20/35/50% less this year; he gets it   easier: he's not losing money,
                    all back next year plus 15%                 just waiting (you owe it even if
                                                                he leaves)
  Role promise      20% less for a promise: a backup is told    easier for a backup — and graded
                    he'll start (or play real snaps) next fall  at season's end like a recruiting
                                                                promise: kept or broken
COORDINATORS (his contract)
  Straight cut      15% less                                    hardest sell
  Extension         two more years with a 3% yearly raise, for  security sells — but his buyout
                    10% or 20% less now                         grows with the years you add
  Pay it back       10/20% less this year, back next year +12%
  Title             10% less plus the assistant head coach      a title costs nothing and means
                    title                                       a lot to a climber
YOUR OWN DEAL
  Pay cut (in the budget screen) or defer: take less this year, get it back next year +10%.

Money promised for later goes on the books for that season as "deferred pay" — next
year's budget will feel it.
"""
import random

import finance as fi
import morale
from ui import C, ask, clear, pad, paint, pause, rule, title_bar


def _y(league):
    return league.year + 1


def _promise_season(league):
    started = getattr(league, "week", 0) >= 1 or getattr(league, "season_complete", False)
    return league.year + (1 if started else 0)


def _log(league, text):
    league.__dict__.setdefault("career_log", []).append((league.year, text))


def odds_word(p):
    return ("very likely" if p >= 0.8 else "likely" if p >= 0.62 else "a coin flip" if p >= 0.42
            else "a tough sell" if p >= 0.25 else "a long shot")


def _done(obj, tag, league):
    return obj.__dict__.setdefault("_deals", {}).get(tag) == league.year


def _mark(obj, tag, league):
    obj.__dict__.setdefault("_deals", {})[tag] = league.year


def defer(team, league, who, amount, year):
    """Money owed later: it sits on that season's books."""
    team.__dict__.setdefault("buyouts", []).append(
        {"name": f"deferred pay: {who}", "role": "DEF", "per_year": int(amount), "start": year, "end": year,
         "kind": "deferred"})


def _try(league, key, odds, label):
    """Roll it. Returns 'yes', 'counter' (a near miss) or 'no'."""
    roll = random.Random(f"deal:{key}:{league.year}").random()
    if roll < odds:
        return "yes"
    if roll < odds + 0.18:
        return "counter"
    return "no"


# ═══ Players ════════════════════════════════════════════════════════════════

def player(league, team, p, starter):
    while True:
        base = 0.45 + (morale.get(p) - 55) / 120 + (0.15 if not starter else -0.05) \
            - 0.15 * (fi.player_appetite(p) - 1)
        nil = p.nil
        opts = []
        opts.append(("cut", f"Straight cut: 25% less ({fi.money(nil * 0.75)}/yr), nothing back",
                     max(0.06, min(0.85, base)), 0.25))
        for pct in (0.20, 0.35, 0.50):
            opts.append((f"defer{int(pct * 100)}",
                         f"Pay it back: {int(pct * 100)}% less this year ({fi.money(nil * pct)}), "
                         f"{fi.money(nil * pct * 1.15)} back next year",
                         max(0.1, min(0.92, base + 0.28 - pct * 0.5)), pct))
        if not starter and p.year < 3:
            opts.append(("role", f"Role promise: 20% less, and he's told he'll start next fall",
                         max(0.1, min(0.92, base + 0.32)), 0.20))
            opts.append(("play", f"Role promise: 15% less, and he's told he'll play real snaps next fall",
                         max(0.1, min(0.92, base + 0.22)), 0.15))
        clear()
        print(title_bar(f"SIT DOWN WITH {p.name.upper()}  ·  {p.position} · {p.class_label}"))
        print(paint(f"\n   His deal: {fi.money(nil)}/yr.  Mood: {morale.word(morale.get(p))}.  "
                    f"{'Starter' if starter else 'Backup'}.", C.GRAY))
        print()
        for i, (tag, text, o, _) in enumerate(opts, 1):
            used = _done(p, tag[:5], league)
            col = C.GRAY if used else C.WHITE
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(text, col)}")
            print(paint(f"        {'already tried this year' if used else odds_word(o)}", C.GRAY))
        ch = ask("Offer # (Enter = done):").strip()
        if not ch:
            return
        if not ch.isdigit() or not 1 <= int(ch) <= len(opts):
            continue
        tag, text, o, pct = opts[int(ch) - 1]
        if _done(p, tag[:5], league):
            print(paint("   You already made him that kind of offer this year.", C.BYELLOW))
            pause()
            continue
        _mark(p, tag[:5], league)
        result = _try(league, f"p:{p.name}:{tag}", o, text)
        if result == "counter":
            pct2 = round(pct / 2, 2)
            print(paint(f"   He won't do {int(pct * 100)}%. He'd do {int(pct2 * 100)}%.", C.BYELLOW, C.BOLD))
            if ask("Take his counter? (y/n)").strip().lower() in ("y", "yes"):
                pct, result = pct2, "yes"
            else:
                result = "walked"
        if result == "yes":
            cut = fi._round(nil * pct, 1_000)
            p.nil -= cut
            if tag.startswith("defer"):
                defer(team, league, p.name, cut * 1.15, _y(league) + 1)
                p.__dict__.setdefault("_nil_restore", []).append((_y(league), cut))
                morale.nudge(p, -1, "deferred part of his NIL", league)
                note = f"{fi.money(cut * 1.15)} owed to him next year"
            elif tag in ("role", "play"):
                p.recruit_promise = {"kind": "start" if tag == "role" else "play", "year": _promise_season(league)}
                morale.nudge(p, 4, "promised a bigger role", league)
                note = "the promise is graded at the end of next season"
            else:
                morale.nudge(p, -5, "took less NIL to help the budget", league)
                note = "he's doing you a favor"
            _log(league, f"{p.name}: {text.split(':')[0].lower()} (-{fi.money(cut)}/yr).")
            print(paint(f"   Deal. {p.name} takes {fi.money(cut)} less this year — {note}.", C.BGREEN, C.BOLD))
        elif result == "no":
            morale.nudge(p, -8 if tag == "cut" else -4, "a hard money conversation", league)
            print(paint(f"   {p.name} says no.", C.BRED))
        else:
            print(paint("   You walk away from the table.", C.GRAY))
        pause()


# ═══ Coordinators ═══════════════════════════════════════════════════════════

def coordinator(league, team, role, c):
    import staff
    while True:
        k = fi.contract(c)
        if not k:
            return
        sal = k["salary"]
        pers = getattr(c, "personality", "")
        base = {"homebody": 0.55, "builder": 0.48, "climber": 0.22}.get(pers, 0.4)
        title = c.__dict__.get("ahc_title")
        opts = [("cut", f"Straight cut: 15% less ({fi.money(sal * 0.85)}/yr)", base, 0.15)]
        for pct in (0.10, 0.20):
            o = base + 0.32 - pct + (0.1 if pers == "homebody" else -0.15 if pers == "climber" else 0)
            opts.append((f"ext{int(pct * 100)}", f"Extension: +2 years at a 3% raise, {int(pct * 100)}% less now "
                                                 f"({fi.money(sal * (1 - pct))}/yr)", o, pct))
        for pct in (0.10, 0.20):
            opts.append((f"def{int(pct * 100)}", f"Pay it back: {int(pct * 100)}% less this year "
                                                 f"({fi.money(sal * pct)}), {fi.money(sal * pct * 1.12)} back next year",
                         base + 0.25 - pct, pct))
        if not title:
            opts.append(("title", "Title: 10% less, and he's named assistant head coach",
                         base + (0.35 if pers == "climber" else 0.2), 0.10))
        clear()
        print(title_bar(f"SIT DOWN WITH {c.name.upper()}  ·  {staff.ROLE_NAMES[role].upper()}"))
        print(paint(f"\n   {fi.deal_line(k, league)}.  Personality: {pers or 'steady'}."
                    + ("  Assistant head coach." if title else ""), C.GRAY))
        print(paint(f"   If you let him go today you'd owe {fi.money(fi.owed(c, league))}.", C.GRAY))
        print()
        for i, (tag, text, o, _) in enumerate(opts, 1):
            o = max(0.06, min(0.92, o))
            used = _done(c, tag[:3], league)
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(text, C.GRAY if used else C.WHITE)}")
            print(paint(f"        {'already tried this year' if used else odds_word(o)}", C.GRAY))
        ch = ask("Offer # (Enter = done):").strip()
        if not ch:
            return
        if not ch.isdigit() or not 1 <= int(ch) <= len(opts):
            continue
        tag, text, o, pct = opts[int(ch) - 1]
        o = max(0.06, min(0.92, o))
        if _done(c, tag[:3], league):
            print(paint("   You already made him that kind of offer this year.", C.BYELLOW))
            pause()
            continue
        _mark(c, tag[:3], league)
        result = _try(league, f"c:{c.name}:{tag}", o, text)
        if result == "counter":
            pct2 = round(pct / 2, 3)
            print(paint(f"   His agent comes back: {round(pct2 * 100)}%, not {int(pct * 100)}%.", C.BYELLOW, C.BOLD))
            if ask("Take the counter? (y/n)").strip().lower() in ("y", "yes"):
                pct, result = pct2, "yes"
            else:
                result = "walked"
        if result == "yes":
            cut = int(sal * pct)
            k["salary"] = sal - cut
            if tag.startswith("ext"):
                k["years"] += 2
                k["end"] += 2
                k["raise"] = max(k.get("raise", 0.0) or 0.0, 0.03)
                c.stay_lean = (league.year, -1)                 # extended: he's settled in
                note = f"signed through {k['end']}"
            elif tag.startswith("def"):
                defer(team, league, c.name, cut * 1.12, _y(league) + 1)
                k.setdefault("_restore", []).append((_y(league), cut))
                note = f"{fi.money(cut * 1.12)} owed to him next year"
            elif tag == "title":
                c.ahc_title = True
                note = "he's your assistant head coach"
            else:
                note = "he believes in what you're building"
            _log(league, f"{c.name}: {text.split(':')[0].lower()} (-{fi.money(cut)}/yr).")
            print(paint(f"   Deal. {c.name} takes {fi.money(cut)} less — {note}.", C.BGREEN, C.BOLD))
        elif result == "no":
            if tag == "cut":
                c.stay_lean = (league.year, 1)                  # insulted: he'll take other schools' calls
            print(paint(f"   {c.name} says no." + (" He'll be listening when other schools call." if tag == "cut" else ""),
                        C.BRED))
        else:
            print(paint("   You walk away from the table.", C.GRAY))
        pause()


# ═══ You ════════════════════════════════════════════════════════════════════

def defer_own(league, team):
    k = fi.contract(team.coach)
    if not k:
        return
    raw = ask(f"Defer how much of your {fi.money(k['salary'])} this year? (e.g. 500k — back next year +10%; "
              "Enter = cancel):").strip()
    amt = fi.parse_money(raw) if raw else None
    if not amt or amt <= 0:
        return
    amt = min(int(amt), int(k["salary"] * 0.5))
    k["salary"] -= amt
    k.setdefault("_restore", []).append((_y(league), amt))
    defer(team, league, "you", amt * 1.1, _y(league) + 1)
    try:
        import ad_trust
        ad_trust.change(league, 1.0, "deferred his own pay to help the budget")
    except Exception:
        pass
    _log(league, f"Deferred {fi.money(amt)} of your salary to next year.")
    print(paint(f"   Done: {fi.money(amt)} less this year, {fi.money(amt * 1.1)} back next year.", C.BGREEN))
    pause()
