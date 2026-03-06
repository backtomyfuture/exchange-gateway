const Layout = () => import('@/layout/index.vue')

export default {
    name: 'Developer',
    path: '/developer',
    component: Layout,
    redirect: '/developer/index',
    meta: {
        titleKey: 'developer.route_title',
        icon: 'material-symbols:code',
        order: 90,
    },
    children: [
        {
            name: 'DeveloperGuide',
            path: 'index',
            component: () => import('@/views/developer/index.vue'),
            meta: {
                titleKey: 'developer.route_guide',
                icon: 'material-symbols:help-outline',
            },
        },
    ],
}
