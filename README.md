# Personal Finance Tracker

## Команды

Добавить транзакцию:
python cli.py add --type income --amount 50000 --category salary --date 2026-01-15 --comment "Зарплата"
python cli.py add --type expense --amount 3500 --category food --date 2026-01-16 --comment "Продукты"

Список транзакций:
python cli.py list
python cli.py list --type expense --category food,transport

Статистика:
python cli.py stats
python cli.py stats --type income --start-date 2026-01-01

Обновить транзакцию:
python cli.py update --id 1 --amount 55000

Удалить транзакцию:
python cli.py delete --id 3
python cli.py delete --id 3 --force

Импорт из JSON:
python cli.py import --file transactions.json

Экспорт в JSON:
python cli.py export --output report.json

## Категории

Доходы: salary, freelance, investment, gift, other_income
Расходы: food, transport, housing, entertainment, health, education, taxes, other_expense