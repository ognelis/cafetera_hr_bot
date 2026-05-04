# llama.cpp

llama.cpp — продвинутый вариант локального запуска ИИ-моделей. В отличие от Ollama, вы сами кладёте файлы моделей в папку `models/` и управляете серверами напрямую. Подходит, если нужен максимальный контроль над потреблением памяти и скоростью.

> Если вы используете **Ollama** или **OpenAI** — этот документ можно пропустить. Выбор провайдера см. в [docs/providers.md](providers.md).

---

## 1. Установить `llama-server`

### macOS (через Homebrew)

```bash
brew install llama.cpp
```

> Если Homebrew не установлен — откройте <https://brew.sh> и следуйте инструкции.

### Linux (сборка из исходников)

```bash
sudo apt-get install -y build-essential cmake
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build
cmake --build build --config Release -j$(nproc)
sudo cp build/bin/llama-server /usr/local/bin/
```

Проверьте установку:

```bash
llama-server --version
```

---

## 2. Файлы моделей (`.gguf`)

llama.cpp использует модели в формате `.gguf`. Файлы нужно положить в папку `models/` в корне проекта.

По умолчанию скрипты ожидают следующие файлы:

| Файл                                       | Назначение                         | Размер  | Когда нужен |
| ------------------------------------------ | ---------------------------------- | ------- | --- |
| `models/Qwen3.5-4B-Q4_K_M.gguf`            | LLM — языковая модель              | ~2.5 ГБ | Всегда (при `LLM_PROVIDER=llamacpp`) |
| `models/Qwen3-Embedding-4B-Q4_K_M.gguf`    | Embedding — поиск по документам    | ~2.4 ГБ | Всегда (при `EMBEDDING_PROVIDER=llamacpp`) |
| `models/Qwen3-Reranker-0.6B-Q4_K_M.gguf`   | Reranker — переранжирование выдачи | ~0.4 ГБ | Только при `RERANKING_ENABLED=true` |

**Скрипты скачают модели автоматически** при первом запуске, если файлов нет. Для ручного скачивания:

```bash
# LLM-модель
curl -L -o models/Qwen3.5-4B-Q4_K_M.gguf \
  https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-Q4_K_M.gguf

# Embedding-модель
curl -L -o models/Qwen3-Embedding-4B-Q4_K_M.gguf \
  https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF/resolve/main/Qwen3-Embedding-4B-Q4_K_M.gguf

# Reranker-модель (нужна только если включён реранкинг)
curl -L -o models/Qwen3-Reranker-0.6B-Q4_K_M.gguf \
  https://huggingface.co/mradermacher/Qwen3-Reranker-0.6B-GGUF/resolve/main/Qwen3-Reranker-0.6B.Q4_K_M.gguf
```

URL можно переопределить переменными `LLM_MODEL_URL` / `EMBED_MODEL_URL` / `RERANKER_MODEL_URL` (см. раздел 4).

---

## 3. Ускорение через GPU (определяется автоматически)

Скрипты сами определяют тип GPU и включают ускорение:

| Железо                          | Что используется                     |
| ------------------------------- | ------------------------------------ |
| Mac на Apple Silicon (M1–M4)    | Metal — все слои модели на GPU       |
| NVIDIA (Linux)                  | CUDA — все слои модели на GPU        |
| Всё остальное                   | CPU (без GPU-ускорения)              |

Если нужно переопределить вручную — задайте переменные в `.env`:

```
LLM_N_GPU_LAYERS=99    # 99 = все слои на GPU, 0 = только CPU
EMBED_N_GPU_LAYERS=99
```

---

## 3.5. Retrieval Evaluation (оценка поиска)

Для оценки качества поиска на SberQuAD нужен **только Embedding-сервер** (порт 8090). LLM-сервер (порт 8080) **не требуется**.

```bash
# Запустить Embedding-сервер (если не запущен)
bash scripts/run_llama_embeddings.sh

# Запустить оценку поиска
bash ragas/run.sh retrieval
```

Файл модели: `models/Qwen3-Embedding-4B-Q4_K_M.gguf` (скачается автоматически при первом запуске). Опциональные переопределения:

```bash
EMBED_MODEL_PATH=./models/my-embed.gguf bash scripts/run_llama_embeddings.sh
EMBED_N_GPU_LAYERS=0 bash scripts/run_llama_embeddings.sh  # принудительно CPU
```

---

## 4. Запуск серверов вручную

Скрипты `run_admin.sh` и `run_all.sh` запускают `llama-server` автоматически. Если нужно поднять серверы отдельно (например, в отдельном окне терминала):

**LLM-сервер** (порт 8080):

```bash
bash scripts/run_llama_llm.sh
```

**Embedding-сервер** (порт 8090):

```bash
bash scripts/run_llama_embeddings.sh
```

**Reranker-сервер** (порт 8082) — нужен только если `RERANKING_ENABLED=true`:

```bash
bash scripts/run_llama_reranker.sh
```

Все три скрипта автоматически:

- Определяют тип GPU (Metal / CUDA / CPU) и включают ускорение.
- Скачивают файл модели с HuggingFace, если его нет в `models/`.

### Переменные окружения

```bash
# Использовать другой файл LLM-модели:
LLM_MODEL_PATH=./models/my-llm.gguf bash scripts/run_llama_llm.sh

# Скачать LLM-модель с другого URL вместо HuggingFace по умолчанию:
LLM_MODEL_URL=https://example.com/my-model.gguf bash scripts/run_llama_llm.sh

# Использовать другой файл Embedding-модели:
EMBED_MODEL_PATH=./models/my-embed.gguf bash scripts/run_llama_embeddings.sh

# Скачать Embedding-модель с другого URL:
EMBED_MODEL_URL=https://example.com/my-embed.gguf bash scripts/run_llama_embeddings.sh

# Использовать другой файл Reranker-модели / URL:
RERANKER_MODEL_PATH=./models/my-reranker.gguf bash scripts/run_llama_reranker.sh
RERANKER_MODEL_URL=https://example.com/my-reranker.gguf bash scripts/run_llama_reranker.sh

# Принудительно только CPU (без GPU):
LLM_N_GPU_LAYERS=0 bash scripts/run_llama_llm.sh
EMBED_N_GPU_LAYERS=0 bash scripts/run_llama_embeddings.sh
RERANKER_N_GPU_LAYERS=0 bash scripts/run_llama_reranker.sh
```

---

## 5. Реранкер (улучшение качества поиска)

**Реранкер** — отдельная модель, которая после первичного поиска по базе знаний пересортировывает кандидатов по релевантности. Обычно это заметно повышает качество ответов, но добавляет ~0.4 ГБ модели и небольшую задержку на каждый запрос.

По умолчанию реранкер **выключен**. Чтобы включить — в `.env`:

```
RERANKING_ENABLED=true
```

> **Примечание:** URL реранкера (`RERANKER_URL`) настраивается автоматически:
> - При запуске через Docker-скрипты (`run_all.sh`, `run_admin_docker.sh`) — `http://host.docker.internal:8082`
> - При локальном запуске (`run_admin.sh`, `ragas/run.sh`) — `http://localhost:8082`
> - Явно указанный `RERANKER_URL` в `.env` используется только для проверки доступности при старте

Дополнительные настройки реранкера в `.env`:

```
RERANKER_TOP_N=5           # сколько документов оставить после переранжирования
RERANKER_PREFETCH_LIMIT=20 # сколько кандидатов брать из Qdrant на вход реранкеру
RERANKER_TIMEOUT=30.0

# Настройки для scripts/run_llama_reranker.sh
RERANKER_MODEL_PATH=./models/Qwen3-Reranker-0.6B-Q4_K_M.gguf
RERANKER_CTX_SIZE=8192
RERANKER_N_GPU_LAYERS=     # пусто = автоопределение (Metal/CUDA/CPU)
```

После включения скрипты `run_admin.sh` и `run_all.sh` сами поднимут реранкер в фоне (порт 8082) и подождут, пока он станет готов. Для ручного запуска в отдельном окне:

```bash
bash scripts/run_llama_reranker.sh
```

Проверить, что сервер ответил:

```bash
curl http://localhost:8082/health
```

> **Важно:** реранкер работает только через llama.cpp — у Ollama и OpenAI-совместимых провайдеров реранкинга нет. Если `RERANKING_ENABLED=false`, файл `Qwen3-Reranker-0.6B-Q4_K_M.gguf` скачивать не нужно.

---

## 6. GPU-ускорение PyTorch (для RAG-сервиса)

По умолчанию на Linux (включая Docker) `torch` устанавливается как CPU-only версия через `[tool.uv.sources]` в `pyproject.toml`. На macOS Apple Silicon torch из PyPI автоматически включает поддержку MPS (Metal) GPU.

> **Примечание:** GPU-ускорение PyTorch используется RAG-сервисом для парсинга и обработки документов (Docling). Админ-панель не содержит Docling/torch — она делегирует обработку RAG-сервису.

Если у вас NVIDIA GPU на Linux и нужно CUDA-ускорение, после `uv sync` переустановите torch:

```bash
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 --reinstall
```
