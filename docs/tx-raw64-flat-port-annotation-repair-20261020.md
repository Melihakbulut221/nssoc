# Repair standalone child port annotations after physical assembly

Run39464090686 produced actual64 handoff routes and256 power/body connections. Full560-category DRC had zero markers. Deep LVS matched all8074 devices and163 ports; the complete actual open, short and wrong-width controls rejected.

Flat LVS still rejected. Its circuit/device match alone was insufficient: the native deck explicitly failed strict port comparison. The extracted deep interface had163 ports, while flat extraction had227. Former core d0p..d31n labels were still exported as64 public ports on internal driver-to-core nets. Shared driver din/dout labels also created aliases such as d0p0|din and d0p|dout.

The candidate removes exactly64 former public core data labels and two labels in the shared driver master, restricted to port-text datatype25. Every actual material shape, terminal pin rectangle, substrate/device-recognition label, device parameter and physical connection remains. The163 explicit parent external labels remain authoritative. No port-check, device-census, native deck or audit gate is weakened.

All full native gates rerun. An additional real GDS fault reintroduces one internal data-port label and must fail flat strict-port LVS, even if the8074-device circuit comparison matches. Prior rejection and native reports are preserved. Full-parent RC, original fullwave electrical gates and mainchip integration remain open.
