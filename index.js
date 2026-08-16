/**
 * dsh-docgen — skill-mount adapter.
 *
 * Cordis plugin entry mounted by the bundle row (cordis.patch.yml). dsh reads
 * the named exports ({ name, inject, apply }) and invokes apply(ctx) once the
 * declared services are ready; apply scans the bundled `skills/` directory and
 * registers every SKILL.md onto `ctx.skills` using dsh's runtime registration
 * contract ({ name, description, whenToUse, content, ... }).
 *
 * If a skill component is not present in the current profile, the pack can
 * still be integrated through the file-based discovery path — copy the skills
 * into a project/user skills root or point customSkillDirs at `skills/`
 * (see README.md and examples/dsh-patch-enable-skills.yml).
 *
 * Zero runtime dependencies on purpose: node built-ins only.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, isAbsolute, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Cordis plugin identifier of this bundle row. */
export const name = 'docgen'

/** Services this plugin must have mounted before it applies. */
export const inject = ['skills']

/** Package root of this plugin (parent of this entry file). */
export const PACKAGE_ROOT = dirname(fileURLToPath(import.meta.url))

const MAX_NAME_LEN = 64
const MAX_DESC_LEN = 1024
const NAME_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

/**
 * One skill discovered under the skills root.
 * @typedef {Object} SkillRecord
 * @property {string} name - kebab-case skill name (matches directory/file).
 * @property {string} description - routing description.
 * @property {string} [whenToUse] - optional routing hint.
 * @property {Object<string,unknown>} [metadata] - optional frontmatter metadata.
 * @property {string} content - SKILL.md body.
 * @property {string} file - absolute path to the skill file.
 * @property {string} directory - absolute path of the skill directory.
 */

/**
 * Scan result.
 * @typedef {Object} ScanResult
 * @property {SkillRecord[]} skills
 * @property {string[]} issues
 */

/** Mirror of the pack's flat YAML subset (see scripts/validate_skills.py). */
function parseScalar(raw) {
  const v = raw.trim()
  if (v.length >= 2 && v[0] === v[v.length - 1] && (v[0] === "'" || v[0] === '"')) {
    return v.slice(1, -1)
  }
  if (v.startsWith('[') && v.endsWith(']')) {
    const inner = v.slice(1, -1).trim()
    if (inner === '') return []
    return inner.split(',').map((item) => parseScalar(item))
  }
  if (v === '{}') return {}
  return v
}

/** Parse SKILL.md frontmatter (flat subset); throws on structural errors. */
export function parseFrontmatter(text) {
  const lines = text.replace(/^\ufeff/, '').split(/\r\n|\r|\n/)
  if (lines.length === 0 || (lines[0] ?? '').trim() !== '---') {
    throw new Error('缺少 frontmatter（文件必须以 --- 开头）')
  }
  const data = {}
  let current = null
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i] ?? ''
    if (line.trim() === '---') {
      if (Object.keys(data).length === 0) throw new Error('frontmatter 为空')
      if (i + 1 >= lines.length) throw new Error('frontmatter 之后没有正文')
      return { data, body: lines.slice(i + 1).join('\n') }
    }
    if (line.trim() === '') continue
    if (/^\s/.test(line)) {
      if (current === null) {
        throw new Error(`第 ${i + 1} 行：缩进内容出现在顶层字段之前`)
      }
      const [key, ...rest] = line.trim().split(':')
      if (!key || !rest.join(':').trim()) {
        throw new Error(`第 ${i + 1} 行：嵌套键值格式应为 key: value`)
      }
      data[current][key] = parseScalar(rest.join(':'))
      continue
    }
    const idx = line.indexOf(':')
    if (idx === -1) throw new Error(`第 ${i + 1} 行：缺少键名`)
    const key = line.slice(0, idx).trim()
    if (!key) throw new Error(`第 ${i + 1} 行：缺少键名`)
    const raw = line.slice(idx + 1)
    if (raw.trim() === '') {
      data[key] = {}
      current = key
    } else {
      data[key] = parseScalar(raw)
      current = null
    }
  }
  throw new Error('frontmatter 未闭合（缺少收尾的 ---）')
}

function skillNameProblem(value) {
  if (typeof value !== 'string') return 'name 必须是字符串'
  if (!value) return 'name 不能为空'
  if (value.length > MAX_NAME_LEN) return `name 超过 ${MAX_NAME_LEN} 字符`
  if (!NAME_PATTERN.test(value)) return 'name 必须为 kebab-case'
  return null
}

function parseSkillFile(file, expectedName) {
  const text = readFileSync(file, 'utf8')
  const { data, body } = parseFrontmatter(text)
  const problem = skillNameProblem(data.name)
  if (problem) return { problem: `${file}: ${problem}` }
  if (data.name !== expectedName) {
    return { problem: `${file}: frontmatter 的 name「${data.name}」与目录/文件名「${expectedName}」不一致` }
  }
  if (typeof data.description !== 'string' || !data.description.trim()) {
    return { problem: `${file}: description 必填且不能为空` }
  }
  if (data.description.trim().length > MAX_DESC_LEN) {
    return { problem: `${file}: description 超过 ${MAX_DESC_LEN} 字符` }
  }
  const content = body.trim()
  if (!content) return { problem: `${file}: 正文为空` }
  const record = {
    name: data.name,
    description: data.description.trim(),
    content,
    file,
    directory: dirname(file),
  }
  if (typeof data.whenToUse === 'string') record.whenToUse = data.whenToUse
  if (data.metadata && typeof data.metadata === 'object' && !Array.isArray(data.metadata)) {
    record.metadata = data.metadata
  }
  return { record }
}

function scanRoot(root) {
  const skills = []
  const issues = []
  const seen = new Set()
  for (const entry of readdirSync(root).sort()) {
    const full = join(root, entry)
    let isDir = false
    try {
      isDir = statSync(full).isDirectory()
    } catch (error) {
      issues.push(`${full}: 无法读取（${error.message}）`)
      continue
    }
    let file
    let expectedName
    if (isDir) {
      file = join(full, 'SKILL.md')
      expectedName = entry
    } else if (entry.endsWith('.md')) {
      file = full
      expectedName = entry.slice(0, -3)
    } else {
      continue
    }
    let parsed
    try {
      parsed = parseSkillFile(file, expectedName)
    } catch (error) {
      issues.push(`${file}: ${error.message}`)
      continue
    }
    if (parsed.problem) {
      issues.push(parsed.problem)
      continue
    }
    if (seen.has(parsed.record.name)) {
      issues.push(`${file}: 技能名 ${parsed.record.name} 重复，已跳过`)
      continue
    }
    seen.add(parsed.record.name)
    skills.push(parsed.record)
  }
  return { skills, issues }
}

/** Scan a skills root (one level deep: <name>/SKILL.md or <name>.md). */
export function scanSkills(root) {
  try {
    return scanRoot(root)
  } catch (error) {
    return { skills: [], issues: [`技能根目录不可读 ${root}: ${error.message}`] }
  }
}

function resolveRoots(config) {
  const raw = config.skillsDir === undefined ? join(PACKAGE_ROOT, 'skills') : config.skillsDir
  return (Array.isArray(raw) ? raw : [raw]).map((dir) => {
    if (typeof dir !== 'string' || dir.trim() === '') throw new TypeError('skillsDir 必须是字符串或字符串数组')
    return isAbsolute(dir) ? dir : resolve(PACKAGE_ROOT, dir)
  })
}

/**
 * Cordis plugin body: register the bundled skills onto `ctx.skills`.
 *
 * Returns a combined disposer; when the plugin unloads, every registration is
 * removed in reverse order (matching Cordis effect teardown ordering).
 */
export function apply(ctx, config = {}) {
  const warn = (message) => {
    try {
      ctx.logger?.warn?.(`docgen: ${message}`)
    } catch {
      // logger shape is not promised; never break loading over a log call
    }
  }
  const info = (message) => {
    try {
      ctx.logger?.info?.(`docgen: ${message}`)
    } catch {
      // noop
    }
  }
  const register = ctx.skills && typeof ctx.skills.register === 'function' ? ctx.skills.register.bind(ctx.skills) : null
  if (!register) {
    warn('未发现 ctx.skills.register 服务。技能不会运行时注册；可将 skills/ 目录拷贝到项目/用户技能根目录，或配置 customSkillDirs 指向本包 skills/（见 README「安装与接入 dsh」）。')
    return () => {}
  }

  const roots = resolveRoots(config)
  const disposers = []
  let registered = 0
  for (const root of roots) {
    const { skills, issues } = scanSkills(root)
    for (const issue of issues) warn(issue)
    for (const skill of skills) {
      disposers.push(
        register({
          name: skill.name,
          description: skill.description,
          ...(skill.whenToUse !== undefined ? { whenToUse: skill.whenToUse } : {}),
          ...(skill.metadata !== undefined ? { metadata: skill.metadata } : {}),
          content: skill.content,
          source: 'bundled',
          resourceBase: { kind: 'directory', path: skill.directory },
          path: skill.file,
        }),
      )
      registered += 1
    }
  }
  info(`已注册 ${registered} 个技能。`)
  return () => {
    for (let i = disposers.length - 1; i >= 0; i--) {
      try {
        disposers[i]?.()
      } catch {
        // teardown of one registration must not break the rest
      }
    }
  }
}