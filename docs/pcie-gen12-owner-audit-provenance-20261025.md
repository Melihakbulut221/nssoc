# Gen1/2 owner audit provenance and current boundary

The frozen record-transport document references an older owner-gap audit. Its two exact source files are now present in the same evidence directory so the reference resolves. The preserved audit describes source77d16d44 and is historical: its pending receive-chain status must not be used as the current result.

Current root evidence separately records the accepted raw32 RX chain in [its hosted receipt](evidence/pcie-gen12-raw32-rx-native-pass-20261024.json). The complete per-lane192-bit training-record transport passed run40169233322 at sourcec5bf80cb, including the Icarus/Verilator and mapped oracle. See [the actual native proof](evidence/pcie-gen12-training-record-noshare-native-pass-20261025.json). This preserves uninterpreted raw fields; it does not qualify a TS1/TS2 semantic owner.

The remaining integration boundary is still the common link-training owner: per-lane recovered-clock record CDC, negotiated lane mapping, actual PHY rate/electrical-idle/equalization completion, Gen3 training formatting and coordinated packet/reset epochs. These have not been implemented or accepted by restoring the historical documentation. The three analog paths and final chip routing/timing remain subject to their separate measured gates.

The existing frozen files and their source manifest are unchanged; this is a documentation dependency repair only. No RTL, workflow, test or native simulation was run.
