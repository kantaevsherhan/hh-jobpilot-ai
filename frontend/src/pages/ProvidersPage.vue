<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { CheckCircle2, Plug, Plus, Trash2, XCircle } from 'lucide-vue-next'
import { testProvider } from '@/api/llm'
import { toMessage } from '@/api/client'
import {
  useCreateProvider,
  useDeleteProvider,
  usePatchProvider,
  useProviders,
  useRouting,
  useSaveRouting
} from '@/queries/llm'
import { PROVIDER_TYPES, ROUTING_STEPS, type Provider, type ProviderTest } from '@/schemas/llm'

const toast = useToast()
const confirm = useConfirm()

const { data: providers, isPending } = useProviders()
const { data: routing } = useRouting()
const createProvider = useCreateProvider()
const patchProvider = usePatchProvider()
const removeProvider = useDeleteProvider()
const saveRouting = useSaveRouting()

const typeOptions = PROVIDER_TYPES.map((value) => ({ value, label: value }))

const dialog = ref(false)
const form = reactive({
  name: '',
  type: 'ollama' as string,
  model: '',
  base_url: '',
  api_key: '',
  command: 'claude',
  temperature: 0.3,
  timeout_sec: 300
})

const needsKey = computed(() => ['anthropic', 'openai', 'openrouter'].includes(form.type))
const isCli = computed(() => form.type === 'cli')

const testResults = ref<Record<number, ProviderTest | 'running'>>({})

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

function openDialog() {
  Object.assign(form, {
    name: '',
    type: 'ollama',
    model: '',
    base_url: '',
    api_key: '',
    command: 'claude',
    temperature: 0.3,
    timeout_sec: 300
  })
  dialog.value = true
}

function submit() {
  if (!form.name.trim()) return
  createProvider.mutate(
    {
      name: form.name.trim(),
      type: form.type,
      model: form.model.trim() || null,
      base_url: form.base_url.trim() || null,
      api_key: form.api_key.trim() || null,
      temperature: form.temperature,
      timeout_sec: form.timeout_sec,
      extra_json: isCli.value ? { command: form.command } : {}
    },
    {
      onSuccess: () => {
        dialog.value = false
      },
      onError: fail
    }
  )
}

async function runTest(provider: Provider) {
  testResults.value = { ...testResults.value, [provider.id]: 'running' }
  try {
    const result = await testProvider(provider.id)
    testResults.value = { ...testResults.value, [provider.id]: result }
  } catch (error) {
    testResults.value = {
      ...testResults.value,
      [provider.id]: { ok: false, error: toMessage(error) }
    }
  }
}

function toggleEnabled(provider: Provider) {
  patchProvider.mutate(
    { id: provider.id, payload: { is_enabled: !provider.is_enabled } },
    { onError: fail }
  )
}

function onDelete(provider: Provider) {
  confirm.require({
    header: 'Удалить провайдера',
    message: `«${provider.name}» будет удалён, а шаги, назначенные на него, останутся без провайдера.`,
    acceptLabel: 'Удалить',
    rejectLabel: 'Отмена',
    acceptProps: { severity: 'danger', size: 'small' },
    rejectProps: { severity: 'secondary', outlined: true, size: 'small' },
    accept: () => {
      removeProvider.mutate(provider.id, { onError: fail })
    }
  })
}

const routingDraft = computed<Record<string, number | null>>(() => {
  const current = routing.value ?? {}
  return Object.fromEntries(ROUTING_STEPS.map((step) => [step.key, current[step.key] ?? null]))
})

function setStep(step: string, providerId: number | null) {
  const next = { ...(routing.value ?? {}) }
  if (providerId === null) delete next[step]
  else next[step] = providerId
  saveRouting.mutate(next, {
    onSuccess: () => {
      toast.add({ severity: 'success', summary: 'Маршрут сохранён', life: 2000 })
    },
    onError: fail
  })
}

const providerOptions = computed(() =>
  (providers.value ?? [])
    .filter((p) => p.is_enabled)
    .map((p) => ({ label: `${p.name}${p.model ? ` · ${p.model}` : ''}`, value: p.id }))
)
</script>

<template>
  <div class="mx-auto w-full max-w-7xl">
    <section>
      <div class="mb-3 flex items-end gap-4">
        <div>
          <h2 class="text-[15px] font-semibold tracking-tight text-slate-900">Провайдеры</h2>
          <p class="mt-1 max-w-prose text-[13px] leading-relaxed text-slate-600">
            Ключи хранятся в базе зашифрованными и наружу отдаются маской. Ключ шифрования лежит в
            настройках пользователя, а не в
            <span class="font-mono">data/</span>, поэтому резервная копия базы его не уносит.
            Локальная модель ключа не требует.
          </p>
        </div>
        <Button class="ml-auto shrink-0" size="small" label="Добавить" @click="openDialog">
          <template #icon><Plus class="mr-1.5 size-4" /></template>
        </Button>
      </div>

      <p v-if="isPending" class="text-[13px] text-slate-500">Загружается…</p>

      <div
        v-else-if="(providers ?? []).length === 0"
        class="rounded-[14px] border border-dashed border-slate-300 px-5 py-8 text-center"
      >
        <Plug class="mx-auto size-6 text-slate-400" />
        <p class="mt-2 text-[13.5px] text-slate-600">Ни одного провайдера не заведено.</p>
        <p class="mt-1 text-[12.5px] text-slate-500">
          Начните с Ollama на localhost:11434 — она уже работает, если запущен make dev.
        </p>
      </div>

      <div v-else class="space-y-2">
        <article
          v-for="provider in providers"
          :key="provider.id"
          class="rounded-[14px] border border-slate-200 bg-white px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-baseline gap-2">
                <span class="text-[13.5px] font-medium text-slate-800">{{ provider.name }}</span>
                <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                  {{ provider.type }}
                </span>
                <span v-if="provider.model" class="font-mono text-[12px] text-slate-500">
                  {{ provider.model }}
                </span>
              </div>
              <p class="mt-0.5 text-[12px] text-slate-500">
                <span v-if="provider.api_key_masked">ключ {{ provider.api_key_masked }} · </span>
                таймаут {{ provider.timeout_sec }} сек · temperature {{ provider.temperature }}
              </p>
            </div>

            <ToggleSwitch
              :model-value="provider.is_enabled"
              @update:model-value="toggleEnabled(provider)"
            />
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Проверить"
              :loading="testResults[provider.id] === 'running'"
              @click="runTest(provider)"
            />
            <button
              type="button"
              class="flex size-8 items-center justify-center rounded-[9px] text-slate-500 hover:bg-red-50 hover:text-red-700"
              @click="onDelete(provider)"
            >
              <Trash2 class="size-4" />
            </button>
          </div>

          <div
            v-if="testResults[provider.id] && testResults[provider.id] !== 'running'"
            class="mt-2.5 flex items-start gap-2 rounded-[10px] px-3 py-2 text-[12.5px]"
            :class="
              (testResults[provider.id] as ProviderTest).ok
                ? 'bg-teal-50 text-teal-900'
                : 'bg-red-50 text-red-900'
            "
          >
            <component
              :is="(testResults[provider.id] as ProviderTest).ok ? CheckCircle2 : XCircle"
              class="mt-0.5 size-4 shrink-0"
            />
            <div class="min-w-0">
              <template v-if="(testResults[provider.id] as ProviderTest).ok">
                Ответил за {{ (testResults[provider.id] as ProviderTest).elapsed_sec }} сек:
                <span class="font-mono">{{
                  (testResults[provider.id] as ProviderTest).response
                }}</span>
              </template>
              <template v-else>
                {{ (testResults[provider.id] as ProviderTest).error }}
              </template>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="mt-8">
      <h2 class="text-[15px] font-semibold tracking-tight text-slate-900">Маршрутизация шагов</h2>
      <p class="mt-1 max-w-prose text-[13px] leading-relaxed text-slate-600">
        Анализ гоняется по каждой вакансии — ему хватает локальной модели, это быстро и приватно.
        Письмо пишется один раз, и разница в качестве там видна сразу. Платить имеет смысл только за
        вторую часть.
      </p>

      <Message v-if="providerOptions.length === 0" severity="warn" size="small" class="mt-3">
        Сначала добавьте хотя бы одного включённого провайдера.
      </Message>

      <div
        v-else
        class="mt-3 divide-y divide-slate-200 overflow-hidden rounded-[14px] border border-slate-200 bg-white"
      >
        <div
          v-for="step in ROUTING_STEPS"
          :key="step.key"
          class="flex items-center gap-4 px-4 py-2.5"
        >
          <div class="min-w-0 flex-1">
            <p class="text-[13.5px] text-slate-800">{{ step.label }}</p>
            <p class="text-[12px] text-slate-500">{{ step.hint }}</p>
          </div>
          <Select
            :model-value="routingDraft[step.key]"
            :options="providerOptions"
            option-label="label"
            option-value="value"
            placeholder="не задан"
            size="small"
            show-clear
            class="w-72"
            @update:model-value="setStep(step.key, $event as number | null)"
          />
        </div>
      </div>
    </section>

    <Dialog
      v-model:visible="dialog"
      modal
      header="Новый провайдер"
      :style="{ width: '30rem', borderRadius: '18px' }"
    >
      <div class="space-y-3">
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Название</label>
          <InputText v-model="form.name" fluid class="w-full" placeholder="Локальная qwen3" />
        </div>
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Тип</label>
          <Select
            v-model="form.type"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            fluid
            class="w-full"
          />
        </div>
        <div v-if="isCli">
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Команда</label>
          <InputText v-model="form.command" fluid class="w-full" placeholder="claude или codex" />
          <p class="mt-1 text-[12px] text-slate-500">
            Неинтерактивный режим CLI: claude -p и codex exec. Биллится по подписке.
          </p>
        </div>
        <div v-else>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Модель</label>
          <InputText v-model="form.model" fluid class="w-full" placeholder="qwen3:4b-instruct" />
        </div>
        <div v-if="needsKey">
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">API-ключ</label>
          <InputText v-model="form.api_key" type="password" fluid class="w-full" />
        </div>
        <div v-if="form.type === 'ollama' || form.type === 'openrouter'">
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Адрес</label>
          <InputText
            v-model="form.base_url"
            fluid
            class="w-full"
            placeholder="http://localhost:11434"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Temperature</label>
            <InputNumber
              v-model="form.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :min-fraction-digits="1"
              fluid
              class="w-full"
              size="small"
            />
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
              >Таймаут, сек</label
            >
            <InputNumber
              v-model="form.timeout_sec"
              :min="5"
              :max="3600"
              fluid
              class="w-full"
              size="small"
            />
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Отмена" severity="secondary" outlined size="small" @click="dialog = false" />
        <Button
          label="Добавить"
          size="small"
          :loading="createProvider.isPending.value"
          @click="submit"
        />
      </template>
    </Dialog>
  </div>
</template>
