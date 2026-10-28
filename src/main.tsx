// 星航日志 · 秋招知识星图 —— 应用入口与状态编排
// 数据源：自研课程（self-courses.json，由 scripts/sync-courses.js 生成）与 JavaGuide 外链

import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import basicsRaw from './data/计算机基础知识.json'
import backendRaw from './data/后端开发知识.json'
import aiRaw from './data/AI应用开发知识.json'
import selfRaw from './data/self-courses.json'
import './styles.css'

import type { Category, CompletionLog, Domain, Page, SourceId, Topic, UserState } from './types/knowledge'
import { emptyState } from './types/knowledge'
import {
  THEME_KEY, SOUND_KEY,
  readStates, writeStates, readCompletionLog, writeCompletionLog,
  readCustomTopics, writeCustomTopics, todayKey,
} from './lib/storage'
import { playTick, playDing, playFanfare } from './lib/sound'
import Shell from './components/Shell'
import ReadPage from './components/ReadPage'
import StarLogPage from './pages/StarLogPage'
import HomePage from './pages/HomePage'
import CheckinPage from './pages/CheckinPage'
import DetailPage from './pages/DetailPage'

type RawDomain = { id: string; title: string; description: string; source: Domain['source']; children: Category[] }

// 自研课程：脚本生成的 JSON 顶层含 description/source，包装为统一 Domain
const selfDomains: Domain[] = (selfRaw as RawDomain[]).map((d) => ({
  id: d.id, title: d.title, description: d.description, source: d.source, data: { children: d.children },
}))

// JavaGuide 三领域（保持原数据与说明）
const javaguideDomains: Domain[] = [
  { id: 'basics', title: '计算机基础知识', description: '计算机网络、操作系统、数据结构和算法。', source: { type: 'javaguide', name: 'JavaGuide', url: 'https://javaguide.cn/' }, data: basicsRaw as { children: Category[] } },
  { id: 'backend', title: '后端开发', description: '数据库、开发工具、Web 后端和系统设计。', source: { type: 'javaguide', name: 'JavaGuide', url: 'https://javaguide.cn/' }, data: backendRaw as { children: Category[] } },
  { id: 'ai', title: 'AI 应用开发', description: '大模型、Agent、RAG、MCP、Prompt 工程与系统设计。', source: { type: 'javaguide', name: 'JavaGuide', url: 'https://javaguide.cn/' }, data: aiRaw as { children: Category[] } },
]

const sources = [
  { id: 'self', title: '自研课程', domains: selfDomains },
  { id: 'javaguide', title: 'JavaGuide', domains: javaguideDomains },
] as const satisfies ReadonlyArray<{ id: SourceId; title: string; domains: Domain[] }>

function App() {
  const [theme, setTheme] = useState<'night' | 'warm'>(() => {
    const saved = localStorage.getItem(THEME_KEY)
    if (saved === 'night' || saved === 'warm') return saved
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'night' : 'warm'
  })
  const [sourceId, setSourceId] = useState<SourceId>('self')
  const [page, setPage] = useState<Page>('log')
  const [domainId, setDomainId] = useState(sources[0].domains[0].id)
  const [activeId, setActiveId] = useState(sources[0].domains[0].data.children[0].id)
  const [customTopics, setCustomTopics] = useState(readCustomTopics)
  const [states, setStates] = useState<Record<string, UserState>>(readStates)
  const [completionLog, setCompletionLog] = useState<CompletionLog>(readCompletionLog)
  const [soundOn, setSoundOn] = useState(() => localStorage.getItem(SOUND_KEY) !== 'off')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [reading, setReading] = useState<{ topic: Topic; category: Category; domain: Domain } | null>(null)

  // 当前源领域 + 动态添加的自定义知识点合并
  const currentSource = sources.find((s) => s.id === sourceId) ?? sources[0]
  const domains = currentSource.domains.map((item) => ({
    ...item,
    data: { children: item.data.children.map((child) => ({ ...child, topics: [...child.topics, ...(customTopics[child.id] || [])] })) },
  }))
  const domain = domains.find((item) => item.id === domainId) || domains[0]
  const active = domain.data.children.find((item) => item.id === activeId) || domain.data.children[0]

  const get = (id: string) => states[id] || emptyState

  const changeTheme = (next: 'night' | 'warm') => { setTheme(next); localStorage.setItem(THEME_KEY, next) }
  const setSound = (on: boolean) => { setSoundOn(on); localStorage.setItem(SOUND_KEY, on ? 'on' : 'off') }

  const addTopic = (categoryId: string, title: string, url: string) => setCustomTopics((old) => {
    const topic: Topic = { id: 'custom-' + Date.now().toString(36), title, url }
    const next = { ...old, [categoryId]: [...(old[categoryId] || []), topic] }
    writeCustomTopics(next)
    return next
  })
  const removeTopic = (categoryId: string, topicId: string) => setCustomTopics((old) => {
    const next = { ...old, [categoryId]: (old[categoryId] || []).filter((topic) => topic.id !== topicId) }
    writeCustomTopics(next)
    return next
  })

  const update = (id: string, patch: Partial<UserState>) => {
    // 音效反馈：开始学习轻响，点亮“叮”，点亮本专题最后一颗星时奏小号角
    if (soundOn && patch.status && patch.status !== get(id).status) {
      if (patch.status === 'completed') {
        const category = domains.flatMap((item) => item.data.children).find((child) => child.topics.some((topic) => topic.id === id))
        const allDone = !!category && category.topics.every((topic) => topic.id === id || (states[topic.id] || emptyState).status === 'completed')
        ;(allDone ? playFanfare : playDing)()
      } else if (patch.status === 'learning') playTick()
    }
    setStates((old) => {
      const prev = old[id] || emptyState
      const next = { ...old, [id]: { ...prev, ...patch } }
      writeStates(next)
      if (patch.status === 'completed' && prev.status === 'learning') {
        setCompletionLog((log) => {
          const key = todayKey()
          const nextLog = { ...log, [key]: Array.from(new Set([...(log[key] || []), id])) }
          writeCompletionLog(nextLog)
          return nextLog
        })
      }
      return next
    })
  }

  const open = (id: string, target: Page) => { setActiveId(id); setQuery(''); setFilter('all'); setPage(target) }
  const switchDomain = (id: string) => {
    const next = domains.find((item) => item.id === id) || domains[0]
    setDomainId(next.id)
    setActiveId(next.data.children[0].id)
    setQuery(''); setFilter('all'); setPage('home')
  }
  const switchSource = (id: SourceId) => {
    if (id === sourceId) return
    const next = sources.find((s) => s.id === id) ?? sources[0]
    setSourceId(id)
    setDomainId(next.domains[0].id)
    setActiveId(next.domains[0].data.children[0].id)
    setQuery(''); setFilter('all'); setReading(null)
    setPage('home')
  }

  // 打开课文阅读（自研课程）；JavaGuide 保持外链
  const openRead = (topic: Topic, category: Category, owner: Domain) => {
    setReading({ topic, category, domain: owner })
    setPage('read')
  }
  const onReadTopic = (topic: Topic) => openRead(topic, active, domain)
  // 全局搜索结果分流：自研源进阅读页；JavaGuide 源定位到该分类的知识星库
  const onOpenTopic = (topic: Topic, category: Category, owner: Domain) => {
    if (sourceId === 'self') openRead(topic, category, owner)
    else open(category.id, 'library')
  }

  // 连续学习流：按当前分类顺序切到下一篇（未开始时自动标记「学习中」）
  const readingIdx = reading ? reading.category.topics.findIndex((t) => t.id === reading.topic.id) : -1
  const hasNext = !!reading && readingIdx >= 0 && readingIdx < reading.category.topics.length - 1
  const goNext = () => {
    if (!reading || readingIdx < 0) return
    const next = reading.category.topics[readingIdx + 1]
    if (next) {
      setReading({ ...reading, topic: next })
      if (get(next.id).status === 'unlearned') update(next.id, { status: 'learning' })
    } else {
      setReading(null)
      setPage('checkin')
    }
  }

  const filtered = active.topics.filter((topic) => {
    const state = get(topic.id)
    return (!query || topic.title.includes(query)) && (filter === 'all' || filter === state.status || (filter === 'exposed' && state.exposed))
  })

  return (
    <Shell page={page} setPage={setPage} theme={theme} setTheme={changeTheme} soundOn={soundOn} setSound={setSound} sourceId={sourceId} setSource={switchSource}>
      {page === 'read' && reading
        ? <ReadPage reading={reading} get={get} update={update} hasNext={hasNext} onNext={goNext} onBack={() => { setReading(null); setPage('checkin') }} />
        : page === 'log'
          ? <StarLogPage domains={domains} get={get} completionLog={completionLog} switchDomain={switchDomain} />
          : page === 'home'
            ? <HomePage domain={domain} domains={domains} get={get} open={open} switchDomain={switchDomain} onOpenTopic={onOpenTopic} />
            : page === 'checkin'
              ? <CheckinPage active={active} get={get} update={update} setPage={setPage} domainTitle={domain.title} isSelf={sourceId === 'self'} onRead={onReadTopic} />
              : <DetailPage active={active} get={get} update={update} filtered={filtered} query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} setPage={setPage} addTopic={addTopic} removeTopic={removeTopic} domainTitle={domain.title} isSelf={sourceId === 'self'} onRead={onReadTopic} />}
    </Shell>
  )
}

// 桌面端自动更新：启动时静默检查更新清单，发现新版本弹窗询问后下载安装并重启。
// 网页环境（无 Tauri 内核）自动跳过，任何失败均静默处理，不打扰正常使用。
async function setupAutoUpdate() {
  if (!('__TAURI_INTERNALS__' in window)) return
  try {
    const { check } = await import('@tauri-apps/plugin-updater')
    const { ask } = await import('@tauri-apps/plugin-dialog')
    const { relaunch } = await import('@tauri-apps/plugin-process')
    const update = await check()
    if (update) {
      const yes = await ask(`发现新版本 ${update.version}，是否立即下载并安装更新？`, { title: '星航日志 · 软件更新', kind: 'info' })
      if (yes) {
        await update.downloadAndInstall()
        await relaunch()
      }
    }
  } catch {
    // 无网络或更新服务不可用时静默跳过
  }
}

createRoot(document.getElementById('root')!).render(<App />)
void setupAutoUpdate()
