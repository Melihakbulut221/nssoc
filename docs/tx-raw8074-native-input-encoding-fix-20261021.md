# Byte-preserving native model input discovery
The first actual8074 native workflow (39521590595) passed all 19 structural controls but stopped both cases before starting ngspice. A model comment contains byte 0xb5; Python UTF-8 text decoding rejected it while discovering recursive includes.

Only the include discovery reader changes. It scans lines from the original bytes with a one-to-one Latin-1 mapping; it does not transcode or rewrite any native model, deck, OSDI, or prepared archive. All preparation SHA256 requirements and full original electrical gates remain unchanged. The cloud controls include a real nested include/section fixture containing that byte and reject changed, missing and unproven model inputs (22 total fault controls).
The failed run remains preserved. Actual native checkpoint and cross-runner continuation remain unproven until their jobs pass.
