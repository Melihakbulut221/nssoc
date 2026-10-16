# Pullup geometry hypothesis after native headroom diagnosis

The actual localpins driver fails12HBT minimum0.4V VCE gates. Full-capture
replay38929031066 reproduced every original engineering field. At xd0125's
native worst sample24.409808ns, C=0.957976V and E=0.620758V: VCE=0.337218V.
Simultaneous d0p/d0n are1.811197/1.792500V, a low common-mode transition.
The intrinsic control has a higher collector voltage at its own worst sample;
those distinct timestamps do not by themselves establish causality.

The source-bound native100-device mapping identifies XD87 unambiguously as
XUP: avdd-to-dout rppd, width4um,length3.08um,ps0,b0,m1. Two prospective
lengths2.7um and2.4um test whether stronger pullup support can prevent the
low-output/common-mode transition from reducing selector collector headroom.
This is a hypothesis, not a demonstrated correction. Current and all device
limits remain evaluated; raising a node must not silently trade a minimum
VCE failure for excessive VCE/VBE or MOS stress.

The cloud study preserves every original260wireR/295wireC, all other99raw
devices and finite contacts, and the12um input-gate damping resistor. Named
native terminal bindings, original resistor parameters and exactly one length
change are checked. Deliberate gate-damping and pullup-terminal corruptions
must fail. All8drivers,672MOS,62HBT,full34ns/256sourcebits,zeroOP,original
0.3/0.5/0.7UI phases and100/150mV/0.4V criteria remain unchanged.

This uses frozen old interconnect with a changed compact resistor parameter:
it is a schematic sensitivity, explicitly not a physical candidate. A useful
result requires a new physical resistor/driver layout, native DRC/LVS, fresh
terminal binding/RC/composition and full loaded/PVT tests before adoption.
Neither variant closes32:1/four-lane SERDES, PLL/CDR or mainchip timing.
