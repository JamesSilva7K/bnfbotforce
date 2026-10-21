"""
Módulo de Edição e Processamento de Documentos PDF
Engine de alta precisão para preenchimento de Declarações com PyMuPDF (fitz).
Altera estritamente: Nome do Lead, RG e CPF, com auto-formatação e pontuação inteligente.
"""

import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import pymupdf
from PIL import Image

from config import GENERATED_PDFS_DIR, PREVIEWS_DIR, FONTS_DIR, TEMPLATE_PDF_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PDF = str(TEMPLATE_PDF_PATH)

BUNDLED_FONT_REG = os.path.join(str(FONTS_DIR), "arial.ttf")
BUNDLED_FONT_BOLD = os.path.join(str(FONTS_DIR), "arialbd.ttf")

FONT_REGULAR_PATH = BUNDLED_FONT_REG if os.path.exists(BUNDLED_FONT_REG) else r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD_PATH = BUNDLED_FONT_BOLD if os.path.exists(BUNDLED_FONT_BOLD) else r"C:\Windows\Fonts\arialbd.ttf"

class PDFEngine:
    def __init__(self, template_path: Optional[str] = None):
        self.template_path = template_path or TEMPLATE_PDF
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template PDF não encontrado em: {self.template_path}")
        
        self.font_reg_path = FONT_REGULAR_PATH if os.path.exists(FONT_REGULAR_PATH) else None
        self.font_bold_path = FONT_BOLD_PATH if os.path.exists(FONT_BOLD_PATH) else None

    @staticmethod
    def format_cpf(raw: str) -> str:
        """
        Formata o CPF inteligentemente com pontuações completas mesmo que o operador digite sem pontuação.
        Ex: 34009182881 -> 340.091.828/81 (padrão idêntico à matriz oficial)
        Ex: 340091828-81 -> 340.091.828-81
        """
        raw_str = str(raw).strip()
        digits = re.sub(r"\D", "", raw_str)
        if len(digits) == 11:
            sep = "/" if "/" in raw_str else ("-" if "-" in raw_str else "/")
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}{sep}{digits[9:]}"
        elif "/" in raw_str or "-" in raw_str:
            return raw_str
        return raw_str

    @staticmethod
    def format_rg(raw: str) -> str:
        """
        Formata o RG inteligentemente com pontuações completas mesmo que o operador digite apenas números.
        Ex: 379467471 -> 37.946.747-1 (padrão idêntico à matriz oficial)
        Ex: 37946747X -> 37.946.747-X
        """
        raw_clean = str(raw).strip()
        clean = re.sub(r"[^0-9Xx]", "", raw_clean).upper()
        if len(clean) == 9:
            return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}-{clean[8]}"
        elif len(clean) == 8:
            return f"{clean[:1]}.{clean[1:4]}.{clean[4:7]}-{clean[7]}"
        elif len(clean) == 10:
            return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}-{clean[8:]}"
        elif "-" in raw_clean or "." in raw_clean:
            return raw_clean
        return clean

    def generate_declaration(
        self,
        nome: str,
        rg: str,
        cpf: str,
        data_emissao: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Gera uma nova declaração em PDF alterando estritamente: Nome do Lead, RG e CPF.
        Pontuações de RG e CPF são aplicadas de forma inteligente e automática.
        Retorna (output_pdf_path, preview_png_path).
        """
        nome_clean = nome.strip().upper()
        rg_clean = self.format_rg(rg)
        cpf_clean = self.format_cpf(cpf)

        # Abre o documento matriz original
        doc = pymupdf.open(self.template_path)
        page = doc[0]

        # Redação limpa estrita das linhas 2 e 3 (área exclusiva do lead)
        rect_lead = pymupdf.Rect(105, 303, 535, 330)
        page.add_redact_annot(rect_lead, fill=(1, 1, 1))
        page.apply_redactions()

        font_reg = pymupdf.Font(fontfile=self.font_reg_path) if self.font_reg_path else pymupdf.Font("helv")
        font_bold = pymupdf.Font(fontfile=self.font_bold_path) if self.font_bold_path else pymupdf.Font("hebo")

        tw = pymupdf.TextWriter(page.rect)
        fontsize = 9.8
        x_left = 106.8
        max_x = 532.4
        y2 = 312.8
        y3 = 325.6

        # Linha 2 padrão: [NOME], portador(a) do RG nº [RG] e CPF nº
        # Linha 3 padrão: [CPF], encontra-se em situação de vulnerabilidade social e em situação de rua,
        test_tw = pymupdf.TextWriter(page.rect)
        r_name = test_tw.append((0, 0), f"{nome_clean}, ", font=font_bold, fontsize=fontsize)
        w_name = r_name[0].width

        r_rg_part = test_tw.append((0, 0), f"portador(a) do RG nº {rg_clean} e CPF nº", font=font_reg, fontsize=fontsize)
        w_rg_part = r_rg_part[0].width

        total_line2_w = w_name + w_rg_part
        available_w = max_x - x_left

        if total_line2_w <= available_w:
            res = tw.append((x_left, y2), f"{nome_clean}, ", font=font_bold, fontsize=fontsize)
            res = tw.append(res[1], "portador(a) do RG nº ", font=font_reg, fontsize=fontsize)
            res = tw.append(res[1], f"{rg_clean} ", font=font_bold, fontsize=fontsize)
            res = tw.append(res[1], "e CPF nº", font=font_reg, fontsize=fontsize)

            res = tw.append((x_left, y3), f"{cpf_clean}, ", font=font_bold, fontsize=fontsize)
            res = tw.append(res[1], "encontra-se em situação de vulnerabilidade social e ", font=font_reg, fontsize=fontsize)
            res = tw.append(res[1], "em situação de rua,", font=font_bold, fontsize=fontsize)
        else:
            adjusted_fontsize = max(8.5, fontsize * (available_w / total_line2_w))
            res = tw.append((x_left, y2), f"{nome_clean}, ", font=font_bold, fontsize=adjusted_fontsize)
            res = tw.append(res[1], "portador(a) do RG nº ", font=font_reg, fontsize=adjusted_fontsize)
            res = tw.append(res[1], f"{rg_clean} ", font=font_bold, fontsize=adjusted_fontsize)
            res = tw.append(res[1], "e CPF nº", font=font_reg, fontsize=adjusted_fontsize)

            res = tw.append((x_left, y3), f"{cpf_clean}, ", font=font_bold, fontsize=fontsize)
            res = tw.append(res[1], "encontra-se em situação de vulnerabilidade social e ", font=font_reg, fontsize=fontsize)
            res = tw.append(res[1], "em situação de rua,", font=font_bold, fontsize=fontsize)

        tw.write_text(page, color=(0, 0, 0))

        if not output_path:
            out_dir = str(GENERATED_PDFS_DIR)
            os.makedirs(out_dir, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", nome_clean[:20])
            output_path = os.path.join(out_dir, f"declaracao_{safe_name}_{timestamp_str}.pdf")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path, garbage=4, deflate=True)

        preview_dir = str(PREVIEWS_DIR)
        os.makedirs(preview_dir, exist_ok=True)
        base_filename = os.path.splitext(os.path.basename(output_path))[0]
        preview_path = os.path.join(preview_dir, f"{base_filename}.png")

        pix = page.get_pixmap(dpi=150)
        pix.save(preview_path)

        doc.close()

        return output_path, preview_path
