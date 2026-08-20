<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import { Building2, FlaskConical, Plus, Trash2 } from 'lucide-vue-next'
import { toMessage } from '@/api/client'
import { createCompanyRule, deleteCompanyRule, testCompanyRules } from '@/api/catalogs'
import EmptyState from '@/components/EmptyState.vue'
import { useCompanyRules, useDictionaries, useMutate } from '@/queries'
import { useUiStore } from '@/stores/ui'
import type { CompanyRule } from '@/api/catalogs'

const MATCH_TYPES = [
  { value: 'CONTAINS', label: 'Содержит' },
  { value: 'EQUALS', label: 'Точное совпадение' }
]

const toast = useToast()
const ui = useUiStore()
const { data: dictionaries } = useDictionaries()
const { data: rules, isPending } = useCompanyRules(() => ui.resumeId)

const form = reactive({
  value: '',
  match_type: 'CONTAINS',
  action: 'SKIP',
  score_delta: 0,
  case_sensitive: false,
  note: '',
  forAllResumes: true
})

const testName = ref('')
const testResult = ref<{ value: string; action: string; score_delta: number }[] | null>(null)
const testing = ref(false)

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

const create = useMutate(['company-rules'], createCompanyRule)
const remove = useMutate(['company-rules'], deleteCompanyRule)

function submit() {
  if (!form.value.trim()) return
  create.mutate(
    {
      resume_id: form.forAllResumes ? null : ui.resumeId,
      value: form.value.trim(),
      match_type: form.match_type,
      action: form.action,
      score_delta: form.score_delta,
      case_sensitive: form.case_sensitive,
      note: form.note.trim() || null
    },
    {
      onSuccess: () => {
        form.value = ''
        form.note = ''
        form.score_delta = 0
      },
      onError: fail
    }
  )
}

async function runTest() {
  if (!testName.value.trim()) return
  testing.value = true
  try {
    const result = await testCompanyRules(testName.value.trim(), ui.resumeId ?? undefined)
    testResult.value = result.matched
  } catch (error) {
    fail(error)
  } finally {
    testing.value = false
  }
}

const actionLabel = (code: string) => dictionaries.value?.company_rule_action?.[code] ?? code
const needsDelta = (action: string) => action === 'BOOST' || action === 'PENALTY'

function ruleLine(rule: CompanyRule): string {
  const match = rule.match_type === 'EQUALS' ? 'точно' : 'содержит'
  const scope = rule.resume_id === null ? 'для всех резюме' : 'только для этого резюме'
  return `${match} · ${scope}${rule.case_sensitive ? ' · регистр важен' : ''}`
}
</script>

<template>
  <div class="grid max-w-5xl grid-cols-[1fr_320px] gap-5">
    <section>
      <p class="mb-3 max-w-prose text-[13px] leading-relaxed text-slate-600">
        Правило «содержит vash» поймает «Vash Group», «VASH COMPANY» и «ТОО Vash». Штрафы и бонусы
        применяются к оценке модели до сравнения с порогами.
      </p>

      <div v-if="isPending" class="text-[13px] text-slate-500">Загружается…</div>

      <div
        v-else-if="(rules?.length ?? 0) === 0"
        class="rounded-[14px] border border-dashed border-slate-300"
      >
        <EmptyState :icon="Building2" title="Правил нет" hint="Добавьте первое справа." />
      </div>

      <div v-else class="space-y-1.5">
        <article
          v-for="rule in rules"
          :key="rule.id"
          class="flex items-center gap-3 rounded-[12px] border border-slate-200 bg-white px-4 py-2.5"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="font-mono text-[13px] text-slate-800">{{ rule.value }}</span>
              <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11.5px] text-slate-700">
                {{ actionLabel(rule.action) }}
              </span>
              <span
                v-if="rule.score_delta !== 0"
                class="font-mono text-[12px]"
                :class="rule.score_delta > 0 ? 'text-teal-800' : 'text-red-700'"
              >
                {{ rule.score_delta > 0 ? '+' : '' }}{{ rule.score_delta }}
              </span>
            </div>
            <p class="mt-0.5 text-[12px] text-slate-500">{{ ruleLine(rule) }}</p>
            <p v-if="rule.note" class="mt-0.5 text-[12.5px] text-slate-600">{{ rule.note }}</p>
          </div>
          <button
            type="button"
            class="flex size-8 shrink-0 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
            @click="remove.mutate(rule.id, { onError: fail })"
          >
            <Trash2 class="size-4" />
          </button>
        </article>
      </div>
    </section>

    <aside class="space-y-4">
      <div class="rounded-[14px] border border-slate-200 bg-white p-4">
        <h3 class="mb-3 text-[13.5px] font-semibold text-slate-800">Новое правило</h3>
        <div class="space-y-2.5">
          <InputText
            v-model="form.value"
            size="small"
            fluid
            class="w-full"
            placeholder="Название или часть"
            @keyup.enter="submit"
          />
          <Select
            v-model="form.match_type"
            :options="MATCH_TYPES"
            option-label="label"
            option-value="value"
            fluid
            class="w-full"
            size="small"
          />
          <Select
            v-model="form.action"
            :options="
              Object.entries(dictionaries?.company_rule_action ?? {}).map(([value, label]) => ({
                value,
                label
              }))
            "
            option-label="label"
            option-value="value"
            class="w-full"
            size="small"
          />
          <InputNumber
            v-if="needsDelta(form.action)"
            v-model="form.score_delta"
            fluid
            class="w-full"
            size="small"
            :min="-50"
            :max="50"
            show-buttons
            placeholder="Дельта скора"
          />
          <InputText v-model="form.note" size="small" fluid class="w-full" placeholder="Заметка" />
          <label class="flex items-center gap-2 text-[12.5px] text-slate-700">
            <ToggleSwitch v-model="form.case_sensitive" />
            Учитывать регистр
          </label>
          <label class="flex items-center gap-2 text-[12.5px] text-slate-700">
            <ToggleSwitch v-model="form.forAllResumes" />
            Для всех резюме
          </label>
          <Button
            class="w-full"
            size="small"
            label="Добавить"
            :disabled="!form.value.trim()"
            :loading="create.isPending.value"
            @click="submit"
          >
            <template #icon><Plus class="mr-1.5 size-3.5" /></template>
          </Button>
        </div>
      </div>

      <div class="rounded-[14px] border border-slate-200 bg-white p-4">
        <h3 class="mb-2 text-[13.5px] font-semibold text-slate-800">Проверить правило</h3>
        <p class="mb-2.5 text-[12px] leading-relaxed text-slate-500">
          Введите название компании и посмотрите, сработает ли что-нибудь.
        </p>
        <div class="flex gap-2">
          <InputText
            v-model="testName"
            size="small"
            class="min-w-0 flex-1"
            placeholder="ТОО Vash"
            @keyup.enter="runTest"
          />
          <Button size="small" severity="secondary" outlined :loading="testing" @click="runTest">
            <template #icon><FlaskConical class="size-3.5" /></template>
          </Button>
        </div>

        <div v-if="testResult !== null" class="mt-3 text-[12.5px]">
          <p v-if="testResult.length === 0" class="text-slate-500">Ни одно правило не сработало.</p>
          <ul v-else class="space-y-1">
            <li v-for="match in testResult" :key="match.value" class="text-slate-700">
              <span class="font-mono">{{ match.value }}</span> → {{ actionLabel(match.action) }}
              <span v-if="match.score_delta" class="font-mono">({{ match.score_delta }})</span>
            </li>
          </ul>
        </div>
      </div>
    </aside>
  </div>
</template>
