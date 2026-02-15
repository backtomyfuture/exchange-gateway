import { request } from '@/utils'

export default {
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),

  // ==========================================================================
  // Exchange 邮件服务
  // ==========================================================================

  // 邮箱账户管理
  getDashboardData: () => request.get('/exchange/accounts/dashboard'),
  getExchangeAccounts: (params = {}) => request.get('/exchange/accounts/list', { params }),
  createExchangeAccount: (data = {}) => request.post('/exchange/accounts/create', data),
  updateExchangeAccount: (data = {}) => request.post('/exchange/accounts/update', data),
  deleteExchangeAccount: (params = {}) => request.delete('/exchange/accounts/delete', { params }),
  testExchangeAccount: (params = {}) => request.post('/exchange/accounts/test', null, { params }),

  // 文件夹管理
  getAllFolders: (params = {}) => request.get('/exchange/emails/folders/all', { params }),

  // API 密钥管理
  getExchangeApiKeys: (params = {}) => request.get('/exchange/api-keys/list', { params }),
  createExchangeApiKey: (data = {}) => request.post('/exchange/api-keys/create', data),
  revokeExchangeApiKey: (params = {}) => request.post('/exchange/api-keys/revoke', null, { params }),
  deleteExchangeApiKey: (params = {}) => request.delete('/exchange/api-keys/delete', { params }),

  // 使用统计和日志
  getExchangeStats: () => request.get('/exchange/api-keys/stats'),
  getExchangeLogs: (params = {}) => request.get('/exchange/api-keys/logs', { params }),

  // 邮件模板管理
  getEmailTemplates: (params = {}) => request.get('/exchange/templates/list', { params }),
  getEmailTemplate: (params = {}) => request.get('/exchange/templates/get', { params }),
  createEmailTemplate: (data = {}) => request.post('/exchange/templates/create', data),
  updateEmailTemplate: (data = {}) => request.post('/exchange/templates/update', data),
  deleteEmailTemplate: (params = {}) => request.delete('/exchange/templates/delete', { params }),
  previewEmailTemplate: (data = {}) => request.post('/exchange/templates/preview', data),

  // Webhook 管理
  getWebhooks: (params = {}) => request.get('/exchange/webhooks/list', { params }),
  createWebhook: (data = {}) => request.post('/exchange/webhooks/create', data),
  updateWebhook: (id, data = {}) => request.post('/exchange/webhooks/update', data, { params: { id } }),
  deleteWebhook: (id) => request.delete('/exchange/webhooks/delete', { params: { id } }),
  testWebhook: (id) => request.post(`/exchange/webhooks/test/${id}`),
}

