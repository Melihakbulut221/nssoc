# Active level-shifter topology experiment

v44-v47 native records expose weak C/D data at the expected aperture and narrow
master-selector headroom. Increasing drive, selector area or lowering data
area did not close the original gates. The next candidate changes topology:
a native differential HBT pair with two parallel36um NMOS tails, an8um MOS
reference, two rppd collector loads and two finite native output shunts.
Collector polarity restores non-inverting differential transfer. There is no
behavioral gain, internal regenerated bit or ideal output-level source.

The initial load dimensions are W8/L2.8um and shunt W4/L7.2um. IHP's published
rppd target sheet resistance is260ohms/square; it recommends at least2um width
for precision resistors. Sheet-only estimates suggest approximately91/468ohms
before contact, bias and temperature effects. These estimates motivate the
candidate; they are not used instead of native models or physical extraction.
Source: https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html#rppd-specs

The standalone native test uses actual pinned npn13G2/SG13 LV MOS/rppd models,
not a linearized replacement. It supplies256 PRBS bits at8Gb/s,60mV differential
input around1.48V common mode,10ohm source resistances and150fF on each output,
with full34.25ns capture and0.3125ps maximum step. These are explicit component
stress conditions motivated by the observed weak source. They do not reproduce
the complete original parent waveform, distributed input loading or clock path.

The component aims for at least100mV differential by37.5ps and1.8-2.15V output
common mode. All original HBT voltage/current and MOS terminal limits are reused.
These additional component goals do not replace any original full-CDR gate.
Nominal,125C/low-supply/res-wcs/mos-ss and-40C/high-supply/res-bcs/mos-ff cases
use the pinned HBT typical model; they are not complete HBT process/PVT signoff.
Actual swapped-output and bias-off captures must reject functional acceptance.
Zero-source OP, native OFF readback, every recorded vector and source identity
are checked. All failures are retained, including numerical diagnostics.

No original parent waveform, topology, gate, active process or layout is changed.
A useful component must next be connected to actual C/D source/loading and
existing bias infrastructure, replace the passive divider in a real candidate
schematic/layout, receive native DRC/LVS/freshRC and repeat every original
full-CDR/loop/PVT test. A standalone pass cannot establish PHY integration.
