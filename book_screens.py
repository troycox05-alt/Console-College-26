"""
book_screens.py — The Window: the sportsbook hub (Spectator mode).

One hub, eight tabs, a bet slip that follows you around:

  B BOARD        this week's games: spread, total, moneyline, where the line opened
  L LOOK-AHEAD   every week still to come — the lines are up all season and move weekly
  F FUTURES      national title · conferences · win totals · make the playoff · Golden Helmet
  P PROPS        the featured games: yards and anytime touchdowns
  S SLIP         straight bets, parlays, teasers
  M MY BETS      what's live, what it pays, and how the number has moved since
  R RECORD       your bankroll over time, results by bet type, every settled ticket
  A ATS          every team against the number (and over/under)
  D STANDINGS    you against the regulars (regulars.py): profiles, their tickets, tail or fade

Quick picks anywhere on a board:  12 opens game 12 · 12a / 12h spread (away/home)
· 12ma / 12mh moneyline · 12o / 12u total. Add an amount to bet it straight now:
"12h 50", "12o $100", "12a 5%" (of your bankroll).
"""
import sportsbook as sb
from ui import C, WIDTH, ask, clear, columns, command_bar, key, pad, paint, panel, pause, section, title_bar, truncate

BRAND = C.BGREEN
TABS = [("B", "BOARD"), ("L", "LOOK-AHEAD"), ("F", "FUTURES"), ("P", "PROPS"), ("S", "SLIP"), ("M", "MY BETS"),
        ("R", "RECORD"), ("A", "ATS"), ("D", "STANDINGS")]
SHOWN = {"LOOK-AHEAD": "AHEAD"}              # the tab strip is 100 columns
PAGE = 9
SPARK = "▁▂▃▄▅▆▇█"
STATUS = {"won": ("✔", C.BGREEN), "lost": ("✘", C.BRED), "push": ("↺", C.BYELLOW), "void": ("↺", C.GRAY),
          None: ("•", C.BCYAN)}


# ═══ Little pieces ═════════════════════════════════════════════════════════

def spark(values, width=26):
    vals = list(values)[-width:]
    if len(vals) < 2:
        return paint("▁" * max(1, len(vals)), C.GRAY)
    lo, hi = min(vals), max(vals)
    rng_ = (hi - lo) or 1
    out = ""
    for i, v in enumerate(vals):
        ch = SPARK[int((v - lo) / rng_ * (len(SPARK) - 1))]
        up = i == 0 or v >= vals[i - 1]
        out += paint(ch, C.BGREEN if up else C.BRED)
    return out


def money_col(x, sign=True):
    return paint(sb.money(x, sign=sign), C.BGREEN if x > 0 else C.BRED if x < 0 else C.GRAY, C.BOLD)


def rank(league, t):
    r = league.rankings.rank_of(t)
    return f"#{r} " if r else ""


def team_cell(league, t, w, follow=None):
    name = rank(league, t) + t.school
    rec = f" ({t.record})"
    col = C.BMAGENTA if t is follow else C.BWHITE
    return pad(paint(truncate(name, w - len(rec)), col, C.BOLD) + paint(rec, C.GRAY), w)


def odds_p(a, width=5):
    return paint(pad(sb.fmt_odds(a), width, "right"), C.GRAY)


def book_title(league):
    return title_bar(f"THE WINDOW  ·  SPORTSBOOK  ·  {league.year}", BRAND)


def _in_slip(book, leg):
    k = leg.key()
    return any(x.key() == k for x in book.slip)


# ═══ The header: bankroll, action, record ══════════════════════════════════

def kpis(league, book):
    bank = book.bank
    d = bank - book.start - book.reloads * sb.RELOAD
    pct = d / book.start * 100 if book.start else 0
    col = C.BGREEN if d >= 0 else C.BRED
    left = [paint(sb.money(bank), col, C.BOLD) + paint("  bankroll", C.GRAY),
            paint(("▲ " if d >= 0 else "▼ ") + sb.money(d, sign=True) + f" ({pct:+.1f}%)", col)
            + paint(" since start", C.GRAY),
            spark([x[2] for x in book.ledger] + [bank]) + (paint(f"  {book.reloads} reload" + ("s" if book.reloads != 1 else ""),
                                                                   C.BYELLOW) if book.reloads else "")]
    op = book.open_bets
    mid = [paint(f"{len(op)} open", C.BWHITE, C.BOLD) + paint(f" · {sb.money(book.at_risk())} at risk", C.GRAY),
           paint("to win ", C.GRAY) + paint(sb.money(book.to_win_open()), C.BGREEN, C.BOLD),
           paint(f"slip: {len(book.slip)} leg" + ("s" if len(book.slip) != 1 else ""), C.BYELLOW if book.slip else C.GRAY)
           + (paint(f" · {len(book.unseen)} new results", C.BMAGENTA) if book.unseen else "")]
    sett = book.settled_bets
    w, l, p, risked, net = sb.record(sett)
    roi = net / risked * 100 if risked else 0.0
    season = book.seasons.get(league.year, 0.0)
    right = [paint(f"{w}-{l}" + (f"-{p}" if p else ""), C.BWHITE, C.BOLD)
             + paint(f"  ({w / (w + l) * 100:.1f}% winners)" if w + l else "  no results yet", C.GRAY),
             paint("ROI ", C.GRAY) + paint(f"{roi:+.1f}%", C.BGREEN if roi >= 0 else C.BRED, C.BOLD)
             + paint(f" on {sb.money(risked)}", C.GRAY),
             paint(f"{league.year}: ", C.GRAY) + money_col(season)]
    return columns(panel("BANKROLL", left, 34, color=BRAND, title_color=BRAND),
                   panel("ACTION", mid, 32, color=C.GRAY), panel("RECORD", right, 32, color=C.GRAY))


def header(league, book, tab):
    clear()
    print(book_title(league))
    wk = league.week + 1
    status = ("Season complete — futures are settled; the new season's lines go up in the preseason."
              if league.season_complete else
              f"{league.week_name(wk)} lines are up" + (" · preseason futures and win totals are open"
                                                         if league.week == 0 else ""))
    print(paint("   " + status, C.GRAY))
    for ln in kpis(league, book):
        print(ln)
    names = []
    for i, (k, name) in enumerate(TABS, 1):
        label = SHOWN.get(name, name) + (f" ({len(book.slip)})" if k == "S" and book.slip else "")
        names.append(f"{k} {label}")
    print(_tab_strip(names, tab))


def _tab_strip(names, active):
    from ui import bg, on
    cells = []
    for i, n in enumerate(names):
        cells.append(paint(f" {n} ", on(BRAND), bg(BRAND), C.BOLD) if i == active else paint(f" {n} ", C.GRAY))
    return paint("│", C.GRAY).join(cells)


def footer(extra, leave=True):
    items = extra + ([key("Q", "leave the window", C.BRED)] if leave else [])
    for ln in command_bar(items):
        print(ln)


# ═══ The board ═════════════════════════════════════════════════════════════

VIEWS = ["all", "top 25", "close (≤7)", "your team", "my action", "conference"]


def _view_games(league, book, games, view, conf=None):
    follow = getattr(league, "follow_team", None)
    rk = league.rankings.rank_of
    if view == "top 25":
        games = [g for g in games if rk(g.home) or rk(g.away)]
    elif view == "close (≤7)":
        games = [g for g in games if sb.line(book, league, g) and abs(sb.line(book, league, g)["spread"]) <= 7]
    elif view == "your team":
        games = [g for g in games if follow in (g.home, g.away)]
    elif view == "my action":
        games = [g for g in games if sb.my_action(book, g)]
    elif view == "conference" and conf:
        games = [g for g in games if conf in (g.home.conference, g.away.conference)]
    return games


def _order(league, book, games):
    rk = league.rankings.rank_of
    follow = getattr(league, "follow_team", None)

    def k(g):
        r = [x for x in (rk(g.home), rk(g.away)) if x]
        ln = sb.line(book, league, g)
        return (0 if follow in (g.home, g.away) else 1, -len(r), min(r) if r else 99,
                abs(ln["spread"]) if ln else 99)
    return sorted(games, key=k)


def board_lines(league, book, games, start):
    """Two lines a game: prefix 7 · team 34 · spread 13 · total 12 · money 7 · note 18 (= 100)."""
    follow = getattr(league, "follow_team", None)
    out = [paint(f"{'':7}{'MATCHUP':<34}{'SPREAD':>13}   {'TOTAL':>12}   {'MONEY':>7}   ", C.GRAY, C.BOLD)]
    from commentary import rivalry_name
    for i, g in enumerate(games[start:start + PAGE], start + 1):
        ln = sb.line(book, league, g)
        if ln is None:
            continue
        legs = sb.game_legs(book, league, g)
        act = sb.my_action(book, g)
        mark = paint("★", C.BMAGENTA, C.BOLD) if act else " "
        op = sb.opening(book, g)
        move = ""
        if op and op[1] != ln["spread"]:
            d = op[1] - ln["spread"]
            who = g.home if d > 0 else g.away
            move = paint(truncate(f"moved {sb.fmt_num(abs(d))} → {who.abbr}", 18), C.BCYAN)
        riv = rivalry_name(g.home, g.away)
        if riv:
            tag = paint(truncate("★ " + riv, 18), C.BMAGENTA)
        elif g.game_type != "Regular Season":
            tag = paint(truncate(getattr(g, "bowl_name", None) or g.game_type, 18), C.BYELLOW)
        elif g.conference_game:
            tag = paint(truncate(g.home.conference, 18), C.GRAY)
        else:
            tag = ""
        fav_home = ln["spread"] < 0

        def cell(code, main, juice, w, strong):
            lg_ = legs.get(code)
            if lg_ is None:
                return pad(paint("—", C.GRAY), w, "right")
            if _in_slip(book, lg_):
                return paint(pad(main + (" " + juice if juice else ""), w, "right"), C.BLACK, C.BOLD, "\033[42m")
            body = paint(main, C.BWHITE if strong else C.GRAY, C.BOLD if strong else "") \
                + (" " + paint(juice, C.GRAY) if juice else "")
            return pad(body, w, "right")
        ml = ln["ml"]
        rows = ((g.away, "sa", -ln["spread"], "o", "O", "ma", ml[0] if ml else None, not fav_home, tag),
                (g.home, "sh", ln["spread"], "u", "U", "mh", ml[1] if ml else None, fav_home, move))
        for n, (t, sc, spv, tc, tl, mc, mlv, fav, note) in enumerate(rows):
            if n == 0:
                pre = f" {mark}{paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  "
                name = team_cell(league, t, 34, follow)
            else:
                at = "vs" if g.neutral else "@"
                pre = " " * 7
                name = paint(at + " ", C.GRAY) + team_cell(league, t, 34 - len(at) - 1, follow)
            out.append(pre + pad(name, 34) + cell(sc, sb.fmt_line(spv), "-110", 13, fav)
                       + "   " + cell(tc, f"{tl} {sb.fmt_num(ln['total'])}", "-110", 12, False)
                       + "   " + cell(mc, sb.fmt_odds(mlv) if mlv is not None else "", "", 7, fav)
                       + "   " + note)
    return out


def parse_pick(c):
    """'12h 50' → (12, 'sh', '50'); '12' → (12, None, None)."""
    import re
    m = re.match(r"^(\d+)\s*(a|h|ma|mh|o|u)?(?:\s+(\$?[\d,.]+%?|max))?$", c.strip().lower())
    if not m:
        return None
    n, code, amt = int(m.group(1)), m.group(2), m.group(3)
    code = {"a": "sa", "h": "sh"}.get(code, code)
    return n, code, amt


def board_tab(league, book, st, week):
    games = sb.games_in(league, week)
    games = _order(league, book, _view_games(league, book, games, st["view"], st.get("conf")))
    st["games"] = games
    pages = max(1, (len(games) + PAGE - 1) // PAGE)
    st["page"] = min(st["page"], pages - 1)
    title = f"{league.week_name(week).upper()}  ·  {len(games)} game{'s' if len(games) != 1 else ''}  ·  view: {st['view']}" \
        + (f" ({st.get('conf')})" if st["view"] == "conference" else "") + f"  ·  page {st['page'] + 1}/{pages}"
    print(section(title, BRAND))
    if not games:
        print(paint("\n   Nothing on the board here." if st["view"] == "all" else "\n   No games in this view — [V] changes it.",
                    C.GRAY))
    for ln in board_lines(league, book, games, st["page"] * PAGE):
        print(ln)
    print(paint("   12 game page · 12a/12h spread · 12ma/12mh money · 12o/12u total · '12h 50' bets $50 now"
                " · ★ your action", C.GRAY))


# ═══ A game page ═══════════════════════════════════════════════════════════

def game_screen(league, book, g):
    while True:
        ln = sb.line(book, league, g)
        clear()
        print(book_title(league))
        at = "vs" if g.neutral else "at"
        print(paint(f"   {league.week_name(g.week).upper()}  ·  {g.away.school.upper()} {at} {g.home.school.upper()}",
                    C.BWHITE, C.BOLD))
        where = (g.venue if g.neutral else f"{g.home.stadium}") + ("  ·  conference game" if g.conference_game else "")
        from commentary import rivalry_name
        riv = rivalry_name(g.home, g.away)
        print(paint(f"   {where}" + (f"  ·  {riv}" if riv else "") + (f"  ·  {g.bowl_name}" if getattr(g, "bowl_name", None) else ""),
                    C.GRAY))
        if g.week == league.week + 1:
            try:
                import weather
                f = weather.forecast(g, league)
                col = C.BRED if f["severity"] >= 3 else C.BYELLOW if f["severity"] >= 2 else C.BCYAN
                print(paint("   Forecast: ", C.GRAY) + paint(f["headline"] + ("" if f["indoor"] else f" · {f['temp']}°"), col))
            except Exception:
                pass
        print()
        import scout
        for t in (g.away, g.home):
            ats = book.ats.get(t, [0, 0, 0])
            ou = book.ou.get(t, [0, 0, 0])
            hurt = [p for p in t.injured() if p in t.players_at(p.position)[:2]][:3]
            strength = scout.team(t.team_ovr, league, who=t)
            print(f"   {pad(paint(rank(league, t) + t.school, C.BWHITE, C.BOLD), 30)}{paint(t.record, C.BWHITE):<6}  "
                  + paint("ATS ", C.GRAY) + f"{ats[0]}-{ats[1]}" + (f"-{ats[2]}" if ats[2] else "")
                  + paint("   O/U ", C.GRAY) + f"{ou[0]}-{ou[1]}" + (f"-{ou[2]}" if ou[2] else "")
                  + paint("   rating ", C.GRAY) + strength)
            last = [x for x in league.team_games(t) if x.played][-3:]
            if last:
                bits = []
                for x in last:
                    won = x.winner is t
                    bits.append(paint("W" if won else "L", C.BGREEN if won else C.BRED)
                                + paint(f" {x.score_for(t)}-{x.score_for(x.opponent_of(t))} {x.opponent_of(t).abbr}", C.GRAY))
                print("      " + paint("last: ", C.GRAY) + paint(" · ", C.GRAY).join(bits)
                      + (paint("   OUT: " + ", ".join(f"{p.position} {p.last_name}" for p in hurt), C.BRED) if hurt else ""))
        h = book.hist.get(g, [])
        if h:
            path = " → ".join(f"{lab.replace('Week ', 'Wk ')} {g.home.abbr} {sb.fmt_line(sp)}, {sb.fmt_num(tt)}"
                              for lab, sp, tt in h[-4:])
            print(paint(f"\n   LINE HISTORY  ", BRAND, C.BOLD) + paint(truncate(path, WIDTH - 18), C.GRAY))
        if ln is None:
            print(paint("\n   This one's off the board.", C.GRAY))
            pause()
            return
        legs = sb.game_legs(book, league, g)
        opts = []

        def add(code):
            if code in legs:
                opts.append(legs[code])
                return len(opts)
            return None

        def cell(code, txt, w=30):
            n = add(code)
            if n is None:
                return pad(paint("—", C.GRAY), w)
            chosen = _in_slip(book, legs[code])
            body = pad(txt, w - 5)
            return paint(f"[{n:>2}] ", C.BYELLOW, C.BOLD) + (paint(body, C.BLACK, C.BOLD, "\033[42m") if chosen else body)
        a, hm = g.away, g.home
        print()
        print(section("GAME LINES", BRAND))
        print(paint(f"   {'':<20}{'SPREAD':<30}{'TOTAL':<30}MONEYLINE", C.GRAY, C.BOLD))
        print(f"   {pad(truncate(a.school, 19), 20)}{cell('sa', sb.fmt_line(-ln['spread']) + '  (-110)')}"
              f"{cell('o', 'Over ' + sb.fmt_num(ln['total']) + '  (-110)')}{cell('ma', sb.fmt_odds(ln['ml'][0]) if ln['ml'] else '', 16)}")
        print(f"   {pad(truncate(hm.school, 19), 20)}{cell('sh', sb.fmt_line(ln['spread']) + '  (-110)')}"
              f"{cell('u', 'Under ' + sb.fmt_num(ln['total']) + '  (-110)')}{cell('mh', sb.fmt_odds(ln['ml'][1]) if ln['ml'] else '', 16)}")
        print(section("FIRST HALF & TEAM TOTALS", C.BCYAN))
        print(paint(f"   {'':<18}{'1ST HALF SPREAD':<22}{'1ST HALF TOTAL':<24}TEAM TOTAL", C.GRAY, C.BOLD))
        print(f"   {pad(truncate(a.school, 17), 18)}{cell('h1a', '1H ' + sb.fmt_line(-ln['h1']), 22)}"
              f"{cell('h1o', '1H Over ' + sb.fmt_num(ln['h1t']), 24)}{cell('tao', 'Over ' + sb.fmt_num(ln['tt'][0]), 16)}"
              f"{cell('tau', 'Under ' + sb.fmt_num(ln['tt'][0]), 16)}")
        print(f"   {pad(truncate(hm.school, 17), 18)}{cell('h1h', '1H ' + sb.fmt_line(ln['h1']), 22)}"
              f"{cell('h1u', '1H Under ' + sb.fmt_num(ln['h1t']), 24)}{cell('tho', 'Over ' + sb.fmt_num(ln['tt'][1]), 16)}"
              f"{cell('thu', 'Under ' + sb.fmt_num(ln['tt'][1]), 16)}")
        if g.week == league.week + 1 and g in sb.featured(book, league, g.week):
            props = sb.props_for(book, league, g)
            if props:
                print(section("PLAYER PROPS", C.BMAGENTA))
                row = []
                for lg_ in props:
                    opts.append(lg_)
                    n = len(opts)
                    chosen = _in_slip(book, lg_)
                    txt = truncate(f"{lg_.label} ({sb.fmt_odds(lg_.odds)})", 42)
                    row.append(paint(f"[{n:>2}] ", C.BYELLOW, C.BOLD)
                               + (paint(pad(txt, 42), C.BLACK, C.BOLD, "\033[42m") if chosen else pad(txt, 42)))
                    if len(row) == 2:
                        print("   " + "  ".join(row))
                        row = []
                if row:
                    print("   " + row[0])
        else:
            print(paint("   Player props go up the week of the game, for the featured matchups.", C.GRAY))
        act = sb.my_action(book, g)
        if act:
            print(section("YOUR ACTION", C.BMAGENTA))
            for b in act:
                print("   " + _bet_line(league, book, b))
        rail = rail_on(book, g)
        if rail:
            print(section("THE REGULARS ON THIS GAME", C.BCYAN))
            for ln_ in rail[:6]:
                print(ln_)
        print()
        footer([key("#", "add to slip (1,4,7)"), key("# $", "bet it now (e.g. 2 50)"),
                key("S", f"slip ({len(book.slip)})", C.BGREEN), key("B", "back")], leave=False)
        c = ask("Pick:").strip().lower()
        if c in ("b", "q", ""):
            return
        if c == "s":
            slip_screen(league, book)
            continue
        parts = c.replace(",", " ").split()
        if (len(parts) == 2 and parts[0].isdigit() and 1 <= int(parts[0]) <= len(opts) and _is_amount(parts[1])
                and (not parts[1].isdigit() or int(parts[1]) > len(opts))):
            straight_now(league, book, opts[int(parts[0]) - 1], parts[1])        # "2 50": bet it now
            continue
        picked = [int(x) for x in parts if x.isdigit() and 1 <= int(x) <= len(opts)]
        if picked and len(picked) == len(parts):
            for n in picked:
                toggle(book, opts[n - 1])
            continue
        msg("A number (or several) adds to your slip; a number and an amount bets it now.")


def _is_amount(s):
    s = s.strip().lower().replace("$", "").replace(",", "")
    if s == "max":
        return True
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s) > 0
    except ValueError:
        return False


def msg(text, color=C.BYELLOW):
    print(paint("   " + text, color))
    pause()


def toggle(book, leg):
    k = leg.key()
    for x in list(book.slip):
        if x.key() == k:
            book.slip.remove(x)
            return False
    book.slip.append(leg)
    return True


# ═══ Stakes and confirmation ═══════════════════════════════════════════════

def read_stake(book, raw=None, cap=None):
    """'50', '$1,000', '5%', 'max' → dollars (or None)."""
    top = min(book.bank, cap) if cap else book.bank
    if raw is None:
        raw = ask(f"Stake (bankroll {sb.money(book.bank)} · 5% = {sb.money(round(book.bank * 0.05, 2))} · Enter = cancel):")
    s = raw.strip().lower().replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        if s == "max":
            v = top
        elif s.endswith("%"):
            v = book.bank * float(s[:-1]) / 100
        else:
            v = float(s)
    except ValueError:
        msg("That's not an amount.")
        return None
    v = round(v, 2)
    if v < 1:
        msg("The window's minimum is $1.")
        return None
    if v > top + 1e-9:
        msg(f"You can bet up to {sb.money(top)}.")
        return None
    return v


def confirm(desc, stake, odds):
    win = round(stake * (sb.dec(odds) - 1), 2)
    print()
    print("   " + paint("TICKET  ", BRAND, C.BOLD) + paint(desc, C.BWHITE, C.BOLD))
    print("   " + paint("Risk ", C.GRAY) + paint(sb.money(stake), C.BWHITE, C.BOLD) + paint(" at ", C.GRAY)
          + paint(sb.fmt_odds(odds), C.BYELLOW, C.BOLD) + paint("  →  to win ", C.GRAY) + paint(sb.money(win), C.BGREEN, C.BOLD)
          + paint(f"  (pays {sb.money(stake + win)})", C.GRAY))
    c = ask("Place it? [Enter/Y] yes · [N] no:").strip().lower()
    return c in ("", "y", "yes")


def _placed(b):
    print(paint(f"   ✔ Ticket #{b.id} — {b.title()}: {sb.money(b.stake)} to win {sb.money(b.to_win)}.", C.BGREEN, C.BOLD))
    pause()


def straight_now(league, book, leg, raw=None):
    if not sb.still_open(league, leg):
        msg("That market's closed.")
        return
    stake = read_stake(book, raw)
    if stake is None:
        return
    if not confirm(leg.label, stake, leg.odds):
        return
    b, why = sb.place(book, league, "straight", [leg], stake)
    if why:
        msg(why, C.BRED)
        return
    for x in list(book.slip):
        if x.key() == leg.key():
            book.slip.remove(x)
    _placed(b)


# ═══ The slip ══════════════════════════════════════════════════════════════

def slip_screen(league, book):
    while True:
        book.slip = [x for x in book.slip if sb.still_open(league, x)]
        clear()
        print(book_title(league))
        for ln in kpis(league, book):
            print(ln)
        slip_body(league, book)
        c = ask("Slip:").strip().lower()
        if not slip_key(league, book, c):
            return


def slip_body(league, book):
    print(section(f"BET SLIP  ·  {len(book.slip)} leg" + ("s" if len(book.slip) != 1 else ""), BRAND))
    if not book.slip:
        print(paint("\n   Empty. Pick lines off the board (12h, 12o...), a game page, props or futures.", C.GRAY))
        footer([key("B", "back")])
        return
    games = {}
    for lg_ in book.slip:
        if lg_.game is not None:
            games[id(lg_.game)] = games.get(id(lg_.game), 0) + 1
    for i, lg_ in enumerate(book.slip, 1):
        where = ""
        if lg_.game is not None:
            g = lg_.game
            where = f"{league.week_name(g.week)} · {g.away.abbr} {'vs' if g.neutral else '@'} {g.home.abbr}"
        else:
            where = "futures"
        same = paint("  same game", C.BYELLOW) if lg_.game is not None and games[id(lg_.game)] > 1 else ""
        print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {pad(truncate(lg_.label, 52), 53)}"
              f"{paint(pad(sb.fmt_odds(lg_.odds), 6, 'right'), C.BWHITE, C.BOLD)}   {paint(truncate(where, 26), C.GRAY)}{same}")
    print()
    stakes = paint("   STRAIGHT  ", C.BWHITE, C.BOLD) + paint(f"each leg its own bet — $100 each wins "
                                                            f"{sb.money(sum(100 * (sb.dec(x.odds) - 1) for x in book.slip))}", C.GRAY)
    print(stakes)
    why = sb.parlay_problem(book.slip)
    if why is None:
        odds, d = sb.parlay_odds(book.slip)
        print(paint("   PARLAY    ", C.BWHITE, C.BOLD) + paint(sb.fmt_odds(odds), C.BYELLOW, C.BOLD)
              + paint(f"  —  $10 pays {sb.money(10 * d)} · $100 pays {sb.money(100 * d)}", C.GRAY))
    else:
        print(paint("   PARLAY    ", C.GRAY, C.BOLD) + paint(why, C.GRAY))
    tw = sb.teaser_problem(book.slip)
    if tw is None:
        n = len(book.slip)
        print(paint("   TEASER    ", C.BWHITE, C.BOLD) + paint(f"{sb.fmt_odds(sb.TEASER_ODDS[n])}", C.BYELLOW, C.BOLD)
              + paint(f"  —  every leg moves {sb.TEASER_PTS} points your way: "
                      + ", ".join(sb.teased(x).label.replace(' (teased)', '') for x in book.slip), C.GRAY))
    else:
        print(paint("   TEASER    ", C.GRAY, C.BOLD) + paint(tw, C.GRAY))
    footer([key("S", "straight bets", C.BGREEN), key("P", "parlay", C.BGREEN), key("T", "teaser", C.BGREEN),
            key("X#", "remove a leg"), key("C", "clear"), key("B", "board")])


def slip_key(league, book, c):
    """Handle one slip command. Returns False to leave the slip."""
    if c in ("b", "q", ""):
        return False
    if not book.slip:
        return False
    if c == "c":
        book.slip = []
        return True
    if c.startswith("x") and c[1:].isdigit():
        n = int(c[1:])
        if 1 <= n <= len(book.slip):
            book.slip.pop(n - 1)
        return True
    if c == "s":
        stake = read_stake(book, ask(f"Stake on EACH of the {len(book.slip)} bets:"))
        if stake is None:
            return True
        if stake * len(book.slip) > book.bank + 1e-9:
            msg(f"That's {sb.money(stake * len(book.slip))} in all — you have {sb.money(book.bank)}.")
            return True
        win = sum(stake * (sb.dec(x.odds) - 1) for x in book.slip)
        print(paint(f"\n   {len(book.slip)} straight bets · {sb.money(stake)} each · {sb.money(stake * len(book.slip))} "
                    f"total · win {sb.money(win)} if they all hit", C.BWHITE))
        if ask("Place them? [Enter/Y] yes · [N] no:").strip().lower() not in ("", "y", "yes"):
            return True
        placed = []
        for lg_ in list(book.slip):
            b, why = sb.place(book, league, "straight", [lg_], stake)
            if why:
                print(paint(f"   ✘ {lg_.label}: {why}", C.BRED))
            else:
                placed.append(b)
        book.slip = []
        print(paint(f"   ✔ {len(placed)} tickets written.", C.BGREEN, C.BOLD))
        pause()
        return True
    if c in ("p", "t"):
        kind = "parlay" if c == "p" else "teaser"
        why = sb.parlay_problem(book.slip) if kind == "parlay" else sb.teaser_problem(book.slip)
        if why:
            msg(why)
            return True
        odds = sb.parlay_odds(book.slip)[0] if kind == "parlay" else sb.TEASER_ODDS[len(book.slip)]
        stake = read_stake(book)
        if stake is None:
            return True
        desc = f"{len(book.slip)}-leg {'parlay' if kind == 'parlay' else f'teaser (+{sb.TEASER_PTS})'}"
        if not confirm(desc, stake, odds):
            return True
        b, why = sb.place(book, league, kind, book.slip, stake)
        if why:
            msg(why, C.BRED)
            return True
        book.slip = []
        _placed(b)
        return True
    msg("S straight · P parlay · T teaser · X# remove · C clear · B back.")
    return True


# ═══ Futures ═══════════════════════════════════════════════════════════════

FUT = [("T", "title", "NATIONAL TITLE"), ("C", "conf", "CONFERENCES"), ("W", "wins", "WIN TOTALS"),
       ("Y", "cfp", "MAKE THE PLAYOFF"), ("H", "heisman", "HEISMAN")]


def futures_tab(league, book, st):
    mk = sb.futures(book, league)
    open_ = sb.markets_open(league)
    cur = st.get("fut", "title")
    strip = []
    for k, m, name in FUT:
        on = m == cur
        state = "" if open_.get(m) else " (closed)"
        strip.append(paint(f" {k} {name}{state} ", C.BLACK, C.BOLD, "\033[46m") if on else paint(f" [{k}] {name}{state} ", C.GRAY))
    print("   " + " ".join(strip))
    rows, fmt = [], None
    follow = getattr(league, "follow_team", None)
    if cur == "title":
        rows = mk["title"]
        st["rows"] = [("title", t, a) for t, a, _ in rows]
        head = f"   {'#':>3}  {'TEAM':<30}{'ODDS':>8}   {'OPENED':>8}   {'':<30}"
        fmt = lambda i, r: _fut_row(league, book, i, r[0], r[1], ("title", r[0]), follow)
    elif cur == "conf":
        conf = st.get("conf") or getattr(follow, "conference", None)
        if conf not in mk["conf"]:
            conf = next(iter(mk["conf"]), None)
        st["conf"] = conf
        rows = mk["conf"].get(conf, [])
        st["rows"] = [("conf", t, a) for t, a, _ in rows]
        head = f"   {'#':>3}  {'TEAM':<30}{'ODDS':>8}   {'OPENED':>8}      {conf}  ·  [K] another conference"
        fmt = lambda i, r: _fut_row(league, book, i, r[0], r[1], ("conf", r[0]), follow)
    elif cur == "wins":
        rows = mk["wins"]
        view = st.get("wview", "all")
        if view != "all":
            rows = [r for r in rows if r[0].conference == view]
        st["rows"] = [("wins", r) for r in rows]
        head = f"   {'#':>3}  {'TEAM':<30}{'LINE':>6}   {'OVER':>7}   {'UNDER':>7}   {'':<12}view: {view} · [K] conference"
        fmt = lambda i, r: _wins_row(league, book, i, r, follow)
    elif cur == "cfp":
        rows = mk["cfp"]
        st["rows"] = [("cfp", r) for r in rows]
        head = f"   {'#':>3}  {'TEAM':<30}{'YES':>7}   {'NO':>7}"
        fmt = lambda i, r: (f"   {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {team_cell(league, r[0], 30, follow)}"
                            f"{paint(pad(sb.fmt_odds(r[1]), 7, 'right'), C.BWHITE, C.BOLD)}   "
                            f"{paint(pad(sb.fmt_odds(r[2]), 7, 'right'), C.BWHITE, C.BOLD)}")
    else:
        rows = mk["heisman"]
        st["rows"] = [("heisman", p, a) for p, a, _ in rows]
        head = f"   {'#':>3}  {'PLAYER':<26}{'POS':<5}{'TEAM':<22}{'ODDS':>8}   {'OPENED':>8}"
        fmt = lambda i, r: (f"   {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {pad(paint(truncate(r[0].name, 25), C.BWHITE, C.BOLD), 26)}"
                            f"{paint(pad(r[0].position, 5), C.BCYAN)}{pad(truncate(rank(league, r[0].team) + r[0].team.school, 21), 22)}"
                            f"{paint(pad(sb.fmt_odds(r[1]), 8, 'right'), C.BWHITE, C.BOLD)}   "
                            f"{paint(pad(sb.fmt_odds(book.futures_open.get(('heisman', r[0]), r[1])), 8, 'right'), C.GRAY)}")
    per = 18
    pages = max(1, (len(rows) + per - 1) // per)
    st["fpage"] = min(st.get("fpage", 0), pages - 1)
    print(paint(head, C.GRAY, C.BOLD))
    for i, r in enumerate(rows[st["fpage"] * per:(st["fpage"] + 1) * per], st["fpage"] * per + 1):
        print(fmt(i, r))
    if not rows:
        print(paint("   Nothing on the board here.", C.GRAY))
    closed = not open_.get(cur)
    tip = {"title": "12 · 12 50", "conf": "12 · 12 50", "heisman": "12 · 12 50", "wins": "12o / 12u (and an amount)",
           "cfp": "12y / 12n (and an amount)"}[cur]
    print(paint(f"   page {st['fpage'] + 1}/{pages} · pick: {tip} · futures are straight bets (no parlays)"
                + ("  ·  THIS MARKET IS CLOSED" if closed else ""), C.BRED if closed else C.GRAY))


def _fut_row(league, book, i, t, a, key_, follow):
    opened = book.futures_open.get(key_, a)
    mv = ""
    if opened != a:
        shorter = sb.implied(a) > sb.implied(opened)
        mv = paint("▲ shortened" if shorter else "▼ drifted", C.BGREEN if shorter else C.BRED)
    return (f"   {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {team_cell(league, t, 30, follow)}"
            f"{paint(pad(sb.fmt_odds(a), 8, 'right'), C.BWHITE, C.BOLD)}   {paint(pad(sb.fmt_odds(opened), 8, 'right'), C.GRAY)}   {mv}")


def _wins_row(league, book, i, r, follow):
    t, L, o, u, _ = r
    return (f"   {paint(f'{i:>3}', C.BYELLOW, C.BOLD)}  {team_cell(league, t, 30, follow)}"
            f"{paint(pad(sb.fmt_num(L), 6, 'right'), C.BWHITE, C.BOLD)}   {paint(pad('o ' + sb.fmt_odds(o), 7, 'right'), C.BWHITE)}   "
            f"{paint(pad('u ' + sb.fmt_odds(u), 7, 'right'), C.BWHITE)}   {paint(t.conference, C.GRAY)}")


def futures_key(league, book, st, c):
    import re
    for k, m, _ in FUT:
        if c == k.lower():
            st["fut"], st["fpage"] = m, 0
            return True
    if c == "k" and st.get("fut") in ("conf", "wins"):
        confs = sorted({t.conference for t in league.teams if not getattr(t, "fcs", False) and t.conference != "Independent"})
        for i, cf in enumerate(confs, 1):
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {cf}")
        if st.get("fut") == "wins":
            print(f"   {paint('[0]', C.BYELLOW, C.BOLD)} all")
        x = ask("Conference:").strip()
        if x.isdigit() and 1 <= int(x) <= len(confs):
            if st["fut"] == "conf":
                st["conf"] = confs[int(x) - 1]
            else:
                st["wview"] = confs[int(x) - 1]
            st["fpage"] = 0
        elif x == "0":
            st["wview"] = "all"
        return True
    m = re.match(r"^(\d+)\s*([ouyn])?(?:\s+(\S+))?$", c)
    if not m:
        return False
    n, side, amt = int(m.group(1)), m.group(2), m.group(3)
    rows = st.get("rows", [])
    if not 1 <= n <= len(rows):
        msg("No such line.")
        return True
    r = rows[n - 1]
    if not sb.markets_open(league).get(r[0]):
        msg("That market is closed.")
        return True
    if r[0] == "wins":
        t, L, o, u, _ = r[1]
        if side not in ("o", "u"):
            msg("Win totals: add o or u — e.g. 12o.")
            return True
        leg = sb.future_leg(league, "wins", t, o if side == "o" else u, "over" if side == "o" else "under", L)
    elif r[0] == "cfp":
        t, y, no = r[1][0], r[1][1], r[1][2]
        if side not in ("y", "n"):
            msg("Make the playoff: add y or n — e.g. 12y.")
            return True
        leg = sb.future_leg(league, "cfp", t, y if side == "y" else no, "yes" if side == "y" else "no")
    else:
        leg = sb.future_leg(league, r[0], r[1], r[2])
    straight_now(league, book, leg, amt)
    return True


# ═══ Props ═════════════════════════════════════════════════════════════════

def props_tab(league, book, st):
    wk = league.week + 1
    games = sb.featured(book, league, wk) if not league.season_complete else []
    st["prows"] = []
    if not games:
        print(paint("\n   No props this week.", C.GRAY))
        return
    shown = 0
    start = st.get("ppage", 0) * 2
    games_page = games[start:start + 2]
    pages = (len(games) + 1) // 2
    print(paint(f"   Featured games, {league.week_name(wk)} · page {st.get('ppage', 0) + 1}/{pages}", C.GRAY))
    n = 0
    for g in games[:start]:
        n += len(sb.props_for(book, league, g))
    for g in games_page:
        ln = sb.line(book, league, g)
        tag = f"{g.home.abbr} {sb.fmt_line(ln['spread'])} · O/U {sb.fmt_num(ln['total'])}" if ln else ""
        print(section(f"{rank(league, g.away)}{g.away.school} {'vs' if g.neutral else '@'} {rank(league, g.home)}{g.home.school}"
                      f"   ({tag})", C.BMAGENTA))
        props = sb.props_for(book, league, g)
        row = []
        for lg_ in props:
            n += 1
            st["prows"].append((n, lg_))
            chosen = _in_slip(book, lg_)
            txt = truncate(f"{lg_.label} ({sb.fmt_odds(lg_.odds)})", 42)
            row.append(paint(f"{n:>3} ", C.BYELLOW, C.BOLD) + (paint(pad(txt, 43), C.BLACK, C.BOLD, "\033[42m") if chosen else pad(txt, 43)))
            if len(row) == 2:
                print("  " + "  ".join(row))
                row = []
        if row:
            print("  " + row[0])
    print(paint("   # adds it to your slip · '# 25' bets it now · props on a player who doesn't play are void", C.GRAY))


def props_key(league, book, st, c):
    parts = c.split()
    rows = dict(st.get("prows", []))
    if parts and parts[0].isdigit() and int(parts[0]) in rows:
        leg = rows[int(parts[0])]
        if len(parts) == 2 and _is_amount(parts[1]):
            straight_now(league, book, leg, parts[1])
        else:
            toggle(book, leg)
        return True
    return False


# ═══ My bets / record ══════════════════════════════════════════════════════

def _leg_line(league, book, lg_, indent="      ", context_only=False):
    icon, col = STATUS[lg_.status]
    extra = ""
    if lg_.status is None and lg_.game is not None:
        g = lg_.game
        extra = paint(f"  {league.week_name(g.week)} · {g.away.abbr} {'vs' if g.neutral else '@'} {g.home.abbr}", C.GRAY)
        mv = sb.clv(book, league, lg_)
        if mv:
            c = book.cache.get(g)
            now = ""
            if c:
                ln = c[1]
                now = (sb.fmt_line(ln["spread"] if lg_.team is g.home else -ln["spread"]) if lg_.kind == "spread"
                       else sb.fmt_num(ln["total"]))
            extra += paint(f"  moved {sb.fmt_num(abs(mv))} {'your way' if mv > 0 else 'against you'} (now {now})",
                           C.BGREEN if mv > 0 else C.BRED)
    elif lg_.game is not None and lg_.game.played:
        g = lg_.game
        extra = paint(f"  final {g.away.abbr} {g.away_score}, {g.home.abbr} {g.home_score}", C.GRAY)
        if lg_.closing is not None and lg_.kind in ("spread", "total"):
            beat = (lg_.line - lg_.closing) if lg_.kind == "spread" else \
                ((lg_.closing - lg_.line) if lg_.side == "over" else (lg_.line - lg_.closing))
            if beat:
                extra += paint(f"  closed {sb.fmt_line(lg_.closing) if lg_.kind == 'spread' else sb.fmt_num(lg_.closing)}"
                               f" ({'beat' if beat > 0 else 'missed'} it by {sb.fmt_num(abs(beat))})",
                               C.BGREEN if beat > 0 else C.BRED)
    if context_only:
        return (indent + "  " + extra.lstrip()) if extra else ""
    return f"{indent}{paint(icon, col, C.BOLD)} {truncate(lg_.label, 46)} {paint(sb.fmt_odds(lg_.odds), C.GRAY)}{extra}"


def _bet_line(league, book, b):
    icon, col = STATUS[b.status if b.status != "open" else None]
    right = (paint(f"{sb.money(b.stake)} to win {sb.money(b.to_win)}", C.BWHITE) if b.status == "open"
             else money_col(b.net))
    kind = {"straight": "", "future": "FUTURE ", "parlay": "", "teaser": "", "boost": "BOOST "}[b.kind]
    return (f"{paint(icon, col, C.BOLD)} {paint(f'#{b.id:<4}', C.GRAY)}{paint(kind, C.BMAGENTA)}"
            f"{pad(truncate(b.title(), 46 - len(kind)), 47 - len(kind))}{paint(pad(sb.fmt_odds(b.odds), 7, 'right'), C.BYELLOW)}   {right}")


def mybets_tab(league, book, st):
    op = book.open_bets
    if not op:
        print(paint("\n   No open bets. The board's that way →  [B]", C.GRAY))
        return
    per = 8
    pages = max(1, (len(op) + per - 1) // per)
    st["mpage"] = min(st.get("mpage", 0), pages - 1)
    print(paint(f"   {len(op)} open · {sb.money(book.at_risk())} at risk · {sb.money(book.to_win_open())} to win"
                f" · page {st['mpage'] + 1}/{pages}", C.GRAY))
    for b in sorted(op, key=lambda b: (b.kind == "future", b.week, b.id))[st["mpage"] * per:(st["mpage"] + 1) * per]:
        print("   " + _bet_line(league, book, b))
        if len(b.legs) > 1:
            for lg_ in b.legs:
                print(_leg_line(league, book, lg_))
        elif b.legs[0].game is not None:
            ctx = _leg_line(league, book, b.legs[0], context_only=True)
            if ctx.strip():
                print(ctx)


def chart(values, width=76, height=7):
    """A bankroll chart in block characters."""
    vals = list(values)
    if len(vals) < 3:
        return [paint("   The chart starts once a week or two of results are in.", C.GRAY)]
    if len(vals) > width:
        step = len(vals) / width
        vals = [vals[int(i * step)] for i in range(width)]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    rows = []
    for r in range(height, 0, -1):
        line = ""
        for i, v in enumerate(vals):
            lvl = (v - lo) / span * height
            col = C.BGREEN if i == 0 or v >= vals[i - 1] else C.BRED
            if lvl >= r:
                line += paint("█", col)
            elif lvl >= r - 0.5:
                line += paint("▄", col)
            else:
                line += " "
        lab = sb.money(hi) if r == height else sb.money(lo) if r == 1 else ""
        rows.append(paint(pad(lab, 11, "right"), C.GRAY) + " " + paint("│", C.GRAY) + line)
    return rows


def record_tab(league, book, st):
    vals = [x[2] for x in book.ledger] + [book.bank]
    print(paint("   BANKROLL", BRAND, C.BOLD) + paint(f"   start {sb.money(book.start)} → now {sb.money(book.bank)}", C.GRAY))
    for ln in chart(vals):
        print(ln)
    sett = book.settled_bets
    print()
    print(paint(f"   {'':<12}{'W-L-P':<12}{'RISKED':>12}{'NET':>13}{'ROI':>9}", C.GRAY, C.BOLD))
    kinds = [("Straight", lambda b: b.kind == "straight" and b.legs[0].kind not in ("prop",)),
             ("Props", lambda b: b.kind == "straight" and b.legs[0].kind == "prop"),
             ("Parlays", lambda b: b.kind in ("parlay", "boost")), ("Teasers", lambda b: b.kind == "teaser"),
             ("Futures", lambda b: b.kind == "future"), ("All", lambda b: True)]
    for name, f in kinds:
        w, l, p, risked, net = sb.record([b for b in sett if f(b)])
        roi = f"{net / risked * 100:+.1f}%" if risked else "—"
        print(f"   {paint(pad(name, 12), C.BWHITE, C.BOLD if name == 'All' else '')}{pad(f'{w}-{l}-{p}', 12)}"
              f"{pad(sb.money(risked), 12, 'right')}{pad(money_col(net), 13, 'right')}{pad(roi, 9, 'right')}")
    if book.seasons:
        print(paint("   by season: " + "  ·  ".join(f"{y} {sb.money(v, sign=True)}" for y, v in sorted(book.seasons.items())),
                    C.GRAY))
    if sett:
        best = max(sett, key=lambda b: b.net)
        print(paint("   best ticket: ", C.GRAY) + f"#{best.id} {truncate(best.title(), 40)} " + money_col(best.net))
    per = 7
    recent = sorted(sett, key=lambda b: -b.id)
    pages = max(1, (len(recent) + per - 1) // per)
    st["rpage"] = min(st.get("rpage", 0), pages - 1)
    print(section(f"SETTLED TICKETS  ·  page {st['rpage'] + 1}/{pages}", C.GRAY))
    for b in recent[st["rpage"] * per:(st["rpage"] + 1) * per]:
        print("   " + _bet_line(league, book, b))


# ═══ ATS ═══════════════════════════════════════════════════════════════════

def ats_tab(league, book, st):
    view = st.get("aview", "top 25")
    follow = getattr(league, "follow_team", None)
    teams = [t for t in league.teams if not getattr(t, "fcs", False)]
    if view == "top 25":
        teams = [t for t in teams if league.rankings.rank_of(t)]
    elif view not in ("all",):
        teams = [t for t in teams if t.conference == view]

    def pct(t):
        w, l, _ = book.ats.get(t, [0, 0, 0])
        return w / (w + l) if w + l else 0.5
    teams.sort(key=lambda t: (-pct(t), -book.ats.get(t, [0, 0, 0])[0], league.rankings.rank_of(t) or 99, t.school))
    per = 20
    pages = max(1, (len(teams) + per - 1) // per)
    st["apage"] = min(st.get("apage", 0), pages - 1)
    print(paint(f"   Against the closing number · view: {view} · [K] change · page {st['apage'] + 1}/{pages}", C.GRAY))
    print(paint(f"   {'TEAM':<32}{'SU':>6}{'ATS':>10}{'COVER':>8}   {'O/U':>8}   {'':<20}", C.GRAY, C.BOLD))
    for t in teams[st["apage"] * per:(st["apage"] + 1) * per]:
        w, l, p = book.ats.get(t, [0, 0, 0])
        o, u, op = book.ou.get(t, [0, 0, 0])
        c = pct(t)
        col = C.BGREEN if c >= 0.6 and w + l >= 3 else C.BRED if c <= 0.4 and w + l >= 3 else C.BWHITE
        bar = (paint("▰" * int(round(c * 10)), col) + paint("▱" * (10 - int(round(c * 10))), C.GRAY)) if w + l \
            else paint("no games yet", C.GRAY)
        print(f"   {team_cell(league, t, 32, follow)}{t.record:>6}{f'{w}-{l}' + (f'-{p}' if p else ''):>10}"
              f"{paint(pad(f'{c * 100:.0f}%' if w + l else '—', 8, 'right'), col)}   {f'{o}-{u}' + (f'-{op}' if op else ''):>8}   {bar}")


# ═══ Options, welcome, report ══════════════════════════════════════════════

def options(league, book):
    while True:
        clear()
        print(book_title(league))
        hide = bool(league.__dict__.get("hide_all_ratings"))
        print(section("OPTIONS", BRAND))
        print(f"   {paint('[1]', C.BYELLOW, C.BOLD)} Ratings for every team:  "
              + paint("HIDDEN (scout's eye on your team, words for the rest)" if hide else
                      "SHOWN (only your team is seen through a scout's eye)", C.BRED if hide else C.BGREEN, C.BOLD))
        print(paint("       Hidden is the sharper game: you and the book both work from what you can see.", C.GRAY))
        can_reload = book.bank < 1 and not book.open_bets
        print(f"   {paint('[2]', C.BYELLOW if can_reload else C.GRAY, C.BOLD)} Take a {sb.money(sb.RELOAD)} reload"
              + paint("  (only when you're broke with nothing open; reloads are counted)" if not can_reload else "", C.GRAY))
        print(f"   {paint('[3]', C.BYELLOW, C.BOLD)} How the book sets its numbers")
        print(f"   {paint('[B]', C.GRAY, C.BOLD)} Back")
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "1":
            league.hide_all_ratings = not hide
        elif c == "2" and can_reload:
            sb.reload(book, league)
            msg(f"A {sb.money(sb.RELOAD)} reload. Make it last.", C.BGREEN)
        elif c == "3":
            clear()
            print(book_title(league))
            for para in (
                    "Every team has a rating gap to its opponent. The book turns that gap into a margin on a curve "
                    "fitted to how games really play out — a moderate favorite wins by more than a straight line "
                    "says, and a mismatch flattens out once the starters sit.",
                    "On top of that: what the season has taught the book (a lot in September, less by November; half "
                    "of it carries into next year) and a point or so of public money on the big brands.",
                    "Home field is worth the same everywhere (about 3.5 points). The book doesn't know which "
                    "buildings are really loud, or which coaches are really good on Saturday — some of the regulars do.",
                    "A margin is about 18 points of noise either way; that's where the moneylines come from. Totals "
                    "come from the offenses and defenses, the weather that week, and the league's scoring climate.",
                    "Every game on the schedule has a line all season. Lines move every week as teams play, get "
                    "hurt and get healthy — take a number early and My Bets shows whether the market came to you.",
                    "Futures come from playing the rest of the season a few hundred times with the book's numbers. "
                    "Win totals are preseason only."):
                import textwrap
                for ln in textwrap.wrap(para, WIDTH - 8):
                    print("   " + ln)
                print()
            pause()


def welcome(league, book):
    """The first walk up to the window: pick a bankroll."""
    clear()
    print(book_title(league))
    print()
    print(paint("   Welcome to The Window.", C.BWHITE, C.BOLD))
    print(paint("   Spreads, totals and moneylines on every game all season, player props, parlays, teasers,\n"
                "   and futures on the whole sport. Your bankroll carries from season to season.", C.GRAY))
    print()
    for i, v in enumerate(sb.BANKROLLS, 1):
        tag = paint("  ← standard", C.BCYAN) if v == sb.DEFAULT_BANK else ""
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(sb.money(v), BRAND, C.BOLD)}{tag}")
    c = ask("Starting bankroll (Enter = $10,000):").strip()
    v = sb.BANKROLLS[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(sb.BANKROLLS) else sb.DEFAULT_BANK
    book.bank = book.start = float(v)
    book.ledger = [(league.year, "Start", book.bank)]
    book.welcomed = True


def report(league, book, bets=None, title=None):
    """What just settled."""
    bets = list(bets if bets is not None else book.unseen)
    if not bets:
        return
    clear()
    print(book_title(league))
    net = sum(b.net for b in bets)
    print(section(title or f"RESULTS SINCE YOUR LAST VISIT  ·  {len(bets)} ticket" + ("s" if len(bets) != 1 else ""), BRAND))
    for b in sorted(bets, key=lambda b: -abs(b.net))[:22]:
        print("   " + _bet_line(league, book, b))
        if len(b.legs) > 1:
            for lg_ in b.legs:
                print(_leg_line(league, book, lg_))
    if len(bets) > 22:
        print(paint(f"   ... and {len(bets) - 22} more on the RECORD tab.", C.GRAY))
    w, l, p, _, _ = sb.record(bets)
    print()
    print("   " + paint("Net ", C.GRAY) + money_col(net) + paint(f"   ({w}-{l}" + (f"-{p}" if p else "") + ")   ", C.GRAY)
          + paint("Bankroll ", C.GRAY) + paint(sb.money(book.bank), BRAND, C.BOLD))
    import regulars as rg
    if book.__dict__.get("regulars"):
        rk, n = rg.your_rank(book, league)
        top = rg.standings(book, league)[:3]
        print("   " + paint("The table: ", C.GRAY) + paint(f"you're {_ord(rk)} of {n} this season", C.BWHITE, C.BOLD)
              + paint("   ·   leaders: " + ", ".join(f"{_short(nm)} {sb.money(v, sign=True)}" for nm, v, _ in top), C.GRAY))
        tick = [t for t in book.__dict__.get("ticker", []) if t[0] == league.year and
                t[1] == (league.week_name(league.week) if league.week else "Preseason")]
        for _, _, text in tick[-3:]:
            print(paint("   ▸ " + text, C.BCYAN))
    book.unseen = []
    pause()


# ═══ The hub ═══════════════════════════════════════════════════════════════

def hub(league):
    book = sb.get(league)
    if book is None:
        clear()
        print(title_bar("THE WINDOW", BRAND))
        print(paint("\n   The sportsbook is for Spectator mode. Coaches and ADs don't get to bet on college football.", C.GRAY))
        pause()
        return
    if not book.welcomed:
        welcome(league, book)
    import regulars as rg
    rg.ensure(book, league)                           # the regulars (created the first time)
    if book.unseen:
        report(league, book)
    st = {"tab": 0, "page": 0, "view": "all", "week": None}
    while True:
        book.slip = [x for x in book.slip if sb.still_open(league, x)]
        tab = st["tab"]
        header(league, book, tab)
        name = TABS[tab][1]
        extra = []
        if name in ("BOARD", "LOOK-AHEAD"):
            weeks = sb.upcoming_weeks(league)
            if name == "BOARD":
                wk = league.week + 1
            else:
                if st["week"] not in weeks:
                    st["week"] = weeks[1] if len(weeks) > 1 else (weeks[0] if weeks else None)
                wk = st["week"]
                if wk is not None:
                    strip = " ".join(paint(f"{'W' + str(w) if w <= sb.REG else league.week_name(w)[:8]}",
                                           C.BLACK if w == wk else C.GRAY, C.BOLD, "\033[42m" if w == wk else "")
                                     for w in weeks)
                    print("   " + paint("weeks: ", C.GRAY) + strip + paint("   W7 jumps · [N]/[U] page", C.GRAY))
            if wk is None or league.season_complete:
                print(paint("\n   No games on the board. The new season's lines go up in the preseason.", C.GRAY))
            else:
                board_tab(league, book, st, wk)
                if name == "BOARD":
                    bo = sb.weekly_boost(book, league)
                    if bo.get("legs") and not bo.get("taken"):
                        print("   " + paint(" ⚡ THE BOOST ", C.BLACK, C.BOLD, "\033[45m") + " "
                              + paint(" + ".join(x.label.replace(" moneyline", "") for x in bo["legs"]), C.BWHITE, C.BOLD)
                              + paint(f"  was {sb.fmt_odds(bo['was'])}, now ", C.GRAY)
                              + paint(sb.fmt_odds(bo["odds"]), C.BMAGENTA, C.BOLD) + paint(f"  ({sb.money(sb.BOOST_MAX)} max · [X])", C.GRAY))
            extra = [key("#", "game"), key("V", "view"), key("N", "next page"), key("U", "prev page")]
        elif name == "FUTURES":
            futures_tab(league, book, st)
            extra = [key("T", "title"), key("C", "conference"), key("W", "win totals"), key("Y", "playoff"),
                     key("H", "Golden Helmet"), key("N", "next page"), key("U", "prev page")]
        elif name == "PROPS":
            props_tab(league, book, st)
            extra = [key("N", "more games"), key("U", "back a page")]
        elif name == "SLIP":
            slip_body(league, book)
            extra = []
        elif name == "MY BETS":
            mybets_tab(league, book, st)
            extra = [key("N", "next page"), key("U", "prev page")]
        elif name == "RECORD":
            record_tab(league, book, st)
            extra = [key("N", "older"), key("U", "newer")]
        elif name == "ATS":
            ats_tab(league, book, st)
            extra = [key("K", "view"), key("N", "next page"), key("U", "prev page")]
        elif name == "STANDINGS":
            standings_tab(league, book, st)
            extra = [key("#", "a regular's profile"), key("K", "season / all-time")]
        if name != "SLIP":
            footer(extra + [key("O", "options")])
        c = ask("The window:").strip().lower()
        if c in ("q",):
            return
        if c == "":
            continue
        tabkeys = {k.lower(): i for i, (k, _) in enumerate(TABS)}
        if name == "FUTURES" and c in ("t", "c", "w", "y", "h", "k"):
            futures_key(league, book, st, c)
            continue
        if name == "SLIP" and (c in ("s", "p", "t", "c") or (c.startswith("x") and c[1:].isdigit())):
            slip_key(league, book, c)                 # on the slip, S P T C are the slip's own keys
            continue
        if c in tabkeys:
            st["tab"] = tabkeys[c]
            continue
        if c == "o":
            options(league, book)
            continue
        if c in ("n", "u"):
            d = 1 if c == "n" else -1
            pk = {"BOARD": "page", "LOOK-AHEAD": "page", "FUTURES": "fpage", "PROPS": "ppage", "MY BETS": "mpage",
                  "RECORD": "rpage", "ATS": "apage"}.get(name)
            if pk:
                st[pk] = max(0, st.get(pk, 0) + d)
                if name == "PROPS":
                    n_games = len(sb.featured(book, league, league.week + 1))
                    st[pk] = min(st[pk], max(0, (n_games - 1) // 2))
            continue
        if name in ("BOARD", "LOOK-AHEAD"):
            if c == "v":
                for i, v in enumerate(VIEWS, 1):
                    print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {v}")
                x = ask("View:").strip()
                if x.isdigit() and 1 <= int(x) <= len(VIEWS):
                    st["view"], st["page"] = VIEWS[int(x) - 1], 0
                    if st["view"] == "conference":
                        confs = sorted({t.conference for t in league.teams if not getattr(t, "fcs", False)})
                        for i, cf in enumerate(confs, 1):
                            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {cf}")
                        y = ask("Conference:").strip()
                        st["conf"] = confs[int(y) - 1] if y.isdigit() and 1 <= int(y) <= len(confs) else confs[0]
                continue
            if c == "x":
                take_boost(league, book)
                continue
            if name == "LOOK-AHEAD" and c.startswith("w") and c[1:].isdigit():
                w = int(c[1:])
                if w in sb.upcoming_weeks(league):
                    st["week"], st["page"] = w, 0
                continue
            p = parse_pick(c)
            if p:
                n, code, amt = p
                games = st.get("games", [])
                if not 1 <= n <= len(games):
                    msg("No game with that number on this page.")
                    continue
                g = games[n - 1]
                if code is None:
                    game_screen(league, book, g)
                    continue
                legs = sb.game_legs(book, league, g)
                if code not in legs:
                    msg("That market isn't offered.")
                    continue
                if amt:
                    straight_now(league, book, legs[code], amt)
                else:
                    added = toggle(book, legs[code])
                    print(paint(f"   {'+ added' if added else '- removed'}: {legs[code].label}", C.BGREEN if added else C.GRAY))
                continue
        if name == "FUTURES" and futures_key(league, book, st, c):
            continue
        if name == "PROPS" and props_key(league, book, st, c):
            continue
        if name == "STANDINGS":
            if c == "k":
                st["season"] = not st.get("season", True)
                continue
            if c.isdigit():
                rows = st.get("srows", [])
                n = int(c)
                if 1 <= n <= len(rows):
                    acct = rows[n - 1][2]
                    if acct is None:
                        st["tab"] = 6                      # you: your record
                    else:
                        regular_screen(league, book, acct)
                continue
        if name == "ATS" and c == "k":
            opts = ["top 25", "all"] + sorted({t.conference for t in league.teams if not getattr(t, "fcs", False)})
            for i, v in enumerate(opts, 1):
                print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {v}")
            x = ask("View:").strip()
            if x.isdigit() and 1 <= int(x) <= len(opts):
                st["aview"], st["apage"] = opts[int(x) - 1], 0
            continue
        msg("Not a command here. Letters switch tabs (B L F P S M R A); Q leaves.")


def take_boost(league, book):
    bo = sb.weekly_boost(book, league)
    if not bo.get("legs"):
        msg("No boost this week.")
        return
    if bo.get("taken"):
        msg("You've already taken this week's boost.")
        return
    stake = read_stake(book, cap=sb.BOOST_MAX)
    if stake is None:
        return
    desc = " + ".join(x.label for x in bo["legs"]) + " (boosted)"
    if not confirm(desc, stake, bo["odds"]):
        return
    b, why = sb.place(book, league, "boost", bo["legs"], stake, boosted_odds=bo["odds"])
    if why:
        msg(why, C.BRED)
        return
    bo["taken"] = True
    _placed(b)


# ═══ The regulars ══════════════════════════════════════════════════════════

def _ord(n):
    if n is None:
        return "—"
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _short(display):
    """'Shane "Tape" Yates' → 'Tape Yates'."""
    if '"' in display:
        parts = display.split('"')
        return f"{parts[1]} {parts[2].strip()}"
    return display


def _style(r):
    import regulars as rg
    return rg.TYPES[r.key][0]


def rail_on(book, g):
    """The regulars' open tickets that touch this game."""
    import regulars as rg
    out = []
    for r in book.__dict__.get("regulars") or []:
        for b in r.open_bets:
            for lg_ in b.legs:
                if lg_.game is g:
                    what = lg_.label if len(b.legs) == 1 else f"{lg_.label} (in a {b.title().lower()})"
                    out.append((b.stake, f"   {paint(pad(_short(rg.display_name(r)), 22), C.BWHITE, C.BOLD)}"
                                          f"{paint(pad(_style(r), 20), C.GRAY)}{pad(truncate(what, 40), 41)}"
                                          f"{paint(sb.money(b.stake), C.BYELLOW)}"))
                    break
    return [x for _, x in sorted(out, key=lambda x: -x[0])]


def standings_tab(league, book, st):
    import regulars as rg
    season = st.get("season", True)
    rows = rg.standings(book, league, season)
    st["srows"] = rows
    yr = league.year
    last = (league.year, league.week)
    print(paint(f"   {'THIS SEASON' if season else 'ALL-TIME'}  ·  {len(rows)} at the table  ·  a number opens a profile",
                C.GRAY))
    print(paint(f"   {'RK':<4}{'':<28}{'STYLE':<18}{'SEASON' if season else 'ALL-TIME':>11}{'BANKROLL':>12}"
                f"{'W-L':>9}{'ROI':>7}{'LAST WK':>10}", C.GRAY, C.BOLD))
    for i, (nm, net, acct) in enumerate(rows, 1):
        if acct is None:
            bets = book.settled_bets
            bank = book.bank
            name = paint("YOU", C.BLACK, C.BOLD, "\033[42m") + " " + paint("★" * len(book.__dict__.get("titles", [])),
                                                                           C.BYELLOW)
            style = paint("—", C.GRAY)
        else:
            bets = acct.settled_bets
            bank = acct.bank
            stars = paint(" " + "★" * len(acct.titles), C.BYELLOW) if acct.titles else ""
            name = paint(truncate(_short(nm), 24 - len(acct.titles)), C.BWHITE, C.BOLD) + stars
            style = paint(truncate(_style(acct), 17), C.BCYAN)
        if season:
            bets = [b for b in bets if b.year == yr]
        w, l, p, risked, n = sb.record(bets)
        roi = (f"{n / risked * 100:+.0f}%" if round(n / risked * 100) else "0%") if risked else "—"
        lw = sum(b.net for b in bets if b.settled == last)
        rk_col = C.BYELLOW if i <= 3 else C.GRAY
        print(f"   {paint(pad(str(i), 4), rk_col, C.BOLD)}{pad(name, 28)}{pad(style, 18)}{pad(money_col(net), 11, 'right')}"
              f"{pad(sb.money(bank), 12, 'right')}{pad(f'{w}-{l}', 9, 'right')}{pad(roi, 7, 'right')}"
              f"{pad(money_col(lw) if lw else paint('—', C.GRAY), 10, 'right')}")
    champs = book.__dict__.get("table_champs") or {}
    if champs:
        print(paint("   Past winners: " + " · ".join(f"{y} {_short(nm)} ({sb.money(v, sign=True)})"
                                               for y, (nm, v) in sorted(champs.items())[-4:]), C.BYELLOW))
    tick = list(reversed(book.__dict__.get("ticker", [])))[:6]
    if tick:
        print(section("AT THE RAIL", C.BCYAN))
        for y, wk, text in tick:
            print(paint(f"   {truncate(wk, 14):<15}", C.GRAY) + truncate(text, 80))


def regular_screen(league, book, r):
    import regulars as rg
    import textwrap
    while True:
        clear()
        print(book_title(league))
        label, kind, role, looks, quote = rg.TYPES[r.key]
        print(f"   {paint(rg.display_name(r), C.BWHITE, C.BOLD)}   " + paint(f" {label} ", C.BLACK, C.BOLD, "\033[46m")
              + (paint("  " + "★" * len(r.titles) + f" won the table in {', '.join(map(str, r.titles))}", C.BYELLOW)
                 if r.titles else ""))
        print(paint(f"   {r.bio}", C.GRAY))
        mascot = getattr(r.school, "nickname", "") or r.school.school
        print(paint(f'   "{quote.format(mascot=mascot)}"', C.BCYAN))
        print()
        print(paint("   WHAT HE LOOKS FOR", C.GRAY, C.BOLD))
        for ln_ in textwrap.wrap(looks, WIDTH - 8):
            print("   " + ln_)
        print()
        yr = league.year
        season = [b for b in r.settled_bets if b.year == yr]
        cols = []
        for title, bets, net in (("THIS SEASON", season, r.season_net(yr)), ("ALL-TIME", r.settled_bets, r.net)):
            w, l, p, risked, n = sb.record(bets)
            cols.append(panel(title, [paint("net ", C.GRAY) + money_col(net),
                                      paint(f"{w}-{l}" + (f"-{p}" if p else "") + "  ", C.BWHITE)
                                      + paint(f"ROI {n / risked * 100:+.1f}%" if risked else "no results", C.GRAY),
                                      paint(f"bankroll {sb.money(r.bank)}" + (f" · {r.reloads} re-up" + ("s" if r.reloads != 1 else "")
                                                                              if r.reloads else ""), C.GRAY)], 32))
        kinds = []
        for nm, f in (("Straight", lambda b: b.kind == "straight" and b.legs[0].kind != "prop"),
                      ("Props", lambda b: b.kind == "straight" and b.legs[0].kind == "prop"),
                      ("Parlays", lambda b: b.kind in ("parlay", "boost")), ("Teasers", lambda b: b.kind == "teaser"),
                      ("Futures", lambda b: b.kind == "future")):
            w, l, p, risked, n = sb.record([b for b in r.settled_bets if f(b)])
            if w + l + p:
                kinds.append(f"{pad(nm, 9)}{pad(f'{w}-{l}', 8)}" + money_col(n))
        cols.append(panel("BY BET TYPE", kinds or [paint("nothing settled yet", C.GRAY)], 34))
        for ln_ in columns(*cols):
            print(ln_)
        print(section("THE BANKROLL", C.GRAY))
        for ln_ in chart(r.ledger + [r.bank + sum(b.stake for b in r.open_bets)], width=70, height=5):
            print(ln_)
        op = sorted(r.open_bets, key=lambda b: (b.kind == "future", b.id))
        print(section(f"OPEN TICKETS  ·  {len(op)}", BRAND))
        for i, b in enumerate(op[:9], 1):
            print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)} " + _bet_line(league, book, b))
            if len(b.legs) > 1:
                for lg_ in b.legs[:7]:
                    print(_leg_line(league, book, lg_, indent="         "))
        if not op:
            print(paint("   Nothing open right now.", C.GRAY))
        recent = sorted(r.settled_bets, key=lambda b: -b.id)[:5]
        if recent:
            print(section("LATELY", C.GRAY))
            for b in recent:
                print("      " + _bet_line(league, book, b))
        footer([key("T#", "tail a ticket (to your slip)"), key("F#", "fade it"), key("S", f"slip ({len(book.slip)})", C.BGREEN),
                key("B", "back")], leave=False)
        c = ask("Profile:").strip().lower()
        if c in ("b", "q", ""):
            return
        if c == "s":
            slip_screen(league, book)
            continue
        if c[:1] in ("t", "f") and c[1:].isdigit():
            n = int(c[1:])
            if not 1 <= n <= min(9, len(op)):
                msg("No ticket with that number.")
                continue
            b = op[n - 1]
            fade = c[0] == "f"
            if fade and (len(b.legs) != 1 or b.legs[0].kind not in ("spread", "ml", "total")):
                msg("You can fade a single side or total. Parlays, props and futures you just watch.")
                continue
            legs = rg.tail_legs(book, league, b, fade=fade)
            if not legs:
                msg("Those games have kicked off (or it's a future) — nothing to tail at the window now.")
                continue
            added = 0
            for lg_ in legs:
                if not _in_slip(book, lg_):
                    book.slip.append(lg_)
                    added += 1
            msg(f"{'Faded' if fade else 'Tailed'}: {added} leg{'s' if added != 1 else ''} on your slip, at today's numbers. "
                f"({', '.join(x.label for x in legs[:3])})", C.BGREEN)
            continue
        msg("T# tails a ticket, F# fades it, S opens your slip, B goes back.")


# ═══ Elsewhere in the game ═════════════════════════════════════════════════

def home_panel(league, w, height=None):
    """The dashboard's HOME panel (spectator mode)."""
    book = sb.get(league, create=False)
    lines = []
    if book is None:
        lines = [paint("Spreads, totals, parlays, props and", C.GRAY), paint("futures on every game, all season.", C.GRAY),
                 "", paint("[B] walk up to the window", C.BYELLOW, C.BOLD)]
        return panel("THE WINDOW", lines, w, height=height, color=BRAND, title_color=BRAND)
    import regulars as rg
    d = rg.you_net(book)
    lines.append(paint(sb.money(book.bank), BRAND, C.BOLD) + "  " + paint(sb.money(d, sign=True), C.BGREEN if d >= 0 else C.BRED))
    if book.__dict__.get("regulars"):
        rk, n = rg.your_rank(book, league)
        lines.append(paint(f"{_ord(rk)} of {n} at the table this season", C.BCYAN))
    lines.append(spark([x[2] for x in book.ledger] + [book.bank], width=w - 6))
    lines.append(paint(f"{len(book.open_bets)} open · {sb.money(book.at_risk())} at risk", C.GRAY))
    if book.unseen:
        net = sum(b.net for b in book.unseen)
        lines.append(paint(f"{len(book.unseen)} settled: ", C.BMAGENTA) + money_col(net))
    lines.append(paint("[B] the sportsbook", C.BYELLOW, C.BOLD))
    return panel("THE WINDOW", lines, w, height=height, color=BRAND, title_color=BRAND)


def card_lines(league, g):
    """Two lines for a matchup card: the number and your action."""
    book = sb.get(league, create=False)
    if book is None:
        return []
    c = book.cache.get(g)
    if not c:
        return []
    ln = c[1]
    fav = g.home if ln["spread"] < 0 else g.away
    sp = abs(ln["spread"])
    line_txt = (f"{fav.school} -{sb.fmt_num(sp)}" if sp else "Pick'em") + f"  ·  O/U {sb.fmt_num(ln['total'])}"
    if ln["ml"]:
        line_txt += f"  ·  ML {g.away.abbr} {sb.fmt_odds(ln['ml'][0])} / {g.home.abbr} {sb.fmt_odds(ln['ml'][1])}"
    out = ["   " + paint(" THE WINDOW ", C.BLACK, C.BOLD, "\033[42m") + "  " + paint(line_txt, C.BWHITE, C.BOLD)]
    act = sb.my_action(book, g)
    if act:
        bits = [f"{truncate(b.title(), 34)} ({sb.money(b.stake)})" for b in act[:3]]
        out.append("   " + paint("Your action: ", BRAND, C.BOLD) + paint(" · ".join(bits), C.BWHITE)
                   + (paint(f" +{len(act) - 3} more", C.GRAY) if len(act) > 3 else ""))
    return out
