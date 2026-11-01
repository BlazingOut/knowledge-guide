// 星航日志页：全领域统计、热力图、连续打卡、领域进度与最近点亮

import type { CompletionLog, Domain, UserState } from '../types/knowledge'
import { doneCount, learningCount, percent, streak, recentCompletions, heatmapWeeks } from '../lib/progress'

type Props = {
  domains: Domain[]
  get: (id: string) => UserState
  completionLog: CompletionLog
  switchDomain: (id: string) => void
}

const warmQuotes = [
  '每一颗星星的点亮，都是未来面试时的底气。',
  '慢一点也没关系，星星不会跑，它一直在等你。',
  '今天的一小步，就是秋招路上的一大步。',
  '知识像星光，看似微弱，聚起来就是银河。',
  '别怕遗忘，复习过的星星会第二次发光。',
  '坚持打卡的你，已经在超越昨天的自己了。',
  '面试官的每一道题，都是你现在种下的种子。',
]

export default function StarLogPage({ domains, get, completionLog, switchDomain }: Props) {
  const allTopics = domains.flatMap((item) => item.data.children.flatMap((child) => child.topics))
  const total = allTopics.length
  const done = doneCount(allTopics, get)
  const learning = learningCount(allTopics, get)
  const verified = allTopics.filter((t) => get(t.id).verified).length
  const exposed = allTopics.filter((t) => get(t.id).exposed).length
  const coverage = percent(done, total)
  const days = streak(completionLog)
  const { weeks, monthLabels, seasonTotal, weekCount } = heatmapWeeks(completionLog)
  const recent = recentCompletions(completionLog, allTopics)
  const quote = warmQuotes[new Date().getDate() % warmQuotes.length]

  return (
    <div className="log">
      <header>
        <div>
          <small>星航日志 · 全领域统计</small>
          <h1>星航日志</h1>
          <p>每一次点亮都会被记录，这里是你的完整航行轨迹。</p>
        </div>
        <div className="voyage-badge">✦ 累计点亮 <b>{done} / {total}<span>知识覆盖率 {coverage}%</span></b></div>
      </header>

      <section className="log-stats">
        <div className="log-stat"><small>已完成</small><strong>{done}<i> / {total}</i></strong><span>覆盖率 {coverage}%</span></div>
        <div className="log-stat"><small>学习中</small><strong>{learning}</strong><span>{learning ? '继续保持节奏' : '暂无进行中'}</span></div>
        <div className="log-stat"><small>面试验证</small><strong>{verified}</strong><span>已通过验证的知识点</span></div>
        <div className="log-stat"><small>面试暴露</small><strong>{exposed}</strong><span>被面试官问到的知识点</span></div>
      </section>

      <div className="log-mid">
        <section className="heatmap">
          <div className="heatmap-head">
            <div><small>学习热力图</small><h2>最近 12 周点亮情况</h2></div>
            <div className="heatmap-head-right">
              <span>{seasonTotal} 个知识点已点亮</span>
              <div className="heatmap-legend"><span>少</span><i className="level-0" /><i className="level-1" /><i className="level-2" /><i className="level-3" /><i className="level-4" /><span>多</span></div>
            </div>
          </div>
          <div className="heatmap-body">
            <div className="heatmap-cal">
              <div className="heatmap-months">{monthLabels.map((label, index) => <span key={index}>{label}</span>)}</div>
              <div className="heatmap-grid-wrap">
                <div className="heatmap-weeks">{['一', '二', '三', '四', '五', '六', '日'].map((label, index) => <span key={label} className={index % 2 ? 'ghost' : ''}>{label}</span>)}</div>
                <div className="heatmap-grid">
                  {weeks.map((week) => week.map((day) => day.future
                    ? null
                    : <span key={day.key} className={'heat level-' + Math.min(day.count, 4)} title={day.key + '：' + day.count + ' 个'} />))}
                </div>
              </div>
            </div>
            <div className="heatmap-side">
              <div className="heatmap-side-item"><small>最长连续</small><strong>{days}<i> 天</i></strong></div>
              <div className="heatmap-side-item"><small>本周点亮</small><strong>{weekCount}<i> 个</i></strong></div>
            </div>
          </div>
        </section>
        <section className="log-warm"><span className="log-warm-star">✦</span><p>{quote}</p><small>暖心话语 · 今日寄语</small></section>
      </div>

      <div className="log-bottom">
        <section className="log-panel">
          <div className="log-panel-head"><small>领域进度</small><h2>三大知识星域</h2></div>
          <div className="log-domains">
            {domains.map((item) => {
              const topics = item.data.children.flatMap((child) => child.topics)
              const domainDone = doneCount(topics, get)
              const domainPercent = percent(domainDone, topics.length)
              return (
                <button className="log-domain" key={item.id} onClick={() => switchDomain(item.id)}>
                  <span className="log-domain-title">{item.title}</span>
                  <span className="log-domain-num">{domainDone} / {topics.length}</span>
                  <span className="bar"><i style={{ width: domainPercent + '%' }} /></span>
                  <em>{domainPercent}%</em>
                </button>
              )
            })}
          </div>
          <p className="log-hint">点击领域卡片可跳转到对应星图 ✦</p>
        </section>
        <section className="log-panel">
          <div className="log-panel-head"><small>最近点亮</small><h2>航行记录</h2></div>
          {recent.length
            ? <ul className="log-recent">{recent.map((item) => <li key={item.date + item.id}><small>{item.date}</small><span>{item.title}</span></li>)}</ul>
            : <p className="log-empty">还没有点亮记录，去「我的星图」选一课，点亮第一颗星星吧 ✦</p>}
        </section>
      </div>
    </div>
  )
}
