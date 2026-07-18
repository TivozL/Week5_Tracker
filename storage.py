import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Any, Iterator
from datetime import datetime

class StorageServices:

    def __init__(self,data_dir: Path):
        self.data_dir = data_dir        #data_dir папка для хранения основных данных
        self.csv_path = self.data_dir / "transactions.csv"
        self.json_path = self.data_dir / "cache.json"
        self.delimiter = ','

        self.logger = logging.getLogger(self.__class__.__name__)
        self._ensure_directory()


    def _ensure_directory(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    #============ CSV методы ===================

    def load_csv(self) -> List[Dict[str, str]]:       #загрузка записей из csv
        if not self.csv_path.exists():
            return []

        try:
            with open(self.csv_path,'r',encoding='utf-8') as file:
                reader = csv.DictReader(file,delimiter=self.delimiter)
                return list(reader)

        except IOError:
            return []
        except csv.Error:
            return []

    def save_csv(self, notes: List[Dict[str,Any]]):         #полная перезапись csv
        if not notes:       #при подаче пустого списка файл удаляется
            if self.csv_path.exists():
                self.csv_path.unlink()
                self.logger.info("CSV file removed (empty list)")
            return

        try:
            fieldnames = list(notes[0].keys())
            with open(self.csv_path, 'w',encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=self.delimiter)
                writer.writeheader()
                writer.writerows(notes)
                self.logger.info(f"Saved {len(notes)} notes in {self.csv_path}")
                return
        except IOError as error:
            self.logger.error(f"Save error {error}")
            raise

    def append_csv(self, new_note: Dict[str,Any]):          #добавление записи в конец csv
        if not new_note:
            self.logger.warning("Trying to add empty note")
            return
        try:
            file_exists = self.csv_path.exists()
            fieldnames = list(new_note.keys())

            with open(self.csv_path, 'a',encoding='utf-8',newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=self.delimiter)

                if not file_exists:
                    writer.writeheader()
                    self.logger.info(f"New CSV file was made with a header")

                writer.writerow(new_note)
                self.logger.info(f"Added new not in CSV: ID={new_note.get('id', 'unknown')}")

        except IOError as error:
            self.logger.error(f"Error add new note: {error}")
            raise

#===========JSON метод для импорта===========

    def read_from_json(self, file_path: Path) -> Iterator[Dict[str, Any]]:     #генератор для чтения транзакций из стороннего json

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                if not isinstance(data, list):
                    self.logger.warning(f"Expected list at root, got {type(data)} in {file_path}")
                    return

                for transaction in data:
                    if not isinstance(transaction, dict):
                        self.logger.warning(f"Skipping non-dict item in {file_path}")
                        continue

                    yield transaction

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in {file_path}: {e}")
            raise
        except IOError as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise