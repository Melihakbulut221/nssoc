# CDC local reset distribution — verified block change

The APB CDC bridge previously recombined raw system/link reset with each clock domain's synchronized release. That put raw asynchronous reset back into the reset trees of functional registers. The downstream response-register recovery path in the exact mainchip timing report exposed this connection.

Functional registers now use only their domain's release-flop output. Both two-flop release chains still assert asynchronously, including when a clock is stopped. No clock, CDC timing exception, or setup/hold gate was changed.

Cloud run [39886209079](https://github.com/Melihakbulut221/nssoc/actions/runs/39886209079), source3416142696a509035b27f9fb4e28c9b740080624, verified:

- The existing frozen-reference event equivalence: **217 proved points, zero unproved**. Clock/reset events and undefined memory semantics remain in the original proof.
- Actual mapping to **414 IHP cells**, using the pinned, unmodified standard-cell Liberty and Verilog models.
- The real mapped-cell port bench at three clock ratios, with **97 completed transfers per ratio**. The extended bench resets a stalled transaction while the source clock is stopped, releases reset before restarting that clock, and checks for stale requests or responses.
- Actual mapped reset connectivity: raw reset reaches only the **four release flops**. The **90 source-domain and89 destination-domain functional registers** use their respective local release outputs.
- Rejection of the mapped pre-change RTL, a raw-reset bypass fault and a wrong-domain reset fault.

The original pre-change RTL is retained as a fixture. Evidence hashes and complete native reports are preserved in docs/evidence/pcie-cdc-local-reset-pass-20261023.json and the linked run's release.

This closes the block-level raw reset reconvergence defect. It does **not** close chip recovery/removal, setup/hold, metastability qualification or physical reset distribution. Route11 still runs the immutable pre-change153130-cell netlist. Applying the change to the chip requires remapping or a separately verified netlist ECO, reset-tree routing, fresh extraction and the original all-corner timing checks. Legitimate first-stage synchronizer handling must remain separate from downstream functional reset paths.
