import io
import re
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def load_uploaded_table(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    return normalize_columns(df)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out

def _find_column(df: pd.DataFrame, candidates):
    lowered = {c.lower(): c for c in df.columns}
    for cand in candidates:
        for lc, original in lowered.items():
            if cand in lc:
                return original
    return None

def infer_xy_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    x = _find_column(df, [' x', 'x ', 'coord_x', 'xcoord', 'x_coordinate', 'imagex']) or _find_column(df, ['x'])
    y = _find_column(df, [' y', 'y ', 'coord_y', 'ycoord', 'y_coordinate', 'imagey']) or _find_column(df, ['y'])
    if x == y:
        return None, None
    return x, y

def infer_curvature_column(df: pd.DataFrame) -> Optional[str]:
    return _find_column(df, ['point curvature', 'curvature', 'curve'])

def infer_segment_column(df: pd.DataFrame) -> Optional[str]:
    return _find_column(df, ['segment'])

def infer_wire_column(df: pd.DataFrame) -> Optional[str]:
    return _find_column(df, ['wire'])

def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')

def make_metric_cards(df: pd.DataFrame, threshold: float) -> Dict[str, str]:
    curv = infer_curvature_column(df)
    rows = len(df)
    if curv is None:
        return {
            'Rows': f'{rows:,}',
            'Curvature column': 'Not detected',
            'Above threshold': 'N/A',
        }
    vals = _safe_numeric(df[curv]).dropna()
    above = int((vals > threshold).sum())
    return {
        'Rows': f'{rows:,}',
        'Curvature points': f'{len(vals):,}',
        'Above threshold': str(above),
        'Max curvature': f'{vals.max():.4f}' if not vals.empty else 'N/A',
    }

def _with_groups(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    wire_col = infer_wire_column(out)
    seg_col = infer_segment_column(out)
    if wire_col is None:
        out['wire'] = 'Wire'
        wire_col = 'wire'
    if seg_col is None:
        out['segment'] = np.arange(1, len(out) + 1)
        seg_col = 'segment'
    out[wire_col] = out[wire_col].astype(str)
    out[seg_col] = out[seg_col].astype(str)
    return out.rename(columns={wire_col: 'wire', seg_col: 'segment'})

def build_segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    curv_col = infer_curvature_column(df)
    grouped = _with_groups(df)
    if curv_col is None:
        return grouped[['wire', 'segment']].drop_duplicates().sort_values(['wire', 'segment']).reset_index(drop=True)
    grouped['curvature'] = _safe_numeric(grouped[curv_col])
    summary = (
        grouped.groupby(['wire', 'segment'], dropna=False)['curvature']
        .agg(['count', 'mean', 'max', 'min', 'std'])
        .reset_index()
    )
    summary.columns = ['wire', 'segment', 'n_points', 'mean_curvature', 'max_curvature', 'min_curvature', 'std_curvature']
    return summary.sort_values(['wire', 'segment']).reset_index(drop=True)

def make_trace_plot(df: pd.DataFrame, title: str):
    x_col, y_col = infer_xy_columns(df)
    grouped = _with_groups(df)
    if x_col is None or y_col is None:
        return None, 'X/Y columns were not detected. Add coordinate columns or adjust the helper function mappings in core/analysis.py.'
    grouped['_x'] = _safe_numeric(grouped[x_col])
    grouped['_y'] = _safe_numeric(grouped[y_col])
    grouped = grouped.dropna(subset=['_x', '_y'])
    if grouped.empty:
        return None, 'No numeric X/Y coordinate rows were found.'
    fig = px.line(
        grouped,
        x='_x',
        y='_y',
        color='wire',
        line_group='segment',
        markers=True,
        title=title,
    )
    fig.update_layout(height=650, xaxis_title='X', yaxis_title='Y', legend_title='Wire')
    fig.update_yaxes(scaleanchor='x', scaleratio=1, autorange='reversed')
    return fig, None

def make_overlay_plot(df_a: pd.DataFrame, df_b: pd.DataFrame, title: str):
    x_a, y_a = infer_xy_columns(df_a)
    x_b, y_b = infer_xy_columns(df_b)
    if not all([x_a, y_a, x_b, y_b]):
        return None, 'Both files need detectable X/Y columns to build an overlay plot.'
    a = _with_groups(df_a)
    b = _with_groups(df_b)
    a['_x'] = _safe_numeric(a[x_a]); a['_y'] = _safe_numeric(a[y_a])
    b['_x'] = _safe_numeric(b[x_b]); b['_y'] = _safe_numeric(b[y_b])
    a = a.dropna(subset=['_x', '_y']).copy()
    b = b.dropna(subset=['_x', '_y']).copy()
    if a.empty or b.empty:
        return None, 'At least one uploaded file does not contain usable numeric tracing rows.'
    fig = go.Figure()
    for wire, part in a.groupby('wire'):
        fig.add_trace(go.Scatter(x=part['_x'], y=part['_y'], mode='lines+markers', name=f'Primary - {wire}'))
    for wire, part in b.groupby('wire'):
        fig.add_trace(go.Scatter(x=part['_x'], y=part['_y'], mode='lines+markers', name=f'Comparison - {wire}', line=dict(dash='dash')))
    fig.update_layout(title=title, height=700, xaxis_title='X', yaxis_title='Y')
    fig.update_yaxes(scaleanchor='x', scaleratio=1, autorange='reversed')
    return fig, None

def make_threshold_plot(df: pd.DataFrame, threshold: float, title: str):
    curv_col = infer_curvature_column(df)
    grouped = _with_groups(df)
    if curv_col is None:
        return None, 'No curvature-like column was detected.'
    grouped['curvature'] = _safe_numeric(grouped[curv_col])
    grouped = grouped.dropna(subset=['curvature'])
    if grouped.empty:
        return None, 'No numeric curvature values were found.'
    grouped['index'] = np.arange(1, len(grouped) + 1)
    fig = px.line(grouped, x='index', y='curvature', color='wire', line_group='segment', markers=True, title=title)
    fig.add_hline(y=threshold, line_dash='dash', line_color='red', annotation_text=f'Limit = {threshold}')
    fig.update_layout(height=650, xaxis_title='Point index', yaxis_title='Curvature (cm⁻¹)')
    return fig, None

def to_excel_bytes(sheet_map: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheet_map.items():
            clean_name = re.sub(r'[^A-Za-z0-9_ ]', '', sheet_name)[:31] or 'Sheet1'
            df.to_excel(writer, sheet_name=clean_name, index=False)
    output.seek(0)
    return output.read()
