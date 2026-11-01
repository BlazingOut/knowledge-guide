// 我的星图页：Hero（标题 + 当前源整体进度）+ 全局搜索 + 领域卡片 + 下一站 CTA
// 交互模型 v2（docs/界面交互重构方案.md 修订）：选课三级浏览（领域 → 课程 → 章节目录）都在本页完成，
// 点具体课时才进入自习舱（纯阅读页）

import { useState } from 'react'
import type { Category, Domain, Page, Topic, UserState } from '../types/knowledge'
import { labels } from '../types/knowledge'
import { doneCount, startedCount, percent } from '../lib/progress'
import PlanetIcon from '../components/PlanetIcon'
import StudyCard from '../components/StudyCard'

type Props = {
  domain: Domain
  domains: Domain[]
  get: (id: string) => UserState
  update: (id: string, patch: Partial<UserState>) => void
  open: (categoryId: string, page: Page) => void
  openCourse: Category | null
  setOpenCourseId: (id: string | null) => void
  switchDomain: (id: string) => void
  onOpenTopic: (topic: Topic, category: Category, domain: Domain) => void
}

const planetTypes = ['network', 'ringed', 'node', 'comet'] as const

export default function HomePage({ domain, domains, get, update, open, openCourse, setOpenCourseId, switchDomain, onOpenTopic }: Props) {
  const [query, setQuery] = useState('')
  // 下钻课程的进度指标（一次计算，避免 JSX 内重复统计）
  const courseDone = openCourse ? doneCount(openCourse.topics, get) : 0
  const coursePct = openCourse ? percent(courseDone, openCourse.topics.length) : 0
  const courseNext = openCourse?.topics.find((topic) => get(topic.id).status !== 'completed')

  // 当前源整体进度：全部知识点完成数 / 总数
  const allTopics = domains.flatMap((item) => item.data.children.flatMap((child) => child.topics))
  const done = doneCount(allTopics, get)
  const pct = percent(done, allTopics.length)

  // 下一站：当前领域第一个未完成的知识点（完成全部则显示庆祝文案）
  const next = (() => {
    for (const category of domain.data.children) {
      for (const topic of category.topics) {
        if (get(topic.id).status !== 'completed') return { topic, category }
      }
    }
    return null
  })()

  // 全局搜索：当前源全部知识点平铺
  const results = query.trim()
    ? domains.flatMap((item) => item.data.children.flatMap((child) => child.topics))
        .filter((topic) => topic.title.includes(query.trim()))
        .map((topic) => {
          const category = domains.flatMap((item) => item.data.children).find((child) => child.topics.includes(topic))
          const owner = domains.find((item) => item.data.children.some((child) => child.topics.includes(topic)))
          return { topic, category, owner }
        })
        .filter((r): r is { topic: Topic; category: Category; owner: Domain } => !!r.category && !!r.owner)
        .slice(0, 40)
    : []

  return (
    <div className="home">
      <header className="hero">
        <div>
          {openCourse ? (
            <>
              <small>我的星图　›　{domain.title}</small>
              <h1>{openCourse.title}</h1>
              <p>选一课进入自习舱阅读，进度与打卡在这里同步。</p>
            </>
          ) : (
            <>
              <small>AI 应用开发 · 秋招准备</small>
              <h1>我的知识星图</h1>
              <p>每掌握一个知识点，就点亮一颗星星。</p>
            </>
          )}
        </div>
        {openCourse ? (
          <div className="hero-progress" aria-label="课程进度">
            <small>课程进度</small>
            <strong>{courseDone}<i> / {openCourse.topics.length}</i></strong>
            <div className="progress-track"><i style={{ width: coursePct + '%' }} /></div>
            <span>{coursePct}% · 已点亮 {courseDone} 颗星星</span>
          </div>
        ) : (
          <div className="hero-progress" aria-label="学习进度">
            <small>学习进度</small>
            <strong>{done}<i> / {allTopics.length}</i></strong>
            <div className="progress-track"><i style={{ width: pct + '%' }} /></div>
            <span>{pct}% · 已点亮 {done} 颗星星</span>
          </div>
        )}
      </header>

      <div className="global-search">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="⌕ 全局搜索知识点（跨全部分类）" />
      </div>

      <div className="home-body">
        {query.trim() ? (
          <section className="search-results">
            <div className="search-results-head"><small>搜索结果</small><h2>{results.length} 个知识点</h2></div>
            {results.length ? (
              <div className="list">
                {results.map(({ topic, category, owner }) => (
                  <button className="search-hit" key={topic.id} onClick={() => onOpenTopic(topic, category, owner)}>
                    <em>{owner.title} · {category.title}</em>
                    <h3>{topic.title}</h3>
                    <span className={'st ' + get(topic.id).status}>{labels[get(topic.id).status]}</span>
                  </button>
                ))}
              </div>
            ) : <p className="log-empty">没有匹配的知识点，换个关键词试试 ✦</p>}
          </section>
        ) : openCourse ? (
          <>
            <div className="checkin-title">
              <div><small>章节目录</small><h2>{openCourse.topics.length} 节 · 按顺序学</h2></div>
              <div className="course-side">
                {courseNext
                  ? <button className="tip-action" onClick={() => onOpenTopic(courseNext, openCourse, domain)}>继续学：{courseNext.title} →</button>
                  : <small>本课全部读完 ✦ 换一门课继续吧</small>}
                <span>{courseDone} / {openCourse.topics.length} 已完成</span>
              </div>
            </div>
            <div className="checkin-list">
              {openCourse.topics.map((topic, index) => (
                <StudyCard key={topic.id} topic={topic} index={index} state={get(topic.id)} update={update}
                  isSelf={domain.source?.type === 'self'} categoryTitle={openCourse.title}
                  onRead={(t) => onOpenTopic(t, openCourse, domain)} />
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="domain-tabs">
              {domains.map((item) => <button className={item.id === domain.id ? 'active' : ''} onClick={() => switchDomain(item.id)} key={item.id}>{item.title}</button>)}
            </div>
            <section className="cards">
              {domain.data.children.map((category, index) => {
                const started = startedCount(category.topics, get)
                const completed = doneCount(category.topics, get)
                const glow = completed === category.topics.length ? 'done' : started > 0 ? 'learning' : 'idle'
                return (
                  <article className="card" key={category.id} onClick={() => setOpenCourseId(category.id)}>
                    <PlanetIcon kind={planetTypes[index % planetTypes.length]} glow={glow} />
                    <label>{String(index + 1).padStart(2, '0')}
                      <button className="library-entry" onClick={(event) => { event.stopPropagation(); open(category.id, 'library') }}>知识星库</button>
                    </label>
                    <h3>{category.title}</h3>
                    <p>{category.topics.length} 个知识点 · {started ? '已点亮 ' + started + ' 颗星星' : '还未点亮'}</p>
                    <div className="bar"><i style={{ width: percent(started, category.topics.length) + '%' }} /></div>
                  </article>
                )
              })}
            </section>
            <section className="tip tip-next">
              <strong>✦</strong>
              <div>
                <small>{next ? '下一站' : '里程碑'}</small>
                <h3>{next ? `${next.category.title} · ${next.topic.title}` : '本领域已全部点亮'}</h3>
                <p>{next ? '从这一个知识点开始，继续点亮你的知识宇宙。' : '这一片星域已经全部点亮，切个领域继续航行吧。'}</p>
              </div>
              {next && <button className="tip-action" onClick={() => onOpenTopic(next.topic, next.category, domain)}>继续学习</button>}
            </section>
          </>
        )}
      </div>
    </div>
  )
}
