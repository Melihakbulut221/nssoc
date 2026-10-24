# Cloud checkpoint: native input configuration and prefix power delivery

Run39639250513 restored the actual input package on a new hosted runner and instantiated LibreLane3.0.5 MainchipCompletedPostroute. All120 compared model, clock, uncertainty, derating, library, RC and flow settings matched the original complete native configuration. Only the analysis directory metadata differs. The shared-reader namespace failure is retained and fixed. No completed route, RC or STA acceptance is claimed by this input-only pass.

Run39641391754 observed the exact normal power128 raw prefix from2.000292307ns to4.798637531ns:6379 active complete rows, all14182 original columns, original partial tail retained in its source. Eight malformed-prefix faults were rejected; the original full-capture reader still rejects this prefix.

At actual physical supply terminal planes, the lowest AVDD was2.044145921V, a0.455854079V external-to-local drop. The highest local AVSS was0.280338929V. Lowest DVDD was1.141408016V. These are diagnostic findings with remaining supply drop/ground rise, not full electrical acceptance. The old8074 full capture has a different observation window; no fullwave A/B pass is inferred.

Native work continues only on hosted runners:
-39631640578: mainchip ninth continuation, from the exact saved eighth process.
-39637767590: whole845 PLL, continuing820.364ns toward the unchanged1us target.
-39640657545: normal power128 TX second continuation, from4.798637531ns.
-39640662925: swapped-leaf-select power128 TX second continuation, from4.827412540ns.

Both TX stages use7200 host seconds within their existing180-minute limits; unchanged simulator/circuit/oracles still require complete34ns captures. All original native processes and prior bytes remain preserved. Do not cold-restart or duplicate live handles.

After mainchip actually completes, dispatch mainchip-postroute-review-cloud with its completed DRT descriptor and the passed input-package39635867954 descriptor. The workflow independently rechecks geometry/fixed clock, exports fresh DEF, and measures antenna/disconnection/freshnominalRC/three-cornerSTA. Full PHY, final physical route/timing, qualifiedRC and production signoff remain open. The local project directory was verified empty; no local CAD, tests, native archives or persistent workspace files were created.
