# Отчёт по реализации — Markdown Link Checker

Эксперимент: спека в одном чате, реализация в новом, затем фиксы на реальной папке `ecto-1-kb`. Отчётный чат в промпты и токены не входит.

---

## Метрики

| Поле | Значение |
| --- | --- |
| Размер спецификации | **3 131 токен** (`tiktoken o200k_base`) на момент impl. После патча UA файл стал **3 182**. |
| Запустился ли с первого раза | **Нет.** Unittest прошёл сразу. Первый прогон на `ecto-1-kb` упал. |
| Качество вспомогательных запросов | **Высокое.** 19 вопросов одним блоком до кода. Слабое место: Q12 User-Agent — спросили, ответ «default is fine» дал ложные 403. Nested badge и HEAD 404/429 не спрашивали. |
| Общее количество промптов | **12** user-сообщений (2 spec + 1 impl + 9 в пяти bug-fix). После готовой спеки: **10**. |
| Итоговое количество багов | **5** |
| Общее количество потраченных токенов | **1 433 900** |

---

## Артефакты

| Требование | Где |
| --- | --- |
| Скриншот / лог терминала | `docs/run_log.txt` |
| Файл спецификации | `docs/SPEC.md` |
| Файл с дополнительными промптами | `docs/extra_prompts.md` |
| Файл с подсчетами | этот файл |

---

## Размер спецификации

Файл: `docs/SPEC.md`. Для поля отчёта — **3 131** (то, что видел чат реализации). **3 182** — файл сейчас, после бага 2 в текст добавили browser User-Agent.

Спека на момент impl:

| Оценка | Значение |
| --- | --- |
| Символы | 11 828 |
| Слова | 1 928 |
| Строки | 299 |
| `tiktoken o200k_base` | **3 131** |
| `tiktoken cl100k_base` | 3 123 |

Текущий файл:

| Оценка | Значение |
| --- | --- |
| Символы | 12 034 |
| Слова | 1 952 |
| Строки | 299 |
| `tiktoken o200k_base` | **3 182** |
| `tiktoken cl100k_base` | 3 176 |

---

## Запустился ли с первого раза

**Нет (5 багов на реальных данных / в спеке).**

1. Чат реализации: один промпт → код + unittest → тесты OK. На фикстурах «с первого раза» да.
2. Первый запуск на `ecto-1-kb` → crash `ValueError: Invalid IPv6 URL` (баг 1).
3. После IPv6 — ложные **403** из‑за `Python-urllib` User-Agent (баг 2).
4. После UA — **6 broken, 14 heading warnings**; 13 warnings ложные (баг 3). После fix headings: **6 broken, 1 warning**.
5. Из 6 broken два ложных: Figma **HEAD 404** (GET 200), GitHub blob **HEAD 429** (GET 200) — узкий HEAD→GET fallback (баг 4). После fix: **4 broken** (localhost), **1 warning**.
6. Nested badge `[![alt](img)](dest)` — извлекался только inner image URL (баг 5). Спека этот паттерн не описывала.

---

## Качество вспомогательных запросов

Это не качество кода и не follow-up после бага: насколько хорошо агент уточнил задачу **до** реализации.

В spec-prepare агент не писал код, задал **19 вопросов** одним блоком, дождался ответов, затем зафиксировал спеку.

| Тема | Спросили? |
| --- | --- |
| Dead-code vs только markdown-ссылки | да (вопрос 1) |
| Рекурсия и skip-директории | да |
| Формы ссылок (image, autolink, reference, HTML, bare) | да |
| `mailto:` / `tel:` / `data:` | да |
| Якоря: файл + heading, warning vs broken | да |
| Относительные пути от директории `.md` | да — главный спотык из брифа |
| HTTP timeout, 4xx/5xx/429, sequential | да — второй спотык из брифа |
| `.env` не нужен | да |
| `rich` vs stdlib | да |
| Entry point, unittest, layout | да |
| Workflow: спека в этом чате, impl в новом | да |

Оценка: **высокое**. Один раунд Q&A, закрыты оба заявленных failure mode.

Слабое место: вопросы 6 и 8 («probably») зафиксировали как жёсткие правила. Вопрос 12 про User-Agent задали, ответ «default is fine» попал в спеку и дал баг 2. Текст вопросов: `docs/extra_prompts.md`.

---

## Баги

| # | Где | Симптом | Фикс |
| --- | --- | --- | --- |
| 1 | `src/extract.py` + `src/resolve.py` | `ValueError: Invalid IPv6 URL` на `[https://x](https://x)` | skip overlapping bare URLs; invalid URL → `invalid url` |
| 2 | `src/check_http.py` | Живые сайты отвечают **403** на `Python-urllib/3.13` | browser-like `User-Agent`; unittest; спека поправлена |
| 3 | `src/headings.py` | **14 heading warnings**, 13 ложных (slug ≠ GitHub) | GitHub-aligned slugify; warnings **14 → 1** |
| 4 | `src/check_http.py` + spec | Figma **HEAD 404** / GitHub blob **HEAD 429**, GET → 200; fallback только на 403/405/501 | GET retry на любой non-2xx HEAD; broken **6 → 4** |
| 5 | `src/extract.py` | `[![alt](img)](dest)` — только inner image URL | bracket-aware nested parse; unittest `test_badge_link_with_nested_image` |

---

## По чатам

Считаются user-сообщения, не tool-calls. Тексты: `docs/extra_prompts.md`.

| Чат | ID | Промптов | Tokens |
| --- | --- | ---: | ---: |
| spec prepare | `598a9c4b-dcbf-46b2-9391-840a6501dcd1` | 2 | 72 400 |
| spec impl | `147c835c-0d62-4fa8-83f1-ca33d202614a` | 1 | 125 300 |
| bug IPv6 | `86c4be5e-6178-4bf3-83fb-1844fde4a8f8` | 1 | 277 000 |
| bug User-Agent | `6b949725-7c40-4c87-90dc-adf71e6122f1` | 1 | 130 500 |
| bug headings | `31e1d6c4-eb83-434e-b025-21a0bb2e8fce` | 2 | 400 100 |
| bug HEAD/GET | `d5ec6bb5-b6f4-4ce4-9a72-d0475b52e3a9` | 3 | 290 000 |
| bug badge links | `d4b00d2a-d043-4198-bebb-a4c0197fc9aa` | 2 | 138 600 |
| **Итого** | | **12** | **1 433 900** |
