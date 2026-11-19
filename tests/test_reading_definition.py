import hashlib
import json
import os
from pathlib import Path
import tomllib
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ReadingDefinitionTests(unittest.TestCase):
    def test_plan_is_development_only_and_budgets_remain_fixed(self):
        plan=tomllib.loads((ROOT/'configs/reading-study.toml').read_text())
        self.assertEqual(plan['status'],'ready_for_execution')
        self.assertEqual(plan['models'],['12b','31b'])
        self.assertEqual(plan['expected_runs'],len(plan['models'])*len(plan['arm_order'])*len(plan['development_tasks']))
        self.assertEqual(plan['controls']['max_turns'],48)
        self.assertFalse(plan['controls']['harness_auto_submit'])

    def test_prompt_arm_changes_only_system_prompt(self):
        for model in ['12b','31b']:
            original=ROOT/'submission_candidates'/model
            baseline=ROOT/'submission_candidates/reading_v1/baseline'/model
            candidate=ROOT/'submission_candidates/reading_v1/prompt'/model
            def files(folder):
                return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
            self.assertEqual(files(original),files(baseline))
            b,c=files(baseline),files(candidate)
            self.assertEqual(b.keys(),c.keys())
            self.assertEqual({p for p in b if b[p]!=c[p]},{'prompts/system.md'})

    def test_skill_arm_adds_only_declared_skill_interface_and_guidance(self):
        for model in ['12b','31b']:
            base=ROOT/'submission_candidates/reading_v1/prompt'/model
            candidate=ROOT/'submission_candidates/reading_v1/skill'/model
            base_files={str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()}
            candidate_files={str(p.relative_to(candidate)) for p in candidate.rglob('*') if p.is_file()}
            self.assertTrue(all(p.startswith('skills/focused-repo-reading/') for p in candidate_files-base_files))
            changed={p for p in base_files if (base/p).read_bytes()!=(candidate/p).read_bytes()}
            self.assertEqual(changed,{'agent.yaml','prompts/system.md'})
            self.assertFalse(list(candidate.rglob('*.py')))
            self.assertNotIn('w3lib_264',(candidate/'prompts/system.md').read_text())

    @unittest.skipUnless(os.environ.get('OFFICIAL_INTEGRATION_TESTS')=='1','run in official ADK env')
    def test_skill_reference_files_are_loadable_by_adk(self):
        from google.adk.skills import load_skill_from_dir
        skill=load_skill_from_dir(ROOT/'experiments/skills/focused-repo-reading')
        self.assertEqual(set(skill.resources.list_references()),{'tool_arguments.md','inspection_checkpoint.md'})
        for text in skill.resources.references.values():
            self.assertIsInstance(text,str)
            self.assertTrue(text.strip())

if __name__=='__main__':unittest.main()
