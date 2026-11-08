# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Group the packet-domain worst paths by the RTL block that captures them.

  families.py <run.sh out_dir> [stage] [corner]

Reads <stage>_core_full_<corner>.rpt (worst path per endpoint, link status
and reset release excluded as startpoints) and prints, per family, the worst
slack, that path's cells and logic cells (cells other than buffers and
inverters), its start and end registers, and the deepest logic count of any
reported path in the family.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import full, logic_levels, register  # noqa: E402

FAMILIES = (
    ("replay store capture (soc_pcie_replay_tx)",
     r"retry\.(halt|source_error_o|bytes|lengths|next_store_sequence|count|tail|write_)"),
    ("replay send and reservation (soc_pcie_replay_tx)",
     r"retry\.(read_pos|replay_read_onehot|send|reserve_|new_slot|transmit_slice|head|sent_count|replay|timer|ack_|retries|acknowledged|input_crc|capturing|write_pos)"),
    ("credit reservation and FC update (soc_pcie_credit_tx)", r"flow\.credits\."),
    ("LCRC framer (soc_pcie_lcrc_tx)", r"transmit_packet\."),
    ("link transmit slice / DLLP merge (soc_pcie_reliable_packets)", r"packets\.(transmit_slice|link_)"),
    ("receive slice and consumers (dllp_rx, lcrc_rx, sequence_rx)",
     r"packets\.(receive_slice|slice_|rx_|receiver\.)|receive_packet\."),
    ("receive queue (soc_pcie_rx_credit)", r"receive_ownership\."),
    ("FC advertiser (soc_pcie_fc_tx)", r"advertiser\."),
    ("TLP register backend (soc_pcie_tlp_stream, soc_pcie_tlp_regs)", r"transaction_stream\.|endpoint\.endpoint\.(word_|byte_index|word_index|header_words)"),
    ("boundary arbiter and slice (soc_pcie_buffered_flow_packets)", r"u_pcie\.(boundary_slice|owner|locked|prefer)"),
    ("ACK/NAK transmit (soc_pcie_packet_tx, acknak_tx)", r"transmitter\."),
)


def main(out, stage="sized", corner="slow"):
    paths = full(Path(out) / f"{stage}_core_full_{corner}.rpt")
    print(f"{stage} {corner}: {len(paths)} worst-endpoint paths")
    print("family | worst slack | cells | logic cells | deepest logic | start -> end")
    for name, pattern in FAMILIES:
        rows = [p for p in paths if re.search(pattern, register(p.get("end", "")))]
        if not rows:
            print(f"{name} | none reported")
            continue
        worst = min(rows, key=lambda p: p["slack"])
        n, m = logic_levels(worst["cells"])
        deepest = max(logic_levels(p["cells"])[1] for p in rows)
        print(f"{name} | {worst['slack']:.2f} | {n} | {m} | {deepest} | "
              f"{register(worst['start'])} -> {register(worst['end'])}")


if __name__ == "__main__":
    main(*sys.argv[1:])
