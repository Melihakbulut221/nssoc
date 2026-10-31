# Candidate PCIe training epoch ingress, 2026-10-31

This step implements command transport and typed record ownership before a semantic
training owner. It does not replace the packet-profile external flags in soc_top.
The full serial Gen3 x4 PHY, normative TS1/TS2/EQ acceptance, LTSSM, seed/lane/state
handoff to the normal consumer, analog PMA, stopped-clock detector, pad/ESD, layout
and final timing remain open. Source controls are not RTL or physical proof.

## Immutable origins and scope

Base: 1d9847cfd8c159a3faef5dd50cc05cdf364cdfc8.
The shared Gen3 front/normal-chain sources derive byte-for-byte from
64d31863ad2f5cd59483251dbe1dad8e7069c44e. Verification Makefile comes from
17033684f3dfd0c760ac7cf64d2e1dc1a4b2fdb0 (adds Verilator --timing).
The existing Gen1/2 collector, complete 192-bit record CDC, decoder/RD owner and
table oracle are frozen. Existing normal-chain oracles stay byte-identical.

Two new RTL modules:
- soc_pcie_training_epoch_control_v1: coherent command mailboxes and applied epoch.
- soc_pcie_training_ingress_x4_v1: actual frozen record front composition.

There are eight physical record FIFOs: four for Gen1/2, four in the single Gen3
shared front. Only the selected encoding's four-lane transport runs. There is
one Gen3 shared front and four Gen3 aligners; no second CDC is added in either
selected path. This is explicit in the planned native hierarchy census.

## Observable contract

A command contains encoding (00 Gen1, 01 Gen2, 10 Gen3; 11 rejected), four polarity
bits and four alignment-control bits. EPOCH_W defaults to 16 and supports 2..32.
Acceptance immediately closes old record admission and asynchronously asserts
coordinated resets in both complete transports. Old retained consumer state must
be discarded when epoch_active_o falls; there is no drain promise across a
command/abort. A normal-mode handoff without this reset needs a future semantic
owner and explicit descrambler/RD/state transfer.

A single in-flight request uses four phases: request high, all four lane acks and
PMA ack high, request low, all five acks low. The held payload cannot change in
any phase. Each recovered-domain mailbox samples it after a two-flop request
synchronizer. Its returned payload settles before the common two-flop ack
synchronizer is observed. The common owner compares every returned epoch,
encoding, polarity and alignment bit. Local mailboxes survive epoch resets and
abort; only common POR resets their four-phase history.

The PMA ack belongs to the common-clock interface and must acknowledge the same
held epoch and encoding, hold high until request falls, and then return low.
This external contract does not implement analog lock, clock generation or
clock continuity detection. A missing/stopped lane or PMA holds the command
pending; the DUT invents no PCIe timing constant or timeout. A clean reset/known
loss assertion is mandatory when external clock continuity is known to fail.

After the ack-low barrier, the selected front reset is released. No owner-visible
record and no ready retirement is allowed until all four selected common CDC
startup barriers are ready. command_success_o is a one-cycle completion witness
only then. Gen1/2 outputs preserve data128, K16, code-error16, disparity-error16,
comma16; Gen3 preserves all194 raw block bits, length3, SKP/EIEOS/realign metadata.
Each lane has independent ready. Physical lane index is not logical lane mapping.
No COM/OS/token count is promoted to TS accepted or link-up.

Short clean reset/abort pulses asynchronously latch an abort even if common or a
recovered clock stops. Reset or loss on any lane closes every lane's epoch.
Queued old records are reset across both FIFO domains. An interrupted handshake
finishes its low-ack phase before a new command; it cannot abandon an ack and
reuse its value. All FIFOs are flushed and all acks return low before each new
transaction, so modulo epoch wrap does not impose an artificial lifetime limit.
A POR must reach every mailbox and both FIFO domains; asynchronous assertion and
clean release plus CDC physical constraints remain integration obligations.

## Planned cloud verification, not yet executed

The original source-only candidate and 16 passing controls are preserved at
2a69d010371aff75fb8be204c92ef4c1d384d48e and run41226031156. Root and peer reviewed
the exact RTL and oracle bytes there. The activation adapter leaves those bytes
unchanged and requires the real dedicated epoch-rtl job, actual branch/HEAD,
manual rtl mode and an explicit approved_source equal to that workflow's SHA.
A separate empty exact-source release must already exist before tool provisioning
or any simulation. Controls mode performs no native work. An activation source
and passing source/refusal controls still require explicit dispatch review.

Planned matrix: 110 positive named RTL tests, six compiled semantic mutants and
four hierarchy checks. New command/actual-ingress tests run in Icarus and pinned
Verilator5.040 at FIFO depths4/8/32 with EPOCH_W=2 (more than three complete wraps).
The default16-bit controller elaborates in the native hierarchy census. The
original50 shared-front/normal-event composition tests are retained unchanged.

Independent oracles use public pins only: frozen standard-table Gen1/2 raw32
SerialOracle and frozen Gen3 bit-list Front.next_word, not DUT classifier output
or private FIFO/FSM state. They compare actual complete typed records, all32
bit offsets, error metadata, both polarities, variable SKP lengths, opaque pre-SDS
OS, held records and per-lane ready. Tests exercise queued records across encoding
changes/wrap, stopped/restarted/asymmetric clocks, short clean resets, actual FIFO
overflow, live caller-pin poisoning and wrong/missing PMA acknowledgments. A recovered clock also stops after its high
ack: abort during the low phase must keep admission/new-command blocked until
that lane resumes and its real low acknowledgment returns.

Compiled mutants must produce the exact independent behavioral assertion:
stale returned epoch, torn live command, lost lane ack, partial-lane ack barrier,
lost Gen3 realign metadata, truncated Gen3 record. Compile/setup errors, unrelated
timeouts, missing tests, skipped required cases and incorrect assertion origins
cannot qualify as detection. The bounded testbench deadline is not a DUT timer.

Existing authoritative full-training-oracle access remains unresolved; no new
normative rules or authorized-standard-access claims are invented here.

## Source review refinements before native execution

The candidate oracle slices each valid HDL lane before integer conversion, so an
unwritten invalid lane cannot contaminate another lane's comparison. Retirement
samples the actual ready pins at the observation edge. No unresolved bit of the
valid record is masked. A dedicated completion-edge abort test covers both clean
reset and external abort; the public success witness is directly qualified by
abort assertion, and the FSM also prioritizes the direct abort level. Source
review also adds the stopped-after-high-ack low-phase test described above.

Native hierarchy checks also require exactly four two-flop request synchronizers
and two four-bit acknowledgment stages. Their actual Yosys $adff D/Q, POR polarity
and reset values, recovered/common clock bindings and ASYNC_REG attributes are
recorded and checked. This is structural evidence; bundled-data setup/hold,
synchronizer placement/metastability parameters and asynchronous reset recovery
remain physical CDC/reset integration obligations, not qualified here.

## Reviewed activation adapter

The 110/6/4 candidate matrix and original50 shared-front cases are unchanged.
Pinned Verilator source51cdf52d0f3a3e59b51fd87762646a851e9f4aff, Python3.12 and
hash-pinned cocotb2.0.1/find_libpython0.4.0 match the qualified shared-front flow.
Actual Icarus/Yosys version evidence is retained. The exact source release helpers
are reused unchanged; the all-output publisher is the frozen shared-front
publisher with only candidate group/pin binding and the explicit native guard.
An existing partial release is refused, never overwritten. Native outputs and
compiled images remain entirely in GitHub. No physical acceptance flag changes.
