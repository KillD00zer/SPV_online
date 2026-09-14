# -*- coding: utf-8 -*-
"""
High-Precision CAD Dimensions Croquis Engine (Cloud & Modal Ready)
==================================================================
Official engineering sketch generator (كروكى الموقع):
- High-contrast white background.
- Thick black polygon outline.
- Numbered vertex nodes with dark brown font (#3E2723, 11pt bold) on bright green (#00E676) circular markers.
- Segment lengths in bold red (#D32F2F, 12pt bold) aligned with edge angles printed INSIDE the shape.
- Neighbor descriptions in bold sky blue (#0284C7, 13pt bold) aligned with edge angles printed OUTSIDE the shape.
- Semi-transparent North Arrow (بوصلة سهم الشمال) at top-left.
- Ultra High Resolution output (300 DPI / 1600x1200 / tight bbox).
- Robust Arabic reshaping and bidi algorithm support for Linux & Cloud containers.
"""

import os
import io
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

# Setup fallback fonts for Arabic text rendering in Linux / Docker / Windows
plt.rcParams['font.sans-serif'] = ['Cairo', 'DejaVu Sans', 'Arial', 'Tahoma', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def format_arabic_text(text):
    """Reshape Arabic characters and apply bidi algorithm for correct display in matplotlib."""
    if not text:
        return ""
    text_str = str(text).strip()
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text_str)
        return get_display(reshaped)
    except Exception:
        return text_str

def get_edge_cardinal_direction(p1_lon, p1_lat, p2_lon, p2_lat, c_lon, c_lat):
    mid_x = (p1_lon + p2_lon) / 2.0 - c_lon
    mid_y = (p1_lat + p2_lat) / 2.0 - c_lat
    dx = p2_lon - p1_lon
    dy = p2_lat - p1_lat
    
    if abs(dx) > abs(dy):
        return "north" if mid_y > 0 else "south"
    else:
        return "east" if mid_x > 0 else "west"

def project_to_metric(vertices_lon_lat):
    if not vertices_lon_lat:
        return []
    lons = [pt[0] for pt in vertices_lon_lat]
    lats = [pt[1] for pt in vertices_lon_lat]
    c_lon = sum(lons) / len(lons)
    c_lat = sum(lats) / len(lats)
    lat_scale = math.cos(math.radians(c_lat)) * 111320.0
    return [((lon - c_lon) * lat_scale, (lat - c_lat) * 110540.0) for lon, lat in vertices_lon_lat]

def render_cad_croquis(vertices, boundaries=None, output_image_path=None,
                       edited_segments=None, edited_lengths=None, edited_directions=None):
    """
    Renders CAD croquis sketch.
    If output_image_path is provided, saves to disk and returns path.
    Otherwise returns bytes of PNG image.
    """
    if not vertices or len(vertices) < 3:
        raise ValueError("At least 3 vertices required to render CAD croquis.")
    
    # Normalize vertices to list of (lon, lat) and dicts
    norm_verts = []
    for idx, v in enumerate(vertices, start=1):
        if isinstance(v, (list, tuple)):
            norm_verts.append({"point_index": idx, "lon": float(v[0]), "lat": float(v[1])})
        elif isinstance(v, dict):
            pt_idx = v.get("point_index", idx)
            norm_verts.append({"point_index": pt_idx, "lon": float(v["lon"]), "lat": float(v["lat"])})
        else:
            raise TypeError(f"Unsupported vertex format: {type(v)}")
            
    n_pts = len(norm_verts)
    lons = [v["lon"] for v in norm_verts]
    lats = [v["lat"] for v in norm_verts]
    
    # Centroid
    c_lon = float(np.mean(lons))
    c_lat = float(np.mean(lats))
    lat_scale = math.cos(math.radians(c_lat)) * 111320.0
    
    xs = [(lon - c_lon) * lat_scale for lon in lons]
    ys = [(lat - c_lat) * 110540.0 for lat in lats]
    pts_2d = list(zip(xs, ys))
    
    # Calculate bounds & span
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 10.0)
    span_y = max(max_y - min_y, 10.0)
    
    pad_x = span_x * 0.14
    pad_y = span_y * 0.14
    
    # Build figure with 300 DPI
    fig, ax = plt.subplots(figsize=(6.5, 4.8), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    # 1. Draw parcel polygon outline with strong line weight
    poly_patch = MplPolygon(pts_2d, closed=True, facecolor='none', edgecolor='black', linewidth=3.0, zorder=2)
    ax.add_patch(poly_patch)
    
    # Determine polygon orientation
    signed_area = 0.5 * sum(xs[i] * ys[(i + 1) % n_pts] - xs[(i + 1) % n_pts] * ys[i] for i in range(n_pts))
    is_ccw = signed_area > 0
    
    # 2. Vertex markers and sequential numbers
    for i in range(n_pts):
        x, y = xs[i], ys[i]
        ax.plot(x, y, marker='o', markersize=7.5, markerfacecolor='#00E676', markeredgecolor='black', markeredgewidth=1.5, zorder=4)
        
        dx = x - 0.0
        dy = y - 0.0
        dist_c = math.hypot(dx, dy) or 1.0
        norm_dx = dx / dist_c
        norm_dy = dy / dist_c
        
        v_offset = max(span_x, span_y) * 0.038
        label_x = x + norm_dx * v_offset
        label_y = y + norm_dy * v_offset
        
        ax.text(label_x, label_y, str(norm_verts[i]["point_index"]),
                color='#3E2723', fontsize=11, fontweight='bold',
                ha='center', va='center', zorder=5)
        
    # Map edges to cardinal neighbor descriptions
    bounds = boundaries or {}
    side_longest_edge = {}
    
    for i in range(n_pts):
        next_i = (i + 1) % n_pts
        length_m = None
        if edited_segments and i < len(edited_segments):
            try:
                length_m = float(edited_segments[i].get("length_m", 0))
            except (ValueError, TypeError):
                pass
        if length_m is None and edited_lengths and str(i) in edited_lengths:
            try:
                length_m = float(edited_lengths[str(i)])
            except (ValueError, TypeError):
                pass
        if length_m is None:
            length_m = math.hypot(xs[next_i] - xs[i], ys[next_i] - ys[i])
            
        side = None
        if edited_segments and i < len(edited_segments):
            side = edited_segments[i].get("direction")
        if not side and edited_directions and str(i) in edited_directions:
            side = edited_directions[str(i)]
        if not side:
            side = get_edge_cardinal_direction(norm_verts[i]["lon"], norm_verts[i]["lat"],
                                               norm_verts[next_i]["lon"], norm_verts[next_i]["lat"],
                                               c_lon, c_lat)
        side = (side or "north").lower()
        if side not in side_longest_edge or length_m > side_longest_edge[side][1]:
            side_longest_edge[side] = (i, length_m)

    # 3. Segment length & neighbor annotations
    for i in range(n_pts):
        next_i = (i + 1) % n_pts
        x1, y1 = xs[i], ys[i]
        x2, y2 = xs[next_i], ys[next_i]
        
        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0
        
        edge_dx = x2 - x1
        edge_dy = y2 - y1
        edge_len = math.hypot(edge_dx, edge_dy) or 1.0
        
        angle_rad = math.atan2(edge_dy, edge_dx)
        angle_deg = math.degrees(angle_rad)
        
        if angle_deg > 90:
            angle_deg -= 180
        elif angle_deg < -90:
            angle_deg += 180
            
        if is_ccw:
            out_nx = edge_dy / edge_len
            out_ny = -edge_dx / edge_len
        else:
            out_nx = -edge_dy / edge_len
            out_ny = edge_dx / edge_len
            
        in_nx = -out_nx
        in_ny = -out_ny
        
        len_offset = min(max(span_x, span_y) * 0.042, max(edge_len * 0.22, 2.0))
        len_x = mid_x + in_nx * len_offset
        len_y = mid_y + in_ny * len_offset
        
        length_m = None
        if edited_segments and i < len(edited_segments):
            try:
                length_m = float(edited_segments[i].get("length_m", 0))
            except (ValueError, TypeError):
                pass
        if length_m is None and edited_lengths and str(i) in edited_lengths:
            try:
                length_m = float(edited_lengths[str(i)])
            except (ValueError, TypeError):
                pass
        if length_m is None:
            length_m = edge_len
            
        len_str = f"{length_m:.2f}م"
        reshaped_len_str = format_arabic_text(len_str)
        
        ax.text(len_x, len_y, reshaped_len_str,
                color='#D32F2F', fontsize=12, fontweight='bold',
                rotation=angle_deg, rotation_mode='anchor',
                ha='center', va='center', zorder=5)
        
        side = None
        if edited_segments and i < len(edited_segments):
            side = edited_segments[i].get("direction")
        if not side and edited_directions and str(i) in edited_directions:
            side = edited_directions[str(i)]
        if not side:
            side = get_edge_cardinal_direction(norm_verts[i]["lon"], norm_verts[i]["lat"],
                                               norm_verts[next_i]["lon"], norm_verts[next_i]["lat"],
                                               c_lon, c_lat)
        side = (side or "north").lower()
        neighbor_text = ""
        if side in side_longest_edge and side_longest_edge[side][0] == i:
            neighbor_text = bounds.get(side, "")
            
        if neighbor_text and str(neighbor_text).strip():
            neigh_offset = max(span_x, span_y) * 0.08
            neigh_x = mid_x + out_nx * neigh_offset
            neigh_y = mid_y + out_ny * neigh_offset
            
            reshaped_neighbor = format_arabic_text(neighbor_text)
            ax.text(neigh_x, neigh_y, reshaped_neighbor,
                    color='#0284C7', fontsize=13, fontweight='bold',
                    rotation=angle_deg, rotation_mode='anchor',
                    ha='center', va='center', zorder=5)
        
    # 4. Semi-Transparent Compass Rose / North Arrow
    ax.annotate(
        '', xy=(0.06, 0.94), xytext=(0.06, 0.81), xycoords='axes fraction',
        arrowprops=dict(facecolor='black', edgecolor='black', width=2.8, headwidth=9.5, headlength=10.5, alpha=0.35),
        zorder=6
    )
    ax.text(0.06, 0.96, 'N', transform=ax.transAxes,
            color='black', fontsize=13, fontweight='bold', ha='center', va='bottom', alpha=0.45, zorder=6)
    
    ax.set_xlim(min_x - pad_x, max_x + pad_x)
    ax.set_ylim(min_y - pad_y, max_y + pad_y)
    ax.set_aspect('equal', adjustable='datalim')
    ax.axis('off')
    plt.tight_layout(pad=0.06)
    
    if output_image_path:
        out_dir = os.path.dirname(os.path.abspath(output_image_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        plt.savefig(output_image_path, dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.03)
        plt.close(fig)
        return output_image_path
    else:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.03)
        plt.close(fig)
        return buf.getvalue()
