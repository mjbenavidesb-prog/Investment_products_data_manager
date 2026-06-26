import re
import streamlit as st
import backend.config as cfg
from backend.database import reseed_from_file, seed_from_file, get_all_products, generate_template_xlsx
from pathlib import Path


def _parse_custom_fields(text: str) -> list:
    """Parse 'Label : opt1, opt2' format into list of field dicts."""
    fields = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            label, rest = line.split(":", 1)
            label = label.strip()
            if not label:
                continue
            opts = [o.strip() for o in rest.split(",") if o.strip()]
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            fields.append({
                "key": key,
                "label": label,
                "type": "select" if opts else "text",
                "options": opts,
            })
    return fields


def _format_custom_fields(fields: list) -> str:
    """Serialize field list back to the editable text format."""
    lines = []
    for f in fields:
        opts = ", ".join(f.get("options", []))
        lines.append(f'{f["label"]} : {opts}')
    return "\n".join(lines)

_TEMPLATES_DIR = Path("data/templates")


def _swatch(color: str, label: str) -> str:
    return f"""<div style='text-align:center;'>
        <div style='width:70px;height:70px;background:{color};border-radius:8px;
                    margin:0 auto 4px;border:1px solid #2d2d4e;'></div>
        <span style='font-size:10px;color:#a0aec0;'>{label}</span>
    </div>"""


def render():
    st.subheader("Settings")

    tab_company, tab_lists = st.tabs(["Company & Branding", "Classification Lists"])

    with tab_company:
        st.markdown("#### Company Identity")
        col1, col2 = st.columns([1, 1])

        with col1:
            company_name = st.text_input(
                "Company Name",
                value=cfg.get("company_name") or "",
                help="Shown in the app header and on generated factsheets.",
            )

        st.markdown("#### Color Palette")
        st.caption("These colors are used across all charts and UI accents.")

        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            primary_color = st.color_picker(
                "Primary Color", value=cfg.get("primary_color") or "#2563EB"
            )
        with cc2:
            secondary_color = st.color_picker(
                "Secondary Color", value=cfg.get("secondary_color") or "#DC2626"
            )
        with cc3:
            accent_color_1 = st.color_picker(
                "Accent 1 (Amber)", value=cfg.get("accent_color_1") or "#F59E0B"
            )

        cc4, cc5, cc6 = st.columns(3)
        with cc4:
            accent_color_2 = st.color_picker(
                "Accent 2 (Green)", value=cfg.get("accent_color_2") or "#10B981"
            )
        with cc5:
            accent_color_3 = st.color_picker(
                "Accent 3 (Purple)", value=cfg.get("accent_color_3") or "#8B5CF6"
            )
        with cc6:
            neutral_color = st.color_picker(
                "Neutral / Gray", value=cfg.get("neutral_color") or "#6B7280"
            )

        # Live color preview
        st.markdown("**Preview**")
        swatches = "".join([
            _swatch(primary_color, "Primary"),
            _swatch(secondary_color, "Secondary"),
            _swatch(accent_color_1, "Accent 1"),
            _swatch(accent_color_2, "Accent 2"),
            _swatch(accent_color_3, "Accent 3"),
            _swatch(neutral_color, "Neutral"),
        ])
        st.markdown(
            f"<div style='display:flex;gap:16px;margin:8px 0 20px;'>{swatches}</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### API Keys")
        current_key = cfg.get("claude_api_key") or ""
        masked = current_key[:8] + "..." if len(current_key) > 8 else ""
        new_api_key = st.text_input(
            "Claude API Key",
            value="",
            type="password",
            placeholder=masked or "sk-ant-...",
            help="Required for termsheet extraction with Claude AI. Stored locally only.",
        )

        if st.button("Save Company Settings", type="primary"):
            cfg.save("company_name", company_name)
            cfg.save("primary_color", primary_color)
            cfg.save("secondary_color", secondary_color)
            cfg.save("accent_color_1", accent_color_1)
            cfg.save("accent_color_2", accent_color_2)
            cfg.save("accent_color_3", accent_color_3)
            cfg.save("neutral_color", neutral_color)
            if new_api_key.strip():
                cfg.save("claude_api_key", new_api_key.strip())
            st.success("Settings saved. Reload the page to apply colors across all charts.")

        # ── Company logo ───────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### Logo de la Empresa")
        st.caption(
            "Sube el logo de tu empresa en **PNG o JPG**. "
            "Aparecerá en la barra de cabecera de todos los factsheets generados. "
            "Recomendado: fondo transparente (PNG) o blanco, formato horizontal."
        )

        _TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

        # Find any existing logo
        _logo_path = None
        for _ext in ("png", "jpg", "jpeg"):
            _p = _TEMPLATES_DIR / f"company_logo.{_ext}"
            if _p.exists():
                _logo_path = _p
                break

        if _logo_path:
            st.image(str(_logo_path), width=220)
            st.success(f"Logo activo: **{_logo_path.name}** ({_logo_path.stat().st_size // 1024} KB)")
            if st.button("Eliminar logo", key="del_logo"):
                _logo_path.unlink()
                st.rerun()
        else:
            st.caption("Sin logo — se mostrará el nombre de la empresa en texto.")

        uploaded_logo = st.file_uploader(
            "Subir logo (PNG, JPG)",
            type=["png", "jpg", "jpeg"],
            key="logo_upload",
            label_visibility="collapsed",
        )
        if uploaded_logo:
            ext = uploaded_logo.name.rsplit(".", 1)[-1].lower()
            # Remove any previous logo files
            for _ext in ("png", "jpg", "jpeg"):
                _old = _TEMPLATES_DIR / f"company_logo.{_ext}"
                if _old.exists():
                    _old.unlink()
            logo_save_path = _TEMPLATES_DIR / f"company_logo.{ext}"
            logo_save_path.write_bytes(uploaded_logo.read())
            st.success("Logo guardado. Se aplicará en el próximo factsheet generado.")
            st.rerun()

    # ── Database / Portfolio import ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Importar Portafolio")

    n_productos = len(get_all_products())
    if n_productos:
        st.info(f"Base de datos activa: **{n_productos} productos** cargados.")
    else:
        st.warning("La base de datos está vacía. Sube un archivo para comenzar.")

    st.caption(
        "Sube tu base de datos en **Excel (.xlsx)** o **CSV (.csv)** para cargar o actualizar "
        "el portafolio completo. Si tu archivo tiene columnas distintas, descarga primero la "
        "plantilla y adáptala a tu formato."
    )

    st.download_button(
        label="Descargar plantilla Excel",
        data=generate_template_xlsx(),
        file_name="plantilla_portafolio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Excel con todas las columnas esperadas y una fila de ejemplo.",
    )

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    uploaded_portfolio = st.file_uploader(
        "Subir Excel o CSV del portafolio",
        type=["xlsx", "xls", "csv"],
        key="portfolio_upload",
        label_visibility="collapsed",
    )

    if uploaded_portfolio:
        mode = st.radio(
            "¿Qué hacer con los datos existentes?",
            ["Reemplazar todo (borrar base y reimportar)", "Agregar a los existentes"],
            key="import_mode",
        )
        if st.button("Importar portafolio", type="primary"):
            file_bytes = uploaded_portfolio.read()
            with st.spinner("Importando..."):
                try:
                    if "Reemplazar" in mode:
                        result = reseed_from_file(file_bytes, uploaded_portfolio.name)
                    else:
                        result = seed_from_file(file_bytes, uploaded_portfolio.name)
                    st.success(f"{result} productos importados desde **{uploaded_portfolio.name}**.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al importar: {e}")

    with st.expander("Opciones avanzadas", expanded=False):
        st.caption("Borra todos los productos de la base de datos sin reimportar.")
        if st.button("Limpiar base de datos", type="secondary", key="clear_db"):
            import sqlite3
            from backend.database import get_connection
            conn = get_connection()
            conn.execute("DELETE FROM products")
            conn.commit()
            conn.close()
            st.success("Base de datos limpiada.")
            st.rerun()

    with tab_lists:
        st.markdown("#### Campos del Panel Derecho (Load Product)")
        st.caption(
            "Activa/desactiva cada campo, renómbralo y edita sus opciones. "
            "Los cambios afectan el formulario de carga de productos."
        )

        _rpf_saved = cfg.get("right_panel_fields") or cfg.DEFAULTS["right_panel_fields"]

        _options_map = {
            "asset_classes": cfg.get("asset_classes") or cfg.DEFAULTS["asset_classes"],
            "vehicles":      cfg.get("vehicles")      or cfg.DEFAULTS["vehicles"],
            "entities":      cfg.get("entities")      or cfg.DEFAULTS["entities"],
            "jurisdictions": cfg.get("jurisdictions") or cfg.DEFAULTS["jurisdictions"],
            "profiles":      cfg.get("profiles")      or cfg.DEFAULTS["profiles"],
            "client_types":  cfg.get("client_types")  or cfg.DEFAULTS["client_types"],
            "countries":     cfg.get("countries")     or cfg.DEFAULTS["countries"],
            "segments":      cfg.get("segments")      or cfg.DEFAULTS["segments"],
        }

        updated_rpf  = []
        updated_opts = {}

        # Header row
        h1, h2, h3 = st.columns([0.5, 3, 6])
        with h1: st.caption("On")
        with h2: st.caption("Label")
        with h3: st.caption("Options (comma-separated)")

        for fi, field in enumerate(_rpf_saved):
            fkey  = field["key"]
            ftype = field.get("type", "select")
            ck    = field.get("config_key")

            fc1, fc2, fc3 = st.columns([0.5, 3, 6])
            with fc1:
                enabled = st.checkbox("", value=field.get("enabled", True),
                                      key=f"rpf_en_{fi}", label_visibility="collapsed")
            with fc2:
                label = st.text_input("", value=field.get("label", fkey),
                                      key=f"rpf_lbl_{fi}", label_visibility="collapsed")
            with fc3:
                if ck and ftype == "select":
                    cur_opts = _options_map.get(ck, [])
                    opts_txt = st.text_input("", value=", ".join(cur_opts),
                                             key=f"rpf_opts_{fi}", label_visibility="collapsed")
                    updated_opts[ck] = [o.strip() for o in opts_txt.split(",") if o.strip()]
                else:
                    st.caption("*(numeric)*")

            updated_rpf.append({
                "key": fkey, "label": label,
                "config_key": ck, "type": ftype, "enabled": enabled,
            })

        st.markdown("---")
        st.markdown("#### Otras listas")
        st.caption("Countries y Segments — usados en los campos de AUM y desglose por segmento.")

        col_a, col_b = st.columns(2)
        with col_a:
            cur_c = cfg.get("countries") or cfg.DEFAULTS["countries"]
            countries_txt = st.text_area("Countries", value="\n".join(cur_c), height=120, key="list_countries")
            countries = [v.strip() for v in countries_txt.splitlines() if v.strip()]
        with col_b:
            cur_s = cfg.get("segments") or cfg.DEFAULTS["segments"]
            segments_txt = st.text_area("Segments", value="\n".join(cur_s), height=120, key="list_segments")
            segments = [v.strip() for v in segments_txt.splitlines() if v.strip()]

        if st.button("Guardar cambios", type="primary"):
            cfg.save("right_panel_fields", updated_rpf)
            for ck, opts in updated_opts.items():
                cfg.save(ck, opts)
            cfg.save("countries", countries)
            cfg.save("segments", segments)
            st.success("Configuración guardada correctamente.")
