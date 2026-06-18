"""PaperTrail — Receipt/Invoice Scanner (regex-based extraction).

Merged from the original ``scanexcel``: parse unstructured text into
structured rows and export as CSV.
"""

from __future__ import annotations

import csv
import io
import json
import re

from papertrail.core.database import Database
from papertrail.core.models import ExtractedRow


class ReceiptParser:
    """Extract table rows from receipt/invoice text using regex heuristics."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def parse(self, text: str, source: str = "manual") -> list[ExtractedRow]:
        """Parse unstructured text into structured rows."""
        rows: list[ExtractedRow] = []
        for line in (l.strip() for l in text.splitlines() if l.strip()):
            row = self._parse_line(line)
            if row is not None:
                rows.append(row)
        return rows

    def process_and_store(self, text: str, source: str = "manual") -> list[ExtractedRow]:
        """Parse *text* into rows, store as a ``receipt`` document, return rows."""
        rows = self.parse(text, source)
        payload = {"rows": [r.model_dump() for r in rows], "source": source}
        self.db.insert_document(
            domain="receipt",
            title=source,
            text_content="\n".join(r.raw for r in rows),
            payload=payload,
            source=source,
        )
        return rows

    def to_csv(self) -> str:
        """Build a CSV string from all stored receipt rows."""
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=["date", "description", "amount", "confidence", "raw"])
        writer.writeheader()
        for rec in self.db.list_documents(domain="receipt"):
            payload = json.loads(str(rec.get("payload", "{}")))
            for row in payload.get("rows", []):
                writer.writerow(row)
        out.seek(0)
        return out.getvalue()

    def _parse_line(self, line: str) -> ExtractedRow | None:
        amounts = re.findall(r"-?\$?\d+\.\d{2}|\$\d+", line)
        if not amounts:
            return None
        date_m = re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", line)
        amount = amounts[-1].replace("$", "")
        rest = re.sub(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", "", line)
        rest = re.sub(r"-?\$?\d+(?:\.\d{2})?", "", rest).strip(" -,:\\t")
        return ExtractedRow(
            date=date_m.group(0) if date_m else "",
            description=rest or line[:60],
            amount=amount,
            confidence=0.86 if amount else 0.62,
            raw=line,
        )
