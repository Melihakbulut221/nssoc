# Extracted PLL temperature-only screen

The standalone extracted c5r3k PLL passed the frozen nominal acquisition
gate in run 42403662141. This experiment holds the extracted deck, models,
supplies, stimulus, 1 us duration, 0.3125 ps maximum step and acquisition
thresholds fixed, and screens -40 C and 125 C.

Source parent: c01fd89fcfb9cc094999b9a6285c6db50b3a5806.
Preparation archive: run 42403338623, SHA256
9624f52ea28ce3aa92c2232b135c7162912756f565913079d8c09863adbf0dde.
The original benchmark and probes are reused unchanged. The frozen gate
source is checked out at 415db81024b44298c0d3fbf1a6b90be3a08e923f and its
existing SHA256 guard is retained.

Only the temperature card changes. The adapter proves the edit is reversible,
rejects multiple/competing temperature overrides, records before/after
hashes and requires the native simulator log to report the requested temperature.
Cloud controls exercise these rejection paths before native jobs can start.

Entry: cloud-evidence-summary.yml on this branch, workflow_dispatch without
inputs. Each corner is a separate hosted job; failure does not cancel the other.
Derived artifacts preserve the temperature edit, readback, native log,
trajectory and unchanged independent acquisition gate verdict.
No new result is claimed until those artifacts exist and are reviewed.

This is temperature-only screening, not full process/voltage/temperature
qualification, device safety, qualified parasitics, closed-loop CDR or mainchip
integration. Only the original public-net probes are saved; device safety
cannot be inferred from this capture.
