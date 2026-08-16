#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docgen 技能包校验脚本。

检查 skills 根目录（或单个技能目录/文件）中的 SKILL.md 是否符合
Agent Skills 开放标准的 frontmatter 契约，以及与 dsh 本地技能发现器的兼容约定：

- name 必须为 kebab-case（小写字母、数字、连字符），长度 <= 64，
  且必须与所在目录名（平铺文件则为文件名去掉 .md）一致；
- description 必填，非空，长度 <= 1024；
- whenToUse / license / compatibility / allowed-tools 若存在必须是字符串；
- metadata 若存在必须是「字符串键 -> 字符串值」的映射；
- 正文非空；--strict 模式下正文行数 <= 500（末尾空行不计，渐进式加载建议）。

用法:
    python scripts/validate_skills.py [--strict] [目录 ...]

不带参数时默认校验插件自带的 skills/ 目录。退出码 0 表示全部通过。

说明: 本脚本只解析本技能包使用的扁平 YAML 子集（顶层 `key: value`，
缩进的子键构成 metadata 映射），不处理锚点、列表、注释等完整 YAML 特性。
"""

import os
import re
import sys
from pathlib import Path

# 与 dsh 及 agentskills.io 规范一致的命名约束
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
MAX_BODY_LINES = 500

TEXT_FIELDS = ("whenToUse", "license", "compatibility", "allowed-tools")
REQUIRED = ("name", "description")


class NoBodyError(ValueError):
    """frontmatter 结构正常但缺少正文（收尾 `---` 之后没有任何内容）。"""


def name_problem(name):
    """返回 name 不合法时的原因描述，合法时返回 None。"""
    if not isinstance(name, str):
        return "name 必须是字符串"
    if not name:
        return "name 不能为空"
    if len(name) > MAX_NAME_LEN:
        return f"name 超过 {MAX_NAME_LEN} 字符"
    if not NAME_RE.match(name):
        return "name 必须为 kebab-case（小写字母/数字/连字符，不得以连字符开头或结尾，不得连续连字符）"
    return None


def _parse_scalar(raw):
    """解析标量值：去空白与成对引号；`[...]` 解析为列表；`{}` 解析为空映射。

    这是本技能包 frontmatter 使用的扁平 YAML 子集：键值形如 `key: value`，
    值允许字符串（可加引号）、`[...]` 列表、`{}` 空映射。不做完整 YAML 解析。
    """
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    if v == "{}":
        return {}
    return v


def parse_frontmatter(text):
    """解析 SKILL.md 的 YAML frontmatter，返回 dict。

    要求: 文件（允许 BOM）以 `---` 开头，有闭合的 `---` 行。
    仅支持本技能包的扁平键值子集；解析失败抛 ValueError。
    """
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("缺少 frontmatter（文件必须以 `---` 开头）")
    data = {}
    current = None  # 当前处于的嵌套映射键（metadata）
    for idx in range(1, len(lines)):
        line = lines[idx]
        if line.strip() == "---":
            if not data:
                raise ValueError("frontmatter 为空")
            if idx + 1 >= len(lines):
                raise NoBodyError("frontmatter 之后没有正文")
            return data
        if not line.strip():
            continue
        if line[0].isspace():
            if current is None:
                raise ValueError(f"第 {idx + 1} 行：缩进内容出现在顶层字段之前")
            key, _, raw = line.strip().partition(":")
            if not key or not raw.strip():
                raise ValueError(f"第 {idx + 1} 行：嵌套键值格式应为 `key: value`")
            data[current][key] = _parse_scalar(raw)
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        if not key:
            raise ValueError(f"第 {idx + 1} 行：缺少键名")
        if raw.strip() == "":
            data[key] = {}
            current = key  # 期望后续缩进行作为其嵌套值
        else:
            data[key] = _parse_scalar(raw)
            current = None
    raise ValueError("frontmatter 未闭合（缺少收尾的 `---`）")


def _body_of(text):
    """提取 frontmatter 之后的正文并返回行列表。"""
    lines = text.lstrip("\ufeff").splitlines()
    start = 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            start = i + 1
            break
    return lines[start:]


def validate_skill_file(path, strict=False):
    """校验单个平铺技能文件 <name>.md，返回问题列表（空列表 = 通过）。"""
    return _validate(path, expected_name=Path(path).stem, strict=strict)


def validate_skill_dir(skill_dir, strict=False):
    """校验单个技能目录 <name>/SKILL.md，返回问题列表。"""
    return _validate(Path(skill_dir) / "SKILL.md",
                     expected_name=Path(skill_dir).name, strict=strict)


def _validate(entry_path, expected_name, strict=False):
    issues = []
    path = Path(entry_path)
    tag = f"{path}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{tag}: 无法读取（{exc}）"]
    except UnicodeDecodeError:
        return [f"{tag}: 不是有效的 UTF-8 文本"]

    try:
        fm = parse_frontmatter(text)
    except ValueError as exc:
        if isinstance(exc, NoBodyError):
            issues.append(f"{tag}: frontmatter 正常但缺少正文")
        else:
            issues.append(f"{tag}: frontmatter 解析失败：{exc}")
        return issues

    name = fm.get("name")
    problem = name_problem(name)
    if problem:
        issues.append(f"{tag}: {problem}")
    elif name != expected_name:
        issues.append(f"{tag}: frontmatter 的 name「{name}」与目录/文件名「{expected_name}」不一致")

    for field in REQUIRED:
        if field not in fm:
            issues.append(f"{tag}: 缺少必填字段 {field}")

    desc = fm.get("description")
    if desc is not None and not isinstance(desc, str):
        issues.append(f"{tag}: description 必须是字符串")
    elif isinstance(desc, str) and not desc.strip():
        issues.append(f"{tag}: description 不能为空")
    elif isinstance(desc, str) and len(desc) > MAX_DESC_LEN:
        issues.append(f"{tag}: description 超过 {MAX_DESC_LEN} 字符")

    for field in TEXT_FIELDS:
        if field in fm and fm[field] is not None and not isinstance(fm[field], str):
            issues.append(f"{tag}: {field} 必须是字符串")

    meta = fm.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            issues.append(f"{tag}: metadata 必须是键值映射")
        else:
            for k, v in meta.items():
                if not isinstance(v, str):
                    issues.append(f"{tag}: metadata 的键「{k}」对应的值必须是字符串")

    body = _body_of(text)
    if not body or not any(l.strip() for l in body):
        issues.append(f"{tag}: 正文为空")
    elif strict:
        # 行数统计不计结尾空行
        while body and not body[-1].strip():
            body.pop()
        if len(body) > MAX_BODY_LINES:
            issues.append(f"{tag}: 正文 {len(body)} 行，超过建议上限 {MAX_BODY_LINES} 行（strict）")

    return issues


def validate_skills_root(root, strict=False):
    """扫描技能根目录（一层深度：<name>/SKILL.md 与 <name>.md），返回问题列表。"""
    issues = []
    root = Path(root)
    if not root.is_dir():
        return [f"{root}: 目录不存在"]
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            issues.extend(validate_skill_dir(entry, strict=strict))
        elif entry.is_file() and entry.suffix.lower() == ".md":
            issues.extend(validate_skill_file(entry, strict=strict))
    return issues


def main(argv=None):
    # Windows 控制台默认编码可能是 cp1252，强制 UTF-8 输出避免中文报错
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    strict = False
    targets = []
    for arg in argv:
        if arg == "--strict":
            strict = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            targets.append(arg)
    if not targets:
        targets = [str(Path(__file__).resolve().parents[1] / "skills")]

    issues = []
    for target in targets:
        p = Path(target)
        if p.is_dir() and (p / "SKILL.md").is_file():
            issues.extend(validate_skill_dir(p, strict=strict))
        elif p.is_dir():
            issues.extend(validate_skills_root(p, strict=strict))
        elif p.is_file():
            issues.extend(validate_skill_file(p, strict=strict))
        else:
            issues.append(f"{p}: 路径不存在")

    if issues:
        print(f"发现 {len(issues)} 个问题：")
        for item in issues:
            print("  -", item)
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
