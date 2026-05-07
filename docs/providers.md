# Настройка ИИ-провайдера

Для работы бота нужны две модели:

- **LLM** (языковая) — формулирует ответ.
- **Embedding** — помогает найти подходящие куски документов.

Провайдер — это место, где эти модели запускаются. Поддерживаются три варианта.

---

## Сравнение

| Провайдер     | Стоимость | Данные уходят наружу | Что нужно установить                   | Кому подходит                                  |
| ------------- | --------- | -------------------- | -------------------------------------- | ---------------------------------------------- |
| **llama.cpp** | Бесплатно | Нет (всё локально)   | `llama-server` + `.gguf`-файлы моделей | **Рекомендуется** — максимальный контроль над памятью |
| **Ollama**    | Бесплатно | Нет (всё локально)   | Ollama                                 | Простой запуск без ручной настройки |
| **OpenAI**    | Платно    | Да (в облако OpenAI) | Только ключ API                        | Быстрый старт без своего железа                |

Если у вас нет сильных причин выбирать иное — **начинайте с llama.cpp** (лучший контроль памяти).

---

## Как указать провайдера

При запуске любого стартового скрипта (`run_admin.sh`, `run_admin_docker.sh`, `run_all.sh`, `ragas/run.sh`) вам будет предложено интерактивно выбрать провайдера для LLM и Embedding:

```
Select LLM provider [1-4, Enter=ollama]:
  1) ollama
  2) openai
  3) llamacpp
  4) custom URL
```

Выбранный провайдер действует **только в текущем сеансе**. URL для подключения настраиваются автоматически:
- При локальном запуске (`run_admin.sh`, `ragas/run.sh`) — используются `localhost`-адреса.
- При запуске через Docker (`run_admin_docker.sh`, `run_all.sh`) — `localhost` автоматически заменяется на `host.docker.internal`, чтобы контейнеры могли обратиться к хосту.

### Custom URL (внешние провайдеры)

Опция `4) custom URL` позволяет подключиться к **любому OpenAI-совместимому API**: vLLM, Together AI, Fireworks, удалённый Ollama и т.д.

При выборе этой опции скрипт попросит:
1. **Формат API** — какой клиент использовать:
   - `openai-compatible` — для vLLM, Together, Fireworks и прочих (`/chat/completions`, `/embeddings`).
   - `ollama` — для удалённой Ollama (`/api/chat`, `/api/embed`).
   - `llamacpp` — для удалённого llama-server (`/chat/completions`).
2. **URL** — адрес сервера (например, `https://api.together.xyz/v1`).
3. **API key** — ключ авторизации (если не нужен — нажмите Enter).

### Фиксация выбора в .env (опционально)

Значения `LLM_PROVIDER` и `EMBEDDING_PROVIDER` в `.env` **не отключают** интерактивное меню — оно показывается всегда. Но заданные значения подставляются как вариант по умолчанию, поэтому согласиться с ними можно одним нажатием **Enter**.

Для `openai` дополнительно полезно зафиксировать `LLM_API_KEY` / `EMBEDDING_API_KEY` в `.env`: тогда скрипт не будет спрашивать ключ интерактивно.

Интерактивный ввод всегда имеет приоритет над `.env`: если ввести число `1`–`4`, выбор из `.env` будет переопределён.

### Полностью неинтерактивный запуск: `SKIP_PROVIDER_MENU`

Флаг `SKIP_PROVIDER_MENU` в `.env` (по умолчанию `false`) полностью выключает интерактивное меню. При `SKIP_PROVIDER_MENU=true` скрипты `run_admin.sh`, `run_admin_docker.sh`, `run_all.sh`, `ragas/run.sh` не спрашивают ничего — провайдер берётся из `LLM_PROVIDER` / `EMBEDDING_PROVIDER`, URL-адреса подставляются автоматически.

Актуально для CI, systemd-юнитов, cron-запусков `ragas/run.sh` и других сценариев без TTY.

```
SKIP_PROVIDER_MENU=true
```

Важно: при `SKIP_PROVIDER_MENU=true` скрипт не будет спрашивать ни провайдера, ни API-ключ. Поэтому все нужные поля должны быть в `.env` заранее. Если что-то критичное не задано — скрипт упадёт с явной ошибкой (например, `ERROR: SKIP_PROVIDER_MENU=true and LLM_PROVIDER=openai, but LLM_API_KEY is not set in .env`).

#### Минимальный набор `.env`-полей для неинтерактивного запуска

Ниже — что **обязательно** должно быть в `.env` для каждого провайдера, чтобы `SKIP_PROVIDER_MENU=true` работал. Остальные параметры имеют разумные дефолты.

**Ollama:**

```
SKIP_PROVIDER_MENU=true
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
# Необязательно, но желательно задать явно:
LLM_MODEL=qwen3.5:4b-q4_K_M
EMBEDDING_MODEL=qwen3-embedding:0.6b-fp16
```

Ключи API не нужны. Скрипты сами запустят Ollama и скачают модели.

**llama.cpp (по умолчанию):**

```
SKIP_PROVIDER_MENU=true
LLM_PROVIDER=llamacpp
EMBEDDING_PROVIDER=llamacpp
# Желательно сразу зафиксировать pooling для правильной модели:
EMBED_POOLING=last
# Необязательно: чтобы сменить LLM/Embedding-модели, задайте пути и URL:
# LLM_MODEL_PATH=./models/Qwen3.5-9B-Q4_K_M.gguf
# LLM_MODEL_URL=https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf
# EMBED_MODEL_PATH=./models/Qwen3-Embedding-0.6B-f16.gguf
# EMBED_MODEL_URL=https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-f16.gguf
```

`.gguf`-файлы скачиваются автоматически. Ключи API не нужны. Подробности о смене моделей — см. [llama.cpp → «Как сменить модель в llama.cpp»](#как-сменить-модель-в-llamacpp) ниже.

**OpenAI (ключи — критичны):**

```
SKIP_PROVIDER_MENU=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-...
```

Без `LLM_API_KEY` / `EMBEDDING_API_KEY` скрипт завершится с ошибкой. Для подключения к OpenAI-совместимым провайдерам (vLLM, Together, Fireworks) — дополнительно задайте `LLM_BASE_URL` и `EMBEDDING_BASE_URL` в `.env` (в неинтерактивном режиме они не перезаписываются).

**llama.cpp:**

```
SKIP_PROVIDER_MENU=true
LLM_PROVIDER=llamacpp
EMBEDDING_PROVIDER=llamacpp
# Желательно сразу зафиксировать pooling для правильной модели:
EMBED_POOLING=last
# Необязательно: чтобы сменить LLM/Embedding-модели, задайте пути и URL:
# LLM_MODEL_PATH=./models/<your-llm>.gguf
# LLM_MODEL_URL=https://huggingface.co/<org>/<repo>/resolve/main/<your-llm>.gguf
# EMBED_MODEL_PATH=./models/<your-embed>.gguf
# EMBED_MODEL_URL=https://huggingface.co/<org>/<repo>/resolve/main/<your-embed>.gguf
```

`.gguf`-файлы скачиваются автоматически. Ключи API не нужны. Подробности о смене моделей — см. [llama.cpp → «Как сменить модель в llama.cpp»](#как-сменить-модель-в-llamacpp) ниже. Если вы хотите подключиться к **удалённому** `llama-server`, см. ниже вариант custom URL.

> **Важно:** вариант `4) custom URL` из интерактивного меню в неинтерактивном режиме не поддерживается напрямую. Чтобы подключиться к OpenAI-совместимому или удалённому серверу, установите `LLM_PROVIDER` в соответствующий формат API (`openai` / `ollama` / `llamacpp`) и вручную укажите `LLM_BASE_URL` и `LLM_API_KEY` в `.env`.

#### Ollama

```
LLM_PROVIDER=ollama
LLM_MODEL=qwen3.5:4b-q4_K_M          # ← имя модели в библиотеке Ollama
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=qwen3-embedding:0.6b-fp16  # ← имя модели в библиотеке Ollama
```

Предварительно установите Ollama (<https://ollama.com/download>). При первом запуске модели (~4–6 ГБ суммарно) скачаются автоматически.

> **Важно:** `LLM_MODEL` и `EMBEDDING_MODEL` — это **только для Ollama**. Для llama.cpp используются `LLM_MODEL_PATH` и `EMBED_MODEL_PATH` (см. ниже).

> **Примечание:** URL-адреса (`LLM_BASE_URL`, `EMBEDDING_BASE_URL`) задавать в `.env` не нужно — они автоматически определяются по выбранному провайдеру.

#### OpenAI

```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...ваш-ключ...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-...ваш-ключ...
```

Ключ получите на <https://platform.openai.com/api-keys>. Оплата идёт по объёму токенов.

#### llama.cpp (по умолчанию)

```
LLM_PROVIDER=llamacpp
LLM_MODEL=local-model                # ← только API-метка, игнорируется llama-server
EMBEDDING_PROVIDER=llamacpp
EMBEDDING_MODEL=qwen3-embedding      # ← только API-метка, игнорируется llama-server
```

Требуется `llama-server` и `.gguf`-файлы моделей в папке `models/`. Подробнее — [docs/llamacpp.md](llamacpp.md).

При выборе llamacpp скрипты запускают локально два сервера: LLM на порту **8080** и Embedding на порту **8090**. Если файлов моделей нет — скрипт скачивает их с HuggingFace.

> **Важно:** `LLM_MODEL` / `EMBEDDING_MODEL` в режиме llama.cpp — это **только API-метки** для поля `model` в HTTP-запросах. `llama-server` их полностью игнорирует. Реально загружаются модели, указанные в `LLM_MODEL_PATH` / `EMBED_MODEL_PATH`.

**Преимущества llama.cpp:**
- Квантизация KV Cache (`q8_0`) — экономия 50% VRAM с минимальной потерей качества
- Контроль параллельных запросов (`LLM_PARALLEL`) — предотвращение explosion памяти
- Гибкая настройка контекста и batch sizes
- Полная конфиденциальность (всё локально)

> **Про `LLM_MODEL` / `EMBEDDING_MODEL` в режиме llama.cpp:** это всего лишь API-метка, которая попадает в поле `model` HTTP-запроса. `llama-server` её игнорирует — реально загружается тот `.gguf`-файл, на который указывает `LLM_MODEL_PATH` / `EMBED_MODEL_PATH`. Менять `LLM_MODEL=local-model` смысла нет.

##### Как сменить модель в llama.cpp

За то, какая модель будет загружена и (при отсутствии файла) скачана, отвечают четыре переменные:

| Переменная | Что делает | Дефолт |
| --- | --- | --- |
| `LLM_MODEL_PATH` | Путь к `.gguf`-файлу LLM, который передаётся в `llama-server --model`. | `./models/Qwen3.5-4B-Q4_K_M.gguf` |
| `LLM_MODEL_URL` | Откуда скачать LLM, если файла по `LLM_MODEL_PATH` нет. | `https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf` |
| `EMBED_MODEL_PATH` | Путь к `.gguf`-файлу embedding-модели. | `./models/Qwen3-Embedding-0.6B-f16.gguf` |
| `EMBED_MODEL_URL` | Откуда скачать embedding-модель, если файла нет. | `https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF/resolve/main/Qwen3-Embedding-0.6B-f16.gguf` |

Пример `.env` — заменить LLM на другую 4B-модель и оставить Qwen3-Embedding по умолчанию:

```
LLM_PROVIDER=llamacpp
EMBEDDING_PROVIDER=llamacpp
LLM_MODEL_PATH=./models/my-llm.Q4_K_M.gguf
LLM_MODEL_URL=https://huggingface.co/<org>/<repo>/resolve/main/my-llm.Q4_K_M.gguf
# EMBED_MODEL_PATH / EMBED_MODEL_URL — оставить пустыми, возьмётся дефолт
EMBED_POOLING=last  # ← проверьте для своей embedding-модели!
```

Те же переменные можно передать разово при запуске: `LLM_MODEL_PATH=./models/my-llm.gguf bash scripts/run_llama_llm.sh`. Полный набор параметров (реранкер, GPU layers, контекст) — см. [docs/llamacpp.md](llamacpp.md), разделы 3 и 8.

> **Важно:** для embedding-сервера режим pooling должен соответствовать модели. По умолчанию `EMBED_POOLING=last` — это правильно для Qwen3-Embedding. Если вы меняете модель — проверьте документацию модели на предмет нужного режима (mean, cls или last). Неправильный pooling приводит к полностью неработающему поиску. Подробнее — [docs/llamacpp.md, раздел 3.6](llamacpp.md#36-настройки-embedding-сервера-важно).

### Реранкер (улучшение качества поиска)

Помимо LLM и Embedding, доступен **реранкер** — модель, которая пересортировывает результаты поиска по релевантности. Это заметно повышает качество ответов, но добавляет задержку.

| Провайдер реранкера | Как работает | Модель по умолчанию |
| --- | --- | --- |
| **llama.cpp** | Локально, через `llama-server` на порту 8082 | `Qwen3-Reranker-0.6B` (~0.4 ГБ) |

Реранкер доступен **только через llama.cpp** — Ollama и OpenAI не предоставляют реранкинг.

По умолчанию реранкер **выключен**. Чтобы включить — добавьте в `.env`:

```
RERANKING_ENABLED=true
```

URL реранкера (`RERANKER_URL`) настраивается автоматически — задавать его вручную не нужно.

Подробности о настройке реранкера, файлах моделей и GPU-ускорении — в [docs/llamacpp.md](llamacpp.md).

---

## Можно ли смешивать провайдеров

Да. Например: LLM — через OpenAI (качественнее), Embedding — через Ollama (бесплатно). Достаточно задать разные значения для `LLM_PROVIDER` и `EMBEDDING_PROVIDER`.

> **Важно:** если вы меняете `EMBEDDING_MODEL` после того как в Qdrant уже есть документы — их нужно переиндексировать. Старые и новые эмбеддинги несовместимы.

---

## Retrieval Evaluation (оценка поиска)

Для оценки качества поиска на бенчмарке SberQuAD требуется **только Embedding-провайдер** — LLM не нужен. Запуск:

```bash
bash ragas/run.sh retrieval
```

Скрипт предложит выбрать Embedding-провайдера и запустит оценку автоматически. Подробности — [docs/ragas.md](ragas.md), раздел 9.

---

## Какие `.env`-переменные применимы к каждому провайдеру

Ниже — быстрая справка, какие настройки **реально влияют** на выбранный провайдер, а какие будут молча проигнорированы. Источник — [packages/rag_service/src/cafetera_rag_service/config.py](../packages/rag_service/src/cafetera_rag_service/config.py) и [chain.py](../packages/rag_service/src/cafetera_rag_service/rag/chain.py).

### Матрица совместимости

| Переменная | Ollama | OpenAI | llama.cpp |
| --- | :-: | :-: | :-: |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TOP_P` | ✅ | ✅ | ✅ |
| `LLM_TOP_K` | ✅ | ⚠️ нестандарт (форвардится через `extra_body`) | ✅ |
| `LLM_PRESENCE_PENALTY` | ❌ игнорируется (Ollama использует `repeat_penalty`) | ✅ | ✅ |
| `LLM_NUM_CTX` | ✅ (Ollama-специфично) | ❌ игнорируется | ✅ (передаётся как `-c`) |
| `LLM_DISABLE_THINKING` | ✅ (только Qwen3/Qwen3.5) | ❌ | ✅ (только Qwen3/Qwen3.5) |
| `LLM_CACHE_TYPE_K`, `LLM_CACHE_TYPE_V` | ❌ | ❌ | ✅ только здесь |
| `LLM_PARALLEL` | ❌ | ❌ | ✅ только здесь |
| `EMBED_POOLING`, `EMBED_CTX_SIZE`, `EMBED_UBATCH_SIZE` | ❌ | ❌ | ✅ только здесь |
| `EMBED_N_GPU_LAYERS`, `LLM_N_GPU_LAYERS` | ❌ | ❌ | ✅ только здесь |
| `EMBEDDING_QUERY_INSTRUCTION` + `EMBEDDING_USE_QUERY_INSTRUCTION` | ✅ (для Qwen3 / E5-instruct) | ✅ | ✅ |
| `EMBEDDING_CHUNK_SIZE` | ✅ | ✅ | ✅ (критично для VRAM) |
| `RERANKING_ENABLED`, `RERANKER_TOP_N`, `RERANKER_PREFETCH_LIMIT`, `RERANKER_TIMEOUT` | провайдер-агностично (нужен запущенный llama-server реранкер) |
| `LLM_MODEL_PATH`, `LLM_MODEL_URL`, `EMBED_MODEL_PATH`, `EMBED_MODEL_URL` | ❌ | ❌ | ✅ только здесь (выбор `.gguf`-файла и URL для скачивания) |
| `RERANKER_MODEL_PATH`, `RERANKER_MODEL_URL`, `RERANKER_CTX_SIZE`, `RERANKER_N_GPU_LAYERS`, `RERANKER_BATCH_SIZE` | ❌ | ❌ | ✅ только здесь |
| `CHUNK_SIZE`, `DOC_QUERY_K`, `GLOBAL_MAX_K`, `DENSE_SCORE_THRESHOLD`, `BM25_LEMMATIZE` | провайдер-агностично — работают везде |

> **Легенда:** ✅ = применяется. ⚠️ = применяется, но нестандартно. ❌ = значение читается, но **молча игнорируется** — задавать его бессмысленно.

### Ollama

**Обязательно задать:**
- `LLM_PROVIDER=ollama`, `LLM_MODEL` (например, `qwen3.5:4b-q4_K_M`).
- `EMBEDDING_PROVIDER=ollama`, `EMBEDDING_MODEL`.

**Можно тюнить:**
- Сэмплинг LLM: `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_TOP_K`, `LLM_MAX_TOKENS`.
- Контекст: `LLM_NUM_CTX` (Ollama-специфично, увеличивайте при длинных ответах).
- Qwen3: `LLM_DISABLE_THINKING=true` отключает режим рассуждения.
- Поиск: `EMBEDDING_QUERY_INSTRUCTION` (для Qwen3 / E5-instruct), `EMBEDDING_CHUNK_SIZE`, `DENSE_SCORE_THRESHOLD`.

**Не задавать (игнорируется):**
- `LLM_PRESENCE_PENALTY` — Ollama использует `repeat_penalty`, эта переменная не прокидывается.
- Любые `EMBED_POOLING`, `EMBED_CTX_SIZE`, `*_N_GPU_LAYERS`, `LLM_CACHE_TYPE_*`, `LLM_PARALLEL` — это настройки `llama-server`, к Ollama отношения не имеют.
- `LLM_BASE_URL`, `EMBEDDING_BASE_URL` — подставляются скриптами автоматически.

### OpenAI

**Обязательно задать:**
- `LLM_PROVIDER=openai`, `LLM_MODEL` (например, `gpt-4o-mini`), `LLM_API_KEY`.
- `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL` (например, `text-embedding-3-small`), `EMBEDDING_API_KEY`.

**Можно тюнить:**
- Сэмплинг: `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_MAX_TOKENS`, `LLM_PRESENCE_PENALTY` (это нативные параметры Chat Completions).
- `LLM_TOP_K` — форвардится через `extra_body`, но работает только у OpenAI-совместимых провайдеров (vLLM, Together, Fireworks); у самого OpenAI будет отброшен сервером.
- Поиск: `EMBEDDING_QUERY_INSTRUCTION`, `EMBEDDING_CHUNK_SIZE`, `DENSE_SCORE_THRESHOLD`, `CHUNK_SIZE`, `DOC_QUERY_K`, `GLOBAL_MAX_K`.

**Не задавать (игнорируется):**
- `LLM_NUM_CTX` — у OpenAI контекст фиксируется моделью.
- `LLM_DISABLE_THINKING` — релевантно только Qwen3 в Ollama/llamacpp.
- Все `LLM_CACHE_TYPE_*`, `LLM_PARALLEL`, `EMBED_POOLING`, `EMBED_CTX_SIZE`, `*_N_GPU_LAYERS` — специфика локального `llama-server`.

### llama.cpp

**Обязательно задать:**
- `LLM_PROVIDER=llamacpp`, `EMBEDDING_PROVIDER=llamacpp`.
- `.gguf`-файлы моделей в `models/` (скрипты скачают автоматически).

**Можно тюнить — все настройки применимы:**
- Выбор модели: `LLM_MODEL_PATH` / `LLM_MODEL_URL` для LLM, `EMBED_MODEL_PATH` / `EMBED_MODEL_URL` для embedding. Именно эти переменные решают, какой `.gguf` загрузится (строка `LLM_MODEL` для llamacpp — это только API-метка, `llama-server` её не использует).
- Сэмплинг LLM: `LLM_TEMPERATURE`, `LLM_TOP_P`, `LLM_TOP_K`, `LLM_PRESENCE_PENALTY`, `LLM_MAX_TOKENS`.
- Контекст: `LLM_NUM_CTX` (передаётся как `-c`), `LLM_DISABLE_THINKING` (для Qwen3).
- VRAM/скорость LLM: `LLM_CACHE_TYPE_K=q8_0`, `LLM_CACHE_TYPE_V=q8_0` (экономят 50% VRAM), `LLM_PARALLEL` (лимит параллельных запросов), `LLM_N_GPU_LAYERS` (99 = всё на GPU, 0 = CPU).
- Embedding-сервер: `EMBED_POOLING` (для Qwen3 — `last`, для BGE — `cls`, для nomic — `mean`), `EMBED_CTX_SIZE` (формула: `≥ EMBEDDING_CHUNK_SIZE × CHUNK_SIZE`), `EMBED_UBATCH_SIZE`, `EMBED_N_GPU_LAYERS`.
- Реранкер (если `RERANKING_ENABLED=true`): `RERANKER_MODEL_PATH`, `RERANKER_MODEL_URL`, `RERANKER_CTX_SIZE`, `RERANKER_BATCH_SIZE`, `RERANKER_N_GPU_LAYERS`, `RERANKER_TOP_N`, `RERANKER_PREFETCH_LIMIT`.

> **Критично:** неверный `EMBED_POOLING` приводит к полностью неработающему поиску. См. [docs/llamacpp.md, раздел 3.6](llamacpp.md#36-настройки-embedding-сервера-важно).

**Не задавать:**
- `LLM_BASE_URL`, `EMBEDDING_BASE_URL`, `RERANKER_URL` — подставляются скриптами автоматически.

---

## Остальные переменные

`DATABASE_URL`, `QDRANT_URL`, `S3_ENDPOINT_URL`, `RAG_SERVICE_URL`, `RAG_SERVICE_API_KEY` оставьте как есть — скрипты и Docker подставят правильные значения сами. Меняйте их только если выносите сервисы на другой хост или порт.
