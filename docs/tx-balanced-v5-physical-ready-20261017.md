# TX v5 fresh physical flow prepared for qualified source

The manual workflow tx-balanced-v5-pre-physical-cloud.yml is prepared for run39060767622/source771aab7120fbaeb6154f094a87f2ef7f4c998b7c. Dispatch it only after all four actual native cases complete successfully. It first rejects any unfinished/failed/wrong-source run before downloading CAD, and then revalidates the complete nominal/hot/cold/fault summaries, controller SHA and both generated cell hashes against actual v5 geometry controls.

The physical generator creates freshNx1/Nx3cells with new_balanced_v5_layout_v1tops and cloud-tx-balanced-v5-preoutput. The original generator is pinned at312391426bd8505b6d6d32fdc5ffec7a76ddfc83b2f4d72543a40d6332e28a3f; exact declared adaptations hash2ff793a8293b3cf13261abdd430dfce4872cdc83ef4860b9f77dc19dc25e935a. All560DRCrules, deep/flat54deviceLVS and five fault controls are retained. Earlier rejected v3/v4 reports remain separate. No GDS or parasitic evidence is claimed until the native physical jobs pass.

After both leaves pass, rebuild the31macro parent, extract actual changed geometry/interconnect and simulate the loaded full32tree. Then frontends, clock/bias, RX/CDR/PLL, x4 and mainchip still need their own source-bound integration. A leaf pass is not a PHY or product pass.
