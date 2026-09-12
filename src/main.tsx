import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import basicsRaw from './data/计算机基础知识.json'
import backendRaw from './data/后端开发知识.json'
import aiRaw from './data/AI应用开发知识.json'
import './styles.css'

type Topic = { id: string; title: string; url: string }
type Category = { id: string; title: string; url: string; topics: Topic[] }
type Status = 'unlearned' | 'seen' | 'answerable'
type UserState = { status: Status; verified: boolean; exposed: boolean }
type Page = 'home' | 'checkin' | 'library'

type Domain = { id: string; title: string; description: string; data: { children: Category[] } }
const domains: Domain[] = [
  { id: 'basics', title: '计算机基础知识', description: '计算机网络、操作系统、数据结构和算法。', data: basicsRaw as { children: Category[] } },
  { id: 'backend', title: '后端开发', description: '数据库、开发工具、Web 后端和系统设计。', data: backendRaw as { children: Category[] } },
  { id: 'ai', title: 'AI 应用开发', description: '大模型、Agent、RAG、MCP、Prompt 工程与系统设计。', data: aiRaw as { children: Category[] } },
]
const icons = ['⌁', '▣', '⌬', '✦']
const labels: Record<Status, string> = { unlearned: '未学习', seen: '已了解', answerable: '可以回答' }
const empty: UserState = { status: 'unlearned', verified: false, exposed: false }

function App() {
  const [page, setPage] = useState<Page>('home')
  const [domainId, setDomainId] = useState('basics')
  const domain = domains.find((item) => item.id === domainId) || domains[0]
  const data = domain.data
  const [activeId, setActiveId] = useState(data.children[0].id)
  const [states, setStates] = useState<Record<string, UserState>>(() => JSON.parse(localStorage.getItem('knowledge-guide:user-state:v1') || '{}'))
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const active = data.children.find((item) => item.id === activeId) || data.children[0]
  const get = (id: string) => states[id] || empty
  const update = (id: string, patch: Partial<UserState>) => setStates((old) => {
    const next = { ...old, [id]: { ...get(id), ...patch } }
    localStorage.setItem('knowledge-guide:user-state:v1', JSON.stringify(next))
    return next
  })
  const open = (id: string, target: Page) => { setActiveId(id); setQuery(''); setFilter('all'); setPage(target) }
  const filtered = active.topics.filter((topic) => { const state = get(topic.id); return (!query || topic.title.includes(query)) && (filter === 'all' || filter === state.status || (filter === 'exposed' && state.exposed)) })
  const switchDomain = (id: string) => { const next = domains.find((item) => item.id === id) || domains[0]; setDomainId(next.id); setActiveId(next.data.children[0].id); setQuery(''); setFilter('all'); setPage('home') }
  return <Shell page={page} setPage={setPage}>{page === 'home' ? <Home domain={domain} domains={domains} get={get} open={open} switchDomain={switchDomain} /> : page === 'checkin' ? <Checkin active={active} get={get} update={update} setPage={setPage} /> : <Detail active={active} get={get} update={update} filtered={filtered} query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} setPage={setPage} />}</Shell>
}

function Shell({ page, setPage, children }: { page: Page; setPage: (page: Page) => void; children: React.ReactNode }) {
  return <div className="shell"><aside className="side"><div className="brand"><b>◈</b><span><strong>AI 应用开发</strong><small>秋招知识地图</small></span></div><nav><button className={page === 'home' ? 'on' : ''} onClick={() => setPage('home')}>⌂　知识地图</button><button className={page === 'checkin' ? 'on' : ''} onClick={() => setPage('checkin')}>✓　每日打卡</button><button className={page === 'library' ? 'on' : ''} onClick={() => setPage('library')}>◌　知识库</button></nav></aside><main>{children}</main></div>
}

function Home({ domain, domains, get, open, switchDomain }: { domain: Domain; domains: Domain[]; get: (id: string) => UserState; open: (id: string, page: Page) => void; switchDomain: (id: string) => void }) {
  return <><header><div><small>AI 应用开发 · 秋招准备</small><h1>知识地图</h1><p>选择一个领域开始今天的学习。</p></div></header><div className="domain-tabs">{domains.map((item) => <button className={item.id === domain.id ? 'active' : ''} onClick={() => switchDomain(item.id)} key={item.id}>{item.title}</button>)}</div><section className="cards">{domain.data.children.map((category, index) => { const done = category.topics.filter((topic) => get(topic.id).status !== 'unlearned').length; return <article className="card" key={category.id} onClick={() => open(category.id, 'checkin')}><div className={'ico i' + index % 4}>{icons[index % 4]}</div><label>{String(index + 1).padStart(2, '0')}<button className="library-entry" onClick={(event) => { event.stopPropagation(); open(category.id, 'library') }}>知识库</button></label><h3>{category.title}</h3><p>{category.topics.length} 个知识点 · {done ? '已完成 ' + done + ' 个' : '尚未开始'}</p><div className="bar"><i style={{ width: done / category.topics.length * 100 + '%' }} /></div></article> })}</section></>
}

function Detail({ active, get, update, filtered, query, setQuery, filter, setFilter, setPage }: { page?: Page; active: Category; get: (id: string) => UserState; update: (id: string, patch: Partial<UserState>) => void; filtered: Topic[]; query: string; setQuery: (value: string) => void; filter: string; setFilter: (value: string) => void; setPage: (page: Page) => void }) {
  const completed = active.topics.filter((topic) => get(topic.id).status !== 'unlearned').length
  return <><button className="back" onClick={() => setPage('home')}>← 返回知识地图</button><div className="catHead"><div><small>知识库 · 计算机基础知识</small><h1>{active.title}</h1><p>查看该领域的完整知识点、资料链接和面试标记。</p></div><a className="source-link" href={active.url} target="_blank">打开专题 ↗</a></div><div className="library-overview"><div><small>当前领域进度</small><strong>{completed} <i>/ {active.topics.length}</i></strong><span>已完成 {Math.round(completed / active.topics.length * 100)}%</span></div><div className="bar"><i style={{ width: completed / active.topics.length * 100 + '%' }} /></div></div><div className="toolbar"><div><h2>{active.title}知识点</h2><span>{filtered.length} / {active.topics.length} 个知识点</span></div><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="⌕ 搜索知识点" /></div><div className="filters">{['all', 'unlearned', 'seen', 'answerable', 'exposed'].map((item) => <button className={filter === item ? 'sel' : ''} onClick={() => setFilter(item)} key={item}>{item === 'all' ? '全部' : item === 'exposed' ? '面试暴露' : labels[item as Status]}</button>)}</div><div className="list">{filtered.map((topic, index) => <Topic key={topic.id} topic={topic} index={index} state={get(topic.id)} update={update} checkin={false} />)}</div></>
}

function Checkin({ active, get, update, setPage }: { active: Category; get: (id: string) => UserState; update: (id: string, patch: Partial<UserState>) => void; setPage: (page: Page) => void }) {
  const completed = active.topics.filter((topic) => get(topic.id).status !== 'unlearned').length
  const percent = Math.round(completed / active.topics.length * 100)
  return <><button className="back" onClick={() => setPage('home')}>←　知识地图</button><section className="checkin-head"><div className="checkin-copy"><small>每日打卡　›　计算机基础知识</small><h1>{active.title}<span className="sparkle">✦</span></h1><p>按顺序完成今天的知识点学习，逐步建立面试准备的完整闭环。</p></div><div className="checkin-summary"><div className="summary-label"><small>今日学习进度</small><strong>{completed}<i> / {active.topics.length}</i></strong><span>{percent}%</span></div><div className="progress-track"><i style={{ width: percent + '%' }} /></div><p>{completed === active.topics.length ? '今日目标已完成 ✦' : `还有 ${active.topics.length - completed} 个知识点待完成`}</p></div></section><div className="checkin-title"><div><small>今日任务</small><h2>一步一步完成学习</h2></div><span>{completed} / {active.topics.length} 已完成</span></div><div className="checkin-list">{active.topics.map((topic, index) => <StudyCard key={topic.id} topic={topic} index={index} state={get(topic.id)} update={update} />)}</div></>
}

function CheckinCard({ topic, index, state, update }: { topic: Topic; index: number; state: UserState; update: (id: string, patch: Partial<UserState>) => void }) {
  const done = state.status !== 'unlearned'
  const learning = state.status === 'seen'
  return <article className={'checkin-card ' + (done ? 'card-done' : '')}><div className="card-top"><em>{String(index + 1).padStart(2, '0')}</em><h3>{topic.title}</h3><span className={'card-status ' + (done ? 'done' : '')}>{done ? (learning ? '● 学习中' : '● 已完成') : '○ 未开始'}</span></div><div className="checkin-actions"><a href={topic.url} target="_blank">阅读资料 ↗</a><button onClick={() => update(topic.id, { status: done && !learning ? 'unlearned' : learning ? 'answerable' : 'seen' })}>{done ? (learning ? '继续学习 →' : '重新学习') : '开始学习 →'}</button></div></article>
}

function StudyCard({ topic, index, state, update }: { topic: Topic; index: number; state: UserState; update: (id: string, patch: Partial<UserState>) => void }) {
  const done = state.status !== 'unlearned'
  const learning = state.status === 'seen'
  const priority = index < 2 ? '必背' : index < 6 ? '高频' : '中频'
  const question = topic.title.includes('握手') ? 'TCP 建立连接时为什么需要三次握手？' : topic.title.includes('HTTP') ? 'HTTP 与 HTTPS 有什么区别？' : `${topic.title}的核心原理是什么？`
  return <article className={'study-card ' + (done ? 'card-done' : '')}><div className="card-top"><em>{String(index + 1).padStart(2, '0')}</em><h3>{topic.title}</h3><span className={'card-status ' + (done ? 'done' : '')}>{done ? '● 已完成' : '○ 未开始'}</span></div><div className="priority">{priority}</div><p className="question">{question}</p>{learning && <div className="learning-progress"><span>学习中</span><i><b /></i><small>3/5</small></div>}<div className="card-foot"><span>◉　JavaGuide　 ·　⌘　{activeTitle(topic.url)}</span><button onClick={() => update(topic.id, { status: done && !learning ? 'unlearned' : learning ? 'answerable' : 'seen' })}>{done ? (learning ? '继续学习 →' : '重新学习') : '开始学习 →'}</button></div></article>
}

function activeTitle(url: string) { return url.includes('/network/') ? '计算机网络' : '知识库' }

function Topic({ topic, index, state, update, checkin }: { topic: Topic; index: number; state: UserState; update: (id: string, patch: Partial<UserState>) => void; checkin: boolean }) {
  const next: Status = state.status === 'unlearned' ? 'seen' : state.status === 'seen' ? 'answerable' : 'unlearned'
  return <article className={checkin ? 'checkin-card' : 'topic'}><em>{String(index + 1).padStart(2, '0')}</em><div><h3>{topic.title} <span className={'st ' + state.status}>{labels[state.status]}</span></h3>{checkin ? <div className="checkin-actions"><a href={topic.url} target="_blank">阅读资料 ↗</a><button className={state.status !== 'unlearned' ? 'done-button' : ''} onClick={() => update(topic.id, { status: next })}>{state.status === 'unlearned' ? '完成打卡' : state.status === 'seen' ? '标记为可以回答' : '重新开始'}</button></div> : <section><a href={topic.url} target="_blank">阅读资料 ↗</a><button onClick={() => update(topic.id, { status: next })}>标记为{labels[next]}</button><button onClick={() => update(topic.id, { verified: !state.verified })}>◉ {state.verified ? '已验证' : '面试验证'}</button><button onClick={() => update(topic.id, { exposed: !state.exposed })}>⚑ {state.exposed ? '已暴露' : '标记暴露'}</button></section>}</div></article>
}

createRoot(document.getElementById('root')!).render(<App />)
