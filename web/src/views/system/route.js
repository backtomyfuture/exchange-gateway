const Layout = () => import('@/layout/index.vue')

export default {
    name: 'System',
    path: '/system',
    component: Layout,
    redirect: '/system/user',
    meta: {
        titleKey: 'system_route.title',
        icon: 'material-symbols:settings-outline',
        order: 20,
    },
    children: [
        {
            name: 'SysUser',
            path: 'user',
            component: () => import('@/views/system/user/index.vue'),
            meta: {
                titleKey: 'system_route.user',
                icon: 'material-symbols:person-outline',
            },
        },
        {
            name: 'SysRole',
            path: 'role',
            component: () => import('@/views/system/role/index.vue'),
            meta: {
                titleKey: 'system_route.role',
                icon: 'material-symbols:shield-person-outline',
            },
        },
        {
            name: 'SysMenu',
            path: 'menu',
            component: () => import('@/views/system/menu/index.vue'),
            meta: {
                titleKey: 'system_route.menu',
                icon: 'material-symbols:menu',
            },
        },
        {
            name: 'SysApi',
            path: 'api',
            component: () => import('@/views/system/api/index.vue'),
            meta: {
                titleKey: 'system_route.api',
                icon: 'material-symbols:api',
            },
        },
        {
            name: 'SysDept',
            path: 'dept',
            component: () => import('@/views/system/dept/index.vue'),
            meta: {
                titleKey: 'system_route.dept',
                icon: 'material-symbols:apartment',
            },
        },
        {
            name: 'SysAuditLog',
            path: 'auditlog',
            component: () => import('@/views/system/auditlog/index.vue'),
            meta: {
                titleKey: 'system_route.auditlog',
                icon: 'material-symbols:history',
            },
        },
    ],
}
