# CDR v43: reduce physical slave selector input area

The full original v41 follower_n8 captures remain electrically rejected.
Direct source-bound pair diagnosis39945517007 measured only approximately
0.476–0.685ps median base-to-collector-current response. Most of the
original-edge-to-selector-current offset already exists at the actual base.
The prior nearest-clock metric used the measured loaded cp/cn port; its
difference from the original edge must not be labeled transistor delay.

One controlled candidate changes only16 slave selector HBTs from Nx3 to Nx2
across A/B/C/D. The actual terminal graph verifies collectors, clock bases,
common emitters and native device identity. It leaves all master devices,
slave data/hold HBTs, tails, loads, followers and biases unchanged. The
total selector emitter count drops from80 to64, targeting input loading.
This is a hypothesis, not an asserted capacitance or timing improvement.

The parent active master selector peaks exceed3mA/device, so Nx1 masters
would violate the existing per-emitter gate at those currents. They are
not changed. Parent slave peaks are approximately5.0–5.21mA/device, giving
a reason to evaluate Nx2. This arithmetic does not prove new safety:
startup, all-time current, VCE/VBE and original functional gates all rerun.

The native test retains external8GHz clock, source10ohm resistance,256bits,
full34.25ns/1104columns,150fF output loads, original phase/deadline/oracles,
model/runtime and solver. Both original early/late cases run in GitHub.
Additional measured loaded-port/pair clock observations aid comparison;
they do not move the original clocks or acceptance windows.

This is an intrinsic candidate on the frozen17918R/12850C v32 network.
Before any layout or PHY claim, an electrically useful candidate needs
actual revised geometry, extraction, DRC/LVS, fresh RC and repeated loaded,
PVT, loop and full integration verification. v42 remains rejected.


## Actual result: rejected in both phases

Run39947591954 completed both original34.25ns captures with113475 complete
rows and1104 columns. Both passed device limits and both failed original
data/phase gates. All pre/post source checks passed; exactly16 parent cards
changed and64 unique original changes remained. Full artifacts and precise
metrics are pinned in docs/evidence/cdr-v43-selector-results-20261023.json.

Early C/D wrong-sign samples are30/36; late12/31. C still has65 samples
below100mV in each phase. B passes, A still misses the100mV gate. Signed
phase magnitudes are13.930mV/14.409mV against the unchanged30mV requirement.
The measured loaded cp/cn rising-edge median offsets are9.861ps/9.845ps
from original expected edges. Every original source window has one crossing.

These results do not support promoting selector-only resizing as the fix.
Do not rerun this same candidate or relax clocks/thresholds. The remaining
C/D failure requires work on actual cascaded data transfer and its gain,
headroom and settling, using existing whole-record terminal observations
before choosing a further circuit or physical change. A new data-path
topology, if needed, must preserve actual loading and receive fresh physical
qualification; a frozen-wire sizing screen is not an integrated layout.
