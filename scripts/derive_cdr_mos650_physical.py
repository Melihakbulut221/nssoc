"""Preserve the frozen full physical checker while adapting its explicit MOS census."""
def derive(text,width):
 edits=[]
 def change(before,after,count=1):
  nonlocal text
  assert text.count(before)==count,(before,text.count(before))
  text=text.replace(before,after);edits.append(dict(before=before,after=after,count=count))
 change('assert sum(EXPECTED_CENSUS.values())==500','assert sum(EXPECTED_CENSUS.values())==500\nEXPECTED_CENSUS=dict(EXPECTED_CENSUS,sg13_lv_nmos=200)\nassert sum(EXPECTED_CENSUS.values())==650')
 change('result["circuits"][0][key] != 500','result["circuits"][0][key] != 650')
 change('PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS','PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS')
 for before,after in [
  ("'Qsc_GP'","'QSC_GP'"),("'Msc_GT0'","'MSC_GT0_U0'"),
  ("f[2]=='irc'","f[2]=='IRC'"),("f[2]='avss'","f[2]='AVSS'"),
  (" w=53.335u "," w="+width+" "),
  ("Qac_D0 avdd aqp cup BULK ","QAC_D0 AVDD AQP CUP BULK "),
  ("Qac_D0 cup aqp avdd BULK ","QAC_D0 CUP AQP AVDD BULK "),
  ("('sa','sb')","('SA','SB')"),("('Rac_','Rbd_')","('RAC_','RBD_')"),
  ("('Rda_D4','Rdc_D4')","('RDA_D4','RDC_D4')"),
  ("'Rsc_DN'","'RSC_DN'"),("'Rsc_DP'","'RSC_DP'"),
  ("'Rsd_DN'","'RSD_DN'"),("'Rsd_DP'","'RSD_DP'")]:
  count=text.count(before);assert count>=1,(before,count)
  change(before,after,count)
 # Preserve each original phase body, but record independent positive failures
 # so a DRC failure cannot conceal the actual deep/flat LVS diagnosis.
 start=text.index("            directory = out / name")
 end=text.index("        if any(digest(p) != h for p, h in pins.items()):",start)
 body=text[start:end]
 wrapped="""            if name not in ("drc","lvs","lvs_flat"):
                prerequisite="drc" if name=="offgrid" else "lvs"
                if record["steps"].get(prerequisite,{}).get("status")!="PASS":
                    record["steps"][name]=dict(status="NOT_RUN_FAILED_PREREQUISITE",prerequisite=prerequisite)
                    save()
                    continue
            try:
"""+ "".join("    "+line if line.strip()else line for line in body.splitlines(keepends=True))+"""            except Exception as error:
                record["steps"].setdefault(name,{}).update(status="FAIL",error=repr(error))
                save()
        if any(v.get("status")!=("PASS" if n in ("drc","lvs","lvs_flat") else "REJECTED_EXPECTED_FAULT") for n,v in record["steps"].items()):
            raise ValueError("One or more full physical phases failed or prerequisite prevented fault qualification")
"""
 change(body,wrapped)
 return text,edits
