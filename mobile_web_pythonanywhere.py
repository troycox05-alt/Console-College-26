"""Console College Mobile Web — Stage 5.
Zero-dependency HTTP server for iPhone/Safari. Uses the real League/save engine.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import json, os, io, contextlib, threading, random

HERE=os.path.dirname(os.path.abspath(__file__))
_lock=threading.RLock(); _league=None

def quiet(fn,*a,**kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a,**kw)

def focus(lg):
    if getattr(lg,'user_coach',None) and lg.user_coach.team: return lg.user_coach.team
    return getattr(lg,'user_team',None) or lg.teams[0]

def summary(lg):
    import gui_data
    t=focus(lg); d=gui_data.snapshot(lg)
    # Keep payload compact for phones.
    return {k:d.get(k) for k in ('team','next','last','coach','program','injuries','leaders','lineup','schedule','standings','top25','news','scores')}

def saves_list():
    import saves
    return [{k:h.get(k) for k in ('name','year','week','mode','coach','team','saved_at','build')} for h in saves.list_saves()]

def quick_career(name, school, preset='balanced'):
    import universe, settings, world_rules
    universe.apply(settings.load().get('universe', universe.DEFAULT))
    from league import League, make_coach
    lg=quiet(League, year=2026, progress=None, burn_in=False)
    lg.universe=universe.current(); world_rules.install(lg, dict(world_rules.PRESETS.get(preset, world_rules.PRESETS['balanced'])))
    team=next((t for t in lg.teams if t.school==school), None)
    if team is None: team=sorted(lg.teams,key=lambda x:x.school)[0]
    from models import Team
    shell=Team('—','—','—',0,'—',None,'',{k:60 for k in Team.RATING_KEYS}); shell.ratings['coach']=60
    c=make_coach((name or 'Chris Walker').strip()[:40], shell)
    for k in c.ratings: c.ratings[k]=55
    c.overall=60; c.team=None; c.traits=[]; c.age=38; c.ceiling=96; c.personality='builder'; c.retire_age=99
    c.is_user=True; c.background='Mobile Career'; c.difficulty='standard'; c.prestige_start='unknown'
    import carousel; carousel.init_coach(c, lg.year, origin='Mobile Career (you)')
    lg.mode='career'; lg.user_coach=c; lg.career_log=[(lg.year,'Began a head coaching career from Console College Mobile.')]
    import career
    old_pause=getattr(career,'pause'); career.pause=lambda *a,**k: None
    try: quiet(career.take_job, lg, c, team, first=True)
    finally: career.pause=old_pause
    import saves; quiet(saves.save,lg,saves.AUTOSAVE)
    return lg

def sim_week(lg):
    if lg.season_complete: return 'Season complete — offseason hub is now available from the mobile navigation.'
    import preseason, week, gameday_show
    old=getattr(lg,'autosim',False); lg.autosim=True
    try:
        if preseason.needed(lg): quiet(preseason.mark_done,lg)
        quiet(week.auto_week,lg)
        games=lg.start_week(); quiet(gameday_show.quiet_show,lg,games)
        for g in games: lg.play_game(g)
        # Keep the user's recruiting board manual while CPU staffs still work theirs.
        lg.autosim=False
        lg.finish_week(games)
        lg.autosim=True
        import saves; quiet(saves.autosave,lg)
    finally: lg.autosim=old
    t=focus(lg); mine=[g for g in games if t in (g.home,g.away)]
    if mine:
        g=mine[0]; o=g.opponent_of(t); return f"{'W' if g.winner is t else 'L'} {g.score_for(t)}-{g.score_for(o)} vs {o.school}"
    return f"Simulated {lg.week_name(lg.week)}"

INDEX=r'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#101317"><title>Console College</title><style>
:root{color-scheme:dark;--bg:#0d1014;--card:#171c22;--line:#2b333d;--muted:#98a3af;--gold:#f2c14e;--green:#66d17a;--red:#ff6b6b;--blue:#75b7ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#f4f7fa;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.wrap{max-width:760px;margin:auto;padding:calc(14px + env(safe-area-inset-top)) 14px calc(30px + env(safe-area-inset-bottom))}h1{font-size:24px;margin:6px 0 2px}.sub,.muted{color:var(--muted)}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px;margin:12px 0}.hero{border-color:#4a4125}.row{display:flex;gap:10px;align-items:center;justify-content:space-between}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}button,select,input{font:inherit;min-height:46px;border-radius:12px;border:1px solid var(--line);background:#11161c;color:#fff;padding:9px 11px}button{font-weight:700}button.primary{background:var(--gold);color:#16130b;border-color:var(--gold)}button.good{background:#183e24;border-color:#2c6b3c}.wide{width:100%}label{display:block;margin:10px 0 5px;color:var(--muted);font-size:14px}.tabs{display:flex;gap:8px;overflow:auto;padding:6px 0;position:sticky;top:0;background:var(--bg);z-index:3}.tabs button{white-space:nowrap;min-height:42px}.big{font-size:30px;font-weight:800}.rank{color:var(--gold)}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:9px 4px;border-bottom:1px solid var(--line);text-align:left}.win{color:var(--green)}.loss{color:var(--red)}#toast{min-height:22px;color:var(--gold);font-size:14px}.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;margin:2px;font-size:12px}.recruit{border-top:1px solid var(--line);padding:12px 0}.actions{display:flex;gap:6px;overflow:auto;margin-top:8px}.actions button{min-height:38px;white-space:nowrap;font-size:13px}.stars{color:var(--gold)}.top5{font-size:12px;color:var(--muted);margin-top:5px}.meter{height:8px;background:#0d1116;border-radius:8px;overflow:hidden}.meter i{display:block;height:100%;background:var(--gold)}.depthplayer{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px 0;border-top:1px solid var(--line)}.tiny button{min-height:36px;padding:5px 10px}.sectiontitle{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}@media(max-width:430px){.grid{grid-template-columns:1fr}.big{font-size:26px}}
</style></head><body><div class="wrap"><h1>CONSOLE COLLEGE <span class="rank">MOBILE</span></h1><div class="sub">v52.90 · Stabilized + Expanded Mobile</div><div id="toast"></div><main id="app"></main></div><script>
const app=document.querySelector('#app'),toast=document.querySelector('#toast');let state=null,tab='home',game=null,rec=null,dep=null,port=null,ibox=null,med=null,strat=null,prog=null,classes=null,off=null,hq=null,camp=null,sets=null,today=null,directory=null,scout=null,national=null,leaders=null,activity=null;
async function api(path,opt={}){let r=await fetch(path,{headers:{'Content-Type':'application/json'},...opt});let j=await r.json();if(!r.ok)throw Error(j.error||j.message||'Request failed');return j}function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}function say(s){toast.textContent=s||''}
async function boot(){try{let j=await api('/api/state');state=j.state;if(state) render(); else await startScreen()}catch(e){app.innerHTML='<div class=card>'+esc(e.message)+'</div>'}}
async function startScreen(){let j=await api('/api/setup');let opts=j.teams.map(t=>`<option>${esc(t)}</option>`).join('');let saves=j.saves.map((s,i)=>`<button class="wide" data-load="${i}">Load ${esc(s.name)} · ${esc(s.team||'World')} · ${s.year}</button>`).join('');app.innerHTML=`<div class="card hero"><b>Start a mobile career</b><label>Coach name</label><input id=name class=wide value="Chris Walker"><label>Program</label><select id=school class=wide>${opts}</select><label>Universe</label><select id=preset class=wide><option value=balanced>Balanced</option><option value=stable>Stable World</option><option value=chaos>Chaos</option></select><p class=muted>Stage 3 adds inbox decisions, media and sim strategy.</p><button id=new class="primary wide">Build My World</button></div>${saves?'<div class=card><b>Saved games</b><div style="display:grid;gap:8px;margin-top:10px">'+saves+'</div></div>':''}`;new.onclick=async()=>{say('Building the universe…');new.disabled=true;try{let x=await api('/api/new',{method:'POST',body:JSON.stringify({name:name.value,school:school.value,preset:preset.value})});state=x.state;render()}catch(e){say(e.message);new.disabled=false}};document.querySelectorAll('[data-load]').forEach(b=>b.onclick=async()=>{let x=await api('/api/load',{method:'POST',body:JSON.stringify({index:+b.dataset.load})});state=x.state;render()})}
function nav(){return `<div class=tabs>${[['home','Today'],['gameday','Game Day'],['recruit','Recruit'],['depth','Depth'],['roster','Roster'],['directory','Players'],['scout','Scout'],['schedule','Schedule'],['standings','Standings'],['national','National'],['leaders','Leaders'],['activity','Activity'],['portal','Portal'],['inbox','Inbox'],['media','Media'],['strategy','Strategy'],['classes','Classes'],['program','Program'],['camp','Camp'],['settings','Settings'],['hq','More']].map(x=>`<button data-tab=${x[0]}>${x[1]}</button>`).join('')}</div>`}
function recRow(r,discover=false){let acts=discover&&!r.target?`<button data-ra="add" data-r="${r.rank}">+ Board</button>`:`<button data-ra="evaluate" data-r="${r.rank}">Film</button><button data-ra="offer" data-r="${r.rank}">Offer</button><button data-ra="contact" data-r="${r.rank}">Contact</button><button data-ra="position_coach" data-r="${r.rank}">Coach</button><button data-ra="campus_visit" data-r="${r.rank}">Visit</button><button data-ra="in_home" data-r="${r.rank}">In-home</button><button data-ra="close" data-r="${r.rank}">Close</button><button data-ra="drop" data-r="${r.rank}">Drop</button>`;return `<div class=recruit><div class=row><div><b>#${r.rank} ${esc(r.name)}</b> <span class=stars>${'★'.repeat(r.stars)}</span><div class=muted>${r.pos} · ${esc(r.state)} · scouted ${esc(r.range)}</div></div><b>${esc(r.standing)}</b></div><div class=top5>${r.commit?'Committed: '+esc(r.commit):'Top 5: '+esc(r.top5.join(', ')||'forming')}</div>${r.connections?.length?`<div class=top5>Connections: ${r.connections.map(x=>esc(x.name)+' — '+esc(x.label)).join('; ')}</div>`:''}<div class=actions>${acts}</div></div>`}
async function loadTab(){if(tab==='home')today=await api('/api/today');if(tab==='directory')directory=await api('/api/directory');if(tab==='scout')scout=await api('/api/scout');if(tab==='national')national=await api('/api/national');if(tab==='leaders')leaders=await api('/api/leaders');if(tab==='activity')activity=await api('/api/activity');if(tab==='gameday')game=await api('/api/gameday');if(tab==='settings')sets=await api('/api/settings');if(tab==='hq')hq=await api('/api/hq');if(tab==='camp')camp=await api('/api/camp');if(tab==='offseason')off=await api('/api/offseason');if(tab==='recruit')rec=await api('/api/recruiting');if(tab==='depth')dep=await api('/api/depth');if(tab==='portal')port=await api('/api/portal');if(tab==='inbox')ibox=await api('/api/inbox');if(tab==='media')med=await api('/api/media');if(tab==='strategy')strat=await api('/api/strategy');if(tab==='classes')classes=await api('/api/classes');if(tab==='program')prog=await api('/api/program');render()}
function render(){let t=state.team||{},n=state.next||{},body='';if(tab==='home'){body=`<div class="card hero"><div class=row><div><div class=muted>${esc(t.confName||t.conference)}</div><div class=big>${t.rank?'#'+t.rank+' ':''}${esc(t.school)}</div><div>${esc(t.nickname||'')} · ${esc(t.record||'0-0')}</div></div><div style="text-align:right"><div class=muted>${esc(t.when||'Preseason')}</div><div>${esc(t.streak||'')}</div></div></div></div>${today?`<div class=card><b>Coach's Today</b>${today.items.map(x=>`<div class=depthplayer><div><b>${esc(x.title)}</b><div class=muted>${esc(x.detail)}</div></div><span class=pill>${esc(x.status)}</span></div>`).join('')}</div>`:''}<div class=card><b>Next game</b><p>${n.opp?`${esc(n.site)} ${n.oppRank?'#'+n.oppRank+' ':''}<b>${esc(n.opp)}</b> · ${esc(n.oppRecord)}`:'No game scheduled'}</p><button id=sim class="primary wide">Sim Next Week</button></div>${state.last?`<div class=card><b>Last game</b><p class=${state.last.won?'win':'loss'}>${state.last.won?'WIN':'LOSS'} · ${state.last.us}-${state.last.them} ${esc(state.last.site)} ${esc(state.last.opp)}</p></div>`:''}`}
else if(tab==='directory'){body=directory?`<div class=card><b>Player Directory</b><input id=psearch class=wide placeholder="Search name, position, class or state"><div id=plist>${directory.players.map(p=>`<button class="wide" style="text-align:left;margin-top:7px" data-player="${esc(p.id)}" data-search="${esc((p.name+' '+p.pos+' '+p.cls+' '+p.state).toLowerCase())}"><b>${esc(p.name)}</b> · ${esc(p.pos)} · ${p.ovr} OVR · ${p.exp} EXP<div class=muted>${esc(p.cls)} · ${esc(p.state)} · ${esc(p.team)}</div></button>`).join('')}</div></div>`:'<div class=card>Loading players…</div>'}
else if(tab==='scout'){body=scout?`<div class=card hero><b>Opponent Scout</b><p>${esc(scout.matchup)}</p><div class=muted>${esc(scout.summary)}</div></div>${scout.sections.map(s=>`<div class=card><b>${esc(s.title)}</b>${s.lines.map(x=>`<div class=depthplayer>${esc(x)}</div>`).join('')}</div>`).join('')}`:'<div class=card>Loading scout…</div>'}
else if(tab==='national'){body=national?`<div class=card hero><b>National Scoreboard</b><p class=muted>${esc(national.week)}</p></div>${national.games.map(g=>`<div class=card><b>${esc(g)}</b></div>`).join('')}`:'<div class=card>Loading national view…</div>'}
else if(tab==='leaders'){body=leaders?`<div class=card hero><b>Team Leaders</b></div>${leaders.sections.map(s=>`<div class=card><b>${esc(s.title)}</b>${s.lines.map(x=>`<div class=depthplayer>${esc(x)}</div>`).join('')}</div>`).join('')}`:'<div class=card>Loading leaders…</div>'}
else if(tab==='activity'){body=activity?`<div class=card hero><b>Program Activity</b><p class=muted>Recent roster, recruiting, portal, injury and career events.</p></div><div class=card>${activity.items.map(x=>`<div class=depthplayer>${esc(x)}</div>`).join('')||'<span class=muted>No logged activity yet.</span>'}</div>`:'<div class=card>Loading activity…</div>'}
else if(tab==='gameday'){body=game?`<div class="card hero"><b>Game Day</b><p>${esc(game.matchup||game.status)}</p><div class=big>${esc(game.score||'')}</div><div class=muted>${esc(game.situation||'')}</div></div>${game.log?`<div class=card><b>Headset / booth</b><pre style="white-space:pre-wrap;font:13px ui-monospace,SFMono-Regular,monospace;line-height:1.35">${esc(game.log)}</pre></div>`:''}${game.prompt?`<div class=card><b>Your decision</b><p>${esc(game.prompt)}</p><input id=gameans class=wide placeholder="Type the console choice here"><button id=gamesend class="primary wide" style="margin-top:8px">Send Call</button></div>`:''}${game.canStart?`<div class=card><p class=muted>This starts your actual console football engine with every-snap coaching. Every console decision is bridged to this screen.</p><button id=gamestart class="primary wide">Start Game</button></div>`:''}${game.done?`<div class=card><b>Final</b><p>${esc(game.final||'Game complete')}</p><button id=gameback class=wide>Return to Today</button></div>`:''}`:'<div class=card>Loading Game Day…</div>'}
else if(tab==='offseason'){body=off?`<div class=card hero><b>Offseason Command Center</b><p>${esc(off.status)}</p><div class=muted>${esc(off.detail||'')}</div></div><div class=card><b>17-Week Calendar</b>${off.weeks.map(w=>`<div class=depthplayer><div><b>${w.done?'✓ ':''}Week ${w.n} · ${esc(w.label)}</b><div class=muted>${esc(w.blurb)}</div></div><span>${w.current?'NOW':''}</span></div>`).join('')}</div>${off.canAdvance?`<div class=card><b>${esc(off.actionTitle)}</b><p class=muted>${esc(off.actionHelp)}</p><button id=offadv class="primary wide">${esc(off.actionLabel)}</button></div>`:''}`:'<div class=card>Loading offseason…</div>'}
else if(tab==='recruit'){if(!rec){body='<div class=card>Loading recruiting…</div>'}else{body=`<div class="card hero"><div class=sectiontitle><b>Recruiting War Room</b><b>${rec.hours}/${rec.hoursTotal} hrs</b></div><div class=muted>${esc(rec.explain)}</div><p>Class momentum: <b>${esc(rec.momentumWord)}</b> · ${rec.momentum}/100 ${rec.classRank?'· #'+rec.classRank+' class':''}</p><div class=meter><i style="width:${rec.momentum}%"></i></div></div><div class=card><b>Your board</b>${rec.board.length?rec.board.map(r=>recRow(r)).join(''):'<p class=muted>No targets yet. Add prospects below.</p>'}</div><div class=card><b>National prospects</b><p class=muted>Top available prospects. Add them to your board before investing hours.</p>${rec.discover.slice(0,50).map(r=>recRow(r,true)).join('')}</div>`}}
else if(tab==='depth'){body=dep?dep.rooms.map(room=>`<div class=card><div class=sectiontitle><b>${room.pos} depth chart</b><span class=muted>${room.starters} starter${room.starters===1?'':'s'}</span></div>${room.players.map((p,i)=>`<div class=depthplayer><div><b>${i<room.starters?'★ ':''}#${p.num} ${esc(p.short)}</b><div class=muted>${esc(p.yr)} · ${p.ovr} OVR${p.exp?' · '+p.exp+' EXP':''}${p.hurt?' · INJURED':''}</div></div><div class=tiny><button data-d="up" data-pos="${room.pos}" data-name="${esc(p.name)}">↑</button><button data-d="down" data-pos="${room.pos}" data-name="${esc(p.name)}">↓</button></div></div>`).join('')}</div>`).join(''):'<div class=card>Loading depth chart…</div>'}
else if(tab==='roster'){body=`<div class=card><b>Starting lineup</b><table><tr><th>Pos</th><th>Player</th><th>Yr</th><th>OVR</th></tr>${(state.lineup||[]).map(p=>`<tr><td>${p.pos}</td><td><button data-player="${p.id}" style="min-height:32px;padding:4px 7px">#${p.num} ${esc(p.name)}</button></td><td>${esc(p.yr)}</td><td>${esc(p.ovr)}</td></tr>`).join('')}</table></div>`}
else if(tab==='schedule'){body=`<div class=card><b>${esc(t.school)} schedule</b><table>${(state.schedule||[]).map(g=>`<tr><td>${esc(g.wk)}</td><td>${esc(g.site)} ${g.oppRank?'#'+g.oppRank+' ':''}${esc(g.opp)}</td><td class=${g.played?(g.won?'win':'loss'):''}>${g.played?(g.won?'W ':'L ')+g.score:(g.next?'NEXT':'')}</td></tr>`).join('')}</table></div>`}
else if(tab==='standings'){let s=state.standings||{};body=`<div class=card><b>${esc(s.conf||'Conference')} standings</b><table><tr><th>Team</th><th>Conf</th><th>All</th></tr>${(s.rows||[]).map(r=>`<tr><td>${r.rank?'#'+r.rank+' ':''}${esc(r.school)}${r.me?' •':''}</td><td>${esc(r.conf)}</td><td>${esc(r.all)}</td></tr>`).join('')}</table></div><div class=card><b>Top 25</b><table>${(state.top25?.poll||[]).map(r=>`<tr><td>#${r.rank}</td><td>${esc(r.school)}${r.me?' •':''}</td><td>${esc(r.record)}</td></tr>`).join('')}</table></div><div class=card><b>${esc(state.scores?.label||'National scoreboard')}</b>${(state.scores?.rows||[]).map(g=>`<div class=depthplayer><div>${g.ar?'#'+g.ar+' ':''}${esc(g.away)} ${g.a??''} ${g.a!==undefined?'—':''} ${g.h??''} ${g.hr?'#'+g.hr+' ':''}${esc(g.home)}</div></div>`).join('')}</div>`}
else if(tab==='inbox'){body=ibox?`<div class=card><b>Program Inbox</b><p class=muted>${ibox.unread} unread · ${ibox.waiting} waiting on you</p></div>${ibox.messages.map((m,i)=>`<div class=card><b>${esc(m.sender)} · ${esc(m.subject)}</b><p>${esc(m.body)}</p>${m.answered?`<div class=muted>Answered: ${esc(m.answered)}</div>`:(m.replies||[]).map(r=>`<button class="wide" style="margin-top:7px" data-ir="${i}" data-key="${esc(r.key)}">${esc(r.label)}</button>`).join('')}</div>`).join('')}`:'<div class=card>Loading inbox…</div>'}
else if(tab==='media'){body=med?`<div class=card><b>Thursday Press Conference</b><p class=muted>${esc(med.context)}</p></div>${med.questions.map((q,qi)=>`<div class=card><b>${esc(q.text)}</b>${q.answers.map((a,ai)=>`<button class="wide" style="margin-top:8px" data-ma="${qi}" data-ai="${ai}"><span class=muted>${esc(a.tone)}</span> · ${esc(a.text)}</button>`).join('')}</div>`).join('')}`:'<div class=card>Loading media…</div>'}
else if(tab==='strategy'){body=strat?`<div class=card><b>Sim Playcalling Strategy</b><p class=muted>These bend your scheme; score, clock, opponent looks and coordinator logic still matter.</p></div>${strat.settings.map(x=>`<div class=card><div class=row><div><b>${esc(x.label)}</b><div class=muted>${esc(x.help||'')}</div></div><button data-sk="${x.key}">${esc(x.value)}</button></div></div>`).join('')}`:'<div class=card>Loading strategy…</div>'}
else if(tab==='classes'){body=classes?`<div class=card><b>Recruiting Class</b><p class=muted>${classes.recruitRank?'National rank #'+classes.recruitRank+' · ':''}${classes.commits.length} commitments / signees</p>${classes.commits.map(x=>`<div class=recruit><b>${esc(x.name)}</b> <span class=stars>${'★'.repeat(x.stars)}</span><div class=muted>${x.pos} · ${esc(x.state)}</div></div>`).join('')||'<p class=muted>No high-school commitments recorded yet.</p>'}</div><div class=card><b>Transfer Class</b><p class=muted>${classes.transfers.length} incoming transfer${classes.transfers.length===1?'':'s'}</p>${classes.transfers.map(x=>`<div class=recruit><b>${esc(x.name)}</b> · ${x.pos} · ${x.ovr} OVR<div class=muted>from ${esc(x.from)}</div></div>`).join('')||'<p class=muted>No incoming transfers recorded yet.</p>'}</div>`:'<div class=card>Loading classes…</div>'}
else if(tab==='camp'){body=camp?`<div class=card hero><b>Fall Camp & Preseason</b><p>${esc(camp.status)}</p><div class=muted>${esc(camp.outlook.join(' · '))}</div></div><div class=card><b>Camp report</b>${camp.rooms.map(x=>`<div class=depthplayer><div><b>${x.pos}</b><div class=muted>${esc(x.note)}</div></div></div>`).join('')}</div><div class=card><b>Redshirt plan</b><p class=muted>Tap an eligible player to protect/unprotect his season.</p>${camp.redshirts.map(x=>`<div class=row style="margin:8px 0"><span>${esc(x.name)} · ${x.pos} · ${x.ovr} OVR · ${esc(x.yr)}</span><button data-rs="${esc(x.name)}">${x.planned?'PLANNED':'ACTIVE'}</button></div>`).join('')}</div>`:'<div class=card>Loading camp…</div>'}
else if(tab==='settings'){body=sets?`<div class=card hero><b>Settings</b><p class=muted>Full mobile translation of the console settings menu. Changes save automatically.</p><button id=copyctx class="primary wide">Copy Team Context</button><p class=muted>Copies the same coach-safe Team Context packet that the console version downloads as a .txt file.</p></div>${sets.groups.map(g=>`<div class=card><b>${esc(g.title)}</b>${g.items.map(x=>`<div class=row style="margin:10px 0"><div><b>${esc(x.label)}</b><div class=muted>${esc(x.help||'')}</div></div><button data-set="${esc(x.key)}">${esc(x.value)}</button></div>`).join('')}</div>`).join('')}<div class=card><b>Big Moments</b>${sets.moments.map(x=>`<div class=row style="margin:10px 0"><div><b>${esc(x.label)}</b><div class=muted>${esc(x.help||'')}</div></div><button data-set="moment:${esc(x.key)}">${esc(x.value)}</button></div>`).join('')}</div><div class=card><b>Sideline</b>${sets.sideline.map(x=>`<div class=row style="margin:10px 0"><div><b>${esc(x.label)}</b><div class=muted>${esc(x.help||'')}</div></div><button data-set="sideline:${esc(x.key)}">${esc(x.value)}</button></div>`).join('')}</div><div class=card><b>Campus Countdown Cast</b><p class=muted>${esc(sets.showName)}</p>${sets.cast.map(x=>`<div class=depthplayer><div><b>${esc(x.role)}</b><div class=muted>${esc(x.name)}</div></div><button data-cast="${esc(x.key)}" data-name="${esc(x.name)}">Edit</button></div>`).join('')}<div class=actions><button data-set="cast:alternate">Alternate Crew</button><button data-set="cast:reset">Restore Defaults</button></div></div>`:'<div class=card>Loading settings…</div>'}
else if(tab==='hq'){body=hq?`<div class=card hero><b>Career HQ</b><p class=muted>Console-to-iPhone parity views.</p></div>${hq.sections.map(s=>`<div class=card><b>${esc(s.title)}</b>${s.lines.map(x=>`<div class=depthplayer><div>${esc(x)}</div></div>`).join('')||'<p class=muted>Nothing yet.</p>'}</div>`).join('')}`:'<div class=card>Loading Career HQ…</div>'}
else if(tab==='program'){body=prog?`<div class=card hero><b>Program Control</b><p>${esc(prog.school)} · ${esc(prog.coach)}</p><div class=muted>${esc(prog.offseason)}</div></div><div class=card><b>Staff</b>${prog.staff.map(x=>`<div class=depthplayer><div><b>${esc(x.role)} · ${esc(x.name)}</b><div class=muted>${x.ovr?x.ovr+' OVR · ':''}${esc(x.detail||'')}</div></div></div>`).join('')}</div><div class=card><b>Universe Rules</b><p class=muted>Tap a rule to toggle it for this career.</p>${prog.rules.map(x=>`<div class=row style="margin:8px 0"><div><b>${esc(x.label)}</b><div class=muted>${esc(x.help)}</div></div><button data-rule="${x.key}">${x.on?'ON':'OFF'}</button></div>`).join('')}</div>`:'<div class=card>Loading program…</div>'}
else{body=port?`<div class=card><b>Transfer Portal</b><p class=muted>${esc(port.message)}</p>${port.active?`<p><b>${port.hours} hours</b> · ${port.offers} offers out</p>`:''}</div>${(port.rows||[]).map(r=>`<div class=card><div class=row><b>${esc(r.name)} · ${r.pos} · ${r.ovr}</b><span>${esc(r.heat)}</span></div><div class=muted>From ${esc(r.from)} · ${esc(r.reason)}</div><p>Top 5: ${esc(r.top5.join(', '))}</p>${r.interest?'<p>Interest: <b>'+esc(r.interest)+'</b></p>':''}${r.destination?'<b>Destination: '+esc(r.destination)+'</b>':port.active?`<div class=actions><button data-pa="contact" data-name="${esc(r.name)}">Contact</button><button data-pa="pitch" data-name="${esc(r.name)}">Pitch</button><button data-pa="visit" data-name="${esc(r.name)}">Visit</button><button data-pa="offer" data-name="${esc(r.name)}">${r.offered?'Pull offer':'Offer spot'}</button></div>`:''}</div>`).join('')}`:'<div class=card>Loading portal…</div>'}
app.innerHTML=nav()+body+`<div class=card><button id=save class="good wide">Save Career</button><button id=exit class="wide" style="margin-top:8px">Back to Start Screen</button></div>`;document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;loadTab()});let sim=document.querySelector('#sim');if(sim)sim.onclick=async()=>{sim.disabled=true;say('Simulating…');try{let x=await api('/api/sim',{method:'POST'});state=x.state;rec=dep=port=null;say(x.message);render()}catch(e){say(e.message);sim.disabled=false}};document.querySelectorAll('[data-ra]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/recruit',{method:'POST',body:JSON.stringify({rank:+b.dataset.r,action:b.dataset.ra})});rec=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-d]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/depth',{method:'POST',body:JSON.stringify({pos:b.dataset.pos,name:b.dataset.name,direction:b.dataset.d})});dep=x.data;say(x.message);let st=await api('/api/state');state=st.state;render()}catch(e){say(e.message)}});document.querySelectorAll('[data-ir]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/inbox',{method:'POST',body:JSON.stringify({index:+b.dataset.ir,key:b.dataset.key})});ibox=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-ma]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/media',{method:'POST',body:JSON.stringify({question:+b.dataset.ma,answer:+b.dataset.ai})});med=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-sk]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/strategy',{method:'POST',body:JSON.stringify({key:b.dataset.sk})});strat=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-rule]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/program',{method:'POST',body:JSON.stringify({key:b.dataset.rule})});prog=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-pa]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/portal',{method:'POST',body:JSON.stringify({name:b.dataset.name,action:b.dataset.pa})});port=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-rs]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/camp',{method:'POST',body:JSON.stringify({name:b.dataset.rs})});camp=x.data;say(x.message);render()}catch(e){say(e.message)}});let oa=document.querySelector('#offadv');if(oa)oa.onclick=async()=>{oa.disabled=true;say('Processing offseason…');try{let x=await api('/api/offseason',{method:'POST'});off=x.data;state=x.state;say(x.message);render()}catch(e){say(e.message);oa.disabled=false}};document.querySelectorAll('[data-set]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/settings',{method:'POST',body:JSON.stringify({key:b.dataset.set})});sets=x.data;say(x.message);render()}catch(e){say(e.message)}});document.querySelectorAll('[data-cast]').forEach(b=>b.onclick=async()=>{let v=prompt('Cast name (blank restores default):',b.dataset.name||'');if(v===null)return;try{let x=await api('/api/settings',{method:'POST',body:JSON.stringify({key:'castname:'+b.dataset.cast,value:v})});sets=x.data;say(x.message);render()}catch(e){say(e.message)}});let cc=document.querySelector('#copyctx');if(cc)cc.onclick=async()=>{try{let x=await api('/api/team-context');if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(x.text)}else{let ta=document.createElement('textarea');ta.value=x.text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.focus();ta.select();document.execCommand('copy');ta.remove()}say(`Copied ${x.lines.toLocaleString()} lines of team context to clipboard.`);cc.textContent='Copied ✓';setTimeout(()=>cc.textContent='Copy Team Context',1800)}catch(e){say('Copy failed: '+e.message)}};let ps=document.querySelector('#psearch');if(ps)ps.oninput=()=>{let q=ps.value.toLowerCase();document.querySelectorAll('[data-search]').forEach(x=>x.style.display=x.dataset.search.includes(q)?'block':'none')};document.querySelectorAll('[data-player]').forEach(b=>b.onclick=async()=>{try{let x=await api('/api/player?id='+encodeURIComponent(b.dataset.player));alert(x.text)}catch(e){say(e.message)}});let gs=document.querySelector('#gamestart');if(gs)gs.onclick=async()=>{gs.disabled=true;say('Starting Game Day…');try{game=await api('/api/gameday/start',{method:'POST'});render();gamePoll()}catch(e){say(e.message);gs.disabled=false}};let gsend=document.querySelector('#gamesend');if(gsend)gsend.onclick=async()=>{let a=document.querySelector('#gameans').value;gsend.disabled=true;try{game=await api('/api/gameday/answer',{method:'POST',body:JSON.stringify({answer:a})});render();gamePoll()}catch(e){say(e.message);gsend.disabled=false}};let gb=document.querySelector('#gameback');if(gb)gb.onclick=async()=>{let st=await api('/api/state');state=st.state;tab='home';today=await api('/api/today');render()};save.onclick=async()=>{await api('/api/save',{method:'POST'});say('Saved.')};exit.onclick=async()=>{await api('/api/close',{method:'POST'});state=null;startScreen()}}
async function gamePoll(){if(tab!=='gameday')return;for(let i=0;i<40;i++){await new Promise(r=>setTimeout(r,250));let g=await api('/api/gameday');game=g;if(g.prompt||g.done){render();return}}render()}
boot();</script></body></html>
'''

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def sendj(self,obj,status=200):
        b=json.dumps(obj,default=str).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
        except:return {}
    def do_GET(self):
        global _league
        p=urlparse(self.path).path
        if p=='/':
            b=INDEX.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b); return
        try:
            with _lock:
                if p=='/api/state': return self.sendj({'state':summary(_league) if _league else None})
                if p=='/api/recruiting': return self.sendj(recruiting_snapshot(_league)) if _league else self.sendj({'error':'No career loaded'},400)
                if p=='/api/depth': return self.sendj(depth_snapshot(_league)) if _league else self.sendj({'error':'No career loaded'},400)
                if p=='/api/portal': return self.sendj(portal_snapshot(_league)) if _league else self.sendj({'error':'No career loaded'},400)
                if p=='/api/setup':
                    if _league: teams=sorted(t.school for t in _league.teams)
                    else:
                        from teams_data import TEAMS; teams=sorted(r[0] for r in TEAMS)
                    return self.sendj({'teams':teams,'saves':saves_list()})
            self.sendj({'error':'Not found'},404)
        except Exception as e:self.sendj({'error':str(e)},500)
    def do_POST(self):
        global _league
        p=urlparse(self.path).path; d=self.body()
        try:
            with _lock:
                if p=='/api/new': _league=quick_career(d.get('name'),d.get('school'),d.get('preset','balanced')); return self.sendj({'state':summary(_league)})
                if p=='/api/load':
                    import saves; rows=saves.list_saves(); i=int(d.get('index',0)); _league=quiet(saves.load,rows[i]['path']); return self.sendj({'state':summary(_league)})
                if not _league: return self.sendj({'error':'No career loaded'},400)
                if p=='/api/recruit':
                    ok,msg=recruit_action(_league,d.get('rank'),d.get('action')); return self.sendj({'ok':ok,'message':msg,'data':recruiting_snapshot(_league)},200 if ok else 400)
                if p=='/api/depth':
                    ok,msg=depth_move(_league,d.get('pos'),d.get('name'),d.get('direction')); return self.sendj({'ok':ok,'message':msg,'data':depth_snapshot(_league)},200 if ok else 400)
                if p=='/api/sim': return self.sendj({'message':sim_week(_league),'state':summary(_league)})
                if p=='/api/save':
                    import saves; quiet(saves.save,_league,saves.AUTOSAVE); return self.sendj({'ok':True})
                if p=='/api/close': _league=None; return self.sendj({'ok':True})
            self.sendj({'error':'Not found'},404)
        except Exception as e:self.sendj({'error':f'{type(e).__name__}: {e}'},500)


def _find_recruit(lg, rank):
    try: rank=int(rank)
    except: return None
    return next((r for r in lg.recruiting.pool if r.national_rank == rank), None)

def recruiting_snapshot(lg):
    import recruit_plus
    rc=lg.recruiting; t=focus(lg)
    def row(r):
        lo,hi=r.scouting_range(t); tops=r.top_schools(5)
        con=recruit_plus.class_connections(rc,t,r,3)
        return {'rank':r.national_rank,'name':r.name,'pos':r.position,'stars':r.stars,'state':r.home_state,
                'range':f'{lo}-{hi}','standing':r.standing(t),'interest':round(r.interest.get(t,0),1),
                'offered':t in r.offers,'target':r in t.recruiting_targets,
                'commit':r.committed_to.school if r.committed_to else None,
                'top5':[x.school for x in tops],
                'connections':[{'name':c.player.name,'label':lab} for _,c,lab in con],
                'priorities':list(r.known_priorities(t))}
    board=rc.board_for(t)
    # Discovery list favors high-ranked open players plus anyone already showing interest.
    discover=[r for r in rc.pool if not r.signed and (r.committed_to is None or r.committed_to is t)]
    discover=sorted(discover,key=lambda r:(r not in t.recruiting_targets, r.national_rank))[:120]
    mom=recruit_plus.class_momentum(rc,t)
    commits=rc.commitments(t)
    return {'hours':rc.remaining_hours(t),'hoursTotal':rc.hours_for(t),'explain':rc.hours_explained(t),
            'momentum':round(mom,1),'momentumWord':recruit_plus.momentum_word(mom),
            'classRank':rc.class_rank(t),'commits':[row(r) for r in commits],
            'board':[row(r) for r in board],'discover':[row(r) for r in discover]}

def recruit_action(lg, rank, action):
    rc=lg.recruiting; t=focus(lg); r=_find_recruit(lg,rank)
    if r is None: return False,'Recruit not found.'
    if action=='add':
        return (rc.add_target(t,r), 'Added to your board.' if r in t.recruiting_targets else 'Board is full or he is already on it.')
    if action=='drop': rc.drop_target(t,r); return True,'Removed from your board.'
    if action not in ('evaluate','contact','offer','position_coach','campus_visit','in_home','close'):
        return False,'Unknown recruiting action.'
    if r not in t.recruiting_targets: rc.add_target(t,r)
    return rc.apply_action(t,r,action,enforce=True,pitch='auto',source='mobile')

def depth_snapshot(lg):
    import depth
    t=focus(lg); starts=depth.starters(t); rooms=[]
    for pos in ('QB','RB','WR','TE','OL','DL','LB','CB','S','K','P'):
        ps=t.players_at(pos)
        rooms.append({'pos':pos,'starters':starts.get(pos,1),'players':[{'name':p.name,'short':p.short_name,'num':p.number,
            'yr':p.class_label,'ovr':p.overall,'exp':getattr(p,'experience',getattr(p,'exp',None)),
            'hurt':getattr(p,'inj_games',0)>0} for p in ps]})
    return {'rooms':rooms}

def depth_move(lg,pos,name,direction):
    t=focus(lg); order=t.__dict__.setdefault('depth_order',{})
    room=list(t.players_at(pos)); idx=next((i for i,p in enumerate(room) if p.name==name),None)
    if idx is None:return False,'Player not found in that position room.'
    j=idx-1 if direction=='up' else idx+1
    if j<0 or j>=len(room):return False,'Already at the edge of the depth chart.'
    room[idx],room[j]=room[j],room[idx]; order[pos]=room; t.depth_set=lg.year
    return True,f'{name} moved {direction} the {pos} depth chart.'

def portal_snapshot(lg):
    import random, portal
    rep=_active_portal_report(lg) or getattr(lg,'last_portal2',None) or getattr(lg,'last_portal',None)
    if rep is None:return {'active':False,'message':'The transfer portal opens during the offseason.','rows':[]}
    active=rep is _active_portal_report(lg); u=_portal_user(lg,rep,active) if active else None
    rows=[]
    for e in getattr(rep,'entries',[]):
        scored=[]
        for tm in lg.teams:
            if tm is e.origin:continue
            rr=random.Random(f'portal-market:{lg.seed}:{lg.year}:{e.player.name}:{tm.school}');scored.append((portal.player_choice(lg,lg.recruiting,tm,e,rr),tm))
        scored.sort(key=lambda x:-x[0]);best=scored[0][0] if scored else 0;serious=sum(1 for x,_ in scored if x>=best*.90) if scored else 0
        heat='National frenzy' if serious>=8 else 'Heavy' if serious>=5 else 'Active' if serious>=3 else 'Light'
        interest=None
        if u and e in u.get('known',{}):
            x=min(1,u['known'][e]+u.get('interest',{}).get(e,0)*.5);interest='Very high' if x>=.85 else 'High' if x>=.65 else 'Medium' if x>=.4 else 'Low' if x>=.2 else 'Very low'
        rows.append({'name':e.player.name,'pos':e.position,'ovr':e.overall,'from':e.origin.school,'reason':e.reason,'heat':heat,'serious':serious,'top5':[tm.school for _,tm in scored[:5]],'destination':e.destination.school if e.destination else None,'interest':interest,'offered':bool(u and e in u.get('offers',set()))})
    msg='LIVE portal window — contact, pitch, visit and offer roster spots.' if active else 'Most recent transfer portal window.'
    return {'active':active,'message':msg,'hours':u.get('hours',0) if u else 0,'offers':len(u.get('offers',set())) if u else 0,'rows':rows[:100]}

def classes_snapshot(lg):
    t=focus(lg); rc=lg.recruiting
    commits=list(rc.commitments(t))
    try: rank=rc.class_rank(t)
    except Exception: rank=None
    # Preserve visibility after signing day too.
    if not commits:
        rep=getattr(lg,'last_recruiting',None)
        commits=list(getattr(rep,'classes',{}).get(t,[]) or []) if rep else []
    transfers=[]; seen=set()
    for rep in (getattr(lg,'last_portal',None),getattr(lg,'last_portal2',None)):
        if not rep: continue
        for e in getattr(rep,'by_team_in',{}).get(t,[]) or []:
            if e.player.name in seen: continue
            seen.add(e.player.name); transfers.append({'name':e.player.name,'pos':e.position,'ovr':e.overall,'from':e.origin.school})
    return {'recruitRank':rank,'commits':[{'name':r.name,'pos':r.position,'stars':r.stars,'state':r.home_state} for r in commits],
            'transfers':sorted(transfers,key=lambda x:-x['ovr'])}

def program_snapshot(lg):
    import world_rules, poscoach
    t=focus(lg); rules=world_rules.normalize(getattr(lg,'world_rules',None)); staff=[]
    for role,attr in [('Offensive coordinator','oc'),('Defensive coordinator','dc')]:
        c=getattr(t,attr,None); staff.append({'role':role,'name':getattr(c,'name','Open'),'ovr':getattr(c,'overall',None),'detail':'Coordinator'})
    try:
        poscoach.ensure(lg)
        for g,c in poscoach.staff_of(t).items():
            if c: staff.append({'role':poscoach.TITLE[g].title(),'name':c.name,'ovr':c.overall,'detail':f'DEV {c.dev} · REC {c.rec} · EVAL {c.eye}'})
    except Exception: pass
    try:
        import offseason_cal; st=offseason_cal._state(lg); w=int(st.get('week') or 0); off='Offseason not started' if not lg.season_complete and w==0 else (f'Offseason Week {w}: '+offseason_cal.BY_NUM.get(w,{}).get('label','') if w else ('Season complete — offseason pending' if lg.season_complete else 'Regular season'))
    except Exception: off='Regular season'
    return {'school':t.school,'coach':getattr(getattr(t,'coach',None),'name','—'),'offseason':off,'staff':staff,
            'rules':[{'key':k,'label':world_rules.LABELS[k][0],'help':world_rules.LABELS[k][1],'on':bool(rules[k])} for k in world_rules.DEFAULTS]}

def program_toggle(lg,key):
    import world_rules
    if key not in world_rules.DEFAULTS:return False,'Unknown universe rule.'
    rules=world_rules.normalize(getattr(lg,'world_rules',None)); rules[key]=not rules[key]; world_rules.install(lg,rules)
    return True,f"{world_rules.LABELS[key][0]} {'enabled' if rules[key] else 'disabled'}."

def _active_portal_report(lg):
    try:
        import offseason_cal
        rep=offseason_cal._CONTEXT.get('portal')
        if rep and any(e.destination is None for e in getattr(rep,'entries',[])): return rep
    except Exception: pass
    for rep in (getattr(lg,'last_portal2',None),getattr(lg,'last_portal',None)):
        if rep and getattr(rep,'weekly',False) and any(e.destination is None for e in getattr(rep,'entries',[])): return rep
    return None

def _portal_user(lg,rep,create=False):
    t=focus(lg); users=rep.__dict__.setdefault('users',[]); u=next((x for x in users if x.get('team') is t),None)
    if u is None and create:
        try:
            import offseason_cal; ow=int(offseason_cal._state(lg).get('week') or 0)
        except Exception: ow=0
        u={'team':t,'offers':set(),'interest':{},'known':{},'visited':set(),'hours':lg.recruiting.hours_for(t)*2,'kept':[],'lost_keep':[],'portal_week':ow,'pitched_week':{}}; users.append(u); rep.user=u
    return u

def portal_action(lg,name,action):
    import portal_screens
    rep=_active_portal_report(lg)
    if rep is None:return False,'No live portal window is active.'
    u=_portal_user(lg,rep,True); e=next((x for x in rep.entries if x.player.name==name and x.destination is None),None)
    if e is None:return False,'That transfer is no longer available.'
    if action=='offer':
        if e in u['offers']:u['offers'].discard(e);rep.nil.pop((focus(lg),e),None);return True,'Roster offer withdrawn.'
        if len(u['offers'])>=8:return False,'You already have the maximum 8 portal offers out.'
        u['offers'].add(e);return True,'Roster spot offered.'
    cost=portal_screens.COST.get(action)
    if cost is None:return False,'Unknown portal action.'
    if action=='contact' and e in u['known']:return False,'Contact is already established.'
    if action in ('pitch','visit') and e not in u['known']:return False,'Establish contact first.'
    if action=='pitch' and u.setdefault('pitched_week',{}).get(e)==u.get('portal_week'):return False,'You already made your full pitch this portal week.'
    if action=='visit' and e in u['visited']:return False,'He has already visited campus.'
    if u['hours']<cost:return False,'Not enough portal hours left.'
    u['hours']-=cost
    if action=='contact':u['known'][e]=__import__('portal').base_interest(lg,focus(lg),e)
    elif action=='pitch':u['interest'][e]=min(1.0,u['interest'].get(e,0)+.12);u['pitched_week'][e]=u.get('portal_week')
    elif action=='visit':u['interest'][e]=min(1.0,u['interest'].get(e,0)+.28);u['visited'].add(e)
    return True,{'contact':'Contact established.','pitch':'Pitch delivered.','visit':'Official visit completed.'}[action]

def inbox_snapshot(lg):
    import people
    msgs=list(reversed(people.inbox(lg)))[:24]; out=[]
    for m in msgs:
        label=people.sender_label(m)
        ans=m.get('answered'); anslabel=next((lab for k,lab in m.get('replies',[]) if k==ans), ans) if ans else None
        out.append({'sender':label,'subject':m.get('subject','Message'),'body':m.get('body',''),'replies':[{'key':k,'label':lab} for k,lab in m.get('replies',[])], 'answered':anslabel})
    return {'unread':people.unread(lg),'waiting':len(people.waiting(lg)),'messages':out}

def inbox_answer(lg,index,key):
    import people
    msgs=list(reversed(people.inbox(lg)))[:24]
    if index<0 or index>=len(msgs): return False,'Message not found.'
    m=msgs[index]
    if m.get('answered') is not None:return False,'That message is already answered.'
    if key not in [k for k,_ in m.get('replies',[])]:return False,'Reply not available.'
    m['read']=True; return True,people.answer(lg,m,key)

def strategy_snapshot(lg):
    import sim_strategy
    s=sim_strategy.ensure(focus(lg)); labs=sim_strategy.LABELS
    defs=[('identity','Base identity',labs[s['identity']]),('first_down','1st down',labs[s['first_down']]),('second_short','2nd & short',labs[s['second_short']]),('second_long','2nd & long',labs[s['second_long']]),('third_short','3rd & short',labs[s['third_short']]),('third_long','3rd & long',labs[s['third_long']]),('red_zone','Red zone',labs[s['red_zone']]),('leading','Playing with lead',labs[s['leading']]),('trailing','Playing from behind',labs[s['trailing']]),('play_action','Play-action plan',s['play_action'].title()),('shots','Shot plays',s['shots'].title()),('screens','Screens',s['screens'].title()),('fourth','Fourth downs',s['fourth'].title()),('tempo','Tempo',s['tempo'].title())]
    return {'settings':[{'key':k,'label':l,'value':v} for k,l,v in defs]}

def strategy_cycle(lg,key):
    import sim_strategy
    s=sim_strategy.ensure(focus(lg)); numeric={'identity','first_down','second_short','second_long','third_short','third_long','red_zone','leading','trailing'}
    if key in numeric:s[key]=sim_strategy._cycle(s[key],[-2,-1,0,1,2])
    elif key=='play_action':s[key]=sim_strategy._cycle(s[key],['rare','balanced','setup','aggressive'])
    elif key=='shots':s[key]=sim_strategy._cycle(s[key],['conservative','balanced','aggressive'])
    elif key=='screens':s[key]=sim_strategy._cycle(s[key],['rare','balanced','aggressive'])
    elif key=='fourth':s[key]=sim_strategy._cycle(s[key],['conservative','coach','aggressive'])
    elif key=='tempo':s[key]=sim_strategy._cycle(s[key],['slow','normal','fast'])
    else:return False,'Unknown strategy setting.'
    return True,f"{key.replace('_',' ').title()} updated."

def settings_snapshot(lg):
    import settings, fieldview, week, difficulty, sideline
    s=settings.load(); coach=getattr(lg,'user_coach',None)
    def on(v): return 'ON' if bool(v) else 'OFF'
    routine=week.default_routine()
    import universe
    here=getattr(lg,'universe',None)
    groups=[
      {'title':'World','items':[
        {'key':'universe_source','label':'Universe for new careers','value':universe.title(s.get('universe',universe.DEFAULT)).replace(' (built-in)',''),'help':f"Teams, coaches, rivalries and names used when building a new world. This save: {universe.title(here) if here else 'current world'}."},
      ]},
      {'title':'Game Day','items':[
        {'key':'gameday','label':'Campus Countdown show','value':on(s.get('gameday',True)),'help':'Saturday-morning show before each week.'},
        {'key':'gameday_speed','label':'Campus Countdown speed','value':str(s.get('gameday_speed','fast')).title(),'help':'Instant, Fast, or Normal.'},
        {'key':'halftime','label':'Halftime adjustments','value':on(s.get('halftime',True)),'help':'Stop at halftime for a second-half plan when actively coaching.'},
        {'key':'field_view','label':'Game view','value':fieldview.MODE_WORDS.get(fieldview.mode(),fieldview.mode()),'help':'Tablet, field-only, slim, or off.'},
      ]},
      {'title':'Your Week · Coach Career','items':[
        {'key':'week_hub','label':'Week hub','value':on(s.get('week_hub',True)),'help':'Film, inbox, practice and presser before games.'},
        {'key':'routine_default','label':'Default routine','value':routine['name'] if routine else 'None','help':'Routine loaded by the week hub and sim weeks.'},
        {'key':'reply_hints','label':'Show what answers do','value':on(s.get('reply_hints',True)),'help':'Show upside/cost under replies and media answers.'},
        {'key':'weekly_wrap','label':'Weekly wrap','value':on(s.get('weekly_wrap',True)),'help':'Poll, hot seat, recruiting, injuries and storylines after games.'},
        {'key':'guided_week','label':'Guided first week','value':on(s.get('guided_week',True)),'help':'Staff explains the major screens for a new career.'},
        {'key':'difficulty','label':'Difficulty','value':difficulty.name(coach),'help':'Changes AD expectations, hot seat, recruiting pull and NIL — not on-field football.'},
      ]},
      {'title':'Presentation & Tools','items':[
        {'key':'faces','label':'Show faces','value':on(s.get('faces',True)),'help':'Portrait setting retained for console-compatible screens.'},
        {'key':'team_theme','label':'Team colors','value':on(s.get('team_theme',True)),'help':'Use program colors where supported.'},
        {'key':'auto_copy','label':'Console auto-copy','value':on(s.get('auto_copy',False)),'help':'Desktop/terminal compatibility. On iPhone use Copy Team Context above.'},
      ]},
    ]
    m=settings.moments()
    moments=[]
    for k,label,num in settings.MOMENT_LABELS:
        help='Trigger for Play the Big Moments.'
        if k=='crunch_time': help=f"Last {m['crunch_minutes']} min, within {m['crunch_margin']} points."
        elif k=='red_zone': help=f"Inside the {m['red_zone_yards']}."
        moments.append({'key':k,'label':label,'value':on(m[k]),'help':help})
    moments += [
      {'key':'crunch_minutes','label':'Crunch-time minutes','value':str(m['crunch_minutes']),'help':'Cycles 2, 4, 6, 8, 10 minutes.'},
      {'key':'crunch_margin','label':'Crunch-time margin','value':str(m['crunch_margin']),'help':'Cycles 3, 6, 8, 10, 14 points.'},
      {'key':'red_zone_yards','label':'Red-zone trigger','value':str(m['red_zone_yards']),'help':'Cycles inside the 5, 8, 10, 15, 20.'},
      {'key':'blowout_margin','label':'Blowout cutoff','value':str(m['blowout_margin']),'help':'Staff plays it out beyond this margin.'},
    ]
    side=[]
    for k,label,help in [('sideline_tablet','The tablet','Momentum, tendencies, coordinator and hot/cold info.'),('sideline_checkins','Series check-ins','Every series, notable only, or off.'),('sideline_people','The people','Trainer, quarterback and leadership moments.'),('sideline_calls','Situational calls','Tries, kickoffs, flags, challenges, icing and overtime.')]:
        v=s.get(k,sideline.DEFAULTS[k]); side.append({'key':k,'label':label,'value':str(v).title() if isinstance(v,str) else on(v),'help':help})
    cast=[{'key':k,'role':__import__('gameday_cast').CAST[k]['role'],'name':settings.cast_name(k)} for k in __import__('gameday_cast').ORDER]
    return {'groups':groups,'moments':moments,'sideline':side,'cast':cast,'showName':settings.show_name()}

def settings_cycle(lg,key,value=None):
    import settings, fieldview, week, difficulty, sideline
    s=settings.load(); coach=getattr(lg,'user_coach',None)
    if key=='universe_source':
        import universe
        vals=[universe.DEFAULT]+[n for n,_,_ in universe.list_files()]; cur=s.get('universe',universe.DEFAULT); s['universe']=vals[(vals.index(cur)+1)%len(vals)] if cur in vals else vals[0]
    elif key in ('gameday','halftime','week_hub','reply_hints','weekly_wrap','guided_week','faces','team_theme','auto_copy'):
        defaults={'gameday':True,'halftime':True,'week_hub':True,'reply_hints':True,'weekly_wrap':True,'guided_week':True,'faces':True,'team_theme':True,'auto_copy':False}
        s[key]=not s.get(key,defaults[key])
    elif key=='gameday_speed':
        order=list(settings.SPEEDS); cur=s.get(key,'fast'); s[key]=order[(order.index(cur)+1)%len(order)] if cur in order else 'fast'
    elif key=='field_view':
        order=list(fieldview.MODES); cur=fieldview.mode(); s[key]=order[(order.index(cur)+1)%len(order)]
    elif key=='routine_default':
        rows=[None]+[k for k,_ in week.routine_list()]; cur=s.get('routine_default'); i=rows.index(cur) if cur in rows else 0; nxt=rows[(i+1)%len(rows)]
        if nxt is None:s.pop('routine_default',None)
        else:s['routine_default']=nxt
    elif key=='difficulty':
        cur=difficulty.key_of(coach); i=difficulty.ORDER.index(cur); difficulty.set_level(lg,coach,difficulty.ORDER[(i+1)%len(difficulty.ORDER)])
    elif key.startswith('moment:'):
        k=key.split(':',1)[1]; store=s.setdefault('moments',{}); m=settings.moments()
        if k in {x[0] for x in settings.MOMENT_LABELS}: store[k]=not m[k]
        else:
            vals={'crunch_minutes':[2,4,6,8,10],'crunch_margin':[3,6,8,10,14],'red_zone_yards':[5,8,10,15,20],'blowout_margin':[14,18,22,28,35]}.get(k)
            if not vals:return False,'Unknown Big Moments setting.'
            cur=m[k]; store[k]=vals[(vals.index(cur)+1)%len(vals)] if cur in vals else vals[0]
    elif key.startswith('sideline:'):
        k=key.split(':',1)[1]; cur=s.get(k,sideline.DEFAULTS.get(k))
        if k=='sideline_checkins':
            vals=['every','notable','off']; s[k]=vals[(vals.index(cur)+1)%len(vals)] if cur in vals else 'notable'
        elif k in sideline.DEFAULTS:s[k]=not bool(cur)
        else:return False,'Unknown sideline setting.'
    elif key.startswith('castname:'):
        role=key.split(':',1)[1]
        if role not in __import__('gameday_cast').ORDER:return False,'Unknown cast member.'
        val=str(value or '').strip()[:50]
        names=s.setdefault('cast_names',{})
        if val:names[role]=val
        else:names.pop(role,None)
    elif key=='cast:alternate':
        s['cast_names']=dict(settings.FICTIONAL_CAST); s['show_name']=settings.FICTIONAL_SHOW
    elif key=='cast:reset':
        s['cast_names']={}; s.pop('show_name',None)
    else:return False,'Unknown setting.'
    settings.save(); return True,'Setting saved.'

def team_context_snapshot(lg):
    import team_context
    t=focus(lg); text=team_context.build(lg,t)
    return {'text':text,'lines':len(text.splitlines()),'team':t.school,'year':lg.year,'week':lg.week}

def _next_user_game(lg):
    t=focus(lg)
    for w in sorted(lg.schedule):
        for g in lg.schedule.get(w,[]):
            if t in (g.home,g.away) and not g.played:return g
    return None

def media_snapshot(lg):
    import presser
    g=_next_user_game(lg)
    if not g:return {'context':'No upcoming game is scheduled.','questions':[]}
    # Cache the procedural room so refreshing the phone does not reroll questions.
    key=(lg.year,lg.week,focus(lg).school)
    cache=lg.__dict__.setdefault('_mobile_media',{})
    if cache.get('key')!=key:
        qs,sit=presser.questions(lg,focus(lg),g,n=3); cache.clear();cache.update(key=key,qs=qs,answered=[])
    opp=g.opponent_of(focus(lg))
    out=[]
    for qi,(text,answers) in enumerate(cache['qs']):
        if qi in cache['answered']:continue
        out.append({'id':qi,'text':text,'answers':[{'tone':a[0].title(),'text':a[1]} for a in answers]})
    return {'context':f"Week {lg.week}: {focus(lg).school} vs {opp.school}",'questions':out}

def media_answer(lg,qidx,aidx):
    import podium
    g=_next_user_game(lg); cache=lg.__dict__.setdefault('_mobile_media',{})
    qs=cache.get('qs',[])
    # qidx from displayed list: map through unanswered originals
    available=[i for i in range(len(qs)) if i not in cache.get('answered',[])]
    if qidx<0 or qidx>=len(available):return False,'Question is no longer available.'
    real=available[qidx]; text,answers=qs[real]
    if aidx<0 or aidx>=len(answers):return False,'Answer not available.'
    tone,label,extra=answers[aidx]; t=focus(lg); opp=g.opponent_of(t) if g else None
    ctx={'league':lg,'team':t,'opp':opp,'qb':(t.players_at('QB') or [None])[0],'underdog':False,'won':None}
    bundle=podium.merge(podium.tone_fx(tone,'thu',ctx),podium.extra_fx(extra,ctx))
    import effects
    got=effects.apply(lg,bundle,'Thursday press conference') or []
    cache.setdefault('answered',[]).append(real)
    return True,(label+' '+(' '.join(got) if got else '')).strip()


def offseason_snapshot(lg):
    import offseason_cal
    st=offseason_cal._state(lg)
    done=set(st.get('completed_weeks',[]))
    cur=int(st.get('week') or (1 if lg.season_complete else 0))
    weeks=[{'n':w['n'],'label':w['label'],'blurb':w['blurb'],'done':w['n'] in done,'current':w['n']==cur and lg.season_complete} for w in offseason_cal.WEEKS]
    mobile=lg.__dict__.setdefault('_mobile_offseason',{})
    if not lg.season_complete:
        return {'status':'Regular season in progress','detail':'The offseason command center unlocks when the season is complete.','weeks':weeks,'canAdvance':False}
    if mobile.get('finished'):
        return {'status':'Offseason complete','detail':'The new season is ready. Return Home to begin preseason.','weeks':weeks,'canAdvance':False}
    step=int(mobile.get('step',0))
    labels=[('Close the season','File the completed season, process awards, graduation and player development.'),
            ('Winter portal','Open and resolve the winter transfer market. Use the Portal tab before continuing if you want to review the market.'),
            ('Signing & arrivals','Resolve the final recruiting push, National Signing Day and incoming class.'),
            ('Spring & summer','Process spring roster movement, post-spring portal, summer work and roll into the new season.')]
    title,help_=labels[min(step,len(labels)-1)]
    return {'status':f'Offseason · Step {step+1} of 4','detail':'Your save is checkpointed after every step. Recruiting, Classes, Portal and Program remain available between steps.','weeks':weeks,'canAdvance':True,'actionTitle':title,'actionHelp':help_,'actionLabel':'Complete '+title}

def offseason_advance(lg):
    if not lg.season_complete:return False,'The regular season is not complete yet.'
    import season, saves, offseason_cal
    m=lg.__dict__.setdefault('_mobile_offseason',{})
    step=int(m.get('step',0))
    ctx=m.get('ctx')
    old=getattr(lg,'autosim',False)
    lg.autosim=True
    try:
        if step==0:
            ctx=season.offseason_begin(lg); season.off_carousel(lg,lg.rng,ctx); season.off_awards(lg,lg.rng,ctx); season.off_winter(lg,lg.rng,ctx)
            m['ctx']=ctx; m['step']=1; offseason_cal._start(lg,ctx['report'].year); offseason_cal._state(lg)['week']=4
            msg='Season filed. Awards, graduation and winter development are complete; the winter portal is next.'
        elif step==1:
            # Resolve the winter market with the same engine. Mobile portal history remains available afterward.
            season.off_portal(lg,lg.rng,ctx); offseason_cal.portal_complete(lg,ctx['report'].portal); m['step']=2; offseason_cal._state(lg)['week']=7
            msg='Winter portal resolved. Review Portal and Classes, then make your final recruiting push.'
        elif step==2:
            season.off_signing(lg,lg.rng,ctx); season.off_arrivals(lg,lg.rng,ctx); m['step']=3; offseason_cal._state(lg)['week']=11
            msg='Signing Day and arrivals are complete. Your incoming class is on campus.'
        else:
            # The terminal spring agenda is not safe under WSGI; run the world rollover without terminal prompts.
            season.off_rollover(lg,lg.rng,ctx); lg.after_offseason(ctx['report'])
            st=offseason_cal._state(lg); st['completed_weeks']=list(range(1,18)); st['week']=17; st['finished']=True
            m.clear(); m['finished']=True; m['step']=4
            msg=f'Offseason complete. Welcome to {lg.year}.'
        quiet(saves.autosave,lg)
        return True,msg
    except Exception as e:
        return False,f'Offseason step stopped safely: {type(e).__name__}: {e}'
    finally:
        lg.autosim=old


def camp_snapshot(lg):
    import preseason, preseason_board
    t=focus(lg); pre=preseason.needed(lg)
    outlook=preseason_board.summary_lines(lg,t)
    rooms=[]
    for pos in ('QB','RB','WR','TE','OL','DL','LB','CB','S','K','P'):
        ps=t.players_at(pos)
        if not ps: continue
        lead=ps[0]; rooms.append({'pos':pos,'note':f'{lead.name} {lead.overall} OVR leads a {len(ps)}-player room'})
    red=[]
    for p in sorted(t.roster,key=lambda x:(x.year,-x.overall,x.name)):
        if p.year<=1 and not getattr(p,'redshirt',False):
            red.append({'name':p.name,'pos':p.position,'ovr':p.overall,'yr':p.class_label,'planned':p.__dict__.get('redshirt_plan')==lg.year})
    return {'status':'Fall camp is open.' if pre else 'Preseason is complete; this remains your camp archive.','outlook':outlook,'rooms':rooms,'redshirts':red}

def camp_toggle_redshirt(lg,name):
    t=focus(lg); p=next((x for x in t.roster if x.name==name),None)
    if not p:return False,'Player not found.'
    if getattr(p,'redshirt',False):return False,'He has already used a redshirt season.'
    if p.__dict__.get('redshirt_plan')==lg.year:
        p.__dict__.pop('redshirt_plan',None);return True,f'{p.name} returned to the active plan.'
    p.__dict__['redshirt_plan']=lg.year;return True,f'{p.name} added to the redshirt plan.'

def today_snapshot(lg):
    t=focus(lg); items=[]; d=summary(lg); n=d.get('next') or {}
    items.append({'title':'Next opponent','detail':(('%s %s %s' % (n.get('site',''),n.get('opp',''),n.get('oppRecord',''))).strip() if n else 'No game scheduled'),'status':lg.week_name(lg.week) if lg.week else 'Preseason'})
    try:
        cyc=lg.recruiting; targets=getattr(cyc,'targets',{}).get(t.school,[])
        items.append({'title':'Recruiting','detail':f'{len(targets)} targets on your board','status':'OPEN'})
    except Exception: pass
    try:
        ib=inbox_snapshot(lg); pending=sum(1 for x in ib.get('items',[]) if x.get('choices'))
        items.append({'title':'Inbox & decisions','detail':f'{pending} unresolved decision' + ('s' if pending != 1 else ''),'status':'ACTION' if pending else 'CLEAR'})
    except Exception: pass
    hurt=[p for p in t.roster if getattr(p,'inj_games',0)>0]
    items.append({'title':'Medical','detail':f'{len(hurt)} injured player' + ('s' if len(hurt)!=1 else ''),'status':'CHECK' if hurt else 'CLEAR'})
    if getattr(lg,'season_complete',False): items.append({'title':'Offseason','detail':'Season complete — offseason management is ready.','status':'READY'})
    return {'items':items}

def player_snapshot(lg,pid):
    t=focus(lg); p=next((x for x in t.roster if str(id(x))==str(pid)),None)
    if not p: return {'text':'Player not found.'}
    stats=', '.join(f'{k}: {v}' for k,v in sorted(getattr(p,'season_stats',{}).items()) if v) or 'No season stats yet'
    ev=[]
    for y,rows in sorted(getattr(p,'events',{}).items()): ev += [f'{y}: {x}' for x in rows[-3:]]
    traits=', '.join(getattr(p,'traits',[]) or []) or 'None'
    lines=[f'{p.name}  #{p.number}  {p.position}',f'{p.class_label} · {p.height_str} · {p.weight} lbs',f'OVR {p.overall} · EXP {getattr(p,"experience",0)} · HS {getattr(p,"hs_stars",0)}★',f'Games: {getattr(p,"games_played",0)} this year / {getattr(p,"career_games",0)} career',f'NIL: ${getattr(p,"nil",0):,} · Home: {getattr(p,"home_state",None) or "—"}',f'Status: {getattr(p,"inj_desc",None) or "Healthy"}',f'Traits: {traits}','',f'Season stats: {stats}','','History:']
    lines += ev[-8:] if ev else ['No major events recorded yet.']
    return {'text':'\n'.join(lines)}

def hq_snapshot(lg):
    t=focus(lg); sections=[]
    # Program finances / NIL
    try:
        import finance as fi
        b=fi.budget(t); avail=fi.available(lg,t); nil=fi.roster_nil(t)
        sections.append({'title':'Budget & NIL','lines':[f'Annual budget: {fi.money(b, exact=True)}',f'Roster NIL: {fi.money(nil, exact=True)}',f'Available for recruiting/NIL: {fi.money(avail, exact=True)}',f'National budget rank: #{fi.budget_rank(lg,t)}']})
    except Exception as e: sections.append({'title':'Budget & NIL','lines':['Financial office unavailable: '+str(e)]})
    # Compliance
    try:
        import compliance
        cs=compliance.cases(lg,t.school,open_only=False)
        lines=[f"#{getattr(c,'cid','?')} {getattr(c,'kind','Case')} · {getattr(c,'status','open')}" for c in cs[-8:]]
        sections.append({'title':'Compliance & Violations','lines':lines or ['No program cases on file.']})
    except Exception: sections.append({'title':'Compliance & Violations','lines':['No program cases on file.']})
    # Awards
    aw=getattr(lg,'awards',{})
    lines=[]
    if aw:
        y=max(aw); a=aw[y]; h=a.get('heisman')
        if h: lines.append(f'{y} Heisman: {h[0].name} — {h[1].school}')
        if a.get('coach'): lines.append(f"{y} Coach of the Year: {a['coach'][0]} — {a['coach'][1].school}")
        mine=[f'{name}: {p.name}' for name,p,tm,_ in a.get('positional',[]) if tm is t]
        lines.extend(mine[:8])
    sections.append({'title':'Awards','lines':lines or ['No awards have been handed out yet.']})
    # Draft
    drafts=getattr(lg,'drafts',{}); lines=[]
    if drafts:
        y=max(drafts); mine=[x for x in drafts[y] if x.get('school')==t.school]
        lines=[f"{y} R{x['round']} #{x['overall_pick']} · {x['name']} {x['pos']} → {x['nfl']}" for x in mine]
    sections.append({'title':'NFL Draft','lines':lines or ['No players from your program in the latest draft.']})
    # Records
    try:
        import records
        tops=records.career_tops(lg,3); lines=[]
        for key,rows in tops.items() if isinstance(tops,dict) else []:
            for row in rows[:1]: lines.append(f'{records.LABEL.get(key,key)}: {row}')
        sections.append({'title':'Record Book','lines':lines[:12] or ['Records are tracked from 2026 onward.']})
    except Exception: sections.append({'title':'Record Book','lines':['Records are tracked from 2026 onward.']})
    # Career/history and facilities summary
    hist=getattr(getattr(lg,'user_coach',None),'history',[]) or []
    sections.append({'title':'Coach Career','lines':[str(x) for x in hist[-10:]] or [f'{getattr(lg.user_coach,"name","Coach")} · {t.school}']})
    fac=[]
    for k,v in sorted(t.__dict__.items()):
        if any(w in k.lower() for w in ('facility','stadium')) and isinstance(v,(str,int,float,bool)): fac.append(f'{k.replace("_"," ").title()}: {v}')
    sections.append({'title':'Facilities & Stadium','lines':fac[:10] or ['Program facilities are managed by the existing world simulation.']})
    return {'sections':sections}



def directory_snapshot(lg):
    rows=[]
    for tm in getattr(lg,'teams',[]):
        for p in getattr(tm,'roster',[]) or []:
            rows.append({'id':str(getattr(p,'pid',getattr(p,'id',getattr(p,'name','')))),'name':getattr(p,'name','Player'),'pos':getattr(p,'pos','?'),'ovr':int(getattr(p,'ovr',getattr(p,'overall',0)) or 0),'exp':int(getattr(p,'exp',50) or 50),'cls':str(getattr(p,'year',getattr(p,'class_year',''))),'state':str(getattr(p,'state',getattr(p,'home_state',''))),'team':tm.school})
    rows.sort(key=lambda x:(-x['ovr'],x['name']))
    return {'players':rows}

def scout_snapshot(lg):
    t=focus(lg); g=_next_user_game(lg)
    if not g:return {'matchup':'No opponent scheduled','summary':'Use this screen once a matchup is on the schedule.','sections':[]}
    o=g.opponent_of(t); hist=[]
    for gm in getattr(lg,'games',[]) or []:
        try:
            if gm.played and t in (gm.home,gm.away) and o in (gm.home,gm.away): hist.append(f"{getattr(gm,'week','?')}: {t.school} {gm.score_for(t)} — {o.school} {gm.score_for(o)}")
        except: pass
    orost=sorted(getattr(o,'roster',[]) or [],key=lambda p:getattr(p,'ovr',getattr(p,'overall',0)),reverse=True)[:8]
    stars=[f"{p.name} {getattr(p,'pos','?')} · {getattr(p,'ovr',getattr(p,'overall','?'))} OVR · {getattr(p,'exp',50)} EXP" for p in orost]
    return {'matchup':f'{t.school} vs {o.school}','summary':f"{getattr(o,'record',lambda:'')() if callable(getattr(o,'record',None)) else getattr(o,'record','')} · {getattr(o,'conference','')}", 'sections':[{'title':'Players to Know','lines':stars or ['No roster data.']},{'title':'Matchup History','lines':hist[-8:] or ['No prior meetings in this career.']}]}

def national_snapshot(lg):
    games=[]
    for g in getattr(lg,'games',[]) or []:
        try:
            if getattr(g,'week',None)!=getattr(lg,'week',None):continue
            if getattr(g,'played',False): games.append(f"{g.away.school} {g.score_for(g.away)} — {g.home.school} {g.score_for(g.home)}")
            else: games.append(f"{g.away.school} at {g.home.school}")
        except: pass
    return {'week':lg.week_name(lg.week) if getattr(lg,'week',None) is not None else 'Season','games':games[:80]}

def leaders_snapshot(lg):
    t=focus(lg); roster=getattr(t,'roster',[]) or []
    def top(attr,label):
        rr=sorted(roster,key=lambda p:getattr(p,attr,0) or 0,reverse=True)[:5]
        return {'title':label,'lines':[f"{p.name} {getattr(p,'pos','')} · {getattr(p,attr,0)}" for p in rr if getattr(p,attr,0)] or ['No stats recorded yet.']}
    # common stat names across engine versions
    sections=[]
    for a,l in [('pass_yards','Passing yards'),('rush_yards','Rushing yards'),('rec_yards','Receiving yards'),('tackles','Tackles'),('sacks','Sacks'),('interceptions','Interceptions')]: sections.append(top(a,l))
    return {'sections':sections}

def activity_snapshot(lg):
    t=focus(lg); items=[]
    # Pull durable player/career events first; tolerate older saves with missing fields.
    for p in getattr(t,'roster',[]) or []:
        for e in (getattr(p,'history',None) or getattr(p,'career_events',None) or []): items.append(f'{p.name}: {e}')
        inj=getattr(p,'injury',None)
        if inj: items.append(f'{p.name}: injury — {inj}')
    for a in getattr(lg,'news',[]) or []:
        txt=str(a)
        if t.school.lower() in txt.lower(): items.append(txt)
    return {'items':items[-80:][::-1]}

# ── True mobile Game Day bridge ─────────────────────────────────────────
import queue, time, re, builtins, sys
_game_bridge=None
_ansi_re=re.compile(r'\x1b\[[0-9;]*m')

class _Capture:
    def __init__(self, bridge): self.bridge=bridge
    def write(self, x):
        if x:
            clean=_ansi_re.sub('',str(x)).replace('\r','')
            with self.bridge.guard:
                self.bridge.output += clean
                if len(self.bridge.output)>18000:self.bridge.output=self.bridge.output[-18000:]
        return len(x or '')
    def flush(self): pass

class MobileGameBridge:
    def __init__(self, lg):
        self.lg=lg; self.answers=queue.Queue(); self.prompt=None; self.output=''; self.sim=None
        self.game=None; self.done=False; self.error=None; self.final=''; self.guard=threading.RLock(); self.thread=None
    def input(self,prompt=''):
        with self.guard:self.prompt=_ansi_re.sub('',str(prompt)).strip() or 'Your choice:'
        ans=self.answers.get()
        with self.guard:self.prompt=None
        return ans
    def start(self):
        self.thread=threading.Thread(target=self._run,daemon=True); self.thread.start()
    def _run(self):
        global _game_bridge
        old_input=builtins.input; old_out=sys.stdout
        try:
            builtins.input=self.input; sys.stdout=_Capture(self)
            import preseason, week, gameday_show, coach_mode, saves
            lg=self.lg
            if lg.season_complete: raise RuntimeError('The season is complete. Use Offseason.')
            old_auto=getattr(lg,'autosim',False); lg.autosim=True
            if preseason.needed(lg): preseason.mark_done(lg)
            week.auto_week(lg)
            games=lg.start_week(); gameday_show.quiet_show(lg,games)
            t=focus(lg); mine=next((g for g in games if t in (g.home,g.away)),None)
            if mine is None:
                for g in games: lg.play_game(g)
                lg.finish_week(games); saves.autosave(lg); self.final=f'No {t.school} game this week.'; self.done=True; return
            self.game=mine
            # Your kickoff comes first on mobile; the national slate resolves after your final.
            lg.autosim=False
            mine.halftime_team=t
            mine.controller=coach_mode.setup_for_game(lg,mine,mode='full',call_defense=None)
            # Hook the live GameSim instance so Safari can show true clock/down/score state.
            import game_sim
            orig_init=game_sim.GameSim.__init__
            bridge=self
            def hooked(obj,*a,**kw):
                orig_init(obj,*a,**kw); bridge.sim=obj
            game_sim.GameSim.__init__=hooked
            try: lg.play_game(mine)
            finally:
                game_sim.GameSim.__init__=orig_init; mine.controller=None; mine.__dict__.pop('halftime_team',None)
            lg.autosim=True
            for g in games:
                if g is not mine: lg.play_game(g)
            lg.autosim=False; lg.finish_week(games); lg.autosim=True; saves.autosave(lg)
            o=mine.opponent_of(t); self.final=f"{'W' if mine.winner is t else 'L'} {mine.score_for(t)}-{mine.score_for(o)} vs {o.school}"
            self.done=True
        except Exception as e:
            self.error=f'{type(e).__name__}: {e}'; self.done=True
        finally:
            builtins.input=old_input; sys.stdout=old_out
            try: self.lg.autosim=False
            except: pass

    def snapshot(self):
        with self.guard:
            g=self.game; sim=self.sim; out=self.output
            # Last console screen is the useful part; collapse excessive blank lines.
            lines=out.splitlines()[-70:]; log='\n'.join(lines)
            data={'status':'Game in progress' if not self.done else 'Complete','prompt':self.prompt,'log':log,'done':self.done,'error':self.error,'final':self.final,'canStart':False}
            if g:
                t=focus(self.lg); o=g.opponent_of(t); data['matchup']=f'{t.school} vs {o.school}'
            if sim:
                t=focus(self.lg); o=sim.other(t); q=f'Q{sim.quarter}' if sim.quarter<=4 else f'OT{sim.quarter-4}'
                data['score']=f'{t.school} {sim.score[t]} — {sim.score[o]} {o.school}'
                if sim.quarter<=4:
                    mm,ss=divmod(max(0,int(sim.clock)),60); down={1:'1st',2:'2nd',3:'3rd',4:'4th'}.get(sim.down,'')
                    poss='Ball' if sim.offense is t else 'Defense'
                    data['situation']=f'{q} {mm}:{ss:02d} · {poss} · {down} & {sim.togo} · ball at {sim.yardline}'
            return data

def gameday_snapshot(lg):
    global _game_bridge
    if _game_bridge and _game_bridge.lg is lg:
        return _game_bridge.snapshot()
    if lg.season_complete:return {'status':'Season complete','canStart':False,'done':False,'matchup':'Use the Offseason hub.'}
    # Before start, show the next scheduled user matchup without advancing the week.
    t=focus(lg); nxt=None
    for wk in sorted(lg.schedule):
        if wk>lg.week:
            nxt=next((g for g in lg.schedule[wk] if t in (g.home,g.away)),None)
            if nxt:break
    if nxt:
        o=nxt.opponent_of(t); return {'status':'Ready','canStart':True,'done':False,'matchup':f'{t.school} vs {o.school}','situation':f'Next: {lg.week_name(lg.week+1)}'}
    return {'status':'No game available','canStart':False,'done':False,'matchup':'No upcoming matchup.'}

def gameday_start(lg):
    global _game_bridge
    if _game_bridge and not _game_bridge.done:return _game_bridge.snapshot()
    _game_bridge=MobileGameBridge(lg); _game_bridge.start()
    for _ in range(100):
        if _game_bridge.prompt or _game_bridge.sim or _game_bridge.done:break
        time.sleep(.02)
    return _game_bridge.snapshot()

def gameday_answer(lg,answer):
    global _game_bridge
    if not _game_bridge or _game_bridge.lg is not lg:return {'error':'No Game Day session is running.'}
    if _game_bridge.done:return _game_bridge.snapshot()
    if _game_bridge.prompt is None:return _game_bridge.snapshot()
    _game_bridge.answers.put(str(answer or ''))
    for _ in range(100):
        time.sleep(.02)
        if _game_bridge.prompt is not None or _game_bridge.done:break
    return _game_bridge.snapshot()

def run(host='0.0.0.0',port=None):
    port=int(port or os.environ.get('PORT','8000')); print(f'Console College Mobile: http://localhost:{port}',flush=True); ThreadingHTTPServer((host,port),H).serve_forever()
if __name__=='__main__': run()

# PythonAnywhere / generic WSGI adapter.
def application(environ, start_response):
    global _league
    path=environ.get('PATH_INFO') or '/'; method=(environ.get('REQUEST_METHOD') or 'GET').upper()
    def respond(obj=None,status='200 OK',ctype='application/json; charset=utf-8',raw=None):
        if raw is None: raw=json.dumps(obj,default=str).encode()
        elif isinstance(raw,str): raw=raw.encode()
        start_response(status,[('Content-Type',ctype),('Cache-Control','no-store'),('Content-Length',str(len(raw)))])
        return [raw]
    def body():
        try:
            n=int(environ.get('CONTENT_LENGTH') or 0); return json.loads(environ['wsgi.input'].read(n) if n else b'{}')
        except:return {}
    try:
        if method=='GET' and path=='/': return respond(raw=INDEX,ctype='text/html; charset=utf-8')
        with _lock:
            if method=='GET' and path=='/api/state': return respond({'state':summary(_league) if _league else None})
            if method=='GET' and path=='/api/gameday': return respond(gameday_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/today': return respond(today_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/directory': return respond(directory_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/scout': return respond(scout_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/national': return respond(national_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/leaders': return respond(leaders_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/activity': return respond(activity_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/player':
                from urllib.parse import parse_qs
                pid=(parse_qs(environ.get('QUERY_STRING','')).get('id') or [''])[0]
                return respond(player_snapshot(_league,pid)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/setup':
                if _league: teams=sorted(t.school for t in _league.teams)
                else:
                    from teams_data import TEAMS; teams=sorted(r[0] for r in TEAMS)
                return respond({'teams':teams,'saves':saves_list()})
            if method=='GET' and path=='/api/recruiting': return respond(recruiting_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/depth': return respond(depth_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/portal': return respond(portal_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/inbox': return respond(inbox_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/media': return respond(media_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/strategy': return respond(strategy_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/classes': return respond(classes_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/program': return respond(program_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/offseason': return respond(offseason_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/camp': return respond(camp_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/hq': return respond(hq_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/settings': return respond(settings_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='GET' and path=='/api/team-context': return respond(team_context_snapshot(_league)) if _league else respond({'error':'No career loaded'},'400 Bad Request')
            if method=='POST':
                d=body()
                if path=='/api/new': _league=quick_career(d.get('name'),d.get('school'),d.get('preset','balanced')); return respond({'state':summary(_league)})
                if path=='/api/load':
                    import saves; rows=saves.list_saves(); _league=quiet(saves.load,rows[int(d.get('index',0))]['path']); return respond({'state':summary(_league)})
                if not _league:return respond({'error':'No career loaded'},'400 Bad Request')
                if path=='/api/gameday/start': return respond(gameday_start(_league))
                if path=='/api/gameday/answer': return respond(gameday_answer(_league,d.get('answer','')))
                if path=='/api/recruit':
                    ok,msg=recruit_action(_league,d.get('rank'),d.get('action')); return respond({'ok':ok,'message':msg,'data':recruiting_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/depth':
                    ok,msg=depth_move(_league,d.get('pos'),d.get('name'),d.get('direction')); return respond({'ok':ok,'message':msg,'data':depth_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/inbox':
                    ok,msg=inbox_answer(_league,int(d.get('index',-1)),d.get('key')); return respond({'message':msg,'data':inbox_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/media':
                    ok,msg=media_answer(_league,int(d.get('question',-1)),int(d.get('answer',-1))); return respond({'message':msg,'data':media_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/strategy':
                    ok,msg=strategy_cycle(_league,d.get('key')); return respond({'message':msg,'data':strategy_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/program':
                    ok,msg=program_toggle(_league,d.get('key')); return respond({'message':msg,'data':program_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/portal':
                    ok,msg=portal_action(_league,d.get('name'),d.get('action')); return respond({'message':msg,**portal_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/offseason':
                    ok,msg=offseason_advance(_league); return respond({'message':msg,'data':offseason_snapshot(_league),'state':summary(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/camp':
                    ok,msg=camp_toggle_redshirt(_league,d.get('name')); return respond({'message':msg,'data':camp_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/settings':
                    ok,msg=settings_cycle(_league,d.get('key'),d.get('value')); return respond({'message':msg,'data':settings_snapshot(_league)},'200 OK' if ok else '400 Bad Request')
                if path=='/api/sim': return respond({'message':sim_week(_league),'state':summary(_league)})
                if path=='/api/save':
                    import saves; quiet(saves.save,_league,saves.AUTOSAVE); return respond({'ok':True})
                if path=='/api/close': _league=None; return respond({'ok':True})
        return respond({'error':'Not found'},'404 Not Found')
    except Exception as e:return respond({'error':f'{type(e).__name__}: {e}'},'500 Internal Server Error')
