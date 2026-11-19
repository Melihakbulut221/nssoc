# Enforce fixed unaffected paths in SRAM clock routing

The selected-route attempt 44433409854 stopped in the detailed-route preservation audit. It is not admitted for timing or signoff. Preserve that run and its artifacts as failure evidence.

Start again from the already authenticated clock-resize preparation 44432691473/head e5536575eb03f3c6ab4bc61b045d243a265fb55e and exact candidate ODB a9e48d0c9f53e2ec3ac03fa35913b209bc0008717cf7b754b42c5b613734aab4. Route only delaynet_17_clk_i and clknet_1_0_0_clk_i. Encode all other existing routed net paths as FIXED through incremental DEF, check normalized pre-routing records, route, verify every fixed record, restore ROUTED status and run the original identity and geometry guards.

This applies the explicit FIXED mechanism under experiment on the separate data candidate; it is not yet proven successful on either candidate. Fixed geometry does not waive DRC, antenna, extracted-RC timing or production gates. No clock constraints or timing models change.
