"""Offline tests — parse real captured UBA Air Data API v4 responses, no network."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from uba_mcp import domain as dom

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name):
    return (FIX / name).read_text(encoding="utf-8")


class TestStationsFixture(unittest.TestCase):
    def setUp(self):
        self.stations = dom.parse_stations(_read("stations.json"))

    def test_station_count(self):
        self.assertEqual(len(self.stations), 11)

    def test_berlin_wedding(self):
        st = dom.resolve_station(self.stations, "DEBE010")
        self.assertEqual(st["name"], "Berlin Wedding")
        self.assertEqual(st["city"], "Berlin")
        self.assertEqual(st["id"], "121")
        self.assertTrue(st["active"])
        self.assertAlmostEqual(st["latitude"], 52.543, places=2)
        self.assertAlmostEqual(st["longitude"], 13.3493, places=2)
        self.assertEqual(st["network_code"], "BE")
        self.assertEqual(st["type"], "background")
        self.assertEqual(st["setting_short"], "urban")

    def test_filter_city(self):
        berlin = dom.filter_stations(self.stations, city="Berlin")
        self.assertEqual(len(berlin), 8)
        self.assertTrue(all(s["city"] == "Berlin" for s in berlin))

    def test_filter_state_and_type(self):
        self.assertEqual(len(dom.filter_stations(self.stations, state="BE")), 8)
        self.assertEqual(len(dom.filter_stations(self.stations, state="Berlin")), 8)
        self.assertEqual(len(dom.filter_stations(self.stations, station_type="traffic")), 1)
        self.assertEqual(len(dom.filter_stations(self.stations, area="rural")), 4)
        self.assertEqual(len(dom.filter_stations(self.stations, area="urban")), 4)

    def test_filter_query(self):
        hits = dom.filter_stations(self.stations, query="wedding")
        self.assertEqual([s["code"] for s in hits], ["DEBE010"])

    def test_resolve_by_city(self):
        st = dom.resolve_station(self.stations, "Berlin")
        self.assertEqual(st["city"], "Berlin")
        self.assertTrue(st["active"])

    def test_resolve_unknown(self):
        with self.assertRaises(ValueError):
            dom.resolve_station(self.stations, "DEZZ999")

    def test_inactive_station_present(self):
        elster = dom.resolve_station(self.stations, "DEBB007")
        self.assertFalse(elster["active"])
        self.assertIsNotNone(elster["active_to"])
        active = dom.filter_stations(self.stations, active_only=True)
        self.assertTrue(all(s["active"] for s in active))
        self.assertNotIn("DEBB007", [s["code"] for s in active])


class TestComponentsFixture(unittest.TestCase):
    def test_components(self):
        comps = dom.parse_components(_read("components.json"))
        self.assertEqual(len(comps), 12)
        codes = [c["code"] for c in comps]
        self.assertIn("PM10", codes)
        self.assertIn("PM2", codes)
        self.assertIn("NO2", codes)
        self.assertIn("O3", codes)
        pm10 = next(c for c in comps if c["code"] == "PM10")
        self.assertEqual(pm10["unit"], "µg/m³")
        self.assertEqual(pm10["symbol"], "PM₁₀")
        pm25 = next(c for c in comps if c["code"] == "PM2")
        self.assertEqual(pm25["symbol"], "PM₂,₅")


class TestAirqualityFixture(unittest.TestCase):
    def setUp(self):
        comps = dom.parse_components(_read("components.json"))
        self.aq = dom.parse_airquality(_read("airquality-debe010.json"), comps)

    def test_hours(self):
        self.assertEqual(self.aq["station_id"], "121")
        self.assertEqual(len(self.aq["hours"]), 24)
        self.assertEqual(self.aq["hours"][0]["start"], "2026-11-10 10:00:00")
        self.assertEqual(self.aq["hours"][-1]["start"], "2026-11-11 09:00:00")

    def test_first_hour_values_and_lqi(self):
        h = self.aq["hours"][0]
        self.assertEqual(h["total_index"], 2)
        self.assertEqual(h["total_label"], "moderate")
        by_code = {v["code"]: v for v in h["values"]}
        self.assertEqual(by_code["PM2"]["value"], 17.0)
        self.assertEqual(by_code["PM2"]["label"], "moderate")
        self.assertEqual(by_code["PM10"]["value"], 20.0)
        self.assertEqual(by_code["PM10"]["label"], "good")
        self.assertEqual(by_code["O3"]["value"], 19.0)
        self.assertEqual(by_code["O3"]["label"], "very good")
        self.assertEqual(by_code["NO2"]["value"], 15.0)
        self.assertEqual(by_code["NO2"]["label"], "good")
        self.assertEqual(by_code["PM10"]["unit"], "µg/m³")

    def test_last_hour_no2_peak(self):
        h = self.aq["hours"][-1]
        by_code = {v["code"]: v for v in h["values"]}
        self.assertEqual(by_code["NO2"]["value"], 31.0)

    def test_summary(self):
        s = dom.summarize_hours(self.aq["hours"])
        pm10 = next(c for c in s["components"] if c["code"] == "PM10")
        self.assertEqual(pm10["count"], 24)
        self.assertEqual(pm10["min"], 17.0)
        self.assertEqual(pm10["max"], 25.0)
        self.assertAlmostEqual(pm10["mean"], 21.625, places=2)
        self.assertEqual([d["date"] for d in s["daily"]],
                         ["2026-11-10", "2026-11-11"])

    def test_summary_component_filter(self):
        s = dom.summarize_hours(self.aq["hours"], "PM10")
        self.assertEqual([c["code"] for c in s["components"]], ["PM10"])
        self.assertTrue(all(set(d) == {"date", "PM10"} for d in s["daily"]))


class TestMetaFixture(unittest.TestCase):
    def test_meta(self):
        m = dom.parse_meta(_read("meta.json"))
        self.assertEqual(len(m["components"]), 12)
        self.assertEqual(len(m["networks"]), 17)
        self.assertEqual(len(m["scopes"]), 6)
        be = next(n for n in m["networks"] if n["code"] == "BE")
        self.assertEqual(be["name"], "Berlin")
        self.assertEqual(m["limits"]["21"]["from"], "2016-01-01 00:00:00")
        self.assertEqual(m["limits"]["21"]["to"], "2026-11-11 09:00:00")
        self.assertEqual(m["limits"]["7"]["to"], "2021-01-18 12:00:00")


class TestLqiBands(unittest.TestCase):
    def test_new_2025_bands(self):
        # Verified against the UBA revised LQI (umid 2/2025).
        self.assertEqual(dom.lqi_class_for_value("PM10", 20), 1)   # 10-27 good
        self.assertEqual(dom.lqi_class_for_value("PM10", 9), 0)
        self.assertEqual(dom.lqi_class_for_value("PM10", 91), 4)
        self.assertEqual(dom.lqi_class_for_value("NO2", 31), 2)    # 31-60 moderate
        self.assertEqual(dom.lqi_class_for_value("O3", 19), 0)
        self.assertEqual(dom.lqi_class_for_value("PM2", 17), 2)
        self.assertEqual(dom.lqi_class_for_value("SO2", 150), 4)
        self.assertIsNone(dom.lqi_class_for_value("CO", 5))

    def test_labels(self):
        self.assertEqual(dom.lqi_label(0), "very good")
        self.assertEqual(dom.lqi_label(4), "very poor")
        self.assertIsNone(dom.lqi_label(9))
        self.assertIsNone(dom.lqi_label(None))


class TestDates(unittest.TestCase):
    def test_valid(self):
        d1, d2 = dom.validate_dates("2026-11-01", "2026-11-10")
        self.assertEqual((d1.isoformat(), d2.isoformat()),
                         ("2026-11-01", "2026-11-10"))

    def test_bad_format(self):
        with self.assertRaises(ValueError):
            dom.validate_dates("10.11.2026", "2026-11-10")

    def test_reversed(self):
        with self.assertRaises(ValueError):
            dom.validate_dates("2026-11-10", "2026-11-01")

    def test_too_long(self):
        with self.assertRaises(ValueError):
            dom.validate_dates("2026-10-01", "2026-11-11")


if __name__ == "__main__":
    unittest.main()
