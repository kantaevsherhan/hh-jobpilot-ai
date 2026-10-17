<script setup lang="ts">
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import AppHeader from '@/layouts/AppHeader.vue'
import AppSidebar from '@/layouts/AppSidebar.vue'
</script>

<template>
  <div class="flex h-full bg-white text-slate-800">
    <AppSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <AppHeader />
      <main class="min-w-0 flex-1 overflow-y-auto bg-slate-50/60 px-4 py-4 sm:px-6 lg:px-8 lg:py-6">
        <div class="mx-auto w-full max-w-[1600px]">
          <RouterView />
        </div>
      </main>
    </div>
    <Toast position="bottom-right" />
    <ConfirmDialog />
  </div>
</template>
