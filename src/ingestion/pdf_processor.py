import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pdfplumber

from src.utils.logger import logger

class PDFProcessor:
    def __init__(self):
        # Regex to find numbers followed by %, Cr, B, or M (e.g., 42%, 10.5 Cr, 1B, 50 M)
        self.stats_pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|Cr|B|M)\b', re.IGNORECASE)

    def _convert_table_to_markdown(self, table: List[List[Optional[str]]]) -> str:
        if not table or not table[0]:
            return ""
        
        md_lines = []
        cleaned_table = []
        for row in table:
            cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
            cleaned_table.append(cleaned_row)

        header = cleaned_table[0]
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("|" + "|".join(["---" for _ in header]) + "|")

        for row in cleaned_table[1:]:
            row_extended = row + [""] * (len(header) - len(row))
            row_extended = row_extended[:len(header)]
            md_lines.append("| " + " | ".join(row_extended) + " |")

        return "\n".join(md_lines)

    def _extract_headings_and_text(self, page) -> str:
        words = page.extract_words(extra_attrs=["size", "fontname"])
        if not words:
            return ""
            
        lines = {}
        for w in words:
            # Round top to group words roughly on the same line
            top = round(w["top"] / 2) * 2
            if top not in lines:
                lines[top] = []
            lines[top].append(w)
            
        sorted_tops = sorted(lines.keys())
        
        content = []
        for top in sorted_tops:
            line_words = sorted(lines[top], key=lambda x: x["x0"])
            text = " ".join(w["text"] for w in line_words)
            
            # Simple heuristic: if font size is larger or bold, treat as heading
            first_word = line_words[0]
            size = first_word.get("size", 10)
            fontname = first_word.get("fontname", "").lower()
            
            if size > 14 or "bold" in fontname:
                content.append(f"## {text}")
            else:
                content.append(text)
                
        return "\n".join(content)

    def process_pdf(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return None

        logger.info(f"Processing PDF: {path.name}")
        
        sections = []
        tables_md = []
        key_stats = set()
        
        try:
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    images = page.images
                    text = page.extract_text() or ""
                    
                    if len(images) >= 3 and len(text.strip()) < 100:
                        logger.info(f"Page {page_num} in {path.name} is image-heavy. Manual review may be needed.")
                        sections.append(f"\n[Page {page_num} - Image-heavy content]\n")
                        continue

                    page_tables = page.extract_tables()
                    for t in page_tables:
                        md_table = self._convert_table_to_markdown(t)
                        if md_table:
                            tables_md.append(md_table)
                            sections.append(f"\n{md_table}\n")

                    page_text = self._extract_headings_and_text(page)
                    if page_text:
                        sections.append(page_text)
                        
                        stats = self.stats_pattern.findall(page_text)
                        key_stats.update(stats)
                        
            content_str = "\n\n".join(sections)
            
            result = {
                "filename": path.name,
                "total_pages": total_pages,
                "sections": content_str,
                "tables": tables_md,
                "key_stats": list(key_stats)
            }
            return result
            
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return None
