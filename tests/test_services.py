import pytest
import logging
from datetime import datetime
from unittest.mock import Mock

from models import TransactionType, TransactionCategory, Note
from storage import StorageServices
from services import ServiceTracker

class TestServices:

    def setup_method(self):
        self.mock_storage = Mock(spec=StorageServices)
        self.mock_storage.load_csv.return_value = []

        self.tracker = ServiceTracker(self.mock_storage)

        logging.getLogger('ServiceTracker').handlers.clear()

    def teardown_method(self):
        self.tracker.notes.clear()

    # =================================================================================

    def test_init_empty_storage(self):      #возвращает пустой список от пустого файла
        assert self.tracker.notes == []
        assert isinstance(self.tracker.logger,logging.Logger)
        self.mock_storage.load_csv.assert_called_once()

    def test_init_with_data(self):      #на непустых данных
        mock_data = [
            {'id': '1', 'type': 'income', 'amount': '1000', 'category': 'salary',
             'date': '2026-01-01T10:00:00', 'comment': 'Test'},
            {'id': '2', 'type': 'expense', 'amount': '500', 'category': 'food',
             'date': '2026-01-02T12:00:00', 'comment': 'Lunch'}
        ]

        self.mock_storage.load_csv.return_value = mock_data

        tracker = ServiceTracker(self.mock_storage)

        assert len(tracker.notes) == 2
        assert tracker.notes[0].id == 1
        assert tracker.notes[0].type == TransactionType.INCOME
        assert tracker.notes[1].id == 2
        assert tracker.notes[1].type == TransactionType.EXPENSE

    # =================================================================================

    def test_get_next_id_empty(self):       #генерация id на основе пустого файла
        assert self.tracker._get_next_id() == 1

    def test_get_next_id_data(self):        #на непустых данных
        self.tracker.notes = [
            Note(id=1, type=TransactionType.INCOME, amount=1000,
                 category=TransactionCategory.SALARY, date=datetime.now()),
            Note(id=2, type=TransactionType.INCOME, amount=2000,
                 category=TransactionCategory.FREELANCE, date=datetime.now()),
            Note(id=3, type=TransactionType.EXPENSE, amount=500,
                 category=TransactionCategory.FOOD, date=datetime.now())
        ]
        assert self.tracker._get_next_id() == 4

    def test_get_next_id_data_after_delete(self):       #после удаления одной транзакции
        self.tracker.notes = [
            Note(id=1, type=TransactionType.INCOME, amount=1000,
                 category=TransactionCategory.SALARY, date=datetime.now()),
            Note(id=3, type=TransactionType.EXPENSE, amount=500,
                 category=TransactionCategory.FOOD, date=datetime.now())
        ]
        assert self.tracker._get_next_id() == 4

    #=================================================================================

    def test_add_note_income_min(self):     #добавление новой записи, минимальные данные
        new_note = self.tracker.add_transaction(
            type = 'income',
            amount = 10_000,
            category="gift",
            date = "2020-01-01"
        )

        assert new_note.id == 1
        assert new_note.type == TransactionType.INCOME
        assert new_note.amount == 10_000
        assert new_note.category == TransactionCategory.GIFT
        assert isinstance(new_note.date, datetime)
        assert new_note.comment == ''
        assert len(self.tracker.notes) == 1
        self.mock_storage.append_csv.assert_called_once()


    def test_add_note_invalid_type(self):       #негативные случай: невалидный тип транзакции
        with pytest.raises(ValueError,match="Unknown type"):
            self.tracker.add_transaction(
                type="aboba",
                amount=1_000,
                category="food",
                date="2020-01-01"
            )

    def test_add_note_negative_amount(self):    #негативные случай: отрицательная сумма
        with pytest.raises(ValueError, match="Amount must be more than 0"):
            self.tracker.add_transaction(
                type="income",
                amount=-100,
                category="salary",
                date="2020-02-02"
            )

    def test_add_category_mismatch(self):       #негативный случай: несовпадение тип-категория
        with pytest.raises(ValueError, match="does not belong to income"):
            self.tracker.add_transaction(
                type='income',
                amount=1000,
                category='food',
                date='2026-03-03'
            )

    #=================================================================================

    def test_get_by_id_existed(self):           #получение транзакции по id (существующая)
        new_note = self.tracker.add_transaction(
            type='income',
            amount=10_000,
            category="gift",
            date="2020-01-01"
        )

        founded_note = self.tracker.get_by_id(1)
        assert new_note == founded_note

    def test_get_by_id_not_existed(self):       #получение транзакции по id (не существующая)
        founded_note = self.tracker.get_by_id(1_000)
        assert founded_note is None

    #===================================================================================

    def test_update_transactions_full_change(self):     #полное обновление имеющейся транзакции
        self.tracker.add_transaction(
            type='income',
            amount=1000,
            category='salary',
            date='2026-01-01',
            comment='Old'
        )
        updated = self.tracker.update_transaction(
            note_id=1,
            type='expense',
            amount=10_000,
            category='taxes',
            date= '2010-01-01',
            comment='ancient'
        )
        assert updated.type == TransactionType.EXPENSE
        assert updated.amount == 10_000
        assert updated.category == TransactionCategory.TAXES
        assert updated.date == datetime.fromisoformat('2010-01-01')
        assert updated.comment == 'ancient'

    def test_update_transaction_not_exist(self):        #негативный случай: обновление несуществующей транзакции
        result = self.tracker.update_transaction(
            note_id=999,
            amount=1500
        )

        assert result is None
        self.mock_storage.save_csv.assert_not_called()

    #====================================================================================

    def setup_filter_data(self):        #заготовка под тест фильтрации
        self.tracker.add_transaction(
            type='income',
            amount=1000,
            category='salary',
            date='2026-01-01',
            comment='Salary Jan'
        )
        self.tracker.add_transaction(
            type='income',
            amount=2000,
            category='freelance',
            date='2026-01-05',
            comment='Freelance work'
        )
        self.tracker.add_transaction(
            type='expense',
            amount=500,
            category='food',
            date='2026-01-10',
            comment='Groceries'
        )
        self.tracker.add_transaction(
            type='expense',
            amount=300,
            category='transport',
            date='2026-01-15',
            comment='Bus ticket'
        )
        self.tracker.add_transaction(
            type='expense',
            amount=1000,
            category='housing',
            date='2026-01-20',
            comment='Rent'
        )

    def test_filter_transactions_by_type(self):         #фильтрация по выбранному типу income
        self.setup_filter_data()
        result = self.tracker.filter_transactions(
            type=TransactionType.INCOME
        )
        assert len(result) == 2
        assert all(n.type == TransactionType.INCOME for n in result)

    def test_filter_transactions_by_date_start(self):       #фильтрация по начальному времени
        self.setup_filter_data()
        result = self.tracker.filter_transactions(
            date_start=datetime(2026,1,7)
        )

        assert len(result) == 3
        assert (note.date <= datetime(2026,1,7) for note in result)

    def test_filter_transactions_no_match(self):            #несовпадающие параметры
        self.setup_filter_data()
        result = self.tracker.filter_transactions(
            type=TransactionType.INCOME,
            categories=[TransactionCategory.FOOD]
        )
        assert len(result) == 0