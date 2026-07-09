# Ревью лендинга The Jarvice

**Файл:** `index.html` (563 строки)
**Версия лендинга:** v0.2.1
**Актуальная версия продукта:** v0.4.0
**Дата ревью:** 2026-06-19

---

## Часть 1. Содержание (контент)

### 1.1. Версия — обязательное обновление

**Сейчас:** `v0.2.1` в eyebrow hero и в footer.
**Должно быть:** `v0.4.0`.
**Где:** строки `<span class="eyebrow">🔒 Privacy-first · v0.2.1</span>` и `Privacy-first AI · v0.2.1`.

> Заменить на `v0.4.0`. Добавить под-лейбл `9 500+ LOC · 267 тестов · 4 деплоя` — это социальное доказательство зрелости.

---

### 1.2. Hero — недостаточно конкретика

**Сейчас:**
- H1: «AI-помощник для безопасной работы с корпоративным контекстом» — слишком абстрактно.
- Lede: «Собирает важное из почты, чатов и документов…» — похоже на любой summary-tool.

**Предлагаю:**
- **Eyebrow:** `🔒 Privacy-first · v0.4.0 · 6 агентов · 27 автоматизаций`
- **H1:** «AI-штаб для руководителя, который не отправляет данные в чужие облака» — коллоквиально, с позиционированием.
- **Lede:** «Jarvice за 5 минут готовит ежедневную сводку из Exchange, Teams и документов — с обезличиванием на вашей машине. Персональные данные не покидают контур.» — конкретные системы + конкретный результат + гарантия.
- **Добавить третий badge:** «27 крон-джобов под капотом» — уникальное торговое предложение, которое никто не копирует.

---

### 1.3. Stats — числа морально устарели

**Сейчая таблица статов не отражает реальность:**

| Сейчас | Должно быть | Обоснование |
|--------|-------------|-------------|
| 3 модели | **3 модели в multi-pass** | Уточнить роли: DeepSeek → GLM → Kimi |
| ≥95% точность | **≥95% после 5-этапной валидации** | Это не одна проверка, это цикл |
| 100% анонимизация | **100% в Private Mode, NER qwen3:14b + regex** | Конкретика = доверие |

**Добавить новые stats (рядом, 2-й ряд или заменить):**
- `6` специализированных агентов
- `937` атомов знаний в The Brain
- `4` клиентских деплоя
- `27` крон-автоматизаций

> Эти цифры есть только у Jarvice. Это барьер для конкурентов.

---

### 1.4. PII Pipeline — не раскрыт вообще

**Проблема:** весь лендинг говорит «обезличивание», но не показывает КАК.

**Что добавить:** новый раздел «PII Pipeline» между `#problem` и `#security`.

**Контент блока:**
- Схема из 5 шагов (с визуализацией, см. Часть 2):
  1. **RED /** — оригиналы из Exchange/Teams хранятся локально
  2. **Anonymizer** — NER qwen3:14b + regex маскирует ФИО, даты, суммы, email
  3. **GREEN /** — обезличенный контекст готов к обработке
  4. **LLM Processing** — облачная модель работает только с масками
  5. **Deanonymizer** — восстановление оригиналов перед выводом в Telegram

- **Key message:** «LLM никогда не видит настоящих имён и цифр. Мы проверили это 267 тестами.»

---

### 1.5. Self-Validation Pipeline — не раскрыт

**Проблема:** в разделе «Три модели в разных ролях» описан упрощённый процесс. Не упомянуты:
- 5 этапов: генерация → проверка фактов → исправление (цикл до ≥95%) → консистентность → вывод
- Multi-pass: 3 модели последовательно, не параллельно
- Цикл исправления: если совпадение <95%, модель переделывает, не просто отбраковывает

**Что сделать:**
- Переименовать раздел `#pipeline` из «Контроль точности» в «Самовалидация: 5 этапов до ответа»
- Добавить визуал timeline/accordion с 5 этапами:
  1. Генерация ответа (модель 1 — DeepSeek)
  2. Проверка фактов (модель 2 — GLM)
  3. Исправление ошибок (цикл до ≥95%)
  4. Консистентность проверки (модель 3 — Kimi)
  5. Финальный вывод в Telegram

---

### 1.6. The Brain — отсутствует как концепция

**Проблема:** лендинг не упоминает The Brain — уникальную систему знаний.

**Что добавить:** новый раздел «The Brain — корпоративная память» (после `#pipeline`).

**Контент:**
- Obsidian-граф знаний с 16 типами атомов: person, product, decision, problem, insight, system, document, meeting...
- 7-фазная валидация с анти-галлюцинацией
- 937 атомов знаний — машинно-проверено
- RAG-поиск: BM25 + вектора, 4012 файлов индексировано
- 3 тира: Private (локально), Enhanced (облако, GREEN), Knowledge (The Brain RAG)

**Key message:** «Jarvice не придумывает ответы — он ищет в вашей корпоративной памяти.»

---

### 1.7. Режимы — названия устарели

**Сейчас:**
1. Локальный режим
2. Облачный режим
3. API-режим

**Должно быть (3 тира продукта):**
1. **Private Mode** — локально, 100% контроль, данные не покидают машину
2. **Enhanced Mode** — облачная обработка GREEN-данных, выше качество
3. **Knowledge Mode** — RAG на The Brain, история компании участвует в ответах

> Добавить в карточки: «Рекомендуем начать с Private Mode → перейти к Enhanced → подключить Knowledge».

---

### 1.8. Roadmap — морально устарела

**Сейчас:** 4 абстрактных шага с 2025-логикой.

**Должно быть:** 4 фазы с датами и статусами:

| Фаза | Название | Статус | Детали |
|------|----------|--------|--------|
| 1 | Private Mode MVP | ✅ Готово | Локальный деплой, PII pipeline, 6 агентов, 27 кронов |
| 2 | Enhanced Mode | ✅ Готово | Облачная обработка GREEN-данных, multi-pass валидация |
| 3 | Knowledge Mode | 🔄 В разработке | Интеграция The Brain, RAG, 16 типов атомов |
| 4 | Team Scale | 📅 Q3 2026 | Командное использование, shared agents, админ-панель |

**Добавить:**
- Инфо-блок: «Уже 4 деплоя: VPS, macOS партнёров, сервер заказчика, наш VPS»
- Badge CI/CD: «GitHub Actions · macOS + Ubuntu · авто-тестирование»

---

### 1.9. Агенты — не упомянуты

**Что добавить:** секция «6 специализированных агентов» (после `#security`).

**Список:**
- **Friday** — DevOps и безопасность
- **Jarvis** — executive copilot, сводки и рекомендации
- **Edith** — ассистент операционных задач
- **Ultron** — технический анализ и код
- **ARGO** — исследования и поиск
- **Hera** — координация и планирование

**Key message:** «Не один универсальный бот — а команда специалистов с доступом к разным системам.»

---

### 1.10. CTA и форма

**Сейчас:**
- Форма на Formspree с `YOUR_FORM_ID` — не работает.
- Только 3 пункта в CTA-list.

**Что улучшить:**
1. **Форма:** заменить Formspree на конкретный endpoint или убрать форму, оставив только Telegram-CTA.
2. **Добавить поле:** «Какой режим интересует?» (Private / Enhanced / Knowledge) — это квалификация лида.
3. **CTA-list дополнить:**
   - «Развёртывание за 10 минут через один скрипт»
   - «Демо на ваших данных — без отправки в облака»
4. **Добавить альтернативный CTA:** «Скачать Whitepaper» (PDF с описанием архитектуры) — для enterprise-лидов, которые не пишут в Telegram.
5. **Telegram-ссылка:** проверить `https://t.me/jarvice_ai` — работает?

---

### 1.11. Footer

**Сейчас:** `Privacy-first AI · v0.2.1 · ПДн не уходят в LLM`

**Должно быть:**
```
Privacy-first AI · v0.4.0 · jarvice.ru · jarvice.tech · jarvice.online
6 агентов · 27 автоматизаций · 937 атомов знаний · 4 деплоя
```

**Добавить:**
- Ссылки на домены (jarvice.ru, jarvice.tech, jarvice.online)
- GitHub-иконку (если репо публичный или есть demo-аккаунт)

---

### 1.12. SEO и мета-теги

**Добавить:**
```html
<meta property="og:title" content="The Jarvice — AI-штаб для руководителя, который не отправляет данные в чужие обла">
<meta property="og:description" content="6 специализированных агентов. PII pipeline с обезличиванием. 937 атомов знаний. Локальный, облачный и Knowledge-режимы.">
<meta property="og:image" content="...">
<meta name="twitter:card" content="summary_large_image">
```

---

## Часть 2. Визуал (дизайн)

### 2.1. Общая оценка текущего дизайна

**Сильные стороны:**
- Dark theme хорошо читается, premium-ощущение
- Orb с ring'ами создаёт фокус в hero
- Grid deco добавляет технологичности
- Структура секций логичная

**Слабые стороны:**
- Нет развития визуальной истории после hero — всё «плоские» карточки
- Roadmap выглядит как PowerPoint 2003
- Comparison table — скучная таблица Excel
- Нет микроанимаций на hover
- Mobile: orb перекрывает текст при landscape

---

### 2.2. Hero — усилить визуальный импакт

#### Orb и rings
**Сейчас:** статичное вращение ring'ов, один float для chip'ов.

**Улучшить:**
1. **Orb pulse:** добавить `box-shadow` анимацию пульсации glow — `0 0 60px rgba(47,123,255,0.3)` → `0 0 90px rgba(47,123,255,0.5)` за 3s ease-in-out infinite alternate.
2. **Rings:** сделать `.r1` сплошной, `.r2` dashed + gradient stroke (CSS `conic-gradient` через mask). Добавить `.r3` — тонкий dotted ring, 530px, 60s rotation — глубина.
3. **Chips:** добавить 4-й chip «27 крон-джобов» справа сверху. Все chips: добавить `backdrop-filter: blur(10px)` — glassmorphism сильнее.
4. **Chip micro-animation:** при hover chip поднимается на 6px + shadow усиливается. При load — staggered fade-in: `c1` delay 0ms, `c2` delay 200ms, `c3` delay 400ms, `c4` delay 600ms.
5. **Big J:** добавить subtle text-shadow animation — glow «дышит».

#### Typo в hero
**Сейчая:** h1 76px clamp, lede 20px — нормально, но не впечатляет.

**Улучшить:**
- h1: добавить `background: linear-gradient(135deg, #eaf0ff 0%, #4f9cff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;` — градиентный текст для «Jarvice».
- lede: поднять до 22px, `letter-spacing: -0.01em`, line-height 1.45.
- Eyebrow: сделать "badge" слева от заголовка, не над — экономит вертикаль.

---

### 2.3. Stats — сделать «живыми» счётчиками

**Улучшить:**
- При скролле в viewport — числа анимируются от 0 до target за 1.5s easeOutExpo.
- Большие цифры (937, 9500) — font-variant-numeric: tabular-nums (не прыгают при анимации).
- Hover на stat-card: translateY(-4px) + border-color brighter — feedback.
- Добавить горизонтальный divider между stats и следующей секцией: gradient line 1px.

---

### 2.4. PII Pipeline (новый раздел) — визуализация

**Дизайн:** горизонтальная timeline с 5 узлами.
- Узлы: круглые иконки (RED → маска → GREEN → облако → Telegram).
- Линии между узлами: animated gradient dash — «данные текут».
- При scroll reveal: узлы появляются staggered слева направо, 150ms delay каждый.
- Цветовая дифференциация: RED узел — red glow, GREEN узел — green glow, облако — blue glow.
- Responsive: на mobile — вертикальная timeline с узлами слева.

---

### 2.5. Modes (3 тира) — усилить карточки

**Сейчас:** простые карточки с hover lift.

**Улучшить:**
1. **Active state indicator:** для «Private Mode» (recommended) — добавить glow-border pulse: `box-shadow: 0 0 0 2px var(--green), 0 0 20px rgba(52,211,153,0.3)` animation.
2. **Tier badges:** рядом с заголовком — «Рекомендуем» ribbon для Private Mode.
3. **Hover:** не только lift, но и `background: linear-gradient(...)` shift — карточка «загорается».
4. **Expand on click:** accordion-раскрытие с деталями (CPU/RAM требования, latency, цена if applicable).
5. **Icons:** MI icons сделать более узнаваемыми — Private (shield lock), Enhanced (cloud sync), Knowledge (brain/network).

---

### 2.6. Comparison Table — сделать WOW

**Сейчас:** обычная HTML table.

**Улучшить:**
1. **Sticky header:** thead sticky при скролле.
2. **Jarvice column highlight:** `.jcol` — фон с анимированным subtle gradient shift, не просто rgba(47,123,255,0.05).
3. **Yes/No icons:** заменить текст ✓/✕ на SVG-иконки (check-circle, x-circle, tilde-circle). Yes — зелёный glow, No — красный muted.
4. **Row hover:** highlight всей строки + текст feat становится белее.
5. **Mobile:** horizontal scroll с drag-индикатором (пользователи не знают, что можно скроллить). Добавить CSS snap-scroll.
6. **Добавить строки:** «The Brain RAG», «Self-validation 5-stage», «Multi-agent architecture» — то, где Jarvice однозначно побеждает.

---

### 2.7. Roadmap — полностью переделать

**Сейчас:** 4 кружка с линиями — скучно и абстрактно.

**Улучшить:**
1. **Vertical timeline слева:** прямая линия с точками-статусами.
   - Готовое — filled circle с checkmark + green glow
   - В разработке — pulsing circle + blue glow
   - Запланировано — empty circle + muted
2. **Каждая фаза — expandable card:** клик открывает детали (дата, что входит, скриншоты if available).
3. **Progress bar:** общий прогресс «75% готово» с анимацией fill.
4. **Deployment map:** small world-map dots (Russia) — где уже работает. 4 точки: Москва, наши VPS, macOS (icons, not geo-accurate).

---

### 2.8. Agents Section (новый) — визуал

**Дизайн:** grid 3×2 cards.
- Каждый агент — avatar circle с initials + цвет роли.
- Friday: blue, Jarvis: amber, Edith: purple, Ultron: red, ARGO: teal, Hera: pink.
- Hover: карточка flips (CSS 3D flip) revealing skills/tools list.
- Staggered entrance: 100ms delay между карточками.

---

### 2.9. CTA Section — усилить urgency

**Улучшить:**
1. **Form redesign:**
   - Input fields: floating labels (Material Design style) вместо статичных label+placeholder.
   - Submit button: ripple effect on click.
   - Success state: confetti-like particle burst (CSS-only, не JS-heavy).
2. **Visual:** добавить background grid pattern (subtle, 10% opacity) — связь с tech-theme.
3. **Urgency element:** «4 пилотных места в июле» — если правда. Если нет — убрать.
4. **Social proof:** «Уже 4 компании используют Jarvice» — если можно раскрывать.

---

### 2.10. Типографика — детали

**Сейчай:** -apple-system stack, неплохо.

**Улучшить:**
- Добавить шрифт Inter (Google Fonts) как primary, системный как fallback. Inter дружит с цифрами и UI.
- h1: `letter-spacing: -2px` (сейчас -1.5) — плотнее, современнее.
- h2: `letter-spacing: -1.2px`, line-height 1.08.
- Body: line-height 1.6 (сейчас 1.55) — air-нее.
- Eyebrow: `font-family: 'IBM Plex Mono', monospace` — tech-вайб.
- Font weights: h1 800, h2 800, h3 700, body 400, labels 600.

**Code:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500&display=swap');

body { font-family: 'Inter', -apple-system, ... }
.eyebrow { font-family: 'IBM Plex Mono', monospace; }
```

---

### 2.11. Цветовая палитра — расширить

**Сейчай:** blue-dominant, зелёный/красный для статусов.

**Добавить:**
- **Amber/gold** — для «в разработке» статусов (roadmap). Hex: `#f59e0b`.
- **Purple** — для Knowledge Mode / The Brain. Hex: `#a855f7`. Gradient: `#a855f7` → `#6366f1`.
- **Teal** — для CI/devops элементов. Hex: `#14b8a6`.
- **Surface hierarchy:** 
  - `--bg-deep: #040810` (для footer, CTA bg)
  - `--bg-elevated: #121b30` (для карточек)
  - `--bg-overlay: rgba(18,27,48,0.8)` (для modals, chips)

---

### 2.12. Отступы и ритм

**Сейчай:** padding 96px для sections — ок, но monotonous.

**Улучшить:**
- Alternate rhythm: 120px / 80px / 120px / 80px — breathing room.
- Sections с dark-bg (CTA, stats) — 100px. Sections light (features) — 80px.
- Add divider lines между некоторыми sections: 1px gradient от transparent → border → transparent.

---

### 2.13. Mobile Responsive — critical fixes

**Сейчайные проблемы:**
- Orb в hero может перекрывать текст на iPhone SE (375px).
- Table comparison — не очевидно, что скроллится.
- Roadmap — 2×2 grid ломает связность timeline.

**Fixes:**
1. **Hero:** на <480px скрывать orb (display:none) или масштабировать до 140px. Текст first, visuals last.
2. **Comparison:** add scroll-hint shadow (fade right edge) + drag icon.
3. **Roadmap:** force 1-column vertical timeline на mobile.
4. **Burger menu:** add overlay backdrop-blur when open.
5. **Touch targets:** ensure all buttons ≥44×44px (сейчас nav-cta 9px 18px — height ~36px, increase to 44px min).

---

### 2.14. Новые визуальные элементы

#### Floating particles (hero background)
- 20-30 маленьких точек (4px), color accent-2, floating slowly.
- CSS-only: pseudo-elements с animation, не canvas.

#### Connection lines (agents section)
- SVG линии между аватарами агентов, showing collaboration mesh.
- Animated dash-offset — «данные текут между агентами».

#### Typing cursor (CTA heading)
- «Запросить пилот Jarvice» с мигающим `_` cursor — terminal feel.

#### Status indicators (footer)
- Small pulsing dot: «Система онлайн» green pulse.

---

### 2.15. Микроанимации — список

| Элемент | Текущее | Желаемое |
|---------|---------|----------|
| Card hover | translateY(-4px) | translateY(-6px) + scale(1.01) + shadow expand |
| Button hover | translateY(-2px) | translateY(-2px) + glow intensify + 0.15s ease-out |
| Link hover | color change | color + underline slide-in from left |
| Scroll reveal | fade + translateY | fade + translateY + subtle scale(0.98→1) |
| Nav scroll | sticky blur | sticky blur + shrink height (68→54px) + logo scale down |
| Form focus | border color | border color + subtle glow + label float up |
| Chip | float | float + 3s delay variation + hover pause |
| Orb ring | constant spin | spin + speed up on scroll-into-view |
| Stat number | static | count-up animation |
| Table row | none | hover highlight + cells subtle shift right |

---

### 2.16. Performance notes

- All animations use `transform` and `opacity` only — GPU-accelerated.
- `@media (prefers-reduced-motion: reduce)` — disable all animations for accessibility.
- Lazy-load below-fold images (when added).
- Consider `content-visibility: auto` for sections.

---

## Summary: Priority Actions

### Must-have (до публикации):
1. ⬆️ Обновить версию v0.2.1 → v0.4.0 везде
2. 📝 Переписать hero headline + lede — конкретнее
3. 📊 Обновить stats — реальные цифры (6 агентов, 937 атомов, 4 деплоя)
4. 🛡️ Добавить PII Pipeline section с визуализацией
5. 🧠 Добавить The Brain / Knowledge Mode section
6. 🗺️ Переписать Roadmap — реальные фазы + статусы
7. 👥 Добавить Agents section
8. 🔧 Fix форма — убрать YOUR_FORM_ID, добавить поле "Режим"

### Should-have (следующая итерация):
9. 🎨 Inter + IBM Plex Mono шрифты
10. ✨ Count-up анимация для stats
11. 🌀 Orb pulse + 3rd ring
12. 📋 Comparison table upgrade (SVG icons, sticky header)
13. 🛣️ Roadmap vertical timeline redesign
14. 📱 Mobile fixes (hero orb, table scroll-hint, burger overlay)

### Nice-to-have:
15. 🌌 Floating particles in hero
16. 🤝 Agent connection mesh SVG
17. ⌨️ Typing cursor in CTA
18. 🎊 Confetti success state
19. 📄 Whitepaper PDF download
