# Secret Drop — тест MCP URL mode

21.11.2026 · Отдельная исследовательская ветка · [План](../plans/2026-11-21-mcp-url-mode-pilot.md)

Проверяем URL-режим MCP 2025-11-25 с отдельной страницей на `127.0.0.1`. Страница записывает фиксированный публичный маркер во временный файл по кнопке. Полей ввода нет. Сервер удаляет временный каталог при штатном завершении. В момент записи MCP сообщает только статус. Это стенд для проверки перехода и подтверждения из Codex, без приёмки браузерной безопасности для реальных ключей.

| Проверка | Результат |
| --- | --- |
| Шлюз записи закрыт до согласия; после Accept и GET файл ещё отсутствует | PASS, эмулятор MCP-клиента и реальный HTTP на loopback |
| POST после согласия записывает ровно заданный маркер, затем MCP возвращает `saved`; повторный POST получает 409 | PASS, эмулятор и HTTP |
| Cancel оставляет файл отсутствующим; клиент с одной Form capability не получает URL-запрос | PASS, эмулятор и HTTP |
| Тесты предыдущих исследовательских проб и адаптера 0.6.0 | 7 + 18 + 36 = 61 PASS |
| Опциональный Chromium через Playwright | BLOCKED: Chromium завершился на создании сокета с `Operation not permitted` |
| Codex app-server в Linux, CLI 0.172.0-alpha.2 | BLOCKED: `Read-only file system (os error 30)` до JSON-RPC initialize даже со временным SQLite-каталогом |
| Нативная карточка и открытие браузера в Codex на Mac; поддержка в ChatGPT Work | OPEN. На этих клиентах URL mode ещё не наблюдался |

## Воспроизведение в ветке пилота

```sh
node --test research/elicitation-url-pilot/test_browser.mjs
# В среде с Playwright и Chromium
RUN_BROWSER_TEST=1 node --test research/elicitation-url-pilot/test_browser.mjs
```

Для пробы в Codex CLI на Mac из корня репозитория запустить отдельную TUI-сессию с process-scoped MCP-настройкой:

```sh
codex \
  -c 'mcp_servers.secret_drop_url.command="python3"' \
  -c "mcp_servers.secret_drop_url.args=[\"-I\",\"$PWD/research/elicitation-url-pilot/stdio_probe.py\"]"
```

В этой сессии попросить вызвать `secret_drop_url.probe_url` с пустыми аргументами. Успех клиента означает, что он показывает полный URL, спрашивает согласие и открывает страницу во внешнем браузере после согласия. Если ссылка открылась, попросить вызвать `probe_status` сначала до нажатия кнопки, затем после. Ожидается `awaiting_browser`, затем `saved`. Для Cancel открыть новую сессию, отменить запрос и проверить `cancelled`. Если появляется `url_not_advertised`, записать фактический клиент и его версию. Прямое открытие ссылки вручную отдельно проверяет страницу, но не URL elicitation клиента.

Этот же probe не проверяет удалённый транспорт ChatGPT Work. Для него нужна отдельная доступная в Work тестовая MCP-точка и страница, достижимая браузером в той топологии. Адрес loopback локального процесса не переносится между хостами. Оба результата хоста следует зафиксировать до выбора архитектуры ввода настоящего секрета. [Спецификация](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation).

## Повторная проверка на Mac

На Mac Codex CLI `0.163.0` объявил `form` и `url`, предложив `2025-06-18` при инициализации. Исходная версия стенда ошибочно сравнивала предложение клиента с версией ответа сервера. После исправления стенд выбирает `2025-11-25` в ответе, а для продолжившего соединение клиента проверяет явную capability `url`. Синтетический клиент реального app-server на Mac получил `mcpServer/elicitation/request` в режиме `url`. Ответ Cancel дошёл до MCP и вернул `cancelled`. Эта проверка охватывает протокол app-server и не подтверждает отображение карточки или открытие браузера в Desktop.

Для Desktop открыть в режиме Local папку тестового checkout и начать новый чат. В доверенном проекте можно положить в `.codex/config.toml` настройку:

```toml
[mcp_servers.secret_drop_url]
command = "/absolute/path/to/python3"
args = ["-I", "/absolute/path/to/checkout/research/elicitation-url-pilot/stdio_probe.py"]
```

В новом чате вызвать только `secret_drop_url.probe_url` с `{}`. Дальше проверить переход и статусы по процедуре выше. [Настройка MCP для проекта](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
