# Full-layout input, isolated fill stages

Pinned IHP c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c, KLayout 0.30.7. Input is the original first-detail KLayout streamout, SHA-256 c8c79effcea9c03349272051318c302ae32cb710872d15135021ecf2ca7e5d56. The earlier [hosted sequential run](https://github.com/Melihakbulut221/nssoc/actions/runs/45710604045) stopped at KLayout.Filler with SIGKILL. Its log gives no failing source line.

Run each row on the same GDS with the flags listed. Use a separate output path per invocation. No layers are disabled in the product flow. The switches are the diagnostic isolation options documented in the PDK filler.py. These four runs used a 2304 MiB virtual-address limit, a 90 s wall limit and a writable scratch directory. Peak resident memory is the largest individual process VmRSS sampled every 0.25 s in the process group (KLayout in all rows). Bytes refer to the output GDS.gz, not all system I/O.

```sh
prlimit --as=2415919104 -- klayout -n sg13g2 -zz \
  -r "$PDK_ROOT/$PDK/libs.tech/klayout/tech/scripts/filler.py" \
  -rd output_file="$OUTPUT" "$@" "$INPUT"
```

| Stage | Additional -rd names | Seconds | Peak RSS KiB | Exit | Output bytes |
|---|---|---:|---:|---:|---:|
| Load and save | no_activ, no_metal, no_topmetal | 6.80 | 492068 | 0 | 14219243 |
| ActGatP | no_metal, no_topmetal | 22.95 | 1720540 | 1 | 0 |
| Metal | no_activ, no_topmetal | 18.80 | 493540 | 1 | 0 |
| TopMetal | no_activ, no_metal | 7.14 | 498552 | 0 | 14219244 |

Both failed stages reported std::bad_alloc in Region::size. ActGatP reached executable macro line 146, Poly_cpy.size(sep,sep,"square_limit"). Metal reached line 249, M1Fil_c.size(0.42,0.42,"square_limit"). The bound is on virtual space, so sampled resident usage does not establish required RAM for completion. Macro line numbers refer to the text inside the .lym XML. This experiment does not establish the allocator call behind the earlier hosted SIGKILL.

TopMetal targets EdgeSeal.holes from layer 39/0. A recursive KLayout region-area check on both the load/save control and successful TopMetal output measured zero area on 39/0, zero hole area and zero filler area on both 126/22 and 134/22. No eligible upper-metal fill domain exists in this snapshot. Full density remains open; use the design-authorized seal geometry and repeat the complete native fill and unchanged density deck. No synthetic boundary or waiver was introduced.
