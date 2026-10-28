// 今日航行页：按顺序完成知识点学习，逐步建立面试准备闭环

import type { Category, Page, Topic, UserState } from '../types/knowledge'
import StudyCard from '../components/StudyCard'
import { doneCount, percent } from '../lib/progress'

type Props = {
  active: Category
  get: (id: string) => UserState
  update: (id: string, patch: Partial<UserState>) => void
  setPage: (page: Page) => void
  domainTitle: string
  isSelf: boolean
  onRead?: (topic: Topic) => void
}

export default function CheckinPage({ active, get, update, setPage, domainTitle, isSelf, onRead }: Props) {
  const completed = doneCount(active.topics, get)
  const pct = percent(completed, active.topics.length)
  const allDone = active.topics.length > 0 && completed === active.topics.length

  return (
    <>
      <button className="back" onClick={() => setPage('home')}>←　知识地图</button>
      <section className={allDone ? 'checkin-head checkin-all-done' : 'checkin-head'}>
        <div className="checkin-copy">
          <small>每日打卡　›　{domainTitle}</small>
          <h1>{active.title}<span className="sparkle">✦</span></h1>
          <p>按顺序完成今天的知识点学习，逐步建立面试准备的完整闭环。</p>
        </div>
        <div className="checkin-summary">
          <div className="summary-label"><small>学习完成进度</small><strong>{completed}<i> / {active.topics.length}</i></strong><span>{pct}%</span></div>
          <div className="progress-track"><i style={{ width: pct + '%' }} /></div>
          <p>{allDone ? '今日目标已完成 ✦' : `还有 ${active.topics.length - completed} 个知识点待完成`}</p>
        </div>
      </section>
      <div className="checkin-title">
        <div><small>今日任务</small><h2>一步一步完成学习</h2></div>
        <span>{completed} / {active.topics.length} 已完成</span>
      </div>
      <div className="checkin-list">
        {active.topics.map((topic, index) => (
          <StudyCard key={topic.id} topic={topic} index={index} state={get(topic.id)} update={update} isSelf={isSelf} categoryTitle={active.title} onRead={onRead} />
        ))}
      </div>
      {allDone && <div className="celebration" aria-hidden="true">{['✦', '✧', '✶', '✧', '✦', '✧'].map((star, index) => <span key={index} style={{ left: 6 + index * 16 + '%', animationDelay: index * 0.35 + 's' }}>{star}</span>)}</div>}
    </>
  )
}
