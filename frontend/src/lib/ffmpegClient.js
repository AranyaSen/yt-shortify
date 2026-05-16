import { FFmpeg } from '@ffmpeg/ffmpeg'
import { toBlobURL } from '@ffmpeg/util'

const CORE_VERSION = '0.12.6'
const CORE_BASE = `https://unpkg.com/@ffmpeg/core-mt@${CORE_VERSION}/dist/esm`

const VERTICAL_VF =
  'scale=1080:1920:force_original_aspect_ratio=decrease,' +
  'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'

let ffmpegPromise = null

export async function getFfmpeg() {
  if (ffmpegPromise) return ffmpegPromise

  ffmpegPromise = (async () => {
    const ffmpeg = new FFmpeg()

    await ffmpeg.load({
      coreURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${CORE_BASE}/ffmpeg-core.wasm`, 'application/wasm'),
      workerURL: await toBlobURL(
        `${CORE_BASE}/ffmpeg-core.worker.js`,
        'text/javascript',
      ),
    })

    return ffmpeg
  })()

  return ffmpegPromise
}

async function formatVerticalClip(ffmpeg, segmentBytes, index) {
  const inputName = `seg_in_${index}.mp4`
  const outputName = `seg_out_${index}.mp4`

  await ffmpeg.writeFile(inputName, segmentBytes)

  const exitCode = await ffmpeg.exec([
    '-y',
    '-i',
    inputName,
    '-vf',
    VERTICAL_VF,
    '-c:v',
    'libx264',
    '-preset',
    'ultrafast',
    '-tune',
    'fastdecode',
    '-crf',
    '28',
    '-pix_fmt',
    'yuv420p',
    '-c:a',
    'aac',
    '-b:a',
    '96k',
    '-ac',
    '2',
    '-movflags',
    '+faststart',
    outputName,
  ])

  await ffmpeg.deleteFile(inputName)

  if (exitCode !== 0) {
    throw new Error('FFmpeg failed to format clip')
  }

  const data = await ffmpeg.readFile(outputName)
  await ffmpeg.deleteFile(outputName)

  return new Blob([data], { type: 'video/mp4' })
}

export async function renderAllShorts(jobId, shorts, { onProgress, onClipDone }) {
  const ffmpeg = await getFfmpeg()
  const results = []

  for (let i = 0; i < shorts.length; i++) {
    const short = shorts[i]
    onProgress?.(i, shorts.length, short)

    const res = await fetch(`/api/segment/${jobId}/${short.id}/`)
    if (!res.ok) {
      throw new Error(`Could not load segment for ${short.title}`)
    }
    const segmentBytes = new Uint8Array(await res.arrayBuffer())

    const blob = await formatVerticalClip(ffmpeg, segmentBytes, i)
    const videoUrl = URL.createObjectURL(blob)
    const rendered = { ...short, videoUrl, blob }
    results.push(rendered)
    onClipDone?.(rendered, i, shorts.length)
  }

  return results
}
