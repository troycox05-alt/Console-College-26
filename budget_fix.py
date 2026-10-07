"""
budget_fix.py — Find the money (Coach Career).

Whenever something you try costs more than you have free — a coordinator's salary, a
recruit's or transfer's NIL, a raise to keep a player, a position coach, a facilities
project, a stadium fund deposit — the game opens this screen instead of just saying no.
You can also open it from the budget screen ([R]).

Everything here moves NEXT SEASON's money (the pool NIL and staff are paid from):

  [1] Players       ask one to restructure his NIL deal (once a year each; he may say no
                    and resent it), or release him (he's gone; the locker room notices)
  [2] Coordinators  ask for a pay cut (once a year; a no makes him likelier to leave),
                    or let him go (you still owe his buyout — the screen shows the net)
  [3] Position coaches  a pay cut (a raise you gave him goes first), or let him go — an
                    interim graduate assistant costs much less
  [4] Buyouts       ask a fired coach to stretch next season's check over three years
                    (10% more in total)
  [5] Your salary   take a pay cut for the rest of your deal (your AD notices)
  [6] Facilities    cancel next season's construction project or a stadium fund deposit
  [7] Recruiting    pull NIL offers you've made to recruits who haven't signed

When the money's there, you go straight back to what you were doing.
"""
import random

import finance as fi
from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate


def interactive(league, team):
    return (getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is team
            and not getattr(league, "autosim", False))


def _y(league):
    return league.year + 1


def _log(league, text):
    league.__dict__.setdefault("career_log", []).append((league.year, text))


def _roll(key):
    return random.Random(key).random()


def _asked(obj, tag, league):
    book = obj.__dict__.setdefault("_budget_asks", {})
    return book.get(tag) == league.year


def _mark(obj, tag, league):
    obj.__dict__.setdefault("_budget_asks", {})[tag] = league.year


def cover(league, team, need, why, free_fn=None):
    """Make sure `need` dollars are free. Opens the rebalance screen if they aren't.
    Returns True when the money is there. `free_fn` measures a different pool (the portal's)."""
    free_fn = free_fn or (lambda: fi.available(league, team))
    if free_fn() >= need:
        return True
    if not interactive(league, team):
        return False
    return screen(league, team, need, why, free_fn)


def screen(league, team, need=0, why=None, free_fn=None):
    free_fn = free_fn or (lambda: fi.available(league, team))
    while True:
        free = free_fn()
        clear()
        print(title_bar("FIND THE MONEY  ·  " + team.school.upper(), sub=why or "rebalance next season's budget"))
        if need:
            short = need - free
            if short <= 0:
                print(paint(f"\n   Done — you have {fi.money(free)} free, enough for this ({fi.money(need)}).", C.BGREEN, C.BOLD))
                pause("Press Enter to go back and finish...")
                return True
            print(paint(f"\n   Needed: {fi.money(need)}   ·   Free: {fi.money(free)}   ·   "
                        f"Short: {fi.money(short)}", C.BRED, C.BOLD))
        else:
            print(paint(f"\n   Free for next season: {fi.money(free)}", C.BGREEN if free >= 0 else C.BRED, C.BOLD))
        _summary(league, team)
        print(rule())
        opts = [("1", "Players: restructure or release NIL deals"), ("2", "Coordinators: pay cut or let go"),
                ("3", "Position coaches: pay cut or let go"), ("4", "Buyouts you owe: stretch them out"),
                ("5", "Your salary: take a cut"), ("6", "Facilities: cancel a project or deposit"),
                ("7", "Recruiting: pull NIL offers")]
        for k, lbl in opts:
            print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {lbl}")
        print(f"   {paint('[Enter]', C.GRAY)} {'give up — cancel what you were doing' if need else 'done'}")
        ch = ask("Where do you want to look?").strip().lower()
        if not ch:
            return free_fn() >= need if need else True
        {"1": players, "2": coordinators, "3": position_coaches, "4": buyouts, "5": your_salary,
         "6": facilities, "7": recruiting}.get(ch, lambda *a: None)(league, team)


def _summary(league, team):
    b = fi.budget(team)
    y = _y(league)
    import poscoach
    import facilities as fa
    lines = [("Budget after operations", b * (1 - fi.OPS_SHARE), C.BWHITE),
             ("Your salary", -fi.salary(team.coach) if fi.contract(team.coach) else -fi.HC_SHARE * b, C.WHITE),
             ("Coordinators", -sum(fi.salary(c) if fi.contract(c) else fi.COORD_SHARE * b
                                   for c in (getattr(team, "oc", None), getattr(team, "dc", None))), C.WHITE),
             ("Position coaches vs a standard room", -poscoach.payroll_delta(team), C.WHITE),
             ("Buyouts owed", -fi.buyouts_in(team, y), C.WHITE),
             ("Facilities & stadium fund", -fa.spend_in(team, y), C.WHITE),
             ("Other income", fi.income_in(team, y), C.WHITE),
             ("Player NIL on the roster", -fi.roster_nil(team, returning=not getattr(league, "nil_rolled", False)), C.WHITE),
             ("NIL promised to recruits", -(fi.committed_nil(league.recruiting, team) + fi.open_nil(league.recruiting, team)),
              C.WHITE)]
    print(section("NEXT SEASON'S BOOKS"))
    for lbl, v, col in lines:
        if v:
            print(f"   {pad(lbl, 40)}{paint(pad(fi.money(v), 10, 'right'), C.BGREEN if v > 0 else C.BRED)}")


# ── 1. Players ───────────────────────────────────────────────────────────────

def _counts(league, p):
    """Does his deal count against next season? (In season, a senior's doesn't.)"""
    return getattr(league, "nil_rolled", False) or p.year < 3


def players(league, team):
    import morale
    while True:
        starters = {id(p) for g in team.starters().values() for p in g}
        paid = sorted((p for p in team.roster if (getattr(p, "nil", 0) or 0) > 0 and _counts(league, p)),
                      key=lambda p: -p.nil)[:20]
        clear()
        print(title_bar("PLAYERS  ·  NIL DEALS"))
        if not paid:
            print(paint("\n   Nobody on the roster has a deal that counts against next season.", C.GRAY))
            pause()
            return
        print(paint(f"   {'#':>2}  {'PLAYER':<24}{'POS':<5}{'CLASS':<7}{'ROLE':<9}{'NIL/YR':>9}   MOOD", C.GRAY, C.BOLD))
        for i, p in enumerate(paid, 1):
            role = "starter" if id(p) in starters else "backup"
            asked = paint("  asked", C.GRAY) if _asked(p, "nil", league) else ""
            print(f"   {i:>2}  {pad(truncate(p.name, 23), 24)}{pad(p.position, 5)}{pad(p.class_label, 7)}{pad(role, 9)}"
                  f"{pad(fi.money(p.nil), 9, 'right')}   {morale.word(morale.get(p))}{asked}")
        print(paint("\n   [N#] sit down and negotiate (pay it back later, a role promise...)   [R#] ask him to take 25% less\n"
                    "   [X#] release him (frees his whole deal)   [Enter] back", C.GRAY))
        ch = ask("Select:").strip().lower()
        if not ch:
            return
        if len(ch) < 2 or not ch[1:].isdigit() or not 1 <= int(ch[1:]) <= len(paid):
            continue
        p = paid[int(ch[1:]) - 1]
        if ch[0] == "n":
            import negotiate
            negotiate.player(league, team, p, id(p) in starters)
            continue
        if ch[0] == "r":
            if _asked(p, "nil", league):
                print(paint(f"   You already asked {p.name} this year.", C.BYELLOW))
                pause()
                continue
            _mark(p, "nil", league)
            odds = 0.45 + (morale.get(p) - 55) / 120 + (0.15 if id(p) not in starters else -0.05) \
                - 0.15 * (fi.player_appetite(p) - 1)
            odds = max(0.08, min(0.85, odds))
            if _roll(f"restructure:{p.name}:{league.year}") < odds:
                cut = fi._round(p.nil * 0.25, 1_000)
                p.nil -= cut
                morale.nudge(p, -5, "took less NIL to help the budget", league)
                _log(league, f"{p.name} restructured his NIL deal (-{fi.money(cut)}/yr).")
                print(paint(f"   {p.name} agrees: {fi.money(p.nil)}/yr now. He's doing you a favor.", C.BGREEN))
            else:
                morale.nudge(p, -12, "was asked to take less NIL", league)
                print(paint(f"   {p.name} says no — and he won't forget you asked.", C.BRED))
            pause()
        elif ch[0] == "x":
            note = " He's a starter." if id(p) in starters else ""
            if ask(f"Release {p.name} and his {fi.money(p.nil)}/yr deal?{note} (y/n)").strip().lower() not in ("y", "yes"):
                continue
            team.roster.remove(p)
            for q in team.roster:
                morale.nudge(q, -2 if id(p) in starters else -1, "a teammate was cut to save money", league)
            _log(league, f"Released {p.name} ({p.position}) to free {fi.money(p.nil)}/yr.")
            print(paint(f"   {p.name} is released. The locker room noticed.", C.BYELLOW))
            pause()


# ── 2. Coordinators ──────────────────────────────────────────────────────────

def coordinators(league, team):
    import staff
    while True:
        clear()
        print(title_bar("COORDINATORS"))
        rows = []
        for role in ("OC", "DC"):
            c = getattr(team, "oc" if role == "OC" else "dc", None)
            if c is None or not fi.contract(c):
                continue
            k = fi.contract(c)
            sal = fi.salary(c)
            nxt = next((p for y, p in fi.remaining_pay(k, league, team) if y == _y(league)), sal)
            save = int(nxt - nxt * k["buyout"])
            rows.append((role, c, sal, save))
            i = len(rows)
            asked = paint("  asked", C.GRAY) if _asked(c, "cut", league) else ""
            print(f"   {i}  {pad(staff.ROLE_NAMES[role], 24)}{pad(c.name, 22)}{pad(fi.money(sal) + '/yr', 11)}"
                  f"{paint(fi.deal_line(k, league, pay=False), C.GRAY)}{asked}")
            print(paint(f"      a 15% cut saves {fi.money(sal * 0.15)}/yr  ·  letting him go saves {fi.money(save)} next "
                        f"season (you'd owe {fi.money(fi.owed(c, league))} in all)", C.GRAY))
        if not rows:
            print(paint("\n   No coordinators under contract.", C.GRAY))
            pause()
            return
        print(paint("\n   [N#] negotiate (extension, pay it back, a title...)   [C#] ask for a 15% pay cut   [F#] let him go"
                    "   [Enter] back", C.GRAY))
        ch = ask("Select:").strip().lower()
        if not ch or len(ch) < 2 or not ch[1:].isdigit() or not 1 <= int(ch[1:]) <= len(rows):
            if not ch:
                return
            continue
        role, c, sal, save = rows[int(ch[1:]) - 1]
        if ch[0] == "n":
            import negotiate
            negotiate.coordinator(league, team, role, c)
            continue
        if ch[0] == "c":
            if _asked(c, "cut", league):
                print(paint(f"   You already asked {c.name} this year.", C.BYELLOW))
                pause()
                continue
            _mark(c, "cut", league)
            odds = {"homebody": 0.6, "builder": 0.5, "climber": 0.2}.get(getattr(c, "personality", ""), 0.4)
            if _roll(f"coordcut:{c.name}:{league.year}") < odds:
                fi.contract(c)["salary"] = int(sal * 0.85)
                _log(league, f"{c.name} took a 15% pay cut.")
                print(paint(f"   {c.name} takes the cut. He believes in what you're building.", C.BGREEN))
            else:
                c.stay_lean = (league.year, 1)              # +1 = listening to other schools
                print(paint(f"   {c.name} says no. He'll be listening when other schools call.", C.BRED))
            pause()
        elif ch[0] == "f":
            import staff_room
            staff_room._fire_coord(league, team, role)


# ── 3. Position coaches ──────────────────────────────────────────────────────

def position_coaches(league, team):
    import poscoach
    while True:
        clear()
        print(title_bar("POSITION COACHES"))
        std = poscoach.POS_SHARE * fi.budget(team)
        room = [(g, c) for g, c in poscoach.staff_of(team).items() if c is not None]
        print(paint(f"   A standard coach at your level costs about {fi.money(std)}. "
                    f"Room payroll vs standard: {fi.money(poscoach.payroll_delta(team))}.", C.GRAY))
        for i, (g, c) in enumerate(room, 1):
            sal = poscoach.salary(c, team)
            extra = paint(f"  (incl. a {fi.money(c.bonus)} raise)", C.GRAY) if getattr(c, "bonus", 0) > 0 else ""
            asked = paint("  asked", C.GRAY) if _asked(c, "cut", league) else ""
            print(f"   {i}  {pad(poscoach.TITLE[g].capitalize(), 18)}{pad(c.name, 22)}{pad(fi.money(sal), 8, 'right')}"
                  f"  {paint(poscoach.fields(c).kind, C.BCYAN)}{extra}{asked}")
        print(paint("\n   [C#] ask for a 10% pay cut   [F#] let him go (an interim GA takes the room)   [Enter] back", C.GRAY))
        ch = ask("Select:").strip().lower()
        if not ch:
            return
        if len(ch) < 2 or not ch[1:].isdigit() or not 1 <= int(ch[1:]) <= len(room):
            continue
        g, c = room[int(ch[1:]) - 1]
        if ch[0] == "c":
            if _asked(c, "cut", league):
                print(paint(f"   You already asked {c.name} this year.", C.BYELLOW))
                pause()
                continue
            _mark(c, "cut", league)
            odds = {"Loyalist": 0.7, "Players' coach": 0.55, "Climber": 0.2}.get(c.kind, 0.45)
            if _roll(f"poscut:{c.name}:{league.year}") < odds:
                c.bonus = int(getattr(c, "bonus", 0) - poscoach.salary(c, team) * 0.10)
                print(paint(f"   {c.name} takes the cut.", C.BGREEN))
            else:
                c.unhappy = (league.year, "a pay cut request")
                print(paint(f"   {c.name} says no, and he's unsettled now.", C.BRED))
            pause()
        elif ch[0] == "f":
            before = poscoach.salary(c, team)
            if ask(f"Let {c.name} go? (y/n)").strip().lower() not in ("y", "yes"):
                continue
            poscoach.fire(league, team, g)
            poscoach.fill_yours(league, team)
            new = poscoach.staff_of(team).get(g)
            import staff_room
            staff_room._show_fallout(c)
            print(paint(f"   {new.name} (graduate assistant) takes the room at {fi.money(poscoach.salary(new, team))} — "
                        f"saves {fi.money(before - poscoach.salary(new, team))}.", C.BGREEN))
            pause()


# ── 4. Buyouts ───────────────────────────────────────────────────────────────

def buyouts(league, team):
    y = _y(league)
    while True:
        due = [b for b in getattr(team, "buyouts", []) if b["start"] <= y <= b["end"] and b.get("per_year", 0) > 0
               and b.get("kind") not in ("release", "deferred")]
        clear()
        print(title_bar(f"BUYOUTS DUE IN {y}"))
        if not due:
            print(paint("\n   No buyout checks due next season.", C.GRAY))
            pause()
            return
        for i, b in enumerate(due, 1):
            done = paint("  stretched", C.GRAY) if b.get("stretched") else ""
            print(f"   {i}  {pad(b['name'], 26)}{pad(b.get('role', ''), 5)}{pad(fi.money(b['per_year']), 10, 'right')}{done}")
        print(paint("\n   [S#] ask him to spread next season's check over three years (10% more in total)   [Enter] back",
                    C.GRAY))
        ch = ask("Select:").strip().lower()
        if not ch:
            return
        if len(ch) < 2 or ch[0] != "s" or not ch[1:].isdigit() or not 1 <= int(ch[1:]) <= len(due):
            continue
        b = due[int(ch[1:]) - 1]
        if b.get("stretched"):
            print(paint("   That one's already been stretched.", C.BYELLOW))
            pause()
            continue
        b["stretched"] = True
        if _roll(f"stretch:{b['name']}:{league.year}:{b['per_year']}") < 0.75:
            each = int(b["per_year"] * 1.1 / 3)
            b["per_year"] = each
            for k in (1, 2):
                team.buyouts.append({"name": b["name"], "role": b.get("role", ""), "per_year": each,
                                     "start": y + k, "end": y + k, "coach": b.get("coach"), "stretched": True})
            _log(league, f"Stretched {b['name']}'s buyout over three years.")
            print(paint(f"   His agent agrees: {fi.money(each)} a year for three years.", C.BGREEN))
        else:
            print(paint("   His agent says no. He wants his money on schedule.", C.BRED))
        pause()


# ── 5. Your salary ───────────────────────────────────────────────────────────

def your_salary(league, team):
    coach = team.coach
    k = fi.contract(coach)
    clear()
    print(title_bar("YOUR SALARY"))
    if not k or not getattr(coach, "is_user", False) and coach is not getattr(league, "user_coach", None):
        print(paint("\n   No contract of yours to change.", C.GRAY))
        pause()
        return
    sal = k["salary"]
    floor = int(k.get("_orig_salary", sal) * 0.5)
    k.setdefault("_orig_salary", sal)
    print(paint(f"\n   You make {fi.money(sal)}/yr ({fi.deal_line(k, league, pay=False)}). You can go as low as "
                f"{fi.money(floor)}.", C.GRAY))
    print(paint("   [D] defer instead: take less this year, get it back next year plus 10%", C.BYELLOW))
    raw = ask("Cut it by how much per year? (e.g. 500k, 1m — D = defer — Enter = cancel):").strip()
    if raw.lower() == "d":
        import negotiate
        negotiate.defer_own(league, team)
        return
    amt = fi.parse_money(raw) if raw else None
    if not amt or amt <= 0:
        return
    amt = min(amt, sal - floor)
    if amt <= 0:
        print(paint("   You're already at the floor.", C.BYELLOW))
        pause()
        return
    k["salary"] = int(sal - amt)
    try:
        import ad_trust
        ad_trust.change(league, min(4.0, amt / max(1, sal) * 12), "took a pay cut to help the budget")
    except Exception:
        pass
    _log(league, f"Took a {fi.money(amt)}/yr pay cut to help the budget.")
    print(paint(f"   Done: {fi.money(k['salary'])}/yr. Your AD noticed.", C.BGREEN))
    pause()


# ── 6. Facilities ────────────────────────────────────────────────────────────

def facilities(league, team):
    import facilities as fa
    y = _y(league)
    rev = {v.lower(): k for k, v in fa.SHORT.items()}
    while True:
        items = [(i, e) for i, e in enumerate(getattr(team, "fac_spend", []))
                 if e[0] == y and ((e[2].startswith("upgrade") and "stadium" not in e[2]) or e[2] == "stadium: fund deposit")]
        clear()
        print(title_bar(f"FACILITIES SPENDING IN {y}"))
        if not items:
            print(paint("\n   Nothing you can cancel — no projects or deposits on next season's books.", C.GRAY))
            pause()
            return
        for n, (i, e) in enumerate(items, 1):
            print(f"   {n}  {pad(e[2], 40)}{pad(fi.money(e[1]), 10, 'right')}")
        ch = ask("Cancel # (Enter = back):").strip()
        if not ch:
            return
        if not ch.isdigit() or not 1 <= int(ch) <= len(items):
            continue
        i, e = items[int(ch) - 1]
        if e[2] == "stadium: fund deposit":
            import stadium as sd
            sd.ensure(team)["fund"] = max(0, sd.fund(team) - e[1])
        else:
            word = e[2].split()[1]
            kind = rev.get(word)
            if kind:
                team.fac[kind] = max(1, team.fac[kind] - 1)
        team.fac_spend.pop(i)
        _log(league, f"Cancelled: {e[2]} ({fi.money(e[1])}).")
        print(paint(f"   Cancelled. {fi.money(e[1])} back in next season's budget.", C.BGREEN))
        pause()


# ── 7. Recruiting offers ─────────────────────────────────────────────────────

def recruiting(league, team):
    cycle = league.recruiting
    while True:
        offers = sorted(((r, a) for r, a in fi.offers_by(cycle, team).items() if not r.signed), key=lambda x: -x[1])
        clear()
        print(title_bar("NIL OFFERS TO RECRUITS"))
        if not offers:
            print(paint("\n   No open NIL offers to recruits.", C.GRAY))
            pause()
            return
        for i, (r, a) in enumerate(offers, 1):
            com = paint("  committed", C.BGREEN) if r.committed_to is team else ""
            print(f"   {i:>2}  {pad(r.name, 24)}{pad(r.position, 5)}{r.stars}★  {pad(fi.money(a), 9, 'right')}{com}")
        print(paint("   Pulling an offer frees the money — and costs you ground with him.", C.GRAY))
        ch = ask("Pull # (Enter = back):").strip()
        if not ch:
            return
        if ch.isdigit() and 1 <= int(ch) <= len(offers):
            ok, msg = fi.withdraw(cycle, team, offers[int(ch) - 1][0])
            print(paint(f"   {msg}", C.BGREEN if ok else C.BRED))
            pause()
