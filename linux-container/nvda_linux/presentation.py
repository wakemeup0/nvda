"""Small, deterministic subset of NVDA web presentation rules."""

from __future__ import annotations

from dataclasses import dataclass, field


ROLE_LABELS = {
	"alert": "alert",
	"article": "article",
	"button": "button",
	"check box": "check box",
	"combo box": "combo box",
	"document web": "document",
	"entry": "edit",
	"form": "form",
	"graphic": "graphic",
	"heading": "heading",
	"landmark": "landmark",
	"link": "link",
	"list": "list",
	"list item": "list item",
	"paragraph": "paragraph",
	"radio button": "radio button",
	"table": "table",
	"table cell": "cell",
}


@dataclass(frozen=True)
class AccessibleSnapshot:
	role: str
	name: str = ""
	text: str = ""
	attributes: dict[str, str] = field(default_factory=dict)
	states: frozenset[str] = frozenset()


def present(snapshot: AccessibleSnapshot) -> str:
	"""Return concise speech in NVDA order: content, role, state."""

	role = snapshot.role.lower()
	name = normalize(snapshot.name)
	text = normalize(snapshot.text)
	content = name or text
	parts: list[str] = []
	if content:
		parts.append(content)
	if role == "heading":
		level = snapshot.attributes.get("level") or snapshot.attributes.get("aria-level")
		parts.append(f"heading level {level}" if level and level.isdigit() else "heading")
	elif role in ROLE_LABELS:
		parts.append(ROLE_LABELS[role])
	elif role and role not in {"section", "panel", "application", "frame"}:
		parts.append(role)
	states = snapshot.states
	if "checked" in states:
		parts.append("checked")
	elif "checkable" in states:
		parts.append("not checked")
	if "expanded" in states:
		parts.append("expanded")
	elif "expandable" in states:
		parts.append("collapsed")
	if "required" in states:
		parts.append("required")
	if "invalid" in states:
		parts.append("invalid entry")
	if (
		role
		in {
			"button",
			"check box",
			"combo box",
			"entry",
			"link",
			"radio button",
			"spin button",
		}
		and "sensitive" not in states
		and "enabled" not in states
	):
		parts.append("unavailable")
	return " ".join(dict.fromkeys(part for part in parts if part))


def normalize(value: str) -> str:
	return " ".join(value.replace("\u00a0", " ").split())[:4000]
