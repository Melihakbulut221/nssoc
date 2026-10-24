# Bridge metal graph and actual terminal planes

Native model run39374716164 passed all30 binding/model corruption controls. Both deep and flat extracted databases preserve one W6/L1.2 rppd and one A4/P8 finite contact. The contact model is81.66666666666666666666666668ohm using the original pinned PDK equation; the resistor body is not shorted to its public substrate port. Intrinsic model SHA256:41829ea61c863aff655b216d0b17e86fff0594cf385ea68ab09622d12d098679.

The new cloud stage extracts the actual metal/via graph without joining disconnected shapes by native net name. It checks every conductor polygon against its original native owner, resolves each public port and each device terminal at a real contact or PCell pin, and preserves both body terminals as distinct from metal reference planes.

Expected inventory: two devices, five terminals, three metal terminals, two body terminals, three public ports and three connected metal components. Six deliberate terminal-reference corruptions must reject, including swapping the two resistor endpoint planes.

The graph and planes are inputs for fresh distributed wire RC; this stage itself does not claim RC, electrical operation, qualified substrate or full PHY/mainchip integration. All results, including failures, are published in the cloud.
