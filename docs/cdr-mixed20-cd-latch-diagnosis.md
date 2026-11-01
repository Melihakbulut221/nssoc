# Mixed20 same-time C/D latch and bias connectivity

Run41284522943/source7e4277e5d0d6ab629541cf4f00905762fcb6459f succeeded using only immutable derived JSON from native41282867236 and full-wave diagnosis41284095439. Full14-file proofdfa424f2d2bf58bf35adcef6bec6c8f9fb1d6604, docs/evidence/cd-latch-diagnosis-41284522943. Four original failure events retain all124 simultaneous HBT identities, terminal voltages and collector currents; complete native500 topology is authenticated. Fourteen is a file count, not a synthetic test count.

At the worst original sample3.1ns, cp1.398632394V andcn1.177041289V:
* C slave-input differential is-139.170264mV; sampled output is-12.305347mV when positive is expected. Slave differential collector current-4.198178mA, total5.166561mA.
* D slave-input differential is-156.446528mV; sampled output is-18.856008mV when positive is expected. Slave differential collector current-4.535684mA, total5.217070mA.
* C/D slave-data-clock totals5.005164/5.003524mA; slave-hold clocks33.734770/31.135065uA. Master-hold clocks carry5.635939/5.629088mA while master-data-clock totals46.110003/45.115736uA.

The slave-input sign is measured first-minus-second B terminal of an inverting differential pair; it must not be equated directly with the required output sign. These139–156mV values are slave inputs/master outputs, not master inputs. C/D master-input differences107.273204/206.277964mV are separately recorded.

## Actual clock emitter connectivity

| Block | Native emitter cluster | MOS drain neighbors | Shared MOS gate cluster | Diode-connected reference |
| --- | --- | --- | --- | --- |
| C master |124|32,33,34,35|123|40|
| C slave |127|36,37,38,39|123|40|
| D master |38|3,4,5,6|25|11|
| D slave |30|7,8,9,10|25|11|

Each listed drain-neighbor MOS is sg13_lv_nmos withW36um,L0.3um,m1,ng1,ad/as12.24um2,pd/ps72.68um,rfmode0. References11/40 areW8um,L0.3um. C followers/buffer bias MOS30/31 andD1/2 also share the respective gate cluster and areW53.335um. These are complete native net-cluster connections, not collapsed distributed-RC nodes or proof of simultaneous MOS current.

Actual all-time HBT checks remain in native report453667B/SHA256096476d0dc446b3e16ad5e2263b5d73f5b4be43c8ccc031bbdd9cfda6d20b643. Master-data clocks Q61/Q62 have minimumactiveVCE0.407017/0.408186V andQ115/Q1160.410240/0.411376V, close to the unchanged0.4V floor. Slave clock minimumVCEs are higher; all original predicates passed for this rejected intrinsic candidate. This does not predict a new bias setting will pass.

## Next controlled circuit question — superseded by model-domain finding

Pinned native-model audit 41285573717 found 42 of 50 MOS definitions outside the stated 0.15–10 um width range; all current ng=1. The unexecuted W36->54 um single-finger trial is superseded and MUST NOT be dispatched. Width is passed through as w=w in captured wrapper branches; changing ng alone is not a demonstrated model-domain repair. First join all50 original MOS to actual physical gate geometry and verify the full core nf/ng mapping, then qualify a physically consistent split-device/finger implementation preserving total original W/L and bias. No simulation/geometry change or acceptance occurred in these audits.

See [model-domain audit](cdr-mos-model-domain-audit.md). The prior W36->54um trial was only a hypothesis and never dispatched. All six-stage gates including failing A, full device stresses, original stimulus/load, independent geometry/DRC/LVS/freshRC and final integration requirements remain mandatory.
