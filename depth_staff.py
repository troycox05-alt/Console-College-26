"""Staff opinions, position coaches, camp work and film grades for v28 depth management."""
import random
from collections import Counter

GROUPS = {"QB":"QB", "RB":"RB", "WR":"WR", "TE":"TE", "OL":"OL", "DL":"DL", "LB":"LB", "CB":"DB", "S":"DB", "K":"ST", "P":"ST"}
GROUP_NAMES = ("QB","RB","WR","TE","OL","DL","LB","DB","ST")
LEANS = ("veterans","youth","practice","gameday","measurables","technician","upside","toughness","character","incumbent")
_ACTIVE_LEAGUE = [None]


def _hc_stamp(team):
    c = team.coach
    return getattr(c, "name", None)


def ensure_position_staff(league, team):
    """Use the real staff-room position coaches when available; generate only special teams fallback."""
    _ACTIVE_LEAGUE[0] = league
    from names import full_name
    rng = random.Random(f"pos-staff:{league.seed}:{team.school}:{_hc_stamp(team)}")
    out = {}
    try:
        import poscoach
        poscoach.ensure(league)
        room = poscoach.staff_of(team)
        kind_lean = {"Developer": "upside", "Recruiter": "measurables", "Technician": "technician",
                     "Players' coach": "character", "Climber": "youth", "Loyalist": "incumbent"}
        for group in GROUP_NAMES:
            pc = room.get(group) if group != "ST" else None
            if pc is not None:
                pc = poscoach.fields(pc)
                eye = max(.6, min(1.4, .6 + (pc.eye - 25) / 72 * .8))
                lean = kind_lean.get(pc.kind, "incumbent")
                if getattr(pc, "spec", None) == "Film junkie":
                    eye = min(1.4, eye + .08)
                out[group] = {"name": pc.name, "eye": round(eye, 2), "lean": lean, "obj": pc}
        if len(out) >= 8:
            pass
    except Exception:
        pass
    used = {x["name"].split()[-1] for x in out.values()}
    for group in GROUP_NAMES:
        if group in out:
            continue
        try:
            nm = full_name(rng, avoid=used)
        except TypeError:
            nm = full_name(rng)
        used.add(nm.split()[-1])
        out[group] = {"name": nm, "eye": round(max(.6, min(1.4, rng.gauss(1.0, .18))), 2),
                      "lean": rng.choice(LEANS), "obj": None}
    team.pos_staff = out
    team._pos_staff_hc = _hc_stamp(team)
    return out


def coordinator(team, pos):
    import staff
    if pos in ("K", "P"):
        return team.coach
    return staff.side_coach(team, pos) or team.coach


def evaluator(team, pos, which="coord"):
    if which == "pos":
        pc = ensure_position_staff(_ACTIVE_LEAGUE[0], team).get(GROUPS[pos], {}) if _ACTIVE_LEAGUE[0] is not None else getattr(team, "pos_staff", {}).get(GROUPS[pos], {})
        return {"name": pc.get("name", "Position coach"), "eye": pc.get("eye", 1.0), "lean": pc.get("lean", "incumbent"), "coach": None}
    c = coordinator(team, pos)
    import traits, coach_profile
    lean = traits.STYLE_LEANS.get(traits.style(c), "incumbent") if c else "incumbent"
    eye = 1.0
    if c:
        eye = max(.6, min(1.4, coach_profile.value(c, "evaluation") / max(1, c.overall) * traits.mod(c, "eye", 1.0)))
    return {"name": getattr(c, "name", "Head coach"), "eye": eye, "lean": lean, "coach": c}


def camp(league, team):
    book = team.__dict__.setdefault("camp_sessions", {})
    key = league.year
    if key in book:
        return book[key]
    import practice
    out = {}
    starts = practice.starter_counts(team)
    for pos in GROUPS:
        room = team.players_at(pos)
        n = starts.get(pos, 1)
        for i, p in enumerate(room):
            tier = 0 if i < n else 1 if i < 2*n else 2
            lines = []
            for session in range(3):
                rng = random.Random(f"camp:{league.seed}:{team.school}:{league.year}:{session}:{p.name}")
                lines.append(practice.stat_line(p, tier, rng))
            out[id(p)] = lines
    book.clear(); book[key] = out
    return out


def camp_form(league, team, p):
    ls = camp(league, team).get(id(p), [])
    return sum(x[1] for x in ls) / max(1, len(ls))


def _lean_bonus(lean, p, pos, league, team):
    import morale, personalities, traits
    b = 0.0
    if lean == "veterans": b += p.year * .65
    elif lean == "youth": b += (3-p.year) * .45 + max(0, p.potential-60)/22
    elif lean == "practice": b += camp_form(league, team, p) * 1.4
    elif lean == "gameday": b += recent_delta(p) * .7
    elif lean == "measurables": b += (p.fundamentals.get("speed",60)+p.fundamentals.get("strength",60)-120)/18
    elif lean == "technician": b += (p.fundamentals.get("iq",60)-60)/9
    elif lean == "upside": b += (p.potential-55)/12
    elif lean == "toughness": b += (p.fundamentals.get("injury",60)+p.fundamentals.get("strength",60)-120)/20
    elif lean == "character": b += personalities._lead_score(p)*.7 - personalities._trouble_score(p)*.5 + (morale.get(p)-50)/25
    elif lean == "incumbent":
        if id(p) in set(getattr(team, "_last_starters", []) or []): b += 2.0
    return b


def opinion(league, team, p, pos, who="coord"):
    ev = evaluator(team, pos, who)
    rng = random.Random(f"opinion:{league.seed}:{league.year}:{team.school}:{pos}:{who}:{ev['name']}:{p.name}")
    blur = 2.2 / max(.55, ev["eye"])
    spring = 0.0
    try:
        import spring_cycle
        spring = spring_cycle.spring_form(league, p)
    except Exception:
        pass
    v = p.overall_at(pos) + rng.gauss(0, blur) + camp_form(league, team, p) * 1.3 + spring * 0.75 + _lean_bonus(ev["lean"], p, pos, league, team)
    if id(p) in set(getattr(team, "_last_starters", []) or []): v += 1.0
    return v


def order(league, team, pos, who="blend"):
    room = [p for p in team.roster if p.position == pos]
    if who == "coord": score=lambda p: opinion(league,team,p,pos,"coord")
    elif who == "pos": score=lambda p: opinion(league,team,p,pos,"pos")
    else: score=lambda p: .55*opinion(league,team,p,pos,"coord") + .45*opinion(league,team,p,pos,"pos")
    return sorted(room, key=score, reverse=True)


def take(league, team, p, pos, who):
    ev = evaluator(team, pos, who)
    ranked = order(league, team, pos, who)
    rank = ranked.index(p) + 1 if p in ranked else 99
    form = camp_form(league, team, p)
    film = recent_delta(p)
    rng = random.Random(f"staff-note:{league.seed}:{league.year}:{team.school}:{pos}:{who}:{ev['name']}:{p.name}")

    # Build a context-specific pool, then pick deterministically so comments stay stable on redraws
    # but players/coaches do not all repeat the same sentence.
    pools = []
    if form >= .75:
        pools += [
            "He has been one of our best workers in camp.",
            "The practice tape is forcing us to take him seriously.",
            "He keeps winning his reps. That matters.",
            "Right now, his camp work is making the case for him.",
            "He has stacked good practices instead of living off his rating.",
        ]
    elif form >= .30:
        pools += [
            "He is trending the right way in practice.",
            "I like the direction of his camp work.",
            "The last few reps have helped his case.",
            "He has given us more good tape than bad lately.",
        ]
    elif form <= -.75:
        pools += [
            "The camp tape is making me nervous.",
            "He has not looked comfortable in these reps.",
            "I need cleaner practice tape before I move him up.",
            "His camp work is putting pressure on his spot.",
            "Right now the reps are not matching the talent.",
        ]
    elif form <= -.30:
        pools += [
            "I want to see a steadier week before we reward him.",
            "There are too many uneven reps on the tape.",
            "He has left the door open for somebody behind him.",
            "The practice work has been a little too inconsistent.",
        ]

    if film >= 3.5:
        pools += [
            "The game film is stronger than the depth chart says.",
            "He has been better on Saturdays than we expected.",
            "His recent game tape deserves more weight in this decision.",
            "He is outperforming the grade we had on him.",
        ]
    elif film <= -3.5:
        pools += [
            "The game film has not backed up the current spot.",
            "He is giving us less on Saturdays than the grade suggests.",
            "The recent film gives me pause.",
            "I do not want to ignore what the last few games are telling us.",
        ]

    lean = ev["lean"]
    if lean in ("youth", "upside") and p.year <= 1:
        pools += [
            "There is more ceiling here than the room thinks.",
            "I would rather invest a few reps now and see how fast he grows.",
            "The upside is worth being patient with the mistakes.",
            "He is young, but the tools are hard to ignore.",
        ]
    elif lean == "veterans" and p.year >= 2:
        pools += [
            "I trust the veteran snaps.",
            "Experience is worth something when the room is this close.",
            "He has banked enough live reps to earn some benefit of the doubt.",
            "When it is tight, I lean toward the player who has done it before.",
        ]
    elif lean == "practice":
        pools += [
            "I am weighting the daily work heavily here.",
            "For me, the practice field has to decide a close battle.",
            "I care more about who is winning reps right now than the preseason label.",
        ]
    elif lean == "gameday":
        pools += [
            "Saturday tape carries more weight for me than drill work.",
            "I want the order to reflect who has actually produced in games.",
            "In a close call, I trust the live snaps first.",
        ]
    elif lean == "measurables":
        pools += [
            "The physical tools give us something to work with.",
            "His measurables keep him in this conversation.",
            "You can see the athletic profile even when the rep is not perfect.",
        ]
    elif lean == "technician":
        pools += [
            "His details are what separate him for me.",
            "I am watching the footwork and assignment discipline more than the flash.",
            "Technique is keeping him high on my board.",
        ]
    elif lean == "toughness":
        pools += [
            "I trust how he holds up when the reps get physical.",
            "He gives us a dependable physical floor.",
            "The toughness shows up when the drill stops being clean.",
        ]
    elif lean == "character":
        pools += [
            "I trust what he gives the room.",
            "He helps the group even when the ball is not coming his way.",
            "The way he works with the room matters in a close decision.",
            "He is one of the players I trust to handle the role the right way.",
        ]
    elif lean == "incumbent" and id(p) in set(getattr(team, "_last_starters", []) or []):
        pools += [
            "He has not done enough to lose the job yet.",
            "The incumbent still gets a little credit in a close call.",
            "Somebody has to clearly take the job from him.",
        ]

    # Rank-aware fallback comments keep the neutral cases from collapsing to one repeated line.
    if rank == 1:
        pools += [
            "He is still my first name on the board.",
            "If we played today, he would be my first choice.",
            "I have him at the top, but it is not untouchable.",
        ]
    elif rank == 2:
        pools += [
            "He is close enough that one strong week could change the order.",
            "He is right on the starter's heels for me.",
            "There is not much daylight between him and the top spot.",
        ]
    else:
        pools += [
            "The tape and the traits are pretty close; I just have others ahead right now.",
            "He is in the mix, but I need a clearer reason to move him up.",
            "Nothing is buried here, but he has work to do to climb my board.",
            "I see a role for him; I just do not have him at the front of the line yet.",
        ]

    # Coordinators speak more big-picture; position coaches sound more rep/detail oriented.
    if who == "coord":
        pools += [
            "I am looking at what gives us the best room on game day.",
            "I care about how the whole rotation fits together, not just one good drill.",
        ]
    else:
        pools += [
            "I see every rep, and the little things are driving my grade.",
            "My board is mostly about what he is doing snap to snap in this room.",
        ]

    return rank, rng.choice(pools)


def apply_order(team, pos, ranked):
    team.__dict__.setdefault("depth_order", {})[pos] = list(ranked)


def react_to_change(league, team, pos, before):
    import practice, morale, traits
    n=practice.starter_counts(team).get(pos,1)
    after=team.players_at(pos)[:n]
    old=set(before); new=set(after)
    promoted=[p for p in after if p not in old]
    demoted=[p for p in before if p not in new]
    for p in promoted: morale.nudge(p, 5*traits.mod(p,"role",1.0), "promoted on the depth chart", league)
    for p in demoted: morale.nudge(p, -7*traits.mod(p,"role",1.0), "demoted on the depth chart", league)
    if demoted:
        p=max(demoted,key=lambda x: traits.mod(x,"role",1.0))
        if traits.mod(p,"role",1.0)>=1.3 and morale.get(p)<45:
            import people
            people.choice(league, f"{p.position} {p.name}", "Player", "About the depth chart",
                          f"Coach, I saw the new order. I need to know if I still have a real shot here.",
                          [("Tell him the job is open every week.", {"who":p,"morale":5}, "He leaves ready to compete."),
                           ("Tell him the tape made the decision.", {"who":p,"morale":-4}, "He doesn't like it, but he heard you."),
                           ("Promise him a role.", {"who":p,"promise":"role"}, "He'll hold you to it.")], ref=p)
    return promoted, demoted


def record_film(league, games):
    """Store one 40-100 film grade for each player who appears in a human-team game."""
    import hotseat
    humans=set(hotseat.humans(league)) if getattr(league,"mode",None)=="career" else set()
    for g in games:
        if not g.played or getattr(g,"box",None) is None: continue
        box=g.box
        for team in (g.home,g.away):
            if team not in humans: continue
            stats=getattr(box,"stats",{}) or {}; ts=getattr(box,"team_stats",{}).get(team,{})
            for p in team.roster:
                c=stats.get(p, Counter())
                if not c and p not in [q for grp in team.starters().values() for q in grp]: continue
                imp=0.0
                if p.position=="QB": imp=(c.get("pass_yds",0)/35 + c.get("pass_td",0)*3 - c.get("pass_int",0)*4 + c.get("rush_yds",0)/25)
                elif p.position in ("RB","WR","TE"): imp=(c.get("rush_yds",0)+c.get("rec_yds",0))/28 + (c.get("rush_td",0)+c.get("rec_td",0))*2.5 - c.get("fumbles",0)*3
                elif p.position=="OL": imp=(ts.get("rush_yds",0)/max(1,ts.get("rush_att",1))-4.0)*2 - ts.get("sacks_allowed",0)*.35
                elif p.position in ("DL","LB","CB","S"): imp=c.get("tkl",0)*.25+c.get("sack",0)*1.4+c.get("int",0)*2.3+c.get("tfl",0)*.6
                else: imp=c.get("fg_made",0)*.8-c.get("fg_att",0)*.2+c.get("punt_yds",0)/180
                rng=random.Random(f"film:{league.seed}:{league.year}:{league.week}:{team.school}:{p.name}")
                expected=64+(p.overall-60)*.28
                grade=max(40,min(100, expected + imp + rng.gauss(0,3.2)))
                p.__dict__.setdefault("film_grades",{})[(league.year,league.week)]=round(grade,1)


def recent(p,n=3):
    vals=sorted(getattr(p,"film_grades",{}).items(), key=lambda x:x[0])[-n:]
    return [v for _,v in vals]


def recent_delta(p):
    vals=recent(p)
    if not vals:return 0.0
    exp=64+(p.overall-60)*.28
    return sum(v-exp for v in vals)/len(vals)


def maybe_suggest(league, team):
    """At most one evidence-backed staff depth suggestion per week."""
    mark=(league.year,league.week)
    if getattr(team,"_depth_suggested",None)==mark:return
    import practice, people
    for pos in GROUPS:
        n=practice.starter_counts(team).get(pos,1); cur=team.players_at(pos); blend=order(league,team,pos,"blend")
        if len(cur)<=n or not blend: continue
        promote=blend[0]; demote=cur[0]
        if promote is demote or recent_delta(promote) < recent_delta(demote)+1.5: continue
        c=coordinator(team,pos); pc=ensure_position_staff(league,team)[GROUPS[pos]]
        people.choice(league, getattr(c,"name",pc["name"]), "Staff", f"A change at {pos}?",
                      f"The last few grades back up what we're seeing in practice: {promote.name} has earned a look ahead of {demote.name}.",
                      [(f"Make the change: {promote.last_name} up.", {"depth_swap":(pos,promote,demote)}, "The staff updates the room."),
                       ("Keep the order for now.", {}, "The job stays where it is.")], color=None)
        team._depth_suggested=mark; return
