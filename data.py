import pandas as pd
import streamlit as st
from requirements_presets import PRESETS

def load_ingredients(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    filename = uploaded_file.name.lower()
    try:
        if filename.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif filename.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file, delimiter=';', encoding='latin1')
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, delimiter=';', encoding='utf-8')
        else:
            st.error("Formato de archivo de ingredientes no soportado. Usa .csv o .xlsx")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar ingredientes: {e}")
        return pd.DataFrame()
    df.columns = df.columns.str.strip()  # Limpia espacios en los nombres de columna
    return df

def get_nutrient_list(ingredients_df):
    exclude_cols = ["Ingrediente", "precio", "Materia seca (%)"]
    return [col for col in ingredients_df.columns if col not in exclude_cols]

def get_preset_requirements(especie, etapa):
    """Returns preset nutritional requirements for the given species and stage.

    Returns a dict of the form {nutrient: {"min": float|None, "max": float|None}},
    or an empty dict if no preset exists for the species/stage combination.
    """
    return PRESETS.get(especie, {}).get(etapa, {})
