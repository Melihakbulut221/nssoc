# Route12 evidence publication repair — 2026-10-24

Recovery run 40110502492 at ac1740af745fe3d62960b1e62297096c619f0c5d
verified the original 65-member artifact byte for byte. Its separate publication
step failed with HTTP 400 Bad Content-Length on a zero-byte log. The original
route run 40095811631 remains rejected for no observed native DRT log progress;
recovered process images do not establish a valid continuation or live router.

The three exact recovery receipts and the publication rejection receipt are
retained under docs/evidence/mainchip-route12-recovery-*.json. The successful
recovery result is 45,327 bytes, SHA256
ef688f4fbb6b238618b7e9c46a4cd7297b1aa809db020ccaa52bffd28d2e3468.
Its fallback Actions artifact 12567520376 is 1,484,547,934 bytes, SHA256
3d9c5f0576457f02c2a0c0783340ebc9bb71e2b6c84d55f79a1f0914e21bc4ff.

This new controller authenticates that failed publication run and its successful
recovery step, the exact fallback metadata, complete ZIP digest and extent,
canonical regular-file inventory, every outer member CRC and exact SHA256.
It restores exactly the 39 output records plus the original result.json. The
original 1,560,640,815-byte ZIP remains opaque and unchanged, SHA256
6231b9523ba15bcabac5e65b166648523a742c146321c7806ff97d01e6272e56.
The prior authenticated 65-member scan is reused; the large inner process image
is not decompressed, parsed or rescanned. No router, CRIU, CAD or simulator runs.

Every nonempty restored file is published through the existing immutable-asset
publisher. Empty files are retained as exact zero-byte files on the runner and
inside the original archive. A nonempty empty-file-inventory.json names each
empty standalone file, its original path, release basename, zero length and
empty SHA256. They are never padded and no zero-byte standalone upload is
attempted. Existing releases and assets remain untouched; this repair uses its
own precreated cloud-results-RUN-1-mainchip-route12-recovery-publication release
at the exact tested source SHA, verified before archive read and each upload.

Hosted controls require 32 new mutations, the original 29 transport controls
and the shared 17 source-release controls. The new positive fixture copies a
small synthetic outer ZIP with an opaque inner-archive fixture, an empty file
and a nonempty file. A mocked publisher proves that only the two nonempty
fixture files and the explicit inventory are submitted; no actual remote upload
occurs in controls. Faults exercise real outer CRC/hash/member/path errors,
metadata identity, detached proof bytes, omitted or padded empties, publication
partition errors and propagation of a publisher failure. These fixtures do not
claim to scan the actual large fallback or original 65-member archive.

The workflow is a nonregistered manual-only template. Source review and a
separate safe no-op registration are required before a single controls-to-
publication run. Source controls run before the archive read. Full small JSON
bytes, length and SHA are printed as PUBLICATION_REPAIR_BYTES and indexed
PUBLICATION_REPAIR_BASE64 chunks before final report upload. An Actions artifact
preserves the report; any failure also retains all restored files. A successful
data-publication report is distinct from final job/publication success, which
must be checked together with authenticated hosted asset digests.

This change leaves the original recovery module, its workflow and method,
route controller, native execution gates and every route/timing/PHY acceptance
flag unchanged. It repairs evidence publication only.
