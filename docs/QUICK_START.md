# Быстрый старт The Jarvice

Пошаговое руководство для новых пользователей — от установки до первой сводки.

---

## Предварительные требования

| Ресурс | Минимум | Примечание |
|--------|---------|------------|
| macOS | 13+ (Ventura) | Linux планируется в v0.2.1 |
| Python | 3.10+ | Устанавливается автоматически |
| Node.js | 20+ | Устанавливается автоматически |
| Свободное место | 12 ГБ | Для модели (~9 ГБ) + данные |
| Интернет | Обязательно | Для загрузки зависимостей и модели |
| Ollama | Последняя версия | Устанавливается автоматически |
| Telegram бот | Токен от @BotFather | Для доставки сводок |

---

## Шаг 1. Установка

### Вариант A: Автоматическая установка (рекомендуется)

```bash
git clone <repo-url> && cd the-jarvice
bash setup/setup.sh
```

Скрипт `setup.sh` **идемпотентный** — его можно запускать повторно без риска. Он выполнит:

1. Проверку ОС (macOS обязательно)
2. Установку Homebrew (если нет)
3. Установку Python 3.10+ и Node.js 20+ через Homebrew
4. Установку Ollama и запуск сервиса
5. Проверку свободного места (≥ 12 ГБ)
6. Создание виртуального окружения `~/.the-jarvice/venv/`
7. Установку Python-зависимостей из `pyproject.toml`
8. Загрузку модели `qwen3:14b` (~9 ГБ)
9. Создание структуры директорий с правильными правами
10. Копирование шаблона конфигурации
11. Установку CLI-команды `the-jarvice`

> **Совет:** Добавьте алиас в shell-профиль:
> ```bash
> echo 'alias the-jarvice=~/.the-jarvice/venv/bin/the-jarvice' >> ~/.zshrc
> source ~/.zshrc
> ```

### Вариант B: Ручная установка

```bash
git clone <repo-url> && cd the-jarvice
python3 -m venv ~/.the-jarvice/venv
source ~/.the-jarvice/venv/bin/activate
pip install -e .
```

---

## Шаг 2. Настройка

### Быстрая настройка (3 поля)

Для первого запуска достаточно трёх полей — email, пароль и токен Telegram-бота:

```bash
the-jarvice configure --quick
```

Мастер запросит:
1. **Email** — адрес корпоративной почты (Exchange-сервер определится автоматически)
2. **Пароль** — сохраняется в macOS Keychain, **никогда** не записывается в конфиг
3. **Telegram бот-токен** — получите у [@BotFather](https://t.me/BotFather)

> Chat ID определится автоматически при наличии отправленного `/start` боту.

### Полная настройка

```bash
the-jarvice configure
```

Полный мастер включает дополнительно:
- **Teams** — IC3-токен (из DevTools браузера)
- **Модель** — выбор Ollama-модели и проверка загрузки
- **Расписание** — часовой пояс, время утренней/вечерней сводок

### Переконфигурация отдельного сервиса

```bash
# Обновить пароль Exchange
the-jarvice configure --reauth exchange

# Обновить IC3-токен Teams
the-jarvice configure --reauth teams

# Обновить токен Telegram-бота
the-jarvice configure --reauth telegram

# Сменить модель Ollama
the-jarvice configure --reauth model
```

### Пропуск ненужных шагов

```bash
the-jarvice configure --skip-exchange   # Без Exchange
the-jarvice configure --skip-teams      # Без Teams
the-jarvice configure --skip-telegram   # Без Telegram
the-jarvice configure --skip-model      # Без загрузки модели
```

---

## Шаг 3. Первый запуск

### Проверка диагностики

Перед первым запуском проверьте, что всё настроено:

```bash
the-jarvice doctor
```

Ожидаемый результат:
```
✅ Python 3.14.0
✅ Ollama running (localhost:11434)
✅ Model qwen3:14b downloaded (9.3 GB)
✅ Keyring accessible (macOS Keychain)
✅ Config valid (~/.the-jarvice/config.yaml)
✅ Exchange connected (mail.corp.ru, 23 folders)
✅ Teams token present
✅ Telegram bot connected (@jarvice_bot)
✅ Disk space (142 GB free)
✅ OpenClaw running (v2026.4.5)
✅ PII Permissions correct
✅ Cron schedule active (morning, evening)

✅ All 12 checks passed!
```

> Если какие-то проверки не прошли — `doctor` покажет, что именно нужно исправить.

### Пробный запуск (без отправки в Telegram)

```bash
the-jarvice run --once --dry-run
```

Команда выполнит весь пайплайн (скрейпинг → анонимизация → генерация сводки), но **не отправит** результат в Telegram. Вместо этого вы увидите превью сводки.

### Реальный запуск

```bash
the-jarvice run --once
```

С подробным выводом:
```bash
the-jarvice run --once --verbose
```

---

## Шаг 4. Настройка расписания

### Включение автоматических сводок

```bash
# Утренняя сводка в 07:00, вечерняя в 19:00 (по умолчанию)
the-jarvice enable

# Свой график
the-jarvice enable --morning 08:00 --evening 18:30 --weekly
```

Команда создаёт записи в системном `crontab` с маркером `# the-jarvice-managed`. Все логи пишутся в `~/.the-jarvice/logs/cron.log`.

### Отключение расписания

```bash
the-jarvice disable
```

---

## Структура директорий

После установки и настройки:

```
~/.the-jarvice/
├── config.yaml              # Конфигурация (единственный источник истины)
├── state.json               # Курсоры скрейперов (автоматически)
├── venv/                    # Python-виртуальное окружение
├── config/
│   └── config_schema.yaml   # Шаблон конфигурации
├── data/
│   ├── exchange/            # Данные Exchange
│   ├── teams/               # Данные Teams
│   └── pii/
│       ├── RED/             # Исходные данные с ПДн (chmod 700)
│       │   └── mapping.json # Маппинг масок → реальные значения
│       └── GREEN/           # Анонимизированные данные
├── logs/                    # Логи приложения
│   └── cron.log             # Лог cron-запусков
├── memory/                  # Сохранённые сводки
└── index/                   # Поисковый индекс
```

---

## Устранение проблем

### `the-jarvice doctor` — первая диагностика

```bash
# Обычная проверка
the-jarvice doctor

# Подробный вывод
the-jarvice doctor --verbose

 JSON-формат для автоматизации
the-jarvice doctor --json

# Автоматическое исправление (где возможно)
the-jarvice doctor --fix
```

12 проверок:
1. **Python** — версия 3.10+
2. **Ollama** — запущен и доступен
3. **Model** — модель загружена
4. **Keyring** — доступность Keychain/keyring
5. **Config** — валидность `config.yaml`
6. **Exchange** — подключение к серверу
7. **Teams** — наличие и валидность IC3-токена
8. **Telegram** — подключение бота
9. **Disk** — свободное место (≥ 12 ГБ)
10. **OpenClaw** — установлен и запущен
11. **PII Permissions** — права доступа к RED-директории
12. **Cron** — активность расписания

### Частые проблемы

#### Ollama не запущена

```bash
ollama serve
# или
the-jarvice doctor --fix
```

#### Модель не загружена

```bash
ollama pull qwen3:14b
ollama list  # проверить
```

#### Keychain/Keyring не работает

```bash
# Тест keyring
python3 -c "import keyring; keyring.set_password('test', 'test', 'ok'); print(keyring.get_password('test', 'test'))"

# На Linux: установите libsecret
sudo apt install libsecret-1-0

# Альтернатива: используйте переменные окружения
export JARVICE_EXCHANGE_PASSWORD="ваш-пароль"
export JARVICE_TEAMS_PASSWORD="ic3-токен"
export JARVICE_TELEGRAM_BOT_PASSWORD="бот-токен"
```

#### Exchange не подключается

- Проверьте URL сервера (например, `https://mail.corp.ru/EWS/Exchange.asmx`)
- Убедитесь, что Basic Auth или NTLM включены на сервере Exchange
- OAuth (Microsoft 365) пока не поддерживается — ожидается в v0.3.0
- Переконфигурируйте: `the-jarvice configure --reauth exchange`

#### IC3-токен Teams истёк

Токены IC3 живут ~24 часа. Обновите:

```bash
the-jarvice configure --reauth teams
```

Для извлечения нового токена:
1. Откройте `teams.microsoft.com` в браузере
2. F12 → Network → фильтр `teams.microsoft.com`
3. Найдите заголовок `Authorization: Bearer <token>`
4. Скопируйте токен целиком

#### Не хватает места на диске

```bash
# Используйте меньшую модель
# В ~/.the-jarvice/config.yaml:
models:
  primary: "qwen2.5:7b"   # ~4.5 ГБ
  fallback: "qwen2.5:3b"  # ~2 ГБ

ollama pull qwen2.5:7b
```

---

## Что дальше?

- **Полная документация:** [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Безопасность:** [docs/SECURITY.md](SECURITY.md) 
- **Конфигурация:** [docs/configuration.md](configuration.md)
- **Установка:** [docs/installation.md](installation.md)
- **Разработка:** [CONTRIBUTING.md](../CONTRIBUTING.md)