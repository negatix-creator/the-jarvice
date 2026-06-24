# Реестр инфраструктуры

> Последнее обновление: 2026-06-19
> Ответственный: Friday

## Машины

| # | Имя | IP | OS | Железо | Назначение | SSH доступ | Статус |
|---|------|-----|-----|--------|------------|------------|--------|
| 1 | **Ноутбук — Вадим** | localhost / 192.168.1.144 (WiFi) | macOS 26.5.1 (Tahoe) | Apple M2, 16 GB RAM, 460 GB SSD | Основной хост OpenClaw, все боты, Ollama | — | ✅ Активен |
| 2 | **allkaip** (VPS) | 78.17.56.204 | Ubuntu 22.04.2 LTS | 2 vCPU, 2 GB RAM, 30 GB SSD (расширен 22.05) | WireGuard сервер, MTProto proxy (TLS), The Jarvice тесты | `root@78.17.56.204` ✅ key auth | ✅ Активен, uptime 56 дней |
| 3 | **Fornex — Quentin** | 162.248.163.139 | Ubuntu 24.04 LTS | 4 vCPU @ 3.8 GHz, 16 GB RAM, 40 GB NVMe | Экспериментальная LLM для обезличивания | ❌ Пароль не подходит | ⚠️ Неактивен, аренда до ~07.04.2026 (истекла?) |
| 4 | **Keenetic Giga** (роутер) | 192.168.1.1 | Keenetic OS | — | Домашний роутер, WireGuard клиент, DHCP, DNS-proxy | RCI API (web 192.168.1.1, admin) | ✅ Активен |
| 5 | **Сервер шефа (Дмитрий)** | 2.58.65.124 (269868.fornex.cloud) | Ubuntu 24.04.4 LTS | 2 vCPU, 3.8 GB RAM, 40 GB SSD | Jarvis + Ultron для Дмитрия, OpenClaw, Ollama | `root@2.58.65.124` (Keychain: `chef-server-ssh`) | ✅ Активен, uptime 13 дней |
| 6 | **Сервер Алексея (Titov)** | 162.248.164.75 (286314.fornex.cloud) | Ubuntu 24.04.4 LTS | 4 vCPU, 7.8 GB RAM, 50 GB SSD (76% занято) | OpenClaw (3 агента), Ollama, nginx, X-UI, xray, PostgreSQL, Docker | `root@162.248.164.75` (Keychain: `alexey-server-ssh`) | ✅ Активен |
| 7 | **Сервер Мурада (бастион)** | 213.142.146.64 | Ubuntu 24.04.4 LTS | 1 vCPU Xeon E5-2695 v3, 961 MB RAM, 20 GB SSD (27% занято) | Jump-сервер Паши, reverse tunnel на мак Мурада | `root@213.142.146.64` (Keychain: `murad-server-ssh`, port 22) | ✅ Активен |
| 8 | **Мак Мурада** | 192.168.31.89 (за NAT, через бастион :2722) | macOS 14.4.1 (Sonoma) | Apple M1, 16 GB RAM, 460 GB SSD (7%) | OpenClaw 2026.6.8 + @Jeeves_and_Wooster_bot, The Jarvice, Ollama | `murad@localhost:2722` через бастион (Keychain: `murad-server-ssh`) | ✅ Настроен |
| 8 | **192.168.1.143** | 192.168.1.143 | Unknown | Unknown | Локальное устройство | ❌ No route to host | ❓ Неизвестно |
| 9 | **82.202.137.142** | 82.202.137.142 | Unknown | Unknown | Unknown | ❌ Permission denied (publickey) | ❓ Unknown |
| 10 | **Fornex — Dilhabibullina** | 130.17.4.116 (326652.fornex.cloud) | Ubuntu 24.04.4 LTS | 2 vCPU, 7.8 GB RAM, 50 GB SSD | OpenClaw (Jarvis), Ollama, лендинг | `root@130.17.4.116` (Keychain: `fornex-130-17-4-116-ssh`) | ✅ Активен, развёрнут 23.06.2026 |

---

## Сервисы по машинам

### Ноутбук — Вадим (localhost)
- **OpenClaw** 2026.6.1 — 6 агентов (Friday, Jarvis, Ultron, Edith, Argo, Hera)
- **Ollama** — локальные модели (qwen2.5:7b, qwen2.5:14b, glm-5.1:cloud)
- **Happ (sing-box)** — VPN клиент (процесс запущен, utun0 активен, но WG handshake устарел)
- **Keychain** — хранение кредов (keenetic-admin, Exchange, Telegram боты)
- **Brain Ingest** — cron 2x/день (03:00, 15:00)
- **Nightly Backup** — cron 04:00 MSK, 10 бэкапов ротация, ~6.8 GB каждый
- **Security Watchdog** — heartbeat проверки

### allkaip (VPS 78.17.56.204)
- **WireGuard** — интерфейс `allk`, порт 443, peer 10.66.66.1/24
- **MTProto Proxy** — Docker контейнер `ammnt/mtproxy:slim`, TLS обфускация (cloudflare.com), порт 64471→3478
- **The Jarvice** — v0.2.1 тестировался 21.05 (требовал расширения диска)
- **Диск:** 15 GB (из 30 GB), 56% занято

### Сервер шефа Дмитрия (2.58.65.124)
- **OpenClaw** 2026.6.1 — 2 бота (Ultron + Jarvis), порт 18789
- **Ollama** — 4 cloud модели (glm-5.2:cloud, glm-5.1:cloud, deepseek-v4-pro:cloud, kimi-k2.6:cloud) + nomic-embed-text
- **Telegram:** @ultron_crazy_bot (DevOps), @tdm_personal_asistant_bot (Jarvis/executive)
- **Python venv:** exchangelib, playwright+chromium, natasha, whisper, keyrings.alt
- **PII pipeline** (7 скриптов) + Teams (11 скриптов)
- **AllowFrom:** 224589523 (Дмитрий), 130110590 (Вадим), 8586243548 (доп.)
- **Диск:** 18 GB занято из 40 GB (49%)
- **Открытые вопросы:** Exchange/Teams креды (ждёт от шефа), cron jobs (нужен pairing), Brain (Фаза 2)

### Сервер Алексея Titov (162.248.164.75)
- **OpenClaw** (ClawdTitov user) — 3 агента (main, devops, marketing), порт 18789
- **Ollama** — 5 моделей (glm-5.2:cloud, glm-5.1:cloud, deepseek-v4-pro:cloud, kimi-k2.6:cloud, nomic-embed-text)
- **nginx** — titovtech.ru (HTTP/HTTPS)
- **X-UI + xray** — VPN прокси (порт 8443, xray на 11111 и 62789)
- **PostgreSQL 16** — БД для аналитики
- **Docker** — containerd запущен
- **fail2ban** — защита от брутфорса
- **ufw** — 22, 80, 443, 3456, 54987 открыты
- **24 скилла** (agent-doctor, agent-forge, deploy-agent, ru-text, yandex-direct и др.)
- **Диск:** 36 GB занято из 50 GB (76%)
- **Крон:** disk-maintenance каждые 6 часов
- **Research:** скопировано 24 скилла в `research/alexey-server-skills/`

### Keenetic Giga (192.168.1.1)
- **WireGuard клиент** — интерфейс Wireguard0, 10.66.66.2/32

### Fornex — Dilhabibullina (130.17.4.116)
- **OpenClaw** 2026.6.9 — 1 агент (main/Jarvis), порт 18789
- **Ollama** — cloud-модели через API ключ (подписка от Крис) + nomic-embed-text
- **UFW** — 22, 80, 443 открыты
- **fail2ban** — защита от брутфорса
- **Swap** — 2 GB
- **Timezone** — Europe/Moscow
- **Telegram бот** @MIT_assistant1_bot — активен, polling работает
- **Owner:** Diana (@dilhabibullina, ID: 803269189)
- **Workspace:** SOUL.md, USER.md, AGENTS.md, IDENTITY.md, MEMORY.md
- **Модель:** glm-5.2:cloud primary, glm-5.1:cloud fallback
- **Статус:** ✅ Полностью развёрнут 25.06.2026

### Keenetic Giga (192.168.1.1) — continued
- **WireGuard клиент** — интерфейс Wireguard0, 10.66.66.2/32 (continued)
- **PPPoE** — основной интернет
- **DNS-proxy** + domain-list для маршрутизации
- **WiFi 6** — MAC Вадима 192.168.1.144, RSSI -74dBm
- **Сегменты:** Bridge0 (Home), Bridge1 (192.168.1.0/24), Bridge2 (IoT)

---

## Сетевая архитектура

```
[Интернет] ←→ PPPoE ←→ [Keenetic Giga 192.168.1.1]
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              [MacBook]    [IoT]      [WG tunnel]
           192.168.1.144  Bridge2    10.66.66.2 ←→ 78.17.56.204 (VPS)
                    │                                  │
                    │                          ┌───────┼───────┐
                    │                    [WG: 443]   [MTProto: 64471]
                    │                    [allk iface]  [Docker proxy]
                    │
              [Happ VPN] ← sing-box → utun0


[Интернет] ←→ Fornex Cloud ←→ [Сервер шефа 2.58.65.124]
                                    │
                          ┌─────────┼─────────┐
                          │         │         │
                    [OpenClaw]  [Ollama]  [PII pipeline]
                    Ultron+Jarvis  4 модели   7 скриптов
```

---

## Ключи и креды (ссылки, НЕ значения)

| Ресурс | Keychain service | Примечание |
|--------|-----------------|------------|
| Keenetic admin | `keenetic-admin` | Логин: admin |
| VPS allkaip SSH | SSH key `~/.ssh/id_ed25519` | root@78.17.56.204 |
| VPS шефа SSH | `chef-server-ssh` | root@2.58.65.124, пароль в Keychain |
| VPS Алексея SSH | `alexey-server-ssh` | root@162.248.164.75, пароль в Keychain |
| VPS Мурада SSH | `murad-server-ssh` | root@213.142.146.64:22, пароль в Keychain (пользователь murad не существует, только root) |
| MTProto secret | `/opt/mtproto/secret` на VPS | dd-secret (ee-prefix, TLS mode) |
| Exchange EWS | Keychain | NTLM auth |
| Telegram bots | Keychain | Токены ботов |
| Шефа боты | Bot tokens | @ultron_crazy_bot, @tdm_personal_asistant_bot |
| Fornex Dilhabibullina SSH | `fornex-130-17-4-116-ssh` | root@130.17.4.116, пароль в Keychain |
| Fornex Dilhabibullina Ollama | API key в /root/.ollama/.env | Cloud-модели, подписка от Крис |
| GitHub | SSH key | Port 443 (ssh.github.com) |

---

## Неизвестные хосты (требуют уточнения)

| IP | Примечание |
|----|-----------|
| **213.142.146.64** | Host key changed — возможно переустановлен. Чей? |
| **82.202.137.142** | SSH key в known_hosts, но доступ запрещён. Чей? |
| **192.168.1.143** | Локальный IP, сейчас offline. Что за устройство? |
| **Fornex Quentin** | Аренда истекла ~07.04.2026. Продлевать? |
| **Мурада сервер** | IP уточнить у Вадима. The Jarvice через setup.sh? |

## Репозитории и исходный код

| Репозиторий | Владелец | Описание | Дата копирования |
|-------------|----------|----------|----------------|
| https://github.com/problemgoout-ops/deploy-agent | Алексей Титов | Скилл деплоя агентов (v2.1, 1605 строк, 40 тестов) | 2026-06-05, 2026-06-18 |
| Сервер Алексея (162.248.164.75) skills/ | Алексей Титов | 24 скилла скопировано в `research/alexey-server-skills/` | 2026-06-18 |
| https://github.com/negatix-creator/the-jarvice | Алексей (negatix) | Setup script для The Jarvice | 2026-06-17 |

---

## Люди и привязка к машинам

| Человек | Telegram ID | Машина | Роль |
|---------|-------------|--------|------|
| **Вадим Миженский** | 130110590 | Ноутбук (macOS M2) | Owner, DevOps, администратор |
| **Дмитрий (Михалыч)** | 224589523 | Сервер шефа (2.58.65.124) | Шеф, пользователь Jarvis |
| **Доп. пользователь** | 8586243548 | — | Доступ к ботам шефа |
| **Мурад Салаватов** | 51291515 | Мак Мурада (192.168.31.89 через бастион) | CPO ФСК, The Jarvice пользователь |
| **Алексей Титов** | 413641149 (@titov_8) | 162.248.164.75 (Fornex) | GTM партнер, deploy-agent автор |
| **Диляра Хабибуллина** | 803269189 (@dilhabibullina) | 130.17.4.116 (Fornex) | Продакт, клиент |
| **Крис** | — | — | Предоставила Ollama подписку для cloud-моделей |

---

## Дежурные проверки (heartbeat)

1. **Config integrity** — SHA-256 baseline
2. **Listening ports** — vs baseline
3. **Non-loopback listeners** — алерт если новые
4. **LaunchAgents** — новые persistence = алерт
5. **Canary files** — integrity check
6. **Gateway alive** — OpenClaw process
7. **Ollama alive** — local models
8. **VPN (Happ)** — процесс запущен
9. **MTProto proxy** — TCP порт 64471 доступен
10. **VPS disk** — < 90%
11. **Disk space** — < 90% на маке
12. **Cron check** — doctor validates

---

## История изменений

| Дата | Машина | Изменение |
|------|--------|-----------|
| 2026-03-17 | Fornex Quentin | Развёрнут Ubuntu 24.04, 16GB RAM, Швеция |
| 2026-04-13 | Keenetic Giga | Настроен WG клиент, MTProto, DNS-proxy |
| 2026-04-16 | Keenetic Giga | WG порт изменён 64471→443, маршрутизация |
| 2026-05-13 | VPS allkaip | MTProto proxy upgraded до TLS mode (ammnt/mtproxy:slim) |
| 2026-05-21 | VPS allkaip | The Jarvice v0.2.1 тест (265/267 тестов) |
| 2026-05-22 | VPS allkaip | Диск расширен 9.8GB → 30GB, без перезагрузки |
| 2026-06-04 | Сервер шефа | Развёрнут OpenClaw + Ollama + 2 бота (Ultron, Jarvis) |
| 2026-06-04 | Сервер шефа | PII pipeline + Teams scripts скопированы, Python venv настроен |
| 2026-06-14 | Сервер шефа | Ollama обновлён до glm-5.2:cloud |
| 2026-06-18 | Реестр | Создан INFRASTRUCTURE_REGISTRY.md, скилл remote-connect |
| 2026-06-18 | Реестр | Добавлен сервер шефа Дмитрия (#5) |
| 2026-06-18 | Сервер Алексея | Подключение, discovery, скопировано 24 скилла |
| 2026-06-18 | Реестр | Добавлен сервер Алексея Titov (#6), секция репозиториев |
| 2026-06-18 | Research | Создан скилл research-loot, обновлён create-bot (6 новых секций) |
| 2026-06-23 | Fornex Dilhabibullina | Развёрнут OpenClaw + Ollama + cloud-модели (10/10 smoke tests ✅) |
| 2026-06-25 | Fornex Dilhabibullina | Telegram бот @MIT_assistant1_bot подключён, owner 803269189, workspace создан |