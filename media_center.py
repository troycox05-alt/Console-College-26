"""
media_center.py — The college football week, as the press sees it.

The Media Center opens as a dashboard (media_hub.py). These are the screens behind it:

  [1] The Wire              headlines written from last week's results
  [2] Players of the Week   offense, defense, freshman, special teams
  [3] Stat Leaders          passing, rushing, receiving, defense
  [4] Team Rankings         scoring, yards, sacks
  [5] Hot Seat Watch        coach.seat plus what this season is doing to it, week to week
  [6] Injury Report         everybody who's out, nationwide
  [7] Playoff Projection    the 12-team bracket if the season ended today
  [8] Award Races           Golden Helmet, defense, freshman, coach of the year
  [9] Campus Countdown Desk          the crew's pick standings and where the show has been

Everything here only reads the world. Looking never changes anything.
"""
from collections import Counter

from ui import C, WIDTH, ask, clear, clip, pad, paint, pause, rating, rule, section, title_bar, truncate

POS_WORD = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "OL": "OL", "DL": "DL", "LB": "LB", "CB": "CB",
            "S": "S", "K": "K", "P": "P"}


def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def _last_week(league):
    """The most recent week with results."""
    for w in range(league.week, 0, -1):
        games = [g for g in league.schedule.get(w, []) if g.played]
        if games:
            return w, games
    return None, []


def _rank(league, t):
    r = league.rankings.rank_of(t)
    return f"#{r} " if r else ""


def _yr(p):
    return p.class_label


# ═══ Menu ═══════════════════════════════════════════════════════════════════

def media_menu(league):
    """The Media Center is a dashboard now (media_hub.py); the old list lives on as list_menu."""
    import media_hub
    media_hub.hub(league)


def list_menu(league):
    items = [("1", "The Wire — this week's headlines", wire), ("2", "Players of the Week", players_of_week),
             ("3", "Stat Leaders", stat_leaders), ("4", "Team Rankings", team_rankings),
             ("5", "Hot Seat Watch", hot_seat_watch), ("6", "Injury Report", injury_report),
             ("7", "Playoff Projection", playoff_projection), ("8", "Award Races", award_races),
             ("9", "Campus Countdown Desk", gameday_desk), ("10", "Awards Archive", _awards),
             ("11", "Pro League Draft", _draft), ("12", "Rivalry Trophies", _trophies),
             ("13", "Conference Realignment", _realign), ("14", "Instant Classics", _classics),
             ("15", "Parity Report", _parity), ("16", "Compliance Wire", _compliance),
             ("17", "History Lookup", _history)]
    while True:
        clear()
        print(title_bar("MEDIA CENTER"))
        wk, games = _last_week(league)
        sub = f"Through {league.week_name(wk)}" if wk else "Preseason — no games played yet"
        print(paint(f"   {league.year} season  ·  {sub}", C.GRAY))
        print()
        for key, label, _ in items:
            print(f"   {paint(f'[{key}]', C.BYELLOW, C.BOLD)}  {label}")
        print(f"   {paint('[B]', C.GRAY, C.BOLD)}  Back")
        choice = ask("Select:").lower()
        if choice in ("b", ""):
            return
        for key, _, fn in items:
            if choice == key:
                fn(league)



def _history(league):
    import history_screens
    history_screens.lookup_screen(league)

def _compliance(league):
    import compliance_screens
    compliance_screens.wire(league)


def _awards(league):
    import awards_screens
    years = sorted(getattr(league, "awards", {}))
    y = years[-1] if years else None
    if len(years) > 1:
        c = ask(f"Which year? ({', '.join(map(str, years))}, Enter = {y}):").strip()
        y = int(c) if c.isdigit() and int(c) in years else y
    awards_screens.awards_screen(league, y)


def _parity(league):
    import dynasty
    dynasty.parity_screen(league)


def _classics(league):
    import classics
    classics.classics_screen(league)


def _realign(league):
    import realignment
    realignment.realignment_screen(league)


def _trophies(league):
    import rivalries
    rivalries.trophy_room(league)


def _draft(league):
    import awards_screens
    years = sorted(getattr(league, "drafts", {}))
    y = years[-1] if years else None
    if len(years) > 1:
        c = ask(f"Which draft? ({', '.join(map(str, years))}, Enter = {y}):").strip()
        y = int(c) if c.isdigit() and int(c) in years else y
    awards_screens.draft_screen(league, y)


# ═══ [1] The Wire ═══════════════════════════════════════════════════════════

def headlines(league):
    """Build the week's news: upsets, huge games, streaks, the poll, injuries, coaching."""
    wk, games = _last_week(league)
    out = []
    if not wk:
        news = getattr(league, "carousel", {}).get(league.year - 1, [])
        import realignment
        for text in realignment.news_for(league, league.year - 1)[:4]:
            out.append(("LEAGUES", text))
        import personalities
        for w, text in personalities.news(league, league.year - 1)[-40:]:
            if w >= 14 and ("returns for" in text or "breaks down" in text):
                out.append(("LOCKER", text))
                if sum(k == "LOCKER" for k, _ in out) >= 3:
                    break
        for kind, text in news[:8]:
            out.append(("COACHING", text))
        if not out:
            out.append(("PRESEASON", f"The {league.year} season kicks off soon. "
                                     f"No. 1 {league.rankings.top(1)[0].school} opens as the favorite."
                        if league.rankings.top(1) else "The season kicks off soon."))
        return out
    # instant classics
    import classics
    for c in sorted((c for c in classics.book(league) if c["year"] == league.year and c["week"] == wk),
                    key=lambda c: -c["score"])[:3]:
        out.append(("CLASSIC", c["headline"]))
    # the locker rooms
    import personalities
    locker = [t for w, t in personalities.news(league) if w == wk]
    for text in locker[:3]:
        out.append(("LOCKER", text))
    # upsets, biggest first
    ups = []
    for g in games:
        rl, rw = getattr(g, "ranks", {}).get(g.loser), getattr(g, "ranks", {}).get(g.winner)
        if rl and (not rw or rw > rl + 5):
            ups.append((rl, g))
    for rl, g in sorted(ups, key=lambda x: x[0])[:4]:
        w, l = g.winner, g.loser
        where = "on the road" if g.away is w and not g.neutral else "at home" if not g.neutral else ""
        out.append(("UPSET", f"{w.school} stuns No. {rl} {l.school} {where}, {g.score_for(w)}-{g.score_for(l)}"
                              .replace("  ", " ")))
    # monster individual games
    big = []
    for g in games:
        if g.box is None:
            continue
        for p, c in g.box.stats.items():
            t = g.box.team_of(p)
            if getattr(t, "fcs", False):
                continue
            if c["pass_yds"] >= 380 or c["pass_td"] >= 5:
                big.append((c["pass_yds"] + c["pass_td"] * 40, f"{p.name} throws for {c['pass_yds']} yards and "
                                                                 f"{c['pass_td']} TDs as {t.school} "
                                                                 f"{'wins' if g.winner is t else 'falls'}"))
            if c["rush_yds"] >= 180:
                big.append((c["rush_yds"] * 1.6, f"{p.name} runs wild — {c['rush_yds']} yards, {c['rush_td']} TD "
                                                  f"for {t.school}"))
            if c["rec_yds"] >= 170:
                big.append((c["rec_yds"] * 1.5, f"{p.name} torches the secondary: {c['rec']} catches, "
                                                 f"{c['rec_yds']} yards for {t.school}"))
            if c["sack"] >= 3.5 or c["int"] >= 3:
                big.append((200, f"{p.name} wrecks the game — {c['sack']:g} sacks, {c['int']} INT for {t.school}"))
    for _, text in sorted(big, key=lambda x: -x[0])[:4]:
        out.append(("STAR", text))
    # thrillers and blowouts
    ots = [g for g in games if g.box is not None and g.box.ot_round and not getattr(g.home, "fcs", False)]
    for g in ots[:2]:
        rounds = g.box.ot_round
        out.append(("THRILLER", f"{g.winner.school} outlasts {g.loser.school} in "
                                f"{'triple ' if rounds >= 3 else 'double ' if rounds == 2 else ''}overtime, "
                                f"{g.score_for(g.winner)}-{g.score_for(g.loser)}"))
    # poll and streaks
    top = league.rankings.top(1)
    if top:
        t = top[0]
        prev = league.rankings.previous_rank(t)
        if prev and prev != 1:
            out.append(("POLL", f"{t.school} takes over at No. 1 after moving up from No. {prev}"))
    unbeaten = [t for t in _fbs(league) if t.losses == 0 and t.wins >= 3]
    if unbeaten and wk >= 5:
        out.append(("UNBEATEN", f"{len(unbeaten)} unbeaten teams remain: "
                                f"{', '.join(t.school for t in sorted(unbeaten, key=lambda t: league.rankings.rank_of(t) or 99)[:6])}"
                                f"{'…' if len(unbeaten) > 6 else ''}"))
    # injuries that matter
    for t in _fbs(league):
        for p in t.injured():
            if getattr(p, "inj_week", -1) == wk and p.inj_games >= 99 and p in t.players_at(p.position)[:1]:
                out.append(("INJURY", f"{t.school} loses starting {p.position} {p.name} for the season "
                                      f"({p.inj_desc})"))
    # the seat
    import carousel as cz
    ovrs = cz.league_ovrs(league)
    heat = {t.coach: projected_heat(league, t.coach, ovrs) for t in _fbs(league)
            if t.coach is not None and t.wins + t.losses >= 4}
    hot = [c for c, h in heat.items() if h >= 80]
    for c in sorted(hot, key=lambda c: -heat[c])[:2]:
        word = cz.seat_word(c, weeks=1)
        out.append(("HOT SEAT", f"Pressure mounts on {c.name} as {c.team.school} falls to {c.team.record}"
                                + (f" — {word}" if word else "")))
    return out


KIND_COLOR = {"UPSET": C.BRED, "STAR": C.BYELLOW, "THRILLER": C.BMAGENTA, "POLL": C.BCYAN, "UNBEATEN": C.BGREEN,
              "INJURY": C.BRED, "HOT SEAT": C.BRED, "COACHING": C.BYELLOW, "LEAGUES": C.BMAGENTA, "LOCKER": C.BCYAN, "CLASSIC": C.BYELLOW, "PRESEASON": C.GRAY}


def wire(league):
    clear()
    wk, _ = _last_week(league)
    print(title_bar(f"THE WIRE  ·  {league.week_name(wk).upper() if wk else 'PRESEASON'}"))
    items = headlines(league)
    if not items:
        print(paint("   A quiet week.", C.GRAY))
    for kind, text in items:
        print(f"   {paint(f'{kind:<10}', KIND_COLOR.get(kind, C.GRAY), C.BOLD)} {text}")
    pause()


# ═══ [2] Players of the Week ════════════════════════════════════════════════

def _off_score(c):
    from impact import offense_impact
    return offense_impact(c)


def _def_score(c):
    from impact import defense_impact
    return defense_impact(c) * 1.6            # same yardstick as the broadcast, scaled to compete


def _st_score(c):
    return c["fg_made"] * 3 - (c["fg_att"] - c["fg_made"]) * 2 + (c["punt_yds"] / max(1, c["punts"]) - 40) * 0.3


def _line(p, c, side):
    if side == "def":
        bits = [f"{c['tkl']} tackles"]
        for k, lbl in (("sack", "sacks"), ("tfl", "TFL"), ("int", "INT"), ("ff", "FF"), ("pbu", "PBU")):
            if c[k]:
                bits.append(f"{c[k]:g} {lbl}")
        return ", ".join(bits)
    if side == "st":
        if c["fg_att"]:
            return f"{c['fg_made']}/{c['fg_att']} FG"
        return f"{c['punts']} punts, {c['punt_yds'] / max(1, c['punts']):.1f} avg"
    if c["pass_att"] >= 10:
        s = f"{c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} yds, {c['pass_td']} TD, {c['pass_int']} INT"
        if c["rush_yds"] >= 40:
            s += f"; {c['rush_yds']} rush yds"
        return s
    if c["rush_att"] >= c["rec"]:
        return f"{c['rush_att']} car, {c['rush_yds']} yds, {c['rush_td']} TD"
    return f"{c['rec']} rec, {c['rec_yds']} yds, {c['rec_td']} TD"


def week_awards(league, games, conference=None):
    best = {"off": (None, -1, None, None), "def": (None, -1, None, None), "fr": (None, -1, None, None),
            "st": (None, -1, None, None)}
    for g in games:
        if g.box is None:
            continue
        for p, c in g.box.stats.items():
            t = g.box.team_of(p)
            if getattr(t, "fcs", False) or (conference and t.conference != conference):
                continue
            win = 1.15 if g.winner is t else 1.0
            for key, score in (("off", _off_score(c) * win), ("def", _def_score(c) * win), ("st", _st_score(c))):
                if score > best[key][1]:
                    best[key] = (p, score, c, t)
            if p.year == 0:                                   # freshmen (true or redshirt) only
                s = max(_off_score(c), _def_score(c) * 1.3)
                if s > best["fr"][1]:
                    best["fr"] = (p, s, c, t)
    return best


def players_of_week(league):
    clear()
    wk, games = _last_week(league)
    print(title_bar(f"PLAYERS OF THE WEEK  ·  {league.week_name(wk).upper() if wk else ''}"))
    if not wk:
        print(paint("   No games yet.", C.GRAY))
        pause()
        return
    aw = week_awards(league, games)
    for key, label, side in (("off", "OFFENSIVE PLAYER OF THE WEEK", "off"),
                             ("def", "DEFENSIVE PLAYER OF THE WEEK", "def"),
                             ("fr", "FRESHMAN OF THE WEEK", None), ("st", "SPECIAL TEAMS PLAYER OF THE WEEK", "st")):
        p, _, c, t = aw[key]
        if p is None:
            continue
        s = side or ("def" if _def_score(c) * 1.3 > _off_score(c) else "off")
        print(section(label, C.BYELLOW))
        print(f"   {paint(p.name, C.BWHITE, C.BOLD)}  {paint(f'{p.position} · {_yr(p)} · {t.school}', C.GRAY)}")
        print(f"   {_line(p, c, s)}")
        print()
    print(section("CONFERENCE OFFENSIVE PLAYERS OF THE WEEK", C.BCYAN))
    confs = sorted({t.conference for t in _fbs(league) if t.conference != "Independent"})
    for conf in confs:
        p, _, c, t = week_awards(league, games, conf)["off"]
        if p is not None:
            print(f"   {pad(paint(conf, league.conference_color(conf), C.BOLD), 16)}{pad(p.name, 24)}"
                  f"{pad(truncate(t.school, 19), 20)}{paint(_line(p, c, 'off'), C.GRAY)}")
    pause()


# ═══ [3] Stat Leaders ═══════════════════════════════════════════════════════

def _rating(s):
    att = s["pass_att"]
    if not att:
        return 0
    return (8.4 * s["pass_yds"] + 330 * s["pass_td"] + 100 * s["pass_cmp"] - 200 * s["pass_int"]) / att


CATEGORIES = [
    ("Passing Yards", "pass_yds", lambda p, s: s["pass_yds"], lambda s: f"{s['pass_cmp']}/{s['pass_att']}, {s['pass_td']} TD, {s['pass_int']} INT"),
    ("Passing TDs", "pass_td", lambda p, s: s["pass_td"], lambda s: f"{s['pass_yds']:,} yds, {s['pass_int']} INT"),
    ("Passer Rating", "rating", lambda p, s: _rating(s) if s["pass_att"] >= 80 else 0,
     lambda s: f"{s['pass_cmp']}/{s['pass_att']}, {s['pass_yds']:,} yds, {s['pass_td']} TD"),
    ("Rushing Yards", "rush_yds", lambda p, s: s["rush_yds"], lambda s: f"{s['rush_att']} car, {s['rush_yds'] / max(1, s['rush_att']):.1f} avg, {s['rush_td']} TD"),
    ("Rushing TDs", "rush_td", lambda p, s: s["rush_td"], lambda s: f"{s['rush_yds']:,} yds"),
    ("Yards per Carry", "ypc", lambda p, s: s["rush_yds"] / s["rush_att"] if s["rush_att"] >= 60 else 0,
     lambda s: f"{s['rush_att']} car, {s['rush_yds']:,} yds"),
    ("Receiving Yards", "rec_yds", lambda p, s: s["rec_yds"], lambda s: f"{s['rec']} rec, {s['rec_td']} TD"),
    ("Receptions", "rec", lambda p, s: s["rec"], lambda s: f"{s['rec_yds']:,} yds, {s['rec_td']} TD"),
    ("Receiving TDs", "rec_td", lambda p, s: s["rec_td"], lambda s: f"{s['rec']} rec, {s['rec_yds']:,} yds"),
    ("Scrimmage Yards", "scrim", lambda p, s: s["rush_yds"] + s["rec_yds"], lambda s: f"{s['rush_yds']:,} rush · {s['rec_yds']:,} rec"),
    ("Tackles", "tkl", lambda p, s: s["tkl"], lambda s: f"{s['tfl']:g} TFL, {s['sack']:g} sacks"),
    ("Sacks", "sack", lambda p, s: s["sack"], lambda s: f"{s['tkl']} tackles, {s['tfl']:g} TFL"),
    ("Tackles for Loss", "tfl", lambda p, s: s["tfl"], lambda s: f"{s['tkl']} tackles, {s['sack']:g} sacks"),
    ("Interceptions", "int", lambda p, s: s["int"], lambda s: f"{s['pbu']} pass breakups"),
    ("Field Goals", "fg", lambda p, s: s["fg_made"], lambda s: f"{s['fg_made']}/{s['fg_att']}"),
]


def stat_leaders(league):
    cat = 0
    while True:
        clear()
        name, key, value, detail = CATEGORIES[cat]
        print(title_bar(f"STAT LEADERS  ·  {name.upper()}"))
        rows = []
        for t in _fbs(league):
            for p in t.roster:
                v = value(p, p.season_stats)
                if v:
                    rows.append((v, p, t))
        rows.sort(key=lambda x: -x[0])
        print(paint(f"   {'#':>3}  {'PLAYER':<24}{'POS':<5}{'YR':<7}{'SCHOOL':<20}{name.upper():>14}   DETAIL", C.GRAY, C.BOLD))
        for i, (v, p, t) in enumerate(rows[:20], 1):
            if key in ("sack", "tfl"):
                val = f"{v:g}"
            elif isinstance(v, float):
                val = f"{v:.1f}"
            else:
                val = f"{v:,}"
            color = league.conference_color(t.conference)
            print(f"   {paint(f'{i:>3}', C.GRAY)}  {pad(truncate(p.name, 23), 24)}{p.position:<5}{_yr(p):<7}"
                  f"{pad(paint(_rank(league, t) + truncate(t.school, 15), color), 20)}"
                  f"{paint(f'{val:>14}', C.BWHITE, C.BOLD)}   {paint(detail(p.season_stats), C.GRAY)}")
        if not rows:
            print(paint("   No stats yet.", C.GRAY))
        print(rule())
        line = "   "
        for i, c in enumerate(CATEGORIES):
            tag = f"[{i + 1}] {c[0]}"
            line += (paint(tag, C.BYELLOW, C.BOLD) if i == cat else paint(tag, C.GRAY)) + "   "
            if (i + 1) % 5 == 0:
                print(line)
                line = "   "
        if line.strip():
            print(line)
        choice = ask("Category # (Enter = back):").lower()
        if choice in ("", "b", "x"):
            return
        if choice.isdigit() and 1 <= int(choice) <= len(CATEGORIES):
            cat = int(choice) - 1


# ═══ [4] Team Rankings ══════════════════════════════════════════════════════

def team_numbers(t):
    tot = Counter()
    for p in t.roster:
        for k in ("pass_yds", "rush_yds", "sack", "int", "pass_int", "sacked"):
            tot[k] += p.season_stats[k]
    g = max(1, t.wins + t.losses)
    return {"ppg": t.points_for / g, "papg": t.points_against / g, "diff": (t.points_for - t.points_against) / g,
            "ypg": (tot["pass_yds"] + tot["rush_yds"]) / g, "rypg": tot["rush_yds"] / g, "pypg": tot["pass_yds"] / g,
            "sacks": tot["sack"], "ints": tot["int"], "to_margin": tot["int"] - tot["pass_int"]}


TEAM_CATS = [("Scoring Offense", "ppg", True), ("Scoring Defense", "papg", False), ("Point Differential", "diff", True),
             ("Total Offense (yds/g)", "ypg", True), ("Rushing Offense (yds/g)", "rypg", True),
             ("Passing Offense (yds/g)", "pypg", True), ("Team Sacks", "sacks", True),
             ("Interceptions", "ints", True), ("INT Margin", "to_margin", True)]


def team_rankings(league):
    cat = 0
    while True:
        clear()
        name, key, high = TEAM_CATS[cat]
        print(title_bar(f"TEAM RANKINGS  ·  {name.upper()}"))
        rows = [(team_numbers(t)[key], t) for t in _fbs(league) if t.wins + t.losses]
        rows.sort(key=lambda x: -x[0] if high else x[0])
        print(paint(f"   {'#':>3}  {'SCHOOL':<26}{'CONF':<14}{'REC':>6}{name.upper()[:18]:>20}", C.GRAY, C.BOLD))
        for i, (v, t) in enumerate(rows[:25], 1):
            if key == "diff":
                val = f"{v:+.1f}"
            elif key == "to_margin":
                val = f"{v:+g}"
            elif isinstance(v, float):
                val = f"{v:.1f}"
            else:
                val = f"{v:g}"
            print(f"   {paint(f'{i:>3}', C.GRAY)}  {pad(paint(_rank(league, t) + t.school, C.BWHITE), 26)}"
                  f"{pad(paint(t.conference, league.conference_color(t.conference)), 14)}{t.record:>6}"
                  f"{paint(f'{val:>20}', C.BWHITE, C.BOLD)}")
        if not rows:
            print(paint("   No games yet.", C.GRAY))
        print(rule())
        tags = [paint(f"[{i + 1}] {c[0]}", C.BYELLOW if i == cat else C.GRAY) for i, c in enumerate(TEAM_CATS)]
        print("   " + "   ".join(tags[:5]))
        print("   " + "   ".join(tags[5:]))
        choice = ask("Category # (B = back):").lower()
        if choice in ("b", ""):
            return
        if choice.isdigit() and 1 <= int(choice) <= len(TEAM_CATS):
            cat = int(choice) - 1


# ═══ [5] Hot Seat Watch ═════════════════════════════════════════════════════

def projected_heat(league, coach, ovrs=None):
    """Where the seat is right now. Seats move every week of the season
    (carousel.weekly_seats); the real verdict still comes after the season."""
    return getattr(coach, "seat", 30)


SEAT_TAKES = {
    "scorching": ["The boosters have stopped returning calls.", "It's not a question of if anymore.",
                  "The search firm has reportedly been contacted.", "Every loss from here is a referendum.",
                  "The only question is whether he makes it to November."],
    "hot": ["Needs a signature win, soon.", "The fan base has turned.", "Another loss and the whispers get loud.",
            "The AD's public support has been lukewarm.", "Recruits are asking questions."],
    "warm": ["Better finish strong.", "Not in trouble yet — but not safe.", "A bowl game would quiet things down.",
             "Expectations were higher than this.", "One bad month away from real trouble."],
    "cooling": ["Turning things around.", "Bought himself some time.", "The trend is finally pointing up."],
}


def hot_seat_watch(league):
    import carousel as cz
    st = league.__dict__.setdefault("media", {}).setdefault("heat", {})
    ovrs = cz.league_ovrs(league)
    now = {t.school: projected_heat(league, t.coach, ovrs) for t in _fbs(league)
           if t.coach and not cz.is_interim(t.coach)}
    prev_week = max((w for w in st if w < league.week), default=None)
    prev = st.get(prev_week, {})
    st[league.week] = now
    clear()
    print(title_bar(f"HOT SEAT WATCH  ·  {league.week_name(league.week).upper() if league.week else 'PRESEASON'}"))
    print(paint("   Seats move every Saturday: the season against what the AD expects, plus the games people remember.",
                C.GRAY))
    print(paint("   Most ADs wait for the verdict after the season; the impatient ones fire in October.", C.GRAY))
    gone = [t for k, t in getattr(league, "midseason_news", {}).get(league.year, []) if k == "fired"]
    if gone:
        print(paint("   Already fired this season: " + "; ".join(x.split(" — ")[0] for x in gone), C.BRED))
    print(paint(f"   {'#':>3}  {'COACH':<20}{'SCHOOL':<16}{'REC':>5}  {'YR':>2}  {'HEAT':<25}{'MOVE':>5}  THE WORD",
                C.GRAY, C.BOLD))
    rows = sorted(((now[t.school], t) for t in _fbs(league) if t.school in now), key=lambda x: -x[0])
    import random
    for i, (h, t) in enumerate(rows[:25], 1):
        c = t.coach
        tenure = league.year - (c.hired_year or league.year) + 1
        was = getattr(c, "seat_prev", None) if league.week else prev.get(t.school)
        move = "" if was is None else (paint(f"▲{h - was:>3}", C.BRED) if h > was else
                                       paint(f"▼{was - h:>3}", C.BGREEN) if h < was else paint("  —", C.GRAY))
        mood = "scorching" if h >= 85 else "hot" if h >= 70 else "warm" if h >= 50 else "cooling"
        if was is not None and h < was - 5:
            mood = "cooling"
        take = random.Random(f"{c.name}{league.year}{league.week}").choice(SEAT_TAKES[mood])
        word = cz.seat_word(c)
        if word:
            take = word[:1].upper() + word[1:] + "."
        color = C.BRED if h >= 70 else C.BYELLOW if h >= 50 else C.BWHITE
        barw = int(h / 100 * 20)
        bar = paint("━" * barw, color, C.BOLD) + paint("─" * (20 - barw), "\033[38;5;238m")
        print(clip(f"   {paint(f'{i:>3}', C.GRAY)}  {pad(truncate(c.name, 19), 20)}{pad(truncate(t.school, 15), 16)}"
                   f"{t.record:>5}  {tenure:>2}  {bar} {h:>3} {move:>5}  {paint(take, C.GRAY)}", WIDTH))
    print(rule())
    print(paint("   Full profiles, goals and AD styles: Coaches & Carousel → Hot Seat Rankings.", C.GRAY))
    pause()


# ═══ [6] Injury Report ══════════════════════════════════════════════════════

def injury_report(league):
    from injuries import status_text
    mode = "starters"
    while True:
        clear()
        print(title_bar(f"INJURY REPORT  ·  {league.week_name(league.week).upper() if league.week else 'PRESEASON'}"))
        teams = _fbs(league)
        if mode == "top25":
            teams = [t for t in teams if league.rankings.rank_of(t)]
            teams.sort(key=lambda t: league.rankings.rank_of(t))
        rows = []
        for t in teams:
            for p in t.injured():
                starter = p in t.players_at(p.position)[:2]
                if mode == "season" and p.inj_games < 99:
                    continue
                if mode == "starters" and not starter:
                    continue
                rows.append((t, p, starter))
        if mode != "top25":
            rows.sort(key=lambda x: (-(x[1].inj_games >= 99), -x[1].overall))
        labels = {"starters": "Starters only", "all": "Everyone", "top25": "Top 25 teams", "season": "Out for the season"}
        print(paint(f"   {labels[mode]}  ·  {len(rows)} players", C.GRAY))
        _ovr = "LOOK" if __import__("scout").hidden(league) else "OVR"
        print(paint(f"   {'SCHOOL':<22}{'PLAYER':<24}{'POS':<5}{_ovr:<4}   STATUS", C.GRAY, C.BOLD))
        for t, p, starter in rows[:40]:
            status = status_text(p)
            color = C.BRED if p.inj_games >= 99 else C.BYELLOW if p.inj_games >= 3 else C.BWHITE
            tag = paint("  · starter", C.BCYAN) if starter else ""
            print(clip(f"   {pad(paint(_rank(league, t) + truncate(t.school, 17), league.conference_color(t.conference)), 22)}"
                       f"{pad(truncate(p.name, 23), 24)}{p.position:<5}{__import__('scout').ovr_short(p)}   {paint(status, color)}{tag}",
                       WIDTH))
        if len(rows) > 40:
            print(paint(f"   …and {len(rows) - 40} more", C.GRAY))
        if not rows:
            print(paint("   Nobody on this list. A healthy week.", C.GRAY))
        print(rule())
        print(f"   {paint('[S]', C.BYELLOW)} starters  {paint('[A]', C.BYELLOW)} everyone  {paint('[T]', C.BYELLOW)} Top 25  "
              f"{paint('[O]', C.BYELLOW)} out for season  {paint('[B]', C.GRAY, C.BOLD)} back")
        choice = ask("Select:").lower()
        mode = {"s": "starters", "a": "all", "t": "top25", "o": "season"}.get(choice, mode)
        if choice in ("b", ""):
            return


# ═══ [7] Playoff Projection ═════════════════════════════════════════════════

def projection(league):
    import committee
    order = [t for t in committee.order_for_selection(league) if not getattr(t, "fcs", False)]
    idx = {t: i for i, t in enumerate(order)}
    champs = []
    for conf in sorted({t.conference for t in _fbs(league) if t.conference != "Independent"}):
        stand = league.standings(conf)
        if stand:
            champs.append(stand[0])
    auto = sorted(champs, key=lambda t: idx.get(t, 999))[:5]
    at_large = [t for t in order if t not in auto][:7]
    field = sorted(auto + at_large, key=lambda t: idx.get(t, 999))
    bubble = [t for t in order if t not in field][:4]
    return field, set(auto), bubble


def playoff_projection(league):
    clear()
    print(title_bar("PLAYOFF PROJECTION  ·  IF THE SEASON ENDED TODAY"))
    if not any(t.wins + t.losses for t in league.teams):
        print(paint("   Check back once games have been played.", C.GRAY))
        pause()
        return
    field, auto, bubble = projection(league)
    import committee
    c = getattr(league, "committee", None)
    by = "the committee's Playoff Rankings" if c is not None and c.released and c.year == league.year \
        else "the media poll (the committee's first rankings come out after week 9)"
    print(paint(f"   12 teams: the five highest-ranked conference leaders, then seven at-large, seeded by {by}.", C.GRAY))
    print()
    print(section("FIRST-ROUND BYES", C.BYELLOW))
    for i, t in enumerate(field[:4], 1):
        tag = paint(f"  {t.conference} leader", C.GRAY) if t in auto else ""
        print(f"   {paint(f'({i})', C.BGREEN, C.BOLD)} {pad(t.school, 20)}{t.record:>6}{tag}")
    print()
    print(section("FIRST ROUND — ON CAMPUS", C.BYELLOW))
    for hi, lo in ((5, 12), (6, 11), (7, 10), (8, 9)):
        h, a = field[hi - 1], field[lo - 1]
        top = field[{5: 4, 6: 3, 7: 2, 8: 1}[hi] - 1]
        print(f"   {pad(f'({lo})', 4)} {pad(a.school, 18)}{a.record:>6}   at   ({hi}) {pad(h.school, 18)}{h.record:>6}   "
              f"{paint(f'winner faces ({top and field.index(top) + 1}) {top.school}', C.GRAY)}")
    print()
    print(section("FIRST FOUR OUT", C.BRED))
    for t in bubble:
        print(f"   {pad(t.school, 20)}{t.record:>6}  {paint(t.conference, league.conference_color(t.conference))}")
    auto_low = [t for t in auto if field.index(t) >= 8]
    if auto_low:
        print(paint(f"\n   Conference leaders in the field on an automatic bid: "
                    f"{', '.join(t.school for t in auto_low)}", C.GRAY))
    pause()


# ═══ [8] Award Races ════════════════════════════════════════════════════════

def award_races(league):
    clear()
    print(title_bar("AWARD RACES"))
    print(section("HEISMAN TROPHY", C.BYELLOW))
    for i, (p, score, blurb) in enumerate(league.rankings.heisman[:5], 1):
        print(f"   {i}. {pad(paint(p.name, C.BWHITE, C.BOLD), 26)}{pad(p.position + ' · ' + p.team.school, 26)}"
              f"{paint(blurb, C.GRAY)}")
    if not league.rankings.heisman:
        print(paint("   The race hasn't started.", C.GRAY))
    print()
    players = [(p, t) for t in _fbs(league) for p in t.roster]
    print(section("DEFENSIVE PLAYER OF THE YEAR", C.BCYAN))
    dp = sorted(players, key=lambda x: -(_def_score(x[0].season_stats) * (1.1 if x[1].win_pct >= .7 else 1)))[:5]
    for i, (p, t) in enumerate(dp, 1):
        print(f"   {i}. {pad(p.name, 24)}{pad(p.position + ' · ' + t.school, 26)}{paint(_line(p, p.season_stats, 'def'), C.GRAY)}")
    print()
    print(section("FRESHMAN OF THE YEAR", C.BGREEN))
    fr = sorted((x for x in players if x[0].year == 0),
                key=lambda x: -max(_off_score(x[0].season_stats), _def_score(x[0].season_stats) * 1.3))[:5]
    for i, (p, t) in enumerate(fr, 1):
        s = p.season_stats
        side = "def" if _def_score(s) * 1.3 > _off_score(s) else "off"
        print(f"   {i}. {pad(p.name, 24)}{pad(p.position + ' · ' + t.school, 26)}{paint(_line(p, s, side), C.GRAY)}")
    print()
    print(section("COACH OF THE YEAR", C.BMAGENTA))
    import carousel as cz
    teams = [t for t in _fbs(league) if t.wins + t.losses >= 3]
    ovrs = cz.league_ovrs(league)
    exp_of = {t: cz.expected_pct(t, league, ovrs) for t in teams}
    cy = sorted(teams, key=lambda t: -(t.win_pct - exp_of[t] + t.wins * 0.01))[:5]
    for i, t in enumerate(cy, 1):
        exp = exp_of[t]
        print(f"   {i}. {pad(t.coach.name, 24)}{pad(t.school, 20)}{t.record:>6}   "
              f"{paint(f'expected about {exp * (t.wins + t.losses):.0f} wins so far', C.GRAY)}")
    pause()


# ═══ [9] Campus Countdown Desk ═══════════════════════════════════════════════════════

def gameday_desk(league):
    import gameday_show as gs
    import settings
    clear()
    print(title_bar("GAMEDAY DESK"))
    rec = gs.standings(league)
    print(section(f"{league.year} PICK STANDINGS", C.BYELLOW))
    if not any(w + l for _, w, l in rec):
        print(paint("   No picks graded yet.", C.GRAY))
    for i, (k, w, l) in enumerate(rec, 1):
        pct = w / (w + l) if w + l else 0
        print(f"   {i}. {pad(settings.cast_name(k), 26)}{w:>3}-{l:<3}   {paint(f'{pct:.3f}'[1:] if w + l else '', C.GRAY)}")
    print()
    print(section("WHERE THE SHOW HAS BEEN", C.BCYAN))
    visits = getattr(league, "gameday", {}).get("visits", {})
    stops = sorted(((y, w, s) for s, v in visits.items() for (y, w) in v), reverse=True)
    for y, w, s in stops[:14]:
        g = next((x for x in league.schedule.get(w, []) if x.home.school == s), None) if y == league.year else None
        res = ""
        if g is not None and g.played:
            res = paint(f"  {g.winner.school} {g.score_for(g.winner)}-{g.score_for(g.loser)}", C.GRAY)
        print(f"   {y}  {league.week_name(w):<32}{pad(s, 20)}{res}")
    if not stops:
        print(paint("   The show hasn't gone on the road yet.", C.GRAY))
    pause()
