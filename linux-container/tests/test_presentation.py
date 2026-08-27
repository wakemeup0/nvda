import unittest

from nvda_linux.presentation import AccessibleSnapshot, present


class PresentationTests(unittest.TestCase):
	def test_heading_uses_nvda_content_role_level_order(self):
		value = AccessibleSnapshot(
			role="heading",
			name="Checkout",
			attributes={"level": "1"},
			states=frozenset({"enabled", "sensitive"}),
		)
		self.assertEqual(present(value), "Checkout heading level 1")

	def test_control_states_are_spoken(self):
		value = AccessibleSnapshot(
			role="check box",
			name="Accept terms",
			states=frozenset({"checkable", "required", "enabled", "sensitive"}),
		)
		self.assertEqual(present(value), "Accept terms check box not checked required")

	def test_text_is_used_when_name_is_missing(self):
		value = AccessibleSnapshot(
			role="paragraph",
			text="Delivery   address",
			states=frozenset({"enabled", "sensitive"}),
		)
		self.assertEqual(present(value), "Delivery address paragraph")
