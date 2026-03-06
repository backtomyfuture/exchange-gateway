const Layout = () => import('@/layout/index.vue')

export default {
    name: 'Exchange',
    path: '/exchange',
    component: Layout,
    redirect: '/exchange/accounts',
    meta: {
        titleKey: 'exchange.route.title',
        icon: 'token:brand-exchange',
        order: 10,
    },
    children: [
        {
            name: 'ExchangeAccounts',
            path: 'accounts',
            component: () => import('@/views/exchange/accounts/index.vue'),
            meta: {
                titleKey: 'exchange.route.accounts',
                icon: 'material-symbols:contact-mail-outline',
            },
        },
        {
            name: 'ExchangeApiKeys',
            path: 'keys',
            component: () => import('@/views/exchange/keys/index.vue'),
            meta: {
                titleKey: 'exchange.route.keys',
                icon: 'material-symbols:key-outline',
            },
        },
        {
            name: 'ExchangeWebhooks',
            path: 'webhooks',
            component: () => import('@/views/exchange/webhooks/index.vue'),
            meta: {
                titleKey: 'exchange.route.webhooks',
                icon: 'connection',
            },
        },
        {
            name: 'ExchangeTemplates',
            path: 'templates',
            component: () => import('@/views/exchange/templates/index.vue'),
            meta: {
                titleKey: 'exchange.route.templates',
                icon: 'material-symbols:article-outline',
            },
        },
        {
            name: 'ExchangeLogs',
            path: 'logs',
            component: () => import('@/views/exchange/logs/index.vue'),
            meta: {
                titleKey: 'exchange.route.logs',
                icon: 'material-symbols:history',
            },
        },
        {
            name: 'ExchangeStats',
            path: 'stats',
            component: () => import('@/views/exchange/stats/index.vue'),
            meta: {
                titleKey: 'exchange.route.stats',
                icon: 'material-symbols:analytics-outline',
            },
        },
    ],
}
