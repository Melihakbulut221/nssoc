# New native trajectory for corrected power128 metal
Fresh nominal and leaf-select fault decks have passed exact source/adaptation
checks and native10032-vector OP transport. A new simulator process is started
for each case; older8074 and pre-power1288088 capsules are retained separately.
The original34ns/256bit/14182-column capture,604HBT5376MOS bounds, signal,
interface and diagnostic gates are unchanged. Native stages save actual
processes and every raw byte rather than restarting simulation time.
A saved checkpoint is not an electrical pass. Review requires full capture.
No supply voltage, geometry, R/C value, native model parameter or acceptance
threshold is changed by this lifecycle adaptation.
Full serial PHY, remaining physical clock/bias/supply boundaries, qualified
device-access/substrate/RF PEX and mainchip original-clock timing remain open.
