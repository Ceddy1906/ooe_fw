<p align="center"><img src="icon.svg" width="120" alt="Icon"></p>

# OÖ Feuerwehr Einsätze

Home-Assistant-Integration, die die **laufenden Feuerwehreinsätze in Oberösterreich** anzeigt. Datenquelle ist der öffentliche JSON-Feed des OÖ Landesfeuerwehrverbands (`json_laufend.txt`).

## Funktionen

- Filter nach **Bezirk** (Mehrfachauswahl, ohne Auswahl werden alle Bezirke angezeigt)
- Filter nach **Einsatz od. Einsatzübung**: alle anzeigen, nur diese oder alles außer diesen
- Einstellbares **Abfrageintervall**: 5, 10, 15 (Standard), 30, 45 oder 60 Minuten
- Eigene **Lovelace-Card**, die automatisch registriert wird (keine Ressource nötig)
- **Benachrichtigungen** an frei wählbare Ziele (neue, beendete und geänderte Einsätze)
- Sensoren und Events für eigene Automationen

## Installation über HACS

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Ceddy1906/ooe_fw` eintragen, Kategorie **Integration**.
2. „OÖ Feuerwehr Einsätze“ installieren und Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „OÖ Feuerwehr Einsätze“**.
4. Bezirke, Filter, Abfrageintervall und (optional) Benachrichtigungen wählen. Spätere Änderungen sind über **Konfigurieren** an der Integration möglich.

Die Card wird mit der Integration geladen. Nach einem Update hilft ein harter Reload des Browsers (Strg+F5), in der Companion-App das Leeren des Frontend-Caches.

## Entitäten

| Entität | Beschreibung |
|---|---|
| `sensor.…_aktuelle_einsaetze` | Anzahl der Einsätze (nach Filter). Das Attribut `einsaetze` enthält alle Details. |
| `binary_sensor.…_einsatz_aktiv` | `on`, sobald mindestens ein Einsatz vorliegt. |

Felder je Einsatz: `nummer`, `beginn`, `alarmstufe`, `einsatzort`, `einsatztyp`, `einsatzsubtyp`, `bezirk`, `gemeinde`, `bereich`, `strasse`, `zusatz`, `latitude`, `longitude`, `karte`, `feuerwehren` (Liste).

## Benachrichtigungen

In den Optionen der Integration wählst du aus, **wohin** Nachrichten gehen (Mehrfachauswahl aus allen `notify`-Diensten und -Entitäten, z. B. `notify.mobile_app_<handy>`):

| Option | Standard | Beschreibung |
|---|---|---|
| Bei neuem Einsatz | an | Typ, Ort, Alarmstufe, Beginn und Feuerwehren, bei der Companion-App mit Link zur Karte |
| Bei beendetem Einsatz | aus | Ein Einsatz gilt als beendet, sobald er nicht mehr im Feed steht (inkl. Dauer) |
| Bei Änderung | aus | Höhere Alarmstufe oder weitere Feuerwehren |
| Ab Alarmstufe | 0 | Nachrichten nur ab dieser Alarmstufe |

- Es werden nur Einsätze gemeldet, die durch deine Bezirks- und Übungsfilter kommen.
- Beim ersten Start, nach geänderten Filtern oder nach längerer Pause werden bereits laufende Einsätze **nicht** gemeldet.
- Wie aktuell die Nachrichten sind, bestimmt das Abfrageintervall.

### Events

Unabhängig von den Nachrichten werden immer diese Events ausgelöst (Daten: alle Felder des Einsatzes, siehe oben): `ooelfv_einsaetze_neu`, `ooelfv_einsaetze_beendet` (zusätzlich `dauer_minuten`) und `ooelfv_einsaetze_geaendert` (zusätzlich `aenderungen`, `neue_feuerwehren`). Die Mindest-Alarmstufe gilt für Events nicht.

```yaml
triggers:
  - trigger: event
    event_type: ooelfv_einsaetze_neu
actions:
  - action: tts.speak
    data:
      message: "Neuer Einsatz: {{ trigger.event.data.einsatztyp }} in {{ trigger.event.data.gemeinde }}"
```

## Card

```yaml
type: custom:ooelfv-einsaetze-card
entity: sensor.aktuelle_einsatze   # deine Entität „Aktuelle Einsätze“
title: Feuerwehr Einsätze   # optional
max_einsaetze: 10           # optional
```

Angezeigt werden je Einsatz: Beginn, Feuerwehren vor Ort (eine oder mehrere), Alarmstufe, Einsatzort, Einsatztyp und Ort (mit Link zur Karte auf OpenStreetMap). Liegt kein Einsatz vor, steht in der Card „Keine Einsätze“.

## Hinweise

- Die Bezirke müssen so geschrieben sein wie im Feld `bezirk.text` der API (z. B. „Braunau“, „Ried im Innkreis“). Fehlt ein Bezirk in der Liste, kann er frei eingegeben werden.
- Je länger das Abfrageintervall, desto später erscheinen neue Einsätze, Nachrichten und Events.
- Der Feed enthält nur laufende Einsätze. „Beendet“ bedeutet daher, dass ein Einsatz nicht mehr im Feed steht.
- Die bekannten Einsätze werden in `.storage/ooelfv_einsaetze.known` gespeichert, damit nach einem Neustart nichts doppelt gemeldet wird.
- Das Integrations-Icon (`brand/icon.png`) zeigt Home Assistant ab Version 2026.3 an.
- Inoffizielles Projekt, steht in keiner Verbindung zum OÖ Landesfeuerwehrverband. Das Icon ist eine eigene Grafik.
