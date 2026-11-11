# uba-mcp 🌬️

mcp-name: io.github.mohammad-abbasi-sh/uba-mcp

Inoffizieller **nur lesender** MCP-Server für **[UBA-Luftqualität](https://www.umweltbundesamt.de/en/data/air/air-data)** — die Air-Data-API v4 des Umweltbundesamtes: stündliche Messwerte von rund 400 deutschen Messstationen (PM10, PM2,5, NO2, O3, SO2, CO, Benzol …) seit 2016, mit dem amtlichen Luftqualitätsindex (LQI) des UBA. Kein Schlüssel, keine Anmeldung.

> Gebaut von Mohammad Abbasi als Teil der "Germany MCP factory". Nicht mit dem Umweltbundesamt verbunden.

## Für KI-Agenten

Zur MCP-Client-Konfiguration hinzufügen (stdio):

```json
{
  "mcpServers": {
    "uba": {
      "command": "uvx",
      "args": ["uba-mcp==0.1.0"]
    }
  }
}
```

Oder lokal starten: `python -m uba_mcp.server` (benötigt `mcp<2`, `httpx`).

## Tools

| Tool | Beschreibung |
|------|-------------|
| `uba_list_stations` | Messstationen, filterbar nach Stadt, Bundesland, Typ, Gebiet oder Name |
| `uba_station_detail` | Eine Station: Adresse, Koordinaten, Typ, Datenzeitraum, aktuelle Schadstoffe |
| `uba_current_air_quality` | Aktuelle Stundenwerte + LQI an einer Station (Code, ID oder Stadtname) |
| `uba_measurements` | Stundenwerte über einen Zeitraum (max. 31 Tage) + Min/Max/Mittel & Tagesmittel |
| `uba_list_components` | Alle 12 Schadstoffe: Code, Symbol, Einheit, Name |
| `uba_list_networks` | Die 17 Messnetze (16 Bundesländer + UBA) |
| `uba_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Hinweise:
- Stationen werden über Code (`DEBE010` = Berlin Wedding), numerische ID oder Stadtname gefunden (erste aktive Station der Stadt).
- `index` / `total_index` (0–4) und Labels kommen direkt aus der API; sie folgen dem UBA-LQI, Revision 2025 (Stundenmittelwerte, µg/m³): sehr gut / gut / mäßig / schlecht / sehr schlecht.
- Alle Zeiten sind MEZ/MESZ, wie von der API geliefert. Daten: UBA Air Data API v4 — kein Schlüssel, keine Anmeldung, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

## Lizenz

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
