const Layout = () => import('@/layout/index.vue')

export default {
    name: 'Exchange',
    path: '/exchange',
    component: Layout,
    redirect: '/exchange/accounts',
    meta: {
        title: 'Exchange邮件',
        icon: 'token:brand-exchange',
        order: 10,
    },
    children: [
        {
            name: 'ExchangeAccounts',
            path: 'accounts',
            component: () => import('@/views/exchange/accounts/index.vue'),
            meta: {
                title: '账户管理',
                icon: 'material-symbols:contact-mail-outline',
            },
        },
        {
            name: 'ExchangeApiKeys',
            path: 'keys',
            component: () => import('@/views/exchange/keys/index.vue'),
            meta: {
                title: 'API密钥',
                icon: 'material-symbols:key-outline',
            },
        },
        {
            name: 'ExchangeTemplates',
            path: 'templates',
            component: () => import('@/views/exchange/templates/index.vue'),
            meta: {
                title: '邮件模板',
                icon: 'material-symbols:article-outline',
            },
        },
        {
            name: 'ExchangeLogs',
            path: 'logs',
            component: () => import('@/views/exchange/logs/index.vue'),
            meta: {
                title: '操作日志',
                icon: 'material-symbols:history',
            },
        },
        {
            name: 'ExchangeStats',
            path: 'stats',
            component: () => import('@/views/exchange/stats/index.vue'),
            meta: {
                title: '使用统计',
                icon: 'material-symbols:analytics-outline',
            },
        },
    ],
}
