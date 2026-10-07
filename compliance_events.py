"""
compliance_events.py — The calls you make: the temptations, the letters, the incidents.

Career mode delivers these to your inbox (people.py); Athletic Director mode puts them on
your desk (ad_mode.py). Every option shows what it does before you pick it. Most of the
time the shortcut works, and that's the problem: the bill comes later, if it comes.

  TEMPTATIONS   a booster wants to "take care of" a recruit's family; an assistant wants
                to text a kid in a dead period; a collective wants to structure a deal that
                isn't a real deal; a professor could "find" the extra credit; a rival's
                starter is unhappy and an assistant can make a call. Say no and you're
                clean. Say "I don't want to know" and you get what you wanted, plus a
                violation that's now out there, waiting.
  YOUR OWN FIND your compliance director found something. Report it (credit for
                cooperation), bury it (a cover-up moves a case up a level if it comes
                out) or look into it first (a coin flip on which of those you end up with).
  THE CASE      when the story breaks, when the CAB opens an inquiry, when the Notice of
                Allegations arrives, when the committee rules. Cooperate, hire counsel,
                contest, punish yourself first, appeal.
  INCIDENTS     an arrest, a failed test, a conduct case, a post that goes viral, a bet.
  GRADES        at midterms, who's on the brink, and what you're willing to do about it.
"""
import random

import compliance as cp
from ui import C


def _career(league):
    return getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None \
        and league.user_coach.team is not None and not getattr(league, "autosim", False)


def _ad_mode(league):
    return getattr(league, "mode", None) == "ad" and cp.mine(league) is not None


def _m(x):
    return cp._money(x)


def _name(rng):
    from names import full_name
    return full_name(rng)



def _choice(league, *a, **k):
    """people.choice, except a letter that arrives during the offseason stays open into the new year
    (otherwise it would expire before you ever saw it)."""
    import people
    if league.week >= 18 or league.week == 0:
        k["due"] = (league.year + 1, 2) if league.week >= 18 else (league.year, 2)
    return people.choice(league, *a, **k)

# ═══ Stage changes ══════════════════════════════════════════════════════════

def stage_changed(league, team, c):
    """A case just moved. If it's yours, somebody wants an answer."""
    if cp.mine(league) is not team:
        return
    stage = c["status"]
    key = (stage, c["closed"])
    if key in c["prompted"]:
        return
    if _career(league):
        c["prompted"].add(key)
        _career_stage(league, team, c, stage)
    # AD mode: the desk picks it up (see ad_desk_event)


def _career_stage(league, team, c, stage):
    import people
    import effects as fx
    cid = c["id"]
    lvl = cp.LEVEL_WORD[c["level"]]
    sender, role = people._ad_sender(team)
    text = c["text"]
    b = cp._budget(team)
    if stage == "rumor":
        style = lambda d: fx.by_ad(team, d)
        opts = [
            ("Get out front: we're cooperating and reviewing everything.",
             {"cp": {"op": "coop", "case": cid, "d": 1, "press": "cooperate", "rep": 1.0}, "seat": style({"default": 0, "patient": -1}),
              "notes": [(True, "the CAB will remember it"), (False, "you've promised openness")]},
             "The statement goes out. Reporters read it as a promise. Your AD reads it twice."),
            ("No comment.",
             {"cp": {"op": "coop", "case": cid, "d": 0, "press": "none"}, "notes": [(None, "the story runs anyway")]},
             "'We don't comment on rumors.' It runs anyway."),
            ("Attack the story: it's a hit job.",
             {"cp": {"op": "coop", "case": cid, "d": -1, "press": "attack", "rep": -1.0},
              "seat": style({"default": 1, "booster": -2, "win_now": -1, "patient": 2, "traditionalist": 2}),
              "notes": [(None, "the base loves it"), (False, "if it's true, it costs you at the end")]},
             "You come out swinging. The radio shows eat it up. The lawyers wince."),
        ]
        _choice(league, "Sports information director", "Staff", "A story is about to run",
                      f"Coach, a reporter is going to run a story tonight alleging that {text}. "
                      f"I need to know what we're saying.", opts, color=C.BRED,
                      silence={"cp": {"op": "coop", "case": cid, "d": 0, "press": "none"}},
                      silence_text="The story ran with no comment from you.")
    elif stage == "inquiry":
        sr = c["self_reported"]
        opts = [
            ("Cooperate fully: open the files, make everyone available.",
             {"cp": {"op": "coop", "case": cid, "d": 2 if not sr else 1}, "hours": -3,
              "notes": [(True, "cooperation shrinks penalties"), (False, "costs 3 recruiting hours")]},
             "Every record goes to the enforcement staff. It takes a week of everybody's time."),
            ("Hire outside counsel.",
             {"cp": {"op": "counsel", "case": cid, "cost": int(b * 0.006)},
              "notes": [(False, f"about {_m(b * 0.006)} out of next year's pool"), (True, "penalties shrink a little")]},
             "The firm's lawyers move into the conference room."),
            ("Give them the minimum.",
             {"cp": {"op": "coop", "case": cid, "d": -1},
              "notes": [(False, "the committee reads it as stonewalling")]},
             "You answer what you're asked and nothing else. Investigators notice."),
        ]
        subject = "The CAB acknowledged your self-report" if sr else "CAB letter: notice of inquiry"
        body = (f"Coach — the enforcement staff has {'acknowledged our self-report and opened' if sr else 'opened'} "
                f"an inquiry into {text}. This is a {lvl} matter ({cp.LEVEL_BLURB[c['level']]}). "
                f"They want interviews and records. How do we handle it?")
        _choice(league, sender, role, subject, body, opts, color=C.BRED, due=(league.year, league.week + 2),
                      silence={"cp": {"op": "coop", "case": cid, "d": -1}},
                      silence_text="The letter sat. The enforcement staff took your silence as an answer.")
    elif stage == "allegations":
        opts = [
            ("Accept the findings and negotiate.",
             {"cp": [{"op": "accept", "case": cid}, {"op": "rep", "d": -1.0}],
              "notes": [(True, "softer penalties"), (False, "you're admitting it publicly")]},
             "You sit down with the enforcement staff and work toward a resolution."),
            ("Contest the allegations.",
             {"cp": {"op": "contest", "case": cid},
              "notes": [(None, "about 1 in 3: penalties shrink a lot · otherwise they grow")]},
             "Your lawyers file a response that disputes the facts."),
            ("Announce penalties on ourselves first.",
             {"cp": {"op": "self_impose", "case": cid},
              "notes": [(False, f"costs about {_m(b * 0.008)} out of next year's pool"), (True, "the committee credits it")]},
             "You announce a set of penalties before the committee can. It's a first for the building."),
        ]
        _choice(league, sender, role, "Notice of Allegations",
                      f"Coach — the CAB has sent its Notice of Allegations: {lvl} ({cp.LEVEL_BLURB[c['level']]}) — {text}. "
                      f"We have to answer it. Here's how I see the options.", opts, color=C.BRED,
                      due=(league.year, league.week + 2),
                      silence={"cp": {"op": "accept", "case": cid}},
                      silence_text="Nobody answered. The school's response was a default.")
    elif stage == "ruled":
        r = c["ruling"] or {}
        lines = "; ".join(r.get("lines", []))
        opts = [("Accept it and move on.", {"chem": 2, "notes": [(True, "closure: the room can move on")]},
                 "You take it on the chin. The team hears it from you first.")]
        if c["level"] <= 2 and not c.get("appeal_done"):
            opts.append(("Appeal.", {"cp": {"op": "appeal", "case": cid},
                                     "notes": [(None, "about 1 in 3 wins some relief"),
                                               (False, "the story keeps running · a denial hurts")]},
                         "The appeal is filed. The news cycle isn't done with you."))
        _choice(league, sender, role, "The CAB has ruled",
                      f"Coach — the committee has ruled on {text}: {lines}.", opts, color=C.BRED,
                      due=(league.year, league.week + 1),
                      silence_text="The penalties stand.")


# ═══ Off the field ══════════════════════════════════════════════════════════

def incident_message(league, team, p, kind, rng):
    """A player's trouble, on your desk."""
    if not _career(league):
        return
    import people
    import effects as fx
    inc = cp.INCIDENTS[kind]
    lo, hi = inc["games"]
    n = rng.randint(max(1, lo), max(1, hi)) if hi else 1
    what = cp.incident_line(p, kind)
    starter = p in {q for g in team.starters().values() for q in g}
    repeat = p.__dict__.get("incidents", 0)
    p.__dict__["incidents"] = repeat + 1
    cp._tables_ok(cp.st(team))["incidents"] += 1
    opts = [
        (f"Suspend him {n} game{'s' if n != 1 else ''}.",
         {"who": p, "sit": n, "sit_why": "suspended", "morale": -6, "chem": 2, "cp": {"op": "rep", "d": inc["rep"] * 0.4},
          "notes": [(True, "the room sees you mean it"), (False, f"{p.first_name} misses {n} game{'s' if n != 1 else ''}")]},
         f"{p.first_name} sits. The seniors nod."),
        ("Handle it internally. He plays.",
         {"who": p, "morale": 4, "chem": -2, "cp": {"op": "rep", "d": inc["rep"] * 1.2},
          "seat": fx.by_ad(team, {"default": 1, "win_now": 0, "booster": 0, "traditionalist": 3}),
          "notes": [(False, "if it gets out, it looks like a cover"), (True, "he's on the field Saturday")]},
         "It stays in the building. For now."),
        ("Dismiss him from the team.",
         {"who": p, "cp": [{"op": "dismiss"}, {"op": "rep", "d": inc["rep"] * 0.15}], "chem": 1,
          "notes": [(True, "the message is unmistakable"), (False, "he's gone, and so is his NIL and scholarship")]},
         ""),
    ]
    if kind == "social":
        opts[0] = ("Make him apologize publicly and sit one game.",
                   {"who": p, "sit": 1, "sit_why": "suspended", "morale": -4, "chem": 1,
                    "cp": {"op": "rep", "d": inc["rep"] * 0.3},
                    "notes": [(True, "the story dies fast")]}, "He posts an apology. The story dies by Wednesday.")
    body = (f"Coach — {what}. " + ("He's a starter. " if starter else "") +
            ("It's not the first time. " if repeat else "") + "I need to know what we're doing before this goes anywhere.")
    who = "Director of Football Operations" if kind not in ("social",) else "Sports information director"
    _choice(league, who, "Staff", f"{p.name}: {kind_word(kind)}", body, opts, ref=p, color=C.BRED,
                  silence={"who": p, "morale": -3, "cp": {"op": "rep", "d": inc["rep"] * 1.5}, "chem": -2},
                  silence_text="Nothing was done. People noticed.")


def kind_word(kind):
    return {"arrest": "arrested", "dui": "DUI", "drugs": "failed test", "conduct": "conduct code",
            "social": "viral post", "wager": "sports wagering"}[kind]


# ═══ Grades ═════════════════════════════════════════════════════════════════

def watch_message(league):
    """Week 5: who's on the brink of losing eligibility."""
    team = cp.mine(league)
    if team is None or not _career(league):
        return
    import people
    risky = [p for p in cp.watch_list(team, 2.25)]
    if not risky:
        return
    star = max(risky, key=lambda p: p.overall)
    n = len(risky)
    if star.overall < 60 and n < 3:
        return
    sup = cp.SUPPORT_TIER[cp.st(team)["support"]][2]
    lvl = 3 if random.Random(f"acad:{league.seed}:{league.year}").random() < 0.7 else 2
    opts = [
        ("Tutors and mandatory study hall.",
         {"who": star, "cp": {"op": "tutor", "d": 0.30}, "hours": -3,
          "notes": [(True, f"{star.first_name}'s grades come up"), (False, "costs 3 recruiting hours")]},
         "Study hall is at 6 a.m. He hates it. The grades come up."),
        ("See what the professor can do.",
         {"who": star, "cp": [{"op": "tutor", "d": 0.55},
                              {"op": "tempt", "kind": "academic", "level": lvl, "evidence": 68, "heat": 0.05,
                               "text": f"a professor changed grades to keep {star.position} {star.name} eligible"}],
          "notes": [(True, f"{star.first_name} is fine"), (None, "a violation is now out there, waiting")]},
         f"The professor 'finds' some extra credit. {star.first_name} is eligible. Nobody writes it down."),
        ("He sits until he earns it.",
         {"who": star, "sit": 3, "sit_why": "held out (grades)", "morale": -10, "cp": {"op": "tutor", "d": 0.20},
          "notes": [(False, f"{star.first_name} misses 3 games"), (True, "clean")]},
         "He'll miss three games. The team hears why."),
    ]
    _choice(league, "Academic advisor", "Staff", f"Midterm grades: {star.name}",
                  f"Coach — midterm grades are due. {n} player{'s' if n != 1 else ''} are on the brink. The one who "
                  f"matters most is {star.position} {star.name} ({star.class_label}). Academic support is {sup.lower()}. "
                  f"Without help he's ineligible by the end of the month.", opts, ref=star, color=C.BYELLOW,
                  silence={"who": star, "morale": -3},
                  silence_text="Nobody stepped in. Grades did what grades do.")


# ═══ Temptations & your own finds ═══════════════════════════════════════════

def inbox(league, team, rng):
    """Called every week from people.weekly (Career): now and then, somebody offers a shortcut."""
    if not _career(league):
        return
    s = cp._tables_ok(cp.st(team))
    if not cp.active(league):
        return
    key = (league.year, league.week)
    if s.get("tempt_at") and 0 <= (league.week - s["tempt_at"][1]) < 3 and s["tempt_at"][0] == league.year:
        return
    # your own compliance director finds something
    hid = [c for c in cp.hidden_cases(league, team) if not c["user"] and ("find",) not in c["prompted"]]
    if hid and rng.random() < 0.16:
        _internal_find(league, team, hid[0])
        s["tempt_at"] = key
        return
    style = cp.ad_style(team)
    p = 0.032 * {"booster": 1.6, "win_now": 1.3, "brand": 1.2, "patient": 0.8, "traditionalist": 0.7}.get(style, 1.0)
    p *= 1.3 - s["rep"] / 100 * 0.6
    if rng.random() > p:
        return
    _temptation(league, team, rng)
    s["tempt_at"] = key


def _board_target(team):
    import effects as fx
    tgt = fx.board(team, 6)
    return tgt[0] if tgt else None


def _temptation(league, team, rng):
    import people
    import effects as fx
    kinds = ["booster", "contact", "collective"]
    if 9 <= league.week <= 13 or league.week == 0:
        kinds.append("portal")
    kind = rng.choice(kinds)
    r = _board_target(team)
    if kind in ("booster", "contact") and r is None:
        kind = "collective"
    b = cp._budget(team)
    if kind == "booster":
        boo = _name(rng)
        lvl = 2 if rng.random() < 0.72 else 1
        opts = [
            ("Absolutely not. Thank him and never take his call again.",
             {"cp": {"op": "rep", "d": 1.0}, "seat": fx.by_ad(team, {"default": -1, "traditionalist": -2, "patient": -2, "booster": 0}),
              "notes": [(True, "clean hands"), (True, "AD trust up a little")]},
             "He leaves angry. You sleep fine."),
            ("I don't want to know what you do.",
             {"ref": r, "recruit": 12, "cp": {"op": "tempt", "kind": "benefits", "level": lvl, "cover": True,
                                              "evidence": 78, "heat": 0.06,
                                              "text": f"a booster paid for a recruit's family to travel and stay in town ({r.name})"},
              "notes": [(True, f"{r.name.split()[0]}'s interest up a lot"), (None, "a violation is now out there, waiting")]},
             f"Mr. {boo.split()[-1]} nods. A week later, {r.name.split()[0]}'s mother has plane tickets."),
            ("Report it to compliance and shut it down.",
             {"cp": {"op": "rep", "d": 2.0}, "money": -150_000, "seat": fx.by_ad(team, {"default": -1, "traditionalist": -2}),
              "notes": [(True, "the program's reputation for integrity grows"), (False, "he pulls a $150K donation")]},
             "Compliance sends him a very polite, very official letter. The donation goes elsewhere."),
        ]
        _choice(league, boo, "Booster", f"A friend of the program on {r.name}",
                      f"Coach, it's {boo}. Heard {r.name} is torn between us and somebody else. I'd like to take care "
                      f"of the family: plane tickets, a place to stay, maybe a little something for his mother. "
                      f"Nobody has to know. All you have to do is not ask.", opts, ref=r, color=C.BMAGENTA,
                      silence_text="He took your silence as permission to do nothing. This time.")
    elif kind == "contact":
        lvl = 3 if rng.random() < 0.65 else 2
        opts = [
            ("Wait for the calendar.", {"cp": {"op": "rep", "d": 0.5}, "notes": [(True, "clean")]},
             "He grumbles. He waits."),
            ("Do it, quietly.",
             {"ref": r, "recruit": 8, "cp": {"op": "tempt", "kind": "recruiting", "level": lvl, "cover": True,
                                             "evidence": 72, "heat": 0.03,
                                             "text": f"an assistant contacted {r.name} outside the permitted window"},
              "notes": [(True, f"{r.name.split()[0]}'s interest up"), (None, "a violation is now out there, waiting")]},
             "The text goes out at 11:48 p.m. He answers in four minutes."),
            ("Log it and reprimand him.", {"cp": {"op": "rep", "d": 0.3}, "chem": -1,
                                           "notes": [(True, "compliance is watching")]},
             "He's not happy. Compliance is."),
        ]
        _choice(league, "Assistant coach", "Staff", f"About {r.name}",
                      f"Coach, {r.name}'s people are wavering and the contact window isn't open. I can reach him tonight. "
                      f"Nobody will ever see it. It's the kind of thing everyone does.", opts, ref=r, color=C.BYELLOW,
                      silence_text="He didn't wait for an answer. Or did he?")
    elif kind == "collective":
        lvl = 2 if rng.random() < 0.65 else 1
        star = max((p for p in team.roster if p.year < 3), key=lambda p: p.overall, default=None)
        target = r.name if r is not None else (star.name if star else "a starter")
        opts = [
            ("Turn it down.", {"cp": {"op": "rep", "d": 1.0}, "notes": [(True, "clean")]},
             "He says he'll take his money to somebody who'll use it."),
            ("Structure it as 'appearances'.",
             {"ref": r, "recruit": 10 if r else 0, "money": 400_000,
              "cp": {"op": "tempt", "kind": "nil", "level": lvl, "evidence": 80, "heat": 0.06,
                     "text": f"a collective's 'appearance' deal for {target} was never tied to real appearances"},
              "notes": [(True, "+$400K to next year's pool"), (None, "a violation is now out there, waiting")]},
             "The paperwork calls it 'appearances.' There will be none."),
            ("Make it a real deal with real work.",
             {"ref": r, "recruit": 3 if r else 0, "hours": -3, "notes": [(True, "clean"), (False, "costs 3 recruiting hours")]},
             "The collective's staff builds an actual schedule. It's about a third as much money."),
        ]
        head = _name(rng)
        _choice(league, head, "NIL collective", "A deal for " + target,
                      f"Coach, {head} from the collective. We can get {target} a very large number this year. It won't "
                      f"say 'signing bonus' anywhere. It'll say 'appearances.' Nobody's ever going to check.",
                      opts, ref=r, color=C.BMAGENTA, silence_text="The collective went shopping.")
    else:
        pool = [q for t in league.teams if t.conference == team.conference and t is not team for q in t.roster
                if q.overall >= 70 and q.position != "K"]
        if not pool:
            return
        q = rng.choice(pool)
        lvl = 3 if rng.random() < 0.6 else 2
        opts = [
            ("No. We wait for the portal window.", {"cp": {"op": "rep", "d": 0.5}, "notes": [(True, "clean")]},
             "He shrugs. He was just asking."),
            ("Make the call.",
             {"hours": 6, "top": (2, 5), "cp": {"op": "tempt", "kind": "tampering", "level": lvl, "cover": True,
                                                "evidence": 65, "heat": 0.03,
                                                "text": f"an assistant contacted {q.team.school}'s {q.position} {q.name} "
                                                        f"before he entered the portal"},
              "notes": [(True, "extra recruiting hours and interest"), (None, "a violation is now out there, waiting")]},
             "It's a five-minute call. Word travels."),
        ]
        _choice(league, "Assistant coach", "Staff", f"{q.team.school}'s {q.position}",
                      f"Coach, I hear {q.name} at {q.team.school} is miserable there. I can make a call before he's "
                      f"in the portal. Everybody does it.", opts, color=C.BYELLOW,
                      silence_text="The moment passed.")


def _internal_find(league, team, c):
    import people
    c["prompted"].add(("find",))
    cid = c["id"]
    b = cp._budget(team)
    opts = [
        ("Self-report it. Right now.",
         {"cp": {"op": "report", "case": cid}, "seat": 1,
          "notes": [(True, "cooperation and self-reporting shrink the penalty"), (False, "it becomes public")]},
         "You call the CAB yourself. It's the hardest call and the safest."),
        ("Bury it.",
         {"cp": {"op": "bury", "case": cid},
          "notes": [(None, "if it comes out, a cover-up moves a case up a level")]},
         "Nobody outside the room ever hears about it. For now."),
        ("Investigate it ourselves first.",
         {"gamble": [(0.5, {"cp": {"op": "report", "case": cid}, "notes": [(True, "credit for finding it first")]},
                      "Your review confirms it. You report it with a full write-up, and the CAB notes the timing."),
                     ({"cp": {"op": "bury", "case": cid}},
                      "The review drags. By the time you know enough, it looks like you sat on it.")],
          "notes": [(None, "a coin flip: report with credit, or it looks like a cover-up")]},
         "You ask compliance for a quiet review."),
    ]
    _choice(league, "Director of compliance", "Staff", "We found something",
                  f"Coach — routine review turned up something that isn't public: {c['text']}. It's a "
                  f"{cp.LEVEL_WORD[c['level']]} matter. I need your decision before it goes any further.", opts,
                  color=C.BRED, silence={"cp": {"op": "bury", "case": cid}},
                  silence_text="Nobody decided. The default was to sit on it.")


# ═══ Athletic Director mode ═════════════════════════════════════════════════

def ad_desk_event(league, team):
    """A compliance decision that has to be made before anything else (AD mode). Returns an event tuple or None."""
    if not _ad_mode(league) or not cp.active(league):
        return None
    b = cp._budget(team)
    for c in cp.cases(league, team.school):
        cid = c["id"]
        if c["closed"] and c["status"] != "ruled":
            continue
        stage = c["status"]
        if stage == "hidden":
            if not c["user"] and ("find",) not in c["prompted"] and random.Random(f"adfind:{cid}:{league.year}:{league.week}").random() < 0.2:
                c["prompted"].add(("find",))
                return (f"comp_find_{cid}", True,
                        f"The compliance director has found something that isn't public: {c['text']}. It's a "
                        f"{cp.LEVEL_WORD[c['level']]} matter. What do you want to do?",
                        [("Self-report it", {"cp": {"op": "report", "case": cid}, "board": 1, "boosters": -2}),
                         ("Have compliance look into it first", {"cp": {"op": "probe", "case": cid}}),
                         ("Sit on it", {"cp": {"op": "bury", "case": cid}, "boosters": 1})])
            continue
        key = (stage, c["closed"])
        if key in c["prompted"] or stage in ("closed", "appeal"):
            continue
        c["prompted"].add(key)
        if stage == "rumor":
            return (f"comp_rumor_{cid}", True,
                    f"A story is about to run alleging that {c['text']}. The press office wants to know what the "
                    f"athletic department is saying.",
                    [("Cooperate publicly and promise a review", {"cp": {"op": "coop", "case": cid, "d": 1, "press": "cooperate", "rep": 1.0}, "board": 1}),
                     ("Attack the story", {"cp": {"op": "coop", "case": cid, "d": -1, "press": "attack", "rep": -1.0},
                                           "fans": 3, "boosters": 2, "board": -2}),
                     ("No comment", {"cp": {"op": "coop", "case": cid, "d": 0, "press": "none"}})])
        if stage == "inquiry":
            return (f"comp_inquiry_{cid}", True,
                    f"The CAB enforcement staff has opened an inquiry into {c['text']} ({cp.LEVEL_WORD[c['level']]}). "
                    f"They want records and interviews.",
                    [(f"Hire outside counsel ({_m(b * 0.006)})", {"cp": {"op": "counsel", "case": cid, "cost": int(b * 0.006)}}),
                     ("Give them the minimum", {"cp": {"op": "coop", "case": cid, "d": -1}, "board": -1}),
                     ("Cooperate fully", {"cp": {"op": "coop", "case": cid, "d": 2}, "board": 1})])
        if stage == "allegations":
            return (f"comp_allegations_{cid}", True,
                    f"The CAB's Notice of Allegations has arrived: {cp.LEVEL_WORD[c['level']]}, {c['text']}. "
                    f"The school has to respond.",
                    [("Contest the allegations", {"cp": {"op": "contest", "case": cid}, "boosters": 2}),
                     (f"Announce penalties on ourselves first ({_m(b * 0.008)})", {"cp": {"op": "self_impose", "case": cid}, "board": 1}),
                     ("Accept the findings and negotiate", {"cp": [{"op": "accept", "case": cid}, {"op": "rep", "d": -1.0}], "fans": -2})])
        if stage == "ruled":
            r = c["ruling"] or {}
            opts = [("Accept it and move on", {"fans": -1})]
            if c["level"] <= 2 and not c.get("appeal_done"):
                opts.insert(0, ("Appeal", {"cp": {"op": "appeal", "case": cid}, "boosters": 1}))
            return (f"comp_ruled_{cid}", True,
                    f"The Committee on Infractions has ruled on {c['text']}: " + "; ".join(r.get("lines", [])) + ".", opts)
    return None
