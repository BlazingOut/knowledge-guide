# 星航日志（knowledge-guide）

配合自研课程仓库使用的本地学习记录应用。桌面端基于 Tauri 2，也可以直接以网页方式运行。数据保存在本地 localStorage，不依赖服务端。

## 功能

- **我的星图**：三级选课导航（领域 → 课程 → 章节目录），课程进度一目了然；全局搜索跨领域检索知识点。
- **自习舱**：应用内阅读课文（Markdown 渲染，含配图与配套代码下载），自动记录上次阅读位置，下次进入直接恢复；支持上一篇 / 下一篇按课程顺序连续学习。
- **知识星库**：按状态筛选、面试验证 / 暴露标记、添加与删除自定义知识点；自研课程在站内阅读，JavaGuide 条目跳转外部链接。
- **星航日志**：学习统计，含近 12 周热力图、点亮记录、领域跳转。
- **数据管理**：学习状态、点亮日志、自定义知识点、上次阅读位置全部持久化到 localStorage；支持 JSON 备份导出 / 导入与一键清空进度。
- **其他**：5 套主题（夜航 / 沙金 / 靛蓝 / 鼠尾草 / 暖阳）、打卡音效、移动端底部导航布局、桌面端自动更新。

## 数据来源

两个课程源：

1. **自研课程**：来自仓库 `ai_application_development_study`（AI 应用开发秋招课程）。通过同步脚本把课文、配图、配套代码拷贝到 `public/courses/`，并生成 `src/data/self-courses.json`；站内直接渲染课文。
2. **JavaGuide**：静态外链数据（`src/data/` 下三个 JSON），点击跳转 javaguide.cn 对应页面。

## 常用命令

```bash
npm install

npm run dev        # 网页方式开发（Vite）
npm run app:dev    # 桌面端开发（Tauri，需 Rust 环境）
npm run build      # 类型检查 + 生产构建
npm run app:build  # 打包桌面安装包
npm run preview    # 预览生产构建

npm run sync       # 从课程仓库同步内容（见下）
```

## 课程同步

```bash
npm run sync [课程仓库路径]   # 同步内容
npm run sync:init             # 把当前显示名批量写入命名映射
```

- 默认读取同级目录 `../ai_application_development_study`，路径不同时可传参覆盖。
- 脚本做的事：扫描课程仓库 `courses/` 与 `code/`，把课文、README、`assets/` 配图、配套代码拷贝到 `public/courses/`；生成 `src/data/self-courses.json` 驱动应用。
- **课文名 / 课程名统一在课程仓库根目录的 `courses-manifest.json` 维护**（`lessonTitles` / `courseTitles`，key 为 `课程目录/文件名.md`）；未映射的条目回退课文标题，同步时会警告列出。
- 课文与代码文件的对应关系通过 manifest 的 `lessonCodes` 配置。
- 机制细节与工作流速查见 `docs/课程同步规则.md`。
- 课程仓库内容变更后需要重新执行同步。

## 目录结构

```
src/
  pages/       页面组件（星图 / 自习舱 / 知识星库 / 星航日志）
  components/  通用组件（顶部导航条、打卡卡片、星球图标等）
  lib/         localStorage 存储、进度统计、备份、音效、代码下载
  styles/      样式模块：tokens.css 为主题变量，其余按页面 / 功能拆分
  data/        JavaGuide 静态数据 + 脚本生成的 self-courses.json
  types/       领域 / 课程 / 知识点 / 学习状态的数据结构
scripts/
  sync-courses.js   课程同步脚本
docs/          设计与方案文档（课程同步规则、界面交互重构方案；历史方案在 archive/，docs/ 整体不入库）
src-tauri/     Tauri 配置、更新器公钥与打包设置
```

## 数据存储

localStorage 键统一前缀 `knowledge-guide:`，包括：学习状态（user-state）、点亮日志（completion-log）、自定义知识点（custom-topics）、上次阅读位置（last-position）、主题与音效设置。备份文件包含前四项；「清空进度」会重置学习状态、点亮日志与上次位置，保留自定义知识点和设置。
