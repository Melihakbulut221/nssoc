# Full serial integration remains a separate requirement

Verified against root source c9d6ea5b2e49d52e73c33d96dcb18db1324abf05 on2026-11-01. The current hw/soc/rtl/soc_top.v is67444 bytes, SHA256 b782a7fbe7b9ad5abb0db67bd132907d71e1ef43c9451b9befa2f356b77d4847. Lines262-270 expose external link/training/retrain status and an8-bit packet stream. Lines988-997 feed those external values into the packet controller. This is not an internally owned trained serial link.

The qualified [shared receiver front](pcie-shared-serial-front-v1.md), source17033684f3dfd0c760ac7cf64d2e1dc1a4b2fdb0/run41223635170, covers50 positive RTL tests, two compiled mutation detections and two production hierarchies. Its recovered clock/raw bits are explicit testbench inputs. The shared aligned raw-record path and existing normal consumers do not establish normative training/equalization interpretation, logical lane mapping, descrambler handoff, full LTSSM or soc_top serial connectivity.

The current mainchip routing job41270471645 preserves the original logical/clock records while repairing scoped signal routes and antenna diode connectivity. Its predecessor is the packet-interface SoC. A successful route/DRC/antenna result cannot by itself establish serial PHY integration. The analog CDR nominal screen and the complete clocked physical pipeline must also close independently.

The official [PCI-SIG Base3.0 catalog](https://pcisig.com/PCIExpress/Specs/Base/_3.0) was rechecked on2026-11-01. Its download still redirects to [member login](https://members.pcisig.com/site/login?return=/wg/PCI-SIG/document/8265). The existing request for authorized specification access remains pending. Public overview material is not treated as a complete training/descrambler correctness oracle.

The full objective therefore still requires the actual CDR/PLL/SERDES signal and clock sources, shared receiver and transmit paths, complete training/state ownership and packet-controller integration, native layout/RC verification and unchanged final multi-corner setup/hold/electrical limits. No green standalone test, metadata map, nominal analog point or packet-interface route substitutes for that integrated evidence.

## Current source check, 2026-11-14

At integration source `b6720274883620dcbf3607a2aa60cc7c7da53f5a`, `soc_top.v` has SHA256 `2695f6318f494bfa04eb7bafdcaccb2994d9dc072c127a30bfca78335510e217`. The external link/training/retrain inputs remain at line262; the synchronized status path at line1002 does not replace their external ownership. The training epoch transport now has [completed hosted qualification](pcie-training-epoch-ingress-20261031.md), but this does not close the semantic training owner or connect serial lanes into `soc_top`.

Current full-transistor LVS run43602758557 verifies the older packet-interface layout with SRAM interiors. Current route43591198141 and analog candidate43603972722 are separate experiments. Even if these pass, complete serial Gen3x4 integration, normative training/equalization ownership, new integrated layout/RC, and final timing remain required.
