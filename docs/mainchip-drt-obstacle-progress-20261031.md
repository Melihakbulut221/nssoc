# Mainchip observer progress, failure preservation and 3600 s read-only budget

The exact original observer source `65e620dc413389fffaa8389e4abdfc17cfbf4ecf`,
[run 41236517605](https://github.com/Melihakbulut221/nssoc/actions/runs/41236517605),
failed the native `obstacle-endpoint-observation` command at 1200.192017743 s
with `elapsed_limit`, return code -15 and complete process-group SIGTERM cleanup.
The last measured group RSS was 1,135,636 KiB; host available memory was
14,116,180 KiB. The terminal 12 GiB cgroup recorded a peak of 1,157,533,696 B
and zero max/OOM/oom_kill events. Its finalization checks completed.

The last saved native progress completed 142 of 373 endpoint nets. The next
sorted endpoint was `VGND`. That endpoint belongs to only one selected report
marker (`VPWR` belongs to four). The previous source did not record substage
progress, so the actual slow operation inside that endpoint is unknown.
Neither a marker spatial index nor repeated clock encoded-path serialization
is asserted to be the observed cause. Geometry algorithms remain unchanged.

All 68 members of the original failed observer artifact were authenticated and
classified on GitHub by [corrected readback 41239406705](https://github.com/Melihakbulut221/nssoc/actions/runs/41239406705).
Its immutable complete derived proof is
[`e8609629`](https://github.com/Melihakbulut221/nssoc/tree/e8609629eb3f6f0753d2c6f66dcb05f3c73be0f9/docs/evidence/mainchip-obstacle-failure-readback-41239406705):
83 files, 6,854,257 B; subtree `64c9f91d41aa8d1c679c8699235bbdf96ef0106f`;
receipt SHA256 `af3c10b61c83c98b55c9df8093d766d8382fd854b1c38c91976f81447ad92f8e`.
Full raw logs and every emitted derived byte are retained. An internal UTF-8
BOM before one log timestamp is accepted only as framing; all reconstructed
file sizes and SHA256 remain mandatory. No native payload was acquired locally.

## Narrow successor

- Complete failure publication is attempted after terminal-result preservation
  and **before** rethrowing the original error. The old `finish_record` raised
  the primary error before the publication call, explaining the empty reserved
  release despite complete cloud artifact retention. Publication/save errors
  cannot replace an earlier primary error; no upload retry or overwrite occurs.
- Native substage begin/end and each 1024 completed-item checkpoint are appended
  to a JSONL journal and an atomic latest record. Stages cover database load,
  native/diode census, identity, encoding, wire projection/shapes, ITerm/BTerm
  pins, special wires and the independent block terminal census.
- A nonterminating built-in Python stack snapshot is emitted every 60 s and
  cancelled during native finalization. The owning process supervisor still
  enforces its finite wall-time and resource limits.
- The explicit read-only native time budget becomes **3600 s**, and the outer
  owned-container deadline becomes **3900 s**, within a future 90-minute job.
  This changes computational wall time only. Group RSS remains 10 GiB, hard
  container memory 12 GiB, host MemAvailable minimum 2 GiB, swap zero, CPU quota
  two CPUs and pids.max 4096. Original source files remain unchanged.
- The inherited runner allows only 1200/14400 s. A small source-pinned adapter
  changes that one guard to exactly integer 3600, proves reverse source equality,
  and clones the original command validator with an isolated `SECONDS=(3600,)`.
  Every other runner/validator operation and resource check remains identical;
  the original supervisor receives 3600 explicitly and its module defaults are
  untouched.
- All 434 Metal2 Short occurrences, all 373 endpoint names, complete pins,
  transformed MPin multiplicity, ordinary/special wire shapes, full digest
  stream, protected/cleared manifests and 154480/143820/1351 census gates remain.
  A hosted AST comparison against the exact protected original native source
  proves `native_scope` differs only by telemetry calls and its trace argument.

Fifty source controls retain all forty previous checks and add progress,
partial-journal, unchanged-geometry AST, nonterminating stack/cancellation,
exact-budget/resource, synthetic command-pipeline and failure-publication
checks. They are source controls, not native observation or physical acceptance.
This source has native authority **false** and a controls-only workflow.
No observation, reroute, STA or physical acceptance is authorized by this commit.
A later explicitly reviewed activation, successful own-source controls and
independent empty exact-source result reservation are required for one actual
read-only observation.

The existing pinned OpenDB Python typemap materializes `dbSet` with one linear
iterator pass; no quadratic Python iterator is inferred:
[pinned primary source](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/odb/src/swig/python/dbtypes.i).
No speculative geometric optimization, larger memory limit or relaxed electrical,
DRC, antenna, timing or topology acceptance was introduced.
