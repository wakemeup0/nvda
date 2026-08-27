import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from nvda_linux.events import PresentationWriter


class PresentationWriterTests(unittest.TestCase):
	def test_writes_ordered_protocol_events(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "events.jsonl"
			writer = PresentationWriter(path)
			writer.speak("  Checkout   heading  ")
			writer.speak("Pay now button")
			records = [json.loads(line) for line in path.read_text().splitlines()]
			self.assertEqual([record["sequence"] for record in records], [1, 2])
			self.assertEqual(records[0]["text"], "Checkout heading")
			self.assertEqual(records[0]["kind"], "speech")
			self.assertIsInstance(records[0]["monotonicNs"], int)

	def test_monotonic_clock_is_session_relative(self):
		with tempfile.TemporaryDirectory() as directory:
			path = Path(directory) / "events.jsonl"
			with mock.patch(
				"nvda_linux.events.time.monotonic_ns",
				side_effect=[2**53 + 1000, 2**53 + 1123],
			):
				writer = PresentationWriter(path)
				writer.speak("Ready")
			record = json.loads(path.read_text().strip())
			self.assertEqual(record["monotonicNs"], 123)
