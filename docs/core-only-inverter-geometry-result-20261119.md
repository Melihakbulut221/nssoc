# Inverter geometry evidence and parent-context hypothesis

Run 44421079818, head 893bcddde5609197cec147731d4aeb6b48e657de, artifact 14481138003, SHA256 4ced23f7564005075cb4f6eeec907acf1937c5a60f7e8120be6262a0c96d19d1. All geometry output hashes verified. The current inverter differs from the old revision on layers 1/0, 6/0, 8/0 and 8/2; tie-cell geometry is unchanged.

Coordinates are 0.001 um DBU. The inverter has active rectangle (-405,6380;-105,10790) inside its nwell, outside its own P implant (whose upper rectangle starts at x=-75). This left-side active is contacted by the metal carrying the i label. The official general_derivations.lvs derives nactiv from active minus P implant, and ntap from nactiv inside nwell outside markers/diode/poly exclusions. This provides a concrete explanation to test for the isolated i/VDD merge: neighboring-cell implant coverage can change this region's classification.

The next native measurement uses the actual inverter instance transform in sg13g2_GateDecode and measures this rectangle against both own and recursive parent P implant polygons. It does not modify geometry or constraints, infer electrical globals, or assert full LVS. Parent context must be established before attempting any edit to this boundary-dependent child cell. The separate tap perimeter and substrate reference mismatches remain unresolved.
