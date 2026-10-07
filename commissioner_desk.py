"""
commissioner_desk.py — the Commissioner Desk: the one screen a Commissioner Mode league
runs from. No per-team screens: status, the team registry, the Commissioner Inbox,
advancing a cycle, the league directory, saving.

[O] imports a file of order codes from any desk screen; [M] enters one team's orders by
hand; [U] rolls back to a snapshot (one is taken before and after every import and before
every cycle). [W] writes the league website (the site/ folder you upload to GitHub Pages)
and the local exports/ folder (passwords, the Discord post); [K] gives a team a new website
password; [L] sets the league's title, links and the note shown on the site.
"""
import commissioner as cm
from ui import C, ask, clear, pad, paint, pause, rule, title_bar, truncate


def _switch_line(league):
    st = cm.state(league)["settings"]
    off = [cm.SWITCHES[k][0] for k in cm.SWITCHES if not st.get(k)]
    on = [cm.SWITCHES[k][0] for k in cm.SWITCHES if st.get(k)]
    line = "Off: " + ", ".join(off) if off else "Every system on"
    if on:
        line += "  ·  On: " + ", ".join(on)
    return line + "  ·  Difficulty: Varsity"


def _draw(league, msg=""):
    st = cm.state(league)
    clear()
    print(title_bar("COMMISSIONER DESK", sub=league.status))
    n_player = len(cm.player_teams(league))
    cyc = st["cycle"]
    print()
    print(paint(f"   Cycle {cyc['n']}", C.BWHITE, C.BOLD)
          + paint(f"   ·   next: {cm.cycle_label(league)}", C.BCYAN)
          + paint(f"   ·   league {st['league_id']}", C.GRAY))
    print(paint(f"   {n_player} player team{'s' if n_player != 1 else ''}", C.BGREEN, C.BOLD)
          + paint(f"   ·   {len(league.teams) - n_player} CPU teams (open to claim)", C.GRAY))
    items = cm.open_items(league)
    print(paint(f"   Commissioner Inbox: {len(items)} open", C.BYELLOW if items else C.GRAY, C.BOLD if items else ""))
    nxt = cyc["n"] + 1
    players = cm.player_teams(league)
    sent = [t for t in players if cm.team_row(league, t).get("last_cycle") == nxt]
    imp = st["imports"][-1] if st["imports"] and st["imports"][-1]["cycle"] == nxt else None
    if players:
        print(paint(f"   Orders for cycle {nxt}: {len(sent)} of {len(players)} player teams in", C.BWHITE)
              + (paint(f"   ·   last import {imp['file']}", C.GRAY) if imp else paint("   ·   nothing imported yet", C.GRAY)))
    ex = st.get("exports") or []
    if players:
        if ex and ex[-1]["cycle"] == nxt:
            print(paint(f"   Website: exported for cycle {nxt}", C.BGREEN))
        else:
            print(paint(f"   Website: not exported for cycle {nxt} yet. [W] before you post the cycle.", C.BYELLOW))
    print(paint(f"   {_switch_line(league)}", C.GRAY))
    champ = league.champion_of(league.year) if league.season_complete else None
    if champ is not None:
        print(paint(f"\n   {league.year} national champion: {champ.champion} ({champ.record}), def. {champ.runner_up} {champ.score}-{champ.opp_score}", C.BYELLOW))
    hist = cyc["history"][-4:]
    if hist:
        print(paint("\n   RECENT CYCLES", C.GRAY, C.BOLD))
        for h in reversed(hist):
            print(paint(f"   {h['n']:>4}  {pad(truncate(h['label'], 26), 28)}{truncate(h['summary'], 64)}", C.GRAY))
    if msg:
        print(paint(f"\n   {msg}", C.BGREEN))
    print()
    print(rule())
    print(f"   {paint('[A]', C.BGREEN, C.BOLD)} advance one cycle   {paint('[T]', C.BYELLOW)} teams & owners   "
          f"{paint('[I]', C.BYELLOW)} Commissioner Inbox   {paint('[D]', C.BYELLOW)} league directory")
    print(f"   {paint('[O]', C.BGREEN, C.BOLD)} import order codes   {paint('[M]', C.BYELLOW)} one team's orders by hand   "
          f"{paint('[U]', C.BRED)} roll back to a snapshot")
    print(f"   {paint('[W]', C.BGREEN, C.BOLD)} export the website   {paint('[K]', C.BYELLOW)} new website password   "
          f"{paint('[L]', C.BYELLOW)} league title & links   {paint('[E]', C.BYELLOW)} members   {paint('[N]', C.BGREEN)} league setup")
    print(f"   {paint('[R]', C.BCYAN)} last week's results   {paint('[S]', C.BCYAN)} standings   "
          f"{paint('[P]', C.BCYAN)} polls   {paint('[V]', C.BYELLOW)} save   {paint('[Q]', C.GRAY)} main menu")


def desk(league):
    """Run the league from here. Returns 'menu' to go back to the title screen."""
    import saves
    msg = ""
    while True:
        _draw(league, msg)
        msg = ""
        c = ask("Commissioner:").strip().lower()
        if c == "a":
            label = cm.cycle_label(league)
            print(paint(f"\n   Running cycle {cm.state(league)['cycle']['n'] + 1}: {label}…", C.GRAY), flush=True)
            cm.snapshot(league, f"before cycle {cm.state(league)['cycle']['n'] + 1}")
            cm.ASK[0] = _decide_now
            try:
                msg = cm.advance(league)
            finally:
                cm.ASK[0] = None
            saves.autosave(league)
            if cm.state(league).setdefault("links", {}).get("auto_export", True) and cm.player_teams(league):
                import site_export
                print(paint("   Writing the website…", C.GRAY), flush=True)
                s = site_export.export(league)
                saves.autosave(league)
                msg += f"  Website written ({s['seconds']}s): upload {s['site']}."
        elif c == "t":
            teams_screen(league)
        elif c == "i":
            inbox_screen(league)
        elif c == "o":
            msg = import_screen(league) or ""
        elif c == "m":
            msg = manual_screen(league) or ""
        elif c == "u":
            back = rollback_screen(league)
            if back is not None:
                league = back
                msg = f"Rolled back: cycle {cm.state(league)['cycle']['n']}, {league.status}."
        elif c == "w":
            msg = export_screen(league) or ""
            saves.autosave(league)                # passwords issued here must survive a quit
        elif c == "k":
            msg = password_screen(league) or ""
            saves.autosave(league)
        elif c == "l":
            msg = links_screen(league) or ""
        elif c == "e":
            members_screen(league)
        elif c == "n":
            msg = setup_wizard(league) or ""
            saves.autosave(league)
        elif c == "d":
            path = cm.write_directory(league)
            clear()
            print(title_bar("LEAGUE DIRECTORY"))
            for ln in cm.directory_lines(league):
                print("   " + ln)
            print(paint(f"\n   Saved to {path}", C.BGREEN))
            pause()
        elif c == "r":
            import screens
            games = [g for g in league.schedule.get(league.week, []) if g.played]
            if games:
                screens.week_results(league, games)
            else:
                msg = "No results yet this season."
        elif c == "s":
            import screens
            screens.standings_menu(league)
        elif c == "p":
            import screens
            screens.rankings_menu(league)
        elif c == "v":
            saves.save_screen(league)
        elif c in ("q", "menu"):
            if ask("Back to the main menu? Your league autosaves after every cycle. (y/n)").strip().lower() in ("y", "yes"):
                saves.autosave(league)
                return "menu"


# ═══ Website ═══════════════════════════════════════════════════════════════

def export_screen(league):
    import site_export
    print(paint("\n   Writing the website…", C.GRAY), flush=True)
    s = site_export.export(league)
    clear()
    print(title_bar("WEBSITE EXPORTED", sub=f"cycle {cm.state(league)['cycle']['n'] + 1} · {s['seconds']}s"))
    print()
    print(paint("   UPLOAD THIS FOLDER (all of it, replacing what's there):", C.BGREEN, C.BOLD))
    print(f"     {s['site']}")
    kb = sum(s["sizes"].values()) // 1024
    print(paint(f"     {s['teams']} locked team files, {kb:,} KB of data in all", C.GRAY))
    print()
    print(paint("   KEEP PRIVATE (never upload):", C.BRED, C.BOLD))
    print(f"     passwords   {s['passwords']}")
    print(f"     post        {s['post']}")
    print(f"     directory   {s['directory']}")
    if s["fresh"]:
        print()
        print(paint(f"   NEW PASSWORDS to DM ({len(s['fresh'])}):", C.BYELLOW, C.BOLD))
        for school in s["fresh"][:40]:
            t = next(x for x in league.teams if x.school == school)
            row = cm.team_row(league, t)
            print(f"     {pad(school, 24)}@{pad(row['owner'] or '', 22)}{row['pw']}")
        if len(s["fresh"]) > 40:
            print(paint(f"     …and {len(s['fresh']) - 40} more in the passwords file", C.GRAY))
    print()
    print(paint("   DISCORD POST", C.BCYAN, C.BOLD))
    for ln in site_export.discord_post(league).splitlines():
        print("     " + ln)
    pause()
    return f"Website written for cycle {cm.state(league)['cycle']['n'] + 1}. Upload the site folder."


def password_screen(league):
    clear()
    print(title_bar("NEW WEBSITE PASSWORD"))
    print(paint("\n   Gives one player team a new password. The old one stops working at your next [W].", C.GRAY))
    print(paint("   Their signing key changes too, so any code built with the old login is refused.", C.GRAY))
    t = _find(league, ask("\n   School name (blank = cancel):"))
    if t is None:
        return ""
    if not cm.is_player_team(league, t):
        pause(f"{t.school} isn't a player team. Press Enter...")
        return ""
    if ask(f"   New password for {t.school} (@{cm.owner(league, t)})? (y/n)").strip().lower() not in ("y", "yes"):
        return ""
    pw = cm.issue_password(league, t, rotate_secret=True)
    print(paint(f"\n   {t.school}: {pw}", C.BGREEN, C.BOLD))
    print(paint("   DM it to the coach, then [W] export so the site uses it.", C.GRAY))
    pause()
    return f"New password for {t.school}. Export the website [W] before they log in."


LINK_FIELDS = (("title", "League title", "shown at the top of the site and the Discord post"),
               ("site_url", "Website address", "e.g. https://you.github.io/my-league/"),
               ("form_url", "Submission form", "where coaches paste their code (Google Form, Discord thread…)"),
               ("note", "Note on the site", "one line for everyone this cycle; blank to clear"),
               ("site_dir", "Site folder", "where [W] writes the site; blank = the game's site/ folder"),
               ("auto_export", "Export after [A]", "on (default) writes the website after every cycle; type off to stop"))


def links_screen(league):
    links = cm.state(league).setdefault("links", {})
    while True:
        clear()
        print(title_bar("LEAGUE TITLE & LINKS"))
        print()
        for i, (k, label, hint) in enumerate(LINK_FIELDS, 1):
            val = ("on" if links.get(k, True) else "off") if k == "auto_export" else (links.get(k) or paint('(not set)', C.GRAY))
            print(f"   [{i}] {pad(label, 18)}{val}")
            print(paint(f"       {hint}", C.GRAY))
        c = ask("\n   Number to change, Enter = done:").strip()
        if not c:
            return "Links saved. They show on the site at your next [W]."
        if c.isdigit() and 1 <= int(c) <= len(LINK_FIELDS):
            k = LINK_FIELDS[int(c) - 1][0]
            v = ask(f"   {LINK_FIELDS[int(c) - 1][1]} (blank = clear):").strip()
            if k == "auto_export":
                links[k] = v.lower() not in ("off", "no", "n", "0", "false")
            elif v:
                links[k] = v
            else:
                links.pop(k, None)


# ═══ Teams & owners ═════════════════════════════════════════════════════════

def _ordered(league):
    return sorted(league.teams, key=lambda t: (t.conference == "Independent", t.conference, t.school))


def _find(league, text):
    ordered = _ordered(league)
    text = text.strip()
    if text.isdigit() and 1 <= int(text) <= len(ordered):
        return ordered[int(text) - 1]
    q = text.lower()
    exact = [t for t in league.teams if t.school.lower() == q]
    if exact:
        return exact[0]
    part = [t for t in league.teams if q and q in t.school.lower()]
    return part[0] if len(part) == 1 else None


def teams_screen(league):
    msg = ""
    while True:
        ordered = _ordered(league)
        clear()
        print(title_bar("TEAMS & OWNERS", sub=f"{len(cm.player_teams(league))} player teams"))
        half = (len(ordered) + 1) // 2
        conf_prev = [None, None]
        rows = []
        for col, chunk in enumerate((ordered[:half], ordered[half:])):
            out = []
            for i, t in enumerate(chunk, 1 + col * half):
                who = cm.owner(league, t)
                tag = paint("@" + truncate(who, 12), C.BGREEN) + _status_mark(league, t) if who else paint("CPU", C.GRAY)
                head = t.conference != conf_prev[col]
                conf_prev[col] = t.conference
                out.append(f"{paint(f'{i:>3}', C.GRAY)} {pad(truncate(t.school, 20), 21)}{pad(tag, 16)}"
                           + (paint(' ' + truncate(t.conference, 9), C.GRAY) if head else ""))
            rows.append(out)
        for a, b in zip(rows[0], rows[1] + [""] * (len(rows[0]) - len(rows[1]))):    # noqa: B905 — Python 3.8
            print(f" {pad(a, 50)}{b}")
        if msg:
            print(paint(f"\n   {msg}", C.BGREEN if not msg.startswith("!") else C.BRED))
        print(rule())
        print(paint("   ✓ orders in for the next cycle   ·  m2 = missed 2 cycles in a row (staff recruits from 2)", C.GRAY))
        print(f"   {paint('[C#]', C.BGREEN)} hand a program to a member (C12, or C then a school name)   "
              f"{paint('[R#]', C.BRED)} make it a CPU team   {paint('[O]', C.BGREEN)} import codes   "
              f"{paint('[Enter]', C.GRAY)} back")
        ch = ask("Teams:").strip()
        msg = ""
        if not ch:
            return
        if ch.lower() == "o":
            msg = import_screen(league) or ""
            continue
        verb, rest = ch[:1].lower(), ch[1:].strip()
        if verb not in ("c", "r"):
            continue
        if not rest:
            rest = ask("Which program (number or name)?").strip()
        team = _find(league, rest)
        if team is None:
            msg = f"! No single program matches '{rest}'."
            continue
        if verb == "c":
            cur = cm.owner(league, team)
            name = ask(f"Discord name for {team.school}" + (f" (now @{cur})" if cur else "") + ":").strip().lstrip("@")
            if not name:
                continue
            ok, text = cm.claim(league, team, name)
            if ok:
                text += " " + coach_choice(league, team, name) + " Export [W] so he can log in now." + " Export [W] so he can log in now."
        else:
            if ask(f"Make {team.school} a CPU team? (y/n)").strip().lower() not in ("y", "yes"):
                continue
            ok, text = cm.release(league, team)
        msg = text if ok else "! " + text


def _decide_now(kind, text, options, default):
    """A decision the cycle needs from you right now (a job offer a member didn't plan for, a contract)."""
    print()
    print(paint(f"   {cm.INBOX_KINDS.get(kind, kind).upper()}", C.BYELLOW, C.BOLD))
    print(paint(f"   {text}", C.BWHITE))
    for i, o in enumerate(options, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {o}" + paint("  (default)", C.GRAY) * (i - 1 == default))
    a = ask(f"Answer # (Enter = {default + 1}):").strip()
    return int(a) - 1 if a.isdigit() and 1 <= int(a) <= len(options) else default


def setup_wizard(league):
    """New league, or a wave of new members: title and links, members from a file, then the first site."""
    import os

    import order_import
    clear()
    print(title_bar("LEAGUE SETUP"))
    print(paint("\n   Three steps: the league's title and links, your members from a file, then the website.", C.GRAY))
    pause("Press Enter for step 1, title and links...")
    links_screen(league)
    clear()
    print(title_bar("LEAGUE SETUP · MEMBERS"))
    folder = order_import.folder()
    print(paint(f"""
   Put a CSV in {folder}
   with a row per member: Discord name, school, and (to give him a new coach) the coach form's answers:
       discord, school, first, last, age, background, offense, defense, fourth, blitz
   A header row with those names is easiest (a Discord or Google form export works). A row without a first
   and last name takes over the sitting coach. Skip this to hand programs out one by one with [T].""", C.GRAY))
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".csv"))
    for i, f in enumerate(files, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {f}")
    ch = ask("Members file # (Enter = skip):").strip()
    if ch.isdigit() and 1 <= int(ch) <= len(files):
        res = cm.load_members(league, os.path.join(folder, files[int(ch) - 1]))
        good = sum(1 for _, ok, _m in res if ok)
        print(paint(f"\n   {good} member{'s' if good != 1 else ''} placed; {len(res) - good} problem{'s' if len(res) - good != 1 else ''}.", C.BGREEN))
        for n, ok, m in res:
            if not ok:
                print(paint(f"   row {n}: {m}", C.BRED))
        pause()
    if not cm.player_teams(league):
        return "No members yet. Hand out programs with [T] or a members file, then [W]."
    if ask("Step 3: write the website now? (y/n)").strip().lower() in ("y", "yes"):
        return export_screen(league)
    return "Setup saved. Export the website with [W] when you're ready."


def coach_choice(league, team, member):
    """After a claim: who's on his headset."""
    import carousel as cz
    mine = cm.member_coach(league, member)
    sit = team.coach
    print()
    print(paint(f"   Who coaches {team.school} for @{member}?", C.BWHITE, C.BOLD))
    opts = []
    if sit is not None and not cz.is_interim(sit):
        opts.append(("adopt", f"the sitting head coach, {sit.name} ({sit.age})"))
    if mine is not None and mine is not sit and mine.status != "retired":
        opts.append(("own", f"his own coach, {mine.name} ({mine.age}, now {'at ' + mine.team.school if mine.team else 'out of work'})"))
    opts.append(("new", "a new coach from his Discord form"))
    for i, (_, label) in enumerate(opts, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {label}")
    c = ask("Coach (Enter = 1):").strip() or "1"
    mode = opts[int(c) - 1][0] if c.isdigit() and 1 <= int(c) <= len(opts) else opts[0][0]
    form = None
    if mode == "new":
        form = coach_form()
    return cm.take_over(league, team, member, mode, form)


def coach_form():
    """The Discord form's answers, one prompt each (Enter takes the default)."""
    import career
    import playbook as pb
    print(paint("   Backgrounds: " + "  ".join(f"[{k}] {v[0]}" for k, v in career.BACKGROUNDS.items()), C.GRAY))
    offs, defs = list(pb.OFFENSE_SCHEMES), list(pb.DEFENSE_SCHEMES)
    print(paint("   Offenses: " + "  ".join(f"[{i}] {n}" for i, n in enumerate(offs, 1)), C.GRAY))
    print(paint("   Defenses: " + "  ".join(f"[{i}] {n}" for i, n in enumerate(defs, 1)), C.GRAY))
    print(paint("   Fourth down: [1] Conservative [2] Balanced [3] Aggressive    Blitz: [1] Sit in coverage [2] Pick your spots [3] Bring it", C.GRAY))
    return {"first": ask("First name:").strip(), "last": ask("Last name:").strip(),
            "age": ask("Age (30-60, Enter = 38):").strip() or 38, "background": ask("Background # (Enter = 1):").strip() or "1",
            "offense": ask("Offense # or name (Enter = the background's):").strip() or None,
            "defense": ask("Defense # or name (Enter = the background's):").strip() or None,
            "fourth": ask("Fourth down # (Enter = 2):").strip() or "2", "blitz": ask("Blitz # (Enter = 2):").strip() or "2"}


def members_screen(league):
    """Every member who has played in the league: where he is now, and his coach."""
    st = cm.state(league)
    clear()
    print(title_bar("MEMBERS", sub=f"{len(st['members'])} on file"))
    print()
    for name, m in sorted(st["members"].items(), key=lambda x: (x[1].get("team") is None, x[0].lower())):
        c = cm.member_coach(league, name)
        where = m.get("team") or paint((m.get("status") or "free").upper(), C.BYELLOW)
        coach = f"{c.name}" + (f" ({c.status})" if c is not None and c.team is None else "") if c is not None else "no coach yet"
        print(f"   {pad('@' + truncate(name, 20), 23)}{pad(where, 24)}{paint(coach, C.GRAY)}")
    pause()


# ═══ Commissioner Inbox ═════════════════════════════════════════════════════

def inbox_screen(league):
    while True:
        items = cm.open_items(league)
        clear()
        print(title_bar("COMMISSIONER INBOX", sub=f"{len(items)} open"))
        if not items:
            print(paint("\n   Nothing waiting on you. Job offers, vacancies, new members and import problems\n"
                        "   land here as the later phases switch them on.", C.GRAY))
            if ask("[O] import codes, Enter = back:").strip().lower() == "o":
                import_screen(league)
                continue
            return
        for i, m in enumerate(items, 1):
            team = f" · {m['team']}" if m.get("team") else ""
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(m['id'], C.BCYAN)}{paint(team, C.GRAY)}  {truncate(m['text'], 70)}")
        print(rule())
        ch = ask("Open # ([O] import codes, Enter = back):").strip()
        if not ch:
            return
        if ch.lower() == "o":
            import_screen(league)
            continue
        if not ch.isdigit() or not 1 <= int(ch) <= len(items):
            continue
        m = items[int(ch) - 1]
        clear()
        print(title_bar(m["id"]))
        print(paint(f"\n   {m['text']}", C.BWHITE))
        opts = m.get("options") or ["Acknowledge"]
        for j, o in enumerate(opts, 1):
            print(f"   {paint(f'[{j}]', C.BYELLOW)} {o}")
        a = ask("Answer # (Enter = later):").strip()
        if a.isdigit() and 1 <= int(a) <= len(opts):
            out = cm.resolve(league, m, opts[int(a) - 1])
            if out:
                pause(out + " Press Enter...")


def _status_mark(league, team):
    row = cm.team_row(league, team)
    nxt = cm.state(league)["cycle"]["n"] + 1
    if row.get("last_cycle") == nxt:
        return paint(" ✓", C.BGREEN, C.BOLD)
    m = int(row.get("missed", 0))
    return paint(f" m{m}", C.BRED if m >= 2 else C.BYELLOW) if m else ""


# ═══ Importing order codes ══════════════════════════════════════════════════

def import_screen(league):
    """Pick a file from the imports folder, read the report, apply. Returns a status line."""
    import order_import as oi
    files = oi.list_files()
    clear()
    print(title_bar("IMPORT ORDER CODES", sub=f"cycle {cm.state(league)['cycle']['n'] + 1}"))
    print(paint(f"\n   Put the Google Form's responses (Download → CSV) or a .txt of codes in:\n   {oi.folder()}", C.GRAY))
    if not files:
        print(paint("\n   No .csv or .txt files there yet.", C.BYELLOW))
        pause()
        return None
    print()
    for i, f in enumerate(files[:12], 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {f}")
    ch = ask("File # (Enter = cancel):").strip()
    if not ch.isdigit() or not 1 <= int(ch) <= min(12, len(files)):
        return None
    import os
    report = oi.build_report(league, os.path.join(oi.folder(), files[int(ch) - 1]))
    if not _show_report(league, report):
        return "Import cancelled; nothing changed."
    results = oi.commit(league, report)
    import saves
    saves.autosave(league)
    bad = sum(1 for lines in results.values() for ln in lines if "refused" in ln or "not added" in ln or "no home game" in ln)
    return (f"Imported {len(report['accepted'])} teams' orders for cycle {report['cycle']}"
            + (f" ({bad} individual moves refused; see the import log)" if bad else "") + ".")


def _show_report(league, report):
    """The report, page by page. Returns True to apply."""
    acc, rej = report["accepted"], report["rejected"]
    lines = [paint(f"   {report['file']}: {report['rows']} codes read · {len(acc)} accepted · {len(rej)} rejected · "
                   f"{len(report['superseded'])} superseded · {len(report['missing'])} missing", C.BWHITE, C.BOLD), ""]
    if rej:
        lines.append(paint("   REJECTED", C.BRED, C.BOLD))
        for r in rej:
            lines.append(paint(f"   row {r['row']:>3}  {pad(truncate(r['team'] or '?', 20), 22)}{r['reason']}", C.BRED))
        lines.append("")
    if acc:
        lines.append(paint("   ACCEPTED", C.BGREEN, C.BOLD))
        for school, e in acc.items():
            lines.append(f"   {pad(truncate(school, 20), 22)}{paint('@' + truncate(e['member'] or '', 14), C.GRAY):<20} "
                         f"{truncate(e['summary'], 70)}")
            for w in e["warnings"][:4]:
                lines.append(paint(f"        ! {truncate(w, 88)}", C.BYELLOW))
            if len(e["warnings"]) > 4:
                lines.append(paint(f"        ! …and {len(e['warnings']) - 4} more", C.BYELLOW))
        lines.append("")
    if report["superseded"]:
        lines.append(paint("   SUPERSEDED (a newer code from the same team counts)", C.GRAY, C.BOLD))
        lines.append(paint("   " + ", ".join(f"{s['team']} (row {s['row']})" for s in report["superseded"]), C.GRAY))
        lines.append("")
    if report["missing"]:
        lines.append(paint("   MISSING (standing orders keep running)", C.BYELLOW, C.BOLD))
        lines.append(paint("   " + ", ".join(report["missing"]), C.BYELLOW))
    page = 34
    for start in range(0, max(1, len(lines)), page):
        clear()
        print(title_bar("IMPORT REPORT", sub=f"cycle {report['cycle']} · page {start // page + 1}"))
        for ln in lines[start:start + page]:
            print(ln)
        if start + page < len(lines) and ask("Enter = next page, X = cancel:").strip().lower() == "x":
            return False
    if not acc:
        pause("Nothing to apply. Press Enter...")
        return False
    return ask(f"Apply {len(acc)} teams' orders? A snapshot is saved first. (y/n)").strip().lower() in ("y", "yes")


# ═══ One team's orders by hand ══════════════════════════════════════════════

def manual_screen(league):
    import json

    import order_import as oi
    import orders
    clear()
    print(title_bar("ONE TEAM'S ORDERS BY HAND"))
    print(paint("\n   For a code that came in late or by DM, or orders a member sent you in writing.\n"
                "   Paste the code, or the orders as JSON (the same sections a code carries).", C.GRAY))
    name = ask("Program (number or name):").strip()
    team = _find(league, name) if name else None
    if team is None or not cm.is_player_team(league, team):
        return f"No player team matches '{name}'." if name else None
    text = ask(f"Code or JSON for {team.school}:").strip()
    if not text:
        return None
    if text.startswith(orders.PREFIX + "."):
        try:
            t, payload = orders.verify(league, text)
            if t is not team:
                return f"That code is for {t.school}, not {team.school}."
            data = payload["o"]
        except orders.CodeError as e:
            print(paint(f"\n   The code doesn't check out: {e}.", C.BRED))
            try:
                payload = orders.peek(text)[2]
            except orders.CodeError:
                pause()
                return "Nothing applied."
            if payload.get("t") != team.school:
                pause()
                return "Nothing applied."
            if ask("Apply its orders anyway, on your authority as commissioner? (y/n)").strip().lower() not in ("y", "yes"):
                return "Nothing applied."
            data = payload["o"]
    else:
        try:
            data = json.loads(text)
        except ValueError as e:
            return f"That isn't valid JSON ({e})."
    clean, warn, lines = oi.apply_manual(league, team, data)
    clear()
    print(title_bar(f"ORDERS APPLIED · {team.school.upper()}"))
    print(paint(f"\n   {oi.summarize(clean)}", C.BWHITE))
    for w in warn:
        print(paint(f"   ! {w}", C.BYELLOW))
    for ln in lines:
        print(paint(f"   · {ln}", C.GRAY))
    pause()
    import saves
    saves.autosave(league)
    return f"Orders applied for {team.school}."


# ═══ Rolling back ═══════════════════════════════════════════════════════════

def rollback_screen(league):
    """Pick a snapshot and load it. Returns the restored league, or None."""
    import time

    import saves
    snaps = cm.list_snapshots(league)[:15]
    clear()
    print(title_bar("ROLL BACK TO A SNAPSHOT"))
    if not snaps:
        print(paint("\n   No snapshots yet: one is taken before and after every import and before every cycle.", C.GRAY))
        pause()
        return None
    print(paint("\n   Loading a snapshot puts the league back exactly as it was then. Re-running a cycle from it\n"
                "   gives exactly the same results, so this fixes mistakes but can't re-roll a game.\n", C.GRAY))
    for i, (path, label, cyc, at) in enumerate(snaps, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(truncate(label, 58), 60)}"
              f"{paint(f'cycle {cyc}', C.BCYAN)}  {paint(time.strftime('%b %d %H:%M', time.localtime(at)), C.GRAY)}")
    ch = ask("Snapshot # (Enter = cancel):").strip()
    if not ch.isdigit() or not 1 <= int(ch) <= len(snaps):
        return None
    path, label = snaps[int(ch) - 1][:2]
    if ask(f"Roll back to '{label}'? Everything since is undone (a snapshot of now is kept). (y/n)").strip().lower() not in ("y", "yes"):
        return None
    cm.snapshot(league, "before rolling back")
    restored = saves.load(path)
    cm.log(restored, f"Rolled back to snapshot '{label}'.")
    saves.autosave(restored)
    return restored
