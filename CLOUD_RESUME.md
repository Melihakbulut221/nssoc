# Cloud continuation — checkpoint v352

Updated: 2026-11-03T21:28:57.469342+00:00

## Actual gate resistance network and intrinsic partition prerequisites

Intrinsic partition41717942914/source30392de6e292c690fe73f469c32c236a5ce51b1c on codex/cdr-mos650-intrinsic-partition SUCCEEDED, release433212710. It runs160 native simulations across four actual geometries, N1/2/4/8/16 fractional replicas, two model libraries and four terminal AC excitations. All13696 DC/complex-admittance comparisons and KCL checks pass. The39-point DC grid covers Vg0..1.2 and Vd0.1/0.6/1.1; AC covers17 points1MHz..10GHz at Vg0.8/Vd0.6. Original physical dimensions and diffusion parameters remain unchanged. Only the separate RF model copy zeros RGO/RSHG, retaining RINT/RVPOLY/NQS. This is an equal-potential prerequisite, not a nonuniform gate or full circuit pass.

Actual gate poly mesh41721107217/source6fc562599fdc527bf95c0ef92332e87a4efd26e6 on codex/cdr-mos650-gate-poly-mesh SUCCEEDED, release433231218. It consumes exact current GDS c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c and wire41712243960. Native KLayout verifies50 complete gate poly groups,200 intrinsic electrodes,200 actual160nm contacts, exact M1 enclosure/centers/ownership, and no gate-poly intersection with SalBlock/pSD. Every finite-volume cell exactly tiles actual material. Contact patch conductances sum to the declared per-cut conductance; every intrinsic area has exact rational weights totaling1. The GDS is unchanged.

Meshes600/300/150/75nm each pass an independent native analytic70ohm rectangular-sheet reference and a full actual-geometry SPICE DC solve. In the diagnostic only, all real M1 contact ports are held at0V and uniform total1nA is injected into each of200 intrinsic electrodes. All gate averages are finite/positive; total contact return current is200nA. The75nm network has131310 cells,236268 poly resistors and1800 contact patches representing the original200 cuts. Complete native fragments, meshes, stdout/stderr and measurements are published.

The maximum uniform-injection gate-average changes are0.343038% for600->300nm,2.178391% for300->150nm and0.4297672% for150->75nm. These are scoped refinement observations, not general convergence. Nominal7ohm/square and15ohm/contact remain engineering inputs, with narrow-gate/temperature/corner calibration open. No nonlinear intrinsic devices or actual full metal network are yet connected to this mesh; full extrinsic C/MIM/substrate and loaded/serial acceptance remain open.

First mesh41719493627/source06256f3a50238a263a1c78472b9bd88af6ed7254/release433221919 FAILED after native material and first analytic reference passed. KLayout returned integral areas as floats; Fraction rejected the type. Successor41720040423/source6c1eb9d790cf5caeff98d10784e868e5e1113648/release433224938 checks finite exact integer areas below2**53 before conversion and passes all three initial pitches. No threshold, geometry or material value was relaxed. The complete failure is preserved.

The next concrete integration method, still unimplemented, is recorded in docs/cdr-mos650-gate-poly-coupling-next.md. It couples area-weighted gate voltage and reciprocal current to keep power and distinct contacts intact, then binds the current metalRC41713023974 and all actual650 device terminals. The fine mesh has535..600 patches per gate, so naive one-MOS-per-cell replication would be unnecessarily expensive. Any reduction must preserve port behavior and thermal noise.

Mainchip full64 route41699812301 remains separately monitored. No fullserialPHY, finished mainchip route, final setup/hold or production acceptance is claimed. All native work and archives remain cloud-only.


## Observed intrinsic partition and actual poly-network outcomes
[
  {
    "conclusion": "success",
    "partition-equivalence.json": {
      "all_original_model_files_unchanged": true,
      "comparisons": 13696,
      "copies": [
        1,
        2,
        4,
        8,
        16
      ],
      "current_physical_units": 200,
      "dc_grid": {
        "drain_V": [
          0.1,
          0.6,
          1.1
        ],
        "gate_V": [
          0.0,
          0.1,
          0.2,
          0.3,
          0.4,
          0.5,
          0.6,
          0.7,
          0.8,
          0.9,
          1.0,
          1.1,
          1.2
        ]
      },
      "distributed_gate_convergence_qualified": false,
      "electrical_accepted": false,
      "final_timing_complete": false,
      "full_pex_qualified": false,
      "full_phy_accepted": false,
      "gate_poly_RC_extracted": false,
      "independent_terminal_excitations": [
        "d",
        "g",
        "s",
        "b"
      ],
      "mim_intrinsic_composition_qualified": false,
      "native_commands": 160,
      "physical_gate_network_present": false,
      "substrate_r_modeled": false,
      "tolerances": {
        "admittance_absolute_S": 1e-14,
        "admittance_relative": 1e-07,
        "dc_absolute_A": 1e-12,
        "dc_relative": 1e-07
      },
      "unique_physical_dimensions": 4,
      "violations": [],
      "worst_ac_budget_fraction": 0.0052119953320583475,
      "worst_dc_budget_fraction": 0.016495369077731845
    },
    "result": {
      "bytes": 562,
      "record": {
        "actual_mos_units": 200,
        "context": {
          "attempt": 1,
          "run": 41717942914,
          "source": "30392de6e292c690fe73f469c32c236a5ce51b1c"
        },
        "electrical_accepted": false,
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "gate_resistance_qualified": false,
        "mim_intrinsic_composition_qualified": false,
        "status": "PASS_EQUAL_ELECTRODE_INTRINSIC_PARTITION_REQUIRES_PHYSICAL_NETWORK_AND_CONVERGENCE",
        "substrate_r_modeled": false,
        "unique_physical_dimensions": 4
      },
      "sha256": "6413bafdc7de2b69ca96754e099d8c2c257eccc195628a8327b77e2841830625"
    },
    "run": 41717942914,
    "source": "30392de6e292c690fe73f469c32c236a5ce51b1c"
  },
  {
    "conclusion": "failure",
    "result": {
      "bytes": 1589,
      "record": {
        "electrical_accepted": false,
        "error": "both arguments should be Rational instances",
        "error_type": "TypeError",
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "mim_intrinsic_composition_qualified": false,
        "substrate_r_modeled": false,
        "traceback": "Traceback (most recent call last):\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 465, in main\n    count=characterize(models)\n          ^^^^^^^^^^^^^^^^^^^^\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 394, in characterize\n    need(sum(x[\"area_dbu2\"]for x in patches)==total and sum(Fraction(x[\"weight_numerator\"],x[\"weight_denominator\"])for x in patches)==1,\"full intrinsic gate area and exact total weight\")\n                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/home/runner/work/nssoc/nssoc/scripts/cdr_mos650_gate_ac.py\", line 394, in <genexpr>\n    need(sum(x[\"area_dbu2\"]for x in patches)==total and sum(Fraction(x[\"weight_numerator\"],x[\"weight_denominator\"])for x in patches)==1,\"full intrinsic gate area and exact total weight\")\n                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/fractions.py\", line 277, in __new__\n    raise TypeError(\"both arguments should be \"\nTypeError: both arguments should be Rational instances\n"
      },
      "sha256": "923b189da8cd9f481aadac8f9244a66aae1da46c1cea373779453ec3f85c10b2"
    },
    "run": 41719493627,
    "source": "06256f3a50238a263a1c78472b9bd88af6ed7254"
  },
  {
    "conclusion": "success",
    "physical-gate-resistance-network.json": {
      "actual_intrinsic_devices_present": false,
      "electrical_accepted": false,
      "final_timing_complete": false,
      "full_metal_network_integrated": false,
      "full_pex_qualified": false,
      "full_phy_accepted": false,
      "gate_groups": 50,
      "gate_poly_RC_extracted": false,
      "intrinsic_gates": 200,
      "material_parameters": {
        "contact_ohm_per_160nm_cut": 15.0,
        "contact_range": [
          8,
          20
        ],
        "scope": "Nominal published salicided n-poly and M1/n-poly contact values; no narrow-gate calibration, temperature/corner qualification or full PEX claim.",
        "sheet_ohm_per_square": 7.0,
        "sheet_range": [
          6.2,
          7.8
        ],
        "source": "https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html"
      },
      "material_values_qualified_for_signoff": false,
      "mim_intrinsic_composition_qualified": false,
      "native_actual_mesh_DC_runs_passed": 3,
      "native_rectangle_references_passed": 3,
      "nonuniform_gate_convergence_qualified": false,
      "physical_contacts": 200,
      "physical_gate_resistance_network_generated": true,
      "pitches_nm": [
        600,
        300,
        150
      ],
      "refinement_observations": [
        {
          "coarse_pitch_nm": 600,
          "fine_pitch_nm": 300,
          "max_relative_gate_average_change": 0.0034303822796408453
        },
        {
          "coarse_pitch_nm": 300,
          "fine_pitch_nm": 150,
          "max_relative_gate_average_change": 0.02178390788373494
        }
      ],
      "substrate_r_modeled": false
    },
    "result": {
      "bytes": 558,
      "record": {
        "actual_mos_units": 200,
        "context": {
          "attempt": 1,
          "run": 41720040423,
          "source": "6c1eb9d790cf5caeff98d10784e868e5e1113648"
        },
        "electrical_accepted": false,
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "gate_resistance_qualified": false,
        "mim_intrinsic_composition_qualified": false,
        "status": "BUILT_ACTUAL_GATE_POLY_R_NETWORK_REQUIRES_INTRINSIC_AND_FULL_METAL_COMPOSITION",
        "substrate_r_modeled": false,
        "unique_physical_dimensions": 4
      },
      "sha256": "f13d97567e66f622a7ed8c5eee1162eced938807332268e3e8874757b46f7721"
    },
    "run": 41720040423,
    "source": "6c1eb9d790cf5caeff98d10784e868e5e1113648"
  },
  {
    "conclusion": "success",
    "physical-gate-resistance-network.json": {
      "actual_intrinsic_devices_present": false,
      "electrical_accepted": false,
      "final_timing_complete": false,
      "full_metal_network_integrated": false,
      "full_pex_qualified": false,
      "full_phy_accepted": false,
      "gate_groups": 50,
      "gate_poly_RC_extracted": false,
      "intrinsic_gates": 200,
      "material_parameters": {
        "contact_ohm_per_160nm_cut": 15.0,
        "contact_range": [
          8,
          20
        ],
        "scope": "Nominal published salicided n-poly and M1/n-poly contact values; no narrow-gate calibration, temperature/corner qualification or full PEX claim.",
        "sheet_ohm_per_square": 7.0,
        "sheet_range": [
          6.2,
          7.8
        ],
        "source": "https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html"
      },
      "material_values_qualified_for_signoff": false,
      "mim_intrinsic_composition_qualified": false,
      "native_actual_mesh_DC_runs_passed": 4,
      "native_rectangle_references_passed": 4,
      "nonuniform_gate_convergence_qualified": false,
      "physical_contacts": 200,
      "physical_gate_resistance_network_generated": true,
      "pitches_nm": [
        600,
        300,
        150,
        75
      ],
      "refinement_observations": [
        {
          "coarse_pitch_nm": 600,
          "fine_pitch_nm": 300,
          "max_relative_gate_average_change": 0.0034303822796408453
        },
        {
          "coarse_pitch_nm": 300,
          "fine_pitch_nm": 150,
          "max_relative_gate_average_change": 0.02178390788373494
        },
        {
          "coarse_pitch_nm": 150,
          "fine_pitch_nm": 75,
          "max_relative_gate_average_change": 0.0042976720037689415
        }
      ],
      "substrate_r_modeled": false
    },
    "result": {
      "bytes": 558,
      "record": {
        "actual_mos_units": 200,
        "context": {
          "attempt": 1,
          "run": 41721107217,
          "source": "6fc562599fdc527bf95c0ef92332e87a4efd26e6"
        },
        "electrical_accepted": false,
        "final_timing_complete": false,
        "full_pex_qualified": false,
        "full_phy_accepted": false,
        "gate_poly_RC_extracted": false,
        "gate_resistance_qualified": false,
        "mim_intrinsic_composition_qualified": false,
        "status": "BUILT_ACTUAL_GATE_POLY_R_NETWORK_REQUIRES_INTRINSIC_AND_FULL_METAL_COMPOSITION",
        "substrate_r_modeled": false,
        "unique_physical_dimensions": 4
      },
      "sha256": "7a4c498f0fe84b0dbb9358ffb43d2340c43d07efec6f00f9466a05c58581fa69"
    },
    "run": 41721107217,
    "source": "6fc562599fdc527bf95c0ef92332e87a4efd26e6"
  }
]


Observed 2026-11-03T21:28:57.469342+00:00:
- 41699812301: in_progress/None
- 41717942914: completed/success
- 41719493627: completed/failure
- 41720040423: completed/success
- 41721107217: completed/success


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/8933dbcb0e1f2e077ae15d94260c161f3f194e67/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
