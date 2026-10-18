# Current cloud-only continuation

Read [the authoritative continuation](docs/cloud-phy-timing-continuation-20261018.md). All CAD, simulations, source and artifacts stay on GitHub. Local task workspace is empty.

Mainchip round4 run39115222502 passed 0 antenna / 0 DRT DRC / 0 critical disconnected. Exact-source RCX and final routed STA run39117700521 (378b1fd258c51ed1eaa8200e6f746cd409b0a29a) is in progress; preserve it and inspect native output before claiming timing closure.

CDR420 physical39116999945, planes39117334854 and fresh wholewire inputs39117796759 passed. The new receipt pins all physical files and 1186 terminals. Native model binding run39118454522 (source94789e90690b45b4a2ed643af3ea262bd2d5d041) is in progress via cdr-retimed-hybrid-v2-binding-cloud.yml for native420 model binding, preserving all12 fault controls and adding actual64um MOS support. Inspect its exact run and release. Next: fresh MIM-aware RC capture/audit/composition and original loaded waveform gates. Never reuse406 device identities or old RC counts.

TX fullwire run39112087217 remains in progress; preserve nominal and swapped-select trajectories. Full serial PHY, retimed sampler attenuation, closed loop, qualified RC and final setup/hold remain OPEN.
