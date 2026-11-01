// 知识点打卡卡片：状态切换、整卡点击进入阅读（自研课程）或外开链接（JavaGuide）

import type { Topic, UserState } from '../types/knowledge'
import { nextStatus, openLink } from '../lib/storage'

type Props = {
  topic: Topic
  index: number
  state: UserState
  update: (id: string, patch: Partial<UserState>) => void
  isSelf: boolean
  categoryTitle: string
  onRead?: (topic: Topic) => void
}

export default function StudyCard({ topic, index, state, update, isSelf, categoryTitle, onRead }: Props) {
  const done = state.status === 'completed'
  const learning = state.status === 'learning'
  const priority = index < 2 ? '必背' : index < 6 ? '高频' : '中频'
  const question = topic.title.includes('握手')
    ? 'TCP 建立连接时为什么需要三次握手？'
    : topic.title.includes('HTTP')
      ? 'HTTP 与 HTTPS 有什么区别？'
      : `${topic.title}的核心原理是什么？`
  const next = nextStatus(state.status)

  const enter = () => {
    if (isSelf && onRead) onRead(topic)
    else void openLink(topic.url)
  }

  return (
    <article className={'study-card ' + (done ? 'card-done' : '')} onClick={enter} role="link" tabIndex={0}
      onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') enter() }}>
      {done && <span className="burst" aria-hidden="true">✦</span>}
      <div className="card-top">
        <em>{String(index + 1).padStart(2, '0')}</em>
        <h3>{topic.title}</h3>
        <span className={'card-status ' + (done ? 'done' : '')}>{done ? '● 已完成' : learning ? '● 学习中' : '○ 未开始'}</span>
      </div>
      <div className="priority">{priority}</div>
      <p className="question">{question}</p>
      {learning && <div className="learning-progress"><span>学习中</span><i><b /></i><small>进行中</small></div>}
      <div className="card-foot">
        <span>◉　{isSelf ? '自研课程' : 'JavaGuide'}　 ·　⌘　{isSelf ? categoryTitle : (topic.url.includes('/network/') ? '计算机网络' : '知识库')}</span>
        <button onClick={(event) => { event.stopPropagation(); update(topic.id, { status: next }) }}>
          {done ? '重新学习 →' : learning ? '已完成 →' : '开始学习 →'}
        </button>
      </div>
    </article>
  )
}
