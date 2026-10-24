# Complete TX driver physical model composition

Source intrinsic run38873849859 preserves84raw MOS fingers,4resistors and12finite contacts, including actual named D/G/S/B junction orientation. Source RC run38875782771 passed251R294C extraction from10real metal/via components,164unique reference planes and all13raw corruption controls. The circuit retains an explicit seventh `wire_cref` port: extraction ground is not silently treated as a supply or substrate.

`cloud_tx_driver_compose.py` requires the same GDS and raw native LVS database in both source capsules. It binds272metal device terminals to their actual contact planes;100body/well terminals retain the two finite-contact common-body nodes. Every individual intrinsic parameter, resistor edge/value and capacitor attachment/value is preserved. A separate parser and resistor-graph collapse verifies all372native terminal identities without inserting original ideal aliases. Ten actual corrupted model files must be rejected.

This is a complete model within the declared metal/via and intrinsic scope. Poly/diffusion resistance, spatial substrate spreading and qualified RF extraction are not included. Electrical/PVT/loaded serializer simulations, actual tree integration and complete PHY/mainchip timing remain required. All source, results and failed controls are preserved in cloud.
