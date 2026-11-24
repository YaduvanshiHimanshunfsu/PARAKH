// In-browser QR decoding. The image never leaves the device; only the decoded
// text is sent for analysis (POST /parakh/qr/analyze).
//
// BarcodeDetector is used when the browser has it (Android, macOS, ChromeOS).
// Desktop Chrome/Edge on Windows does not, so jsQR (pure JS, offline) is the
// fallback — without it the QR check would fail on the demo laptop.

import jsQR from 'jsqr'

const MAX_EDGE = 1600

export function nativeDetectorAvailable() {
  return typeof window !== 'undefined' && 'BarcodeDetector' in window
}

export function cameraAvailable() {
  return Boolean(globalThis.isSecureContext && navigator.mediaDevices?.getUserMedia)
}

function pixelsFrom(source, width, height) {
  const scale = Math.min(1, MAX_EDGE / Math.max(width, height))
  const w = Math.max(1, Math.round(width * scale))
  const h = Math.max(1, Math.round(height * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const context = canvas.getContext('2d', { willReadFrequently: true })
  context.drawImage(source, 0, 0, w, h)
  return context.getImageData(0, 0, w, h)
}

async function detectNative(source) {
  try {
    const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
    const codes = await detector.detect(source)
    return codes[0]?.rawValue || null
  } catch {
    return null
  }
}

function detectJs(source, width, height) {
  const image = pixelsFrom(source, width, height)
  const code = jsQR(image.data, image.width, image.height, { inversionAttempts: 'attemptBoth' })
  return code?.data || null
}

/** Decode a QR code from an uploaded image file. Throws if none is found. */
export async function decodeQrFile(file) {
  const bitmap = await createImageBitmap(file)
  try {
    const value =
      (nativeDetectorAvailable() && (await detectNative(bitmap))) || detectJs(bitmap, bitmap.width, bitmap.height)
    if (!value) throw new Error('No QR code was found in this image. Try a sharper, closer photo.')
    return value
  } finally {
    bitmap.close?.()
  }
}

/** Decode one frame from a playing <video>. Returns null when no code is visible. */
export async function decodeQrFrame(video) {
  if (!video?.videoWidth) return null
  if (nativeDetectorAvailable()) {
    const value = await detectNative(video)
    if (value) return value
  }
  return detectJs(video, video.videoWidth, video.videoHeight)
}
