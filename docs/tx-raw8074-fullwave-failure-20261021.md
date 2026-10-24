# Complete actual8074 TX nominal capture rejected

Run39592603205 completed the exact native trajectory through34ns,77904 rows,
14162 columns, with no solver diagnostics and unchanged sources. The original
bit screen rejected130 of768 sampled signs and133 samples below100mV.
All five interface groups failed original150mV/common-mode checks; the CMOS
input group has zero sign errors but5049 samples below150mV and common mode
0.879--1.606V. That low input range is a measured observation, not a proved
cause.284 of604 HBTs failed original bounds; all5376 MOS devices passed.

The full raw file remains in the original immutable release. A separate
cloud observer reproduces the entire original review, then measures local
AVDD/AVSS/DVDD terminal planes and every physical logical input bank at the
unchanged sample times. No new simulation, shifted oracle or weaker limit is
used. Its temporary raw copy can be removed only after exact reproduction;
the original capture is retained. A passing diagnosis is not a repaired PHY.

The actual8088 parent includes the physical output and has new native initial
capsules39601746737. Those early incomplete trajectories do not establish that
the common input/core failures were repaired. Keep their distinct source/model
identity and use the diagnosed rail/input evidence to select the next actual
circuit or route change.
