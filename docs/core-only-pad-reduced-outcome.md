# Reduced pad outcomes and next device isolation

Run44374874242/head0f3eb2ffea9745b557c034515d357df21251238d:
- decoder only: six captures complete50ns.
- decode_clamps (remove input receiver):0-turnoff still fails22.7529ns; other five captures complete.
- clamps with ideal gate drive:0-turnoff fails21.3262ns; other five complete. At failure ngate=0V,pgate=3V,pad=1.5V,current approximately-1.471nA. Failure is after the120ps gate ramp has ended.

All artifact hashes and79 declared output hashes per archive checked; finite waveforms and full increasing time for completed cases checked independently. Six failure-injection/readback tests passed in each matrix job. These are changed diagnostic circuits, never substitutes for full-pad acceptance. The unloaded decoder result does not prove it correct under every load.

The input receiver is not necessary to reproduce this numerical failure, and ideal gate sources do not cure it. Next split the output fixture into native NMOS clamp, individual forward/reverse-oriented native HV NMOS devices and antenna/protection paths. Keep model bytes,dimensions,PVT,tolerances unchanged and label omissions explicitly. Determine a minimal failing model circuit before any simulator/model correction. Do not alter product pinning or Liberty to hide the failure.

Separate full-pad1ps completed1-turnoff analysis (artifact14461386374, SHA25680014bf65ab48b5c61631af6ff4dedba20d9edcf158384744c9a7dab4eefa551) used linear interpolation on current normalized between10–19ns and40–49ns means: enable midpoint to50percent current1.5409975355ns;90–10percent current duration0.5135224229ns;80–20percent0.3012312671ns. These are current metrics under an ideal clamp, not Liberty voltage slew or permission to remove timing arcs.

Core route44337630426 remains active; independently admit and extract when terminal. Full production gates remain open. All diagnostic sources/artifacts are on GitHub.
