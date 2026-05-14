# VK Media Downloader CLI - Документация (Версия 1)

## Обзор

VK Media Downloader CLI - это консольное приложение для поиска, скачивания и управления медиафайлами из ВКонтакте. Приложение предоставляет богатый набор команд для работы с фотографиями, видео и документами.

## Установка

```bash
pip install -e .
```

Или с зависимостями для разработки:

```bash
pip install -e ".[dev]"
```

## Конфигурация

Создайте файл конфигурации в `~/.config/vk-cli/config.yaml`:

```yaml
vk:
  service_token: "ваш_токен_здесь"
  api_version: "5.199"
download:
  download_directory: "/path/to/downloads"
  max_concurrent_downloads: 4
cache:
  enabled: true
  ttl_hours: 1
favorite_users: []
min_size_mb: 0.0
allow_private: false
media_types: ["photo", "video"]
```

Или используйте переменные окружения:

```bash
export VK_SERVICE_TOKEN="ваш_токен_здесь"
export VK_DOWNLOAD_DIR="/path/to/downloads"
```

## Команды

### 1. config - Управление конфигурацией

Команда для управления настройками приложения.

#### Подкоманды:

**config set** - Установка значения конфигурации:
```bash
vk-downloader config set download.max_concurrent_downloads 6
```

**config get** - Получение значения конфигурации:
```bash
vk-downloader config get download.max_concurrent_downloads
```

**config auth status** - Проверка статуса аутентификации:
```bash
vk-downloader config auth status
```

#### Скриншоты:
[Проверка config](image.png)

### 2. search - Поиск медиа

Команда для поиска медиафайлов в профилях и сообществах ВКонтакте.

```bash
vk-downloader search --source "club123456" --type photo --limit 10 --min-likes 5
```

#### Опции:
- `--source` - ID или shortname владельца (обязательно)
- `--type` - Тип медиа (photo, video, doc), по умолчанию photo
- `--after` - Фильтр по дате (формат YYYY-MM-DD)
- `--before` - Фильтр по дате (формат YYYY-MM-DD)
- `--min-likes` - Минимальное количество лайков
- `--limit` - Количество результатов (1-200), по умолчанию 30
- `--save-filter` - Сохранить параметры как фильтр
- `--offset` - Смещение для пагинации

#### Скриншоты:
[Проверка search](image-1.png)

### 3. download - Скачивание медиа

Команда для асинхронного скачивания медиафайлов.

```bash
vk-downloader download --ids "photo_123456_789012,photo_123456_789013" --max-concurrent 4
```

#### Опции:
- `--ids` - Список VK ID через запятую
- `--from-filter` - Имя сохранённого фильтра для скачивания
- `--max-concurrent` - Максимальное количество параллельных загрузок (1-10), по умолчанию 4
- `--dest` - Папка для загрузки
- `--skip-existing` - Пропускать файлы, уже находящиеся на диске
- `--verify-hash` - Проверять SHA256 хеш при --skip-existing

#### Скриншоты:
[Проверка download](image-2.png)

### 4. list - Просмотр библиотеки

Команда для просмотра и фильтрации локальной библиотеки скачанных медиа.

```bash
vk-downloader list-media --source "123456" --type photo --starred --page 1 --per-page 20
```

#### Опции:
- `--source` - Фильтр по владельцу (ID или shortname)
- `--type` - Фильтр по типу медиа (photo, video, doc)
- `--after` - Фильтр по дате скачивания (формат YYYY-MM-DD)
- `--before` - Фильтр по дате скачивания (формат YYYY-MM-DD)
- `--starred` - Показать только отмеченные
- `--read` - Показать только прочитанные
- `--search` - Полноценный поиск по названию и описанию
- `--page` - Номер страницы для пагинации
- `--per-page` - Количество элементов на странице (1-100), по умолчанию 50
- `--format` - Формат вывода (table, json, csv), по умолчанию table

#### Скриншоты:
[Проверка list-media](image-3.png)

### 5. metadata - Управление метаданными

Команда для управления тегами и статусами медиафайлов.

```bash
vk-downloader metadata --id "photo_123456_789012" --star --tags "природа,ландшафт"
```

#### Опции:
- `--id` - VK ID медиафайла (обязательно)
- `--star` / `--unstar` - Отметить/снять отметку "избранное"
- `--read` / `--unread` - Отметить/снять отметку "прочитано"
- `--tags` - Добавить теги (через запятую)
- `--tags-remove` - Удалить указанные теги
- `--open` - Открыть оригинал в браузере
- `--show` - Показать текущие метаданные

#### Скриншоты:
[Проверка metadata](image-4.png)

### 6. filter - Управление фильтрами

Команда для создания и управления сохранёнными фильтрами поиска.

```bash
vk-downloader create --name "my_photos" --source "123456" --type photo --limit 50
```

#### Подкоманды:

**create** - Создание нового фильтра:
```bash
vk-downloader create --name "my_filter" --source "club12345" --type photo --limit 20
```

**list** - Просмотр всех фильтров:
```bash
vk-downloader list
```
**apply** - Просмотр всех фильтров:
```bash
vk-downloader apply --name "my_filter"
```
#### Скриншоты:
[Проверка create](image-5.png)
[Проверка list](image-6.png)

### 7. delete - Удаление медиа

Команда для удаления записей из локальной библиотеки и файлов с диска.

```bash
vk-downloader delete --ids "photo_123456_789012" --remove-files --dry-run
```

#### Опции:
- `--ids` - Список VK ID для удаления
- `--older-than` - Удалить записи старше N дней
- `--max-likes` - Удалить записи с лайками <= порога
- `--source` - Фильтр по владельцу
- `--type` - Фильтр по типу медиа
- `--remove-files` - Также удалить локальные файлы
- `--dry-run` - Показать, что будет удалено, без выполнения
- `--force` - Пропустить подтверждение при массовом удалении

#### Скриншоты:
[Проверка download](image-7.png)

## Примеры использования

### Пример 1: Скачивание фото из сообщества
```bash
# Найти последние 20 популярных фото в сообществе
vk-downloader search --source "club12345" --type photo --limit 20 --min-likes 10

# Скачать найденные фото
vk-downloader download --from-filter "recent_popular" --max-concurrent 5
```

### Пример 2: Организация медиа с тегами
```bash
# Пометить важные фото
vk-downloader metadata --id "photo_12345_67890" --star --tags "важное,для_работы"

# Просмотреть все важные фото
vk-downloader list --starred --search "для_работы"
```

### Пример 3: Управление хранилищем
```bash
# Удалить старые файлы (>90 дней) с диска
vk-downloader delete --older-than 90 --remove-files
```

## Структура проекта

```
vk-media-downloader/
├── src/
│   ├── api/           # Модели и клиент API ВК
│   ├── cli/           # Команды интерфейса
│   ├── config/        # Управление конфигурацией
│   ├── storage/       # Работа с базой данных
│   ├── utils/         # Вспомогательные функции
│   └── main.py        # Главная точка входа
├── tests/             # Тесты
└── pyproject.toml     # Конфигурация проекта
```

## Коды выхода

- `0` - Успешное выполнение
- `1` - Ошибка ввода/параметров
- `2` - Ошибка API/сети
- `3` - Ошибка файловой системы/базы данных

## Часто задаваемые вопросы

**Q: Как получить токен ВКонтакте?**
A: Перейдите на https://vk.com/apps?act=manage, создайте standalone-приложение и скопируйте сервисный токен.

**Q: Почему возникает ошибка "Rate limit exceeded"?**
A: Приложение автоматически ограничивает частоту запросов к API ВКонтакте (до 3 запросов в секунду) для соблюдения условий использования.

**Q: Где хранятся скачанные файлы?**
A: По умолчанию файлы сохраняются в ~/Downloads/vk-media, но путь можно изменить в конфигурации.