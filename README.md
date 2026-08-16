# docgen — 文档工坊技能包

一组纯提示词（Agent Skills）形态的文档生成技能，为 dsh 等插件化 agent harness 提供四项能力：**README 生成、PR 描述生成、changelog 生成、代码审查**。所有技能遵循 [Agent Skills 开放标准](https://agentskills.io/specification)（`SKILL.md` + YAML frontmatter），自包含、无第三方依赖、离线可用。

## 包含的技能

| 技能 | 做什么 | 何时用 |
|---|---|---|
| [`readme-forge`](skills/readme-forge/SKILL.md) | 从代码库生成/重写 README.md，只写有证据的内容 | 「给这个项目写个 README」 |
| [`pr-dossier`](skills/pr-dossier/SKILL.md) | 从 diff 与提交历史生成完整 PR 描述（变更档案） | 「为这次改动写 PR 描述」 |
| [`changelog-curator`](skills/changelog-curator/SKILL.md) | 从 git 历史分类、合并、改写生成 CHANGELOG | 「更新 changelog，准备发版」 |
| [`diff-verdict`](skills/diff-verdict/SKILL.md) | 输出结构化审查意见：结论 + 分级问题清单 + 亮点 | 「审查一下这个 PR」 |

每个技能都是**自包含的单个 `SKILL.md`**：正文包含输入收集指引、工作流程、输出模板与模板变量表、语言风格选项、输出质量检查清单、「不要做」清单与边界情况处理。

## 目录结构

```
docgen/
├── README.md                     # 本文档：安装、使用、接口说明
├── manifest.json                 # 插件清单（自描述元数据）
├── SKILLS.md                     # 入口索引文件
├── LICENSE                       # MIT 许可
├── skills/                       # 技能根目录（接入时指向这里或拷贝其中条目）
│   ├── readme-forge/SKILL.md
│   ├── pr-dossier/SKILL.md
│   ├── changelog-curator/SKILL.md
│   └── diff-verdict/SKILL.md
├── examples/
│   ├── prompts.md                # 每个技能的示例调用提示词
│   └── dsh-patch-enable-skills.yml  # dsh 接入补丁示例（web profile 启用技能 + 登记目录）
├── scripts/
│   └── validate_skills.py        # 技能包校验脚本（Python 标准库，无依赖）
└── tests/
    └── test_validate_skills.py   # 校验脚本的回归测试
```

## 安装与接入 dsh

dsh 通过 `skill-filesystem` 提供方按**技能根目录**发现技能（一层深度：目录束 `<root>/<name>/SKILL.md` 或平铺文件 `<root>/<name>.md`）。接入本插件任选一种方式：

### 方式一：项目级（推荐，零配置）

把 `skills/` 下的四个技能目录（或整个 `skills/`）放进项目的技能根目录：

```bash
# 项目根目录（包含 .git 的最近祖先）任选其一：
#   <project>/.dsh/skills/   或   <project>/.agents/skills/
cp -r skills/* <project>/.dsh/skills/
```

### 方式二：用户级（所有项目可用）

```bash
# $DSH_HOME 默认 ~/.dsh；$DSH_AGENTS_HOME 默认 ~/.agents
cp -r skills/* ~/.dsh/skills/
```

### 方式三：自定义目录（插件原地接入，不拷贝）

通过配置给 `skill-filesystem` 提供方登记 `customSkillDirs`，例如用补丁文件（见 `examples/dsh-patch-enable-skills.yml`）：

```bash
npx @deepseek-ai/dsh web --patch ./examples/dsh-patch-enable-skills.yml
```

> 注意：dsh 的 `web` profile 默认关闭技能相关组件（`skill-filesystem` / `tool-skill`），需要补丁或 preset 启用；`headless` profile 默认开启。具体配置键路径以你所装版本的 `dsh --dump-config` 与官方文档为准。

### 验证安装

```bash
python scripts/validate_skills.py            # 校验本包技能格式（全部通过则退出码 0）
python scripts/validate_skills.py --strict   # 追加正文行数上限检查
python -m unittest discover -s tests -t .    # 运行校验脚本自身的回归测试
```

接入后在会话中直接以自然语言发起请求即可，模型会通过 `skill` 工具加载对应技能：

```
给这个项目写一个 README
为刚才的改动生成 PR 描述
根据 git 历史更新 changelog，准备发 1.2.0
帮我审查这个 PR
```

## 使用说明

- **触发**：在提问中自然描述需求（见技能表「何时用」列），无需记住技能名；harness 依据 `description` / `whenToUse` 自动路由。
- **风格选项**：每个技能支持三种可覆盖维度——语言（默认跟随提问语言）、篇幅（精简/标准/详尽或完整）、语气/深度。以自然语言追加即可：`篇幅=精简`、`关注=安全`、`language=en`。
- **输出形态**：技能直接产出 markdown 文本；README/changelog 类技能会给出可直接保存为文件的完整内容，PR/审查类技能给出结构化描述或意见清单。
- **示例提示词**：见 [examples/prompts.md](examples/prompts.md)。

## 接口说明

### 技能接口（dsh 原生契约）

每个技能是一个目录束，`SKILL.md` 的 frontmatter 是 harness 读取的唯一契约：

| 字段 | 必填 | 约束 | 本包用法 |
|---|---|---|---|
| `name` | 是 | kebab-case（小写字母/数字/连字符），≤64 字符，与所在目录名一致 | 见各技能 |
| `description` | 是 | 非空，≤1024 字符，说明做什么 + 何时用 + 触发关键词 | 中文描述 + 英文关键词 |
| `whenToUse` | 否 | 字符串，补充路由提示（社区确立的驼峰扩展字段） | 各技能均已提供 |
| `metadata` | 否 | 字符串键值映射 | author / version / family |
| `license` | 否 | 字符串 | MIT |
| `compatibility` | 否 | 字符串，环境要求 | 纯提示词，无需网络 |
| `allowed-tools` | 否 | 字符串，预先批准的工具清单（实验性） | 未使用 |

dsh 额外识别（本包不写、按默认处理）：`disable-model-invocation` 与 `user-invocable`（缺省均开放）。**注意**：字段名必须按上表拼写——`allowed-tools` 含连字符、`whenToUse` 为既定驼峰拼写，拼写不一致（如写成 `allowed_tools` 或 `when-to-use`）会导致该字段不被识别；其中调用策略字段拼写或类型错误时，dsh 会丢弃整个技能（fail-closed）。

### 插件清单与入口

- `manifest.json`：插件的自描述元数据（id / version / kind / entry / interface / skills / scripts）。dsh 的技能发现不读取它，它服务于人工查阅、发布流程与支持「入口文件」型加载器的 harness；`interface` 字段声明了技能发现契约。
- `SKILLS.md`：入口索引，列出加载契约摘要与技能清单。

### dsh 加载原理（摘要）

dsh 的技能能力由 `skill`（注册表）、`skill-filesystem`（本地发现）、`tool-skill`（模型目录与 `skill` 工具）三个插件协作提供：启动时按根目录扫描 frontmatter 生成目录（模型只看到 `name` + `description`）；模型决定调用某技能时按名读取最新正文；正文中的相对引用以技能目录为基准。本包四个技能均为单文件自包含，不依赖相对资源。

## 开发与扩展

- **新增技能**：在 `skills/` 下新建目录 + `SKILL.md`（frontmatter 见上表），运行 `python scripts/validate_skills.py` 通过校验，并同步更新 `manifest.json` 与 `SKILLS.md`。
- **修改技能**：只编辑对应 `SKILL.md`，harness 下次加载即读到新内容（正文修改无需重启目录缓存）。
- **校验脚本**：`scripts/validate_skills.py` 仅用 Python 标准库，可独立用于任何技能包；支持传任意目录/文件。解析范围是扁平 YAML 子集（顶层键值 + `metadata` 缩进映射 + 引号/列表字面量），不含锚点、注释等完整 YAML 特性。

## 依赖与隐私

- 零第三方依赖：纯提示词 + Python 标准库脚本；
- 不发起网络请求，不收集任何数据；需要的能力仅为读取代码库文件与 git 历史（由 harness 提供）；
- 许可证：MIT，见 [LICENSE](LICENSE)。

## 常见问题

- **web 界面看不到技能？** dsh web profile 默认关闭技能组件，用方式三的补丁启用（或使用 CLI/headless profile）。
- **改了 SKILL.md 没生效？** 技能正文按次读取，重发一次请求即可；若改的是 frontmatter 的 `name`/`description`，目录会随文件系统监听刷新。
- **技能与已有技能重名？** dsh 按根目录优先级与层（layer）就近覆盖同名技能；本包技能名均为原创命名，冲突时优先检查是否已安装同名技能。
