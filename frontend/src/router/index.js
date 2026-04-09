import { createRouter, createWebHistory } from 'vue-router'
import MainPage from '@/views/MainPage.vue'
import DocumentPage from '@/views/DocumentPage.vue'
import LoginPage from '@/views/LoginPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'main',
      component: MainPage,
    },
    {
      path: '/doc/:id',
      name: 'doc',
      component: DocumentPage,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
    },
  ],
})

router.beforeEach((to, from, next) => {
  const userName = localStorage.getItem('username')
  
  if (!userName && to.name !== 'login') {
    next({ name: 'login' })
  } else {
    next()
  }
})

export default router
