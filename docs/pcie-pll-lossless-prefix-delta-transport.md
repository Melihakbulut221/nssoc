# Lossless native prefix/delta transport

This transport is qualified independently on branch codex/pll-lossless-prefix-publication.
It is **not connected to the production PLL controller or completed-capture reader**.
No native simulation, activation, acquisition acceptance or full PHY acceptance is
claimed by the transport test.

PLL run 40041871167 finished its native step but exceeded the hosted job's 6 hour
limit while republishing the complete ordinary raw archive. The terminal
check-run annotation confirms that timeout; 423 partial release assets
(113548197888 bytes) remain preserved. No summary or parts manifest was published.
Those pieces must not be treated as a complete native capture.

## Exact retained data

cloud_native_prefix_delta.write_capsule() requires a stopped process and a
qualified existing sparse-prefix plan. It copies every original auxiliary file,
preserving contents and modes. The raw file is represented by two real extents:
[0,hole_start) from the current head and [hole_stop,current_size) from the
current tail. The middle remains in the immutable prior archive, identified by
the source descriptor and full raw/payload hashes.

The native-lossless-prefix-delta-v1 format is explicitly distinct from an
ordinary full-raw archive. Its manifest records every original file, both
extent hashes, source/plan and expected full logical raw/payload hashes.
capture_chunks() verifies every byte of the complete immutable source before
accepting reconstruction. It checks the reconstructed whole hash, payload hash,
unchanged prior payload, all auxiliary files and concurrent mutation guards.
Output is provisional until iterator exhaustion sets proof['complete'] true.
Consumers must never accept a partially consumed iterator.

The archived prefix remains authoritative and must remain available. A delta
capsule cannot replace or delete that source. No column, sample, interval or
diagnostic is omitted by the reconstructed logical stream.

## Cloud evidence

Run 40068424229 at ad327aca40c7eb1024ac6112697044088802fe70 passed:

- Exact byte/archive round trips for an explicit synthetic fixture and an actual native-prefix fixture.
- 28 negative controls for each fixture, 56 total.
- 512 rows across all 5106 native columns: 2614272 binary64 samples bit-identical.
- Unchanged protected controller, readers, acquisition analyzer and sparse store.

The native fixture came from a hash-verified first archive part of run 40001626503.
It is explicitly a prefix test: the complete 130569396155 byte source raw was not
read by this test, and the short fixture header was rewritten without changing
payload samples. The fixture cannot pass a full-duration electrical gate.
The actual fixture reconstructed 21110715 bytes while storing 5775291 raw-extent
bytes and retaining 15335424 bytes in its immutable prefix.

## Reviewed production integration still required

1. Keep the existing native controller, full-capture vector table, clocks,
   simulator options and acquisition/device-safety gates unchanged.
2. Restore only the exact qualified run 40001626503 CRIU checkpoint at
   998.45671875031 ns after the timeout is recorded. A t=0 restart is forbidden.
3. After the same native process stops, bind its report and current full logical
   contract to the actual immutable source descriptor/manifest. Publish the
   delta capsule with an ordinary hash-verified archive/parts envelope. Publish
   a readiness descriptor only after all parts and metadata are hosted.
4. Add an explicit delta source envelope gate that requires a terminal successful
   owning workflow, exact source head/method hashes, original completed-native
   report assertions and matching capsule/source/report identities. Do not fake
   an ordinary manifest or relax the existing reader's source-workflow checks.
5. Reconstruct all original raw bytes through capture_chunks(), then apply
   the unchanged 5106-column full-capture reader and acquisition analyzer.
   Acceptance requires both complete transport proof and all original gates.
6. Retain the failed partial publication and all source artifacts. Do not launch
   a production continuation until this integration is separately reviewed.

The present branch contains only transport code, controls, workflow and receipts.
