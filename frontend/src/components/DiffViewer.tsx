import { useMemo } from 'react'
import { FileCode } from 'lucide-react'
import type { DiffFile, DiffLine } from '../lib/diff'
import { fileMatches, normalizePath, parseDiff } from '../lib/diff'
import type { Finding } from '../types'
import { SEVERITY_DOT, SEVERITY_ORDER } from '../lib/status'

/** Side-by-side-style diff with inline severity markers. */
export default function DiffViewer({ diff, findings }: { diff: string; findings: Finding[] }) {
  const files = useMemo(() => parseDiff(diff), [diff])

  if (files.length === 0) {
    return <p className="text-sm text-slate-500">No diff available for this run.</p>
  }

  return (
    <div className="space-y-6">
      {files.map((file, index) => (
        <DiffFileBlock key={`${file.newPath}-${index}`} file={file} findings={findings} />
      ))}
    </div>
  )
}

function DiffFileBlock({ file, findings }: { file: DiffFile; findings: Finding[] }) {
  const fileFindings = useMemo(
    () =>
      findings
        .filter((finding) => fileMatches(finding.file_path, file))
        .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]),
    [findings, file],
  )

  const findingsByNewLine = useMemo(() => {
    const map = new Map<number, Finding[]>()
    for (const finding of fileFindings) {
      if (finding.line_start == null) continue
      const end = finding.line_end ?? finding.line_start
      for (let line = finding.line_start; line <= end; line += 1) {
        const list = map.get(line) ?? []
        list.push(finding)
        map.set(line, list)
      }
    }
    return map
  }, [fileFindings])

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
        <div className="flex items-center gap-2 font-mono text-sm font-medium text-slate-700">
          <FileCode size={15} className="text-slate-400" />
          {normalizePath(file.newPath) || file.newPath}
        </div>
        {fileFindings.length > 0 && (
          <span className="text-xs text-slate-500">
            {fileFindings.length} finding{fileFindings.length === 1 ? '' : 's'}
          </span>
        )}
      </div>
      <div className="diff-scroll overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse font-mono text-[13px] leading-5">
          <tbody>
            {file.lines.map((line, index) => (
              <LineRow
                key={`${file.newPath}-${index}`}
                line={line}
                findings={line.newLine == null ? undefined : findingsByNewLine.get(line.newLine)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LineRow({ line, findings }: { line: DiffLine; findings: Finding[] | undefined }) {
  const gutter = line.type === 'add' || line.type === 'ctx' ? String(line.newLine ?? '') : ''
  const marker =
    line.type === 'add' ? '+' : line.type === 'del' ? '-' : line.type === 'meta' ? '' : ' '
  const classes =
    line.type === 'meta'
      ? 'bg-slate-50 text-slate-400'
      : line.type === 'add'
        ? 'bg-emerald-50/70 text-emerald-900'
        : line.type === 'del'
          ? 'bg-rose-50/70 text-rose-900'
          : 'text-slate-600'

  return (
    <tr className={classes}>
      <td className="w-10 select-none pr-2 text-right text-slate-400">{gutter}</td>
      <td className="w-8 select-none text-center text-slate-400">{marker}</td>
      <td className="px-3">
        {line.type === 'add' && findings && findings.length > 0 ? (
          <div className="flex items-start gap-2">
            <span className="mt-[7px] flex shrink-0 gap-1">
              {findings.slice(0, 3).map((finding) => (
                <span
                  key={finding.id}
                  title={`${finding.severity}: ${finding.message}${
                    finding.suggestion ? `\n\nFix: ${finding.suggestion}` : ''
                  }`}
                  className={`inline-block h-2 w-2 rounded-full ${SEVERITY_DOT[finding.severity]}`}
                />
              ))}
            </span>
            <span className="whitespace-pre">{line.text}</span>
          </div>
        ) : (
          <span className="whitespace-pre">{line.text}</span>
        )}
      </td>
    </tr>
  )
}
