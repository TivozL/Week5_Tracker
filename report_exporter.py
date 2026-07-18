import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ReportExporter:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def export_to_json(self,report_data: Dict[str,Any], export_path: Path) -> bool:
        try:
            export_data = {
                "export_date": datetime.now().isoformat(),
                "report": report_data
            }
            export_path.parent.mkdir(parents=True, exist_ok=True)
            with open(export_path, 'w', encoding='utf-8') as file:
                json.dump(export_data, file, indent=4, ensure_ascii=False, default=str)

            self.logger.info(
                f"Report exported successfully to {export_path} "
                f"(type: {report_data.get('report_type', 'unknown')})"
                )
            return True
        except IOError as error:
            self.logger.error(f"IO Error while exporting report: {error}")
            return False
        except Exception as error:
            self.logger.error(f"Unexpected error while exporting report: {error}")
            return False