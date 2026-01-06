# Weight Battle

Eine mobile-first Web-App für einen freundschaftlichen Gewichtsverlust-Wettbewerb. Perfekt für Familien oder Freundesgruppen, die sich gegenseitig motivieren wollen.

## Inhalt

- [Features](#features)
- [Spielregeln](#spielregeln)
- [Technologie](#technologie)
- [Installation](#installation)
  - [Lokale Entwicklung](#lokale-entwicklung)
  - [Docker Deployment](#docker-deployment)
- [Verwendung](#verwendung)
- [API Dokumentation](#api-dokumentation)
- [Projektstruktur](#projektstruktur)
- [Konfiguration](#konfiguration)

## Features

- **Wöchentliche Wiegungen**: Jeder Teilnehmer wiegt sich einmal pro Woche
- **Prozentuale Bewertung**: Faire Berechnung basierend auf prozentualem Gewichtsverlust
- **Topf-System**: Verlierer der Woche zahlt einen festgelegten Betrag in den Topf
- **Statistiken & Charts**: Übersichtliche Darstellung des Fortschritts
- **Prognosen**: Lineare Regression zur Vorhersage des Endgewichts
- **Audit-Log**: Transparente Nachverfolgung aller Änderungen
- **Mobile-First Design**: Optimiert für die Nutzung auf dem Smartphone
- **Keine Registrierung**: Einfache Einrichtung ohne Accounts

## Spielregeln

### Wöchentliche Bewertung

- Referenzwert ist immer das **Gewicht der Vorwoche**
- Formel: `Prozent = ((Vorwoche - Aktuell) / Vorwoche) * 100`
- Positive Werte = Gewicht verloren (gut)
- Negative Werte = Gewicht zugenommen

### Gewinner und Verlierer

- **Wochengewinner**: Höchste prozentuale Abnahme
- **Wochenverlierer**: Niedrigste prozentuale Abnahme (oder Zunahme)
- Bei Gleichstand: Kein Gewinner, keine Topf-Einzahlung

### Topf-System

- Der Wochenverlierer zahlt den konfigurierten Betrag (Standard: 5 EUR) in den Topf
- Am Ende des Wettbewerbs zahlt der Teilnehmer mit den **meisten Niederlagen** den Restbetrag bis zur Gesamtsumme
- Beispiel: Gesamtsumme 100 EUR, im Topf sind 60 EUR → Verlierer zahlt 40 EUR

## Technologie

### Backend
- **Python 3.11+**
- **FastAPI** - Modernes Web-Framework
- **SQLite** - Einfache, dateibasierte Datenbank
- **Uvicorn** - ASGI Server

### Frontend
- **Vanilla JavaScript** - Keine Framework-Abhängigkeiten
- **HTML5 & CSS3** - Mobile-first Design
- **Chart.js** - Interaktive Diagramme

## Installation

### Voraussetzungen

- Python 3.11 oder höher (für lokale Entwicklung)
- Docker und Docker Compose (für Container-Deployment)

### Lokale Entwicklung

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd WeightBattle
   ```

2. **Virtuelle Umgebung erstellen**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # oder
   venv\Scripts\activate     # Windows
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Server starten**
   ```bash
   cd backend
   python app.py
   # oder mit Auto-Reload für Entwicklung:
   uvicorn app:app --reload
   ```

5. **App öffnen**

   Browser öffnen: `http://localhost:8000`

### Docker Deployment

1. **Image bauen und Container starten**
   ```bash
   docker-compose up -d --build
   ```

2. **Logs überprüfen**
   ```bash
   docker-compose logs -f
   ```

3. **App öffnen**

   Browser öffnen: `http://localhost:8000`

4. **Container stoppen**
   ```bash
   docker-compose down
   ```

5. **Container stoppen und Daten löschen**
   ```bash
   docker-compose down -v
   ```

### Testdaten laden (optional)

Für Entwicklungs- und Testzwecke können realistische Beispieldaten geladen werden:

```bash
cd backend
python seed_data.py
```

Dies erstellt 4 Teilnehmer mit 8 Wochen Wiegedaten.

## Verwendung

### Ersteinrichtung

Beim ersten Start der App erscheint der Setup-Bildschirm:

1. **Enddatum festlegen**: Wann endet der Wettbewerb?
2. **Einsatz pro Woche**: Wie viel zahlt der Wochenverlierer? (Standard: 5 EUR)
3. **Gesamtsumme**: Ziel für den Topf, z.B. für ein gemeinsames Essen (Standard: 100 EUR)
4. **Teilnehmer hinzufügen**: Name und Startgewicht für jeden Teilnehmer

### Dashboard

Die Hauptansicht zeigt:

- **Tage bis Battle-Ende**: Countdown zum Enddatum
- **Gesamtfortschritt**: Prozentuale Abnahme aller Teilnehmer seit Start
- **Aktuelle Führung**: Wer hat die meisten Wochensiege?
- **Topf**: Aktueller Stand und letzte Einzahlungen
- **Gewichtsverlauf**: Individueller Verlauf pro Teilnehmer in kg

### Wiegen

1. Teilnehmer auswählen
2. Aktuelles Gewicht eingeben
3. Live-Vorschau der prozentualen Änderung
4. Speichern

### Statistik

- **Rangliste**: Sortiert nach Anzahl der Siege
- **Abgenommen in %**: Chart mit dem Fortschritt aller Teilnehmer
- **Prognose bis Ende**: Geschätztes Endgewicht basierend auf bisherigem Trend
- **Topf-Details**: Wer hat wie viel eingezahlt, wer zahlt den Rest?
- **Änderungsverlauf**: Audit-Log aller Wiegungen

## API Dokumentation

Die API ist unter `http://localhost:8000/docs` (Swagger UI) oder `http://localhost:8000/redoc` dokumentiert.

### Wichtige Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/setup/status` | Setup-Status prüfen |
| POST | `/setup` | Ersteinrichtung abschließen |
| GET | `/users` | Alle Teilnehmer abrufen |
| POST | `/users` | Neuen Teilnehmer anlegen |
| GET | `/weeks/current` | Aktuelle Woche abrufen |
| POST | `/weigh-ins` | Wiegung speichern |
| GET | `/weigh-ins/preview` | Vorschau der prozentualen Änderung |
| GET | `/stats/overview` | Gesamtübersicht |
| GET | `/stats/leaderboard` | Rangliste |
| GET | `/stats/pot` | Topf-Informationen |
| GET | `/stats/prognosis` | Gewichtsprognosen |
| GET | `/stats/progress` | Fortschrittsdaten für Charts |
| GET | `/stats/user/{id}` | Detailstatistik eines Teilnehmers |
| GET | `/audit` | Änderungsverlauf |
| GET | `/config` | Konfiguration abrufen |
| PUT | `/config` | Konfiguration ändern |

## Projektstruktur

```
WeightBattle/
├── backend/
│   ├── app.py           # FastAPI Anwendung & Endpunkte
│   ├── models.py        # Datenbankschema & Verbindung
│   ├── crud.py          # Datenbankoperationen
│   ├── stats.py         # Statistiken & Prognosen
│   ├── audit.py         # Änderungsprotokollierung
│   ├── seed_data.py     # Testdaten-Generator
│   ├── requirements.txt # Python-Abhängigkeiten
│   └── db.sqlite        # SQLite-Datenbank (wird erstellt)
├── frontend/
│   ├── index.html       # Haupt-HTML (deutsche UI)
│   ├── styles.css       # Mobile-first Styling
│   └── app.js           # Frontend-Logik
├── Dockerfile           # Container-Definition
├── docker-compose.yml   # Container-Orchestrierung
├── .dockerignore        # Ausschlüsse für Docker-Build
└── README.md            # Diese Datei
```

## Konfiguration

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `DATABASE_PATH` | Pfad zur SQLite-Datenbank | `backend/db.sqlite` |

### App-Konfiguration (in der Datenbank)

Diese Werte werden beim Setup festgelegt und können über die API geändert werden:

| Schlüssel | Beschreibung | Standard |
|-----------|--------------|----------|
| `pot_contribution` | EUR pro Wochenniederlage | 5 |
| `total_amount` | Gesamtsumme für den Topf | 100 |
| `battle_end_date` | Enddatum (YYYY-MM-DD) | 2026-04-05 |

### Port ändern

**Lokal:**
```bash
uvicorn app:app --host 0.0.0.0 --port 3000
```

**Docker:** In `docker-compose.yml` die Ports anpassen:
```yaml
ports:
  - "3000:8000"
```

## Datensicherung

### Lokale Installation

Die Datenbank liegt unter `backend/db.sqlite`. Diese Datei sichern.

### Docker

Die Daten liegen im Docker Volume `weightbattle_data`. Backup erstellen:

```bash
# Volume-Inhalt in lokalen Ordner kopieren
docker run --rm -v weightbattle_data:/data -v $(pwd):/backup alpine cp /data/db.sqlite /backup/

# Backup wiederherstellen
docker run --rm -v weightbattle_data:/data -v $(pwd):/backup alpine cp /backup/db.sqlite /data/
```

## Lizenz

Dieses Projekt ist für den privaten Gebrauch gedacht.

---

**Viel Erfolg beim Abnehmen!**
