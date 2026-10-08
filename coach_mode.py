"""
coach_mode.py — Call the game yourself.

When you coach a game, the sim stops before every snap your team is involved in:

  Offense   pick a run or pass from the full playbook (or take the staff's call),
            decide fourth downs (go / punt / field goal), set the tempo
            (hurry-up, normal, milk the clock), and call timeouts.
  Defense   optional — pick the defensive call, or let your coordinator handle it.
  Sim ahead hand it to the staff for the rest of the drive, the quarter, the half
            or the game, then take it back whenever you want.

The staff's recommendation is always shown, so you can learn what the AI would do.

Everything around the call — the tablet, series orders, the trainer, the people
moments, the try, kickoffs, flags, challenges, icing, overtime — is sideline.py.

BIG MOMENTS mode: the staff calls the game and the broadcast stays quiet until
a snap that decides it — a fourth down worth thinking about, goal-to-go, a
two-minute drill, a goal-line stand, and every snap of a one-score fourth
quarter. Then the booth comes back on, you get a recap of what you missed,
and the headset is yours until the moment passes.
"""
import random

import playbook as pb
from ui import C, WIDTH, ask, paint, pad, rule, truncate

TEMPOS = {"n": "normal", "h": "hurry-up", "m": "milk the clock"}


def _clock(sec):
    return f"{sec // 60}:{sec % 60:02d}"


def _spot(sim, team, whose="your"):
    """'your own 26', 'their own 31', 'the Toledo 41', 'midfield'."""
    yl = sim.yardline
    if yl == 50:
        return "midfield"
    if yl < 50:
        return f"{whose} own {yl}"
    return f"the {sim.other(team).school} {100 - yl}"


def _play_desc(p):
    if p.kind == "run":
        bits = [p.concept.replace("_", " ")]
        if p.trick:
            bits.append("trick")
        return "run · " + ", ".join(bits)
    depth = p.max_depth
    band = "screen" if p.screen else "quick" if depth <= 7 else "intermediate" if depth <= 16 else "deep"
    bits = [band]
    if p.play_action:
        bits.append("play action")
    if p.rpo:
        bits.append("RPO")
    if p.trick:
        bits.append("trick")
    return "pass · " + ", ".join(bits)


def _def_desc(c):
    return f"{c.rush} rush · {c.coverage} · {c.shell} deep · {c.box} in box"


def big_moment(sim, team, side):
    """Why this snap matters (a short label), or None. side: "OFFENSE" / "DEFENSE".
    What counts is yours to set: Settings → Big moments."""
    import settings
    m = settings.moments()
    opp = sim.other(team)
    margin = sim.score[team] - sim.score[opp]
    q, clock = sim.quarter, sim.clock
    close = abs(margin) <= m["crunch_margin"]
    if q > 4:
        return "overtime" if m["overtime"] else None
    if m["crunch_time"] and q == 4 and clock <= m["crunch_minutes"] * 60 and close:
        return "crunch time"
    if abs(margin) >= m["blowout_margin"]:
        return None                                  # the game's decided; let the staff play it out
    to_goal = 100 - sim.yardline
    if side == "OFFENSE":
        if m["fourth_down"] and sim.down == 4 and ((sim.yardline >= 55 and sim.togo <= 5)
                                                   or (sim.togo <= 2 and sim.yardline >= 35) or sim.yardline >= 65):
            return "fourth down"                     # a real decision, not a routine punt
        if m["two_minute"] and q == 2 and clock <= 120 and sim.yardline >= 35:
            return "two-minute drill"
        if m["two_minute"] and q == 2 and clock <= 45 and sim.yardline >= 20:
            return "end of the half"
        if m["red_zone"] and to_goal <= m["red_zone_yards"] and abs(margin) <= 14:
            return "goal to go" if to_goal <= sim.togo else "red zone"
    else:
        if m["goal_line_stand"] and to_goal <= 5 and q >= 3 and abs(margin) <= 10:
            return "goal-line stand"
        if m["fourth_down_stop"] and sim.down == 4 and q >= 3 and abs(margin) <= 8 and sim.yardline >= 40:
            return "fourth-down stop"
    return None


class Controller:
    def __init__(self, team, call_defense=True, mode="full", call_offense=True):
        self.team = team
        self.call_defense = call_defense
        self.call_offense = call_offense    # False: your OC calls it; you still own fourth downs
        self.tempo = "normal"
        self.auto_until = None          # a function(sim) -> True when you want control back
        self.seen_def_sheet = False
        self.mode = mode                # "full": every snap · "moments": only the snaps that decide it
        self.in_moment = False
        self._seen_scores = 0
        self.moments = 0
        self._fourth_asked, self._fourth_staff = False, None

    # ── big moments ─────────────────────────────────────────────────────
    def _pride_moment(self, sim, side):
        """A game that got away still gives you the headset now and then: your offense
        reaching their 20 in the second half while behind — a drive to prove something.
        Up to two a game; the moment lasts until that drive ends."""
        d = getattr(sim, "drive", None)
        if side != "OFFENSE":
            return None
        if d is not None and d is getattr(self, "_pride_drive", None):
            return "red zone — get something going"
        if sim.quarter < 3 or sim.quarter > 4 or getattr(self, "_pride", 0) >= 2:
            return None
        if sim.score[self.team] >= sim.score[sim.other(self.team)] or 100 - sim.yardline > 20:
            return None
        self._pride = getattr(self, "_pride", 0) + 1
        self._pride_drive = d
        return "red zone — get something going"

    def _gate(self, sim, side):
        """Moments mode: True if this snap is yours. Handles the booth going quiet and coming back."""
        if self.mode != "moments":
            return True
        if self.in_moment:
            # You had the headset for the last snap: whatever it produced (your touchdown,
            # their field goal) you watched live, so it never goes in the catch-up.
            self._seen_scores = len(sim.scoring)
        why = big_moment(sim, self.team, side)
        if why is None:
            why = self._pride_moment(sim, side)
        narr = getattr(sim, "narr", None)
        if why is None:
            if self.in_moment:
                self.in_moment = False
                print(paint("   ▷ Back to the staff. We'll call you when it matters again.", C.GRAY))
            if narr is not None:
                narr.muted = True
            return False
        if not self.in_moment:
            self.in_moment = True
            self.moments += 1
            if narr is not None:
                narr.muted = False
            self._moment_banner(sim, why)
        return True

    def _moment_banner(self, sim, why):
        t, o = self.team, sim.other(self.team)
        q = f"Q{sim.quarter}" if sim.quarter <= 4 else f"OT{sim.quarter - 4}"
        print()
        print(paint(rule("━", C.BMAGENTA), C.BMAGENTA))
        print(f"   {paint('★ BIG MOMENT', C.BMAGENTA, C.BOLD)} — {paint(why.upper(), C.BYELLOW, C.BOLD)}   "
              f"{q} {_clock(sim.clock)}   {paint(t.school, C.BWHITE, C.BOLD)} {sim.score[t]}  {o.school} {sim.score[o]}")
        new = sim.scoring[self._seen_scores:]
        self._seen_scores = len(sim.scoring)
        if new:
            print(paint("   While the staff had it:", C.GRAY))
            for sq, sc, team, what in new[-6:]:
                qq = f"Q{sq}" if sq <= 4 else "OT"
                who = paint(team.school, C.BWHITE if team is t else C.GRAY)
                print(paint(f"     {qq} {_clock(sc)}  ", C.GRAY) + f"{who} {paint(str(what), C.GRAY)}")
        else:
            print(paint("   Nothing's changed on the scoreboard while the staff had it.", C.GRAY))
        print(paint(rule("━", C.BMAGENTA), C.BMAGENTA))

    # ── shared ──────────────────────────────────────────────────────────
    def _auto(self, sim):
        if self.auto_until is None:
            return False
        if self.auto_until(sim):
            self.auto_until = None
            print(paint("\n   ▶ You have the headset back.", C.BYELLOW, C.BOLD))
            return False
        return True

    def header(self, sim, side):
        t, o = self.team, sim.other(self.team)
        down = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(sim.down, "")
        togo = "goal" if 100 - sim.yardline <= sim.togo else sim.togo
        q = f"Q{sim.quarter}" if sim.quarter <= 4 else f"OT{sim.quarter - 4}"
        import fieldview
        import sideline
        if fieldview.mode() in fieldview.TABLET_MODES:
            import tabletview
            tabletview.show(sim, ctl=self, side="off" if side == "OFFENSE" else "def", narr=getattr(sim, "narr", None),
                            force=True)                   # every time the call screen draws: a clean screen
        else:
            fieldview.show(sim, indent=3)                 # the field, with the ball on it
            sideline.tablet(sim, self, "off" if side == "OFFENSE" else "def")
        print(paint(rule("─", C.BMAGENTA), C.BMAGENTA))
        print(f"   {paint('YOUR CALL', C.BMAGENTA, C.BOLD)} — {side}   {q} {_clock(sim.clock)}   "
              f"{paint(t.school, C.BWHITE, C.BOLD)} {sim.score[t]}  {o.school} {sim.score[o]}")
        import staff
        caller = staff.play_caller(t, "off" if side == "OFFENSE" else "def")
        scheme = caller.offense_scheme if side == "OFFENSE" else caller.defense_scheme
        book = paint(f"  ·  {scheme}" + ("" if caller is t.coach else f" ({caller.name.split()[-1]}'s)"), C.GRAY)
        import weather
        c = weather.now(sim)
        if c is not None:
            tl = weather.tail(sim, t)
            wind = (f"wind {c['wind']} " + ("at your back" if tl >= 4 else "in your face" if tl <= -4 else "across the field")
                    if c["wind"] >= 8 else "calm")
            pw = weather.precip_words(c)
            fl = weather.field_words(c)
            rng_d, _ = weather.fg_mods(sim, t)
            kick = f"   ·   FG range {rng_d:+.0f} yds" if abs(rng_d) >= 2 else ""
            print(paint(f"   Weather: {c['temp']}°" + (f" · {pw}" if pw else "") + f" · {wind}"
                        + (f" · field {fl}" if fl not in ("dry",) else "") + kick, C.BCYAN))
        if side == "OFFENSE":
            print(f"   {down} & {togo} at {_spot(sim, t)}  ·  timeouts {sim.timeouts[t]}  ·  tempo {self.tempo}" + book)
        else:
            print(f"   {o.school}: {down} & {togo} at {_spot(sim, o, 'their')}   ·   your timeouts: {sim.timeouts[t]}" + book)

    def sim_menu(self, sim):
        swap = "big moments only" if self.mode == "full" else "every snap"
        print(f"   {paint('[1]', C.BYELLOW)} rest of this drive   {paint('[2]', C.BYELLOW)} end of the quarter   "
              f"{paint('[3]', C.BYELLOW)} end of the half   {paint('[4]', C.BYELLOW)} rest of the game   "
              f"{paint('[B]', C.BYELLOW)} switch to {swap}")
        import webview
        webview.opts("Hand it to the staff until…", [("1", "End of this drive", ""), ("2", "End of the quarter", ""),
                                                      ("3", "End of the half", ""), ("4", "The rest of the game", ""),
                                                      ("b", f"Switch to {swap}", "")])
        c = ask("Hand it to the staff until:").strip().lower()
        if c == "b":
            self.mode = "moments" if self.mode == "full" else "full"
            self.in_moment = self.mode == "moments"            # you're in one right now
            if self.mode == "full" and getattr(sim, "narr", None) is not None:
                sim.narr.muted = False
            print(paint(f"   You'll call {'only the big moments' if self.mode == 'moments' else 'every snap'} "
                        f"from here.", C.BYELLOW))
            return self.mode == "moments" and big_moment(sim, self.team, "OFFENSE") is None
        q = sim.quarter
        drive = sim.drive
        if c == "1":
            self.auto_until = lambda s: s.drive is not drive
        elif c == "2":
            self.auto_until = lambda s: s.quarter != q
        elif c == "3":
            self.auto_until = lambda s: (q <= 2 and s.quarter >= 3) or s.quarter > 4
        elif c == "4":
            self.auto_until = lambda s: False
        if self.auto_until is not None:
            self._seen_scores = len(sim.scoring)     # everything up to now you saw; the staff's part starts here
            self.in_moment = False
        return self.auto_until is not None

    def timeout(self, sim):
        t = self.team
        if not sim.timeouts[t]:
            print(paint("   You're out of timeouts.", C.BRED))
            return
        refund = getattr(sim, "last_runoff", 0)
        if refund and getattr(sim, "last_runoff_q", sim.quarter) == sim.quarter:
            sim.clock = min(900, sim.clock + refund)
            sim.last_runoff = 0
        sim.timeouts[t] -= 1
        sim._n("timeout", t)
        print(paint(f"   Timeout. {_clock(sim.clock)} left, {sim.timeouts[t]} remaining.", C.BYELLOW))
        import sideline
        if sideline.settle(sim, t):
            print(paint("   You gather them up. The building exhales — whatever they had going, it's cooled off.", C.BYELLOW))
            sideline._log(sim, "timeout", f"Timeout to stop the bleeding ({sideline._qc(sim)})", chart="good", weight=0.3)

    # ── substitutions ───────────────────────────────────────────────────
    def substitutions(self, sim):
        """In-game personnel changes: mass subs or a direct same-position swap."""
        from ui import clear
        team = self.team
        while True:
            clear()
            self.header(sim, "OFFENSE" if sim.offense is team else "DEFENSE")
            mass = getattr(sim, "manual_mass_subs", {}).get(team, False)
            print(paint("   SUBSTITUTIONS", C.BCYAN, C.BOLD))
            print(paint("   Changes last for the rest of this game unless you switch them back.", C.GRAY))
            print()
            print(f"   {paint('[1]', C.BYELLOW)} Switch one player   "
                  f"{paint('[2]', C.BYELLOW)} {'Put starters back in' if mass else 'Mass subs — put the backups in'}   "
                  f"{paint('[3]', C.BYELLOW)} Formation/play packages   {paint('[Enter]', C.BYELLOW)} Back")
            c = ask("Substitutions:").strip().lower()
            if c == "":
                return
            if c == "2":
                sim.set_mass_subs(team, not mass)
                print(paint("   Starters are back in." if mass else
                            "   Mass subs are in. The backup units will handle the next snaps.", C.BYELLOW, C.BOLD))
                ask("Press Enter to continue:")
                continue
            if c == "3":
                import formation_subs
                formation_subs.screen(None, team)
                continue
            if c != "1":
                continue
            positions = [p for p in ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P")
                         if len(sim.depth.get(team, {}).get(p, [])) >= 2]
            print()
            print("   " + "   ".join(f"{i+1}. {pos}" for i, pos in enumerate(positions)))
            pc = ask("Position to change (Enter = back):").strip()
            if not pc.isdigit() or not (1 <= int(pc) <= len(positions)):
                continue
            pos = positions[int(pc) - 1]
            room = list(sim.depth[team][pos])
            need = __import__('game_sim').DEPTH_NEED.get(pos, 1)
            print()
            for i, p in enumerate(room):
                tag = "STARTER" if i < need else "backup"
                print(f"   {i+1:>2}. #{p.number:<3} {pad(truncate(p.name, 24), 24)} "
                      f"{paint(tag, C.BGREEN if i < need else C.GRAY)}")
            a = ask("Player to replace/switch (number on this list):").strip()
            if not a.isdigit() or not (1 <= int(a) <= len(room)):
                continue
            first = room[int(a) - 1]
            b = ask(f"Who should replace/switch with {first.name}? (number on this list):").strip()
            if not b.isdigit() or not (1 <= int(b) <= len(room)) or b == a:
                continue
            second = room[int(b) - 1]
            if sim.switch_players(team, pos, first, second):
                print(paint(f"   Switched {first.name} and {second.name} at {pos}.", C.BYELLOW, C.BOLD))
                ask("Press Enter to continue:")

    # ── offense ─────────────────────────────────────────────────────────
    def offense(self, sim, staff_call):
        """Returns an action tuple like choose_offense, or None for the staff's call."""
        if self._auto(sim) or not self._gate(sim, "OFFENSE"):
            return None
        import sideline
        sideline.maybe_checkin(sim, self, "off")     # between series: what the OC sees, your orders
        if not self.call_offense and sim.down != 4:
            return None                     # the OC has the offense; the fourth-down decision is still yours
        self._fourth_asked, self._fourth_staff = sim.down == 4, staff_call
        if staff_call[0] == "play" and staff_call[1].kind == "kneel":
            rec = "Victory formation (kneel)"
        elif staff_call[0] == "play":
            rec = staff_call[1].name
        else:
            rec = {"punt": "Punt", "fg": "Field goal"}.get(staff_call[0], staff_call[0])
        shown = False
        while True:
            if shown:
                c = ask("Call:").strip().lower()
            else:
                shown = True
                c = None
            if c is None:
                pass
            elif c not in ("", "t", "h", "n", "m", "s", "b", "k", "u", "f", "r", "p", "g", "x", "z"):
                print(paint("   That's not a call — R, P, Enter, or one of the options above.", C.GRAY))
                continue
            else:
                result = self._offense_key(sim, c)
                if result == "again":
                    continue
                return result
            self.header(sim, "OFFENSE")
            fg_dist = 100 - sim.yardline + 17
            print(f"   Staff suggests: {paint(rec, C.BCYAN, C.BOLD)}")
            opts = [f"{paint('[R]', C.BYELLOW)} run", f"{paint('[P]', C.BYELLOW)} pass",
                    f"{paint('[Enter]', C.BYELLOW)} staff's call"]
            if sim.down == 4:
                opts += [f"{paint('[U]', C.BYELLOW)} punt", f"{paint('[F]', C.BYELLOW)} field goal ({fg_dist} yds)"]
            opts += [f"{paint('[K]', C.BYELLOW)} kneel", f"{paint('[T]', C.BYELLOW)} timeout",
                     f"{paint('[H/N/M]', C.BYELLOW)} tempo", f"{paint('[S]', C.BYELLOW)} sim ahead",
                     f"{paint('[B]', C.BYELLOW)} substitutions", f"{paint('[G]', C.BYELLOW)} orders"]
            print("   " + "   ".join(opts))
            wv_fourth = {}
            if sim.down == 4 and sim.quarter <= 4:
                fakes = [f"{paint('[X]', C.BYELLOW)} fake punt ({sideline.fake_words(sideline.fake_odds(sim, 'fake_punt'))})"]
                if fg_dist <= 60:
                    fakes.append(f"{paint('[Z]', C.BYELLOW)} fake field goal "
                                 f"({sideline.fake_words(sideline.fake_odds(sim, 'fake_fg'))})")
                chart = sideline.fourth_chart(sim)
                print("   " + "   ".join(fakes) + paint(f"   ·   the chart says: {sideline.CHOICE_WORDS[chart]}", C.GRAY))
                wv_fourth = {"chart": sideline.CHOICE_WORDS[chart],
                             "fakes": [{"key": "x", "label": "Fake punt", "odds": sideline.fake_words(sideline.fake_odds(sim, "fake_punt"))}]
                             + ([{"key": "z", "label": "Fake field goal", "odds": sideline.fake_words(sideline.fake_odds(sim, "fake_fg"))}]
                                if fg_dist <= 60 else [])}
            self._wv_call(sim, "offense", rec, fg_dist=fg_dist, fourth=wv_fourth)

    def _wv_call(self, sim, side, rec, fg_dist=0, fourth=None, personnel="", calls=None):
        import webview
        if not webview.on():
            return
        try:
            t, o = self.team, sim.other(self.team)
            down = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(sim.down, "")
            togo = "goal" if 100 - sim.yardline <= sim.togo else sim.togo
            import staff
            caller = staff.play_caller(t, "off" if side == "offense" else "def")
            d = {"side": side, "rec": rec, "down": down, "togo": togo, "timeouts": sim.timeouts[t],
                 "spot": webview.plain(_spot(sim, t) if side == "offense" else _spot(sim, o, "their")),
                 "tempo": self.tempo, "scheme": caller.offense_scheme if side == "offense" else caller.defense_scheme,
                 "fourth": sim.down == 4 and side == "offense", "fg": fg_dist, "extra": fourth or {}, "personnel": personnel}
            try:
                import weather
                c = weather.now(sim)
                if c is not None:
                    tl = weather.tail(sim, t)
                    d["wx"] = f"{c['temp']}°" + (f" · wind {c['wind']} " + ("at your back" if tl >= 4 else "in your face" if tl <= -4 else "across")
                                                 if c["wind"] >= 8 else " · calm")
            except Exception:
                pass
            if calls is not None:
                mine = pb.DEFENSE_SCHEMES.get(caller.defense_scheme, {})
                d["calls"] = [{"key": str(i), "name": x.name, "desc": _def_desc(x), "star": x.name in mine}
                              for i, x in enumerate(calls, 1)]
            webview.emit("call", d, add=True)
        except Exception:
            pass

    def _offense_key(self, sim, c):
        """One key from the offense prompt. Returns an action, None (staff), or 'again'."""
        if c == "":
            return None
        if c == "t":
            self.timeout(sim)
            return "again"
        if c in ("h", "n", "m"):
            self.tempo = TEMPOS[c]
            print(paint(f"   Tempo: {self.tempo}.", C.BYELLOW))
            return "again"
        if c == "s":
            return None if self.sim_menu(sim) else "again"
        if c == "b":
            self.substitutions(sim)
            return "again"
        if c == "k":
            return ("play", pb.KNEEL, "22")
        if c == "g":
            import sideline
            sideline.checkin(sim, self, "off")
            return "again"
        if c in ("x", "z"):
            if sim.down != 4 or sim.quarter > 4:
                print(paint("   Fakes are a fourth-down call.", C.GRAY))
                return "again"
            if c == "z" and 100 - sim.yardline + 17 > 60:
                print(paint("   Nobody would believe a field goal from there.", C.GRAY))
                return "again"
            return ("fake_punt",) if c == "x" else ("fake_fg",)
        if c == "u":
            if sim.down == 4:
                return ("punt",)
            print(paint("   You only punt on fourth down.", C.GRAY))
            return "again"
        if c == "f":
            if sim.down == 4:
                return ("fg",)
            print(paint("   Field goals are a fourth-down call here.", C.GRAY))
            return "again"
        play = self.pick_play(sim, "run" if c == "r" else "pass")
        if play is not None:
            return ("play", play, self.personnel(sim, play))
        return "again"

    def pick_play(self, sim, kind):
        plays = [p for p in (pb.RUN_PLAYS if kind == "run" else pb.PASS_PLAYS) if p.name != "Hail Mary"
                 or sim.clock < 60]
        import staff
        scheme = pb.OFFENSE_SCHEMES[staff.play_caller(self.team, "off").offense_scheme]["plays"]
        plays.sort(key=lambda p: (p.name not in scheme, p.name))
        from ui import clear
        clear()
        t, o = self.team, sim.other(self.team)
        down = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(sim.down, "")
        print(paint(rule("─", C.BMAGENTA), C.BMAGENTA))
        print(f"   {paint(('RUN' if kind == 'run' else 'PASS') + ' PLAYS', C.BMAGENTA, C.BOLD)}   "
              f"{down} & {sim.togo} at {_spot(sim, t)}   ·   {t.school} {sim.score[t]}  {o.school} {sim.score[o]}")
        print(paint(rule("─", C.BMAGENTA), C.BMAGENTA))
        half = (len(plays) + 1) // 2
        for i in range(half):
            cells = []
            for j in (i, i + half):
                if j < len(plays):
                    p = plays[j]
                    star = paint("★", C.BYELLOW) if p.name in scheme else " "
                    cells.append(f"{paint(f'{j + 1:>2}', C.BYELLOW)} {star}{pad(truncate(p.name, 19), 20)}"
                                 f"{paint(pad(truncate(_play_desc(p), 21), 21), C.GRAY)}")
            print("   " + "   ".join(cells))
        print(paint("   ★ = in your scheme's playbook", C.GRAY))
        import webview
        if webview.on():
            webview.emit("plays", {"kind": kind, "down": down, "togo": sim.togo, "spot": webview.plain(_spot(sim, t)),
                                   "us": t.school, "them": o.school, "su": sim.score[t], "so": sim.score[o],
                                   "plays": [{"key": str(i), "name": p.name, "desc": _play_desc(p), "star": p.name in scheme}
                                             for i, p in enumerate(plays, 1)]})
        c = ask("Play # (Enter = back):").strip()
        if c.isdigit() and 1 <= int(c) <= len(plays):
            return plays[int(c) - 1]
        return None

    def personnel(self, sim, play):
        if "FB" in play.needs:
            return "21"
        if "SLOT_WR" in play.needs:
            return "11"
        if sim.togo <= 2 or 100 - sim.yardline <= 3:
            return "12" if play.kind == "pass" else "22"
        if sim.togo >= 8 and play.kind == "pass":
            return "10"
        return "11"

    # ── defense ─────────────────────────────────────────────────────────
    def def_sheet(self):
        import staff
        calls = list(pb.DEF_CALLS.values())
        caller = staff.play_caller(self.team, "def")
        mine = pb.DEFENSE_SCHEMES.get(caller.defense_scheme, {})
        half = (len(calls) + 1) // 2
        for i in range(half):
            cells = []
            for j in (i, i + half):
                if j < len(calls):
                    d = calls[j]
                    star = paint("★", C.BYELLOW) if d.name in mine else " "
                    cells.append(f"{paint(f'{j + 1:>2}', C.BYELLOW)}{star}{pad(truncate(d.name, 16), 17)}"
                                 f"{paint(pad(truncate(_def_desc(d), 25), 25), C.GRAY)}")
            print("   " + "   ".join(cells))
        print(paint(f"   ★ = in the {caller.defense_scheme} playbook"
                    + ("" if caller is self.team.coach else f" (your DC {caller.name}'s scheme)"), C.GRAY))
        self.seen_def_sheet = True

    def defense(self, sim, personnel, staff_call):
        if self._auto(sim) or not self._gate(sim, "DEFENSE"):
            return None
        import sideline
        sideline.maybe_checkin(sim, self, "def")     # between series: what the DC sees, your orders
        if not self.call_defense:
            return None
        calls = list(pb.DEF_CALLS.values())
        self.header(sim, "DEFENSE")
        print(f"   They're in {personnel} personnel.   Staff suggests: {paint(staff_call.name, C.BCYAN, C.BOLD)}")
        if not self.seen_def_sheet:
            self.def_sheet()
        print(f"   {paint('[#]', C.BYELLOW)} call   {paint('[Enter]', C.BYELLOW)} staff's call   "
              f"{paint('[L]', C.BYELLOW)} list calls   {paint('[T]', C.BYELLOW)} timeout   "
              f"{paint('[S]', C.BYELLOW)} sim ahead   {paint('[B]', C.BYELLOW)} substitutions   "
              f"{paint('[O]', C.BYELLOW)} let the DC call the rest   {paint('[G]', C.BYELLOW)} orders")
        self._wv_call(sim, "defense", staff_call.name, personnel=personnel, calls=calls)
        while True:
            c = ask("Call:").strip().lower()
            if c == "":
                return None
            if c == "g":
                sideline.checkin(sim, self, "def")
                continue
            if c == "c":
                sideline.crowd_up(sim, self)
                continue
            if c == "l":
                self.def_sheet()
                continue
            if c == "t":
                self.timeout(sim)
                continue
            if c == "o":
                self.call_defense = False
                print(paint("   Your coordinator has the defense.", C.BYELLOW))
                return None
            if c == "s":
                if self.sim_menu(sim):
                    return None
                continue
            if c == "b":
                self.substitutions(sim)
                self.header(sim, "DEFENSE")
                print(f"   They're in {personnel} personnel.   Staff suggests: {paint(staff_call.name, C.BCYAN, C.BOLD)}")
                continue
            if c.isdigit() and 1 <= int(c) <= len(calls):
                return calls[int(c) - 1]
            print(paint("   That's not a call — pick a number, or Enter for the staff's call.", C.GRAY))


def setup_for_game(league, game, mode="full", call_defense=None):
    """A Controller for your game, or None. mode: "full" or "moments"."""
    team = league.user_team
    if team not in (game.home, game.away):
        return None
    import staff
    cl = staff.calls(team)
    call_offense = cl["off"] == "HC" or getattr(team, "oc", None) is None
    if call_defense is None:
        call_defense = cl["def"] == "HC" or getattr(team, "dc", None) is None
    return Controller(team, call_defense=call_defense, mode=mode, call_offense=call_offense)
