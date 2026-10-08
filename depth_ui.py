"""Interactive fall-camp and in-season depth rooms.

The depth room deliberately uses the same panel/chip/footer vocabulary as the
rest of Console College.  It is information-dense, but should feel like a
football staff room rather than a debug list.
"""
import re
import textwrap

from ui import (C, WIDTH, ask, chip, clear, columns, footer, key, meter, pad,
                paint, panel, section, title_bar, truncate, visible_len)
from models import POSITIONS, POSITION_NAMES


def _number_choice(prompt, room, exclude=None):
    """Ask for a player by the number shown on the depth card. Blank cancels."""
    exclude = set(exclude or ())
    while True:
        raw = ask(prompt).strip()
        if not raw:
            return None
        try:
            idx = int(raw) - 1
        except ValueError:
            idx = -1
        if 0 <= idx < len(room) and idx not in exclude:
            return idx
        print(paint("  Enter one of the player numbers shown above, or press Enter to cancel.", C.BYELLOW))


def _switch_players(team, pos, room):
    """Guided two-step swap. The user never has to remember command syntax."""
    if len(room) < 2:
        return False, "There is only one player in this room."
    a = _number_choice("Who do you want to switch?  Player number (Enter cancels):", room)
    if a is None:
        return False, "Switch canceled."
    b = _number_choice(f"Switch {room[a].name} with who?  Player number (Enter cancels):", room, exclude={a})
    if b is None:
        return False, "Switch canceled."
    first, second = room[a], room[b]
    room[a], room[b] = room[b], room[a]
    return True, f"Switched {first.name} and {second.name}."


def _choose_position_move(ideas):
    """Guided position-change picker for the ideas already printed above."""
    if not ideas:
        return None
    while True:
        raw = ask("Which position move?  Idea number (Enter cancels):").strip()
        if not raw:
            return None
        try:
            idx = int(raw) - 1
        except ValueError:
            idx = -1
        if 0 <= idx < len(ideas):
            return ideas[idx]
        print(paint("  Enter one of the position-move numbers shown above, or press Enter to cancel.", C.BYELLOW))


def _signed(value, good=C.BGREEN, bad=C.BRED, quiet=C.GRAY):
    if value > .15:
        return paint(f"+{value:.1f}", good, C.BOLD)
    if value < -.15:
        return paint(f"{value:.1f}", bad, C.BOLD)
    return paint(f"{value:+.1f}", quiet)


def _rank(rank, total):
    col = C.BGREEN if rank == 1 else C.BYELLOW if rank <= max(2, total // 2) else C.GRAY
    return paint(f"#{rank}", col, C.BOLD)


def _movement(cur_rank, staff_rank):
    """Show where the blended staff board would move this player."""
    d = cur_rank - staff_rank
    if d > 0:
        return paint(f"▲{d}", C.BGREEN, C.BOLD)
    if d < 0:
        return paint(f"▼{abs(d)}", C.BRED, C.BOLD)
    return paint("—", C.GRAY)


def _form_label(form):
    if form >= .75:
        return paint("HOT", C.BGREEN, C.BOLD)
    if form >= .20:
        return paint("UP", C.GREEN, C.BOLD)
    if form <= -.75:
        return paint("COLD", C.BRED, C.BOLD)
    if form <= -.20:
        return paint("DOWN", C.YELLOW, C.BOLD)
    return paint("STEADY", C.GRAY, C.BOLD)


def _film_label(delta):
    if delta >= 4:
        return paint("OUTPLAYING GRADE", C.BGREEN, C.BOLD)
    if delta >= 1:
        return paint("TRENDING UP", C.GREEN, C.BOLD)
    if delta <= -4:
        return paint("UNDER GRADE", C.BRED, C.BOLD)
    if delta <= -1:
        return paint("TRENDING DOWN", C.YELLOW, C.BOLD)
    return paint("ON EXPECTATION", C.GRAY, C.BOLD)


def _staff_header(league, team, pos, n):
    """Two compact staff-room panels at the top of every position screen."""
    import depth_staff
    evc = depth_staff.evaluator(team, pos, "coord")
    evp = depth_staff.evaluator(team, pos, "pos")
    coord = [
        paint(truncate(evc["name"], 30), C.BWHITE, C.BOLD),
        f"Lean  {chip(str(evc['lean']).upper(), C.BCYAN)}",
        paint("Sets the big-picture board for this room.", C.GRAY),
    ]
    pc = [
        paint(truncate(evp["name"], 30), C.BWHITE, C.BOLD),
        f"Lean  {chip(str(evp['lean']).upper(), C.BCYAN)}",
        paint("Owns the daily reps and position detail.", C.GRAY),
    ]
    left = panel("COORDINATOR", coord, 49, color=league.team_color(team), height=3)
    right = panel(f"POSITION COACH  ·  {n} STARTER{'S' if n != 1 else ''}", pc, 50,
                  color=league.team_color(team), height=3)
    return columns(left, right)


def _trait_descriptions(p):
    """Visible personality/traits for one player, described in plain football language only."""
    import traits
    items = []
    try:
        pk = traits.persona(p)
        if pk in traits.PERSONAS:
            label, blurb = traits.PERSONAS[pk][0], traits.PERSONAS[pk][1]
            items.append(("PERSONALITY", label, blurb))
    except Exception:
        pass
    for tk in (getattr(p, "traits", ()) or ()):
        if tk in traits.PLAYER_TRAITS:
            label, blurb = traits.PLAYER_TRAITS[tk][0], traits.PLAYER_TRAITS[tk][1]
            items.append(("TRAIT", label, blurb))
    return items[:5]


def _trait_lines(p, width=84):
    """Render a player's own descriptions inside his card; no hidden modifier numbers."""
    out = []
    for kind, label, blurb in _trait_descriptions(p):
        tag = chip(kind, C.BMAGENTA if kind == "PERSONALITY" else C.BCYAN)
        lead_plain = f"{kind}  {label} — "
        room = max(34, width - len(lead_plain))
        wrapped = textwrap.wrap(blurb, width=room) or [blurb]
        out.append(f"{tag}  {paint(label, C.BWHITE, C.BOLD)}  {paint('— ' + wrapped[0], C.GRAY)}")
        if len(wrapped) > 1:
            out.extend(paint(" " * 16 + x, C.GRAY) for x in wrapped[1:])
    return out


def _player_lines(league, team, p, pos, idx, n, camp_mode, staff_order):
    import depth_staff, morale, traits, scout

    total = len(team.players_at(pos))
    cr, ct = depth_staff.take(league, team, p, pos, "coord")
    pr, pt = depth_staff.take(league, team, p, pos, "pos")
    form = depth_staff.camp_form(league, team, p)
    blend_rank = staff_order.index(p) + 1 if p in staff_order else idx
    starter = idx <= n

    role = chip("STARTER", C.BGREEN) if starter else chip("ROTATION", C.GRAY)
    move = _movement(idx, blend_rank)
    identity = (f"{role}  {paint(p.class_label, C.GRAY)}   {scout.ovr_tag(p)}   "
                f"{paint('Morale', C.GRAY)} {paint(f'{morale.get(p):.0f}', C.BWHITE, C.BOLD)} {meter(morale.get(p), 8)}")
    board = (f"{paint('STAFF BOARD', C.GRAY)} {_rank(blend_rank, total)} {move}   "
             f"{paint('Coordinator', C.GRAY)} {_rank(cr, total)}   "
             f"{paint('Position coach', C.GRAY)} {_rank(pr, total)}")

    lines = [identity, board]
    if camp_mode:
        sessions = depth_staff.camp(league, team).get(id(p), [])
        vals = [x[1] for x in sessions]
        session_text = "   ".join(
            f"S{i} {_signed(v)}" for i, v in enumerate(vals, 1)
        ) or paint("No camp reps recorded", C.GRAY)
        lines.append(f"Camp     {session_text}   ·   AVG {_signed(form)}  {_form_label(form)}")
        # The detailed practice prose is useful, but one concise latest-note keeps the card readable.
        if sessions:
            lines.append(paint("Tape     " + truncate(sessions[-1][0], 78), C.GRAY))
    else:
        film = depth_staff.recent(p)
        delta = depth_staff.recent_delta(p)
        grades = "  ".join(paint(f"{x:.0f}", C.BGREEN if x >= 75 else C.BYELLOW if x >= 65 else C.BRED,
                                     C.BOLD) for x in film) if film else paint("NO FILM", C.GRAY)
        lines.append(f"Film     {grades}   ·   vs expected {_signed(delta)}  {_film_label(delta)}")
        lines.append(f"Practice {_signed(form)}  {_form_label(form)}")

    disagree = abs(cr - pr)
    voice = paint("STAFF SPLIT", C.BYELLOW, C.BOLD) if disagree >= 2 else paint("STAFF ALIGNED", C.GRAY)
    lines.append(f"{paint('STAFF READ', C.GRAY)}  {voice}")
    # Give each staff voice up to two wrapped lines so longer, more varied comments stay readable.
    for label, note in (("Coordinator", ct), ("Position coach", pt)):
        wrapped = textwrap.wrap(note, width=72) or [note]
        lines.append(paint(f"  {label:<15}", C.GRAY) + paint(wrapped[0], C.BWHITE))
        if len(wrapped) > 1:
            lines.append(paint(" " * 17 + wrapped[1], C.GRAY))

    trait_lines = _trait_lines(p)
    if trait_lines:
        lines.append("")
        lines.append(paint("WHAT HIS TAGS MEAN", C.BCYAN, C.BOLD))
        lines.extend(trait_lines)
    return lines


def _screen_key(camp_mode):
    """Plain-English legend for the shorthand used on every depth card."""
    if camp_mode:
        entries = [
            ("S1 / S2 / S3", "Camp practice sessions. + means he beat expectation; - means he was below it."),
            ("AVG", "Average of the three camp sessions. This is practice form, not an OVR change."),
            ("HOT / UP / STEADY / DOWN / COLD", "Quick read of that camp average. DOWN means a poor camp, not lost ratings."),
        ]
    else:
        entries = [
            ("FILM", "Grades from the last games. Higher is better; 'vs expected' compares those grades with his talent level."),
            ("PRACTICE", "Current practice form. + is above expectation; - is below it."),
            ("TRENDING / UNDER / ON EXPECTATION", "Whether recent game film is beating, missing, or matching expectation."),
        ]
    entries += [
        ("STAFF BOARD #", "Blended coordinator + position-coach ranking. ▲ means staff would move him up; ▼ means down; — means keep him here."),
        ("COORD # / POS COACH #", "Each coach's independent rank. STAFF SPLIT means they differ by two or more spots."),
        ("SWITCH PLAYER", "Press S, choose the first player by his depth number, then choose the player you want to swap him with."),
    ]
    out = []
    for label, explanation in entries:
        prefix = label + "  "
        wrapped = textwrap.wrap(explanation, width=max(30, 88 - len(prefix))) or [explanation]
        out.append(paint(label, C.BWHITE, C.BOLD) + "  " + wrapped[0])
        out.extend(" " * (len(label) + 2) + x for x in wrapped[1:])
    return out


def _show_room(league, team, pos, camp_mode, msg=""):
    import depth_staff, practice
    n = practice.starter_counts(team).get(pos, 1)
    cur = list(team.players_at(pos))
    staff_order = depth_staff.order(league, team, pos, "blend")

    clear()
    phase = "DECIDE YOUR DEPTH" if camp_mode else "MANAGE DEPTH CHART"
    print(title_bar(f"{team.school.upper()}  ·  {phase}  ·  {POSITION_NAMES[pos].upper()}",
                    league.team_color(team)))
    for ln in _staff_header(league, team, pos, n):
        print(ln)
    if msg:
        print()
        print(paint("  ◆ ", C.BYELLOW, C.BOLD) + paint(msg, C.BWHITE, C.BOLD))

    print()
    print(section("DEPTH ROOM", league.team_color(team)))
    for i, p in enumerate(cur, 1):
        if i == n + 1:
            label = "  CUT LINE  ·  ROTATION / DEVELOPMENT"
            print(paint("  ┄" + label + " " + "┄" * max(1, WIDTH - len(label) - 4), C.GRAY))
        card_title = (f"{i}  ·  #{p.number}  {truncate(p.name, 30).upper()}"
                      f"  ·  {POSITION_NAMES[pos].upper()}")
        card = panel(card_title, _player_lines(league, team, p, pos, i, n, camp_mode, staff_order),
                     96, color=league.team_color(team), title_color=league.team_color(team))
        for ln in card:
            print("  " + ln)

    print()
    for ln in panel("SCREEN KEY", _screen_key(camp_mode), 96, color=C.BCYAN):
        print("  " + ln)
    return cur, n


def _wv_room(league, team, pos, camp_mode, cur, n, ideas, msg):
    import webview
    if not webview.on():
        return
    try:
        import depth_staff, morale, scout
        staff_order = depth_staff.order(league, team, pos, "blend")
        total = len(cur)
        rows = []
        for i, p in enumerate(cur, 1):
            cr, ct = depth_staff.take(league, team, p, pos, "coord")
            pr, pt = depth_staff.take(league, team, p, pos, "pos")
            br = staff_order.index(p) + 1 if p in staff_order else i
            form = depth_staff.camp_form(league, team, p)
            r = {"i": i, "id": webview.pid(p), "num": p.number, "name": p.name, "yr": p.class_label,
                 "ovr": webview.plain(scout.ovr_tag(p)), "morale": round(morale.get(p)), "starter": i <= n,
                 "staff": br, "coord": cr, "posc": pr, "move": i - br, "split": abs(cr - pr) >= 2,
                 "coordNote": ct, "posNote": pt, "form": round(form, 1), "formWord": webview.plain(_form_label(form)),
                 "hurt": p.inj_games > 0, "traits": [label for _, label, _ in _trait_descriptions(p)]}
            if camp_mode:
                r["camp"] = [round(x[1], 1) for x in depth_staff.camp(league, team).get(id(p), [])]
            else:
                r["film"] = [round(x) for x in depth_staff.recent(p)]
                r["filmWord"] = webview.plain(_film_label(depth_staff.recent_delta(p)))
            rows.append(r)
        evc = depth_staff.evaluator(team, pos, "coord")
        evp = depth_staff.evaluator(team, pos, "pos")
        webview.emit("depth", {"school": team.school, "pos": pos, "posName": POSITION_NAMES[pos], "n": n,
                               "camp": bool(camp_mode), "total": total, "rows": rows, "msg": msg,
                               "coord": {"name": evc["name"], "lean": str(evc["lean"])},
                               "posCoach": {"name": evp["name"], "lean": str(evp["lean"])},
                               "ideas": [{"i": k, "name": p.name, "old": old, "new": new, "why": why}
                                         for k, (p, old, new, why) in enumerate(ideas, 1)],
                               "color": webview._color(league, team)})
    except Exception:
        pass


def room(league, team, pos, camp_mode=True):
    """Run one position room. In-season navigation returns next/prev/back."""
    import depth_staff, depth, practice
    depth_staff.ensure_position_staff(league, team)
    n = practice.starter_counts(team).get(pos, 1)
    before = list(team.players_at(pos)[:n])
    msg = ""

    while True:
        cur, n = _show_room(league, team, pos, camp_mode, msg)
        msg_shown, msg = msg, ""
        ideas = [x for x in depth.move_ideas(league, team) if x[1] == pos]
        if ideas:
            print()
            print(section("POSITION MOVE IDEAS", C.BCYAN))
            for i, (p, old, new, why) in enumerate(ideas, 1):
                print(f"  {chip(str(i), C.BCYAN)}  {paint(p.name, C.BWHITE, C.BOLD)}  "
                      f"{paint(old, C.GRAY)} → {paint(new, C.BCYAN, C.BOLD)}  ·  {paint(why, C.GRAY)}")

        if camp_mode:
            footer(key("S", "Switch player"),
                   key("C", "Use coordinator board"), key("P", "Use position-coach board"),
                   key("L", "Let staff set depth", C.BGREEN), key("X", "Change position"),
                   key("Enter", "Done", C.GRAY))
            prompt = "Choose an action — S switch · C/P staff board · L staff decides · X position change · Enter done:"
        else:
            footer(key("S", "Switch player"),
                   key("C", "Use coordinator board"), key("P", "Use position-coach board"),
                   key("L", "Let staff set depth", C.BGREEN), key("X", "Change position"),
                   key("N", "Next room"), key("PREV", "Previous room"), key("Enter", "Back", C.GRAY))
            prompt = "Choose an action — S switch · C/P staff board · L staff decides · X position change · N/PREV rooms · Enter back:"

        _wv_room(league, team, pos, camp_mode, cur, n, ideas, msg_shown)
        c = ask(prompt).strip().lower()
        if not c or c in ("b", "back"):
            depth_staff.react_to_change(league, team, pos, before)
            return "done" if camp_mode else "back"
        mv = re.match(r"^(u|up|d|dn|down)\s*(\d+)$", c)
        if mv:                                            # one-tap moves (the web app's ↑ / ↓ buttons)
            room_ = list(team.players_at(pos))
            k = int(mv.group(2)) - 1
            j = k - 1 if mv.group(1).startswith("u") else k + 1
            if 0 <= k < len(room_) and 0 <= j < len(room_):
                room_[k], room_[j] = room_[j], room_[k]
                depth_staff.apply_order(team, pos, room_)
                msg = f"Moved {room_[j].name} {'up' if j < k else 'down'} to #{j + 1}."
            continue
        if not camp_mode and c in ("n", "next"):
            depth_staff.react_to_change(league, team, pos, before)
            return "next"
        if not camp_mode and c in ("prev", "previous", "pv"):
            depth_staff.react_to_change(league, team, pos, before)
            return "prev"
        if c in ("c", "p", "l"):
            who = {"c": "coord", "p": "pos", "l": "blend"}[c]
            label = {"c": "coordinator", "p": "position coach", "l": "blended staff"}[c]
            depth_staff.apply_order(team, pos, depth_staff.order(league, team, pos, who))
            msg = f"Applied the {label} board."
            continue
        if c in ("s", "switch", "switch player"):
            room_ = list(team.players_at(pos))
            changed, note = _switch_players(team, pos, room_)
            if changed:
                depth_staff.apply_order(team, pos, room_)
            msg = note
            continue
        if c in ("x", "position", "position change", "change position"):
            pick = _choose_position_move(ideas)
            if pick is None:
                msg = "Position change canceled." if ideas else "No position-change ideas are available for this room."
            else:
                p, old, new, why = pick
                depth.apply_move(league, team, p, new)
                msg = f"Moved {p.name}: {old} → {new}."
            continue
        msg = "Command not recognized. Choose one of the labeled actions at the bottom."


def decide_camp(league, team):
    import depth_staff
    depth_staff.ensure_position_staff(league, team)
    depth_staff.camp(league, team)
    done = team.__dict__.setdefault("depth_decided", {}).setdefault(league.year, set())
    for pos in POSITIONS:
        if pos in done:
            continue
        room(league, team, pos, True)
        done.add(pos)
    team.depth_set = league.year
    team.depth_decided[league.year] = done


def manage(league, team):
    i = 0
    while True:
        action = room(league, team, POSITIONS[i], False)
        if action == "next":
            i = (i + 1) % len(POSITIONS)
        elif action == "prev":
            i = (i - 1) % len(POSITIONS)
        else:
            return
