import { describe, expect, it } from 'vitest'
import { fileMatches, normalizePath, parseDiff } from './diff'

const DIFF = [
  'diff --git a/app.py b/app.py',
  'index 111..222 100644',
  '--- a/app.py',
  '+++ b/app.py',
  '@@ -1,4 +1,4 @@',
  ' def handle():',
  '-    return run("clean")',
  '+    eval(input())',
  '+    print("debug")',
  '     return',
].join('\n')

describe('parseDiff', () => {
  it('splits into files and classifies lines', () => {
    const files = parseDiff(DIFF)
    expect(files).toHaveLength(1)
    expect(files[0].newPath).toBe('app.py')
    expect(files[0].oldPath).toBe('app.py')

    const lines = files[0].lines
    const adds = lines.filter((line) => line.type === 'add')
    const dels = lines.filter((line) => line.type === 'del')
    const ctx = lines.filter((line) => line.type === 'ctx')
    const meta = lines.filter((line) => line.type === 'meta')

    expect(adds).toHaveLength(2)
    expect(dels).toHaveLength(1)
    expect(ctx).toHaveLength(2)
    expect(meta).toHaveLength(4)
  })

  it('tracks new-file line numbers for added lines', () => {
    const files = parseDiff(DIFF)
    const adds = files[0].lines.filter((line) => line.type === 'add')
    expect(adds[0].newLine).toBe(3)
    expect(adds[1].newLine).toBe(4)
  })

  it('returns no files for an empty diff', () => {
    expect(parseDiff('')).toEqual([])
  })
})

describe('fileMatches', () => {
  it('ignores git a/ b/ prefixes', () => {
    const file = { oldPath: 'a/src/app.py', newPath: 'b/src/app.py', lines: [] }
    expect(fileMatches('src/app.py', file)).toBe(true)
    expect(fileMatches('other.py', file)).toBe(false)
  })

  it('normalizes paths', () => {
    expect(normalizePath('b/app.py')).toBe('app.py')
    expect(normalizePath('app.py')).toBe('app.py')
  })
})
