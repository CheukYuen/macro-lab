#!/usr/bin/env python3
"""Build the October China macro report from reviewed UTF-8 JSON content.

Usage: uv run --python <bundled-python> --no-project python build_report.py
       report_content.json ../../reports/<name>-wind.docx [--render-dir out/render]

Renderer paths come from MACROLAB_DOCX_RUNTIME / MACROLAB_DOCX_RENDERER.

The optional render step always calls the packaged renderer and bundled
LibreOffice. It never falls back to a desktop LibreOffice installation.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor


# Codex documents 运行环境的位置因机器而异，从环境变量读取。
RUNTIME = Path(os.environ.get('MACROLAB_DOCX_RUNTIME', '~/.cache/codex-runtimes/codex-primary-runtime/dependencies')).expanduser()
RENDERER = Path(os.environ.get('MACROLAB_DOCX_RENDERER', '~/.codex/plugins/cache/openai-primary-runtime/documents/26.1013.11914/skills/documents/render_docx.py')).expanduser()
SOFFICE = RUNTIME / 'bin/override/soffice'
SYSTEM_FONT_DIRS = [
    '/System/Library/Fonts/Supplemental',
    '/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData',
]
BODY_FONT = 'Songti SC'
HEADING_FONT = 'PingFang SC'
NAVY = '163652'
PALE = 'F2F6FA'
GRAY = 'D9D9D9'
TEXT = '111111'


def set_font(run, size=11, bold=False, color=TEXT, heading=False):
    name = HEADING_FONT if heading else BODY_FONT
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    for key in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn(f'w:{key}'), name)
    lang = rpr.find(qn('w:lang'))
    if lang is None:
        lang = OxmlElement('w:lang')
        rpr.append(lang)
    lang.set(qn('w:eastAsia'), 'zh-CN')


def hyperlink(paragraph, label, url, size=11, bold=False):
    rel = paragraph.part.relate_to(
        url,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
        is_external=True,
    )
    link = OxmlElement('w:hyperlink')
    link.set(qn('r:id'), rel)
    run = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    fonts = OxmlElement('w:rFonts')
    for key in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
        fonts.set(qn(f'w:{key}'), BODY_FONT)
    rpr.append(fonts)
    for tag, value in [('color', NAVY), ('sz', str(round(size * 2)))]:
        node = OxmlElement(f'w:{tag}')
        node.set(qn('w:val'), value)
        rpr.append(node)
    if bold:
        rpr.append(OxmlElement('w:b'))
    run.append(rpr)
    txt = OxmlElement('w:t')
    txt.text = label
    run.append(txt)
    link.append(run)
    paragraph._p.append(link)


def rich(paragraph, text, size=11, bold=False, color=TEXT, heading=False):
    """Preserve simple markdown emphasis and links without exposing markup."""
    for token in re.split(r'(\*\*.*?\*\*|\[[^\]]+\]\(https?://[^\s)]+\))', str(text)):
        if not token:
            continue
        match = re.fullmatch(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', token)
        if match:
            hyperlink(paragraph, match[1], match[2], size, bold)
        else:
            is_bold = token.startswith('**') and token.endswith('**')
            run = paragraph.add_run(token[2:-2] if is_bold else token)
            set_font(run, size, bold or is_bold, color, heading)


def source_note(source):
    note = source.get('note', '')
    formal_notes = {
        'S1': '制造业PMI正文及分类指数表；分类指数按国家统计局公开索引核对',
        'S4': '海关10月14日发布会官方转载；采用累计人民币口径结构',
        'S11': '全球增长与通胀预测采用官方发布摘要；完整国别预测表不在本报告引用范围',
    }
    if source.get('id') in formal_notes:
        note = formal_notes[source['id']]
    # Compact link labels prevent long official URLs from widening a source line.
    return re.sub(r'https?://[^\s；。]+', lambda match: f'[相关原文]({match[0]})', note)


def clean_heading(text):
    # The document skill requires descriptive headings without punctuation.
    return re.sub(r'\s+', ' ', re.sub(r'[，。；：、,.;:!?！？《》“”"()（）—–/\\\[\]【】]', ' ', text)).strip()


def paragraph_format(paragraph, after=5, before=0, line=1.22):
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    fmt.widow_control = True


def add_body(doc, text, size=11, style=None):
    paragraph = doc.add_paragraph(style=style)
    paragraph_format(paragraph)
    rich(paragraph, text, size=size)
    return paragraph


def add_heading(doc, text, level=1):
    paragraph = doc.add_paragraph(style=f'Heading {min(level, 3)}')
    paragraph_format(paragraph, before=13 if level == 1 else 8, after=6, line=1.15)
    paragraph.paragraph_format.keep_with_next = True
    rich(paragraph, clean_heading(text), size={1: 15, 2: 12.5, 3: 11.5}[min(level, 3)],
         bold=True, color='000000', heading=True)
    return paragraph


def cell_shade(cell, color):
    tcpr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    tcpr.append(shading)


def table_widths(headers, rows, given):
    if given and len(given) == len(headers):
        return [value / sum(given) for value in given]
    weights = []
    for index, header in enumerate(headers):
        longest = max([len(str(header))] + [len(str(row[index])) for row in rows])
        weights.append(math.sqrt(min(75, max(longest, 6))))
    return [value / sum(weights) for value in weights]


def add_table(doc, spec):
    headers = spec['headers']
    rows = spec['rows']
    if not headers or any(len(row) != len(headers) for row in rows):
        raise ValueError('Each table row must match the header count')
    if spec.get('caption'):
        caption = doc.add_paragraph()
        paragraph_format(caption, before=6, after=5)
        caption.paragraph_format.keep_with_next = True
        rich(caption, spec['caption'], size=10.5, bold=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tblpr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        elem = OxmlElement(f'w:{edge}')
        for key, value in [('val', 'single'), ('sz', '4'), ('color', GRAY)]:
            elem.set(qn(f'w:{key}'), value)
        borders.append(elem)
    tblpr.append(borders)
    compact_numeric = str(spec.get('caption', '')).startswith('表3')
    vertical_padding = '55' if compact_numeric else '82'
    margins = OxmlElement('w:tblCellMar')
    for side, value in [('top', vertical_padding), ('bottom', vertical_padding), ('left', '95'), ('right', '95')]:
        elem = OxmlElement(f'w:{side}')
        elem.set(qn('w:w'), value)
        elem.set(qn('w:type'), 'dxa')
        margins.append(elem)
    tblpr.append(margins)
    fractions = table_widths(headers, rows, spec.get('widths'))
    available_mm = 168
    for col, fraction in zip(table.columns, fractions):
        col.width = Mm(available_mm * fraction)
    for body_row in rows:
        table.add_row()
    for row_index, values in enumerate([headers, *rows]):
        row = table.rows[row_index]
        rowpr = row._tr.get_or_add_trPr()
        rowpr.append(OxmlElement('w:cantSplit'))
        if row_index == 0:
            rowpr.append(OxmlElement('w:tblHeader'))
        for col_index, value in enumerate(values):
            cell = row.cells[col_index]
            cell.width = Mm(available_mm * fractions[col_index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell_shade(cell, NAVY if row_index == 0 else (PALE if row_index % 2 == 0 else 'FFFFFF'))
            paragraph = cell.paragraphs[0]
            paragraph_format(paragraph, after=0, line=1.12 if compact_numeric else 1.14)
            if row_index == 0:
                paragraph.paragraph_format.keep_with_next = True
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            elif len(str(value)) <= 14 and len(headers) >= 3:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            rich(paragraph, str(value), size=10 if len(headers) <= 4 else 9.5,
                 bold=row_index == 0, color='FFFFFF' if row_index == 0 else TEXT)
    if spec.get('note'):
        note = doc.add_paragraph()
        paragraph_format(note, before=4, after=7, line=1.15)
        rich(note, spec['note'], size=9.5, color='444444')
    else:
        spacer = doc.add_paragraph()
        paragraph_format(spacer, after=2, line=0.5)
        set_font(spacer.add_run(''), size=3)


def add_section(doc, spec, level=1):
    add_heading(doc, spec['heading'], level)
    for text in spec.get('paragraphs', []):
        add_body(doc, text)
    for text in spec.get('bullets', []):
        add_body(doc, text, style='List Bullet')
    for table in spec.get('tables', []):
        add_table(doc, table)
    for subsection in spec.get('subsections', []):
        add_section(doc, subsection, min(level + 1, 3))


def build(data, output):
    if not data.get('title') or not data.get('sections'):
        raise ValueError('Reviewed title and nonempty sections are required')
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin, section.bottom_margin = Mm(20), Mm(18)
    section.left_margin = section.right_margin = Mm(21)
    section.footer_distance = Mm(8)
    for style_name in ('Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3', 'List Bullet'):
        style = doc.styles[style_name]
        style.font.name = BODY_FONT
        style.font.size = Pt(11)
        style.font.color.rgb = RGBColor.from_string('000000')
        fonts = style.element.get_or_add_rPr().rFonts
        if fonts is not None:
            for key in ('ascii', 'hAnsi', 'eastAsia', 'cs'):
                fonts.set(qn(f'w:{key}'), BODY_FONT)
        # Eliminate theme colors and latent paragraph borders.
        for color in style.element.findall('.//' + qn('w:color')):
            for attribute in ('themeColor', 'themeTint', 'themeShade'):
                color.attrib.pop(qn(f'w:{attribute}'), None)
        for border in style.element.findall('.//' + qn('w:pBdr')):
            border.getparent().remove(border)
    doc.core_properties.author = 'macro-lab'
    doc.core_properties.title = data['title']
    doc.core_properties.subject = '中国市场与外部宏观环境'
    doc.core_properties.language = 'zh-CN'
    title = doc.add_paragraph(style='Title')
    paragraph_format(title, after=9, line=1.12)
    title.paragraph_format.keep_with_next = True
    rich(title, clean_heading(data['title']), size=22, bold=True, color='000000', heading=True)
    if data.get('subtitle'):
        sub = doc.add_paragraph(style='Subtitle')
        paragraph_format(sub, after=10, line=1.15)
        sub.paragraph_format.keep_with_next = True
        rich(sub, data['subtitle'], size=10, color='000000')
    for text in data.get('intro', []):
        add_body(doc, text)
    for spec in data['sections']:
        add_section(doc, spec)
    if data.get('sources'):
        add_heading(doc, data.get('sources_heading', '资料来源与核验口径'))
        for index, source in enumerate(data['sources'], 1):
            paragraph = doc.add_paragraph()
            paragraph_format(paragraph, after=2, line=1.12)
            label = source.get('id', str(index))
            rich(paragraph, f'[{label}] ', size=9.5)
            if source.get('url'):
                hyperlink(paragraph, source['title'], source['url'], size=9.5)
            else:
                rich(paragraph, source['title'], size=9.5)
            details = [str(source[key]) for key in ('publisher', 'date') if source.get(key)]
            if source.get('note'):
                details.append(source_note(source))
            if details:
                rich(paragraph, '。' + '；'.join(details) + '。', size=9.5, color='444444')
    if data.get('closing_note'):
        add_body(doc, data['closing_note'], size=9.5)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph_format(footer, after=0)
    set_font(footer.add_run('macro-lab  |  '), size=8.5, color='555555')
    run = footer.add_run()
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    run._r.addnext(field)
    update = OxmlElement('w:updateFields')
    update.set(qn('w:val'), 'true')
    doc.settings.element.append(update)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('content', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--render-dir', type=Path)
    args = parser.parse_args()
    data = json.loads(args.content.read_text(encoding='utf-8'))
    output = build(data, args.output.resolve())
    print(output)
    if args.render_dir:
        if not SOFFICE.is_file():
            raise FileNotFoundError(f'Missing bundled LibreOffice: {SOFFICE}')
        render_dir = args.render_dir.resolve()
        render_dir.mkdir(parents=True, exist_ok=True)
        lo_fonts = RUNTIME / 'native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype'
        dirs = ''.join(f'  <dir>{d}</dir>\n' for d in [*SYSTEM_FONT_DIRS, lo_fonts])
        fontconfig = render_dir.parent / 'fontconfig.xml'
        fontconfig.write_text(
            '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            f'<fontconfig>\n{dirs}  <cachedir>{render_dir.parent / "font-cache"}</cachedir>\n</fontconfig>\n',
            encoding='utf-8')
        render_env = os.environ.copy()
        render_env['FONTCONFIG_FILE'] = str(fontconfig)
        render_env['SAL_FONTPATH'] = ':'.join(SYSTEM_FONT_DIRS)
        subprocess.run([sys.executable, str(RENDERER), str(output),
                        '--output_dir', str(render_dir), '--emit_pdf'],
                       check=True, env=render_env)


if __name__ == '__main__':
    main()
