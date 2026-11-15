# Clock output follower Nx5 trial

Source: run43751034595, commit71c9e88747cf83a498f29c19d4b8df7c433cab2f, derived artifact14179641397 SHA256 f8f60637b7f486a82cc85992ed8f9a0814eff8af88b9d0d2bb9c736b101aafdf. The electrical report rejects the candidate despite native return0 and no diagnostics. Positive followers peak at 3.114436595 mA/emitter against unchanged3mA gate. Phase response20.547192mV remains below30mV; sampler/data failures persist.

Change exactly six output followers Xfp_0..2/Xfn_0..2 from Nx4 to Nx5. Keep30 HBT instances; total emitters93->99. The native model declares Nx1..10; existing parser retains exact per-family census and model-card guard. This tests reduced per-emitter current; increased input capacitance may worsen timing. No predicted pass or physical-layout claim.

Same physical650 circuit5f66ce0c, current28458R/18384C/7MIM reduction, source composition43750397504. The clock buffer remains exploratory with ideal sizing resistors and is NOT physically implemented. Full256bit stimulus, all loads, solver settings, 100mV sample margin, 30mV phase threshold, device limits and data comparison functions unchanged. Acceptance still requires all original gates. FullPHY/mainchip/closed-loop/PVT/PEX remain open.
