# Actual local contacts and160nm M1 gate straps

The final candidate starts from the independently qualified650 GDS
17bcc6f9e98f5346e92f7c770f4212a012ab1718ba78432fd609e280ff5e0541.
Retain all original shapes, devices, hierarchy, annotations and650 reference.

## Actual geometry diagnosis
Run41701650129 completed generation with a rejection of all42 multi-unit
groups. Its report preserves every attempted offset and clipped original
obstacles. A representative gate axis is x1084090nm; the neighboring M1
inner edges are1083830 and1084350nm. The available corridor is520nm.
A290nm Via1 landing leaves115nm, below the180nm M1 spacing requirement.
The same-axis Via1 also collides with the original via. Lateral paths cross
continuous source/drain M1 rails. No groups were accepted and no newGDS was
serialized. The full failure is permanently published in release433116338.

## Physical repair
Use a160nm-wide continuous Metal1 strap on the gate axis, from the first
inter-unit gap to the existing top gate contact. It leaves180nm to each
160nm source/drain rail in the measured corridor; every actual group is
independently checked against all foreign M1 geometry before serialization.
Add the150 standard160nm contacts in the existing500nm gaps. Preserve70nm
poly enclosure, require140nm Cont-on-poly to Activ spacing, cover each
contact with M1 and provide50nm longitudinal M1 endcaps. No new Via1 orM2
is needed. Do not widen M1 locally into the source/drain clearance.

The8 single-unit groups remain unchanged. All42 multi-unit groups must
route; no partial candidate is accepted. All old layer unions/hierarchy
and complete serialized geometry are compared. The planner is NOT full
DRC orLVS. The unchanged full560-category/deep-flat650/13fault physical
checker must independently accept the actual resulting GDS, then terminal
binding and all fresh RC/electrical tests must be regenerated.

Primary rules: M1.a160nm, M1.b180nm, Cnt.e140nm; M1.c lateral Cont
enclosure0 and M1.c1 longitudinal endcap50nm:
https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html
https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/03_extra_drc.html
The complete pinned native deck, including wide-metal and density rules,
remains the acceptance authority.

## Preserved failures and publication
Run41700152258 rejected side routing and then failed publication404;
run41701260499 failed cloud tag creation403 before geometry.
Run41701650129 preserved the complete42-group rejection in release433116338.
The authorized dispatcher reserves each exact-source tag/release; the
cloud job verifies it before native work. No token permissions are widened.


## Whole-strap ownership diagnosis and preserved failure41702925124
Run41702925124 rejected all42 complete straps. The first-gap cross section
alone was insufficient: nonzero conflicts occur elsewhere along each full
path. No candidateGDS was accepted. The successor uses the exact qualified
wire l2n database and flat native LVS to identify the gate's complete actual
metal-connected component. Every start contact is probed in both native
databases and must match the independently extracted gate owner. The full
own-M1 union must be present in the original GDS and contain the original
contact component. Only that physically connected geometry is excluded from
foreign-net checks; no schematic aliases, logical labels or guessed bridges.
All foreign-net clearance values remain unchanged. If still rejected, save
full-path intersection, actual foreignM1, ownM1 and contact outlines to
identify the necessary physical reroute from actual whole-path geometry.
The first-gap corridor is not evidence that the full strap fits.


## Actual obstruction and source/drain Via1 relocation
Whole-path native ownership run41703662218 confirmed all42 strap obstructions
are foreign source/drain metal, not misclassified same-gate connections.
The full native M1 component increased correctly, but collision area did not
change. Existing290nm-wide source/drain Via1 landings protrude65nm into
the otherwise valid160nm gate corridor. Representative left/right protrusions
overlap in Y, so a lateral160nm gate jog cannot solve the constriction.

The successor moves only source/drain Via1 cuts on the measured x=gate+/-340nm
columns65nm outward, together with their290nm M1 landing squares. Add same-net
M2 landing extensions while retaining every original M2 polygon. Every cut
must be an actual190nm Via1, have the observed50nm M1 enclosure, and be probed
in both the original flat native LVS and physical wire database as a source
or drain owner of the group's actual MOS devices. No schematic-name inference.
The full relocation list records original/new geometry and both owners.

Remove the original cut and landing, add the shifted geometry, and preserve
complete coverage of every existing Cont. Check50nm new via enclosures,
220nm via spacing, foreign M1/M2 spacing, same-physical-net overlaps and5nm
grid. Then add the150 local gate contacts and42 M1 straps. Full actual
conductor layer unions are serialized/reloaded; only Cont/M1/M2/Via1 may
change. Original transistor/nonconductor shapes, hierarchy and text/pin
annotations remain identical. The earlier all-original-material invariant
is explicitly superseded by documented conductor relocation, not silently
waived. No physical acceptance until the unchanged full DRC/LVS/fault checker.


## Complete source/drain bar correction
Run41704706891 moved934 actual source/drain vias and cleared6 of42 groups.
The other36 still failed: moving only each via's290nm square leaves the
continuous original M1 bar protruding between cuts. Some actual via columns
also differ from the initially assumed+/-340nm axis offsets. The full
foreign-metal outlines and all934 movements are preserved, not accepted.

The successor computes each cut's outward shift from its actual edge and
the required gate corridor; it no longer assumes a single column position.
It then removes the full residual M1 protrusion inside that corridor.
Every removed polygon is independently probed in the original native LVS
and must belong to an actual source or drain of that gate group. It may
remove only original M1 material, and every original Cont and every retained
or relocated Via1 must remain covered. No signal is joined by name. All
foreign spacing guards and the independent full DRC/LVS requirement remain.
