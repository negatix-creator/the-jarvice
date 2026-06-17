# The Jarvice — Design System

## Концепция

**Cyber Shield** — корпоративный tech-стиль с акцентом на безопасность. Тёмный, уверенный, профессиональный. Не кричащий стартап, а серьёзный продукт для enterprise. Щит = защита, замок = приватность, cyan = технологии.

## Цвета

### Основная палитра

| Роль | Цвет | HEX | RGB | Использование |
|------|------|-----|-----|---------------|
| **Background** | Deep Navy | `#0A1628` | 10, 22, 40 | Фон всех слайдов |
| **Surface** | Dark Slate | `#0F2240` | 15, 34, 64 | Карточки, панели, таблицы |
| **Primary** | Electric Cyan | `#00D4FF` | 0, 212, 255 | Заголовки, иконки, ссылки, акценты |
| **Secondary** | Gold | `#F0C040` | 240, 192, 64 | Версии, бейджи, CTA, важные числа |
| **Text Primary** | White | `#FFFFFF` | 255, 255, 255 | Основной текст |
| **Text Secondary** | Slate Blue | `#8899BB` | 136, 153, 187 | Подписи, описания, dim-текст |
| **Text Dim** | Dark Blue | `#4466AA` | 68, 102, 170 | Сноски, метаданные |

### Семантические цвета

| Роль | Цвет | HEX | Использование |
|------|------|-----|---------------|
| **Success** | Green | `#22C55E` | ✅ чекмарки, "работает", "бесплатно" |
| **Warning** | Amber | `#F59E0B` | ⚠️ предупреждения, "частично" |
| **Danger** | Red | `#EF4444` | ❌ ошибки, "не работает", "риск" |
| **Privacy** | Cyan Glow | `#00D4FF80` | Щит, замок, PII-зоны |
| **PII Red** | Soft Red | `#EF444480` | RED/ директория, оригиналы |
| **PII Green** | Soft Green | `#22C55E80` | GREEN/ директория, обезличенные |

### Градиенты

```
Primary gradient:  #0A1628 → #0F2240 (фон)
Cyan gradient:    #00D4FF → #0088CC (кнопки, акценты)
Gold gradient:    #F0C040 → #E0A020 (бейджи, CTA)
Card glow:        #00D4FF20 (тень под карточками)
```

## Типографика

### Иерархия

| Уровень | Размер | Вес | Цвет | Шрифт | Пример |
|---------|--------|-----|------|-------|--------|
| **H1** | 48–64px | 700 | White | Inter / SF Pro Display | "The Jarvice" |
| **H2** | 32–40px | 600 | White | Inter / SF Pro Display | "Три режима приватности" |
| **H3** | 24–28px | 600 | Cyan | Inter / SF Pro Display | "Private Mode" |
| **Body** | 18–20px | 400 | White | Inter / SF Pro Text | Описания |
| **Caption** | 14–16px | 400 | Slate Blue | Inter / SF Pro Text | Подписи |
| **Code** | 16–18px | 500 | Cyan | SF Mono / JetBrains Mono | `the-jarvice run --once` |

### Шрифты

- **Основной:** Inter (Google Fonts, бесплатный) или SF Pro Display (macOS)
- **Моноширинный:** SF Mono, JetBrains Mono, Fira Code
- **Fallback:** -apple-system, Helvetica Neue, Arial, sans-serif

## Иконки и символы

### Основной набор

| Иконка | Значение | Стиль |
|--------|----------|-------|
| 🛡️ Щит с замком | Приватность / The Jarvice | Line art, cyan glow |
| 📧 Конверт | Exchange / Почта | Line art, white |
| 💬 Чат-пузырь | Teams / Сообщения | Line art, white |
| 🤖 Мозг/Чип | LLM / Ollama | Line art, cyan |
| 📲 Telegram-пузырь | Доставка | Line art, white |
| 🔒 Замок | Безопасность | Line art, gold |
| 📁 Папка с замком | RED/ PII зона | Line art, red glow |
| 📁 Папка с галкой | GREEN/ Чистые данные | Line art, green glow |

### Стиль иконок

- **Line art**, stroke 1.5–2px
- **Не filled** — контурные, не заливочные
- **Цвет:** Cyan (#00D4FF) для активных, Slate Blue (#8899BB) для неактивных
- **Размер:** 24×24px в таблицах, 48–64px как hero-иконки
- **Источник:** Phosphor Icons (бесплатный, MIT) или Heroicons

## Компоновка слайдов

### Сетка

```
┌─────────────────────────────────────────┐
│  48px  Padding top                       │
│  ┌───────────────────────────────────┐  │
│  │                                   │  │
│  │         Content area              │  │
│  │         (max 1200×675px)          │  │
│  │                                   │  │
│  └───────────────────────────────────┘  │
│  48px  Padding bottom                    │
│  ┌───────────────────────────────────┐  │
│  │ Slide number · Title    Logo →    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

- **Aspect ratio:** 16:9 (1920×1080 или 1280×720)
- **Padding:** 48px по краям, 64px сверху для заголовка
- **Content max width:** 1200px
- **Footer:** 32px высота, Slate Blue текст, Cyan номер слайда

### Типы слайдов

| Тип | Компоновка | Использование |
|-----|-----------|---------------|
| **Hero** | Центр: крупная иконка + H1 + подзаголовок | Титульный, CTA |
| **Pipeline** | Горизонтальный поток: 3-4 ноды со стрелками | Как работает, архитектура |
| **Cards** | 2-3 вертикальные карточки в ряд | Три режима, конкуренты |
| **Split** | 50/50: слева текст, справа визуал | Демо, Enterprise |
| **Table** | Таблица с Cyan заголовками | Сравнение, CLI команды |
| **Timeline** | Горизонтальная линия с 4 точками | Roadmap |

## Карточки

```css
.card {
  background: #0F2240;
  border: 1px solid #00D4FF30;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 0 20px #00D4FF10;
}
.card.highlight {
  border: 2px solid #00D4FF;
  box-shadow: 0 0 30px #00D4FF20;
}
.card-title {
  font-size: 20px;
  font-weight: 600;
  color: #00D4FF;
}
```

## Кнопки и CTA

| Тип | Стиль | Использование |
|-----|-------|---------------|
| **Primary** | Cyan gradient, белый текст, 12px radius | "Попробовать", "Установить" |
| **Secondary** | Прозрачный, cyan border, cyan текст | "Документация", "GitHub" |
| **Badge** | Золотой фон, тёмный текст, pill shape | "v0.2.1", "Бесплатно", "MIT" |

## Анимации (для веб/PDF)

- **Появление:** fade-in + slide-up, 0.4s ease-out
- **Ноды pipeline:** последовательно, 0.3s задержка между нодами
- **Карточки:** stagger, 0.2s между карточками
- **Иконки:** subtle pulse на hover (1.05x scale)
- **Стрелки:** dash-flow анимация (поток данных)

## Форматы

| Формат | Размер | Использование |
|--------|--------|---------------|
| **Keynote** | 1920×1080 | Презентация |
| **PDF** | 1920×1080 | Рассылка |
- **PNG** | 2x retina | Отдельные слайды для Telegram/WhatsApp |
- **SVG** | Вектор | Иконки, логотип, баннер |

## Примеры CSS-переменных (для веб-версии)

```css
:root {
  --bg-primary: #0A1628;
  --bg-surface: #0F2240;
  --cyan: #00D4FF;
  --cyan-dim: #00D4FF80;
  --gold: #F0C040;
  --gold-dim: #F0C04080;
  --text-primary: #FFFFFF;
  --text-secondary: #8899BB;
  --text-dim: #4466AA;
  --success: #22C55E;
  --warning: #F59E0B;
  --danger: #EF4444;
  --radius: 12px;
  --font-main: 'Inter', -apple-system, sans-serif;
  --font-mono: 'SF Mono', 'JetBrains Mono', monospace;
}
```

## Что НЕ делать

- ❌ Градиентный текст (кроме логотипа)
- ❌ Скругления больше 16px
- ❌ Более 3 цветов на одном слайде (cyan + gold + white)
- ❌ Filled иконки (только line art)
- ❌ Comic Sans, Papyrus, Impact
- ❌ Анимации длиннее 0.5s
- ❌ Текст меньше 14px
- ❌ Более 6 строк текста в одном блоке