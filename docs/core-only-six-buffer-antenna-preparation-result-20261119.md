# Six-buffer antenna preparation — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44543564994 completed successfully at d72f86c0b21a4fa58e8ba0c78ea909bccd49b732 (attempt 1).
Artifact 14539671194 SHA256: 0f19828dcb524691653a206c474ec42b9ef54294c0a18f969dac7f15f76955d1.
Candidate ODB: 942ddc27bced208cc806144b74ac4bc90a084bf25cc2c47366c29c4004b087e6.

ANTENNA_2577 and ANTENNA_2578 connect to nssoc_regiso_0_net. Total instances: 106672. Four added power terminals contact the correct rails; native rail removal is detected. All 103093 unaffected nonpower net records and 2113 clock nets are preserved. The affected net has six loads, below the existing maximum of eight. This is preparation only; antenna closure and timing are not yet established.

Next experiment routes only nssoc_regiso_0_net, locks encoded native routes of other nets, restores routing status, and requires zero router DRC, zero antenna violations, and independent geometry checks. Fresh RC and timing are required afterward. No frequency or electrical limit is relaxed.

## External I/O boundary
The user confirmed that package, PCB and attached devices have not been selected. External I/O production timing remains open; no board delays, loads, device models or interface speeds may be represented as approved. Internal routing and timing work continues independently. PCIe and Ethernet remain excluded from this production target.
