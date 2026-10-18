# CDR v2 MIM-aware native wire audit

Run 39081441241 passed strict comparison of all 8956 resistors and 7079 capacitors against native extraction records. All 776 points belong to the expected 111 physical conductor components. The native resistor topology/value multiset, each point capacitance, each mutual attachment/value, and the complete 12544-entry collapsed capacitance matrix are conserved. All 13 raw wire corruptions and nine intrinsic MIM corruptions were rejected. All eleven MIM identities, exact dimensions and ordered terminals match the new native LVS binding.

The earlier v2 audit failure (39081203572) is preserved: its helper accidentally loaded the v1 binding. Only the helper receipt binding was corrected; no device, wire value or verification threshold was changed. The original v1 helper and failures remain intact.

The composed candidate must retain 394 devices and all 16035 wire elements, with each intrinsic MIM emitted exactly once. Model assembly repeats 15 fault controls before native loaded transient simulation. Passing these conservation checks does not qualify RF capacitance distribution, substrate spreading, closed-loop acquisition or a complete serial PCIe PHY. The early/late data, timing, current and device-voltage gates remain unchanged.
