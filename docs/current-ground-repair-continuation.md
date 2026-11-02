## Current continuation: monitor inventory overflow repaired without dropping history

The scheduled monitor41501146100 failed because an inventory shard exceeded its unchanged65536byte bound. The main workflow already loads the exact working-branch inventory; this was NOT a missing main synchronization problem. The previous v322 note named the failing guard but did not yet identify this cause.

All835 ordered records are now repacked into contiguous shards below60000bytes, with matching byte counts, Git blob IDs, per-shard SHA256 and unchanged combined ordered-row SHA256. No record, failure or job was removed; monitor source,8hour schedule,request bounds and automatic_native_dispatch=false remain unchanged. Run existing main cloud-progress-monitor.yml mode=observe with approved_source equal current main SHA to verify live acquisition. Do not claim successful observation until that job actually passes loading.

Two obsolete push CI runs41498680552 and41493899500 were cancellation-requested after verifying their branch source had advanced and intervening changes were only scripts/docs/.github. Existing lint/RTL failures remain; cancellation is not pass. Current-source tests and all actual CAD/SPICE jobs remain enabled.

Full64 independent source controls41512344559 succeeded at302f9c30a847acd659a8c451bdce83707fce5d70. Authenticate its derived controls and dispatch actual full64 once with control_run41512344559, then reserve exact-source release. Isolated16MOS current-only controls41512921089 remain their own handle. Complete PHY diagnosis and both candidate source snapshots are preserved in v322. No PHY, chip route or setup/hold acceptance is implied.

Observed 2026-11-02T19:50:16.034850+00:00:
- 41498680552: completed/cancelled
- 41493899500: completed/cancelled
- 41512344559: completed/success
- 41512921089: in_progress/None
