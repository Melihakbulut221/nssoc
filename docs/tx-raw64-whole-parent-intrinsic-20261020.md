# Actual full-parent8074-device intrinsic model

This cloud stage uses the passed full-parent LVS database and every28582 terminal witness from39471428433. It exports raw device parameters without combining the5376 MOS fingers, retaining separately named AD/AS/PD/PS and finite contacts. The native census is589HBT,2560HVNMOS,1408LVNMOS,1408LVPMOS,504rppd,1477ptap and128ntap. All163 public ports and763 electrical nets must be preserved. Common bulk plus64 independent NWELL nets remain65 separate body nets, distinct from698 metal conductors.

Model-library files and contact conductance coefficients are pinned to the existing IHP commit. Fifteen corruption controls cover missing devices, named MOS junction/terminal/width/multiplicity changes, HBT size/C-E changes, resistor/contact changes, supply body shorts and cross-driver well shorts.

This emits an intrinsic development model only. Whole-parent RC composition follows successful native producer precision repair; every actual interconnect R/C must then be included. The older64 separate-driver simulations still have ideal driver/core interconnect and cannot substitute for this complete parent. Native substrate spreading, device-access and RF qualification, full serialPHY and mainchip acceptance remain open.

## Recorded first conversion failure

Run39482444225 exported and checked all8074 native devices,28582 terminals,163 ports and65 body nets. It then rejected all504 actual rppd records because the new converter incorrectly required ps>0. These are b=0 non-meander resistors with native ps=0. The pinned PDK uses leff=(b+1)*l+(2/kappa*weff+ps)*b, so bend spacing does not apply. The corrected candidate requires w/l>0 and the actual b=ps=0, preserves every native parameter and adds a negative-spacing rejection. No physical geometry or model value is changed.
