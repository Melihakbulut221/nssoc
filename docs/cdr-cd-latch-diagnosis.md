# Same-time C/D latch diagnosis

Run41282425236/sourceae6db2f7ee9a11bad03154f5401ca9837a3db6fb passed actual topology/current identity checks using existing q15-derived wave diagnostics031a9d3d6554b1574f4ba609279d3543cff03b8e. It did not simulate the later A/C-divider candidate. Full13-file proof007ac2338efc578c90ffb827e48b2ab0d31000dd, docs/evidence/cd-latch-diagnosis-41282425236. Thirteen is the proof file count, not a test count.

The diagnosis authenticates all500 devices and124HBT identities, complete follower/input-buffer/master/slave/hold/clock topology and same-time voltage/current identities. C followers areQ121/Q124, notQ122; D followersQ69/Q70. Master data clocks usecn, masterholdcp, slavedatacp andslaveholdcn.

At the original worst sample3.1ns, cp=1.3987045V, cn=1.1771133V. C master output/slave input differential magnitude140.084623mV becomes33.754185mV at the sampled slave output; D157.171451mV becomes22.772750mV. These140–157mV values are slave inputs, not master inputs. C/D master input differential magnitudes are115.949mV/206.510mV.

C/D slave differential collector currents are4.212637/4.548597mA, total5.152850/5.215113mA. Slave data clock totals4.992668/5.003827mA; hold-clock currents34.695919/32.220982uA. Slave hold total collector currents0.960992/0.859176mA are transient observations; incomplete terminal-current capture does not establish DC KCL or a short. Distinct distributed-RC leaf nodes of the same native nets can have different transient voltages.

Four retained events cover the worst C/D deadlines and worst samples. Strong sampled slave-input differential with weak sampled output motivates a controlled split A/B versus C/D load experiment; it does not prove the resize will work. All original acceptance limits remain unchanged.
