/**
 * 路由配置
 * 功能描述：定义前端路由，懒加载视图组件
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'TaskList',
    component: () => import('@/views/TaskList.vue'),
    meta: { title: '任务列表' },
  },
  {
    path: '/task/:id',
    name: 'TaskDetail',
    component: () => import('@/views/TaskDetail.vue'),
    meta: { title: '任务详情' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 页面标题更新
router.afterEach((to) => {
  document.title = `${to.meta.title} - 任务调度平台`
})

export default router
