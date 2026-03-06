export const OUTPUT_DIR = 'dist'

export function getProxyConfig(viteEnv) {
  const backendUrl = viteEnv.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
  const baseApi = viteEnv.VITE_BASE_API || '/api/v1'

  return {
    [baseApi]: {
      target: backendUrl,
      changeOrigin: true,
    },
  }
}
