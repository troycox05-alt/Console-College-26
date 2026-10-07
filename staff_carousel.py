"""
staff_carousel.py — The staff carousel: early December to late January.

After the head coaching carousel, every assistant opening in the country is filled one
at a time, biggest programs first, on a calendar:

  * Openings come from firings, clean-outs by new head coaches, retirements, assistants
    who walk out after their coordinator is fired, and every hire that empties a chair
    somewhere else (the dominoes: an OC hired away opens his job, whose new OC opens a
    position coach job, whose new coach opens one at a smaller school...).
  * Each coordinator search interviews three candidates — proven coordinators, fired head
    coaches, and position coaches ready for their first coordinator job (including the
    school's own). The best willing one gets the offer. Candidates turn jobs down: happy
    where they are, a counteroffer from their school, waiting for a bigger job, staying
    with their guy.
  * A new coordinator brings his guys — assistants who worked under him — and bumps
    whoever had the room. A fired coordinator who lands somewhere takes his unsettled
    guys with him.
  * Your people get calls. A bigger program wants your WR coach as its OC: give him your
    blessing (a career event — your coaching tree grows) or try to keep him.
  * Your openings come up in turn: interview, offer, and sometimes hear no.

Everything goes in a dated news feed (league.staff_carousel_log[year]).
"""
import datetime
import random

import poscoach
import staff
from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

DAYS = 48
FEED_PAGE = 22


def team_by_school(league, school):
    return next((t for t in league.teams if t.school == school), None) if school else None


class Carousel:
    def __init__(self, league, rng, show):
        self.league, self.rng, self.show = league, rng, show
        self.me = staff.user_team(league)
        self.year = league.year
        self.day = datetime.date(league.year, 12, 8)
        self.news, self.unread = [], 0
        self.queue = []
        self.cause = {}
        self.steps = 0
        self.power = staff._power()

    # ── feed ─────────────────────────────────────────────────────────────
    def say(self, text, tag="coord", team=None):
        if tag == "pos" and team is not None and team.conference not in self.power \
                and (self.me is None or team.conference != self.me.conference):
            return                                           # small-school position moves stay off the wire
        self.news.append((self.day.strftime("%b %d"), text, tag))
        self.unread += 1

    def flush(self, final=False):
        if not self.show or not self.unread:
            return
        lines = self.news[-self.unread:]
        self.unread = 0
        i = 0
        while i < len(lines):
            clear()
            print(title_bar(f"STAFF CAROUSEL  ·  {self.year}-{str(self.year + 1)[2:]}",
                            sub=f"through {self.day.strftime('%B %d')}"))
            for d, text, tag in lines[i:i + FEED_PAGE]:
                col = {"you": C.BGREEN, "tree": C.BYELLOW, "big": C.BWHITE, "domino": C.GRAY,
                       "no": C.BRED, "pos": C.CYAN}.get(tag, C.WHITE)
                print(f"   {paint(d, C.BCYAN)}  {paint(truncate(text, 88), col)}")
            i += FEED_PAGE
            if i < len(lines):
                if ask("Enter for more, S to skip ahead:").strip().lower() == "s":
                    return
            elif not final:
                pause()

    # ── the queue ────────────────────────────────────────────────────────
    def open(self, team, kind, key, why=None):
        if team is None:
            return
        v = (team.school, kind, key)
        if v not in [(t.school, k, x) for t, k, x in self.queue]:
            self.queue.append((team, kind, key))
            if why:
                self.cause[v] = why

    def filled(self, team, kind, key):
        if kind == "coord":
            return getattr(team, "oc" if key == "OC" else "dc", None) is not None
        return poscoach.staff_of(team).get(key) is not None

    def next(self):
        self.queue.sort(key=lambda v: (-v[0].prestige, 0 if v[1] == "coord" else 1))
        return self.queue.pop(0)

    def tick(self, est):
        self.steps += 1
        last = datetime.date(self.year + 1, 1, 24)
        if self.day < last and self.rng.random() < DAYS / max(20, est):
            self.day += datetime.timedelta(days=1)

    # ── setup ────────────────────────────────────────────────────────────
    def seed(self):
        lg = self.league
        poscoach.ensure(lg)
        for t in lg.teams:
            for role in ("OC", "DC"):
                if getattr(t, "oc" if role == "OC" else "dc", None) is None:
                    self.open(t, "coord", role)
            for g in poscoach.GROUPS:
                c = poscoach.staff_of(t).get(g)
                if c is None:
                    self.open(t, "pos", g)
                elif poscoach.fields(c).unhappy and c.unhappy[0] >= self.year - 1 and t is not self.me \
                        and self.rng.random() < 0.3:
                    poscoach.staff_of(t)[g] = None
                    c.school = None
                    lg.pos_pool.append(c)
                    self.say(f"{t.school} {poscoach.TITLE[g]} coach {c.name} walks out after {c.unhappy[1]}'s firing.",
                             "pos", t)
                    self.open(t, "pos", g)
        if self.me is not None:
            for g, c in poscoach.staff_of(self.me).items():
                if c is not None and c.unhappy and c.unhappy[0] >= self.year - 1 and self.rng.random() < 0.35:
                    poscoach.staff_of(self.me)[g] = None
                    c.school = None
                    lg.pos_pool.append(c)
                    self.say(f"Your {poscoach.TITLE[g]} coach {c.name} resigns — he was {c.unhappy[1]}'s guy.", "you")
                    self.open(self.me, "pos", g)

    # ── decisions ────────────────────────────────────────────────────────
    def accepts(self, team, c, role, tie):
        """(yes?, offer or reason)"""
        import finance
        pc = c.__dict__.get("_from_pos")
        if pc is not None:
            old = team_by_school(self.league, pc.school)
            if old is team:
                return True, None
            if old is not None and old.prestige - team.prestige > 18 and pc.kind not in ("Climber",) \
                    and self.rng.random() < 0.55:
                return False, f"would rather wait for a coordinator job at a bigger program than {team.school}"
            if pc.kind == "Loyalist" and old is not None:
                coord = getattr(old, "oc" if role == "OC" else "dc", None)
                if coord is not None and coord.name in pc.ties and self.rng.random() < 0.6:
                    return False, f"is staying with {coord.name} at {old.school}"
            return True, None
        offer = finance.coord_offer(self.league, team, c, role, self.rng)
        if not staff._willing(c, team, self.league, tie, offer):
            if c.team is not None:
                return False, "is happy where he is"
            return False, "turned down the money"
        if c.team is not None and staff.role_of(c) in ("OC", "DC") and self.rng.random() < 0.15:
            return False, f"stays at {c.team.school} after a counteroffer"
        return True, offer

    def keep_yours(self, team, who, now_title, new_title, promotion):
        """A program wants one of your coaches. True if he stays."""
        lg = self.league
        if not self.show:
            return self.rng.random() < (0.15 if promotion else 0.45)
        self.flush()
        clear()
        print(title_bar(f"PHONE CALL  ·  {self.day.strftime('%B %d')}"))
        print(paint(f"\n   {team.school}'s head coach is on the line. He wants your {now_title}, {who.name},\n"
                    f"   as his {new_title}.", C.BWHITE, C.BOLD))
        if promotion:
            print(paint("   It's a promotion — the kind of job he's been working toward.", C.BYELLOW))
        kind = getattr(who, "kind", None) or getattr(who, "personality", "")
        print(paint(f"   ({who.name.split()[-1]}: {kind}{' · ' + poscoach.KIND_NOTE.get(kind, '') if kind in poscoach.KIND_NOTE else ''})",
                    C.GRAY))
        odds = 0.2 if promotion else 0.55
        if getattr(who, "kind", "") == "Loyalist":
            odds += 0.15
        if getattr(who, "kind", "") == "Climber" or getattr(who, "personality", "") == "climber":
            odds -= 0.12
        odds = max(0.05, min(0.8, odds))
        print(f"\n   {paint('[B]', C.BGREEN)} give him your blessing   "
              f"{paint('[K]', C.BYELLOW)} try to keep him (a raise; about {round(odds * 100)}% he stays)")
        ch = ask("Your call:").strip().lower()
        if ch == "k":
            if self.rng.random() < odds:
                if hasattr(who, "bonus"):
                    who.bonus = int(getattr(who, "bonus", 0) + poscoach.salary(who, self.me) * 0.25)
                print(paint(f"   {who.name} stays. The raise helped; so did you.", C.BGREEN))
                lg.__dict__.setdefault("career_log", []).append((lg.year, f"Kept {who.name} from {team.school}."))
                pause()
                return True
            print(paint(f"   {who.name} thanks you — but he's taking it.", C.BRED))
            pause()
        lg.__dict__.setdefault("staff_tree", []).append((self.year, who.name, self.me.school, team.school, new_title))
        lg.__dict__.setdefault("career_log", []).append(
            (lg.year, f"{who.name} left your staff to become {team.school}'s {new_title}."))
        return False

    # ── coordinators ─────────────────────────────────────────────────────
    def coord_cands(self, team, role):
        lg = self.league
        ranked = staff.candidates_for(lg, team, role, self.rng)
        for pc, t in poscoach.coord_candidates(lg, team, role):
            ranked.append((poscoach.as_coordinator(lg, pc, role), False))
        return sorted(ranked, key=lambda x: -(staff._score(team, x[0], role, lg)
                                              - (4 if x[0].__dict__.get("_from_pos") else 0)
                                              + self.rng.gauss(0, 2.5)))

    def fill_coord(self, team, role):
        lg = self.league
        cands = self.coord_cands(team, role)
        title = staff.ROLE_NAMES[role]
        names = [c.name for c, _ in cands[:3]]
        if names:
            self.say(f"{team.school} interviews {', '.join(names)} for {title}.",
                     "big" if team.conference in self.power else "coord")
        for c, tie in cands[:14]:
            ok, got = self.accepts(team, c, role, tie)
            if not ok:
                if c.name in names:
                    self.say(f"{c.name} {got} — he turns down {team.school}.", "no")
                continue
            if self.me is not None and team is not self.me and self._is_mine(c):
                pc = c.__dict__.get("_from_pos")
                now = f"{poscoach.TITLE[pc.group]} coach" if pc else staff.ROLE_NAMES[staff.role_of(c)]
                if self.keep_yours(team, pc or c, now, title, promotion=pc is not None):
                    self.say(f"{c.name} stays at {self.me.school} — {team.school} moves on.", "you")
                    continue
            self.hire_coord(team, role, c, got if isinstance(got, dict) else None)
            return
        gen = next((c for c, _ in cands if c.__dict__.get("_generated") and not c.__dict__.get("_from_pos")), None)
        if gen is None:
            gen = staff._generated(lg, team, role, self.rng)[0]
        self.hire_coord(team, role, gen, None)

    def _is_mine(self, c):
        pc = c.__dict__.get("_from_pos")
        if pc is not None:
            return pc.school == self.me.school
        return c.team is self.me

    def hire_coord(self, team, role, c, offer):
        lg = self.league
        title = staff.ROLE_NAMES[role]
        pc = c.__dict__.pop("_from_pos", None)
        old_coord_team = c.team if c.team is not None and staff.role_of(c) in ("OC", "DC") else None
        old_role = staff.role_of(c) if old_coord_team is not None else None
        if pc is not None:
            old = team_by_school(lg, pc.school)
            if old is not None and poscoach.staff_of(old).get(pc.group) is pc:
                for mate in poscoach.colleagues(old, pc):
                    poscoach.tie(c, mate)
                poscoach.staff_of(old)[pc.group] = None
                poscoach.log(lg, old, pc, f"became {team.school} {role}")
            staff._hire(lg, team, role, c, team.conference in self.power, offer)
            if old is team:
                self.say(f"{team.school} promotes {poscoach.TITLE[pc.group]} coach {c.name} to {title}.",
                         "you" if team is self.me else "big")
            else:
                tag = "tree" if old is self.me else ("you" if team is self.me else "big")
                where = old.school if old else "out of work"
                self.say(f"★ {where} {poscoach.TITLE[pc.group]} coach {c.name} gets his first coordinator job: "
                         f"{title} at {team.school}.", tag)
            if old is not None:
                self.open(old, "pos", pc.group, f"{c.name} left for {team.school}")
                self.say(f"   ↳ opens the {poscoach.TITLE[pc.group]} job at {old.school}.", "domino")
        else:
            staff._hire(lg, team, role, c, team.conference in self.power, offer)
            src = f"from {old_coord_team.school}" if old_coord_team else (
                "a former head coach" if staff.role_of(c) == "HC" or c.history else c.origin)
            tag = "you" if team is self.me else ("tree" if old_coord_team is self.me else
                                                 "big" if team.conference in self.power else "coord")
            self.say(f"{team.school} hires {c.name} as {title} ({src}).", tag)
            if old_coord_team is not None:
                self.open(old_coord_team, "coord", old_role, f"{c.name} left for {team.school}")
                self.say(f"   ↳ opens the {staff.ROLE_NAMES[old_role]} job at {old_coord_team.school}.", "domino")
        self.bring_guys(team, role, c)

    def bring_guys(self, team, role, c):
        lg = self.league
        brought = 0
        guys = sorted(poscoach.guys_of(lg, c), key=lambda x: (-(1 if x[2].unhappy else 0), -x[2].overall))
        for t, g, pc in guys:
            if brought >= 2 or poscoach.SIDE[g] != role or t is team:
                continue
            # Newly signed assistants are off the market for the rest of this offseason.
            if getattr(pc, "since", None) is not None and pc.since >= lg.year + 1:
                continue
            cur = poscoach.staff_of(team).get(g)
            if team is self.me:
                if not self.show:
                    continue
                self.flush()
                cur_txt = f", replacing {cur.name}" if cur else ""
                print(paint(f"\n   {c.name} wants to bring his guy {pc.name} ({pc.kind}, DEV {pc.dev} · REC {pc.rec} · "
                            f"EVAL {pc.eye}) as your {poscoach.TITLE[g]} coach{cur_txt}.", C.BYELLOW))
                if ask("Let him? (y/n)").strip().lower() not in ("y", "yes"):
                    self.say(f"You tell {c.name} no on {pc.name}. He doesn't love it.", "you")
                    continue
            elif cur is not None and pc.overall < cur.overall - 3 and not pc.unhappy:
                continue
            if t is not None and t is self.me:
                if self.keep_yours(team, pc, f"{poscoach.TITLE[g]} coach", f"{poscoach.TITLE[g]} coach", False):
                    continue
            elif t is not None and t.prestige > team.prestige + 10 and pc.kind != "Loyalist" and not pc.unhappy \
                    and self.rng.random() < 0.6:
                continue
            if cur is not None:
                poscoach.staff_of(team)[g] = None
                cur.school = None
                lg.pos_pool.append(cur)
                self.say(f"   {cur.name} is out as {team.school}'s {poscoach.TITLE[g]} coach.", "pos", team)
            poscoach.hire(lg, team, g, pc, refill=False)
            poscoach.tie(c, pc)
            brought += 1
            frm = f"from {t.school}" if t is not None else "off the market"
            self.say(f"{c.name} brings his guy {pc.name} {frm} to coach {poscoach.TITLE[g]} at {team.school}.",
                     "you" if self.me is not None and self.me in (team, t) else "pos", team)
            if t is not None:
                self.open(t, "pos", g, f"{pc.name} followed {c.name}")
                self.say(f"   ↳ opens the {poscoach.TITLE[g]} job at {t.school}.", "domino")

    # ── position coaches ─────────────────────────────────────────────────
    def fill_pos(self, team, group):
        lg = self.league
        cands = poscoach.candidates(lg, team, group, self.rng)
        for c in cands:
            src = team_by_school(lg, c.school)
            if src is team:
                continue
            if src is not None:
                if src is self.me:
                    if self.keep_yours(team, c, f"{poscoach.TITLE[c.group]} coach",
                                       f"{poscoach.TITLE[group]} coach", promotion=team.prestige > src.prestige + 8):
                        continue
                elif not poscoach.willing(lg, team, c) or (c.kind == "Loyalist" and self.rng.random() < 0.5):
                    continue
            was = c.group
            poscoach.hire(lg, team, group, c, refill=False)
            frm = f"from {src.school}" if src else c.origin
            self.say(f"{team.school} hires {c.name} as {poscoach.TITLE[group]} coach ({frm}).",
                     "you" if self.me is not None and self.me in (team, src) else "pos", team)
            if src is not None:
                self.open(src, "pos", was, f"{c.name} left for {team.school}")
                self.say(f"   ↳ opens the {poscoach.TITLE[was]} job at {src.school}.", "domino")
            return

    # ── yours ────────────────────────────────────────────────────────────
    def yours(self, kind, key):
        lg, team = self.league, self.me
        self.flush()
        why = self.cause.get((team.school, kind, key))
        if kind == "coord":
            import staff_screens
            while True:
                options = self.coord_cands(team, key)        # the search judges interest itself
                clear()
                print(title_bar(f"YOUR OPENING  ·  {staff.ROLE_NAMES[key].upper()}  ·  {self.day.strftime('%B %d')}"))
                if why:
                    print(paint(f"   {why}.", C.GRAY))
                print(paint("   Position coaches on this list would be taking their first coordinator job — your own "
                            "included.", C.GRAY))
                pause("Press Enter to see the candidates...")
                picked = staff_screens.pick(lg, team, key, options)
                if picked is None:
                    self.fill_coord(team, key)
                    return
                c, offer = picked                            # retention fights happen inside the search
                self.hire_coord(team, key, c, offer)
                return
        else:
            import staff_room

            def accept(c):
                src = team_by_school(lg, c.school)
                if src is not None and src.prestige > team.prestige - 2 and c.kind != "Loyalist":
                    return False, f"{c.name} would rather stay at {src.school}."
                if src is not None and self.rng.random() < 0.12:
                    return False, f"{c.name} takes a raise to stay at {src.school}."
                return True, ""
            print(paint(f"\n   Your opening: {poscoach.TITLE[key]} coach" + (f" — {why}." if why else "."), C.BYELLOW))
            pause()
            got = staff_room._hire_pos(lg, team, key, accept=accept, refill=False)
            if got is not None:
                c, src = got
                self.say(f"You hire {c.name} as {poscoach.TITLE[key]} coach" + (f" from {src}." if src else "."), "you")
                srct = team_by_school(lg, src)
                if srct is not None:
                    self.open(srct, "pos", key, f"{c.name} left for {team.school}")
                    self.say(f"   ↳ opens the {poscoach.TITLE[key]} job at {src}.", "domino")

    # ── run ──────────────────────────────────────────────────────────────
    def _member(self, team):
        import commissioner as cm
        return cm.is_player_team(self.league, team)

    def run(self):
        self.seed()
        start = len(self.queue)
        self.news.insert(0, (self.day.strftime("%b %d"),
                             f"The staff carousel opens: {start} assistant jobs open across the country.", "big"))
        self.unread += 1
        est = start * 2.6
        while self.queue and self.steps < 3000:
            team, kind, key = self.next()
            if self.filled(team, kind, key):
                continue
            self.tick(est)
            if team is self.me and self.show:
                self.yours(kind, key)
            elif getattr(self.league, "mode", None) == "commissioner" and self._member(team):
                import member_offseason as mo  # a member's own list, worked headless
                done = mo.fill_coord(self, team, key) if kind == "coord" else mo.fill_pos(self, team, key)
                if not done:
                    (self.fill_coord if kind == "coord" else self.fill_pos)(team, key)
            elif kind == "coord":
                self.fill_coord(team, key)
            else:
                self.fill_pos(team, key)
        self.day = max(self.day, datetime.date(self.year + 1, 1, 24))
        self.say(f"The carousel stops spinning: {self.steps} hires in all.", "big")
        self.league.__dict__.setdefault("staff_carousel_log", {})[self.year] = list(self.news)
        if self.show:
            self.flush(final=True)
            summary(self.league, self.year, pause_after=True)


def run(league, rng, show=False):
    c = Carousel(league, rng, show)
    c.run()
    return c


def summary(league, year, pause_after=True):
    news = league.__dict__.get("staff_carousel_log", {}).get(year, [])
    me = getattr(league, "user_team", None)
    clear()
    print(title_bar(f"STAFF CAROUSEL  ·  WHAT IT MEANT  ·  {year}-{str(year + 1)[2:]}"))
    mine = [x for x in news if x[2] == "you"]
    tree = [x for x in news if x[2] == "tree"]
    stars = [x for x in news if x[1].startswith("★") and x[2] != "tree"]
    print(section("YOUR STAFF"))
    for d, t, _ in mine[-14:] or [("", "No changes on your staff.", "")]:
        print(f"   {paint(d, C.BCYAN)}  {truncate(t, 90)}")
    if tree:
        print(section("YOUR COACHING TREE"))
        for d, t, _ in tree:
            print(f"   {paint(d, C.BCYAN)}  {paint(truncate(t, 90), C.BYELLOW)}")
    if stars:
        print(section("FIRST COORDINATOR JOBS AROUND THE COUNTRY"))
        for d, t, _ in stars[:8]:
            print(f"   {paint(d, C.BCYAN)}  {truncate(t[2:], 90)}")
    n_dom = sum(1 for x in news if x[2] == "domino")
    print(paint(f"\n   {n_dom} dominoes fell. The full feed is on the offseason calendar.", C.GRAY))
    if pause_after:
        pause()


def replay(league, year):
    news = league.__dict__.get("staff_carousel_log", {}).get(year, [])
    i = 0
    while i < len(news):
        clear()
        print(title_bar(f"STAFF CAROUSEL FEED  ·  {year}-{str(year + 1)[2:]}"))
        for d, text, tag in news[i:i + FEED_PAGE]:
            col = {"you": C.BGREEN, "tree": C.BYELLOW, "big": C.BWHITE, "domino": C.GRAY,
                   "no": C.BRED, "pos": C.CYAN}.get(tag, C.WHITE)
            print(f"   {paint(d, C.BCYAN)}  {paint(truncate(text, 88), col)}")
        i += FEED_PAGE
        if i < len(news) and ask("Enter for more, B to stop:").strip().lower() == "b":
            return
    summary(league, year)
