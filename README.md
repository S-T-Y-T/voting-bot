# Telegram Voting Bot

Telegram бот для проведения опросов и сбора голосов.

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd BOt
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте конфигурацию:
   - Скопируйте `config.example.py` в `config.py`
   - Заполните токен вашего бота и другие параметры

4. Запустите бот:
```bash
python bot.py
```

## Структура проекта

- `bot.py` - главный файл бота
- `config.py` - конфигурация (не добавляется в git)
- `config.example.py` - пример конфигурации
- `database.py` - работа с базой данных
- `votes.json` - хранилище голосов

## Требования

- Python 3.7+
- aiogram
