# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2026 Hoo Said That contributors
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Dependency-free JSONL primitives used by the Hoo Said That capture plugin."""

import json
import os
from datetime import datetime, timezone
from typing import Any


MAX_RECORD_BYTES = 1024 * 1024


def serializeRecord(kind: str, sequence: int, fields: dict[str, Any]) -> bytes:
	"""Serialize one bounded record, preserving valid UTF-8 and JSON."""

	record = {
		"kind": kind,
		"sequence": sequence,
		"timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
		**fields,
	}
	payload = _encode(record)
	if len(payload) <= MAX_RECORD_BYTES:
		return payload
	record["text"] = str(record.get("text", ""))[: MAX_RECORD_BYTES // 4]
	record["truncated"] = True
	return _encode(record)


def appendRecord(path: str, payload: bytes) -> None:
	"""Append all bytes as one record and close the descriptor before returning."""

	flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_BINARY", 0)
	fd = os.open(path, flags, 0o600)
	try:
		remaining = memoryview(payload)
		while remaining:
			written = os.write(fd, remaining)
			if written <= 0:
				raise OSError("capture append made no progress")
			remaining = remaining[written:]
	finally:
		os.close(fd)


def _encode(record: dict[str, Any]) -> bytes:
	return (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
