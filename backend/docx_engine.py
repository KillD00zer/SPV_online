# -*- coding: utf-8 -*-
"""
Official Cadastral Survey Certificate DOCX Generator (Cloud & Modal Ready)
==========================================================================
Generates official survey certificates using the official template:
- Side-by-side tables for boundary dimensions and parcel coordinates.
- High precision (8 decimals for coordinates).
- In-memory and file-based support for serverless execution.
"""

import os
import io
import sys
import glob
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

def get_template_path():
    """Locates the official adjusted template docx across various deployment targets."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(app_dir, "template.docx"),
        "/root/template.docx",
        os.path.join(app_dir, "قالب_شهادة_الرفع_المساحي_الرسمية.docx"),
        "/root/قالب_شهادة_الرفع_المساحي_الرسمية.docx",
        os.path.join(os.getcwd(), "template.docx"),
        os.path.join(os.getcwd(), "قالب_شهادة_الرفع_المساحي_الرسمية.docx"),
        os.path.join(app_dir, "..", "backend", "template.docx"),
        r"d:\Work\GIS_tools\project_SPV\قالب_شهادة_الرفع_المساحي_الرسمية.docx"
    ]
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', app_dir)
        candidates.insert(0, os.path.join(meipass, "قالب_شهادة_الرفع_المساحي_الرسمية.docx"))
    
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
            
    matches = glob.glob(os.path.join(app_dir, "*.docx"))
    if matches:
        return os.path.abspath(matches[0])
        
    raise FileNotFoundError("Could not find قالب_شهادة_الرفع_المساحي_الرسمية.docx")

def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    for edge in ('top', 'left', 'bottom', 'right'):
        edge_data = kwargs.get(edge, {'val': 'single', 'sz': '8', 'color': '4F81BD'})
        val = edge_data.get('val', 'single')
        sz = edge_data.get('sz', '8')
        color = edge_data.get('color', '4F81BD')
        b_el = parse_xml(f'<w:{edge} {nsdecls("w")} w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>')
        tcBorders.append(b_el)
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    for s in tcPr.findall(qn('w:shd')):
        tcPr.remove(s)
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>'))

def set_cell_text(cell, text, bold=False, font_size=10.0, font_name="Arial", color=RGBColor(0,0,0), align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(str(text))
    r.font.name = font_name
    r.font.size = Pt(font_size)
    r.font.bold = bold
    r.font.color.rgb = color
    p._element.get_or_add_pPr().append(parse_xml(f'<w:bidi {nsdecls("w")}/>'))
    r._element.get_or_add_rPr().append(parse_xml(f'<w:rtl {nsdecls("w")}/>'))

def create_certificate_docx(land_data, areas_list, boundaries_dict, output_target=None,
                             survey_tech="محمد ابراهيم بدير", sys_officer="شريف محمد",
                             croquis_img=None, sat_img=None):
    """
    Fills the official survey certificate.
    output_target: file path (str) or None (returns io.BytesIO)
    croquis_img: file path (str) or bytes or io.BytesIO
    sat_img: file path (str) or bytes or io.BytesIO
    """
    template_file = get_template_path()
    doc = docx.Document(template_file)
    table = doc.tables[0]

    # --- 1. Populate Metadata (Rows 1..6) ---
    name = str(land_data.get('name', '')).strip()
    
    # Parcel ID
    parcel_ids = []
    if areas_list:
        for a in areas_list:
            pid = str(a.get('parcel_id', '')).strip()
            if pid and pid not in parcel_ids:
                parcel_ids.append(pid)
    parcel_str = ", ".join(parcel_ids) if parcel_ids else str(land_data.get('parcel_id', '')).strip()

    # Hod Name
    hod_names = []
    if areas_list:
        for a in areas_list:
            hname = str(a.get('hod_name', '')).strip()
            if hname and hname not in hod_names:
                hod_names.append(hname)
    hod_str = " - ".join(hod_names) if hod_names else str(land_data.get('hod_name', '')).strip()

    id_no = str(land_data.get('id_no', '')).strip()
    
    # Inherit date from Data_Int or other date variations
    raw_date = land_data.get('Data_Int', land_data.get('data_int', land_data.get('Data_int', land_data.get('Data_Inter', land_data.get('data inter', land_data.get('date', land_data.get('Date', land_data.get('تاريخ تقديم الطلب', ''))))))))
    req_date = str(raw_date).strip() if raw_date else ""
    
    center = str(land_data.get('Center', land_data.get('center', ''))).strip()
    village = str(land_data.get('Sheikhah', land_data.get('village', ''))).strip()
    
    # Map IDs
    map_ids = []
    if areas_list:
        for a in areas_list:
            mid = str(a.get('map_id', '')).strip()
            if mid and mid not in map_ids:
                map_ids.append(mid)
    map_id_str = ", ".join(map_ids) if map_ids else str(land_data.get('map_id', '')).strip()
    map_id2_str = str(land_data.get('map_id2', '')).strip()

    # Area
    area_val = land_data.get('area', '')
    unit_val = land_data.get('unit', 'م2')
    area_str = f"{area_val} {unit_val}".strip() if area_val else "-"

    # Address / Place / Activity
    address = str(land_data.get('place', land_data.get('address', ''))).strip()
    if not address and land_data.get('activity'):
        address = str(land_data.get('activity')).strip()

    # Apply Metadata to Template Cells
    set_cell_text(table.rows[1].cells[1], name, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.RIGHT)
    set_cell_text(table.rows[1].cells[6], parcel_str, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    set_cell_text(table.rows[2].cells[1], hod_str, bold=True, font_size=10.5, align=WD_ALIGN_PARAGRAPH.RIGHT)
    set_cell_text(table.rows[2].cells[6], id_no, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    set_cell_text(table.rows[3].cells[4], req_date, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    set_cell_text(table.rows[4].cells[1], center, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text(table.rows[4].cells[6], village, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    set_cell_text(table.rows[5].cells[1], map_id_str, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text(table.rows[5].cells[6], area_str, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    set_cell_text(table.rows[6].cells[1], map_id2_str, bold=True, font_size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell_text(table.rows[6].cells[6], address, bold=True, font_size=10, align=WD_ALIGN_PARAGRAPH.RIGHT)

    # --- 2. Populate Container Row (Row 8) Side-by-Side Tables ---
    container_row = table.rows[8]
    cell_bounds = container_row.cells[0]  # Right: gridSpan 5
    cell_coords = container_row.cells[5]  # Left: gridSpan 3

    # Clear existing tables inside cells
    for child in list(cell_bounds._element):
        if child.tag.endswith('tbl'):
            cell_bounds._element.remove(child)
    for child in list(cell_coords._element):
        if child.tag.endswith('tbl'):
            cell_coords._element.remove(child)

    # A. Right Table: الحدود والأبعاد على الطبيعة
    t_bounds = cell_bounds.add_table(rows=6, cols=4)
    t_bounds.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_bounds._tbl.tblPr.append(parse_xml(f'<w:bidiVisual {nsdecls("w")}/>'))
    t_bounds._tbl.tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="6597" w:type="dxa"/>'))

    headers_b = ["الجهة الجغرافية", "وصف الحد والجار", "بطول", "الطول (م)"]
    b_col_widths = [Inches(1.2), Inches(1.88), Inches(0.5), Inches(1.0)]

    for c_i, h_text in enumerate(headers_b):
        cell = t_bounds.rows[0].cells[c_i]
        set_cell_text(cell, h_text, bold=True, font_size=10, font_name="Arial", align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(cell, "D3DFEE")
        set_cell_border(cell)

    n_data = boundaries_dict.get('north', {})
    e_data = boundaries_dict.get('east', {})
    s_data = boundaries_dict.get('south', {})
    w_data = boundaries_dict.get('west', {})

    len_n = float(n_data.get('length', 0.0) or 0.0)
    len_e = float(e_data.get('length', 0.0) or 0.0)
    len_s = float(s_data.get('length', 0.0) or 0.0)
    len_w = float(w_data.get('length', 0.0) or 0.0)
    total_len = len_n + len_e + len_s + len_w

    desc_n = str(n_data.get('desc', '')).strip()
    desc_e = str(e_data.get('desc', '')).strip()
    desc_s = str(s_data.get('desc', '')).strip()
    desc_w = str(w_data.get('desc', '')).strip()

    bounds_data = [
        ("الحد البحري", desc_n, "بطول", f"{len_n:.2f} م"),
        ("الحد الشرقي", desc_e, "بطول", f"{len_e:.2f} م"),
        ("الحد القبلي", desc_s, "بطول", f"{len_s:.2f} م"),
        ("الحد الغربي", desc_w, "بطول", f"{len_w:.2f} م"),
        ("الإجمالي", "مجموع أطوال الأضلاع", "بطول", f"{total_len:.2f} م")
    ]

    for r_i, row_data in enumerate(bounds_data, start=1):
        row = t_bounds.rows[r_i]
        for c_i, val in enumerate(row_data):
            cell = row.cells[c_i]
            is_bold = (c_i == 0 or c_i == 3 or r_i == 5)
            shd = "F2F2F2" if c_i == 2 else ("E9EEF4" if r_i == 5 else "FFFFFF")
            set_cell_text(cell, val, bold=is_bold, font_size=9.5, font_name="Arial", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(cell, shd)
            set_cell_border(cell)

    for r in t_bounds.rows:
        for c_i, w in enumerate(b_col_widths):
            r.cells[c_i].width = w

    # B. Left Table: إحداثيات الموقع (WGS84)
    vertices = land_data.get('vertices', [])
    num_pts = len(vertices) if vertices else 4

    t_coords = cell_coords.add_table(rows=num_pts + 1, cols=3)
    t_coords.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_coords._tbl.tblPr.append(parse_xml(f'<w:bidiVisual {nsdecls("w")}/>'))
    t_coords._tbl.tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="4571" w:type="dxa"/>'))

    headers_c = ["م", "LONG (E)", "LAT (N)"]
    c_col_widths = [Inches(0.55), Inches(1.31), Inches(1.31)]

    for c_i, h_text in enumerate(headers_c):
        cell = t_coords.rows[0].cells[c_i]
        set_cell_text(cell, h_text, bold=True, font_size=10, font_name="Arial", align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell_shading(cell, "D3DFEE")
        set_cell_border(cell)

    if vertices:
        for idx, pt in enumerate(vertices, start=1):
            px = float(pt[0])
            py = float(pt[1])
            row = t_coords.rows[idx]
            
            set_cell_text(row.cells[0], str(idx), bold=True, font_size=9.5, font_name="Arial", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[0], "F2F2F2")
            set_cell_border(row.cells[0])
            
            set_cell_text(row.cells[1], f"{px:.8f}°", bold=False, font_size=9.0, font_name="Courier New", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[1], "FFFFFF")
            set_cell_border(row.cells[1])
            
            set_cell_text(row.cells[2], f"{py:.8f}°", bold=False, font_size=9.0, font_name="Courier New", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[2], "FFFFFF")
            set_cell_border(row.cells[2])
    else:
        for idx in range(1, 5):
            row = t_coords.rows[idx]
            set_cell_text(row.cells[0], str(idx), bold=True, font_size=9.5, font_name="Arial", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[0], "F2F2F2")
            set_cell_border(row.cells[0])
            set_cell_text(row.cells[1], "00.00000000°", bold=False, font_size=9.0, font_name="Courier New", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[1], "FFFFFF")
            set_cell_border(row.cells[1])
            set_cell_text(row.cells[2], "00.00000000°", bold=False, font_size=9.0, font_name="Courier New", align=WD_ALIGN_PARAGRAPH.CENTER)
            set_cell_shading(row.cells[2], "FFFFFF")
            set_cell_border(row.cells[2])

    for r in t_coords.rows:
        for c_i, w in enumerate(c_col_widths):
            r.cells[c_i].width = w

    # --- 3. Embed Images (Row 10) ---
    img_row = table.rows[10]

    # Helper to resolve image to stream or path
    def prepare_img_target(img):
        if not img:
            return None
        if isinstance(img, (bytes, bytearray)):
            return io.BytesIO(img)
        if isinstance(img, io.BytesIO):
            img.seek(0)
            return img
        if isinstance(img, str) and os.path.exists(img):
            return img
        return None

    croq_target = prepare_img_target(croquis_img)
    sat_target = prepare_img_target(sat_img)

    # Embed CAD Croquis in cell 0
    if croq_target:
        c_croq = img_row.cells[0]
        c_croq.text = ""
        p_c = c_croq.paragraphs[0]
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c.paragraph_format.space_before = Pt(2)
        p_c.paragraph_format.space_after = Pt(2)
        p_c.add_run().add_picture(croq_target, width=Inches(3.15))

    # Embed Satellite Image in cell 3
    if sat_target:
        c_sat = img_row.cells[3]
        c_sat.text = ""
        p_s = c_sat.paragraphs[0]
        p_s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_s.paragraph_format.space_before = Pt(2)
        p_s.paragraph_format.space_after = Pt(2)
        p_s.add_run().add_picture(sat_target, width=Inches(3.95))

    # --- 4. Populate Notes Row (Row 11) ---
    notes_val = str(land_data.get('notes', land_data.get('Notes', land_data.get('ملاحظات', land_data.get('note', land_data.get('Note', '')))))).strip()
    if len(table.rows) >= 12:
        c_notes = table.rows[11].cells[2]
        set_cell_text(c_notes, notes_val, bold=False, font_size=9.5, font_name="Arial", align=WD_ALIGN_PARAGRAPH.RIGHT)
    elif len(table.rows) == 11:
        new_tr = parse_xml(f'''
        <w:tr {nsdecls("w")}>
          <w:trPr><w:trHeight w:val="450"/></w:trPr>
          <w:tc>
            <w:tcPr>
              <w:tcW w:w="1600" w:type="dxa"/>
              <w:gridSpan w:val="2"/>
              <w:tcBorders>
                <w:top w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:left w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:bottom w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:right w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
              </w:tcBorders>
              <w:shd w:val="clear" w:color="auto" w:fill="D3DFEE"/>
            </w:tcPr>
            <w:p><w:pPr><w:jc w:val="center"/><w:bidi/></w:pPr><w:r><w:rPr><w:rFonts w:cs="Arial"/><w:b/><w:bCs/><w:sz w:val="20"/><w:rtl/></w:rPr><w:t>ملاحظات</w:t></w:r></w:p>
          </w:tc>
          <w:tc>
            <w:tcPr>
              <w:tcW w:w="9568" w:type="dxa"/>
              <w:gridSpan w:val="6"/>
              <w:tcBorders>
                <w:top w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:left w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:bottom w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
                <w:right w:val="single" w:sz="8" w:space="0" w:color="4F81BD"/>
              </w:tcBorders>
              <w:shd w:val="clear" w:color="auto" w:fill="FFFFFF"/>
            </w:tcPr>
            <w:p><w:pPr><w:jc w:val="right"/><w:bidi/></w:pPr><w:r><w:rPr><w:rFonts w:cs="Arial"/><w:sz w:val="19"/><w:rtl/></w:rPr><w:t></w:t></w:r></w:p>
          </w:tc>
        </w:tr>
        ''')
        table._tbl.append(new_tr)
        set_cell_text(table.rows[11].cells[2], notes_val, bold=False, font_size=9.5, font_name="Arial", align=WD_ALIGN_PARAGRAPH.RIGHT)

    if output_target:
        if isinstance(output_target, str):
            os.makedirs(os.path.dirname(os.path.abspath(output_target)), exist_ok=True)
            doc.save(output_target)
            return output_target
        elif hasattr(output_target, "write"):
            doc.save(output_target)
            return output_target
    else:
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio.getvalue()
