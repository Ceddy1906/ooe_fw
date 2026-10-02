"""Konstanten für OÖ Feuerwehr Einsätze."""

DOMAIN = "ooelfv_einsaetze"

API_URL = "https://cf-einsaetze.ooelfv.at/webext2/rss/json_laufend.txt"

CONF_BEZIRKE = "bezirke"
CONF_SUBTYP_FILTER = "subtyp_filter"
CONF_INTERVAL = "interval"

# Filter auf einsatzsubtyp.text
FILTER_ALL = "all"
FILTER_ONLY = "only"
FILTER_EXCLUDE = "exclude"
SUBTYP_UEBUNG_TEXT = "Einsatz od. Einsatzübung"

DEFAULT_SUBTYP_FILTER = FILTER_ALL
DEFAULT_INTERVAL = 15
INTERVAL_OPTIONS = [5, 10, 15, 30, 45, 60]

# Schreibweise wie im Feld bezirk.text der API. Weitere Werte können in der
# Konfiguration frei eingegeben werden.
BEZIRKE = [
    "Braunau",
    "Eferding",
    "Freistadt",
    "Gmunden",
    "Grieskirchen",
    "Kirchdorf",
    "Linz",
    "Linz-Land",
    "Perg",
    "Ried im Innkreis",
    "Rohrbach",
    "Schärding",
    "Steyr",
    "Steyr-Land",
    "Urfahr-Umgebung",
    "Vöcklabruck",
    "Wels",
    "Wels-Land",
]

CARD_URL = f"/{DOMAIN}/ooelfv-einsaetze-card.js"
