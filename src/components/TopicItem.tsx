// 知识星库条目：状态切换、面试标记、阅读入口（自研课程应用内读课文）

import type { Topic, UserState } from '../types/knowledge'
import { labels } from '../types/knowledge'
import { nextStatus, openLink } from '../lib/storage'

type Props = {
  topic: Topic
  index: number
  state: UserState
  update: (id: string, patch: Partial<UserState>) => void
  isSelf: boolean
  onDelete?: () => void
  onRead?: (topic: Topic) => void
}

export default function TopicItem({ topic, index, state, update, isSelf, onDelete, onRead }: Props) {
  const next = nextStatus(state.status)
  const read = () => {
    if (isSelf && onRead) onRead(topic)
    else void openLink(topic.url)
  }
  return (
    <article className="topic">
      <em>{String(index + 1).padStart(2, '0')}</em>
      <div>
        <h3>{topic.title} <span className={'st ' + state.status}>{labels[state.status]}</span></h3>
        <section>
          <button className="linklike" onClick={read}>{isSelf ? '读课文 ↗' : '阅读资料 ↗'}</button>
          <button onClick={() => update(topic.id, { status: next })}>{labels[next]}</button>
          <button onClick={() => update(topic.id, { verified: !state.verified })}>◉ {state.verified ? '已验证' : '面试验证'}</button>
          <button onClick={() => update(topic.id, { exposed: !state.exposed })}>⚑ {state.exposed ? '已暴露' : '标记暴露'}</button>
          {onDelete && <button className="del" onClick={onDelete}>✕ 删除</button>}
        </section>
      </div>
    </article>
  )
}
