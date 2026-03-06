import { defineStore } from 'pinia'
import { basicRoutes, asyncRoutes, vueModules } from '@/router/routes'
const Layout = () => import('@/layout/index.vue')
import api from '@/api'

function buildTitleKeyMap(routes, basePath = '') {
  const map = {}
  for (const route of routes) {
    const fullPath = basePath ? `${basePath}/${route.path}`.replace(/\/+/g, '/') : route.path
    if (route.meta?.titleKey) {
      map[fullPath] = route.meta.titleKey
    }
    if (route.children) {
      Object.assign(map, buildTitleKeyMap(route.children, fullPath))
    }
  }
  return map
}

const titleKeyMap = buildTitleKeyMap(asyncRoutes)

function buildRoutes(routes = []) {
  return routes.map((e) => {
    const routeTitleKey = titleKeyMap[e.path] || null
    const route = {
      name: e.name,
      path: e.path,
      component: Layout,
      isHidden: e.is_hidden,
      alwaysShow: e.alwaysShow,
      redirect: e.redirect,
      meta: {
        title: e.name,
        titleKey: routeTitleKey,
        icon: e.icon,
        order: e.order,
        keepAlive: e.keepalive,
      },
      children: [],
    }

    if (e.children && e.children.length > 0) {
      route.children = e.children.map((e_child) => {
        const childPath = `${e.path}/${e_child.path}`.replace(/\/+/g, '/')
        const childTitleKey = titleKeyMap[childPath] || null
        return {
          name: e_child.name,
          path: e_child.path,
          component: vueModules[`/src/views${e_child.component}/index.vue`],
          isHidden: e_child.is_hidden,
          meta: {
            title: e_child.name,
            titleKey: childTitleKey,
            icon: e_child.icon,
            order: e_child.order,
            keepAlive: e_child.keepalive,
          },
        }
      })
    } else {
      route.children.push({
        name: `${e.name}Default`,
        path: '',
        component: vueModules[`/src/views${e.component}/index.vue`],
        isHidden: true,
        meta: {
          title: e.name,
          titleKey: routeTitleKey,
          icon: e.icon,
          order: e.order,
          keepAlive: e.keepalive,
        },
      })
    }

    return route
  })
}

export const usePermissionStore = defineStore('permission', {
  state() {
    return {
      accessRoutes: [],
      accessApis: [],
    }
  },
  getters: {
    routes() {
      return basicRoutes.concat(this.accessRoutes)
    },
    menus() {
      return this.routes.filter((route) => route.name && !route.isHidden)
    },
    apis() {
      return this.accessApis
    },
  },
  actions: {
    async generateRoutes() {
      const res = await api.getUserMenu() // 调用接口获取后端传来的菜单路由
      this.accessRoutes = buildRoutes(res.data) // 处理成前端路由格式
      return this.accessRoutes
    },
    async getAccessApis() {
      const res = await api.getUserApi()
      this.accessApis = res.data
      return this.accessApis
    },
    resetPermission() {
      this.$reset()
    },
  },
})
