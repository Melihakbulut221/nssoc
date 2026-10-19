# Fit actual drive strength into vacant native sites
The first vacant-site candidate39329794073 failed before legalization: selected driver $abc$1804206$auto$blifparse.cc:397:parse_blif$1846591 had no remaining free buf16 site within80um (nearest110.174um). Failure and archive pins remain explicit.

For each of the same128selected drivers, try actual positive buf16, then buf8, then buf4 using their native widths and input-pin geometries. Pick the strongest that fits a vacant legal row/site within the unchanged80um limit. Retain every attempted strength/distance. If none fits, fail the whole preparation; do not silently drop a driver or move an original cell.

All three masters must have exactly inputA/outputX signal terminals. The existing equation proof must prove all added buffers positive, and the inversion fault now reads the actual first inserted master. Final geometry checks compare each buffer with its explicitly recorded master. Timing/RC/antenna and fullPHY acceptance remain false until independently proven by the original gates. A smaller buffer may have different setup/hold/electrical results; placement feasibility is not timing approval.
