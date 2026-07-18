from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict

class TransactionType(Enum):    #тип транзакции
    INCOME = "income"
    EXPENSE = "expense"

class TransactionCategory(Enum):    #категории транзакций

    SALARY = "salary"           #входные
    FREELANCE = "freelance"
    INVESTMENT = "investment"
    GIFT = "gift"
    OTHER_INCOME = "other_income"

    FOOD = "food"               #выходные
    TRANSPORT = "transport"
    HOUSING = "housing"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    EDUCATION = "education"
    TAXES = "taxes"
    OTHER_EXPENSE = "other_expense"

    @classmethod
    def get_transactions_for_type(cls, type:TransactionType) -> List:
        if type == TransactionType.INCOME:
            return [
                cls.SALARY,
                cls.FREELANCE,
                cls.INVESTMENT,
                cls.GIFT,
                cls.OTHER_INCOME
            ]
        else:
            return [
                cls.FOOD,
                cls.TRANSPORT,
                cls.HOUSING,
                cls.ENTERTAINMENT,
                cls.HEALTH,
                cls.EDUCATION,
                cls.TAXES,
                cls.OTHER_EXPENSE
            ]

@dataclass
class Note:     #основная запись в csv файле транзакций
    id: int
    type: TransactionType
    amount: float
    category: TransactionCategory
    date: datetime
    comment: str=""

    def from_note_to_dict(self) -> Dict:        #из объекта Note создаёт словарь для записи
        return {
            'id': self.id,
            'type': self.type.value,
            'amount': self.amount,
            'category': self.category.value,
            'date': self.date.isoformat(),
            'comment': self.comment
        }

    @classmethod
    def from_dict_to_note(cls,data: Dict):      #из словаря создаёт объект Note
        return cls(
            id=int(data['id']),
            type=TransactionType(data['type']),
            amount=float(data['amount']),
            category=TransactionCategory(data['category']),
            date=datetime.fromisoformat(data['date']),
            comment=data.get('comment', '')
        )

    def __str__(self) -> str:
        symbol = "↑" if self.type == TransactionType.INCOME else "↓"
        return (f"[{self.id}] {symbol} {self.type.value} | {self.amount:.2f} |"
                f" {self.category.value} | {self.date.strftime('%Y-%m-%d %H:%M')} {self.comment[:20]}")

    def is_income(self) -> bool:
        return self.type == TransactionType.INCOME

    def is_expense(self) -> bool:
        return self.type == TransactionType.EXPENSE