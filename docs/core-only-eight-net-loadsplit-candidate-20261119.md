# Eight-net load split candidate — 2026-11-19

Native inventory https://github.com/Melihakbulut221/nssoc/actions/runs/44553878161, artifact 14543794857 SHA256 cceb44389b870b32133aedec6e415fc47d54a33f8dea15ade05d1397b10b369b, verified against ODB bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc.

Prepare 21 sg13g2_buf_8 identity buffers across eight measured data nets. Group functional loads by physical coordinates and assign retained antenna diodes to the nearest group with space, never exceeding eight loads. Every new output group must include a functional load. All 44 affected diodes remain instantiated. No original instance may move, no clock route or unrelated net record may change, and collapsing inserted identity buffers must restore every original terminal connection. Check all 42 added power terminals and a native rail-removal negative control. This is a candidate: routing, antenna and fresh RC/STA are still required; constraints remain unchanged.

Groups (native loads including diodes):

```json
[
  {
    "driver": "nssoc_sta_i_8564",
    "net": "nssoc_sta_n_100391",
    "old_loads": 7,
    "groups": [
      3,
      4
    ]
  },
  {
    "driver": "nssoc_sta_i_52754",
    "net": "nssoc_sta_n_53514",
    "old_loads": 2,
    "groups": [
      2
    ]
  },
  {
    "driver": "nssoc_sta_i_63235",
    "net": "nssoc_sta_n_62713",
    "old_loads": 24,
    "groups": [
      2,
      6,
      8,
      8
    ]
  },
  {
    "driver": "fanout5181",
    "net": "net5181",
    "old_loads": 8,
    "groups": [
      4,
      4
    ]
  },
  {
    "driver": "nssoc_sta_i_78307",
    "net": "nssoc_sta_n_95189",
    "old_loads": 7,
    "groups": [
      3,
      4
    ]
  },
  {
    "driver": "nssoc_sta_i_78698",
    "net": "nssoc_sta_n_95548",
    "old_loads": 7,
    "groups": [
      3,
      4
    ]
  },
  {
    "driver": "fanout4366",
    "net": "net4366",
    "old_loads": 20,
    "groups": [
      3,
      6,
      7,
      4
    ]
  },
  {
    "driver": "fanout5013",
    "net": "net5013",
    "old_loads": 20,
    "groups": [
      8,
      6,
      4,
      2
    ]
  }
]
```

The source candidate has zero router DRC/native antenna violations and zero nominal-RC setup/hold violations. Electrical violations remain: 456 slow slew pins, 210 fanout pins, and 52/54/60 capacitance pins across slow/typical/fast corners. The new candidate is not admitted until all follow-up checks pass.
