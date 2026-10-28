// Web Audio 现场合成音效，不引入音频素材；首次点击（用户手势）时惰性创建 AudioContext

let audioCtx: AudioContext | null = null

function ensureAudio() {
  if (!audioCtx) audioCtx = new (window.AudioContext || (window as typeof window & { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
  if (audioCtx.state === 'suspended') void audioCtx.resume()
}

function tone(freq: number, at: number, duration: number, volume: number) {
  if (!audioCtx) return
  const start = audioCtx.currentTime + at
  const osc = audioCtx.createOscillator()
  const gain = audioCtx.createGain()
  osc.type = 'sine'
  osc.frequency.value = freq
  gain.gain.setValueAtTime(volume, start)
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration)
  osc.connect(gain).connect(audioCtx.destination)
  osc.start(start)
  osc.stop(start + duration + 0.05)
}

export function playTick() { ensureAudio(); tone(523.25, 0, 0.09, 0.06) } // 开始学习：轻“嗒”
export function playDing() { ensureAudio(); tone(880, 0, 0.5, 0.12); tone(1318.51, 0.09, 0.6, 0.1) } // 点亮一颗星：叮✦
export function playFanfare() { ensureAudio(); [659.25, 880, 1318.51].forEach((freq, index) => tone(freq, index * 0.12, 0.7, 0.12)) } // 点亮全部：小号角
