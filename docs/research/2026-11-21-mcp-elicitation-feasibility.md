# Исследование: встроенные запросы пользователя и защищённый ввод Secret Drop

**Дата:** 21.11.2026
**Состояние:** эксперимент, **не принят в релиз**
**Владелец:** [shzk/secret-drop](https://github.com/shzk/secret-drop), ветка `research/mcp-elicitation-20261121`
**Задача:** TickTick `6b01a4b48f0887ff0a4c82e8`
**База:** `main@ad14933b7cdc94a6bd574bfbf476a1a03226f32c`, принятый Secret Drop Codex `0.6.0` не изменён.

## 1. Вопрос и проверяемое поведение

Пользователь показал встроенную карточку «Вопрос» внутри ChatGPT и спросил, нельзя ли использовать аналогичное окно вместо отдельного модального окна Secret Drop на macOS. **Скриншот подтверждает только интерфейс пользователя, но не конкретный транспорт или API вызова**. Не следует по одному изображению заявлять, что его реализовал `request_user_input`, MCP Elicitation или MCP Apps.

Цель — по возможности встроить **объяснение, выбор назначения и подтверждение** в интерфейс ChatGPT/Codex, не передавая значения секретов в модель, MCP Form, логи, tool arguments или незащищённую веб-форму.

## 2. Проверенные факты и актуальные спецификации

| Утверждение | Основание | Уровень доказательств |
| --- | --- | --- |
| MCP Elicitation поддерживает `form` (структурированные ответы) и `url` (чувствительное действие вне MCP-клиента). **Form MUST NOT** запрашивать API-ключи, пароли, access tokens и платёжные credentials; для этого MUST использоваться URL mode. | [MCP specification 2026-07-28: Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) § User Interaction Model | **Нормативная спецификация** |
| URL mode не возвращает значение ключа по MCP, но **принятие URL не подтверждает завершение сохранения**. Клиент должен показывать полный URL и запрашивать согласие; сервер — связывать сессию с подлинной учётной записью пользователя, не вкладывать секрет/PII в URL и защищаться от phishing. | [MCP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) § URL Mode, Security Considerations | **Нормативная спецификация** |
| В 2025-11-25 Elicitation объявляется в `initialize.capabilities.elicitation`; в 2026-07-28 — в `_meta.io.modelcontextprotocol/clientCapabilities` каждого запроса. В URL-mode старой схемы используется `elicitationId`; в актуальной 2026-07-28 этот идентификатор не требуется. | [MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation), [MCP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation) | **Нормативная спецификация**, разные версии |
| Codex app-server документирует `tool/requestUserInput` (1–3 коротких вопроса, experimental) и отдельный канал `mcpServer/elicitation/request` для Form/URL. Наличие маршрута в app-server **не доказывает**, что любое средство расширения может вызвать именно UI со скриншота в каждой версии Desktop. | [openai/codex app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md) и [elicitation.rs](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/elicitation.rs) | **Исходники/документация**, реальный Desktop host не проверен |
| OpenAI Plugins рекомендует MCP Apps для UI-ресурсов, которые отображаются в iframe ChatGPT. Совместимость зависит от хоста; нельзя автоматически считать UI безопасным каналом получения секретов лишь из-за iframe. | [OpenAI — Add UI to your MCP server](https://developers.openai.com/plugins/build/chatgpt-ui), [MCP server and UI quickstart](https://developers.openai.com/plugins/build/app-quickstart) | **Официальная документация**, host E2E отсутствует |
| Codex Secret Drop v0.6.0 использует собственный stdio JSON-RPC-сервер с `PROTOCOL = "2025-06-18"`; его единственный MCP tool — `request_secret`, который открывает безопасный AppKit-dialog. Реализации server-initiated `elicitation/create` в текущем плагине нет. | [Текущий исходник](https://github.com/shzk/secret-drop/blob/main/codex/secret-drop/server/mcp_server.py) | **Непосредственно прочитан код в main** |

**Вывод для скриншота:** похожие встроенные формы реально поддерживаются несколькими интерфейсными механизмами. Однако определить, **какой именно породил показанный скриншот**, только по изображению нельзя. `request_user_input` — внутренняя экспериментальная поверхность Codex; **публичного подтверждённого способа** вызвать её напрямую из стороннего MCP plugin не найдено. Стороннему MCP предпочтительно использовать стандартный `elicitation/create`, только если клиент явно объявляет поддержку.

## 3. Сравнение вариантов

| Вариант | Пользовательский интерфейс | Где поступает значение ключа | Что придётся менять | Вывод |
| --- | --- | --- | --- | --- |
| **A. Codex Form Elicitation только для несекретного подтверждения + существующий AppKit** | Встроенное согласование цели и назначения **если host поддерживает Form**, затем знакомое защищённое окно | Только локальный AppKit-процесс, как в v0.6.0; **никогда не в Form** | Уточнить согласование состояния двух окон и MCP версий, проверить host support, fallback и отмену | **Лучший кандидат для минимального пилота Codex**. Может увеличить число кликов; не заменяет полностью native window |
| **B. MCP URL Elicitation для секретного ввода** | Клиент показывает ссылку и полный домен; секрет вводится в браузере вне MCP | HTTPS-сервер с верифицированной сессией пользователя и безопасным хранением/назначением | Авторизация OAuth/сессия, user binding, CSRF/phishing defense, HTTPS, state/retry, storage policy, отдельные сервисные решения | **Потенциально подходит для ChatGPT Web**, но **не вводить в текущий проект без отдельного архитектурного согласования** |
| **C. MCP Apps UI в ChatGPT** | Нативно отображаемый iframe-компонент рядом с перепиской | Зависит от backend/bridge: **сам iframe не гарантирует** недоступность значения клиенту, модели и логам | Отдельный MCP Apps компонент, инструменты, auth, проверенный мост данных/логирования | Подходит для **несекретного UI** и метаданных; ввод реальных ключей требует отдельного аудита trust boundary, не равен URL Elicitation |
| **D. Прямой вызов Codex `request_user_input` из стороннего плагина** | Возможна карточка, похожая на скриншот | Ответы идут в хостовый механизм запроса | Нет доказанного публичного API для внешнего MCP-плагина | **Не считать доступным**, пока не будет документированного интерфейса и host E2E |

### Принятые границы

- Нельзя передавать даже тестовый *реальный* API-ключ через Form, `toolInput`, `structuredContent` или `ui/update-model-context`.
- Модель может предложить `config/.env.local` или GitHub environment, но **доверенная часть** должна вычислить/проверить полный адрес, а пользователь — его подтвердить.
- Для внешнего URL клиент показывает домен и получает согласие; сервер проверяет принадлежность операции тому же пользователю. Одноразовые URL с полномочием доступа, секреты в query string и неаутентифицированный endpoint неприемлемы.
- URL mode в `2026-07-28` может потребовать возобновления/повтора запроса после внесистемного ввода: `accept` не подтверждает готовность ключа или успешное сохранение.
- При отсутствии поддержки Elicitation — **fail closed или использовать уже принятый native AppKit v0.6.0**, не подставляя настоящий секрет в chat/tool arguments.
- Не вводить новый продовый MCP, базу, SecretStore, web-сервис, туннель или платный API без отдельного решения. Прежний Claude plugin и экспериментальный OpenCode adapter не затрагиваются.

## 4. Воспроизводимый офлайн-прототип

[Прототип без сервера](../../research/elicitation-fixture/wire_shapes.py) и [7 тестов](../../research/elicitation-fixture/test_wire_shapes.py) демонстрируют **только форматы сообщений**:

- `confirmation_form()`: два несекретных поля `destination` и `confirm`, никаких паролей/токенов;
- `credential_url_request()`: фиктивный HTTPS URL `secrets.example.invalid`, не открывается, не содержит значения; вариант 2025 с `elicitationId`, вариант 2026 без него;
- `capability_advertisement()`: различие старой и новой схемы;
- `model_visible_result()`: только имя переменной и статус.

**Команда:**
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s research/elicitation-fixture -v
```
**Свидетельство:** 7/7 PASS на Mac (изолированный worktree), `git diff --check` PASS. Ни клиент Codex, ни ChatGPT Web, ни настоящий OAuth/HTTPS сервис этим тестом не запускались. Это **protocol-fixture PASS**, **НЕ host UI E2E**.

## 5. Следующий осмысленный эксперимент и условие остановки

**Рекомендуемый следующий этап — только при отдельном разрешении на реализацию:**
1. На **этой ветке** добавить к экспериментальному *отдельному* MCP tool вызов **Form Elicitation исключительно для несекретного выбора/подтверждения**, оставив текущий `request_secret`/AppKit неизменным.
2. Через **Codex Desktop**, а не `codex exec` (в exec Elicitation может быть автоматически отменено), проверить наличие объявленной Form capability, показ реального встроенного запроса, decline/cancel, корректное возобновление и отсутствие значения в событиях. Сначала только фиктивные метаданные.
3. Если Form не поддерживается хостом/режимом, зафиксировать ограничение и завершить пилот без обходных неофициальных UI API.
4. Для URL-mode/ChatGPT Web **сначала** принять отдельную модель доверия и архитектурное решение об авторизованном HTTPS endpoint. Пока этого нет, только статическое исследование спецификации, никаких real-key и network E2E.

**Обновлённый результат пилота 21.11.2026:** **PASS для встроенной несекретной MCP Form в Codex Desktop**, подтверждён собственным скриншотом пользователя и реальным тестом app-server. Через проектный `.codex/config.toml` инструмент дважды не обнаруживался; после временной пользовательской регистрации стал доступен и показал встроенную форму, подтвердил фиктивный путь. Временная регистрация удалена, конфигурация Codex восстановлена побайтово, плагины на `main` не изменены. [Полный протокол E2E и отката](2026-11-21-codex-form-host-pilot.md). **Остаётся HOLD для переноса ввода значений ключей в Form/MCP Apps** и для создания публичного URL-ориентированного сервиса без отдельного решения. Переход от исследовательского пилота к продуктовой реализации Secret Drop — отдельное изменение, не авторизованное этим тестом.

### Дополнительная проверка с фиктивным значением (21.11.2026)

[Отдельный протокол: Form marker vs protected intake](2026-11-21-public-marker-vs-secure-intake.md). При реальном app-server Elicitation публичный синтетический маркер из Form **попал в MCP tool result** (`PUBLIC_DEMO_MARKER_IN_TOOL_RESULT=True`), что подтверждает небезопасность такого канала для ключей. Синтетическая связка **Form только для назначения → реальный writer Secret Drop с AppKit-mock → `.env.local` 0600 → status-only** прошла; фактическое появление двух окон подряд в Desktop не проверялось. Тесты: 18/18 исследовательских и 36/36 действующего v0.6 PASS. **Решение HOLD для ключей в Form остаётся в силе.**

## Проверяемые основные источники

1. [MCP Elicitation, версия 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
2. [MCP Elicitation, версия 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)
3. [MCP TypeScript SDK Elicitation](https://ts.sdk.modelcontextprotocol.io/v2/servers/elicitation)
4. [OpenAI Codex app-server protocol](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md)
5. [OpenAI Codex MCP Elicitation implementation](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/elicitation.rs)
6. [OpenAI Plugins: MCP UI](https://developers.openai.com/plugins/build/chatgpt-ui)
7. [OpenAI Plugins: Build an MCP server](https://developers.openai.com/plugins/build/mcp-server)

**Research-only:** до принятия пилота эти выводы не изменяют релиз `0.6.0`, его установленную копию, канонические инструкции или upstream PR #2.
