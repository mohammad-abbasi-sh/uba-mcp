# uba-mcp 🌬️

mcp-name: io.github.mohammad-abbasi-sh/uba-mcp

Unofficial **read-only** MCP server for **[UBA air quality](https://www.umweltbundesamt.de/en/data/air/air-data)** — the Umweltbundesamt (German Federal Environment Agency) Air Data API v4: hourly measurements from ~400 German stations (PM10, PM2.5, NO2, O3, SO2, CO, benzene …) since 2016, with the official UBA air-quality index (LQI). No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory". Not affiliated with the Umweltbundesamt.

## For AI agents

Add to your MCP client config (stdio):

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

Or run locally: `python -m uba_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `uba_list_stations` | Measuring stations, filterable by city, state, type, area or name |
| `uba_station_detail` | One station: address, coordinates, type, data window, recent pollutants |
| `uba_current_air_quality` | Latest hourly values + LQI at a station (code, id or city name) |
| `uba_measurements` | Hourly values over a date range (max 31 days) + min/max/mean & daily means |
| `uba_list_components` | All 12 pollutants: code, symbol, unit, name |
| `uba_list_networks` | The 17 measuring networks (16 Länder + UBA) |
| `uba_health` | Reachability check (ok / blocked / error) — one polite request |

Example output (`uba_current_air_quality` / Berlin Neukölln, 2026-11-11 09:00 CET):

```json
{"station": {"code": "DEBE034", "name": "Berlin Neukölln", "city": "Berlin"},
 "hour": {"start": "2026-11-11 09:00:00", "total_index": 2, "total_label": "moderate",
  "values": [{"code": "PM2", "value": 17.0, "unit": "µg/m³", "label": "moderate"},
             {"code": "PM10", "value": 23.0, "unit": "µg/m³", "label": "good"},
             {"code": "O3", "value": 24.0, "unit": "µg/m³", "label": "very good"},
             {"code": "NO2", "value": 15.0, "unit": "µg/m³", "label": "good"}]}}
```

Notes:
- Stations are found by code (`DEBE010` = Berlin Wedding), numeric id, or city name (first active station in that city).
- The `index` / `total_index` (0–4) and labels come from the API itself; they follow the UBA LQI, 2025 revision (hourly means, µg/m³):

| Class | NO2 | PM10 | PM2.5 | O3 | SO2 |
|-------|-----|------|-------|----|-----|
| 0 very good | 0–10 | 0–9 | 0–5 | 0–24 | 0–10 |
| 1 good | 11–30 | 10–27 | 6–15 | 25–72 | 11–30 |
| 2 moderate | 31–60 | 28–54 | 16–30 | 73–144 | 31–60 |
| 3 poor | 61–100 | 55–90 | 31–50 | 145–240 | 61–100 |
| 4 very poor | >100 | >90 | >50 | >240 | >100 |

- All times are CET/CEST as returned by the API. Data: UBA Air Data API v4 `umweltbundesamt.de/api/air_data/v4` — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses real captured API fixtures
- `tests/test_live.py` — 7 cautious live requests against the UBA API

## License

MIT

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
