# Native physical PLL process portability diagnosis

The separate-job4ns restore38898727014 failed with native `internal error -- illegal instruction` and exit1 after Docker restore succeeded. The same-host proof38897452492 remains a bounded bit-exact runtime result only. No source CPU capability image was captured, so CPU compatibility is not proved.

CRIU documents that CPU feature differences may produce execution exceptions during migration: https://www.criu.org/Cpuinfo . This is a hypothesis here, not an established root cause. The diagnostic workflow records destination CPU/kernel/capability images, decodes original process registers and memory/file mappings using the pinned CRIU source, and retains actual partial raw/OP captures even on failure. It also runs an independent fresh4ns reference using the exact saved image, original solver/circuit/libraries and native options on the destination before restoring the immutable source process. That reference is never used as replacement continuation data. Exact sample/time/probe and single-entrypoint gates remain unchanged.

A successful diagnostic only proves this source/destination bounded test. Original1us PLL acquisition, all device operating limits, PVT, full serial x4 and actual routed mainchip signoff remain open. CPU portability must be understood before relying on a multi-job full acquisition.
