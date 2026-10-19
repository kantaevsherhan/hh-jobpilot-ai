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
import { CheckCircle2, Pencil, Plug, Plus, Trash2, XCircle } from 'lucide-vue-next'
import { testProvider } from '@/api/llm'
import { toMessage } from '@/api/client'
import FieldError from '@/components/FieldError.vue'
import { useFormErrors } from '@/composables/useFormErrors'
import {
  useCliCatalog,
  useCreateProvider,
  useDeleteProvider,
  usePatchProvider,
  useProviders,
  useRouting,
  useSaveRouting
} from '@/queries/llm'
import {
  PROVIDER_TYPES,
  ROUTING_STEPS,
  type Provider,
  type ProviderInput,
  type ProviderTest
} from '@/schemas/llm'

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
const editingProvider = ref<Provider | null>(null)
const form = reactive({
  name: '',
  type: 'ollama' as string,
  model: '',
  base_url: '',
  api_key: '',
  command: 'claude',
  effort: '',
  cli_path: '',
  temperature: 0.3,
  timeout_sec: 300
})

const needsKey = computed(() => ['anthropic', 'openai', 'openrouter'].includes(form.type))
const isCli = computed(() => form.type === 'cli')

const { data: cliCatalog } = useCliCatalog(isCli)
const cliTool = computed(() => cliCatalog.value?.find((tool) => tool.command === form.command))
const cliToolOptions = computed(() =>
  (cliCatalog.value ?? []).map((tool) => ({
    value: tool.command,
    label: tool.path ? tool.label : `${tool.label} — не найден`
  }))
)
const cliModelOptions = computed(() =>
  (cliTool.value?.models ?? []).map((model) => ({
    value: model.id,
    label: model.id ? `${model.label} · ${model.id}` : model.label,
    description: model.description
  }))
)
// У Codex уровни свои у каждой модели, у Claude — общие на весь CLI
const cliEffortOptions = computed(() => {
  const model = cliTool.value?.models.find((m) => m.id === form.model)
  const efforts = model?.efforts.length ? model.efforts : (cliTool.value?.efforts ?? [])
  return [
    { value: '', label: 'По умолчанию' },
    ...efforts.map((effort) => ({ value: effort, label: effort }))
  ]
})

function onCliCommandChange() {
  form.model = ''
  form.effort = ''
  if (!form.name.trim() || ['Claude CLI', 'Codex CLI'].includes(form.name)) {
    form.name = form.command === 'codex' ? 'Codex CLI' : 'Claude CLI'
  }
}

function cliExtra(): Record<string, unknown> {
  const extra: Record<string, unknown> = {
    ...(editingProvider.value?.extra_json ?? {}),
    command: form.command.trim()
  }
  // Пустое значение убирается целиком: иначе в базе останется старый уровень или путь
  for (const [key, value] of [
    ['effort', form.effort],
    ['path', form.cli_path.trim()]
  ] as const) {
    if (value) extra[key] = value
    else delete extra[key]
  }
  return extra
}

const {
  errors,
  validate,
  reset: resetErrors
} = useFormErrors(() => ({
  name: form.name.trim() ? undefined : 'Укажите название провайдера',
  // У CLI модель необязательна: без неё берётся модель из настроек самого CLI
  model: isCli.value || form.model.trim() ? undefined : 'Укажите модель',
  api_key:
    needsKey.value && !editingProvider.value?.api_key_masked && !form.api_key.trim()
      ? 'Укажите API-ключ'
      : undefined
}))

const testResults = ref<Record<number, ProviderTest | 'running'>>({})

function fail(error: unknown) {
  toast.add({ severity: 'error', summary: 'Не получилось', detail: toMessage(error), life: 6000 })
}

function openDialog() {
  editingProvider.value = null
  Object.assign(form, {
    name: '',
    type: 'ollama',
    model: '',
    base_url: '',
    api_key: '',
    command: 'claude',
    effort: '',
    cli_path: '',
    temperature: 0.3,
    timeout_sec: 300
  })
  resetErrors()
  dialog.value = true
}

function extraString(provider: Provider, key: string): string {
  const value = provider.extra_json[key]
  return typeof value === 'string' ? value : ''
}

function openEdit(provider: Provider) {
  editingProvider.value = provider
  Object.assign(form, {
    name: provider.name,
    type: provider.type,
    model: provider.model ?? '',
    base_url: provider.base_url ?? '',
    api_key: '',
    command: extraString(provider, 'command') || 'claude',
    effort: extraString(provider, 'effort'),
    cli_path: extraString(provider, 'path'),
    temperature: provider.temperature,
    timeout_sec: provider.timeout_sec
  })
  resetErrors()
  dialog.value = true
}

function submit() {
  if (!validate()) return
  const payload: ProviderInput = {
    name: form.name.trim(),
    type: form.type,
    model: form.model.trim() || null,
    base_url: form.base_url.trim() || null,
    temperature: form.temperature,
    timeout_sec: form.timeout_sec,
    extra_json: isCli.value ? cliExtra() : (editingProvider.value?.extra_json ?? {})
  }
  const key = form.api_key.trim()
  if (key || !editingProvider.value) payload.api_key = key || null

  if (editingProvider.value) {
    const id = editingProvider.value.id
    patchProvider.mutate(
      { id, payload },
      {
        onSuccess: () => {
          dialog.value = false
          delete testResults.value[id]
          toast.add({ severity: 'success', summary: 'Провайдер сохранён', life: 2000 })
        },
        onError: fail
      }
    )
  } else {
    createProvider.mutate(payload, {
      onSuccess: () => {
        dialog.value = false
      },
      onError: fail
    })
  }
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
            <span class="">data/</span>, поэтому резервная копия базы его не уносит. Локальная
            модель ключа не требует.
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
          <div class="flex flex-wrap items-center gap-3">
            <div class="min-w-0 flex-1 basis-80">
              <div class="flex flex-wrap items-baseline gap-2">
                <span class="text-[13.5px] font-medium text-slate-800">{{ provider.name }}</span>
                <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                  {{ provider.type }}
                </span>
                <span v-if="provider.model" class="text-[12px] text-slate-500">
                  {{ provider.model }}
                </span>
              </div>
              <p class="mt-0.5 text-[12px] text-slate-500">
                <span v-if="provider.api_key_masked">ключ {{ provider.api_key_masked }} · </span>
                <template v-if="provider.type === 'cli'">
                  {{ extraString(provider, 'command') || 'claude' }} · effort
                  {{ extraString(provider, 'effort') || 'по умолчанию' }} · таймаут
                  {{ provider.timeout_sec }} сек
                </template>
                <template v-else>
                  таймаут {{ provider.timeout_sec }} сек · temperature {{ provider.temperature }}
                </template>
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
            <Button
              size="small"
              severity="secondary"
              outlined
              label="Изменить"
              @click="openEdit(provider)"
            >
              <template #icon><Pencil class="mr-1.5 size-3.5" /></template>
            </Button>
            <button
              type="button"
              :aria-label="`Удалить провайдера ${provider.name}`"
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
                <span class="">{{ (testResults[provider.id] as ProviderTest).response }}</span>
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
      :header="editingProvider ? 'Редактировать провайдера' : 'Новый провайдер'"
      :style="{ width: '30rem', borderRadius: '18px' }"
    >
      <div class="space-y-3">
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Название</label>
          <InputText
            v-model="form.name"
            :invalid="!!errors.name"
            fluid
            class="w-full"
            placeholder="Локальная qwen3"
          />
          <FieldError :message="errors.name" />
        </div>
        <div>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Тип</label>
          <Select
            v-model="form.type"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            :disabled="editingProvider !== null"
            fluid
            class="w-full"
          />
        </div>
        <template v-if="isCli">
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">CLI</label>
            <Select
              v-model="form.command"
              :options="cliToolOptions"
              option-label="label"
              option-value="value"
              :loading="!cliCatalog"
              fluid
              class="w-full"
              @update:model-value="onCliCommandChange"
            />
            <p class="mt-1 text-[12px] text-slate-500">
              <template v-if="cliTool?.path"
                >Найден: <span class="break-all">{{ cliTool.path }}</span
                >.
              </template>
              <template v-else-if="cliTool">
                Не найден — установите CLI или укажите путь ниже.
              </template>
              Работает по вашей подписке, без API-ключа. Вход выполняется в самом CLI один раз:
              <code>{{ form.command }}</code> в терминале.
            </p>
          </div>
          <div>
            <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Модель</label>
            <Select
              v-model="form.model"
              :options="cliModelOptions"
              option-label="label"
              option-value="value"
              editable
              fluid
              class="w-full"
              placeholder="По умолчанию CLI"
            >
              <template #option="{ option }">
                <div>
                  <p class="text-[13px]">{{ option.label }}</p>
                  <p v-if="option.description" class="text-[11.5px] text-slate-500">
                    {{ option.description }}
                  </p>
                </div>
              </template>
            </Select>
            <p class="mt-1 text-[12px] text-slate-500">
              Можно выбрать из списка или вписать точное имя модели.
            </p>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
                >Усилие (effort)</label
              >
              <Select
                v-model="form.effort"
                :options="cliEffortOptions"
                option-label="label"
                option-value="value"
                fluid
                class="w-full"
              />
            </div>
            <div>
              <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600"
                >Путь к CLI</label
              >
              <InputText v-model="form.cli_path" fluid class="w-full" placeholder="найдётся сам" />
            </div>
          </div>
        </template>
        <div v-else>
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Модель</label>
          <InputText
            v-model="form.model"
            :invalid="!!errors.model"
            fluid
            class="w-full"
            placeholder="qwen3:4b-instruct"
          />
          <FieldError :message="errors.model" />
        </div>
        <div v-if="needsKey">
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">API-ключ</label>
          <InputText
            v-model="form.api_key"
            type="password"
            autocomplete="new-password"
            :invalid="!!errors.api_key"
            fluid
            class="w-full"
          />
          <FieldError :message="errors.api_key" />
          <p v-if="editingProvider?.api_key_masked" class="mt-1 text-[12px] text-slate-500">
            Сейчас сохранён ключ {{ editingProvider.api_key_masked }}. Оставьте поле пустым, чтобы
            сохранить его; введите новый ключ для замены.
          </p>
        </div>
        <div v-if="form.type === 'ollama' || form.type === 'openrouter'">
          <label class="mb-1.5 block text-[12.5px] font-medium text-slate-600">Адрес</label>
          <InputText
            v-model="form.base_url"
            fluid
            class="w-full"
            :placeholder="
              form.type === 'openrouter' ? 'https://openrouter.ai/api/v1' : 'http://localhost:11434'
            "
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <!-- CLI не принимает temperature, поле там ничего бы не меняло -->
          <div v-if="!isCli">
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
          :label="editingProvider ? 'Сохранить' : 'Добавить'"
          size="small"
          :loading="createProvider.isPending.value || patchProvider.isPending.value"
          @click="submit"
        />
      </template>
    </Dialog>
  </div>
</template>
