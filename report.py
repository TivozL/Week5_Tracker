import logging
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional

from models import TransactionType, Note, TransactionCategory
from services import ServiceTracker

class ReportType(Enum):
    FULL = "full_stats"
    BY_PERIOD = "by_period"
    BY_CATEGORY = "by_category"
    BY_TYPE = "by_type"
    BY_PERIOD_AND_TYPE = "by_period_and_type"
    EMPTY = "empty_report"

class ReportBuilder:
    def __init__(self, tracker: ServiceTracker):
        self.tracker = tracker
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def get_default_stat_dict() -> Dict[str, Any]:      #генерирует шаблон отчёта
        return {
            "report_type": None,
            "total_transactions": 0,
            "total_income": 0.0,
            "total_expense": 0.0,
            'income_count': 0,
            'expense_count': 0,
            "date_start": None,
            "date_end": None,
            "income_by_categories": {},
            "expense_by_categories": {},
            "balance": 0
        }

    def _calculate_stats_from_notes(self, notes: List[Note],report_type: ReportType)-> Dict[str,Any]:       #вспомогательный метод, считает отчёт для списка
        stats = self.get_default_stat_dict()

        if not notes:
            self.logger.warning("No transactions found")
            stats['report_type'] = ReportType.EMPTY.value
            return stats

        for note in notes:
            stats["total_transactions"] += 1       #всего транзакций

            if note.type == TransactionType.INCOME:  #Если транзакция это зачисление
                stats["total_income"] += note.amount
                stats["income_count"] += 1
                stats["income_by_categories"][note.category.value] = \
                    stats["income_by_categories"].get(note.category.value, 0) + note.amount
            else:                                   #если расходы
                stats["total_expense"] += note.amount
                stats["expense_count"] += 1
                stats["expense_by_categories"][note.category.value] = \
                    stats["expense_by_categories"].get(note.category.value, 0) + note.amount

            if stats["date_start"] is None or note.date < stats["date_start"]:    #самая ранняя и поздняя даты
                stats["date_start"] = note.date
            if stats["date_end"] is None or note.date > stats["date_end"]:
                stats["date_end"] = note.date

        stats["balance"] = stats["total_income"] - stats["total_expense"]
        stats["report_type"] = report_type.value

        self.logger.info(
            f"Generated {report_type.value} report: "
            f"{stats['total_transactions']} transactions"
        )
        return stats

    def get_stats(                  #общий метод для подсчёта статистики по заданным фильтрам
            self,
            type: Optional[TransactionType] = None,
            categories: Optional[List[TransactionCategory]] = None,
            date_start: Optional[datetime] = None,
            date_end: Optional[datetime] = None
    ) -> Dict[str, Any]:

        filtered_notes = self.tracker.filter_transactions(
            type=type,
            categories=categories,
            date_start=date_start,
            date_end=date_end
        )

        # Определяем тип отчета
        if date_start is not None and date_end is not None and type is not None:
            report_type = ReportType.BY_PERIOD_AND_TYPE
        elif date_start is not None or date_end is not None:
            report_type = ReportType.BY_PERIOD
        elif type is not None:
            report_type = ReportType.BY_TYPE
        elif categories:
            report_type = ReportType.BY_CATEGORY
        else:
            report_type = ReportType.FULL

        return self._calculate_stats_from_notes(filtered_notes, report_type)
