# Packed paired650 buffer/comparator layout candidate

The failed actual loaded PHY waveform showed weak comparator drive. Native circuit analysis measured ADP/ADN external metal capacitance of467/496fF and collector-to-base effective metal resistance up to124.7/132.7ohm. These are diagnostic metal values; intrinsic device loading and finite driver resistance add other effects.

This candidate shortens physical interconnect without changing transistor dimensions, resistor geometries, bias, clock, expected data or electrical acceptance thresholds. It preserves the first six sampler/clock bands and translates the later ten complete bands in the existing paired order. A16um gap is applied to actual material occupancy, including child bounds and parent labels. All local overlays and16 primitive child instances are retained. The37 global TM1 trunks are rebuilt using exact physical via incidence. The resulting GDS is independently read back and checked layer by layer; deleting a real trunk or native contacts is detected.

Total signal trunk length is23738.76um versus25676.76um in the preceding paired geometry (about7.55% shorter). No individual signal trunk grew. This is a geometric result, not demonstrated bandwidth or timing closure. The upper occupied extent shrank329.4um; supply trunks retain their original border endpoints, so no total bbox reduction is claimed.

Generation: run43639421390, sourcedbe212de5ae00036284f104d45742db443186f51. Candidate GDS SHA256ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193. Native artifact14131740193 remains in cloud. See the generation receipt for exact artifact hashes and each trunk comparison.

Full native validation [run43640075616](https://github.com/Melihakbulut221/nssoc/actions/runs/43640075616) passed the unchanged independent650-device schematic checks: zero violations across560 DRC categories, deep/flat LVS matches of650/650 devices, and rejection of all13 fault cases. The first run stopped because of a bounded memory-counter observation timeout; the corrected monitor passed regression controls before the entire physical suite was rerun. See [physical evidence](evidence/paired650-packed-physical-20261115.json).

Fresh native identity/conductor extraction is running in run43640446032. Pending stages are exact-source terminal anchors and metal RC, intrinsic/gate composition, and the unchanged whole-loaded transient gates. Physical verification alone does not establish electrical timing. Full serial PCIe PHY and main-chip integration remain incomplete.
