<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { Archive, Copy, ExternalLink, Plus, Trash2 } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { toMessage } from '@/api/client'
import {
  useArchiveResume,
  useCreateResume,
  useDeleteResume,
  useDuplicateResume,
  useResumes
} from '@/queries/resumes'
import { useUiStore } from '@/stores/ui'
import type { Resume } from '@/schemas/resume'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const ui = useUiStore()

const includeArchived = ref(false)
const { data: resumes, isPending } = useResumes(includeArchived)

const createDialog = ref(false)
const newName = ref('')

const create = useCreateResume()
const duplicate = useDuplicateResume()
const archive = useArchiveResume()
const remove = useDeleteResume()

const canCreate = computed(() => newName.value.trim().length > 0)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

function submitCreate() {
  if (!canCreate.value) return
  create.mutate(
    { name: newName.value.trim() },
    {
      onSuccess: (resume) => {
        createDialog.value = false
        newName.value = ''
        ui.resumeId = resume.id
        void router.push(`/resumes/${String(resume.id)}`)
      },
      onError: fail
    }
  )
}

function onDuplicate(resume: Resume) {
  duplicate.mutate(resume.id, {
    onSuccess: () => {
      toast.add({ severity: 'success', summary: 'Копия создана', life: 3000 })
    },
    onError: fail
  })
}

function onArchive(resume: Resume) {
  archive.mutate(resume.id, { onError: fail })
}

function onDelete(resume: Resume) {
  confirm.require({
    header: 'Удалить резюме',
    message: `«${resume.name}» будет удалено вместе с решениями по вакансиям. Отменить нельзя.`,
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger', size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => {
      remove.mutate(resume.id, {
        onSuccess: () => {
          if (ui.resumeId === resume.id) ui.resumeId = null
        },
        onError: fail
      })
    }
  })
}

function openResume(resume: Resume) {
  void router.push(`/resumes/${String(resume.id)}`)
}

const dateFormat = (value: string) => dayjs(value).format('DD.MM.YYYY')
</script>

<template>
  <div>
    <div class="mb-4 flex items-center gap-4">
      <p class="max-w-prose text-[13.5px] leading-relaxed text-slate-600">
        Текст резюме — источник истины для всего приложения: из него собирается выжимка, по нему
        пишутся письма и проверяются факты.
      </p>
      <div class="ml-auto flex shrink-0 items-center gap-3">
        <label class="flex items-center gap-2 text-[13px] text-slate-600">
          <ToggleSwitch v-model="includeArchived" />
          Показывать архив
        </label>
        <Button size="small" label="Новое резюме" @click="createDialog = true">
          <template #icon><Plus class="mr-1.5 size-4" /></template>
        </Button>
      </div>
    </div>

    <DataTable
      :value="resumes ?? []"
      :loading="isPending"
      data-key="id"
      class="overflow-hidden rounded-[14px] border border-slate-200 bg-white text-[13.5px]"
      row-hover
      @row-click="openResume($event.data as Resume)"
    >
      <template #empty>
        <div class="py-10 text-center text-[13.5px] text-slate-500">
          Резюме пока нет. Создайте первое — дальше всё строится вокруг него.
        </div>
      </template>

      <Column field="name" header="Название">
        <template #body="{ data }: { data: Resume }">
          <span class="font-medium text-slate-800">{{ data.name }}</span>
          <Tag
            v-if="data.is_archived"
            value="в архиве"
            severity="secondary"
            class="ml-2 text-[11px]"
          />
        </template>
      </Column>

      <Column header="Текст" class="w-32">
        <template #body="{ data }: { data: Resume }">
          <span v-if="data.raw_text" class="text-slate-600"
            >{{ data.raw_text.length }} символов</span
          >
          <span v-else class="text-amber-700">не вставлен</span>
        </template>
      </Column>

      <Column header="Выжимка" class="w-32">
        <template #body="{ data }: { data: Resume }">
          <span :class="data.digest_json ? 'text-slate-600' : 'text-slate-400'">
            {{ data.digest_json ? 'собрана' : 'нет' }}
          </span>
        </template>
      </Column>

      <Column header="Навыки" class="w-24">
        <template #body="{ data }: { data: Resume }">
          <span class="text-slate-600">{{ data.skills.length }}</span>
        </template>
      </Column>

      <Column header="Пороги" class="w-32">
        <template #body="{ data }: { data: Resume }">
          <span class="text-slate-600">{{ data.min_score }} / {{ data.auto_apply_score }}</span>
        </template>
      </Column>

      <Column header="Создано" class="w-28">
        <template #body="{ data }: { data: Resume }">
          <span class="text-slate-500">{{ dateFormat(data.created_at) }}</span>
        </template>
      </Column>

      <Column class="w-40">
        <template #body="{ data }: { data: Resume }">
          <div class="flex justify-end gap-1" @click.stop>
            <a
              v-if="data.hh_resume_url"
              v-tooltip.top="'Открыть на hh.kz'"
              :href="data.hh_resume_url"
              target="_blank"
              rel="noopener"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-slate-100"
            >
              <ExternalLink class="size-4" />
            </a>
            <button
              v-tooltip.top="'Дублировать'"
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-slate-100"
              @click="onDuplicate(data)"
            >
              <Copy class="size-4" />
            </button>
            <button
              v-if="!data.is_archived"
              v-tooltip.top="'В архив'"
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-slate-100"
              @click="onArchive(data)"
            >
              <Archive class="size-4" />
            </button>
            <button
              v-tooltip.top="'Удалить'"
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
              @click="onDelete(data)"
            >
              <Trash2 class="size-4" />
            </button>
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="createDialog"
      modal
      header="Новое резюме"
      :style="{ width: '26rem', borderRadius: '18px' }"
    >
      <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Название</label>
      <InputText
        v-model="newName"
        autofocus
        fluid
        class="w-full"
        placeholder="Backend Node.js"
        @keyup.enter="submitCreate"
      />
      <p class="mt-1.5 text-[12px] text-slate-500">
        Название видно только вам — по нему выбирается активное резюме в шапке.
      </p>
      <template #footer>
        <Button
          label="Отмена"
          severity="secondary"
          outlined
          size="small"
          @click="createDialog = false"
        />
        <Button
          label="Создать"
          size="small"
          :disabled="!canCreate"
          :loading="create.isPending.value"
          @click="submitCreate"
        />
      </template>
    </Dialog>
  </div>
</template>
