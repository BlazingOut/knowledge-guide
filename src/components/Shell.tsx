// 应用外壳：侧边栏导航、课程源切换、主题/音效/数据设置；移动端使用底部导航栏

import { useState } from 'react'
import type { ReactNode } from 'react'
import type { Page, SourceId, Theme } from '../types/knowledge'
import { exportBackup, importBackup, clearProgress } from '../lib/storage'
import PlanetIcon from './PlanetIcon'

type Props = {
  page: Page
  setPage: (page: Page) => void
  theme: Theme
  setTheme: (theme: Theme) => void
  soundOn: boolean
  setSound: (on: boolean) => void
  sourceId: SourceId
  setSource: (id: SourceId) => void
  children: ReactNode
}

// 导航对齐 docs/界面交互重构方案.md v2；「今日航行」已删除，今日任务（M2）待重新设计后再加回
const NAV: { id: Page; label: string }[] = [
  { id: 'home', label: '我的星图' },
  { id: 'study', label: '自习舱' },
  { id: 'library', label: '知识星库' },
  { id: 'log', label: '星航日志' },
]

const THEMES: { id: Theme; label: string }[] = [
  { id: 'night', label: '☾ 夜航' },
  { id: 'sand', label: '✧ 沙金' },
  { id: 'indigo', label: '✦ 靛蓝' },
  { id: 'sage', label: '🌿 鼠尾草' },
  { id: 'warm', label: '☼ 暖阳' },
]

export default function Shell({ page, setPage, theme, setTheme, soundOn, setSound, sourceId, setSource, children }: Props) {
  const themeIcon: Record<Theme, string> = { night: '☾', sand: '✧', indigo: '✦', sage: '🌿', warm: '☼' }
  const cycleTheme = () => setTheme(THEMES[(THEMES.findIndex((t) => t.id === theme) + 1) % THEMES.length].id)
  const [confirmClear, setConfirmClear] = useState(false)

  return (
    <div className="shell" data-theme={theme}>
      <div className="starfield" aria-hidden="true">✦　·　✧　　　·　✦　　·　✧　　✦　·　　　✧　·　✦</div>
      <div className="sky-decoration" aria-hidden="true">
        <span className="moon"></span><span className="planet"><i></i></span>
        <span className="orbit orbit-one"></span><span className="orbit orbit-two"></span>
        <span className="constellation constellation-one"><i></i><i></i><i></i></span>
        <span className="constellation constellation-two"><i></i><i></i><i></i><i></i></span>
      </div>

      <aside className="side">
        <div className="brand"><PlanetIcon kind="network" size={30} /><span><strong>AI 应用开发</strong><small>秋招知识星图</small></span></div>

        <nav>
          {NAV.map((item) => (
            <button key={item.id} className={page === item.id ? 'on' : ''} onClick={() => setPage(item.id)}>{item.label}</button>
          ))}
        </nav>

        <div className="theme-switch">
          <small>课程源</small>
          <div>
            <button className={sourceId === 'self' ? 'selected' : ''} onClick={() => setSource('self')}>✧ 自研课程</button>
            <button className={sourceId === 'javaguide' ? 'selected' : ''} onClick={() => setSource('javaguide')}>外源 JavaGuide</button>
          </div>
        </div>

        <div className="theme-switch">
          <small>主题</small>
          <div className="theme-grid">
            {THEMES.map((item) => (
              <button key={item.id} className={theme === item.id ? 'selected' : ''} onClick={() => setTheme(item.id)}>{item.label}</button>
            ))}
          </div>
        </div>

        <div className="theme-switch">
          <small>音效</small>
          <div>
            <button className={soundOn ? 'selected' : ''} onClick={() => setSound(true)}>♪ 开</button>
            <button className={!soundOn ? 'selected' : ''} onClick={() => setSound(false)}>♪ 关</button>
          </div>
        </div>

        <div className="theme-switch backup-switch">
          <small>数据</small>
          <div>
            <button onClick={() => void exportBackup()} title="导出学习记录备份">↑ 导出</button>
            <label className="import-btn" title="从备份文件恢复">↓ 导入
              <input type="file" accept="application/json,.json" onChange={(event) => { const file = event.target.files?.[0]; if (file) void importBackup(file); event.target.value = '' }} />
            </label>
            <button className="danger-btn" title="清空全部学习进度（不可恢复）" onClick={() => setConfirmClear(true)}>✕ 清空进度</button>
          </div>
        </div>
      </aside>

      <div className="mobile-nav">
        {NAV.map((item) => (
          <button key={item.id} className={page === item.id ? 'on' : ''} onClick={() => setPage(item.id)}>{item.label}</button>
        ))}
        <button title="切换主题" onClick={cycleTheme}>{themeIcon[theme]}</button>
      </div>

      <main>{children}</main>

      {confirmClear && (
        <div className="modal-overlay" onClick={() => setConfirmClear(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <h3>清空全部学习进度？</h3>
            <small>所有知识点的学习状态与点亮日志将被重置，且不可恢复；自定义知识点与主题、音效设置会保留。建议先「↑ 导出」备份。</small>
            <div className="modal-actions">
              <button onClick={() => setConfirmClear(false)}>取消</button>
              <button className="danger" onClick={() => { setConfirmClear(false); clearProgress() }}>确认清空</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
