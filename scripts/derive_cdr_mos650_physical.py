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
 return text,edits
