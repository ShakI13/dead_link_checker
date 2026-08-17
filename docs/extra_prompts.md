# Extra prompts

Все user-промпты эксперимента + вспомогательные вопросы агента при подготовке спеки.

«Файл с дополнительными промптами» — это этот файл: что человек отправил сверх исходного брифа, и какие уточняющие вопросы понадобились, чтобы спека стала однозначной.

Итого user-промптов: **12**.

---

## 1. Spec prepare — промпт 1

Чат: `598a9c4b-dcbf-46b2-9391-840a6501dcd1`

```
I have the following task:
### CLI-утилита: Markdown Link & Dead Code Checker
> Суть: Консольный скрипт на Python, который сканирует указанную папку с проектом.
- Функционал:
  - Находит все .md файлы в папке.
  - Извлекает все ссылки [текст] (url) и file:///...).
  - Проверяет локальные ссылки на существование файлов, а внешние HTTP-ссылки — на доступность (отправляет HEAD или GET запрос).
  - Выводит красивый отчёт в консоль (с цветами/таблицей) со списком сломанных ссылок и статус-кодами.
- На чем "спотыкается" ИИ без хорошей спеки:
  - Обработка относительных путей относительно текущего файла.
  - Ограничение по таймаутам HTTP-запросов и обработка ошибок сети 404, 500, timeout).

And from that we need to discuss what specification should be and:
Размер в токенах спецификации
Запустился ли с первого раза
Качество вспомогательных запросов

Общее количество промптов
Итоговое количество багов
Общее количество потраченых токенов

Скриншот из терминала
Файл спецификации
Файл с дополнительными промптами
Файл с подсчетами

Python version should be: Python 3.13.5
you need to create virtual env in venv
env vars should be stored in .env file
should be created folder src, tests, docs
use unittest for making tests
do we need not built-in python libs for the task?

What do you think about the task? Ask questions if you have don't make assumptions.
```

---

## Вспомогательные запросы агента (spec prepare)

Это как раз поле **«качество вспомогательных запросов»**: уточнения до кода, одним блоком, 19 пунктов.

1. Dead code в скоупе, или только markdown-ссылки?
2. Рекурсия по дереву? Игнорировать `.git` / `venv` / `node_modules` / `__pycache__`?
3. Только `[text](url)`, или ещё images, autolinks, reference-style, bare URLs, HTML `<a href>`?
4. `mailto:` / `tel:` / `data:` — skip или unsupported?
5. Якоря `#heading`: проверять heading или только файл? Missing heading = warning?
6. База относительного пути: директория текущего `.md`?
7. Ссылка на директорию (`docs/`): OK, если директория есть?
8. Абсолютный `/path`: корень ФС или корень проекта?
9. HTTP timeout, follow redirects, SSL verify?
10. Broken = 4xx/5xx? 429, неудачный redirect, connection errors?
11. Sequential или thread pool?
12. User-Agent: свой или дефолтный Python?
13. Entry: `python -m src`, скрипт в корне, console script?
14. Флаги: только PATH, или ещё `--timeout` / `--exclude` / `--offline`?
15. В отчёте только broken, или все ссылки? Exit 1 если broken?
16. Цвета: ANSI или `rich`?
17. Что класть в `.env`, если секретов нет?
18. `docs/`: README пользователя или спека эксперимента?
19. Этот чат только пишет спеку; новый чат реализует с чистого контекста?

Ответы пользователя (промпт 2 того же чата):

```
1. md file links
2. yes
3. yes
4. skip
5. files and heading, if heading don't exist - warning
6. probably
7. yes
8. probably file system
9. lets set it configurable from args
10. yes, lets include them
11. make simple code
12. default is fine
13. script in project root that will import code from src
14. target path and timeout
15. only broken
16. rich allowed
17. if we don't need it, don't use
18. spec.
19. yes
```

После этого агент записал `docs/SPEC.md` и остановился. Реализации в этом чате не было.

---

## 2. Spec implement — единственный промпт реализации

Чат: `147c835c-0d62-4fa8-83f1-ca33d202614a`  
Пустой контекст, только спека в репозитории.

```
Implement this repo from docs/SPEC.md only. Do not invent flags, libraries, or .env.

Constraints:
- Python 3.13.5, venv at ./venv
- unittest only (not pytest)
- Entry: check_links.py at repo root importing from src/
- Third-party: rich only

Read docs/SPEC.md, then implement layout, CLI, tests, and README.
When done, show how to run the checker and tests.
```

Follow-up в этом чате не было. Тесты прошли.

---

## 3. Bug fix IPv6 — первый follow-up после impl

Чат: `86c4be5e-6178-4bf3-83fb-1844fde4a8f8`

```
Got an error on real folder:
```txt
$ python ./check_links.py ./target
Traceback (most recent call last):
  File "./check_links.py", line 131, in <module>
    sys.exit(main())
             ~~~~^^
  File "./check_links.py", line 63, in main
    resolved = classify_and_resolve(link.url, md_path)
  File "src/resolve.py", line 35, in classify_and_resolve
    parsed = urlparse(url)
  File "urllib/parse.py", line 395, in urlparse
    splitresult = urlsplit(url, scheme, allow_fragments)
  File "urllib/parse.py", line 514, in urlsplit
    raise ValueError("Invalid IPv6 URL")
ValueError: Invalid IPv6 URL
```
```

Первый follow-up после «реализуй по спеке».

---

## 4. Bug fix User-Agent — второй follow-up

Чат: `6b949725-7c40-4c87-90dc-adf71e6122f1`

В промпт вставлен тот же terminal report, что в `docs/run_log.txt` (63 broken, в основном 403). Суть запроса:

```
I'm curious why in that report we have 403:
[полный лог python ./check_links.py ./target]

Server refused to authorize our request. Why? Bad user agent?
For example that link opens ok from my browser:
https://feature-sliced.design/

We should set real user agent in headers?
Please check that, write test function to check 403 response without headers and correct response with headers.
```

Это второй баг: спека явно требовала дефолтный UA (`Do not send a custom User-Agent`). На Cloudflare/shields.io это 403. Фикс — browser-like `User-Agent` в `src/check_http.py` + unittest + правка спеки.

---

## 5. Bug fix headings — третий follow-up (2 промпта)

Чат: `31e1d6c4-eb83-434e-b025-21a0bb2e8fce`

**Промпт 1** — вопрос после прогона с UA-fix (6 broken, 14 heading warnings):

```
That the output after the last run:
[полный лог: 6 broken, 14 warnings]

How do we check whether heading is ok or not?
Because I've checked the heading mentioned in the table and some of them actually work ok in github webpage view.
```

**Промпт 2** — подтверждение фикса:

```
Yes, please do
```

Третий баг: slug-алгоритм не совпадал с GitHub — не читал HTML `<a id="…">`, не давал `--` после `&`/`/`, ломал `_` в `0001_create_tmp_table`. Фикс в `src/headings.py` + 4 unittest. Heading warnings on the sample tree: **14 → 1** (one shortened anchor left).

---

## 6. Bug fix HEAD/GET — четвёртый follow-up (3 промпта)

Чат: `d5ec6bb5-b6f4-4ce4-9a72-d0475b52e3a9`

**Промпт 1** — после всех предыдущих фиксов (6 broken, 1 warning):

```
[лог: Figma 404, GitHub Dockerfile 429, 4× localhost]

first 2 urls with 404 and 429, why did the script get these status codes?
I opened the links in browser and they were opened fine.
```

**Промпт 2** — уточнение (спека не требовала GET fallback на 404; 429 стабилен между прогонами):

```
But according to specs if HEAD -> 404 fallback should be trying GET, no?
…
You suggest to wait and try again? But I made several different runs of the script and each time I got 429, wtf?
```

**Промпт 3:**

```
Yes!
```

Четвёртый баг: спека требовала GET fallback **только** на 403/405/501. Figma отвечает HEAD→404, GET→200. GitHub blob — HEAD→429 (Varnish throttling после серии HEAD), GET→200. Фикс: GET retry на **любой** non-2xx HEAD; спека обновлена. Broken on the sample tree: **6 → 4** (localhost leftovers).

---

## 7. Bug fix badge links — пятый follow-up (2 промпта)

Чат: `d4b00d2a-d043-4198-bebb-a4c0197fc9aa`

**Промпт 1:**

```
Do we handle such links in md files?

```Markdown
[![Docs](https://img.shields.io/badge/Documentation-1.0.0-blue.svg)](https://github.com/example/project/wiki)
```

```

**Промпт 2:**

```
Please add
```

Пятый баг: regex `INLINE_LINK` не парсил nested «image as link text». Извлекался только `img.shields.io/...`, outer `github.com/.../wiki` пропускался; текст становился `'![Docs'`. Фикс: bracket-aware parse в `src/extract.py` + `test_badge_link_with_nested_image`. Спека описывала inline и images раздельно, nested badge не называла.

---

## По чатам

| Чат | Промптов | Tokens |
| --- | ---: | ---: |
| spec prepare | 2 | 72 400 |
| spec impl | 1 | 125 300 |
| bug IPv6 | 1 | 277 000 |
| bug User-Agent | 1 | 130 500 |
| bug headings | 2 | 400 100 |
| bug HEAD/GET | 3 | 290 000 |
| bug badge links | 2 | 138 600 |
| **Итого** | **12** | **1 433 900** |
