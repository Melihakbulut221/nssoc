# Three worst slew drivers: load isolation candidate — 2026-11-19

Native inventory run https://github.com/Melihakbulut221/nssoc/actions/runs/44484077080 at `639778cf2ef82bf99ebf9788c5a910326c50c68a`, attempt 1, succeeded. Artifact 14510051644 SHA256 `eaf320d3d30cdca96b6765ed26186d3e3bc4e04966e882a9ecfef46551d6996e`, both outputs verified. It reads unchanged ODB `a185d1494ffb265a9d07a08a4175704602ade02cf974ee8f9efbb923d22d098e` (106651 instances).

The three worst driver outputs are o21ai_1 cells without a larger o21ai variant in this native library. All three selected output nets have no antenna cells. Their measured connections are:

- 8457/Y, net 100406: load_slew2431/A, load_slew2428/A and wire2427/A; loads spread far from the driver.
- 52826/Y, net 53586: 57620/A1 and 52834/A2, about 687 micrometres away in x.
- 63807/Y, net 63283: 66452/B2, 65898/C, 65702/C, 65697/D, 65678/A1, 65288/A1 and 63808/C.

Candidate: insert one sg13g2_buf_8 adjacent to each original driver, move precisely its listed loads to the buffer output, and keep the driver connected to the new buffer input. Expected cells 106651 -> 106654, three new nets; six affected data nets require fresh routing. Original cells are frozen for legalization. Prove identity by verifying Liberty function A and collapsing inserted buffers to recover every original terminal connection; preserve all other geometry, supplies, diode connections, 103082 unaffected non-power DEF net records and 2113 clock records. Verify six buffer supply contacts against same-net native rails with negative controls. Original NDR assignments must remain unchanged.

This is a measured-load hypothesis, not a timing claim. Added buffer delays and rerouting can affect setup/hold and antenna. After legal preparation, require selected routing, independent geometry, DRC/antenna and fresh extraction/all-corner timing. Existing nominal zero-setup/hold result is retained as evidence, not overwritten by an unmeasured candidate.

Other findings retained: the new 57622/A_N violation is driven by o21ai_1 instance 52788/Y on net 53548 with a second load 52789/B. Drivers 8624 and 8545 have existing diodes and are not part of this no-diode-net isolation change. All remaining electrical and production requirements stay open.
