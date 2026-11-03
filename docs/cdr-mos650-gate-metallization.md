# Shorten long shared poly gate access using actual metal/contact geometry

Start from the independently DRC/deep+flat LVS qualified650 GDS17bcc6f9e98f5346e92f7c770f4212a012ab1718ba78432fd609e280ff5e0541 and actual native200 gate geometries. Preserve the complete transistor geometry, original hierarchy, labels, public interface, reference schematic and all existing material.

For42 multi-unit gate groups, add150 contacts in actual500nm inter-unit gaps. A continuous M1 stripe over the gate can conflict with source/drain M1, so use160nm-wide M1 lateral stubs and190nm Via1 cuts with50nm landing enclosure to a320nm M2 side bus. Search actual empty side channels, checking foreign M1, all M2, Via1, contact/active/poly clearance, macro extent and5nm grid. Existing original gate contact attaches the bus to the same physical gate network. The8 single-unit groups remain unchanged.

This geometry planner retains conservative spacing guards but is NOT full DRC/LVS. No candidate is accepted if any multi-unit group has no clear route; retain all attempted geometry and failures. Serialize/reload every actual layer union and all hierarchy/labels. Independently re-run complete native DRC/deep+flat650 LVS/fault controls before using any generated candidate.

Then regenerate current terminal/contact binding and full fresh RC. Each unit can now see multiple contacts; the old one-contact anchor assumption cannot be reused. Compact gate resistance, NQS and remaining short poly paths still require explicit modeling. Physical routing improvements do not waive full PHY or final timing requirements.
