# Hierarchical extracted timing qualification

The actual parent netlist instantiates `soc_top u_core`; its single declared module is `nssoc_chip`. Read the real routed core netlist alongside the actual parent netlist, link the parent, read parent SPEF first and then core SPEF with `-path u_core`. Do not use a blackbox core timing model, double-count the isolated core IO constraints, or silently promote this fixture to full-chip timing evidence.

Pinned OpenSTA 857316ff001b2a8dbbdc5996944d08a6d38c87ab `parasitics/SpefReader.cc` dspfBegin attaches hierarchical port nets to their parent net's existing parasitic network; top-level reading creates a fresh network. `ConcreteParasitics.cc` makeParasiticNetwork deletes an existing network. Therefore reversed read order can lose core contributions. Native cloud fixture must prove 0.01 pF parent + 0.02 pF child = 0.03 pF; reversed order and omitted-child controls must measure 0.01 pF, exposing the lost contribution.

Primary source: https://github.com/The-OpenROAD-Project/OpenSTA/blob/857316ff001b2a8dbbdc5996944d08a6d38c87ab/parasitics/SpefReader.cc

This test only qualifies accumulation at one hierarchical boundary in the pinned runtime. Actual net/terminal matching, both routed data sources, annotation coverage, cross-boundary coupling, SRAM corners, external IO budgets and CDC constraints still require separate verification. Existing internal 20 ns clocks and 5% derate are unchanged. No false paths or budget relaxations are introduced.
