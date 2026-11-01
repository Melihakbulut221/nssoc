# Loaded sampler operating-point diagnosis

Two read-only GitHub diagnoses reproduce the entire original native result and add simultaneous operating points:

| Native case | Diagnostic run | Diagnostic source | Full 29-file proof |
| --- | --- | --- | --- |
| Rejected24-resistor master/buffer | 41277766243 | 84d7f18fa89ac715ee242d17cd2dfdbeb51dce14 | 5fa4b869e7b10c5ceedd5265ec1ffc4561a8e1e9 |
| Rejected16-resistor q20 | 41278288991 | bb6ab5d1aa4a9e4b796ba8db40069d9d4902da61 | d0d1c4a8441ce8bb85997bd73e45eb87f66bd93e |

Each passed7frozen-reader and13event/operating-point controls. All124HBT metrics, all6stages and1530bit delays, phase and VI values reproduce the complete original report. All109 native archive members are verified on a GitHub runner. No simulation, stimulus change, geometry mutation or local native download occurs. Current equality at3mA/emitter remains a failure.

For each stage, the full result records all124HBT C/B/E/S voltages and collector currents at two common times: the original deadline for the worst-delay bit and the worst original sampled margin. The same interpolation time is used throughout a snapshot; finite vectors, strictly increasing time and in-capture interpolation are required. These simultaneous observations avoid combining unrelated extrema.

## Observations

In q20, at the X deadline for bit229 (30.7625ns), samplerA is2.235964/1.997223V and samplerC is2.007809/2.190464V. The following AD nodes are1.780820/1.903942V and CD nodes1.805119/1.857308V; S0 nodes are1.183484/1.196722V. X signed margin is-0.116870mV and Y signed margin2.614882mV at their75ps deadline.

At bit255's X sample (34.0125ns), q20 A is1.993740/2.240795V, C2.214440/1.981057V, AD2.017691/1.660620V, CD1.997915/1.658660V, and X signed margin-115.284513mV. These are measured voltages at one time, not a demonstrated causal model or proposed fix.

Static inspection of the authenticated candidate composition identifies separate divider networks:
* AQP cluster88 throughR227 L3.6um/W1 to cluster139 (Q123 base), withR228 L21.6um/W1 toavss and MIM273 3.6x3.6um acrossR227.
* AQN cluster87 similarly usesR229/R230/MIM274 toQ125 base cluster140.
* CQP cluster118 usesR238/R239/MIM277 toQ128 base cluster152.
* CQN cluster117 usesR240/R241/MIM278 toQ130 base cluster153.

All four buffer HBTs haveNx2, le.9um/we.07um. They are not directly connected input bases; divider and feedforward dynamics must be examined together with HBT loading. A output clusters87/88 also connect hold pair87/88, data pair89/91 and follower bases121/124, allNx4. This fanout is relevant to the unresolved A delay. Complete primitive records and simultaneous currents remain in the proofs.

In q15, Q89/91 maximum recorded current per emitter is about2.115mA, withNx4; Q123/125 about1.223/1.263mA, Q128/130 about1.083/1.095mA, withNx2. These are the existing device extrema. They do not predict current after resizing or certify a safe operating area.

The public IHP [npn13G2 PCell source](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/main/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py) exposes Nx from1to10 and fixed default le/we. It also annotates collector-current limits by voltage. Any sizing change must be checked against the actual pinned PDK/model and operating envelope; the current nominal screening gate alone is not production approval. No change of emitter count, divider or capacitor has been implemented by this diagnosis.

## Corrected selector identity

The initial transfer analysis incorrectly assigned the S0/S1 divider input to B. The authenticated native composition instead binds DQP/DQN clusters18/17 throughR234/R236 to bases150/151, shared byQ131/Q149 andQ132/Q150. The topology guard refused the wrong assumption. See [actual transfer topology](cdr-sampler-transfer-topology.md) for full failure proofs and the corrected preflight.

## Next bounded work

Use the preserved full wave and complete composition to quantify transfer from A/C/D outputs into the divider bases and buffered AD/CD/S0/S1 nodes at the failing deadlines. Separate sampler delay from downstream settling. Qualify a controlled edit to the identified path only after confirming its complete native identity, current/voltage constraints and model support. Keep all original external load, source, timing and voltage gates.

The original static8GHz screen is still rejected. Closed-loop CDR, complete serialGen3x4PHY, newphysicalDRC/LVS/freshRC and finalchip timing are not established by this diagnosis.
