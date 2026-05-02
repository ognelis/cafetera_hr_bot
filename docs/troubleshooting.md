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
