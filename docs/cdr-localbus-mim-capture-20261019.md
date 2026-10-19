# Native local-bus MIM capture handoff — 2026-10-19

The cloud controller waits for exact extraction run39249871918 at commit
09748dc79e33298c19c339ac5a1ff00c13d566c7. It will not start capture unless
planes, wire-inputs, binding and rawRC all complete successfully. It binds
their release summary and ordered-archive manifest digests, same source
commit and parent/input provenance. Receipts are created only on the cloud
runner and retained with the result; no local files or process are required.

The capture algorithm differs from folded_v11 only in source namespaces.
It reads actual localbus_v12 parent geometry, retains all original metal/vias,
adds exactly the11 native MIM PCell masks, rebinds physical bottom contacts
and verifies946 points and111 conductors. No heuristic capacitance subtraction
or old foldedRC is substituted. The intrinsic-capacitance handling is unchanged
and its source-delta guard remains enforced.

A capture PASS is not an audited or electrically accepted model. Next steps:
inspect actual measured R/C census; original22 raw-capacitance controls and
19 composition controls; unchanged full loaded early/late and fault waveforms.
Full serialPHY, closed-loop CDR and final SoC setup/hold remain open.
