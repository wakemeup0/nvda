"""Command-line entry point for the Linux NVDA container port."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import __version__


def main() -> int:
	parser = argparse.ArgumentParser(prog="nvda-linux")
	parser.add_argument("--version", action="store_true")
	args = parser.parse_args()
	if args.version:
		print(f"NVDA Linux container port {__version__} (NVDA fork release-2026.1.1)")
		return 0
	events_path = os.environ.get("HOOSAIDTHAT_NVDA_CAPTURE")
	if not events_path:
		parser.error("HOOSAIDTHAT_NVDA_CAPTURE is required")
	logging.basicConfig(level=os.environ.get("NVDA_LINUX_LOG_LEVEL", "INFO"))
	from .backend import LinuxNvdaScreenReader

	LinuxNvdaScreenReader(Path(events_path)).run()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
