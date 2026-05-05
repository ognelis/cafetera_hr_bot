# Частые проблемы

Список типичных ошибок при локальном запуске и Docker Compose — с быстрыми способами их устранить.

---

### «docker: command not found»

Docker не установлен или не запущен. См. раздел «Установить Docker» в [README.md](../README.md#2-установить-docker).

---

### «uv: command not found»

Закройте Терминал и откройте заново. Если не помогло — переустановите `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

### «ADMIN_API_KEY is not set»

Откройте файл `.env` и убедитесь, что строка `ADMIN_API_KEY=` содержит значение (не пустая).

---

### «Qdrant failed to start» / «MinIO failed to start» / «PostgreSQL failed to start»

- Убедитесь, что Docker запущен.
- Проверьте, не заняты ли порты другими программами:

  ```bash
  lsof -i :6333   # Qdrant
  lsof -i :9000   # MinIO
  lsof -i :5432   # PostgreSQL
  ```

- Посмотрите логи Docker:

  ```bash
  docker compose logs
  ```

---

### «Ollama is not installed»

Установите Ollama: <https://ollama.com/download>.

---

### Модель скачивается очень долго

При первом запуске Ollama скачивает модели — суммарно около 4–6 ГБ. Это нормально. Дождитесь завершения — при следующем запуске модели уже будут на диске.

---

### Порт 8000 уже занят

Запустите админку на другом порту (например, 8080):

```bash
ADMIN_PORT=8080 bash scripts/run_admin.sh
```

Админ-панель будет доступна по адресу <http://127.0.0.1:8080/documents>.

---

### Порт 8001 уже занят (RAG-сервис не запускается)

RAG-сервис использует порт 8001. Проверьте:

```bash
lsof -i :8001
```

Если порт занят — остановите другой процесс или измените порт в `.env`:

```
RAG_SERVICE_PORT=9001
RAG_SERVICE_URL=http://localhost:9001
```

---

### VK-бот не отвечает в группе

1. Проверьте, что `VK_ACCESS_TOKEN` и `VK_GROUP_ID` правильно заполнены в `.env`.
2. Убедитесь, что бот запущен: `docker compose logs -f vk_bot`.
3. Проверьте, что в настройках VK-сообщества включены «Сообщения».

---

### Ошибка при запуске через Docker на Linux: «host.docker.internal»

На Linux это имя хоста не всегда работает автоматически. Скрипт и `docker-compose.yml` добавляют `extra_hosts: host.docker.internal:host-gateway` — это должно решить проблему. Если нет — проверьте версию Docker: `docker --version` (нужна 20.10+).

---

### «llamacpp: llama-server not found» или порт 8080/8090 уже занят

1. Проверьте, что `llama-server` установлен: `llama-server --version`.
2. Проверьте, что порты свободны:

   ```bash
   lsof -i :8080   # LLM-сервер
   lsof -i :8090   # Embedding-сервер
   ```

3. Убедитесь, что файлы моделей есть в `models/`: `ls -lh models/`.
4. Если сервер упал — посмотрите логи: `/tmp/llama_llm.log` и `/tmp/llama_embed.log`.

Подробнее про llama.cpp — в [docs/llamacpp.md](llamacpp.md).

---

### «404 page not found» в RAG-сервисе (несовпадение провайдера и URL)

Если в логах RAG-сервиса видите `openai.NotFoundError: 404 page not found`, это значит, что провайдер и URL не соответствуют друг другу. Например:

- `LLM_PROVIDER=llamacpp` (использует OpenAI-совместимый клиент, обращается к `/chat/completions`) но `LLM_BASE_URL` указывает на Ollama (порт 11434), которая не поддерживает этот эндпоинт.
- `EMBEDDING_PROVIDER=llamacpp` но `EMBEDDING_BASE_URL` указывает на Ollama.

**Как проверить:**

```bash
docker exec rag-bot-rag-service env | grep -E "^(LLM|EMBEDDING)_"
```

Должно быть:
- При выборе `llamacpp`: `LLM_BASE_URL=http://host.docker.internal:8080`, `EMBEDDING_BASE_URL=http://host.docker.internal:8090/v1`
- При выборе `ollama`: `LLM_BASE_URL=http://host.docker.internal:11434`, `EMBEDDING_BASE_URL=http://host.docker.internal:11434`

**Причина:** Контейнеры запускаются с URL по умолчанию (порт 11434), если стартовый скрипт не экспортировал переменные до запуска `docker compose up`.

**Решение:** Всегда запускайте систему через стартовые скрипты (`bash scripts/run_all.sh` или `bash scripts/run_admin_docker.sh`), а не напрямую через `docker compose up`. Скрипты автоматически настраивают правильные URL для выбранного провайдера.

Если контейнеры уже запущены с неверными настройками — пересоздайте их:

```bash
docker compose down
bash scripts/run_all.sh
```

---

### «host.docker.internal» не резолвится при локальном запуске

Если при запуске `ragas/run.sh` видите ошибку `nodename nor servname provided, or not known` с адресом `host.docker.internal`, значит скрипт использует Docker-адрес вместо локального.

**Решение:** Это произошло из-за того, что `RERANKER_URL` был установлен как `http://host.docker.internal:8082`. Для локальных скриптов (`ragas/run.sh`, `run_admin.sh`) всегда должен использоваться `localhost`. Скрипты автоматически определяют правильный адрес — просто запустите их заново.

---

### Переменные из .env не применяются в Docker-контейнерах

Docker Compose читает `.env` файл, но переменные из секции `environment` в `docker-compose.yml` имеют приоритет над `env_file`. Если в `.env` указан `LLM_PROVIDER=llamacpp`, но в `docker-compose.yml` стоит `LLM_PROVIDER: "${LLM_PROVIDER:-ollama}"`, а переменная `LLM_PROVIDER` не экспортирована в оболочке — будет использовано значение по умолчанию (`ollama`).

**Решение:** Запускайте систему через стартовые скрипты, которые экспортируют переменные перед вызовом `docker compose up`.

---

### «ERROR: Can't connect to Docker daemon» при запуске retrieval evaluation

Retrieval evaluation поднимает временный контейнер Qdrant через `docker run --rm`. Убедитесь, что Docker запущен:

```bash
docker ps
```

Если Docker не установлен — см. раздел «Установить Docker» в [README.md](../README.md).

---

### «ERROR: Qdrant is not healthy» при retrieval evaluation

Возможные причины:

1. Порт 6333 занят другим процессом:

   ```bash
   lsof -i :6333
   ```

2. Недостаточно памяти для контейнера Qdrant.
3. Проблемы с Docker-сетью — попробуйте `docker network prune`.

---

### «ConnectionError» при скачивании SberQuAD

Датасет SberQuAD загружается с HuggingFace при первом запуске. Проверьте:

- Есть ли доступ в интернет.
- Достаточно ли места на диске.
- Если кэш повреждён — очистите его: `rm -rf ~/.cache/huggingface/datasets/kuznetsoffandrey___sberquad`.

---

### Retrieval evaluation выдаёт MRR близкий к нулю (0.03–0.05) с llamacpp

**Симптом:** MRR@10 около 0.03–0.05 при `EMBEDDING_PROVIDER=llamacpp`, при этом тот же модель через Ollama даёт MRR около 0.82.

**Причина 1 — неправильный EMBED_POOLING:**

Kaждая embedding-модель обучена «смотреть» на определённую часть текста при сжатии в вектор. Если режим pooling не совпадает с тем, на чём модель обучена — результат бессмысленный (модель «смотрит» не на тот кусочек текста).

- Qwen3-Embedding требует `EMBED_POOLING=last`
- Проверьте значение в `.env` и в логах запуска `scripts/run_llama_embeddings.sh`

**Причина 2 — LangChain отправлял неправильные токены (историческая):**

LangChain `OpenAIEmbeddings` по умолчанию разбивает текст токенайзером GPT-4 (tiktoken) и отправляет серверу номера токенов вместо текста. Но llama-server использует токенайзер Qwen3 — номера не совпадают, и сервер получает мусор на входе. Это исправлено в коде проекта (параметр `check_embedding_ctx_length=False`). Убедитесь, что у вас актуальная версия кода.

**Быстрая диагностика** — сравните векторы напрямую:

```bash
# llamacpp (порт 8090)
curl -s http://localhost:8090/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "Тестовый текст", "model": "qwen3-embedding"}' | python -c "
import json, sys; d = json.load(sys.stdin)
v = d['data'][0]['embedding'][:5]
print(f'llamacpp: {v}')
"

# ollama (порт 11434)
curl -s http://localhost:11434/api/embed \
  -d '{"model": "qwen3-embedding", "input": "Тестовый текст"}' | python -c "
import json, sys; d = json.load(sys.stdin)
v = d['embeddings'][0][:5]
print(f'ollama:   {v}')
"
```

Если числа сильно отличаются — проблема в настройках llamacpp-сервера (см. `EMBED_POOLING` выше).

---

### «SIGTRAP» или «failed to find a memory slot» при batch embedding

**Симптом:** Embedding-сервер падает при индексации документов с ошибкой SIGTRAP или «failed to find a KV cache slot».

**Причина:** серверу не хватает «рабочей памяти» (KV-кэша), чтобы обработать все тексты в пачке одновременно. Нужно: `EMBED_CTX_SIZE >= EMBEDDING_CHUNK_SIZE × 512`.

**Решение (любое из двух):**

- Увеличить память: `EMBED_CTX_SIZE=16384` в `.env`
- Уменьшить размер пачки: `EMBEDDING_CHUNK_SIZE=8` в `.env`

После изменения перезапустите embedding-сервер: `bash scripts/run_llama_embeddings.sh`

Подробнее о формуле и значениях по умолчанию — [docs/llamacpp.md, раздел 3.6](llamacpp.md#36-настройки-embedding-сервера-важно).
