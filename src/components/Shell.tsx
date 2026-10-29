// 应用外壳：侧边栏导航、课程源切换、主题/音效/数据设置；移动端使用底部导航栏

import type { ReactNode } from 'react'
import type { Page, SourceId, Theme } from '../types/knowledge'
import { exportBackup, importBackup } from '../lib/storage'
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

const NAV: { id: Page; label: string }[] = [
  { id: 'log', label: '星航日志' },
  { id: 'home', label: '我的星图' },
  { id: 'checkin', label: '今日航行' },
  { id: 'library', label: '知识星库' },
]

const THEMES: { id: Theme; label: string }[] = [
  { id: 'night', label: '☾ 夜航' },
  { id: 'sand', label: '✧ 沙金' },
  { id: 'indigo', label: '✦ 靛蓝' },
  { id: 'warm', label: '☼ 暖阳' },
]

export default function Shell({ page, setPage, theme, setTheme, soundOn, setSound, sourceId, setSource, children }: Props) {
  const themeIcon: Record<Theme, string> = { night: '☾', sand: '✧', indigo: '✦', warm: '☼' }
  const cycleTheme = () => setTheme(THEMES[(THEMES.findIndex((t) => t.id === theme) + 1) % THEMES.length].id)

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
    </div>
  )
}
