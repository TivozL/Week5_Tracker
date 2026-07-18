import argparse
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

from models import TransactionType, TransactionCategory, Note
from storage import StorageServices
from services import ServiceTracker
from report import ReportBuilder
from report_exporter import ReportExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('finance_tracker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TrackerCLI:
    def __init__(self, data_dir: Path):
        self.storage = StorageServices(data_dir)
        self.tracker = ServiceTracker(self.storage)
        self.report_builder = ReportBuilder(self.tracker)
        self.report_exporter = ReportExporter()
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_transaction(self, args):
        try:
            current_date = args.date if args.date else datetime.now().isoformat()

            new_note = self.tracker.add_transaction(
                type=args.type,
                amount=args.amount,
                category=args.category,
                date=current_date,
                comment=args.comment or ""
            )

            self.logger.info(f"User added new transaction ID: {new_note.id}")
            print(f"Transaction added!")
            print(f"    {new_note}")
            return new_note
        except ValueError as error:
            print(f"Error: {error}")
            return None

    def list_transactions(self, args):
        try:
            type_enum = None
            categories = None
            date_start = None
            date_end = None

            if args.type:
                type_enum = TransactionType(args.type)

            if args.category:
                categories = [TransactionCategory(c.strip()) for c in args.category.split(',')]

            if args.start_date:
                date_start = datetime.fromisoformat(args.start_date)

            if args.end_date:
                date_end = datetime.fromisoformat(args.end_date)

            notes = self.tracker.filter_transactions(
                type=type_enum,
                categories=categories,
                date_start=date_start,
                date_end=date_end
            )

            if not notes:
                print("Transactions not found")
                return

            print(f"\nTotal transactions: {len(notes)}")
            for note in notes:
                print(note)

            total_income = sum(n.amount for n in notes if n.is_income())
            total_expense = sum(n.amount for n in notes if n.is_expense())
            print(f"All incomes: {total_income:.2f}")
            print(f"All expenses: {total_expense:.2f}")
            print(f"Balance: {(total_income - total_expense):.2f}")

            self.logger.info(f"User listed {len(notes)} transactions")

        except ValueError as error:
            print(f"Filter error: {error}")
        except Exception as error:
            self.logger.error(f"Unexpected error in list: {error}")
            print(f"Error: {error}")

    def update_transaction(self, args):
        try:
            existing_note = self.tracker.get_by_id(args.id)
            if existing_note is None:
                print(f"Transaction with ID {args.id} not found")
                return None

            type_str = args.type if hasattr(args, 'type') and args.type else None
            amount = args.amount if hasattr(args, 'amount') and args.amount is not None else None
            category = args.category if hasattr(args, 'category') and args.category else None
            date = args.date if hasattr(args, 'date') and args.date else None
            comment = args.comment if hasattr(args, 'comment') and args.comment else None

            updated_note = self.tracker.update_transaction(
                note_id=args.id,
                type=type_str,
                amount=amount,
                category=category,
                date=date,
                comment=comment
            )

            if updated_note:
                self.logger.info(f"User updated transaction ID: {args.id}")
                print("Transaction updated successfully!")
                print(f"    {updated_note}")
                return updated_note
            else:
                print(f"Failed to update transaction ID: {args.id}")
                return None

        except ValueError as error:
            print(f"Error: {error}")
            return None
        except Exception as error:
            self.logger.error(f"Unexpected error in update: {error}")
            print(f"Error: {error}")
            return None

    def show_stats(self, args):
        try:
            type_enum = None
            categories = None
            date_start = None
            date_end = None

            if args.type:
                type_enum = TransactionType(args.type)

            if args.category:
                categories = [TransactionCategory(c.strip()) for c in args.category.split(',')]

            if args.start_date:
                date_start = datetime.fromisoformat(args.start_date)

            if args.end_date:
                date_end = datetime.fromisoformat(args.end_date)

            stats = self.report_builder.get_stats(
                type=type_enum,
                categories=categories,
                date_start=date_start,
                date_end=date_end
            )

            self._print_stats(stats)

        except ValueError as error:
            print(f"Filter error: {error}")
        except Exception as error:
            self.logger.error(f"Unexpected error in stats: {error}")
            print(f"Error: {error}")

    @staticmethod
    def _print_stats(stats: Dict[str, Any]):
        report_type = stats.get('report_type', 'full_stats').upper()
        print(f"\nTRANSACTION STATISTICS ({report_type})")
        print()

        print("General information:")
        print(f"  Total transactions: {stats['total_transactions']}")
        print(f"  Income: {stats['income_count']}")
        print(f"  Expenses: {stats['expense_count']}")

        if stats['date_start'] and stats['date_end']:
            print(f"  Period: {stats['date_start'].strftime('%Y-%m-%d %H:%M')} - "
                  f"{stats['date_end'].strftime('%Y-%m-%d %H:%M')}")

        print()
        print("Finance:")
        print(f"  Total income: {stats['total_income']:.2f}.")
        print(f"  Total expenses: {stats['total_expense']:.2f}.")
        print(f"  Balance: {stats['balance']:.2f}.")

        if stats['income_by_categories']:
            print()
            print("Income by category:")
            for cat, amount in sorted(stats['income_by_categories'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {cat}: {amount:.2f} .")

        if stats['expense_by_categories']:
            print()
            print("Expenses by category:")
            total_expense = stats['total_expense']
            for cat, amount in sorted(stats['expense_by_categories'].items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_expense * 100) if total_expense > 0 else 0
                print(f"  {cat}: {amount:.2f}. ({percentage:.1f}%)")

        print()

    def import_transactions(self, args):
        try:
            file_path = Path(args.file)

            if not file_path.exists():
                print(f"File not found: {file_path}")
                return

            file_size = file_path.stat().st_size
            self.logger.info(f"Starting import from {file_path} (size: {file_size} bytes)")

            imported = self.tracker.import_from_json(file_path)

            if imported > 0:
                print(f"Imported: {imported} transactions")
            else:
                print("No transactions to import")

        except json.JSONDecodeError:
            print(f"Invalid JSON format in file: {args.file}")
        except ValueError as error:
            print(f"Error: {error}")
        except Exception as error:
            self.logger.error(f"Unexpected error in import: {error}")
            print(f"Unexpected error: {error}")

    def delete_transaction(self, args):
        try:
            existing_note = self.tracker.get_by_id(args.id)
            if existing_note is None:
                print(f"Transaction with ID {args.id} not found")
                return False

            if hasattr(args, 'force') and args.force:
                confirm = 'y'
            else:
                print(f"Are you sure you want to delete transaction {args.id}?")
                print(f"    {existing_note}")
                confirm = input("Delete? (y/N): ").strip().lower()

            if confirm != 'y':
                print("Deletion cancelled")
                return False

            success = self.tracker.delete_transactions(args.id)

            if success:
                self.logger.info(f"User deleted transaction ID: {args.id}")
                print(f"Transaction {args.id} deleted successfully!")
                return True
            else:
                print(f"Failed to delete transaction ID: {args.id}")
                return False
        except ValueError as error:
            print(f"Error: {error}")
            return False
        except Exception as error:
            self.logger.error(f"Unexpected error in delete: {error}")
            print(f"Error: {error}")
            return False

    def export_report(self, args):
        try:
            type_enum = None
            categories = None
            date_start = None
            date_end = None

            if args.type:
                type_enum = TransactionType(args.type)

            if args.category:
                categories = [TransactionCategory(c.strip()) for c in args.category.split(',')]

            if args.start_date:
                date_start = datetime.fromisoformat(args.start_date)

            if args.end_date:
                date_end = datetime.fromisoformat(args.end_date)

            stats = self.report_builder.get_stats(
                type=type_enum,
                categories=categories,
                date_start=date_start,
                date_end=date_end
            )

            output_path = Path(args.output)
            success = self.report_exporter.export_to_json(stats, output_path)

            if success:
                print(f"Report exported successfully to {output_path}")
                self.logger.info(f"User exported report to {output_path}")
            else:
                print(f"Failed to export report to {output_path}")

        except ValueError as error:
            print(f"Error: {error}")
        except Exception as error:
            self.logger.error(f"Unexpected error in export: {error}")
            print(f"Error: {error}")


def main():
    if len(sys.argv) == 1:
        print("Personal Finance Tracker")
        print("Usage: python cli.py <command> [options]")
        print("\nCommands:")
        print("  add     - Add new transaction")
        print("  list    - List transactions")
        print("  stats   - Show statistics")
        print("  update  - Update transaction")
        print("  delete  - Delete transaction")
        print("  import  - Import from JSON")
        print("  export  - Export report to JSON")
        print("\nFor help: python cli.py --help")
        return

    parser = argparse.ArgumentParser(
        description="Console finance tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add transactions
  python cli.py add --type income --amount 50000 --category salary --date 2026-01-15 --comment "Monthly salary"
  python cli.py add --type expense --amount 5000 --category food --date 2026-01-16 --comment "Groceries"

  # List transactions
  python cli.py list
  python cli.py list --type expense --category food,transport
  python cli.py list --start-date 2026-01-01 --end-date 2026-01-31

  # Statistics
  python cli.py stats
  python cli.py stats --type income --start-date 2026-01-01

  # Update transaction
  python cli.py update --id 1 --amount 55000 --comment "Salary with bonus"

  # Delete transaction
  python cli.py delete --id 3
  python cli.py delete --id 3 --force

  # Import/Export
  python cli.py import --file transactions.json
  python cli.py export --output reports/stats.json
        """
    )

    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add new transaction")
    add_parser.add_argument("--type", required=True, choices=["income", "expense"], help="Transaction type")
    add_parser.add_argument("--amount", required=True, type=float, help="Transaction amount")
    add_parser.add_argument("--category", required=True, help="Transaction category")
    add_parser.add_argument("--date", help="Transaction date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    add_parser.add_argument("--comment", help="Transaction comment")

    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--type", choices=["income", "expense"], help="Filter by type")
    list_parser.add_argument("--category", help="Filter by categories (comma-separated)")
    list_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    list_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")

    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--type", choices=["income", "expense"], help="Filter by type")
    stats_parser.add_argument("--category", help="Filter by categories (comma-separated)")
    stats_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    stats_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")

    export_parser = subparsers.add_parser("export", help="Export report to JSON")
    export_parser.add_argument("--output", required=True, help="Output file path")
    export_parser.add_argument("--type", choices=["income", "expense"], help="Filter by type")
    export_parser.add_argument("--category", help="Filter by categories (comma-separated)")
    export_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    export_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")

    import_parser = subparsers.add_parser("import", help="Import transactions from JSON")
    import_parser.add_argument("--file", required=True, help="JSON file path")

    update_parser = subparsers.add_parser("update", help="Update transaction")
    update_parser.add_argument("--id", required=True, type=int, help="Transaction ID")
    update_parser.add_argument("--type", choices=["income", "expense"], help="New transaction type")
    update_parser.add_argument("--amount", type=float, help="New transaction amount")
    update_parser.add_argument("--category", help="New transaction category")
    update_parser.add_argument("--date", help="New transaction date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    update_parser.add_argument("--comment", help="New transaction comment")

    delete_parser = subparsers.add_parser("delete", help="Delete transaction")
    delete_parser.add_argument("--id", required=True, type=int, help="Transaction ID")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    data_dir = Path.cwd() / "data"
    cli = TrackerCLI(data_dir)

    if args.command == "add":
        cli.add_transaction(args)
    elif args.command == "list":
        cli.list_transactions(args)
    elif args.command == "stats":
        cli.show_stats(args)
    elif args.command == "export":
        cli.export_report(args)
    elif args.command == "import":
        cli.import_transactions(args)
    elif args.command == "update":
        cli.update_transaction(args)
    elif args.command == "delete":
        cli.delete_transaction(args)


if __name__ == "__main__":
    main()