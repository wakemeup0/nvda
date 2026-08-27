"""AT-SPI and physical-key backend for the Linux NVDA container port."""

from __future__ import annotations

from collections.abc import Iterable
import logging
from pathlib import Path
from typing import Any

import gi

gi.require_version("Atspi", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Atspi, Gdk, GLib  # noqa: E402

from .events import PresentationWriter  # noqa: E402
from .presentation import AccessibleSnapshot, present  # noqa: E402


LOG = logging.getLogger(__name__)
MAX_TREE_NODES = 50_000
STRUCTURAL_ROLES = {
	"heading": {"heading"},
	"landmark": {"landmark"},
	"button": {"button"},
	"formField": {"check box", "combo box", "entry", "radio button", "spin button"},
	"link": {"link"},
	"list": {"list"},
	"listItem": {"list item"},
	"table": {"table"},
	"image": {"graphic", "image"},
	"checkbox": {"check box"},
	"radioButton": {"radio button"},
	"combobox": {"combo box"},
	"entry": {"entry"},
	"paragraph": {"paragraph"},
}
QUICK_KEYS = {
	"h": "heading",
	"d": "landmark",
	"b": "button",
	"f": "formField",
	"k": "link",
	"l": "list",
	"i": "listItem",
	"t": "table",
	"g": "image",
	"x": "checkbox",
	"r": "radioButton",
	"c": "combobox",
	"e": "entry",
	"p": "paragraph",
}


class LinuxNvdaScreenReader:
	"""Screen reader using NVDA gestures and an AT-SPI accessibility backend."""

	def __init__(self, events_path: Path) -> None:
		self._writer = PresentationWriter(events_path)
		self._current: Any | None = None
		self._browse_mode = True
		self._insert_down = False
		self._character_offset = 0
		self._device = Atspi.Device.new_full("org.nvaccess.NVDALinux")
		self._device.add_key_watcher(self._on_key_event)
		self._listener = Atspi.EventListener.new(self._on_accessibility_event)
		for event_type in (
			"document:load-complete",
			"object:announcement",
			"object:state-changed:checked",
			"object:state-changed:expanded",
			"object:state-changed:focused",
		):
			self._listener.register(event_type)

	def run(self) -> None:
		self._writer.speak("NVDA Linux ready", "NVDA.startup")
		GLib.MainLoop().run()

	def _on_accessibility_event(self, event: Any) -> None:
		try:
			if event.type == "object:state-changed:focused" and not event.detail1:
				return
			if event.type == "object:announcement":
				announcement = str(event.any_data or "")
				if announcement:
					self._writer.speak(announcement, "NVDA.liveRegion")
				return
			self._current = event.source
			self._character_offset = 0
			self._present(event.source)
		except Exception:
			LOG.exception("accessibility event processing failed")

	def _on_key_event(
		self,
		_device: Any,
		pressed: bool,
		_keycode: int,
		keysym: int,
		modifiers: int,
		text: str,
	) -> bool:
		key_name = Gdk.keyval_name(keysym) or text or ""
		if key_name in {"Insert", "KP_Insert"}:
			self._insert_down = pressed
			return False
		if not pressed:
			return False
		try:
			if self._insert_down:
				return self._handle_nvda_chord(key_name)
			if not self._browse_mode or self._has_control_or_alt(modifiers):
				return False
			quick_key = key_name.lower()
			if quick_key in QUICK_KEYS:
				backward = self._has_shift(modifiers) or key_name.isupper()
				self._move_to_role(QUICK_KEYS[quick_key], backward)
				return True
			if key_name in {"Right", "Left"}:
				self._move_character(-1 if key_name == "Left" else 1)
				return True
			if key_name in {"Down", "Up"}:
				self._move_linear(-1 if key_name == "Up" else 1)
				return True
			if key_name in {"Return", "KP_Enter", "space"} and self._current is not None:
				return self._activate_current()
		except Exception:
			LOG.exception("keyboard event processing failed")
			self._writer.speak("NVDA command failed", "NVDA.error")
			return True
		return False

	def _handle_nvda_chord(self, key_name: str) -> bool:
		if key_name in {"Tab", "KP_Enter"}:
			self._ensure_current()
			self._present(self._current)
			return True
		if key_name == "Down":
			self._say_all()
			return True
		if key_name in {"space", "Space"}:
			self._browse_mode = not self._browse_mode
			self._writer.speak(
				"browse mode" if self._browse_mode else "focus mode",
				"NVDA.mode",
			)
			return True
		return False

	def _move_to_role(self, kind: str, backward: bool) -> None:
		document = self._document()
		if document is None:
			self._writer.speak("no browse mode document", "NVDA.error")
			return
		nodes = [node for node in self._walk(document) if self._role(node) in STRUCTURAL_ROLES[kind]]
		self._select_relative(nodes, -1 if backward else 1, f"no {kind}")

	def _move_linear(self, direction: int) -> None:
		document = self._document()
		if document is None:
			return
		nodes = [node for node in self._walk(document) if self._is_presentable(node)]
		self._select_relative(nodes, direction, "edge of document")

	def _select_relative(self, nodes: list[Any], direction: int, empty_message: str) -> None:
		if not nodes:
			self._writer.speak(empty_message, "NVDA.browseMode")
			return
		index = self._identity_index(nodes, self._current)
		if index is None:
			index = len(nodes) if direction < 0 else -1
		next_index = (index + direction) % len(nodes)
		self._current = nodes[next_index]
		self._character_offset = 0
		self._present(self._current)

	def _move_character(self, direction: int) -> None:
		self._ensure_current()
		if self._current is None:
			return
		value = self._snapshot(self._current).name or self._snapshot(self._current).text
		if not value:
			self._move_linear(direction)
			return
		self._character_offset = max(0, min(len(value) - 1, self._character_offset + direction))
		character = value[self._character_offset]
		self._writer.speak("space" if character.isspace() else character, "NVDA.character")

	def _say_all(self) -> None:
		document = self._document()
		if document is None:
			return
		nodes = [node for node in self._walk(document) if self._is_presentable(node)]
		index = self._identity_index(nodes, self._current) or 0
		for node in nodes[index:]:
			self._present(node, "NVDA.sayAll")

	def _activate_current(self) -> bool:
		try:
			count = Atspi.Action.get_n_actions(self._current)
			if count > 0 and Atspi.Action.do_action(self._current, 0):
				return True
		except GLib.Error:
			pass
		return False

	def _ensure_current(self) -> None:
		if self._current is None:
			self._current = self._document()

	def _document(self) -> Any | None:
		node = self._current
		while node is not None:
			if self._role(node) == "document web":
				return node
			try:
				node = Atspi.Accessible.get_parent(node)
			except GLib.Error:
				break
		for candidate in self._walk(Atspi.get_desktop(0)):
			if self._role(candidate) == "document web":
				return candidate
		return None

	def _walk(self, root: Any) -> Iterable[Any]:
		stack = [root]
		visited = 0
		while stack:
			node = stack.pop()
			visited += 1
			if visited > MAX_TREE_NODES:
				raise RuntimeError("AT-SPI tree exceeded safety bound")
			yield node
			try:
				for index in range(Atspi.Accessible.get_child_count(node) - 1, -1, -1):
					child = Atspi.Accessible.get_child_at_index(node, index)
					if child is not None:
						stack.append(child)
			except GLib.Error:
				continue

	def _present(self, node: Any | None, command: str = "NVDA.speech.speak") -> None:
		if node is not None:
			self._writer.speak(present(self._snapshot(node)), command)

	def _snapshot(self, node: Any) -> AccessibleSnapshot:
		role = self._role(node)
		name = self._safe(lambda: Atspi.Accessible.get_name(node), "")
		attributes = self._safe(lambda: Atspi.Accessible.get_attributes(node), {}) or {}
		text = ""
		try:
			length = Atspi.Text.get_character_count(node)
			if 0 < length <= 10_000:
				text = Atspi.Text.get_text(node, 0, length)
		except GLib.Error:
			pass
		states: set[str] = set()
		state_set = self._safe(lambda: Atspi.Accessible.get_state_set(node), None)
		if state_set is not None:
			for state_name, state_type in {
				"checkable": Atspi.StateType.CHECKABLE,
				"checked": Atspi.StateType.CHECKED,
				"enabled": Atspi.StateType.ENABLED,
				"expandable": Atspi.StateType.EXPANDABLE,
				"expanded": Atspi.StateType.EXPANDED,
				"invalid": Atspi.StateType.INVALID_ENTRY,
				"required": Atspi.StateType.REQUIRED,
				"sensitive": Atspi.StateType.SENSITIVE,
			}.items():
				if state_set.contains(state_type):
					states.add(state_name)
		return AccessibleSnapshot(role, str(name or ""), str(text or ""), dict(attributes), frozenset(states))

	@staticmethod
	def _role(node: Any) -> str:
		try:
			return str(Atspi.Accessible.get_role_name(node)).lower()
		except GLib.Error:
			return ""

	def _is_presentable(self, node: Any) -> bool:
		snapshot = self._snapshot(node)
		return bool(present(snapshot)) and snapshot.role not in {"application", "frame", "panel", "section"}

	@staticmethod
	def _identity_index(nodes: list[Any], current: Any | None) -> int | None:
		if current is None:
			return None
		for index, node in enumerate(nodes):
			if node == current:
				return index
		return None

	@staticmethod
	def _safe(operation, fallback):
		try:
			return operation()
		except GLib.Error:
			return fallback

	@staticmethod
	def _has_shift(modifiers: int) -> bool:
		return bool(modifiers & (1 << int(Atspi.ModifierType.SHIFT)))

	@staticmethod
	def _has_control_or_alt(modifiers: int) -> bool:
		blocked = (1 << int(Atspi.ModifierType.CONTROL)) | (1 << int(Atspi.ModifierType.ALT))
		return bool(modifiers & blocked)
