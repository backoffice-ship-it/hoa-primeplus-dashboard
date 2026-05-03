# HOA Prime+ Dashboard

Dagelijks automatisch bijgewerkte Nordpool België dag-ahead prijzen.

## Hoe het werkt

```
GitHub Actions (gratis)
  → scraper.py draait dagelijks
    → haalt Nordpool BE prijzen op
      → slaat op als data/today.csv + data/tomorrow.csv
        → index.html leest de CSV en toont de grafiek
```

**Geen server. Geen kosten. Volledig automatisch.**

---

## Opzetten in 5 stappen

### Stap 1 — GitHub account aanmaken
Ga naar [github.com](https://github.com) en maak een gratis account aan.

### Stap 2 — Nieuwe repository aanmaken
1. Klik op **"New repository"**
2. Naam: `prime-dashboard` (of eigen keuze)
3. Zet op **Public** (zodat GitHub Pages gratis werkt)
4. Klik **"Create repository"**

### Stap 3 — Bestanden uploaden
Upload deze bestanden naar uw repository:
```
scraper.py
index.html
data/today.csv          (leeg bestand, wordt overschreven)
data/tomorrow.csv       (leeg bestand, wordt overschreven)
.github/workflows/fetch-prices.yml
```

### Stap 4 — GitHub Pages aanzetten
1. Ga naar uw repository → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / root
4. Klik **Save**

Uw dashboard is nu bereikbaar op:
`https://[uw-username].github.io/prime-dashboard/`

### Stap 5 — index.html aanpassen
Open `index.html` en vervang bovenaan:
```javascript
const GITHUB_USER = "HOA-Energy";      // ← uw GitHub username
const GITHUB_REPO = "prime-dashboard"; // ← uw repo naam
```

### Stap 6 — Eerste run handmatig starten
1. Ga naar **Actions** tab in uw repository
2. Klik op **"HOA Prime+ Nordpool Data"**
3. Klik op **"Run workflow"** → **"Run workflow"**

Na ~1 minuut zijn de CSV bestanden gevuld en werkt het dashboard.

---

## Planning

| Tijd | Wat |
|------|-----|
| 02:15 CET | Vandaag-data ophalen |
| 13:30 CET | Day-ahead morgen ophalen (na Nordpool publicatie) |

---

## Bestanden

| Bestand | Omschrijving |
|---------|-------------|
| `scraper.py` | Python script dat Nordpool aanroept |
| `index.html` | Dashboard website |
| `data/today.csv` | Huidige dag-prijzen (auto-update) |
| `data/tomorrow.csv` | Morgen-prijzen (auto-update na 13u) |
| `.github/workflows/fetch-prices.yml` | Automatisch schema |

---

## CSV formaat

```csv
datum,tijd,uur,kwartier,eur_mwh,eur_kwh,label,timestamp
2026-05-03,00:00,0,0,68.50,0.068500,today,2026-05-03T00:00:00+02:00
2026-05-03,00:15,0,15,65.20,0.065200,today,2026-05-03T00:15:00+02:00
...
```
