import assert from 'node:assert/strict'
import { once } from 'node:events'
import { createServer } from 'node:http'
import { test } from 'node:test'
import { desktopStreamReady } from '../startos/desktopStream.ts'

test('desktop readiness follows the authenticated reconnect endpoint', async () => {
  let status = 204
  const server = createServer((request, response) => {
    const authorized = request.headers.authorization === 'Basic ZGV2OnRlc3Q='
    if (request.url !== '/api/websockets') response.writeHead(404)
    else if (!authorized) response.writeHead(401)
    else if (status === 302) response.writeHead(302, { Location: '/login' })
    else response.writeHead(status)
    response.end()
  })
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  const port = server.address().port
  try {
    assert.equal(await desktopStreamReady(port, 'dev', 'test'), true)
    assert.equal(await desktopStreamReady(port, 'dev', 'incorrect'), false)
    for (status of [200, 302, 404, 409, 502]) {
      assert.equal(await desktopStreamReady(port, 'dev', 'test'), false)
    }
  } finally {
    await new Promise((resolve) => server.close(resolve))
  }
  assert.equal(await desktopStreamReady(port, 'dev', 'test'), false)
})

test(
  'an unresponsive stream is reported unavailable',
  { timeout: 10000 },
  async () => {
    const server = createServer(() => {})
    server.listen(0, '127.0.0.1')
    await once(server, 'listening')
    try {
      assert.equal(
        await desktopStreamReady(server.address().port, 'dev', 'test'),
        false,
      )
    } finally {
      server.closeAllConnections()
      await new Promise((resolve) => server.close(resolve))
    }
  },
)
