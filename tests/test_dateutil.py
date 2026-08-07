"""Unit tests for deterministic local-day handling (timezone boundaries)."""
import unittest

from _util import SCRIPTS  # noqa: F401
import dateutil as bd  # our module, not the PyPI package


class TestDateUtil(unittest.TestCase):
    def test_human_day(self):
        self.assertEqual(bd.human_day("2026-08-07"), "Friday, August 7")
        self.assertEqual(bd.human_day("2026-08-08"), "Saturday, August 8")

    @unittest.skipUnless(bd.have_tz(), "zoneinfo unavailable")
    def test_local_day_boundaries(self):
        # 2026-08-07 in LA is UTC-7 (PDT). Local midnight = 07:00Z.
        start, end = bd.local_day_bounds("2026-08-07", "America/Los_Angeles")
        self.assertEqual(start.isoformat(), "2026-08-07T07:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-08-08T07:00:00+00:00")

    @unittest.skipUnless(bd.have_tz(), "zoneinfo unavailable")
    def test_instant_in_and_out_of_day(self):
        # 06:30Z on Aug 7 is still Aug 6 in LA (23:30 previous day) -> out of the Aug 7 window.
        self.assertFalse(bd.in_local_day("2026-08-07T06:30:00Z", "2026-08-07", "America/Los_Angeles"))
        # 20:00Z on Aug 7 is 13:00 LA -> in window.
        self.assertTrue(bd.in_local_day("2026-08-07T20:00:00Z", "2026-08-07", "America/Los_Angeles"))

    @unittest.skipUnless(bd.have_tz(), "zoneinfo unavailable")
    def test_timezone_conversion_for_source(self):
        # A NY-created noon meeting is 9am LA on the same date.
        self.assertEqual(bd.local_date_for("2026-08-07T12:00:00-04:00", "America/Los_Angeles"), "2026-08-07")


if __name__ == "__main__":
    unittest.main()
