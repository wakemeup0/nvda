"""Bounded NVDA presentation-request JSONL output."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import threading
import time


MAX_EVENT_BYTES = 1024 * 1024
MAX_LOG_BYTES = 16 * 1024 * 1024


class PresentationWriter:
	"""Append ordered speech requests without replacing a synthesizer."""

	def __init__(self, path: Path) -> None:
		self._path = path
		self._lock = threading.Lock()
		self._sequence = 0
		path.parent.mkdir(parents=True, exist_ok=True)
		path.touch(mode=0o600, exist_ok=True)

	def speak(self, text: str, command: str = "NVDA.speech.speak") -> None:
		clean = " ".join(text.split())
		if not clean:
			return
		with self._lock:
			self._sequence += 1
			record = {
				"sequence": self._sequence,
				"monotonicNs": time.monotonic_ns(),
				"kind": "speech",
				"text": clean,
				"command": command,
			}
			payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
			if len(payload) > MAX_EVENT_BYTES:
				record["text"] = clean[: MAX_EVENT_BYTES // 4]
				record["truncated"] = True
				payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
			self._append(payload)

	def _append(self, payload: bytes) -> None:
		with self._path.open("ab", buffering=0) as stream:
			fcntl.flock(stream, fcntl.LOCK_EX)
			if os.fstat(stream.fileno()).st_size + len(payload) > MAX_LOG_BYTES:
				raise RuntimeError("NVDA presentation log exceeded safety bound")
			stream.write(payload)
			os.fsync(stream.fileno())
			fcntl.flock(stream, fcntl.LOCK_UN)
