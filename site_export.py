"""
site_export.py — Write the league website (Commissioner Mode, Phase 3).

[W] on the Commissioner Desk writes two things:

  site/        THE FOLDER YOU UPLOAD (GitHub Pages). Static files only:
                 index.html, assets/   the website itself (copied from site_template/)
                 data/*.json           public data: manifest, rules, scores (games/w<N>.json box scores), standings, polls,
                                       news, every recruit, one file per team
                 data/private/*.bin    one locked file per player team (password needed)
  exports/     STAYS ON YOUR COMPUTER. Never upload it:
                 passwords_<league>.txt   every player team's website password, to DM out
                 discord_cycle<N>.txt     a ready-to-paste Discord post for the cycle
                 league_directory_*.txt   every program and who coaches it

Exporting only reads the league (and issues passwords to new player teams), so it never
changes results.
"""
import json
import os
import pickle
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "site_template")


def site_dir(league):
    import commissioner as cm
    return cm.state(league).setdefault("links", {}).get("site_dir") or os.path.join(HERE, "site")


def local_dir():
    path = os.path.join(HERE, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False, default=str)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(path + ".tmp", path)
    return len(data)


def export(league):
    """Write the site and the local files. Returns a summary dict."""
    t0 = time.time()
    import random
    rstate = random.getstate()                     # the export draws nothing the league will notice
    try:
        return _export(league, t0)
    finally:
        random.setstate(rstate)


def _export(league, t0):
    import commissioner as cm
    import knowledge as kn
    import orders
    import sitecrypto
    st = cm.state(league)
    orders.ensure_ids(league)
    fresh = cm.ensure_passwords(league)
    fresh_names = {t.school for t in fresh}
    # Everything below reads a private copy of the world: the game's own screens cache what they
    # show (practice, camp reads, morale), and none of that may touch the league you play.
    real = league
    league = pickle.loads(pickle.dumps(real, protocol=pickle.HIGHEST_PROTOCOL))
    fresh = [t for t in league.teams if t.school in fresh_names]
    for t in league.teams:                        # caches keyed by object id don't survive a copy: let them rebuild
        t.__dict__.pop("_practice", None)
        t.__dict__.pop("camp_sessions", None)
    out = site_dir(league)
    data = os.path.join(out, "data")
    os.makedirs(data, exist_ok=True)
    # the website itself
    build = int(time.time())                       # every export gets its own stamp, so browsers never show a stale copy
    with open(os.path.join(TEMPLATE, "index.html"), encoding="utf-8") as f:
        page = f.read().replace("assets/style.css", f"assets/style.css?v={build}").replace("assets/app.js", f"assets/app.js?v={build}")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    if os.path.isdir(os.path.join(out, "assets")):
        shutil.rmtree(os.path.join(out, "assets"))
    shutil.copytree(os.path.join(TEMPLATE, "assets"), os.path.join(out, "assets"))
    open(os.path.join(out, ".nojekyll"), "w").close()               # GitHub Pages: serve files as they are
    sizes = {}
    sizes["manifest"] = _write(os.path.join(data, "manifest.json"), {**kn.manifest(league), "build": build})
    sizes["rules"] = _write(os.path.join(data, "rules.json"), kn.rules(league))
    sizes["scores"] = _write(os.path.join(data, "scores.json"), kn.scores(league))
    sizes["standings"] = _write(os.path.join(data, "standings.json"), kn.standings(league))
    sizes["polls"] = _write(os.path.join(data, "polls.json"), kn.polls(league))
    sizes["news"] = _write(os.path.join(data, "news.json"), kn.news(league))
    sizes["recruits"] = _write(os.path.join(data, "recruits.json"), kn.recruits_public(league))
    sizes["classes"] = _write(os.path.join(data, "classes.json"), kn.classes(league))
    import job_market
    sizes["jobs"] = _write(os.path.join(data, "jobs.json"), job_market.public_jobs(league))
    rdir = os.path.join(data, "rd")
    if os.path.isdir(rdir):
        shutil.rmtree(rdir)
    sizes["details"] = sum(_write(os.path.join(rdir, f"{k}.json"), v) for k, v in kn.recruit_details(league).items())
    gdir = os.path.join(data, "games")
    if os.path.isdir(gdir):
        shutil.rmtree(gdir)
    boxes, logs = kn.box_scores(league)
    sizes["games"] = sum(_write(os.path.join(gdir, f"w{wk}.json"), rows) for wk, rows in boxes.items())
    tdir = os.path.join(data, "teams")
    if os.path.isdir(tdir):
        shutil.rmtree(tdir)
    total = 0
    for t in league.teams:
        total += _write(os.path.join(tdir, kn.slug(t.school) + ".json"), kn.team_public(league, t, logs))
    sizes["teams"] = total
    # one locked file per player team; nothing left behind for teams that went back to CPU
    pdir = os.path.join(data, "private")
    if os.path.isdir(pdir):
        shutil.rmtree(pdir)
    os.makedirs(pdir)
    locked = 0
    for t in cm.player_teams(league):
        row = cm.team_row(league, t)
        raw = json.dumps(kn.team_private(league, t), separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
        keys = bytes.fromhex(row["keys"])
        blob = sitecrypto.lock(raw, (keys[:32], keys[32:]), bytes.fromhex(row["salt"]))
        with open(os.path.join(pdir, kn.slug(t.school) + ".bin"), "wb") as f:
            f.write(blob)
        locked += len(blob)
    sizes["private"] = locked
    league = real
    cm.fresh_reads(league)                         # leave no cached reads behind for the next cycle
    # local files
    loc = local_dir()
    pw_path = os.path.join(loc, f"passwords_{st['league_id']}.txt")
    with open(pw_path, "w", encoding="utf-8") as f:
        f.write(f"WEBSITE PASSWORDS — {st['league_id']} — keep this file private, never upload it\n\n")
        for t in sorted(cm.player_teams(league), key=lambda t: t.school):
            row = cm.team_row(league, t)
            new = " (NEW)" if t.school in fresh_names else ""
            f.write(f"{t.school:<26}@{row['owner']:<24}{row['pw']}{new}\n")
    post_path = os.path.join(loc, f"discord_cycle{st['cycle']['n'] + 1}.txt")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(discord_post(league))
    dir_path = cm.write_directory(league, loc)
    st.setdefault("exports", []).append({"cycle": st["cycle"]["n"] + 1, "at": time.time()})
    del st["exports"][:-40]
    cm.log(league, f"Website exported for cycle {st['cycle']['n'] + 1} ({len(cm.player_teams(league))} team files).")
    return {"site": out, "passwords": pw_path, "post": post_path, "directory": dir_path, "fresh": sorted(fresh_names),
            "sizes": sizes, "seconds": round(time.time() - t0, 1), "teams": len(cm.player_teams(league))}


def discord_post(league):
    import commissioner as cm
    st = cm.state(league)
    links = st.setdefault("links", {})
    nxt = st["cycle"]["n"] + 1
    lines = [f"**{links.get('title') or 'Console College League'} — cycle {nxt} is open: {cm.cycle_label(league)}**"]
    games = [g for g in league.schedule.get(league.week, []) if g.played] if league.week else []
    if games:
        ranked = sorted(games, key=lambda g: min([r for r in ((getattr(g, 'ranks', None) or {}).get(g.home),
                                                             (getattr(g, 'ranks', None) or {}).get(g.away)) if r] or [99]))
        lines.append("")
        lines.append(f"__{league.week_name(league.week)} results__")
        for g in ranked[:8]:
            rk = getattr(g, "ranks", None) or {}
            w, lo = g.winner, g.loser
            tw = f"#{rk[w]} " if rk.get(w) else ""
            tl = f"#{rk[lo]} " if rk.get(lo) else ""
            lines.append(f"{tw}{w.school} {g.score_for(w)}, {tl}{lo.school} {g.score_for(lo)}")
    top = league.rankings.order[:5]
    if top:
        lines.append("")
        lines.append("__Top 5__  " + ", ".join(f"{i}. {t.school} ({t.record})" for i, t in enumerate(top, 1)))
    lines.append("")
    if league.season_complete:
        lines.append("The offseason runs next. No orders needed this cycle.")
    else:
        lines.append("Orders: set your board, depth chart and game plan on the site, build your code, paste it in the form.")
    if links.get("note"):
        lines.append(links["note"])
    if links.get("site_url"):
        lines.append(f"Site: {links['site_url']}")
    if links.get("form_url"):
        lines.append(f"Submit: {links['form_url']}")
    return "\n".join(lines) + "\n"
