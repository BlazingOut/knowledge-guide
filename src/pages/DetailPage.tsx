// 知识星库页：当前分类知识点列表、搜索、筛选、面试标记与动态添加

import { useState } from 'react'
import type { Category, Page, Topic, UserState } from '../types/knowledge'
import { labels } from '../types/knowledge'
import { startedCount, percent } from '../lib/progress'
import { openLink } from '../lib/storage'
import TopicItem from '../components/TopicItem'

type Props = {
  active: Category
  get: (id: string) => UserState
  update: (id: string, patch: Partial<UserState>) => void
  filtered: Topic[]
  query: string
  setQuery: (value: string) => void
  filter: string
  setFilter: (value: string) => void
  setPage: (page: Page) => void
  addTopic: (categoryId: string, title: string, url: string) => void
  removeTopic: (categoryId: string, topicId: string) => void
  domainTitle: string
  isSelf: boolean
  onRead?: (topic: Topic) => void
}

export default function DetailPage({ active, get, update, filtered, query, setQuery, filter, setFilter, setPage, addTopic, removeTopic, domainTitle, isSelf, onRead }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')

  const completed = startedCount(active.topics, get)
  const pct = percent(completed, active.topics.length)

  const closeForm = () => { setShowForm(false); setName(''); setUrl('') }
  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!name.trim() || !url.trim()) return
    addTopic(active.id, name.trim(), url.trim())
    closeForm()
  }

  // 自研课程：专题链接改为应用内阅读课程大纲（README）
  const openSource = () => {
    if (isSelf && active.readme) {
      onRead?.({ id: active.id + '-readme', title: active.title + ' · 课程大纲', url: active.readme })
    } else {
      void openLink(active.url)
    }
  }

  return (
    <>
      <button className="back" onClick={() => setPage('home')}>← 返回知识地图</button>
      <div className="catHead">
        <div>
          <small>知识星库 · {domainTitle}</small>
          <h1>{active.title}</h1>
          <p>查看该领域的完整知识点、资料链接和面试标记。</p>
        </div>
        <button className="source-link" onClick={openSource}>{isSelf ? '读课程大纲 ↗' : '打开专题 ↗'}</button>
      </div>
      <div className="library-overview">
        <div className="library-progress-copy"><small>当前领域进度</small><strong>{completed}<i> / {active.topics.length}</i></strong><span>已完成 {pct}%</span></div>
        <div className="bar"><i style={{ width: pct + '%' }} /></div>
      </div>
      <div className="toolbar">
        <h2>知识点</h2>
        <div className="toolbar-actions">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="⌕ 搜索知识点" />
          <button className="add-topic-btn" title="添加知识点" onClick={() => setShowForm(true)}>＋</button>
        </div>
      </div>
      <div className="filters">
        {['all', 'unlearned', 'learning', 'completed', 'exposed'].map((item) => (
          <button className={filter === item ? 'sel' : ''} onClick={() => setFilter(item)} key={item}>
            {item === 'all' ? '全部' : item === 'exposed' ? '面试暴露' : labels[item as keyof typeof labels]}
          </button>
        ))}
      </div>
      <div className="list">
        {filtered.map((topic, index) => (
          <TopicItem key={topic.id} topic={topic} index={index} state={get(topic.id)} update={update} checkin={false} isSelf={isSelf} onRead={onRead}
            onDelete={topic.id.startsWith('custom-') ? () => removeTopic(active.id, topic.id) : undefined} />
        ))}
      </div>
      {showForm && (
        <div className="modal-overlay" onClick={closeForm}>
          <form className="modal" onClick={(event) => event.stopPropagation()} onSubmit={submit}>
            <h3>添加知识点</h3>
            <small>将添加到「{active.title}」</small>
            <input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="课程名" />
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="网址，如 https://javaguide.cn/..." />
            <div className="modal-actions">
              <button type="button" onClick={closeForm}>取消</button>
              <button type="submit" className="primary">添加</button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}
