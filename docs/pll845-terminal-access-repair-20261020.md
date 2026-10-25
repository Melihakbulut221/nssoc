# PLL845 actual terminal access repair

Run 39347984074 resolved all 102 HBT physical primitives and covered every
one of the 235 wire components. It classified 1652 metal references,
819 intrinsic body terminals and 58 shared nonmetal diffusion terminals.
It rejected 208 unresolved terminals rather than inventing anchors.

All 178 resistor ends are native LVS boundary strips, typically only 5 nm
thick, so requiring a full contact inside each strip cannot bind a resistor
end. The repair locates the unique original rppd primitive enclosing both
native ends, requires exactly two native M1 pin boxes, maps the ends to
distinct nearest physical pins without ties and reprobes both exact native
and wire ownership. This also preserves separate physical planes for
electrically tied ends. The original 89-resistor census is mandatory.

The other 30 failures are MOS source/drain contacts. Contacts now require
positive-area overlap with the actual native terminal region (or connected
gate poly), full M1 coverage and exact native/wire owner agreement. Partial
overlap is a physical connection; proximity alone is never sufficient.
If unresolved, the report records nearby contact geometry and native
ownership for diagnosis. No arbitrary remote same-net point is substituted.

All original fault controls remain, with an additional actual resistor-end
swap control. No GDS, native LVS network or device parameter changes.
This remains a reference-plane stage, not qualified poly/diffusion/substrate
PEX or electrical acceptance. A new native cloud run is required.
