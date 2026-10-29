# 暖阳主题 UI 优化 · 进度清单

> 配套方案：`docs/暖阳主题UI优化方案.md`
> 创建日期：2026-10-28

## Phase 0 · CSS 还债（承诺零视觉变化）✅
- [x] 编写级联解析/对比工具 `scripts/css-resolve.mjs`（解析 @import、同选择器合并、元素签名 × 两主题 × 两视口的声明级 diff、var 拼接 LINT）
- [x] 按原始规则顺序拆分为 14 个模块（tokens / base / shell / components / cards-layers / planets / viewport-fixes / pages-log / modals / animations / backup / search / pages-read / mobile），`styles.css` 仅作 @import 入口
- [x] 段内合并重复选择器（保留胜者原位置，级联等价）
- [x] 96 处硬编码色值收编为 token：13 个共享装饰 token（两主题同值：`--planet-*` / `--veil-*` / `--heat-*` / `--track` / `--shadow-ambient` / `--on-green`）+ warm 作用域内 `--yellow` 等值替换
- [x] 星球图标 5 层补丁（原 94 条规则）收敛为 10 条，按最终计算值重写为 `styles/planets.css`
- [x] 等价性验证：元素签名 diff 仅剩隐藏装饰件的死属性丢弃（渲染零影响）；选择器级 diff 全部为已核对 token 替换；LINT 0
- [x] `npm run build` 通过（tsc + vite；CSS 产物 41.7 KB）

### Phase 0 完成后的度量
| 指标 | 还债前 | 还债后 |
| --- | --- | --- |
| 样式文件 | 1 个 60KB 单文件 | 14 模块共 47KB + 入口 |
| `!important` | 396 | 152（余下在存量覆盖层，Phase 3/4 消化） |
| 硬编码 hex | 148 处 | 82 处（含 tokens.css 定义本身；散落值多为单次使用/上下文敏感，Phase 1 处理） |
| `.cards` 规则定义 | 26 次 | 跨 3 个文件分层（组件基线 / cards-layers / viewport-fixes，存量层已注释标记） |

### Phase 0 过程中发现并记录的问题（未修改，留待后续阶段）
- [ ] **星球装饰全部不可见（真实 bug）**：第一层补丁「图标最终隔离」给卡片星球与品牌星球的伪元素/`<i>` 加了 `display:none!important`，后续 5 层补丁从未恢复——环/轨道/卫星/彗尾当前全部不渲染，四类星球看起来一样。Phase 2 改 SVG 星球组件时自然解决
- [ ] `.shell .cards{overflow:visible!important}`（高特异性）压过 `.cards{overflow-y:auto!important;max-height:380px!important}`——首页卡片无内部滚动，`.shell .cards` 与 `.cards` 的特异性互搏待 Phase 3 布局重构时消除
- [ ] 暖阳 nav 星标 text-shadow 的历史字面量 `#e2ae4366`（夜航黄 40%，疑似历史笔误）保留在 `styles/planets.css`，Phase 1 收编为正式 token

## Phase 1 · 暖阳色板切换 ✅（2026-10-28）
- [x] 按 4.1 表更新 `[data-theme=warm]` token：纸张白 `#FAF8F1` 打底 / 深墨 `#293B3A` / 星球绿 `#78966B` / 星光金 `#E9B95F` / 柔雾灰 `#DCDDD2`；夜航块仅补 token 定义、渲染值不变
- [x] 新增语义 token（两主题）：`--green-bg`(选中底) / `--hover-ring`(悬停圈) / `--shadow-hover` / `--focus-ring` / `--badge-bg|border|text`(徽章) / `--brand-halo`(品牌光晕)
- [x] 金色黑名单清理：focus outline、卡片/搜索/下载 hover 金圈、三处金徽章（学习进度/今日任务/热力图头部/必背标签）、品牌星球金晕 → 暖阳全部转绿系；夜航经 diff 工具逐值验证不变
- [x] 装饰 token 化：moon/orbit/constellation/planet 辉光、暖阳背景渐变端点、glow-breath/heat.level-4 → `color-mix(var(--yellow/--green))`（夜航按 8-bit 精确百分比换算，逐像素相等）
- [x] 暖阳 nav 星标历史字面量 `#e2ae4366` → `color-mix(var(--yellow-deep) 40%)`
- [x] 验证：night 签名 diff = 9（全部为 Phase 0 已记录的隐藏装饰死属性丢弃）；warm 签名 diff = 92（预期色板变化）；LINT 0；`npm run build` 通过
- [x] 对比度抽查结论：Primary 按钮**保留深墨字**（`--on-green` #102018 on #78966B ≈ 5.1:1 ✓ AA）；外部方案建议的白字仅 3.3:1（10–14px 按钮字号不达标），作为对方案的偏离记录

### Phase 1 遗留（转 Phase 2）
- [ ] `.filters button.sel` 的 `#82b8792e`、`.theme-switch button.selected` 金描边、`.domain-tabs` 金星标前缀、`.mobile-nav .sel` —— 属选中态语言统一（Phase 2）
- [ ] `.modal-actions button.primary` 的 `#0b2420` 与 `--on-green`(#102018) 并存 —— 按钮规范统一时合并（Phase 2）
- [ ] `shell.css` 夜航背景渐变三字面量（`#071316/#0b2420/#061014`，仅夜航生效）与通用黑阴影（`#0002/#0003`）—— 低优先级，Phase 4 一并清理

## Phase 2 · 状态规范 + 星球图标 ✅（2026-10-28）

### 星球图标 ✅
- [x] `PlanetIcon` 组件落地（`src/components/PlanetIcon.tsx`，移植 `docs/ref-design/星球SVG预览-gpt.html`）：结构统一（轨道后段 + 球体 + 前段弧穿球 + 双星光），四类差异 = 色相（network 绿 / ringed 蓝 / node 金 / comet 玫瑰）
- [x] 替换 `HomePage` 卡片星球与 `Shell` 品牌星球引用；类名 `planet-icon-*` 前缀（避开 shell 背景装饰 `.planet/.star` 的类名冲突）
- [x] 删除 `styles/planets.css` 旧纯色球规则与三处 `.cards .ico` 死规则（components/cards-layers/viewport-fixes）；移除 `--brand-halo` token
- [x] 组件尺寸用内联 `--planet-size` + em 缩放，卡片 44px / 品牌 30px，比例恒定
- [x] 卡片 hover 星球轻微旋转放大（`rotate(-5deg) scale(1.05)` + transition，prefers-reduced-motion 由全局规则兜底）
- [x] 删除旧预览文件 `星球SVG预览.html`（被 GPT 版取代，已授权删除）

### 状态语言统一 ✅
- [x] 三种选中态收敛为「浅绿底 `--green-bg` + 细绿边 `--green`」：导航 `button.on`（去掉内嵌条与金色星标前缀）、领域 tab `.active`（拆出 hover 用 `--veil-green`，去掉金标与光晕）、主题/音效开关 `.selected`（去掉金深描边）
- [x] `.filters button.sel`、移动端 `mobile-nav button.on/.sel`、`mobile-theme-switch selected` 同步收敛；`.modal-actions button.primary` 的 `#0b2420` 并入 `--on-green`
- [x] 删除 nav/domain-tabs 的金色 `:before` 星标规则（planets.css + components.css + shell.css）
- [x] 验收：任意一页"选中"语言唯一；`--yellow-deep` 当前无引用（保留为语义色板，Phase 3 金色引言可能用）

### 侧边栏设置区收纳 ✅
- [x] 四组设置（课程源/主题/音效/数据）紧凑化：`.side` padding 30/17→24/16、brand 底部留白 48→40、theme-switch 组 padding 18→12、标题间距 9→6、按钮 7px→6px、字号 10→9

### 参考
- `docs/ref-design/` 新增交接文档（`AIA7E69B9FE88698E5BE_A1E7AEBAE6A596E6A3.txt`）：设计方向与本方案一致，无新要求；其星球方案（.planet/.planet-sphere/.planet-ring/.star 结构）即本次移植源

## Phase 3 · 首页重构
- [ ] Hero 区：标题 + 一句话 + 当前源整体进度；`voyage-badge` 降级为 meta 文本
- [ ] 卡片 `height:180px!important` → `min-height` 内容自适应；`StudyCard.card-foot` 改流式布局
- [ ] 底部 tip → 「下一站」真实 CTA（定位当前领域首个未完成知识点）
- [ ] 合并 `cards-layers.css` 存量覆盖层
- [ ] 验收：首屏一眼可读"我在哪/学多少/下一步做什么"；短视口无内容被裁切

## Phase 4 · 字号刻度 + 布局机制治理
- [ ] 按 4.4/4.5 应用字号与间距刻度
- [ ] 列表高度 `calc(100vh - N)` 魔法数字 → flex `min-height:0` 自适应；断点收敛为 1150/820/620
- [ ] 合并 `viewport-fixes.css`；移动端全页面回归
- [ ] 验收：`!important` 降到两位数以内；四页内滚行为与改前一致

## Phase 3 · 首页重构 ✅（2026-10-28）
- [x] Hero 区：标题 + 一句话 + **真实整体进度**（当前源全部知识点 完成/总数 + 进度条 + 已点亮星星数，数据来自 `domains`+`get`）；静态 `voyage-badge` 移除
- [x] 卡片 `height:180px!important` 系列 → `min-height:180px` 内容自适应（padding 16 / 圆角 16 / 标题 15px 单一规则）
- [x] `StudyCard.card-foot` 绝对定位 → 流式 `margin-top:auto`（study-card 改 flex column，内容增高不再与底部按钮重叠）
- [x] 底部提示条 → 「下一站：分类 · 知识点」真实 CTA：定位当前领域首个未完成知识点，点击走 `onOpenTopic` 直达阅读页；全部完成显示「今日航行已完成」庆祝文案
- [x] 首页外壳 `.home`（flex column）+ `.home-body`（flex:1 min-height:0 滚动）——短视口内容不再被裁切，替代 calc 魔法数字（Phase 4 的 flex 模式先行落地首页）
- [x] 合并存量覆盖层：`cards-layers.css` 删除全部 .cards/.card/.tip 首页层（284→约 100 行），`viewport-fixes.css` 删除 .shell .cards 系列（129→14 行）；收敛为 components.css 单一规则
- [x] 断点收敛 1150/820/620（首页卡片 4/3/2/1 列）
- [x] 误伤修复：`.checkin-list .study-card .priority/.question` 高特异性覆盖、`.cards .library-entry` 紧凑版均已按原值恢复
- [x] 验证：元素 diff 全部属于预期类别（状态/星球/首页结构/card-foot）；LINT 0；`npm run build` 通过

## Phase 4 · 字号刻度 + 布局机制治理 ✅（2026-10-28）
- [x] **calc(100vh - N) 魔法数字 18 处 → 0**：main 改 flex column，各页根/滚动元素统一 `flex:1;min-height:0`（.log / .home-body / .checkin-list / .list / .read / .search-results）；知识星库 570px 高度栈（viewport-fixes）整体删除；搜索列表改由 home-body 内 flex 滚动
- [x] **断点收敛 1150/820/620**：media900 块删除，`.side{width:190px}` + checkin-head 单列搬入 media820
- [x] **存量覆盖层全部收尾**：`viewport-fixes.css` 删除（129→0 行），`cards-layers.css` 仅剩今日航行网格（284→约 60 行）；styles 文件 15→13
- [x] **字号间距刻度（4.4/4.5）**：正文 13→14、辅助 small 10→11、页面标题 38→34、卡片标题 15→16、列表/打卡/阅读各 9-10px 档位上移一档；main `padding:40px 48px + max-width:1240px`
- [x] **!important 396 → 2**（仅剩 reduced-motion 无障碍规则，属故意保留）；去 !important 经元素签名 diff 验证零渲染变化
- [x] 验证：元素签名 diff 0、LINT 0、`npm run build` 通过
- [ ] 人工回归：`npm run dev` 五页 × 两主题 × 三视口（1600×900 / 1280×800 / 390×844）比对内滚行为与排布

## 全案指标（Phase 0 → Phase 4）
| 指标 | 改造前 | 改造后 |
| --- | --- | --- |
| 样式文件 | 1 个 60KB 单文件 | 13 模块共约 46KB + 入口 |
| `!important` | 396 | **2**（仅无障碍规则） |
| `calc(100vh - N)` 魔法数字 | 18 处 | **0** |
| 硬编码 hex | 148 处 | 88（含 token 定义 ~60 + GPT 星球四色相设计值 16 + 少量单次字面量） |
| 断点 | 1150/900/820/620 四套 | **1150/820/620** |
| 星球图标 | 纯色球（装饰被历史补丁隐藏） | 四色相 GPT 方案组件 |
| 选中态语言 | 三套并存 | 一套（浅绿底 + 细绿边） |

## 验证方式备忘
- 等价性：`node scripts/css-resolve.mjs diff <参照css> src/styles.css`（元素签名 × 两主题 × 两视口 + 选择器级 + LINT）
- 构建：`npm run build`（tsc -b && vite build）
- 视觉：`npm run dev` 后三视口（1600×900 / 1280×800 / 390×844）× 两主题人工比对，重点页：星航日志 / 我的星图 / 今日航行 / 知识星库 / 阅读页 / 添加知识点弹窗
