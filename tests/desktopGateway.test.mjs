import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import fs from 'node:fs/promises'
import https from 'node:https'
import os from 'node:os'
import path from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { promisify } from 'node:util'
import test from 'node:test'

const execute = promisify(execFile)
const image = process.env.DESKTOP_TEST_IMAGE

async function docker(...args) {
  return (
    await execute('docker', args, { timeout: 60000, maxBuffer: 1024 * 1024 })
  ).stdout.trim()
}

async function request(url, headers = {}, options = {}) {
  return new Promise((resolve, reject) => {
    const request = https.request(
      url,
      { rejectUnauthorized: false, headers, method: options.method ?? 'GET' },
      (response) => {
        response.resume()
        response.once('end', () => resolve(response.statusCode))
      },
    )
    request.once('upgrade', (response, socket) => {
      socket.destroy()
      resolve(response.statusCode)
    })
    request.once('error', reject)
    request.setTimeout(5000, () =>
      request.destroy(new Error('Desktop response timeout.')),
    )
    request.end(options.body)
  })
}

test(
  'desktop requires credentials and rejects foreign origins and file transfers',
  { timeout: 150000 },
  async () => {
    assert.ok(image, 'Set DESKTOP_TEST_IMAGE to the candidate image.')
    const token = randomUUID()
    const name = `scratch-desktop-gateway-${token}`
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), name))
    const username = 'desktop-test'
    const password = randomBytes(24).toString('hex')
    const environment = path.join(directory, 'fixture.env')
    await fs.writeFile(
      environment,
      `CUSTOM_USER=${username}\nPASSWORD=${password}\n`,
      { mode: 0o600 },
    )
    let container
    try {
      container = await docker(
        'create',
        '--name',
        name,
        '--label',
        `dev-workspace-fixture=${token}`,
        '--shm-size',
        '512m',
        '--publish',
        '127.0.0.1::3001',
        '--tmpfs',
        '/config:rw,size=256m',
        '--env-file',
        environment,
        '--entrypoint',
        '/init',
        image,
      )
      await docker('start', container)
      const mapping = await docker('port', container, '3001/tcp')
      assert.match(mapping, /^127\.0\.0\.1:\d+$/)
      const url = new URL(`https://${mapping}/`)
      const authorization = `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`
      const deadline = Date.now() + 90000
      while (Date.now() < deadline) {
        try {
          if ((await request(url, { Authorization: authorization })) === 200)
            break
        } catch {}
        const state = JSON.parse(await docker('inspect', container))[0].State
        assert.equal(
          state.Running,
          true,
          `Desktop gateway exited with ${state.ExitCode}.`,
        )
        await delay(500)
      }
      assert.equal(await request(url), 401)
      assert.equal(
        await request(url, { Authorization: 'Basic Zm9vOmJhcg==' }),
        401,
      )
      assert.equal(await request(url, { Authorization: authorization }), 200)
      assert.equal(
        await request(url, {
          Authorization: authorization,
          Origin: url.origin,
        }),
        200,
      )
      const origins = [
        'https://example.invalid',
        `http://${url.host}`,
        `https://${url.hostname}:${Number(url.port) + 1}`,
        'null',
      ]
      for (const origin of origins) {
        assert.equal(
          await request(url, { Authorization: authorization, Origin: origin }),
          403,
          origin,
        )
        assert.equal(
          await request(new URL('/api/websockets', url), {
            Authorization: authorization,
            Origin: origin,
            Connection: 'Upgrade',
            Upgrade: 'websocket',
            'Sec-WebSocket-Version': '13',
            'Sec-WebSocket-Key': randomBytes(16).toString('base64'),
          }),
          403,
          `Streaming origin ${origin}`,
        )
      }
      assert.equal(
        await request(new URL('/api/websockets', url), {
          Origin: url.origin,
          Connection: 'Upgrade',
          Upgrade: 'websocket',
          'Sec-WebSocket-Version': '13',
          'Sec-WebSocket-Key': randomBytes(16).toString('base64'),
        }),
        401,
      )
      const streamHeaders = {
        Authorization: authorization,
        Origin: url.origin,
        Connection: 'Upgrade',
        Upgrade: 'websocket',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Key': randomBytes(16).toString('base64'),
      }
      let streamStatus
      const streamDeadline = Date.now() + 30000
      do {
        streamStatus = await request(
          new URL('/api/websockets', url),
          streamHeaders,
        )
        if (streamStatus === 101) break
        await delay(500)
      } while (Date.now() < streamDeadline)
      assert.equal(streamStatus, 101)
      const transferHeaders = {
        Authorization: authorization,
        Origin: url.origin,
      }
      assert.equal(
        await request(
          new URL('/api/upload', url),
          {
            ...transferHeaders,
            'X-Upload-Path': `upload-${token}.txt`,
            'Content-Type': 'application/octet-stream',
          },
          { method: 'POST', body: `upload fixture ${token}` },
        ),
        403,
      )
      await docker(
        'exec',
        container,
        'runuser',
        '-u',
        'abc',
        '--',
        'python3',
        '-c',
        `from pathlib import Path; p=Path('/config/Desktop/download-${token}.txt'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('download fixture ${token}')`,
      )
      assert.equal(
        await request(
          new URL(`/api/files/download-${token}.txt`, url),
          transferHeaders,
        ),
        403,
      )
      assert.equal(
        await request(
          new URL('/api/file-manager/browse', url),
          transferHeaders,
        ),
        403,
      )
      assert.equal(
        await docker(
          'exec',
          container,
          'python3',
          '-c',
          `from pathlib import Path; p=Path('/config/Desktop'); assert not (p/'upload-${token}.txt').exists(); print((p/'download-${token}.txt').read_text())`,
        ),
        `download fixture ${token}`,
      )
    } finally {
      if (container) {
        const inspection = JSON.parse(await docker('inspect', container))[0]
        assert.equal(inspection.Config.Labels['dev-workspace-fixture'], token)
        await docker('rm', '--force', '--volumes', container)
      }
      await fs.rm(directory, { recursive: true })
    }
  },
)
