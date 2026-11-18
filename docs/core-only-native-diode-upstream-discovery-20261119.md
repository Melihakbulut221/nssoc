# Native branch diagnosis and upstream correction — 2026-11-19

Trace run https://github.com/Melihakbulut221/nssoc/actions/runs/44413656261, attempt 1, head `b4f2a57b7ed3a0237fd81bd4c486cb2095d980e9`, artifact `14479696181`, SHA256 `e9b02fc8ddb632a7ce3293d43226af49b9ddbb52b4c11dea9d3f20692c70c916`; all 32 output hashes independently verified.

The unchanged old model at 398.15 K has DIOtBrkdwnV = -17.53791625663495 V and breakdown thermal voltage 1.6777541460701233 V. All 442 below-boundary trace records select breakdown branch 2, not reverse branch 1; 15 select forward branch 0. The ~-0.103856 V switch introduces the observed DC current and diffusion charge discontinuity. No simulator equation was changed.

## Upstream discovery changes the next action

IHP issue https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1288 documents exactly this porting problem and is closed. PR https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1294 was merged on 2026-10-20 (merge `80910b426074b4e9985aed545be6f36c8c4b4919`). The latest diode-library update inspected is `013bb30bb7c8f9d3c85173378597ac992ef7a272`. Its unmodified diodes.lib SHA256 is `e6211bd0318122fbeb707498ede893223c332098cbb21c441b28b9d8c365e83d`.

The pinned reduced fixture embeds the old library. Earlier debugging did not refresh this upstream fix soon enough. Stop developing speculative simulator workarounds: qualify the official complete library first. It changes diode level/area scaling, breakdown and temperature handling and corner capacitance; it is not equivalent to the old model. Preserve source provenance and requalify dependent pad timing rather than relabel old measurements.

The new qualification uses the unchanged published ngspice47 binary, original 125 C failure control, and official-library cases at -40, 27 and 125 C with the same topology, voltage stimulus, transit time and solver tolerances. Completion requires finite monotonic waveform samples through 50 ns with no simulator abort, regardless of process exit code. The production PDK is not changed until full dependent qualification; reduced-fixture success alone is not pad or manufacturing signoff.
