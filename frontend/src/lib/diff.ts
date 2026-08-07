/** Minimal unified-diff parser for the dashboard diff viewer. */

export type DiffLineType = 'add' | 'del' | 'ctx' | 'meta'

export interface DiffLine {
  type: DiffLineType
  /** Raw line content (marker stripped for code lines; raw for meta). */
  text: string
  /** New-file line number for add/context lines. */
  newLine?: number
}

export interface DiffFile {
  oldPath: string
  newPath: string
  lines: DiffLine[]
}

const HEADER_RE = /^diff --git a\/(.+) b\/(.+)$/
const HUNK_RE = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/

/** Split a unified diff into per-file structures with line numbers. */
export function parseDiff(diff: string): DiffFile[] {
  const files: DiffFile[] = []
  let current: DiffFile | null = null
  let newStart = 0
  let newCount = 0

  for (const raw of diff.split('\n')) {
    const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw
    if (line.startsWith('diff --git ')) {
      const match = line.match(HEADER_RE)
      current = {
        oldPath: match?.[1] ?? '',
        newPath: match?.[2] ?? '',
        lines: [],
      }
      files.push(current)
      continue
    }
    if (current === null) continue

    if (line.startsWith('@@')) {
      const match = line.match(HUNK_RE)
      newStart = match ? Number.parseInt(match[1], 10) : newStart
      newCount = 0
      current.lines.push({ type: 'meta', text: line })
      continue
    }
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('index ')) {
      current.lines.push({ type: 'meta', text: line })
      continue
    }

    if (line.startsWith('+')) {
      current.lines.push({ type: 'add', text: line.slice(1), newLine: newStart + newCount + 1 })
      newCount += 1
    } else if (line.startsWith('-')) {
      current.lines.push({ type: 'del', text: line.slice(1) })
    } else {
      current.lines.push({ type: 'ctx', text: line.slice(1), newLine: newStart + newCount + 1 })
      newCount += 1
    }
  }

  return files
}

/** Normalize a path for comparison (strips git a/ b/ prefixes). */
export function normalizePath(path: string): string {
  return path.replace(/^(a|b)\//, '')
}

/** True when a finding's file_path refers to this diff file. */
export function fileMatches(filePath: string, file: DiffFile): boolean {
  const normalized = normalizePath(filePath)
  return normalized === normalizePath(file.newPath) || normalized === normalizePath(file.oldPath)
}
