# Native mainchip geometry gate after saved-process routing
The running detailed-route process must not be restarted to run this audit.
This independent read-only workflow restores the exact152762-instance fanout
candidate and the actual saved-global database from immutable receipts.
It reuses the unchanged native ODB topology/geometry verifier and its four
corruption controls, then the exact fixed clock wire verifier. Every original
master, pin, position, orientation, public pin geometry, net and NDR is compared.

On initial push it audits candidate-to-global preparation. That result cannot
prove detailed routing completed. To audit a completed detailed route, dispatch
with source_checkpoint containing run,attempt,group,source_head,controller_sha256,
summary_sha256 and parts_sha256. The controller requires the selected run to
be terminal/successful, actual route_complete=true, no saved unfinished process,
the frozen DRT controller and exact original global ODB, runtime and clock
contract. It restores the real detailed-route.odb and native completion record.
A matching instance count alone is never sufficient.

No original gate is relaxed. Native DRC, antenna and disconnected pins,
fresh nominal RC/three-corner20/4/8/8ns STA with5percent derate, qualified RC,
full-chip transistor LVS/DRC and full PHY remain separate required work.
All native work and retained evidence are on GitHub-hosted runners.
