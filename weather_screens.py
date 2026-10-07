"""
weather_screens.py — The Weather Center: your forecast, the extended outlook, the country's
weather games, and your program's weather book.
"""
import weather
from ui import C, WIDTH, ask, clear, columns, key, pad, paint, panel, rule, title_bar, truncate, command_bar


def _sev_color(sev):
    return C.BRED if sev >= 3 else C.BYELLOW if sev >= 2 else C.BCYAN if sev >= 1 else C.BGREEN


def _upcoming(league, team, n=4):
    return [g for g in league.team_games(team) if not g.played][:n]


def _where(g, team):
    opp = g.opponent_of(team)
    at = "vs" if g.home is team or g.neutral else "at"
    return f"{at} {opp.school}"


def _place_words(g):
    if weather.indoor(g):
        return (weather._venue(g) or "").split(",")[0] + " (indoors)"
    clim, st, alt, pkey, city = weather.place(g)
    stad = (weather._venue(g) or g.home.stadium).split(",")[0]
    bits = [stad] + ([city] if city else [])
    if alt >= 3000:
        bits.append(f"{alt:,} ft")
    return ", ".join(bits)


def forecast_lines(league, team, g, w=46):
    """The detailed forecast for a game (lines for a panel)."""
    lead = max(0, g.week - (league.week + 1))
    f = weather.forecast(g, league, lead)
    L = [paint(truncate(f"{league.week_name(g.week)} · {_where(g, team)}", w), C.BWHITE, C.BOLD),
         paint(truncate(_place_words(g), w), C.GRAY)]
    try:
        import broadcast
        when = broadcast.when(g, short=True)
        if when:
            L.append(paint(when, C.GRAY))
    except Exception:
        pass
    if f["indoor"]:
        L.append(paint("Indoors. 72 degrees, no wind, a dry ball.", C.BGREEN))
        return L
    col = _sev_color(f["severity"])
    L.append(paint(truncate(f["headline"], w), col, C.BOLD))
    L.append(f"Kickoff temp  {paint(str(f['temp']) + '°', C.BWHITE, C.BOLD)}"
             + paint(f"  (likely {f['lo']}°–{f['hi']}°)", C.GRAY))
    pt = {"snow": "snow", "mix": "sleet", "storms": "storms", "rain": "rain"}[f["ptype"]]
    L.append(f"Chance of {pt:<6} {paint(str(f['pop']) + '%', C.BWHITE, C.BOLD)}")
    wlo, whi = f["wind"]
    L.append(f"Wind          {paint(f'{wlo}-{whi} mph', C.BWHITE, C.BOLD)}"
             + (paint(f"  from the {f['dir']}", C.GRAY) if f["dir"] else ""))
    wx = weather.truth(g, league)
    L.append(paint(f"Normal for the date: {wx['normal']}°", C.GRAY))
    L.append(paint(f"Confidence: {f['confidence']}" + ("" if lead else " — it's game week"), C.GRAY))
    return L


def center(league, team=None):
    team = team or getattr(league, "user_team", None) or getattr(league, "follow_team", None)
    page = "home"
    while True:
        clear()
        print(title_bar("WEATHER CENTER", C.BCYAN))
        if page == "home":
            _home(league, team)
            items = [key("C", "around the country"), key("K", "weather book"), key("L", "last week's weather games"),
                     key("B", "back", C.GRAY)]
        elif page == "country":
            _country(league)
            items = [key("Y", "your forecast"), key("K", "weather book"), key("B", "back", C.GRAY)]
        elif page == "book":
            _book(league, team)
            items = [key("Y", "your forecast"), key("C", "around the country"), key("B", "back", C.GRAY)]
        else:
            _last_week(league)
            items = [key("Y", "your forecast"), key("C", "around the country"), key("B", "back", C.GRAY)]
        for ln in command_bar(items):
            print(ln)
        c = ask("Select:").strip().lower()
        if c in ("b", "", "q"):
            return
        page = {"c": "country", "k": "book", "l": "last", "y": "home"}.get(c, page)


def _home(league, team):
    if team is None:
        print(paint("\n  Pick a team to follow first.", C.GRAY))
        return
    up = _upcoming(league, team)
    if not up:
        print(paint(f"\n  {team.school} has no games left this season. The weather book [K] has the rest.", C.GRAY))
        return
    g = up[0]
    left = forecast_lines(league, team, g, 44)
    right = []
    note = weather.staff_note(league, team, g) if (g.week == league.week + 1) else ""
    if note:
        right += [paint(ln, C.BCYAN) for ln in _wrap(note, 44)] + [""]
    wx = weather.truth(g, league)
    if not wx.get("indoor"):
        surf = {1: "worn turf", 2: "modern turf", 3: "natural grass", 4: "heated hybrid grass"}.get(wx["surface"], "turf")
        right.append(paint("The field: ", C.GRAY) + surf)
        if wx["surface"] == 3:
            right.append(paint("Grass gets sloppy in the rain.", C.GRAY))
        elif wx["surface"] == 4:
            right.append(paint("Heated: snow won't stick.", C.GRAY))
        clim = weather.team_climate(team)
        right.append(paint("Home climate: ", C.GRAY) + f"{clim[0]}° in Sept, {clim[1]}° in Dec")
        if (wx.get("alt") or 0) >= 3000:
            right.append(paint(f"Altitude {wx['alt']:,} ft: kicks carry,", C.GRAY))
            right.append(paint("visitors tire late.", C.GRAY))
    right += ["", paint("Weather prep (practice focus) halves", C.GRAY), paint("what the weather does to your team.", C.GRAY)]
    for ln in columns(panel("YOUR NEXT GAME", left, 50, color=C.BCYAN, height=10),
                      panel("WHAT IT MEANS", right, 49, height=10)):
        print(ln)
    rows = []
    for g2 in up[1:4]:
        lead = max(0, g2.week - (league.week + 1))
        f = weather.forecast(g2, league, lead)
        if f["indoor"]:
            txt = paint("indoors", C.BGREEN)
        else:
            txt = f"{f['temp']}°  " + paint(f"{f['pop']}% {f['ptype'] if f['ptype'] != 'mix' else 'sleet'}", C.GRAY) \
                + paint(f"  wind {f['wind'][0]}-{f['wind'][1]}", C.GRAY) + paint(f"  {f['headline']}", _sev_color(f["severity"]))
        rows.append(f"{paint(pad(league.week_name(g2.week), 12), C.GRAY)}{pad(truncate(_where(g2, team), 26), 27)}{txt}")
    if rows:
        for ln in panel("EXTENDED OUTLOOK", rows + [paint("The farther out, the closer it is to normal for the date.",
                                                          C.GRAY)], WIDTH - 1):
            print(ln)
    alerts = _alerts(league)
    if alerts:
        for ln in panel("ALERTS", alerts[:3], WIDTH - 1, color=C.BRED):
            print(ln)


def _wrap(text, w):
    import textwrap
    return textwrap.wrap(text, w)


def _alerts(league):
    out = []
    wk = league.week + 1
    for w, name, states in weather.tropical(league.year):
        if wk <= w <= wk + 1 and not league.season_complete:
            from recruiting_data import STATES
            where = ", ".join(STATES.get(s, (s,))[0] for s in states)
            when = "this week" if w == wk else "next week"
            out.append(paint(f"Tropical Storm {name} expected to come ashore {when} — {where}.", C.BRED, C.BOLD))
    return out


def _interest(f):
    """How much of a weather game it looks like, for sorting the board."""
    if f["indoor"]:
        return -1
    t, whi = f["temp"], f["wind"][1]
    return (f["pop"] * (1.4 if f["ptype"] in ("snow", "mix") else 1.0) + max(0, whi - 14) * 2.5
            + max(0, 36 - t) * 2 + max(0, t - 88) * 3 + (80 if "Tropical" in f["headline"] else 0))


def _country(league):
    wk = league.week + 1
    games = league.schedule.get(wk, [])
    if league.season_complete or not games:
        print(paint("\n  No games on the board this week.", C.GRAY))
        return
    rows = []
    for g in games:
        f = weather.forecast(g, league, 0)
        rows.append((_interest(f), f["pop"], g, f))
    rows.sort(key=lambda x: (-x[0], -x[1]))
    print(paint(f"\n  {league.week_name(wk).upper()} FORECASTS — the weather games first\n", C.BCYAN, C.BOLD))
    print(paint(f"  {'GAME':<32}{'WHERE':<15}{'TEMP':>5}  {'PRECIP':<11}{'WIND':<8}OUTLOOK", C.GRAY))
    for sev, pop, g, f in rows[:22]:
        game = truncate(f"{g.away.school} at {g.home.school}" if not g.neutral else f"{g.away.school} vs {g.home.school}", 31)
        where = truncate(weather.place(g)[4] or g.home.school if not weather.indoor(g) else "indoors", 14)
        if f["indoor"]:
            print(f"  {pad(game, 32)}{paint(pad(where, 15), C.GRAY)}{'72°':>5}  {paint('—', C.GRAY)}")
            continue
        pt = {"snow": "snow", "mix": "sleet", "storms": "storms", "rain": "rain"}[f["ptype"]]
        whi = f["wind"][1]
        print(f"  {pad(game, 32)}{paint(pad(where, 15), C.GRAY)}{str(f['temp']) + '°':>5}  "
              f"{pad(f'{pop}% {pt}' if pop >= 10 else 'dry', 11)}{pad(f'{whi} mph', 8)}"
              + paint(truncate(f["headline"], 25), _sev_color(f["severity"])))
    if len(rows) > 22:
        print(paint(f"\n  ...and {len(rows) - 22} more games in ordinary weather.", C.GRAY))
    for a in _alerts(league):
        print("  " + a)


def _last_week(league):
    wk = league.week
    games = [g for g in league.schedule.get(wk, []) if g.played and getattr(g, "wx", None)]
    rows = sorted(games, key=lambda g: -weather.severity(g.wx))
    rows = [g for g in rows if weather.severity(g.wx) >= 2][:18]
    print(paint(f"\n  {league.week_name(wk).upper() if wk else 'LAST WEEK'} — THE WEATHER GAMES\n", C.BCYAN, C.BOLD))
    if not rows:
        print(paint("  Nothing worth talking about. Football weather everywhere.", C.GRAY))
        return
    for g in rows:
        w, l = g.winner, g.loser
        score = f"{w.school} {g.score_for(w)}, {l.school} {g.score_for(l)}"
        print(f"  {pad(truncate(score, 44), 45)}{paint(pad(truncate(weather.summary(g.wx), 30), 31), C.GRAY)}"
              + paint(truncate(weather.headline(g.wx), 22), _sev_color(weather.severity(g.wx))))


def _book(league, team):
    if team is None:
        return
    book = league.__dict__.get("wx_book", {}).get(team.school, [])
    print(paint(f"\n  {team.school.upper()} IN THE WEATHER\n", C.BCYAN, C.BOLD))
    if not book:
        print(paint("  No weather games on file yet. They'll show up here: the rain, the snow, the wind, "
                    "the heat.", C.GRAY))
        return
    def rec(rows):
        w = sum(1 for r in rows if r[4])
        return f"{w}-{len(rows) - w}"
    groups = [("Rain & storms", [r for r in book if r[7] in ("Rain", "Storms", "Tropical storm", "Sleet")]),
              ("Snow", [r for r in book if r[7] == "Snow"]), ("Wind", [r for r in book if r[7] == "Windy"]),
              ("Cold (35° or colder)", [r for r in book if r[8] <= 35]), ("Heat (90° or hotter)", [r for r in book if r[9] >= 90])]
    line = "   ".join(f"{paint(name, C.GRAY)} {paint(rec(rows), C.BWHITE, C.BOLD)}" for name, rows in groups if rows)
    print("  " + line + "\n")
    cold = min(book, key=lambda r: r[8])
    hot = max(book, key=lambda r: r[9])
    ext = []
    if cold[8] <= 40:
        ext.append(f"Coldest: {cold[8]}° {cold[3]} {cold[2]} ({cold[0]})")
    if hot[9] >= 85:
        ext.append(f"Hottest: {hot[9]}° {hot[3]} {hot[2]} ({hot[0]})")
    if ext:
        print(paint("  " + "   ".join(ext) + "\n", C.GRAY))
    print(paint(f"  {'YEAR':<6}{'WK':<4}{'GAME':<30}{'RESULT':<12}{'WEATHER':<16}TEMP", C.GRAY))
    for r in reversed(book[-24:]):
        yr, wk, opp, at, won, pf, pa, lab, lo, hi, storm, sev = r
        res = paint(f"{'W' if won else 'L'} {pf}-{pa}", C.BGREEN if won else C.BRED)
        print(f"  {yr:<6}{wk:<4}{pad(truncate(f'{at} {opp}', 28), 30)}{pad(res, 12)}"
              f"{paint(pad(lab if not storm else 'TS ' + storm, 16), _sev_color(sev))}{lo}°" + (f"-{hi}°" if hi - lo >= 6 else ""))
