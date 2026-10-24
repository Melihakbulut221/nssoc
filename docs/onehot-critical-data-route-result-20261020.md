# Critical data buffer route: measured result
The completed route39293720171 preserved the original clocks, 5% derate and native topology checks. Routing DRC and disconnected pins are zero; 25 antenna nets remain. Fresh nominal OpenRCX with three cell corners is not qualified min/max RC or full-chip LVS.

| Corner | Setup count before / after | Setup WNS ns before / after | Hold count before / after | Hold WNS ns before / after |
|---|---|---|---|---|
| Slow | 9684 / 9691 | -20.665470 / -18.542956 | 5 / 6 | -0.431694 / -0.451715 |
| Typical | 7627 / 7619 | -7.882026 / -5.466296 | 7 / 9 | -0.372727 / -0.387717 |
| Fast | 3733 / 3917 | -3.799566 / -2.539953 | 19 / 17 | -0.325945 / -0.338548 |

All three worst setup values improved, but several counts and all worst hold values regressed. No timing closure is claimed. Native antenna nets fell from32 to25. This is evidence for inspecting changed paths, not accepting the candidate for production.

The new cloud-only critical-data-path-review retains the unchanged native report parser and all-corner metrics, with exact source-delta verification. It retrieves the immutable routed reports and compares the actual39243328773 baseline. No reroute, extraction, clock relaxation or local artifact is introduced. Next use measured max/min paths to choose setup repairs that also account for newly failing hold endpoints.
