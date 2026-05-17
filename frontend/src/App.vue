<template>
  <AppNavbar v-if="showNavbar" />
  <RouterView />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppNavbar from './components/AppNavbar.vue'

const route = useRoute()

const GUEST_ROUTES = new Set(['login', 'register', 'verify-email', 'forgot-password', 'reset-password'])
const showNavbar = computed(() => !GUEST_ROUTES.has(route.name as string))
</script>
