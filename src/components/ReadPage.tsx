// 课文阅读页：应用内完整渲染自研课程 markdown 课文，底部提供配套代码下载与快捷打卡、「下一篇」

import { useEffect, useMemo, useState } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ReadingTarget, UserState } from '../types/knowledge'
import { labels } from '../types/knowledge'
import { nextStatus } from '../lib/storage'
import { downloadCourseCode } from '../lib/download'

type Props = {
  reading: ReadingTarget
  get: (id: string) => UserState
  update: (id: string, patch: Partial<UserState>) => void
  hasNext: boolean
  onNext: () => void
  onBack: () => void
}

// 课文相对路径 courses/<课程>/xxx.md → 课程目录名（用于重写配图路径）
function courseDirOf(url: string) {
  const parts = url.split('/')
  return parts.length >= 2 ? parts[1] : ''
}

export default function ReadPage({ reading, get, update, hasNext, onNext, onBack }: Props) {
  const { topic, category, domain } = reading
  const [md, setMd] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setMd('')
    setError('')
    fetch(topic.url)
      .then((res) => {
        if (!res.ok) throw new Error(`加载失败：${res.status}`)
        return res.text()
      })
      .then((text) => { if (!cancelled) setMd(text) })
      .catch((err: Error) => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [topic])

  // 配图相对路径重写：md 内 (assets/x.svg → (courses/<课程>/assets/x.svg
  const html = useMemo(() => {
    if (!md) return ''
    const dir = courseDirOf(topic.url)
    const rewritten = dir ? md.replace(/\(\.?\/?assets\//g, `(courses/${dir}/assets/`) : md
    return DOMPurify.sanitize(marked.parse(rewritten) as string)
  }, [md, topic.url])

  const state = get(topic.id)
  const isDone = state.status === 'completed'

  return (
    <div className="read">
      <div className="read-head">
        <div className="read-meta">
          <small>{domain.title} · {category.title}</small>
          <h1>{topic.title}</h1>
          <div className="read-actions">
            <button className={isDone ? 'done-button' : ''} onClick={() => update(topic.id, { status: nextStatus(state.status) })}>
              {isDone ? '重新学习 ✓' : state.status === 'learning' ? '已完成 →' : '开始学习 →'}
            </button>
            {hasNext && <button className="read-next" onClick={onNext}>下一篇 →</button>}
          </div>
        </div>
      </div>

      {error && <p className="read-error">⚠ {error}</p>}

      {md && (
        <article className="read-body" dangerouslySetInnerHTML={{ __html: html }} />
      )}

      {topic.codeFiles && topic.codeFiles.length > 0 && (
        <section className="read-download">
          <div className="read-download-head">
            <small>配套代码 · 本课</small>
            <h2>下载本课代码</h2>
          </div>
          <div className="read-download-list">
            {topic.codeFiles.map((path) => (
              <button key={path} className="read-download-btn" title="保存到本地"
                onClick={() => void downloadCourseCode(path, path.split('/').pop() || 'code.txt')}>
                ↓ {path.split('/').pop()}
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="read-foot">
        <div className="read-actions">
          <span className="read-status">{labels[state.status]}</span>
          <button className={isDone ? 'done-button' : ''} onClick={() => update(topic.id, { status: nextStatus(state.status) })}>
            {isDone ? '重新学习 ✓' : state.status === 'learning' ? '已完成 →' : '开始学习 →'}
          </button>
        </div>
        {hasNext
          ? <button className="read-next" onClick={onNext}>下一篇：{reading.category.topics[reading.category.topics.findIndex((t) => t.id === topic.id) + 1]?.title} →</button>
          : <button className="read-next" onClick={onBack}>已完成本章 · 返回课程目录 →</button>}
      </div>
    </div>
  )
}
