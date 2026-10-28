// localStorage 持久化：学习状态、完成日志、自定义知识点、备份导入导出

import type { UserState, CompletionLog, Status } from '../types/knowledge'
import { emptyState, normalizeStatus } from '../types/knowledge'

export const STATE_KEY = 'knowledge-guide:user-state:v1'
export const COMPLETION_KEY = 'knowledge-guide:completion-log:v1'
export const CUSTOM_TOPICS_KEY = 'knowledge-guide:custom-topics:v1'
export const THEME_KEY = 'knowledge-guide:theme:v1'
export const SOUND_KEY = 'knowledge-guide:sound:v1'
export const BACKUP_KEYS = [STATE_KEY, COMPLETION_KEY, CUSTOM_TOPICS_KEY]

export type CustomTopics = Record<string, { id: string; title: string; url: string }[]>

export function readStates(): Record<string, UserState> {
  const raw = JSON.parse(localStorage.getItem(STATE_KEY) || '{}') as Record<string, { status?: string; verified?: boolean; exposed?: boolean }>
  return Object.fromEntries(Object.entries(raw).map(([id, state]) => [
    id,
    { ...emptyState, ...state, status: normalizeStatus(state.status) },
  ]))
}

export function writeStates(next: Record<string, UserState>) {
  localStorage.setItem(STATE_KEY, JSON.stringify(next))
}

export function readCompletionLog(): CompletionLog {
  try {
    return JSON.parse(localStorage.getItem(COMPLETION_KEY) || '{}')
  } catch {
    return {}
  }
}

export function writeCompletionLog(next: CompletionLog) {
  localStorage.setItem(COMPLETION_KEY, JSON.stringify(next))
}

export function readCustomTopics(): CustomTopics {
  try {
    const raw = JSON.parse(localStorage.getItem(CUSTOM_TOPICS_KEY) || '{}') as CustomTopics
    return Object.fromEntries(Object.entries(raw).filter(([, topics]) => Array.isArray(topics)))
  } catch {
    return {}
  }
}

export function writeCustomTopics(next: CustomTopics) {
  localStorage.setItem(CUSTOM_TOPICS_KEY, JSON.stringify(next))
}

// 网址归一化：没有协议时默认补 https://
export function normalizeUrl(url: string) { return /^https?:\/\//.test(url) ? url : 'https://' + url }

// 桌面端通过 Tauri opener 插件调用系统浏览器，网页端走 window.open
export async function openLink(url: string) {
  if ('__TAURI_INTERNALS__' in window) {
    try {
      const { openUrl } = await import('@tauri-apps/plugin-opener')
      await openUrl(url)
    } catch {
      // 插件不可用时静默失败
    }
  } else {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

async function notify(text: string) {
  if ('__TAURI_INTERNALS__' in window) {
    try {
      const { message } = await import('@tauri-apps/plugin-dialog')
      await message(text, { title: '星航日志 · 数据备份', kind: 'info' })
      return
    } catch { /* 插件不可用时退回 alert */ }
  }
  window.alert(text)
}

export function todayKey() { return new Date().toISOString().slice(0, 10) }

// 数据备份：学习状态、点亮记录、自定义知识点统一打包为 JSON。
// 桌面端走系统保存对话框（plugin-dialog + plugin-fs），网页端走浏览器下载。
export async function exportBackup() {
  const payload = {
    app: 'starlog',
    version: 1,
    exportedAt: new Date().toISOString(),
    data: Object.fromEntries(BACKUP_KEYS.map((key) => [key, localStorage.getItem(key) || ''])),
  }
  const json = JSON.stringify(payload, null, 2)
  const name = `starlog-backup-${todayKey()}.json`
  if ('__TAURI_INTERNALS__' in window) {
    try {
      const { save } = await import('@tauri-apps/plugin-dialog')
      const { writeTextFile } = await import('@tauri-apps/plugin-fs')
      const path = await save({ defaultPath: name, filters: [{ name: 'JSON', extensions: ['json'] }] })
      if (!path) return
      await writeTextFile(path, json)
      await notify('备份已保存到：\n' + path)
    } catch {
      await notify('备份失败，请重试')
    }
    return
  }
  const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

export async function importBackup(file: File) {
  let payload: { app?: string; data?: Record<string, unknown> }
  try {
    payload = JSON.parse(await file.text())
  } catch {
    await notify('导入失败：文件不是有效的 JSON')
    return
  }
  if (payload.app !== 'starlog' || typeof payload.data !== 'object' || payload.data === null) {
    await notify('导入失败：这不是星航日志的备份文件')
    return
  }
  for (const [key, value] of Object.entries(payload.data)) {
    if (BACKUP_KEYS.includes(key) && typeof value === 'string') localStorage.setItem(key, value)
  }
  location.reload() // 重新挂载应用，从 localStorage 恢复全部状态
}

// 状态循环：未开始 → 学习中 → 已完成 → 学习中
export function nextStatus(status: Status): Status {
  return status === 'unlearned' ? 'learning' : status === 'learning' ? 'completed' : 'learning'
}
