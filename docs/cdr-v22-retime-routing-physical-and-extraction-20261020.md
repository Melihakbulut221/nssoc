# CDR v22 physical proof and fresh extraction — 2026-10-20

Cloud physical run 39454675485 passed the original full native DRC/LVS and fault controls. The GDS is ebbdf5d83b35c110409c8934058e838f59751d9088485c36bd4d78e5166e510c. The four cup/cun/dup/dun trunks moved to {'cun': 949.6, 'cup': 944.6, 'dun': 949.6, 'dup': 944.6}, removing 3423.2um of horizontal wire. The original 16 child instances, primitive geometry, external ports, schematic and LEF remain unchanged; v21 collector routes remain present.

The next workflow performs native planes, terminal/geometry capture, device binding and fresh metal RC extraction from this exact GDS. Dynamic per-stage receipts are created only from successful same-run release assets and must not overwrite precommitted receipts. Original extraction algorithms and fail-closed controls are preserved by exact source deltas.

Physical success does not prove CDR data or phase acceptance. Fresh MIM capture/composition and unchanged early/late/fault waveforms remain mandatory. No full PHY/mainchip signoff is claimed.
