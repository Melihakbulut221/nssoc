from pathlib import Path
import json,hashlib
B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
r=json.loads((B/"saved-controls-peer-vco03-before-note.json").read_text())
r["reviewer_diagnostic_correction"]={'scope': 'Initial independent reader assumed incorrect raw witness token spelling; original method/log retained. Corrected to actual frozen V23_ADJACENT_WITNESSES and exact raw field names; no DUT/test/source changes or reruns.', 'initial_method': {'bytes': 9633, 'sha256': '4185e7f246184c51112b172e5a5444f947105c5b64d0ba93df194ff0fb39d34c'}, 'initial_log': {'bytes': 273, 'sha256': 'e6bf2cedc07930ae24a23cf431963a4dd7c1603e0343b71e4c089ec4c5ee861e'}}
r["additive_note_method"]=pin(Path(__file__))
(B/"saved-controls-peer-vco03.json").write_text(json.dumps(r,indent=2)+"\n")
print(pin(B/"saved-controls-peer-vco03.json"))
