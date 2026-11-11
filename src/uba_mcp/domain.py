"""Domain logic: shape UBA (Umweltbundesamt) Air Data API responses into
compact dicts (stdlib only).

Data source: the official UBA Air Data API v4
(umweltbundesamt.de/api/air_data/v4) — free, no key, no login.
- stations/json?use=airquality — ~493 measuring stations (429 active),
  one row per station, dict keyed by station id.
- components/json — 12 pollutants (PM10, PM2.5, NO2, O3, SO2, CO ...).
- airquality/json — hourly values per station over a date range.
  Row: [end (CET), total_index, data_incomplete, [component_id, value,
  index, y_value], ...]. The per-component `index` (0-4) and the row
  `total_index` are the UBA air-quality index (LQI) class for that hour:
  0 very good, 1 good, 2 moderate, 3 poor, 4 very poor — verified
  against the 2025 revised LQI bands (umid 2/2025; the API's own index
  values match the new bands, e.g. PM2.5 17 -> index 2 = moderate).
- meta/json — reference data: components, scopes, per-station data
  availability windows (limits), stations, networks (17: the 16
  Bundesländer + UBA's own network).

All times are CET/CEST as returned by the API; the server never invents
times — it reports the hour keys the API returns.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

BASE = "https://www.umweltbundesamt.de/api/air_data/v4"

# UBA air-quality index (LQI) classes, 2025 revision (hourly means, µg/m³).
# The API returns the class per component (`index` 0-4); this table is the
# documented band set behind it (umid 2/2025) and the fallback when the
# API omits an index. Upper bounds are inclusive: 0-10, 11-30, ...
LQI_LABELS_EN = ["very good", "good", "moderate", "poor", "very poor"]
LQI_LABELS_DE = ["sehr gut", "gut", "mäßig", "schlecht", "sehr schlecht"]
LQI_BANDS = {
    # component code -> [(upper bound, class), ...]; above last bound = 4
    "NO2": [(10, 0), (30, 1), (60, 2), (100, 3)],
    "PM10": [(9, 0), (27, 1), (54, 2), (90, 3)],
    "PM2": [(5, 0), (15, 1), (30, 2), (50, 3)],
    "O3": [(24, 0), (72, 1), (144, 2), (240, 3)],
    "SO2": [(10, 0), (30, 1), (60, 2), (100, 3)],
}

DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
MAX_DAYS = 31


def lqi_label(index) -> str | None:
    """English label for a UBA LQI class 0-4; None when unknown."""
    try:
        i = int(index)
    except (TypeError, ValueError):
        return None
    if 0 <= i <= 4:
        return LQI_LABELS_EN[i]
    return None


def lqi_class_for_value(code: str, value) -> int | None:
    """LQI class (0-4) for a pollutant value, 2025 bands.

    Fallback only — the API's own `index` field is authoritative and
    is used whenever present. Returns None for unknown components."""
    bands = LQI_BANDS.get((code or "").upper())
    if bands is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    for bound, cls in bands:
        if v <= bound:
            return cls
    return 4


def stations_url() -> str:
    return f"{BASE}/stations/json?use=airquality&lang=en"


def components_url() -> str:
    return f"{BASE}/components/json?lang=en"


def meta_url(station_id: str, date_from: str, date_to: str) -> str:
    return (
        f"{BASE}/meta/json?use=airquality&station={station_id}"
        f"&date_from={date_from}&date_to={date_to}"
    )


def airquality_url(station: str, date_from: str, time_from: str,
                   date_to: str, time_to: str) -> str:
    from urllib.parse import quote_plus
    return (
        f"{BASE}/airquality/json?date_from={date_from}&time_from={time_from}"
        f"&date_to={date_to}&time_to={time_to}"
        f"&station={quote_plus(station)}&lang=en"
    )


def validate_dates(date_from: str, date_to: str, max_days: int = MAX_DAYS):
    """Parse YYYY-MM-DD dates; returns (date_from, date_to) or raises."""
    m1 = DATE_RE.fullmatch((date_from or "").strip())
    m2 = DATE_RE.fullmatch((date_to or "").strip())
    if not m1 or not m2:
        raise ValueError(
            f"bad date format (expected YYYY-MM-DD): {date_from!r} / {date_to!r}"
        )
    d1 = date(int(m1.group(1)), int(m1.group(2)), int(m1.group(3)))
    d2 = date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    if d2 < d1:
        raise ValueError(f"date_to {date_to!r} is before date_from {date_from!r}")
    if (d2 - d1).days + 1 > max_days:
        raise ValueError(
            f"date range too long: {(d2 - d1).days + 1} days (max {max_days})"
        )
    return d1, d2


def recent_range(days: int = 2) -> tuple[str, str]:
    """(date_from, date_to) covering today + the previous days-1 days."""
    today = date.today()
    return ((today - timedelta(days=days - 1)).isoformat(), today.isoformat())


def _rows(payload: dict) -> tuple[list, dict]:
    """UBA list responses: {'indices': [...], 'data': {id: [...]}}.

    Returns (index-name -> position map, data dict)."""
    indices = payload.get("indices") or []
    pos = {name: i for i, name in enumerate(indices)}
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("unexpected UBA response shape: data is not an object")
    return pos, data


def parse_stations(text: str) -> list:
    """Stations list -> one dict per station, keyed by readable fields."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid stations response: {e}") from e
    pos, data = _rows(payload)
    need = ["station id", "station code", "station name", "station city"]
    for n in need:
        if n not in pos:
            raise ValueError(f"unexpected stations shape: no {n!r} column")
    out = []
    for row in data.values():
        def get(name):
            i = pos.get(name)
            return row[i] if i is not None and i < len(row) else None
        out.append({
            "id": str(get("station id")),
            "code": get("station code") or "",
            "name": get("station name") or "",
            "city": get("station city") or "",
            "synonym": get("station synonym") or "",
            "active_from": get("station active from"),
            "active_to": get("station active to"),
            "longitude": _f(get("station longitude")),
            "latitude": _f(get("station latitude")),
            "network_code": get("network code") or "",
            "network": get("network name") or "",
            "setting": get("station setting name") or "",
            "setting_short": get("station setting short name") or "",
            "type": get("station type name") or "",
            "address": get("station address") or "",
            "postcode": get("station postcode") or "",
            "active": get("station active to") is None,
        })
    out.sort(key=lambda s: (s["city"].casefold(), s["name"].casefold()))
    return out


def _f(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def filter_stations(stations: list, city: str | None = None,
                    state: str | None = None,
                    station_type: str | None = None,
                    area: str | None = None, query: str | None = None,
                    active_only: bool = True) -> list:
    """Filter stations. state: network code (BE, BY, ...) or name
    (Berlin, Bayern, ...). station_type: background / traffic / industry.
    area: urban / suburban / rural. query: substring of name/city/code."""
    city_k = (city or "").strip().casefold()
    state_k = (state or "").strip().casefold()
    type_k = (station_type or "").strip().casefold()
    area_k = (area or "").strip().casefold()
    q = (query or "").strip().casefold()
    out = []
    for s in stations:
        if active_only and not s["active"]:
            continue
        if city_k and city_k != s["city"].casefold():
            continue
        if state_k and state_k not in (s["network_code"].casefold(),
                                       s["network"].casefold()):
            continue
        if type_k and type_k != s["type"].casefold():
            continue
        if area_k and area_k != s["setting_short"].casefold():
            continue
        if q and q not in f"{s['name']} {s['city']} {s['code']}".casefold():
            continue
        out.append(s)
    return out


def resolve_station(stations: list, ref: str) -> dict:
    """Resolve a station reference: code (DEBE010), numeric id, or a city
    name (first active station in that city). Raises when not found."""
    ref = (ref or "").strip()
    if not ref:
        raise ValueError("station must not be empty")
    for s in stations:
        if s["code"].casefold() == ref.casefold() or s["id"] == ref:
            return s
    city_hits = [s for s in stations
                 if s["city"].casefold() == ref.casefold() and s["active"]]
    if city_hits:
        return city_hits[0]
    name_hits = [s for s in stations
                 if ref.casefold() in s["name"].casefold() and s["active"]]
    if name_hits:
        return name_hits[0]
    raise ValueError(
        f"no station found for {ref!r} (try a station code like DEBE010 "
        "or a German city name)"
    )


def parse_components(text: str) -> list:
    """Components list -> [{id, code, symbol, unit, name}].

    The components endpoint returns rows as top-level digit keys
    ({"1": [...], "2": [...], ...}), not under a "data" key."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid components response: {e}") from e
    indices = payload.get("indices") or []
    pos = {name: i for i, name in enumerate(indices)}
    rows = payload.get("data")
    if not isinstance(rows, dict):
        rows = {k: v for k, v in payload.items() if k.isdigit()}
    out = []
    for row in rows.values():
        def get(name):
            i = pos.get(name)
            return row[i] if i is not None and i < len(row) else None
        out.append({
            "id": str(get("component id")),
            "code": get("component code") or "",
            "symbol": get("component symbol") or "",
            "unit": get("component unit") or "",
            "name": get("component name") or "",
        })
    out.sort(key=lambda c: int(c["id"]) if c["id"].isdigit() else 99)
    return out


def parse_airquality(text: str, components: list | None = None) -> dict:
    """Air-quality response -> {"station_id", "hours": [...]}.

    Each hour: {start, end, total_index, total_label, incomplete,
    values: [{component_id, code, symbol, unit, value, index, label}]}.
    `components` (from parse_components) enriches values with code/unit;
    without it, code/unit are None and only the id is reported."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid air-quality response: {e}") from e
    data = payload.get("data") or {}
    if not isinstance(data, dict) or not data:
        raise ValueError("no air-quality data in response (unknown station?)")
    station_id, series = next(iter(data.items()))
    by_id = {c["id"]: c for c in (components or [])}
    hours = []
    for start in sorted(series.keys()):
        row = series[start]
        if not isinstance(row, list) or len(row) < 3:
            continue
        end, total_index, incomplete = row[0], row[1], row[2]
        values = []
        for item in row[3:]:
            if not isinstance(item, list) or len(item) < 2:
                continue
            comp_id, value, index = str(item[0]), item[1], item[2] if len(item) > 2 else None
            comp = by_id.get(comp_id, {})
            code = comp.get("code")
            if index is None and code:
                index = lqi_class_for_value(code, value)
            values.append({
                "component_id": comp_id,
                "code": code,
                "symbol": comp.get("symbol"),
                "unit": comp.get("unit"),
                "name": comp.get("name"),
                "value": _f(value),
                "index": index,
                "label": lqi_label(index),
            })
        hours.append({
            "start": start,
            "end": end,
            "total_index": total_index,
            "total_label": lqi_label(total_index),
            "incomplete": bool(incomplete),
            "values": values,
        })
    return {"station_id": str(station_id), "hours": hours}


def parse_meta(text: str) -> dict:
    """Meta response -> reference data: components, scopes, networks,
    per-station availability windows (limits) and stations."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid meta response: {e}") from e
    components = []
    for row in (payload.get("components") or {}).values():
        components.append({
            "id": str(row[0]), "code": row[1], "symbol": row[2],
            "unit": row[3], "name": row[4],
        })
    scopes = []
    for row in (payload.get("scopes") or {}).values():
        scopes.append({
            "id": str(row[0]), "code": row[1], "period": row[2],
            "seconds": row[3], "max": bool(row[4]), "label": row[5],
        })
    networks = []
    for row in (payload.get("networks") or {}).values():
        networks.append({"id": str(row[0]), "code": row[1], "name": row[2]})
    limits = {}
    for sid, row in (payload.get("limits") or {}).items():
        # Rows are [id, from, to] — except the id-"0" row, which is
        # [from, to] (the id is the key). Handle both shapes.
        if len(row) >= 3:
            limits[str(sid)] = {"from": row[1], "to": row[2]}
        elif len(row) == 2:
            limits[str(sid)] = {"from": row[0], "to": row[1]}
    return {
        "components": components,
        "scopes": scopes,
        "networks": networks,
        "limits": limits,
        "station_count": len(payload.get("stations") or {}),
    }


def summarize_hours(hours: list, component: str | None = None) -> dict:
    """Per-component min/max/mean over hourly rows, plus daily means.

    component: code like PM10 — when given, only that pollutant is
    summarised. Returns {"components": {...}, "daily": [...]}."""
    code_k = (component or "").strip().upper()
    per: dict[str, dict] = {}
    daily: dict[str, dict[str, list]] = {}
    for h in hours:
        day = (h["start"] or "")[:10]
        for v in h["values"]:
            code = (v.get("code") or "").upper()
            if not code or v.get("value") is None:
                continue
            if code_k and code != code_k:
                continue
            slot = per.setdefault(code, {
                "code": code, "symbol": v.get("symbol"),
                "unit": v.get("unit"), "name": v.get("name"),
                "count": 0, "min": None, "max": None, "sum": 0.0,
            })
            val = v["value"]
            slot["count"] += 1
            slot["sum"] += val
            slot["min"] = val if slot["min"] is None else min(slot["min"], val)
            slot["max"] = val if slot["max"] is None else max(slot["max"], val)
            daily.setdefault(day, {}).setdefault(code, []).append(val)
    comps = []
    for code, s in sorted(per.items()):
        comps.append({
            "code": code, "symbol": s["symbol"], "unit": s["unit"],
            "name": s["name"], "count": s["count"],
            "min": s["min"], "max": s["max"],
            "mean": round(s["sum"] / s["count"], 3) if s["count"] else None,
        })
    days = []
    for day in sorted(daily):
        row = {"date": day}
        for code, vals in sorted(daily[day].items()):
            row[code] = round(sum(vals) / len(vals), 3)
        days.append(row)
    return {"components": comps, "daily": days}
