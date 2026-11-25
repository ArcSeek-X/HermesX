import { existsSync, readFileSync } from 'node:fs'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { isIP } from 'node:net'
import path from 'node:path'
import { parseEnv } from 'node:util'
import type { Plugin, ProxyOptions } from 'vite'

const SYSTEM_API_PATTERN = '^/api/system(?:/|\\?|$)'
const SYSTEM_API_MATCHER = new RegExp(SYSTEM_API_PATTERN)

function isLoopbackAddress(address: string): boolean {
  const normalized = address.toLowerCase().replace(/^\[|\]$/g, '').replace(/^::ffff:/, '')
  return normalized === '::1' || (isIP(normalized) === 4 && normalized.startsWith('127.'))
}

/** 不信任转发IP；仅允许本机地址、本机Host以及同源浏览器请求使用管理代传。 */
function isLocalDevelopmentRequest(request: IncomingMessage): boolean {
  if (!isLoopbackAddress(request.socket.remoteAddress ?? '')) return false
  try {
    const protocol = 'encrypted' in request.socket && request.socket.encrypted ? 'https:' : 'http:'
    const frontend = new URL(`${protocol}//${request.headers.host ?? ''}`)
    if (frontend.hostname !== 'localhost' && !isLoopbackAddress(frontend.hostname)) return false
    if (frontend.pathname !== '/' || frontend.search || frontend.hash || frontend.username || frontend.password) return false
    if (request.headers['sec-fetch-site'] === 'cross-site') return false
    return !request.headers.origin || new URL(request.headers.origin).origin === frontend.origin
  } catch {
    return false
  }
}

function proxyError(response: ServerResponse, status: number, resultCode: string, resultMsg: string): void {
  if (response.writableEnded || response.destroyed) return
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' })
  response.end(JSON.stringify({ resultCode, resultMsg, resultData: null }))
}

/** 每次POST等写请求独立获取token与对应session，避免并发请求或token轮换相互覆盖。 */
async function attachSystemCsrf(request: IncomingMessage, target: string, authorization: string): Promise<void> {
  const csrfResponse = await fetch(new URL('/api/system/users/csrf', target), {
    headers: { Authorization: authorization },
    signal: AbortSignal.timeout(5000),
    redirect: 'error',
  })
  if (!csrfResponse.ok) throw new Error('system CSRF request failed')
  const envelope = await csrfResponse.json() as { resultCode?: unknown; resultData?: { headerName?: unknown; token?: unknown } }
  const csrf = envelope.resultData
  const cookies = csrfResponse.headers.getSetCookie().map(cookie => cookie.split(';')[0]).join('; ')
  if (envelope.resultCode !== '200' || typeof csrf?.headerName !== 'string' || csrf.headerName.toLowerCase() !== 'x-csrf-token'
    || typeof csrf.token !== 'string' || !csrf.token || !cookies) throw new Error('Invalid system CSRF response')
  request.headers[csrf.headerName.toLowerCase()] = csrf.token
  request.headers.cookie = cookies
}

/** 开发地址来自显式配置或本机启动记录，不把随机端口写入前端。 */
export function resolveSystemApiTarget(repositoryRoot: string, configuredTarget?: string): string | undefined {
  let target: unknown = configuredTarget?.trim()
  if (!target) {
    const runtimeFile = path.join(repositoryRoot, 'local/hrs-system-service/runtime.json')
    if (!existsSync(runtimeFile)) return undefined
    const runtime = JSON.parse(readFileSync(runtimeFile, 'utf8')) as { base_url?: unknown }
    target = runtime.base_url
  }
  if (typeof target !== 'string' || !target) throw new Error('system启动记录缺少有效服务地址')
  const address = new URL(target)
  if (!['http:', 'https:'].includes(address.protocol) || address.username || address.password
    || address.pathname !== '/' || address.search || address.hash) {
    throw new Error('system代理地址必须是HTTP服务根地址，不能包含凭据、路径或查询参数')
  }
  return address.origin
}

export function createSystemDevProxy(repositoryRoot: string, configuredTarget?: string, configuredDevAuth?: string): {
  plugin: Plugin
  proxy: Record<string, ProxyOptions>
} {
  const target = resolveSystemApiTarget(repositoryRoot, configuredTarget)
  const privateEnvironmentFile = path.join(repositoryRoot, 'local/hrs-system-service/runtime.env')
  const privateEnvironment = existsSync(privateEnvironmentFile) ? parseEnv(readFileSync(privateEnvironmentFile, 'utf8')) : {}
  const devAuthSetting = configuredDevAuth?.trim() || privateEnvironment.HRS_WEB_SYSTEM_DEV_AUTH || 'false'
  if (!['true', 'false'].includes(devAuthSetting)) throw new Error('HRS_WEB_SYSTEM_DEV_AUTH只能为true或false')
  const delegateAuthentication = devAuthSetting === 'true'
  if (delegateAuthentication && target) {
    const hostname = new URL(target).hostname
    if (hostname !== 'localhost' && !isLoopbackAddress(hostname)) throw new Error('本机开发代传只允许连接回环地址的Java服务')
  }
  const username = privateEnvironment.HRS_SYSTEM_ADMIN_USERNAME
  const password = privateEnvironment.HRS_SYSTEM_ADMIN_PASSWORD
  const authorization = username && password && !username.includes(':')
    ? `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}` : undefined
  return {
    proxy: target ? { [SYSTEM_API_PATTERN]: {
      target,
      changeOrigin: true,
      configure(proxy) {
        if (!delegateAuthentication) return
        proxy.on('proxyRes', upstreamResponse => {
          // Java的CSRF session留在代理内，不污染浏览器的Python登录会话，也不弹出Basic登录框。
          delete upstreamResponse.headers['set-cookie']
          delete upstreamResponse.headers['www-authenticate']
        })
      },
    } } : {},
    plugin: {
      name: 'hermesx-system-dev-proxy',
      apply: 'serve',
      configureServer(server) {
        server.middlewares.use((request, response, next) => {
          if (!SYSTEM_API_MATCHER.test(request.url ?? '')) return next()
          if (!target) return proxyError(response, 503, 'SERVICE_UNAVAILABLE', '未配置Java system服务地址，请先启动服务或配置HRS_WEB_SYSTEM_API_TARGET。')
          if (!delegateAuthentication) return next()
          if (!isLocalDevelopmentRequest(request)) return proxyError(response, 403, 'FORBIDDEN', '本机开发管理代理只接受本机同源请求。')
          if (!authorization) return proxyError(response, 503, 'SERVICE_UNAVAILABLE', '本机管理配置缺失，请核对私有runtime.env文件。')
          request.headers.authorization = authorization
          delete request.headers.cookie
          delete request.headers['x-csrf-token']
          delete request.headers['x-xsrf-token']
          if (['GET', 'HEAD', 'OPTIONS'].includes(request.method ?? 'GET')) return next()
          void attachSystemCsrf(request, target, authorization).then(() => {
            if (!response.writableEnded && !response.destroyed) next()
          }).catch(() => {
            proxyError(response, 503, 'SERVICE_UNAVAILABLE', '无法取得system请求校验信息，请检查Java服务和本机管理配置。')
          })
        })
      },
    },
  }
}
