<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { Database, Download } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { exportUrl } from '@/api/settings'
import { useBackup } from '@/queries'
import { useUiStore } from '@/stores/ui'

const toast = useToast()
const ui = useUiStore()
const backup = useBackup()
const lastPath = ref<string | null>(null)

function makeBackup() {
  backup.mutate(undefined, {
    onSuccess: (result) => {
      lastPath.value = result.path
      toast.add({
        severity: 'success',
        summary: 'Копия создана',
        detail: `${String(Math.round(result.size_bytes / 1024))} КБ`,
        life: 5000
      })
    },
    onError: (error: unknown) => {
      toast.add({
        severity: 'error',
        summary: 'Не получилось',
        detail: toMessage(error),
        life: 6000
      })
    }
  })
}
</script>

<template>
  <div class="mx-auto w-full max-w-5xl space-y-4">
    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="flex items-start gap-3">
        <Database class="mt-0.5 size-5 shrink-0 text-slate-400" />
        <div class="min-w-0 flex-1">
          <h3 class="text-[13.5px] font-semibold text-slate-800">Резервная копия базы</h3>
          <p class="mt-1 max-w-prose text-[12.5px] leading-relaxed text-slate-500">
            Копия файла базы кладётся в data/backups с датой в имени. Там вся история: вакансии,
            решения, письма и отклики. Ключи внешних провайдеров в копии зашифрованы — ключ
            шифрования хранится отдельно и в копию не попадает.
          </p>
          <p v-if="lastPath" class="mt-2 font-mono text-[12px] break-all text-slate-600">
            {{ lastPath }}
          </p>
        </div>
        <Button
          size="small"
          severity="secondary"
          outlined
          label="Создать"
          :loading="backup.isPending.value"
          @click="makeBackup"
        />
      </div>
    </section>

    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <h3 class="text-[13.5px] font-semibold text-slate-800">Выгрузки</h3>
      <p class="mt-1 mb-3 text-[12.5px] text-slate-500">
        CSV с разделителем «;» и BOM — Excel открывает кириллицу как надо.
      </p>
      <div v-if="ui.resumeId === null" class="text-[13px] text-slate-500">
        Выберите резюме в шапке.
      </div>
      <div v-else class="flex gap-2">
        <a :href="exportUrl('vacancies', ui.resumeId)" download>
          <Button size="small" severity="secondary" outlined label="Вакансии">
            <template #icon><Download class="mr-1.5 size-3.5" /></template>
          </Button>
        </a>
        <a :href="exportUrl('applications', ui.resumeId)" download>
          <Button size="small" severity="secondary" outlined label="Отклики">
            <template #icon><Download class="mr-1.5 size-3.5" /></template>
          </Button>
        </a>
      </div>
    </section>
  </div>
</template>
