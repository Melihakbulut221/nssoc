# v51 compact local routing candidate

The v50 native waveform diagnosis40038187745 measured nominal input-to-valid delays4.531ps at public inputs,4.844ps at actual HBT bases,45.781ps at intrinsic collectors and57.031ps at public outputs. The input thresholds are30mV, collector/output thresholds100mV; these are direct voltage samples, not internal reconstructed data. Original output metrics exactly match rejected run40037560023.

Nominal actual v50 tail-source return paths were45.785/45.868ohm with84.863/85.217mV elevation. Collector-to-port paths were20.798/21.017ohm. Load-source paths20.344/20.427ohm still lost94.765/95.073mV. The hot-low CM and all three output timing gates remain failed.

v51 preserves all intrinsic dimensions and circuit connections. Device pitch is reduced60->30um, substrate escape columns move+15->+6um to maintain distinct routing lanes, and horizontal buses begin90um instead of110um. It retains4um TopMetal1 trunks,8um power/return buses,4um output/tail buses and2um remaining TopMetal2 buses. The upper terminal-escape via arrays use four columns instead of two.

MOS source/drain escape points move from extreme ends of the long native pins to3um on either side of the midpoint, within the verified pin rectangles. Four via rows at one column use the long pin direction. Resistor terminal escapes use eight via columns across their4/8um pin widths. Those local Metal3 links are1.6um wide; close HBT signal-pin escapes retain their existing width. These are actual geometry changes, not resistance scaling.

Full native DRC/LVS and nine real fault checks run before fresh native extraction and full unchanged loaded waveform tests. No result is accepted in advance. The same intrinsic v49 schematic preflight remains a limited component prerequisite; only new physical results can assess this geometry. Full parent/PHY/production timing remain open.
