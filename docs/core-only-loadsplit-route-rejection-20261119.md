# Load split route rejection and neighbor repair — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44556401044 failed independent native geometry checks. Artifact 14549202167 SHA256 45267cc8bfce04694c3483f5be8afeeda2703ff9e6c77e98d3d99e0b344dfe41, all 45 outputs verified. Rejected ODB 8205dd3cf5d8fe085b84768dd8b5facb7e525246cc1c6c6b0ddff853c9899fa3.

Router DRC reached zero at iteration 23; native antenna zero nets/pins. Instance/connection identity and 103086 unaffected net records / 2113 clock routes passed. Independent geometry found 22 contacts on Metal2; no disconnected nets or missing terminal geometry. Thus the candidate is rejected despite clean router metrics.

Measured contact counts:

```json
{
  "Metal2:nssoc_sta_n_62713:nssoc_sta_n_63701": 7,
  "Metal2:nssoc_loadsplit_3_net:nssoc_sta_n_62607": 3,
  "Metal2:net2514:nssoc_loadsplit_4_net": 3,
  "Metal2:nssoc_sta_n_62661:nssoc_sta_n_62713": 3,
  "Metal2:net4366:net4845": 3,
  "Metal2:net5013:nssoc_sta_n_43169": 3
}
```

Restart from the exact same admitted 21-buffer preparation ODB 3c55f2e88aff518b5483e10760b2d75042856d2b77616526bc731cb2083fd7c3, not from rejected metal. Release only these six additional neighbors: nssoc_sta_n_63701, nssoc_sta_n_62607, net2514, nssoc_sta_n_62661, net4845, nssoc_sta_n_43169. New route set: 35 nets. Preserve the other 103080 nonpower records and all 2113 clocks, native identity and NDR rules. All physical and antenna checks remain mandatory before fresh RC/STA.
