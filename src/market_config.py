SENTIMENT_MONTHLY = {
    "mcsi":        "UMCSENT",       # Michigan Consumer Sentiment
    "cpi":         "CPIAUCSL",      # US CPI (inflation)
    "hy_spread":   "BAMLH0A0HYM2",  # US high-yield credit spread
    "yield_curve": "T10Y2Y",        # 10yr-2yr Treasury slope
    "epu":         "USEPUINDXM",    # Economic Policy Uncertainty
}

SENTIMENT_DAILY = {
    "vix":         "VIXCLS",        # CBOE VIX
    "ted_spread":  "TEDRATE",       # TED spread (interbank stress)
    "hy_spread":   "BAMLH0A0HYM2",  # ICE BofA US High Yield OAS (~1997+)
    "baa_spread":  "BAA10Y",        # Moody's Baa - 10yr Treasury (1986+)
}

# All equity markets in the cross-market study.
# ticker  : Yahoo Finance symbol passed to yf.download()
# country : display name used in results tables
MARKETS = {
    # ── North America ──────────────────────────────────────────────────────────
    "sp500":         {"country": "USA",               "ticker": "^GSPC",       "region": "N. America",   "market_class": "DM"},
    "nasdaq":        {"country": "USA (NASDAQ)",      "ticker": "^IXIC",       "region": "N. America",   "market_class": "DM"},
    "djia":          {"country": "USA (DJIA)",        "ticker": "^DJI",        "region": "N. America",   "market_class": "DM"},
    "rut":           {"country": "USA (Small-Cap)",   "ticker": "^RUT",        "region": "N. America",   "market_class": "DM"},
    "rui":           {"country": "USA (Large-Cap)",   "ticker": "^RUI",        "region": "N. America",   "market_class": "DM"},
    "sp400":         {"country": "USA (Mid-Cap)",     "ticker": "^MID",        "region": "N. America",   "market_class": "DM"},
    "wilshire5000":  {"country": "USA (Total Mkt)",   "ticker": "^W5000",      "region": "N. America",   "market_class": "DM"},
    "tsx":           {"country": "Canada",            "ticker": "^GSPTSE",     "region": "N. America",   "market_class": "DM"},

    # ── Latin America ─────────────────────────────────────────────────────────
    "ipc":           {"country": "Mexico",            "ticker": "^MXX",        "region": "Latin America", "market_class": "EM"},
    "bovespa":       {"country": "Brazil",            "ticker": "^BVSP",       "region": "Latin America", "market_class": "EM"},
    "ipsa":          {"country": "Chile",             "ticker": "^IPSA",       "region": "Latin America", "market_class": "EM"},
    "colcap":        {"country": "Colombia",          "ticker": "^COLCAP",     "region": "Latin America", "market_class": "EM"},
    "merval":        {"country": "Argentina",         "ticker": "^MERV",       "region": "Latin America", "market_class": "Frontier"},

    # ── Europe – Western & Southern ───────────────────────────────────────────
    "eurostoxx50":   {"country": "Eurozone",          "ticker": "^STOXX50E",   "region": "W. Europe",    "market_class": "DM"},
    "ftse100":       {"country": "UK",                "ticker": "^FTSE",       "region": "W. Europe",    "market_class": "DM"},
    "ftmc":          {"country": "UK (Mid-Cap)",      "ticker": "^FTMC",       "region": "W. Europe",    "market_class": "DM"},
    "dax":           {"country": "Germany",           "ticker": "^GDAXI",      "region": "W. Europe",    "market_class": "DM"},
    "mdax":          {"country": "Germany (MDAX)",    "ticker": "^MDAXI",      "region": "W. Europe",    "market_class": "DM"},
    "cac40":         {"country": "France",            "ticker": "^FCHI",       "region": "W. Europe",    "market_class": "DM"},
    "ibex35":        {"country": "Spain",             "ticker": "^IBEX",       "region": "W. Europe",    "market_class": "DM"},
    "smi":           {"country": "Switzerland",       "ticker": "^SSMI",       "region": "W. Europe",    "market_class": "DM"},
    "aex":           {"country": "Netherlands",       "ticker": "^AEX",        "region": "W. Europe",    "market_class": "DM"},
    "ftsemib":       {"country": "Italy",             "ticker": "FTSEMIB.MI",  "region": "W. Europe",    "market_class": "DM"},
    "iseq":          {"country": "Ireland",           "ticker": "^ISEQ",       "region": "W. Europe",    "market_class": "DM"},
    "athex":         {"country": "Greece",            "ticker": "GD.AT",       "region": "W. Europe",    "market_class": "DM"},
    "bel20":         {"country": "Belgium",           "ticker": "^BFX",        "region": "W. Europe",    "market_class": "DM"},
    "atx":           {"country": "Austria",           "ticker": "^ATX",        "region": "W. Europe",    "market_class": "DM"},
    "psi20":         {"country": "Portugal",          "ticker": "PSI20.LS",    "region": "W. Europe",    "market_class": "DM"},

    # ── Europe – Northern & Eastern ───────────────────────────────────────────
    "omxstockholm":  {"country": "Sweden",            "ticker": "^OMX",        "region": "N. Europe",    "market_class": "DM"},
    "omxhelsinki":   {"country": "Finland",           "ticker": "^OMXH25",     "region": "N. Europe",    "market_class": "DM"},
    "omxcopenhagen": {"country": "Denmark",           "ticker": "^OMXC25",     "region": "N. Europe",    "market_class": "DM"},
    "oseax":         {"country": "Norway",            "ticker": "^OSEAX",      "region": "N. Europe",    "market_class": "DM"},
    "bux":           {"country": "Hungary",           "ticker": "^BUX",        "region": "E. Europe",    "market_class": "EM"},

    # ── Middle East & Africa ──────────────────────────────────────────────────
    "ta125":         {"country": "Israel",            "ticker": "^TA125.TA",   "region": "Middle East",  "market_class": "DM"},
    "ta35":          {"country": "Israel (TA-35)",    "ticker": "TA35.TA",     "region": "Middle East",  "market_class": "DM"},
    "bist100":       {"country": "Turkey",            "ticker": "XU100.IS",    "region": "Middle East",  "market_class": "EM"},


    # ── Asia – Japan ─────────────────────────────────────────────────────────
    "nikkei225":     {"country": "Japan",             "ticker": "^N225",       "region": "Japan",        "market_class": "DM"},
    "topix":         {"country": "Japan (TOPIX)",     "ticker": "1306.T",      "region": "Japan",        "market_class": "DM"},

    # ── Asia – China & Hong Kong ──────────────────────────────────────────────
    "shanghai":      {"country": "China (SSE)",       "ticker": "000001.SS",   "region": "China",        "market_class": "EM"},
    "csi300":        {"country": "China (CSI 300)",   "ticker": "000300.SS",   "region": "China",        "market_class": "EM"},
    "szse":          {"country": "China (SZSE)",      "ticker": "399001.SZ",   "region": "China",        "market_class": "EM"},
    "hangseng":      {"country": "Hong Kong",         "ticker": "^HSI",        "region": "Asia Pacific", "market_class": "DM"},
    "hscei":         {"country": "Hong Kong (H-shr)", "ticker": "^HSCE",       "region": "Asia Pacific", "market_class": "EM"},

    # ── Asia – Korea ──────────────────────────────────────────────────────────
    "kospi":         {"country": "South Korea",       "ticker": "^KS11",       "region": "Asia Pacific", "market_class": "EM"},
    "kosdaq":        {"country": "South Korea (KQ)",  "ticker": "^KQ11",       "region": "Asia Pacific", "market_class": "EM"},

    # ── Asia – South ─────────────────────────────────────────────────────────
    "nifty50":       {"country": "India",             "ticker": "^NSEI",       "region": "SE Asia",      "market_class": "EM"},
    "kse100":        {"country": "Pakistan",          "ticker": "^KSE",        "region": "S. Asia",      "market_class": "EM"},

    # ── Asia – Southeast ──────────────────────────────────────────────────────
    "sti":           {"country": "Singapore",         "ticker": "^STI",        "region": "Asia Pacific", "market_class": "DM"},
    "twse":          {"country": "Taiwan",            "ticker": "^TWII",       "region": "Asia Pacific", "market_class": "EM"},
    "jkse":          {"country": "Indonesia",         "ticker": "^JKSE",       "region": "SE Asia",      "market_class": "EM"},
    "lq45":          {"country": "Indonesia (LQ45)",  "ticker": "^JKLQ45",     "region": "SE Asia",      "market_class": "EM"},
    "klci":          {"country": "Malaysia",          "ticker": "^KLSE",       "region": "SE Asia",      "market_class": "EM"},
    "set":           {"country": "Thailand",          "ticker": "^SET.BK",     "region": "SE Asia",      "market_class": "EM"},
    "psei":          {"country": "Philippines",       "ticker": "PSEI.PS",     "region": "SE Asia",      "market_class": "EM"},

    # ── Pacific ───────────────────────────────────────────────────────────────
    "asx200":        {"country": "Australia",         "ticker": "^AXJO",       "region": "Pacific",      "market_class": "DM"},
    "aord":          {"country": "Australia (All)",   "ticker": "^AORD",       "region": "Pacific",      "market_class": "DM"},
    "nzx50":         {"country": "New Zealand",       "ticker": "^NZ50",       "region": "Asia Pacific", "market_class": "DM"},
}

# OECD country codes for markets with a published consumer confidence index.
# eurostoxx50 excluded — no single OECD country code for the Eurozone aggregate.
# Secondary indices for the same country share the same OECD code.
# Non-OECD markets excluded: china (csi300/szse/shanghai), indonesia (jkse/lq45),
#   thailand (set), philippines (psei), malaysia (klci), hong kong (hangseng),
#   taiwan (twse), singapore (sti), south africa (jse), egypt (egx30),
#   argentina (merval).
OECD_CCI_MARKETS = {
    # ── North America ──────────────────────────────────────────────────────────
    "sp500":         "USA",
    "nasdaq":        "USA",
    "djia":          "USA",
    "rut":           "USA",
    "rui":           "USA",
    "sp400":         "USA",
    "wilshire5000":  "USA",
    "tsx":           "CAN",

    # ── Latin America ─────────────────────────────────────────────────────────
    "ipc":           "MEX",
    "ipsa":          "CHL",
    "colcap":        "COL",

    # ── Europe – Western & Southern ───────────────────────────────────────────
    "ftse100":       "GBR",
    "dax":           "DEU",
    "cac40":         "FRA",
    "ibex35":        "ESP",
    "smi":           "CHE",
    "aex":           "NLD",
    "ftsemib":       "ITA",
    "iseq":          "IRL",
    "athex":         "GRC",
    "bel20":         "BEL",
    "atx":           "AUT",
    "psi20":         "PRT",

    # ── Europe – Northern & Eastern ───────────────────────────────────────────
    "omxstockholm":  "SWE",
    "omxhelsinki":   "FIN",
    "omxcopenhagen": "DNK",
    "oseax":         "NOR",
    "wig20":         "POL",
    "px":            "CZE",

    # ── Middle East ───────────────────────────────────────────────────────────
    "ta125":         "ISR",
    "ta35":          "ISR",
    "bist100":       "TUR",

    # ── Asia – Japan ─────────────────────────────────────────────────────────
    "nikkei225":     "JPN",
    "topix":         "JPN",

    # ── Asia – Korea ──────────────────────────────────────────────────────────
    "kospi":         "KOR",
    "kosdaq":        "KOR",

    # ── Asia – South ──────────────────────────────────────────────────────────
    "nifty50":       "IND",

    # ── Pacific ───────────────────────────────────────────────────────────────
    "asx200":        "AUS",
    "nzx50":         "NZL",
}
