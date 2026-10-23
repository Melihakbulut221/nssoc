# PLL control-wire current diagnosis — 2026-10-23

Run39873653454 completed the original1us/3,201,410-row capture analysis, preserving all original acquisition and cycle results exactly. Acquisition remains rejected. This was a read-only diagnosis; no new SPICE activation or weaker gate.

The modeled control network carries current. In the final900–1000ns window, the source-output wire averages+19.184768uA and the sink-output wire-16.998670uA, under the declared leaf-to-interior sign convention. The upper and lower bias-resistor wires average+47.223124uA and-48.026965uA. These are currents through actual modeled metal resistors; they are not intrinsic MOS channel-current measurements.

The last100ns window's integrated net wire charge is1.04838846e-13C. The interior capacitor charge change is1.04838837e-13C and the quadrature residual is9.1730e-21C. The coarser-sample quadrature difference is-7.5020e-20C. Original adaptive samples and actual included window endpoints are preserved; these numerical comparisons are not certified integration error bounds or qualified PEX.

After300ns, successive100ns windows repeatedly alternate roughly+/-1.0487e-13C net wire charge and two nearly repeated sets of pump/bias wire-current means. This suggests persistent closed-loop oscillation rather than simple continued settling; it does not by itself prove a particular pole, pump polarity error or intrinsic VCO tuning curve. The unchanged original acquisition result remains the authority: final feedback110.440673637MHz against100MHz and phase span9.1903191769ns against50ps.

Next diagnosis should correlate the preserved exact control-column cache with the original feedback-cycle/phase records and actual PFD wiring before selecting a loop/filter or device change. Do not repeat the130GB native capture or merely extend its duration without a design-based reason. Native columns are archived on GitHub only. Any candidate then needs the full original acquisition and terminal checks, plus corresponding fresh physical/extraction evidence.

See docs/evidence/pll845-complete-wire-current-results-20261023.json for immutable assets, all original-sample windows and output hashes. Full serial PHY/mainchip integration and qualified physical parasitics remain open.
