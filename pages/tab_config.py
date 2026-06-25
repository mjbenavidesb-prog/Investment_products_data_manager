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
        st.markdown("Edit the dropdown options available throughout the app.")
        st.caption("Enter one item per line.")

        def list_editor(label, config_key, default_values):
            current = cfg.get(config_key) or default_values
            current_text = "\n".join(current) if isinstance(current, list) else str(current)
            edited = st.text_area(label, value=current_text, height=160, key=f"list_{config_key}")
            return [v.strip() for v in edited.splitlines() if v.strip()]

        col_a, col_b = st.columns(2)
        with col_a:
            vehicles = list_editor("Vehicles", "vehicles", cfg.DEFAULTS["vehicles"])
            segments = list_editor("Segments", "segments", cfg.DEFAULTS["segments"])
            asset_classes = list_editor("Asset Classes", "asset_classes", cfg.DEFAULTS["asset_classes"])

        with col_b:
            countries = list_editor("Countries", "countries", cfg.DEFAULTS["countries"])
            client_types = list_editor("Client Types", "client_types", cfg.DEFAULTS["client_types"])
            profiles = list_editor("Risk Profiles", "profiles", cfg.DEFAULTS["profiles"])

        col_c, col_d = st.columns(2)
        with col_c:
            entities = list_editor("Entities / Business Lines", "entities", cfg.DEFAULTS["entities"])
        with col_d:
            jurisdictions = list_editor("Jurisdictions", "jurisdictions", cfg.DEFAULTS["jurisdictions"])

        st.markdown("---")
        st.markdown("**Campos Adicionales (Panel Derecho — Load Product)**")
        st.caption(
            "Define campos personalizados que aparecen en la sección Manual Input del formulario "
            "de carga. Formato por línea:  \n"
            "`Nombre del campo : Opción1, Opción2, Opción3`  \n"
            "Para campo de texto libre: `Nombre del campo :` (sin opciones).  \n"
            "Para renombrar un campo existente agrega `:` al final con las opciones deseadas."
        )

        current_cf = cfg.get("custom_fields") or []
        cf_default = _format_custom_fields(current_cf)
        cf_text = st.text_area(
            "Campos adicionales",
            value=cf_default,
            height=200,
            key="list_custom_fields",
            label_visibility="collapsed",
            placeholder=(
                "Advisor : María García, Juan Pérez, Carlos López\n"
                "Canal de Venta : Digital, Presencial, Referido\n"
                "Observaciones :"
            ),
        )
        custom_fields_parsed = _parse_custom_fields(cf_text)

        if st.button("Save Lists", type="primary"):
            cfg.save("vehicles", vehicles)
            cfg.save("segments", segments)
            cfg.save("asset_classes", asset_classes)
            cfg.save("countries", countries)
            cfg.save("client_types", client_types)
            cfg.save("profiles", profiles)
            cfg.save("entities", entities)
            cfg.save("jurisdictions", jurisdictions)
            cfg.save("custom_fields", custom_fields_parsed)
            st.success("Classification lists saved successfully.")

        if custom_fields_parsed:
            st.caption(f"**Vista previa** — {len(custom_fields_parsed)} campo(s) personalizado(s):")
            for f in custom_fields_parsed:
                t = "Selector" if f["type"] == "select" else "Texto libre"
                opts = ", ".join(f["options"]) if f["options"] else "—"
                st.caption(f"• **{f['label']}** ({t}): {opts}")
