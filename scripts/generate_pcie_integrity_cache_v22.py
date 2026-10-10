#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One cache-content writer may update inside an atomically invalidated epoch."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v21.v"
SOURCE_SHA = "740757e328072118e57a775cf7987f942bd44c2f4e411484f9f1aeac8310ae78"
OLD = "     if(step && !fault_now) slot_verdict[cache_slot]<=next_value;"
NEW = "     if(step) slot_verdict[cache_slot]<=next_value; // V22 invalid cache content is quarantined."
OLD_COMMENT = " // matching verdict updates. Faulted/aborted steps cannot update either array."
NEW_COMMENT = " // matching verdict updates. V22 permits cache-only writes in a fault-invalidated epoch."


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    assert text.count(OLD) == text.count(OLD_COMMENT) == 1
    return text.replace(OLD, NEW).replace(OLD_COMMENT, NEW_COMMENT).replace("integrity_v21", "integrity_v22")


def inverse(text):
    assert text.count(NEW) == 1
    assert text.count(NEW_COMMENT) == 1
    restored = text.replace(NEW, OLD).replace(NEW_COMMENT, OLD_COMMENT).replace("integrity_v22", "integrity_v21")
    assert hashlib.sha256(restored.encode()).hexdigest() == SOURCE_SHA
    return restored


if __name__ == "__main__":
    text = candidate()
    assert inverse(text) == SOURCE.read_text()
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v22.v").write_text(text)
