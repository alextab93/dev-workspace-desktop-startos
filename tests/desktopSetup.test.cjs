const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const os = require('node:os')
const path = require('node:path')
const { test, mock } = require('node:test')
const { execFile } = require('node:child_process')
const { promisify } = require('node:util')
const run = promisify(execFile)

const password = 'fixture-only-password-not-an-account-secret'

test('desktop setup and recovery with real settings files', async (t) => {
  const directory = await fs.mkdtemp(
    path.join(os.tmpdir(), 'desktop-recovery-'),
  )
  t.after(async () => {
    mock.restoreAll()
    await fs.rm(directory, { recursive: true, force: true })
  })
  const bundle = path.join(directory, 'bundle')
  await run(
    process.execPath,
    [
      require.resolve('@vercel/ncc/dist/ncc/cli.js'),
      'build',
      path.join(__dirname, 'desktopSetup.entry.ts'),
      '--no-cache',
      '-o',
      bundle,
    ],
    { timeout: 60000, maxBuffer: 1024 * 1024 },
  )
  const {
    main,
    setInterfaces,
    watchDesktopSetup,
    desktopSettings,
    editorVersion,
  } = require(path.join(bundle, 'index.js'))
  const settingsPath = path.join(directory, 'desktop.json')
  const access = fs.access.bind(fs)
  const realpath = fs.realpath.bind(fs)
  const watch = fs.watch.bind(fs)
  const mapped = (value) =>
    value === desktopSettings.path ? settingsPath : value
  mock.method(fs, 'access', (value, ...args) => access(mapped(value), ...args))
  mock.method(fs, 'realpath', (value, ...args) =>
    realpath(mapped(value), ...args),
  )
  mock.method(fs, 'watch', (value, ...args) => watch(mapped(value), ...args))

  let tasks = new Map()
  let bindings = new Map()
  let interfaces = new Map()
  const effects = {
    isInContext: true,
    onLeaveContext: () => {},
    getHostInfo: async () => null,
    action: {
      createTask: async (task) => {
        if (!tasks.has(task.replayId)) tasks.set(task.replayId, task)
      },
      clearTasks: async ({ only }) => {
        for (const id of only) tasks.delete(id)
      },
    },
    bind: async (binding) => {
      bindings.set(`${binding.id}:${binding.internalPort}`, binding)
    },
    exportServiceInterface: async (item) => {
      interfaces.set(item.id, item)
    },
    clearBindings: async ({ except }) => {
      const keep = new Set(
        except.map((item) => `${item.id}:${item.internalPort}`),
      )
      bindings = new Map([...bindings].filter(([id]) => keep.has(id)))
    },
    clearServiceInterfaces: async ({ except }) => {
      interfaces = new Map(
        [...interfaces].filter(([id]) => except.includes(id)),
      )
    },
  }
  const write = (editor, credential = password) =>
    fs.writeFile(
      settingsPath,
      JSON.stringify({
        password: credential,
        editorVersion: editor,
        connectionRevision: 7,
      }),
    )
  const prompts = () =>
    [...tasks.values()]
      .map(({ actionId, severity }) => ({ actionId, severity }))
      .sort((a, b) => a.actionId.localeCompare(b.actionId))
  const refresh = async () => {
    await watchDesktopSetup.init(effects)
    await setInterfaces(effects)
  }
  const blocked = async () => {
    await assert.rejects(main({ effects }), /Complete desktop setup/)
    assert.deepEqual([...interfaces], [])
    assert.deepEqual([...bindings], [])
  }
  const usable = async () => {
    await assert.doesNotReject(main({ effects }))
    assert.equal(interfaces.get('desktop').addressInfo.internalPort, 3000)
    assert.deepEqual(bindings.get('desktop:3000').proxy.auth.credentials, [
      { username: 'desktop', password },
    ])
  }

  await t.test(
    'fresh settings require password and first installation',
    async () => {
      await write(null, null)
      await refresh()
      await blocked()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'critical' },
        { actionId: 'set-desktop-password', severity: 'critical' },
      ])
    },
  )
  await t.test(
    'password alone leaves first installation required',
    async () => {
      await write(null)
      await refresh()
      await blocked()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'critical' },
      ])
    },
  )
  await t.test(
    'retained editor clears the old critical task and publishes protected access',
    async () => {
      await write('1.145.2')
      const before = await fs.readFile(settingsPath)
      await refresh()
      await usable()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'important' },
      ])
      assert.deepEqual(await fs.readFile(settingsPath), before)
    },
  )
  await t.test(
    'pending update remains usable across repeated initialization',
    async () => {
      await refresh()
      await usable()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'important' },
      ])
    },
  )
  await t.test('successful update clears the reminder', async () => {
    await write(editorVersion)
    await refresh()
    await usable()
    assert.deepEqual(prompts(), [])
  })
  await t.test(
    'lost installation record revokes the interface and requires installation',
    async () => {
      await write(null)
      await refresh()
      await blocked()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'critical' },
      ])
    },
  )
  await t.test(
    'malformed installation records cannot unlock the desktop',
    async () => {
      for (const value of [
        '',
        'unknown',
        '../1.145.2',
        '1.145.2\n',
        ' 1.145.2',
        145,
        {},
        '1.2',
      ]) {
        await write(value)
        await refresh()
        await blocked()
        assert.deepEqual(prompts(), [
          { actionId: 'install-editor', severity: 'critical' },
        ])
      }
    },
  )
  await t.test('retained editor still requires a valid password', async () => {
    for (const credential of [null, '', 'short']) {
      await write('1.145.2', credential)
      await refresh()
      await blocked()
      assert.deepEqual(prompts(), [
        { actionId: 'install-editor', severity: 'important' },
        { actionId: 'set-desktop-password', severity: 'critical' },
      ])
    }
  })
  await t.test('current editor still requires a password', async () => {
    await write(editorVersion, null)
    await refresh()
    await blocked()
    assert.deepEqual(prompts(), [
      { actionId: 'set-desktop-password', severity: 'critical' },
    ])
  })
  await t.test(
    'restored password makes the current editor accessible',
    async () => {
      await write(editorVersion)
      await refresh()
      await usable()
      assert.deepEqual(prompts(), [])
    },
  )
})
