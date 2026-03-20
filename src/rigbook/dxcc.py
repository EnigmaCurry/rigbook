# DXCC Entity Code to ADIF country name mapping
# Source: ADIF 3.1.6 specification https://adif.org/316/ADIF_316.htm

DXCC_ENTITIES: dict[int, str] = {
    0: "NONE",
    1: "CANADA",
    2: "ABU AIL IS.",
    3: "AFGHANISTAN",
    4: "AGALEGA & ST. BRANDON IS.",
    5: "ALAND IS.",
    6: "ALASKA",
    7: "ALBANIA",
    8: "ALDABRA",
    9: "AMERICAN SAMOA",
    10: "AMSTERDAM & ST. PAUL IS.",
    11: "ANDAMAN & NICOBAR IS.",
    12: "ANGUILLA",
    13: "ANTARCTICA",
    14: "ARMENIA",
    15: "ASIATIC RUSSIA",
    16: "NEW ZEALAND SUBANTARCTIC ISLANDS",
    17: "AVES I.",
    18: "AZERBAIJAN",
    19: "BAJO NUEVO",
    20: "BAKER & HOWLAND IS.",
    21: "BALEARIC IS.",
    22: "PALAU",
    23: "BLENHEIM REEF",
    24: "BOUVET",
    25: "BRITISH NORTH BORNEO",
    26: "BRITISH SOMALILAND",
    27: "BELARUS",
    28: "CANAL ZONE",
    29: "CANARY IS.",
    30: "CELEBE & MOLUCCA IS.",
    31: "C. KIRIBATI (BRITISH PHOENIX IS.)",
    32: "CEUTA & MELILLA",
    33: "CHAGOS IS.",
    34: "CHATHAM IS.",
    35: "CHRISTMAS I.",
    36: "CLIPPERTON I.",
    37: "COCOS I.",
    38: "COCOS (KEELING) IS.",
    39: "COMOROS",
    40: "CRETE",
    41: "CROZET I.",
    42: "DAMAO, DIU",
    43: "DESECHEO I.",
    44: "DESROCHES",
    45: "DODECANESE",
    46: "EAST MALAYSIA",
    47: "EASTER I.",
    48: "E. KIRIBATI (LINE IS.)",
    49: "EQUATORIAL GUINEA",
    50: "MEXICO",
    51: "ERITREA",
    52: "ESTONIA",
    53: "ETHIOPIA",
    54: "EUROPEAN RUSSIA",
    55: "FARQUHAR",
    56: "FERNANDO DE NORONHA",
    57: "FRENCH EQUATORIAL AFRICA",
    58: "FRENCH INDO-CHINA",
    59: "FRENCH WEST AFRICA",
    60: "BAHAMAS",
    61: "FRANZ JOSEF LAND",
    62: "BARBADOS",
    63: "FRENCH GUIANA",
    64: "BERMUDA",
    65: "BRITISH VIRGIN IS.",
    66: "BELIZE",
    67: "FRENCH INDIA",
    68: "KUWAIT/SAUDI ARABIA NEUTRAL ZONE",
    69: "CAYMAN IS.",
    70: "CUBA",
    71: "GALAPAGOS IS.",
    72: "DOMINICAN REPUBLIC",
    74: "EL SALVADOR",
    75: "GEORGIA",
    76: "GUATEMALA",
    77: "GRENADA",
    78: "HAITI",
    79: "GUADELOUPE",
    80: "HONDURAS",
    81: "GERMANY",
    82: "JAMAICA",
    84: "MARTINIQUE",
    85: "BONAIRE, CURACAO",
    86: "NICARAGUA",
    88: "PANAMA",
    89: "TURKS & CAICOS IS.",
    90: "TRINIDAD & TOBAGO",
    91: "ARUBA",
    93: "GEYSER REEF",
    94: "ANTIGUA & BARBUDA",
    95: "DOMINICA",
    96: "MONTSERRAT",
    97: "ST. LUCIA",
    98: "ST. VINCENT",
    99: "GLORIOSO IS.",
    100: "ARGENTINA",
    101: "GOA",
    102: "GOLD COAST, TOGOLAND",
    103: "GUAM",
    104: "BOLIVIA",
    105: "GUANTANAMO BAY",
    106: "GUERNSEY",
    107: "GUINEA",
    108: "BRAZIL",
    109: "GUINEA-BISSAU",
    110: "HAWAII",
    111: "HEARD I.",
    112: "CHILE",
    113: "IFNI",
    114: "ISLE OF MAN",
    115: "ITALIAN SOMALILAND",
    116: "COLOMBIA",
    117: "ITU HQ",
    118: "JAN MAYEN",
    119: "JAVA",
    120: "ECUADOR",
    122: "JERSEY",
    123: "JOHNSTON I.",
    124: "JUAN DE NOVA, EUROPA",
    125: "JUAN FERNANDEZ IS.",
    126: "KALININGRAD",
    127: "KAMARAN IS.",
    128: "KARELO-FINNISH REPUBLIC",
    129: "GUYANA",
    130: "KAZAKHSTAN",
    131: "KERGUELEN IS.",
    132: "PARAGUAY",
    133: "KERMADEC IS.",
    134: "KINGMAN REEF",
    135: "KYRGYZSTAN",
    136: "PERU",
    137: "REPUBLIC OF KOREA",
    138: "KURE I.",
    139: "KURIA MURIA I.",
    140: "SURINAME",
    141: "FALKLAND IS.",
    142: "LAKSHADWEEP IS.",
    143: "LAOS",
    144: "URUGUAY",
    145: "LATVIA",
    146: "LITHUANIA",
    147: "LORD HOWE I.",
    148: "VENEZUELA",
    149: "AZORES",
    150: "AUSTRALIA",
    151: "MALYJ VYSOTSKIJ I.",
    152: "MACAO",
    153: "MACQUARIE I.",
    154: "YEMEN ARAB REPUBLIC",
    155: "MALAYA",
    157: "NAURU",
    158: "VANUATU",
    159: "MALDIVES",
    160: "TONGA",
    161: "MALPELO I.",
    162: "NEW CALEDONIA",
    163: "PAPUA NEW GUINEA",
    164: "MANCHURIA",
    165: "MAURITIUS",
    166: "MARIANA IS.",
    167: "MARKET REEF",
    168: "MARSHALL IS.",
    169: "MAYOTTE",
    170: "NEW ZEALAND",
    171: "MELLISH REEF",
    172: "PITCAIRN I.",
    173: "MICRONESIA",
    174: "MIDWAY I.",
    175: "FRENCH POLYNESIA",
    176: "FIJI",
    177: "MINAMI TORISHIMA",
    178: "MINERVA REEF",
    179: "MOLDOVA",
    180: "MOUNT ATHOS",
    181: "MOZAMBIQUE",
    182: "NAVASSA I.",
    183: "NETHERLANDS BORNEO",
    184: "NETHERLANDS NEW GUINEA",
    185: "SOLOMON IS.",
    186: "NEWFOUNDLAND, LABRADOR",
    187: "NIGER",
    188: "NIUE",
    189: "NORFOLK I.",
    190: "SAMOA",
    191: "NORTH COOK IS.",
    192: "OGASAWARA",
    193: "OKINAWA (RYUKYU IS.)",
    194: "OKINO TORI-SHIMA",
    195: "ANNOBON I.",
    196: "PALESTINE",
    197: "PALMYRA & JARVIS IS.",
    198: "PAPUA TERRITORY",
    199: "PETER 1 I.",
    200: "PORTUGUESE TIMOR",
    201: "PRINCE EDWARD & MARION IS.",
    202: "PUERTO RICO",
    203: "ANDORRA",
    204: "REVILLAGIGEDO",
    205: "ASCENSION I.",
    206: "AUSTRIA",
    207: "RODRIGUES I.",
    208: "RUANDA-URUNDI",
    209: "BELGIUM",
    210: "SAAR",
    211: "SABLE I.",
    212: "BULGARIA",
    213: "SAINT MARTIN",
    214: "CORSICA",
    215: "CYPRUS",
    216: "SAN ANDRES & PROVIDENCIA",
    217: "SAN FELIX & SAN AMBROSIO",
    218: "CZECHOSLOVAKIA",
    219: "SAO TOME & PRINCIPE",
    220: "SARAWAK",
    221: "DENMARK",
    222: "FAROE IS.",
    223: "ENGLAND",
    224: "FINLAND",
    225: "SARDINIA",
    226: "SAUDI ARABIA/IRAQ NEUTRAL ZONE",
    227: "FRANCE",
    228: "SERRANA BANK & RONCADOR CAY",
    229: "GERMAN DEMOCRATIC REPUBLIC",
    230: "FEDERAL REPUBLIC OF GERMANY",
    231: "SIKKIM",
    232: "SOMALIA",
    233: "GIBRALTAR",
    234: "SOUTH COOK IS.",
    235: "SOUTH GEORGIA I.",
    236: "GREECE",
    237: "GREENLAND",
    238: "SOUTH ORKNEY IS.",
    239: "HUNGARY",
    240: "SOUTH SANDWICH IS.",
    241: "SOUTH SHETLAND IS.",
    242: "ICELAND",
    243: "PEOPLE'S DEMOCRATIC REP. OF YEMEN",
    244: "SOUTHERN SUDAN",
    245: "IRELAND",
    246: "SOVEREIGN MILITARY ORDER OF MALTA",
    247: "SPRATLY IS.",
    248: "ITALY",
    249: "ST. KITTS & NEVIS",
    250: "ST. HELENA",
    251: "LIECHTENSTEIN",
    252: "ST. PAUL I.",
    253: "ST. PETER & ST. PAUL ROCKS",
    254: "LUXEMBOURG",
    255: "ST. MAARTEN, SABA, ST. EUSTATIUS",
    256: "MADEIRA IS.",
    257: "MALTA",
    258: "SUMATRA",
    259: "SVALBARD",
    260: "MONACO",
    261: "SWAN IS.",
    262: "TAJIKISTAN",
    263: "NETHERLANDS",
    264: "TANGIER",
    265: "NORTHERN IRELAND",
    266: "NORWAY",
    267: "TERRITORY OF NEW GUINEA",
    268: "TIBET",
    269: "POLAND",
    270: "TOKELAU IS.",
    271: "TRIESTE",
    272: "PORTUGAL",
    273: "TRINDADE & MARTIM VAZ IS.",
    274: "TRISTAN DA CUNHA & GOUGH I.",
    275: "ROMANIA",
    276: "TROMELIN I.",
    277: "ST. PIERRE & MIQUELON",
    278: "SAN MARINO",
    279: "SCOTLAND",
    280: "TURKMENISTAN",
    281: "SPAIN",
    282: "TUVALU",
    283: "UK SOVEREIGN BASE AREAS ON CYPRUS",
    284: "SWEDEN",
    285: "VIRGIN IS.",
    286: "UGANDA",
    287: "SWITZERLAND",
    288: "UKRAINE",
    289: "UNITED NATIONS HQ",
    291: "UNITED STATES OF AMERICA",
    292: "UZBEKISTAN",
    293: "VIET NAM",
    294: "WALES",
    295: "VATICAN",
    296: "SERBIA",
    297: "WAKE I.",
    298: "WALLIS & FUTUNA IS.",
    299: "WEST MALAYSIA",
    301: "W. KIRIBATI (GILBERT IS.)",
    302: "WESTERN SAHARA",
    303: "WILLIS I.",
    304: "BAHRAIN",
    305: "BANGLADESH",
    306: "BHUTAN",
    307: "ZANZIBAR",
    308: "COSTA RICA",
    309: "MYANMAR",
    312: "CAMBODIA",
    315: "SRI LANKA",
    318: "CHINA",
    321: "HONG KONG",
    324: "INDIA",
    327: "INDONESIA",
    330: "IRAN",
    333: "IRAQ",
    336: "ISRAEL",
    339: "JAPAN",
    342: "JORDAN",
    344: "DEMOCRATIC PEOPLE'S REP. OF KOREA",
    345: "BRUNEI DARUSSALAM",
    348: "KUWAIT",
    354: "LEBANON",
    363: "MONGOLIA",
    369: "NEPAL",
    370: "OMAN",
    372: "PAKISTAN",
    375: "PHILIPPINES",
    376: "QATAR",
    378: "SAUDI ARABIA",
    379: "SEYCHELLES",
    381: "SINGAPORE",
    382: "DJIBOUTI",
    384: "SYRIA",
    386: "TAIWAN",
    387: "THAILAND",
    390: "TURKEY",
    391: "UNITED ARAB EMIRATES",
    400: "ALGERIA",
    401: "ANGOLA",
    402: "BOTSWANA",
    404: "BURUNDI",
    406: "CAMEROON",
    408: "CENTRAL AFRICA",
    409: "CAPE VERDE",
    410: "CHAD",
    411: "COMOROS",
    412: "REPUBLIC OF THE CONGO",
    414: "DEMOCRATIC REPUBLIC OF THE CONGO",
    416: "BENIN",
    420: "GABON",
    422: "THE GAMBIA",
    424: "GHANA",
    428: "COTE D'IVOIRE",
    430: "KENYA",
    432: "LESOTHO",
    434: "LIBERIA",
    436: "LIBYA",
    438: "MADAGASCAR",
    440: "MALAWI",
    442: "MALI",
    444: "MAURITANIA",
    446: "MOROCCO",
    450: "NIGERIA",
    452: "ZIMBABWE",
    453: "REUNION I.",
    454: "RWANDA",
    456: "SENEGAL",
    458: "SIERRA LEONE",
    460: "ROTUMA I.",
    462: "REPUBLIC OF SOUTH AFRICA",
    464: "NAMIBIA",
    466: "SUDAN",
    468: "KINGDOM OF ESWATINI",
    470: "TANZANIA",
    474: "TUNISIA",
    478: "EGYPT",
    480: "BURKINA FASO",
    482: "ZAMBIA",
    483: "TOGO",
    488: "WALVIS BAY",
    489: "CONWAY REEF",
    490: "BANABA I. (OCEAN I.)",
    492: "YEMEN",
    493: "PENGUIN IS.",
    497: "CROATIA",
    499: "SLOVENIA",
    501: "BOSNIA-HERZEGOVINA",
    502: "NORTH MACEDONIA (REPUBLIC OF)",
    503: "CZECH REPUBLIC",
    504: "SLOVAK REPUBLIC",
    505: "PRATAS I.",
    506: "SCARBOROUGH REEF",
    507: "TEMOTU PROVINCE",
    508: "AUSTRAL I.",
    509: "MARQUESAS IS.",
    510: "PALESTINE",
    511: "TIMOR-LESTE",
    512: "CHESTERFIELD IS.",
    513: "DUCIE I.",
    514: "MONTENEGRO",
    515: "SWAINS I.",
    516: "SAINT BARTHELEMY",
    517: "CURACAO",
    518: "SINT MAARTEN",
    519: "SABA & ST. EUSTATIUS",
    520: "BONAIRE",
    521: "SOUTH SUDAN (REPUBLIC OF)",
    522: "REPUBLIC OF KOSOVO",
}


def dxcc_country(code: int | str | None) -> str | None:
    """Return the ADIF standardized country name for a DXCC entity code."""
    if code is None:
        return None
    try:
        return DXCC_ENTITIES.get(int(code))
    except (ValueError, TypeError):
        return None


# ISO 3166-1 alpha-2 to primary DXCC entity code
ISO_TO_DXCC: dict[str, int] = {
    "AD": 203,  # Andorra
    "AF": 3,  # Afghanistan
    "AG": 94,  # Antigua & Barbuda
    "AI": 12,  # Anguilla
    "AL": 7,  # Albania
    "AM": 14,  # Armenia
    "AO": 401,  # Angola
    "AQ": 13,  # Antarctica
    "AR": 100,  # Argentina
    "AS": 9,  # American Samoa
    "AT": 206,  # Austria
    "AU": 150,  # Australia
    "AW": 91,  # Aruba
    "AX": 5,  # Aland Is.
    "AZ": 18,  # Azerbaijan
    "BA": 501,  # Bosnia-Herzegovina
    "BB": 62,  # Barbados
    "BD": 305,  # Bangladesh
    "BE": 209,  # Belgium
    "BF": 480,  # Burkina Faso
    "BG": 212,  # Bulgaria
    "BH": 304,  # Bahrain
    "BI": 404,  # Burundi
    "BJ": 416,  # Benin
    "BL": 516,  # Saint Barthelemy
    "BM": 64,  # Bermuda
    "BN": 345,  # Brunei Darussalam
    "BO": 104,  # Bolivia
    "BQ": 520,  # Bonaire
    "BR": 108,  # Brazil
    "BS": 60,  # Bahamas
    "BT": 306,  # Bhutan
    "BV": 24,  # Bouvet
    "BW": 402,  # Botswana
    "BY": 27,  # Belarus
    "BZ": 66,  # Belize
    "CA": 1,  # Canada
    "CC": 38,  # Cocos (Keeling) Is.
    "CD": 414,  # Democratic Republic of the Congo
    "CF": 408,  # Central Africa
    "CG": 412,  # Republic of the Congo
    "CH": 287,  # Switzerland
    "CI": 428,  # Cote d'Ivoire
    "CK": 234,  # South Cook Is.
    "CL": 112,  # Chile
    "CM": 406,  # Cameroon
    "CN": 318,  # China
    "CO": 116,  # Colombia
    "CR": 308,  # Costa Rica
    "CU": 70,  # Cuba
    "CV": 409,  # Cape Verde
    "CW": 517,  # Curacao
    "CX": 35,  # Christmas I.
    "CY": 215,  # Cyprus
    "CZ": 503,  # Czech Republic
    "DE": 81,  # Germany
    "DJ": 382,  # Djibouti
    "DK": 221,  # Denmark
    "DM": 95,  # Dominica
    "DO": 72,  # Dominican Republic
    "DZ": 400,  # Algeria
    "EC": 120,  # Ecuador
    "EE": 52,  # Estonia
    "EG": 478,  # Egypt
    "EH": 302,  # Western Sahara
    "ER": 51,  # Eritrea
    "ES": 281,  # Spain
    "ET": 53,  # Ethiopia
    "FI": 224,  # Finland
    "FJ": 176,  # Fiji
    "FK": 141,  # Falkland Is.
    "FM": 173,  # Micronesia
    "FO": 222,  # Faroe Is.
    "FR": 227,  # France
    "GA": 420,  # Gabon
    "GB": 223,  # England
    "GD": 77,  # Grenada
    "GE": 75,  # Georgia
    "GF": 63,  # French Guiana
    "GG": 106,  # Guernsey
    "GH": 424,  # Ghana
    "GI": 233,  # Gibraltar
    "GL": 237,  # Greenland
    "GM": 422,  # The Gambia
    "GN": 107,  # Guinea
    "GP": 79,  # Guadeloupe
    "GQ": 49,  # Equatorial Guinea
    "GR": 236,  # Greece
    "GS": 235,  # South Georgia I.
    "GT": 76,  # Guatemala
    "GU": 103,  # Guam
    "GW": 109,  # Guinea-Bissau
    "GY": 129,  # Guyana
    "HK": 321,  # Hong Kong
    "HM": 111,  # Heard I.
    "HN": 80,  # Honduras
    "HR": 497,  # Croatia
    "HT": 78,  # Haiti
    "HU": 239,  # Hungary
    "ID": 327,  # Indonesia
    "IE": 245,  # Ireland
    "IL": 336,  # Israel
    "IM": 114,  # Isle of Man
    "IN": 324,  # India
    "IQ": 333,  # Iraq
    "IR": 330,  # Iran
    "IS": 242,  # Iceland
    "IT": 248,  # Italy
    "JE": 122,  # Jersey
    "JM": 82,  # Jamaica
    "JO": 342,  # Jordan
    "JP": 339,  # Japan
    "KE": 430,  # Kenya
    "KG": 135,  # Kyrgyzstan
    "KH": 312,  # Cambodia
    "KI": 301,  # W. Kiribati (Gilbert Is.)
    "KM": 411,  # Comoros
    "KN": 249,  # St. Kitts & Nevis
    "KP": 344,  # Democratic People's Rep. of Korea
    "KR": 137,  # Republic of Korea
    "KW": 348,  # Kuwait
    "KY": 69,  # Cayman Is.
    "KZ": 130,  # Kazakhstan
    "LA": 143,  # Laos
    "LB": 354,  # Lebanon
    "LC": 97,  # St. Lucia
    "LI": 251,  # Liechtenstein
    "LK": 315,  # Sri Lanka
    "LR": 434,  # Liberia
    "LS": 432,  # Lesotho
    "LT": 146,  # Lithuania
    "LU": 254,  # Luxembourg
    "LV": 145,  # Latvia
    "LY": 436,  # Libya
    "MA": 446,  # Morocco
    "MC": 260,  # Monaco
    "MD": 179,  # Moldova
    "ME": 514,  # Montenegro
    "MF": 213,  # Saint Martin
    "MG": 438,  # Madagascar
    "MH": 168,  # Marshall Is.
    "MK": 502,  # North Macedonia
    "ML": 442,  # Mali
    "MM": 309,  # Myanmar
    "MN": 363,  # Mongolia
    "MO": 152,  # Macao
    "MQ": 84,  # Martinique
    "MR": 444,  # Mauritania
    "MS": 96,  # Montserrat
    "MT": 257,  # Malta
    "MU": 165,  # Mauritius
    "MV": 159,  # Maldives
    "MW": 440,  # Malawi
    "MX": 50,  # Mexico
    "MY": 299,  # West Malaysia
    "MZ": 181,  # Mozambique
    "NA": 464,  # Namibia
    "NC": 162,  # New Caledonia
    "NE": 187,  # Niger
    "NF": 189,  # Norfolk I.
    "NG": 450,  # Nigeria
    "NI": 86,  # Nicaragua
    "NL": 263,  # Netherlands
    "NO": 266,  # Norway
    "NP": 369,  # Nepal
    "NR": 157,  # Nauru
    "NU": 188,  # Niue
    "NZ": 170,  # New Zealand
    "OM": 370,  # Oman
    "PA": 88,  # Panama
    "PE": 136,  # Peru
    "PF": 175,  # French Polynesia
    "PG": 163,  # Papua New Guinea
    "PH": 375,  # Philippines
    "PK": 372,  # Pakistan
    "PL": 269,  # Poland
    "PM": 277,  # St. Pierre & Miquelon
    "PN": 172,  # Pitcairn I.
    "PR": 202,  # Puerto Rico
    "PS": 510,  # Palestine
    "PT": 272,  # Portugal
    "PW": 22,  # Palau
    "PY": 132,  # Paraguay
    "QA": 376,  # Qatar
    "RE": 453,  # Reunion I.
    "RO": 275,  # Romania
    "RS": 296,  # Serbia
    "RU": 54,  # European Russia
    "RW": 454,  # Rwanda
    "SA": 378,  # Saudi Arabia
    "SB": 185,  # Solomon Is.
    "SC": 379,  # Seychelles
    "SD": 466,  # Sudan
    "SE": 284,  # Sweden
    "SG": 381,  # Singapore
    "SH": 250,  # St. Helena
    "SI": 499,  # Slovenia
    "SJ": 259,  # Svalbard
    "SK": 504,  # Slovak Republic
    "SL": 458,  # Sierra Leone
    "SM": 278,  # San Marino
    "SN": 456,  # Senegal
    "SO": 232,  # Somalia
    "SR": 140,  # Suriname
    "SS": 521,  # South Sudan
    "ST": 219,  # Sao Tome & Principe
    "SV": 74,  # El Salvador
    "SX": 518,  # Sint Maarten
    "SY": 384,  # Syria
    "SZ": 468,  # Kingdom of Eswatini
    "TC": 89,  # Turks & Caicos Is.
    "TD": 410,  # Chad
    "TG": 483,  # Togo
    "TH": 387,  # Thailand
    "TJ": 262,  # Tajikistan
    "TK": 270,  # Tokelau Is.
    "TL": 511,  # Timor-Leste
    "TM": 280,  # Turkmenistan
    "TN": 474,  # Tunisia
    "TO": 160,  # Tonga
    "TR": 390,  # Turkey
    "TT": 90,  # Trinidad & Tobago
    "TV": 282,  # Tuvalu
    "TW": 386,  # Taiwan
    "TZ": 470,  # Tanzania
    "UA": 288,  # Ukraine
    "UG": 286,  # Uganda
    "US": 291,  # United States of America
    "UY": 144,  # Uruguay
    "UZ": 292,  # Uzbekistan
    "VA": 295,  # Vatican
    "VC": 98,  # St. Vincent
    "VE": 148,  # Venezuela
    "VG": 65,  # British Virgin Is.
    "VI": 285,  # Virgin Is.
    "VN": 293,  # Viet Nam
    "VU": 158,  # Vanuatu
    "WF": 298,  # Wallis & Futuna Is.
    "WS": 190,  # Samoa
    "XK": 522,  # Republic of Kosovo
    "YE": 492,  # Yemen
    "YT": 169,  # Mayotte
    "ZA": 462,  # Republic of South Africa
    "ZM": 482,  # Zambia
    "ZW": 452,  # Zimbabwe
}
