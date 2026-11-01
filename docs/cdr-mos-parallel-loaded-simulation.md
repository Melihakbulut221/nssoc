# PD650 expanded-MOS loaded simulation — isolated binding

PD650 actual transient job41288195752/source d638e0e3cd15a0ee930212c27ab1f238b5085237 is live in native preparation/execution. Independent empty release430445706/tagcloud-results-41288195752-1-cdr-sampler-load. Same original mainchip41270471645 remains live. Previous41287653458 is TERMINAL PREPARATION FAILURE, not running and not an electrical waveform result. Do not restart either live run on observation timeout.

## Corrected native preparation failure

Run41287653458/source030ef6022a00fde8bfc787690c1ce2ada0044963 reached actual candidate preparation but failed before the simulator command. The adapter made a shallow copy of the numerical namespace, then overwrote bind_native in the original dictionary. The frozen baseline binding_controls function retained that original globals dictionary and therefore called the expanded650 binder on the500 baseline input. The exact-candidate check correctly refused it. There are no electrical wave results for this run.

All native outputs were published to release430442514. Full113-file proof10157a329e4d101a7af822b1105ebea847fe4bc5,11047172bytes, receiptSHA2564c24b198ae919a30d6436b1241ad8684f193c5b15e48f086743b6bc1cd71f8c7 preserves full derived/source/log records and complete release/index/part metadata. Native archives remain on GitHub only.

Fix d638e0e3cd15a0ee930212c27ab1f238b5085237 creates the candidate namespace as a separate dictionary before installing candidate callbacks. The original frozen functions retain their original unmodified globals. Explicit ownership checks protect the original binder. The new regression invokes the SAME compiled binding block and namespace factory used by native preparation; two independently created candidate namespaces and the original baseline namespace are all checked.

Controls41288015065 passed with actual_compiled_binding_block_exercised:true, isolated_namespace_factories_checked:2 and baseline_namespace_unchanged:true. Full61-file proof08fbd45956809eb9c2e9e8e2e716404a7dbaaa40,5725586bytes, receiptSHA2567812fa463ae5ecd011ad40c044a678521c293c67cc320ba8db01569400cd222a. Synthetic source fixtures remain source tests, not native simulation proof. Earlier controls41287453836 verified standalone components but missed this runtime-namespace interaction; their successful result is retained with that limitation. Earlier missing-dependency failure41287229546 and its15-file deficit remain preserved.

## Preserved scope and electrical gates

The same actual published model SHA2567787330b1bd617a1da93ca6cce0c1b4b3d874a4299cde70733f32fd9fc0b4150 is derived from authenticated original fresh-RC inputs, mixed20 resistors and explicit200-unit MOS transformation. Every original500 binding and650 candidate card/terminal/parameter, all original planes/aliases and unchanged non-MOS groups are checked. Each of50 MOS origins keeps its totalW/L and exact four nodes.

Qualification preserves original21 resistor-mutation refusals,5 archive refusals,13 baseline binding refusals and2 equivalent-unit spellings. It adds12 candidate-binding refusals and4 projection refusals.200 MOS units,192 tail units,42 original tail identities and16 original instantaneous-sum groups are covered. There are1301 unique vectors:977 voltages,124 HBT currents and200 MOS currents, saved in11 commands. Every original voltage/HBT vector retains identity/order.

Original preparation/measurement orchestration function bodies remain unchanged. Only five explicit block substitutions are allowed: deck MOS cardinality50->200, measurement cardinalities50/42->200/192, and threePD500->PD650 display/status strings. Reversing these reproduces every other original executable block byte. Measurement block SHA25612a33663c5ec9273a1b6a2ab4269fd703d2dd032f1fe0f100d14f7dedec174dc and deck34ba2b399b5a02de4ecb747a3e16d3f193f3b651b51ab1b139e75818df4c9f8e are unchanged by the namespace fix.

UI125ps, original externalclock/stimulus,10ohm source resistors,150fF sampler/50fF XOR loads,100mV sampler/XOR validity,37.5/75ps limits, phase/VI, strict124HBT current/headroom/voltage predicates, all200MOS voltage/current predicates,16stage0.5mA instantaneous-sum thresholds and7MIM voltage gates remain mandatory.

## Active actual attempt

Run41288195752 has its own successful source-controls job and independent exact-source release430445706. Reservation proof5c4f21f4273e0bd87b6dcce1fcebe61cdc89498f has5files/18410bytes, receiptSHA25608a656087e7d5c07ec273762d3d3bb9488901c088818f651549595f640233b53. Observe this SAME run until terminal; the combined preparation/execution step does not prove an internal subphase. Preserve all native and derived output, including failures. Confirm actual capture1301, all200MOS/192tails/16groups/124HBT/7MIM and original gates before interpreting a pass/rejection. Original engine runtime budget1200s is distinct from electrical timing limits.

The candidate retains old distributed wire RC. New geometry/contact/routing, independent schematic, fullDRC/LVS, fresh extraction/rebinding, PVT/closedloop, full serial PHY integration and final chip setup/hold remain open. Mainchip41270471645 separately routes the packet-interface SoC. All native computation/data stays in cloud; local workspace and project temporary files remain empty.
