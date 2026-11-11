"""Live tests — hit the real UBA Air Data API v4. Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set UBA_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from uba_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("UBA_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="UBA_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_list_stations_live(self):
        out = json.loads(srv.uba_list_stations(city="Berlin"))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["total_results"], 10)
        self.assertTrue(all(s["city"] == "Berlin" for s in out["stations"]))
        print(f"\nLIVE stations Berlin: {out['total_results']} total")

    def test_station_detail_live(self):
        out = json.loads(srv.uba_station_detail("DEBE010"))
        self.assertNotIn("error", out)
        self.assertEqual(out["station"]["name"], "Berlin Wedding")
        self.assertIn("data_availability", out)
        codes = [v["code"] for v in out["pollutants_with_recent_data"]]
        self.assertIn("PM10", codes)
        print(f"\nLIVE DEBE010: {out['station']['name']}, recent: {codes}")

    def test_current_live(self):
        out = json.loads(srv.uba_current_air_quality("DEBE034"))
        self.assertNotIn("error", out)
        self.assertEqual(out["station"]["code"], "DEBE034")
        self.assertIn(out["hour"]["total_label"],
                      ["very good", "good", "moderate", "poor", "very poor"])
        vals = {v["code"]: v["value"] for v in out["hour"]["values"]}
        self.assertIn("PM10", vals)
        print(f"\nLIVE current Neukölln {out['hour']['start']}: "
              f"LQI {out['hour']['total_label']}, PM10={vals['PM10']}")

    def test_measurements_live(self):
        out = json.loads(srv.uba_measurements(
            "DEBE010", "2026-11-10", "2026-11-11", component="PM10"))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["hours_count"], 20)
        pm10 = next(c for c in out["summary"]["components"]
                    if c["code"] == "PM10")
        self.assertGreater(pm10["count"], 0)
        print(f"\nLIVE measurements DEBE010 PM10: {out['hours_count']} hours, "
              f"mean {pm10['mean']} µg/m³")

    def test_components_live(self):
        out = json.loads(srv.uba_list_components())
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 12)
        print(f"\nLIVE components: {out['count']}")

    def test_networks_live(self):
        out = json.loads(srv.uba_list_networks())
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 17)
        print(f"\nLIVE networks: {out['count']}")

    def test_health_live(self):
        out = json.loads(srv.uba_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
