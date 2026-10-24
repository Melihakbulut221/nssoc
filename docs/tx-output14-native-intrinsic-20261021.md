# Native TX output14 compact model

Export all four HBTs, two rsil and eight distinct ptap1 contacts from both unsimplified native
deep/flat LVS databases of physical run39564026768. Public nets are bound using actual GDS
labels and native metal probes. TAIL/BULK are identified from the actual Nx8 tail transistor;
neither may alias a public net. Both modes must reproduce the complete original output topology.

Original HBT geometry/multiplicity, native rsil geometry and self-heating, all38 ordered device
terminals and all eight finite body contacts remain in the simulator model. Each tap conductance
uses its actual native A/P and the pinned PDK law A/raspec + P/rpspec. No zero-ohm body tie or
invented substrate spreading network. Eight native identity faults and eight compact-model
faults must reject. This compact model alone contains no wire RC and is not yet simulator tested.

Next combine every actual extracted wire token with these exact terminal references, verify
the complete native topology after collapsing only wire resistors, and validate the physically
routed lane including its parent/output/bias/clock boundaries under full loaded gates.
