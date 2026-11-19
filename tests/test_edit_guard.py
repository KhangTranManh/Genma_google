import unittest,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('edit_guard',ROOT/'scripts/harness/edit_guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
SRC=(ROOT/'experiments/hint_ladder_v2/source.txt').read_text()
REGION=g.Region('_baseurl_re =','_meta_refresh_re')
OLD='r"<base\\s[^>]*href'
def call(old,new,**extra):return [{'name':'edit_file','arguments':dict(filepath='w3lib/html.py',old_string=old,new_string=new,**extra)}]

class Tests(unittest.TestCase):
    def test_ok_edit(self):
        r=g.check_edit(call(OLD,'r"<base\\s[^<>]*href'),SRC,'w3lib/html.py',REGION)
        self.assertEqual(r['status'],'ok');self.assertIn('[^<>]*',r['after'])
    def test_identical_strings_noop(self):
        self.assertEqual(g.check_edit(call(OLD,OLD),SRC,'w3lib/html.py',REGION)['status'],'noop')
    def test_out_of_region(self):
        self.assertEqual(g.check_edit(call('_ent_re = re.compile(','_ent_re = re.compile( '),SRC,'w3lib/html.py',REGION)['status'],'out_of_region')
    def test_not_found_and_invalid(self):
        self.assertEqual(g.check_edit(call('nope<<','x'),SRC,'w3lib/html.py',REGION)['status'],'not_found')
        self.assertEqual(g.check_edit(call(OLD,'x')+call(OLD,'y'),SRC,'w3lib/html.py',REGION)['status'],'invalid')
        self.assertEqual(g.check_edit([{'name':'edit_file','arguments':{'filepath':'other.py','old_string':OLD,'new_string':'x'}}],SRC,'w3lib/html.py')['status'],'invalid')
    def test_reask_once_then_accept(self):
        replies=[call(OLD,OLD),call(OLD,'r"<base\\s[^<>]*href')];notices=[]
        def gen(notice):notices.append(notice);return replies[len(notices)-1]
        r=g.guarded_call(gen,SRC,'w3lib/html.py',REGION)
        self.assertEqual(r.check['status'],'ok');self.assertEqual(r.generations,2);self.assertIsNone(notices[0]);self.assertIn('identical',notices[1]);self.assertEqual(len(r.events),1)
    def test_reask_limited_to_one(self):
        r=g.guarded_call(lambda n:call(OLD,OLD),SRC,'w3lib/html.py',REGION)
        self.assertEqual(r.check['status'],'noop');self.assertEqual(r.generations,2);self.assertTrue(r.events[-1]['final'])
    def test_invalid_not_reasked(self):
        r=g.guarded_call(lambda n:call(OLD,'x')+call(OLD,'y'),SRC,'w3lib/html.py',REGION)
        self.assertEqual(r.generations,1);self.assertEqual(r.check['status'],'invalid')
    def test_not_found_reasked(self):
        r=g.guarded_call(lambda n:call('nope<<','x'),SRC,'w3lib/html.py',REGION)
        self.assertEqual(r.generations,2);self.assertEqual(r.check['status'],'not_found')

class Dedup(unittest.TestCase):
    def test_repeated_identical_noop_calls_are_noop(self):
        r=g.check_edit(call(OLD,OLD)*5,SRC,'w3lib/html.py',REGION)
        self.assertEqual(r['status'],'noop');self.assertTrue(r['deduplicated_identical_calls'])
    def test_repeated_identical_real_edit_ok(self):
        self.assertEqual(g.check_edit(call(OLD,'r"<base\\s[^<>]*href')*3,SRC,'w3lib/html.py',REGION)['status'],'ok')
    def test_truncated_trailing_call_dropped(self):
        cut=[{'name':'edit_file','arguments':{'filepath':'w3lib/html.py','new_string':'_baseurl_re ='}}]
        self.assertEqual(g.check_edit(call(OLD,OLD)*4+cut,SRC,'w3lib/html.py',REGION)['status'],'noop')
    def test_different_calls_still_invalid(self):
        self.assertEqual(g.check_edit(call(OLD,'a')+call(OLD,'b'),SRC,'w3lib/html.py',REGION)['status'],'invalid')

class Multi(unittest.TestCase):
    R2=[g.Region('_baseurl_re =','_meta_refresh_re'),g.Region('_ent_re =','_tag_re')]
    def test_two_edits_two_regions(self):
        c=call(OLD,'r"<base\\s[^<>]*href')+call('(?P<semicolon>;?)','(?P<semicolon>;)')
        r=g.check_edits(c,SRC,'w3lib/html.py',self.R2);self.assertEqual(r['status'],'ok');self.assertEqual(r['n_edits'],2)
    def test_edit_outside_all_regions(self):
        r=g.check_edits(call('_meta_tag_re = re.compile(','_meta_tag_re = re.compile( '),SRC,'w3lib/html.py',self.R2)
        self.assertEqual(r['status'],'out_of_region')
    def test_noop_reported(self):
        self.assertEqual(g.check_edits(call(OLD,OLD)*3,SRC,'w3lib/html.py',self.R2)['status'],'noop')

if __name__=='__main__':unittest.main()
