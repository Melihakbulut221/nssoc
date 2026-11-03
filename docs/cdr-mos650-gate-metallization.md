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
