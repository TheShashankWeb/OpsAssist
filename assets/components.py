# assets/components.py
# OpsAssist v2.0 — Reusable HTML Component Library

def page_header(title: str, subtitle: str = "", icon: str = "") -> str:
    """Renders a styled page header with optional icon and subtitle."""
    icon_html = f'<span class="header-icon">{icon}</span>' if icon else ""
    sub_html = f'<p class="header-subtitle">{subtitle}</p>' if subtitle else ""
    return f"""
    <div class="oa-page-header fade-in">
        <div class="header-title-row">
            {icon_html}
            <h1 class="header-title">{title}</h1>
        </div>
        {sub_html}
    </div>
    """

def kpi_card(
    label: str,
    value: str,
    delta: str = "",
    delta_type: str = "neutral",
    icon: str = "",
    border_color: str = "#0EA5E9"
) -> str:
    """
    Renders a premium KPI card.
    delta_type: 'positive', 'negative', 'neutral', 'warning'
    """
    delta_colors = {
        "positive": "#10B981",
        "negative": "#EF4444",
        "warning":  "#F59E0B",
        "neutral":  "#94A3B8"
    }
    delta_color = delta_colors.get(delta_type, "#94A3B8")
    delta_html = f"""
        <div class="kpi-delta" style="color:{delta_color}">
            {delta}
        </div>
    """ if delta else ""
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""

    return f"""
    <div class="oa-kpi-card fade-in" style="border-top: 3px solid {border_color}">
        <div class="kpi-top">
            {icon_html}
            <div class="kpi-label">{label}</div>
        </div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """

def alert_card(
    alert_type: str,
    title: str,
    message: str,
    sector: str = "",
    detail: str = ""
) -> str:
    """Renders a styled alert card with color coding by type."""
    type_config = {
        "Vendor TAT Decline":  {"color": "#F59E0B", "bg": "rgba(245,158,11,0.08)",  "icon": "🟠"},
        "Cold Storage Breach": {"color": "#EF4444", "bg": "rgba(239,68,68,0.08)",   "icon": "🔴"},
        "Shipment Ageing":     {"color": "#FBBF24", "bg": "rgba(251,191,36,0.08)",  "icon": "🟡"},
        "Slow-Moving SKU":     {"color": "#0EA5E9", "bg": "rgba(14,165,233,0.08)",  "icon": "🔵"},
    }
    cfg = type_config.get(alert_type, {"color": "#94A3B8", "bg": "rgba(148,163,184,0.08)", "icon": "⚪"})
    sector_html = f'<span class="alert-sector">📍 {sector}</span>' if sector else ""
    detail_html = f'<div class="alert-detail">{detail}</div>' if detail else ""

    return f"""
    <div class="oa-alert-card fade-in" style="border-left: 4px solid {cfg['color']}; background: {cfg['bg']}">
        <div class="alert-header">
            <span class="alert-icon">{cfg['icon']}</span>
            <span class="alert-type" style="color:{cfg['color']}">{alert_type}</span>
            {sector_html}
        </div>
        <div class="alert-title">{title}</div>
        <div class="alert-message">{message}</div>
        {detail_html}
    </div>
    """

def badge(text: str, variant: str = "info") -> str:
    """Renders a colored status badge/pill."""
    variants = {
        "success": ("var(--success-bg)", "var(--success)"),
        "warning": ("var(--warning-bg)", "var(--warning)"),
        "danger":  ("var(--danger-bg)",  "var(--danger)"),
        "info":    ("var(--info-bg)",    "var(--info)"),
        "neutral": ("rgba(148,163,184,0.12)", "#94A3B8"),
    }
    bg, color = variants.get(variant, variants["info"])
    return f"""<span style="
        background:{bg}; color:{color};
        padding:3px 10px; border-radius:999px;
        font-size:0.72rem; font-weight:600;
        letter-spacing:0.04em; text-transform:uppercase;
        display:inline-block;
    ">{text}</span>"""

def section_header(title: str, subtitle: str = "") -> str:
    """Renders a styled section divider with title."""
    sub_html = f'<span class="section-subtitle"> — {subtitle}</span>' if subtitle else ""
    return f"""
    <div class="oa-section-header">
        <span class="section-title">{title}</span>
        {sub_html}
    </div>
    """

def info_banner(message: str, variant: str = "info") -> str:
    """Renders a styled info/warning/success banner."""
    configs = {
        "info":    ("var(--info-bg)",    "var(--info)",    "ℹ️"),
        "success": ("var(--success-bg)", "var(--success)", "✅"),
        "warning": ("var(--warning-bg)", "var(--warning)", "⚠️"),
        "danger":  ("var(--danger-bg)",  "var(--danger)",  "🚨"),
    }
    bg, color, icon = configs.get(variant, configs["info"])
    return f"""
    <div style="
        background:{bg}; border:1px solid {color};
        border-radius:10px; padding:0.75rem 1rem;
        color:{color}; font-size:0.88rem;
        font-weight:500; margin:0.5rem 0;
        display:flex; align-items:center; gap:0.5rem;
    ">
        <span>{icon}</span>
        <span>{message}</span>
    </div>
    """

def stat_row(items: list) -> str:
    """
    Renders a horizontal row of small stat items.
    items = [{"label": "Total", "value": "500", "color": "#0EA5E9"}, ...]
    """
    items_html = ""
    for item in items:
        color = item.get("color", "#0EA5E9")
        items_html += f"""
        <div class="stat-item">
            <div class="stat-value" style="color:{color}">{item['value']}</div>
            <div class="stat-label">{item['label']}</div>
        </div>
        """
    return f'<div class="oa-stat-row fade-in">{items_html}</div>'

# ── Component CSS (appended to main.css via load_css) ────────────────────────
COMPONENT_CSS = """
/* ── Page Header ─────────────────────────────────────────── */
.oa-page-header {
  margin-bottom: 1.75rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}
.header-title-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.header-icon { font-size: 1.6rem; }
.header-title {
  font-size: 1.6rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
}
.header-subtitle {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin: 0.4rem 0 0 0;
}

/* ── KPI Cards ───────────────────────────────────────────── */
.oa-kpi-card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: all 0.25s ease;
  height: 100%;
}
.oa-kpi-card:hover {
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}
.kpi-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}
.kpi-icon { font-size: 1.1rem; }
.kpi-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.kpi-value {
  font-size: 2.1rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.15;
  letter-spacing: -0.02em;
}
.kpi-delta {
  font-size: 0.78rem;
  font-weight: 500;
  margin-top: 0.35rem;
}

/* ── Alert Cards ─────────────────────────────────────────── */
.oa-alert-card {
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  transition: transform 0.2s ease;
}
.oa-alert-card:hover { transform: translateX(3px); }
.alert-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}
.alert-type {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.alert-sector {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-left: auto;
}
.alert-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}
.alert-message {
  font-size: 0.83rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
.alert-detail {
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-top: 0.35rem;
  font-style: italic;
}

/* ── Section Header ──────────────────────────────────────── */
.oa-section-header {
  margin: 1.5rem 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.07em;
}
.section-subtitle {
  font-size: 0.82rem;
  color: var(--text-muted);
}

/* ── Stat Row ────────────────────────────────────────────── */
.oa-stat-row {
  display: flex;
  gap: 2rem;
  padding: 1rem 0;
  flex-wrap: wrap;
}
.stat-item { text-align: center; }
.stat-value {
  font-size: 1.4rem;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.2rem;
}
"""
