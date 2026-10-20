# Full TX test of four physically replaced p4 drivers

Native composition39450330853 passed all1674-device/117251R/77892C checks,
six malformed-model controls, all124 actual input legs/372 data-base terminals,
and both wrong-endpoint controls. The compact model is
1f0709a19395e7de77529adb20fbdff04f895fcc8588e0ba7ac5a32fb8c110bb and distributed
model df92e5b36e0c633a9df3a065fe55729d50ca103e3fbaaa2a8267a5464d1f3eee.

Before simulation, an independent compact-model comparison reconstructs the
intended change from the *old native a master*, not from candidate parameters.
All untouched macros retain original physical primitive identities. Each changed
p4 macro must have exactly that master's model and local nanometer bounding boxes.
All twelve port nets are rebound through original native interface probes and
the original selector topology; genuinely shared body nodes remain shared.
Every other local node receives a separate target-macro identity. The resulting
expected circuit must match the extracted candidate via a bijective node map
with fixed public ports and exact device parameters. Missing-device, changed-
parameter, wrong-terminal, physical-identity swap and reused low-drive parameter
controls must be rejected. This proves the intended change, not equivalence to
the old rejected circuit.

The full34ns/256bits, original0.3/0.5/0.7UI samples, all604HBT/512MOS limits,
eleven physical clock macros (groups0/2/3/4 l5p7; others l6p25), source bits,
solver settings and actual leaf-selection fault are unchanged. Both nominal and
fault cases run in the cloud. All changed physical model identities are exact
and source-delta checked. No smaller core, shorter capture, phase adjustment,
ideal intermacro alias or relaxed electrical gate is substituted.

The native emitter budget increases to863/core and remains unqualified at
whole-chip scope. External clock modulation/frontends and full PVT/RF/ESD,
closed-loop serial PHY and mainchip integration remain open. Passing this test
would not on its own close those requirements.
