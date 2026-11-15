# Local RX lane next-state experiment

Candidate RTL SHA256: dbdc7a33a7b118f3c96e114a477135c9bb1ef82ebd41800229366935dde202af. Qualification run 43659632740, immutable source da44f20d6af407cdfdd5e353ce36536067dccde7; exact formal job132645821996 and traffic job132645821805. The build gate validates completed success, source digest, case counts, mutation failures and log hashes. A failed or pending qualification must not start CAD.

SOC_PCIE_RX_LOCAL_LANE_NEXT is opt-in. It replaces a shared lane D bus with local rotate/hold/restart logic under keep_hierarchy; the asynchronous master reset covers between-edge reset pulses. No additional cycle or relaxed timing contract. New source requires independent mapping, boot, placement, route and STA. Old source placement hold-zero evidence is not transferable. Full PHY and production qualification remain open.
