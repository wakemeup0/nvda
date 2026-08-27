# Hoo Said That Windows VM test profile

This branch adds an opt-in presentation recorder for real NVDA browser tests.
It does not make NVDA a Windows container application: NVDA still needs an
interactive Windows desktop. A Linux OCI launcher may host that desktop in a
KVM virtual machine, but the screen reader and browser run inside Windows.

Set `HOOSAIDTHAT_NVDA_CAPTURE` to an absolute file path before starting NVDA.
The built-in `hoosaidthatCapture` global plugin writes line-delimited JSON for:

- fully processed speech sequences queued for synthesis;
- speech cancellation;
- pause and resume state;
- recorder readiness.

Each record has a monotonic process-local sequence and UTC timestamp. Speech
records retain NVDA speech-command class names and priority. Capture failure is
logged but never changes or suppresses presentation.

Recommended launch flags for a disposable test desktop:

```powershell
nvda.exe --minimal --disable-addons --no-logging --config-path C:\HooSaidThat\nvda-config
```

`--minimal` removes UI, sounds, and startup speech. `--disable-addons` removes
third-party variability; this recorder is built in and remains available.
Keep UIA and IAccessible enabled because browser access depends on them.
