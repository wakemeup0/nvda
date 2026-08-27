import unittest

from nvda_linux.backend import live_region_text, relative_index


class NavigationTests(unittest.TestCase):
	def test_navigation_stops_at_document_boundaries(self):
		self.assertEqual(relative_index(3, 0, 1), 1)
		self.assertIsNone(relative_index(3, 2, 1))
		self.assertIsNone(relative_index(3, 0, -1))

	def test_chromium_text_insert_is_a_live_presentation_candidate(self):
		self.assertEqual(
			live_region_text("object:text-changed:insert", " Order  review ready "),
			"Order review ready",
		)
		self.assertEqual(live_region_text("object:state-changed:focused", "ignored"), "")
