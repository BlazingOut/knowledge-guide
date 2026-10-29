// CSS 级联解析与等价性对比工具（Phase 0 还债用）
// 用法：
//   node scripts/css-resolve.mjs blocks  <file>                      列出顶层块及行号
//   node scripts/css-resolve.mjs cut    <file> <plan.json> <outdir>  按行号区间切段生成模块文件（段内合并重复选择器；plan 项可带 extractTokens）
//   node scripts/css-resolve.mjs diff   <old.css> <new-entry.css>    元素签名 × 两主题 × 两视口 的声明级 diff + 选择器级 diff
//   node scripts/css-resolve.mjs inspect <file.css> <选择器子串>      查看某选择器跨文件合并后的最终声明
//   node scripts/css-resolve.mjs stats  <file>                       统计 !important / 硬编码色值 / 重复选择器
//
// 原理：
// - 同选择器字符串的重复规则按「!important 优先、后者胜出」合并；被压掉的必败声明可以安全删除，
//   保留胜者在其原有位置（顺序不变），因此简写/长写互不干扰。
// - 跨选择器的级联关系用元素签名（模拟组件真实 DOM 路径 + 状态/伪元素）解析后逐属性 diff，
//   var() 按当前主题的 token 值解析后再比较。

import fs from 'node:fs'
import path from 'node:path'
import postcss from 'postcss'

// ---------- 解析 ----------

function inlineImports(file, seen = new Set()) {
  const abs = path.resolve(file)
  if (seen.has(abs)) return postcss.root()
  seen.add(abs)
  const css = fs.readFileSync(abs, 'utf8')
  const ast = postcss.parse(css, { from: abs })
  const out = postcss.root()
  for (const node of ast.nodes) {
    if (node.type === 'atrule' && node.name === 'import') {
      const m = /url\(\s*['"]?([^'")]+)['"]?\s*\)|['"]([^'"]+)['"]/.exec(node.params)
      const target = m && (m[1] || m[2])
      if (!target || /^(https?:|data:)/.test(target)) continue
      const sub = inlineImports(path.resolve(path.dirname(abs), target), seen)
      while (sub.nodes.length) out.append(sub.nodes[0]) // append 会把节点从 sub 摘出，逐个取首节点避免遍历中数组变动
      continue
    }
    out.append(node.clone())
  }
  return out
}

function collectRules(root, out = [], media = '') {
  let n = 0
  const walk = (container, curMedia) => {
    for (const node of container.nodes) {
      if (node.type === 'rule') {
        out.push({ kind: 'rule', media: curMedia, selector: node.selector.replace(/\s+/g, ' ').trim(), decls: node.nodes.filter((d) => d.type === 'decl'), order: n++ })
      } else if (node.type === 'atrule' && node.name === 'media') {
        walk(node, node.params.replace(/\s+/g, ' ').trim())
      }
      // @keyframes / @font-face 等不参与级联，diff 时跳过
    }
  }
  walk(root, media)
  return out
}

// ---------- 同选择器合并 ----------

function mergeWinners(rules) {
  // 返回 [{prop, value, important, order}]，每属性仅保留最终胜者，按原 order 排序
  const decls = []
  rules.forEach((r, ri) => {
    for (const d of r.decls) {
      decls.push({ prop: d.prop.trim(), value: d.value.replace(/\s+/g, ' ').trim(), important: !!d.important, order: r.order, ri })
    }
  })
  const byProp = new Map()
  for (const e of decls) {
    const cur = byProp.get(e.prop)
    const better = !cur || (e.important !== cur.important ? e.important : e.order >= cur.order)
    if (better) byProp.set(e.prop, e)
  }
  return [...byProp.values()].sort((a, b) => a.order - b.order)
}

// ---------- 选择器匹配 ----------

function specificity(sel) {
  let a = 0, b = 0, c = 0
  let s = sel
  // 旧式单冒号伪元素（:before/:after 等）按伪元素计
  s = s.replace(/:{1,2}(before|after|first-line|first-letter)\b/g, () => { c++; return '' })
  s = s.replace(/::[a-z-]+/g, () => { c++; return '' })
  const tokens = s.match(/::?[a-z-]+(?:\([^()]*\))?|\[[^\]]*\]|[#.][\w-]+|[a-zA-Z]+|\*/g) || []
  for (const t of tokens) {
    if (t.startsWith('#')) a++
    else if (t.startsWith('.') || t.startsWith('[')) b++
    else if (t.startsWith('::')) c++
    else if (t.startsWith(':')) {
      const inner = /\(([^()]*)\)/.exec(t)
      if (/^:not\b/i.test(t)) {
        const [na, nb, nc] = specificity(inner ? inner[1] : '')
        a += na; b += nb; c += nc
      } else b++
    } else if (t === '*') continue
    else c++
  }
  return [a, b, c]
}
const cmpSpec = (x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2]

function parseSelector(sel) {
  const parts = []
  let buf = ''
  let pendingComb = ' '
  for (let i = 0; i < sel.length; i++) {
    const ch = sel[i]
    if (ch === '>' || ch === '+') { if (buf.trim()) { parts.push({ compound: buf.trim(), comb: pendingComb }); buf = '' } pendingComb = ch; while (sel[i + 1] === ' ') i++ }
    else if (ch === ' ') {
      if (buf.trim()) { parts.push({ compound: buf.trim(), comb: pendingComb }); buf = ''; pendingComb = ' ' }
      // 若下一个非空字符是 > 或 +，留给下一轮处理
      let j = i + 1
      while (sel[j] === ' ') j++
      if (sel[j] === '>' || sel[j] === '+') { pendingComb = pendingComb === ' ' ? ' ' : pendingComb; i = j - 1 }
    } else buf += ch
  }
  if (buf.trim()) parts.push({ compound: buf.trim(), comb: pendingComb })
  // 修正：pendingComb 应归属“下一个”复合选择器
  for (let i = 1; i < parts.length; i++) { /* comb 已随前一块记录，占位 */ }
  return parts
}

const PSEUDO_ELEMENTS = /^(before|after|first-line|first-letter|placeholder|selection)$/

function matchCompound(compound, node) {
  let m = compound
  const pseudoEl = /:{1,2}([a-z-]+)/.exec(m.replace(/[.\[][^ :]*(?= |$)/g, ''))
  if (pseudoEl && PSEUDO_ELEMENTS.test(pseudoEl[1])) {
    if ((node.pseudo || '') !== pseudoEl[1]) return false
    m = m.replace(new RegExp(`::?${pseudoEl[1]}\\b`), '')
  } else if (node.pseudo) {
    return false // 元素规则不作用于其伪元素
  }
  const nots = []
  m = m.replace(/:not\(([^()]*)\)/g, (_, inner) => { nots.push(inner); return '' })
  const pieces = m.match(/\[[^\]]*\]|[#.][\w-]+|:[a-z-]+|[a-zA-Z]+/g) || []
  for (const p of pieces) {
    if (p.startsWith('.')) { if (!node.classes.has(p.slice(1))) return false }
    else if (p.startsWith('[')) {
      const am = /^\[\s*([\w-]+)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+))\s*)?\]$/.exec(p)
      if (!am) return false
      const name = am[1], val = am[2] ?? am[3] ?? am[4]
      if (!(name in node.attrs)) return false
      if (val !== undefined && String(node.attrs[name]) !== val) return false
    } else if (p.startsWith(':')) {
      if (p === ':root') { if (!node.isRoot) return false }
      else if (!node.states.has(p.slice(1))) return false
    } else if (p !== '*') { if (node.tag !== p.toLowerCase()) return false }
  }
  for (const inner of nots) if (matchCompound(inner.trim(), node)) return false
  return true
}

function matchChain(parts, from, node) {
  // 匹配 parts[from] 及其更早部分到 node 及其祖先
  let cur = node
  for (let i = from; i >= 0; i--) {
    const { compound, comb } = parts[i]
    if (!matchCompound(compound, cur)) return false
    if (i === 0) return true
    // comb 描述 parts[i-1] 与 parts[i] 的关系
    if (comb === ' ') {
      let anc = cur.parent, ok = false
      while (anc) { if (matchChain(parts, i - 1, anc)) { ok = true; break } anc = anc.parent }
      return ok
    }
    if (comb === '>') { cur = cur.parent; if (!cur) return false; continue }
    if (comb === '+') { cur = cur.prev; if (!cur) return false; continue }
  }
  return false
}
const matchSelector = (sel, node) => matchChain(parseSelector(sel), parseSelector(sel).length - 1, node)

// ---------- var() 解析 ----------

function resolveVars(value, vars, depth = 0) {
  if (depth > 12 || !value.includes('var(')) return value
  let out = value, prev = null
  const re = /var\(\s*(--[\w-]+)\s*(?:,((?:[^()]|\([^()]*\))*))?\)/
  let guard = 0
  while (out !== prev && guard++ < 20) {
    prev = out
    out = out.replace(re, (all, name, fallback) => {
      const v = vars[name] !== undefined ? vars[name] : (fallback || '').trim()
      return v === '' ? all : v
    })
  }
  return out
}

// ---------- 颜色归一化（diff 比较 用：hex 展开 + color-mix(...,transparent) 求值） ----------

function normalizeColors(value) {
  let v = value
  // color-mix(in srgb, <color> N%, transparent) → rgba(r,g,b,a)；N 按 8-bit 量化
  v = v.replace(/color-mix\(\s*in srgb\s*,\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))\s+([\d.]+)%\s*,\s*transparent\s*\)/g, (all, color, pct) => {
    const rgb = parseColor(color)
    if (!rgb) return all
    const a = Math.round((parseFloat(pct) / 100) * 255) / 255
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`
  })
  // hex → rgba 展开
  v = v.replace(/#([0-9a-fA-F]{8})\b/g, (all, h) => {
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16), a = parseInt(h.slice(6, 8), 16) / 255
    return `rgba(${r},${g},${b},${a})`
  })
  v = v.replace(/#([0-9a-fA-F]{6})\b/g, (all, h) => `rgb(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)})`)
  v = v.replace(/#([0-9a-fA-F]{3})\b/g, (all, h) => `rgb(${parseInt(h[0] + h[0], 16)},${parseInt(h[1] + h[1], 16)},${parseInt(h[2] + h[2], 16)})`)
  return v.replace(/\s+/g, ' ')
}
function parseColor(c) {
  const hex = /^#([0-9a-fA-F]{6})$/.exec(c)
  if (hex) return [parseInt(hex[1].slice(0, 2), 16), parseInt(hex[1].slice(2, 4), 16), parseInt(hex[1].slice(4, 6), 16)]
  const rgba = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/.exec(c)
  if (rgba) return [Number(rgba[1]), Number(rgba[2]), Number(rgba[3])]
  return null
}

// ---------- 元素签名解析 ----------

function mediaMatches(cond, ctx) {
  if (/prefers-reduced-motion\s*:\s*reduce/.test(cond)) return !!ctx.prefersReducedMotion
  const max = /max-width\s*:\s*([\d.]+)px/.exec(cond)
  if (max) return ctx.width <= parseFloat(max[1])
  const min = /min-width\s*:\s*([\d.]+)px/.exec(cond)
  if (min) return ctx.width >= parseFloat(min[1])
  return false
}

function computeFor(node, allRules) {
  let root = node
  while (root.parent) root = root.parent
  const ctx = root.mediaCtx || { width: 1280, prefersReducedMotion: false }
  const matched = []
  let ord = 0
  for (const r of allRules) {
    if (r.kind !== 'rule') continue
    if (r.media && !mediaMatches(r.media, ctx)) continue
    for (const sel of r.selector.split(',')) {
      const s = sel.trim()
      if (!matchSelector(s, node)) continue
      matched.push({ order: ord++, spec: specificity(s), decls: r.decls.map((d) => ({ prop: d.prop.trim(), value: d.value.replace(/\s+/g, ' ').trim(), important: !!d.important })) })
    }
  }
  // 每属性取胜者：important > specificity > order；自定义属性随匹配顺序覆盖
  const result = {}
  const vars = {}
  const list = []
  for (const m of matched) for (const d of m.decls) list.push({ ...d, spec: m.spec, order: m.order })
  for (const d of list) {
    if (d.prop.startsWith('--')) { vars[d.prop] = d.value; continue }
    const cur = result[d.prop]
    const better = !cur || (d.important !== cur.important ? d.important : (cmpSpec(d.spec, cur.spec) || d.order - cur.order) > 0)
    if (better) result[d.prop] = d
  }
  // 继承祖先的自定义属性（祖先已先算好 __vars）
  let anc = node.parent
  while (anc) { if (anc.__vars) for (const [k, v] of Object.entries(anc.__vars)) if (vars[k] === undefined) vars[k] = v; anc = anc.parent }
  node.__vars = vars
  const resolved = {}
  for (const [k, v] of Object.entries(result)) resolved[k] = resolveVars(v.value, vars)
  return { resolved, vars }
}

// 自顶向下预处理：让祖先的 __vars 先就绪
function computeTree(rootNode, allRules) {
  const walk = (n) => { if (n.parent) walk(n.parent); if (!n.__done) { computeFor(n, allRules); n.__done = true } for (const key of ['prev']) if (n[key]) walk(n[key]) }
  walk(rootNode)
  return computeFor(rootNode, allRules)
}

// ---------- 元素签名库（对应 src 组件真实结构） ----------

function lvl(spec) {
  const node = { tag: 'div', classes: new Set(), attrs: {}, states: new Set(), pseudo: null, isRoot: false }
  const [compound, ...stateList] = spec.split('|')
  const tag = /^([a-zA-Z][\w-]*)(?=[.\[:]|$)/.exec(compound)
  if (tag && !['.', '#'].includes(compound[0])) node.tag = tag[1].toLowerCase()
  for (const c of compound.match(/\.([\w-]+)/g) || []) node.classes.add(c.slice(1))
  for (const a of compound.match(/\[[^\]]+\]/g) || []) {
    const m = /\[\s*([\w-]+)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+))\s*)?\]/.exec(a)
    if (m) node.attrs[m[1]] = m[2] ?? m[3] ?? m[4] ?? ''
  }
  for (const st of stateList) {
    if (st.startsWith('::')) node.pseudo = st.slice(2)
    else node.states.add(st.replace(/^:/, ''))
  }
  return node
}
// S('div.shell[data-theme=warm]', 'main', 'article.card:hover|::before') 从根到叶
function S(...specs) {
  let parent = null
  let prev = null
  const nodes = []
  for (const sp of specs) {
    const o = typeof sp === 'string' ? lvl(sp) : sp
    o.parent = parent
    o.prev = prev ?? null
    nodes.push(o)
    parent = o
    prev = null
  }
  return nodes[nodes.length - 1]
}
const WARM = '[data-theme=warm]', NIGHT = '[data-theme=night]'
const shellTh = (th) => `div.shell${th === 'warm' ? WARM : NIGHT}`

function signatures() {
  const list = []
  const add = (name, node) => list.push({ name, node })
  for (const th of ['night', 'warm']) {
    const sh = shellTh(th)
    add(`${th}/shell`, S(sh))
    add(`${th}/side`, S(sh, '.side'))
    add(`${th}/brand-planet`, S(sh, '.side', '.brand', 'b.brand-planet'))
    add(`${th}/brand-planet>i`, S(sh, '.side', '.brand', 'b.brand-planet', 'i'))
    add(`${th}/nav>button`, S(sh, '.side', 'nav', 'button'))
    add(`${th}/nav>button.on`, S(sh, '.side', 'nav', 'button.on'))
    add(`${th}/nav>button.on::before`, S(sh, '.side', 'nav', 'button.on|::before'))
    add(`${th}/nav>button:hover`, S(sh, '.side', 'nav', 'button:hover'))
    add(`${th}/theme-switch>button.selected`, S(sh, '.side', '.theme-switch', 'button.selected'))
    add(`${th}/import-btn`, S(sh, '.side', '.theme-switch.backup-switch', 'label.import-btn'))
    for (const [n, cls] of [['starfield', '.starfield'], ['moon', '.moon'], ['planet', '.planet'], ['orbit-one', '.orbit.orbit-one'], ['constellation-one', '.constellation.constellation-one']]) {
      add(`${th}/${n}`, S(sh, cls))
    }
    add(`${th}/main`, S(sh, 'main'))

    const M = (th_ = th) => [`div.shell${th_ === 'warm' ? WARM : NIGHT}`, 'main']
    add(`${th}/header h1`, S(...M(), 'header', 'div', 'h1'))
    add(`${th}/voyage-badge`, S(...M(), 'header', '.voyage-badge'))
    add(`${th}/global-search input`, S(...M(), '.global-search', 'input'))
    add(`${th}/search-hit`, S(...M(), '.search-results', '.list', 'button.search-hit'))
    add(`${th}/domain-tabs>button`, S(...M(), '.domain-tabs', 'button'))
    add(`${th}/domain-tabs>button.active`, S(...M(), '.domain-tabs', 'button.active'))

    // 卡片与四类星球（真实 DOM：article.card > div.ico.planet-orb.planet-*）
    for (const t of ['network', 'ringed', 'node', 'comet']) {
      const ico = `.ico.planet-orb.planet-${t}`
      add(`${th}/card(${t})`, S(...M(), '.cards', 'article.card'))
      add(`${th}/card(${t}):hover`, S(...M(), '.cards', 'article.card:hover'))
      add(`${th}/ico(${t})`, S(...M(), '.cards', 'article.card', ico))
      add(`${th}/ico(${t})::before`, S(...M(), '.cards', 'article.card', `${ico}|::before`))
      add(`${th}/ico(${t})::after`, S(...M(), '.cards', 'article.card', `${ico}|::after`))
    }
    add(`${th}/card h3`, S(...M(), '.cards', 'article.card', 'h3'))
    add(`${th}/card p`, S(...M(), '.cards', 'article.card', 'p'))
    add(`${th}/card .bar`, S(...M(), '.cards', 'article.card', '.bar'))
    add(`${th}/card .bar>i`, S(...M(), '.cards', 'article.card', '.bar', 'i'))
    add(`${th}/card .bar>i::after`, S(...M(), '.cards', 'article.card', '.bar', 'i|::after'))
    add(`${th}/card>label`, S(...M(), '.cards', 'article.card', 'label'))
    add(`${th}/library-entry`, S(...M(), '.cards', 'article.card', 'label', 'button.library-entry'))
    add(`${th}/tip`, S(...M(), '.tip'))
    add(`${th}/tip>strong`, S(...M(), '.tip', 'strong'))

    // 今日航行
    add(`${th}/checkin-head`, S(...M(), '.checkin-head'))
    add(`${th}/checkin-summary strong`, S(...M(), '.checkin-head', '.checkin-summary', 'strong'))
    add(`${th}/summary-label>span`, S(...M(), '.checkin-head', '.checkin-summary', '.summary-label', 'span'))
    add(`${th}/progress-track>i`, S(...M(), '.checkin-head', '.checkin-summary', '.progress-track', 'i'))
    add(`${th}/progress-track>i::after`, S(...M(), '.checkin-head', '.checkin-summary', '.progress-track', 'i|::after'))
    add(`${th}/checkin-title>span`, S(...M(), '.checkin-title', 'span'))
    const SC = (extra = '', state = '') => S(...M(), '.checkin-list', `article.study-card${extra}${state}`)
    add(`${th}/study-card`, SC())
    add(`${th}/study-card:hover`, SC('', ':hover'))
    add(`${th}/study-card.card-done`, SC('.card-done'))
    add(`${th}/study-card .card-top>em`, S(...M(), '.checkin-list', 'article.study-card', '.card-top', 'em'))
    add(`${th}/study-card .priority`, S(...M(), '.checkin-list', 'article.study-card', '.priority'))
    add(`${th}/study-card .question`, S(...M(), '.checkin-list', 'article.study-card', 'p.question'))
    add(`${th}/study-card .card-foot>button`, S(...M(), '.checkin-list', 'article.study-card', '.card-foot', 'button'))
    add(`${th}/study-card .learning-progress`, S(...M(), '.checkin-list', 'article.study-card', '.learning-progress'))
    add(`${th}/study-card .learning-progress>i`, S(...M(), '.checkin-list', 'article.study-card', '.learning-progress', 'i'))
    add(`${th}/study-card .learning-progress>i>b`, S(...M(), '.checkin-list', 'article.study-card', '.learning-progress', 'i', 'b'))
    add(`${th}/burst`, S(...M(), '.checkin-list', 'article.study-card.card-done', 'span.burst'))

    // 知识星库（含 + 兄弟链）
    const listNode = (() => {
      const shN = lvl(sh)
      const back = lvl('button.back')
      const catHead = lvl('.catHead')
      const libOv = lvl('.library-overview')
      const toolbar = lvl('.toolbar')
      const filters = lvl('.filters')
      const list = lvl('.list')
      back.parent = shN; catHead.parent = shN; catHead.prev = back
      libOv.parent = shN; libOv.prev = catHead
      toolbar.parent = shN; toolbar.prev = libOv
      filters.parent = shN; filters.prev = toolbar
      list.parent = shN; list.prev = filters
      return list
    })()
    add(`${th}/library .list`, listNode)
    const topicN = (() => { const t = lvl('article.topic'); t.parent = listNode; return t })()
    add(`${th}/library .topic`, topicN)
    add(`${th}/library .topic>section>button`, (() => { const sec = lvl('section'); sec.parent = topicN; const b = lvl('button'); b.parent = sec; return b })())
    add(`${th}/library-overview`, listNode.prev)
    add(`${th}/toolbar input`, (() => { const ta = lvl('.toolbar-actions'); ta.parent = listNode.prev.prev; const i = lvl('input'); i.parent = ta; return i })())
    add(`${th}/filters>button.sel`, (() => { const b = lvl('button.sel'); b.parent = listNode.prev; return b })())
    add(`${th}/catHead h1`, (() => { const d = lvl('div'); d.parent = listNode.prev.prev.prev.prev; const h = lvl('h1'); h.parent = d; return h })())
    add(`${th}/source-link`, (() => { const b = lvl('button.source-link'); b.parent = listNode.prev.prev.prev.prev; return b })())
    add(`${th}/modal`, (() => { const ov = lvl('.modal-overlay'); ov.parent = lvl(sh); const f = lvl('form.modal'); f.parent = ov; return f })())
    add(`${th}/modal input`, (() => { const ov = lvl('.modal-overlay'); ov.parent = lvl(sh); const f = lvl('form.modal'); f.parent = ov; const i = lvl('input'); i.parent = f; return i })())
    add(`${th}/modal-actions button.primary`, (() => { const ov = lvl('.modal-overlay'); ov.parent = lvl(sh); const f = lvl('form.modal'); f.parent = ov; const d = lvl('.modal-actions'); d.parent = f; const b = lvl('button.primary'); b.parent = d; return b })())

    // 星航日志
    add(`${th}/log`, S(...M(), '.log'))
    add(`${th}/log-stat`, S(...M(), '.log-stats', '.log-stat'))
    add(`${th}/log-stat strong`, S(...M(), '.log-stats', '.log-stat', 'strong'))
    add(`${th}/heatmap`, S(...M(), '.heatmap'))
    add(`${th}/heatmap-head>span`, S(...M(), '.heatmap', '.heatmap-head', 'span'))
    add(`${th}/heat.level-1`, S(...M(), '.heatmap', '.heatmap-body', '.heatmap-grid', 'span.heat.level-1'))
    add(`${th}/heat.level-4`, S(...M(), '.heatmap', '.heatmap-body', '.heatmap-grid', 'span.heat.level-4'))
    add(`${th}/log-warm`, S(...M(), '.log-mid', '.log-warm'))
    add(`${th}/log-domain`, S(...M(), '.log-panel', '.log-domains', 'button.log-domain'))
    add(`${th}/log-recent li`, S(...M(), '.log-panel', 'ul.log-recent', 'li'))

    // 阅读页
    add(`${th}/read`, S(...M(), '.read'))
    add(`${th}/read-meta h1`, S(...M(), '.read', '.read-head', '.read-meta', 'h1'))
    add(`${th}/read-actions button`, S(...M(), '.read', '.read-head', '.read-actions', 'button'))
    add(`${th}/read-body p`, S(...M(), '.read', '.read-body', 'p'))
    add(`${th}/read-body h2`, S(...M(), '.read', '.read-body', 'h2'))
    add(`${th}/read-body pre`, S(...M(), '.read', '.read-body', 'pre'))
    add(`${th}/read-body code`, S(...M(), '.read', '.read-body', 'code'))
    add(`${th}/read-body th`, S(...M(), '.read', '.read-body', 'table', 'th'))
    add(`${th}/read-body blockquote`, S(...M(), '.read', '.read-body', 'blockquote'))
    add(`${th}/read-download-btn`, S(...M(), '.read', '.read-download', '.read-download-list', 'button.read-download-btn'))

    // 移动端
    add(`${th}/mobile-nav>button.on`, S(sh, '.mobile-nav', 'button.on'))
    add(`${th}/mobile-theme-switch>button.selected`, S(sh, '.mobile-theme-switch', 'button.selected'))
  }
  // 键盘焦点
  {
    const n = S('div.shell', '.side', 'nav', 'button.on:focus-visible')
    add('focus/nav button.on:focus-visible', n)
  }
  return list
}

// ---------- 命令 ----------

function cmdBlocks(file) {
  const css = fs.readFileSync(file, 'utf8')
  const ast = postcss.parse(css, { from: file })
  for (const node of ast.nodes) {
    const sel = node.type === 'rule' ? node.selector.replace(/\s+/g, ' ').slice(0, 95)
      : node.type === 'atrule' ? `@${node.name} ${node.params}`.slice(0, 95) : node.type
    console.log(`${String(node.source?.start?.line ?? 0).padStart(4)}-${String(node.source?.end?.line ?? 0).padEnd(4)} ${sel}`)
  }
}

function cmdInspect(file, needle) {
  const rules = collectRules(inlineImports(file))
  const groups = new Map()
  for (const r of rules) {
    const k = `${r.media} :: ${r.selector}`
    if (!k.includes(needle)) continue
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k).push(r)
  }
  for (const [k, rs] of [...groups].sort((a, b) => a[1][0].order - b[1][0].order)) {
    console.log(`\n== ${k}  (${rs.length} 条)`)
    for (const w of mergeWinners(rs)) console.log(`  ${w.prop}: ${w.value}${w.important ? ' !important' : ''}`)
  }
}

function cmdStats(file) {
  const css = fs.readFileSync(file, 'utf8')
  console.log('bytes:', css.length)
  console.log('!important:', (css.match(/!important/g) || []).length)
  const hexes = css.match(/#[0-9a-fA-F]{3,8}\b/g) || []
  console.log('hex colors:', new Set(hexes.map((x) => x.toLowerCase())).size, '种 /', hexes.length, '处')
  console.log('@media:', (css.match(/@media/g) || []).length)
  const rules = collectRules(inlineImports(file))
  const counts = new Map()
  for (const r of rules) for (const sel of r.selector.split(',')) {
    const k = `${r.media}::${sel.trim().replace(/\s+/g, ' ')}`
    counts.set(k, (counts.get(k) || 0) + 1)
  }
  const dups = [...counts.entries()].filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1])
  console.log('重复 (media+selector) 组:', dups.length)
  for (const [s, n] of dups.slice(0, 30)) console.log(`  ${n}x  ${s.slice(0, 90)}`)
}

function cloneSig(node) {
  const cp = (n) => n ? { ...n, classes: new Set(n.classes), attrs: { ...n.attrs }, states: new Set(n.states), parent: cp(n.parent), prev: n.prev ? { ...n.prev, classes: new Set(n.prev.classes), attrs: { ...n.prev.attrs }, states: new Set(n.prev.states), parent: null, prev: null } : null } : null
  return cp(node)
}

function cmdDiff(oldFile, newFile) {
  const oldRules = collectRules(inlineImports(oldFile))
  const newRules = collectRules(inlineImports(newFile))
  const sigs = signatures()
  let diffs = 0
  for (const { name, node } of sigs) {
    for (const [label, width] of [['desktop', 1280], ['mobile390', 390]]) {
      const oN = cloneSig(node); let r = oN; while (r.parent) r = r.parent; r.mediaCtx = { width, prefersReducedMotion: false }
      const nN = cloneSig(node); r = nN; while (r.parent) r = r.parent; r.mediaCtx = { width, prefersReducedMotion: false }
      const ov = computeTree(oN, oldRules).resolved
      const nv = computeTree(nN, newRules).resolved
      const keys = new Set([...Object.keys(ov), ...Object.keys(nv)])
      for (const k of keys) {
        const a = normalizeColors(ov[k] ?? '(无)'), b = normalizeColors(nv[k] ?? '(无)')
        if (a !== b) {
          diffs++
          console.log(`DIFF [${name}] ${label} ${k}:\n    old: ${ov[k]}\n    new: ${nv[k]}`)
        }
      }
    }
  }
  // 选择器级对比
  const groupOf = (rules) => {
    const m = new Map()
    for (const r of rules) {
      const k = `${r.media} :: ${r.selector}`
      if (!m.has(k)) m.set(k, [])
      m.get(k).push(r)
    }
    const out = new Map()
    for (const [k, rs] of m) out.set(k, mergeWinners(rs).map((w) => `${w.prop}:${w.important ? '!' : ''}${w.value}`).sort().join(';'))
    return out
  }
  const go = groupOf(oldRules), gn = groupOf(newRules)
  const allKeys = new Set([...go.keys(), ...gn.keys()])
  let selDiffs = 0
  for (const k of allKeys) if (go.get(k) !== gn.get(k)) { selDiffs++; console.log(`SELECTOR-DIFF ${k}\n    old: ${go.get(k) || '(无)'}\n    new: ${gn.get(k) || '(无)'}`) }
  // LINT：var() 后紧跟十六进制/标识符字符 = 无效拼接（如 var(--x)55）
  let lint = 0
  for (const r of newRules) for (const d of r.decls) {
    if (/var\(--[\w-]+\)[0-9a-zA-Z]/.test(d.value)) { lint++; console.log(`LINT ${r.selector.slice(0, 60)} :: ${d.prop}: ${d.value.slice(0, 80)}`) }
  }
  console.log(`\n元素签名 diff: ${diffs} 处；选择器级 diff: ${selDiffs} 处；LINT: ${lint} 处（var 替换属预期，需人工核对值等价）`)
}

// ---------- cut ----------

function extractTokens(text, part = 'both') {
  const ast = postcss.parse(text, { from: 'tokens' })
  const out = postcss.root()
  for (const node of ast.nodes) {
    const selNorm = node.type === 'rule' ? node.selector.replace(/\s+/g, '') : ''
    if (node.type === 'rule' && /^\.shell(\[data-theme=warm\])?$/.test(selNorm)) {
      const tok = postcss.rule({ selector: node.selector })
      const rest = postcss.rule({ selector: node.selector })
      for (const d of node.nodes) {
        if (d.type === 'decl' && d.prop.startsWith('--')) tok.append(d.clone())
        else rest.append(d.clone())
      }
      if (tok.nodes.length && (part === 'both' || part === 'tokens')) out.append(tok)
      if (rest.nodes.length && (part === 'both' || part === 'rest')) out.append(rest)
    } else out.append(node.clone())
  }
  return out.toString()
}

function mergeSegment(text) {
  const ast = postcss.parse(text, { from: 'segment' })
  const out = postcss.root()
  for (const node of ast.nodes) {
    if (node.type === 'rule') {
      out.append(mergeRuleGroup([node]))
    } else if (node.type === 'atrule' && node.name === 'media') {
      const m = postcss.atRule({ name: 'media', params: node.params })
      // media 内同 selector 合并
      const groups = new Map()
      const orderKeys = []
      for (const rn of node.nodes) {
        if (rn.type === 'rule') {
          const k = rn.selector.replace(/\s+/g, ' ').trim()
          if (!groups.has(k)) { groups.set(k, []); orderKeys.push(k) }
          groups.get(k).push(rn)
        } else m.append(rn.clone())
      }
      for (const k of orderKeys) for (const r of mergeRuleGroup(groups.get(k))) m.append(r)
      out.append(m)
    } else out.append(node.clone())
  }
  // 跨顶层合并且不在 media 内的相同 selector（保持首现位置，仅当中间没有 media 干扰时安全——本工具按段处理，段内顶层合并即可）
  return dedupeTopLevel(out).toString()
}
function mergeRuleGroup(rules) {
  // rules: 同 selector 的 1..n 条规则 → 合并为一条（丢弃必败者）
  const all = []
  rules.forEach((r, ri) => {
    for (const d of r.nodes) if (d.type === 'decl') all.push({ d, ri, important: !!d.important, prop: d.prop.trim(), idx: all.length })
  })
  const byProp = new Map()
  for (const e of all) {
    const cur = byProp.get(e.prop)
    const better = !cur || (e.important !== cur.important ? e.important : e.ri >= cur.ri && e.idx >= cur.idx)
    if (better) byProp.set(e.prop, e)
  }
  const keep = [...byProp.values()].sort((a, b) => a.idx - b.idx)
  const rule = postcss.rule({ selector: rules[0].selector.replace(/\s+/g, ' ').trim() })
  for (const e of keep) rule.append(e.d.clone())
  return [rule]
}
function dedupeTopLevel(root) {
  // 顶层相邻同 selector 规则合并（保守：仅合并“中间没有被其他规则隔断”的同选择器）
  const out = postcss.root()
  let lastRule = null
  for (const node of root.nodes) {
    if (node.type === 'rule' && lastRule && lastRule.selector.replace(/\s+/g, ' ').trim() === node.selector.replace(/\s+/g, ' ').trim()) {
      const merged = mergeRuleGroup([lastRule, node])
      out.nodes.pop()
      out.append(merged[0])
      lastRule = merged[0]
    } else {
      out.append(node.clone())
      lastRule = node.type === 'rule' ? out.nodes[out.nodes.length - 1] : null
    }
  }
  return out
}

function cmdCut(file, planFile, outdir) {
  const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'))
  const css = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n')
  const lines = css.split('\n')
  fs.mkdirSync(outdir, { recursive: true })
  const imports = []
  const fontImport = css.match(/@import\s+url\([^)]*\)[^;]*;/)
  for (const seg of plan) {
    const [from, to] = seg.lines
    let text = lines.slice(from - 1, to).join('\n')
    if (seg.extractTokens) text = extractTokens(text, seg.part || 'both')
    text = mergeSegment(text)
    text = text.replace(/\n{3,}/g, '\n\n').trim() + '\n'
    const fp = path.join(outdir, seg.file)
    const body = text.replace(/\n{3,}/g, '\n\n').trim() + '\n'
    if (seg.append && fs.existsSync(fp)) {
      fs.appendFileSync(fp, '\n' + body)
    } else {
      const header = `/* ${seg.title || seg.file} — Phase 0 拆分自 src/styles.css（原 ${from}-${to} 行）*/\n`
      fs.writeFileSync(fp, header + body)
    }
    if (!imports.includes(seg.file)) imports.push(seg.file)
    console.log(`wrote ${fp} (${text.length} bytes)`)
  }
  console.log('\n== 入口 src/styles.css 建议内容 ==\n')
  console.log([fontImport ? fontImport[0] : null, ...imports.map((f) => `@import './styles/${f}';`)].filter(Boolean).join('\n'))
}

function cmdElem(file, sigName) {
  const rules = collectRules(inlineImports(file))
  for (const { name, node } of signatures()) {
    if (!name.includes(sigName)) continue
    for (const [label, width] of [['desktop', 1280], ['mobile390', 390]]) {
      const n = cloneSig(node); let r = n; while (r.parent) r = r.parent; r.mediaCtx = { width, prefersReducedMotion: false }
      const { resolved, vars } = computeTree(n, rules)
      console.log(`\n== ${name} [${label}]`)
      for (const k of Object.keys(resolved).sort()) console.log(`  ${k}: ${resolved[k]}`)
      void vars
    }
  }
}

function cmdCheck(file) {
  const root = inlineImports(file)
  const rules = collectRules(root)
  console.log('inlined rules:', rules.length)
  // 逐 import 调试
  const abs = path.resolve(file)
  const css = fs.readFileSync(abs, 'utf8')
  const ast = postcss.parse(css, { from: abs })
  for (const node of ast.nodes) {
    if (node.type === 'atrule' && node.name === 'import') {
      const m = /url\(\s*['"]?([^'")]+)['"]?\s*\)|['"]([^'"]+)['"]/.exec(node.params)
      const target = m && (m[1] || m[2])
      if (!target || /^(https?:|data:)/.test(target)) { console.log(`  skip: ${node.params.slice(0, 50)}`); continue }
      const sub = inlineImports(path.resolve(path.dirname(abs), target), new Set())
      const n = collectRules(sub).length
      console.log(`  ${target} -> ${n} rules`)
    }
  }
  console.log('last 8:', rules.slice(-8).map((r) => `${r.media}::${r.selector.slice(0, 60)}`).join('\n  '))
  const mediaSeen = new Map()
  for (const r of rules) mediaSeen.set(r.media, (mediaSeen.get(r.media) || 0) + 1)
  console.log('media 分布:', [...mediaSeen.entries()].map(([m, n]) => `${m || '(顶层)'}=${n}`).join(', '))
}

// ---------- tokenize：硬编码色值收编（仅在渲染值等价处替换） ----------

// 两主题同值的新 token（Phase 1 再分主题调值）
const SHARED_TOKENS = {
  '--planet-light': '#d8efb9',
  '--planet-shade': '#315f4d',
  '--planet-shade-veil': '#315f4d55',
  '--planet-inset': '#39765f59',
  '--planet-glow': '#82b87955',
  '--planet-glow-soft': '#82b87952',
  '--track': '#2b584899',
  '--veil-green': '#82b8791f',
  '--veil-green-strong': '#82b87929',
  '--heat-1': '#82b8794d',
  '--heat-2': '#82b87985',
  '--heat-3': '#82b879bb',
  '--shadow-ambient': '#00000024',
  '--on-green': '#102018',
}
// 主题内等值替换：warm 规则里的暖阳 token 字面量 / night 规则里的夜航 token 字面量
const WARM_MAP = {
  '#f0bd4f': 'var(--yellow)',
  '#f0bd4f66': 'color-mix(in srgb,var(--yellow) 40%,transparent)',
  '#b8832e': 'var(--yellow-deep)',
  '#fff9e9': 'var(--bg-page)',
  '#fff4d0': 'var(--bg-sidebar)',
  '#e7d39b': 'var(--border)',
  '#3b4539': 'var(--text)',
  '#6f7968': 'var(--muted)',
  '#a09a82': 'var(--subtle)',
  '#719861': 'var(--green)',
  '#bbd795': 'var(--green-soft)',
  '#c97b6c': 'var(--rose)',
}
const NIGHT_MAP = {
  '#f7d56b': 'var(--yellow)',
  '#f7d56b66': 'color-mix(in srgb,var(--yellow) 40%,transparent)',
  '#f7d56b47': 'color-mix(in srgb,var(--yellow) 28%,transparent)',
  '#f7d56b1a': 'color-mix(in srgb,var(--yellow) 10%,transparent)',
  '#f7d56b33': 'color-mix(in srgb,var(--yellow) 20%,transparent)',
  '#f7d56b29': 'color-mix(in srgb,var(--yellow) 16%,transparent)',
  '#f7d56b4d': 'color-mix(in srgb,var(--yellow) 30%,transparent)',
  '#f7d56b5c': 'color-mix(in srgb,var(--yellow) 36%,transparent)',
  '#e2ae43': 'var(--yellow-deep)',
  '#e2ae4366': 'color-mix(in srgb,var(--yellow-deep) 40%,transparent)',
  '#82b879': 'var(--green)',
  '#82b87973': 'color-mix(in srgb,var(--green) 45%,transparent)',
}

function tokenizeDir(dir) {
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.css'))
  // 所有替换按 hex 长度降序执行，防止 #315f4d 抢先吃掉 #315f4d55 的前缀
  const shared = Object.entries(SHARED_TOKENS).map(([name, hex]) => ({ hex, rep: `var(${name})` }))
  for (const f of files) {
    const fp = path.join(dir, f)
    const ast = postcss.parse(fs.readFileSync(fp, 'utf8'), { from: fp })
    let count = 0
    ast.walkRules((rule) => {
      const warm = /data-theme\s*=\s*['"]?warm/.test(rule.selector)
      const night = /data-theme\s*=\s*['"]?night/.test(rule.selector)
      const map = warm ? WARM_MAP : night ? NIGHT_MAP : null
      const themed = map ? Object.entries(map).map(([hex, rep]) => ({ hex, rep })) : []
      const subs = [...shared, ...themed].sort((a, b) => b.hex.length - a.hex.length)
      rule.walkDecls((decl) => {
        if (decl.prop.startsWith('--')) return // token 定义本身绝不改写，防止循环引用
        let v = decl.value
        for (const { hex, rep } of subs) {
          if (v.toLowerCase().includes(hex)) { v = v.split(hex).join(rep); count++ }
        }
        if (v !== decl.value) decl.value = v
      })
    })
    if (count) { fs.writeFileSync(fp, ast.toString()); console.log(`${f}: ${count} 处替换`) }
  }
}

function addSharedTokens(tokensFile) {
  let css = fs.readFileSync(tokensFile, 'utf8')
  const lines = Object.entries(SHARED_TOKENS).map(([k, v]) => `  ${k}:${v};`).join('\n')
  // 追加到 .shell（夜航）块
  css = css.replace(/^\.shell\{/, `\.shell{\n${lines}\n`)
  // warm 块
  css = css.replace(/^\.shell\[data-theme=warm\]\{/, `.shell[data-theme=warm]{\n${lines}\n}`)
  fs.writeFileSync(tokensFile, css)
  console.log('shared tokens 已写入两个主题块')
}

function cmdMatch(file, sigName, selSub) {
  const rules = collectRules(inlineImports(file))
  const { name, node } = signatures().find((s) => s.name === sigName) || {}
  if (!node) { console.log('签名不存在，可选:', signatures().map((s) => s.name).filter((n) => n.includes(sigName)).join(', ')); return }
  let r = node; while (r.parent) r = r.parent; r.mediaCtx = { width: 1280, prefersReducedMotion: false }
  const root2 = node; const chain = []
  for (let n = node; n; n = n.parent) chain.unshift(n)
  for (const rule of rules) {
    if (rule.media) continue
    for (const sel of rule.selector.split(',')) {
      const s = sel.trim()
      if (!s.includes(selSub)) continue
      if (matchSelector(s, node)) {
        console.log(`[${specificity(s).join(',')}] #${rule.order} ${s.slice(0, 90)}`)
      }
    }
  }
}

// ---------- main ----------

const cmd = process.argv[2]
const file = process.argv[3]
if (cmd === 'blocks') cmdBlocks(file)
else if (cmd === 'stats') cmdStats(file)
else if (cmd === 'inspect') cmdInspect(file, process.argv[4])
else if (cmd === 'diff') cmdDiff(file, process.argv[4])
else if (cmd === 'cut') cmdCut(file, process.argv[4], process.argv[5])
else if (cmd === 'elem') cmdElem(file, process.argv[4])
else if (cmd === 'match') cmdMatch(file, process.argv[4], process.argv[5])
else if (cmd === 'norm') console.log(JSON.stringify(normalizeColors(file)))
else if (cmd === 'check') cmdCheck(file)
else if (cmd === 'tokenize') tokenizeDir(file)
else if (cmd === 'add-tokens') addSharedTokens(file)
else console.log('用法见文件头注释')
