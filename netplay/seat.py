"""
netplay/seat.py — several Coach Careers in one world (the online host).

A career keeps some of its coach's life on the league itself: the inbox, the hub, the
presser's memory, the career log, the guide. On the host every player has his own; they're
kept in league.online["career"][school] and swapped in while the game acts as that coach
(acting_as), which also points user_team / user_coach at him and reads the world as his
career. hotseat.py asks here whenever the world is an online one, so every place the game
already loops over "every human coach" runs once per player.
"""
SEAT_KEYS = ("inbox", "_hub_state", "_presser_asked", "_postgame_lift", "_fx_stakes", "_people_week",
             "_people_end", "_nil_seeded", "_pursuit_notes", "_beats", "_asked_players", "_asked_depth",
             "_asked_hurt", "_asked_optout", "_mood_flagged", "_trips", "career_log", "decision_log", "cplus",
             "week_calls", "_prep_done", "_user_offer_terms", "_user_walked", "_your_games_played", "guide",
             "recap_prefs", "recap_seen", "_career_tops", "off_cal", "offseason_state", "_offseason_user_job_market",
             "_reserved_user_jobs", "_hc_interviews", "_job_fields", "_season_end_done")


def online(league):
    return getattr(league, "mode", None) == "online"


def careers(league):
    return league.__dict__.setdefault("online", {}).setdefault("career", {})


def schools(league):
    return [s["school"] for s in (league.__dict__.get("online") or {}).get("seats", {}).values() if s.get("school")]


def name_of(league, school):
    """The player who coaches this school (his career is kept under his name: it follows him)."""
    for s in (league.__dict__.get("online") or {}).get("seats", {}).values():
        if s.get("school") == school:
            return s["name"]
    return school


def humans(league):
    by = {t.school: t for t in league.teams}
    return [by[s] for s in schools(league) if s in by]


class acting_as:
    """with acting_as(league, team): the world is this coach's career (his inbox, his hub...)."""
    def __init__(self, league, team):
        self.league, self.team = league, team
        self.active = False

    def __enter__(self):
        lg, t = self.league, self.team
        if t is None or t.school not in schools(lg) or getattr(lg, "user_team", None) is t:
            return self                                  # not a player, or already him
        self.active = True
        d = lg.__dict__
        self.saved = (d.get("mode"), d.get("user_team"), d.get("user_coach"),
                      d.get("user_offer_hook"), d.get("portal_hook"),
                      {k: d.pop(k) for k in SEAT_KEYS if k in d})
        d.update(careers(lg).get(name_of(lg, t.school), {}))
        d["mode"], d["user_team"], d["user_coach"] = "career", t, t.coach
        import career
        import portal_screens
        d["user_offer_hook"], d["portal_hook"] = career.offer_prompt, portal_screens.portal_window
        from netplay import replay
        self.screen = replay.as_player(name_of(lg, t.school))
        self.screen.__enter__()                          # a question here goes to his computer
        return self

    def __exit__(self, *exc):
        if not self.active:
            return False
        lg, d = self.league, self.league.__dict__
        self.screen.__exit__(None, None, None)
        careers(lg)[name_of(lg, self.team.school)] = {k: d.pop(k) for k in SEAT_KEYS if k in d}
        mode, ut, uc, offer_hook, portal_hook, keep = self.saved
        d["mode"], d["user_team"], d["user_coach"] = mode, ut, uc
        if offer_hook is None:
            d.pop("user_offer_hook", None)
        else:
            d["user_offer_hook"] = offer_hook
        if portal_hook is None:
            d.pop("portal_hook", None)
        else:
            d["portal_hook"] = portal_hook
        d.update(keep)
        return False


def adopt_career(league, school, name=None):
    """A world that came from a Coach Career: its coach's inbox, log and the rest go to the
    player who picks his program (claim_seat files it under that player's name)."""
    d = league.__dict__
    stash = {k: d.pop(k) for k in SEAT_KEYS if k in d}
    if school and stash:
        careers(league)["school:" + school] = stash


def claim_career(league, name, school):
    """At START: a player who takes over the world's own career program takes its career."""
    c = careers(league)
    if "school:" + school in c and name not in c:
        c[name] = c.pop("school:" + school)


def load_mine(league, school):
    """On a client: this copy shows your own career (inbox, hub, log)."""
    d = league.__dict__
    for k in SEAT_KEYS:
        d.pop(k, None)
    d.update(careers(league).get(name_of(league, school), {}))
