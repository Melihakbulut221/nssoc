# Gen1/Gen2 single-lane 8b/10b development

This addition supplies a real synthesizable codec prerequisite at the raw PMA/PCS boundary. It does not implement comma alignment, TS1/TS2 scheduling or parsing, LTSSM, rate switching, Gen3 equalization, or a qualified low-rate analog PHY. The current SoC packet interface is unchanged; no link-up input is tied off.

## Interface

`soc_pcie_gen12_8b10b_encode` is combinational: byte `data_i`, `k_i` and explicit `rd_i` yield ten-bit `code_o`, `rd_o` and `k_error_o`. RD0 means negative; RD1 positive. The wire order is a,b,c,d,e,i,f,g,h,j, so bit0 is transmitted first and the Verilog vector is {j,h,g,f,i,e,d,c,b,a}. Unsupported K requests return zero, hold RD and flag error; a caller must not transmit them.

`soc_pcie_gen12_8b10b_decode` consumes an already aligned ten-bit symbol and explicit RD. It produces byte, K flag, next RD, code error and disparity error. Invalid-code data/K are deterministic zero. Code error takes precedence over disparity reporting. Next RD always follows the received 6b then4b sub-blocks, including invalid input; legal symbols received at the wrong disparity still decode and report that error. Special balanced sub-blocks 000111/111000 and0011/1100 require explicit handling.

`soc_pcie_gen12_codec_lane` owns independent TX and RX RD registers on separately supplied clocks and resets. Reset assertion is asynchronous, initial RD negative; reset release belongs to the caller in each domain. Disabled cycles hold payload and RD and clear valid/error strobes. An invalid TX K is flagged and not emitted; RX valid marks every supplied symbol, including flagged errors. There is no clock crossing. Four combinational cores can chain RD in one symbol-group cycle; the verification covers this but makes no physical timing claim.

## Sources and independent oracle

The implementation derives from [Chuck Benz's original permissively licensed codec](https://asics.chuckbenz.com/), retaining the full2002 notice and byte-exact upstream copies. The vendor derivative changes only module namespaces and the old identifier `do` (reserved by SystemVerilog). Exact upstream and derived SHA256 values are recorded in `third_party/chuck_benz_8b10b/provenance.json`.

The independent oracle is the256D/12K numeric table in [Rich Taborek/Amdahl's IEEE802.3z contribution, September9,1996](https://www.ieee802.org/3/z/public/presentations/sep1996/RT8b10b_codes.pdf). The cloud run re-fetches the exact18,141-byte PDF, verifies its hash, parses all268 rows and compares the committed numeric fixture. It does not obtain expected code words from the encoder. [AMD AM002's valid-character tables](https://docs.amd.com/r/en-US/am002-versal-gty-transceivers/8B/10B-Valid-Characters) corroborate the code-group convention. Running disparity uses the received sub-block rules in [ATM Forum af-phy-0162 R43](https://www.broadband-forum.org/download/af-phy-0162.000.pdf), not the presentation's ancillary ending-RD column.

The alternate .7 encodings are explicit: D17/D18/D20.7 use0111 at negative RD; D11/D13/D14.7 use1000 at positive RD. The other incoming-RD forms remain separately represented. Benz's encoder comment mentions D19 where its actual equations and the independent table select D20; the original comment is retained as provenance. Every1024 receive word is checked at both RDs against the independent table's complete legal set, including all alternate forms present in that table. No encoder-emitted-only roundtrip oracle is used.

## Cloud verification and limits

The workflow runs Icarus and Verilator on all1024 encoder requests (including488 invalid K/RD combinations), all2048 receive-code/RD combinations,2048 four-symbol chains and4096 independently generated clock/reset/enable/error cycles. Yosys synthesizes and checks both combinational cores and the lane wrapper. Nine actual RTL corruptions must fail the same Icarus checks. Full logs, source hashes, coverage, synthesis netlists and rejection evidence are retained in GitHub.

A passing result establishes bounded digital coding/state behavior. It cannot establish 2.5/5GT/s clock support, serial electrical compliance, training completion, main-chip connectivity or final setup/hold closure. Those remain separate work.
