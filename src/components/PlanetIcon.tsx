// 星球图标：GPT 方案移植（docs/ref-design/星球SVG预览-gpt.html）
// 结构统一（轨道后段 → 球体 → 轨道前段弧 → 双星光），四类差异 = 色相：
// network 绿 / ringed 蓝 / node 金 / comet 玫瑰。颜色走组件级 CSS 变量，两主题通用。
// 类名统一 planet-icon-* 前缀，避免与 shell 背景装饰 .planet/.star 冲突。

import type { CSSProperties } from 'react'

const HUES: Record<string, number> = { network: 0, ringed: 1, node: 2, comet: 3 }

type Props = {
  kind: 'network' | 'ringed' | 'node' | 'comet'
  /** 容器直径（px），内部比例按 em 缩放保持不变 */
  size?: number
  /** 星光三态：idle 未学（暗淡）/ learning 学习中（亮金）/ done 已完成（暖光+绿晕）；不传保持现状 */
  glow?: 'idle' | 'learning' | 'done'
}

export default function PlanetIcon({ kind, size = 44, glow }: Props) {
  const hue = HUES[kind] ?? 0
  return (
    <span
      className={`planet-icon planet-icon-hue-${hue}`}
      style={{ '--planet-size': size + 'px' } as CSSProperties}
      data-glow={glow}
      aria-hidden="true"
    >
      <span className="planet-icon-ring planet-icon-ring-back" />
      <span className="planet-icon-sphere" />
      <span className="planet-icon-ring planet-icon-ring-front" />
      <span className="planet-icon-star planet-icon-star-one" />
      <span className="planet-icon-star planet-icon-star-two" />
    </span>
  )
}
