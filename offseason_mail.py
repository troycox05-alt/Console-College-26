"""Winter/spring inbox cadence.

The offseason hub advances quickly, but the program should never feel silent. This
module posts a small number of contextual messages once per offseason week.
"""
import random


def ensure_week(league, week):
    if getattr(league, "mode", None) != "career" or getattr(league, "user_team", None) is None:
        return
    st = league.__dict__.setdefault("offseason_state", {})
    sent = st.setdefault("mail_weeks", [])
    key = f"{st.get('season', league.year)}:{week}"
    if key in sent:
        return
    sent.append(key)
    team = league.user_team
    # league.year rolls over mid-offseason (Week 8). Deadlines are anchored to the season that just
    # ended so every winter/spring decision closes when the next season kicks off, not a year later.
    season = int(st.get("season") or league.year)
    due = (season + 1, 0)
    r = random.Random(f"offmail:{league.seed}:{league.year}:{team.school}:{week}")
    import people

    def note(sender, role, subject, body, ref=None, color=None):
        people._post(league, sender, role, subject, body, ref=ref, color=color,
                     due=due)

    def choice(sender, role, subject, body, options, ref=None, color=None):
        return people.choice(league, sender, role, subject, body, options, ref=ref, color=color,
                             due=due)

    ad = getattr(team, "ad", {}) or {}
    adname = "AD " + str(ad.get("name", "Athletic Director"))
    hc = getattr(team, "coach", None)
    oc, dc = getattr(team, "oc", None), getattr(team, "dc", None)
    players = [p for p in team.roster if getattr(p, "inj_games", 0) < 99]
    older = [p for p in players if getattr(p, "year", 0) >= 2]
    youngster = [p for p in players if getattr(p, "year", 0) <= 1]

    if week == 1:
        note(adname, "Athletic Director", "The winter starts now",
             "The season is over, but the calendar isn't. Staff movement, portal retention and the class all overlap now. "
             "I want you treating every advance like a deadline, not a menu click.")
        if oc or dc:
            c = r.choice([x for x in (oc, dc) if x])
            choice(c.name, "Coordinator", "Before the market gets loud",
                   "Other staffs are already making calls. I like where this is headed, but I want to know how you see my role next year.",
                   [("You're part of the plan.", {"coord": c, "stay": -1}, "He hears clearly that you want him here."),
                    ("I can't promise anything yet.", {"coord": c, "stay": 0}, "You keep flexibility, but give him no reassurance.")], ref=c)
    elif week == 2:
        note(adname, "Athletic Director", "Staff search expectations",
             "Don't assume a résumé means interest. Strong assistants have options. Interviews, fit and compensation all matter, and a coach we hire this winter is ours for this offseason — no revolving-door poaching.")
    elif week == 3:
        pool = [x for x in (oc, dc) if x] or ([hc] if hc else [])
        c = r.choice(pool) if pool else None
        if c:
            choice(c.name, "Staff", "What the room needs",
                   "I'm finishing winter evaluations. Before spring, I need to know whether you want me coaching for stability or opening every job to competition.",
                   [("Open the jobs. Best player wins.", {"coord": c, "stay": 1, "chem": -1}, "He gets permission to make spring uncomfortable."),
                    ("Protect the core and develop it.", {"coord": c, "stay": -1, "chem": 1}, "He hears that continuity matters too.")], ref=c)
        note("Football Operations", "Staff", "Carousel settling", "The assistant market is thinning. Some names who listened two weeks ago are no longer available; some coaches who missed on jobs are suddenly realistic targets.")
    elif week in (4,5,6):
        note("Personnel Department", "Staff", f"Portal Window I · Week {week-3}",
             "The board is moving at different speeds. Some players are ready to commit now; others are collecting visits and may wait until the deadline. A verbal commitment is not the same thing as being safely enrolled.")
        if players:
            p = r.choice(older or players)
            choice(p.name, f"{p.position} · {p.class_label}", "Where do I stand?",
                   "Coach, before this window gets away from me, I need an honest answer about whether I'm really in the plan.",
                   [("You'll have a real chance to win it.", {"who": p, "morale": 5, "promise": "role"}, "He leaves encouraged, and he'll remember the opportunity you promised."),
                    ("I won't promise a role I can't guarantee.", {"who": p, "morale": -2}, "He respects the honesty, even if it isn't what he wanted to hear.")], ref=p)
    elif week == 7:
        note("Recruiting Office", "Recruiting", "Signing Day board",
             "We still have unsigned prospects and schools are testing shaky commitments. The class ranking can move a lot in one week. Check the board before you advance.")
        from models import POSITIONS
        thin = min(POSITIONS, key=lambda pos: len([p for p in team.roster if p.position == pos]))
        choice("Recruiting Office", "Recruiting", "One last priority",
               f"If we have to spend the last push somewhere, {thin} is the thinnest room on the roster. Do you want us leaning there?",
               [(f"Yes — prioritize {thin}.", {"priority": thin}, f"The staff marks {thin} as the final roster priority."),
                ("Stay on the best player available.", {}, "You keep the board open instead of forcing a need.")])
    elif week == 8:
        note(adname, "Athletic Director", "Signing Day",
             "Today is a deadline, not a ceremony. Make sure scholarship space, NIL promises and the actual roster all agree before the class becomes official.")
    elif week == 9:
        note("Football Operations", "Staff", "Roster audit",
             "Signing Day is behind us. Now the honest question is whether the roster we built matches the roster we thought we were building. Review thin rooms before spring begins.")
    elif week == 10:
        if youngster:
            p = r.choice(youngster)
            choice(p.name, f"{p.position} · {p.class_label}", "Ready for spring",
                   "I've been in the building every day. I know the depth chart isn't decided in March, but I want reps with the group that gives me a chance to prove I belong.",
                   [("You'll get a fair spring look.", {"who": p, "morale": 4}, "He enters spring believing the reps are there to earn."),
                    ("Nothing is promised. Keep working.", {"who": p, "morale": -2}, "He hears the challenge more than the reassurance.")], ref=p)
        note("Strength Staff", "Staff", "Winter development report",
             "Winter gains are in. Spring will tell us whether those gains are real football improvement or just better numbers in the weight room.")
    elif week == 11:
        c = oc or dc or hc
        if c:
            choice(c.name, "Staff", "Spring Ball I",
                   "The first three practices matter most for identifying who deserves more reps. Do you want a calmer install or a more competitive camp tone?",
                   [("Turn up the competition.", {"chem": -1}, "The staff is told to make every rep count."),
                    ("Teach first. Let the evaluations come.", {"chem": 1}, "The staff keeps the room steadier while installing.")], ref=c)
    elif week == 12:
        if players:
            p = r.choice(players)
            choice(p.name, f"{p.position} · {p.class_label}", "A-Day reps",
                   "Coach, I want a real look in the spring game. If the depth chart is going to move, I need enough snaps for the film to mean something.",
                   [("Earn them this week and you'll get the look.", {"who": p, "morale": 4}, "He attacks the week believing the door is open."),
                    ("The rotation is what it is right now.", {"who": p, "morale": -5}, "He hears that his path is narrowing.")], ref=p)
    elif week == 13:
        note("Football Operations", "Staff", "A-Day film is ready",
             "Don't overreact to one scrimmage, but don't ignore it either. The spring-game grades are now part of the staff's depth opinion, and buried players will notice before Portal Window II opens.")
    elif week in (14,15):
        note("Personnel Department", "Staff", f"Portal Window II · {'opens' if week == 14 else 'deadline'}",
             "This window is smaller and more emotional. Most entries are reacting to spring roles. Some players will move fast because they already know exactly what they want.")
        if week == 14 and players:
            p = min(players, key=lambda x: getattr(x, "overall", 50) + r.random()*8)
            choice(p.name, f"{p.position} · {p.class_label}", "I saw the spring board",
                   "I know where the staff has me after spring. I'm going to think about what that means for my future before this window closes.",
                   [("Stay and compete in fall camp.", {"who": p, "morale": 6, "promise": "role"}, "You ask him to bet on one more competition."),
                    ("I understand if you need to look.", {"who": p, "morale": -3}, "You don't make a promise just to stop a transfer.")], ref=p)
    elif week == 16:
        note("Strength Staff", "Staff", "Summer attendance",
             "The freshmen are in, the roster is mostly settled, and conditioning is becoming the separator. The next meaningful evaluation is fall camp.")
    elif week == 17:
        note(adname, "Athletic Director", "Media Days",
             "The predictions are public now. Polls and projected wins don't decide anything, but they define the expectations everyone will use once September starts.")
        note("Football Operations", "Staff", "Fall camp handoff",
             "The offseason file is almost closed. Next stop is Decide Your Depth: camp reps, staff boards, morale reactions and the final opening-day order.")
