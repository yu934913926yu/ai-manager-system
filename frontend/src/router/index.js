import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

// 路由组件懒加载
const Layout = () => import('@/layout/index.vue')
const Login = () => import('@/views/Login.vue')
const Dashboard = () => import('@/views/Dashboard.vue')
const Projects = () => import('@/views/Projects.vue')
const ProjectDetail = () => import('@/views/ProjectDetail.vue')
const Tasks = () => import('@/views/Tasks.vue')
const Suppliers = () => import('@/views/Suppliers.vue')
const Users = () => import('@/views/Users.vue')
const Reports = () => import('@/views/Reports.vue')
const Settings = () => import('@/views/Settings.vue')
const NotFound = () => import('@/views/404.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { 
      title: '登录', 
      requiresAuth: false,
      hideInMenu: true
    }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: { 
          title: '工作台',
          icon: 'Monitor',
          affix: true
        }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: Projects,
        meta: { 
          title: '项目管理',
          icon: 'FolderOpened',
          permissions: ['project:read']
        }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: ProjectDetail,
        meta: { 
          title: '项目详情',
          hideInMenu: true,
          permissions: ['project:read']
        }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: Tasks,
        meta: { 
          title: '任务管理',
          icon: 'List',
          permissions: ['task:read']
        }
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: Suppliers,
        meta: { 
          title: '供应商管理',
          icon: 'OfficeBuilding',
          permissions: ['supplier:read']
        }
      },
      {
        path: 'users',
        name: 'Users',
        component: Users,
        meta: { 
          title: '用户管理',
          icon: 'User',
          permissions: ['user:read']
        }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: Reports,
        meta: { 
          title: '数据报告',
          icon: 'TrendCharts',
          permissions: ['report:view']
        }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings,
        meta: { 
          title: '系统设置',
          icon: 'Setting',
          permissions: ['system:config']
        }
      }
    ]
  },
  {
    path: '/404',
    name: '404',
    component: NotFound,
    meta: { 
      title: '页面不存在',
      hideInMenu: true,
      requiresAuth: false
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - AI管理系统` : 'AI管理系统'
  
  // 登录页面直接放行
  if (to.path === '/login') {
    if (userStore.isLoggedIn) {
      next('/')
    } else {
      next()
    }
    return
  }
  
  // 检查是否需要登录
  if (to.meta.requiresAuth !== false) {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录')
      next('/login')
      return
    }
    
    // 检查权限
    if (to.meta.permissions && to.meta.permissions.length > 0) {
      const hasPermission = userStore.hasPermissions(to.meta.permissions)
      if (!hasPermission) {
        ElMessage.error('权限不足')
        next('/dashboard')
        return
      }
    }
  }
  
  next()
})

router.afterEach((to, from) => {
  console.log(`路由跳转: ${from.path} -> ${to.path}`)
})

export default router