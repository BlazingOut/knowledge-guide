// 顶部导航条：返回按钮 + 面包屑，固定渲染于内容区第一行（main 不滚动，天然常驻）。
// 由 main.tsx 按当前视图统一渲染：星图下钻 → 返回课程列表；课文阅读 → 返回来路页。
// 顶层视图（星图卡片 / 知识星库 / 星航日志）不渲染——一级导航无需返回。

type Props = {
  backLabel: string
  onBack: () => void
  crumbs: string[]
}

export default function NavBar({ backLabel, onBack, crumbs }: Props) {
  return (
    <div className="navbar">
      <button className="navbar-back" onClick={onBack}>←　{backLabel}</button>
      <span className="navbar-crumbs">{crumbs.join('　›　')}</span>
    </div>
  )
}
