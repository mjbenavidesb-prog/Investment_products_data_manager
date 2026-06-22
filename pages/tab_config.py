import streamlit as st
import backend.config as cfg
from backend.database import reseed_from_csv


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
                value=cfg.get("company_name") or "My Company",
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

    # ── Database section ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Database")
    st.caption(
        "Si actualizaste el CSV o hay valores incorrectos (cupones en 0, barreras mal), "
        "usa este botón para borrar la base y re-importar desde el CSV."
    )
    if st.button("Reseed Database from CSV", type="secondary"):
        with st.spinner("Borrando base y re-importando..."):
            result = reseed_from_csv()
        if result:
            st.success("Base re-importada correctamente desde el CSV.")
            st.rerun()
        else:
            st.error("No se encontró el archivo CSV en data/. Colócalo ahí primero.")

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

        if st.button("Save Lists", type="primary"):
            cfg.save("vehicles", vehicles)
            cfg.save("segments", segments)
            cfg.save("asset_classes", asset_classes)
            cfg.save("countries", countries)
            cfg.save("client_types", client_types)
            cfg.save("profiles", profiles)
            cfg.save("entities", entities)
            cfg.save("jurisdictions", jurisdictions)
            st.success("Classification lists saved successfully.")
