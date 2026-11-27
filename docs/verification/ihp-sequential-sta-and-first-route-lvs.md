# Sequential STA and first-detail native LVS

These measurements refer to different layouts. The Ibex experiment used the two global-placement checkpoints. Native LVS used the earlier [first-detail layout and reference](ihp-first-detail-lvs-inputs.md).

## Sequential timing diagnostic

Both processes read their own step-19 OpenDB through the step-21 state. Each stopped at the first fast-corner hold report in step 23. Both min.rpt files contained 279 bytes of headings and no path. Candidate elapsed 8m57.727s with rounded peak RSS 9 GiB. Control elapsed 8m29.815s with rounded peak RSS 8 GiB. Both flow wrappers returned 1. Cgroup memory.max was 17179869184 bytes. Its cumulative OOM-kill count increased over these runs. Memory charged to the cgroup includes the tmpfs workspace (8,589,582,336 bytes of shmem at the later inspection after LVS). That later reading is not the instantaneous memory balance at either kill.

The upstream corner.tcl SHA-256 was e0096884c1929ed80506366ecc3e809c78c8493180e366fc095e2b09f5c36f53. After loading the ODB, timing/RC setup and corner, the first path query was:

```tcl
report_checks -sort_by_slack -path_delay min -fields {slew cap input net fanout} -format full_clock_expanded -group_path_count 1000 -corner $corner_name
```

The printed corner was nom_fast_1p32V_m40C. The declared list also included nom_slow_1p08V_125C and nom_typ_1p20V_25C. The interface SDC SHA-256 was 78ce832a94cc18fd7956ddabb136d00827047903f83d420ac52658f222869ca8. Timing derate was 5.0 percent. This is mid-PnR before detailed routing and final RC extraction. Splitting off later reports into fresh processes leaves the failing first query intact. Loading only one Liberty corner changes the setup and has no demonstrated equivalence here. No reduced report, endpoint filter, changed corner model or timing verdict is accepted as a substitute.

## First-detail native LVS result

The extended run reached comparison, returned process code 0, and logged `ERROR : Netlists don't match`. Deck-reported runtime was 1427.596960 seconds. The resulting extended.lvsdb SHA-256 was 622c56ffb4dff2547fd65c98f158bde09a549c30e1bbb4c92849f30bd4fd0ac5. The separate KLayout report reader was killed (137, make exit 2). The ASCII database can independently establish the negative result without expanding its geometry:

```sh
LC_ALL=C rg '^ X\(soc_top SOC_TOP ' extended.lvsdb
LC_ALL=C rg '^ X\(RM_IHPSG13_[12]P_.* RM_IHPSG13_' extended.lvsdb
```

The top record has status S and explicitly says the two circuits could not be compared because both SRAM macro comparisons failed. The single-port macro names layout-side RSC_IHPSG13_CDLYX1_DUMMY and RSC_IHPSG13_WLDRVX8 among its dependencies. Both macro records name additional unresolved reference-side subcircuits. The report establishes an incomplete top comparison, with no affirmative result for top connectivity. It does not establish a specific top-level open or short. The streaming inspection supports this negative finding only.
