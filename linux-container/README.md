# NVDA Linux container port

This directory is the Linux backend of the `wakemeup0/nvda` fork. It keeps
NVDA navigation gestures and NVDA-style web presentation ordering, but replaces
Windows UI Automation, IAccessible2, Win32 input, audio and installer code with
AT-SPI 2, an AT-SPI device listener and a bounded presentation-request stream.

The published Linux image copies only this directory from the fork. It does not
contain Wine, Windows, a Windows VM, the NVDA Windows executable, or Orca.

This is a port, not an upstream-supported NVDA platform. Compatibility claims
must be tied to the tested action and presentation corpus.
