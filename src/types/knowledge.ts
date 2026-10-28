// 统一知识数据结构：领域 → 分类 → 知识点；自研课程与 JavaGuide 共用同一 schema

export type Topic = { id: string; title: string; url: string; codeFiles?: string[] }
export type Category = { id: string; title: string; url: string; readme?: string; topics: Topic[] }
export type Domain = {
  id: string
  title: string
  description: string
  source?: { type: 'self' | 'javaguide'; name: string; url: string }
  data: { children: Category[] }
}

export type Status = 'unlearned' | 'learning' | 'completed'
export type UserState = { status: Status; verified: boolean; exposed: boolean }
export type CompletionLog = Record<string, string[]>
export type Page = 'log' | 'home' | 'checkin' | 'library' | 'read'
export type SourceId = 'self' | 'javaguide'
export type Source = { id: SourceId; title: string; domains: Domain[] }

// 课文阅读目标：携带所在分类/领域上下文（用于「下一篇」与来源标注）
export type ReadingTarget = { topic: Topic; category: Category; domain: Domain }

export const labels: Record<Status, string> = { unlearned: '未开始', learning: '学习中', completed: '已完成' }
export const emptyState: UserState = { status: 'unlearned', verified: false, exposed: false }

// 历史兼容：旧版本曾用 seen/answerable 表示已掌握，统一归并为 completed
export function normalizeStatus(raw: string | undefined): Status {
  if (raw === 'seen' || raw === 'answerable' || raw === 'completed') return 'completed'
  if (raw === 'learning') return 'learning'
  return 'unlearned'
}
