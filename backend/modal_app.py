# -*- coding: utf-8 -*-
"""
Cadastral Survey Certificate Suite - Modal Serverless Backend (FastAPI)
=======================================================================
Deployable to Modal (modal deploy modal_app.py) or runnable locally (uvicorn modal_app:web_app).
Provides REST APIs for:
  1. Parsing Land & Areas CSV data and geodesic calculations.
  2. Generating Google Satellite Map image preview.
  3. Generating CAD Croquis sketch preview.
  4. Generating full official package (DOCX + Images in ZIP or direct download).
"""

import os
import io
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import csv
import math
import json
import base64
import zipfile
from typing import Dict, Any, List, Optional
import urllib.parse

from pyproj import Geod
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Ensure local engines can be imported
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if "/root" not in sys.path:
    sys.path.insert(0, "/root")

from cad_engine import render_cad_croquis
from sat_engine import fetch_satellite_image
from docx_engine import create_certificate_docx

GEOD = Geod(ellps="WGS84")

# ---------------------------------------------------------------------------
# Modal Cloud App Definition
# ---------------------------------------------------------------------------
try:
    import modal
    modal_image = (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install("fonts-dejavu-core", "fontconfig")
        .pip_install(
            "fastapi>=0.100.0",
            "uvicorn>=0.23.0",
            "pyproj>=3.6.0",
            "python-docx>=1.1.0",
            "pillow>=10.0.0",
            "matplotlib>=3.7.0",
            "numpy>=1.24.0",
            "arabic-reshaper>=3.0.0",
            "python-bidi>=0.4.2"
        )
        .add_local_file(os.path.join(CURRENT_DIR, "cad_engine.py"), "/root/cad_engine.py")
        .add_local_file(os.path.join(CURRENT_DIR, "sat_engine.py"), "/root/sat_engine.py")
        .add_local_file(os.path.join(CURRENT_DIR, "docx_engine.py"), "/root/docx_engine.py")
        .add_local_file(os.path.join(CURRENT_DIR, "template.docx"), "/root/template.docx")
    )

    app = modal.App("spv-cert-suite", image=modal_image)
except Exception:
    app = None

# ---------------------------------------------------------------------------
# FastAPI Web Application
# ---------------------------------------------------------------------------
web_app = FastAPI(
    title="Cadastral Survey Certificate Suite API",
    version="2.0.0",
    description="Cloud backend for cadastral survey certificate suite"
)

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_filename(name):
    if name is None:
        return "Unknown"
    text = str(name).strip()
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text).strip()
    return cleaned if cleaned else "Unknown"

def calculate_geodesic_area(vertices_lon_lat):
    if len(vertices_lon_lat) < 3:
        return 0.0
    lons = [v[0] for v in vertices_lon_lat]
    lats = [v[1] for v in vertices_lon_lat]
    area, _ = GEOD.polygon_area_perimeter(lons, lats)
    return round(abs(area), 2)

def calculate_boundary_segments(vertices_lon_lat):
    n = len(vertices_lon_lat)
    if n < 3:
        return [], {'north': 0.0, 'east': 0.0, 'south': 0.0, 'west': 0.0, 'total': 0.0}

    area_2d = 0.0
    for i in range(n):
        x1, y1 = vertices_lon_lat[i]
        x2, y2 = vertices_lon_lat[(i + 1) % n]
        area_2d += (x1 * y2 - x2 * y1)
    is_ccw = area_2d > 0

    cardinal_name_ar = {
        'north': 'الحد البحري',
        'east': 'الحد الشرقي',
        'south': 'الحد القبلي',
        'west': 'الحد الغربي'
    }

    segments = []
    edge_totals = {'north': 0.0, 'east': 0.0, 'south': 0.0, 'west': 0.0, 'total': 0.0}

    for i in range(n):
        p1 = vertices_lon_lat[i]
        p2 = vertices_lon_lat[(i + 1) % n]
        fwd_az, _, dist = GEOD.inv(p1[0], p1[1], p2[0], p2[1])
        dist_m = round(dist, 2)
        if dist > 0 and dist_m == 0.0:
            dist_m = 0.01

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length > 0:
            if is_ccw:
                nx = dy / length
                ny = -dx / length
            else:
                nx = -dy / length
                ny = dx / length
            angle_deg = (math.degrees(math.atan2(ny, nx)) + 360) % 360
        else:
            angle_deg = 0.0

        if 45 <= angle_deg < 135:
            d = 'north'
        elif 315 <= angle_deg < 360 or 0 <= angle_deg < 45:
            d = 'east'
        elif 225 <= angle_deg < 315:
            d = 'south'
        else:
            d = 'west'

        segments.append({
            'index': i,
            'from_point': i + 1,
            'to_point': ((i + 1) % n) + 1,
            'length_m': dist_m,
            'direction': d,
            'direction_name': cardinal_name_ar.get(d, 'حد'),
            'azimuth_deg': round(fwd_az % 360, 1)
        })
        edge_totals[d] += dist_m
        edge_totals['total'] += dist_m

    for k in edge_totals:
        edge_totals[k] = round(edge_totals[k], 2)

    return segments, edge_totals

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@web_app.get("/")
@web_app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Cadastral Survey Certificate Suite API",
        "environment": "Modal / FastAPI",
        "wgs84_geod": True
    }

@web_app.post("/api/parse-csv")
def parse_csv_data(payload: Dict[str, Any] = Body(...)):
    """
    Parses Land CSV text & Areas CSV text provided as raw string or base64.
    Computes vertices, deduplication, geodesic area, and boundary segments.
    """
    land_content = payload.get("land_csv", "")
    areas_content = payload.get("areas_csv", "")

    if not land_content:
        raise HTTPException(status_code=400, detail="محتوى ملف Land CSV مطلوب.")

    # Parse Land CSV
    metadata = {}
    raw_vertices = []
    
    reader = csv.DictReader(io.StringIO(land_content))
    for row in reader:
        clean_row = {}
        for k, v in row.items():
            if not k:
                continue
            clean_k = k.strip().lstrip('\ufeff')
            clean_v = v.strip() if isinstance(v, str) else v
            clean_row[clean_k] = clean_v
            
        for k, v in clean_row.items():
            if k not in ["POINT_NUM", "POINT_X", "POINT_Y", "ORIG_FID", "Shape_Length", "Shape_Area"]:
                if v and (k not in metadata or not metadata[k]):
                    metadata[k] = v
                    
        try:
            px = float(clean_row.get("POINT_X", 0))
            py = float(clean_row.get("POINT_Y", 0))
            raw_vertices.append((px, py))
        except (ValueError, TypeError):
            continue

    # Standardize inherited fields
    date_val = metadata.get('Data_Int') or metadata.get('data_int') or metadata.get('Data_int') or metadata.get('Data_Inter') or metadata.get('data inter') or metadata.get('date') or metadata.get('Date') or metadata.get('تاريخ تقديم الطلب') or ''
    if date_val:
        metadata['Data_Int'] = date_val

    notes_val = metadata.get('notes') or metadata.get('Notes') or metadata.get('ملاحظات') or metadata.get('note') or ''
    if notes_val:
        metadata['notes'] = notes_val

    for dir_k, aliases in [('north', ['الحد البحري', 'بحري']), ('east', ['الحد الشرقي', 'شرقي']), ('south', ['الحد القبلي', 'قبلي']), ('west', ['الحد الغربي', 'غربي'])]:
        if not metadata.get(dir_k):
            for alias in aliases:
                if metadata.get(alias):
                    metadata[dir_k] = metadata[alias]
                    break

    # Standardize site description / place
    place_val = metadata.get('place') or metadata.get('activity') or metadata.get('address') or metadata.get('وصف الموقع') or metadata.get('وصف التعدي') or ''
    if place_val:
        metadata['place'] = place_val
        metadata['address'] = place_val

    if len(raw_vertices) < 3:
        raise HTTPException(status_code=400, detail="الملف لا يحتوي على 3 أركان على الأقل للأرض.")

    # Deduplicate consecutive duplicates (< 1e-9 deg ~ 0.1mm)
    vertices = []
    for pt in raw_vertices:
        if not vertices:
            vertices.append(pt)
        else:
            prev = vertices[-1]
            if abs(pt[0] - prev[0]) > 1e-9 or abs(pt[1] - prev[1]) > 1e-9:
                vertices.append(pt)

    # Check Ring Closure duplicate
    if len(vertices) > 3:
        if abs(vertices[-1][0] - vertices[0][0]) < 1e-9 and abs(vertices[-1][1] - vertices[0][1]) < 1e-9:
            vertices.pop()

    # Parse Areas CSV
    areas_list = []
    if areas_content:
        reader_a = csv.DictReader(io.StringIO(areas_content))
        for row in reader_a:
            areas_list.append(row)

    # Auto-enrich metadata
    if areas_list:
        if not metadata.get("hod_name"):
            hods = [a.get("hod_name", "").strip() for a in areas_list if a.get("hod_name")]
            metadata["hod_name"] = " - ".join(dict.fromkeys(hods)) if hods else "-"
        if not metadata.get("parcel_id"):
            parcels = [str(a.get("parcel_id", "")).strip() for a in areas_list if a.get("parcel_id")]
            metadata["parcel_id"] = ", ".join(dict.fromkeys(parcels)) if parcels else "-"
        if not metadata.get("map_id"):
            maps = [str(a.get("map_id", "")).strip() for a in areas_list if a.get("map_id")]
            metadata["map_id"] = ", ".join(dict.fromkeys(maps)) if maps else "-"

    if not metadata.get("address") and metadata.get("place"):
        metadata["address"] = metadata.get("place")

    # Geodesic area calculation
    stated_area_val = 0.0
    try:
        stated_area_val = float(metadata.get("area", 0))
    except (ValueError, TypeError):
        pass

    calc_area = calculate_geodesic_area(vertices)
    diff = round(calc_area - stated_area_val, 2)
    is_valid = abs(diff) <= 2.0

    segments, edge_lens = calculate_boundary_segments(vertices)

    return {
        "metadata": metadata,
        "vertices": vertices,
        "segments": segments,
        "stated_area": f"{stated_area_val:.2f}",
        "calculated_area": f"{calc_area:.2f}",
        "area_difference": f"{diff:+.2f}",
        "is_area_valid": is_valid,
        "edge_lengths": {k: f"{v:.2f}" for k, v in edge_lens.items()},
        "areas": areas_list
    }

@web_app.post("/api/preview-satellite")
def preview_satellite(payload: Dict[str, Any] = Body(...)):
    """Fetches high-resolution satellite imagery and returns as base64 Data URI"""
    vertices = payload.get("vertices", [])
    if not vertices or len(vertices) < 3:
        raise HTTPException(status_code=400, detail="مطلوب 3 إحداثيات على الأقل.")

    stated_area = payload.get("stated_area")
    try:
        img_bytes = fetch_satellite_image(vertices, stated_area=stated_area)
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        return {"satellite_url": f"data:image/jpeg;base64,{b64_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب صورة القمر الصناعي: {str(e)}")

@web_app.post("/api/preview-croquis")
def preview_croquis(payload: Dict[str, Any] = Body(...)):
    """Renders CAD croquis and returns as base64 Data URI"""
    vertices = payload.get("vertices", [])
    if not vertices or len(vertices) < 3:
        raise HTTPException(status_code=400, detail="مطلوب 3 إحداثيات على الأقل.")

    boundaries = payload.get("boundaries", {})
    edited_segments = payload.get("edited_segments")
    edited_lengths = payload.get("edited_lengths")
    edited_directions = payload.get("edited_directions")

    try:
        img_bytes = render_cad_croquis(
            vertices,
            boundaries=boundaries,
            edited_segments=edited_segments,
            edited_lengths=edited_lengths,
            edited_directions=edited_directions
        )
        b64_str = base64.b64encode(img_bytes).decode("utf-8")
        return {"croquis_url": f"data:image/png;base64,{b64_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في رسم كروكي الـ CAD: {str(e)}")

@web_app.post("/api/generate-certificate")
def generate_certificate(payload: Dict[str, Any] = Body(...)):
    """
    Generates official certificate (.docx) + separate satellite & croquis images.
    Returns ZIP package with all files ready for browser download.
    """
    land_data = payload.get("land_data", {})
    areas_list = payload.get("areas_list", [])
    boundaries = payload.get("boundaries", {})
    vertices = land_data.get("vertices", [])
    survey_tech = payload.get("survey_tech", "محمد ابراهيم بدير")
    sys_officer = payload.get("sys_officer", "شريف محمد")
    edited_segments = payload.get("edited_segments")
    edited_lengths = payload.get("edited_lengths")
    edited_directions = payload.get("edited_directions")

    if not vertices or len(vertices) < 3:
        raise HTTPException(status_code=400, detail="مطلوب 3 إحداثيات صالحة لإنشاء الشهادة.")

    case_id = clean_filename(str(land_data.get("id_no", "000")))
    raw_name = clean_filename(str(land_data.get("name", "Unknown"))).strip()

    # 1. Satellite Image (custom base64 or generated)
    custom_sat = payload.get("custom_sat_base64")
    if custom_sat and "," in custom_sat:
        sat_bytes = base64.b64decode(custom_sat.split(",")[1])
    else:
        stated_area = land_data.get("area")
        sat_bytes = fetch_satellite_image(vertices, stated_area=stated_area)

    # 2. CAD Croquis Image (custom base64 or generated)
    custom_croq = payload.get("custom_croq_base64")
    if custom_croq and "," in custom_croq:
        croq_bytes = base64.b64decode(custom_croq.split(",")[1])
    else:
        croq_bytes = render_cad_croquis(
            vertices,
            boundaries=boundaries,
            edited_segments=edited_segments,
            edited_lengths=edited_lengths,
            edited_directions=edited_directions
        )

    # 3. Calculate 4-direction sums
    edge_sums = {'north': 0.0, 'east': 0.0, 'south': 0.0, 'west': 0.0}
    if edited_segments and isinstance(edited_segments, list):
        for seg in edited_segments:
            d = seg.get('direction', 'north').lower()
            if d in edge_sums:
                try:
                    edge_sums[d] += float(seg.get('length_m', 0.0))
                except (ValueError, TypeError):
                    pass
    else:
        _, edge_totals = calculate_boundary_segments(vertices)
        edge_sums = edge_totals

    docx_bounds = {
        'north': {'desc': boundaries.get('north', '').strip(), 'length': round(edge_sums.get('north', 0.0), 2)},
        'east': {'desc': boundaries.get('east', '').strip(), 'length': round(edge_sums.get('east', 0.0), 2)},
        'south': {'desc': boundaries.get('south', '').strip(), 'length': round(edge_sums.get('south', 0.0), 2)},
        'west': {'desc': boundaries.get('west', '').strip(), 'length': round(edge_sums.get('west', 0.0), 2)}
    }

    # 4. Generate DOCX in memory
    try:
        docx_bytes = create_certificate_docx(
            land_data,
            areas_list,
            docx_bounds,
            output_target=None,
            survey_tech=survey_tech,
            sys_officer=sys_officer,
            croquis_img=croq_bytes,
            sat_img=sat_bytes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ أثناء إنشاء ملف Word: {str(e)}")

    # 5. Pack everything into an in-memory ZIP archive
    zip_buffer = io.BytesIO()
    docx_name = f"Certificate_{case_id}_{raw_name}.docx"
    sat_name = f"satellite_{case_id}.jpg"
    croq_name = f"croquis_{case_id}.png"

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(docx_name, docx_bytes)
        zip_file.writestr(sat_name, sat_bytes)
        zip_file.writestr(croq_name, croq_bytes)

    zip_buffer.seek(0)
    zip_filename = f"Certificate_Package_{case_id}_{raw_name}.zip"
    encoded_filename = urllib.parse.quote(zip_filename)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

# ---------------------------------------------------------------------------
# Modal Function Wrapper
# ---------------------------------------------------------------------------
if app is not None:
    @app.function(timeout=300)
    @modal.asgi_app()
    def modal_asgi():
        return web_app

if __name__ == "__main__":
    import uvicorn
    print("Starting local development server at http://localhost:8000")
    uvicorn.run(web_app, host="0.0.0.0", port=8000)
