# A part of NonVisual Desktop Access (NVDA)
# Copyright (C) 2026 Hoo Said That contributors
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Opt-in, lossless presentation-request capture for automated web testing.

This built-in plugin stays inert unless ``HOOSAIDTHAT_NVDA_CAPTURE`` points to
an output file. It observes the same fully processed sequences sent to the
synthesizer. It never changes speech or inspects a browser accessibility tree.
"""

import os
import threading
from typing import Any

import globalPluginHandler
from hoosaidthatCapture import appendRecord, serializeRecord
from logHandler import log
import speech.extensions


_CAPTURE_ENV = "HOOSAIDTHAT_NVDA_CAPTURE"


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Append speech lifecycle records to a UTF-8 JSONL stream when enabled."""

	def __init__(self):
		super().__init__()
		self._path = os.environ.get(_CAPTURE_ENV)
		self._lock = threading.Lock()
		self._sequence = 0
		self._registrations: list[tuple[Any, Any]] = []
		if not self._path:
			return
		try:
			parent = os.path.dirname(os.path.abspath(self._path))
			os.makedirs(parent, exist_ok=True)
			self._register(speech.extensions.pre_speechQueued, self._onSpeechQueued)
			self._register(speech.extensions.speechCanceled, self._onSpeechCanceled)
			self._register(speech.extensions.post_speechPaused, self._onSpeechPaused)
			self._writeRecord("ready", captureVersion=1)
			log.info("Hoo Said That presentation capture registered")
		except Exception:
			self._unregister()
			log.exception("Hoo Said That presentation capture registration failed")

	def _onSpeechQueued(self, speechSequence, priority=None, **_kwargs):
		textParts: list[str] = []
		commandTypes: list[str] = []
		for item in speechSequence:
			if isinstance(item, str):
				textParts.append(item)
			else:
				commandTypes.append(type(item).__name__)
		priorityName = getattr(priority, "name", None)
		self._writeRecord(
			"speech",
			text="".join(textParts),
			commandTypes=commandTypes,
			priority=priorityName if isinstance(priorityName, str) else str(priority or ""),
		)

	def _onSpeechCanceled(self, **_kwargs):
		self._writeRecord("interrupt")

	def _onSpeechPaused(self, switch=False, **_kwargs):
		self._writeRecord("pause", paused=bool(switch))

	def _register(self, extension, handler):
		extension.register(handler)
		self._registrations.append((extension, handler))

	def _writeRecord(self, kind: str, **fields: Any):
		if not self._path:
			return
		try:
			with self._lock:
				self._sequence += 1
				appendRecord(self._path, serializeRecord(kind, self._sequence, fields))
		except Exception:
			# Evidence transport failure must not alter NVDA speech behavior.
			log.exception("Hoo Said That presentation capture write failed")

	def _unregister(self):
		for extension, handler in reversed(self._registrations):
			try:
				extension.unregister(handler)
			except Exception:
				pass
		self._registrations.clear()

	def terminate(self):
		self._unregister()
		super().terminate()
