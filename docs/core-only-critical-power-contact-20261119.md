# Six critical driver local supply-contact admission — 2026-11-19

The six resized/legally placed critical drivers have verified local native LEF power-pin contact to same-net special-wire metal/via landing geometry. This is not full PDN, transistor LVS, GDS, IR/EM, or manufacturing signoff.

## Authenticated evidence

- Run: https://github.com/Melihakbulut221/nssoc/actions/runs/44410078177 (attempt 1, success).
- Source commit: `1d372e13f975294c16c0322e220f13ba4945f6d0`.
- Artifact: `14476737991`, SHA256 `d225553482d232a380739d9a55170321962eecd95522306426749b899b79b747`.
- All three manifest output hashes independently verified after download; no local artifact files retained.
- Candidate ODB SHA256: `4da67d1ffad55f5cb4aacbcea38b2e7c27124f8a728e79056bd096435b624c60`.
- Source resize run: `44399362987`, commit `dfa8f24652dc77838f127b77980364ee5bf944b6`, artifact `14471483674`.

## Native result

All 12 supply terminals on `fanout541`, `fanout644`, `fanout657`, `fanout677`, `nssoc_sta_i_59322`, and `nssoc_sta_i_15034` have positive-area same-net rail contact. No wrong-supply contacts or missing contacts were found. Five cells are `sg13g2_buf_4`; instance 15034 is `sg13g2_a21oi_2`.

Synthetic controls reject missing rail, wrong layer, wrong supply, displaced pin and edge/point-only contact. Removing the five native rail shapes contacting `fanout541/VDD` is detected as loss of contact. The source ODB is unchanged.

## Binding to later routing

This proof covers the legalized candidate, not an arbitrary later layout. Detailed-route run `44402072903` is still pending at this admission. Its independently checked identity chain must preserve exact instance geometry/status/masters, terminal connections and special-wire geometry before carrying this local-contact proof forward. Fresh post-route extraction and all-corner timing remain required. Estimated setup/hold zero is not signoff.

Package, PCB, external devices and interface rates remain unselected per the user; external I/O timing is not signed off.
