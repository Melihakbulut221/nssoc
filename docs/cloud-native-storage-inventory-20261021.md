# Read-only hosted storage inventory

The complete original PLL waveform requires at least130,713,600,000 uncompressed payload bytes before native/runtime/checkpoint overhead. The last completed native checkpoint reached820.364ns and had21.1GB free inside its existing preallocated shared filesystem; the original12GiB native reserve remains mandatory. Full remaining capacity has not been proven.

This new disposable-hosted-runner probe inventories actual filesystems, block devices, mounts and swap, including any independent /mnt resource volume. It does not format disks, disable swap, allocate storage, clean files or touch any ongoing native process. Device IDs prevent counting different paths on the same filesystem twice. A listed block device is not yet usable storage.

Any potential additional volume must be independently prepared and tested on a fresh hosted runner, with original native checkpoint/runtime paths and every byte preserved, before an actual process migration. No vector reduction, timestep relaxation, shortened acquisition window or purchase is authorized by this probe.
