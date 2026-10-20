# Isolated native total-load precision repair

Diagnosis39479905356 reproduced all698 serialized native totals with the actual MagAtof binary32 conversion followed by binary32 accumulation. Four corruptions were rejected. P_avdd differs by+4.092605ppm and P_avss by-3.067328ppm from sums of the actual source records. The original3ppm gate correctly rejects them.

The new cloud run restores all2057 original source files from the immutable migration archive, checks every hash, applies the frozen coupled-v2, precision-v3 and area-v4 patches and rebuilds the original producer. A second private source tree changes only the native total-capacitance field and its downstream rg_nodecap storage from float to double. Every compilation unit is rebuilt; no stale ABI objects survive. Intrinsic capacitance distribution, R/C coefficients, geometry, tolerances and device rules are unchanged.

The baseline rebuild must reproduce both the original137221R/98241C records and the two rejected total witnesses. The repaired producer must emit exactly the same R/C records, pass the original independent raw auditor and reject all13 original corruptions. Otherwise the run is rejected and raw evidence is retained.

This remains a private unqualified extraction runtime. Native model composition, substrate/device-access spreading, RF/parasitic/PVT qualification, loaded serial behavior, fullPHY and mainchip timing are not proved by this repair.
