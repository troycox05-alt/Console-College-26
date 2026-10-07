"""names.py — Name pools for generated people, and the helpers that keep them apart.

The pools are big on purpose: a world holds ~12,000 players and ~600 coaches,
and a small pool puts two Browns in every backfield. Helpers:

  full_name(rng, avoid=...)   a first/last pair, never "Parker Parker", avoiding
                              surnames already taken nearby (a roster, a game, a show)
  surname(rng, avoid=...)     just a last name, same rules
  dedupe_roster(team, rng)    new-world cleanup: one of each surname per roster
"""

FIRST_NAMES = [
    "Aaron", "Abram", "Adrian", "Aiden", "AJ", "Alijah", "Alonzo", "Amari", "Amir", "Andre", "Andrew", "Anthony",
    "Antonio", "Armani", "Asher", "Austin", "Avery", "Beau", "Ben", "Bishop", "Blake", "Bo", "Bobby", "Brady",
    "Brandon", "Braxton", "Brayden", "Brennan", "Brock", "Bryce", "Byron", "Cade", "Caleb", "Calvin", "Cam",
    "Camden", "Carlos", "Carson", "Carter", "Casey", "Cedric", "Chance", "Chase", "Chris", "Christian", "Clay",
    "Cody", "Colby", "Cole", "Colin", "Colt", "Colton", "Conner", "Connor", "Corey", "Cortez", "Curtis", "Dak",
    "Dallas", "Damari", "Damien", "Damon", "Dante", "Darius", "Darnell", "Darren", "Davion", "Dawson", "DeAndre",
    "Deion", "Demarcus", "Demetrius", "Denzel", "Derek", "Derrick", "DeShawn", "Desmond", "Devin", "Devon",
    "Dexter", "Diego", "Dominic", "Donovan", "Drake", "Drew", "Dylan", "Eli", "Elijah", "Emeka", "Emmanuel",
    "Eric", "Ethan", "Evan", "Ezekiel", "Gabe", "Gabriel", "Garrett", "Gavin", "Grady", "Grant", "Griffin",
    "Hayden", "Hudson", "Ike", "Isaac", "Isaiah", "Ivan", "Jabari", "Jace", "Jack", "Jackson", "Jacob", "Jadon",
    "Jahmir", "Jake", "Jalen", "Jamal", "Jamarcus", "Jamari", "James", "Jameson", "Jared", "Jarrett", "Jason",
    "Javon", "Jaxon", "Jay", "Jaylen", "Jayden", "Jeremiah", "Jermaine", "Jesse", "Joel", "John", "Jonah",
    "Jordan", "Jose", "Josh", "Josiah", "Juan", "Julian", "Julius", "Justin", "Kade", "Kaden", "Kaleb", "Kam",
    "Kamari", "Kareem", "Keaton", "Keenan", "Keith", "Kellen", "Kelvin", "Kendall", "Kendrick", "Kenny",
    "Keon", "Keshawn", "Kevin", "Khalil", "Kobe", "Kolby", "Kyle", "Kyler", "Lamar", "Lance", "Landon", "Lane",
    "Leo", "Levi", "Liam", "Logan", "Lorenzo", "Luca", "Lucas", "Luke", "Malachi", "Malcolm", "Malik", "Manny",
    "Marcus", "Mario", "Marquis", "Mason", "Mateo", "Matt", "Maurice", "Max", "Micah", "Michael", "Miles",
    "Mitchell", "Montel", "Nate", "Nathan", "Nehemiah", "Nick", "Nico", "Noah", "Nolan", "Omar", "Oscar",
    "Owen", "Pierce", "Preston", "Quentin", "Quincy", "Quinn", "Rashad", "Ray", "Reggie", "Reid", "Rhett",
    "Ricky", "Riley", "Roman", "Ronnie", "Ryan", "Sam", "Samuel", "Saul", "Sean", "Seth", "Shane", "Silas",
    "Solomon", "Stefan", "Sterling", "Tanner", "Tavion", "Tate", "Terrance", "Terrell", "Thaddeus", "Theo",
    "Tommy", "Travis", "Trent", "Trevor", "Trey", "Tristan", "Troy", "Ty", "Tyler", "Tyrese", "Tyson",
    "Victor", "Vince", "Wade", "Walker", "Wes", "Will", "Xavier", "Zach", "Zaire", "Zane", "Zion",
    "Ahmad", "Akeem", "Anfernee", "Bryson", "Cayden", "Chidi", "Cyrus", "Dorian", "Elias", "Fabian", "Gus",
    "Harrison", "Hollis", "Ja'Marr", "Jalin", "Jaquan", "Kalani", "Keanu", "Kingston", "Kofi", "Lathan",
    "Makai", "Marek", "Matthias", "Nasir", "Obi", "Pono", "Rocco", "Santana", "Sione", "Tavita", "Teague",
    "Tobias", "Uriah", "Vaughn", "Wyatt", "Yusuf", "Zeke",
]

LAST_NAMES = [
    # Common American surnames
    "Adams", "Allen", "Anderson", "Armstrong", "Atkins", "Bailey", "Baker", "Banks", "Barnes", "Barrett",
    "Bates", "Beasley", "Bell", "Bennett", "Benson", "Berry", "Bishop", "Black", "Blackwell", "Blair", "Bolden",
    "Booker", "Bowen", "Bowers", "Boyd", "Bradley", "Brewer", "Bridges", "Briggs", "Brooks", "Brown", "Bryant",
    "Buckner", "Burke", "Burns", "Burton", "Bush", "Butler", "Byrd", "Caldwell", "Calhoun", "Campbell", "Cannon",
    "Carpenter", "Carr", "Carroll", "Carter", "Casey", "Chambers", "Chandler", "Chapman", "Clark", "Clay",
    "Clayton", "Cobb", "Cole", "Coleman", "Collier", "Collins", "Conley", "Conner", "Cook", "Cooper", "Copeland",
    "Cox", "Craig", "Crawford", "Crenshaw", "Crosby", "Cross", "Cunningham", "Curry", "Dalton", "Daniels",
    "Davenport", "Davis", "Dawkins", "Dawson", "Day", "Dean", "Dennis", "Dickerson", "Dixon", "Dorsey",
    "Douglas", "Drake", "Duncan", "Dunn", "Durham", "Eaton", "Edwards", "Elliott", "Ellis", "Evans",
    "Farmer", "Ferguson", "Fields", "Finley", "Fisher", "Fleming", "Fletcher", "Flowers", "Floyd", "Ford",
    "Foster", "Fowler", "Franklin", "Frazier", "Freeman", "Fuller", "Gaines", "Gardner", "Garner", "Gibbs",
    "Gibson", "Gilbert", "Gill", "Glover", "Goodwin", "Gordon", "Graham", "Grant", "Graves", "Gray", "Green",
    "Greene", "Griffin", "Grimes", "Hale", "Hall", "Hamilton", "Hammond", "Hampton", "Hancock", "Hardy",
    "Harmon", "Harper", "Harrington", "Harris", "Hart", "Harvey", "Hawkins", "Hayes", "Haynes", "Henderson",
    "Henry", "Hicks", "Hill", "Hines", "Hodge", "Hodges", "Holland", "Holloway", "Holmes", "Holt", "Hood",
    "Hopkins", "Horton", "Houston", "Howard", "Howell", "Hubbard", "Hudson", "Huff", "Hughes", "Hunt",
    "Ingram", "Irving", "Jackson", "James", "Jefferson", "Jenkins", "Jennings", "Johnson", "Jones", "Jordan",
    "Joseph", "Keller", "Kelley", "Kennedy", "Kent", "Kerr", "Kimble", "King", "Kirby", "Knight", "Knox",
    "Lambert", "Lane", "Lang", "Lawrence", "Lawson", "Lee", "Leonard", "Lewis", "Lindsey", "Little", "Lloyd",
    "Lockett", "Logan", "Long", "Love", "Lowe", "Lucas", "Lyons", "Mack", "Maddox", "Malone", "Mann", "Manning",
    "Marsh", "Marshall", "Martin", "Mason", "Mathis", "Matthews", "Maxwell", "May", "Mayfield", "McBride",
    "McCall", "McCoy", "McDaniel", "McDonald", "McGee", "McKinney", "McKnight", "Meadows", "Merritt", "Miles",
    "Miller", "Mills", "Mitchell", "Montgomery", "Moody", "Moore", "Morgan", "Morris", "Morrison", "Morton",
    "Moss", "Murphy", "Murray", "Nash", "Neal", "Nelson", "Newman", "Newton", "Nichols", "Nixon", "Norris",
    "Norton", "Oliver", "Owens", "Page", "Palmer", "Parks", "Parrish", "Patrick", "Patterson", "Payne",
    "Pearson", "Perkins", "Perry", "Peters", "Peterson", "Phillips", "Pierce", "Pittman", "Poole", "Porter",
    "Potter", "Powell", "Powers", "Pratt", "Preston", "Price", "Pruitt", "Quinn", "Ramsey", "Randall", "Ray",
    "Reed", "Reese", "Reeves", "Reid", "Reynolds", "Rhodes", "Rice", "Richards", "Richardson", "Riggs",
    "Riley", "Rivers", "Roberson", "Roberts", "Robinson", "Rogers", "Rose", "Ross", "Rowe", "Russell",
    "Sampson", "Sanders", "Saunders", "Scott", "Sellers", "Sharp", "Shaw", "Shelton", "Shepherd", "Simmons",
    "Simpson", "Sims", "Singleton", "Slater", "Sloan", "Smalls", "Smith", "Snyder", "Spears", "Spencer",
    "Stanley", "Steele", "Stephens", "Stevens", "Stewart", "Stokes", "Stone", "Strickland", "Sullivan",
    "Summers", "Sutton", "Swain", "Talley", "Tate", "Taylor", "Terrell", "Thomas", "Thompson", "Thornton",
    "Tillman", "Todd", "Townsend", "Tucker", "Turner", "Tyler", "Underwood", "Vaughn", "Vincent", "Wade",
    "Walker", "Wallace", "Walls", "Walton", "Ward", "Warner", "Warren", "Washington", "Waters", "Watkins",
    "Watson", "Watts", "Weaver", "Webb", "Webster", "Welch", "Wells", "West", "Wheeler", "Whitaker", "White",
    "Whitfield", "Whitley", "Wiggins", "Wilcox", "Wilkerson", "Wilkins", "Williams", "Williamson", "Willis",
    "Wilson", "Winfield", "Winston", "Wise", "Womack", "Wood", "Woodard", "Woods", "Wright", "Wyatt", "Yates",
    "York", "Young",
    # Southern and small-town names
    "Abernathy", "Ashford", "Bankston", "Barfield", "Beauchamp", "Blakely", "Blanton", "Blount", "Boudreaux",
    "Boykin", "Brantley", "Breaux", "Broussard", "Buchanan", "Burrell", "Cagle", "Canady", "Cantrell",
    "Carlisle", "Cheatham", "Colquitt", "Cotton", "Counts", "Crockett", "Culpepper", "Dabney", "Darden",
    "Dockery", "Doucet", "Dupree", "Easley", "Etheridge", "Faircloth", "Fontenot", "Gatlin", "Gentry",
    "Godwin", "Goolsby", "Guidry", "Hargrove", "Harkness", "Hatcher", "Heflin", "Hebert", "Hollins",
    "Honeycutt", "Hooks", "Hulsey", "Jernigan", "Kilgore", "Lacy", "Landry", "Lassiter", "LeBlanc", "Ledbetter",
    "Mabry", "McAllister", "McCrary", "McElroy", "McFadden", "McGowan", "McMillan", "McNair", "Mayo", "Muse",
    "Nesbitt", "Oakley", "Pettaway", "Pickett", "Pippin", "Poindexter", "Primus", "Pullen", "Quarles",
    "Rainey", "Ratliff", "Rushing", "Sconiers", "Shackelford", "Speight", "Stallworth", "Stringer",
    "Sturdivant", "Tolbert", "Toney", "Trahan", "Truitt", "Tubbs", "Upshaw", "Varnado", "Wimberly",
    "Witherspoon", "Worthy", "Yarbrough",
    # Irish, Scottish, English
    "Brennan", "Callahan", "Carney", "Cassidy", "Connolly", "Costello", "Cullen", "Delaney", "Donnelly",
    "Doyle", "Driscoll", "Duffy", "Egan", "Fahey", "Farrell", "Fitzgerald", "Flanagan", "Flynn", "Gallagher",
    "Garrity", "Hanlon", "Healy", "Hennessy", "Kavanagh", "Keane", "Keegan", "Kilpatrick", "Lynch",
    "MacKenzie", "Maguire", "McCarthy", "McGrath", "McGuire", "McKenna", "McLaughlin", "Moran", "Mulligan",
    "Nolan", "O'Brien", "O'Connor", "O'Donnell", "O'Hara", "O'Neal", "O'Rourke", "Quigley", "Regan",
    "Rooney", "Ryan", "Shanahan", "Sheridan", "Sweeney", "Tierney", "Whelan", "Buchan", "Cameron", "Dunbar",
    "Fraser", "Galloway", "Kincaid", "Lockhart", "Munro", "Ogilvie", "Ramsay", "Sinclair", "Abbott",
    "Ainsworth", "Ashby", "Barlow", "Blackburn", "Bramwell", "Chatfield", "Colby", "Dunlap", "Fairbanks",
    "Fenwick", "Gladwell", "Hadley", "Hartley", "Hawthorne", "Kendrick", "Langley", "Lowery", "Mercer",
    "Pendleton", "Radford", "Rutherford", "Stafford", "Thatcher", "Whitmore", "Winslow", "Woodley",
    # German, Dutch, Scandinavian
    "Albrecht", "Bauer", "Becker", "Brandt", "Dietrich", "Eckert", "Engel", "Fischer", "Frank", "Friedrich",
    "Gerhardt", "Hahn", "Hartmann", "Hoffman", "Huber", "Kaiser", "Kessler", "Klein", "Koch", "Kramer",
    "Krause", "Kuhn", "Lehman", "Lutz", "Meyer", "Mueller", "Neumann", "Pfeiffer", "Reinhardt", "Richter",
    "Schaefer", "Schmidt", "Schneider", "Schroeder", "Schultz", "Schwartz", "Stahl", "Vogel", "Wagner",
    "Weber", "Weiss", "Zimmerman", "DeVries", "Vanderberg", "Van Dyke", "Visser", "Anders", "Berglund",
    "Dahl", "Engstrom", "Halvorsen", "Hanson", "Iversen", "Johansson", "Lindgren", "Lindqvist", "Lund",
    "Nygaard", "Olsen", "Pedersen", "Sorensen", "Strand", "Swanson", "Thorsen",
    # Italian, French, Portuguese
    "Amato", "Bianchi", "Caruso", "Costa", "DeLuca", "Esposito", "Ferrari", "Gallo", "Giordano", "Lombardi",
    "Mancini", "Marino", "Moretti", "Rizzo", "Romano", "Russo", "Santoro", "Vitale", "Belanger", "Bouchard",
    "Dubois", "Fortier", "Gagnon", "Lefebvre", "Marchand", "Moreau", "Pelletier", "Rousseau", "Thibodeaux",
    "Almeida", "Carvalho", "Ferreira", "Medeiros", "Pereira", "Souza",
    # Hispanic
    "Acosta", "Aguilar", "Alvarado", "Alvarez", "Arroyo", "Avila", "Barrera", "Benitez", "Cabrera",
    "Calderon", "Camacho", "Castaneda", "Castillo", "Castro", "Cervantes", "Chavez", "Contreras", "Cordova",
    "Cruz", "Delgado", "Diaz", "Dominguez", "Escobar", "Espinoza", "Estrada", "Figueroa", "Flores", "Fuentes",
    "Gallegos", "Garza", "Guerrero", "Gutierrez", "Herrera", "Ibarra", "Juarez", "Lara", "Leon", "Lozano",
    "Luna", "Maldonado", "Marquez", "Medina", "Mejia", "Mendez", "Mendoza", "Miranda", "Molina", "Montoya",
    "Morales", "Moreno", "Navarro", "Nunez", "Ochoa", "Orozco", "Ortega", "Ortiz", "Pacheco", "Padilla",
    "Pena", "Quintero", "Ramirez", "Ramos", "Rangel", "Reyes", "Rios", "Rivera", "Robles", "Rojas", "Rosales",
    "Ruiz", "Salazar", "Salinas", "Sandoval", "Santiago", "Serrano", "Solis", "Soto", "Suarez", "Tapia",
    "Torres", "Trevino", "Valdez", "Valencia", "Vargas", "Vasquez", "Vega", "Velasquez", "Zamora",
    # Pacific Islander
    "Aumavae", "Faleolo", "Fanene", "Fonoti", "Fuimaono", "Havili", "Kaufusi", "Kauhane", "Kaumatule",
    "Leavitt", "Lealaimatafao", "Mahe", "Mailata", "Malietoa", "Mata'afa", "Moala", "Nacua", "Niumatalolo",
    "Paepule", "Palelei", "Pulu", "Sewell", "Sopoaga", "Sua", "Taamu", "Tafuna", "Tagovailoa", "Taufa",
    "Tuiasosopo", "Tuimavave", "Tuipulotu", "Tupou", "Vaipulu", "Vainikolo", "Kahananui", "Kealoha",
    "Makanani", "Nakamura", "Kanoho", "Alapati",
    # West African
    "Adebayo", "Adeyemi", "Agbaje", "Akinola", "Amadi", "Anyanwu", "Asante", "Babatunde", "Boateng",
    "Chukwu", "Ekwueme", "Eze", "Ibeh", "Igwe", "Ikenna", "Mensah", "Nwosu", "Obi", "Odeyingbo", "Odunze",
    "Ogbonna", "Ogunbowale", "Okafor", "Okeke", "Okonkwo", "Okoro", "Olawale", "Onwuzurike", "Opoku",
    "Oduya", "Owusu", "Uche", "Udoh", "Ukwu", "Umeh", "Diallo", "Toure", "Kamara", "Sesay", "Mbeki",
    # Eastern European
    "Babich", "Borowski", "Dombrowski", "Dudek", "Hajek", "Horvath", "Jankowski", "Kaminski", "Kovac",
    "Kowalski", "Kozlowski", "Krawczyk", "Lewandowski", "Malinowski", "Marek", "Mazur", "Nowak", "Novak",
    "Pavlovic", "Petrovic", "Sikora", "Sokolov", "Stasko", "Wisniewski", "Zelinski", "Zielinski",
    # Middle Eastern, Asian, other
    "Haddad", "Hakim", "Kassab", "Mansour", "Nassar", "Saleh", "Chen", "Kim", "Nguyen", "Park", "Tran",
    "Yamamoto", "Tanaka", "Watanabe", "Singh", "Patel",
    # More American surnames
    "Alexander", "Arnold", "Austin", "Ball", "Barber", "Barker", "Barton", "Baxter", "Beck", "Benton",
    "Blackmon", "Blake", "Bond", "Bonner", "Boone", "Bowden", "Bowman", "Boyer", "Bradford", "Bragg", "Branch",
    "Brock", "Brunson", "Bullock", "Burgess", "Burnett", "Burrows", "Cain", "Carey", "Carson", "Cash",
    "Chaney", "Christian", "Cleveland", "Cochran", "Coffey", "Colbert", "Combs", "Conrad", "Cooke", "Corbin",
    "Cowan", "Crane", "Cummings", "Dancy", "Dudley", "Dukes", "Dyson", "Early", "English", "Everett",
    "Fair", "Faulk", "Fitzpatrick", "Forbes", "Fox", "Gamble", "Garland", "Gates", "Givens", "Goff",
    "Golden", "Gooden", "Gore", "Grady", "Greer", "Gregory", "Hackett", "Hairston", "Hardin", "Hardaway",
    "Harrell", "Hester", "Hightower", "Hinton", "Hobbs", "Holden", "Holley", "Hooper", "Horne", "Hurst",
    "Jacobs", "Jeffries", "Kearse", "Kemp", "Kidd", "Kinard", "Kirkland", "Lattimore", "Lester", "Lofton",
    "Lott", "Lynn", "Mayes", "McCain", "McClain", "McCray", "McGhee", "McNeil", "Monroe", "Moon", "Mosley",
    "Neely", "Norwood", "Odom", "Orr", "Paige", "Pace", "Peoples", "Person", "Pinkney", "Pope", "Prince",
    "Pryor", "Randle", "Redd", "Rollins", "Ruffin", "Samuels", "Sapp", "Seals", "Sherman", "Sills", "Skinner",
    "Starks", "Stovall", "Tatum", "Toliver", "Trotter", "Upton", "Vance", "Venable", "Wagoner", "Wakefield",
    "Walden", "Waller", "Whitehead", "Whitlock", "Wilder", "Word", "Workman", "Wynn", "Youngblood",
    "Ashe", "Beamon", "Bly", "Chubb", "Cromartie", "Dotson", "Fant", "Forte", "Gilliam", "Hairgrove",
    "Hollings", "Jolly", "Kitchens", "Lamb", "Merriweather", "Mims", "Oates", "Peay", "Ridley", "Rudd",
    "Scarbrough", "Speed", "Stingley", "Swinney", "Tisdale", "Troupe", "Vick", "Weatherspoon", "Winters",
    "Blankenship", "Hargis", "Kinsey", "Lundy", "Maynard", "Pickens", "Presley", "Sadler", "Stroud",
    "Tackett", "Whitt", "Wolfe", "Yeager",
]
# Broadcasters and show hosts go by their last names on air — no player shares one.
# ── expanded pools (v39) ──
FIRST_NAMES += ['Abdul', 'Abel', 'Ace', 'Adonis', 'Ahmad', 'Ahmir', 'Ajani', 'Akeem', 'Alden', 'Alec', 'Alex', 'Alvin', 'Amarion', 'Ameer', 'Amon', 'Anderson', 'Andy', 'Angel', 'Ansel', 'Anton', 'Arlo', 'Arthur', 'Ashton', 'Atticus', 'Aubrey', 'Augustus', 'Austin', 'Avery', 'Axel', 'Ayden', 'Barrett', 'Beau', 'Benji', 'Bennett', 'Bentley', 'Blaine', 'Blake', 'Bo', 'Bobby', 'Boden', 'Brady', 'Branson', 'Brayden', 'Breylon', 'Brice', 'Brock', 'Brody', 'Bronson', 'Bryce', 'Bryson', 'Buck', 'Byron', 'Cade', 'Caden', 'Cal', 'Callum', 'Camden', 'Cameron', 'Camren', 'Carson', 'Carter', 'Casey', 'Cash', 'Cason', 'Cayden', 'Cedric', 'Chance', 'Chandler', 'Charlie', 'Chase', 'Christian', 'Clay', 'Clayton', 'Cody', 'Colby', 'Cole', 'Colin', 'Colton', 'Conner', 'Cooper', 'Corey', 'Cortez', 'Craig', 'Cruz', 'Cullen', 'Curtis', 'Dakota', 'Dallas', 'Damarion', 'Damian', 'Damon', 'Dane', 'Dante', 'Darius', 'Darnell', 'Darren', 'Davion', 'Dawson', 'Deandre', 'Deion', 'Demarcus', 'Demetrius', 'Denzel', 'Derek', 'Derrick', 'Desmond', 'Devonta', 'Dexter', 'Diego', 'Dillon', 'Dominique', 'Donovan', 'Drake', 'Drew', 'Duke', 'Dwayne', 'Dylan', 'Easton', 'Eddie', 'Edwin', 'Eli', 'Elias', 'Elijah', 'Emanuel', 'Emmett', 'Enzo', 'Eric', 'Ernest', 'Ethan', 'Evan', 'Ezekiel', 'Ezra', 'Felix', 'Fernando', 'Finn', 'Fletcher', 'Ford', 'Francisco', 'Frank', 'Gabe', 'Garrett', 'Gavin', 'George', 'Gideon', 'Grady', 'Graham', 'Grant', 'Grayson', 'Greg', 'Griffin', 'Gunnar', 'Hank', 'Harrison', 'Hayden', 'Hector', 'Hendrix', 'Henry', 'Hezekiah', 'Holden', 'Houston', 'Hudson', 'Hunter', 'Ian', 'Ike', 'Isaac', 'Isaiah', 'Ismael', 'Ivan', 'Jabari', 'Jace', 'Jackson', 'Jacoby', 'Jaden', 'Jadon', 'Jahmir', 'Jair', 'Jaire', 'Jakobe', 'Jalen', 'Jamal', 'Jamari', 'Jameson', 'Jamir', 'Jaquan', 'Jared', 'Jarvis', 'Jase', 'Jasper', 'Javion', 'Javon', 'Jaxon', 'Jaylen', 'Jaylon', 'Jayson', 'Jeremiah', 'Jermaine', 'Jerome', 'Jett', 'Joaquin', 'Joel', 'Jonah', 'Jordan', 'Jordy', 'Jorge', 'Josiah', 'Jovan', 'Judah', 'Julian', 'Julius', 'Justice', 'Justin', 'Kaden', 'Kaleb', 'Kamari', 'Kameron', 'Kareem', 'Kasen', 'Keaton', 'Keegan', 'Keenan', 'Kellen', 'Kendall', 'Kendrick', 'Kenny', 'Keon', 'Keshawn', 'Khalil', 'Kingston', 'Knox', 'Kobe', 'Kofi', 'Kolby', 'Kristian', 'Kyler', 'Kymani', 'Lamar', 'Lance', 'Landon', 'Lane', 'Larry', 'Laurence', 'Lawson', 'Leland', 'Leo', 'Leon', 'Leonard', 'Levi', 'Lincoln', 'Logan', 'Lorenzo', 'Luca', 'Lucas', 'Luke', 'Maddox', 'Major', 'Makai', 'Malachi', 'Malik', 'Manny', 'Marcus', 'Mario', 'Marquez', 'Marshall', 'Mason', 'Mateo', 'Maurice', 'Maverick', 'Max', 'Messiah', 'Micah', 'Miles', 'Moses', 'Myles', 'Nash', 'Nasir', 'Nate', 'Nehemiah', 'Nico', 'Noah', 'Nolan', 'Odell', 'Omar', 'Orlando', 'Oscar', 'Otis', 'Owen', 'Parker', 'Paxton', 'Peyton', 'Phillip', 'Pierce', 'Preston', 'Quentin', 'Quinton', 'Rashad', 'Raymond', 'Reed', 'Reggie', 'Rhett', 'Ricky', 'Riley', 'Rodney', 'Roman', 'Romeo', 'Ronan', 'Rowan', 'Russell', 'Ryder', 'Sage', 'Santiago', 'Sawyer', 'Semaj', 'Shane', 'Shaun', 'Shemar', 'Simeon', 'Solomon', 'Spencer', 'Stetson', 'Sterling', 'Stone', 'Sullivan', 'Syncere', 'Tanner', 'Tate', 'Terrance', 'Thaddeus', 'Theo', 'Titus', 'Tobias', 'Trace', 'Travis', 'Tre', 'Trent', 'Trevon', 'Trey', 'Tristan', 'Troy', 'Tucker', 'Ty', 'Tyson', 'Uriah', 'Vance', 'Victor', 'Vince', 'Wade', 'Walker', 'Warren', 'Wesley', 'Weston', 'Will', 'Wyatt', 'Xavier', 'Zach', 'Zaire', 'Zion', 'Akoni', 'Kainoa', 'Keoni', 'Malakai', 'Sione', 'Tevita', 'Tuli', 'Viliami', 'Penei', 'Isileli', 'Kekoa', 'Makana', 'Tavita', 'Kalolo', 'Chukwuma', 'Emeka', 'Femi', 'Kelechi', 'Obinna', 'Olumide', 'Tobi', 'Chidi', 'Adebayo', 'Babatunde', 'Yaw', 'Kwame', 'Ade']
LAST_NAMES += ['Abernathy', 'Acevedo', 'Ackerman', 'Adeyemi', 'Adkins', 'Agee', 'Aguilar', 'Akins', 'Albright', 'Alcorn', 'Aldridge', 'Alford', 'Alston', 'Alvarado', 'Ambrose', 'Amos', 'Andrews', 'Anthony', 'Appleton', 'Archer', 'Archuleta', 'Arnett', 'Arrington', 'Ashby', 'Ashford', 'Atwater', 'Augustine', 'Austin', 'Avant', 'Avery', 'Ayers', 'Babcock', 'Baca', 'Bader', 'Bagley', 'Bainbridge', 'Baldwin', 'Ballard', 'Bankston', 'Barber', 'Barkley', 'Barksdale', 'Barlow', 'Barnett', 'Barr', 'Barron', 'Bartley', 'Bass', 'Batiste', 'Battle', 'Baxter', 'Beal', 'Beck', 'Beckham', 'Belcher', 'Benjamin', 'Berry', 'Bethea', 'Bigby', 'Billups', 'Bingham', 'Bishop', 'Blackburn', 'Blackmon', 'Blakely', 'Bland', 'Blount', 'Bolden', 'Bolton', 'Booker', 'Boone', 'Bost', 'Bowden', 'Bowers', 'Boykin', 'Bradshaw', 'Brandt', 'Branch', 'Braxton', 'Brewer', 'Bridges', 'Briggs', 'Brinkley', 'Britt', 'Broadnax', 'Brooks', 'Broussard', 'Bryant', 'Buckner', 'Bullock', 'Burgess', 'Burks', 'Burrell', 'Bush', 'Butler', 'Byrd', 'Cabrera', 'Cain', 'Caldwell', 'Calhoun', 'Camacho', 'Cannon', 'Cantrell', 'Carlisle', 'Carmichael', 'Carrington', 'Carroll', 'Carver', 'Castillo', 'Castro', 'Causey', 'Chambers', 'Chandler', 'Chaney', 'Chapman', 'Chavis', 'Cherry', 'Childress', 'Christian', 'Clanton', 'Clayborne', 'Clemons', 'Clinton', 'Cobb', 'Coker', 'Coleman', 'Collier', 'Combs', 'Conley', 'Conner', 'Cooke', 'Corbin', 'Cornelius', 'Cosby', 'Cotton', 'Council', 'Covington', 'Cox', 'Crenshaw', 'Crockett', 'Crosby', 'Crowder', 'Crump', 'Cunningham', 'Curry', 'Dabney', 'Dalton', 'Daniels', 'Darby', 'Davenport', 'Dawkins', 'Deas', 'Dejean', 'Delaney', 'Dempsey', 'Dennis', 'Denson', 'Dickerson', 'Diggs', 'Dillard', 'Dixon', 'Dobbins', 'Dorsey', 'Dotson', 'Dowdell', 'Downs', 'Drake', 'Dukes', 'Dunbar', 'Duncan', 'Dunlap', 'Dupree', 'Durant', 'Dye', 'Easley', 'Echols', 'Edmonds', 'Edwards', 'Elam', 'Ellington', 'Elliott', 'Ellis', 'Embry', 'Emerson', 'Epps', 'Escobar', 'Espinoza', 'Estes', 'Evans', 'Everett', 'Fairley', 'Farmer', 'Faulk', 'Felder', 'Fennell', 'Fenner', 'Fields', 'Finley', 'Fitzgerald', 'Flagg', 'Fleming', 'Fletcher', 'Flowers', 'Floyd', 'Foreman', 'Fountain', 'Fowler', 'Frazier', 'Freeman', 'Fuller', 'Fulton', 'Gaines', 'Galloway', 'Gamble', 'Gardner', 'Garland', 'Garrett', 'Gates', 'Gentry', 'Gibbs', 'Gilliam', 'Gipson', 'Glover', 'Goff', 'Golden', 'Gooden', 'Goodwin', 'Gordon', 'Graves', 'Gray', 'Greer', 'Griffin', 'Grimes', 'Guidry', 'Guy', 'Hairston', 'Hall', 'Hamilton', 'Hampton', 'Hancock', 'Hardaway', 'Hardin', 'Harmon', 'Harper', 'Harrell', 'Hartley', 'Hatcher', 'Hawkins', 'Hayes', 'Haynes', 'Heard', 'Henderson', 'Herring', 'Hicks', 'Hightower', 'Hilliard', 'Hines', 'Hinton', 'Hobbs', 'Holcomb', 'Holiday', 'Holloway', 'Holmes', 'Hood', 'Hopkins', 'Horne', 'Horton', 'Houston', 'Howell', 'Hubbard', 'Huff', 'Hughes', 'Humphrey', 'Hunt', 'Hurst', 'Hutchinson', 'Ingram', 'Irby', 'Irvin', 'Isaac', 'Ivey', 'Jacobs', 'James', 'Jamison', 'Jefferson', 'Jenkins', 'Jennings', 'Joiner', 'Jolly', 'Jordan', 'Joseph', 'Joyner', 'Justice', 'Kearney', 'Keith', 'Keller', 'Kemp', 'Kendrick', 'Kennedy', 'Key', 'Kidd', 'Killebrew', 'Kinard', 'Kirkland', 'Knight', 'Knox', 'Lacy', 'Lamb', 'Landry', 'Lane', 'Langford', 'Lassiter', 'Lattimore', 'Lawson', 'Ledbetter', 'Lemon', 'Lester', 'Lewis', 'Lindsey', 'Little', 'Littleton', 'Lockett', 'Lofton', 'Logan', 'Love', 'Lowery', 'Lyles', 'Lyons', 'Mack', 'Maddox', 'Malone', 'Manning', 'Marsh', 'Massey', 'Mathis', 'Maxwell', 'Mayfield', 'Mays', 'McBride', 'McCall', 'McClain', 'McCoy', 'McDaniel', 'McFadden', 'McGee', 'McKenzie', 'McKinney', 'McNeil', 'Meadows', 'Melton', 'Mercer', 'Merritt', 'Middleton', 'Miles', 'Mims', 'Mobley', 'Montgomery', 'Moody', 'Moon', 'Morrow', 'Mosley', 'Moss', 'Muhammad', 'Murray', 'Myers', 'Nance', 'Neal', 'Nelson', 'Newsome', 'Newton', 'Nichols', 'Nixon', 'Noble', 'Norman', 'Norwood', 'Oates', 'Odom', 'Oliver', 'Oneal', 'Orr', 'Osborne', 'Outlaw', 'Overton', 'Owens', 'Pace', 'Parham', 'Parrish', 'Patton', 'Payne', 'Peay', 'Pearson', 'Peebles', 'Pender', 'Penn', 'Perry', 'Person', 'Pettis', 'Phifer', 'Pickett', 'Pierce', 'Pitts', 'Pleasant', 'Poole', 'Pope', 'Porter', 'Powell', 'Pratt', 'Price', 'Pruitt', 'Pugh', 'Quarles', 'Ragland', 'Randle', 'Ransom', 'Rawls', 'Ray', 'Redd', 'Reese', 'Revis', 'Rhodes', 'Richardson', 'Riddick', 'Ridley', 'Rivers', 'Robbins', 'Roberson', 'Rollins', 'Roper', 'Ross', 'Rountree', 'Rowe', 'Ruffin', 'Rush', 'Russell', 'Sanders', 'Sapp', 'Saunders', 'Scales', 'Settles', 'Shabazz', 'Sharpe', 'Shaw', 'Shelton', 'Shepherd', 'Simmons', 'Sims', 'Singleton', 'Slaughter', 'Sledge', 'Smalls', 'Snead', 'Spann', 'Speight', 'Spencer', 'Spikes', 'Stallworth', 'Staton', 'Steele', 'Stokes', 'Strong', 'Sumlin', 'Swain', 'Swann', 'Tate', 'Tatum', 'Teague', 'Terrell', 'Thigpen', 'Thornton', 'Threatt', 'Tillman', 'Toney', 'Toomer', 'Townsend', 'Trotter', 'Tubbs', 'Tucker', 'Tunsil', 'Turner', 'Tyson', 'Underwood', 'Upshaw', 'Vance', 'Vaughn', 'Vereen', 'Vick', 'Waddell', 'Walton', 'Ware', 'Warrick', 'Washington', 'Watkins', 'Weathers', 'Webb', 'Westbrook', 'Whitfield', 'Whitley', 'Wiggins', 'Wilder', 'Wilkerson', 'Willis', 'Winfield', 'Witherspoon', 'Womack', 'Woodard', 'Woodson', 'Wright', 'Wyatt', 'Yancey', 'Yates', 'Young', 'Zeigler', 'Fifita', 'Fonoti', 'Fuimaono', 'Havili', 'Latu', 'Lauina', 'Mahe', 'Moala', 'Pouha', 'Sewell', 'Soliai', 'Taufa', 'Tuitele', 'Tupou', 'Vainikolo', 'Adebo', 'Ajayi', 'Akinola', 'Anoliefo', 'Chukwu', 'Eze', 'Ezeudu', 'Nwankwo', 'Ogbonnia', 'Okafor', 'Okonkwo', 'Oladapo', 'Olawale', 'Onyemata', 'Uche', 'Alvarez', 'Barajas', 'Becerra', 'Carrillo', 'Cervantes', 'Contreras', 'Delgado', 'Duarte', 'Esparza', 'Flores', 'Fuentes', 'Galindo', 'Gallegos', 'Guerrero', 'Gutierrez', 'Ibarra', 'Juarez', 'Lozano', 'Macias', 'Medina', 'Mendoza', 'Montoya', 'Ochoa', 'Orozco', 'Pacheco', 'Quintero', 'Rios', 'Salazar', 'Sandoval', 'Serrano', 'Tapia', 'Trevino', 'Valdez', 'Vargas', 'Velasquez', 'Zamora', 'Adler', 'Bauer', 'Becker', 'Brandt', 'Dietrich', 'Engel', 'Fischer', 'Gruber', 'Hartman', 'Hoffman', 'Kessler', 'Klein', 'Koenig', 'Kruger', 'Lange', 'Meier', 'Muller', 'Neumann', 'Richter', 'Schaefer', 'Schmidt', 'Schroeder', 'Schultz', 'Vogel', 'Wagner', 'Weber', 'Zimmerman', 'Brennan', 'Callahan', 'Doherty', 'Donnelly', 'Flanagan', 'Gallagher', 'Kavanagh', 'Keane', 'McCarthy', 'McGrath', 'Moriarty', 'Mulligan', 'Nolan', 'Quinlan', 'Reilly', 'Sheridan', 'Sullivan', 'Walsh', 'Kowalski', 'Nowak', 'Novak', 'Wisniewski', 'Zielinski', 'Petrovic', 'Horvath', 'Kovac', 'Lindqvist', 'Nilsson', 'Halvorsen', 'Larsen', 'Olsen']

LAST_NAMES += ['Albers', 'Alder', 'Aldrich', 'Allison', 'Ames', 'Ammons', 'Ansley', 'Applegate', 'Ashcraft', 'Ashworth', 'Aycock', 'Bagwell', 'Ballew', 'Bancroft', 'Barham', 'Barnhill', 'Bartlett', 'Beard', 'Beaty', 'Beckett', 'Beecher', 'Belk', 'Bellamy', 'Benfield', 'Berkley', 'Biggers', 'Billings', 'Bivens', 'Blalock', 'Blevins', 'Bloodworth', 'Bowling', 'Boyett', 'Brackett', 'Brasher', 'Bratton', 'Brigham', 'Brinson', 'Bromley', 'Brower', 'Burleson', 'Burnside', 'Burrow', 'Byers', 'Calloway', 'Cantu', 'Carden', 'Carlton', 'Cartwright', 'Cates', 'Caudill', 'Chadwick', 'Chalmers', 'Champion', 'Chastain', 'Chestnut', 'Clancy', 'Clary', 'Claxton', 'Cloud', 'Clyburn', 'Coburn', 'Colvin', 'Compton', 'Conway', 'Corley', 'Cothran', 'Crain', 'Crawley', 'Creech', 'Crews', 'Crutchfield', 'Dacus', 'Dailey', 'Daugherty', 'Deal', 'Dearing', 'Decker', 'Delk', 'Denham', 'Devine', 'Dewitt', 'Dial', 'Dobson', 'Dodd', 'Dollar', 'Doss', 'Dowling', 'Drummond', 'Dugan', 'Eddings', 'Edge', 'Elkins', 'Emory', 'Eubanks', 'Ezell', 'Fain', 'Fairchild', 'Falls', 'Farrow', 'Faust', 'Featherston', 'Ferrell', 'Few', 'Finch', 'Fincher', 'Flood', 'Folsom', 'Fortner', 'Foust', 'Franks', 'Frye', 'Furr', 'Gadsden', 'Gaither', 'Gantt', 'Garrison', 'Gaskins', 'Gilmore', 'Gleason', 'Goforth', 'Goins', 'Grace', 'Granger', 'Grayson', 'Greenlee', 'Gresham', 'Griggs', 'Grubbs', 'Gully', 'Gunter', 'Haddock', 'Hagan', 'Haley', 'Hammock', 'Hanna', 'Harden', 'Harley', 'Haskins', 'Hatfield', 'Hedrick', 'Helms', 'Henley', 'Hensley', 'Hickman', 'Higdon', 'Hilton', 'Hipp', 'Hogan', 'Holder', 'Hollis', 'Horn', 'Hovis', 'Howze', 'Hudgins', 'Huggins', 'Hull', 'Hutto', 'Inman', 'Isom', 'Jarrell', 'Jarvis', 'Jessup', 'Jewell', 'Jolley', 'Keel', 'Kendall', 'Kersey', 'Kyle', 'Lacey', 'Ladd', 'Laney', 'Lanier', 'Larkin', 'Latham', 'Laws', 'Leach', 'Ledford', 'Leggett', 'Lilly', 'Linder', 'Lipscomb', 'Lively', 'Lomax', 'Loving', 'Lunsford', 'Lusk', 'Majors', 'Mangum', 'Marlow', 'Marlowe', 'Mashburn', 'Mattox', 'Mauldin', 'McCarley', 'McCaskill', 'McClure', 'McCord', 'McCullough', 'McDowell', 'McIntosh', 'McKee', 'McLaurin', 'McLeod', 'Mead', 'Metcalf', 'Milam', 'Millsap', 'Mingo', 'Mitchum', 'Monk', 'Mooney', 'Morehead', 'Moseley', 'Mullins', 'Murdock', 'Nettles', 'Newberry', 'Nickerson', 'Nunn', 'Ogle', 'Oldham', 'Pagan', 'Painter', 'Pardue', 'Partridge', 'Paschal', 'Pate', 'Peacock', 'Pegues', 'Pemberton', 'Petty', 'Pinckney', 'Pinkston', 'Plummer', 'Polk', 'Pond', 'Poston', 'Prather', 'Proctor', 'Purvis', 'Quick', 'Rankin', 'Rayburn', 'Reaves', 'Rector', 'Renfro', 'Rhoden', 'Rich', 'Rickman', 'Riggins', 'Rigsby', 'Ritter', 'Roach', 'Rochester', 'Rodgers', 'Rouse', 'Royal', 'Rucker', 'Rutledge', 'Sanford', 'Satterfield', 'Scarborough', 'Self', 'Sexton', 'Shealy', 'Shipman', 'Shore', 'Shuler', 'Sigmon', 'Simms', 'Sizemore', 'Slade', 'Smalley', 'Snipes', 'Snow', 'Southerland', 'Sparks', 'Spivey', 'Springer', 'Stackhouse', 'Stamps', 'Stancil', 'Starling', 'Steed', 'Stinson', 'Suggs', 'Summerall', 'Sumner', 'Tanner', 'Tarver', 'Teal', 'Templeton', 'Thurman', 'Tidwell', 'Timmons', 'Tolliver', 'Trammell', 'Tripp', 'Tuck', 'Tyner', 'Upchurch', 'Utley', 'Varner', 'Vaught', 'Vines', 'Wadsworth', 'Walters', 'Watt', 'Weeks', 'Westmoreland', 'Whaley', 'Whatley', 'Wilburn', 'Wiley', 'Willingham', 'Winn', 'Wofford', 'Woodall', 'Woodruff', 'Worley', 'Yarborough', 'Yeargin']

RESERVED_SURNAMES = {"Whitmore", "Ruiz", "Pell", "Grant", "Sutter", "Navarro", "Kimbrough", "Ferris", "Oakes",
                     "Hollis", "Delacroix", "Brandvold", "Merriman", "Albright", "Voss", "Kowalski", "Pettaway",
                     "Marchetti", "Harwood", "Brennaman", "Pruett", "Oliphant"}
LAST_NAMES = [n for n in dict.fromkeys(LAST_NAMES) if n not in RESERVED_SURNAMES]   # one of each
FIRST_NAMES = list(dict.fromkeys(FIRST_NAMES))
_FIRST_SET = set(FIRST_NAMES)


# Real, well-known players: a generated name never matches one exactly.
FAMOUS = {
    "Keenan Allen", "Josh Allen", "Tom Brady", "Patrick Mahomes", "Aaron Rodgers", "Joe Burrow", "Justin Jefferson",
    "Travis Kelce", "Derrick Henry", "Christian McCaffrey", "Tyreek Hill", "Davante Adams", "Stefon Diggs",
    "Josh Jacobs", "Aaron Jones", "Chris Johnson", "Calvin Johnson", "Andre Johnson", "Michael Thomas",
    "Mike Evans", "Chris Godwin", "Cooper Kupp", "Russell Wilson", "Cam Newton", "Lamar Jackson", "Tony Romo",
    "Peyton Manning", "Eli Manning", "Drew Brees", "Jerry Rice", "Barry Sanders", "Deion Sanders", "Emmitt Smith",
    "Walter Payton", "Jim Brown", "Joe Montana", "Dan Marino", "John Elway", "Brett Favre", "Troy Aikman",
    "Randy Moss", "Terrell Owens", "Larry Fitzgerald", "Reggie White", "Lawrence Taylor", "Ray Lewis", "Ed Reed",
    "Troy Polamalu", "Aaron Donald", "J.J. Watt", "Von Miller", "Khalil Mack", "Myles Garrett", "Nick Bosa",
    "Joey Bosa", "Micah Parsons", "T.J. Watt", "Jalen Hurts", "Jalen Ramsey", "Justin Herbert", "Kyler Murray",
    "Baker Mayfield", "Matthew Stafford", "Kirk Cousins", "Dak Prescott", "Ezekiel Elliott", "Saquon Barkley",
    "Nick Chubb", "Jonathan Taylor", "Dalvin Cook", "Alvin Kamara", "Austin Ekeler", "James Conner", "Joe Mixon",
    "Tyler Lockett", "DK Metcalf", "Amari Cooper", "Brandin Cooks", "Adam Thielen", "Jarvis Landry",
    "George Kittle", "Mark Andrews", "Darren Waller", "Kyle Pitts", "Sam LaPorta", "Brock Bowers", "Travis Hunter",
    "Caleb Williams", "Jayden Daniels", "Drake Maye", "Bo Nix", "Michael Penix", "Cam Ward", "Shedeur Sanders",
    "Bryce Young", "C.J. Stroud", "Anthony Richardson", "Will Anderson", "Marvin Harrison", "Malik Nabers",
    "Rome Odunze", "Garrett Wilson", "Chris Olave", "Jaxon Smith-Njigba", "Ja'Marr Chase", "Tee Higgins",
    "Justin Fields", "Trevor Lawrence", "Mac Jones", "Zach Wilson", "Tua Tagovailoa", "Jordan Love",
    "Brock Purdy", "Jared Goff", "Geno Smith", "Derek Carr", "Daniel Jones", "Sam Darnold", "Kenny Pickett",
    "Arch Manning", "Carson Beck", "Quinn Ewers", "Dillon Gabriel", "Jaxson Dart", "Ashton Jeanty",
    "Tim Tebow", "Johnny Manziel", "Reggie Bush", "Vince Young", "Matt Leinart", "Mark Ingram", "Kyle Hamilton",
    "Sauce Gardner", "Patrick Surtain", "Derek Stingley", "Josh Downs", "David Montgomery", "Kenneth Walker",
    "Breece Hall", "Bijan Robinson", "Jahmyr Gibbs", "De'Von Achane", "Puka Nacua", "Amon-Ra St. Brown",
    "Nico Collins", "Drake London", "Zay Flowers", "Jordan Addison", "Jameson Williams", "Mike Williams",
    "Josh Palmer", "Chris Jones", "Cam Heyward", "Jalen Carter", "Jordan Davis", "Aidan Hutchinson",
}


def surname(rng, avoid=()):
    """A last name not in `avoid` (falls back to any if the pool is somehow exhausted)."""
    avoid = set(avoid)
    for _ in range(60):
        last = rng.choice(LAST_NAMES)
        if last not in avoid:
            return last
    free = [n for n in LAST_NAMES if n not in avoid]
    return rng.choice(free or LAST_NAMES)


def full_name(rng, avoid=(), first=None):
    """'Kaden Brown' — never a first name that is also his last ('Parker Parker'),
    and never a surname in `avoid`."""
    last = surname(rng, avoid)
    for _ in range(40):
        f = first or rng.choice(FIRST_NAMES)
        if f != last and f"{f} {last}" not in FAMOUS:
            return f"{f} {last}"
        first = None
        if _ % 8 == 7:
            last = surname(rng, avoid)
    return f"{rng.choice(FIRST_NAMES)} {surname(rng, set(avoid) | {last})}"


def split_pair(rng, avoid=()):
    """(first, last) — the same rules as full_name."""
    f, _, l = full_name(rng, avoid).partition(" ")
    return f, l


def dedupe_roster(team, rng, reserved=()):
    """One of each surname on a roster (a new world, before anyone has seen it):
    the later arrival of a pair gets a new last name. Also fixes a first name that
    equals the last. Returns how many players were renamed."""
    taken = set(reserved)
    firsts = {c.name.split()[0] for c in (getattr(team, "coach", None), getattr(team, "oc", None),
                                         getattr(team, "dc", None)) if c is not None}
    fixed = 0
    # Upperclassmen and starters keep their names; the youngest gives way.
    for p in sorted(team.roster, key=lambda p: (-getattr(p, "year", 0), -getattr(p, "overall", 0))):
        if p.last_name in taken or p.first_name == p.last_name or f"{p.first_name} {p.last_name}" in FAMOUS:
            p.last_name = surname(rng, taken | {p.first_name})
            fixed += 1
        taken.add(p.last_name)
        # One of each first name too (no two Ashers, no player named after his head coach),
        # as long as the pool has room.
        if p.first_name in firsts and len(firsts) < len(FIRST_NAMES) - 5:
            for _ in range(30):
                f = rng.choice(FIRST_NAMES)
                if f not in firsts and f != p.last_name and f"{f} {p.last_name}" not in FAMOUS:
                    p.first_name = f
                    fixed += 1
                    break
        firsts.add(p.first_name)
    return fixed
