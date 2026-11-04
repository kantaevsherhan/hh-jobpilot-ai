<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { Mail, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { createLetterExample, deleteLetterExample, patchLetterExample } from '@/api/catalogs'
import EmptyState from '@/components/EmptyState.vue'
import FieldError from '@/components/FieldError.vue'
import { useFormErrors } from '@/composables/useFormErrors'
import { useLetterExamples, useMutate } from '@/queries'
import { useUiStore } from '@/stores/ui'
import type { LetterExample } from '@/api/catalogs'

const CATEGORIES = ['Backend', 'Frontend', 'Fullstack', 'Go', 'Стартап', 'Энтерпрайз', 'Общий']
const TONES = ['Нейтральный', 'Дружелюбный', 'Строгий', 'Технический']

const toast = useToast()
const ui = useUiStore()
const { data: examples, isPending } = useLetterExamples(() => ui.resumeId)

const dialog = ref(false)
const editing = ref<LetterExample | null>(null)
const form = reactive({
  name: '',
  category: 'Общий',
  tone: 'Нейтральный',
  content: '',
  is_preferred: false
})

const { errors, validate, reset } = useFormErrors(() => ({
  name: form.name.trim() ? undefined : 'Укажите название',
  content: form.content.trim() ? undefined : 'Вставьте текст письма'
}))

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

const create = useMutate(['letter-examples'], createLetterExample)
const patch = useMutate(
  ['letter-examples'],
  (args: { id: number; payload: Record<string, unknown> }) =>
    patchLetterExample(args.id, args.payload)
)
const remove = useMutate(['letter-examples'], deleteLetterExample)

function openNew() {
  editing.value = null
  Object.assign(form, {
    name: '',
    category: 'Общий',
    tone: 'Нейтральный',
    content: '',
    is_preferred: false
  })
  reset()
  dialog.value = true
}

function openEdit(example: LetterExample) {
  editing.value = example
  Object.assign(form, {
    name: example.name,
    category: example.category,
    tone: example.tone,
    content: example.content,
    is_preferred: example.is_preferred
  })
  reset()
  dialog.value = true
}

function submit() {
  if (!validate()) return
  const payload = { ...form, name: form.name.trim(), content: form.content.trim() }
  const done = {
    onSuccess: () => {
      dialog.value = false
    },
    onError: fail
  }
  if (editing.value) patch.mutate({ id: editing.value.id, payload }, done)
  else create.mutate({ ...payload, resume_id: ui.resumeId }, done)
}
</script>

<template>
  <div class="mx-auto w-full max-w-6xl">
    <div class="mb-4 flex flex-col items-start gap-4 md:flex-row">
      <p class="max-w-prose text-[13px] leading-relaxed text-slate-600">
        Модель выбирает до трёх активных примеров по названию и описанию вакансии. Назовите свой
        пример по профессии или отметьте его предпочтительным. Примеры задают тон и структуру, а
        факты для письма берутся из вашего резюме.
      </p>
      <Button class="shrink-0 md:ml-auto" size="small" label="Добавить пример" @click="openNew">
        <template #icon><Plus class="mr-1.5 size-4" /></template>
      </Button>
    </div>

    <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

    <div
      v-else-if="(examples?.length ?? 0) === 0"
      class="rounded-[14px] border border-dashed border-slate-300"
    >
      <EmptyState
        :icon="Mail"
        title="Примеров нет"
        hint="Без них модель пишет усреднённо. Достаточно одного письма, которое вам самим нравится."
      />
    </div>

    <div v-else class="space-y-2">
      <article
        v-for="example in examples"
        :key="example.id"
        class="rounded-[14px] border border-slate-200 bg-white p-4"
      >
        <div class="flex flex-col items-start gap-3 md:flex-row">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-2">
              <button
                type="button"
                class="text-[14px] font-medium text-slate-800 hover:underline"
                @click="openEdit(example)"
              >
                {{ example.name }}
              </button>
              <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11.5px] text-slate-600">
                {{ example.category }}
              </span>
              <span class="text-[12px] text-slate-500">{{ example.tone }}</span>
              <span v-if="example.is_preferred" class="text-[12px] font-medium text-teal-700">
                Предпочтительный
              </span>
              <span class="text-[12px] text-slate-400">{{ example.content.length }} симв.</span>
            </div>
            <p class="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-slate-600">
              {{ example.content }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Изменить"
              @click="openEdit(example)"
            >
              <template #icon><Pencil class="mr-1.5 size-3.5" /></template>
            </Button>
            <ToggleSwitch
              :model-value="example.is_active"
              :aria-label="`Использовать пример «${example.name}»`"
              @update:model-value="
                patch.mutate(
                  { id: example.id, payload: { is_active: !example.is_active } },
                  { onError: fail }
                )
              "
            />
            <button
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
              :aria-label="`Удалить пример «${example.name}»`"
              @click="remove.mutate(example.id, { onError: fail })"
            >
              <Trash2 class="size-4" />
            </button>
          </div>
        </div>
      </article>
    </div>

    <Dialog
      v-model:visible="dialog"
      modal
      :header="editing ? 'Пример письма' : 'Новый пример'"
      class="w-[min(38rem,calc(100vw-2rem))] rounded-[18px]"
    >
      <div class="space-y-3">
        <div class="grid gap-3 sm:grid-cols-3">
          <div>
            <label
              for="letter-example-name"
              class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
              >Название</label
            >
            <InputText
              id="letter-example-name"
              v-model="form.name"
              :invalid="!!errors.name"
              fluid
              class="w-full"
              size="small"
            />
            <FieldError :message="errors.name" />
          </div>
          <div>
            <label
              for="letter-example-category"
              class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
              >Категория</label
            >
            <Select
              v-model="form.category"
              input-id="letter-example-category"
              :options="CATEGORIES"
              fluid
              class="w-full"
              size="small"
            />
          </div>
          <div>
            <label
              for="letter-example-tone"
              class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
              >Тон</label
            >
            <Select
              v-model="form.tone"
              input-id="letter-example-tone"
              :options="TONES"
              fluid
              class="w-full"
              size="small"
            />
          </div>
        </div>
        <div>
          <label
            for="letter-example-content"
            class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
            >Текст письма</label
          >
          <Textarea
            id="letter-example-content"
            v-model="form.content"
            :invalid="!!errors.content"
            class="w-full text-[13px] leading-relaxed"
            rows="14"
          />
          <FieldError :message="errors.content" />
        </div>
        <div class="flex items-center gap-3">
          <ToggleSwitch v-model="form.is_preferred" input-id="letter-example-preferred" />
          <div>
            <label for="letter-example-preferred" class="block text-[13px] font-medium">
              Предпочтительный
            </label>
            <p class="text-[12px] text-slate-600">
              Учитывать пример даже без совпадений с вакансией.
            </p>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined size="small" @click="dialog = false" />
        <Button
          label="Сохранить"
          size="small"
          :loading="create.isPending.value || patch.isPending.value"
          @click="submit"
        />
      </template>
    </Dialog>
  </div>
</template>
