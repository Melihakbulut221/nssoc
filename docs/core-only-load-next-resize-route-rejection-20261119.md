# Two-driver route rejection and measured-neighbor repair — 2026-11-19

Rejected run: https://github.com/Melihakbulut221/nssoc/actions/runs/44507049713
Head b754ac1dfec7a00a74586c857a5a0041e0eee14f, attempt 1, failure.
Artifact 14524137030 SHA256 b8487902a4f95fe13a022a1dc33bc93a348ee0b6e1f32218d4af24fba45798fd. All 45 output hashes verified independently in memory.

DRT reached zero DRC at iteration 24, but independent native geometry rejected 32 inter-net contacts. They involve only four previously fixed neighbors: net2135 (against 63198/62749), net2194 (against net2774), net5510 (against 18115), and net5513 (against 28565). Metal2/3/4 are involved. No disconnected signal geometry, missing terminal geometry, or unwired multi-terminal nets was reported. 103080 unaffected non-power DEF records and 2113 clock nets remained exact; encoded FIXED/ROUTED checks passed for 102964 nets. Instances and connections remained 106656/103090.

Antenna is also open: nssoc_sta_n_60783 has two violating sinks, 61075/B and fanout935/A. Metal5 cumulative ratios 289.88/296.35 and TopMetal1 ratios 304.13/310.60 exceed 200. Do not treat DRC zero as a clean route or production approval.

The next candidate starts again from the verified pre-route resize ODB 756fdc34ff3710eaf3341548c9c06815866d76ce5215c60e87c511eefddd6286. It opens exactly the original eight incident nets plus the four measured neighbors, preserving all other routing and clocks. A cloud admission helper rechecks the rejected artifact and exact contact map. The same DRC, antenna, geometry and identity gates remain mandatory. If antenna persists after geometry repair, targeted antenna protection and fresh RC/STA remain required. No constraint relaxation or timing closure is claimed.
