import { describe, expect, it } from 'vitest'
import {
  NODE_STATUS_STYLE,
  RUN_STATUS_LABEL,
  RUN_STATUS_STYLE,
  SEVERITY_ORDER,
  SEVERITY_STYLE,
} from './status'

describe('status maps', () => {
  it('covers every run status with a label and style', () => {
    const statuses = ['queued', 'running', 'waiting_hitl', 'succeeded', 'failed']
    for (const status of statuses) {
      expect(RUN_STATUS_LABEL[status as keyof typeof RUN_STATUS_LABEL]).toBeTruthy()
      expect(RUN_STATUS_STYLE[status as keyof typeof RUN_STATUS_STYLE]).toBeTruthy()
    }
  })

  it('covers every node status for the DAG', () => {
    const statuses = ['idle', 'running', 'success', 'failed', 'paused']
    for (const status of statuses) {
      expect(NODE_STATUS_STYLE[status as keyof typeof NODE_STATUS_STYLE]).toBeTruthy()
    }
  })

  it('covers every severity with a style', () => {
    for (const severity of ['critical', 'error', 'warning', 'info']) {
      expect(SEVERITY_STYLE[severity as keyof typeof SEVERITY_STYLE]).toBeTruthy()
    }
  })

  it('orders severities most-severe first', () => {
    expect(SEVERITY_ORDER.critical).toBeLessThan(SEVERITY_ORDER.error)
    expect(SEVERITY_ORDER.error).toBeLessThan(SEVERITY_ORDER.warning)
    expect(SEVERITY_ORDER.warning).toBeLessThan(SEVERITY_ORDER.info)
  })
})
