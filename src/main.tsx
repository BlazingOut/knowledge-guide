// 星航日志 · 秋招知识星图 —— 应用入口与状态编排
// 数据源：自研课程（self-courses.json，由 scripts/sync-courses.js 生成）与 JavaGuide 外链

import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import basicsRaw from './data/计算机基础知识.json'
import backendRaw from './data/后端开发知识.json'
import aiRaw from './data/AI应用开发知识.json'
import selfRaw from './data/self-courses.json'
import './styles.css'

import type { Category, CompletionLog, Domain, Page, ReadingTarget, SourceId, Theme, Topic, UserState } from './types/knowledge'
import { emptyState } from './types/knowledge'
import {
  THEME_KEY, SOUND_KEY,
  readStates, writeStates, readCompletionLog, writeCompletionLog,
  readCustomTopics, writeCustomTopics, readLastPosition, writeLastPosition, todayKey,
} from './lib/storage'
import { playTick, playDing, playFanfare } from './lib/sound'
import Shell from './components/Shell'
import NavBar from './components/NavBar'
import ReadPage from './components/ReadPage'
import StarLogPage from './pages/StarLogPage'
import HomePage from './pages/HomePage'
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

const THEMES: Theme[] = ['night', 'sand', 'indigo', 'sage', 'warm']

function App() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem(THEME_KEY) as Theme | null
    if (saved && THEMES.includes(saved)) return saved
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'night' : 'warm'
  })
  const setTheme = (next: Theme) => { setThemeState(next); localStorage.setItem(THEME_KEY, next) }
  const [sourceId, setSourceId] = useState<SourceId>('self')
  const [page, setPage] = useState<Page>('home')
  const [domainId, setDomainId] = useState(sources[0].domains[0].id)
  const [activeId, setActiveId] = useState(sources[0].domains[0].data.children[0].id)
  const [customTopics, setCustomTopics] = useState(readCustomTopics)
  const [states, setStates] = useState<Record<string, UserState>>(readStates)
  const [completionLog, setCompletionLog] = useState<CompletionLog>(readCompletionLog)
  const [openCourseId, setOpenCourseId] = useState<string | null>(null)
  const [soundOn, setSoundOn] = useState(() => localStorage.getItem(SOUND_KEY) !== 'off')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [reading, setReading] = useState<ReadingTarget | null>(null)

  // 当前源领域 + 动态添加的自定义知识点合并
  // memo：保持领域/分类/知识点对象身份稳定，否则自习舱空态解析出的阅读目标会在打卡等
  // 重渲染时变成新引用，触发 ReadPage 按 [topic] 依赖重新拉取课文
  const currentSource = sources.find((s) => s.id === sourceId) ?? sources[0]
  const domains = useMemo(() => currentSource.domains.map((item) => ({
    ...item,
    data: { children: item.data.children.map((child) => ({ ...child, topics: [...child.topics, ...(customTopics[child.id] || [])] })) },
  })), [currentSource, customTopics])
  const domain = domains.find((item) => item.id === domainId) || domains[0]
  const active = domain.data.children.find((item) => item.id === activeId) || domain.data.children[0]
  // 星图下钻的当前课程（id 失配自动回落卡片视图；切领域/切源时在对应函数里清空）
  const openCourse = domain.data.children.find((item) => item.id === openCourseId) ?? null

  const get = (id: string) => states[id] || emptyState

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
    setOpenCourseId(null)
    setQuery(''); setFilter('all'); setPage('home')
  }
  const switchSource = (id: SourceId) => {
    if (id === sourceId) return
    const next = sources.find((s) => s.id === id) ?? sources[0]
    setSourceId(id)
    setDomainId(next.domains[0].id)
    setActiveId(next.domains[0].data.children[0].id)
    setOpenCourseId(null)
    setQuery(''); setFilter('all'); setReading(null)
    setPage('home')
  }

  // 打开课文阅读（自研课程）；记录来源页（返回时恢复来路）与上次位置（自习舱空态恢复）。
  // JavaGuide 保持外链
  const openRead = (topic: Topic, category: Category, owner: Domain) => {
    // 课程大纲是伪课题（id 带 -readme 后缀），不在课文列表里——写入 last-position 会破坏自习舱恢复
    if (!topic.id.endsWith('-readme')) writeLastPosition({ categoryId: category.id, topicId: topic.id })
    setReading({ topic, category, domain: owner, from: page })
    setPage('read')
  }
  const onReadTopic = (topic: Topic) => openRead(topic, active, domain)
  // 全局搜索结果分流：自研源进阅读页；JavaGuide 源定位到该分类的知识星库
  const onOpenTopic = (topic: Topic, category: Category, owner: Domain) => {
    if (sourceId === 'self') openRead(topic, category, owner)
    else open(category.id, 'library')
  }

  // 自习舱空态解析（M3 继续学习）：侧边栏直接进自习舱且无在读课文时，
  // 优先恢复上次位置（last-position），首次使用回退显示第一门课第一课。
  const fallbackReading = useMemo<ReadingTarget | null>(() => {
    if (page !== 'study' || reading || sourceId !== 'self') return null
    const last = readLastPosition()
    if (last) {
      for (const d of domains) {
        const category = d.data.children.find((c) => c.id === last.categoryId)
        const topic = category?.topics.find((t) => t.id === last.topicId)
        if (category && topic) return { topic, category, domain: d, from: 'study' }
      }
    }
    const d = domains[0]
    const category = d?.data.children[0]
    const topic = category?.topics[0]
    return d && category && topic ? { topic, category, domain: d, from: 'study' } : null
  }, [page, reading, domains, sourceId])

  // 在读目标：阅读页用 reading；自习舱页无 reading 时用空态解析结果
  const activeReading = page === 'read' ? reading : page === 'study' ? (reading ?? fallbackReading) : null

  // 连续学习流：按当前课程目录顺序切到下一篇（未开始时自动标记「学习中」）
  const readingIdx = activeReading ? activeReading.category.topics.findIndex((t) => t.id === activeReading.topic.id) : -1
  const hasNext = !!activeReading && readingIdx >= 0 && readingIdx < activeReading.category.topics.length - 1
  const goNext = () => {
    if (!activeReading || readingIdx < 0) return
    const next = activeReading.category.topics[readingIdx + 1]
    if (next) {
      setReading({ ...activeReading, topic: next })
      writeLastPosition({ categoryId: activeReading.category.id, topicId: next.id })
      if (get(next.id).status === 'unlearned') update(next.id, { status: 'learning' })
    } else {
      setReading(null)
      setPage(activeReading.from)
    }
  }

  const filtered = active.topics.filter((topic) => {
    const state = get(topic.id)
    return (!query || topic.title.includes(query)) && (filter === 'all' || filter === state.status || (filter === 'exposed' && state.exposed))
  })

  // 顶部导航条：星图下钻与课文阅读显示（返回 + 面包屑）；顶层视图不渲染
  let nav: { backLabel: string; onBack: () => void; crumbs: string[] } | null = null
  if (page === 'home' && openCourse) {
    nav = { backLabel: '返回课程列表', onBack: () => setOpenCourseId(null), crumbs: ['我的星图', domain.title, openCourse.title] }
  } else if ((page === 'read' || page === 'study') && activeReading) {
    const dest = activeReading.from === 'library' ? '知识星库' : '我的星图'
    nav = {
      backLabel: '返回',
      onBack: () => { setReading(null); setPage(activeReading.from === 'study' ? 'home' : activeReading.from) },
      crumbs: [dest, activeReading.category.title, activeReading.topic.title],
    }
  }

  // Esc 返回：导航条可见时生效；弹窗打开时让位给弹窗
  useEffect(() => {
    if (!nav) return
    const { onBack } = nav
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !document.querySelector('.modal-overlay')) onBack()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <Shell page={page} setPage={setPage} theme={theme} setTheme={setTheme} soundOn={soundOn} setSound={setSound} sourceId={sourceId} setSource={switchSource}>
      {nav && <NavBar backLabel={nav.backLabel} onBack={nav.onBack} crumbs={nav.crumbs} />}
      {(page === 'read' || page === 'study') && activeReading
        ? <ReadPage reading={activeReading} get={get} update={update} hasNext={hasNext} onNext={goNext} onBack={nav!.onBack} />
        : page === 'log'
          ? <StarLogPage domains={domains} get={get} completionLog={completionLog} switchDomain={switchDomain} />
          : page === 'home'
            ? <HomePage domain={domain} domains={domains} get={get} update={update} open={open} openCourse={openCourse} setOpenCourseId={setOpenCourseId} switchDomain={switchDomain} onOpenTopic={onOpenTopic} />
            : page === 'study'
              ? <div className="study-empty">
                  <h2>自习舱暂无可读课文</h2>
                  <p>当前课程源是 JavaGuide（外链课程），条目请到知识星库打开；切回自研课程后，这里会自动恢复上次阅读位置。</p>
                  <button className="tip-action" onClick={() => setPage('library')}>去知识星库 →</button>
                </div>
              : <DetailPage active={active} get={get} update={update} filtered={filtered} query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} addTopic={addTopic} removeTopic={removeTopic} domainTitle={domain.title} isSelf={sourceId === 'self'} onRead={onReadTopic} />}
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
  } catch (err) {
    const text = err instanceof Error ? err.message : String(err)
    console.error('自动更新失败：', err)
    // 显示具体错误（下载失败 / 签名校验失败 / 安装失败都能看到原因），不再静默
    try {
      const { message } = await import('@tauri-apps/plugin-dialog')
      await message(`更新失败：${text}`, { title: '星航日志 · 更新失败', kind: 'error' })
    } catch {
      window.alert(`更新失败：${text}`)
    }
  }
}

createRoot(document.getElementById('root')!).render(<App />)
void setupAutoUpdate()
