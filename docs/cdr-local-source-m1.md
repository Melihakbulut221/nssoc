# Measured local source Metal1 candidate

Actual map41397314520 establishes eight32.5245ohm source-access branches and actual original Metal1 terminal strips of290nm width. This candidate adds only Metal1 to the left of these original source strips, within18um above and below each actual reference. It tries1500,1200,900,600,300nm added widths in order and requires all eight targets to admit.

The source and exact parent GDS are pinned to the complete actual resistance mapping. No transistor, contact, via, logical reference, ground source or model changes. New material must remain inside the parent bbox, attach to original same-net Metal1, maintain605nm from foreign Metal1 and5nm from foreign Via1, and avoid unclassified drawing. Existing material is never removed. Serialized full-layer equality and reversal prove the only material delta is the reported Metal1 addition. Six new guard controls cover acceptance, foreign metal/via, floating metal, unclassified material and bbox escape; all85original controls remain.

This is an unqualified candidate. Full560DRC, deep/flatLVS13, canonical native binding, freshRC and the original loaded electrical gates are mandatory. The32.5245ohm native edge can aggregate several physical segments; widening this local strip is a measurable candidate, not a claimed solution. Re-extraction must determine how much resistance, headroom and sample delay actually change.

Generation41397981344 refused all8targets and preserved actual proposals. The intended horizontal expansion called Region.sized(dx,0), whose two-argument overload is isotropic sizing with a mode argument. It also grew Y, causing the independent span, left-only and single-addition checks to refuse the candidate. The corrected helper uses explicit sized(dx,dy,mode) with dy=0 and mode=2. No spacing, attachment or scope checks are relaxed.

Seven additional cloud controls compare the complete polygon result against independently constructed expected boxes for all5proposed widths, reproduce the old native overload error, and verify a stepped source contour. Original91controls remain unchanged. The actual GDS is still required to pass all8targets before any file is accepted.

Primary API reference: https://www.klayout.de/doc-qt5/code/class_Region.html (sized anisotropic three-argument versus isotropic two-argument overload). Runtime remains pinned klayout0.30.4.post1 and the regression executes that actual runtime.

Corrected sizing run41399519731 passed98controls and removed the unintended vertical growth. Actual native geometry still refused: near the ends of the36um source window, original M1 narrows from290nm. Expanding that stepped band filled65nm inside the nominal left boundary and approached foreign M1. All8targets remained refused, preserving the actual failure.

The next geometry variant selects only an exactly rectangular, fully original290nm source band. It tries halfspans18,16,14,12,10um, in that order, and preserves every original spacing, left-only, connectivity and36um maximum-span check. Narrowed ends are excluded from the candidate; no threshold is relaxed. Each proposed original band and all rejected width trials are recorded. Four additional controls reject narrowed ends or holes and admit complete central rectangles. Resistance improvement remains unproven until actual freshRC and loaded simulation.
