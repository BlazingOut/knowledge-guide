// 进度统计：覆盖率、连续天数、热力图、最近点亮等纯函数

import type { CompletionLog, Topic, UserState } from '../types/knowledge'

export function doneCount(topics: Topic[], get: (id: string) => UserState) {
  return topics.filter((t) => get(t.id).status === 'completed').length
}

export function learningCount(topics: Topic[], get: (id: string) => UserState) {
  return topics.filter((t) => get(t.id).status === 'learning').length
}

export function startedCount(topics: Topic[], get: (id: string) => UserState) {
  return topics.filter((t) => get(t.id).status !== 'unlearned').length
}

export function percent(done: number, total: number) {
  return total ? Math.round((done / total) * 100) : 0
}

// 最近 365 天内连续打卡天数
export function streak(completionLog: CompletionLog) {
  let s = 0
  while (s < 365 && (completionLog[dateKey(s)]?.length || 0) > 0) s++
  return s
}

export function dateKey(offset: number) {
  const date = new Date()
  date.setDate(date.getDate() - offset)
  return date.toISOString().slice(0, 10)
}

// 最近点亮记录（按日期倒序，最多 8 条）
export function recentCompletions(completionLog: CompletionLog, allTopics: Topic[]) {
  const titleOf = new Map(allTopics.map((t) => [t.id, t.title]))
  return Object.entries(completionLog)
    .flatMap(([date, ids]) => ids.map((id) => ({ date, id })))
    .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id))
    .slice(0, 8)
    .map((item) => ({ ...item, title: titleOf.get(item.id) || item.id }))
}

// 最近 12 周热力图：返回 12 周 × 7 天的格子，含月份标签与未来占位
export function heatmapWeeks(completionLog: CompletionLog) {
  const dow = (new Date().getDay() + 6) % 7
  const cellOf = (offset: number) => {
    const date = new Date()
    date.setDate(date.getDate() - offset)
    const key = date.toISOString().slice(0, 10)
    return { key, count: completionLog[key]?.length || 0, month: date.getMonth() + 1, future: false }
  }
  const weeks = Array.from({ length: 12 }, (_, week) =>
    Array.from({ length: 7 }, (_, day) => {
      const offset = (11 - week) * 7 + (dow - day)
      return offset < 0 ? { key: `future-${week}-${day}`, count: 0, month: 0, future: true } : cellOf(offset)
    }))
  const monthLabels = weeks.map((week, index) => {
    const first = week.find((day) => !day.future)
    const prevFirst = index > 0 ? weeks[index - 1].find((day) => !day.future) : undefined
    if (!first) return ''
    return index === 0 || !prevFirst || first.month !== prevFirst.month ? first.month + '月' : ''
  })
  const seasonTotal = weeks.reduce((sum, week) => sum + week.reduce((s, day) => s + day.count, 0), 0)
  const weekCount = weeks[11].slice(0, dow + 1).reduce((s, day) => s + day.count, 0)
  return { weeks, monthLabels, seasonTotal, weekCount }
}
