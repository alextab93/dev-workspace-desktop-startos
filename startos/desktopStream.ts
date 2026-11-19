import { Buffer } from 'node:buffer'

export async function desktopStreamReady(
  port: number,
  user: string,
  password: string,
) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 3000)
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/websockets`, {
      headers: {
        Authorization:
          'Basic ' + Buffer.from(`${user}:${password}`).toString('base64'),
      },
      redirect: 'error',
      signal: controller.signal,
    })
    return response.status === 204
  } catch {
    return false
  } finally {
    controller.abort()
    clearTimeout(timeout)
  }
}
