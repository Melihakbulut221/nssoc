# Continue the actual full-terminal PLL process without duplicate archive disk copies

Run 39370629792 continuation saved a valid native process and unchanged previous
waveform prefix, but reached the disk guard after only 0.014 seconds of supervised
execution. It had 36,213,374,907 waveform bytes, 71,302,311,936 free bytes and a
72,426,749,814-byte archive reservation. It did not complete the 1 us capture or
prove lock. The immutable receipt and 31 archive parts preserve every native byte.

The output packer already writes one gzip stream directly to ordered parts.
The host guard incorrectly reserved twice the waveform size rather than budgeting
one archive of the entire output tree. The replacement budgets every source file,
8 KiB per entry for tar/PAX headers, one percent worst-case compression expansion,
and an additional 8 GiB for checkpoint images, native growth between polls and
runner activity, with a 12 GiB minimum. It does not assume a favorable compression
ratio. Input restoration also reads the already fully hash-verified parts as one
stream, avoiding an extra complete concatenated compressed file.

Only the exact prior controller SHA256
185b78aa506cf5fbd84d171ac58ddc5bf3c7e415f91139dbbb1fbe320c05f4f3
may migrate. Seven explicit reversible source edits prove the controller change
is confined to host storage and its provenance. Every other recorded parser,
physical-model and native-method digest must remain identical. The current
controller and helper are hash-bound in the migration manifest. Current-revision
continuations require the exact complete method dictionary.

Cloud controls exercise the ordered compressed-stream round trip, truncation,
the observed reserve trap, exact legacy/current method maps and five altered-map
rejections. The original source-delta verifier, full-terminal reader controls,
native prefix integrity and all physical/solver/acquisition contracts remain.

Workflow pll845-storage-continuation-cloud requires the immutable saved-process
descriptor. It must never cold-start the oscillator in place of continuing the
saved trajectory. The native 1 us / 0.3125 ps analysis, 1694 terminal vectors,
845 devices plus four contacts, source ramps, loads, solver and both final
100 ns acquisition windows are unchanged. This is storage repair, not PLL lock,
device safety, qualified extraction, x4 PHY or mainchip acceptance.
