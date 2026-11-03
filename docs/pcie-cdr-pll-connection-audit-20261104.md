# Current CDR to PLL connection audit

This is a source/evidence audit, not a new circuit, simulation, repaired PLL or physical acceptance.

The earlier PLL845 result (110.440674MHz feedback and9.190319ns phase span) belongs to a different captured design. The RHI120-C8 capture used by the first-divider diagnosis has raw SHA256 60f5318b08315751f7d3bede13223c12e4f4a13378e8d3d76e647f768446d8be and all3,201,410 rows/5106 columns verified. Its original final0.9-1.0us window measures 104.152221297MHz feedback and 5.002708790ns phase span. Original frequency100ppm, phase50ps and no-slip acquisition checks remain authoritative. Its acquisition is rejected. These captures must not be interchanged.

The current root's five first-divider schematic/generator files exactly match the hashes bound by the existing first-latch diagnosis. The linked terminal map was absent from the root continuation branch; it is restored byte-for-byte from a4bf51c1219fe521f34bb477035cdfc2a5012335 with its original SHA256d405e712... and all original false acceptance flags. It binds15 HBTs and4 collector loads to54 distinct native voltage columns. It contains no individual HBT Ic/Ib/Ie observations.

The source first conditioner is XSP/XSN W4/L3.6um and XUP/XUN W1/L4um. The physical generator explicitly restores the first toggle's four W8/L2.8um loads; the older generic latch text still saysL2.12um. A new parent must preserve the actual native loads rather than silently instantiate the generic defaults. The second toggle's four W8/L3.2um loads and its referenceL11.5um belong to the existing separate candidate and must not be confused with the first stage.

The existing RHI120 first-latch observations show159 double-transition intervals at10mV, conditioned clock differential extrema about-86/+91mV and approximately1.364V common mode. Corresponding master/slave clock-base routes differ by at most about1.35mV. The observed shared-emitter differences reduce effective hold/sample VBE separation at the recorded events. These facts support a loading/steering/regeneration investigation; they do not prove branch current, a unique root cause or safe replacement resistor values.

The next actual design experiment must retain the loaded VCO, native first conditioner, both master/slave stages and real downstream feedback loads; measure individual clock-steering/tail/data/hold HBT currents and their exact terminal voltages. A lower-impedance conditioner changes upstream VCO loading as well as clock amplitude/common mode, so a fixed ideal replay clock cannot establish the final repair. Any geometry change requires fresh DRC/LVS/RC and the original full1us acquisition gates afterward.

Current650 CDR N1/N2 runs still use the external8GHz clock bench. They cannot establish a recovered-clock loop. Actual CDR-to-VCO control coupling, stable PLL/divider operation, real clock/data ownership, four serial lanes and final serial-integrated chip timing remain required.
