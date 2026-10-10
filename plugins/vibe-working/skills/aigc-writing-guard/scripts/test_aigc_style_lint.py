"""Mechanical regression, not an independent semantic quality evaluation.

Real-source cases are recorded separately from synthetic calculation cases.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import aigc_style_lint as lint


class LintRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.en = lint.load_policy(lint.EN_PATTERN_PATH)
        cls.fixtures = json.loads((lint.SKILL_ROOT / 'scripts/fixtures/en-source-cases.json').read_text())['cases']
        cls.sources = {c['id']: c for c in cls.fixtures}

    def cli(self, *args, text=''):
        return subprocess.run([sys.executable, str(Path(lint.__file__)), *args], input=text,
                              text=True, capture_output=True, check=False)

    def test_zh_behavior_matches_frozen_baseline(self):
        baseline = json.loads((lint.SKILL_ROOT / 'scripts/fixtures/zh-compatibility.json').read_text())
        for case in baseline['cases']:
            with self.subTest(text=case['text'][:24]):
                self.assertEqual(lint.analyze_languages(case['text'], 'zh'), case['report'])

    def test_real_source_cases(self):
        lint.english_self_test()

    def test_zh_source_cases(self):
        lint.zh_source_self_test(lint.load_policy(lint.DEFAULT_PATTERN_PATH))

    def test_zh_density_floor_and_heading_prefix(self):
        zh = lint.load_policy(lint.DEFAULT_PATTERN_PATH)
        # synthetic coordinate tests only; not few-shot material
        self.assertEqual(lint.analyze('该参数尚未生效。', zh)['hits'], [])
        ordinal = lint.analyze('## 六、一次完整执行：CI 故障修复\n\n## 七、系统选型', zh)
        self.assertNotIn('coordinated_heading', {h['rule_id'] for h in ordinal['hits']})
        judged = lint.analyze('## 一、系统分层：模型提出下一步，系统负责执行和保存', zh)
        self.assertNotIn('coordinated_heading', {h['rule_id'] for h in judged['hits']})

    def test_auto_languages_and_cross_line_locations(self):
        # Synthetic line wrapping tests only; no new semantic example.
        source = self.sources['genome_author_positioning']['text'].replace('By contrast,', 'By\ncontrast,')
        report = lint.analyze_languages(source, 'auto')
        hit = next(h for h in report['hits'] if h['rule_id'] == 'en_contrast_scope')
        self.assertEqual((hit['line'], hit['column']), (1, 1))
        mixed = lint.analyze_languages('诚实说：数据不足。\n\n' + source, 'auto')
        self.assertEqual(mixed['languages'], ['zh', 'en'])
        self.assertIn('honesty_preface', {h['rule_id'] for h in mixed['hits']})
        self.assertIn('en_contrast_scope', {h['rule_id'] for h in mixed['hits']})

    def test_distribution_cannot_raise_severity(self):
        text = self.sources['avengers_participial_result']['text']
        once = lint.analyze(text, self.en)
        repeated = lint.analyze('\n\n'.join([text] * 12), self.en)
        self.assertEqual(repeated['distribution_signals']['metrics']['participial_tails']['count'], 12)
        self.assertEqual({h['severity'] for h in once['hits']}, {'low'})
        self.assertEqual({h['severity'] for h in repeated['hits']}, {'low'})
        self.assertTrue(all(h['semantic_severity'] is None for h in repeated['hits']))
        self.assertEqual(repeated['coverage']['overall_review'], 'incomplete')

    def test_colons_are_distribution_only(self):
        text = '\n\n'.join([self.sources['muse_formula_colon']['text']] * 8)
        result = self.cli('--lang', 'en', '--fail-on', 'low', '--format', 'json', text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['distribution_signals']['metrics']['prose_colons']['count'], 8)
        self.assertEqual(report['hits'], [])

    def test_contrast_ownership_and_non_trigger_contexts(self):
        for ident in ['acpo_background_contrast', 'acpo_baseline_definition', 'acpo_method_rationale', 'genome_author_positioning']:
            report = lint.analyze(self.sources[ident]['text'], self.en)
            hit = next(h for h in report['hits'] if h['rule_id'] == 'en_contrast_scope')
            self.assertEqual(hit['decision_owner'], 'academic-writing/Authority')
            self.assertEqual(hit['scope_status'], 'unclassified')
            self.assertEqual(hit['auto_action'], 'none')
        # The actual contextual judgments are in source fixtures/reference prose,
        # not inferred by this test from words such as "we" or "In contrast".

    def test_protected_spans_and_word_boundaries(self):
        # Synthetic container/coordinate tests, never promoted as real few-shot.
        text = '```text\nleverage\n```\n`novel` $x_{pivotal}$ https://example.org/unique\nThe novelty score is defined.\nWe leverage the measurements.'
        report = lint.analyze(text, self.en)
        self.assertEqual([(h['matched'], h['line'], h['column']) for h in report['hits']], [('leverage', 6, 4)])
        latex = '\\begin{equation}\npivotal := x\n\\end{equation}\nA value: $x:y$.'
        equation_report = lint.analyze(latex, self.en)
        self.assertEqual(equation_report['hits'], [])
        self.assertEqual(equation_report['distribution_signals']['metrics']['prose_colons']['count'], 1)
        markup = '<a id="fig:novel"></a>\nSee [Figure 1](#fig:pivotal) and \\ref{sec:unique}.\n| --- | :---: |\nA definition: $x:y$.'
        markup_report = lint.analyze(markup, self.en)
        self.assertEqual(markup_report['hits'], [])
        self.assertEqual(markup_report['distribution_signals']['metrics']['prose_colons']['count'], 1)
        self.assertEqual(markup_report['distribution_signals']['metrics']['em_dashes']['count'], 0)

    def test_cli_default_custom_policy_and_exit_semantics(self):
        text = self.sources['genome_author_positioning']['text']
        default = self.cli('--format', 'json', text=text)
        explicit = self.cli('--lang', 'en', '--format', 'json', text=text)
        self.assertEqual(default.returncode, 0)
        self.assertEqual(default.stdout, explicit.stdout)
        self.assertEqual(self.cli('--lang', 'en', '--fail-on', 'low', text=text).returncode, 2)
        self.assertEqual(self.cli('--lang', 'en', '--fail-on', 'medium', text=text).returncode, 0)
        custom = self.cli('--patterns', str(lint.DEFAULT_PATTERN_PATH), '--format', 'json', text='诚实说：数据不足。')
        original = lint.analyze_languages('诚实说：数据不足。', 'zh')
        self.assertEqual(json.loads(custom.stdout), original)
        self.assertEqual(lint.analyze_languages('', 'auto')['hits'], [])


if __name__ == '__main__':
    unittest.main()
