# ======================== BLOQUE 1: IMPORTS Y UTILIDADES ========================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
from datetime import date
from data import load_ingredients, get_nutrient_list, get_preset_requirements
from optimization import DietFormulator

# ======================== BLOQUE 2: ESTILO Y LOGO CON BARRA LATERAL (IGUAL A "PETS") ========================
st.set_page_config(page_title="Formulador UYWA Premium", layout="wide")

st.markdown("""
    <style>
    html, body, .stApp, .block-container {
        background: linear-gradient(120deg, #ffffff 0%, #eef4fc 100%) !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #2C3E50 !important;
        color: #fff !important;
    }
    section[data-testid="stSidebar"] * {
        color: #fff !important;
    }

    .stButton > button {
        background-color: #2176ff;
        color: #fff !important;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem !important;
    }
    .stButton > button:hover {
        background-color: #1254d1;
        color: #fff !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2) !important;
    }

    .block-container {
        padding: 2rem 4rem;
    }

    .stNumberInput, .stSelectbox, .stTextInput {
        background-color: #eef4fc !important;
        border-radius: 4px;
        border: 1px solid #d4e4fc !important;
        padding: 0.5rem;
    }

    footer {visibility: hidden !important;}

    /* Opcional: sidebar un poco más angosto */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"][aria-expanded="true"]{
        width: 18.5rem !important;
        min-width: 18.5rem !important;
        max-width: 18.5rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# ======================== BLOQUE 3: LOGIN ========================
from auth import USERS_DB

def login():
    st.title("Iniciar sesión")
    username = st.text_input("Usuario", key="usuario_login")
    password = st.text_input("Contraseña", type="password", key="password_login")

    if st.button("Entrar", key="entrar_login"):
        user = USERS_DB.get(username.strip().lower())
        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["usuario"] = username.strip()
            st.session_state["user"] = user
            st.success(f"Bienvenido, {user['name']}!")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

    if not st.session_state.get("logged_in", False):
        st.stop()

if not st.session_state.get("logged_in", False):
    login()

# ======================== SIDEBAR ÚNICO (después de login) ========================
user = st.session_state.get("user", None)

with st.sidebar:
    st.image("assets/logo.png", use_container_width=True)

    st.markdown(
        """
        <div style="text-align:center;margin-bottom:20px;">
            <h1 style="font-family:Montserrat,sans-serif;margin:0;color:#fff;">UYWA Nutrition</h1>
            <p style="font-size:14px;margin:0;color:#fff;">Nutrición de Precisión Basada en Evidencia</p>
            <br>
            <hr style="border:1px solid #fff;">
            <p style="font-size:13px;color:#fff;margin:0;">📧 uywasas@gmail.com</p>
            <p style="font-size:11px;color:#fff;margin:0;">Derechos reservados © 2026</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if user:
        st.success("Acceso premium activado" if user.get("premium", False) else "Acceso estándar activado")
    else:
        st.warning("Por favor, inicia sesión.")
        
# ======================== BLOQUE 3.2: IDENTIDAD DE USUARIO EN MAIN ========================
USER_KEY = f"uywa_req_{st.session_state['usuario']}"
st.markdown(
    f"<div style='text-align:right'>👤 Usuario: <b>{st.session_state['usuario']}</b></div>",
    unsafe_allow_html=True
)

# ======================== BLOQUE 4: UTILIDADES DE SESIÓN ========================
def safe_float(val, default=0.0):
    """Convierte string con coma o punto decimal a float."""
    try:
        if isinstance(val, str):
            val = val.replace(",", ".")
        return float(val)
    except Exception:
        return default

def render_progress_bar(min_val, max_val, obtenido, width=12):
    """
    Genera visualización de progreso con emoji + porcentaje.
    Retorna (emoji_pct, pct_text).
    """
    if min_val == 0 and max_val == 0:
        return "—", "—"

    # Calcular porcentaje respecto a mínimo
    if min_val > 0:
        pct = (obtenido / min_val) * 100
    elif max_val > 0:
        pct = (obtenido / max_val) * 100
    else:
        pct = 100

    # Determinar emoji según estado
    if abs(pct - 100) < 1:  # Cumple exacto (99-101%)
        emoji = "✅"
    elif pct < 100:  # Por debajo del mínimo
        emoji = "❌"
    else:  # Por encima del mínimo
        emoji = "⚠️"

    # Formato: "✅ 100%"
    pct_text = f"{pct:.1f}%"
    progreso_visual = f"{emoji} {pct_text}"

    return progreso_visual, pct_text


def calculate_shadow_impact(shadow_price, total_cost):
    """Convierte shadow price a % del costo total y clasifica impacto."""
    if shadow_price is None:
        return "—", "—"
    if total_cost == 0:
        return "—", "—"
    impact_pct = (abs(shadow_price) / total_cost) * 100
    if impact_pct > 5:
        impacto = "🔴 Alto"
    elif impact_pct >= 1:
        impacto = "🟠 Medio"
    else:
        impacto = "🟢 Bajo"
    return f"{impact_pct:.1f}%", impacto



def get_gradient_color(index, total):
    """
    Calcula color gradiente azul según posición.
    Oscuro (índice 0) → Claro (índice total-1)
    """
    gradiente = [
        "#1f3a93",  # Azul oscuro (0-20%)
        "#2e5ca6",  # Azul medio (20-40%)
        "#4a7db8",  # Azul claro (40-60%)
        "#7da8d4",  # Azul muy claro (60-80%)
        "#c0d9ed",  # Gris azulado claro (80-100%)
    ]

    posicion = 0
    if total > 1:
        posicion = int((index / (total - 1)) * (len(gradiente) - 1))
    posicion = min(posicion, len(gradiente) - 1)

    return gradiente[posicion]


def clean_state(keys_prefix, valid_names):
    for key in list(st.session_state.keys()):
        for prefix in keys_prefix:
            if key.startswith(prefix):
                found = False
                for n in valid_names:
                    if key.endswith(f"{n}_incl_input") or key.endswith(f"{n}_input"):
                        found = True
                        break
                if not found:
                    del st.session_state[key]

# ======================== BLOQUE 5: TITULO Y TABS PRINCIPALES ========================
st.title("Gestión y Análisis de Dietas")

tabs = st.tabs(["Formulación", "Resultados", "Gráficos", "Comparar Escenarios"])

# ======================== BLOQUE 6: TAB FORMULACIÓN CON RATIOS Y BORRADO INDIVIDUAL ========================
with tabs[0]:
    st.header("Formulación de Dieta")

    # ---- 6.1 Carga de ingredientes ----
    ingredientes_file = st.file_uploader("Matriz de ingredientes (.csv o .xlsx)", type=["csv", "xlsx"])
    ingredientes_df = load_ingredients(ingredientes_file)

    # ====== 6.1.1 LIMPIEZA Y CONVERSIÓN DE DATOS DE INGREDIENTES (intermedio) ======
    if ingredientes_df is not None and not ingredientes_df.empty:
        ingredientes_df = ingredientes_df.replace('.', 0)
        nutr_cols = [
            'EMA_POLLIT', 'EMA_AVES', 'PB', 'EE', 'FB', 'Materia seca (%)', 'LYS_DR', 'MET_DR', 'M+C_DR',
            'THR_DR', 'TRP_DR', 'ILE_DR', 'VAL_DR', 'ARG_DR', 'Ca', 'P', 'Pdisp.AVES',
            'Na', 'K', 'Zn', 'Cu', 'Mn', 'Fe', 'S', 'Vit. E', 'Colina', 'Biotina', 'precio'
        ]
        for col in nutr_cols:
            if col in ingredientes_df.columns:
                ingredientes_df[col] = pd.to_numeric(ingredientes_df[col], errors='coerce').fillna(0)

    ingredientes_sel = []
    ingredientes_df_filtrado = pd.DataFrame()
    min_limits = {}
    max_limits = {}

    if ingredientes_df is not None and not ingredientes_df.empty:
        st.subheader("Selecciona ingredientes para formular")
        ingredientes_disp = ingredientes_df["Ingrediente"].tolist()
        ingredientes_sel = st.multiselect(
            "Buscar y selecciona ingredientes",
            ingredientes_disp,
            default=[],
            help="Elige solo los ingredientes que deseas usar en la dieta.",
            key="ingredientes_sel"
        )

        ingredientes_sel = list(dict.fromkeys(ingredientes_sel))  # Elimina duplicados
        clean_state(["min_", "max_"], ingredientes_sel)

        st.subheader("¿Deseas limitar inclusión de algún ingrediente?")
        ingredientes_a_limitar = st.multiselect(
            "Solo estos ingredientes tendrán límites min/max:",
            ingredientes_sel,
            default=[],
            help="El resto se formulará libremente.",
            key="ingredientes_a_limitar"
        )

        ingredientes_a_limitar = list(dict.fromkeys(ingredientes_a_limitar))
        clean_state(["min_", "max_"], ingredientes_a_limitar)

        # ======================== BLOQUE 6.2: Límites de inclusión por ingrediente ========================
        if ingredientes_a_limitar:
            with st.expander("Límites de inclusión por ingrediente (%)", expanded=True):
                head_cols = st.columns([2, 1, 1])
                with head_cols[0]:
                    st.markdown("**Ingrediente**")
                with head_cols[1]:
                    st.markdown("**Max**")
                with head_cols[2]:
                    st.markdown("**Min (opcional)**")
                min_limits = {}
                max_limits = {}
                for ing in ingredientes_a_limitar:
                    cols = st.columns([2, 1, 1])
                    with cols[0]:
                        st.markdown(ing)
                    with cols[1]:
                        key_max = f"ingrediente_max_{ing}"
                        max_val = st.number_input(
                            label="",
                            min_value=0.0,
                            max_value=100.0,
                            key=key_max,
                            format="%.2f",
                            help="Valor máximo requerido (%)"
                        )
                    with cols[2]:
                        key_min = f"ingrediente_min_{ing}"
                        min_placeholder = "Opcional: ingresa valor mínimo si aplica"
                        min_val_raw = st.text_input(
                            label="",
                            value="",
                            key=key_min,
                            help=min_placeholder,
                            placeholder=min_placeholder
                        )
                        min_val = safe_float(min_val_raw, 0)
                    min_limits[ing] = min_val
                    max_limits[ing] = safe_float(max_val, 0)
                    st.session_state[f"min_{ing}"] = min_val
                    st.session_state[f"max_{ing}"] = safe_float(max_val, 0)

        # ---- 6.3 Edición de ingredientes seleccionados ----
        if ingredientes_sel:
            with st.expander("Ver/editar composición de ingredientes seleccionados"):
                df_edit = ingredientes_df[ingredientes_df["Ingrediente"].isin(ingredientes_sel)].copy()
                key_editor = "ingredientes_editor_" + "_".join([str(e).replace(" ", "_") for e in ingredientes_sel])
                # Formatea todas las columnas numéricas a 2 decimales antes de mostrar
                for col in df_edit.select_dtypes(include=['float', 'int']).columns:
                    df_edit[col] = df_edit[col].round(2)
                df_edit = st.data_editor(
                    df_edit,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=key_editor
                )
            ingredientes_df_filtrado = df_edit.copy()
        else:
            ingredientes_df_filtrado = pd.DataFrame()

        # ---- 6.4 Selección de especie y etapa ----
        st.subheader("Configura los requerimientos nutricionales")
        especies = ["Aves", "Cerdos", "Rumiantes"]
        etapa_default = {
            "Aves": ["Broiler Iniciación", "Broiler Crecimiento", "Broiler Cebo", "Broiler Acabado"],
            "Cerdos": ["Crecimiento", "Engorde", "Reproductoras"],
            "Rumiantes": ["Terneros", "Vacas lecheras", "Vacas secas"]
        }
        col1, col2 = st.columns(2)
        with col1:
            especie = st.selectbox("Especie", especies, key="especie_selectbox")
        with col2:
            etapas_opciones = etapa_default.get(especie, [])
            etapa = st.selectbox("Etapa", etapas_opciones + ["Otra"], key="etapa_selectbox")
            if etapa == "Otra":
                etapa = st.text_input("Ingrese nombre de la etapa", key="etapa_input")

        # ---- 6.4.1 PASO 2: Botón para precargar nutrientes del preset ----
        if etapa and etapa != "Otra":
            _presets_step2 = get_preset_requirements(especie, etapa)
            _nutrientes_posibles_step2 = get_nutrient_list(ingredientes_df) if not ingredientes_df.empty else []
            if _presets_step2 and _nutrientes_posibles_step2:
                _nutrientes_en_preset = [n for n in _presets_step2.keys() if n in _nutrientes_posibles_step2]
                if _nutrientes_en_preset:
                    if st.button(
                        f"📋 Cargar nutrientes del preset para {especie} – {etapa}",
                        key="btn_cargar_nutrientes_preset"
                    ):
                        # Solo cargar nutrientes SIN valores
                        st.session_state["nutrientes_seleccionados"] = _nutrientes_en_preset
                        st.session_state["nutrientes_seleccionados_key"] = _nutrientes_en_preset

                        # Forzar limpiar cualquier valor previo (siempre Min/Max = 0)
                        for nutriente in _nutrientes_en_preset:
                            st.session_state[f"nutriente_min_{nutriente}"] = 0.0
                            st.session_state[f"nutriente_max_{nutriente}"] = 0.0

                        st.success(f"✅ Se preseleccionaron {len(_nutrientes_en_preset)} nutrientes SIN valores. Presiona 'Cargar requerimientos' para cargar valores del preset.")
                        st.rerun()

        # ---- 6.5 Selección de nutrientes ----
        nutrientes_posibles = get_nutrient_list(ingredientes_df) if not ingredientes_df.empty else []
        nutrientes_preseleccionados = st.session_state.get("nutrientes_seleccionados", [])
        nutrientes_seleccionados = st.multiselect(
            "Nutrientes a considerar en la formulación",
            nutrientes_posibles,
            default=nutrientes_preseleccionados,  # Solo usa preseleccionados, NO autocarga primeros 8
            key="nutrientes_seleccionados_key",
            help="Selecciona los nutrientes a optimizar. Usa el botón de arriba para cargar desde el preset."
        )
        nutrientes_seleccionados = list(dict.fromkeys(nutrientes_seleccionados))
        st.session_state["nutrientes_seleccionados"] = nutrientes_seleccionados
        clean_state(["min_", "max_"], nutrientes_seleccionados)

        # ---- 6.5.1 PASO 4: Botón para cargar valores de requerimientos ----
        if etapa and etapa != "Otra" and nutrientes_seleccionados:
            presets_disponibles = get_preset_requirements(especie, etapa)
            nutrientes_con_preset = [n for n in nutrientes_seleccionados if n in presets_disponibles]
            if nutrientes_con_preset:
                if st.button(
                    f"🔢 Cargar requerimientos preestablecidos ({len(nutrientes_con_preset)} nutrientes)",
                    key="btn_cargar_presets_valores"
                ):
                    for nutriente in nutrientes_con_preset:
                        preset = presets_disponibles[nutriente]
                        if preset.get("min") is not None:
                            st.session_state[f"nutriente_min_{nutriente}"] = float(preset["min"])
                        if preset.get("max") is not None:
                            st.session_state[f"nutriente_max_{nutriente}"] = float(preset["max"])
                    st.success(f"✅ Se cargaron {len(nutrientes_con_preset)} requerimientos con valores del preset")
                    st.rerun()

        # ---- 6.6.2 CARGA DE REQUERIMIENTOS DESDE CSV (ANTES de los inputs) ----
        uploaded_req = st.file_uploader(
            "⬆️ Cargar requerimientos desde archivo (CSV)",
            type=["csv"],
            key="uploader_requerimientos"
        )
        if uploaded_req is not None:
            try:
                df_req = pd.read_csv(uploaded_req)
                required_cols = {"especie", "etapa", "nutriente", "min_value"}
                if not required_cols.issubset(set(df_req.columns)):
                    st.error(f"❌ El archivo CSV debe contener las columnas: {', '.join(required_cols)}")
                else:
                    cargados = 0
                    for _, row in df_req.iterrows():
                        nutriente = str(row["nutriente"])
                        if nutriente in nutrientes_seleccionados:
                            try:
                                st.session_state[f"nutriente_min_{nutriente}"] = float(row["min_value"])
                                cargados += 1
                            except (ValueError, TypeError):
                                pass
                    st.success(f"✅ Se cargaron {cargados} requerimientos desde el archivo")
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")

        # ---- 6.6 TABLA UNIFICADA: INPUTS + ANÁLISIS EN VIVO ----
        st.subheader("Requerimientos Nutricionales")
        st.write("Edita Min/Max en la tabla. Las columnas Obtenido, Progreso y Shadow Price se actualizan en vivo.")

        # ---- PASO 1: Leer estado actual (puede ser viejo o nuevo) ----
        req_preview = {}
        for nutriente in nutrientes_seleccionados:
            min_val = safe_float(st.session_state.get(f"nutriente_min_{nutriente}", 0), 0)
            max_raw = st.session_state.get(f"nutriente_max_{nutriente}", 0)
            max_val = safe_float(max_raw, 0) if pd.notna(max_raw) else 0
            req_preview[nutriente] = {"min": min_val, "max": max_val}

        # Obtener estado actual de req_input (para después de guardar)
        nutrientes_data = st.session_state.get("req_input", {})
        for nutriente in nutrientes_seleccionados:
            if nutriente not in nutrientes_data:
                nutrientes_data[nutriente] = {"min": 0, "max": 0}

        # ---- PASO 2: Calcular preview con datos actualizados ----
        preview_result_table = {"success": False}
        if (ingredientes_df_filtrado is not None and not ingredientes_df_filtrado.empty and
            nutrientes_seleccionados and len(nutrientes_seleccionados) > 0):
            try:
                preview_formulator_table = DietFormulator(
                    ingredientes_df_filtrado,
                    nutrientes_seleccionados,
                    req_preview,
                    min_limits,
                    max_limits,
                    ratios=st.session_state.get("ratios", [])
                )
                preview_result_table = preview_formulator_table.solve()
                preview_nutrition_table = preview_result_table.get("nutritional_values", {}) if preview_result_table.get("success") else {}
            except Exception:
                preview_result_table = {"success": False}
                preview_nutrition_table = {}
        else:
            preview_nutrition_table = {}

        shadow_prices_preview = preview_result_table.get("shadow_prices", {}) if preview_result_table.get("success") else {}
        preview_cost_table = preview_result_table.get("cost", 0) if preview_result_table.get("success") else 0

        # ---- PASO 3: Construir tabla con datos frescos y columna Limitante ----
        nutrientes_table_data = []
        for nutriente in nutrientes_seleccionados:
            min_val = req_preview.get(nutriente, {}).get("min", 0)
            max_val = req_preview.get(nutriente, {}).get("max", 0)
            obtenido = safe_float(preview_nutrition_table.get(nutriente, 0), 0)

            bar_visual, pct_text = render_progress_bar(min_val, max_val, obtenido)

            shadow_price = shadow_prices_preview.get(nutriente, None) if min_val != 0 else None
            shadow_pct, impacto = calculate_shadow_impact(shadow_price, preview_cost_table)

            # Calcular brecha
            brecha_text = "—"
            if min_val > 0 and obtenido < min_val:
                brecha_val = min_val - obtenido
                brecha_text = f"❌ FALTA {brecha_val:.2f}"
            elif max_val > 0 and obtenido > max_val:
                brecha_val = obtenido - max_val
                brecha_text = f"⚠️ EXCESO {brecha_val:.2f}"

            # Determinar si este nutriente es el factor limitante
            limitante_text = "—"
            if preview_result_table.get("success"):
                if min_val > 0 and obtenido < min_val:
                    brecha_pct = (obtenido / min_val * 100) if min_val > 0 else 0
                    if brecha_pct < 50:
                        limitante_text = "🔴 BLOQUEA"
                    elif brecha_pct < 85:
                        limitante_text = "🟡 Crítico"
                    else:
                        limitante_text = "🟠 Bajo"
                elif max_val > 0 and obtenido > max_val:
                    limitante_text = "⚠️ EXCESO"
                elif min_val > 0 or max_val > 0:
                    limitante_text = "🟢 OK"

            nutrientes_table_data.append({
                "Nutriente": nutriente,
                "Min": min_val,
                "Max": max_val if max_val > 0 else None,
                "Obtenido": obtenido,
                "% Logrado": bar_visual,
                "Brecha": brecha_text,
                "Limitante": limitante_text,
                "Impacto": impacto
            })

        # ---- PASO 4: Renderizar formulario con datos actualizados ----
        with st.form(key="form_nutrientes_unificada"):
            df_nutrients_unified = st.data_editor(
                pd.DataFrame(nutrientes_table_data),
                use_container_width=True,
                hide_index=True,
                key="nutrientes_editor_unified",
                column_config={
                    "Nutriente": st.column_config.TextColumn("Nutriente", disabled=True, width=130),
                    "Min": st.column_config.NumberColumn("Min", min_value=0.0, format="%.2f", width=90),
                    "Max": st.column_config.NumberColumn("Max (opt)", min_value=0.0, format="%.2f", width=100),
                    "Obtenido": st.column_config.NumberColumn("Obtenido", format="%.2f", disabled=True, width=110),
                    "% Logrado": st.column_config.TextColumn("% Logrado", disabled=True, width=100),
                    "Brecha": st.column_config.TextColumn("Brecha", disabled=True, width=120),
                    "Limitante": st.column_config.TextColumn("Limitante", disabled=True, width=120),
                    "Impacto": st.column_config.TextColumn("Impacto", disabled=True, width=90),
                }
            )

            btn_guardar = st.form_submit_button(
                "💾 Guardar cambios en requerimientos",
                type="primary"
            )

        # ---- PASO 5: Guardar cambios en session_state ----
        if btn_guardar:
            nutrientes_data = {}
            for _, row in df_nutrients_unified.iterrows():
                nut = row["Nutriente"]
                min_v = safe_float(row["Min"], 0) if pd.notna(row["Min"]) else 0
                max_v = safe_float(row["Max"], 0) if pd.notna(row["Max"]) else 0

                st.session_state[f"nutriente_min_{nut}"] = min_v
                st.session_state[f"nutriente_max_{nut}"] = max_v
                st.session_state[f"min_{nut}"] = min_v
                st.session_state[f"max_{nut}"] = max_v
                nutrientes_data[nut] = {"min": min_v, "max": max_v}

            req_input = nutrientes_data
            st.session_state["req_input"] = req_input
            st.success("✅ Cambios guardados exitosamente")
        else:
            req_input = nutrientes_data

        # ---- 6.6.1 DESCARGA DE REQUERIMIENTOS (CSV) ----
        if nutrientes_seleccionados and etapa and etapa != "Otra" and nutrientes_data:
            especie_slug = especie.lower().replace(" ", "_")
            etapa_slug = etapa.lower().replace(" ", "_").replace("ó", "o").replace("é", "e").replace("í", "i")
            fecha_hoy = date.today().strftime("%Y%m%d")
            csv_buffer = io.StringIO()
            csv_buffer.write("especie,etapa,nutriente,min_value\n")
            for nutriente, vals in nutrientes_data.items():
                min_v = vals.get("min", 0) or 0
                csv_buffer.write(f"{especie_slug},{etapa_slug},{nutriente},{min_v}\n")
            csv_content = csv_buffer.getvalue()
            st.download_button(
                label="⬇️ Descargar requerimientos editados (CSV)",
                data=csv_content,
                file_name=f"requerimientos_{especie_slug}_{etapa_slug}_{fecha_hoy}.csv",
                mime="text/csv",
                key="btn_descargar_requerimientos"
            )

        # ---- Vista Previa: Ingredientes y Cumplimiento ----
        if (ingredientes_df_filtrado is not None and not ingredientes_df_filtrado.empty and
            nutrientes_seleccionados and len(nutrientes_seleccionados) > 0 and preview_result_table.get("success")):

            st.markdown("---")
            st.subheader("📊 Vista Previa: Ingredientes y Cumplimiento")

            preview_diet = preview_result_table.get("diet", {})
            preview_cost = preview_result_table.get("cost", 0)

            # ---- Ingredientes en la Fórmula (Barras Gradiente) ----
            with st.expander("🔹 Ingredientes en la Fórmula", expanded=True):
                ing_list_sorted = sorted(preview_diet.items(), key=lambda x: x[1], reverse=True)
                total_ings = len(ing_list_sorted)

                ing_costos = {}
                for ing, pct in ing_list_sorted:
                    if "Ingrediente" in ingredientes_df_filtrado.columns and ing in ingredientes_df_filtrado["Ingrediente"].values:
                        precio = ingredientes_df_filtrado[ingredientes_df_filtrado["Ingrediente"] == ing]["precio"].values[0]
                        costo_aportado = (precio * pct / 100) * 10  # precio por kg × inclusión × 10 = costo por 100 kg / 10
                        ing_costos[ing] = costo_aportado
                    else:
                        ing_costos[ing] = 0

                for idx, (ing, pct) in enumerate(ing_list_sorted):
                    color = get_gradient_color(idx, total_ings)
                    costo = ing_costos.get(ing, 0)
                    # Use dark text on lighter bars for sufficient contrast
                    text_color = "#2C3E50" if idx >= (total_ings - 1) * 0.6 else "white"

                    st.markdown(
                        f"""
                        <div style='margin-bottom: 12px;'>
                            <div style='display: flex; justify-content: space-between; margin-bottom: 4px;'>
                                <span style='font-weight: bold; color: #2C3E50;'>{ing}</span>
                                <span style='color: #666; font-size: 13px;'>{pct:.2f}% | ${costo:.2f}</span>
                            </div>
                            <div style='background-color: #e8eef5; border-radius: 4px; height: 24px; overflow: hidden;'>
                                <div style='background-color: {color}; width: {pct}%; height: 100%; border-radius: 4px; 
                                            display: flex; align-items: center; justify-content: flex-end; padding-right: 8px;
                                            color: {text_color}; font-size: 12px; font-weight: bold;'>
                                    {pct:.1f}%
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)

            cumplidos = 0
            for nut in nutrientes_seleccionados:
                min_val = nutrientes_data.get(nut, {}).get("min", 0)
                max_val = nutrientes_data.get(nut, {}).get("max", 0)
                obtenido = preview_nutrition_table.get(nut, 0)
                if not ((min_val > 0 and obtenido < min_val) or (max_val > 0 and obtenido > max_val)):
                    cumplidos += 1

            total_nut = len(nutrientes_seleccionados)
            pct_general = (cumplidos / total_nut) * 100 if total_nut > 0 else 0

            with col1:
                st.metric("💰 Costo", f"${preview_cost:.2f}", "por 100 kg")

            with col2:
                st.metric("✅ Nutrientes OK", f"{cumplidos}/{total_nut}")

            with col3:
                st.metric("📈 Cumplimiento", f"{pct_general:.1f}%")

            with col4:
                st.metric("📊 Ingredientes", f"{len(ing_list_sorted)}")

        # ---- 6.7 SUBAPARTADO DE RATIOS ENTRE NUTRIENTES ----
        st.subheader("Restricciones adicionales: Ratios entre nutrientes")
        if "ratios" not in st.session_state:
            st.session_state["ratios"] = []

        # Opciones de operadores disponibles
        operadores = {
            "=": "Igual a",
            "<=": "Menor o igual que",
            ">=": "Mayor o igual que",
            "<": "Menor que",
            ">": "Mayor que"
        }

        with st.expander("Agregar restricción de ratio entre nutrientes", expanded=False):
            cols_ratio = st.columns([2, 2, 1, 2, 1])
            with cols_ratio[0]:
                nutr_a = st.selectbox("Nutriente numerador", nutrientes_seleccionados, key="ratio_nutr_a")
            with cols_ratio[1]:
                nutr_b = st.selectbox("Nutriente denominador", nutrientes_seleccionados, key="ratio_nutr_b")
            with cols_ratio[2]:
                operador = st.selectbox("Operador", list(operadores.keys()), format_func=lambda x: operadores[x], key="ratio_operador")
            with cols_ratio[3]:
                valor = st.number_input("Valor del ratio", min_value=0.0, max_value=1000.0, value=1.0, step=0.01, key="ratio_valor")
            with cols_ratio[4]:
                agregar = st.button("Agregar ratio", key="btn_agregar_ratio")

            if agregar:
                if nutr_a != nutr_b:
                    nueva_restriccion = {
                        "numerador": nutr_a,
                        "denominador": nutr_b,
                        "operador": operador,
                        "valor": valor
                    }
                    st.session_state["ratios"].append(nueva_restriccion)
                else:
                    st.warning("El numerador y denominador deben ser diferentes.")

        # Mostrar ratios agregados con opción de borrado individual
        if st.session_state["ratios"]:
            st.markdown("**Ratios de nutrientes definidos:**")
            ratios_a_borrar = []
            for i, ratio in enumerate(st.session_state["ratios"]):
                cols_ratio_disp = st.columns([5, 1])
                with cols_ratio_disp[0]:
                    st.write(
                        f"{ratio['numerador']} / {ratio['denominador']} {ratio['operador']} {ratio['valor']}",
                        key=f"ratio_{i}_display"
                    )
                with cols_ratio_disp[1]:
                    if st.button("🗑️ Eliminar", key=f"eliminar_ratio_{i}"):
                        ratios_a_borrar.append(i)
            # Borrado fuera del loop para evitar problemas de reindexación
            if ratios_a_borrar:
                for idx in sorted(ratios_a_borrar, reverse=True):
                    st.session_state["ratios"].pop(idx)

        # ---- 6.8 Guardado seguro para diagnóstico en resultados ----
        if not ingredientes_df_filtrado.empty:
            st.session_state["ingredients_df"] = ingredientes_df_filtrado.copy()
        elif not ingredientes_df.empty:
            st.session_state["ingredients_df"] = ingredientes_df.copy()

        # ---- 6.9 Formulable y botón ----
        formulable = not ingredientes_df_filtrado.empty and nutrientes_seleccionados

        def is_zero(val):
            try:
                f = float(val)
                return abs(f) < 1e-8
            except Exception:
                return True

        if formulable and all(is_zero(v.get("min", 0)) and is_zero(v.get("max", 0)) for v in req_input.values()):
            st.warning("¡Advertencia! No hay restricciones nutricionales activas. La fórmula resultante puede ser solo el ingrediente más barato.")

        if formulable:
            if st.button("Formular dieta óptima"):
                formulator = DietFormulator(
                    ingredientes_df_filtrado,
                    nutrientes_seleccionados,
                    req_input,
                    min_limits,
                    max_limits,
                    ratios=st.session_state.get("ratios", [])
                )
                result = formulator.solve()
                if result["success"]:
                    st.session_state["last_diet"] = result["diet"]
                    st.session_state["last_cost"] = result["cost"]
                    st.session_state["last_nutritional_values"] = result["nutritional_values"]
                    st.session_state["formulacion_result"] = {"success": True}
                    st.success("¡Formulación realizada!")
                else:
                    st.session_state["formulacion_result"] = {"success": False}
                    st.error("No se pudo formular la dieta: " + result.get("message", "Error desconocido"))

        else:
            st.info("Carga los ingredientes, selecciona y edita, luego configura nutrientes para comenzar.")

# ======================== BLOQUE 7: TAB RESULTADOS CON DIAGNÓSTICO Y RATIOS ========================
with tabs[1]:
    st.header("Resultados de la formulación")
    diet = st.session_state.get("last_diet", None)
    total_cost = st.session_state.get("last_cost", 0)
    nutritional_values = st.session_state.get("last_nutritional_values", {})
    req_input = st.session_state.get("req_input", {})
    nutrientes_seleccionados = st.session_state.get("nutrientes_seleccionados", [])
    ingredients_df = st.session_state.get("ingredients_df", None)
    ratios = st.session_state.get("ratios", [])

    def emoji_estado(minimo, maximo, obtenido):
        if pd.isna(obtenido): return ""
        if maximo and obtenido > maximo:
            return "⬆️"
        if minimo and obtenido < minimo:
            return "❌"
        if minimo or maximo:
            return "✅"
        return ""

    def estado_texto(minimo, maximo, obtenido):
        if pd.isna(obtenido): return ""
        if maximo and obtenido > maximo:
            return "Exceso"
        if minimo and obtenido < minimo:
            return "Deficiente"
        if minimo or maximo:
            return "Cumple"
        return "Sin restricción"

    # --- Formato decimales para tablas ---
    def fmt2(x):
        try:
            f = float(x)
            return f"{f:.2f}"
        except Exception:
            return x

    def fmt2_df(df):
        df_fmt = df.copy()
        for c in df_fmt.columns:
            if df_fmt[c].dtype in [np.float64, np.float32, np.int64, np.int32]:
                df_fmt[c] = df_fmt[c].apply(fmt2)
            elif c.startswith('%') or c.lower().startswith('costo') or c.lower().startswith('precio') or c.lower().startswith('aporte'):
                df_fmt[c] = df_fmt[c].apply(fmt2)
        return df_fmt

    if diet:
        st.subheader("Composición óptima de la dieta (%)")
        res_df = pd.DataFrame(list(diet.items()), columns=["Ingrediente", "% Inclusión"])
        st.dataframe(fmt2_df(res_df.set_index("Ingrediente")), use_container_width=True)

        st.markdown(f"<b>Costo total (por 100 kg):</b> ${total_cost:.2f}", unsafe_allow_html=True)
        precio_kg = total_cost / 100 if total_cost else 0
        precio_ton = precio_kg * 1000
        st.metric(label="Precio por kg de dieta", value=f"${precio_kg:,.2f}")
        st.metric(label="Precio por tonelada de dieta", value=f"${precio_ton:,.2f}")

        st.subheader("Composición nutricional de la dieta")

        comp_list = []
        for nut in nutrientes_seleccionados:
            valores = req_input.get(nut, {})
            min_r = valores.get("min", "")
            max_r = valores.get("max", "")
            obtenido = nutritional_values.get(nut, None)
            comp_list.append({
                "Nutriente": nut,
                "Mínimo": min_r if min_r else "",
                "Máximo": max_r if max_r else "",
                "Obtenido": round(obtenido, 2) if obtenido is not None and obtenido != "" else "",
                "Estado": estado_texto(min_r, max_r, obtenido),
                "": emoji_estado(min_r, max_r, obtenido)
            })

        comp_df = pd.DataFrame(comp_list)
        st.dataframe(fmt2_df(comp_df), use_container_width=True)

        # === APARTADO DE CUMPLIMIENTO DE RATIOS ENTRE NUTRIENTES ===
        if ratios:
            st.subheader("Cumplimiento de restricciones de ratios entre nutrientes")
            ratio_rows = []
            for i, ratio in enumerate(ratios):
                num = ratio.get("numerador")
                den = ratio.get("denominador")
                op = ratio.get("operador")
                val = ratio.get("valor")

                num_val = nutritional_values.get(num, None)
                den_val = nutritional_values.get(den, None)
                calculado = None
                cumple = ""
                detalle = ""
                if den_val is not None and den_val != 0:
                    calculado = num_val / den_val
                    calc_str = f"{num_val:.2f} / {den_val:.2f} = {calculado:.2f}"
                    # Evaluación del cumplimiento
                    if op == "=":
                        cumple = abs(calculado - val) < 1e-2
                    elif op == ">=":
                        cumple = calculado >= val - 1e-2
                    elif op == "<=":
                        cumple = calculado <= val + 1e-2
                    elif op == ">":
                        cumple = calculado > val
                    elif op == "<":
                        cumple = calculado < val
                    detalle = f"Calculado: {calc_str}"
                else:
                    cumple = False
                    detalle = f"División por cero (denominador '{den}' = {den_val})"

                cumple_txt = (
                    "✅ Cumple" if cumple else "❌ No cumple"
                )

                ratio_rows.append({
                    "Ratio definido": f"{num} / {den} {op} {val}",
                    "Valor calculado": f"{calculado:.2f}" if calculado is not None else "N/A",
                    "Cumplimiento": cumple_txt,
                    "Detalle": detalle
                })

            ratio_df = pd.DataFrame(ratio_rows)
            st.dataframe(fmt2_df(ratio_df), use_container_width=True)
    else:
        st.warning("No se ha formulado ninguna dieta aún. Realiza la formulación en la pestaña anterior.")

# ======================== BLOQUE AUXILIARES PARA BLOQUE 8 (GRÁFICOS) ========================

def fmt2(x):
    try:
        f = float(x)
        return f"{f:,.2f}"
    except Exception:
        return x

def fmt2_df(df):
    df_fmt = df.copy()
    for c in df_fmt.columns:
        if df_fmt[c].dtype in [np.float64, np.float32, np.int64, np.int32]:
            df_fmt[c] = df_fmt[c].apply(fmt2)
        elif c.startswith('%') or c.lower().startswith('costo') or c.lower().startswith('precio') or c.lower().startswith('aporte'):
            df_fmt[c] = df_fmt[c].apply(fmt2)
    return df_fmt

def get_color_map(ingredientes):
    palette = [
        "#19345c", "#7a9fc8", "#e2b659", "#7fc47f",
        "#ed7a7a", "#c07ad7", "#7ad7d2", "#ffb347",
        "#b7e28a", "#d1a3a4", "#f0837c", "#b2b2b2",
    ]
    return {ing: palette[i % len(palette)] for i, ing in enumerate(ingredientes)}

def unit_selector(label, options, default, key):
    idx = options.index(default) if default in options else 0
    return st.selectbox(label, options, index=idx, key=key)

def get_unit_factor(base_unit, manual_unit):
    conversion = {
        ("kg", "kg"): (1, "kg"),
        ("kg", "ton"): (0.001, "ton"),
        ("g", "g"): (1, "g"),
        ("g", "100g"): (0.01, "100g"),
        ("g", "kg"): (0.001, "kg"),
        ("g", "ton"): (0.000001, "ton"),
        ("kcal", "kcal"): (1, "kcal"),
        ("kcal", "1000kcal"): (0.001, "1000kcal"),
        ("%", "%"): (1, "%"),
        ("%", "100 unidades"): (100, "100 unidades"),
        ("unidad", "unidad"): (1, "unidad"),
        ("unidad", "100 unidades"): (100, "100 unidades"),
        ("unidad", "1000 unidades"): (1000, "1000 unidades"),
        ("unidad", "kg"): (1, "kg"),
        ("unidad", "ton"): (0.001, "ton"),
    }
    return conversion.get((base_unit, manual_unit), (1, manual_unit))

def get_unidades_dict(nutrientes):
    default = "unidad"
    ref = {
        "PB": "kg",
        "EE": "kg",
        "FB": "kg",
        "EMA_POLLIT": "kcal",
        "LYS_DR": "g",
        "MET_DR": "g",
        "M+C_DR": "g",
    }
    return {nut: ref.get(nut, default) for nut in nutrientes}

def cargar_escenarios():
    if "escenarios_guardados" not in st.session_state:
        st.session_state["escenarios_guardados"] = []
    return st.session_state["escenarios_guardados"]

def guardar_escenarios(escenarios):
    st.session_state["escenarios_guardados"] = escenarios

# ======================== BLOQUE 8: TAB GRÁFICOS DINÁMICOS ========================
with tabs[2]:
    st.header("Gráficos de la formulación")
    diet = st.session_state.get("last_diet", None)
    nutritional_values = st.session_state.get("last_nutritional_values", {})
    req_input = st.session_state.get("req_input", {})
    ingredientes_seleccionados = list(st.session_state.get("last_diet", {}).keys())
    nutrientes_seleccionados = st.session_state.get("nutrientes_seleccionados", [])
    ingredients_df = st.session_state.get("ingredients_df", None)
    total_cost = st.session_state.get("last_cost", 0)
    unidades_dict = get_unidades_dict(nutrientes_seleccionados)

    if diet and ingredients_df is not None and not ingredients_df.empty:
        df_formula = ingredients_df.copy()
        df_formula["% Inclusión"] = df_formula["Ingrediente"].map(diet).fillna(0)
        df_formula["precio"] = df_formula["precio"].fillna(0)
        df_formula = df_formula[df_formula["Ingrediente"].isin(diet.keys())].reset_index(drop=True)
        ingredientes_seleccionados = list(df_formula["Ingrediente"])
        color_map = get_color_map(ingredientes_seleccionados)

        subtab1, subtab2, subtab3 = st.tabs([
            "Costo Total por Ingrediente",
            "Aporte por Ingrediente a Nutrientes",
            "Precio Sombra por Nutriente (Shadow Price)"
        ])

        with subtab1:
            manual_unit = unit_selector(
                "Unidad para mostrar el costo total por ingrediente",
                ['USD/kg', 'USD/ton'],
                'USD/ton',
                key="unit_selector_costototal_tab1"
            )
            factor = 1 if manual_unit == 'USD/kg' else 10  # 1 para USD/kg, 10 para USD/ton a partir de 100 kg base
            label = manual_unit
            costos = [
                float(row["precio"]) * float(row["% Inclusión"]) / 100 * factor
                if pd.notnull(row["precio"]) and pd.notnull(row["% Inclusión"]) else 0
                for _, row in df_formula.iterrows()
            ]
            suma_costos = sum(costos)
            suma_inclusion = sum(df_formula["% Inclusión"])
            proporciones = [
                float(row["% Inclusión"]) * 100 / suma_inclusion if suma_inclusion > 0 else 0
                for _, row in df_formula.iterrows()
            ]
            chart_type = st.radio("Tipo de gráfico", ["Pastel", "Barras"], index=0)
            if chart_type == "Pastel":
                fig_pie = go.Figure(go.Pie(
                    labels=ingredientes_seleccionados,
                    values=costos,
                    marker_colors=[color_map[ing] for ing in ingredientes_seleccionados],
                    hoverinfo="label+percent+value",
                    textinfo="label+percent",
                    hole=0.3
                ))
                fig_pie.update_layout(title="Participación de cada ingrediente en el costo total")
                st.plotly_chart(fig_pie, use_container_width=True, key="chart_cost_pie")
            else:
                fig2 = go.Figure([go.Bar(
                    x=ingredientes_seleccionados,
                    y=costos,
                    marker_color=[color_map[ing] for ing in ingredientes_seleccionados],
                    text=[fmt2(c) for c in costos],
                    textposition='auto',
                    customdata=proporciones,
                    hovertemplate='%{x}<br>Costo: %{y:.2f} ' + label + '<br>Proporción dieta: %{customdata:.2f}%<extra></extra>'
                )])
                fig2.update_layout(
                    xaxis_title="Ingrediente",
                    yaxis_title=f"Costo aportado ({label})",
                    title=f"Costo total aportado por ingrediente ({label})",
                    showlegend=False,
                    template="simple_white"
                )
                st.plotly_chart(fig2, use_container_width=True, key="chart_cost_bar")
            df_costos = pd.DataFrame({
                "Ingrediente": ingredientes_seleccionados,
                f"Costo aportado ({label})": [fmt2(c) for c in costos],
                "% Inclusión": [fmt2(row["% Inclusión"]) for _, row in df_formula.iterrows()],
                "Proporción dieta (%)": [fmt2(p) for p in proporciones],
                "Precio ingrediente (USD/kg)": [fmt2(row["precio"]) for _, row in df_formula.iterrows()],
            })
            st.dataframe(fmt2_df(df_costos), use_container_width=True)
            st.markdown(f"**Costo total de la fórmula:** {fmt2(suma_costos)} {label} (suma de los ingredientes). Puedes cambiar la unidad.")

        with subtab2:
            unit_options = {
                'kg': ['kg', 'ton'],
                'g': ['g', '100g', 'kg', 'ton'],
                'kcal': ['kcal', '1000kcal'],
                '%': ['%', '100 unidades'],
                'unidad': ['unidad', '100 unidades', '1000 unidades', 'kg', 'ton'],
            }
            nut_tabs = st.tabs([nut for nut in nutrientes_seleccionados])
            for i, nut in enumerate(nutrientes_seleccionados):
                with nut_tabs[i]:
                    unit = unidades_dict.get(nut, "unidad")
                    manual_unit = unit_selector(
                        f"Unidad para {nut}",
                        unit_options.get(unit, ["unidad", "100 unidades", "1000 unidades", "kg", "ton"]),
                        unit_options.get(unit, ["unidad"])[0],
                        key=f"unit_selector_{nut}_aporte_tab1"
                    )
                    factor, label = get_unit_factor(unit, manual_unit)
                    valores = []
                    porc_aporte = []
                    total_nut = sum([
                        (float(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) *
                         float(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0]) / 100 * factor)
                        if nut in df_formula.columns and
                           pd.notnull(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) else 0
                        for ing in ingredientes_seleccionados
                    ])
                    for ing in ingredientes_seleccionados:
                        valor = float(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) \
                            if nut in df_formula.columns and pd.notnull(df_formula.loc[df_formula["Ingrediente"] == ing, nut].values[0]) else 0
                        porc = float(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0])
                        aporte = valor * porc / 100 * factor
                        valores.append(aporte)
                        porc_aporte.append(100 * aporte / total_nut if total_nut > 0 else 0)
                    df_aporte = pd.DataFrame({
                        "Ingrediente": ingredientes_seleccionados,
                        f"Aporte de {nut} ({label})": [fmt2(v) for v in valores],
                        "% Inclusión": [fmt2(df_formula[df_formula["Ingrediente"] == ing]["% Inclusión"].values[0]) for ing in ingredientes_seleccionados],
                        "Contenido por kg": [fmt2(df_formula[df_formula["Ingrediente"] == ing][nut].values[0]) if nut in df_formula.columns else "" for ing in ingredientes_seleccionados],
                        f"Proporción aporte {nut} (%)": [fmt2(p) for p in porc_aporte],
                    })
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=ingredientes_seleccionados,
                        y=valores,
                        marker_color=[color_map[ing] for ing in ingredientes_seleccionados],
                        text=[fmt2(v) for v in valores],
                        textposition='auto',
                        customdata=porc_aporte,
                        hovertemplate='%{x}<br>Aporte: %{y:.2f} ' + label + '<br>Proporción aporte: %{customdata:.2f}%<extra></extra>',
                    ))
                    fig.update_layout(
                        xaxis_title="Ingrediente",
                        yaxis_title=f"Aporte de {nut} ({label})",
                        title=f"Aporte de cada ingrediente a {nut} ({label})",
                        template="simple_white"
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_aporte_{nut}")
                    st.dataframe(fmt2_df(df_aporte), use_container_width=True)
                    st.markdown(
                        f"Puedes ajustar la unidad para visualizar el aporte en la escala más útil para tu análisis."
                    )

        with subtab3:
            unit_options = {
                'kg': ['kg', 'ton'],
                'g': ['g', '100g', 'kg', 'ton'],
                'kcal': ['kcal', '1000kcal'],
                '%': ['%', '100 unidades'],
                'unidad': ['unidad', '100 unidades', '1000 unidades', 'kg', 'ton'],
            }
            shadow_tab = st.tabs([nut for nut in nutrientes_seleccionados])
            for idx, nut in enumerate(nutrientes_seleccionados):
                with shadow_tab[idx]:
                    unit = unidades_dict.get(nut, "unidad")
                    manual_unit = unit_selector(
                        f"Unidad para {nut}",
                        unit_options.get(unit, ["unidad", "100 unidades", "1000 unidades", "kg", "ton"]),
                        unit_options.get(unit, ["unidad"])[0],
                        key=f"unit_selector_{nut}_shadow_tab1"
                    )
                    factor, label = get_unit_factor(unit, manual_unit)
                    precios_unit = []
                    contenidos = []
                    precios_ing = []
                    for i, ing in enumerate(ingredientes_seleccionados):
                        row = df_formula[df_formula["Ingrediente"] == ing].iloc[0]
                        contenido = float(row.get(nut, 0))
                        precio = float(row.get("precio", np.nan))
                        if pd.notnull(contenido) and contenido > 0 and pd.notnull(precio):
                            precios_unit.append(precio / contenido * factor)
                        else:
                            precios_unit.append(np.nan)
                        contenidos.append(contenido)
                        precios_ing.append(precio)
                    df_shadow = pd.DataFrame({
                        "Ingrediente": ingredientes_seleccionados,
                        f"Precio por {manual_unit}": [fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                        f"Contenido de {nut} por kg": [fmt2(c) for c in contenidos],
                        "Precio ingrediente (USD/kg)": [fmt2(p) for p in precios_ing],
                    })
                    precios_unit_np = np.array([v if pd.notnull(v) else np.inf for v in precios_unit])
                    if np.all(np.isinf(precios_unit_np)):
                        min_idx = 0  # Valor por defecto si no hay precios válidos
                    else:
                        min_idx = int(np.nanargmin(precios_unit_np))
                    df_shadow["Es el más barato"] = ["✅" if i == min_idx else "" for i in range(len(df_shadow))]
                    bar_colors = ['green' if i == min_idx else 'royalblue' for i in range(len(df_shadow))]
                    fig_shadow = go.Figure()
                    fig_shadow.add_trace(go.Bar(
                        x=df_shadow["Ingrediente"],
                        y=[v if pd.notnull(v) else 0 for v in precios_unit],
                        marker_color=bar_colors,
                        text=[fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                        textposition='auto',
                        customdata=df_shadow["Es el más barato"],
                        hovertemplate=f'%{{x}}<br>Precio sombra: %{{y:.2f}} {label}<br>%{{customdata}}<extra></extra>',
                    ))
                    fig_shadow.update_layout(
                        xaxis_title="Ingrediente",
                        yaxis_title=label,
                        title=f"Precio sombra y costo por ingrediente para {nut}",
                        template="simple_white"
                    )
                    st.plotly_chart(fig_shadow, use_container_width=True, key=f"chart_shadow_{nut}")
                    st.dataframe(fmt2_df(df_shadow), use_container_width=True)
                    st.markdown(
                        f"**El precio sombra de {nut} es el menor costo posible para obtener una unidad de este nutriente usando el ingrediente más barato en la fórmula.**\n\n"
                        f"- Puedes ajustar la unidad para mejorar la visualización.\n"
                        f"- El ingrediente marcado con ✅ aporta el precio sombra."
                    )

        st.markdown("---")
        escenarios = cargar_escenarios()
        nombre_escenario = st.text_input("Nombre para guardar este escenario", value="Escenario " + str(len(escenarios)+1), key="nombre_escenario")
        if st.button("Guardar escenario"):
            escenario = {
                "nombre": nombre_escenario,
                "ingredientes": ingredientes_seleccionados,
                "nutrientes": nutrientes_seleccionados,
                "data_formula": df_formula.to_dict(),
                "unidades_dict": unidades_dict,
                "costo_total": fmt2(total_cost),
            }
            escenarios.append(escenario)
            guardar_escenarios(escenarios)
            st.success(f"Escenario '{nombre_escenario}' guardado exitosamente.")
    else:
        st.info("No hay resultados para graficar. Formula primero una dieta.")

# ======================== BLOQUE 9: COMPARADOR DE ESCENARIOS AVANZADO ========================
with tabs[3]:
    st.header("Comparador de escenarios guardados")

    escenarios = cargar_escenarios()
    if not escenarios:
        st.info("No hay escenarios guardados para comparar.")
    else:
        nombres = [esc["nombre"] for esc in escenarios]
        seleccionados = st.multiselect(
            "Selecciona escenarios para comparar",
            nombres,
            default=nombres[:2] if len(nombres) > 1 else nombres
        )
        esc_sel = [esc for esc in escenarios if esc["nombre"] in seleccionados]

        if esc_sel:
            st.subheader("Comparación de costo total (USD/ton)")
            df_cost = pd.DataFrame({
                esc["nombre"]: [float(esc.get("costo_total", "0").replace(",", ""))] for esc in esc_sel
            })
            df_cost.index = ["Costo total (USD/ton)"]
            st.dataframe(fmt2_df(df_cost), use_container_width=True)

            st.subheader("Comparación de composición de ingredientes (%)")
            ingredientes_all = sorted(set(sum([list(esc["ingredientes"]) for esc in esc_sel], [])))
            data_comp = {}
            for esc in esc_sel:
                df = pd.DataFrame(esc["data_formula"])
                comp = df.set_index("Ingrediente")["% Inclusión"] if "Ingrediente" in df.columns else pd.Series()
                comp = comp.reindex(ingredientes_all).fillna(0)
                data_comp[esc["nombre"]] = comp
            df_comp = pd.DataFrame(data_comp)
            df_comp.index.name = "Ingrediente"
            st.dataframe(fmt2_df(df_comp), use_container_width=True)

            st.subheader("Comparación de perfil nutricional (todos los nutrientes)")
            if 'ingredients_df' in st.session_state and st.session_state['ingredients_df'] is not None:
                nutrientes_posibles = get_nutrient_list(st.session_state['ingredients_df'])
            else:
                nutrientes_posibles = sorted(set(sum([esc["nutrientes"] for esc in esc_sel], [])))
            data_nut = {}
            for esc in esc_sel:
                df = pd.DataFrame(esc["data_formula"])
                nut_vals = pd.Series({nut: df[nut].sum() if nut in df.columns else 0 for nut in nutrientes_posibles})
                data_nut[esc["nombre"]] = nut_vals
            df_nut = pd.DataFrame(data_nut)
            df_nut.index.name = "Nutriente"
            st.dataframe(fmt2_df(df_nut), use_container_width=True)

            st.subheader("Comparación gráfica")
            opciones_grafico = [
                "Costo total por ingrediente",
                *["Aporte de " + nut for nut in nutrientes_posibles],
                *["Precio sombra de " + nut for nut in nutrientes_posibles]
            ]
            grafico_sel = st.selectbox("Selecciona el gráfico a comparar:", opciones_grafico)

            ncols = len(esc_sel)
            cols = st.columns(ncols)
            for idx, esc in enumerate(esc_sel):
                with cols[idx]:
                    st.markdown(f"**{esc['nombre']}**")
                    df_formula = pd.DataFrame(esc["data_formula"])
                    color_map = get_color_map(list(df_formula["Ingrediente"])) if "Ingrediente" in df_formula.columns else {}

                    if grafico_sel == "Costo total por ingrediente":
                        if "precio" in df_formula.columns and "% Inclusión" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            costos = df_formula["precio"] * df_formula["% Inclusión"] / 100 * 10  # USD/ton
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=costos,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(c) for c in costos],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title="Costo aportado (USD/ton)",
                                title="Costo total por ingrediente",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_compare_cost_{idx}")
                        else:
                            st.info("No hay datos suficientes en este escenario.")

                    elif grafico_sel.startswith("Aporte de "):
                        nut = grafico_sel.replace("Aporte de ", "")
                        if nut in df_formula.columns and "% Inclusión" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            valores = df_formula[nut] * df_formula["% Inclusión"] / 100
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=valores,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(v) for v in valores],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title=f"Aporte de {nut}",
                                title=f"Aporte de cada ingrediente a {nut}",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_compare_aporte_{nut}_{idx}")
                        else:
                            st.info("No hay datos suficientes en este escenario.")

                    elif grafico_sel.startswith("Precio sombra de "):
                        nut = grafico_sel.replace("Precio sombra de ", "")
                        if nut in df_formula.columns and "precio" in df_formula.columns and "Ingrediente" in df_formula.columns:
                            precios_unit = []
                            for _, row in df_formula.iterrows():
                                contenido = row.get(nut, 0)
                                precio = row.get("precio", np.nan)
                                if pd.notnull(contenido) and contenido > 0 and pd.notnull(precio):
                                    precios_unit.append(precio / contenido)
                                else:
                                    precios_unit.append(np.nan)
                            fig = go.Figure([go.Bar(
                                x=df_formula["Ingrediente"],
                                y=precios_unit,
                                marker_color=[color_map.get(ing, "#19345c") for ing in df_formula["Ingrediente"]],
                                text=[fmt2(v) if pd.notnull(v) else "" for v in precios_unit],
                                textposition='auto'
                            )])
                            fig.update_layout(
                                xaxis_title="Ingrediente",
                                yaxis_title=f"Precio sombra de {nut} (USD por unidad)",
                                title=f"Precio sombra por ingrediente para {nut}",
                                showlegend=False,
                                template="simple_white"
                            )
                            st.plotly_chart(fig, use_container_width=True, key=f"chart_compare_shadow_{nut}_{idx}")
                        else:
                            st.info("No hay datos suficientes en este escenario.")
