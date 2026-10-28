# 自研课程接入星航日志 · 进度清单

> 配套方案：`docs/自研课程接入星航日志方案.md`
> 创建日期：2026-10-28

## M1 同步脚本 ✅
- [x] 编写 `scripts/sync-courses.js`（扫描 / 标题提取 / 代码配对 / 拷贝）
- [x] 六大类 → 6 领域映射正确

## M2 数据生成与核对 ✅
- [x] 运行脚本生成 `src/data/self-courses.json`
- [x] 核对 JSON：6 领域 / 17 门课 / 139 篇课文
- [x] 核对 `public/courses/`：课文、README、assets 配图、code 代码齐全
- [x] 抽查代码配对（network L5 ↔ `network_lesson05.py`、database 05-JOIN ↔ 05 两个 sql 文件）

## M3 依赖与 App 改造 ✅
- [x] `npm install marked dompurify`
- [x] 组件拆分：types / lib（storage、progress、sound）/ pages / components，main.tsx 瘦身
- [x] 课程源切换（侧边栏「自研课程 / JavaGuide」，默认自研）
- [x] 课文阅读页 ReadPage（marked + DOMPurify + 图片路径重写）
- [x] 配套代码只读查看 + 运行提示
- [x] 卡片动作适配（读课文 / 看代码；JavaGuide 行为不变）
- [x] 移动端底部导航（修复手机上无法切页的缺陷）
- [x] 全局搜索（跨当前源全部知识点；自研进阅读页 / JavaGuide 定位到分类）
- [x] 连续学习流「下一篇」

## M4 样式 ✅
- [x] read 页排版（md 标题 / 表格 / 代码块）
- [x] 移动端导航样式
- [x] 全局搜索样式

## M5 验证与收尾
- [x] `npm run build`（tsc 通过；dist 内含 335 个课程文件）
- [ ] `npm run dev` 人工验证：读课文、看代码、打卡、切源、热力图、移动端导航（HTTP 冒烟已过，需浏览器人工过一遍）
- [ ] 桌面端（Tauri）验证（可选）
- [ ] 写仓库 README（启动方式、数据结构、同步脚本用法）

## 风险备忘
- [x] 课程文件改名 → 知识点 id 失联：重跑脚本前先导出备份
- [ ] 课文 H1 标题为「XX学习记录」的两篇（database-sqlite L1、fastapi L1）：不改脚本，由课程源文件自行决定是否改标题

## 用户反馈迭代
- [x] 2026-10-28 配套代码改为下载形式：阅读页只渲染完整 markdown；课文底部「下载本课代码」（桌面端保存对话框 / 网页端浏览器下载），移除内联代码展示
- [x] 2026-10-28 课程/课文命名映射：新增 `courses-manifest.json`（课程仓库根目录，增量覆盖），同步脚本读取并烧入 JSON；覆盖优先级：映射 > README/md 标题 > 目录名/文件名；17 门课程名 + 15 篇课文名已生效
- [x] 2026-10-28 标题规范：课程仓库新增《标题规范.md》（H1=第X课唯一、H2 起小节、README=课程名）；同步脚本对齐——H1 优先提取 + 自动去「第X课：」前缀（支持中文/阿拉伯数字），无课标题回退文件名；存量 12 篇不合规课文清单已列出，由用户自行统一
