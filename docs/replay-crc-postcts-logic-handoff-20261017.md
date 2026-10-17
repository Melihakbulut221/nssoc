# Exact replay-CRC post-CTS logic handoff

The replay CRC placement run39042752404 (sourcea39447804f23c1cb7d0bdd4d6fb49f5ceac01c9f) feeds native repair39052168254 (source2f32b51eec3d0dfc0c5d695c1aec921044e6a90b). The new replay-crc-logic-cloud job waits for that exact currently live repair. It never restarts the source when an observation budget expires, never accepts another run or attempt, and refuses a terminal unsuccessful source.

After successful repair it verifies both immutable-source workflow identities, release summary/parts hashes, all restored file hashes, exact saved-state netlist paths and each state's ODB hash. It re-runs all six source proofs plus protocol and native-boot binding against the current unchanged RTL. Controller commit labels may differ only when every per-module source hash is identical; all other proof metadata must match. The repair's own current-source revalidation is checked too.

The actual CTS and repaired netlists then undergo the existing native ECO controls and full retained-cell equation/state proof, including positive-buffer contraction and combinational clones. The proof binds the fixed standard-cell Liberty and both FUNCTIONAL SRAM interface models. It does not establish SRAM transistor interiors, physical connectivity, initialization, CDC, delay, analog PHY, routing or timing signoff. No previous successful banked-netlist proof is reused as acceptance.

This successor is prepared while the native repair runs. Its result remains unknown until its real source-bound proof completes. All execution, logs and output archives remain in GitHub Actions/releases.
