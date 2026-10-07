> Current build: **v51.15 — In-season roster management: retention conversations with tracked role promises, saved formation/play substitutions available outside games and on the sideline, and preseason redshirt protection under the four-game rule; v51.14 — Team Podcast story kits now include a full selected-program dossier (roster, complete staff, AD/goals, schedule/results, expectations, injuries, production, NIL and recruiting context); v51.13 — Curate Stories stays open after each copied prompt so you can generate multiple kits before explicitly backing out; v51.12 — Curate Stories can include coaching-staff reference at four depths (off, head coaches, coordinators, or full position staff); Online imported game boxes now expose the normal opponent helper used by records/classics, fixing the postgame host worker crash; v51.10 — Window prompts stay in the main game screen instead of being clipped into the input bar; v51.9 — Online authoritative client games: connected coaches play once and the host imports their score/box score/state; v51.8 — Online multiplayer polish; v51.7: synchronized offseason**

# Console College

Immersion-first college football simulation that runs in the terminal.

## Run
The full manual is in **MANUAL.txt**, and in the game: press **[?]** on the dashboard (or tab 8 SYSTEM → [H]).

    python main.py

Python 3.8+, no external packages. Works in Windows Terminal, macOS Terminal, and Linux terminals
(ANSI colors are enabled automatically on Windows 10+). Best in a window at least **100 columns wide**
with 256 colors; anything wider than the screen folds onto the next line instead of running off it.

## Play in a window  (play.py)
Double-click **play.bat** (Windows) or **play.command** (Mac/Linux), or run `python play.py`.
The first time, it offers to install one small package (`pywebview`) that gives the game its own window.
Say no, or run `python play.py --browser`, and it opens in your web browser instead. `python main.py` still
runs it in the terminal. It's the same game and the same saves either way.
- **Click instead of type.** Every `[R]`-style key on screen is a button, and the dashboard tabs are clickable. Typing still works everywhere,
  and the up arrow brings back what you typed last.
- **Almost every name is a link.** Players, teams (including "ALABAMA" in a header and names cut short to fit, like
  "South Carol…"), head coaches and coordinators, conferences, stadiums, rivalries and trophies, recruits, and this
  season's bowls — on any screen, in the sidebar, and inside the cards themselves. A click opens its page in a card
  over the screen you're on: click another name in the card to keep going, **◀ Back** (Backspace) to return, Esc to
  close. The sidebar also has your whole roster with a search box.
- **Sidebar:** your season at a glance, always live, in your conference's colors.
  - **Up top:** rank, record, streak, the last five results, season progress, points per game, and a
    "your move / working" light.
  - **Home:** the next game (a win-chance dial — an outlook dial in Coach Career — kickoff, stadium, how loud
    it is, the rivalry and the series), your last result, one-click **shortcuts** (play the next week, save,
    inbox, depth chart, practice, recruiting, standings, the poll, facilities and more — they run from the
    dashboard), the coach card (hot seat and why it moved, contract, goals) and an inbox preview. AD mode shows
    your board, fans and boosters.
  - **Games:** your poll rank week by week, points for and against, and the whole schedule with results.
  - **League:** conference standings, the Media Top 25 with movement, the NP rankings, the Golden Helmet watch and the
    toughest places to play.
  - **Team:** the starting lineup (who's filling in for whom), the injury report, team leaders, the program
    (facilities, stadium, fund) and the recruiting class — plus the searchable roster with position filters.
  - **News:** this week's national scoreboard (upsets marked), headlines, the hot seat watch, the recruiting wire
    and your own story.
  - Pop-up notes for wins, losses, poll moves and new mail. Click any player name for his card. Click a card's
    title to fold it; drag the sidebar's left edge to resize; Alt+1-5 switches tabs. It all remembers your
    choices. The menu button hides the sidebar.
- **Earlier screens:** the arrow buttons look back at the last 40 screens (Alt+Left / Alt+Right). Scroll back
  through a long broadcast with the mouse or Page Up.
- **A- / A+** (Ctrl - / Ctrl +) text size; the screen fits itself to the window. Light/dark theme. Sounds (a
  touchdown chime and an inbox ping). **Copy screen** puts the screen's text on the clipboard.
- It runs on your computer only (a local page at 127.0.0.1; nothing goes online). Save with [V] or quit with
  [Q] before closing the window. Closing it mid-week loses whatever happened since the last autosave.

## Multiplayer
Hot Seat (several coaches on one screen) and its LAN version were removed in v51. Hot Seat saves still load,
as a normal Coach Career with the coach who was on the keyboard. Multiplayer leagues run through Commissioner
Mode (Discord) for now; an online mode where everyone runs their own copy of one shared world is in the works.

## What's new in v29
- **An original universe.** Every program has its own nickname, stadium, chant and head coach; conferences,
  rivalries, trophies, bowls, the pregame show and its crew, the top award and the media poll all have original
  names. States, towns, stadium sizes and the shape of the sport are unchanged.
- **Universe files.** `universes/*.json` can replace any of it. Settings **[U]** picks the universe new worlds
  use, and every save remembers its own. **[X]** exports the universe in use as an editable template. Manual
  chapter 33.
- **Almost every name in the window is a link** — players, teams, coaches, conferences, stadiums, rivalries,
  recruits, bowls — opening its page in a card you can click through.

## What's new in v25
- **The record book.** Every record from 2026 on, national and school by school: single game, season and
  career, team records and winning streaks, coaches. Records make the headlines. Rankings tab **[R]**.
- **The Hall of Fame.** A national Hall voted by a panel of 20 writers with their own leans (75% gets in),
  with a ceremony, every ballot and each candidate's case, and a Hall for every program. You pick your
  school's class each offseason. Rankings tab **[F]**.
- **Custom programs.** Team files (JSON, rosters included) and an in-game team builder that edits
  everything the game keeps about a program. Add or swap programs in a new world, or edit, export and
  load them in a save. Team page **[J]**; example in `custom_teams/`.
- **A guided first week.** Your staff walks you through each screen the first time you open it. Settings **[G]**.

## What's new in v24
- **Talent wins.** The preseason ratings finally show up on Saturday: the rosters you inherit match their programs'
  ratings, a hidden coach "fit" and game-day luck no longer swing games by a touchdown, and the option has to beat
  somebody to gain yards. Top teams win more, G5 upsets of P4 teams are rarer, and blowouts and margins are closer
  to real college football. Details in CHANGES.md.

## What's new in v23
- **The game on a tablet.** Before every snap of a game you watch or coach: a scoreboard with big score digits, the text
  field in the middle with the ball on it, the play-by-play down the side (newest first), score by quarter, this drive,
  your coach's clipboard (or top performers and scoring when you watch), and team stats along the bottom. Wide (124
  columns) or compact (100); Settings **[F]** picks it (auto by default), or field-only, slim, or the old ticker. Manual 8.13.

## What's new in v22
- **A field made of text.** Before every snap of a game you watch or coach, a football field is drawn with the ball
  on it: yard lines, the line of scrimmage, the first-down marker, the drive so far, and the end zone you're attacking.
  Settings **[F]**: Full / Slim / Off. Manual 8.13.

## What's new in v21
- **Compliance & Integrity** (tab 3, 6 or 7 -> **[Y]**; in AD mode, **[Y]** in your office): every program can bend a
  rule, and the CAB is watching from 2026. Violations start hidden, then a report, an inquiry, a Notice of Allegations
  and a ruling (Level I / II / III). Cooperation, self-reporting, counsel and self-imposed penalties shrink the
  penalty; stonewalling and cover-ups grow it. Penalties: fines, probation, postseason bans, scholarship cuts
  (a smaller signing class), recruiting and NIL limits, vacated wins, players held out, a head-coach suspension
  and heat on the seat. Random sanctions are gone: they now come out of real cases.
- **Temptations and decisions** in your inbox (Coach Career) or on your desk (AD mode): a booster, a dead-period
  text, a collective's "appearance" deal, a rival's unhappy starter. The shortcut works, and the bill may come later.
- **Academics:** every player has a GPA (in words), midterms and finals decide eligibility, and each team has an
  APR (930 is the line; two years below it is a postseason ban). Choose your academic support and compliance office budgets.
- **Off the field:** arrests, DUIs, failed tests, conduct cases, viral posts and wagering, on every roster.
- **Integrity** is a program's reputation for a clean shop, worth up to about two points of recruiting pull.
- Sheets export gains a Compliance tab; player cards show a Classroom line; Manual Chapter 29.

## What's new in v20
- **Export to Sheets** (tab 8 SYSTEM → **[E]**): the whole league in one formatted workbook — teams, rankings,
  schedules and every game, full rosters with every player rating and position fit, stats, rating history, coaches,
  the full recruit database, every recruiting board, class rankings, and your own weekly decisions and recruiting
  actions. Opens in Excel, Numbers, LibreOffice and Google Sheets. Needs `openpyxl` (the screen offers to install it).

## What's new in v19
- **A main menu** (Continue, New Game, Load, Settings, Manual, About, Quit), mode cards before the world is
  built, and a leave menu on [Q].
- **One look everywhere** — headers, keys, tabs, footers — and **[B] goes back on every screen**.
- Rebuilt settings, save/load (with delete), the new-career steps and job offers; wide tables fit 100 columns.

## What's new in v18
- **Routines:** the week hub sets practice focus, game plan and scripted openers in one key ([1]-[5] built in,
  your own with [Y]); a default routine loads itself, and sim weeks use it.
- **The week's work:** after every game, each decision of the week credited in form and in points.
- **A fair process grade:** every headset call priced in win chance (score, clock, kicker, matchup), not in
  agreement with the chart; the log shows what your judgment added over simply following it.
- **Difficulty:** Freshman · Varsity · All-American · Golden Helmet (Coach Career), changeable any time.
See CHANGES.md for the details.

## Saving and loading
Your world is saved to the `saves/` folder next to the game.

- **Autosave** — written whenever the calendar moves (every week, the offseason, a new job), right
  after you choose how to play, and when you quit.
- **[V]** on any dashboard tab saves under any name you like; **tab 8 SYSTEM → [L]** loads any save
  (and **[X#]** deletes one).
- **The main menu** (every launch): Continue (your latest save), New Game, Load Game, Settings, Manual,
  About, Quit. **[Q]** on the dashboard takes you back to it, or quits — saving either way.

Saves are written to a temp file first, so a crash mid-save never wipes the last good one. A save keeps
every finished game's box score but not the broadcast itself. Saves are Python pickles — only load
files you made yourself.

## Season flow
Main menu → [3] Advance Week walks you through that week's games, biggest matchups first.
The regular season is 13 weeks and every team plays exactly 12 games with one bye. For each game:

- **[C] Commentary** – watch it live with a two-person broadcast booth calling the game in natural
  language. Choose a speed (Slow / Normal / Fast / Instant). At each quarter break: Enter to
  continue, F to speed up, S to skip to the final, C to toggle "coach's view" (shows both play
  calls on every snap). A full box score follows.
- **[F] Fast Sim** – play it instantly and move to the next game.
- **[W] Fast Sim to End of Week** – play every remaining game instantly.

The week's results screen lets you open the box score of any game by number.

## The sideline (your games)
When you coach a game (every snap, or the big moments) you do more than call plays:
- **The tablet** on every call: momentum and the crowd, what's working, what they do in this down and distance, a
  line from your coordinator, who's hot and cold.
- **Series orders** (`[G]`, and a check-in between series): max protect, quick game, pound it, tempo, take shots,
  feed a player; spy the QB, two deep, load the box, pin your ears back, double their best receiver.
- **The people**: the trainer's report, pulling a struggling quarterback, and what you say to a player after a
  pick, a fumble, a flag or a blown coverage.
- **The calls**: the try, onside and squib kicks, accept or decline, the replay challenge, fakes, icing the kicker,
  a timeout to stop the bleeding, getting the crowd up, overtime.
- **Friday's game plan** on the week hub (`[G]`), checked at halftime, and a **headset log** with a process grade after
  the game. Settings → [9] Sideline turns each part on or off.

## The Window (Spectator mode's sportsbook)
Press **[B]** on the dashboard in Spectator mode. Start with a bankroll and bet every game all season: spreads, totals,
moneylines, first-half lines, team totals, player props, parlays, teasers, a weekly boost, and futures (national title,
conferences, the playoff, the Golden Helmet, preseason win totals). Lines are up for every game on the schedule and move
every week; a bet locks your number. Matchup cards show the line and let you bet until kickoff; a results screen
follows every week. In Spectator mode the team you follow is seen through a scout's eye (words and estimate ranges);
the book's options can hide every team's numbers.
Twelve regulars — made-up former players and coaches, each with a strategy — bet the same lines every week. The
STANDINGS tab ranks you against them; open a profile to see what someone's on and tail or fade it.

## Box scores, this season and every season before
Every finished game keeps its box score. Open one by number from the week's results, from any scoreboard
in **Schedules & Scores** (where **W7** jumps to week 7 and **N/P** step through weeks), or from any team's
schedule. **Schedules & Scores → [4] Past seasons** has every finished season's scoreboards and team schedules,
and **[Y]** on a team schedule switches seasons. Old box scores show the players who actually played that
day, with poll ranks as they stood at kickoff. Each archived season adds about 3 MB to a save.

## Postseason
After week 13 the season keeps going:

- **Conference Championships** – the top two in each league. The SCC, Continental, Seaboard, Meridian and Lake Country play at
  neutral sites (Atlanta, Indianapolis, Charlotte, Arlington, Detroit); the rest host on campus.
  Title games don't count toward conference records.
- **National Playoff** – 12 teams: the five highest-ranked conference champions plus seven at-large,
  straight-seeded by the poll. First round on campus, quarterfinals and semifinals at the Six Classics
  bowls in rotation, and the title game at Spring Mountain Stadium in Las Vegas on January 25, 2027.
- **Bowls** – 35 more bowls around the country, best teams to the best bowls.

The game preview shows what every postseason game *is*: the bowl or round, the stadium, city and date,
NP seeds, conference-champion and defending-champion tags, how each team got there, and a STAKES line
(who the winner plays next, and when). The broadcast booth knows it too — postseason openers, bowl history,
stakes talk during the game, trophy presentations, game MVPs, and title-history callbacks.

**National champions** (tab 5 RANKINGS → [N]) — the built-in universe's book starts in 2026 (the real-world
universe file brings 1998–2025 with it); every title won in your world is added. Team pages list their titles.

## Playing: Coach Career or Spectator
Right after the world is built you choose how to play.

- **Coach Career** — create your coach: name, age, one of six backgrounds (each shapes your ratings and
  starts you with a signature trait), your offense and defense, your fourth-down philosophy, a difficulty,
  and your **prestige** — how big a name you are (Unknown, Rising, Established, Elite). Four programs
  offer you a job: the bottom of the G5 for an Unknown, the top of the G5 and the low end of the Power 4
  for a Rising name, solid Power 4 programs for an Established one, blue bloods for an Elite one. A
  bigger name also gets a bigger first contract and more leverage when you negotiate. It's reputation,
  not ability: your ratings come from your background either way (or pick any program as a sandbox
  "dream job"). From there the
  carousel treats you like everyone else: your AD grades every season against the program's goals,
  your seat heats up, and you can be fired. Win, and bigger jobs call every offseason — openings where
  you're a top candidate, and sometimes a big program willing to push its own coach out to get you.
  Traits are earned from what your teams actually do (The Closer, QB Whisperer, Trench Guru, Developer,
  Motivator, Salesman, Culture Builder…). Your recruiting board is yours alone — the AI stops running it.
  **[C] My Career** shows your seat, goals, record, reputation and story.
- **Spectator** — you control nothing. Every board and every coaching change runs itself; you can open
  any team's recruiting board to look, but not touch.

## Coach this game
In career mode, press **[P] Coach this game** at your matchup screen. Before every snap you choose:
a run or pass from the full playbook (★ marks your scheme's plays), the staff's call (always shown as a
suggestion), punts and field goals on fourth down, kneels, timeouts (a timeout gets back the clock the
last play burned), and tempo — hurry-up, normal, or milk the clock. On defense, pick the call yourself or
hand it to your coordinator. **[S] sim ahead** gives the headset to your staff for the drive, the
quarter, the half, or the game. Fast Sim to End of Week always stops at your game.

## The Schedule and Kickoff Times
Schedules are laid out like a real season:

- **Weeks 1-3** (1-4 in eight-game leagues) are non-conference: FCS guarantee games ("cupcakes"),
  Group of Five "buy games", and the occasional marquee Power matchup. Iowa–Iowa State and the
  Coal Country Clash stay in September.
- **Conference play** fills the middle and end of the season, with each league's bye in the middle.
  The Midway Melee keeps its October week and the St. Marys Classic its early-November week.
- **Week 13 is Rivalry Week** — the Iron and Pine, the Toledo War, the Magnolia Cup, the Hill Country Clash and every
  league's rivals, plus the cross-conference ones (Upcountry–South Carolina, Florida–Florida State,
  Georgia–Atlanta, Kentucky–Louisville).

Every game has a date and kickoff time (Eastern), and games are played in that order:
Thursday and Friday nights, a Labor Day game and a Sunday night game on opening weekend, Lake Country Lights on
Tuesday/Wednesday in November, Thanksgiving night and Black Friday on Rivalry Week, and Saturday's
noon, 3:30 and primetime windows — the week's biggest game gets national primetime, the West Coast plays
late, and Hawaii kicks off at midnight Eastern. The postseason runs on its real calendar through the
Monday night title game. Weeknight games are played before Campus Countdown goes on the air Saturday morning,
so the crew talks about last night's results, mentions kickoff times, and shows them next to every pick.
In week 1, Campus Countdown talks about the preseason poll, last year's champion, the coaching carousel and the
Golden Helmet favorites instead of season stats that don't exist yet.


## Awards Season & the Pro League Draft
When the season ends, before seniors graduate:

- **Awards Season** — the Golden Helmet, the best player at every position (Best Quarterback, Best Linebacker…),
  Freshman and Coach of the Year, and first- and second-team All-Americans. Honors go into each player's
  history.
- **The Pro League Draft** — 7 rounds, 224 picks. Juniors and redshirt sophomores decide whether to declare from
  where they project on the board (most likely first-rounders go, some mid-rounders gamble, and a few get
  bad advice and go undrafted). Teams grade tools, position value, production and honors, with scouting
  noise. Programs that produce picks earn a **prestige bonus** that fades over three drafts, and prestige
  is part of what recruits and transfers look at. Browse any draft by round, by school, or your own picks
  (Media Center → Pro League Draft); team pages show picks since 2026.

## Your Transfer Portal Window
In career mode, the portal pauses after everyone enters and before anyone lands. You get two weeks'
worth of recruiting hours to **contact** entrants (learn their interest), **pitch** them, host **official
visits**, and **offer roster spots** (up to 8 — a player can only choose you if you offered). You can also
try to **talk your own players out of leaving**. Your staff stops bidding on its own, so the players you
land are the ones you went after. A results screen shows who you landed and who got away.


## Media Center
Main menu **[10]**: The Wire (headlines written from last week), Players of the Week (plus every
conference's offensive player), Stat Leaders (15 categories), Team Rankings, Hot Seat Watch (a live
in-season projection of every seat, with week-to-week movement), a nationwide Injury Report, a 12-team
Playoff Projection, Award Races (Golden Helmet, defense, freshman, coach), the Campus Countdown Desk, the Awards
Archive, every Pro League Draft, **Rivalry Trophies** (every trophy game and who holds it) and **Conference
Realignment** (every league's membership, media payout and deal length, announced moves, and the most
valuable TV programs).


## Campus Countdown
Every week, right before the games, the Campus Countdown crew goes live from the week's biggest campus.

- **The site** is picked like the real show picks it: ranked matchups, rivalries, postseason stakes,
  campuses that have never hosted, coaches on the hot seat — and never the same campus twice in a season.
- **The show is built from the season.** A dossier ranks the week's real storylines (rivalries, unbeaten
  clashes, revenge games from past results in your world, hot seats, coaches facing old schools, Golden Helmet
  players, streaks, poll moves, injuries, trap games, conference and playoff races) and the crew talks
  through them in whole, back-and-forth scenes.
- **The crowd** chants, holds up signs the cast reads and answers, boos picks against the home team,
  and builds to the headgear pick.
- **Segments** flow with spoken hand-offs: signs, the matchup, the film room, a defender to watch, coach
  stories, crowd challenges, an upset alert, last week's recap, around the league, a long one-on-one
  interview with a star player, the sideline report, desk banter, the picks, a guest picker, and the
  final headgear pick.
- **Around the country.** The crew walks through the four to six games from last Saturday that
  mattered — upsets, ranked matchups, rivalry and trophy games, overtime thrillers, coaches on the hot seat —
  and says *why* each one went the way it did (turnovers, a run game that took over, a fourth-quarter
  comeback, a pass rush, penalties, the player who won it) and *what it means* (the poll, the league race,
  the playoff math, a seat, a trophy, a streak). Later, a tour of today's board beyond the picks: kickoff
  time, the stakes, where the matchup tilts (offense against defense, the quarterbacks, the player to
  watch, the series history), somebody's lean — and sometimes somebody on the desk who disagrees.
- **The state of the season.** Every week from Week 2 on, the crew reads the whole sport and talks through
  the three or four stories everybody's discussing: a preseason top-10 team that's 0-2 or has dropped two
  straight, the team nobody ranked in August that's now top ten, the defending champion (rolling or reeling),
  winless programs and long skids, long winning streaks, first-year coaches who flipped a program and coaches
  whose seats are on fire, an unbeaten Group of Five team crashing the playoff talk, the Golden Helmet race (and a
  new leader), crowded league races, the poll's biggest fall, a star quarterback lost for the season, a team
  playing under a postseason ban, a school in its first year in a new league, a locker room coming apart.
  Each one gets the number that frames it, a diagnosis read off the season (turnovers, the quarterback, the
  defense, one-score losses, injuries, a new staff, a brutal schedule), somebody who disagrees, and what's
  next, down to who they play this week. The same context runs through the recaps ("preseason No. 4, now
  0-2"), the previews (what a team is playing for, the trap game with a ranked opponent on deck), the signs,
  and the one-on-one, where the player is asked about *his* week — the zero in the loss column, the losing
  streak, the Golden Helmet lists, the school he transferred from, being a captain, his coach's job, the Pro League scouts
  in the building, the rival that's beaten them three straight, the trophy on the line. A story isn't told
  twice unless it has moved.
- **Today's Tailgate.** Boom walks the lots and brings back the best tailgate on campus: one fan (now and
  then a visitor who drove in), what's on the grill, how long they've had the spot, the secret, dessert,
  and a score prediction, with the desk heckling. The menu knows where it is and who's in town — fans cook
  the visiting mascot (blackened redfish for the Gars, mule-kick chili for the Mules, pretzel twists for
  the Twisters, deviled eggs for the Hellcats…), or the local specialty (boudin in Baton
  Rouge, brats and curds in Madison, pepperoni rolls in Morgantown, green chile in Albuquerque), or one of
  thirty classics, plus forty-odd desserts. Add food in `tailgate.py`, one line each.
- **Picks** come from each analyst's own model (talent, quarterbacks, defense, coaching, home crowd,
  form) and personality. Everyone explains his pick by what actually drove it, and the crew keeps a
  season-long standings race. Watching the show never changes a game result.
- **Memory:** no scene, sign, interview question, banter or guest picker repeats within a season.

[Enter] continues, [S] skips to the picks, [X] skips the show. **Settings** (tab 8 SYSTEM → [S]) turns
the show on or off, sets its speed (Instant / Fast / Normal), and renames any cast member.

**The cast** is original — each character is a seat at the desk, not a real person:
Cal Merriman (host), Trent Albright (former QB, film), Harlan Voss (legendary coach, headgear pick),
Jace "Boom" Kowalski (entertainer), Dorian Pettaway (former star defender), plus a guest picker every week.

To add content, edit the data files — every entry is a single line or a short list:
`gameday_cast.py` (cast, banter, guest pickers), `gameday_scenes.py` and `gameday_more.py`
(scenes, signs, interviews, transitions, pick reasons).

Every launch builds a new random world (the seed is shown on tab 8 SYSTEM), and it starts in 2022.
Four years of recruiting classes, transfer windows and player development run before you arrive —
no games, no invented results — so the 2026 rosters you inherit were recruited and developed the
same way every future roster will be. Takes about half a minute to build.

## Personality traits
Ratings say what a player can do; traits say what he does with it. 59 player traits and 36 coach traits,
drawn from opposing pairs so nobody is both Iron Man and Injury Prone. Most players carry one to
three: Clutch, Big-Game Player, Cold Blooded, Slow Starter, Flat-Track Bully, Gamer, Practice
All-American, Warrior, Glass, Fast Healer, Wears Down, Film Junkie, Late Bloomer, Raw, Maxed Out,
Coachable, Stubborn, Weight Room Rat, Captain, Hothead, Patient, Impatient, Homesick, Chasing
Spotlight, Grinder, Quiet Professional, Chip On His Shoulder, Prodigy, Mentor, Diva, Showman, Humble,
Tone Setter, Road Warrior, Home Cooking, Rivalry Guy, Big-Game Jitters, November Player and more.
Big-Game Players lift their team against ranked opponents; Flat-Track Bullies lift it against teams it
should beat (unranked and clearly worse, or FCS) and drag it down against ranked ones.
They tilt game-day form, the fourth quarter of a one-score game, injury odds, offseason growth, who
draws the flags, and whether a player enters the portal when he loses a job or his coach leaves.
Leaders (and divas) lift (or drag) the whole team; some players are better on the road, at home, in
the rivalry game, or in November. A team's locker room is worth at most a point and a half.

Coaches carry one or two of the 36 — The Closer, Evaluator, Developer, Culture Builder, Burns Them Out,
QB Whisperer, Trench Guru, Riverboat Gambler, Conservative, Clock Manager, Salesman, Fence Builder,
Poor Evaluator, Portal King, Micromanager, Motivator, Big-Game Coach, Can't Win the Big One, Rivalry
Specialist, Road Dog, Lightning Rod, Teflon, Boosters' Favorite, Old School and the rest — and they move
recruiting closes, scouting accuracy, development, fourth-down nerve, penalties, portal shopping, how many
of his own players he keeps out of the portal, how his team plays in big games, and how loudly every loss
echoes on his seat. Contradictory pairs (Riverboat Gambler and Conservative) never land on one coach.
Nothing here swings a game alone; over a season the tilt shows.

## Coaches, ADs and the seat
**Career personalities** (12) decide how a coach handles job offers: Climber, Loyalist, Mercenary, Builder,
Homebody, Journeyman, Alma Mater Guy (his old school can have him any time), Blue-Blood Chaser (only the
biggest jobs), Fixer (loves a program that's down), Survivor (jumps before he's pushed), Short-Timer and
Lifer (retire early, or never). Coach profiles show each coach's alma mater.

**Athletic directors** (12 styles) judge coaches their own way: Patient, Win-Now, Big-Game Hunter,
Conference First, Analytics, Booster-Driven, Turnaround (wants more wins every year), Recruiting-First
(grades the classes), Traditionalist (the rival and the home record; gives long-tenured coaches rope),
Budget Hawk (hates buyouts in either direction), Brand Builder (ranked and on TV) and Fan Pulse (governs
by talk radio). Each sets three program goals from 28 kinds, including winning more than last year,
going unbeaten outside the league, winning one-score games, scoring or defense targets, winning at a
ranked team's stadium, and never getting blown out.

**The seat moves every Saturday.** Each coach starts the season where last winter's verdict left him,
and every week moves it: how the year is going against what his AD expected, plus the games people
remember — the rival, a loss to an FCS or Group of Five team, an upset, a blowout, a losing streak, a big
win. The AD's style sets how loud one Saturday is, coaches in their first years get the same patience
the verdict gives them, and traits like Lightning Rod and Teflon turn it up or down. The Hot Seat Watch,
the Wire, the Campus Countdown crew and the booth all use the live seat. Firings still happen after the season.

**Coordinators.** Every FBS program has an offensive and a defensive coordinator — real coaches with an
age, a personality, traits and a ceiling. They start out rated below the head coaches at their level,
but their ceilings run higher, and the good ones grow into head coaches. Offensive coordinators are
strongest developing quarterbacks, receivers, backs and linemen; defensive coordinators, the back seven
and the defensive line. Each one carries part of the load, always less than the head coach:
- **Games:** his side's in-game adjustments, blitz and trick-play nerve (about a third), and his traits
  at half strength.
- **Development:** 40% of the development rating for players on his side of the ball.
- **Recruiting:** 20% each of the staff's recruiting hours and pull, plus a boost with recruits from his
  home region, and his recruiting traits at half strength. A quarterback recruit's development pitch
  is the head coach *and* the OC.

Every season goes on a role-specific resume: points, yards, passing and rushing per game (allowed, for
a defensive coordinator), with national ranks, the unit's overall rank, and where its roster's talent
ranked. Beating the talent is what gets a coordinator noticed. Open one from a team page (**[O]** / **[D]**)
or **Coaches → [6] Coordinators** and **[7] Rising Coordinators**.

**The staff carousel** runs every offseason after the head coaching carousel, and gets its own report:
- A new head coach cleans house — most coordinators leave, a good one sometimes stays — and brings
  coordinators he's worked with.
- Coordinators whose units flop against their talent get fired, sooner when the head coach's own seat
  is hot.
- **In Coach Career mode, your staff is yours.** Every offseason a staff review shows how each of your
  coordinators' units did against their talent; keep them or let them go. Take a new job and you decide
  which of the inherited coordinators stay. For every opening you get the candidates who would actually
  take your job — coordinators from smaller programs, coaches out of work, fired head coaches, and new
  faces (high school and FCS coaches at Group of Five programs; promoted position coaches and Pro League
  assistants at Power programs) — with ratings, potential, scheme fit, recruiting region, and last unit
  against its talent. ★ marks coaches who've worked with you; **[V#]** opens anyone's full resume. Your
  coordinators can still be hired away, by bigger programs or as head coaches. **tab 6 COACH → [S] My staff**
  shows your staff and lets you hand the job to your AD (or take it back).
- Openings are filled biggest programs first. Power programs hire coordinators away from smaller ones;
  Group of Five programs promote high school and FCS coaches; fired head coaches land as coordinators.
  High school coaches only enter college football through Group of Five coordinator jobs now.
- Coordinators are head coaching candidates, judged on their resume and the stage they did it on. A
  coordinator whose unit flopped doesn't get the interview.

**Second chances.** A fired coach goes back into the candidate pool, and smaller programs love a big
name who got fired somewhere bigger: he's recruited at that level, run a real program, and the old
school is still paying him. Fired coaches will step down a long way to get back on a sideline. The
carousel report tags these hires "second chance".

## Choosing a job
Every offer card shows each program goal with how often it's asked for — "Beat a Power 4 opponent
(1 in 4 yrs)" reads very differently from "every year" — and one line on how that AD watches you: how
loud a single Saturday is, how short his leash is, and the reminder that the goals are the bar he holds
you to over each one's window. The same line appears on the welcome screen and the program page.

## Creating your coach
Every offense and defense on the scheme screens comes with a plain-English explanation: what the scheme
is trying to do, what kind of players it needs, the kind of program it looks like, how often it runs the
ball and how fast it plays — and which recruits it's an easier (or harder) sell to, straight from the
game's recruiting math. The fourth-down philosophies are explained too. Your background's suggested
schemes are marked, but any combination can win.

## The preseason week (Coach Career)
Before Week 1 every year, the dashboard's [A] opens fall camp: your full schedule with a projected win
total, your AD's expectations for the year and a captain's check-in, and your recruiting board. Enter
kicks off Week 1 (straight into that week's hub); simming weeks skips camp and keeps the schedule you have.

- **Recruiting:** build your board — add and drop targets, read the film. There are no recruiting hours
  in the preseason week; they start in Week 1.
- **Custom non-conference schedule ([S]):** pick any of your non-conference games and choose a new
  opponent for that week — Power, Group of Five or FCS, with each one's rating and your odds shown.
  Everyone else keeps twelve games: the team you take leaves its own game that week, and your old opponent
  plays theirs (or an FCS guarantee game). Conference games, protected rivalries and Rivalry Week can't
  be moved. A Power program won't play at a Group of Five stadium — take it on the road or not at all.
  The schedule you build is the one your AD, the polls and the committee judge you on.

## Your games: sim it, play the big moments, coach every snap, or watch
When your game comes up (Coach Career) you choose how to play it — and the game remembers your last
choice, your speed and whether you call the defense, so it's usually one keystroke.

- **Sim it** — straight to the final, with the scoring summary and an optional box score.
- **Play the big moments** — your staff calls the game and the booth stays quiet until a snap that
  decides it: a real fourth-down decision, goal-to-go, a two-minute drill, a goal-line stand, every snap
  of a one-score fourth quarter, overtime. Each moment opens with a recap of what you missed.
- **Coach every snap** — every play is your call.
- **Watch the broadcast** — full commentary, no play-calling.

At every quarter break: skip the next quarter, skip to the final, change the speed (1 slow → 4 instant),
toggle the coach's view, or switch between big moments and every snap. Mid-drive, [S] hands the headset to
your staff (for the drive, the quarter, the half or the game) — or switches modes. In a career, everyone
else's games play around yours; the week's results follow.

## The week (Coach Career)
Before each of your games, one screen covers the week:
- **Monday · Film** — what the tape says about Saturday.
- **Tuesday · Inbox** — who's reached out (below).
- **Wednesday · Practice** — the week's focus, each a trade-off: game-plan heavy (+0.8 Saturday,
  injuries ×1.25), balanced (+0.4), ball security (+0.5, steadier late), situational football (+0.3, much
  sharper in one-score fourth quarters), physical full pads (+0.7, injuries ×1.3), rest & recover (no lift,
  injuries ×0.75, short injuries heal a week sooner), recruiting week (−0.3, +8 recruiting hours).
- **Thursday · Press conference** — optional, two questions built from the week you're actually having:
  your first game ever as a head coach, your first win, a blowout loss, a one-point heartbreaker, the first
  loss after a hot start, a winning or losing streak, turnovers, a quiet run game, the quarterback's
  interceptions (or Golden Helmet buzz), an injured star, the upset you just pulled, the ranked team coming in,
  your old school, the rival, the conference opener, your job security, your seniors' last home game, your
  recruiting class, and more. Nobody asks about an opponent's 0-0 record in Week 1, and the room doesn't
  repeat itself week after week. Every question has its own three answers, and every answer shows its
  upside and its cost before you pick it. The tones: confident (recruits like it — as an underdog it's
  bulletin-board material for them), measured (composed late — but no headlines, and an AD who wants noise
  notices an all-measured podium), fiery (+0.3 Saturday — but emotional late; some ADs love it, some wince),
  humble (+0.15, takes the heat off your players — doesn't sell to recruits; patient ADs like it). Many
  answers do more: backing your quarterback, standing by your coordinator, a shot at the rival, admitting
  locker-room friction. Some draw a follow-up — say you're ready for the rival and somebody asks if you're
  guaranteeing it (say yes and it's on the record: win and recruits share the clip, lose and your AD
  remembers). The THURSDAY panel shows what your answers have banked for Saturday.
- **After the game · Postgame podium** — two or three questions from the game you just played, same
  rules, carried into next week: owning a blowout (and whether staff changes are coming), calling out the
  officials after a close loss (a fine, and a locker room that loves it), a freshman's breakout day, bowl
  eligibility, a leaky defense, your job security.
- **Friday · Injuries** — who's out.
Enter goes straight to Saturday with your usual plan. Simming weeks uses your usual plan automatically.
Settings → [5] turns the hub off.

## People who talk to you (Coach Career)
Your inbox ([I] anywhere; the unread count sits in the dashboard header) fills with people reacting to
what actually happened, in their own voice. Every message that wants an answer gives you three or four real
choices, and none of them is free — the colored line under each option says what it does (green: what you
get; red: what it costs; yellow: a risk, or something riding on a later result). What a reply can touch:
your AD's patience, the locker room, this Saturday or the game after, late-game poise, injury risk (this
week or all year), recruiting hours and interest, next year's NIL money, a coordinator's loyalty, and single
players — who's bought in, who's unhappy and eyeing the portal, who develops faster this offseason.

- **Your AD** — camp expectations, after a bad loss or a big win, rivalry week, the hot seat, midseason, the
  year in review. Promise results and he holds you to them ("Judge me after the rivalry game" buys time —
  and bets your job on one Saturday). Ask for money and you'll get some, depending on who he is.
- **Players** — a buried backup wants snaps (promise it, give him a role, tell him to earn it, or help
  him find a better fit), captains during streaks and skids, a starter's family emergency, a walk-on who's
  earned a scholarship, a freshman plan, a star playing through an injury (he might aggravate it), a player
  whose grades could make him ineligible.
- **Recruits** — a wavering commit (a call, a home visit, a teammate's call, or an ultimatum), a kid asking
  about NIL, reactions to Saturday, a high school coaches' banquet.
- **Staff** — camp reports, the QB room, film notes that set practice focus, saving a pressure package for
  a bigger game, opening up the playbook as an underdog, in-season lifting, travel plans, Pro League scouts at
  practice, tampering by another school's collective, a coordinator with job offers or wanting a raise.
- **Everyone else** — media day, the podcast, the student section, the rival coach's radio comments, a
  booster's circled date, a donor whose gift comes with a favor, a program legend who wants to talk to the
  team, the Golden Helmet campaign, team rules for the year, bowl practices, signing day, conference realignment.

Leave a message for two weeks and it closes — and a few people notice (the AD on the hot seat, a recruit,
a player asking about his role). When something you said rides on a later result, the verdict lands in your
inbox after the game. Settings → [7] hides the effect lines if you'd rather play it by feel.

## Halftime (Coach Career)
Every game you coach stops at the half — simmed or played — with the first-half numbers and what your staff is
seeing. Pick a second-half plan (trust the staff, lean on the run, air it out, bring pressure, sit back in
coverage, protect the lead or go for broke; each changes the play-calling for real) and a message (let the
coordinators talk, calm and clear, or light into them, with the odds shown). The postgame shows how the second
half went. Settings → [8] turns it off.

## Morale (every player)
Every player has a mood, 0–100, on his player card. Playing time, results, the locker room, his NIL deal, who
he is, and every call you make about him move it. Under 40 he's shopping the portal; under 25 he's very likely
gone; above 75 he's staying. The starters' average is worth about half a point on Saturday. Tab 3 → [K] (locker
room) shows who's sliding and why, and your position coaches tell you when a key player hits bottom.

## What you see: the staff's eye, not the numbers (Coach Career)
In Coach Career you never see a real rating: not your players', not anyone else's, not a team's. You see what a
head coach sees. (Spectator, Athletic Director and simmed seasons still show every number. Stats always show.)
- **Words, on a fixed scale.** A player "looks like" a long shot, developmental, backup, rotation player, starter,
  quality starter, star or All-American. Skills read horrible / bad / below average / average / good / great / elite.
  Teams read very weak to elite, and your odds read "slight underdog", "toss-up", "heavy favorite".
- **Practice report** (tab 3 TEAM → [P], [R] on the week hub, [C] in fall camp). Each week every player puts up a
  practice stat line: team-period completions and picks for QBs, one-on-ones won for linemen, drops for receivers,
  field goals by distance for kickers. Lines come from his real skills plus luck, so a great player can have a bad
  Wednesday and a walk-on can get hot. The report also names position battles and gives the staff's depth chart,
  which blends his true level (blurred by how sharp your staff is) with this week's practice. Veterans are read
  better than freshmen, and the read sharpens as the season's film piles up. [A] takes the staff's chart; [R] on the
  depth chart takes it one position at a time. It's advice. You can ignore it.
- **Your staff sets the depth chart every preseason.** When a new season starts (and when you take a job), your
  staff builds the whole chart from scratch with the same eye as the practice report — last year's starters keep a
  small edge, and a true freshman who isn't starting sits behind a close veteran to save his redshirt. Fall camp
  shows how many new starters there are and any position moves the staff suggests ([S1] on the depth chart takes
  one). From there it's yours: the staff never touches it during the season.
- **Every other staff manages its chart all year.** Preseason: a fresh chart, starters per position from the
  scheme's base personnel, and position moves when a room is short on bodies or a deep backup elsewhere would start.
  Every week: a re-sort as players develop and the film sharpens the read — a backup who has clearly passed a
  starter takes the job, but a starter doesn't lose it over a point. Better staffs misread less.
- **Scouting reports.** Every player card has a staff report ("accurate on quick throws, but can't push the ball
  downfield; a real threat with his legs"). [O] on the week hub shows film on your opponent's best players.
- **Position skills.** Every position has sub-skills: QB short / medium / deep accuracy, under pressure and dual
  threat; RB inside / outside running, receiving, pass protection and ball security; WR short routes, deep routes,
  hands and YAC; TE run block, routes, hands and YAC; OL run block, pass pro and space; DL pass rush, run defense and
  pursuit; LB run fits, blitz, coverage and tackling; CB short and deep cover, ball skills and tackling; S deep help,
  man cover, run support and ball skills; K accuracy and range; P distance and placement. They all matter in the
  game engine: a QB with a bad deep ball misses deep, a corner with poor deep cover gets beat over the top, and a
  punter with good placement pins teams inside the 20.
- **Development:** about a third of a player's yearly growth now happens during the season, week by week, and
  two-thirds happens in the offseason. The practice report shows who's trending up.
- **Scout's Eye** (Developer capstone in the coaching tree) adds the staff's estimate next to every word:
  "quality starter (76-81)", "good (1.03-1.09)". It's a range near the truth, never the number itself.

## The coaching tree (Coach Career — your coach only)
Tab 6 COACH → [T]. Results earn skill points (the December review: seasons, beating expectations, bowls,
titles, the rival, AD goals, top classes; plus first-round picks and career milestones). Spend them on six
branches — Recruiter, Developer, Motivator, Tactician, Politician, Program Builder — each with four tiers that
open as you invest (0/4/7/13), a fork at tier 2 (pick one, lose the other), and a capstone. The whole tree
costs about 110; a long career earns 50–70. Free respec whenever you take a new job. Money still buys your
ratings on the Develop screen.

## Promises, trust and the locker room (Coach Career)
- **Recruiting promises:** [M] on a recruit's card promises him a starting job, real snaps, or a redshirt to
  develop. The card shows his position room next fall, and top targets ask where they fit. The promise follows
  him to campus, is graded after his first season, and your kept/broken record changes how much the next one is
  worth.
- **AD trust (0–100):** built by keeping your word, answers he likes and goals met; spent by broken promises,
  money asks, missed goals and silence. It changes how hard results hit your seat and how much money he finds.
  Shown on AD messages and your career page. A new AD starts over.
- **Contagious morale:** captains pull the room toward their mood, unhappy wild cards drag their position group,
  happy leaders lift theirs. After the captains vote you can accept it, add a captain, or overrule it.

## December (Coach Career)
Each postseason week is set a week early, so the title game, your bowl or your playoff game has a full week
of prep, presser and mail. December brings championship week, the bowl trip (business or reward), draft-bound
players asking to opt out (and stars around the country actually opting out), every playoff round, the early
signing period, the unhappy players you might lose when the portal opens, and — with no bowl — what to do with
a long December.

## The dashboard (the main menu)
The main menu is a dynasty-style dashboard: a scoreboard header for your team (or, as a spectator, the
team you follow — [F] on the Team tab), a tab strip, and a grid of live panels. Type a number to switch
tabs: 1 Home (next game, team, coach, polls, standings, recruiting, headlines) · 2 Schedule · 3 Team ·
4 Recruiting · 5 Rankings · 6 Coach · 7 Media · 8 System. Each tab lists its own commands; anywhere,
[A] plays the next week, [M] sims several, [V] saves and [Q] leaves (main menu or quit). In Coach Career your recruiting board
starts empty — you build it; no staff adds to it for you.

## Simulate seasons  ([M] from any tab, then e.g. `30s`)
Type a number for weeks, or a number with an `s` for whole seasons — `30s` runs thirty seasons back to back:
every game, every carousel, portal and signing day, with a one-line summary per year (champion, Golden Helmet, your
team). Nobody stops to ask: in a coach career your staff recruits and works the portal, your agent signs
extensions and takes the best job if you're fired (or a much bigger one calls); in AD mode your deputy runs the
program like any other AD. Ctrl+C stops cleanly at the end of the current week. Up to 100 seasons at a time.

## Athletic Director mode  (choose [3] when a new world starts)
You run the program, not the team: the coach recruits and calls plays; you decide who the coach is.
- **Preseason** — make the Statement (a rebuild, show progress, bowl or bust, contend, championship or bust).
  It sets the win total the fans will judge you against: big promises buy goodwill in August and cost double in
  December. Set the coach's three goals (easier, standard or harder ones) and price the tickets.
- **Every week** — the AD's desk: the fans react to Saturday against what you promised (the rival game counts
  double; blowouts sting), the boosters follow the fans, and something lands on your desk about half the weeks —
  a naming-rights deal, a broken weight room, a coach who wants recruiting staff, a "fire him" banner plane, a
  video board, a donor, a TV network, the NIL collective. Each choice moves money, fans, boosters or the coach.
- **The AD office ([C] from any tab)** — facilities projects, upkeep (deferred / standard / premium: how often
  your buildings slip), ticket prices (value / standard / premium), the budget, the coach's goals, extending him
  (you write the salary, years, buyout, bonuses, a per-goal bonus and a rollover), and firing him mid-season.
- **Season's end** — the report card: the promise, the goals, crowds and money (ticket pricing, booster
  donations, upkeep), then the board grades you. Then your call on the coach: keep, extend, let the deal run out,
  or fire him (the buyout is on you). Lose the board and you're fired — take a smaller job or walk away. Keep it
  high for three years and bigger schools call.
- **The search** — if the job is open, you see a real list: out-of-work coaches, sitting head coaches (with the
  release fee you'd owe), and coordinators, each with an asking price and his agent's read on his interest. Write
  the offer; he says yes or tells you why not. Other schools can come after your coach — match or let him walk.
Fans move attendance, and attendance is the home-field edge.

## Weather  (tab 2 SCHEDULE → [F] the Weather Center, or [W] on the week hub)
Every outdoor game is played in real weather built from where and when it kicks off: each state's (and some
towns') September-to-December climate, the kickoff time, regional weather systems that soak a whole conference
at once, fronts that blow through mid-game, and a tropical storm or two coming ashore most seasons. Domes and
closed roofs have none.
- **It changes during the game** — rain moves in or clears, snow piles up, the sun goes down, a front drops the
  temperature and turns up the wind. Thunderstorms can bring a lightning delay (momentum resets). Teams switch
  ends every quarter, so the wind helps one side and then the other. Grass fields get sloppy; heated hybrid
  grass (a stadium part) shrugs off snow.
- **It changes the game** — rain and snow cost accuracy and catches and cause fumbles and muffs; wind moves
  deep balls, punts and field goals (a head wind can take 10+ yards off a kicker's range); cold makes the ball
  a rock and bothers warm-weather teams; heat wears down visitors in the second half; altitude adds distance to
  kicks and tires sea-level teams late. Coaches adapt: more runs, fewer shots, punts instead of long kicks into
  the wind. A real weather game averages fewer points and passing yards and more fumbles.
- **Forecasts** — on HOME's next-game panel, tab 2, your schedule, the week hub, the sidebar, and the Weather
  Center (your forecast and extended outlook, the country's weather games, last week's, and your program's
  weather book). Honest but uncertain: three weeks out it's close to normal for the date; the week of the game
  it's close. A 40% chance of rain means rain in about four of ten of those games.
- **Weather prep** (practice focus) halves what the weather does to your team; the staff suggests it when the
  forecast is bad. Bad weather also keeps some fans home (a roof canopy helps), follows recruits on official
  visits, and gets talked about by the booth, the Campus Countdown crew and the headlines. The box score lists the
  conditions for every quarter.

## Facilities & attendance  (tab 3 TEAM → [F], or My Career → [F])
Every program has two buildings rated 1 (crumbling) to 10 (elite), and a stadium built out of parts:
- **Recruiting Facilities** — every recruiting pitch lands harder (0.94x at 1 → 1.12x at 10), and it's most of
  what a recruit means by "facilities".
- **Training Facilities** — players develop faster every offseason (0.94x → 1.08x).
- **The stadium** — nineteen parts, each with tiers (below). Its 1-10 grade is what the parts add up to.

A recruiting or training upgrade is a one-time purchase out of next season's player-NIL pool (the same money that
pays recruits), one project a season. Each level costs more than the last — $0.3M for level 2, $9M for level 10.
Every offseason each one has a small chance to slip a level (2% plus 0.8% per level). The CPU's ADs run their own
building plans; you run yours.

### The stadium, part by part  ([F] → [S])
| Group | Parts |
|---|---|
| Seating | Lower Bowl (6 tiers, +6,000 seats each), End Zone Stands (to an Enclosed Bowl, +4,000), Upper Deck (home side, then twin, then wraparound, +5,500), Student Section (+1,500), Club Seats (+1,200), Luxury Suites (20 a tier) |
| Atmosphere | Roof Canopy, Video Board, Sound System, Stadium Lights (standard → LED light show), Team Entrance |
| Fan experience | Concourses (open-air → climate-controlled), Fan Plaza (lots → Gameday Village), Hall of Fame, Press Box |
| Football | Home Locker Room, Visitors' Locker Room (spartan, or pink), Recruiting Lounge, Playing Surface (worn turf → heated hybrid grass) |

What the parts do:
- **Seats.** Capacity, and $45 a game for every new seat that's actually sold.
- **Noise.** Steep decks, enclosed ends, a student section, a canopy and a big sound system make the building
  louder (1-10). With the crowd, that's the home-field edge and how hard momentum swings at home.
- **Money.** Club seats, suites, concessions and video-board ads — sold in proportion to what the market can pay
  (a small school's suites don't all lease). Stadium revenue is added to next season's budget.
- **Recruiting appeal (0-100).** What a recruit sees on a game-day visit: it's a quarter of what recruits call
  "facilities", every pitch lands a little harder, and the Recruiting Lounge makes campus visits count more.
- **In the game.** A good home locker room is worth a little at home; a spartan or pink visitors' room takes a
  little from the other team; worn turf means more home injuries, good grass fewer.
- **Fans.** Concourses, the fan plaza and the hall of fame grow the fan base a little every year.

Building: **one stadium project at a time**, and the big ones take two or three seasons (a seating project closes a
section while it's built). Many parts need others first — an upper deck needs a horseshoe lower bowl, suites need
a press box, a canopy needs an upper deck. Money comes from the **stadium fund**: boosters give every offseason
(more at a big, winning, sold-out program), and a conference title, a playoff run or a national title starts a
capital campaign. The fund pays first; the rest is paid out of the NIL pool as it's built, or with a 6- or
10-season **bond** the fund pays back (+15% / +30%; if the fund runs dry, the NIL pool covers it). You can also move
NIL money into the fund ([D]). Screens, speakers, turf, lights, the locker room and the lounge can age a tier.

**The fan base** is the crowd a full-interest Saturday brings. It grows with prestige, winning, sellouts and a
good game-day experience, slowly. Build seats faster than you build fans and the place plays half-empty — quieter,
and no ticket money. A small school can turn a 20,000-seat stadium into an 80,000-seat bowl, but it takes decades,
and a program good enough to fill it.

### Toughest Places to Play  (tab 5 RANKINGS → [S], or [T] from the stadium)
A live ranking of every FBS home field: the building's noise (20 points), the crowd's size and fill (20), the home
record (35: this season counts double, plus the last three), ranked visitors sent home beaten (12), the home streak
(8) and the tradition (5). Pick a team for its breakdown; [Y] shows every finished season's final list, and
movement is measured against last season's. The booth mentions it, and new parts, when you're there.

### Attendance
Every home game draws a real crowd: the fan base, how this season is going (a program that expects to win and
doesn't will see empty seats), last season, the poll, the opponent, a night kickoff (more under an LED show), and
how comfortable the stadium is. Rivalry games, postseason games and big home openers sell out — if the fan base is
big enough to fill the place. The crowd *is* the home-field advantage: a packed, loud building is worth about three
times what a half-empty one is. The preview shows the expected crowd, the broadcast and box score show the real
one, and a team's page shows its season average, sellouts and where it ranks among the toughest places to play.

## Who calls the plays  (My Career → My Staff → [O] / [D])
Every head coach either calls the offense and/or the defense himself or hands a side to his coordinator —
offensive-minded head coaches usually call the offense, defensive ones the defense, a few call neither and a
rare few call both. The play-caller's scheme is what the team runs on Saturday and recruits to, and he carries
most of that side's in-game adjustments. Yours defaults to you calling both; change it on My Staff or before any
game you coach. Hand the offense to your OC and the headset skips offensive snaps — fourth downs stay yours.

## Big moments  (tab 8 SYSTEM → [S] Settings → [6])
Choose what brings you in during "Play the big moments": overtime, crunch time (minutes and point margin are
adjustable), offensive fourth downs, the two-minute drill, the red zone (distance adjustable), goal-line stands,
their late fourth downs, and the blowout margin past which the staff plays it out. The catch-up at each big
moment lists only what happened while the staff had the headset.

## Auto copy output (tab 8 SYSTEM → [S] Settings → [4])
Turn it on and every screen is copied to your clipboard — colors stripped, the whole screen plus the
prompt — each time the game waits for you to type. Paste it into a chatbot, talk it over, type your move
back into the game. What you type is added to the recording, so a screen that asks two questions reads
like a transcript. The same text is also saved to `last_screen.txt` in the game folder. On a Mac it uses
the built-in pbcopy; Windows uses clip; Linux needs wl-copy, xclip or xsel (without one, you still get
the file).

## NIL in the transfer portal
Every transfer has a market price for what he can do right now (his rating and position — quarterbacks
cost the most). In your window, offer a roster spot, then **[N] NIL offer** on top of it; open offers are
held against your budget until he picks. Every other staff bids what its budget allows. Money multiplies
a program's appeal — more for players who care about money, less when somebody else is offering more — but
never decides for him. His deal becomes his NIL on your roster. Trying to talk one of your own players out
of leaving? A raise helps. The budget screen counts it all.

## Developing your coach (Coach Career)
CPU coaches grow on their own. Yours only grows through money you earn on the job: salary is paid into
your bank after every season, contract bonuses too, and **tab 6 COACH → [D]** turns it into ratings — Coach
Skill and the six development ratings. You can only spend while you have a job, and buyout checks from a
school that fired you count toward career earnings but never reach the bank.

A point costs $30,000 × 1.09^(rating − 50): $30K at 50, $71K at 60, $154K at 69, $168K at 70, $398K at 80,
$942K at 90, about $2.05M at 99. Coach Skill costs 50% more. Each rating can rise at most +3 a year (Coach
Skill +2), and unspent money carries over. You start with $250K; a first job at a small school pays about
$0.7-1.3M a year, which buys roughly 8-15 points a year while your ratings are in the 50s and 60s.
Nothing goes down on its own. Reputations (traits) are still earned by results.

## Hot seats, firings, extensions and hiring
- **Expectations are game by game.** Every game is scored for how likely the roster was to win it against
  that opponent, where it was played. A coach is judged on wins above or below that. Early in his tenure
  it's the roster he inherited; by year four the AD also expects what the program's stature says it
  should win — it's his roster now.
- **The AD keeps a ledger.** Results vs. expectation (this year and the two before), the trend, goals
  (capped both ways), the rival, the postseason, recruiting against the program's size, being paid like a
  winner without winning, and fans leaving after losing seasons. First-year coaches, recent playoff
  coaches and long-tenured winners get rope; a new AD who didn't hire him gives less. The coach profile
  shows the ledger, the season's projected wins, and what firing him would cost.
- **Firing.** Two hot years or one disaster puts a coach on the edge. Then the AD checks the price (a Budget
  Hawk won't eat a buyout over 12% of the budget, others over 30%; nobody pays 50% unless the season was
  dreadful) and the market (a borderline coach usually stays if nobody available is clearly better). A
  winning season usually buys another year. A coach at the end of his deal with a warm seat can simply
  not be renewed, for free.
- **Mid-season firings.** Impatient ADs (Fan Pulse, Win-Now, Booster-Driven) can fire in weeks 5-11 once the
  season is gone. The better coordinator becomes interim coach and is a real candidate for the job; a good
  finish helps his case. You're never fired mid-season.
- **Extensions.** Coaches get extended early — after a title or a big season, when the deal gets short, or
  to keep bigger schools away — and extensions always add years. When a school tries to hire a sitting
  coach, his AD can counter with a raise, and some coaches stay. You get early-extension offers too; if
  your seat is hot when your deal ends, it isn't renewed.
- **Hiring.** Bigger jobs interview more people; nobody interviews a coach the budget can't pay. A thin
  roster wants a recruiter, an underachieving talented one wants a better coach on Saturdays, Power jobs
  want Power-level experience, coaches who've won a similar job get a bump. A just-fired big name waits
  for a better job rather than dropping to the bottom of the Group of Five, nobody rehires the coach it
  just fired, and first-time head coaches get first-time money.

## Money: budgets, contracts and NIL  (tab 3 TEAM → [$])
Every FBS program has an annual football budget set by its size and its league — about $50M at the
biggest SCC and Continental programs, $20-35M across the rest of the Power leagues, $4-12M in the Group of
Five. It moves once a year with results: winning seasons, playoff runs and titles grow it (up to 1.5x where
it started); three or more straight losing seasons, and firing coach after coach, shrink it (down to 0.7x).
Big changes make the carousel news. It pays the head coach, both coordinators, any buyouts, and player NIL; whatever
the staff doesn't cost is what the players can get.

- **Contracts.** Every coach and coordinator signs for a salary and a number of years. Bigger coaches get
  bigger offers from bigger schools, and the AD's style shapes the deal: Booster-Driven ADs back up the
  truck for seven years, Budget Hawks offer short, cheap deals with small buyouts, Recruiting-First ADs
  keep coach pay down to fund NIL. Coaches weigh the money against what they think they're worth — a
  Mercenary most of all — and a big enough check moves a coach for a smaller step up.
- **The fine print.** Every deal also has, written the AD's way: a yearly raise (1-5%); a buyout
  guarantee; maybe an offset clause (fire him, and whatever his next job pays comes off what he's owed);
  a release clause (leave early and your new school pays your old one a share of your salary for up to
  three of the years you walked out on); performance bonuses for a bowl, a league title, the playoff and a
  national title; and maybe a rollover (every 8-win season adds a year). Win-Now ADs load up on bonuses,
  Budget Hawks almost always demand an offset, Booster-Driven ADs write big raises and rollovers.
- **Buyouts.** Fire a coach (or coordinator) with years left and the school keeps paying part of his
  salary every year until the deal would have ended — cut by his new salary if there's an offset clause.
  Fired during the season, he's paid for the games he coached and the buyout covers the rest of that year.
  Budget Hawks sometimes keep a coach rather than pay.
- **Release fees.** Hiring a sitting coach means paying his release: it lands on the new school's books
  and adds to the old school's pool the next year. A school won't chase a coach whose release is more
  than 15% of its budget (30% for a splash-hire AD).
- **Renewals.** Expiring deals are redone every offseason; ADs who like their coach extend early.
- **NIL.** Offer a scholarship first, then put money on top from the recruit's card ([N]) or the board
  ([$#]). Money makes you louder in his ear every week — how loud depends on how much money matters to
  him, how the offer compares to his market (about $900K for a five-star, $300K for a four-star, $70K for
  a three-star), and whether someone else is offering more. Money alone never gets a commitment. Open
  offers are held against your budget until he picks; a signee's deal is paid every year he's on the
  roster, and ends if he enters the portal.
- **Seeing it.** The budget screen breaks down this season's spending, next class's NIL room, the top deals,
  buyouts, the full payroll, and every program side by side. The roster has an NIL/YR column; player
  cards and coach profiles show deals.
- **Coach Career.** Every job offer shows the whole contract and what it would leave for NIL. Negotiate as
  much as you dare: 10% or 20% more money, more years, a bigger buyout guarantee, a smaller release
  clause, no offset, or less base for bigger bonuses. The risk is real — every ask can make the AD walk
  away (a pulled job offer is gone; pulled extension talks mean you play out your deal, or leave if it's
  expiring). ADs have short, normal or long patience, harder asks are riskier, and the risk climbs with
  every counter. And he remembers: whatever you squeeze out of him, your seat starts that much warmer
  (taking less base for bigger bonuses cools it). You set salary and years when you hire coordinators —
  they can say no — and decide whether to re-sign them when their deals are up.

## Strength of schedule  (tab 5 RANKINGS → [O], tab 2 → [O], or [S] on any team schedule)
Every FBS schedule is rated the way the committee reads it: each opponent's roster plus his record (blended
with last season's early in the year; an FCS school counts as a weak roster at .300). Every team is ranked
1-138 on its full schedule, the games played so far, and the games still ahead, with a word (brutal, tough,
average, soft, very soft) and its opponents' combined record. It shows under the record on every team's
schedule, on the team page, in the dashboard's schedule panel and in the window sidebar; the rankings screen
sorts by any of the three, filters by conference, and keeps every finished season's final list. Coach Career
shows ranks and words only.

## The Playoff Rankings & the Selection Committee  (tab 5 RANKINGS → [P] / [C])
The Top 25 is the media poll. The **NP Playoff Rankings** are a separate list, and they're what seeds the
12-team playoff and fills the bowls.

- **The committee.** Twelve members — former coaches, former ADs, former players, a conference
  administrator, a university president, a sportswriter. Three-year terms, staggered, so a few seats turn
  over every winter; the open seats go to coaches who just retired in your world. Nobody votes on a school
  he's tied to.
- **How each member votes.** Everyone looks at the same résumé — record, strength of schedule, quality wins,
  bad losses, capped margin of victory, conference titles, the eye test (roster talent), recent form, and
  whether it came in the Group of Five — but weighs it his own way. Each member is a kind of voter
  (Résumé, Win-loss, Eye test, Old school, Analytics, Hot hand, Power-league, Big-tent) with procedurally
  rolled weights around a shared, sensible base, so ballots differ without anyone turning in a crazy one.
  Retired coaches vote the way they coached: aggressive coaches trust margin and talent, conservative ones
  want clean records, coaches who won outside the Power leagues don't discount it.
- **The rankings.** Each member hands in a Top 25. A team's committee number is its average ballot spot
  (off a ballot = 30), blended 70/30 with the media poll; head-to-head settles near-ties. First release after
  week 9, updated weekly, final after the conference title games.
- **See it all.** The rankings show committee average, first-place ballots, Media rank and the projected (or
  seeded) field. Open any team to see where every member put it and the résumé they read; open any member
  to see how he weighs things and his whole ballot next to the committee's. Former members and each year's
  final top four are kept.

**Campus Countdown on simmed weeks.** Simulate Multiple Weeks (and turning the show off in Settings) skips the
broadcast, but the crew still chooses the week's campus and makes every pick, so the site history and the
season-long pick standings keep counting.

## Recruiting  (tab 4 RECRUITING)
Recruiting is persuasion, not shopping. Roughly 1,950 prospects come out each cycle. Every one has
real ratings you can't see, a **public star rating that is national opinion** (about one in six is
rated a full star off what he actually is, which is where busts and steals come from), three hidden
priorities, and a personality that decides how he reacts when his school loses or another program
comes calling.

Your staff gets a pool of **hours** each week, set by the head coach's recruiting rating and cut
during the season. You spend them on evaluations, calls, offers, position-coach trips, campus
visits, in-homes and closing pushes. Evaluating buys *information only* — it narrows a recruit's
projected range and reveals his priorities, and gives no ground on the pitch. That trade-off is the
whole game.

Interest is driven by whether your program is good at the things *he* cares about: playing time
comes off your depth chart, development off your coach's position ratings, winning off the poll,
plus scheme fit, academics, facilities, tradition, campus and distance from home. Gains shrink as
interest climbs, interest decays every week you go quiet, nothing gets past a hard ceiling until you
actually offer, and campus visits are tied to the real schedule — he attends a home game, and a win
over a ranked team is worth far more than a blowout of an FCS opponent.

Rosters are hard-capped at the scholarship template, so a class that comes in over the limit at a
position costs somebody a spot — walk-ons and the lowest-rated reserves first, never a starter.
Walk-ons themselves are unrated (0 stars) and sit a clear notch below the players a staff actually
recruited, so you can always tell the difference on a roster page.

Commitments build through the fall, recruits decommit and flip, and signing day resolves the rest.
Classes are ranked nationally the way the services do it, weighted toward top-end talent — see the
final class rankings after every signing day, or from the recruiting menu during the season. Players
who picked a school that matched their priorities carry a **fit bonus** and develop faster; bad fits
stall out. You see ranges, not ratings, and words, not numbers.

### Standing orders  (recruiting hub → [Q], or [Q] on any recruit's card)
Any action on any recruit can be a standing order: **once**, **every week**, **every other week**, **for N weeks**,
or **every week until he commits**. Every order sits in one queue, in the order you choose — the same recruit can
be in it as often as you like ("call Johnny, call Steven, call Johnny again, call Richard"). At the end of each
week the queue spends the hours you didn't, top to bottom. An order that doesn't fit is **cut** (a cheaper one
further down still runs), and the queue screen shows, before the week ends, exactly which orders will run and
which will be cut — with a line where the hours run out. [M 3 1] moves an order, [T#] sends it to the top, [C#]
copies it, [E#] changes how often it repeats, [X#] removes it, [R] runs it now. Calls and visits in the queue sell
the best thing your staff knows he wants. **Coordinator autopilot** ([O]): your OC and DC can work their side of
your board on their own after the queue runs, with an hour cap you set. A weekly Recruiting report lands in your
inbox: what ran, what was cut, visits, commitments, rating changes, what rivals said about you.

### Official visits  ([V] on a card, or the hub → [V])
Five per recruit, one per school, booked for one of your home games (4 hours). The Saturday decides it: the
result, who you played, the rivalry, the crowd and how loud it got, a night game, your stadium (the recruiting
lounge especially) — weighted by what he cares about. Every visit writes a report: a home run, a good weekend,
flat, or a bad weekend, and where you stand before and after. CPU staffs book visits too, and five-stars' visits
make the news.

### Pitches
Calls, position-coach visits and in-home visits are conversations: pick what you sell him on. Hit something he
cares about and it lands (harder the more he cares, and the better your case) — and now you know it. Miss and he
checks his phone. It's a second way to learn his priorities besides film.

### The living trail
Every recruit plays a senior season: his stats and his team's record update on his card each week. The ratings
services re-rank everyone in Weeks 5, 9 and 13 — risers and fallers make the wire. In the preseason, run a
**summer camp** (hub → [C]): up to 12 kids from your board come to campus; your staff learns a lot about them and
tells you who looked better than his rating. The camp circuit makes a few unknowns into names every summer.

### Commitments, the crystal ball and signing days
Commitments are **hard** (locked in) or **soft** (still listening) — soft ones decommit and flip far more often.
Some kids **commit silently**: to everyone but that school he still looks open, until he announces it weeks later.
The **crystal ball** predicts where uncommitted kids land (on the card, the war room and the wire), and "trending"
news follows the swings. The **early signing period** (NP First Round week) locks most hard commits in; soft
commits and the undecided wait for **National Signing Day**, where some soft commits flip — and you watch it
**live**: hats on the table, one kid at a time, your board first.

### Rivals fight back
Rival staffs use what they can against you: your hot seat ("you won't be there in a year"), your record, a
position room you've already stacked. From Week 11, collectives get into **NIL bidding wars** over the four- and
five-stars you're paying. And a kid will ask why you already have three quarterbacks committed — a crowded room
makes every pitch at that position land softer.

### Pipelines
Every recruit has a high school. Sign kids from a school and it becomes a pipeline: pitches to its players land
harder and your staff gets free intel on them. Break a promise to one of its kids, or cut one at signing day, and
that school goes cold. Ties fade a little every year.

### More ways to find players
**JUCO transfers** (JC in the finder): older, ready now, less upside — they arrive as juniors. **International**
kickers and punters (INT): big legs from ProKick Australia and the Pro League academies. **Preferred walk-ons** (hub →
[L] from Week 8, or [W] on a 1-2 star's card): no scholarship, a roster spot and a shot; the good ones earn a
scholarship.

### The war room and hit or bust  (hub → [W], [H])
Your own ordered big board: move players up and down, tier them, and see each one's standing, commitment type,
crystal ball, official visit and standing orders at a glance, with your class needs, a class goal you pick, and
your pipelines. **Hit or bust** grades every class you've signed on what the players became: hit rates by star
rating, your best steals and your biggest misses.

## Transfer Portal  (tab 4 RECRUITING → [P])
The portal opens every offseason, between class advancement and the arrival of the freshman class,
so a team that loses a starter still has a window to replace him.

Players enter for reasons they actually have: buried on the depth chart, a bad fit from the day they
signed (the recruiting fit bonus tracks this), no development, or a losing program. Starters who are
playing well and winning don't go anywhere; the two-deep and the misused four-stars do. Teams shop
with the same pitches recruiting uses, but the market prices *immediate help* — being better than
the man currently starting is worth more than a rating, and quarterbacks move the market.

The window runs in three rounds, with standards dropping each time: the first is the frenzy at the
top of the board, and by the third staffs are filling a two-deep rather than handing the spot to a
walk-on. Roughly 88% of the portal finds a home. Everyone else is out of the sport, which is what makes
entering it a real decision. Good players move up or sideways; the bottom of the portal doesn't move
at all. The portal screen shows the top transfers nationally, your own ins and outs, and the biggest
hauls of the window.

## Top 25 & Golden Helmet  (tab 5 RANKINGS → [T] / [H])
A preseason poll is built from program prestige, roster strength and last year's record, then
re-voted every week the way human voters actually behave: ballots are sticky, so teams move in
steps (at most 7 spots up or 14 down in a week); losses cost more than wins and *who* you lost to
matters most; undefeated teams get protected; idle teams barely move; and strength of schedule
plus a Group of Five discount keep unbeaten mid-majors in their realistic lane. Movement arrows and
"also receiving votes" are shown, and ranks appear on scoreboards, matchup cards, team pages and
the schedule browser.

The Golden Helmet race is a weekly straw poll: production weighted by position (voters start with
quarterbacks), scaled by team success and poll rank, with defenders needing a monster year. Each
candidate shows his season line, and the board tracks week-to-week movement.

## Schedules
Each season is generated fresh so that every FBS team plays 12 games in 13 weeks:

- **Conference games first**, since they're the most constrained. Every team in a league plays the
  same number of league games — 9 in the SCC, Continental, Seaboard and Meridian, 8 in the Group of Five
  leagues, 7 in the eight-team Golden West — laid out so nobody plays twice in a week. Conference play
  leans to the back half of the season.
- **Non-conference games are scheduled the way athletic directors actually do it** — not as a
  gauntlet. Every program decides what it wants from its open dates, then games are matched so both
  sides get what they were shopping for:
  - **Power programs** keep one marquee Power-4 game (or their protected rival), buy one or two Group
    of Five opponents, and pay an FCS school for an early win. The SCC always plays at least one
    Power-4 opponent; the Continental plays fewer FCS games. About one in ten Power teams schedules two
    Power opponents; almost nobody schedules three.
  - **Group of Five programs** take one or two "guarantee checks" on a Power team's field, play a
    regional G5 neighbour, and host their own FCS game.
  - **South Bend** books a national, Power-heavy slate first; **Connecticut** schedules like a G5 program.
  - Matchups lean regional, and buy games are played at the bigger program (about one in ten is the
    return trip of a home-and-home).
- **FCS guarantee games** are played at the FBS team's stadium, early, and usually against a school
  from the same part of the country. Seventy FCS programs (Montana, Macon, Clarksville,
  Tennessee State, Main Line, Jackson State, Bethlehem and more) sell one or two games apiece, win about
  9% of them, and stay out of the standings, recruiting and development entirely. Their rosters are
  rebuilt every year.
- Power programs usually finish with 7 home games and Group of Five programs with 5-6; the data check
  on launch verifies all 138 schedules (12 games, 5-8 home games each).

## Files
- `main.py` – entry point
- `MANUAL.txt` – the full manual; `manual.py` – the in-game viewer for it (contents, chapters, search)
- `weather.py` – climate, weather systems, forecasts, in-game conditions and their effects on the field
- `weather_screens.py` – the Weather Center
- `saves.py` – save, load, autosave, and the save/load screens
- `preseason.py` – the preseason week: fall camp and custom non-conference scheduling
- `presser.py` – the press conference: situational questions and answers
- `week.py` – the week hub: film, practice focus, press conference
- `people.py` – the inbox: your AD, players, recruits and staff reaching out
- `inbox_scenarios.py` – the rest of the season's dilemmas (injuries, travel, tampering, donors, scouts...)
- `effects.py` – what inbox and podium answers do, how they're described, and results that ride on later games
- `podium.py` – press-conference tones, follow-up questions, and the podium summary
- `postgame.py` – the postgame press conference
- `december.py` – championship week, bowls, opt-outs, the playoff, early signing, the portal window
- `morale.py` – every player's mood and what it does
- `halftime.py` – your halftime adjustment and message
- `promises.py` – recruiting promises that follow players to campus
- `ad_trust.py` – what your AD remembers about you
- `skills.py` – your coaching tree: points, perks, forks, respec, the screen
- `dashboard.py` – the main-menu dashboard: header, tabs and live panels
- `screen_copy.py` – records the screen and copies it to the clipboard (Auto copy output)
- `finance.py` – budgets, coaching contracts, buyouts, renewals, NIL offers and deals
- `finance_screens.py` – the budget screen, payroll, every program's budget, NIL offers
- `staff.py` – coordinators, their resumes, and the staff carousel
- `staff_screens.py` – running your own staff in Coach Career mode
- `archive.py` – every finished season's games and box scores
- `models.py` – `Player` and `Team` classes, position weights, proficiency rules
- `teams_data.py` – all 138 FBS programs for 2026 (edit ratings here)
- `coaches_data.py` – 2026 head coaches + reputation-based rating overrides
- `roster.py` – recruits (from star ratings), opening rosters, signing classes
- `development.py` – the offseason development algorithm
- `season.py` – schedule generator, weekly games, postseason bracket, offseason
- `postseason.py` – bowl and NP venues, dates and rotation, national champion history, game stakes
- `carousel.py`, `coach_screens.py` – coaching careers, ADs, program goals, the carousel
- `gameday_show.py`, `gameday_dossier.py` – the Campus Countdown show and its storylines
- `gameday_cast.py`, `gameday_scenes.py`, `gameday_more.py` – Campus Countdown cast and content
- `campus_towns.py`, `settings.py` – datelines; saved settings
- `career.py` – your coach, job offers, earned traits, spectator mode
- `coach_mode.py` – calling plays yourself
- `media_center.py` – headlines, awards, leaders, hot seats, injuries, projections
- `draft.py`, `awards_screens.py` – awards season and the Pro League Draft
- `broadcast.py` – game dates, kickoff times and TV windows
- `portal_screens.py` – your transfer portal window
- `rankings.py` – the Top 25 poll and the Golden Helmet race
- `committee.py`, `committee_screens.py` – the Selection Committee and the NP Playoff Rankings
- `traits.py` – personality traits for players and coaches
- `portal.py` – the transfer portal: who leaves, who takes them, who lands nowhere
- `recruiting.py` – prospects, pitches, interest, commitments, signing day
- `recruiting_data.py` – states and talent, program home states, priorities, personalities, actions
- `recruiting_screens.py` – the recruiting interface
- `fcs_data.py` – 70 FCS programs (and their home states) used for guarantee games
- `playbook.py` – routes, offensive plays, defensive calls, coaching schemes, situational play calling
- `engine.py` – resolves each snap: trench battles, run fits and tackles, protection, routes and
  separation, QB progression and pocket movement, throws, yards after catch, special teams
- `game_sim.py` – game flow: clock, downs, drives, scoring, kicks, timeouts, overtime, box score
- `booth_lines.py` – every phrasing the booth can use, pooled by moment
- `booth_banter.py` – between-play conversations: off-topic banter, analysts' playing-days stories, weather
- `commentary.py` – the broadcast booth: play-by-play voice, color analyst, between-play
  conversation, rivalry names, box score layout
- `momentum.py` – the bounded momentum meter and home-crowd effects
- `injuries.py` – injury rolls, severity, weekly healing
- `league.py` – holds the teams, conferences, standings ordering, search, data validation
- `screens.py` – main menu, standings, team view, roster, player card
- `universe.py` / `world.py` – universes: which programs, coaches and names a world uses; universe files live in `universes/`
- `links.py` – every name the window turns into a link, and the page each one opens
- `ui.py` – colors, bars, layout helpers, title art
- `names.py` – name pools

## How a play is simulated
Every rating in a game is an *applied* fundamental: the raw fundamental × the player's proficiency
at the position he's lining up at.

1. **Play calls.** Each head coach has an offensive scheme (Air Raid, Spread RPO, Pro Style, West
   Coast, Smashmouth, Triple Option, Power Spread, Veer & Shoot), a defensive scheme (4-3 Zone,
   4-2-5 Quarters, Pressure 3-4, 3-3-5 Stack, Multiple Man, Tite Front), an aggression rating, and
   his own personal lean on every play and coverage, including a few signature calls he goes to
   more than anyone else in his scheme. In-game both staffs adapt: they go back to what's working,
   avoid repeating themselves, punish blitz-heavy defenses with screens and draws, load the box
   against run-heavy offenses, spy mobile quarterbacks, bracket star receivers, and adjust at
   halftime. 53 offensive plays (including reverses, flea flickers, halfback passes, fake punts and
   fake field goals) and 20 defensive calls. The offense picks run/pass, personnel and a
   play from down, distance, field position, quarter, clock and score (two-minute drill, clock
   milking, kneel-downs, Hail Marys, 4th-down go/kick/punt, two-point chart). The defense sees the
   personnel and picks a coverage/pressure for the situation.
2. **Runs.** Point of attack (linemen vs the defensive lineman at the gap, double teams, pullers,
   box count vs blockers) → second level (climbing blocks, unblocked defenders reading and fitting
   their gap, misdirection) → alley and secondary (pursuit angles, speed) → open field.
3. **Passes.** Each rusher vs his blocker produces a time-to-pressure; unblocked blitzers get home
   fast. Each receiver runs a route with its own depth and break time; separation comes from route
   running vs the defender in man or the zone defender for that area, plus scheme matchups (smash vs
   Cover 2, seams vs Cover 3, rubs vs man, high-low stretches, safety help). The QB reads in order at
   a speed set by his IQ, climbs or slides when pressure arrives, escapes, scrambles, throws it away,
   goes hot vs the blitz, or takes the sack. Throws resolve from accuracy, arm vs depth, window and
   pressure (drops, breakups, interceptions, pass interference), then yards after catch.
4. **Every tackle is attributed with a reason** – who made it and why (shed a named block, unblocked
   in a heavy box, came downhill from the deep half, ran him down from behind, and so on).

5. **Momentum, crowd and injuries.** One momentum meter (-100 to +100) moves on big plays and
   bleeds back toward zero every snap; at most it is worth ±2 rating points, halftime wipes most of
   it out, and blowouts barely feed it. Home crowds add a real edge and make road offenses jump
   offside; neutral-site rivalries (Georgia–Florida, Texas–Oklahoma, Hudson–Chesapeake) have no home team.
   Every contact carries an injury risk scaled by the player's Durability: shaken up, out for the
   game, 1-3 games, 4-8 games, or season-ending. Depth charts reshuffle mid-game, ratings drop while
   starters are out, injuries heal weekly, and everyone is back by fall camp.
6. **Game day.** Each team gets a small random "form" swing for the day. In blowouts the leader
   pulls starters, runs clock, and eventually kneels; a trailing team stops gambling once it's hopeless.

Calibrated across thousands of simulated games to FBS norms, per team per game: ~26 points,
~70 plays, ~5.2 yards per play, ~4.1 yards per carry, ~64% completions, ~2.5 sacks,
~0.8 interceptions, ~37% on third down, ~0.9 injuries.

Rosters are deliberately polar — the best programs sign blue-chippers and rate in the mid-80s while
the bottom of the sport sits in the mid-50s — but the play engine is forgiving enough that talent
alone doesn't decide games. Evenly matched teams produce upsets about 45% of the time, a 4-8 point
rating edge holds up about 80% of the time, and a 12+ point edge almost always does. Home teams win
about 57%, roughly 4% of games go to overtime, and a handful of 60-point games happen a year.


## Rivalries & series history
Every game two FBS programs play goes into a series book the moment it ends. Team page → **[V] Rivalries**
shows a program's rivals and trophy games (series since 2026, current streak, who holds the trophy, the last
meeting) plus its most-played opponents; type any school for the full head-to-head: every meeting, the
longest streak, the biggest blowout and the closest finish. 48 trophies are tracked — the Bronze Heifer,
the Northwoods Saw, the Magnolia Cup, the Copper Kettle, the Canyon State Cup, the Silver State Howitzer and the rest.

The booth reads the book. Before kickoff they know the series and the streak, what's on the line and who has
it, and when these two met last — last year, or in a bowl four years ago — including who hurt whom that day.
Mid-game they bring up the old blowout or the one that went to the wire. After the final: who keeps the
Jug, who takes it back (and how long the other side had it), whose streak just died. The matchup card shows
the series too. Older saves build the book from their archived seasons on load.

## Conference realignment
From the winter after 2026 on, schools change leagues for the reasons they really do. Each program has a TV
value — brand (tradition, prestige), how it's winning over the last four years (titles and playoff trips
count extra), its home TV market and its crowd. Each league pays every member the same media check; deals
run 6-10 years and are renegotiated from what the membership is worth at renewal, so a league that loses
its brands gets a smaller check next time.

Leagues with room invite schools that would raise their value, and a league about to fall below eight
backfills from the leagues below it. A school says yes when the new money beats the exit fee (three years of
payout from a Power league) with room to spare — distance, leaving its rival behind, and a proud
independent's independence all argue against it. Moves are announced one winter and happen the season after
next. Split-up traditional rivalries become protected non-conference games. The Power leagues stay the Power
leagues; who's in them changes. Budgets move with the money (half the difference reaches football).

News lands on the Wire, in the offseason report and the season-sim summary; team pages show where a
school came from and where it's headed. In **Athletic Director mode**, an invitation to your school is your
call. In a coach career, your AD tells you when you're moving.

## Players as people
Built on the personality traits every player already carries:
- **Captains** — every August each team votes three (sometimes four): upperclassmen who lead, never the
  divas. The booth mentions them; they call players-only meetings when things go sideways.
- **Locker-room chemistry** (0-100) — winning warms it, losing streaks and blowups cool it, leaders and a
  Players' Coach hold it together. Worth up to about a point either way on Saturday. Team page → **[K]
  Locker Room** shows the temperature, the leaders and the wild cards.
- **Incidents** — suspensions for hotheads, divas venting online after a loss, practice fights, players who
  check out. League-wide ones hit the Wire; on your team, they land in your inbox and you decide (sit him,
  handle it internally, dismiss him; back him or bench him).
- **NIL raises** — after the title game, underpaid starters ask for a raise, and the Mercenaries and
  spotlight-chasers add "or I'm in the portal." Pay, counter, or refuse; refuse a threat and he's very
  likely gone. AI programs make the same call with the same money.
- **Leaving early** — draft-eligible underclassmen decide from where they project and who they are: the
  Loyal kid and the captain come back more often, the spotlight-chaser goes, big NIL keeps mid-rounders home.
  On your team, you get a sit-down with each one projected in the first five rounds: make the case to stay,
  or tell him he's earned it. Before the offseason starts, the game walks you through every one of these.

## Sim calibration
Measured over full simulated seasons against real FBS per-team averages: about 27-28 points a game,
7.3-7.4 yards per pass attempt, 64% completions, 2.2 sacks and 4.5 tackles for loss a game; single-season
leaders land around 13-16 sacks, 19-24 TFL, 1,800-2,300 rushing yards. The knobs live at the top of
`engine.py` (TUNING) and `FG_RANGE_BASE` in `playbook.py`.

## Instant Classics
Every game is judged the moment it ends, however it was played: watched snap by snap, coached, fast-simmed,
or simmed thirty seasons at a time. The ones that earn it go into the Instant Classics book for good:
huge upsets (an unranked team over a top-five one, an FCS school over anybody, a Group of Five team over a
Power program), overtime marathons (the more overtimes, the better), finishes nobody will believe (the
go-ahead score in the last thirty seconds, at the gun, the overtime walk-off), big comebacks, lead change
after lead change, shootouts, record-book performances (500 passing, 300 rushing, 250 receiving, seven
touchdowns, five sacks, three picks), and great games with big stakes (ranked against ranked, rivalry and
trophy games, the playoff). Stakes lift a great game; they never turn a blowout into one. The very best are
marked LEGENDARY (★★). A typical season adds around twenty.

**Media Center → [14] Instant Classics** (or a team page → **[I]**) lists them by greatness or by date,
filtered by season. Open one for its headline, why it made the book, the line score, and the scoring
summary with the running score, then **[B]** for the full box score and every player's stats (from the
season archive once the season is over). New classics show up with a ★ on the week's results, on the Wire,
and in the season-sim summary.

## The changing of the guard
A program's standing isn't fixed at the start of the world anymore. **Prestige** has two halves, and both move:
- **Legacy (tradition)** covers the decades. Every season it drifts toward the program's last dozen years of
  results. A decade of winning adds real points and a decade of losing takes them away, but slowly: the blue
  bloods stay blue bloods for a while.
- **Brand** covers the last five seasons, the most recent counting most: wins, final poll finish, playoff trips
  and wins, titles, league titles, bowl wins. It moves fast, and recruits, transfers and every staff's
  recruiting board read it. A hot program recruits like one; a fading blue blood feels it.

On day one prestige equals the old number exactly; after that it's earned. **Money** follows: budgets can grow
to twice where they started (or fall to 60%) with sustained winning, a rising brand, or losing. Every winter,
rarely, the unplanned happens: a **booster windfall** (a mega-donor or new collective: a big budget jump and a
rebuilt facility, likelier at a rising program), or **CAB sanctions** (a postseason ban, two years of
recruiting restrictions, a brand hit, and a hot seat).

**Coaches** are more variable, and great ones are rarer. Only a couple of coaches start the world at 90 or
better. Most coaches have only a few points of room to grow; about one in six has real upside, and about one
in twenty-five is a genius who can climb into the 90s. ADs hire on *reputation*, not the true number: a coach
who has never run a program can be badly misjudged either way, and the miss shrinks as he builds a record.
Every coach also has a hidden fit with each school (some pairings just click on Saturdays; some never do),
and year-to-year growth is streakier.

**Media Center → [15] Parity Report** tracks it all: how many different programs finished in the top 10, made
the playoff, and won it, by decade; the biggest risers and fallers since 2026; the most prestigious programs
now against where they started; and every booster windfall and sanction.


### Custom player databases
Place `.json` databases in `custom players`. They are applied after the four-season history simulation, just before the 2026 career begins. The bundled expanded database contains 476 real 2026 players across 120 programs.
