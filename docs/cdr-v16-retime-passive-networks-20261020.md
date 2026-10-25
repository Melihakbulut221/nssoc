# CDR retime repair: measure native metal before changing intrinsic circuits

V16's metal widening preserved all device gates but failed sampling. It is not
evidence that the nominal filter resistor alone is the cause: the existing
native waveform shows substantial loss before and after the intrinsic filter.
Via resistance and distributed conductor load must be distinguished from
the actual nonlinear rppd, MIM and sampler bias network.

This cloud job restores the exact v16 composed model, native terminals,
device locations and planes. It derives all four master/slave latch graphs
from actual116HBT ownership and retains the original three graph faults per
sampler. Both retime chains retain their native filter/series/shunt/bias/MIM
identities and three wrong-ownership/terminal/rail corruption controls.

On each differential leg it solves R-only effective resistance along actual
collector-to-filter, filter-to-sampler, sampler-to-base and supply-return
components. Wire capacitance is classified separately. No intrinsic device
is replaced by a linear resistor, no waveform is altered and no R*C delay
prediction is promoted to transient evidence. The original failed fullwave
remains the required electrical acceptance test.

The purpose is selecting a physical via/access repair versus an intrinsic
filter/sampler change from measured circuit evidence. Computation and all
artifacts remain cloud-only.
