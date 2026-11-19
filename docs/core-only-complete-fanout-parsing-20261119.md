# Complete fanout report parsing — 2026-11-19

The comparison artifact 14534485221 contains 211 actual fanout violation rows for the resized slow corner. Eighty rows (including clkbuf_1_0_0_clk_i/X, fanout1425/X and fanout2109/X) have a blank printed slack column, not wrapped names. A five-column-only parser therefore counted only 131 rows. Native aggregate counts remain authoritative; no violations were waived.

The new parser retains four- and five-field violation rows, preserves missing printed slack as null, labels limit-minus-actual as a separately derived margin, rejects malformed/nonviolating/duplicate rows, and requires exact equality with all three native electrical counts in every corner for both candidates. This comparison is read-only and does not modify the running eleven-net route.
