# -*- coding: utf-8 -*-
"""validate_skills.py 的回归测试（仅用标准库，无需第三方依赖）。

运行方式（在插件根目录）:
    python -m unittest discover -s tests -t .
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_skills as vs


def make_skill(root: Path, name: str, body: str = "# 正文\n示例内容。\n") -> Path:
    """在 root 下创建名为 name 的合法技能目录并返回其路径。"""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        "description: 这是一个用于测试的技能。\n"
        "whenToUse: 测试时使用。\n"
        "metadata:\n"
        '  author: "docgen"\n'
        '  version: "1.0.0"\n'
        "license: MIT\n"
        "---\n" + body,
        encoding="utf-8",
    )
    return d


def make_flat(root: Path, name: str) -> Path:
    """在 root 下创建名为 name.md 的平铺技能文件。"""
    p = root / f"{name}.md"
    p.write_text(
        "---\n"
        f"name: {name}\n"
        "description: 平铺格式测试技能。\n"
        "---\n# 正文\n",
        encoding="utf-8",
    )
    return p


class ParseFrontmatterTests(unittest.TestCase):
    def test_bom_and_crlf_tolerated(self):
        text = "\ufeff---\r\nname: alpha\r\ndescription: 描述\r\n---\r\n正文\r\n"
        self.assertEqual(vs.parse_frontmatter(text), {"name": "alpha", "description": "描述"})

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            vs.parse_frontmatter("# 没有 frontmatter 的文件\n")

    def test_unclosed_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            vs.parse_frontmatter("---\nname: alpha\n")

    def test_empty_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            vs.parse_frontmatter("---\n---\n正文\n")

    def test_nested_metadata(self):
        text = "---\nname: alpha\ndescription: 描述\nmetadata:\n  author: docgen\n  version: \"1.0.0\"\n---\n正文\n"
        meta = vs.parse_frontmatter(text)["metadata"]
        self.assertEqual(meta, {"author": "docgen", "version": "1.0.0"})

    def test_unindented_nested_key_is_treated_as_top_level(self):
        # metadata 下的键必须缩进；未缩进的键被当作顶层字段，空值解析为 {}
        text = "---\nname: alpha\nmetadata:\nauthor: docgen\n---\n正文\n"
        data = vs.parse_frontmatter(text)
        self.assertEqual(data.get("metadata"), {})
        self.assertEqual(data.get("author"), "docgen")

    def test_indent_before_any_top_level_field_raises(self):
        text = "---\n  author: docgen\nname: alpha\n---\n正文\n"
        with self.assertRaises(ValueError):
            vs.parse_frontmatter(text)

    def test_closing_marker_as_last_line_raises(self):
        # 收尾 --- 位于最后一行：frontmatter 之后没有正文
        with self.assertRaises(ValueError):
            vs.parse_frontmatter("---\nname: alpha\n---")

    def test_quoted_and_unquoted_scalars(self):
        text = '---\nname: "alpha"\ndescription: \'描述 文本\'\n---\n正文\n'
        data = vs.parse_frontmatter(text)
        self.assertEqual(data["name"], "alpha")
        self.assertEqual(data["description"], "描述 文本")

    def test_list_and_empty_map_scalars(self):
        text = "---\nname: alpha\ntags: [a, b, c]\nempty:\n---\n正文\n"
        data = vs.parse_frontmatter(text)
        self.assertEqual(data["tags"], ["a", "b", "c"])
        self.assertEqual(data["empty"], {})

    def test_quoted_value_with_inner_colon(self):
        text = '---\nname: alpha\ndescription: "说明：冒号在引号内"\n---\n正文\n'
        self.assertEqual(vs.parse_frontmatter(text)["description"], "说明：冒号在引号内")


class NameRuleTests(unittest.TestCase):
    def test_name_rules(self):
        valid = ["alpha", "readme-forge", "a1-b2-c3", "changelog-curator", "1abc"]
        for n in valid:
            self.assertIsNone(vs.name_problem(n), n)
        invalid = [
            "Alpha",        # 大写
            "-alpha",       # 以连字符开头
            "alpha-",       # 以连字符结尾
            "alpha--beta",  # 连续连字符
            "alpha_beta",   # 下划线
            "alpha.beta",   # 点
            "a" * 65,       # 超长
            "",             # 空
        ]
        for n in invalid:
            self.assertIsNotNone(vs.name_problem(n), n)


class ValidateSkillTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_skill_has_no_issues(self):
        d = make_skill(self.root, "alpha")
        self.assertEqual(vs.validate_skill_dir(d), [])

    def test_valid_flat_skill_has_no_issues(self):
        p = make_flat(self.root, "beta")
        self.assertEqual(vs.validate_skill_file(p), [])

    def test_flat_skill_name_must_match_filename(self):
        p = make_flat(self.root, "beta")
        p.write_text(
            "---\nname: gamma\ndescription: 名称与文件名不一致。\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_file(p)
        self.assertTrue(any("文件名" in i for i in issues))

    def test_name_must_match_directory(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: omega\ndescription: 名称与目录不一致。\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("不一致" in i for i in issues))

    def test_missing_description_fails(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\n---\n正文\n", encoding="utf-8"
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("description" in i for i in issues))

    def test_overlong_description_fails(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: " + "x" * 1025 + "\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("1024" in i for i in issues))

    def test_non_string_when_to_use_fails(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\nwhenToUse: [1, 2]\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("whenToUse" in i for i in issues))

    def test_empty_when_to_use_value_fails(self):
        # `whenToUse:` 空值被解析为空映射 {}，同样触发字段类型检查
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\nwhenToUse:\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("whenToUse" in i for i in issues))

    def test_non_string_metadata_value_fails(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\nmetadata:\n  version: [1, 2]\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("metadata" in i for i in issues))

    def test_metadata_must_be_mapping(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\nmetadata: not-a-map\n---\n正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("metadata" in i for i in issues))

    def test_empty_body_fails(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---\n", encoding="utf-8"
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("正文" in i for i in issues))

    def test_overlong_body_fails_only_in_strict_mode(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---\n" + ("# x\n" * 501),
            encoding="utf-8",
        )
        self.assertEqual(vs.validate_skill_dir(d), [])
        self.assertTrue(any("500" in i for i in vs.validate_skill_dir(d, strict=True)))

    def test_body_at_exactly_500_lines_passes_strict(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---\n" + ("# x\n" * 500),
            encoding="utf-8",
        )
        self.assertEqual(vs.validate_skill_dir(d, strict=True), [])

    def test_empty_metadata_block_is_accepted_end_to_end(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\nmetadata:\n---\n正文\n",
            encoding="utf-8",
        )
        self.assertEqual(vs.validate_skill_dir(d), [])

    def test_missing_body_reported_as_such(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---", encoding="utf-8"
        )
        issues = vs.validate_skill_dir(d)
        self.assertTrue(any("缺少正文" in i for i in issues))

    def test_trailing_blank_lines_do_not_count_towards_strict_limit(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---\n"
            + ("# x\n" * 500)
            + "\n\n\n",
            encoding="utf-8",
        )
        self.assertEqual(vs.validate_skill_dir(d, strict=True), [])


class RootScanTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_scan_collects_all_entries(self):
        make_skill(self.root, "alpha")
        make_skill(self.root, "beta")
        make_flat(self.root, "gamma")
        issues = vs.validate_skills_root(self.root)
        self.assertEqual(issues, [])

    def test_scan_reports_every_broken_entry(self):
        make_skill(self.root, "alpha")
        d = make_skill(self.root, "bad--name")  # 非法名称
        issues = vs.validate_skills_root(self.root)
        self.assertEqual(len(issues), 1)
        self.assertIn("bad--name", issues[0])

    def test_dirs_without_skill_md_are_ignored(self):
        (self.root / "plain-dir").mkdir()
        make_skill(self.root, "alpha")
        self.assertEqual(vs.validate_skills_root(self.root), [])

    def test_uppercase_md_extension_is_picked_up(self):
        p = self.root / "gamma.MD"
        p.write_text(
            "---\nname: gamma\ndescription: 大写扩展名。\n---\n# 正文\n",
            encoding="utf-8",
        )
        issues = vs.validate_skills_root(self.root)
        self.assertEqual(issues, [])

    def test_missing_root_is_an_error(self):
        missing = self.root / "nope"
        self.assertTrue(vs.validate_skills_root(missing))


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_exit_codes(self):
        good = make_skill(self.root, "alpha")
        bad = make_skill(self.root, "Beta")
        self.assertEqual(vs.main([str(good)]), 0)
        self.assertEqual(vs.main([str(bad)]), 1)

    def test_strict_flag(self):
        d = make_skill(self.root, "alpha")
        (d / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: 描述。\n---\n" + ("# x\n" * 501),
            encoding="utf-8",
        )
        self.assertEqual(vs.main([str(d)]), 0)
        self.assertEqual(vs.main(["--strict", str(d)]), 1)

    def test_missing_path_exits_nonzero(self):
        self.assertEqual(vs.main([str(self.root / "nope")]), 1)

    def test_help_exits_zero(self):
        self.assertEqual(vs.main(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
