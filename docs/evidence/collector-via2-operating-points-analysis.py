import subprocess,json,hashlib,base64,time
R='repos/Melihakbulut221/nssoc/'
B='codex/complete-open-work'
def api(path,data=None,method=None):
 for attempt in range(4):
  cmd=['gh','api',R+path]
  if data is not None:cmd+=['--method',method or 'POST','--input','-']
  p=subprocess.run(cmd,input=json.dumps(data)if data is not None else None,text=True,capture_output=True)
  if p.returncode==0:return json.loads(p.stdout)if p.stdout.strip()else {}
  if data is not None or method not in(None,'GET')or attempt==3 or not any(x in p.stderr for x in('HTTP 502','HTTP 503','HTTP 504','TLS handshake','connection reset','unexpected EOF','i/o timeout')):raise RuntimeError(path+': '+p.stderr[:2000])
  time.sleep(2+attempt)
def remote(path,ref):
 d=api('contents/'+path+'?ref='+ref)
 if d.get('content'):return base64.b64decode(d['content'])
 return base64.b64decode(api('git/blobs/'+d['sha'])['content'])
def sha(b):return hashlib.sha256(b).hexdigest()
def publish(head,files,msg):
 parent=api('git/commits/'+head);entries=[]
 for p,b in files.items():
  if isinstance(b,str):b=b.encode()
  blob=api('git/blobs',dict(encoding='base64',content=base64.b64encode(b).decode()))
  entries.append(dict(path=p,mode='100644',type='blob',sha=blob['sha']))
 tree=api('git/trees',dict(base_tree=parent['tree']['sha'],tree=entries))
 commit=api('git/commits',dict(message=msg,tree=tree['sha'],parents=[head]))
 assert api('git/ref/heads/'+B)['object']['sha']==head
 api('git/refs/heads/'+B,dict(sha=commit['sha'],force=False),'PATCH')
 return commit['sha']

import io,zipfile
raw=subprocess.check_output(["gh","api",R+"actions/artifacts/13140329003/zip"]);assert len(raw)==120423 and sha(raw)=="16ffa363ead36ea95ae97cc579780a274d8015bca56fccdf8949f22f40793c77"
d=json.loads(zipfile.ZipFile(io.BytesIO(raw)).read("native-device-diagnosis.json"))
out={}
for name,v in d["failing_devices"].items():
 p={k:v[k]for k in ["at_s","ic_a","minimum_vce_v","vb_v","vc_v","ve_v","samples_below"]}
 p["collector_drivers"]=[];p["tail_mos"]=[]
 for dev in v["same_net_native_voltage_drops_at_minimum"]["C"]["connected_devices"]:
  if dev["native_id"]in[54,56,106,108]:
   t=next(x for x in dev["terminals"]if x["terminal"]=="E")
   assert t["same_extracted_net"]
   p["collector_drivers"].append(dict(native_id=dev["native_id"],emitter_v=t["voltage_v"],collector_path_drop_v=t["delta_from_failed_terminal_v"],all_terminals=dev["terminals"],device_scalars={k:v for k,v in dev.items()if not isinstance(v,(dict,list))}))
 for dev in v["same_net_native_voltage_drops_at_minimum"]["E"]["connected_devices"]:
  if dev["model"]=="sg13_lv_nmos":
   ts={t["terminal"]:t for t in dev["terminals"]}
   p["tail_mos"].append(dict(native_id=dev["native_id"],d_v=ts["D"]["voltage_v"],g_v=ts["G"]["voltage_v"],s_v=ts["S"]["voltage_v"],emitter_to_drain_drop_v=-ts["D"]["delta_from_failed_terminal_v"]))
 out[name]=p
print(json.dumps(out),flush=True)
