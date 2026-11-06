"""
Dashboard del Proyecto Final - Programacion Aplicada
=====================================================
Frontend (Streamlit) que consume la API (api.py): lista, filtra, grafica
y permite agregar registros nuevos.

Como ejecutar (en OTRA terminal, con la API ya corriendo):
    streamlit run dashboard.py

La API debe estar activa en http://localhost:8000
"""

import pandas as pd
import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(page_title="Proyecto Final", page_icon="📊", layout="wide")
st.title("📊 Dashboard del Proyecto Final")


# --- Funciones que hablan con la API ---------------------------------------
@st.cache_data(ttl=30)
def listar(campo=None, valor=None, limite=0):
    params = {"limite": limite}
    if campo and valor:
        params.update({"campo": campo, "valor": valor})
    r = requests.get(f"{API}/datos", params=params, timeout=10)
    r.raise_for_status()
    return pd.DataFrame(r.json()["datos"])


@st.cache_data(ttl=30)
def estadisticas(agrupar_por, sumar):
    r = requests.get(
        f"{API}/estadisticas",
        params={"agrupar_por": agrupar_por, "sumar": sumar},
        timeout=10,
    )
    r.raise_for_status()
    return pd.DataFrame(r.json()["grupos"])


# --- Verifica que la API este arriba ---------------------------------------
try:
    df = listar()
except Exception:
    st.error(
        f"No pude conectarme a la API en {API}. "
        f"Revisa que este corriendo:  uvicorn api:app --reload"
    )
    st.stop()

if df.empty:
    st.warning("La coleccion esta vacia.")
    st.stop()

columnas = [c for c in df.columns if c != "_id"]
numericas = df.select_dtypes("number").columns.tolist()

# --- Filtro en la barra lateral --------------------------------------------
st.sidebar.header("Filtros")
campo = st.sidebar.selectbox("Filtrar por campo", ["(todos)"] + columnas)
if campo != "(todos)":
    opciones = sorted(df[campo].dropna().astype(str).unique())
    valor = st.sidebar.selectbox("Valor", opciones)
    df = listar(campo=campo, valor=valor)

# --- Metricas ---------------------------------------------------------------
c1, c2 = st.columns(2)
c1.metric("Registros", len(df))
if numericas:
    # 👈 elige una columna con sentido (p. ej. 'total', no 'venta_id')
    col_metrica = numericas[-1]
    c2.metric(f"Suma de {col_metrica}", int(df[col_metrica].sum()))

# --- Estadisticas (usa la agregacion de la API) ----------------------------
st.subheader("Estadisticas")
categoricas = [c for c in columnas if c not in numericas]
if categoricas and numericas:
    a1, a2 = st.columns(2)
    agrupar = a1.selectbox("Agrupar por", categoricas)
    sumar = a2.selectbox("Sumar", numericas)
    if st.button("Calcular"):
        g = estadisticas(agrupar, sumar)
        st.bar_chart(g.set_index(agrupar)["suma"])
        st.dataframe(g, use_container_width=True)

# --- Tabla de datos ---------------------------------------------------------
st.subheader("Datos")
st.dataframe(df, use_container_width=True)

# --- Agregar un registro (POST a la API) -----------------------------------
st.subheader("➕ Agregar planeta")
with st.form("nuevo"):
    planeta = st.text_input("Nombre del planeta *")
    estrella = st.text_input("Estrella")
    metodo_descubrimiento = st.selectbox(
        "Método de descubrimiento",
        ["Transit", "Radial Velocity", "Microlensing", "Imaging",
         "Transit Timing Variations", "Eclipse Timing Variations",
         "Pulsar Timing", "Orbital Brightness Modulation", "Astrometry"],
    )
    lugar_descubrimiento = st.selectbox("Lugar de descubrimiento", ["Ground", "Space"])
    anio_descubrimiento = st.number_input("Año de descubrimiento", min_value=1989, max_value=2100, value=None, step=1)
    radio_tierras = st.number_input("Radio (Tierras)", min_value=0.0, value=None)
    insolacion_tierra = st.number_input("Insolación (Tierra = 1)", min_value=0.0, value=None)
    distancia_sistema_parsec = st.number_input("Distancia (parsec)", min_value=0.0, value=None)
    temperatura_planeta_k = st.number_input("Temperatura (K)", min_value=0.0, value=None)
    periodo_orbital_dias = st.number_input("Periodo orbital (días)", min_value=0.0, value=None)
    masa_tierras = st.number_input("Masa (Tierras)", min_value=0.0, value=None)
    densidad_planeta = st.number_input("Densidad (g/cm³)", min_value=0.0, value=None)
    enviar = st.form_submit_button("Guardar")

if enviar:
    if not planeta.strip():
        st.error("El nombre del planeta es obligatorio.")
    else:
        payload = {
            "planeta": planeta.strip(),
            "estrella": estrella.strip() or None,
            "metodo_descubrimiento": metodo_descubrimiento,
            "lugar_descubrimiento": lugar_descubrimiento,
            "anio_descubrimiento": int(anio_descubrimiento) if anio_descubrimiento else None,
            "radio_tierras": radio_tierras,
            "insolacion_tierra": insolacion_tierra,
            "distancia_sistema_parsec": distancia_sistema_parsec,
            "temperatura_planeta_k": temperatura_planeta_k,
            "periodo_orbital_dias": periodo_orbital_dias,
            "masa_tierras": masa_tierras,
            "densidad_planeta": densidad_planeta,
        }
        r = requests.post(f"{API}/datos", json=payload, timeout=10)
        if r.ok:
            st.success(f"Guardado con id {r.json()['id']}")
            st.cache_data.clear()  # refresca la tabla
        else:
            st.error(f"Error de la API: {r.text}")

# === NUEVO (IA): pregúntale a tus datos ====================================
st.subheader("🤖 Pregúntale a tus datos")
pregunta = st.text_input("Escribe tu pregunta (ej. ¿cuál sucursal vendió más?)")
if st.button("Preguntar") and pregunta:
    with st.spinner("Pensando..."):
        r = requests.post(f"{API}/preguntar", json={"pregunta": pregunta}, timeout=120)
    if r.ok:
        st.success(r.json()["respuesta"])
    else:
        st.error(f"Error: {r.text}")
# === FIN NUEVO (IA) ========================================================
