<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { ArrowLeft, ExternalLink, Plus, Save, Sparkles, X } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { toMessage } from '@/api/client'
import { usePatchResume, useRebuildDigest, useResume, useSaveSkills } from '@/queries/resumes'
import type { Skill } from '@/schemas/resume'

const LANGUAGES = [
  { code: 'ru', label: 'Русский' },
  { code: 'kk', label: 'Қазақша' },
  { code: 'en', label: 'English' }
]

const route = useRoute()
const router = useRouter()
const toast = useToast()

const resumeId = computed(() => Number(route.params.id))
const { data: resume, isPending } = useResume(resumeId)
const patch = usePatchResume()
const saveSkills = useSaveSkills()
const rebuildDigest = useRebuildDigest()

const form = ref({
  name: '',
  raw_text: '',
  allowed_facts: '',
  hh_resume_url: '',
  letter_languages: ['ru'] as string[],
  min_score: 75,
  auto_apply_score: 90
})
const skills = ref<Skill[]>([])
const newSkill = ref('')

watch(
  resume,
  (value) => {
    if (!value) return
    form.value = {
      name: value.name,
      raw_text: value.raw_text,
      allowed_facts: value.allowed_facts,
      hh_resume_url: value.hh_resume_url ?? '',
      letter_languages: [...value.letter_languages],
      min_score: value.min_score,
      auto_apply_score: value.auto_apply_score
    }
    skills.value = [...value.skills]
  },
  { immediate: true }
)

const factsCount = computed(
  () => form.value.allowed_facts.split('\n').filter((line) => line.trim().length > 0).length
)

// Порог автоотклика ниже порога отбора означал бы, что вакансия
// одновременно отклонена и отправлена — такое сохранять нельзя
const thresholdsValid = computed(() => form.value.auto_apply_score >= form.value.min_score)

function toggleLanguage(code: string) {
  const list = form.value.letter_languages
  form.value.letter_languages = list.includes(code)
    ? list.filter((item) => item !== code)
    : [...list, code]
}

function addSkill() {
  const name = newSkill.value.trim()
  if (!name || skills.value.some((s) => s.name.toLowerCase() === name.toLowerCase())) return
  skills.value = [...skills.value, { id: 0, name, is_core: false }]
  newSkill.value = ''
}

function removeSkill(name: string) {
  skills.value = skills.value.filter((s) => s.name !== name)
}

function toggleCore(name: string) {
  skills.value = skills.value.map((s) => (s.name === name ? { ...s, is_core: !s.is_core } : s))
}

function save() {
  if (!thresholdsValid.value) return
  patch.mutate(
    {
      id: resumeId.value,
      payload: { ...form.value, hh_resume_url: form.value.hh_resume_url.trim() || null }
    },
    {
      onSuccess: () => {
        saveSkills.mutate(
          { id: resumeId.value, skills: skills.value },
          {
            onSuccess: () => {
              toast.add({ severity: 'success', summary: 'Сохранено', life: 2500 })
            },
            onError: onFail
          }
        )
      },
      onError: onFail
    }
  )
}

function rebuild() {
  rebuildDigest.mutate(resumeId.value, {
    onSuccess: () => {
      toast.add({ severity: 'success', summary: 'Выжимка собрана', life: 3000 })
    },
    onError: onFail
  })
}

function onFail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не сохранилось', detail: toMessage(error), life: 6000 })
}
</script>

<template>
  <div v-if="isPending" class="text-[13.5px] text-slate-500">Загружается…</div>

  <div v-else-if="resume" class="max-w-4xl pb-10">
    <div class="mb-5 flex items-center gap-3">
      <button
        type="button"
        class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-slate-100"
        @click="router.push('/resumes')"
      >
        <ArrowLeft class="size-4" />
      </button>
      <h2 class="text-lg font-semibold tracking-tight text-slate-900">{{ resume.name }}</h2>
      <a
        v-if="resume.hh_resume_url"
        :href="resume.hh_resume_url"
        target="_blank"
        rel="noopener"
        class="flex items-center gap-1 text-[13px] text-teal-700 no-underline hover:underline"
      >
        <ExternalLink class="size-3.5" />
        на hh.kz
      </a>
      <Button
        class="ml-auto"
        size="small"
        label="Сохранить"
        :disabled="!thresholdsValid"
        :loading="patch.isPending.value || saveSkills.isPending.value"
        @click="save"
      >
        <template #icon><Save class="mr-1.5 size-4" /></template>
      </Button>
    </div>

    <section class="rounded-[14px] border border-slate-200 bg-white p-5">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Название</label>
          <InputText v-model="form.name" fluid class="w-full" />
        </div>
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
            >Ссылка на резюме HH</label
          >
          <InputText
            v-model="form.hh_resume_url"
            fluid
            class="w-full"
            placeholder="https://hh.kz/resume/…"
          />
        </div>
      </div>

      <div class="mt-4">
        <div class="mb-1.5 flex items-baseline gap-2">
          <label class="text-[12.5px] font-medium text-slate-600">Текст резюме</label>
          <span class="text-[12px] text-slate-400">{{ form.raw_text.length }} символов</span>
        </div>
        <Textarea
          v-model="form.raw_text"
          class="w-full font-mono text-[12.5px] leading-relaxed"
          rows="14"
          placeholder="Вставьте текст резюме с hh.kz как есть"
        />
      </div>

      <div class="mt-4">
        <div class="mb-1.5 flex items-baseline gap-2">
          <label class="text-[12.5px] font-medium text-slate-600">Allowed Facts</label>
          <span class="text-[12px] text-slate-400">по факту на строку · {{ factsCount }}</span>
        </div>
        <Textarea
          v-model="form.allowed_facts"
          class="w-full text-[13px] leading-relaxed"
          rows="5"
          placeholder="Готов к переезду в Алматы&#10;Желаемая зарплата 900 000 KZT"
        />
        <p class="mt-1.5 text-[12px] leading-relaxed text-slate-500">
          Всё, чего нет в тексте резюме, но что разрешено писать в письмах. За пределы этих двух
          источников модель выходить не должна.
        </p>
      </div>
    </section>

    <section class="mt-4 grid grid-cols-[1fr_260px] gap-4">
      <div class="rounded-[14px] border border-slate-200 bg-white p-5">
        <div class="mb-2 flex items-baseline gap-2">
          <h3 class="text-[13.5px] font-semibold text-slate-800">Навыки</h3>
          <span class="text-[12px] text-slate-400">клик по чипу — ключевой навык</span>
        </div>
        <div class="flex flex-wrap items-center gap-1.5">
          <Chip
            v-for="skill in skills"
            :key="skill.name"
            class="cursor-pointer text-[12.5px]"
            :class="skill.is_core ? 'bg-teal-700/12 font-medium text-teal-900' : ''"
            @click="toggleCore(skill.name)"
          >
            {{ skill.name }}
            <button
              type="button"
              class="ml-1 text-slate-400 hover:text-red-600"
              @click.stop="removeSkill(skill.name)"
            >
              <X class="size-3" />
            </button>
          </Chip>
          <span v-if="skills.length === 0" class="text-[13px] text-slate-400">
            Пусто. Заполнится из выжимки в фазе 2 или добавьте руками.
          </span>
        </div>
        <div class="mt-3 flex gap-2">
          <InputText
            v-model="newSkill"
            size="small"
            class="w-48"
            placeholder="TypeScript"
            @keyup.enter="addSkill"
          />
          <Button size="small" severity="secondary" outlined label="Добавить" @click="addSkill">
            <template #icon><Plus class="mr-1.5 size-3.5" /></template>
          </Button>
        </div>
      </div>

      <div class="rounded-[14px] border border-slate-200 bg-white p-5">
        <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Пороги оценки</h3>
        <label class="mb-1 block text-[12.5px] text-slate-600">Ниже — отклонить</label>
        <InputNumber
          v-model="form.min_score"
          :min="0"
          :max="100"
          show-buttons
          size="small"
          fluid
          class="w-full"
        />
        <label class="mt-3 mb-1 block text-[12.5px] text-slate-600">Выше — можно откликаться</label>
        <InputNumber
          v-model="form.auto_apply_score"
          :min="0"
          :max="100"
          show-buttons
          size="small"
          fluid
          class="w-full"
        />
        <Message v-if="!thresholdsValid" severity="error" size="small" class="mt-3 text-[12px]">
          Порог автоотклика не может быть ниже порога отбора.
        </Message>
      </div>
    </section>

    <section class="mt-4 grid grid-cols-[260px_1fr] gap-4">
      <div class="rounded-[14px] border border-slate-200 bg-white p-5">
        <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Языки писем</h3>
        <label
          v-for="lang in LANGUAGES"
          :key="lang.code"
          class="mb-2 flex cursor-pointer items-center gap-2 text-[13px] text-slate-700"
        >
          <input
            type="checkbox"
            class="size-4 accent-teal-700"
            :checked="form.letter_languages.includes(lang.code)"
            @change="toggleLanguage(lang.code)"
          />
          {{ lang.label }}
        </label>
      </div>

      <div class="rounded-[14px] border border-slate-200 bg-white p-5">
        <div class="flex items-start gap-3">
          <Sparkles class="mt-0.5 size-5 shrink-0 text-slate-400" />
          <div class="min-w-0 flex-1">
            <div class="flex items-baseline gap-3">
              <h3 class="text-[13.5px] font-semibold text-slate-800">Выжимка</h3>
              <span v-if="resume.digest_updated_at" class="text-[12px] text-slate-400">
                собрана {{ dayjs(resume.digest_updated_at).format('DD.MM.YYYY HH:mm') }}
              </span>
              <Button
                class="ml-auto"
                size="small"
                severity="secondary"
                outlined
                :label="resume.digest_json ? 'Пересобрать' : 'Собрать'"
                :disabled="form.raw_text.trim().length === 0"
                :loading="rebuildDigest.isPending.value"
                @click="rebuild"
              />
            </div>
            <p class="mt-1 text-[13px] leading-relaxed text-slate-500">
              Сжимает текст резюме до ~600 токенов: в контекст модели он должен помещаться вместе с
              вакансией. Из выжимки же собирается список навыков.
            </p>
            <p v-if="rebuildDigest.isPending.value" class="mt-2 text-[12.5px] text-slate-500">
              Локальная модель читает резюме целиком — это занимает около минуты.
            </p>
            <pre
              v-if="resume.digest_json"
              class="mt-3 max-h-56 overflow-auto rounded-[10px] bg-slate-50 p-3 font-mono text-[12px] text-slate-700"
              >{{ JSON.stringify(resume.digest_json, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
