<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { Pencil, Play, Plus, Search, Trash2 } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { createSearchProfile, deleteSearchProfile, patchSearchProfile } from '@/api/catalogs'
import EmptyState from '@/components/EmptyState.vue'
import FieldError from '@/components/FieldError.vue'
import { useFormErrors } from '@/composables/useFormErrors'
import { useBotControls, useMutate, useSearchProfiles } from '@/queries'
import { useUiStore } from '@/stores/ui'
import type { SearchProfile } from '@/api/catalogs'

const EXPERIENCE = [
  { value: 'noExperience', label: 'Нет опыта' },
  { value: 'between1And3', label: '1–3 года' },
  { value: 'between3And6', label: '3–6 лет' },
  { value: 'moreThan6', label: 'Более 6 лет' }
]

const REMOTE_MODES = [
  { value: 'REMOTE_ONLY', label: 'Только удалённо' },
  { value: 'REMOTE_OR_HYBRID', label: 'Удалённо или гибрид' },
  { value: 'ANY', label: 'Любой' }
]

// Коды регионов hh.kz
const AREAS = [
  { value: '40', label: 'Казахстан' },
  { value: '160', label: 'Алматы' },
  { value: '159', label: 'Астана' },
  { value: '177', label: 'Усть-Каменогорск' },
  { value: '163', label: 'Караганда' },
  { value: '168', label: 'Шымкент' }
]

const toast = useToast()
const confirm = useConfirm()
const ui = useUiStore()
const { start } = useBotControls()

const { data: profiles, isPending } = useSearchProfiles(() => ui.resumeId)

const dialog = ref(false)
const editing = ref<SearchProfile | null>(null)
const form = reactive({
  name: '',
  queries: [] as string[],
  queryDraft: '',
  remote_mode: 'ANY',
  min_salary: null as number | null,
  currency: 'KZT',
  allow_unknown_salary: true,
  experience_levels: [] as string[],
  areas: ['40'] as string[],
  max_age_days: 7 as number | null,
  include_keywords: [] as string[],
  includeDraft: '',
  exclude_keywords: [] as string[],
  excludeDraft: '',
  max_vacancies_per_run: 25,
  use_recommendations: false,
  enabled: true,
  priority: 1
})

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

const create = useMutate(['search-profiles'], createSearchProfile)
const patch = useMutate(
  ['search-profiles'],
  (args: { id: number; payload: Record<string, unknown> }) =>
    patchSearchProfile(args.id, args.payload)
)
const remove = useMutate(['search-profiles'], deleteSearchProfile)

function openNew() {
  editing.value = null
  Object.assign(form, {
    name: '',
    queries: [],
    queryDraft: '',
    remote_mode: 'ANY',
    min_salary: null,
    currency: 'KZT',
    allow_unknown_salary: true,
    experience_levels: [],
    areas: ['40'],
    max_age_days: 7,
    include_keywords: [],
    includeDraft: '',
    exclude_keywords: [],
    excludeDraft: '',
    max_vacancies_per_run: 25,
    use_recommendations: false,
    enabled: true,
    priority: 1
  })
  resetErrors()
  dialog.value = true
}

function openEdit(profile: SearchProfile) {
  editing.value = profile
  Object.assign(form, {
    name: profile.name,
    queries: profile.queries.map((query) => query.text),
    queryDraft: '',
    remote_mode: profile.remote_mode,
    min_salary: profile.min_salary,
    currency: profile.currency,
    allow_unknown_salary: profile.allow_unknown_salary,
    experience_levels: profile.experience_levels.map(String),
    areas: profile.areas.map(String),
    max_age_days: profile.max_age_days,
    include_keywords: profile.include_keywords.map(String),
    includeDraft: '',
    exclude_keywords: profile.exclude_keywords.map(String),
    excludeDraft: '',
    max_vacancies_per_run: profile.max_vacancies_per_run,
    use_recommendations: profile.use_recommendations,
    enabled: profile.enabled,
    priority: profile.priority
  })
  resetErrors()
  dialog.value = true
}

function addTo(
  list: 'queries' | 'include_keywords' | 'exclude_keywords',
  draft: 'queryDraft' | 'includeDraft' | 'excludeDraft'
) {
  const value = form[draft].trim()
  if (!value || form[list].includes(value)) return
  form[list] = [...form[list], value]
  form[draft] = ''
}

function removeFrom(list: 'queries' | 'include_keywords' | 'exclude_keywords', value: string) {
  form[list] = form[list].filter((item) => item !== value)
}

const {
  errors,
  validate,
  reset: resetErrors
} = useFormErrors(() => ({
  name: form.name.trim() ? undefined : 'Укажите название профиля',
  // Лента рекомендаций HH сама по себе источник вакансий, запросы тогда не обязательны
  queries:
    form.queries.length || form.use_recommendations
      ? undefined
      : 'Добавьте хотя бы один поисковый запрос или включите рекомендации HH',
  resume:
    ui.resumeId === null ? 'Выберите резюме в шапке — профиль привязывается к нему' : undefined
}))

function submit() {
  // Вписанное, но не добавленное по Enter — частая причина «пустого» профиля
  addTo('queries', 'queryDraft')
  addTo('include_keywords', 'includeDraft')
  addTo('exclude_keywords', 'excludeDraft')
  if (!validate() || ui.resumeId === null) return
  const payload = {
    name: form.name.trim(),
    queries: form.queries,
    remote_mode: form.remote_mode,
    min_salary: form.min_salary,
    currency: form.currency,
    allow_unknown_salary: form.allow_unknown_salary,
    experience_levels: form.experience_levels,
    areas: form.areas,
    max_age_days: form.max_age_days,
    include_keywords: form.include_keywords,
    exclude_keywords: form.exclude_keywords,
    max_vacancies_per_run: form.max_vacancies_per_run,
    use_recommendations: form.use_recommendations,
    enabled: form.enabled,
    priority: form.priority
  }
  const done = {
    onSuccess: () => {
      dialog.value = false
    },
    onError: fail
  }
  if (editing.value) patch.mutate({ id: editing.value.id, payload }, done)
  else create.mutate({ ...payload, resume_id: ui.resumeId }, done)
}

function runProfile(profile: SearchProfile) {
  if (ui.resumeId === null) return
  start.mutate(
    {
      resume_id: ui.resumeId,
      mode: ui.botMode,
      runtime_mode: ui.runtimeMode,
      search_profile_id: profile.id
    },
    {
      onSuccess: () => {
        toast.add({ severity: 'success', summary: 'Прогон запущен', life: 3000 })
      },
      onError: fail
    }
  )
}

function confirmDelete(profile: SearchProfile) {
  confirm.require({
    header: 'Удалить профиль',
    message: `«${profile.name}» и его запросы будут удалены. Найденные вакансии останутся.`,
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger', size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => {
      remove.mutate(profile.id, { onError: fail })
    }
  })
}

const areaLabel = (codes: unknown[]) =>
  codes
    .map((code) => AREAS.find((area) => area.value === String(code))?.label ?? String(code))
    .join(', ')
</script>

<template>
  <div class="mx-auto w-full max-w-7xl">
    <div class="mb-4 flex items-start gap-4">
      <p class="max-w-prose text-[13px] leading-relaxed text-slate-600">
        Профиль — это набор поисковых запросов и условий отбора. Одна вакансия, найденная тремя
        запросами, сохранится один раз.
      </p>
      <Button class="ml-auto shrink-0" size="small" label="Новый профиль" @click="openNew">
        <template #icon><Plus class="mr-1.5 size-4" /></template>
      </Button>
    </div>

    <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

    <div
      v-else-if="(profiles?.length ?? 0) === 0"
      class="rounded-[14px] border border-dashed border-slate-300"
    >
      <EmptyState
        :icon="Search"
        title="Профилей нет"
        hint="Без поискового профиля прогон запустить нельзя — боту неоткуда брать вакансии."
      />
    </div>

    <div v-else class="space-y-2">
      <article
        v-for="profile in profiles"
        :key="profile.id"
        class="rounded-[14px] border border-slate-200 bg-white p-4"
      >
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="text-[14px] font-medium text-slate-800 hover:underline"
                @click="openEdit(profile)"
              >
                {{ profile.name }}
              </button>
              <span
                v-if="!profile.enabled"
                class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500"
              >
                выключен
              </span>
            </div>

            <div class="mt-1.5 flex flex-wrap gap-1.5">
              <span
                v-if="profile.use_recommendations"
                class="rounded-full bg-teal-700/10 px-2.5 py-0.5 text-[12px] text-teal-900"
              >
                Рекомендации HH «Для вас»
              </span>
              <span
                v-for="query in profile.queries"
                :key="query.id"
                class="rounded-full bg-slate-100 px-2.5 py-0.5 text-[12px] text-slate-700"
              >
                {{ query.text }}
              </span>
            </div>

            <p class="mt-2 text-[12.5px] text-slate-500">
              {{ REMOTE_MODES.find((m) => m.value === profile.remote_mode)?.label }}
              <template v-if="profile.min_salary">
                · от {{ profile.min_salary.toLocaleString('ru-RU') }} {{ profile.currency }}
              </template>
              <template v-if="profile.max_age_days">
                · за {{ profile.max_age_days }} дней
              </template>
              · {{ areaLabel(profile.areas) }} · лимит {{ profile.max_vacancies_per_run }}
            </p>
            <p v-if="profile.exclude_keywords.length" class="mt-1 text-[12.5px] text-slate-500">
              Стоп-слова: {{ profile.exclude_keywords.join(', ') }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-1.5">
            <ToggleSwitch
              :model-value="profile.enabled"
              @update:model-value="
                patch.mutate(
                  { id: profile.id, payload: { enabled: !profile.enabled } },
                  { onError: fail }
                )
              "
            />
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Изменить"
              @click="openEdit(profile)"
            >
              <template #icon><Pencil class="mr-1.5 size-3.5" /></template>
            </Button>
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Запустить"
              :loading="start.isPending.value"
              @click="runProfile(profile)"
            >
              <template #icon><Play class="mr-1.5 size-3.5" /></template>
            </Button>
            <button
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
              @click="confirmDelete(profile)"
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
      :header="editing ? 'Профиль поиска' : 'Новый профиль поиска'"
      :style="{ width: '34rem', borderRadius: '18px' }"
    >
      <div class="space-y-3">
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Название</label>
          <InputText
            v-model="form.name"
            :invalid="!!errors.name"
            fluid
            class="w-full"
            placeholder="Backend Remote"
          />
          <FieldError :message="errors.name" />
        </div>

        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
            Поисковые запросы
          </label>
          <div class="mb-1.5 flex flex-wrap gap-1.5">
            <span
              v-for="query in form.queries"
              :key="query"
              class="flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[12.5px] text-slate-700"
            >
              {{ query }}
              <button
                type="button"
                class="text-slate-400 hover:text-red-600"
                @click="removeFrom('queries', query)"
              >
                ×
              </button>
            </span>
          </div>
          <InputText
            v-model="form.queryDraft"
            :invalid="!!errors.queries"
            size="small"
            fluid
            class="w-full"
            placeholder="Node.js Developer, затем Enter"
            @keyup.enter="addTo('queries', 'queryDraft')"
          />
          <FieldError :message="errors.queries" />
          <FieldError :message="errors.resume" />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
              Формат работы
            </label>
            <Select
              v-model="form.remote_mode"
              :options="REMOTE_MODES"
              option-label="label"
              option-value="value"
              fluid
              class="w-full"
              size="small"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Регионы</label>
            <MultiSelect
              v-model="form.areas"
              :options="AREAS"
              option-label="label"
              option-value="value"
              fluid
              class="w-full"
              size="small"
              :max-selected-labels="2"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
              Минимальная зарплата
            </label>
            <InputNumber v-model="form.min_salary" fluid class="w-full" size="small" :min="0" />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Опыт</label>
            <MultiSelect
              v-model="form.experience_levels"
              :options="EXPERIENCE"
              option-label="label"
              option-value="value"
              fluid
              class="w-full"
              size="small"
              :max-selected-labels="1"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
              Свежесть, дней
            </label>
            <InputNumber
              v-model="form.max_age_days"
              fluid
              class="w-full"
              size="small"
              :min="1"
              :max="30"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
              Лимит за прогон
            </label>
            <InputNumber
              v-model="form.max_vacancies_per_run"
              fluid
              class="w-full"
              size="small"
              :min="1"
              :max="200"
            />
          </div>
        </div>

        <label class="flex items-center gap-2 text-[13px] text-slate-700">
          <ToggleSwitch v-model="form.allow_unknown_salary" />
          Учитывать вакансии без указанной зарплаты
        </label>

        <div>
          <label class="flex items-center gap-2 text-[13px] text-slate-700">
            <ToggleSwitch v-model="form.use_recommendations" />
            Брать вакансии из рекомендаций HH «Для вас»
          </label>
          <p class="mt-1 pl-12 text-[12px] text-slate-500">
            Лента, которую HH подбирает под ваше резюме. Нужна ссылка на резюме hh.kz в разделе «Мои
            резюме». Фильтры профиля применяются и к ней.
          </p>
        </div>

        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Стоп-слова</label>
          <div class="mb-1.5 flex flex-wrap gap-1.5">
            <span
              v-for="word in form.exclude_keywords"
              :key="word"
              class="flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-[12.5px] text-red-900"
            >
              {{ word }}
              <button
                type="button"
                class="text-red-400 hover:text-red-700"
                @click="removeFrom('exclude_keywords', word)"
              >
                ×
              </button>
            </span>
          </div>
          <InputText
            v-model="form.excludeDraft"
            size="small"
            fluid
            class="w-full"
            placeholder="1С, Bitrix, WordPress — по одному, Enter"
            @keyup.enter="addTo('exclude_keywords', 'excludeDraft')"
          />
        </div>

        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">
            Обязательные слова
          </label>
          <div class="mb-1.5 flex flex-wrap gap-1.5">
            <span
              v-for="word in form.include_keywords"
              :key="word"
              class="flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-[12.5px] text-slate-700"
            >
              {{ word }}
              <button
                type="button"
                class="text-slate-400 hover:text-red-600"
                @click="removeFrom('include_keywords', word)"
              >
                ×
              </button>
            </span>
          </div>
          <InputText
            v-model="form.includeDraft"
            size="small"
            fluid
            class="w-full"
            placeholder="достаточно одного совпадения"
            @keyup.enter="addTo('include_keywords', 'includeDraft')"
          />
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
