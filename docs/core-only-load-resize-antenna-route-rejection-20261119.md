# Protected resized-driver route rejection — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44519671827 (head 614a0a8ccab89228478e255e92df9db1a323b66e, attempt 1) failed independent native geometry admission.
Artifact 14528307995 SHA256 b724b253cb6f0b2731a90ad9d2596aaea9c0336ba1c492d53ffa7c290afbdc4b; all 50 output hashes independently verified in memory.

Antenna now reports zero violating nets and pins, with an empty antenna report. DRT reaches zero DRC at iteration 23. However, native geometry finds eight Metal2 contacts: net912 against nssoc_sta_n_60783 (one), and nssoc_sta_n_54415 against nssoc_sta_n_60783 (seven). No disconnected geometry, unwired multi-terminal nets, or missing terminals is reported. The candidate remains rejected.

106664 instances and 103090 nets retain identity/connections; 103087 unaffected signal records and all 2113 clocks remain exact. 102971 native encoded paths were checked FIXED then ROUTED. Rejected ODB SHA256 4ea3593748463388944db28db453184655a2b9cb81c8a81972a2566358e004fb.

Next experiment starts from the verified eight-diode preparation ODB 8d1a34b991abf59c1e26a7e2ef119b3ee74f7bf82ddd96167b4e95814524e5ed, and routes only 60783, net912 and 54415. A cloud helper re-verifies the failed predecessor artifact and exact contact map. All other routes and clocks remain protected. Zero antenna, DRC and independent geometry are still mandatory before fresh RC and all-corner timing. No production closure is claimed.
