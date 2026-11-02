# Run guarded PCIe tests from the repository runner

Historical general RTL job125454372217 in run41496973308 failed before simulation for Makefile.pcie_shared_serial_front and Makefile.pcie_training_epoch_ingress: Explicit protected sources required. The runner discovered the guarded Makefiles but supplied neither their explicit source lists nor named test modules. The failure log is preserved with this change. Its1203 passing tests do not make these missing suites pass.

The root runner now delegates those two suites to an explicit hosted root driver. Frozen Makefiles, DUTs, oracles and standalone branch/release guards are unchanged. No environment branch is spoofed, no original pins function is replaced and no test is exempted. The driver binds the actual checked-out source to GITHUB_SHA, verifies the complete protected closure and uses the original runtime, pinned vendor FIFO, source-list helpers and strict XML reviewers.

Shared-front coverage is all original positive Icarus cases: four front tests at depths4/8/32 plus eleven event-composition and two barrier tests at depth32,25 tests total. Epoch control/ingress coverage is six controller and four ingress tests at each depth4/8/32,30 tests total; epoch width remains2. Each case compiles separately, runs actual simulation, requires the exact named tests, positive simulated time, no errors/failures/skips and successful process exit. Fresh output directories and separate binary/XML paths prevent old results from satisfying the run. The generic module completeness check now recognizes these explicit dispatches.

The original standalone two-simulator, mutation and hierarchy campaigns remain distinct and unchanged. This normal root Icarus regression does not replace their broader qualification or claim full PHY, chip integration, layout or setup/hold acceptance.

Two existing root differences from historical protected packages are recorded exactly: the Gen12 root controls workflow already differs, and raw32 align has exactly default_nettype none/wire guards added. The new admission requires their exact current hashes; the RTL difference must reverse byte-for-byte to the original hash by removing only those two directives. All other original protected bytes remain exact. The existing Gen12 root integration manifest receives only the new runner hash; its implementation, test dispatch and controls remain intact.

Before integration, run the focused cloud workflow at its exact approved source. It runs source and XML rejection controls, existing Gen12 root controls, then both suites through scripts/run_cocotb.sh. Derived logs/JSON/XML are separated from native simulator images, and failures are retained. Current source publication alone is not a passed RTL run.

## First focused control failure and correction

Run41518536751 passed122 new root binding/XML refusals but stopped before RTL because the older Gen12 root integration manifest still pinned the pre-nettype-guard aligner. Its frozen source-reuse proposal also identifies the original bytes. The failure is preserved; no RTL pass is claimed.

The root Gen12 adapter now pins the actual guarded file. It proves its exact current hash and reverses only one default_nettype none and one default_nettype wire directive to the original hash. It invokes the original byte-exact source checker with a separate temporary validation view and independent function globals; neither the checker module nor the working tree is modified. Original manifests/proposal/source provenance remain untouched. Actual compilation and simulation use the guarded root RTL. Missing directives, an extra byte and a changed module body are rejected; the complete original27-source structure check runs on the canonical view. This is an explicit exact-byte root integration proof, not permission for arbitrary RTL differences.

## Complete sparse root discovery closure

Run41520194928 at sourcec74a5834c1ceb83e3d8b13733dbbc78abe18cd19 passed the corrected source controls and actually simulated all25 shared-front and30 epoch-ingress tests. Both root commands nevertheless failed their unchanged global completeness guard: the focused checkout omitted scripts/check_soc_memory_parity.sh and .github/workflows/checks.yml, which establish the existing separate native memory-parity job. The full derived artifact, every XML, output log and result are retained in docs/evidence/pcie-guarded-root-sparse-failure-41520194928.json.

The current protected closure now includes both real parity-discovery dependencies. The workflow already materializes every protected file. No runner completeness logic, skipped-module list, test, RTL, parity command or frozen package was changed to hide the failure. The focused run does not execute native memory parity and must not claim it passed. Rerun both actual PCIe groups through the unchanged root command before integrating this adapter.

## Actual55-test root pass and affected Gen12 regression

Run41521054837/sourcec574444973148615ea91a192bbcd85d26ef73890 completed successfully. All11 XML invocations authenticated:25 shared-front and30 epoch-ingress actual positive tests, zero errors/failures/skipped testcases. Root completeness also passed; each filtered invocation explicitly reports the existing separately owned native memory-parity module as1 skip, and this focused job does not claim memory parity execution. Full source controls, XML, logs and results are preserved in docs/evidence/pcie-guarded-root-pass-41521054837.json.

Before root integration, the workflow now also exercises all33 Gen12 CDC tests at depths4/8/32 through the affected canonical source-review adapter. No RTL, test body or acceptance predicate changed. The final expected functional scope is88 Icarus positive tests across17 invocations, with the separate memory-parity ownership still explicit. This remains functional regression, not full serialPHY, formal CDC signoff, analog or physical acceptance.
