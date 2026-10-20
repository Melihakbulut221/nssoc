# Bounded compressed staging for full-terminal PLL continuation

The actual saved initial stage of run39390580356 contains49178611643 raw bytes. It checkpointed after2281.91 additional host seconds when free disk58332934144 bytes fell below the conservative58475225668-byte full-archive reserve. Native progress and payload were preserved; full1us capture and acquisition are still false. The immutable archive contains42 parts totaling44705575058 bytes. Initial publication completed and the same-run continuation is active; it must not be restarted.

A complete extra compressed archive consumes increasing disk as the native capture grows. The proposed storage helper streams the existing tar/gzip bytes into one256MiB temporary part. It requires the hosted asset name, size and SHA256 to match before removing only that compressed temporary file. All original native evidence is retained. The completed manifest is published only after every part has a verified hosted receipt.

Restore likewise verifies each downloaded part before delivering its bytes and verifies the ordered full archive digest before returning success. Extraction is preparatory; no native process may be activated unless the entire archive, restored files and existing source/capsule proofs pass. This bounds compressed staging without dropping vectors, samples, source files or native process state.

A dedicated cloud job exercises exact archive and restored-payload equality,12 publication/restore corruption cases, preservation of original source bytes and retention of failed parts. It also performs a real1MiB GitHub release roundtrip split across several parts and verifies the downloaded content. These tests establish storage behavior only.

The helper is not yet adopted by the PLL controller. Adoption must preserve the exact845+4-contact native process, all1694 probes,1us/.3125ps analysis, original inputs/loads, full-terminal readers, prefix/cold-restart controls and frozen acquisition windows. The active continuation remains on its existing revision.
