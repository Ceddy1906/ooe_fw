<p align="center"><img src="icon.svg" width="120" alt="Icon"></p>

# OÖ Feuerwehr Einsätze

Home-Assistant-Integration, die die **laufenden Feuerwehreinsätze in Oberösterreich** anzeigt. Datenquelle ist der öffentliche JSON-Feed des OÖ Landesfeuerwehrverbands (`json_laufend.txt`).

## Funktionen

- Filter nach **Bezirk** (Mehrfachauswahl, ohne Auswahl werden alle Bezirke angezeigt)
- Filter nach **Einsatz od. Einsatzübung**: alle anzeigen, nur diese oder alles außer diesen
- Einstellbares **Abfrageintervall**: 5, 10, 15 (Standard), 30, 45 oder 60 Minuten
- Eigene **Lovelace-Card**, die automatisch registriert wird (keine Ressource nötig)
- Sensoren für Automationen (z. B. Push-Nachricht bei neuem Einsatz)

## Installation über HACS

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Ceddy1906/ooe_fw` eintragen, Kategorie **Integration**.
2. „OÖ Feuerwehr Einsätze“ installieren und Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → „OÖ Feuerwehr Einsätze“**.
4. Bezirke, Filter und Abfrageintervall wählen. Spätere Änderungen sind über **Konfigurieren** an der Integration möglich.

## Entitäten

| Entität | Beschreibung |
|---|---|
| `sensor.…_aktuelle_einsaetze` | Anzahl der Einsätze (nach Filter). Das Attribut `einsaetze` enthält alle Details. |
| `binary_sensor.…_einsatz_aktiv` | `on`, sobald mindestens ein Einsatz vorliegt. |

Felder je Einsatz: `nummer`, `beginn`, `alarmstufe`, `einsatzort`, `einsatztyp`, `einsatzsubtyp`, `bezirk`, `gemeinde`, `bereich`, `strasse`, `zusatz`, `latitude`, `longitude`, `karte`, `feuerwehren` (Liste).

## Card

```yaml
type: custom:ooelfv-einsaetze-card
entity: sensor.oo_feuerwehr_einsaetze_aktuelle_einsaetze
title: Feuerwehr Einsätze   # optional
max_einsaetze: 10           # optional
```

Angezeigt werden je Einsatz: Beginn, Feuerwehren vor Ort (eine oder mehrere), Alarmstufe, Einsatzort, Einsatztyp und Ort (mit Link zur Karte auf OpenStreetMap).

## Hinweise

- Die Bezirke müssen so geschrieben sein wie im Feld `bezirk.text` der API (z. B. „Braunau“, „Ried im Innkreis“). Fehlt ein Bezirk in der Liste, kann er frei eingegeben werden.
- Je länger das Abfrageintervall, desto später erscheinen neue Einsätze.
- Inoffizielles Projekt, steht in keiner Verbindung zum OÖ Landesfeuerwehrverband. Das Icon ist eine eigene Grafik.
