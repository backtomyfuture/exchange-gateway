import { useUserStore } from '@/store'
import i18n from '~/i18n'

export function addBaseParams(params) {
  if (!params.userId) {
    params.userId = useUserStore().userId
  }
}

export function resolveResError(code, message) {
  const t = i18n.global.t
  switch (code) {
    case 400:
      message = message ?? t('common.http_errors.400')
      break
    case 401:
      message = message ?? t('common.http_errors.401')
      break
    case 403:
      message = message ?? t('common.http_errors.403')
      break
    case 404:
      message = message ?? t('common.http_errors.404')
      break
    case 500:
      message = message ?? t('common.http_errors.500')
      break
    default:
      message = message ?? `【${code}】: ${t('common.http_errors.unknown')}!`
      break
  }
  return message
}
