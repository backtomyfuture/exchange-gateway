const Layout = () => import('@/layout/index.vue')

export default {
    name: 'Developer',
    path: '/developer',
    component: Layout,
    redirect: '/developer/index',
    meta: {
        title: '开发者服务',
        icon: 'material-symbols:code',
        order: 90,
    },
    children: [
        {
            name: 'DeveloperGuide',
            path: 'index',
            component: () => import('@/views/developer/index.vue'),
            meta: {
                title: '开发者指南',
                icon: 'material-symbols:help-outline',
            },
        },
    ],
}
