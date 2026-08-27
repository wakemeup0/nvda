# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2026 Hoo Said That contributors
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import json
import os
import tempfile
import unittest

from hoosaidthatCapture import MAX_RECORD_BYTES, appendRecord, serializeRecord


class TestHooSaidThatCapture(unittest.TestCase):
	def test_unicodeJsonlRoundTrip(self):
		payload = serializeRecord("speech", 7, {"text": "Grüße 世界", "commandTypes": ["LangChange"]})
		self.assertTrue(payload.endswith(b"\n"))
		record = json.loads(payload)
		self.assertEqual(record["kind"], "speech")
		self.assertEqual(record["sequence"], 7)
		self.assertEqual(record["text"], "Grüße 世界")

	def testOversizeSpeechIsBoundedValidJson(self):
		payload = serializeRecord("speech", 1, {"text": "x" * (MAX_RECORD_BYTES * 2)})
		self.assertLessEqual(len(payload), MAX_RECORD_BYTES)
		record = json.loads(payload)
		self.assertTrue(record["truncated"])

	def testAppendPreservesRecordBoundaries(self):
		with tempfile.TemporaryDirectory() as directory:
			path = os.path.join(directory, "capture.jsonl")
			appendRecord(path, serializeRecord("ready", 1, {}))
			appendRecord(path, serializeRecord("interrupt", 2, {}))
			with open(path, "rb") as stream:
				lines = stream.readlines()
			self.assertEqual(len(lines), 2)
			self.assertEqual([json.loads(line)["sequence"] for line in lines], [1, 2])
