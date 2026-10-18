# Native CDR sampler placement candidate

The complete repaired power484 screen39141648105 still fails data/phase and
53/52 HBT gates. Actual path review39142648950 reproduces those failures.
The prior waveform showed up to about150mV collector-to-base drop on the
same sampler output feedback conductor. Full-parent clock/output wire
capacitance remains significant. XOR source access improvement alone did
not repair sampler behavior.

This candidate changes only the physical order of37 active/passive primitives
inside the existing54-device sampler. Native PCell widths and original18um
clearance determine exact positions. Deterministic pair swaps and segment
reversals reduce weighted native-center spans, prioritizing master/slave
output/feedback nets, clocks and data. This is a geometry planning objective,
not a timing model or an acceptance criterion. All dimensions, source circuit,
route widths, native via arrays and17 finite substrate taps remain unchanged.

The original560-rule DRC, unsimplified deep/flat54-device LVS, fourteen actual
fault controls and native LEF readback apply. Exact source-delta checks retain
the prior generator/checker/controller and all original checks. No transistor
or waveform gate is relaxed. A leaf physical pass must be followed by full
parent integration, independent primitive/route identity checks, fresh native
MIM-aware RC and all original loaded early/late/fault screens. Full PHY,
closed-loop recovery and mainchip timing remain unproven.


First run39143329188 stopped during generation: a distributed body tap had no
independent M4 column within the old plus/minus3um search window after the
primitive reordering. Native DRC/LVS was not reached. The correction expands
only the eight distributed taps' nearest-safe search to plus/minus20um. All
nine local MOS taps keep their original search and primitive-clearance checks;
all taps retain the original2um M4-column separation, area/perimeter and
finite reference devices. The failed source and logs remain archived.


Corrected leaf39143630895 passed560DRC categories, unsimplified deep/flat54LVS,
all14 actual faults and LEF readback. Weighted planning cost fell15665.54 to
11095.76; QP span1029.285→302.31um andQN1079.685→377.615um. Some emitter/
clock nets became longer, so only fresh complete RC/transients can determine
whether the tradeoff is useful. Native cell sizes/circuit remain unchanged.

Fullparent candidate replaces all four sampler masters, retains repaired XOR
and all other seven child types, and compares every one of54 native primitive
drawings and reference independently. Original484-device DRC/LVS and five
faults remain. The supply-riser code retains every actual clearance/endpoint
check; the previous placement-specific three shifted-device names are replaced
by the same1.645um geometric clearance check for every current sampler riser.


## Full parent physical result and fresh extraction boundary

Run39145031468 at55d7f857dd60d8757f8bcb8352287c7f151d58f5 passed the actual560-category native DRC and unsimplified484-device deep/flat LVS with five physical fault controls. The54-primitive sampler drawing comparison and its three corruption controls also passed after retaining both native Layout owners. Earlier comparison failures and polygon diagnostics remain in their original cloud releases. The diagnostic JSON emitted during a deliberately removed-HBT fault in the successful run is a negative-control artifact, not an accepted geometry mismatch.

The new parent has four reordered sampler leaves. Its old wire RC and failed-wave results must not be reused as this candidate's extracted result. The next cloud stage independently compares all eight copied leaf drawings and all16 actual macro transforms, then binds158 planes and1394 native terminals to51 logical nets with the original19 fault controls. Fresh wire RC, intrinsic-device binding, MIM composition and unchanged full loaded electrical gates remain mandatory. No closed-loop or full serial PHY acceptance is claimed.


## Fresh native wire RC and compact models

Runs39146048020 and39146048128 atf63d92772632e117c68d918bace534ad09c3340e completed the new geometry's whole-parent wire-only extraction and484-device PDK compact-model binding. The raw wire network contains3227 resistors and3830 capacitors with111 conductor components and946 physical points;13 raw-network corruptions and12 model-binding corruptions were rejected. These element counts describe an extracted network, not timing improvement or electrical acceptance.

The next capture restores this exact RC and model binding, adds all11 actual MIM masks, rebinds the native bottom-contact points and preserves the original geometry/ownership controls. Substrate spreading, RF distribution and full loaded electrical behavior remain unqualified.
