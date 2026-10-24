# Actual TX output terminal reference planes

Wire run39565287494 passed with14 native devices,38 terminals,9 geometric metal components,
eight physical ports and unchanged serialized geometry. All metal/via ownership is checked
against unsimplified LVS without merging disconnected conductors by logical labels.

This stage assigns24 metal terminal reference planes and retains14 body terminals separately.
Each of four HBT instances is matched by its own terminal enclosure to the actual serialized
native PCell. The pinned PCell source identifies upper Metal1 collector, lower Metal1 base and
Metal2 emitter, including Nx8 cells. REF collector/base share IREF electrically but retain
distinct spatial planes and the original swapped-plane fault must reject.
Resistor and ptap access comes from actual native contacts and original PCell port boxes.
Eight public access planes come from actual serialized GDS labels and pin rectangles.

All six original physical point corruption controls remain mandatory. Eight finite contacts
must not become ideal body shorts. Poly/diffusion access resistance and spatial substrate
spreading remain unmodeled and are explicitly not called qualified PEX. Next: fresh raw
wire RC audit, composition, real parent intermacro routes and complete loaded waves.
