# -*- coding: utf-8 -*-
"""
Local Smoke Test for SPV_online Backend APIs
============================================
Runs directly using FastAPI TestClient (no deployment needed).
Tests:
  1. Health check
  2. CSV Parsing & Geodesic Calculations
  3. CAD Croquis generation
  4. Certificate Package ZIP generation
"""

import os
import sys
import zipfile
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi.testclient import TestClient
from modal_app import web_app

client = TestClient(web_app)

def run_tests():
    print("\n" + "="*60)
    print("  بدء فحص واختبار سيرفر SPV_online محلياً")
    print("="*60)

    # 1. Health check
    print("\n[1] فحص حالة الخادم (Health Check)...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("    ✔ نجح الفحص: ", res.json())

    # 2. Test CSV parsing
    print("\n[2] فحص معالجة وتحليل ملفات الـ CSV...")
    land_path = os.path.join(CURRENT_DIR, "..", "sample_data", "Land_101_محمد_احمد.csv")
    areas_path = os.path.join(CURRENT_DIR, "..", "sample_data", "Areas_101_محمد_احمد.csv")

    with open(land_path, "r", encoding="utf-8") as f:
        land_content = f.read()
    with open(areas_path, "r", encoding="utf-8") as f:
        areas_content = f.read()

    parse_res = client.post("/api/parse-csv", json={
        "land_csv": land_content,
        "areas_csv": areas_content
    })
    assert parse_res.status_code == 200, f"Parse CSV failed: {parse_res.text}"
    case_data = parse_res.json()
    print(f"    ✔ تم تحليل بيانات: {case_data['metadata'].get('name')}")
    print(f"    ✔ عدد الأركان: {len(case_data['vertices'])} نقاط")
    print(f"    ✔ المساحة المحسوبة: {case_data['calculated_area']} م2 (المصرح بها: {case_data['stated_area']} م2)")
    print(f"    ✔ مطابقة المساحة قانونياً: {case_data['is_area_valid']} (فارق {case_data['area_difference']} م2)")
    print(f"    ✔ أطوال الأضلاع: {case_data['edge_lengths']}")

    # 3. Test CAD Croquis generation
    print("\n[3] فحص رسم كروكي الـ CAD...")
    croq_res = client.post("/api/preview-croquis", json={
        "vertices": case_data["vertices"],
        "boundaries": {
            "north": "شارع بعرض 8 متر",
            "east": "ملك أحمد حسن",
            "south": "جار ملاصق",
            "west": "طريق عام"
        },
        "edited_segments": case_data["segments"]
    })
    assert croq_res.status_code == 200, f"CAD Croquis failed: {croq_res.text}"
    croq_data = croq_res.json()
    assert "croquis_url" in croq_data and croq_data["croquis_url"].startswith("data:image/png;base64,")
    print(f"    ✔ تم توليد كروكي الـ CAD بنجاح (طول Base64: {len(croq_data['croquis_url'])} حرف)")

    # 4. Test Certificate ZIP generation
    print("\n[4] فحص إنشاء حزمة الشهادة الرسمية وتجميع الـ ZIP...")
    pkg_res = client.post("/api/generate-certificate", json={
        "land_data": {
            **case_data["metadata"],
            "vertices": case_data["vertices"],
            "calc_area": case_data["calculated_area"]
        },
        "areas_list": case_data["areas"],
        "boundaries": {
            "north": "شارع بعرض 8 متر",
            "east": "ملك أحمد حسن",
            "south": "جار ملاصق",
            "west": "طريق عام"
        },
        "custom_croq_base64": croq_data["croquis_url"],
        "custom_sat_base64": croq_data["croquis_url"],
        "survey_tech": "محمد ابراهيم بدير",
        "sys_officer": "شريف محمد"
    })
    assert pkg_res.status_code == 200, f"Generate certificate failed: {pkg_res.text}"
    assert pkg_res.headers.get("content-type") == "application/zip"
    
    zip_bytes = pkg_res.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        docx_name = next(n for n in names if n.endswith(".docx"))
        import docx
        doc_obj = docx.Document(io.BytesIO(z.read(docx_name)))
        tbl = doc_obj.tables[0]
        assert "وصف التعدي" in tbl.rows[6].cells[4].text, "Missing وصف التعدي in docx table"
        print(f"    ✔ تم التأكد من حقل الشهادة: {tbl.rows[6].cells[4].text.strip()} = {tbl.rows[6].cells[6].text.strip()}")

    print("\n" + "="*60)
    print("  🎉 جميع الفحوصات تمت بنجاح وبكفاءة تامة 100%!")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_tests()
