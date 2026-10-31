#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source/receipt refusals only. These tests cannot qualify RTL behavior."""
import copy,json,os,unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import check_pcie_training_epoch_ingress as target

class Controls(unittest.TestCase):
    def setUp(self):
        self.m=json.loads(target.METHOD.read_bytes())
        self.raw={p:(target.ROOT/p).read_bytes()for p in self.m['protected']}
        self.env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Melihakbulut221/nssoc',
          GITHUB_REF='refs/heads/'+target.BRANCH,GITHUB_SHA='a'*40,GITHUB_EVENT_NAME='workflow_dispatch')
    def reject_manifest(self,mutate):
        m=copy.deepcopy(self.m);raw=dict(self.raw);mutate(m,raw)
        with self.assertRaises((AssertionError,KeyError,TypeError,ValueError)):target.validate_manifest(m,raw)
    def xml(self,module='test_pcie_training_epoch_control',mutation=None):
        root=ET.Element('testsuites');suite=ET.SubElement(root,'testsuite')
        for name in target.TESTS[module]:
            c=ET.SubElement(suite,'testcase',name=name,classname=module,
              file=str(target.BENCH/(module+'.py')),sim_time_ns='200')
            if mutation:
                if name==mutation['test']:ET.SubElement(c,'failure',error_type='AssertionError',error_msg=mutation['assertion'])
                else:c.attrib['sim_time_ns']='0';ET.SubElement(c,'skipped')
        return root
    def review(self,tree,mutation=None,returncode=0,log=''):
        return target.xml_review(ET.tostring(tree),'test_pcie_training_epoch_control',returncode,mutation,log)
    def test_actual_pinned_sources(self):
        self.assertEqual(target.pins()['base'],target.BASE)
    def test_actual_context_and_unchanged_environment(self):
        before=dict(os.environ);target.context(self.env,'a'*40)
        self.assertEqual(before,dict(os.environ))
    def test_context_refusals(self):
        for k,v in [('GITHUB_ACTIONS','false'),('GITHUB_REPOSITORY','wrong/repo'),
          ('GITHUB_REF','refs/heads/main'),('GITHUB_SHA','z'*40),('GITHUB_EVENT_NAME','push')]:
            with self.subTest(k=k):
                env=dict(self.env);env[k]=v
                with self.assertRaises(AssertionError):target.context(env,'a'*40)
        with self.assertRaises(AssertionError):target.context(self.env,'b'*40)
    def test_manifest_base_branch_schema_refusals(self):
        for key in ('base','branch','schema'):
            self.reject_manifest(lambda m,r,key=key:m.__setitem__(key,'wrong'))
    def test_each_protected_source_is_required_and_byte_bound(self):
        for p in self.raw:
            with self.subTest(path=p):
                self.reject_manifest(lambda m,r,p=p:r.pop(p))
                self.reject_manifest(lambda m,r,p=p:r.__setitem__(p,r[p]+b'\n'))
    def test_extra_source_and_nonbytes_refused(self):
        self.reject_manifest(lambda m,r:r.__setitem__('extra',b''))
        p=next(iter(self.raw));self.reject_manifest(lambda m,r:r.__setitem__(p,r[p].decode()))
    def test_native_authority_and_each_acceptance_refused(self):
        self.reject_manifest(lambda m,r:m.__setitem__('native_authorized',True))
        for k in self.m['physical_and_protocol_acceptance']:
            self.reject_manifest(lambda m,r,k=k:m['physical_and_protocol_acceptance'].__setitem__(k,True))
        with self.assertRaises(PermissionError):target.authorize_native(self.m)
    def test_positive_xml_is_complete(self):
        rows=self.review(self.xml());self.assertEqual(len(rows),6)
        self.assertTrue(all(r['disposition']=='PASS'for r in rows))
    def test_missing_extra_duplicate_case_refused(self):
        for kind in ('missing','extra','duplicate'):
            t=self.xml();s=t[0]
            if kind=='missing':s.remove(s[-1])
            else:
                c=copy.deepcopy(s[-1])
                if kind=='extra':c.attrib['name']='unreviewed'
                s.append(c)
            with self.assertRaises(AssertionError):self.review(t)
    def test_skips_errors_zero_nonfinite_time_refused(self):
        for kind in ('skip','error','zero','negative','nan','infinity'):
            t=self.xml();c=t[0][0]
            if kind in ('skip','error'):ET.SubElement(c,'skipped'if kind=='skip'else'error')
            else:c.attrib['sim_time_ns']={'zero':'0','negative':'-1','nan':'NaN','infinity':'inf'}[kind]
            with self.assertRaises(AssertionError):self.review(t)
    def test_wrong_oracle_identity_and_nonzero_return_refused(self):
        for key in ('file','classname'):
            t=self.xml();t[0][0].attrib[key]='wrong'
            with self.assertRaises(AssertionError):self.review(t)
        with self.assertRaises(AssertionError):self.review(self.xml(),returncode=1)
    def mutation_log(self,mu):
        p=target.BENCH/(mu['module']+'.py')
        lines=[i for i,s in enumerate(p.read_text().splitlines(),1)if mu['assertion']in s and 'assert 'in s]
        self.assertTrue(lines)
        return f'File "{p}", line {lines[0]}, in oracle\n'+mu['assertion']
    def test_exact_semantic_mutation_accepted(self):
        mu=self.m['mutations'][0];rows=self.review(self.xml(mutation=mu),mu,2,self.mutation_log(mu))
        self.assertEqual(sum(r['disposition']=='DETECTED_ASSERTION'for r in rows),1)
        self.assertEqual(sum(r['disposition']=='FILTERED_NOT_EXECUTED'for r in rows),5)
    def test_compile_error_timeout_and_wrong_mutation_assertion_refused(self):
        mu=self.m['mutations'][0]
        for field,value in [('error_type','TimeoutError'),('error_msg','compile failed')]:
            t=self.xml(mutation=mu);t[0][0][0].attrib[field]=value
            with self.assertRaises(AssertionError):self.review(t,mu,2,value)
        with self.assertRaises(AssertionError):self.review(self.xml(mutation=mu),mu,0,mu['assertion'])
        with self.assertRaises(AssertionError):self.review(self.xml(mutation=mu),mu,2,'wrong actual log')
    def test_xml_entity_and_size_refused(self):
        for raw in (b'<!DOCTYPE x><testsuites/>',b'<!ENTITY x><testsuites/>',b'x'*(2*1024**2+1)):
            with self.assertRaises((AssertionError,ET.ParseError)):target.xml_review(raw,'test_pcie_training_epoch_control',0)
    def test_compiled_mutation_anchors_are_exact(self):
        for mu in self.m['mutations']:
            raw=(target.RTL/mu['file']).read_text()
            self.assertEqual(raw.count(mu['old']),1)
            self.assertNotEqual(raw,raw.replace(mu['old'],mu['new']))
            self.assertIn(mu['assertion'],(target.BENCH/(mu['module']+'.py')).read_text())
    def test_source_oracles_never_read_private_hierarchy(self):
        for module in target.TESTS:
            s=(target.BENCH/(module+'.py')).read_text()
            self.assertNotIn('command_owner.',s);self.assertNotIn('.mailboxes',s)
            self.assertNotIn('force(',s);self.assertNotIn('deposit(',s)
        self.assertIn('table_rx.SerialOracle',self.raw['hw/soc/tb/cocotb/test_pcie_training_ingress.py'].decode())
        self.assertIn('self.gen3.next_word(k)',self.raw['hw/soc/tb/cocotb/test_pcie_training_ingress.py'].decode())

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(schema='epoch-ingress-source-refusal-controls-v1',source=os.environ['GITHUB_SHA'],
      tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
      native_executed=False,behavior_qualified=False),sort_keys=True),flush=True)
    raise SystemExit(not result.wasSuccessful())
