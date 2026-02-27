import { createI18n } from 'vue-i18n'

import messages from './messages'

function readLocale() {
  try {
    const raw = localStorage.getItem('LOCALE')
    if (raw) {
      const data = JSON.parse(raw)
      return data.value || null
    }
  } catch {
    // ignore
  }
  return null
}

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: readLocale() || 'cn',
  fallbackLocale: 'cn',
  messages: messages,
})

export default i18n
