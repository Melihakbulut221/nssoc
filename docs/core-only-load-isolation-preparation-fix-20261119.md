# Buffer preparation check repair

Run 44425640731, head 0d114ef7b9cfc36f7c835c5ad2a1abb4b33ce9b8, artifact 14484930255, SHA256 0ffb41b8b36970754ac3cf3606f5527792779f2da544b6371a2e07df2662e366 failed before writing the candidate, at the assertion comparing t.getNet() == net. The compound assertion does not identify which operand failed; no placement or timing success is claimed.

Replace proxy-object equality with explicit connected-net name equality in the same native block. Preserve the input-direction check and exact planned sink/driver list; add diagnostic values on failure. This avoids dependence on Python wrapper identity and makes a genuine connectivity discrepancy visible. Subsequent buffer-collapse connectivity, frozen geometry, legalization and supply checks remain unchanged. No reroute or signoff claim follows from this preparation fix.
