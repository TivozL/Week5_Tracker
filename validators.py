import logging
from datetime import datetime
from typing import Any, Dict

from models import TransactionType, TransactionCategory

class Validator:
    logger = logging.getLogger(__name__)

    @staticmethod
    def is_valid_type(new_type:str):
        if not isinstance(new_type,str):
            raise ValueError("Type must be string")

        try:
            return TransactionType(new_type.strip().lower())
        except ValueError:
            raise ValueError(f"Unknown type: {new_type}. Available types: income, expense")

    @staticmethod
    def is_valid_amount(new_amount: Any):
        try:
            new_amount = float(new_amount)
        except (ValueError, TypeError):
            raise ValueError("Amount must be a number")

        if new_amount <= 0:
            raise ValueError(f"Amount must be more than 0, got instead: {new_amount}")

        return new_amount

    @staticmethod
    def is_valid_category(new_category: str, type: TransactionType):   #валидация и преобразование в категорию из мнрожетва
        if not isinstance(new_category,str):
            raise ValueError(f"Category must be string")

        try:
            category = TransactionCategory(new_category.strip().lower())
        except ValueError:
            raise ValueError(f"Unknown category: {new_category}")

        valid_categories = TransactionCategory.get_transactions_for_type(type)
        if category not in valid_categories:
            available_values = [c.value for c in valid_categories]
            raise ValueError(
                f"Category '{category}' does not belong to {type.value}. "
                f"Available: {', '.join(available_values)}"
            )
        return category

    @staticmethod
    def is_valid_date(new_date: str) ->datetime:            #валидность даты (формат)
        if not isinstance(new_date, str):
            raise ValueError("Date must be string")

        try:
            return datetime.fromisoformat(new_date)
        except ValueError:
            raise ValueError(
                f"Invalid date format: {new_date}. "
                "Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS instead"
            )

    @staticmethod
    def is_valid_comment(new_comment: str, max_len = 200):      #валидность комментариев, длиной не более 200
        if not isinstance(new_comment,str):
            raise ValueError(f"Comment must be string!")

        cleaned_comment = new_comment.strip()

        if len(cleaned_comment) > max_len:
            raise ValueError(f"Maximum comment length is {max_len}!"
                             f"(now - {len(cleaned_comment)}")
        return cleaned_comment

    @classmethod
    def is_all_valid(                   #проверка всех полей
        cls,
        type: str,
        amount: Any,
        category: str,
        date: str,
        comment: str = ""
    ) -> Dict[str, Any]:

        validated_type = cls.is_valid_type(type)
        validated_amount = cls.is_valid_amount(amount)
        validated_date = cls.is_valid_date(date)
        validated_category = cls.is_valid_category(category, validated_type)
        validated_comment = cls.is_valid_comment(comment)

        return {
            'type': validated_type,
            'amount': validated_amount,
            'date': validated_date,
            'category': validated_category,
            'comment': validated_comment
        }