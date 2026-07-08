import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/books' },
  { path: '/upload', component: () => import('../views/Upload.vue') },
  { path: '/books', component: () => import('../views/BookList.vue') },
  { path: '/compare', component: () => import('../views/Compare.vue') },
  { path: '/books/:id', component: () => import('../views/BookDetail.vue'), props: true },
  { path: '/books/:id/behavior-cards', component: () => import('../views/BehaviorCards.vue'), props: true },
  { path: '/books/:id/dialogue-cards', component: () => import('../views/DialogueCards.vue'), props: true },
  { path: '/books/:id/characters', component: () => import('../views/CharacterView.vue'), props: true },
  { path: '/books/:id/characters/:cid', component: () => import('../views/CharacterView.vue'), props: true },
  { path: '/books/:id/clusters', component: () => import('../views/Clusters.vue'), props: true },
  { path: '/books/:id/rules', component: () => import('../views/RuleCards.vue'), props: true },
  { path: '/books/:id/family', component: () => import('../views/FamilyView.vue'), props: true },
  { path: '/books/:id/read', component: () => import('../views/Reader.vue'), props: true },
  { path: '/books/:id/stats', component: () => import('../views/StatsView.vue'), props: true },
  { path: '/search', component: () => import('../views/SearchView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
