// @vitest-environment node
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createServer, request as httpRequest, type Server, type IncomingHttpHeaders } from 'node:http'
import type { AddressInfo } from 'node:net'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createServer as createViteServer } from 'vite'
import { createSystemDevProxy, resolveSystemApiTarget } from './systemDevProxy'

let repositoryRoot: string
beforeEach(() => { repositoryRoot = mkdtempSync(path.join(os.tmpdir(), 'hermesx-system-proxy-')) })
afterEach(() => rmSync(repositoryRoot, { recursive: true, force: true }))

const privateUsername = 'test-system-manager'
const privatePassword = 'test-only-private-password'
const expectedAuthorization = `Basic ${Buffer.from(`${privateUsername}:${privatePassword}`).toString('base64')}`

/** 独立连接发送真实原始HTTP头，避免fetch重写Host或跨测试复用旧端口连接。 */
function proxyHttpRequest(url: string, requestOptions: { method?: string; body?: string; headers?: Record<string, string> } = {}) {
  return new Promise<{ status: number; headers: IncomingHttpHeaders; payload?: { resultCode?: string; resultData?: { total: number } | null; source?: string } }>((resolve, reject) => {
    const outbound = httpRequest(url, { method: requestOptions.method ?? 'GET', headers: requestOptions.headers, agent: false }, response => {
      let text = ''
      response.setEncoding('utf8')
      response.on('data', chunk => { text += chunk })
      response.on('error', reject)
      response.on('end', () => {
        try { resolve({ status: response.statusCode ?? 0, headers: response.headers, payload: response.headers['content-type']?.includes('application/json') ? JSON.parse(text) : undefined }) }
        catch (error) { reject(error) }
      })
    })
    outbound.on('error', reject)
    outbound.end(requestOptions.body)
  })
}

async function listenLocally(server: Server): Promise<string> {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`
}

/** 使用真实HTTP服务和Vite代理，只替代Java的网络端点，不mock代理或请求头处理。 */
async function startProxyHarness(configuration: { authSetting?: string; credentialsPresent?: boolean; csrfAvailable?: boolean; targetPresent?: boolean } = {}) {
  const javaRequests: { url?: string; authorization?: string; cookie?: string; csrf?: string | string[]; body: string }[] = []
  const pythonRequests: { authorization?: string; cookie?: string }[] = []
  let csrfSequence = 0
  const java = createServer(async (request, response) => {
    let body = ''
    for await (const chunk of request) body += String(chunk)
    javaRequests.push({ url: request.url, authorization: request.headers.authorization, cookie: request.headers.cookie, csrf: request.headers['x-csrf-token'], body })
    response.setHeader('Content-Type', 'application/json')
    if (request.headers.authorization !== expectedAuthorization) {
      response.writeHead(401, { 'WWW-Authenticate': 'Basic realm="test-system"' })
      response.end(JSON.stringify({ resultCode: 'UNAUTHENTICATED', resultMsg: 'unauthenticated', resultData: null })); return
    }
    if (request.url === '/api/system/users/csrf') {
      if (configuration.csrfAvailable === false) { response.writeHead(503); response.end('{}'); return }
      const current = ++csrfSequence
      response.setHeader('Set-Cookie', `JSESSIONID=session-${current}; HttpOnly; Path=/`)
      response.end(JSON.stringify({ resultCode: '200', resultMsg: 'ok', resultData: { headerName: 'X-CSRF-TOKEN', token: `token-${current}` } })); return
    }
    if (request.method === 'POST') {
      const sequence = request.headers.cookie?.match(/^JSESSIONID=session-(\d+)$/)?.[1]
      if (!sequence || request.headers['x-csrf-token'] !== `token-${sequence}`) {
        response.writeHead(403); response.end(JSON.stringify({ resultCode: 'CSRF_INVALID', resultMsg: 'invalid', resultData: null })); return
      }
    }
    response.setHeader('Set-Cookie', 'JSESSIONID=private-business-session; HttpOnly; Path=/')
    response.end(JSON.stringify({ resultCode: '200', resultMsg: 'ok', resultData: { total: 12 } }))
  })
  const python = createServer((request, response) => {
    pythonRequests.push({ authorization: request.headers.authorization, cookie: request.headers.cookie })
    response.setHeader('Content-Type', 'application/json')
    response.end(JSON.stringify({ source: 'python' }))
  })
  const target = await listenLocally(java)
  const pythonTarget = await listenLocally(python)
  const privateFolder = path.join(repositoryRoot, 'local/hrs-system-service')
  mkdirSync(privateFolder, { recursive: true })
  writeFileSync(path.join(privateFolder, 'runtime.env'), `HRS_WEB_SYSTEM_DEV_AUTH=${configuration.authSetting ?? 'true'}\n`
    + (configuration.credentialsPresent === false ? '' : `HRS_SYSTEM_ADMIN_USERNAME=${privateUsername}\nHRS_SYSTEM_ADMIN_PASSWORD=${privatePassword}\n`))
  if (configuration.targetPresent !== false) writeFileSync(path.join(privateFolder, 'runtime.json'), JSON.stringify({ base_url: target }))
  const routing = createSystemDevProxy(repositoryRoot)
  const vite = await createViteServer({ configFile: false, root: repositoryRoot, logLevel: 'silent',
    plugins: [routing.plugin], optimizeDeps: { noDiscovery: true, include: [] },
    server: { host: '127.0.0.1', port: 0, hmr: false, watch: null, proxy: { ...routing.proxy, '/api': { target: pythonTarget } } },
  })
  await vite.listen()
  const origin = `http://127.0.0.1:${(vite.httpServer!.address() as AddressInfo).port}`
  return { origin, javaRequests, pythonRequests, async close() {
    await vite.close()
    await Promise.all([java, python].map(server => new Promise<void>(resolve => server.close(() => resolve()))))
  } }
}

describe('system development routing', () => {
  it('uses the local startup address without hardcoding its port', () => {
    const runtimeFolder = path.join(repositoryRoot, 'local/hrs-system-service')
    mkdirSync(runtimeFolder, { recursive: true })
    writeFileSync(path.join(runtimeFolder, 'runtime.json'), JSON.stringify({ base_url: 'http://127.0.0.1:31973' }))
    expect(resolveSystemApiTarget(repositoryRoot)).toBe('http://127.0.0.1:31973')
    expect(resolveSystemApiTarget(repositoryRoot, 'http://localhost:31974')).toBe('http://localhost:31974')
  })

  it('keeps the system path and matches its prefix before the Python catch-all', () => {
    const routing = createSystemDevProxy(repositoryRoot, 'http://127.0.0.1:31973')
    const [pattern, options] = Object.entries(routing.proxy)[0]
    expect(new RegExp(pattern).test('/api/system/organization/list-organization')).toBe(true)
    expect(new RegExp(pattern).test('/api/v1/system/config')).toBe(false)
    expect(new RegExp(pattern).test('/api/systematic')).toBe(false)
    expect(options).toMatchObject({ target: 'http://127.0.0.1:31973', changeOrigin: true })
    expect(options.rewrite).toBeUndefined()
    expect(options.auth).toBeUndefined()
  })

  it('does not silently select Python when no system address exists', () => {
    expect(resolveSystemApiTarget(repositoryRoot)).toBeUndefined()
    expect(createSystemDevProxy(repositoryRoot).proxy).toEqual({})
  })

  it('rejects credentials and non-root addresses in target configuration', () => {
    for (const address of ['ftp://localhost', 'http://user:secret@localhost', 'http://localhost/api', 'http://localhost/?target=another']) {
      expect(() => resolveSystemApiTarget(repositoryRoot, address)).toThrow()
    }
  })
})

describe('local development authentication delegation', () => {
  it('adds private Basic/CSRF information for consecutive and concurrent POSTs without exposing Java cookies', async () => {
    const harness = await startProxyHarness()
    try {
      const body = JSON.stringify({ pageNum: 1, pageSize: 10, filterList: [{ fieldName: 'name', comparison: 'LIKE', fieldValue: '研发' }] })
      const sendQuery = () => proxyHttpRequest(`${harness.origin}/api/system/organization/list-organization`, { method: 'POST', body,
        headers: { Origin: harness.origin, 'Content-Type': 'application/json', Cookie: 'python_session=keep-private', Authorization: 'Bearer client-value', 'X-CSRF-TOKEN': 'client-value' } })
      for (const response of [await sendQuery(), ...await Promise.all([sendQuery(), sendQuery()])]) {
        expect(response.status).toBe(200)
        expect(response.headers['set-cookie']).toBeUndefined()
        const envelope = response.payload
        expect(envelope?.resultData?.total).toBe(12)
        expect(JSON.stringify(envelope)).not.toContain(privatePassword)
      }
      const businessRequests = harness.javaRequests.filter(request => request.url?.endsWith('list-organization'))
      expect(businessRequests).toHaveLength(3)
      expect(businessRequests.every(request => request.authorization === expectedAuthorization && request.body === body)).toBe(true)
      expect(new Set(businessRequests.map(request => request.cookie)).size).toBe(3)
      expect(harness.javaRequests.filter(request => request.url?.endsWith('/csrf'))).toHaveLength(3)
      expect(harness.javaRequests.every(request => !request.cookie?.includes('python_session'))).toBe(true)
    } finally { await harness.close() }
  })

  it('leaves Python routes and its login cookie unchanged', async () => {
    const harness = await startProxyHarness()
    try {
      const response = await proxyHttpRequest(`${harness.origin}/api/v1/auth/status`, { headers: { Cookie: 'python_session=original' } })
      expect(response.payload).toEqual({ source: 'python' })
      expect(harness.javaRequests).toHaveLength(0)
      expect(harness.pythonRequests).toEqual([{ authorization: undefined, cookie: 'python_session=original' }])
    } finally { await harness.close() }
  })

  it('rejects cross-origin and rebinding-style requests before credentials reach Java', async () => {
    const harness = await startProxyHarness()
    try {
      for (const headers of [{ Origin: 'https://untrusted.example' }, { 'Sec-Fetch-Site': 'cross-site' }]) {
        const response = await proxyHttpRequest(`${harness.origin}/api/system/organization/list-organization`, { method: 'POST', body: '{}', headers: { ...headers, 'X-Forwarded-For': '127.0.0.1' } })
        expect(response.status).toBe(403)
        expect(response.payload?.resultCode).toBe('FORBIDDEN')
      }
      // Vite自带Host检查可在代理前返回纯文本403，仍应证明未触达Java。
      const rebindingResponse = await proxyHttpRequest(`${harness.origin}/api/system/organization/list-organization`, { method: 'POST', body: '{}', headers: { Host: 'untrusted.example', 'X-Forwarded-For': '127.0.0.1' } })
      expect(rebindingResponse.status).toBe(403)
      expect(harness.javaRequests).toHaveLength(0)
    } finally { await harness.close() }
  })

  it('fails closed when CSRF cannot be obtained and never replays the business request', async () => {
    const harness = await startProxyHarness({ csrfAvailable: false })
    try {
      const response = await proxyHttpRequest(`${harness.origin}/api/system/organization/add-organization`, { method: 'POST', body: '{}' })
      expect(response.status).toBe(503)
      expect(response.payload?.resultCode).toBe('SERVICE_UNAVAILABLE')
      expect(harness.javaRequests.map(request => request.url)).toEqual(['/api/system/users/csrf'])
    } finally { await harness.close() }
  })

  it('does not forward requests with missing credentials or an unknown service address', async () => {
    for (const configuration of [{ credentialsPresent: false }, { targetPresent: false }]) {
      const harness = await startProxyHarness(configuration)
      try {
        const response = await proxyHttpRequest(`${harness.origin}/api/system/organization/list-organization`, { method: 'POST', body: '{}' })
        expect(response.status).toBe(503)
        expect(response.payload?.resultCode).toBe('SERVICE_UNAVAILABLE')
        expect(harness.javaRequests).toHaveLength(0)
        expect(harness.pythonRequests).toHaveLength(0)
      } finally { await harness.close() }
    }
  })

  it('preserves normal authentication when delegation is disabled', async () => {
    const harness = await startProxyHarness({ authSetting: 'false' })
    try {
      const response = await proxyHttpRequest(`${harness.origin}/api/system/organization/get-organization-tree`)
      expect(response.status).toBe(401)
      expect(response.headers['www-authenticate']).toContain('Basic')
      expect(harness.javaRequests[0].authorization).toBeUndefined()
    } finally { await harness.close() }
  })

  it('rejects invalid switches and non-local Java targets for delegation', () => {
    expect(() => createSystemDevProxy(repositoryRoot, 'http://127.0.0.1:31973', 'yes')).toThrow()
    expect(() => createSystemDevProxy(repositoryRoot, 'https://remote.example', 'true')).toThrow()
  })
})
