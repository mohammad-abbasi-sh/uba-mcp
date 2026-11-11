"""MCP server: unofficial read-only access to UBA air quality — the
Umweltbundesamt (German Federal Environment Agency) Air Data API v4:
hourly measurements from ~400 German stations (PM10, PM2.5, NO2, O3,
SO2, CO ...) since 2016, plus the official UBA air-quality index (LQI).
No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for UBA air quality — the \
Umweltbundesamt (German Federal Environment Agency) Air Data API v4. \
Hourly measurements from ~400 German measuring stations (PM10, PM2.5, \
NO2, O3, SO2, CO, benzene ...) since 2016, with the official UBA \
air-quality index (LQI, 2025 revision: very good / good / moderate / \
poor / very poor) per pollutant and per hour. Stations are found by \
code (e.g. DEBE010 = Berlin Wedding), numeric id, or city name. All \
times are CET/CEST as returned by the API. Built by Mohammad Abbasi \
(mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — \
Germany MCP factory.\
"""

_SOURCE = "UBA Air Data API v4 (umweltbundesamt.de)"
_DISCLAIMER = "Unofficial read-only data from the Umweltbundesamt; verify on the UBA air-data portal before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("uba-mcp", instructions=INSTRUCTIONS)


def _stations() -> list:
    return _dom.parse_stations(_http.fetch_text(_dom.stations_url()))


def _components() -> list:
    return _dom.parse_components(_http.fetch_text(_dom.components_url()))


def _airquality(station_code: str, date_from: str, date_to: str,
                time_from: str = "00", time_to: str = "23") -> dict:
    comps = _components()
    text = _http.fetch_text(_dom.airquality_url(
        station_code, date_from, time_from, date_to, time_to))
    return _dom.parse_airquality(text, comps)


@mcp.tool()
def uba_list_stations(city: str | None = None, state: str | None = None,
                      station_type: str | None = None,
                      area: str | None = None, query: str | None = None,
                      active_only: bool = True, limit: int = 20) -> str:
    """List German air-quality measuring stations, filterable by city,
    state (network code like BE or name like Berlin), type (background /
    traffic / industry), area (urban / suburban / rural) or a name/code
    substring. limit: 1..100 (default 20)."""
    try:
        if not 1 <= limit <= 100:
            raise ValueError(f"limit out of range: {limit} (expected 1..100)")
        stations = _stations()
        found = _dom.filter_stations(stations, city, state, station_type,
                                     area, query, active_only)
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"total_results": len(found), "limit": limit,
                "count": len(found[:limit]), "stations": found[:limit]})


@mcp.tool()
def uba_station_detail(station: str) -> str:
    """Full detail of one measuring station: code, name, city, address,
    coordinates, type, area, network, active period, data availability
    window, and which pollutants have recent data.
    station: code (DEBE010), numeric id, or city name."""
    try:
        stations = _stations()
        st = _dom.resolve_station(stations, station)
        date_from, date_to = _dom.recent_range(30)
        meta = _dom.parse_meta(_http.fetch_text(
            _dom.meta_url(st["id"], date_from, date_to)))
        availability = meta["limits"].get(st["id"])
        recent = []
        try:
            d_from, d_to = _dom.recent_range(2)
            aq = _airquality(st["code"], d_from, d_to)
            if aq["hours"]:
                seen = {}
                for v in aq["hours"][-1]["values"]:
                    seen[v["code"]] = v
                recent = [seen[k] for k in sorted(seen)]
        except (_http.UbaMcpError, ValueError):
            recent = []
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"station": st, "data_availability": availability,
                "pollutants_with_recent_data": recent})


@mcp.tool()
def uba_current_air_quality(station: str) -> str:
    """Latest hourly air quality at a station: each pollutant's value
    (µg/m³) with the UBA air-quality index class (very good / good /
    moderate / poor / very poor) and the overall index for that hour.
    station: code (DEBE010), numeric id, or city name."""
    try:
        stations = _stations()
        st = _dom.resolve_station(stations, station)
        date_from, date_to = _dom.recent_range(2)
        aq = _airquality(st["code"], date_from, date_to)
        if not aq["hours"]:
            raise ValueError(
                f"no recent measurements for station {st['code']!r} "
                "(it may have stopped measuring)")
        latest = aq["hours"][-1]
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"station": {"code": st["code"], "name": st["name"],
                            "city": st["city"], "type": st["type"],
                            "area": st["setting_short"]},
                "hour": latest})


@mcp.tool()
def uba_measurements(station: str, date_from: str, date_to: str,
                     component: str | None = None) -> str:
    """Hourly air-quality values for a station over a date range
    (max 31 days), with per-pollutant min/max/mean and daily means.
    component: one pollutant code (PM10, PM2, NO2, O3, SO2, CO ...) to
    limit the series to it; empty = all pollutants the station measures.
    station: code (DEBE010), numeric id, or city name."""
    try:
        _dom.validate_dates(date_from, date_to)
        stations = _stations()
        st = _dom.resolve_station(stations, station)
        aq = _airquality(st["code"], date_from, date_to)
        summary = _dom.summarize_hours(aq["hours"], component)
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"station": {"code": st["code"], "name": st["name"],
                            "city": st["city"]},
                "date_from": date_from, "date_to": date_to,
                "component": component,
                "hours_count": len(aq["hours"]),
                "summary": summary,
                "hours": aq["hours"]})


@mcp.tool()
def uba_list_components() -> str:
    """All pollutants UBA publishes air-quality data for: code, symbol,
    unit and name (PM10, PM2.5, NO2, O3, SO2, CO, benzene, lead ...)."""
    try:
        comps = _components()
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"count": len(comps), "components": comps})


@mcp.tool()
def uba_list_networks() -> str:
    """The measuring networks behind the stations: one per Bundesland
    (16) plus the UBA's own network."""
    try:
        stations = _stations()
        first = next((s for s in stations if s["active"]), None)
        if first is None:
            raise ValueError("no active station found")
        date_from, date_to = _dom.recent_range(30)
        meta = _dom.parse_meta(_http.fetch_text(
            _dom.meta_url(first["id"], date_from, date_to)))
    except (_http.UbaMcpError, ValueError) as e:
        return _err(e)
    return _ok({"count": len(meta["networks"]),
                "networks": meta["networks"]})


@mcp.tool()
def uba_health() -> str:
    """Check whether the UBA Air Data API is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
