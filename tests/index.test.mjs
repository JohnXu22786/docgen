import { afterEach, beforeEach, describe, test } from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { apply, inject, name, parseFrontmatter, scanSkills, PACKAGE_ROOT } from '../index.js'

const LEGACY_ROOT = join(PACKAGE_ROOT, 'skills')

function fakeCtx() {
  const registrations = []
  const ctx = {
    logger: { warn() {}, info() {} },
    skills: {
      register(skill) {
        registrations.push(skill)
        return () => {}
      },
    },
  }
  return { ctx, registrations }
}

describe('docgen skill-mount adapter', () => {
  test('exports the Cordis plugin contract', () => {
    assert.equal(name, 'docgen')
    assert.deepEqual(inject, ['skills'])
    assert.equal(typeof apply, 'function')
  })

  test('apply registers all four bundled skills onto ctx.skills', () => {
    const { ctx, registrations } = fakeCtx()
    apply(ctx)
    const names = registrations.map((r) => r.name).sort()
    assert.deepEqual(names, ['changelog-curator', 'diff-verdict', 'pr-dossier', 'readme-forge'])
    for (const r of registrations) {
      assert.ok(r.description.length > 0, `${r.name}: description 非空`)
      assert.ok(r.content.length > 0, `${r.name}: content 非空`)
      assert.equal(r.source, 'bundled')
      assert.equal(r.resourceBase.kind, 'directory')
      assert.equal(r.path, join(LEGACY_ROOT, r.name, 'SKILL.md'))
    }
  })

  test('combined disposer unregisters every registration in reverse order', () => {
    let next = 0
    const log = []
    const ctx = {
      logger: { warn() {}, info() {} },
      skills: {
        register() {
          const id = next
          next += 1
          return () => log.push(id)
        },
      },
    }
    const dispose = apply(ctx)
    dispose()
    assert.deepEqual(log, [3, 2, 1, 0], '卸载应按注册逆序执行')
  })

  test('apply without a skills service degrades to a warning, not a throw', () => {
    const notes = []
    const ctx = { logger: { warn: (m) => notes.push(m) } }
    const dispose = apply(ctx)
    assert.strictEqual(typeof dispose, 'function')
    assert.ok(notes.some((n) => n.includes('customSkillDirs')), notes.join('\n'))
  })

  test('frontmatter parsing mirrors the pack flat YAML subset', () => {
    const text =
      '---\n' +
      'name: alpha\n' +
      'description: 描述\n' +
      'whenToUse: 测试时使用。\n' +
      'metadata:\n' +
      '  author: docgen\n' +
      '  version: "1.0.0"\n' +
      '---\n正文'
    const { data, body } = parseFrontmatter(text)
    assert.deepEqual(data, {
      name: 'alpha',
      description: '描述',
      whenToUse: '测试时使用。',
      metadata: { author: 'docgen', version: '1.0.0' },
    })
    assert.equal(body, '正文')
  })

  test('unclosed frontmatter throws', () => {
    assert.throws(() => parseFrontmatter('---\nname: alpha\n'), /未闭合/)
  })
})

describe('scanSkills over a scratch root', () => {
  let dir
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'dsh-docgen-'))
  })
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true })
  })

  test('collects dir bundles and flat files, skipping broken ones with issues', () => {
    const good = join(dir, 'alpha')
    mkdirSync(good)
    writeFileSync(
      join(good, 'SKILL.md'),
      '---\nname: alpha\ndescription: 合格技能。\n---\n# 正文\n示例内容。\n',
      'utf8',
    )
    writeFileSync(join(dir, 'beta.md'), '---\nname: beta\ndescription: 平铺技能。\n---\n# 正文\n', 'utf8')
    writeFileSync(join(dir, 'broken.md'), '---\nname: gamma\ndescription: 名称不一致。\n---\n# 正文\n', 'utf8')

    const { skills, issues } = scanSkills(dir)
    assert.deepEqual(skills.map((s) => s.name).sort(), ['alpha', 'beta'])
    assert.equal(issues.length, 1)
    assert.ok(issues[0].includes("不一致"))
  })

  test('missing root reports a non-fatal issue', () => {
    const { skills, issues } = scanSkills(join(dir, 'nope'))
    assert.deepEqual(skills, [])
    assert.equal(issues.length, 1)
  })
})