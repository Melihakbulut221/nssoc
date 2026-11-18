# Native diode-only reproducer

Prior isolation showed the antenna diode alone reproduces the failure while both original NMOS devices together complete. This test removes all transistor libraries, OSDI models and pad circuitry. It loads the identical diodes.lib bytes from the authenticated input capsule and tests the original dantenna hierarchy plus each original area/perimeter/corner diode component separately.

Geometry remains l0.64um,w0.48um: area0.3072,perimeter2.24,corners4. Each fixture uses125C,3Vreverse-to0V ramp20–20.12ns and50ns total capture; constant3V and0V controls accompany it. Same pinned ngspice47,KLU,Gear2,itl4=100,1ps,default tolerances,nativeDC solution. No diode parameter edit. Failure of any of12 captures makes the aggregate fail; all independent cases still execute and retain logs. Capture actual gate-source current, not an unrelated pad clamp current.

This reduced reproducer can distinguish native diode behavior from OSDI/device-library interaction. It does not qualify a production pad. Compare native simulator revisions only with precise binary/version identity and unchanged models. Main core route44337630426 remains independently active.
