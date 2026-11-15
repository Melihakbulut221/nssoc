# Explicit PCIe root context refresh, 2026-11-15

Root CI43710889358/job132813745298 rejected stale source pins before dispatching four guarded PCIe modules. An independent audit of61protected files found exactly two pre-existing drifts: the epoch status document and soc_top.v. All other protected inputs matched. The new manifest retains both legacy manifests unchanged and admits only these exact old/new hashes plus existing nettype/workflow deltas. Removing a delta or changing any pinned byte must still be rejected. No acceptance scope flag is changed.

The document corrects historical verification status. soc_top.v adds optional CORE_BT_ALU, a dedicated system-reset leaf, and registered link/training/retrain inputs. These are semantic top-level changes, not comment-only changes or proven equivalent transformations. Existing shared/epoch/Gen12 standalone tests do not certify these top-level reset semantics or full serial PHY integration. Fresh dedicated root source/refusal controls and all88actual root RTL tests are required before merging this refresh; physical/main-chip boot requirements remain independent and open.

The fixture/source-refresh issue is separate and remains tracked. No frozen historical result is rewritten and no source gate removed. This file records exact reviewed context rather than asserting that current chip integration is qualified.

```diff
docs/pcie-training-epoch-ingress-20261031.md
--- admitted-root
+++ current-root
@@ -66,7 +66,10 @@
 A POR must reach every mailbox and both FIFO domains; asynchronous assertion and
 clean release plus CDC physical constraints remain integration obligations.
 
-## Planned cloud verification, not yet executed
+## Completed cloud verification
+
+Verified on 2026-11-14 against the retained [native result](evidence/pcie-training-epoch-native-41227114547/reports/result.json) and [terminal summary](evidence/pcie-training-epoch-native-41227114547/derived-terminal-summary.json): [run 41227114547](https://github.com/Melihakbulut221/nssoc/actions/runs/41227114547) passed all 110 positive tests without positive skips, six compiled semantic mutation detections, and four production hierarchy checks. These are historical executed results, not a new simulation run. The epoch-control, training-ingress, shared-front RTL and the two new test files still have the same Git blobs as the tested source. This corrects the stale pre-execution status; it does not establish normative TS/EQ/LTSSM behavior or full serial chip integration.
+
 
 The original source-only candidate and 16 passing controls are preserved at
 2a69d010371aff75fb8be204c92ef4c1d384d48e and run41226031156. Root and peer reviewed
@@ -74,11 +77,10 @@
 unchanged and requires the real dedicated epoch-rtl job, actual branch/HEAD,
 manual rtl mode and an explicit approved_source equal to that workflow's SHA.
 A separate empty exact-source release must already exist before tool provisioning
-or any simulation. Controls mode performs no native work. An activation source
-and passing source/refusal controls still require explicit dispatch review.
+or any simulation. Controls mode performs no native work. The reviewed activation was subsequently executed in run `41227114547`.
 
-Planned matrix: 110 positive named RTL tests, six compiled semantic mutants and
-four hierarchy checks. New command/actual-ingress tests run in Icarus and pinned
+Executed matrix: 110 positive named RTL tests, six compiled semantic mutants and
+four hierarchy checks, all passed at source `f2e452405f87aa079f79f604604294138fcfe261`. New command/actual-ingress tests run in Icarus and pinned
 Verilator5.040 at FIFO depths4/8/32 with EPOCH_W=2 (more than three complete wraps).
 The default16-bit controller elaborates in the native hierarchy census. The
 original50 shared-front/normal-event composition tests are retained unchanged.

hw/soc/rtl/soc_top.v
--- admitted-root
+++ current-root
@@ -233,12 +233,12 @@
     parameter integer REQ_REG = 0,
     // Timing candidates; historical configurations remain at zero. The
     // request register adds a cycle before fabric arbitration. Ibex's optional
-    // writeback stage separates ALU work from protected-register re-encoding.
-    // It also requires the dedicated branch-target ALU: the pinned core's
-    // shared-ALU branch path misdirects a taken branch stalled behind a store
-    // in writeback. tb_ibex_branch_stall retains that failing counterexample.
+    // writeback stage requires the dedicated branch-target ALU (the pinned
+    // core's shared-ALU path misdirects a taken branch stalled behind a store
+    // in writeback; tb_ibex_branch_stall keeps it). CORE_BT_ALU selects that
+    // ALU alone, without writeback stage (docs/ibex-execute-timing.md).
     parameter integer CORE_REQ_REG = 0,
-    parameter integer CORE_WB_STAGE = 0,
+    parameter integer CORE_WB_STAGE = 0, parameter integer CORE_BT_ALU = 0,
     // 256 ACCESS cycles = 5.12 us at 50 MHz. Normal register slaves,
     // including the CAN Wishbone bridge, respond in a few cycles.
     // Zero reproduces the historical unbounded bridge configuration.
@@ -605,7 +605,7 @@
       .RV32B           (0),
       .RV32ZC          (0),
       .RegFile         (0),
-      .BranchTargetALU (CORE_WB_STAGE),
+      .BranchTargetALU (CORE_BT_ALU != 0 ? 1 : CORE_WB_STAGE),
       .WritebackStage  (CORE_WB_STAGE),
       .ICache          (0),
       .ICacheECC       (0),
@@ -956,9 +956,18 @@
   wire [3:0] packet_pstrb;
 `ifdef SOC_PCIE_ASYNC
   wire packet_clk=pcie_clk_i;
+  // Dedicated leaf of the system reset for the packet-domain reset
+  // synchronizers below. It asserts with rst_raw_n, together with
+  // rst_sys_n, and releases one clk_i cycle after it. It drives only those
+  // synchronizers' reset pins, so their recovery path starts at this flop
+  // instead of the end of the CPU's rst_sys_n tree.
+  reg pcie_sys_rst_n;
+  always @(posedge clk_i or negedge rst_raw_n)
+    if (!rst_raw_n) pcie_sys_rst_n <= 1'b0;
+    else            pcie_sys_rst_n <= rst_sys_n;
   (* ASYNC_REG="TRUE" *) reg [1:0] packet_reset_release;
-  always @(posedge pcie_clk_i or negedge rst_sys_n)
-    if(!rst_sys_n) packet_reset_release<=0;
+  always @(posedge pcie_clk_i or negedge pcie_sys_rst_n)
+    if(!pcie_sys_rst_n) packet_reset_release<=0;
     else packet_reset_release<={packet_reset_release[0],1'b1};
   // The local release flop also clears with a stopped packet clock.
   // Avoid feeding the raw CPU reset into packet-domain data/output cones.
@@ -967,7 +976,7 @@
   // are deliberately unaffected. A write already accepted by APB remains.
   soc_pcie_apb_cdc u_pcie_cdc (
     .source_clk_i(pcie_clk_i),.destination_clk_i(clk_i),
-    .reset_ni(rst_sys_n && pcie_link_up_i && !pcie_retrain_done_i),
+    .reset_ni(pcie_sys_rst_n && pcie_link_up_i && !pcie_retrain_done_i),
     .s_psel_i(packet_psel),.s_penable_i(packet_penable),.s_pwrite_i(packet_pwrite),
     .s_paddr_i(packet_paddr),.s_pwdata_i(packet_pwdata),.s_pstrb_i(packet_pstrb),
     .s_pready_o(packet_pready),.s_pslverr_o(packet_pslverr),.s_prdata_o(packet_prdata),
@@ -984,9 +993,16 @@
   assign packet_pslverr=ep_bad_strobe || ep_pslverr;
   assign packet_prdata=ep_prdata;
 `endif
+  // Link status enters the packet domain through one flop each, so the
+  // boundary inputs do not fan out combinationally into every reset cone.
+  // All three move together and keep their relative timing.
+  reg pcie_link_up_q,pcie_training_q,pcie_retrain_done_q;
+  always @(posedge packet_clk or negedge packet_rst_n)
+    if(!packet_rst_n) {pcie_link_up_q,pcie_training_q,pcie_retrain_done_q}<=3'b0;
+    else {pcie_link_up_q,pcie_training_q,pcie_retrain_done_q}<={pcie_link_up_i,pcie_training_i,pcie_retrain_done_i};
   soc_pcie_buffered_flow_packets #(.APB_TIMEOUT(APB_TIMEOUT)) u_pcie (
-      .clk_i(packet_clk),.rst_ni(packet_rst_n),.link_up_i(pcie_link_up_i),
-      .training_i(pcie_training_i),.retrain_done_i(pcie_retrain_done_i),
+      .clk_i(packet_clk),.rst_ni(packet_rst_n),.link_up_i(pcie_link_up_q),
+      .training_i(pcie_training_q),.retrain_done_i(pcie_retrain_done_q),
       .function_id_i(pcie_function_id_i),.rx_data_i(pcie_rx_data_i),
       .rx_sop_i(pcie_rx_sop_i),.rx_eop_i(pcie_rx_eop_i),
       .rx_error_i(pcie_rx_error_i),.rx_valid_i(pcie_rx_valid_i),

```
