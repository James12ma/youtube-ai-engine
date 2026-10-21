# Task 8 technical audit

**Status:** Code compiles and offline suite passes. Not live-validated with Piper or WhisperX.

**Tests executed:** `155 passed, 3 skipped` (full Tasks 1–8 suite) on Python 3.13.5, ffmpeg 7.1.5. The 3 skipped tests are the original provider API smoke tests. Thirteen newly added Task 8 offline tests passed. Real Piper/WhisperX execution is unavailable in this container because dependencies/models are not installed and outbound DNS is disabled.

**Major defects in supplied design:** incompatible version pins; false positive model path from `Path('')` in original tests; caption quality validates against already-aligned subset rather than verifying transcript completeness; max pause treated as failure of alignment; no hard per-line ASS wrapping; unqualified claims of exact alignment, commercial rights, or quality of sample; real smoke script did not itself render MP4 (only original test case did).

**Corrections:** compatible dependency constraints; explicit CPU Piper WAV wrapper; WhisperX CTC wrapper with token coverage rejection and interval checks; two-line ASS; independent caption QA; verified EBU R128 output; opt-in real MP4 proof script; no publishing.

**Still pending:** Install dependencies in isolated environment and confirm resolution, download a voice and CTC acoustic model subject to their licenses/attribution, run genuine synthesis/forced alignment and inspect/listen to its MP4. CPU runtime/RAM, voice appeal, model rights and alignment accuracy are not established by offline mocks.
