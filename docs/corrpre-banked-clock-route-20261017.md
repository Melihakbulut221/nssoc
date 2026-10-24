# Banked mainchip clock-layer experiment

The actual39031588904 native router completed55minutes with385overflow and disabled NDR on clknet_1_1_0_pcie_clk_i. Source failure and alllogs remain retained. PeakRSS was2GiB; this is evidence of congestion, not a RAM exhaustion diagnosis.

The separate candidate changes only clock routing from inherited Metal2..TopMetal2 to explicit Metal4..TopMetal2. It retains exact proven repairedODB/logic, signal layer range,20percent capacity reserve,50routingiterations, original SDC and5percent derate. Overflow is disallowed; any native NDRdowngrade rejects the candidate. It must have actualnonemptyguides andsourcehash equality, then detailedrouting/extractedSTA/signoff.

The control is documented by [OpenROAD set_routing_layers](https://openroad.readthedocs.io/en/latest/main/src/grt/README.html#set-routing-layers) and [LibreLane RT_CLOCK_MIN_LAYER](https://librelane.readthedocs.io/en/latest/reference/step_config_vars.html). The native source config already exposes these keys; success also requires the real log to show the intendedclockrange. No routing or timing success is presumed.
