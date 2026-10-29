// 同步自研课程到星航日志
// 扫描课程仓库 courses/ 与 code/，生成 src/data/self-courses.json（统一 schema），
// 并拷贝课文 / README / 配图 / 配套代码到 public/courses/（静态资源打进应用）。
//
// 用法：node scripts/sync-courses.js [课程仓库路径]（默认 ../ai_application_development_study）

import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync, copyFileSync, cpSync, existsSync } from 'fs'
import { resolve, join, dirname, relative } from 'path'
import { fileURLToPath } from 'url'

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const coursesRepo = resolve(process.argv[2] || join(repoRoot, '..', 'ai_application_development_study'))
const outData = join(repoRoot, 'src', 'data', 'self-courses.json')
const outPublic = join(repoRoot, 'public', 'courses')

const giteeUrl = 'https://gitee.com/Mystery9527/ai_application_development_study'

// 六大类 → 领域
const DOMAIN_MAP = [
  { dir: 'engineering', id: 'self-engineering', title: '工程基础', description: 'Python、Git、Docker 与 Linux 等工程基本功。' },
  { dir: 'cs-basics', id: 'self-cs-basics', title: '计算机基础', description: '计算机网络与操作系统核心机制。' },
  { dir: 'backend', id: 'self-backend', title: '后端基础', description: 'MySQL/InnoDB、Redis、FastAPI 与分布式后端。' },
  { dir: 'ai-apps', id: 'self-ai-apps', title: 'AI 应用', description: 'AI Agent、LangGraph 与 RAG 应用开发。' },
  { dir: 'algorithms', id: 'self-algorithms', title: '算法', description: '刷题专题、机器学习与搜索推荐。' },
  { dir: 'capstone', id: 'self-capstone', title: '综合实战', description: '学习版外卖系统等端到端实战。' },
]

// 拷贝整个目录（保留相对结构），不存在则跳过
function copyDir(src, dest) {
  if (!existsSync(src)) return false
  mkdirSync(dest, { recursive: true })
  cpSync(src, dest, { recursive: true, force: true })
  return true
}

// 课文编号：lesson-05-* 或 05-* / 05_* 前缀
function topicNo(fileName) {
  const m = fileName.match(/^lesson-(\d+)/i) || fileName.match(/^(\d+)[-_]/)
  return m ? m[1] : null
}

// 辅助文件命名（非课程正文代码），自动配对时排除
const AUX_PATTERNS = [/^_verify/, /^test_/, /^_test/, /^homework_/, /^draft_/, /^_bak/, /\.bak$/, /\.tmp$/, /_old$/]

// 课文 ↔ 配套代码自动配对：只认「lessonNN」（后一位非数字）与「NN-」前缀，避免 lesson1 误配 lesson10~13
function matchCodeFiles(codeFiles, no) {
  const two = String(no).padStart(2, '0')
  const lessonRe = new RegExp(`(^|[_-])lesson${two}(?![0-9])`)
  return codeFiles.filter((f) => {
    if (AUX_PATTERNS.some((re) => re.test(f))) return false
    return lessonRe.test(f) || f.startsWith(`${two}-`)
  })
}

// 课文标题提取（《标题规范》：H1 优先；无 H1 回退「第X课」格式的 H2；其余返回 null 交给文件名）
// 「第X课」支持中文数字（第一课/第五课）与阿拉伯数字（第1课/第12课）
const LESSON_NO = '[0-9一二三四五六七八九十]+'
const LESSON_TITLE_RE = new RegExp(`第\\s*${LESSON_NO}\\s*课`)
const LESSON_PREFIX_RE = new RegExp(`^第\\s*${LESSON_NO}\\s*课[:：]?\\s*`)

function lessonHeading(md) {
  const h1 = md.match(/^#\s+(.+)$/m)
  if (h1) return h1[1].trim()
  const h2 = md.match(/^##\s+(.+)$/m)
  if (h2 && LESSON_TITLE_RE.test(h2[1])) return h2[1].trim()
  return null
}

// 去掉「第X课：」前缀：打卡卡片已显示序号，避免「05」+「第五课」重复
function stripLessonNo(title) {
  return title.replace(LESSON_PREFIX_RE, '')
}

// 首个 # 或 ## 标题；README 的标题作为课程名
function firstHeading(md) {
  const m = md.match(/^#{1,2}\s+(.+)$/m)
  return m ? m[1].trim() : null
}

function main() {
  if (!existsSync(join(coursesRepo, 'courses'))) {
    console.error(`找不到课程仓库（缺少 courses/）：${coursesRepo}`)
    console.error('用法：node scripts/sync-courses.js [课程仓库路径]')
    process.exit(1)
  }

  // 课程 ↔ 中文名映射（课程仓库内维护，增量覆盖默认取名规则）
  const manifestPath = existsSync(join(coursesRepo, 'courses-manifest.json'))
    ? join(coursesRepo, 'courses-manifest.json')
    : join(coursesRepo, 'courses', 'courses-manifest.json')
  let manifest = { courseTitles: {}, lessonTitles: {}, lessonCodes: {} }
  if (existsSync(manifestPath)) {
    try {
      manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
      console.log(`📋 读取课程映射：${relative(coursesRepo, manifestPath)}`)
    } catch {
      console.warn(`⚠️  课程映射文件解析失败，忽略：${manifestPath}`)
    }
  }
  const titleOf = (courseId, fileName) => manifest.lessonTitles?.[`${courseId}/${fileName}`]
  const codeOf = (courseId, fileName) => manifest.lessonCodes?.[`${courseId}/${fileName}`]
  let manifestCourseHits = 0
  let manifestLessonHits = 0
  let manifestCodeHits = 0

  const domains = []
  const missingHeading = []
  let topicCount = 0

  for (const domainCfg of DOMAIN_MAP) {
    const classDir = join(coursesRepo, 'courses', domainCfg.dir)
    if (!existsSync(classDir)) {
      console.warn(`跳过不存在的领域目录：${domainCfg.dir}`)
      continue
    }
    const categories = []
    for (const entry of readdirSync(classDir, { withFileTypes: true })) {
      if (!entry.isDirectory() || entry.name === 'assets') continue
      const courseId = entry.name
      const coursePath = join(classDir, courseId)
      // 课文 = 课程目录顶层 *.md（README 单独作为大纲入口）
      const lessonFiles = readdirSync(coursePath)
        .filter((f) => f.endsWith('.md') && f.toLowerCase() !== 'readme.md')
        .sort()
      if (!lessonFiles.length) continue

      // 配套代码（code/<课程>/ 下的文件）
      const codeDir = join(coursesRepo, 'code', courseId)
      const codeFiles = existsSync(codeDir)
        ? readdirSync(codeDir).filter((f) => statSync(join(codeDir, f)).isFile())
        : []

      const topics = lessonFiles.map((f, i) => {
        const md = readFileSync(join(coursePath, f), 'utf8')
        const heading = lessonHeading(md)
        if (!heading) missingHeading.push(relative(coursesRepo, join(coursePath, f)))
        const mapped = titleOf(courseId, f)
        if (mapped) manifestLessonHits++
        const no = topicNo(f)
        const mappedCodes = codeOf(courseId, f)
        if (mappedCodes !== undefined) manifestCodeHits++
        const matched = mappedCodes !== undefined ? mappedCodes : (no ? matchCodeFiles(codeFiles, no) : [])
        return {
          id: `course-${courseId}-${i + 1}`,
          title: mapped || (heading ? stripLessonNo(heading) : f.replace(/\.md$/, '')),
          url: `courses/${courseId}/${f}`,
          ...(matched.length ? { codeFiles: matched.map((cf) => `courses/code/${courseId}/${cf}`) } : {}),
        }
      })
      topicCount += topics.length

      // 拷贝课文 / README / 配图 / 代码
      const outCourse = join(outPublic, courseId)
      mkdirSync(outCourse, { recursive: true })
      for (const f of lessonFiles) copyFileSync(join(coursePath, f), join(outCourse, f))
      const readmePath = join(coursePath, 'README.md')
      if (existsSync(readmePath)) copyFileSync(readmePath, join(outCourse, 'README.md'))
      copyDir(join(coursePath, 'assets'), join(outCourse, 'assets'))
      if (codeFiles.length) copyDir(codeDir, join(outPublic, 'code', courseId))

      // 课程名：映射优先，其次 README 标题（去掉「课程大纲」「课程」后缀），最后目录名
      const readmeText = existsSync(readmePath) ? readFileSync(readmePath, 'utf8') : ''
      const mappedTitle = manifest.courseTitles?.[courseId]
      if (mappedTitle) manifestCourseHits++
      const courseTitle = mappedTitle || (firstHeading(readmeText) || courseId).replace(/课程大纲$/, '').replace(/课程$/, '').trim()
      categories.push({
        id: `course-${courseId}`,
        title: courseTitle,
        url: `courses/${courseId}/README.md`,
        readme: `courses/${courseId}/README.md`,
        topics,
      })
    }
    if (categories.length) {
      domains.push({
        id: domainCfg.id,
        title: domainCfg.title,
        description: domainCfg.description,
        source: { type: 'self', name: '自研课程', url: giteeUrl },
        children: categories,
      })
    }
  }

  mkdirSync(dirname(outData), { recursive: true })
  writeFileSync(outData, JSON.stringify(domains, null, 2), 'utf8')

  const catCount = domains.reduce((s, d) => s + d.children.length, 0)
  const codeCount = existsSync(join(outPublic, 'code'))
    ? readdirSync(join(outPublic, 'code'), { withFileTypes: true }).filter((e) => e.isDirectory()).length
    : 0
  console.log(`✅ 完成：${domains.length} 个领域 / ${catCount} 门课程 / ${topicCount} 篇课文 / ${codeCount} 个代码目录`)
  console.log(`   映射生效：${manifestCourseHits} 门课程名 / ${manifestLessonHits} 篇课文名 / ${manifestCodeHits} 篇代码配对`)
  console.log(`   数据 → ${relative(repoRoot, outData)}`)
  console.log(`   资源 → ${relative(repoRoot, outPublic)}/`)

  // 重复挂载诊断：同一代码文件被多篇课文引用，通常是自动配对误配
  const fileOwners = {}
  for (const d of domains) for (const c of d.children) for (const t of c.topics) for (const cf of t.codeFiles || []) (fileOwners[cf] ||= []).push(t.title)
  const dup = Object.entries(fileOwners).filter(([, owners]) => owners.length > 1)
  if (dup.length) {
    console.warn(`⚠️  同一代码文件被多篇课文引用（${dup.length} 处，建议用 lessonCodes 精确指定）：`)
    for (const [cf, owners] of dup) console.warn(`   ${cf}\n      ${owners.join('\n      ')}`)
  }
  if (missingHeading.length) {
    console.warn(`⚠️  ${missingHeading.length} 篇课文无课标题（H1/「第X课」H2），已回退为文件名——建议按《标题规范》补齐：`)
    missingHeading.forEach((f) => console.warn('   ' + f))
  }
}

main()
