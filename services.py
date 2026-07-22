from models import *
from typing import List,Dict,Optional
from storage import *
from pathlib import Path
from datetime import datetime
from validators import Validator
import logging


class ServiceTracker:
    def __init__(self, storage: StorageServices):
        self.storage = storage
        self.logger = logging.getLogger(self.__class__.__name__)

        self.notes: List[Note] = []

        self._load_data()

    def _load_data(self):           #загрузка данных из CSV
        raw_data = self.storage.load_csv()
        loaded_notes = []
        skipped_rows = 0

        for idx,item in enumerate(raw_data):
            try:
                note = Note.from_dict_to_note(item)
                loaded_notes.append(note)
            except (ValueError, KeyError, TypeError) as error:
                self.logger.warning(f"Skipping invalid row {idx + 1}: {error}. Data: {item}")
                skipped_rows += 1
                continue
        self.notes = loaded_notes
        if skipped_rows > 0:
            self.logger.warning(f"Loaded {len(self.notes)} notes, skipped {skipped_rows} invalid rows")
        else:
            self.logger.info(f"Loaded {len(self.notes)} notes from CSV")


    def _get_next_id(self) -> int:      #генерация нового ID на основе максимального ID в списке
        if not self.notes:
            return 1
        return max(note.id for note in self.notes) + 1

    def _save_all(self) -> None:        # сохранение всех транзакций в CSV
        notes_dict = [note.from_note_to_dict() for note in self.notes]
        self.storage.save_csv(notes_dict)
        self.logger.debug(f"Saved {len(notes_dict)} notes")

    def add_transaction(                #добавление новой транзакции
            self,
            type: str,
            amount: Any,
            category: str,
            date: str,
            comment: str = ""
    ) -> Note:
        try:
            valid_dict = Validator.is_all_valid(
                type=type,
                amount=amount,
                category=category,
                date=date,
                comment=comment
            )
        except ValueError as error:
            self.logger.warning(f"Got invalid data: {error}")
            raise

        new_id = self._get_next_id()
        self.logger.info(f"New ID generated: {new_id}")

        new_note = Note(
            id=new_id,
            type=valid_dict["type"],
            amount=valid_dict["amount"],
            category=valid_dict["category"],
            date=valid_dict["date"],
            comment=valid_dict["comment"]
        )

        self.notes.append(new_note)
        self.storage.append_csv(new_note.from_note_to_dict())

        self.logger.info(f"Added new Note: ID={new_note.id}, {new_note.type.value}, {new_note.amount:.2f}")
        return new_note

    def add_transactions_bulk(self, new_notes: List[Note]) -> int:  #массовое добавление транзакций (для импорта)
        if not new_notes:
            return 0

        added = 0
        existing_ids = {note.id for note in self.notes}

        for note in new_notes:
            if note.id in existing_ids:
                self.logger.warning(f"Skipping note with existing ID: {note.id}")
                continue

            # Генерируем новый ID
            note.id = self._get_next_id()
            self.notes.append(note)
            added += 1

        if added > 0:
            # Сохраняем все заново (перезаписываем CSV)
            self._save_all()
            self.logger.info(f"Added {added} transactions in bulk")

        return added

    def import_from_json(self, file_path: Path) -> int:     #импорт из json

        imported = 0
        skipped = 0

        existing_transactions = set()   #множество кортежей с данными имеющихся записей
        for note in self.notes:
            key = (note.type, note.amount, note.category, note.date, note.comment)
            existing_transactions.add(key)

        try:
            for transaction_data in self.storage.read_from_json(file_path):
                try:
                    type_str = transaction_data.get('type')     #извлечение данных для валидации
                    amount = transaction_data.get('amount')
                    category_str = transaction_data.get('category')
                    date_str = transaction_data.get('date')
                    comment = transaction_data.get('comment', '')

                    validated_dict = Validator.is_all_valid(    #валидация
                        type=type_str,
                        amount=amount,
                        category=category_str,
                        date=date_str,
                        comment=comment
                    )
                    note_key =(             #кортеж ключ для проверки нахождения в существующих записях
                        validated_dict["type"],
                        validated_dict["amount"],
                        validated_dict["category"],
                        validated_dict["date"],
                        validated_dict["comment"]
                    )

                    if note_key in existing_transactions:       #если такая запись уже есть
                        self.logger.info(f"Skipping duplicate transaction")
                        skipped += 1
                        continue

                    new_note = Note(
                        id=self._get_next_id(),
                        type=validated_dict["type"],
                        amount=validated_dict["amount"],
                        category=validated_dict["category"],
                        date=validated_dict["date"],
                        comment=validated_dict["comment"]
                    )

                    self.notes.append(new_note)
                    existing_transactions.add(note_key)  # Добавляем в множество
                    imported += 1

                except (ValueError, KeyError, TypeError) as error:
                    self.logger.warning(f"Skipping invalid transaction: {error}. Data: {transaction_data}")
                    skipped += 1
                    continue

            if imported > 0:
                self._save_all()
                self.logger.info(f"Imported {imported} transactions from {file_path}")

            if skipped > 0:
                self.logger.warning(f"Skipped {skipped} invalid transactions")

            return imported

        except FileNotFoundError as error:
            self.logger.error(f"File not found: {error}")
            raise
        except json.JSONDecodeError as error:
            self.logger.error(f"Invalid JSON format: {error}")
            raise

    def get_all_transactions(self):
        return self.notes.copy()

    def get_by_id(self,note_id: int) -> Optional[Note]:     #поиск по id
        for note in self.notes:
            if note.id == note_id:
                return note
        return None

    def update_transaction(                 #обновление транзакции
            self,
            note_id: int,
            type: Optional[str] = None,
            amount: Optional[Any] = None,
            category: Optional[str] = None,
            date: Optional[str] = None,
            comment: Optional[str] = None
    ) -> Optional[Note]:

        note = self.get_by_id(note_id)
        if note is None:
            self.logger.warning(f"Note with ID {note_id} not found")
            return None

        old_type = note.type    #старые данные для логов
        old_amount = note.amount
        old_category = note.category
        old_date = note.date
        old_comment = note.comment

        new_type = type if type is not None else note.type.value        #
        new_amount = amount if amount is not None else note.amount
        new_category = category if category is not None else note.category.value
        new_date = date if date is not None else note.date.isoformat()
        new_comment = comment if comment is not None else note.comment

        try:
            validated = Validator.is_all_valid(     #валидация новых данных
                type=new_type,
                amount=new_amount,
                category=new_category,
                date=new_date,
                comment=new_comment
            )
        except ValueError as error:
            self.logger.warning(f"Invalid data for update: {error}")
            raise

        note.type = validated['type']           #обновление
        note.amount = validated['amount']
        note.category = validated['category']
        note.date = validated['date']
        note.comment = validated['comment']

        self._save_all()

        self.logger.info(
            f"Note updated ID={note_id}: "
            f"{old_type.value}->{note.type.value}, "
            f"{old_amount:.2f}->{note.amount:.2f}, "
            f"{old_category.value}->{note.category.value}"
        )
        return note

    def delete_transactions(self,new_id: int):      #удаление транзакции
        target = self.get_by_id(new_id)
        if target is None:
            self.logger.warning(f"Note with ID {new_id} not found")
            return False
        self.notes.remove(target)
        self._save_all()
        self.logger.info(
            f"Note with ID {new_id} was removed"
            f"{target.type.value}, {target.amount:.2f}, {target.category.value}"
        )
        return True

    def filter_transactions(                                #общий метод фильтрации
            self,
            type: Optional[TransactionType] = None,
            categories: Optional[List[TransactionCategory]] = None,
            date_start: Optional[datetime] = None,
            date_end: Optional[datetime] = None,
            notes: Optional[List[Note]] = None
    ) -> List[Note]:

        if notes is None:
            notes = self.notes

        result = notes
            #по типам
        if type is not None:
            result = [note for note in result if note.type == type]

            #по категориям
        if categories:
            result = [note for note in result if note.category in categories]

            #по датам
        if date_start is not None:
            result = [note for note in result if note.date >= date_start]
        if date_end is not None:
            result = [note for note in result if note.date <= date_end]

        return result
