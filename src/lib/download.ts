// 下载课程配套代码到本地：桌面端走系统保存对话框（plugin-dialog + plugin-fs），网页端走浏览器下载

export async function downloadCourseCode(path: string, suggestedName: string) {
  const text = await fetch(path).then((res) => {
    if (!res.ok) throw new Error(`下载失败：${res.status}`)
    return res.text()
  })
  if ('__TAURI_INTERNALS__' in window) {
    try {
      const { save } = await import('@tauri-apps/plugin-dialog')
      const { writeTextFile } = await import('@tauri-apps/plugin-fs')
      const target = await save({ defaultPath: suggestedName })
      if (!target) return
      await writeTextFile(target, text)
      return
    } catch {
      // 插件不可用时退回浏览器下载
    }
  }
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
  const link = document.createElement('a')
  link.href = url
  link.download = suggestedName
  link.click()
  URL.revokeObjectURL(url)
}
