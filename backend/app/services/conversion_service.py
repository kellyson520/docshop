"""
文件格式转换服务

支持:
- DOCX/DOC → PDF（优先使用 docx2pdf / MS Word COM 原生转换）
- DOCX/DOC → HTML（增强渲染：图片、列表、页眉页脚）
- XLSX/XLS → HTML 表格 / PDF
- 30 天缓存：已转换的 PDF 缓存到磁盘，按源文件哈希索引

设计原则：
1. Windows: 使用 docx2pdf（底层调用 MS Word COM），输出像素级完美
2. 非 Windows 或无 Word: 回退到 LibreOffice headless
3. 最后回退: python-docx 生成增强 HTML
4. 所有 PDF 转换结果按源文件 SHA-256 缓存 30 天
"""

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, List

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("services.conversion")

# ── 缓存配置 ────────────────────────────────────────────────────

CACHE_DIR = os.path.join(settings.TEMP_DIR, "conversions")
CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 天


def _ensure_cache_dir() -> str:
    """确保缓存目录存在。"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    return CACHE_DIR


def _source_hash(file_path: str) -> str:
    """计算源文件的 SHA-256 哈希（用于缓存键）。"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _cache_path(source_hash: str, suffix: str) -> str:
    """返回缓存文件路径：cache_dir / {前2位} / {hash}.{suffix}"""
    prefix = source_hash[:2]
    d = os.path.join(CACHE_DIR, prefix)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{source_hash}{suffix}")


def _cache_meta_path(cache_file: str) -> str:
    """返回缓存元数据文件路径。"""
    return cache_file + ".meta.json"


def _read_cache(source_hash: str, suffix: str) -> Optional[str]:
    """
    读取缓存。如果缓存存在且未过期，返回缓存文件路径；否则返回 None。
    过期缓存会被自动清理。
    """
    cache_file = _cache_path(source_hash, suffix)
    meta_file = _cache_meta_path(cache_file)

    if not os.path.exists(cache_file) or not os.path.exists(meta_file):
        return None

    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        # 元数据损坏 → 清理
        _remove_cache(cache_file)
        return None

    created_at = meta.get("created_at", 0)
    if time.time() - created_at > CACHE_TTL_SECONDS:
        _remove_cache(cache_file)
        return None

    if os.path.getsize(cache_file) == 0:
        _remove_cache(cache_file)
        return None

    logger.info(f"Cache hit: {cache_file} (age: {(time.time() - created_at) / 3600:.1f}h)")
    return cache_file


def _write_cache(source_hash: str, source_path: str, suffix: str, source_file_type: str) -> str:
    """将源文件复制到缓存（用于 PDF 缓存的是转换结果，这里直接复制原文件作缓存）。"""
    cache_file = _cache_path(source_hash, suffix)
    shutil.copy2(source_path, cache_file)

    meta = {
        "created_at": time.time(),
        "source_hash": source_hash,
        "source_file_type": source_file_type,
        "original_size": os.path.getsize(source_path),
    }
    meta_file = _cache_meta_path(cache_file)
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f)

    logger.info(f"Cache write: {cache_file}")
    return cache_file


def _remove_cache(cache_file: str) -> None:
    """删除缓存文件及其元数据。"""
    for f in (cache_file, _cache_meta_path(cache_file)):
        try:
            if os.path.exists(f):
                os.unlink(f)
        except OSError:
            pass


# ── 转换引擎检测 ────────────────────────────────────────────────

def _has_docx2pdf() -> bool:
    """检测 MS Word COM 是否可用（Windows 上通过 win32com 调用 Word）。"""
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _find_libreoffice() -> Optional[str]:
    """查找 LibreOffice 可执行文件路径。"""
    candidates = [
        "libreoffice", "soffice",
        "/usr/bin/libreoffice", "/usr/bin/soffice",
        "/usr/local/bin/libreoffice", "/usr/local/bin/soffice",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return None


# 懒加载检测（只检测一次）
_engine = None  # 'docx2pdf' | 'libreoffice' | 'fallback'


def _detect_engine() -> str:
    """检测最佳转换引擎，只执行一次。"""
    global _engine
    if _engine is not None:
        return _engine

    if _has_docx2pdf():
        _engine = "docx2pdf"
        logger.info("转换引擎: docx2pdf (MS Word COM)")
        return _engine

    lo = _find_libreoffice()
    if lo:
        _engine = "libreoffice"
        logger.info(f"转换引擎: LibreOffice ({lo})")
        return _engine

    _engine = "fallback"
    logger.warning("无原生转换引擎，使用 python-docx HTML 渲染")
    return _engine


def _convert_via_libreoffice(input_path: str, output_dir: str, fmt: str = "pdf") -> Optional[str]:
    """使用 LibreOffice headless 转换。"""
    lo = _find_libreoffice()
    if not lo:
        return None
    try:
        result = subprocess.run(
            [lo, "--headless", "--convert-to", fmt, "--outdir", output_dir, input_path],
            capture_output=True, timeout=120, check=False,
        )
        if result.returncode != 0:
            logger.error(f"LibreOffice 失败: {result.stderr.decode(errors='replace')}")
            return None
        base = os.path.splitext(os.path.basename(input_path))[0]
        out = os.path.join(output_dir, f"{base}.{fmt}")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out
        return None
    except Exception as e:
        logger.error(f"LibreOffice 异常: {e}")
        return None


# ── DOCX → HTML 增强渲染 ────────────────────────────────────────

def _convert_docx_to_html(input_path: str) -> str:
    """
    将 DOCX 转换为增强 HTML。

    相比基础版本，增强内容：
    - 图片（内嵌 base64）
    - 编号列表 / 项目符号列表
    - 页眉 / 页脚
    - 文本框内容
    - 合并单元格的表格
    """
    from docx import Document as DocxDoc
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from lxml import etree
    import base64

    doc = DocxDoc(input_path)
    MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

    # OMML → MathML XSLT
    xsl_path = Path(__file__).parent.parent / "diff_engine" / "omml2mml.xsl"
    xslt_transform = None
    if xsl_path.exists():
        try:
            xslt_doc = etree.parse(str(xsl_path))
            xslt_transform = etree.XSLT(xslt_doc)
        except Exception:
            pass

    # ── 提取图片 ──
    image_map = {}  # rId → base64 data URI
    try:
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                try:
                    img_bytes = rel.target_part.blob
                    ext = os.path.splitext(rel.target_part.partname)[-1].lower()
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg",
                                ".jpeg": "image/jpeg", ".gif": "image/gif",
                                ".bmp": "image/bmp", ".svg": "image/svg+xml",
                                ".webp": "image/webp"}
                    mime = mime_map.get(ext, "image/png")
                    b64 = base64.b64encode(img_bytes).decode()
                    image_map[rel.rId] = f"data:{mime};base64,{b64}"
                except Exception:
                    pass
    except Exception:
        pass

    # ── 页眉页脚 ──
    def _section_html(section, tag: str) -> str:
        """提取节的页眉或页脚为 HTML。"""
        try:
            hdr = getattr(section, tag, None)
            if hdr is None or not hdr.paragraphs:
                return ""
            parts = []
            for p in hdr.paragraphs:
                if p.text.strip():
                    parts.append(f"<p style='margin:0;font-size:9pt;color:#666'>{p.text.strip()}</p>")
            return "".join(parts)
        except Exception:
            return ""

    header_html = ""
    footer_html = ""
    try:
        for section in doc.sections:
            h = _section_html(section, "header")
            f = _section_html(section, "footer")
            if h:
                header_html += h
            if f:
                footer_html += f
    except Exception:
        pass

    # ── 构建 HTML ──
    parts = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>文档预览</title>',
        '<script>MathJax={tex:{inlineMath:[["$","$"]]}};</script>',
        '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>',
        '<style>',
        'body{margin:0;padding:40px;font-family:"Times New Roman","SimSun","Microsoft YaHei",serif;',
        'font-size:12pt;color:#111;line-height:1.6;background:#f0f0f0;}',
        '.docx-page{max-width:210mm;margin:0 auto;padding:20mm 25mm;background:#fff;',
        'box-shadow:0 0 12px rgba(0,0,0,.08);min-height:297mm;}',
        '.docx-header{border-bottom:1px solid #ddd;padding-bottom:8pt;margin-bottom:12pt;text-align:center;}',
        '.docx-footer{border-top:1px solid #ddd;padding-top:8pt;margin-top:12pt;text-align:center;}',
        'h1{font-size:22pt;margin:16pt 0 8pt;font-weight:bold;border-bottom:1px solid #000;padding-bottom:4pt;}',
        'h2{font-size:16pt;margin:14pt 0 6pt;font-weight:bold;}',
        'h3{font-size:14pt;margin:12pt 0 4pt;font-weight:bold;}',
        'p{margin:0 0 6pt 0;}',
        'img{max-width:100%;height:auto;margin:4pt 0;}',
        'table{border-collapse:collapse;width:100%;margin:8pt 0;}',
        'td,th{border:1px solid #333;padding:3pt 6pt;vertical-align:top;font-size:11pt;}',
        'ul,ol{margin:0 0 6pt 0;padding-left:24pt;}',
        'li{margin:2pt 0;}',
        '/* 公式样式 */',
        '.math-block{display:block;text-align:center;margin:12pt 0;padding:4pt 0;}',
        '.math-block mjx-container,.math-block MathJax{display:inline-block!important;}',
        '.math-inline{display:inline;vertical-align:middle;margin:0 2pt;}',
        '.math-inline mjx-container,.math-inline MathJax{display:inline-block!important;vertical-align:middle;}',
        '/* 段落内文字与公式同行 */',
        'p .math-inline,p .math-block{white-space:normal;}',
        'p .math-inline mjx-container{margin:0 1pt;}',
        '@media print{',
        'body{background:#fff;padding:0;}',
        '.docx-page{box-shadow:none;max-width:none;margin:0;padding:0;}',
        '@page{size:A4;margin:20mm;}}',
        '@media(max-width:800px){.docx-page{padding:10px;max-width:100%;margin:0;}}',
        '</style></head><body><div class="docx-page">',
    ]

    if header_html:
        parts.append(f'<div class="docx-header">{header_html}</div>')

    # ── 段落渲染 ──
    for para in doc.paragraphs:
        pf = para.paragraph_format
        css = []
        if pf.alignment == WD_ALIGN_PARAGRAPH.CENTER: css.append("text-align:center")
        elif pf.alignment == WD_ALIGN_PARAGRAPH.RIGHT: css.append("text-align:right")
        elif pf.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY: css.append("text-align:justify")
        if pf.first_line_indent: css.append(f"text-indent:{pf.first_line_indent.pt}pt")
        if pf.space_before: css.append(f"margin-top:{pf.space_before.pt}pt")
        if pf.space_after: css.append(f"margin-bottom:{pf.space_after.pt}pt")
        if pf.line_spacing and pf.line_spacing != 1.0: css.append(f"line-height:{pf.line_spacing}")
        style = ";".join(css) if css else ""

        # 列表检测
        numPr = para._element.find(qn("w:pPr"))
        is_list_item = False
        list_tag = ""
        if numPr is not None:
            numPr_elem = numPr.find(qn("w:numPr"))
            if numPr_elem is not None:
                is_list_item = True
                # 判断有序/无序：检查 ilvl 和 numId
                ilvl = numPr_elem.find(qn("w:ilvl"))
                list_tag = "ol"  # 默认有序，实际可能需要检查 numbering 定义
                # 简单处理：统一用 ul（不确定编号格式时更安全）
                list_tag = "ul"

        is_heading = para.style.name.startswith("Heading")
        hn = para.style.name.replace("Heading ", "") if is_heading else ""

        # ── 空段落 / 仅含图片的段落 ──
        if not para.text.strip() and not para.runs:
            has_math = (
                para._element.findall(f"{{{MNS}}}oMath") +
                para._element.findall(f"{{{MNS}}}oMathPara")
            )
            if not has_math:
                # 检查是否有图片
                images = para._element.findall(".//" + qn("wp:inline")) + para._element.findall(".//" + qn("wp:anchor"))
                has_images = False
                for img_elem in images:
                    blip = img_elem.find(".//" + qn("a:blip"))
                    if blip is not None:
                        rId = blip.get(qn("r:embed"))
                        if rId and rId in image_map:
                            parts.append(f'<p><img src="{image_map[rId]}" alt="图片" style="max-width:100%"></p>')
                            has_images = True
                if not has_images:
                    parts.append('<p><br></p>')
                continue

        # ── 列表包裹 ──
        if is_list_item and not is_heading:
            parts.append(f'<{list_tag}>')

        # ── 段落容器开标签 ──
        default_style = style if style else "margin:3pt 0;line-height:1.5"
        if is_heading:
            parts.append(f'<h{hn} style="{style or "margin:12pt 0 6pt"}">')
        elif is_list_item:
            style_li = style if style else "margin:2pt 0"
            parts.append(f'<li style="{style_li}">')
        else:
            parts.append(f'<p style="{default_style}">')

        # ── 按 XML 子元素文档顺序渲染：文本 run 与数学公式交织 ──
        for child in para._element:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "r":
                # 文本 run
                run_elem = child
                # 检查图片（内嵌 drawing）
                drawings = run_elem.findall(".//" + qn("w:drawing"))
                for dw in drawings:
                    blip = dw.find(".//" + qn("a:blip"))
                    if blip is not None:
                        rId = blip.get(qn("r:embed"))
                        if rId and rId in image_map:
                            parts.append(f'<img src="{image_map[rId]}" alt="图片" style="max-width:100%">')

                # 提取 run 文本
                t_elements = run_elem.findall(qn("w:t"))
                run_text = "".join(t.text or "" for t in t_elements)
                if not run_text:
                    # 可能只有图片或空白，仍需检查 br
                    if run_elem.find(qn("w:br")) is not None:
                        parts.append("<br>")
                    continue

                run_text = run_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

                # 读取格式属性（兼容 w:val="false" 的情况）
                rPr = run_elem.find(qn("w:rPr"))
                is_bold = False
                is_italic = False
                is_underline = False
                font_size_pt = None
                font_name = None
                font_color = None
                if rPr is not None:
                    b = rPr.find(qn("w:b"))
                    if b is not None:
                        v = b.get(qn("w:val"), "true")
                        is_bold = v not in ("false", "0", "off", "none")
                    i = rPr.find(qn("w:i"))
                    if i is not None:
                        v = i.get(qn("w:val"), "true")
                        is_italic = v not in ("false", "0", "off", "none")
                    u = rPr.find(qn("w:u"))
                    if u is not None:
                        v = u.get(qn("w:val"), "single")
                        is_underline = v not in ("false", "0", "off", "none", "nil")
                    sz = rPr.find(qn("w:sz"))
                    if sz is not None:
                        try:
                            font_size_pt = float(sz.get(qn("w:val"), "0")) / 2
                        except (ValueError, TypeError):
                            pass
                    rFonts = rPr.find(qn("w:rFonts"))
                    if rFonts is not None:
                        font_name = rFonts.get(qn("w:ascii")) or rFonts.get(qn("w:eastAsia")) or rFonts.get(qn("w:hAnsi"))
                    color = rPr.find(qn("w:color"))
                    if color is not None:
                        font_color = color.get(qn("w:val"))

                tags_list, stys = [], []
                if is_bold: tags_list.append("b")
                if is_italic: tags_list.append("i")
                if is_underline: tags_list.append("u")
                if font_size_pt: stys.append(f"font-size:{font_size_pt}pt")
                if font_name: stys.append(f"font-family:'{font_name}'")
                if font_color: stys.append(f"color:#{font_color}")
                if stys: tags_list.append(f'span style="{";".join(stys)}"')
                for t in tags_list: parts.append(f"<{t}>")
                parts.append(run_text)
                for t in reversed(tags_list): parts.append(f"</{t.split()[0]}>")

            elif tag == "oMath":
                # 行内公式
                parts.append('<span class="math-inline">')
                try:
                    if xslt_transform is not None:
                        mathml = str(xslt_transform(child))
                        if mathml.strip():
                            # 确保行内显示
                            mathml = mathml.replace("<math", '<math display="inline"', 1)
                            parts.append(mathml)
                        else:
                            parts.append('<span style="color:#999">[公式]</span>')
                    else:
                        parts.append('<span style="color:#999">[公式]</span>')
                except Exception:
                    parts.append('<span style="color:#999">[公式]</span>')
                parts.append('</span>')

            elif tag == "oMathPara":
                # 块级公式
                parts.append('<div class="math-block">')
                try:
                    if xslt_transform is not None:
                        mathml = str(xslt_transform(child))
                        if mathml.strip():
                            mathml = mathml.replace("<math", '<math display="block"', 1)
                            parts.append(mathml)
                        else:
                            parts.append('<span style="color:#999">[公式]</span>')
                    else:
                        parts.append('<span style="color:#999">[公式]</span>')
                except Exception:
                    parts.append('<span style="color:#999">[公式]</span>')
                parts.append('</div>')

        # ── 段落容器闭标签 ──
        if is_heading:
            parts.append(f'</h{hn}>')
        elif is_list_item:
            parts.append('</li>')
        else:
            parts.append('</p>')

        if is_list_item and not is_heading:
            parts.append(f'</{list_tag}>')

    # ── 表格渲染（含合并单元格） ──
    for table in doc.tables:
        parts.append('<table>')
        for row in table.rows:
            parts.append('<tr>')
            for cell in row.cells:
                # 合并单元格检测
                tc = cell._tc
                gridspan = tc.find(qn("w:tcPr"))
                colspan = 1
                rowspan = 1
                if gridspan is not None:
                    gm = gridspan.find(qn("w:gridSpan"))
                    if gm is not None:
                        colspan = int(gm.get(qn("w:val"), "1"))
                    vm = gridspan.find(qn("w:vMerge"))
                    if vm is not None:
                        val = vm.get(qn("w:val"), "continue")
                        if val == "restart":
                            rowspan = 2  # 保守处理
                        elif val == "continue":
                            continue  # 被合并的单元格跳过

                attrs = []
                if colspan > 1: attrs.append(f'colspan="{colspan}"')
                if rowspan > 1: attrs.append(f'rowspan="{rowspan}"')
                parts.append(f'<td {" ".join(attrs)}>')
                for cp in cell.paragraphs:
                    if cp.text.strip():
                        parts.append('<p>')
                        for r in cp.runs:
                            t = r.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            if r.bold: parts.append(f"<b>{t}</b>")
                            elif r.italic: parts.append(f"<i>{t}</i>")
                            else: parts.append(t)
                        parts.append('</p>')
                parts.append('</td>')
            parts.append('</tr>')
        parts.append('</table>')

    if footer_html:
        parts.append(f'<div class="docx-footer">{footer_html}</div>')

    parts.append('</div></body></html>')
    return "".join(parts)


def _convert_xlsx_to_html(input_path: str) -> str:
    """将 XLSX/XLS 转换为 HTML 表格（限制行数防 OOM）。"""
    import openpyxl
    MAX_ROWS = 5000  # 单表最大行数，超出截断
    wb = openpyxl.load_workbook(input_path, data_only=True)
    parts = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<title>表格预览</title>',
        '<style>',
        'body{font-family:"Microsoft YaHei","SimSun",sans-serif;padding:20px;}',
        'h2{color:#333;}',
        'table{border-collapse:collapse;width:100%;margin-bottom:20px;}',
        'td,th{border:1px solid #ccc;padding:4px 8px;font-size:11pt;}',
        'tr:nth-child(even){background:#f9f9f9;}',
        '@media print{body{padding:0;}@page{size:A4 landscape;margin:10mm;}}',
        '</style></head><body>',
    ]
    for name in wb.sheetnames:
        ws = wb[name]
        parts.append(f'<h2>{name}</h2><table>')
        row_count = 0
        for row in ws.iter_rows(values_only=True):
            if row_count >= MAX_ROWS:
                parts.append(f'<tr><td colspan="20" style="color:#c00">[已截断，仅展示前 {MAX_ROWS} 行]</td></tr>')
                break
            parts.append('<tr>')
            for cell in row:
                val = str(cell) if cell is not None else ""
                val = val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                parts.append(f'<td>{val}</td>')
            parts.append('</tr>')
            row_count += 1
        parts.append('</table>')
    parts.append('</body></html>')
    return "".join(parts)


# ── DOCX → images → HTML（持久化 + 并行 + JPEG，浏览器通用）──────────

def _build_images_html(file_id: str, image_paths: List[str], total: int) -> str:
    """将磁盘图片列表构建为内嵌 HTML（按页展示）。"""
    import base64 as b64

    img_tags = []
    for idx, ip in enumerate(image_paths):
        try:
            with open(ip, "rb") as fh:
                data = b64.b64encode(fh.read()).decode()
            src = f"data:image/jpeg;base64,{data}"
        except OSError:
            src = ""
        img_tags.append(
            f'<div class="page" style="margin-bottom:16px;text-align:center">'
            f'<img src="{src}" style="max-width:100%;height:auto;'
            f'box-shadow:0 2px 12px rgba(0,0,0,.08)" alt="第{idx+1}页" loading="lazy" />'
            f'<div style="color:#999;font-size:11px;padding:4px">'
            f'第 {idx+1} / {total} 页</div></div>'
        )

    css = (
        "body{margin:0;padding:24px;background:#e8e8e8;"
        "font-family:\"Microsoft YaHei\",\"SimSun\",sans-serif}"
        ".wrap{max-width:900px;margin:0 auto}"
        "h2{text-align:center;color:#333;margin:0 0 16px}"
        "@media print{body{background:#fff;padding:0}"
        " .page{box-shadow:none!important;page-break-after:always}"
        " .page img{box-shadow:none!important}}"
        "@media(max-width:640px){body{padding:8px}}"
    )
    return (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>文档预览</title><style>{css}</style></head>'
        f'<body><div class="wrap"><h2>文档预览</h2>{"".join(img_tags)}</div></body></html>'
    )


def _ensure_pdf(file_id: str, source_path: str, source_hash: str) -> Optional[str]:
    """
    确保 document_store 中存在 PDF 版本。
    缓存命中直接返回，否则通过 MS Word COM 转换并持久化。
    """
    from app.services.document_store import get_cached_pdf, store_pdf

    cached = get_cached_pdf(file_id, source_hash)
    if cached:
        return cached

    pdf_path = _convert_via_docx2pdf(source_path)
    if pdf_path is None:
        return None

    try:
        stored = store_pdf(file_id, pdf_path, source_hash)
        return stored
    finally:
        # 清理临时 PDF（docx2pdf 输出在 tempdir 下）
        parent = os.path.dirname(pdf_path)
        if pdf_path.startswith(tempfile.gettempdir()):
            try:
                shutil.rmtree(parent, ignore_errors=True)
            except Exception:
                pass


def _ensure_images(file_id: str, pdf_path: str, page_count: int, pdf_hash: str) -> List[str]:
    """
    确保 document_store 中存在页面图片。
    缓存命中直接返回，否则并行生成 JPEG 并持久化。
    """
    from app.services.document_store import get_cached_images, generate_images

    cached = get_cached_images(file_id, pdf_hash, page_count)
    if cached:
        return cached

    return generate_images(file_id, pdf_path, page_count, pdf_hash,
                           dpi=150, quality=85, max_workers=4)


def convert_to_images_html(file_id: str, input_path: str, file_type: str) -> Optional[str]:
    """
    DOCX/PDF → 持久化图片 → HTML 页面。

    PDF 文件跳过 Word→PDF 步骤，直接从 PDF 生成图片。
    所有中间产物（PDF、图片）持久化到 document_store，
    下次预览同一文件秒开。

    返回 HTML 字符串，失败返回 None。
    """
    import fitz

    file_type = file_type.lower().lstrip(".")
    if file_type not in ("docx", "doc", "pdf"):
        return None  # 调用方自行处理不支持类型

    from app.services.document_store import store_original, doc_root
    from app.exceptions import ConversionError
    import base64 as b64

    # 检测引擎可用性
    if file_type in ("docx", "doc") and _detect_engine() == "fallback":
        raise ConversionError(
            "文档预览不可用：系统未安装 Microsoft Word 或 LibreOffice，无法将 Word 转为 PDF",
            reason="no_word_engine",
        )

    # 绑定上下文日志
    log = get_logger(f"services.conversion.{file_id[:8]}")
    t_start = time.time()
    log.info(f"convert_to_images_html 开始 | type={file_type}")

    # 1. 原始文件持久化 + 哈希
    store_original(file_id, input_path)
    source_hash = _source_hash(input_path)
    log.info(f"原始文件哈希: {source_hash[:16]}")

    # 2. PDF 版本
    if file_type == "pdf":
        from app.services.document_store import _ensure_dirs, dir_pdf, _write_meta
        _ensure_dirs(file_id)
        pdf_dest = os.path.join(dir_pdf(file_id), "document.pdf")
        if os.path.abspath(input_path) != os.path.abspath(pdf_dest):
            shutil.copy2(input_path, pdf_dest)
        pdf_path = pdf_dest
        meta = _read_meta_internal(file_id)
        meta["pdf_source_hash"] = source_hash
        _write_meta_internal(file_id, meta)
        log.info(f"PDF 即原始文件，已复制到 pdf/")
    else:
        t_pdf = time.time()
        pdf_path = _ensure_pdf(file_id, input_path, source_hash)
        if pdf_path is None:
            log.error("Word→PDF 转换失败")
            return None
        log.info(f"Word→PDF 完成 | {time.time()-t_pdf:.1f}s")

    pdf_hash = _source_hash(pdf_path)

    # 3. 页码
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    log.info(f"PDF 页数: {page_count}")

    # 4. 图片生成（持久化 + 缓存）
    t_img = time.time()
    image_paths = _ensure_images(file_id, pdf_path, page_count, pdf_hash)
    log.info(f"图片生成完成 | {time.time()-t_img:.1f}s | {page_count} 页")

    # 5. 构建 HTML
    html = _build_images_html(file_id, image_paths, page_count)

    elapsed = time.time() - t_start
    total_kb = sum(os.path.getsize(p) for p in image_paths if os.path.exists(p)) // 1024
    log.info(f"convert_to_images_html 完成 | {page_count}页 {total_kb}KB {elapsed:.1f}s")

    return html


# 内联辅助（避免循环导入）
def _read_meta_internal(file_id: str) -> dict:
    import json
    from app.services.document_store import meta_path
    mp = meta_path(file_id)
    if os.path.exists(mp):
        try:
            with open(mp, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_meta_internal(file_id: str, data: dict) -> None:
    import json
    from app.services.document_store import meta_path, _ensure_dirs
    _ensure_dirs(file_id)
    with open(meta_path(file_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── 工具函数 ────────────────────────────────────────────────────

def schedule_cleanup(background_tasks, file_path: str) -> None:
    """在响应发送后清理临时文件（及其父目录，如果为空）。"""
    def _cleanup():
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
            parent = os.path.dirname(file_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass
    background_tasks.add_task(_cleanup)


# ── 对外 API ────────────────────────────────────────────────────

def convert_to_pdf(input_path: str, file_type: str, filename: str) -> Tuple[str, str, str, bool]:
    """
    将文件转换为 PDF，优先使用原生引擎，结果缓存 30 天。

    转换优先级：
    1. 已有 PDF → 直接返回原文件
    2. docx2pdf (MS Word COM) → 像素级完美 PDF
    3. LibreOffice headless → 原生 PDF
    4. python-docx → 增强 HTML（浏览器打印为 PDF）

    Args:
        input_path: 源文件磁盘路径
        file_type: 文件类型 (pdf/docx/doc/xlsx/xls)
        filename: 原始文件名

    Returns:
        (output_path, media_type, actual_format, needs_cleanup)
    """
    file_type = file_type.lower().lstrip(".")
    _ensure_cache_dir()
    src_hash = _source_hash(input_path)

    # 0. 文件大小保护：超过 50MB 拒绝转换，直接返回原文件
    try:
        fsize = os.path.getsize(input_path)
        if fsize > 50 * 1024 * 1024:
            logger.warning(f"文件过大 ({fsize / 1024 / 1024:.1f}MB)，跳过转换")
            return (input_path, "application/octet-stream", file_type, False)
    except OSError:
        pass

    # 1. 已是 PDF → 直接返回
    if file_type == "pdf":
        return (input_path, "application/pdf", "pdf", False)

    # 2. 检查缓存
    cached = _read_cache(src_hash, ".pdf")
    if cached:
        return (cached, "application/pdf", "pdf", False)  # cached, no cleanup

    # 3. 原生引擎转换
    engine = _detect_engine()
    output_pdf = None

    if engine == "docx2pdf" and file_type in ("docx", "doc"):
        output_pdf = _convert_via_docx2pdf(input_path)

    if output_pdf is None and engine == "libreoffice":
        tmp_dir = tempfile.mkdtemp(prefix="conv_")
        try:
            output_pdf = _convert_via_libreoffice(input_path, tmp_dir, "pdf")
            if output_pdf is None:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            output_pdf = None

    # 4. 原生引擎成功 → 写入缓存
    if output_pdf and os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0:
        try:
            cached_path = _write_cache(src_hash, output_pdf, ".pdf", file_type)
            # 清理临时输出（如果是临时文件）
            if output_pdf != cached_path and output_pdf.startswith(tempfile.gettempdir()):
                try:
                    parent = os.path.dirname(output_pdf)
                    shutil.rmtree(parent, ignore_errors=True)
                except Exception:
                    pass
            return (cached_path, "application/pdf", "pdf", False)
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}，直接返回转换结果")
            return (output_pdf, "application/pdf", "pdf", True)

    # 5. 所有引擎失败 → HTML fallback
    tmp_path = None
    try:
        if file_type in ("docx", "doc"):
            html = _convert_docx_to_html(input_path)
        elif file_type in ("xlsx", "xls"):
            html = _convert_xlsx_to_html(input_path)
        else:
            return (input_path, "application/octet-stream", file_type, False)

        fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="conv_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        return (tmp_path, "text/html; charset=utf-8", "html", True)
    except Exception as e:
        logger.error(f"HTML 转换失败: {e}")
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return (input_path, "application/octet-stream", file_type, False)


def _convert_via_docx2pdf(input_path: str) -> Optional[str]:
    """使用 MS Word COM（win32com）转换 DOCX → PDF。"""
    try:
        import pythoncom
        import win32com.client

        abs_input = os.path.abspath(input_path)
        output_dir = tempfile.mkdtemp(prefix="docx2pdf_")
        base = os.path.splitext(os.path.basename(abs_input))[0]
        pdf_path = os.path.join(output_dir, f"{base}.pdf")
        abs_pdf = os.path.abspath(pdf_path)

        pythoncom.CoInitialize()
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            doc = None
            try:
                doc = word.Documents.Open(abs_input, ReadOnly=True)
                doc.ExportAsFixedFormat(abs_pdf, 17, OptimizeFor=1)
                doc.Close(SaveChanges=0)
            finally:
                if doc is not None:
                    try:
                        doc.Close(SaveChanges=0)
                    except Exception:
                        pass
                word.Quit()
        finally:
            pythoncom.CoUninitialize()

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            logger.info(f"MS Word COM PDF 转换成功: {pdf_path}")
            return pdf_path
        else:
            logger.error("MS Word COM 未生成 PDF 文件")
            shutil.rmtree(output_dir, ignore_errors=True)
            return None
    except ImportError:
        logger.debug("win32com 不可用，跳过 MS Word 转换")
        return None
    except Exception as e:
        logger.warning(f"MS Word COM 转换失败: {e}")
        return None


def convert_to_html(input_path: str, file_type: str = "docx") -> Tuple[str, str, bool]:
    """
    将 DOCX 转换为 HTML 用于预览。
    使用 python-docx 增强渲染（图片 base64 内嵌，无需外部文件）。
    
    Returns:
        (html_string, media_type, needs_cleanup)
    """
    file_type = file_type.lower().lstrip(".")
    if file_type in ("docx", "doc"):
        html = _convert_docx_to_html(input_path)
    elif file_type in ("xlsx", "xls"):
        html = _convert_xlsx_to_html(input_path)
    else:
        html = "<p>不支持此文件类型的预览</p>"
    return (html, "text/html; charset=utf-8", False)


def _wrap_word_html(html_path: str, output_dir: str, title: str) -> str:
    """读取 Word 导出的 HTML，嵌入图片为 base64，包裹为带样式控制的预览页面。"""
    import re
    import base64 as b64

    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # ── 将外部图片引用转为 base64 data URI ──
    def _replace_img_src(match):
        src = match.group(1)
        # 跳过已经是 data: 或 http: 的
        if src.startswith("data:") or src.startswith("http"):
            return match.group(0)
        # 尝试在 output_dir 下找到图片文件
        # Word 导出图片通常在 {basename}.files/ 子目录
        img_path = os.path.join(output_dir, src)
        if not os.path.exists(img_path):
            # 也尝试直接在 output_dir 下查找
            alt_path = os.path.join(output_dir, os.path.basename(src))
            if os.path.exists(alt_path):
                img_path = alt_path
            else:
                return match.group(0)  # 找不到，保留原样
        try:
            with open(img_path, "rb") as img_f:
                img_bytes = img_f.read()
            ext = os.path.splitext(img_path)[1].lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".gif": "image/gif", ".bmp": "image/bmp", ".svg": "image/svg+xml",
                        ".webp": "image/webp", ".wmf": "image/wmf", ".emf": "image/emf"}
            mime = mime_map.get(ext, "image/png")
            data_uri = f"data:{mime};base64,{b64.b64encode(img_bytes).decode()}"
            return match.group(0).replace(src, data_uri)
        except Exception:
            return match.group(0)

    raw = re.sub(r'src="([^"]*)"', _replace_img_src, raw)

    # 提取 <body> 内容
    body_match = re.search(r"<body[^>]*>(.*?)</body>", raw, re.DOTALL | re.IGNORECASE)
    body = body_match.group(1) if body_match else raw

    # 提取 <style> 标签（Word 的内联样式）
    style_match = re.search(r"<style[^>]*>(.*?)</style>", raw, re.DOTALL | re.IGNORECASE)
    word_styles = style_match.group(1) if style_match else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
/* 页面容器 — 模拟 A4 纸 */
body {{
    margin: 0;
    padding: 20px;
    background: #e8e8e8;
    font-family: "Times New Roman", "SimSun", "Microsoft YaHei", serif;
}}
.docx-page {{
    max-width: 210mm;
    margin: 0 auto;
    padding: 20mm 25mm;
    background: #fff;
    box-shadow: 0 2px 20px rgba(0,0,0,.12);
    min-height: 297mm;
    line-height: 1.6;
    font-size: 12pt;
    color: #111;
}}
.docx-page p {{ margin: 0 0 6pt 0; }}
.docx-page h1 {{ font-size: 22pt; margin: 16pt 0 8pt; }}
.docx-page h2 {{ font-size: 16pt; margin: 14pt 0 6pt; }}
.docx-page h3 {{ font-size: 14pt; margin: 12pt 0 4pt; }}
.docx-page table {{ border-collapse: collapse; width: 100%; margin: 8pt 0; }}
.docx-page td, .docx-page th {{ border: 1px solid #ccc; padding: 4pt 8pt; }}
.docx-page img {{ max-width: 100%; height: auto; }}

/* Word 原始样式 */
{word_styles}

/* 打印优化 */
@media print {{
    body {{ background: #fff; padding: 0; }}
    .docx-page {{ box-shadow: none; max-width: none; margin: 0; padding: 0; }}
    @page {{ size: A4; margin: 20mm; }}
}}
@media (max-width: 800px) {{
    .docx-page {{ padding: 12px; max-width: 100%; }}
}}
</style>
</head>
<body>
<div class="docx-page">
{body}
</div>
</body>
</html>"""


def convert_to_word(input_path: str, file_type: str, filename: str) -> Tuple[str, str, str, bool]:
    """
    获取文件的 Word 格式版本。
    如果已是 DOCX/DOC → 直接返回；PDF → 暂不支持反向转换。
    """
    file_type = file_type.lower().lstrip(".")
    if file_type in ("docx", "doc"):
        return (input_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", file_type, False)
    return (input_path, "application/octet-stream", file_type, False)
