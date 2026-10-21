# Completed-route electrical and timing repair

The exact route measured by run39654204345 has0 routerDRC and0 critical disconnected pins, but563 antenna nets/626pins. Original-clock nominalRC produced9671setup/3hold violations at slow,7358/9 at typical,3967/31 at fast. The exact native diagnosis39657466517 identifies large data-cell delays on the Ibex path and PCIe link-up paths, plus PCIe RX-valid and Ethernet SRAM hold paths.

The new cloud workflow consumes the exact completed ODB, original netlist/SDC, fresh143338-net SPEF and resolved configuration. Before any mutation, native OpenROAD must reproduce all six worst slacks within1ps. The previously qualified native electrical/setup/hold algorithm now consumes these new actual routed loads: repair_design, setup buffering/sizing and positive hold buffers. No clock period, uncertainty, derate, slew/cap acceptance or endpoint waiver changes. This is another measured physical optimization iteration, not proof that the algorithm will close all violations.

Native geometry/equation/fault controls preserve original152762instances,20SRAMs, clock-pin geometry, fixed PCIe clock route, supplies and external interfaces. Actual intermediate databases and failures are retained. Any candidate must subsequently pass routing, antenna repair, freshRC and all-corner STA. Optimizer estimates, source-binding controls and a green execution job are not final timing or fullPHY acceptance.

## Native crash and controlled retry

Run39661771876 reproduced all six baseline worst slacks within1ps, then saved an electrical-repair database before SIGSEGV in BaseMove::upsizeCell/LibertyPort::capacitance during setup. The actual failure and intermediate hashes are retained. No candidate was accepted. Retry uses one thread and one repair per pass, with exact native version logged. This tests a stale-path/concurrency hypothesis; it is not a confirmed bug fix. All endpoints, iteration policy, original constraints and physical/equation controls remain required.

Upstream [issue10210](https://github.com/The-OpenROAD-Project/OpenROAD/issues/10210) reports a similar SizeUpMove crash but does not prove our cause. [Issue9781](https://github.com/The-OpenROAD-Project/OpenROAD/issues/9781) documents buffered-driver cache invalidation and multithread nondeterminism; it motivates the controlled experiment, not a waiver or assertion of equivalence.
