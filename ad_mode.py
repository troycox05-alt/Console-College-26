"""
ad_mode.py — Athletic Director: you run the program, not the team.

You don't call plays or recruit. You hire the coach and decide when he's done;
you write his goals and his contract; you spend the money on buildings or
players; you set ticket prices and keep the facilities from slipping; and you
tell the fans what to expect — then live with it. Above you sits the board.

THE LOOP
  Preseason   The Statement: what you tell the fans to expect this year (a
              rebuild, progress, a bowl, a title run, or the whole thing). Big
              promises buy goodwill now and cost you later if they don't come
              true. Set the coach's three goals, and your ticket prices.
  Each week   The fans react to Saturday against what they were promised; the
              boosters react to the fans, the rival game and the building. Now
              and then something lands on your desk that needs a decision.
              Your office ([C]) is open all season: facilities, maintenance,
              money, the coach's contract — and the button that fires him.
  Season end  The report card: goals, the promise, the crowd, the money. Then
              your decision on the coach — keep him, extend him (you write
              the incentives), let his deal run out, or fire him. The board
              grades you. Keep them happy and bigger jobs call; lose them and
              you're the one who's fired.
  Offseason   If the job is open, you run the search: a real list of
              candidates with real asking prices, and you make the offers.
              Other programs can come after your coach — match or let him go.

THE METERS (0-100)
  Fans       wins against what you promised, the rival, blowouts, ticket
             prices, your hires. The fans are the crowd: attendance moves
             with them, and the crowd is the home-field edge.
  Boosters   follow the fans, the rival game, big hires and new buildings.
             At season's end they write checks (added to next year's pool).
  Board      your job. Goals met, the promise kept, fans, boosters, money,
             and whether the facilities held up under you.
"""
import random

import carousel as cz
import facilities as fa
import finance as fi
from ui import C, WIDTH, ask, bar, clear, pad, paint, pause, rule, section, title_bar, truncate

# key -> (label, expected-wins shift, fan bump now, blurb)
STATEMENTS = {
    "1": ("rebuild", "A rebuilding year", -2.0, -6, "Low bar, patient fans — and a quiet stadium."),
    "2": ("progress", "Show progress", -0.8, -2, "Better than last year. A safe promise."),
    "3": ("bowl", "Bowl or bust", 0.0, 2, "What the roster says you should do. Honest."),
    "4": ("contend", "Contend for the conference", 1.0, 6, "Sells tickets. The fans will hold you to it."),
    "5": ("title", "Championship or bust", 2.2, 11, "The building goes crazy in August. December might be ugly."),
}
STATEMENT_BY_KEY = {v[0]: v for v in STATEMENTS.values()}

TICKETS = {"value": ("Value pricing", 0.06, -4.0, "fuller stands, fans like you, less money"),
           "standard": ("Standard", 0.0, 0.0, "the market price"),
           "premium": ("Premium pricing", -0.07, 6.0, "more money a seat, emptier stands, grumbling")}
MAINT = {"deferred": ("Deferred", 2.2, -40_000, "save money now; facilities slip twice as often"),
         "standard": ("Standard", 1.0, 0, "normal upkeep, included in the budget"),
         "premium": ("Premium", 0.35, 120_000, "costs more every year; facilities rarely slip")}
AD_PHILOSOPHIES = {"1": "patient", "2": "win_now", "3": "brand", "4": "budget", "5": "booster", "6": "recruiting"}


# ═══ State ══════════════════════════════════════════════════════════════════

def active(league):
    """AD mode is on — unless you're simming seasons, when your deputy runs the place the
    way any other AD would."""
    return (getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None) is not None
            and not getattr(league, "autosim", False))


def my_team(league):
    return league.ad_user["team"] if active(league) else None


def is_mine(league, team):
    return team is not None and my_team(league) is team


def _st(league):
    return league.ad_user


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def bump(league, key, amount, why=None):
    st = _st(league)
    st[key] = _clamp(st[key] + amount)
    if why:
        st.setdefault("feed", []).append((league.year, league.week, key, round(amount, 1), why))
        del st["feed"][:-40]


def expectation(league, team=None):
    """What the fans expect this season, in wins: the roster against the schedule,
    moved by what you told them."""
    team = team or my_team(league)
    st = _st(league)
    games = [g for g in league.team_games(team) if g.game_type == "Regular Season"]
    pr = st.get("promised")
    if isinstance(pr, tuple) and pr[0] == league.year and st.get("statement_locked") == league.year:
        return pr[1], len(games)                     # the bar was set in August; it doesn't move
    xw = sum(cz.win_prob(team, g.opponent_of(team), 0 if g.neutral else (1 if g.home is team else -1), league)
             for g in games)
    st = STATEMENT_BY_KEY.get(_st(league).get("statement", "bowl"))
    return max(1.0, min(len(games), xw + (st[2] if st else 0))), len(games)


# ═══ Starting out ═══════════════════════════════════════════════════════════

def start(league):
    """Create your AD and take a first job."""
    clear()
    print(title_bar("ATHLETIC DIRECTOR"))
    print(paint("\n   You hire the coach. You fire the coach. You pay for the buildings, set the prices,\n"
                "   and tell the fans what to expect. The board grades you every December.\n", C.GRAY))
    name = ask("Your name (Enter for a random one):").strip()
    if not name:
        from names import FIRST_NAMES, LAST_NAMES
        from names import full_name
        name = full_name(random)
    print()
    print(paint("   What kind of AD are you? (It shapes the contracts you write by default.)", C.GRAY))
    for k, style in AD_PHILOSOPHIES.items():
        lab, blurb, _ = cz.AD_STYLES[style]
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {pad(lab, 18)} {paint(blurb, C.GRAY)}")
    style = AD_PHILOSOPHIES.get(ask("Select (Enter = Patient):").strip(), "patient")
    team = _pick_job(league, _first_offers(league), first=True)
    _take_job(league, team, name, style, first=True)


def _first_offers(league):
    rng = random.Random(f"adjobs:{league.seed}")
    pools = [[t for t in league.teams if lo <= t.prestige < hi] for lo, hi in ((0, 52), (52, 60), (60, 70), (70, 80))]
    return [rng.choice(p) for p in pools if p]


def _pick_job(league, offers, first=False, current=None):
    while True:
        clear()
        print(title_bar("ATHLETIC DIRECTOR JOBS" if first else "THE PHONE IS RINGING"))
        print()
        for i, t in enumerate(offers, 1):
            fa.ensure(t)
            f = t.fac
            c = t.coach
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(paint(t.school, C.BWHITE, C.BOLD), 22)} "
                  f"{pad(t.conference, 12)} prestige {t.prestige:>2}   budget {fi.money(fi.budget(t)):>7}   "
                  f"facilities {f['recruiting']}/{f['training']}/{f['stadium']}")
            if c is not None:
                k = fi.contract(c)
                print(paint(f"        coach {c.name} (résumé {__import__('resume').letter(__import__('resume').reputation(c, league))}, {cz._record(c)})"
                            + (f" · signed through {k['end']}" if k else ""), C.GRAY))
        extra = "   [D] dream job — any program (sandbox)" if first else "   [Enter] stay where you are"
        print(paint(extra, C.GRAY))
        c = ask("Select:").strip().lower()
        if c.isdigit() and 1 <= int(c) <= len(offers):
            return offers[int(c) - 1]
        if first and c == "d":
            from screens import pick_team
            t = pick_team(league)
            if t is not None:
                return t
        if not first and c == "":
            return current


def _take_job(league, team, name, style, first=False):
    old = my_team(league) if active(league) else None
    if old is not None and old is not team:
        from names import FIRST_NAMES, LAST_NAMES
        st = random.choice(list(cz.AD_WEIGHTS))
        from names import full_name
        old.ad = {"name": full_name(random), "style": st,
                  "inherited": True, "since": league.year + 1}
    team.ad = {"name": name, "style": style, "inherited": False, "since": league.year, "user": True}
    fa.ensure(team)
    league.mode = "ad"
    league.user_team = None
    league.user_coach = None
    league.follow_team = team
    prev = getattr(league, "ad_user", None) or {}
    league.ad_user = {"team": team, "name": name, "style": style, "since": league.year,
                      "fans": 55 + (team.prestige - 60) * 0.2, "boosters": 55, "board": 60,
                      "statement": "bowl", "statement_year": None, "ticket": "standard",
                      "maint": {k: "standard" for k in fa.KINDS}, "feed": [], "seasons": [],
                      "career": prev.get("career", []) + [(league.year, team.school)],
                      "history": prev.get("seasons", []) + prev.get("history", []),
                      "events_seen": set(), "fire_at_end": False, "let_expire": False, "promised": None}
    league.__dict__.setdefault("career_log", []).append((league.year, f"Named athletic director at {team.school}."))


# ═══ The offices: dashboard hooks ══════════════════════════════════════════

def meter(label, v, width=20):
    col = C.BGREEN if v >= 65 else C.BYELLOW if v >= 40 else C.BRED
    return f"{paint(pad(label, 9), C.GRAY)} {paint(f'{v:>3.0f}', col, C.BOLD)} {bar(v, width, color=col)}"


def mood(v):
    return "thrilled" if v >= 80 else "happy" if v >= 62 else "restless" if v >= 45 else "angry" if v >= 28 else "furious"


def office(league):
    """The AD's office: every lever in one place."""
    import guide
    guide.tip(league, "ad_office")
    team = my_team(league)
    msg = ""
    while True:
        clear()
        st = _st(league)
        color = league.conference_color(team.conference)
        print(title_bar(f"ATHLETIC DIRECTOR {st['name'].upper()}  ·  {team.school.upper()}  ·  {league.year}", color))
        print(f"   {meter('Board', st['board'])}    {meter('Fans', st['fans'])}    {meter('Boosters', st['boosters'])}")
        exp, n = expectation(league)
        stmt = STATEMENT_BY_KEY[st["statement"]][1]
        print(paint(f"   You told them: \"{stmt}\" — they expect about {exp:.1f} wins.   {team.record} so far.", C.GRAY))
        print()
        c = team.coach
        print(section("THE HEAD COACH", color))
        if c is None:
            print(paint("   The job is open. The search happens in the offseason.", C.BYELLOW))
        else:
            k = fi.contract(c)
            interim = " (interim)" if cz.is_interim(c) else ""
            print(f"   {paint(c.name + interim, C.BWHITE, C.BOLD)}, {c.age}  ·  résumé {__import__('resume').letter(__import__('resume').reputation(c, league))}  ·  "
                  f"{cz.PERSONALITIES.get(getattr(c, 'personality', ''), ('',))[0]}  ·  "
                  f"{c.offense_scheme} / {c.defense_scheme}")
            mine = [s for s in c.history if s["school"] == team.school]
            if mine:
                print(paint(f"   Here since {c.hired_year}: {sum(s['w'] for s in mine)}-{sum(s['l'] for s in mine)}"
                            f"   ·   career {cz._record(c)}", C.GRAY))
            if k:
                bon = k.get("bonuses") or {}
                print(paint(f"   Contract: {fi.deal_line(k, league)} · buyout today "
                            f"{fi.money(fi.owed(c, league), exact=True)}" + (f" · bonuses {', '.join(fi.BONUS_LABELS[x] + ' ' + fi.money(v) for x, v in bon.items())}" if bon else "")
                            + (f" · {fi.money(k['goal_bonus'])} per goal met" if k.get("goal_bonus") else ""), C.GRAY))
            print(paint(f"   Public pressure: {cz.seat_label(c.seat)}", C.GRAY))
            for g in getattr(team, "goals", [])[:3]:
                status, x = cz.goal_status(team, c, g, league.year)
                tag = paint("✔ met " + str(x), C.BGREEN) if status == "met" else \
                    paint("✘ missed", C.BRED) if status == "failed" else paint(f"{x} season{'s' if x != 1 else ''} left", C.GRAY)
                print(f"   • {pad(g.label, 52)} {tag}")
        print()
        print(section("THE PROGRAM", color))
        f = team.fac
        avail = fi.available(league, team)
        print(f"   Budget {fi.money(fi.budget(team))}  ·  available for next season "
              f"{paint(fi.money(avail), C.BGREEN if avail >= 0 else C.BRED, C.BOLD)}  ·  tickets: "
              f"{TICKETS[st['ticket']][0]}")
        print("   Facilities  " + "   ".join(
            f"{fa.SHORT[k]} {paint(str(f[k]), C.BWHITE, C.BOLD)} {paint('(' + MAINT[st['maint'][k]][0].lower() + ' upkeep)', C.GRAY)}"
            for k in fa.KINDS))
        import finance_screens
        nh, avg, fill, sold = finance_screens.season_crowds(league, team)
        if nh:
            print(paint(f"   Crowds: {nh} home game{'s' if nh != 1 else ''}, average {avg:,} ({fill * 100:.0f}%), "
                        f"{sold} sellout{'s' if sold != 1 else ''}", C.GRAY))
        recent = [x for x in st.get("feed", []) if x[0] == league.year][-4:]
        if recent:
            print()
            print(section("WHAT PEOPLE ARE SAYING", color))
            for yr, wk, key, amt, why in reversed(recent):
                col = C.BGREEN if amt > 0 else C.BRED
                print(f"   {paint(f'Wk {wk:>2}', C.GRAY)}  {paint(pad(key.title(), 8), C.GRAY)} "
                      f"{paint(f'{amt:+.0f}', col, C.BOLD)}  {why}")
        if msg:
            print(paint(f"\n   {msg}", C.BYELLOW))
            msg = ""
        print(rule())
        in_season = 1 <= league.week <= 13 and not league.season_complete
        acts = ["[F] facilities", "[U] upkeep", "[T] tickets", "[$] budget", "[G] coach's goals",
                "[E] extend the coach"]
        if league.week == 0:
            acts.insert(0, "[S] preseason statement")
        if in_season and c is not None and not cz.is_interim(c):
            acts.append(paint("[X] fire the coach now", C.BRED))
        acts += ["[Y] compliance", "[H] history", "[B] back"]
        print("   " + "   ".join(acts))
        ch = ask("Select:").strip().lower()
        if ch == "y":
            import compliance_screens
            compliance_screens.hub(league)
        elif ch == "f":
            finance_screens.facilities_screen(league, team)
        elif ch == "u":
            upkeep_screen(league)
        elif ch == "t":
            tickets_screen(league)
        elif ch == "$":
            finance_screens.budget_screen(league, team)
        elif ch == "g":
            msg = goals_screen(league)
        elif ch == "e" and c is not None and not cz.is_interim(c):
            msg = extension_screen(league)
        elif ch == "s" and league.week == 0:
            statement_screen(league)
        elif ch == "x" and in_season and c is not None and not cz.is_interim(c):
            msg = fire_now(league)
        elif ch == "h":
            history_screen(league)
        else:
            return


# ═══ Levers ═════════════════════════════════════════════════════════════════

def statement_screen(league):
    st = _st(league)
    team = my_team(league)
    games = [g for g in league.team_games(team) if g.game_type == "Regular Season"]
    xw = sum(cz.win_prob(team, g.opponent_of(team), 0 if g.neutral else (1 if g.home is team else -1), league)
             for g in games)
    clear()
    print(title_bar(f"THE {league.year} STATEMENT  ·  WHAT DO YOU TELL THE FANS?"))
    print(paint(f"\n   The roster against this schedule projects to about {xw:.1f} wins. What you say today sets the\n"
                "   bar the fans will measure every Saturday against. A big promise sells tickets now; a broken one\n"
                "   costs you twice in December — with the fans and with the board.\n", C.GRAY))
    for k, (key, lab, shift, now, blurb) in STATEMENTS.items():
        cur = paint("  ← current", C.BCYAN) if key == st["statement"] else ""
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {pad(lab, 28)} bar ≈ {max(1, xw + shift):4.1f} wins   "
              f"{paint(blurb, C.GRAY)}{cur}")
    c = ask("Select (Enter = keep):").strip()
    if c in STATEMENTS:
        key, lab, shift, now, _ = STATEMENTS[c]
        if st.get("statement_year") == league.year:
            prev = STATEMENT_BY_KEY[st["statement"]][3]
            bump(league, "fans", -prev)                      # changing your story takes back the first one
        st["statement"], st["statement_year"] = key, league.year
        bump(league, "fans", now, f"you told them: \"{lab}\"")
        if now > 0:
            bump(league, "boosters", now * 0.5)


def tickets_screen(league):
    st = _st(league)
    clear()
    print(title_bar("TICKET PRICES"))
    print(paint("\n   Applies to every home game from here on. Money is settled at season's end.\n", C.GRAY))
    keys = list(TICKETS)
    for i, k in enumerate(keys, 1):
        lab, fill, dollars, blurb = TICKETS[k]
        cur = paint("  ← current", C.BCYAN) if k == st["ticket"] else ""
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(lab, 18)} crowd {fill * 100:+.0f}%   "
              f"{'+' if dollars >= 0 else '-'}${abs(dollars):.0f} a fan   {paint(blurb, C.GRAY)}{cur}")
    c = ask("Select (Enter = keep):").strip()
    if c.isdigit() and 1 <= int(c) <= len(keys):
        st["ticket"] = keys[int(c) - 1]


def upkeep_screen(league):
    st = _st(league)
    team = my_team(league)
    while True:
        clear()
        print(title_bar("FACILITY UPKEEP"))
        print(paint("\n   Every offseason each facility can slip a level (the better it is, the likelier). Upkeep is\n"
                    "   what you spend to stop that — or what you save by letting it go. Billed every offseason.\n", C.GRAY))
        for i, k in enumerate(fa.KINDS, 1):
            lv = team.fac[k]
            m = st["maint"][k]
            base = fa.DEGRADE_BASE + fa.DEGRADE_PER_LEVEL * lv
            cost = MAINT[m][2] * lv
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(fa.LABELS[k], 22)} level {lv:>2}   "
                  f"{pad(MAINT[m][0], 9)} slip chance {base * MAINT[m][1] * 100:4.1f}%   "
                  f"{('costs ' + fi.money(cost)) if cost > 0 else ('saves ' + fi.money(-cost)) if cost < 0 else 'in the budget'}/yr")
        print(paint("\n   Pick a facility to cycle deferred → standard → premium.   [B] back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c in ("1", "2", "3"):
            k = fa.KINDS[int(c) - 1]
            order = list(MAINT)
            st["maint"][k] = order[(order.index(st["maint"][k]) + 1) % len(order)]
        else:
            return


def goals_screen(league):
    team = my_team(league)
    c = team.coach
    if league.week != 0 and not league.season_complete:
        return "Goals are set before the season. You can change them next preseason."
    tier = getattr(team, "goal_tier", None) or cz._tier(team)
    picks = []
    while True:
        clear()
        print(title_bar(f"GOALS FOR {'THE HEAD COACH' if c is None else c.name.upper()}"))
        print(paint("\n   Three goals. They're how the public — and your board — keep score on the coach, and you can pay\n"
                    "   him for each one he hits. Ambitious goals raise the pressure on him; soft ones lower it.\n", C.GRAY))
        print(paint("   Current: " + "; ".join(g.label for g in getattr(team, "goals", [])), C.GRAY))
        print()
        menu = []
        seen = set()
        for tr in (max(1, tier - 1), tier, min(5, tier + 1)):
            for g in cz._goal_menu(team, league, tr):
                if g.label not in seen:
                    seen.add(g.label)
                    menu.append((tr, g))
        for i, (tr, g) in enumerate(menu, 1):
            level = "easier" if tr < tier else "harder" if tr > tier else "standard"
            mark = paint(" ★", C.BYELLOW) if any(p.label == g.label for p in picks) else "  "
            print(f"  {mark}{paint(f'{i:>2}', C.BYELLOW)}  {pad(g.label, 58)} {paint(level, C.GRAY)}")
        print(paint(f"\n   Picked {len(picks)}/3.   [#] pick   [C] clear   [K] keep current   [Enter] save", C.GRAY))
        ch = ask("Select:").strip().lower()
        if ch.isdigit() and 1 <= int(ch) <= len(menu):
            g = menu[int(ch) - 1][1]
            if any(p.kind == g.kind for p in picks):
                continue
            if len(picks) < 3:
                g.why = "AD priority"
                picks.append(g)
        elif ch == "c":
            picks = []
        elif ch == "k":
            return ""
        elif ch == "" and picks:
            team.goals = picks[:3]
            team.goals_set = league.year if league.week == 0 else league.year + 1
            hard = sum(1 for tr, g in menu if tr > tier and any(p.label == g.label for p in picks))
            easy = sum(1 for tr, g in menu if tr < tier and any(p.label == g.label for p in picks))
            if c is not None:
                c.seat = _clamp(c.seat + hard * 4 - easy * 3)
            if hard:
                bump(league, "boosters", 2 * hard, "you set ambitious goals for the coach")
            return "Goals set: " + "; ".join(g.short for g in picks)
        elif ch == "":
            return ""


# ═══ Contracts: offers and extensions you write ═══════════════════════════

def _offer_value_ratio(league, coach, offer):
    """How good this offer looks to him: salary against his price, sweetened by
    incentives he thinks he can hit and a buyout that protects him."""
    ask_ = fi.asking(league, coach, "HC")
    if not ask_:
        return 2.0
    b = offer.get("bonuses") or {}
    likely = {"bowl": 0.6, "conf_title": 0.2, "cfp": 0.15, "title": 0.04}
    sweet = sum(v * likely.get(k, 0.1) for k, v in b.items()) + offer.get("goal_bonus", 0) * 1.2
    ratio = (offer["salary"] + sweet) / ask_
    ratio += (offer.get("buyout", 0.6) - 0.6) * 0.3                    # guaranteed money matters
    ratio += (offer["years"] - 5) * 0.015                               # so does security
    return ratio


def build_offer(league, team, coach, base, title):
    """Let you write the deal. Returns the offer dict, or None."""
    offer = dict(base)
    offer["bonuses"] = dict(base.get("bonuses") or {})
    offer.setdefault("goal_bonus", 0)
    while True:
        clear()
        print(title_bar(title))
        ask_ = fi.asking(league, coach, "HC")
        r = _offer_value_ratio(league, coach, offer)
        feel = "he'd sign today" if r >= 1.1 else "he's interested" if r >= 0.95 else \
            "he'll want more" if r >= 0.8 else "insulting"
        print(paint(f"\n   {coach.name} thinks he's worth about {fi.money(ask_)}/yr.   Your budget: "
                    f"{fi.money(fi.budget(team))} (a head coach usually takes {int(fi.HC_SHARE * 100)}%, "
                    f"never more than {int(fi.HC_CAP * 100)}%).\n", C.GRAY))
        print(f"   {paint('[1]', C.BYELLOW)} Salary        {fi.money(offer['salary'])}/yr")
        print(f"   {paint('[2]', C.BYELLOW)} Years         {offer['years']}")
        print(f"   {paint('[3]', C.BYELLOW)} Buyout        {offer['buyout'] * 100:.0f}% of what's left if you fire him "
              f"{paint('(higher = he feels safer; lower = cheaper to fire)', C.GRAY)}")
        print(f"   {paint('[4]', C.BYELLOW)} Bonuses       " + (", ".join(f"{fi.BONUS_LABELS[k]} {fi.money(v)}"
                                                                        for k, v in offer['bonuses'].items()) or "none"))
        print(f"   {paint('[5]', C.BYELLOW)} Goal bonus    {fi.money(offer['goal_bonus'])} for every goal he meets in a season")
        print(f"   {paint('[6]', C.BYELLOW)} Rollover      {'yes — every 8-win season adds a year' if offer.get('rollover') else 'no'}")
        print()
        print(f"   How it reads to him: {paint(feel.upper(), C.BGREEN if r >= 0.95 else C.BYELLOW if r >= 0.8 else C.BRED, C.BOLD)}"
              f"  {paint(f'(value {r:.2f}x his price)', C.GRAY)}")
        print(rule())
        print(paint("   [#] change a term   [O] make the offer   [B] walk away", C.GRAY))
        c = ask("Select:").strip().lower()
        if c == "1":
            v = fi.parse_money(ask("Salary per year (e.g. 3.5m):"))
            if v:
                offer["salary"] = int(min(v, fi.HC_CAP * fi.budget(team)))
        elif c == "2":
            v = ask("Years (2-8):").strip()
            if v.isdigit() and 2 <= int(v) <= 8:
                offer["years"] = int(v)
        elif c == "3":
            v = ask("Buyout percent (30-100):").strip()
            if v.isdigit() and 30 <= int(v) <= 100:
                offer["buyout"] = int(v) / 100
        elif c == "4":
            for k in fi.BONUS_SPLIT:
                v = ask(f"Bonus for {fi.BONUS_LABELS[k]} (Enter = {fi.money(offer['bonuses'].get(k, 0))}, 0 = none):").strip()
                if v:
                    amt = fi.parse_money(v)
                    if amt:
                        offer["bonuses"][k] = int(amt)
                    else:
                        offer["bonuses"].pop(k, None)
        elif c == "5":
            v = fi.parse_money(ask("Bonus per goal met (e.g. 100k, 0 = none):"))
            offer["goal_bonus"] = int(v or 0)
        elif c == "6":
            offer["rollover"] = not offer.get("rollover")
        elif c == "o":
            return offer
        elif c == "b":
            return None


def extension_screen(league):
    team = my_team(league)
    c = team.coach
    base = fi.hc_offer(league, team, c, extension=True)
    k = fi.contract(c)
    if k:
        base["salary"] = max(base["salary"], k["salary"])
        base["years"] = max(base["years"], k["end"] - league.year + 2)
        base["goal_bonus"] = k.get("goal_bonus", 0)
    offer = build_offer(league, team, c, base, f"EXTEND {c.name.upper()}")
    if offer is None:
        return ""
    r = _offer_value_ratio(league, c, offer)
    need = 0.9 if c.seat <= 40 else 0.8                           # a coach under fire takes security
    if k and offer["salary"] < k["salary"] * 0.97:
        need += 0.15                                              # nobody likes a pay cut
    if r < need:
        return f"{c.name} passes. He wants a better deal than that."
    fi.extend(league, team, c, random.Random(), "", offer, news=False)
    c.contract["goal_bonus"] = offer.get("goal_bonus", 0)
    cz._news(league, "extended", f"{team.school} extends {c.name} through {c.contract['end']} "
                                 f"({fi.terms(offer, total=False)})")
    bump(league, "fans", 3 if c.seat < 45 else -4, f"you extended {c.name}")
    c.seat = _clamp(c.seat - 6)
    return f"Done: {c.name} is signed through {c.contract['end']} at {fi.money(c.contract['salary'])}/yr."


def fire_now(league):
    team = my_team(league)
    c = team.coach
    owed = fi.owed(c, league)
    ok = ask(f"Fire {c.name} now? The school owes him {fi.money(owed)}. An interim finishes the season. "
             f"Type FIRE:").strip().upper()
    if ok != "FIRE":
        return ""
    st = _st(league)
    cz.fire_midseason(league, team, random.Random(f"adfire:{league.year}:{league.week}"))
    if st["fans"] < 42:
        bump(league, "fans", 8, f"you fired {c.name} — the fans wanted it")
    else:
        bump(league, "fans", -5, f"you fired {c.name} mid-season — a lot of people didn't see it coming")
    bump(league, "boosters", 3 if st["boosters"] < 45 else -3)
    league.__dict__.setdefault("career_log", []).append((league.year, f"Fired head coach {c.name} in week {league.week} ({team.record})."))
    return f"{c.name} is out. {team.coach.name} is the interim head coach."


def history_screen(league):
    st = _st(league)
    clear()
    print(title_bar(f"{st['name'].upper()} — AD CAREER"))
    print()
    for yr, school in st.get("career", []):
        print(f"   {yr}  AD at {school}")
    print()
    for s in st.get("seasons", []):
        print(f"   {s['year']}  {s['school']:<16} {s['rec']:<6} promise: {s['promise']:<28} kept: "
              f"{'yes' if s['kept'] else 'no ':<4} goals {s['goals']}  board {s['board']:.0f}  fans {s['fans']:.0f}")
    print()
    for yr, text in getattr(league, "career_log", [])[-12:]:
        print(f"   {paint(str(yr), C.GRAY)}  {text}")
    pause()


# ═══ The season: preseason, each week, the reactions ═════════════════════

def preseason(league):
    """Before week 1: the statement, the goals, the prices. Returns True to play on."""
    st = _st(league)
    if st.get("preseason_done") == league.year:
        return True
    team = my_team(league)
    exp, _ = expectation(league)
    clear()
    print(title_bar(f"{league.year} PRESEASON  ·  THE AD'S DESK  ·  {team.school.upper()}",
                    league.conference_color(team.conference)))
    print(paint(f"\n   Before the season: tell the fans what to expect, set the coach's goals, and price the tickets.\n", C.GRAY))
    statement_screen(league)
    msg = goals_screen(league)
    tickets_screen(league)
    st["preseason_done"] = league.year
    st["promised"] = (league.year, expectation(league)[0])
    st["statement_locked"] = league.year
    if msg:
        print(paint(f"\n   {msg}", C.BYELLOW))
    pause("Press Enter for Week 1...")
    return True


# Something lands on your desk. (id, needs(league, team, st) -> bool, text, [(label, effects)])
# effects: dict of fans/boosters/board bumps, money (+ in / - out), special keys.
def _events(league, team, st):
    b = fi.budget(team)
    c = team.coach
    rival = cz.PRIMARY_RIVAL.get(team.school)
    losing = team.losses > team.wins and team.wins + team.losses >= 3
    ev = []
    ev.append(("naming", st["boosters"] >= 45 and team.fac["stadium"] >= 4,
               f"A regional bank wants its name on {team.stadium}: {fi.money(b * 0.06)} a year, ten years.",
               [("Take the money", {"money": b * 0.06, "fans": -5, "boosters": 2}),
                ("Tradition isn't for sale", {"fans": 3, "boosters": -1})]))
    ev.append(("weight_room", True,
               "The weight room's HVAC died in August heat. A proper fix is "
               f"{fi.money(team.fac['training'] * 60_000)}; a patch job is cheap but won't last.",
               [("Fix it properly", {"money": -team.fac["training"] * 60_000}),
                ("Patch it", {"slip": "training"})]))
    ev.append(("recruit_staff", c is not None,
               f"{c.name if c else 'The coach'} wants {fi.money(b * 0.015)} for two more recruiting staffers this year.",
               [("Approve it", {"money": -b * 0.015, "hours": 6, "seat": -3}),
                ("Not this year", {"seat": 4})]))
    ev.append(("fire_banner", losing and st["fans"] < 45 and c is not None,
               f"A plane is flying a 'FIRE {c.name.split()[-1].upper() if c else 'HIM'}' banner over campus. "
               "Reporters want a statement.",
               [("Vote of confidence", {"fans": -4, "board": 2, "seat": -8}),
                ("\"Everything will be evaluated\"", {"fans": 3, "seat": 10}),
                ("No comment", {})]))
    ev.append(("students", st["fans"] < 60 and team.fac["stadium"] <= 7,
               f"The student section has been half-empty. A student-ticket promotion would cost {fi.money(b * 0.004)}.",
               [("Run it", {"money": -b * 0.004, "fans": 4, "fill": 0.04}), ("Pass", {})]))
    ev.append(("board_video", fa.ensure(team) is not None and team.stad["parts"]["video_board"] < 4,
               f"A vendor pitches a new video board: {fi.money(b * 0.05)}, installed before next week. "
               "Louder, prettier, better.",
               [("Buy it", {"money": -b * 0.05, "fans": 3, "boosters": 3, "noise": True}), ("Not now", {})]))
    ev.append(("donor", st["boosters"] >= 60,
               f"A big donor will give {fi.money(b * 0.08)} — if it goes to a facility project with his name on it.",
               [("Accept", {"money": b * 0.08, "boosters": 3, "earmark": True}), ("Decline", {"boosters": -2})]))
    ev.append(("rival_talk", bool(rival) and league.week <= 10,
               f"{rival}'s AD took a shot at your program on the radio this morning.",
               [("Fire back", {"fans": 4, "boosters": 2, "rival": True}), ("Take the high road", {"board": 1})]))
    ev.append(("tv", team.prestige >= 55,
               f"The network wants to move a home game to a Tuesday night: {fi.money(b * 0.02)} for the privilege.",
               [("Take the TV money", {"money": b * 0.02, "fans": -3}), ("Saturdays are for football", {"fans": 2})]))
    ev.append(("nil", True,
               f"The NIL collective is short. Moving {fi.money(b * 0.03)} of department money to player NIL would "
               "help the next class — but it's money you can't spend on buildings.",
               [("Move the money", {"money": -b * 0.03, "nil": b * 0.03, "boosters": 2}), ("Keep it", {})]))
    return [e for e in ev if e[1]]


def _apply(league, team, eff, label):
    st = _st(league)
    for key in ("fans", "boosters", "board"):
        if eff.get(key):
            bump(league, key, eff[key], label)
    money = eff.get("money", 0)
    if money > 0:
        team.__dict__.setdefault("income", []).append({"what": label, "amount": int(money), "year": league.year + 1})
    elif money < 0 and not eff.get("nil"):
        team.fac_spend.append((league.year + 1, int(-money), label))
    if eff.get("nil"):
        pass                                                    # it was always player money — nothing moves
    if eff.get("hours"):
        team.ad_hours = (league.year, eff["hours"])
    if eff.get("seat") and team.coach is not None:
        team.coach.seat = _clamp(team.coach.seat + eff["seat"])
    if eff.get("slip"):
        st.setdefault("slip_risk", {})[eff["slip"]] = league.year
    if eff.get("fill"):
        prev = st.get("fill_bonus") or (0, 0.0)
        st["fill_bonus"] = (league.year, (prev[1] if prev[0] == league.year else 0.0) + eff["fill"])
    if eff.get("noise"):
        import stadium
        if stadium.upgrade_now(team, "video_board") is None:
            st["noise_bonus"] = league.year                     # already the best board there is: just louder
    if eff.get("earmark"):
        st["earmark"] = league.year
    if eff.get("cp"):
        import compliance
        for ln in compliance.apply_fx(league, team, eff["cp"]) or []:
            st.setdefault("feed", []).append((league.year, league.week, "board", 0, ln))


def week_hub(league):
    """Before each week: how it's going, this Saturday, and maybe a decision. Returns True to play."""
    team = my_team(league)
    st = _st(league)
    if league.week == 0 and not preseason(league):
        return False
    rng = random.Random(f"adweek:{league.seed}:{league.year}:{league.week}")
    event = None
    import compliance_events
    event = compliance_events.ad_desk_event(league, team)    # a CAB matter comes before anything else
    if event is None and rng.random() < 0.45:
        seen = st.setdefault("events_seen", set())
        pool = [e for e in _events(league, team, st) if (league.year, e[0]) not in seen]
        if pool:
            event = rng.choice(pool)
            seen.add((league.year, event[0]))
    while True:
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"{league.week_name(league.week + 1).upper()}  ·  THE AD'S DESK  ·  {team.school.upper()}", color))
        print(f"   {meter('Board', st['board'])}    {meter('Fans', st['fans'])}    {meter('Boosters', st['boosters'])}")
        exp, n = expectation(league)
        print(paint(f"   {team.record} · the fans expect about {exp:.1f} wins · they're {mood(st['fans'])}", C.GRAY))
        last = [x for x in st.get("feed", []) if x[0] == league.year and x[1] == league.week]
        if last:
            print()
            for _, wk, key, amt, why in last[-3:]:
                col = C.BGREEN if amt > 0 else C.BRED
                print(f"   {paint(pad(key.title(), 9), C.GRAY)}{paint(f'{amt:+.0f}', col, C.BOLD)}  {why}")
        g = next((x for x in league.schedule.get(league.week + 1, []) if team in (x.home, x.away)), None)
        print()
        if g is None:
            print(paint("   Bye week.", C.GRAY))
        else:
            opp = g.opponent_of(team)
            home = g.home is team and not g.neutral
            rk = league.rankings.rank_of(opp)
            line = f"   This week: {'vs' if home or g.neutral else 'at'} {('#' + str(rk) + ' ') if rk else ''}{opp.school}"
            if home:
                att, cap, fill, why = fa.forecast(league, g)
                line += paint(f"   ·   expected crowd {'SELLOUT' if fill >= 0.985 else f'{att:,} ({fill * 100:.0f}%)'}", C.GRAY)
            print(line)
        if event is not None:
            eid, _, text, choices = event
            print()
            print(section("ON YOUR DESK", C.BYELLOW))
            for ln in _wrap(text):
                print("   " + ln)
            for i, (lab, _) in enumerate(choices, 1):
                print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {lab}")
        print(rule())
        print(paint("   [Enter] on to Saturday   [C] AD office" + ("   [1-3] decide" if event else ""), C.GRAY))
        ch = ask("Select:").strip().lower()
        if event is not None and ch.isdigit() and 1 <= int(ch) <= len(event[3]):
            lab, eff = event[3][int(ch) - 1]
            _apply(league, team, eff, f"{lab.lower()} ({event[0].replace('_', ' ')})")
            event = None
            continue
        if ch == "c":
            office(league)
            continue
        if event is not None and ch == "":
            _apply(league, team, event[3][-1][1], "you let it sit")     # no decision is a decision
        return True


def _wrap(text, w=WIDTH - 8):
    import textwrap
    return textwrap.wrap(text, w)


def after_week(league, games):
    """The fans and boosters react to Saturday."""
    if not active(league):
        return
    team = my_team(league)
    st = _st(league)
    g = next((x for x in games if team in (x.home, x.away) and x.played), None)
    for k in ("fans", "boosters"):
        st[k] += (55 - st[k]) * 0.02                          # moods drift back toward normal
    if g is None:
        return
    opp = g.opponent_of(team)
    won = g.winner is team
    site = 0 if g.neutral else (1 if g.home is team else -1)
    p = cz.win_prob(team, opp, site, league)
    shift = STATEMENT_BY_KEY[st["statement"]][2]
    pressure = 1 + max(0, shift) * 0.18                       # a big promise makes every loss louder
    delta = (1 - p) * 9 if won else -p * 9 * pressure
    rival = cz.PRIMARY_RIVAL.get(team.school) == opp.school or cz.PRIMARY_RIVAL.get(opp.school) == team.school
    ranks = getattr(g, "ranks", {}) or {}
    margin = g.score_for(team) - g.score_for(opp)
    why = f"{'beat' if won else 'lost to'} {opp.school} {g.score_for(team)}-{g.score_for(opp)}"
    if rival:
        delta *= 2.0
        why += " — the rival"
    if won and ranks.get(opp):
        delta += 3
    if not won and margin <= -21:
        delta -= 3
        why += ", and it wasn't close"
    # The season against what you promised them.
    exp, n = expectation(league)
    played = team.wins + team.losses
    pace = team.wins - exp * played / max(1, n)
    delta += max(-2, min(2, pace * 0.6))
    if g.home is team and not g.neutral:
        tk = st["ticket"]
        delta += {"value": 0.8, "standard": 0.0, "premium": -1.0}[tk]
    bump(league, "fans", delta, why)
    bump(league, "boosters", delta * 0.55 + (3 if rival and won else -2 if rival else 0))


# ═══ Attendance hook ════════════════════════════════════════════════════════

def fill_shift(league, game):
    """How your decisions move the crowd at your home games."""
    if not active(league) or game.home is not my_team(league) or game.neutral:
        return 0.0
    st = _st(league)
    shift = (st["fans"] - 55) * 0.003 + TICKETS[st["ticket"]][1]
    fb = st.get("fill_bonus")
    if fb and fb[0] == league.year:
        shift += fb[1]
    return shift


def noise_shift(league, game):
    if active(league) and game.home is my_team(league) and _st(league).get("noise_bonus") == league.year:
        return 3.0                                    # the new video board and sound: louder, like a bigger building
    return 0.0


def degrade_mult(league, team, kind):
    if not is_mine(league, team):
        return 1.0
    st = _st(league)
    m = MAINT[st["maint"][kind]][1]
    if st.get("slip_risk", {}).get(kind) == league.year:
        m *= 2.5                                               # the patch job didn't hold
    return m


def recruiting_hours(team, league):
    h = getattr(team, "ad_hours", None)
    return h[1] if h and h[0] == league.year else 0


# ═══ Season's end ═══════════════════════════════════════════════════════════

def season_review(league):
    """The report card, the board's verdict on you, and your call on the coach."""
    if not active(league):
        return
    team = my_team(league)
    st = _st(league)
    c = team.coach
    s = cz.season_line(league, team)
    exp = expectation(league)[0]
    kept = s["w"] >= exp - 0.5
    goals = getattr(team, "goals", [])
    graded = [g for g in goals if g.kind != "recruit" and g.applies(s)]   # the class is graded on signing day
    met = [g for g in graded if g.achieved(s)]
    missed = [g for g in graded if not g.achieved(s)]
    # ── the money ────────────────────────────────────────────────────
    homes = [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played
             and getattr(g, "attendance", None)]
    ticket_money = int(sum(g.attendance for g in homes) * TICKETS[st["ticket"]][2])
    donations = int(fi.budget(team) * max(0, st["boosters"] - 45) / 100 * 0.25)
    maint = sum(MAINT[st["maint"][k]][2] * team.fac[k] for k in fa.KINDS)
    for what, amt in (("ticket pricing", ticket_money), ("booster donations", donations), ("facility upkeep", -maint)):
        if amt > 0:
            team.__dict__.setdefault("income", []).append({"what": what, "amount": amt, "year": league.year + 1})
        elif amt < 0:
            team.fac_spend.append((league.year + 1, -amt, what))
    # Goal bonuses in his contract.
    k = fi.contract(c) if c is not None else None
    if k and k.get("goal_bonus") and met and not cz.is_interim(c):
        pay = k["goal_bonus"] * len(met)
        fi.credit(c, pay)
        fi._books(team, league.year).append((f"goal bonuses to {c.name} ({len(met)} met)", pay))
    # ── the board ────────────────────────────────────────────────────
    shift = STATEMENT_BY_KEY[st["statement"]][2]
    d = (len(met) - len(missed)) * 4 + (st["fans"] - 50) * 0.25 + (st["boosters"] - 50) * 0.15
    d += 4 if kept else -(3 + max(0, shift) * 3)
    d += 10 * bool(s.get("title")) + 5 * bool(s.get("cfp")) + 3 * bool(s.get("conf_champ"))
    avail = fi.available(league, team)
    d += 2 if avail >= 0 else -8
    slipped = sum(1 for k2 in fa.KINDS if team.fac[k2] < team.fac_start[k2])
    grown = sum(1 for k2 in fa.KINDS if team.fac[k2] > team.fac_start[k2])
    d += grown * 1.5 - slipped * 3
    first_year = league.year == st["since"]
    if first_year:
        d = max(d, -6)                                          # the board gives a new AD a year
    before = st["board"]
    st["board"] = _clamp(st["board"] + d)
    if not kept:
        bump(league, "fans", -(2 + max(0, shift) * 3), "the season fell short of what you promised")
    st["seasons"].append({"year": league.year, "school": team.school, "rec": f"{s['w']}-{s['l']}",
                          "promise": STATEMENT_BY_KEY[st["statement"]][1], "kept": kept,
                          "goals": f"{len(met)}/{len(met) + len(missed)}", "board": st["board"], "fans": st["fans"]})
    # ── the report card ─────────────────────────────────────────────
    clear()
    color = league.conference_color(team.conference)
    print(title_bar(f"{league.year} REPORT CARD  ·  AD {st['name'].upper()}  ·  {team.school.upper()}", color))
    print()
    print(f"   {team.school} went {paint(s['w'], C.BWHITE, C.BOLD)}-{s['l']}. You promised "
          f"\"{STATEMENT_BY_KEY[st['statement']][1]}\" — about {exp:.1f} wins. "
          + (paint("Promise kept.", C.BGREEN, C.BOLD) if kept else paint("Promise broken.", C.BRED, C.BOLD)))
    for g in goals:
        tag = paint("✔", C.BGREEN) if g in met else paint("✘", C.BRED) if g in missed else paint("–", C.GRAY)
        note = paint("  (graded on signing day)", C.GRAY) if g.kind == "recruit" else ""
        print(f"   {tag} {g.label}{note}")
    import finance_screens
    nh, avg, fill, sold = finance_screens.season_crowds(league, team)
    if nh:
        print(paint(f"   Crowds: average {avg:,} ({fill * 100:.0f}% full), {sold} sellout{'s' if sold != 1 else ''}", C.GRAY))
    print(paint(f"   Money for next year: tickets {fi.money(ticket_money)}, boosters {fi.money(donations)}, "
                f"upkeep {fi.money(-maint)}", C.GRAY))
    if slipped or grown:
        print(paint(f"   Facilities: {grown} above where you found them, {slipped} below.", C.GRAY))
    print()
    print(f"   {meter('Fans', st['fans'])}    {meter('Boosters', st['boosters'])}")
    col = C.BGREEN if st["board"] >= before else C.BRED
    chg = f"({st['board'] - before:+.0f})"
    print(f"   {meter('Board', st['board'])}  {paint(chg, col, C.BOLD)}")
    # ── the verdict on you ──────────────────────────────────────────
    if st["board"] < 22 and not first_year:
        print(paint("\n   The board has relieved you of your duties.", C.BRED, C.BOLD))
        league.__dict__.setdefault("career_log", []).append((league.year, f"Fired as athletic director at {team.school}."))
        pause()
        lower = sorted((t for t in league.teams if t.prestige < team.prestige - 4 and t is not team),
                       key=lambda t: -t.prestige)
        rng = random.Random(f"adfired:{league.year}")
        offers = rng.sample(lower[:25], min(3, len(lower[:25]))) if lower else []
        if offers:
            new = _pick_job(league, offers, current=None)
            if new is not None:
                _take_job(league, new, st["name"], st["style"])
                return
        league.mode = "spectator"
        league.ad_user = None
        print(paint("\n   You're out of the business. The world goes on without you.", C.GRAY))
        pause()
        return
    if st["board"] < 35:
        print(paint("\n   The board is losing patience. Another year like this and you're done.", C.BRED))
    pause()
    coach_decision(league)
    _career_offers(league)


def _career_offers(league):
    """A good AD gets calls from bigger schools."""
    st = _st(league)
    team = my_team(league)
    tenure = league.year - st["since"] + 1
    if st["board"] < 75 or tenure < 3:
        return
    rng = random.Random(f"adoffers:{league.year}")
    up = [t for t in league.teams if team.prestige + 5 <= t.prestige <= team.prestige + 20]
    if not up or rng.random() > 0.6:
        return
    offers = rng.sample(up, min(2, len(up)))
    new = _pick_job(league, offers, current=team)
    if new is not None and new is not team:
        _take_job(league, new, st["name"], st["style"])


def coach_decision(league):
    """Keep him, extend him, let the deal run out, or fire him."""
    team = my_team(league)
    st = _st(league)
    st["fire_at_end"] = st["let_expire"] = False
    c = team.coach
    if c is None or cz.is_interim(c):
        if c is not None:
            print(paint(f"\n   {c.name} coached the rest of the year as interim. The job is open — the search is yours.", C.BYELLOW))
            pause()
        return
    k = fi.contract(c)
    expiring = k is not None and k["end"] <= league.year
    while True:
        clear()
        print(title_bar(f"DECISION: {c.name.upper()}"))
        mine = [s for s in c.history if s["school"] == team.school]
        print()
        print(f"   {c.name}, {c.age}  ·  {len(mine) + 1} season{'s' if mine else ''} here  ·  "
              f"{sum(s['w'] for s in mine) + team.wins}-{sum(s['l'] for s in mine) + team.losses} at {team.school}")
        print(paint(f"   Fans are {mood(st['fans'])} ({st['fans']:.0f}) · boosters {st['boosters']:.0f} · "
                    f"public pressure: {cz.seat_label(c.seat)}", C.GRAY))
        if k:
            print(paint(f"   Contract through {k['end']} · firing him costs {fi.money(fi.owed(c, league))}"
                        + (" · his deal is up" if expiring else ""), C.GRAY))
        print()
        print(f"   {paint('[K]', C.BGREEN, C.BOLD)} Keep him" + (" (you'll have to extend him — his deal is up)" if expiring else ""))
        print(f"   {paint('[E]', C.BYELLOW, C.BOLD)} Extend him — write the new deal")
        if expiring:
            print(f"   {paint('[L]', C.BYELLOW, C.BOLD)} Let his contract run out — no buyout, open search")
        print(f"   {paint('[F]', C.BRED, C.BOLD)} Fire him" + (f" — {fi.money(fi.owed(c, league))} buyout" if k else ""))
        ch = ask("Your call:").strip().lower()
        if ch == "k" and not expiring:
            bump(league, "fans", -4 if st["fans"] < 40 else 1, f"you're keeping {c.name}")
            return
        if ch == "e" or (ch == "k" and expiring):
            msg = extension_screen(league)
            if msg:
                print(paint("   " + msg, C.BYELLOW))
                pause()
                if msg.startswith("Done"):
                    return
            continue
        if ch == "l" and expiring:
            st["let_expire"] = {"coach": c.name, "school": team.school, "year": league.year}
            bump(league, "fans", 4 if st["fans"] < 45 else -2, f"you let {c.name}'s contract run out")
            return
        if ch == "f":
            if ask(f"Fire {c.name}? Type FIRE:").strip().upper() == "FIRE":
                st["fire_at_end"] = {"coach": c.name, "school": team.school, "year": league.year}
                bump(league, "fans", 8 if st["fans"] < 42 else -6, f"you fired {c.name}")
                bump(league, "boosters", 4 if st["boosters"] < 45 else -4)
                return


# ═══ Carousel hooks ════════════════════════════════════════════════════════

def carousel_verdict(league, team):
    """Your decision, applied in the carousel's firing step. Returns 'fired' / 'not retained' / None."""
    st = _st(league)
    c = team.coach
    out = None
    for key, verdict in (("fire_at_end", "fired"), ("let_expire", "not retained")):
        call = st.get(key)
        st[key] = False
        # Only the coach you made the call on, at this school, this winter. If he's already gone
        # (retired, took another job, you moved to another school), the call goes with him.
        if isinstance(call, dict) and out is None and c is not None and call.get("coach") == c.name \
                and call.get("school") == team.school and call.get("year") == league.year:
            out = verdict
        elif call is True and out is None and c is not None:
            out = verdict                                  # a save from before v14: the call as it was made
    return out


def keep_coach_prompt(league, coach, offer):
    """Another school wants your coach. Returns True if he stays."""
    team = my_team(league)
    st = _st(league)
    raw = ask(f"\n   {coach.name} has an offer elsewhere: {fi.terms(offer, total=False)}. Match it to keep him? "
              f"(y/n)").strip().lower()
    if raw not in ("y", "yes"):
        bump(league, "fans", -3, f"you let {coach.name} walk")
        return False
    match = min(int(offer["salary"]), int(fi.HC_CAP * fi.budget(team)))
    if match < offer["salary"] * 0.95:
        print(paint(f"   Your budget can't match that. {coach.name} is gone.", C.BRED))
        pause()
        return False
    stay = 0.75 if getattr(coach, "personality", "") != "mercenary" else 0.5
    if random.Random(f"keep:{coach.name}:{league.year}").random() >= stay:
        print(paint(f"   You matched. He's going anyway.", C.BRED))
        pause()
        return False
    fi.extend(league, team, coach, random.Random(), "", {"salary": match, "years": 5, "buyout": 0.65, "role": "HC",
                                                        "bonuses": (fi.contract(coach) or {}).get("bonuses", {})},
              news=False)
    coach._retained = league.year
    cz._news(league, "extended", f"{coach.name} stays at {team.school} after the AD matched another offer")
    bump(league, "fans", 4, f"you kept {coach.name} from leaving")
    print(paint(f"   {coach.name} stays.", C.BGREEN))
    pause()
    return True


def candidates(league, team, rng):
    sitting = [t.coach for t in league.teams if t.coach is not None and t is not team and t.coach.history
               and not cz.is_interim(t.coach) and t.prestige < team.prestige + 6
               and not cz.off_market(t.coach, league)]
    pool = [c for c in league.coach_pool if c.status == "unemployed"
            and getattr(c, "_last_exit", {}).get("school") != team.school]
    import staff
    coords = staff.head_coach_candidates(league, team)
    seen, out = set(), []
    for c in pool + sitting + coords:
        if id(c) in seen:
            continue
        seen.add(id(c))
        out.append((cz.candidate_score(team, c, league, random.Random(0), sitting=c in sitting), c))
    out.sort(key=lambda x: -x[0])
    return [c for _, c in out[:16]]


def _interest(league, team, c, offer=None):
    """(odds 0-1, words): how likely he is to say yes to a market-rate offer, from
    what his agent tells you. Personalities differ; so does his situation."""
    if offer is None:
        offer = fi.hc_offer(league, team, c)
        offer["salary"] = int(min(fi.HC_CAP * fi.budget(team), max(offer["salary"], fi.asking(league, c, "HC"))))
    yes = sum(cz.will_accept(c, team, league, random.Random(f"int:{c.name}:{league.year}:{i}"), offer)
              for i in range(12)) / 12
    words = "very interested" if yes >= 0.75 else "interested" if yes >= 0.45 else \
        "would listen" if yes >= 0.2 else "long shot" if yes > 0 else "not leaving"
    return yes, words


def _decline_reason(league, team, c, offer):
    ratio = fi.money_ratio(league, c, offer, "HC")
    if ratio < 0.85:
        return "wants more money"
    if c.team is None:
        return "is waiting for a bigger job"
    if getattr(c, "role", "HC") in ("OC", "DC"):
        return "isn't ready to leave his staff"
    tenure = league.year - (c.hired_year or league.year) + 1
    tr = cz.PERSONALITIES.get(getattr(c, "personality", ""), cz.PERSONALITIES["builder"])[2]
    if tenure < tr["settle"]:
        return "just got to his school and wants to finish what he started"
    if team.prestige - c.team.prestige < tr["min_jump"]:
        return "doesn't see this as enough of a step up"
    return "is happy where he is"


def _cls(c):
    import resume
    ranks = [s.get("class_rank") for s in c.history[-4:] if s.get("class_rank")]
    return resume.letter(resume.recruit_rep(c)) if ranks else "—"


def coach_search(league, rng):
    """Your job is open: find the next head coach."""
    import resume
    team = my_team(league)
    st = _st(league)
    tried = set()
    while team.coach is None:
        cands = [c for c in candidates(league, team, rng) if id(c) not in tried]
        clear()
        print(title_bar(f"{team.school.upper()} HEAD COACH SEARCH  ·  {league.year}"))
        print(paint(f"\n   Budget {fi.money(fi.budget(team))} — a head coach usually takes about "
                    f"{fi.money(fi.HC_SHARE * fi.budget(team))}. Fans {st['fans']:.0f} ({mood(st['fans'])}).\n", C.GRAY))
        print(paint(f"   {'#':>3}  {'COACH':<22}{'NOW':<26}{'AGE':>4}{'RES':>5}{'CLS':>5}  {'RECORD':<12}{'ASKS':>8}  "
                    f"{'BUYOUT':>8}  INTEREST", C.GRAY, C.BOLD))
        cache = st.setdefault("_interest", {})
        for i, c in enumerate(cands, 1):
            key_ = (league.year, c.name)
            if key_ not in cache:
                cache[key_] = _interest(league, team, c)
            odds, words = cache[key_]
            col = C.BGREEN if odds >= 0.45 else C.BYELLOW if odds >= 0.2 else C.BRED
            now = (f"{c.team.school} {getattr(c, 'role', 'HC')}" if c.team is not None else
                   ("out of coaching" if c.history else getattr(c, "origin", "") or "—"))
            fee = fi.release_fee(c, league) if c.team is not None and getattr(c, "role", "HC") == "HC" else 0
            print(f"  {paint(f'{i:>3}', C.BYELLOW)}  {pad(truncate(c.name, 21), 22)}{pad(truncate(now, 25), 26)}"
                  f"{c.age:>4}{resume.letter(resume.reputation(c, league)):>5}{_cls(c):>5}  {pad(cz._record(c), 12)}"
                  f"{fi.money(fi.asking(league, c, 'HC')):>8}  {fi.money(fee) if fee else '—':>8}  "
                  f"{paint(words, col)}")
        print(paint("   You see what everyone sees: RES = his résumé (results against what the roster should have done,\n"
                    "   the level, rings), CLS = his recruiting classes. Nobody knows how good a coach is until he coaches.\n"
                    "   BUYOUT = the release fee you'd pay his school. Interest is his\n"
                    "   agent's read on a market-rate offer — pay more, add incentives or security and the odds go up.", C.GRAY))
        print(rule())
        print(paint("   [#] look at him / make an offer   [S] let a search firm handle it   ", C.GRAY))
        ch = ask("Select:").strip().lower()
        if ch == "s":
            return False
        if not (ch.isdigit() and 1 <= int(ch) <= len(cands)):
            continue
        c = cands[int(ch) - 1]
        import coach_screens
        coach_screens.coach_view(league, c, scout=True)
        base = fi.hc_offer(league, team, c, rng)
        base["salary"] = int(min(fi.HC_CAP * fi.budget(team),
                                 max(base["salary"], round(fi.asking(league, c, "HC") / 25_000) * 25_000)))
        offer = build_offer(league, team, c, base, f"OFFER TO {c.name.upper()}")
        if offer is None:
            continue
        r = _offer_value_ratio(league, c, offer)
        eff = dict(offer)
        eff["salary"] = int(fi.asking(league, c, "HC") * r)            # what the whole package is worth to him
        ok = cz.will_accept(c, team, league, rng, eff)
        if ok and c.team is not None and getattr(c, "role", "HC") == "HC" and fi.retention_counter(league, c, eff, rng):
            print(paint(f"\n   {c.team.school} matched. {c.name} is staying put.", C.BRED))
            tried.add(id(c))
            pause()
            continue
        if not ok:
            print(paint(f"\n   {c.name} turns you down — he {_decline_reason(league, team, c, eff)}.", C.BRED))
            tried.add(id(c))
            pause()
            continue
        fee = fi.release_fee(c, league) if c.team is not None and getattr(c, "role", "HC") == "HC" else 0
        cz.hire(league, team, c, "pool" if c.team is None else "poach", offer)
        if team.coach is c and fi.contract(c):
            c.contract["goal_bonus"] = offer.get("goal_bonus", 0)
        react = (resume.reputation(c, league) - team.prestige) * 0.4 + cz.track_record(c, league) * 25 + (4 if fee else 0)
        react = max(-8, min(12, react))
        bump(league, "fans", react, f"you hired {c.name}")
        bump(league, "boosters", react * 0.8 + (3 if fee else 0))
        league.__dict__.setdefault("career_log", []).append((league.year, f"Hired {c.name} as head coach ({fi.terms(offer, total=False)})."))
        print(paint(f"\n   {c.name} is your new head coach.", C.BGREEN, C.BOLD))
        pause()
        return True
    return True
