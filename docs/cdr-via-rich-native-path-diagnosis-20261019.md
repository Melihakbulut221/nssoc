# Via-rich CDR native path diagnosis, 2026-10-19

Cloud run 39170038075 reproduces all original sampler failures and all 116 HBT voltage/current measurements from the complete unchanged binary captures. Both nominal cases still fail. The diagnostic success is not electrical acceptance.

The remaining 8/6 failed HBTs are in the XOR data comparison stages. Clock wire incident capacitance is 1.734 pF (cp) and 1.653 pF (cn); this includes coupling and is not an effective lumped load or RF-qualified PEX. Actual sampler load supply losses remain substantial despite the previously proven roughly 45–49% DC wire-resistance improvement. Clock crossing times vary by physical sampler; acceptance windows remain unchanged.

Next action: bind the dominant branches in all 64 new native supply/load-to-collector resistance calculations to the actual native raw node records and physical anchors. The largest new supply branch is R10067, 6.21653 ohm; the identified collector branch R1047 is 9.49825 ohm. Their actual geometry must determine the next repair; do not scale resistor values or replace the native waveform with a DC estimate. This commit launches that read-only extraction-record diagnosis on a GitHub-hosted runner.

The original route 39161219456 and full TX waveform 39158584151 remain live. Keep them. The local project directory remains empty. Full serial PHY, routed mainchip and final timing are still unproven.
