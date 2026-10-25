# Bind the actual GDB loaded executable

The authenticated original fixture40172782148 failed before attach at the literal progspace filename comparison. Readback40173543363 preserved the exact traceback, all twelve artifact members and the full original rejected result. The actual GDB filename spelling was not recorded, so its value remains unknown.

The repaired fixture records that spelling before validation, resolves the reported absolute path, opens both that actual file and /proc/PID/exe, and requires the original exact canonical path, device, inode, length and SHA256. The held proc-directory/pidfd is revalidated before attaching. Matching a display string alone no longer controls acceptance; matching the actual protected executable does. Three actual path spellings and eight wrong-object/identity controls supplement all original24 controls. The C fixture, no-write/autoload settings,20 samples, stack census, debugger cleanup and native-admission rejection remain unchanged.

Before any future attachment rejection, bounded exact stdout/stderr slices are logged with offsets, full-file hashes and omitted-byte counts; full raw files remain in the artifact. Actual long/non-UTF8 stream fixtures verify the bounded reporting. Console failure is recorded and never turns rejection into acceptance.

This source is not yet a passed fixture. Fixture execution remains disabled pending independent review. No chip process restore/attach, route continuation, or routing acceptance is authorized.
