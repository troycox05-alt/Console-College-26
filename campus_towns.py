"""
campus_towns.py — Where every FBS team plays its home games, for datelines
like "Good morning from Provo, Utah."
"""

TOWNS = {
    "Front Range": "Colorado Springs, Colorado", "Akron": "Akron, Ohio", "Alabama": "Tuscaloosa, Alabama",
    "Appalachian State": "Boone, North Carolina", "Arizona": "Tucson, Arizona", "Arizona State": "Tempe, Arizona",
    "Arkansas": "Fayetteville, Arkansas", "Arkansas State": "Jonesboro, Arkansas", "Hudson": "West Point, New York",
    "East Alabama": "Auburn, Alabama", "Provo": "Provo, Utah", "Muncie": "Muncie, Indiana", "Waco": "Waco, Texas",
    "Boise State": "Boise, Idaho", "Boston": "Chestnut Hill, Massachusetts",
    "Bowling Green": "Bowling Green, Ohio", "Buffalo": "Buffalo, New York", "California": "Berkeley, California",
    "Central Michigan": "Mount Pleasant, Michigan", "Charlotte": "Charlotte, North Carolina",
    "Cincinnati": "Cincinnati, Ohio", "Upcountry": "Upcountry, South Carolina", "Grand Strand": "Conway, South Carolina",
    "Colorado": "Boulder, Colorado", "Colorado State": "Fort Collins, Colorado", "Delaware": "Newark, Delaware",
    "Durham": "Durham, North Carolina", "East Carolina": "Greenville, North Carolina",
    "Eastern Michigan": "Ypsilanti, Michigan", "Biscayne": "Miami, Florida", "Florida": "Gainesville, Florida",
    "Florida Atlantic": "Boca Raton, Florida", "Florida State": "Tallahassee, Florida", "Fresno State": "Fresno, California",
    "Georgia": "Athens, Georgia", "Georgia Southern": "Statesboro, Georgia", "Georgia State": "Atlanta, Georgia",
    "Atlanta": "Atlanta, Georgia", "Hawai'i": "Honolulu, Hawai'i", "Houston": "Houston, Texas",
    "Illinois": "Champaign, Illinois", "Indiana": "Bloomington, Indiana", "Iowa": "Iowa City, Iowa",
    "Iowa State": "Ames, Iowa", "Jacksonville State": "Jacksonville, Alabama", "Shenandoah": "Harrisonburg, Virginia",
    "Kansas": "Lawrence, Kansas", "Kansas State": "Manhattan, Kansas", "Kennesaw State": "Kennesaw, Georgia",
    "Kent State": "Kent, Ohio", "Kentucky": "Lexington, Kentucky", "Bayou State": "Baton Rouge, Louisiana",
    "Lynchburg": "Lynchburg, Virginia", "Louisiana": "Lafayette, Louisiana", "Ruston": "Ruston, Louisiana",
    "Louisville": "Louisville, Kentucky", "Huntington": "Huntington, West Virginia", "Maryland": "College Park, Maryland",
    "Memphis": "Memphis, Tennessee", "Miami": "Miami, Florida", "Miami (OH)": "Oxford, Ohio",
    "Michigan": "Ann Arbor, Michigan", "Michigan State": "East Lansing, Michigan",
    "Middle Tennessee": "Murfreesboro, Tennessee", "Minnesota": "Minneapolis, Minnesota",
    "Mississippi State": "Starkville, Mississippi", "Missouri": "Columbia, Missouri",
    "Missouri State": "Springfield, Missouri", "NC State": "Raleigh, North Carolina", "Chesapeake": "Annapolis, Maryland",
    "Nebraska": "Lincoln, Nebraska", "Nevada": "Reno, Nevada", "New Mexico": "Albuquerque, New Mexico",
    "New Mexico State": "Las Cruces, New Mexico", "North Carolina": "Chapel Hill, North Carolina",
    "North Dakota State": "Fargo, North Dakota", "North Texas": "Denton, Texas", "Northern Illinois": "DeKalb, Illinois",
    "Lakeshore": "Evanston, Illinois", "South Bend": "South Bend, Indiana", "Ohio": "Athens, Ohio",
    "Ohio State": "Columbus, Ohio", "Oklahoma": "Norman, Oklahoma", "Oklahoma State": "Stillwater, Oklahoma",
    "Norfolk": "Norfolk, Virginia", "Mississippi": "Oxford, Mississippi", "Oregon": "Eugene, Oregon",
    "Oregon State": "Corvallis, Oregon", "Pennsylvania": "State College, Pennsylvania",
    "Pittsburgh": "Pittsburgh, Pennsylvania", "Tippecanoe": "West Lafayette, Indiana", "Montrose": "Houston, Texas",
    "New Jersey": "Piscataway, New Jersey", "Dallas": "Dallas, Texas", "Sacramento State": "Sacramento, California",
    "Huntsville": "Huntsville, Texas", "San Diego State": "San Diego, California",
    "San Jose State": "San Jose, California", "South Alabama": "Mobile, Alabama",
    "South Carolina": "Columbia, South Carolina", "South Florida": "Tampa, Florida",
    "Southern Miss": "Hattiesburg, Mississippi", "Palo Alto": "Palo Alto, California", "Syracuse": "Syracuse, New York",
    "Fort Worth": "Fort Worth, Texas", "Philadelphia": "Philadelphia, Pennsylvania", "Tennessee": "Knoxville, Tennessee",
    "Texas": "Austin, Texas", "Brazos": "College Station, Texas", "Texas State": "San Marcos, Texas",
    "Lubbock": "Lubbock, Texas", "Toledo": "Toledo, Ohio", "Troy": "Troy, Alabama", "New Orleans": "New Orleans, Louisiana",
    "Tulsa": "Tulsa, Oklahoma", "Birmingham": "Birmingham, Alabama", "Orlando": "Orlando, Florida", "Los Angeles": "Pasadena, California",
    "Connecticut": "East Hartford, Connecticut", "Monroe": "Monroe, Louisiana", "Massachusetts": "Amherst, Massachusetts",
    "Las Vegas": "Las Vegas, Nevada", "Southern California": "Los Angeles, California", "El Paso": "El Paso, Texas",
    "San Antonio": "San Antonio, Texas", "Utah": "Salt Lake City, Utah", "Utah State": "Logan, Utah",
    "Nashville": "Nashville, Tennessee", "Virginia": "Charlottesville, Virginia", "Blacksburg": "Blacksburg, Virginia",
    "Winston-Salem": "Winston-Salem, North Carolina", "Washington": "Seattle, Washington",
    "Washington State": "Pullman, Washington", "West Virginia": "Morgantown, West Virginia",
    "Western Kentucky": "Bowling Green, Kentucky", "Western Michigan": "Kalamazoo, Michigan",
    "Wisconsin": "Madison, Wisconsin", "Wyoming": "Laramie, Wyoming",
}


def town(school, full=True):
    t = TOWNS.get(school)
    if not t:
        return school
    return t if full else t.split(",")[0]
