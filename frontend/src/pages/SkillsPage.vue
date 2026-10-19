<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { FileUp, Pencil, Plus, Trash2, Wand2 } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import EmptyState from '@/components/EmptyState.vue'
import FieldError from '@/components/FieldError.vue'
import { useFormErrors } from '@/composables/useFormErrors'
import {
  useCreateSkill,
  useDeleteSkill,
  usePatchSkill,
  useSkills,
  useSkillTargets
} from '@/queries/llm'
import type { Skill, SkillInput } from '@/schemas/llm'

// Локальная модель работает с контекстом 8K токенов, и в него же идут резюме и
// вакансия. Скилл больше этого порога рискует вытеснить данные
const LARGE_SKILL_TOKENS = 3000

const toast = useToast()
const confirm = useConfirm()

const { data: skills, isPending } = useSkills()
const { data: targets } = useSkillTargets()
const createSkill = useCreateSkill()
const patchSkill = usePatchSkill()
const removeSkill = useDeleteSkill()

const titles = computed(
  () => new Map((targets.value ?? []).map((target) => [target.key, target.title]))
)

const dialog = ref(false)
const editing = ref<Skill | null>(null)
const form = reactive({ name: '', content: '', prompt_keys: ['letter'] as string[] })
const fileInput = ref<{ click: () => void } | null>(null)

const { errors, validate, reset } = useFormErrors(() => ({
  name: form.name.trim() ? undefined : 'Укажите название',
  content: form.content.trim() ? undefined : 'Вставьте текст скилла или загрузите файл',
  prompt_keys: form.prompt_keys.length
    ? undefined
    : 'Выберите хотя бы один промпт, иначе скилл ни на что не влияет'
}))

/** Русский текст — примерно 3,5 символа на токен у большинства моделей. */
function tokens(text: string): number {
  return Math.round(text.length / 3.5)
}

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

function openNew() {
  editing.value = null
  Object.assign(form, { name: '', content: '', prompt_keys: ['letter'] })
  reset()
  dialog.value = true
}

function openEdit(skill: Skill) {
  editing.value = skill
  Object.assign(form, {
    name: skill.name,
    content: skill.content,
    prompt_keys: [...skill.prompt_keys]
  })
  reset()
  dialog.value = true
}

/** Имя из frontmatter SKILL.md, чтобы не набирать его руками. */
function nameFromFrontmatter(text: string): string | undefined {
  return /^---[\s\S]*?^name:\s*["']?([^"'\n]+)["']?\s*$/m.exec(text)?.[1]?.trim()
}

// Вставили SKILL.md целиком, а название пустое — берём его из шапки
watch(
  () => form.content,
  (content) => {
    if (!form.name.trim()) form.name = nameFromFrontmatter(content) ?? ''
  }
)

/** Только то, что нужно от <input type="file">: в .vue-файлах нет DOM-глобалов линтера. */
interface FilePicker {
  files: ArrayLike<{ name: string; text: () => Promise<string> }> | null
  value: string
}

async function onFile(event: { target: unknown }) {
  const input = event.target as FilePicker
  const file = input.files?.[0]
  if (!file) return
  const name = form.name.trim()
  form.content = await file.text()
  if (!name) form.name = nameFromFrontmatter(form.content) ?? file.name.replace(/\.md$/i, '')
  // Сброс, чтобы повторный выбор того же файла снова сработал
  input.value = ''
}

function submit() {
  if (!validate()) return
  const payload: SkillInput = {
    name: form.name.trim(),
    content: form.content.trim(),
    prompt_keys: form.prompt_keys
  }
  const done = {
    onSuccess: () => {
      dialog.value = false
      toast.add({ severity: 'success', summary: 'Скилл сохранён', life: 2000 })
    },
    onError: fail
  }
  if (editing.value) patchSkill.mutate({ id: editing.value.id, payload }, done)
  else createSkill.mutate(payload, done)
}

function toggle(skill: Skill) {
  patchSkill.mutate({ id: skill.id, payload: { is_enabled: !skill.is_enabled } }, { onError: fail })
}

function onDelete(skill: Skill) {
  confirm.require({
    header: 'Удалить скилл',
    message: `«${skill.name}» перестанет подставляться в промпты.`,
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger', size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => {
      removeSkill.mutate(skill.id, { onError: fail })
    }
  })
}
</script>

<template>
  <div class="mx-auto w-full max-w-6xl">
    <div class="mb-4 flex items-start gap-4">
      <p class="max-w-prose text-[13px] leading-relaxed text-slate-600">
        Скилл — набор правил стиля, например «пиши без штампов нейросети». Включённый скилл
        дописывается в конец выбранных промптов при каждом вызове модели. Требования к фактам и
        формату ответа в промпте важнее скилла. Сам промпт при этом не меняется.
      </p>
      <Button class="ml-auto shrink-0" size="small" label="Добавить скилл" @click="openNew">
        <template #icon><Plus class="mr-1.5 size-4" /></template>
      </Button>
    </div>

    <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

    <div
      v-else-if="(skills?.length ?? 0) === 0"
      class="rounded-[14px] border border-dashed border-slate-300"
    >
      <EmptyState
        :icon="Wand2"
        title="Скиллов нет"
        hint="Вставьте текст SKILL.md или загрузите файл — например, правила против текста «как от нейросети»."
      />
    </div>

    <div v-else class="space-y-2">
      <article
        v-for="skill in skills"
        :key="skill.id"
        class="rounded-[14px] border border-slate-200 bg-white p-4"
        :class="{ 'opacity-60': !skill.is_enabled }"
      >
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-2">
              <button
                type="button"
                class="text-[14px] font-medium text-slate-800 hover:underline"
                @click="openEdit(skill)"
              >
                {{ skill.name }}
              </button>
              <span
                v-for="key in skill.prompt_keys"
                :key="key"
                class="rounded-full bg-slate-100 px-2 py-0.5 text-[11.5px] text-slate-600"
              >
                {{ titles.get(key) ?? key }}
              </span>
              <span class="text-[12px] text-slate-400">≈ {{ tokens(skill.content) }} токенов</span>
            </div>
            <p
              v-if="tokens(skill.content) > LARGE_SKILL_TOKENS"
              class="mt-1 text-[12px] text-amber-700"
            >
              Большой скилл: локальной модели с контекстом 8K может не хватить места на резюме и
              вакансию. Для промптов с ним лучше выбрать Claude CLI или внешнего провайдера.
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Изменить"
              @click="openEdit(skill)"
            >
              <template #icon><Pencil class="mr-1.5 size-3.5" /></template>
            </Button>
            <ToggleSwitch
              :model-value="skill.is_enabled"
              :aria-label="`Включить скилл ${skill.name}`"
              @update:model-value="toggle(skill)"
            />
            <button
              type="button"
              :aria-label="`Удалить скилл ${skill.name}`"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
              @click="onDelete(skill)"
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
      :header="editing ? 'Скилл' : 'Новый скилл'"
      :style="{ width: '44rem', borderRadius: '18px' }"
    >
      <div class="space-y-3">
        <div>
          <label for="skill-name" class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
            >Название</label
          >
          <InputText
            id="skill-name"
            v-model="form.name"
            :invalid="!!errors.name"
            fluid
            class="w-full"
            size="small"
            placeholder="anti-ai-writing"
          />
          <FieldError :message="errors.name" />
        </div>

        <div>
          <p class="mb-1.5 text-[12.5px] font-medium text-slate-600">Подставлять в промпты</p>
          <div class="flex flex-wrap gap-x-4 gap-y-2">
            <label
              v-for="target in targets ?? []"
              :key="target.key"
              class="flex items-center gap-2 text-[13px] text-slate-700"
            >
              <Checkbox
                v-model="form.prompt_keys"
                :value="target.key"
                :invalid="!!errors.prompt_keys"
              />
              {{ target.title }}
            </label>
          </div>
          <FieldError :message="errors.prompt_keys" />
        </div>

        <div>
          <div class="mb-1.5 flex items-center gap-2">
            <label for="skill-content" class="text-[12.5px] font-medium text-slate-600"
              >Текст скилла</label
            >
            <span class="text-[12px] text-slate-400">≈ {{ tokens(form.content) }} токенов</span>
            <Button
              class="ml-auto"
              size="small"
              severity="secondary"
              text
              label="Загрузить .md"
              @click="fileInput?.click()"
            >
              <template #icon><FileUp class="mr-1.5 size-3.5" /></template>
            </Button>
            <input
              ref="fileInput"
              type="file"
              accept=".md,.txt,text/markdown,text/plain"
              class="hidden"
              @change="onFile"
            />
          </div>
          <Textarea
            id="skill-content"
            v-model="form.content"
            :invalid="!!errors.content"
            class="w-full text-[13px] leading-relaxed"
            rows="16"
            placeholder="Вставьте SKILL.md целиком: шапку --- name / description --- приложение уберёт само"
          />
          <FieldError :message="errors.content" />
        </div>

        <Message v-if="tokens(form.content) > LARGE_SKILL_TOKENS" severity="warn" size="small">
          Скилл большой. Локальная модель с контекстом 8K может обрезать резюме и вакансию — для
          этих промптов лучше назначить Claude CLI или внешнего провайдера.
        </Message>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined size="small" @click="dialog = false" />
        <Button
          label="Сохранить"
          size="small"
          :loading="createSkill.isPending.value || patchSkill.isPending.value"
          @click="submit"
        />
      </template>
    </Dialog>
  </div>
</template>
