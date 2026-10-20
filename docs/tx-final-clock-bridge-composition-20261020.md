# Final-clock bridge distributed model composition

Native RC run39375552658 passed. Actual geometry produces3 wire resistors and8 capacitors across3 conductors. All6 reference planes remain connected at exact native grid positions. Native/export R topology and values, every point ground C, every mutual attachment/value and the complete collapsed C matrix agree. All13 saved raw-output/anchor corruption controls rejected.

The next cloud job composes exactly these3R8C elements with the two native devices, preserving all five device terminal identities and the finite81.6667ohm contact. The physical resistor remains W6um/L1.2um, ps0, b0, m1 and self-heating enabled. No body node or capacitance reference is silently joined to a supply. Twelve deliberately corrupted composed models must reject.

Expected model ports: sp sn sub wire_cref. The model is a candidate for the final clock differential pair in the original full32 TX simulation. Electrical acceptance requires that loaded simulation with unchanged clock PWL,25ohm source resistors,data,phases,device limits and timing gates. Mainchip integration, assembled physical routing, qualified PEX/substrate and PVT are not established by composition.
