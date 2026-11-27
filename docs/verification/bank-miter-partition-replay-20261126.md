# PCIe bank miter regression replay

All 295 originally assigned test nodes passed through `make test` on source `effb9713107a27e181a461a4819706fcca99e618`. The workflow reuses the original lists, including parameter strings. Counts by original tail partition are 0: 50, 1: 49, 2: 49, 3: 49, 6: 49, 7: 49. [Native CI logs](https://github.com/Melihakbulut221/nssoc/actions/runs/45729030912).

The historical ALU workflow pinned at commit `14f5b2f38ce6040433b888b3522800b1b264a04d` has blob `7eecbd2655f6e8974fc4a4c1e7f0edfb6ec6dc8f` for `.github/workflows/timing-alu-state-bits-complete.yml`. The live blob `0270c5026ef346f6a24a2693e06d50dc2d8c205f` includes branch filtering. The archive replay retains the original bytes. This six-partition run does not qualify the historical ALU suite or the entire Python tree.
