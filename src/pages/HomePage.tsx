// 我的星图页：课程源领域卡片 + 全局搜索（跨当前源全部知识点）

import { useState } from 'react'
import type { Category, Domain, Page, Topic, UserState } from '../types/knowledge'
import { labels } from '../types/knowledge'
import { startedCount, percent } from '../lib/progress'

type Props = {
  domain: Domain
  domains: Domain[]
  get: (id: string) => UserState
  open: (categoryId: string, page: Page) => void
  switchDomain: (id: string) => void
  onOpenTopic: (topic: Topic, category: Category, domain: Domain) => void
}

const planetTypes = ['network', 'ringed', 'node', 'comet'] as const

export default function HomePage({ domain, domains, get, open, switchDomain, onOpenTopic }: Props) {
  const [query, setQuery] = useState('')

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
    <>
      <header>
        <div>
          <small>AI 应用开发 · 秋招准备</small>
          <h1>我的知识星图</h1>
          <p>每掌握一个知识点，就点亮一颗星星。</p>
        </div>
        <div className="voyage-badge">✦ 当前航程 <b>探索阶段</b><span>知识准备中</span></div>
      </header>

      <div className="global-search">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="⌕ 全局搜索知识点（跨全部分类）" />
      </div>

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
      ) : (
        <>
          <div className="domain-tabs">
            {domains.map((item) => <button className={item.id === domain.id ? 'active' : ''} onClick={() => switchDomain(item.id)} key={item.id}>{item.title}</button>)}
          </div>
          <section className="cards">
            {domain.data.children.map((category, index) => {
              const done = startedCount(category.topics, get)
              return (
                <article className="card" key={category.id} onClick={() => open(category.id, 'checkin')}>
                  <div className={'ico planet-orb planet-' + planetTypes[index % planetTypes.length]} aria-hidden="true" />
                  <label>{String(index + 1).padStart(2, '0')}
                    <button className="library-entry" onClick={(event) => { event.stopPropagation(); open(category.id, 'library') }}>知识星库</button>
                  </label>
                  <h3>{category.title}</h3>
                  <p>{category.topics.length} 个知识点 · {done ? '已点亮 ' + done + ' 颗星星' : '还未点亮'}</p>
                  <div className="bar"><i style={{ width: percent(done, category.topics.length) + '%' }} /></div>
                </article>
              )
            })}
          </section>
          <section className="tip"><strong>✦</strong><div><small>今晚的航行</small><h3>从一颗小星球开始</h3><p>选择一个知识领域，继续建立你的知识宇宙。</p></div></section>
        </>
      )}
    </>
  )
}
