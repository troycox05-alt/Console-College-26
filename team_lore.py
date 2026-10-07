"""
team_lore.py — What the booth knows about each program: traditions, history,
legends, and the things every broadcast crew mentions when it visits.

Every Power 4 school plus the flagship independent. Each line is (moment, speaker, text):

  any        can be said anytime, home or away
  home       only when the team is playing in its own stadium
  pregame    home-stadium entrance traditions, said before kickoff
  q1 / q3    home crowd traditions at the end of the 1st / 3rd quarter
  td         after a home touchdown          first_td  after the first home score
  win        after a home win

Speaker "P" is the play-by-play voice, "A" the analyst. {school} and
{stadium} are filled in by the narrator.
"""

TEAM_LORE = {
    'Alabama': [
        ('pregame', 'P', 'Each Ironclad strikes the old anvil at the Foundry Gate on the way out.'),
        ('win', 'P', 'Listen to that — the old ironworks steam whistle. They blow it after every win.'),
        ('any', 'A', "Coach Amos Redding's teams won eleven conference titles in fourteen years. That's the standard here."),
    ],
    'Arkansas': [
        ('pregame', 'P', 'A smith from the Ozarks forges a blade in the north end zone and hands it to the captain before kickoff.'),
        ('home', 'A', 'Sparks fly from the end-zone forge after that home touchdown.'),
        ('any', 'A', 'The unbeaten 1964 Bladesmiths are still the standard in this state.'),
    ],
    'East Alabama': [
        ('home', 'A', 'Every Longleaf touches the Old Longleaf, a two-hundred-year-old pine at the tunnel mouth.'),
        ('win', 'P', "They'll hang pine-straw garlands on the oaks downtown tonight. That's how this town celebrates a win."),
        ('any', 'A', "Halfback Cyrus Bell's 1985 Golden Helmet season still comes up every time a Longleaf breaks one."),
    ],
    'Florida': [
        ('home', 'A', '{stadium} sits below street level, and everybody calls it the Pit. It holds the heat and the noise.'),
        ('q3', 'P', 'Before the fourth, the Pit opens its jaws — every arm in the place snapping shut together.'),
        ('any', 'A', "Quarterback Wes Darby won three straight state titles here in the '90s."),
    ],
    'Georgia': [
        ('home', 'A', "The Marauders' flag comes in on horseback down the sideline before every home game."),
        ('win', 'P', 'The Old College bell will ring until midnight after this home win.'),
        ('any', 'A', 'Coach Vernon Tate won back-to-back national titles here. The trophies sit right by the front door.'),
    ],
    'Kentucky': [
        ('pregame', 'P', 'A bugler plays the call to post as the Thoroughbreds come out.'),
        ('win', 'P', 'The paddock gate behind the north end zone swings open for the seniors after a win.'),
        ('any', 'A', "Coach Bartley Shaw's 1950 team upset the No. 1 team in the country on New Year's Day."),
    ],
    'Bayou State': [
        ('home', 'A', 'Night game in Baton Rouge — the Gars come down Red Stick Hill through a tunnel of torches.'),
        ('td', 'P', "And the brass band strikes up 'the Gar Rag' after that home score."),
        ('any', 'A', 'Three national titles in a decade, and the Midnight Interception of 2007. This place has seen some things.'),
    ],
    'Mississippi State': [
        ('home', 'A', 'Hoofbeats over the PA, and the Stallions charge out behind a riderless black horse.'),
        ('win', 'P', 'The whole stadium stamps the bleachers in a slow gallop after a win.'),
        ('any', 'A', 'Running back Leroy Pettis ran for two thousand yards here in 1998.'),
    ],
    'Missouri': [
        ('pregame', 'P', 'A pair of mules pulled the game ball in on a wagon before kickoff. Only in Columbia.'),
        ('home', 'A', 'Students in straw hats line the Hinkson Creek hill all game long.'),
        ('any', 'A', "The 1960 Mules finished No. 1 in one poll, and you'll hear about it if you spend a day in town."),
    ],
    'Oklahoma': [
        ('pregame', 'P', 'Tornado sirens wind up as the Twisters run out of the tunnel.'),
        ('home', 'A', "There's the siren — they sound it after every home touchdown."),
        ('any', 'A', 'Seven national titles and five Golden Helmets. Few programs anywhere can match that.'),
    ],
    'Mississippi': [
        ('home', 'A', 'The tailgating under the magnolias on Lafayette Hill is as old as the program itself.'),
        ('win', 'P', 'A riverboat horn sounds from the stadium roof after a Rivermen win.'),
        ('any', 'A', "Quarterback Dell Ransom's 1969 comeback over the Ironclads is still the most famous game in Oxford."),
    ],
    'South Carolina': [
        ('pregame', 'P', 'Smoke, then flames — the Firebrands come out through a ring of fire.'),
        ('q3', 'P', 'Fourth-quarter torches light up the upper deck at {stadium}.'),
        ('any', 'A', 'Three straight eleven-win seasons under Coach Ward Abernathy. The best run this program has had.'),
    ],
    'Tennessee': [
        ('home', 'A', 'Fans come to this one by boat — the Holston Fleet docks right beside the stadium.'),
        ('win', 'P', 'The band forms the Long Trail for the team after a win.'),
        ('any', 'A', 'The 1998 national champions. They still sell the T-shirts on every corner.'),
    ],
    'Texas': [
        ('pregame', 'P', 'Six riders lead the Stampede out at a full gallop.'),
        ('win', 'P', 'The stands roll in a rumbling stampede after a Texas win.'),
        ('any', 'A', "Quarterback Ray Cordova's last-second drive in the title game is the moment everybody here remembers."),
    ],
    'Brazos': [
        ('pregame', 'P', "The Wranglers' riders form a lasso circle at midfield before the kickoff."),
        ('home', 'A', 'The student section stands the entire game. They call themselves the Standing Herd.'),
        ('any', 'A', 'The 1939 national champions. Ask anybody in College Station.'),
    ],
    'Nashville': [
        ('home', 'A', 'A different songwriter plays the Troubadours out every home game.'),
        ('win', 'P', "The whole stadium sings 'Cumberland Night' after a win."),
        ('any', 'A', "Coach Clay Dunbar's upset of the No. 1 team in 2024 put this program back on the map."),
    ],
    'Illinois': [
        ('pregame', 'P', 'Students light prairie torches all along Boneyard Creek before kickoff.'),
        ('td', 'P', 'The end-zone flame cannon fires after that home score.'),
        ('any', 'A', "Linebacker Jack Pruszynski, a two-time All-American, is still the toughest player they've ever had."),
    ],
    'Indiana': [
        ('home', 'A', 'The seniors carry out a block of Indiana limestone and set it at midfield.'),
        ('win', 'P', 'After a home win the seniors carve the score into the Quarry Wall.'),
        ('any', 'A', 'The 2024 Quarrymen went from afterthought to playoff team in a single season.'),
    ],
    'Iowa': [
        ('pregame', 'P', 'A combine leads the Harvesters out of the north tunnel.'),
        ('q3', 'P', 'The Harvest Moon — phone lights everywhere as the fourth quarter starts.'),
        ('any', 'A', 'Coach Abel Krause spent twenty-six seasons on this sideline.'),
    ],
    'Maryland': [
        ('home', 'A', 'Every Watermen player touches the crab pot hanging over the tunnel.'),
        ('home', 'A', 'Steamed-crab tailgates ring {stadium} from sunup.'),
        ('any', 'A', 'The 1953 national champions.'),
    ],
    'Michigan': [
        ('pregame', 'P', 'The seniors carry a birchbark canoe the length of the field before kickoff.'),
        ('win', 'P', "'Onward, Voyageurs' plays three times after a win. It's tradition."),
        ('any', 'A', 'Eleven national titles and three Golden Helmet winners in Ann Arbor.'),
    ],
    'Michigan State': [
        ('pregame', 'P', 'The Foresters run out under crossed axes held by the senior class.'),
        ('win', 'P', 'The Red Cedar Stone gets a fresh coat of paint after every home win.'),
        ('any', 'A', "The 'Ten-Ten Teams' of 1965 and '66 are still the gold standard in East Lansing."),
    ],
    'Minnesota': [
        ('pregame', 'P', 'Snow cannons blast white confetti over the tunnel as the Blizzard comes out.'),
        ('home', 'A', "'Snow Day!' from all four sides at the end of the first quarter."),
        ('any', 'A', "Five national titles in the 1930s and '40s. History runs deep here."),
    ],
    'Nebraska': [
        ('pregame', 'P', 'The Sodbusters run out over a strip of fresh-cut sod.'),
        ('win', 'P', 'Fans turn a spade of sod outside the stadium after every win.'),
        ('any', 'A', 'The four-title run of the 1990s — some of the best teams the sport has ever seen.'),
    ],
    'Lakeshore': [
        ('home', 'A', "Storm flags are flying off the stadium roof. That's the Gales' welcome."),
        ('win', 'P', 'The lake wind decides games here — the captains checked it before the coin toss.'),
        ('any', 'A', "The 1995 Gales went from nowhere to New Year's Day."),
    ],
    'Ohio State': [
        ('home', 'A', 'The captains carry the Vanguard standard out first.'),
        ('win', 'P', 'The Olentangy carillon rings the fight song after a win.'),
        ('any', 'A', 'Eight national titles and seven Golden Helmets.'),
    ],
    'Oregon': [
        ('pregame', 'P', 'The scoreboard rain machines mist the field as the Rainmakers come out.'),
        ('home', 'A', '{stadium} is the loudest small stadium in the country. You can feel it up here.'),
        ('any', 'A', 'The 2010s Rainmakers scored fifty a game at the fastest tempo in the sport.'),
    ],
    'Pennsylvania': [
        ('pregame', 'P', 'The furnace bell rings as the Ironmasters come out.'),
        ('q3', 'P', "Here comes 'the Pour' — section to section, back and forth before the fourth."),
        ('any', 'A', 'Coach Elias Brenner coached forty-six seasons here.'),
    ],
    'Tippecanoe': [
        ('pregame', 'P', 'A rivet gun fires as the Riveters take the field.'),
        ('win', 'P', 'The engine whistle blows after a Riveters win.'),
        ('any', 'A', 'Three Riveters quarterbacks went first overall in the pro draft.'),
    ],
    'New Jersey': [
        ('pregame', 'P', 'The Pinebarons come out through a tunnel of pitch pine.'),
        ('win', 'P', 'Fans light Pine Barrens lanterns all over the lots after a win.'),
        ('any', 'A', "The Pinebarons claim the oldest program in the country, and they'll tell you about it."),
    ],
    'Los Angeles': [
        ('home', 'A', 'The sun drops behind the Arroyo hills — no prettier setting in the sport.'),
        ('td', 'P', 'The surfboard drumline breaks out after that score.'),
        ('any', 'A', "Quarterback Gus Alvarado's 1998 season is the one they all measure against."),
    ],
    'Southern California': [
        ('pregame', 'P', 'A drumline leads the Sundogs down the Figueroa steps.'),
        ('win', 'P', "The band will play 'Chase the Sun' on the field for twenty minutes after this win."),
        ('any', 'A', 'Eleven national titles and seven Golden Helmets.'),
    ],
    'Washington': [
        ('pregame', 'P', 'The Evergreens run out through the Mist Gate.'),
        ('home', 'A', "{stadium}'s roofs trap the noise on third down. Brutal for visitors."),
        ('any', 'A', 'The unbeaten 1991 Evergreens.'),
    ],
    'Wisconsin': [
        ('pregame', 'P', 'Fans march to the lakeshore to ring the Mendota bell before kickoff.'),
        ('q3', 'P', 'Here comes the Mendota Stomp to open the fourth quarter.'),
        ('any', 'A', 'Three Golden Helmet running backs have come through Madison.'),
    ],
    'Boston': [
        ('pregame', 'P', 'Two lanterns hang in the press box before kickoff. One if by land.'),
        ('win', 'P', "They'll light lanterns all along Chestnut Hill after this win."),
        ('any', 'A', "Linebacker Pat Keane's 2007 season still gets talked about around here."),
    ],
    'California': [
        ('home', 'A', 'Students were panning for gold in the creek outside the stadium this morning.'),
        ('td', 'P', 'The cannon on the hill fires after a Prospectors score.'),
        ('any', 'A', 'The 1937 national champions.'),
    ],
    'Upcountry': [
        ('pregame', 'P', 'Lights out, and the Hellcats come out of the cage gate.'),
        ('win', 'P', 'Students ring the old mill bell after a Hellcats win.'),
        ('any', 'A', 'Two national titles in three seasons. This is a big-time program now.'),
    ],
    'Durham': [
        ('home', 'A', 'The lights cut out and the Phantoms appear through the fog.'),
        ('home', 'A', 'The woods around {stadium} echo every big play.'),
        ('any', 'A', "Coach Gil Matheny's 1940s Phantoms were some of the best teams in the country."),
    ],
    'Florida State': [
        ('pregame', 'P', 'The Torchbearers run out carrying lit torches that ring the field.'),
        ('td', 'P', 'The torch line lifts after that home score.'),
        ('any', 'A', "Coach Ward Bellamy's fourteen straight top-five finishes."),
    ],
    'Atlanta': [
        ('pregame', 'P', 'A sparking dynamo at the tunnel throws arcs as the Dynamos come out.'),
        ('win', 'P', 'Students throw the giant breaker on the scoreboard after a win.'),
        ('any', 'A', 'The 1990 co-national champions.'),
    ],
    'Louisville': [
        ('home', 'A', 'A steamboat calliope plays the Steamers out of the tunnel.'),
        ('win', 'P', 'The Falls City Belle sounds her horn from the river after a win.'),
        ('any', 'A', 'Quarterback Jalen Archer won the Golden Helmet here in 2016.'),
    ],
    'Miami': [
        ('pregame', 'P', 'The Barracudas run out through a giant set of jaws.'),
        ('td', 'P', 'The whole crowd snaps the barracuda bite after that one.'),
        ('any', 'A', 'Five national titles between 1983 and 2001.'),
    ],
    'NC State': [
        ('pregame', 'P', 'A brass band rambles across the field before kickoff.'),
        ('q3', 'P', "Walnut Creek's tailgate smoke hangs over the fourth quarter."),
        ('any', 'A', 'The eleven-win 2002 Ramblers.'),
    ],
    'North Carolina': [
        ('pregame', 'P', 'A lighthouse beacon on the scoreboard sweeps the stands as the Keepers come out.'),
        ('win', 'P', 'The beacon spins after a Keepers win.'),
        ('any', 'A', 'The 1997 Keepers had the best defense this state has seen.'),
    ],
    'Pittsburgh': [
        ('pregame', 'P', 'Molten-steel pyrotechnics as the Smelters come out.'),
        ('td', 'P', 'The river horns blow after a Smelters score.'),
        ('any', 'A', 'Running back Earl Sweeney won the 1976 Golden Helmet here.'),
    ],
    'Dallas': [
        ('pregame', 'P', 'The end-zone derrick gushes confetti as the Wildcatters come out.'),
        ('win', 'P', 'The gusher fountain outside the stadium lights up after a win.'),
        ('any', 'A', 'The unbeaten 1982 Wildcatters.'),
    ],
    'Palo Alto': [
        ('home', 'A', 'Students plant a redwood seedling for every senior.'),
        ('home', 'A', "The redwoods around {stadium} swallow the noise. It's a strange quiet for a big game."),
        ('any', 'A', 'A long line of quarterbacks who went on to the pros came through Palo Alto.'),
    ],
    'Syracuse': [
        ('home', 'A', 'The captains throw a handful of salt on the field before the coin toss.'),
        ('home', 'A', 'The Dome is the loudest indoor stadium in the East.'),
        ('any', 'A', 'The 1959 national champions.'),
    ],
    'Virginia': [
        ('home', 'A', 'The Statesmen walk in down the Rivanna Steps.'),
        ('win', 'P', 'Students sing the Rivanna Hymn after a win.'),
        ('any', 'A', "Coach Calvin Hale's 1990 team got to No. 1."),
    ],
    'Blacksburg': [
        ('home', 'A', 'Lights out, and the stadium thumps along to the Ridge Drum.'),
        ('q3', 'P', 'Visitors feel the two-thousand-foot altitude by the fourth quarter.'),
        ('any', 'A', "Coach Delbert Haynes and his special teams — that was this program's identity for years."),
    ],
    'Winston-Salem': [
        ('pregame', 'P', 'Every spire in town rings its bell at kickoff.'),
        ('win', 'P', 'Students light the Spire with twinkle lights after a win.'),
        ('any', 'A', 'The 2006 Seaboard champions.'),
    ],
    'Arizona': [
        ('pregame', 'P', 'A desert-storm siren as the Gila Monsters come out.'),
        ('home', 'A', 'The Santa Catalinas glow at sunset behind the end zone.'),
        ('any', 'A', 'The twelve-win 1998 Gilas.'),
    ],
    'Arizona State': [
        ('pregame', 'P', "Fireworks shaped like a scorpion's tail as the team comes out."),
        ('home', 'A', 'Night game in the desert, and it was still a hundred degrees at kickoff.'),
        ('any', 'A', 'The unbeaten 1975 Scorpions.'),
    ],
    'Waco': [
        ('pregame', 'P', 'The Mammoths run out between giant mammoth tusks.'),
        ('home', 'A', 'Fans stomp three times after every Mammoths first down.'),
        ('any', 'A', "Quarterback Teddy Cole's record-breaking 2014 season."),
    ],
    'Provo': [
        ('pregame', 'P', 'A peregrine falcon flew the stadium before kickoff. Spectacular.'),
        ('home', 'A', 'The mountains behind the end zone light up at dusk.'),
        ('any', 'A', 'The 1984 national champions.'),
    ],
    'Cincinnati': [
        ('pregame', 'P', "The Sovereigns enter through the Queen's Gate."),
        ('home', 'A', '{stadium} is dug right into the hillside — one of the oldest stadiums in the country.'),
        ('any', 'A', 'The 2021 playoff team.'),
    ],
    'Colorado': [
        ('pregame', 'P', 'Horn blasts echo off the Flatirons as the Bighorns come out.'),
        ('home', 'A', 'The Flatirons fill the view behind the student section.'),
        ('any', 'A', 'The 1990 national champions.'),
    ],
    'Houston': [
        ('home', 'A', 'The pumpjacks on the concourse nod in time with the drumline.'),
        ('td', 'P', 'Black confetti geysers after a Gushers score.'),
        ('any', 'A', 'The thirteen-win 2011 Gushers.'),
    ],
    'Iowa State': [
        ('home', 'A', 'Thunder rumbles through the PA as fog pours out of the tunnel.'),
        ('home', 'A', 'This crowd stays to the end, even in the losing seasons.'),
        ('any', 'A', "Coach Earl Hansen's long rebuild turned this into a real program."),
    ],
    'Kansas': [
        ('pregame', 'P', 'A free-state flag gets run the length of the field before kickoff.'),
        ('win', 'P', "Students ring the Old Settlers' bell after a win."),
        ('any', 'A', "The 2008 New Year's Day win is still the high-water mark."),
    ],
    'Kansas State': [
        ('pregame', 'P', 'Fans wave blue towels over a prairie-burn video as the Bluestems come out.'),
        ('q3', 'P', 'That Flint Hills sunset over the fourth quarter — beautiful.'),
        ('any', 'A', "Coach Harlan Bishop took this program from worst to first in the '90s."),
    ],
    'Oklahoma State': [
        ('pregame', 'P', 'An outrider on horseback leads the team out.'),
        ('home', 'A', 'The student section never sits down here.'),
        ('any', 'A', "Running back Tyrell Sims's record 1988 season."),
    ],
    'Fort Worth': [
        ('pregame', 'P', 'The cattle-drive bell rings at kickoff.'),
        ('home', 'A', 'Stockyard tailgates will run until midnight tonight.'),
        ('any', 'A', 'The 1935 national champions.'),
    ],
    'Lubbock': [
        ('home', 'A', 'A red-smoke dust devil spins out of the tunnel with the team.'),
        ('home', 'A', 'Towels spinning in a dust-devil spiral on third down.'),
        ('any', 'A', 'The 2008 run to No. 2.'),
    ],
    'Orlando': [
        ('pregame', 'P', 'The launch countdown runs on the board before kickoff.'),
        ('td', 'P', 'Rocket smoke after that score, and the Launchpad is shaking.'),
        ('any', 'A', 'The unbeaten 2017 Rocketeers.'),
    ],
    'Utah': [
        ('pregame', 'P', 'Boulders roll down the video board as the Rockslides come out.'),
        ('home', 'A', 'The student section — the Slide Zone — never stops.'),
        ('any', 'A', 'The unbeaten 2008 team that crashed the big bowls.'),
    ],
    'West Virginia': [
        ('pregame', 'P', 'A bagpiper leads the Highlanders out.'),
        ('win', 'P', 'Sixty thousand headlamps light up after a win.'),
        ('any', 'A', 'The unbeaten 1988 Highlanders.'),
    ],
    'South Bend': [
        ('pregame', 'P', 'The Sentinels touch the Watch Bell on their way out of the locker room.'),
        ('home', 'A', 'The river and the spires behind the north end zone. Beautiful Saturday in South Bend.'),
        ('any', 'A', "Eleven national titles and seven Golden Helmets. There's no program with more mystique."),
    ],
}
