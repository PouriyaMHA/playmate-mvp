"""Regions → countries → cities for player profiles.

A region is what matching cares about most (same servers / ping). Country and city refine it.
The US and Canada appear in two regions (west / east) with different cities.
City names that existed before countries were added are kept so old profiles stay valid.
"""

_DATA = [
    ("na-west", "North America West", [
        ("United States", ["Los Angeles", "San Francisco", "Seattle", "San Diego", "Las Vegas", "Phoenix", "Denver",
                           "Portland", "Salt Lake City", "San Jose"]),
        # BC + Alberta (Pacific / Mountain time) play on West servers
        ("Canada", ["Vancouver", "Calgary", "Edmonton", "Victoria", "Surrey", "Burnaby", "Richmond", "Kelowna",
                    "Abbotsford", "Kamloops", "Nanaimo", "Prince George", "Red Deer", "Lethbridge"]),
        ("Mexico", ["Tijuana", "Guadalajara", "Monterrey"]),
    ]),
    ("na-east", "North America East", [
        ("United States", ["New York", "Chicago", "Miami", "Atlanta", "Boston", "Dallas", "Houston", "Washington DC",
                           "Philadelphia", "Detroit", "Orlando", "Austin"]),
        # Prairies (Central time) and everything east of them play on Central / East servers
        ("Canada", ["Toronto", "Montreal", "Ottawa", "Mississauga", "Brampton", "Hamilton", "London", "Kitchener",
                    "Waterloo", "Windsor", "Markham", "Vaughan", "Oshawa", "Barrie", "Guelph", "Sudbury",
                    "Quebec City", "Laval", "Gatineau", "Longueuil", "Sherbrooke", "Winnipeg", "Saskatoon", "Regina",
                    "Halifax", "Moncton", "Fredericton", "Saint John", "Charlottetown", "St. John's"]),
    ]),
    ("eu-west", "Europe West", [
        ("United Kingdom", ["London", "Manchester", "Birmingham", "Liverpool", "Leeds", "Glasgow", "Edinburgh", "Bristol"]),
        ("Ireland", ["Dublin", "Cork"]),
        ("France", ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Lille", "Bordeaux"]),
        ("Spain", ["Madrid", "Barcelona", "Valencia", "Seville", "Bilbao", "Malaga"]),
        ("Portugal", ["Lisbon", "Porto"]),
        ("Netherlands", ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven"]),
        ("Belgium", ["Brussels", "Antwerp", "Ghent"]),
        ("Luxembourg", ["Luxembourg"]),
    ]),
    ("eu-central", "Europe Central & East", [
        ("Germany", ["Frankfurt", "Berlin", "Munich", "Hamburg", "Cologne", "Stuttgart", "Düsseldorf", "Leipzig"]),
        ("Austria", ["Vienna", "Graz", "Salzburg"]),
        ("Switzerland", ["Zurich", "Geneva", "Basel", "Bern"]),
        ("Italy", ["Rome", "Milan", "Naples", "Turin", "Florence", "Bologna"]),
        ("Sweden", ["Stockholm", "Gothenburg", "Malmö"]),
        ("Norway", ["Oslo", "Bergen"]),
        ("Denmark", ["Copenhagen", "Aarhus"]),
        ("Finland", ["Helsinki", "Tampere"]),
        ("Poland", ["Warsaw", "Krakow", "Wroclaw", "Gdansk", "Poznan"]),
        ("Czechia", ["Prague", "Brno"]),
        ("Hungary", ["Budapest"]),
        ("Romania", ["Bucharest", "Cluj-Napoca"]),
        ("Greece", ["Athens", "Thessaloniki"]),
        ("Ukraine", ["Kyiv", "Kharkiv", "Lviv", "Odesa"]),
        ("Russia", ["Moscow", "Saint Petersburg", "Kazan", "Novosibirsk", "Yekaterinburg"]),
    ]),
    ("middle-east", "Middle East", [
        ("Iran", ["Tehran", "Mashhad", "Isfahan", "Karaj", "Shiraz", "Tabriz", "Qom", "Ahvaz", "Kermanshah", "Urmia",
                  "Rasht", "Kerman", "Zahedan", "Hamedan", "Yazd", "Ardabil", "Bandar Abbas", "Arak", "Zanjan", "Sari",
                  "Qazvin", "Gorgan", "Sanandaj", "Khorramabad", "Bushehr", "Birjand", "Semnan", "Bojnurd", "Kish"]),
        ("Turkey", ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana", "Konya", "Gaziantep", "Kayseri", "Trabzon"]),
        ("United Arab Emirates", ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Al Ain"]),
        ("Saudi Arabia", ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar"]),
        ("Iraq", ["Baghdad", "Basra", "Erbil", "Mosul", "Najaf", "Karbala", "Sulaymaniyah"]),
        ("Kuwait", ["Kuwait City"]),
        ("Qatar", ["Doha"]),
        ("Bahrain", ["Manama"]),
        ("Oman", ["Muscat", "Salalah"]),
        ("Jordan", ["Amman", "Irbid"]),
        ("Lebanon", ["Beirut", "Tripoli"]),
        ("Syria", ["Damascus", "Aleppo"]),
        ("Israel", ["Tel Aviv", "Jerusalem", "Haifa"]),
        ("Egypt", ["Cairo", "Alexandria", "Giza"]),
        ("Azerbaijan", ["Baku", "Ganja"]),
        ("Armenia", ["Yerevan"]),
        ("Georgia", ["Tbilisi", "Batumi"]),
        ("Afghanistan", ["Kabul", "Herat", "Mazar-i-Sharif"]),
    ]),
    ("asia", "Asia", [
        ("Japan", ["Tokyo", "Osaka", "Nagoya", "Fukuoka", "Sapporo"]),
        ("South Korea", ["Seoul", "Busan", "Incheon"]),
        ("China", ["Shanghai", "Beijing", "Shenzhen", "Guangzhou", "Chengdu"]),
        ("Hong Kong", ["Hong Kong"]),
        ("Taiwan", ["Taipei", "Kaohsiung"]),
        ("Singapore", ["Singapore"]),
        ("Malaysia", ["Kuala Lumpur", "Penang"]),
        ("Indonesia", ["Jakarta", "Surabaya", "Bandung"]),
        ("Philippines", ["Manila", "Cebu"]),
        ("Thailand", ["Bangkok", "Chiang Mai"]),
        ("Vietnam", ["Ho Chi Minh City", "Hanoi"]),
        ("India", ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune"]),
        ("Pakistan", ["Karachi", "Lahore", "Islamabad"]),
        ("Kazakhstan", ["Almaty", "Astana"]),
    ]),
    ("oceania", "Oceania", [
        ("Australia", ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide"]),
        ("New Zealand", ["Auckland", "Wellington", "Christchurch"]),
    ]),
    ("south-america", "Latin America", [
        ("Brazil", ["São Paulo", "Rio de Janeiro", "Brasília", "Belo Horizonte", "Porto Alegre", "Curitiba"]),
        ("Argentina", ["Buenos Aires", "Córdoba", "Rosario"]),
        ("Chile", ["Santiago", "Valparaíso"]),
        ("Colombia", ["Bogotá", "Medellín", "Cali"]),
        ("Peru", ["Lima"]),
        ("Mexico", ["Mexico City", "Puebla", "Cancún"]),
    ]),
    ("africa", "Africa", [
        ("Morocco", ["Casablanca", "Rabat", "Marrakesh"]),
        ("Algeria", ["Algiers", "Oran"]),
        ("Tunisia", ["Tunis"]),
        ("Nigeria", ["Lagos", "Abuja"]),
        ("South Africa", ["Johannesburg", "Cape Town", "Durban"]),
        ("Kenya", ["Nairobi"]),
        ("Ghana", ["Accra"]),
    ]),
]

REGIONS = [
    {
        "id": rid,
        "label": label,
        "countries": [{"name": name, "cities": cities} for name, cities in countries],
        # flat list kept for older clients
        "cities": [c for _, cities in countries for c in cities],
    }
    for rid, label, countries in _DATA
]

_BY_ID = {r["id"]: r for r in REGIONS}


def get_region(region_id: str | None) -> dict | None:
    return _BY_ID.get(region_id or "")


def get_country(region_id: str | None, name: str | None) -> dict | None:
    r = get_region(region_id)
    return next((c for c in r["countries"] if c["name"] == name), None) if r and name else None


def country_of_city(region_id: str | None, city: str | None) -> str | None:
    r = get_region(region_id)
    if not r or not city:
        return None
    return next((c["name"] for c in r["countries"] if city in c["cities"]), None)


def region_label(region_id: str | None) -> str:
    r = get_region(region_id)
    return r["label"] if r else (region_id or "")
