"""
Dashboard del Proyecto Final - Programacion Aplicada
=====================================================
Frontend interactivo que consume la API del proyecto y permite explorar,
filtrar y analizar el catalogo de exoplanetas.
"""

import os

import pandas as pd
import requests
import streamlit as st

API = os.environ.get("API_URL", "https://api-exoplanetas.onrender.com").rstrip("/")

st.set_page_config(page_title="Exoplanetas", page_icon="🪐", layout="wide")
st.title("🪐 Explorador de exoplanetas")
st.caption("Explora el catálogo, compara propiedades y consulta los datos con IA.")


@st.cache_data(ttl=60)
def listar():
    response = requests.get(f"{API}/datos", params={"limite": 0}, timeout=90)
    response.raise_for_status()
    return pd.DataFrame(response.json()["datos"])


try:
    df = listar()
except requests.RequestException as error:
    detail = error.response.text if error.response is not None else str(error)
    st.error(f"No pude cargar los datos desde {API}. Detalle: {detail}")
    st.stop()

if df.empty:
    st.warning("La colección no tiene registros.")
    st.stop()


def opciones_de(columna):
    if columna not in df:
        return []
    return sorted(str(value) for value in df[columna].dropna().unique())


def histograma(data, columna, titulo):
    if columna not in data:
        st.info(f"No hay un campo «{columna}» en los datos.")
        return
    valores = pd.to_numeric(data[columna], errors="coerce").dropna()
    if valores.empty:
        st.info(f"No hay valores disponibles para {titulo.lower()}.")
        return
    bins = min(20, max(1, valores.nunique()))
    conteo = pd.cut(valores, bins=bins, duplicates="drop").value_counts().sort_index()
    conteo.index = conteo.index.map(str)
    st.bar_chart(conteo.rename("Planetas"), height=260)


# --- Filtros ---------------------------------------------------------------
st.sidebar.header("Filtros")
if st.sidebar.button("Limpiar filtros"):
    for key in (
        "filtro_nombre",
        "filtro_metodos",
        "filtro_lugares",
        "filtro_clasificacion",
        "filtro_anios",
        "filtro_radio",
        "filtro_distancia",
    ):
        st.session_state.pop(key, None)
    st.rerun()

buscar = st.sidebar.text_input(
    "Buscar planeta o estrella", key="filtro_nombre", placeholder="Ej. Kepler"
)
metodos = st.sidebar.multiselect(
    "Método de descubrimiento",
    opciones_de("metodo_descubrimiento"),
    key="filtro_metodos",
)
lugares = st.sidebar.multiselect(
    "Lugar de descubrimiento",
    opciones_de("lugar_descubrimiento"),
    key="filtro_lugares",
)

clasificaciones = opciones_de("resultado_tierra")
clasificacion = st.sidebar.selectbox(
    "Clasificación tipo Tierra",
    ["Todas"] + clasificaciones,
    key="filtro_clasificacion",
)

anios = pd.to_numeric(df.get("anio_descubrimiento"), errors="coerce").dropna()
if not anios.empty and anios.min() < anios.max():
    rango_anios = st.sidebar.slider(
        "Año de descubrimiento",
        min_value=int(anios.min()),
        max_value=int(anios.max()),
        value=(int(anios.min()), int(anios.max())),
        key="filtro_anios",
    )
else:
    rango_anios = None

radios = pd.to_numeric(df.get("radio_tierras"), errors="coerce").dropna()
if not radios.empty and radios.min() < radios.max():
    rango_radio = st.sidebar.slider(
        "Radio (veces la Tierra)",
        min_value=float(radios.min()),
        max_value=float(radios.max()),
        value=(float(radios.min()), float(radios.max())),
        step=max((float(radios.max()) - float(radios.min())) / 1000, 0.01),
        key="filtro_radio",
    )
else:
    rango_radio = None

distancias = pd.to_numeric(df.get("distancia_sistema_parsec"), errors="coerce").dropna()
if not distancias.empty and distancias.min() < distancias.max():
    rango_distancia = st.sidebar.slider(
        "Distancia (parsec)",
        min_value=float(distancias.min()),
        max_value=float(distancias.max()),
        value=(float(distancias.min()), float(distancias.max())),
        step=max((float(distancias.max()) - float(distancias.min())) / 1000, 0.01),
        key="filtro_distancia",
    )
else:
    rango_distancia = None

filtrados = df.copy()
if buscar.strip():
    termino = buscar.strip()
    coincide = pd.Series(False, index=filtrados.index)
    for columna in ("planeta", "estrella"):
        if columna in filtrados:
            coincide |= filtrados[columna].astype("string").str.contains(
                termino, case=False, regex=False, na=False
            )
    filtrados = filtrados[coincide]
if metodos:
    filtrados = filtrados[filtrados["metodo_descubrimiento"].astype(str).isin(metodos)]
if lugares:
    filtrados = filtrados[filtrados["lugar_descubrimiento"].astype(str).isin(lugares)]
if clasificacion != "Todas":
    filtrados = filtrados[filtrados["resultado_tierra"] == clasificacion]
if rango_anios:
    valores_anio = pd.to_numeric(filtrados["anio_descubrimiento"], errors="coerce")
    filtrados = filtrados[valores_anio.between(*rango_anios)]
if rango_radio:
    valores_radio = pd.to_numeric(filtrados["radio_tierras"], errors="coerce")
    filtrados = filtrados[valores_radio.between(*rango_radio)]
if rango_distancia:
    valores_distancia = pd.to_numeric(
        filtrados["distancia_sistema_parsec"], errors="coerce"
    )
    filtrados = filtrados[valores_distancia.between(*rango_distancia)]

tab_resumen, tab_catalogo, tab_ia, tab_agregar = st.tabs(
    ["📊 Resumen", "🔎 Catálogo", "🤖 Pregúntale a tus datos", "➕ Agregar planeta"]
)


with tab_resumen:
    estrellas = (
        filtrados["estrella"].nunique()
        if "estrella" in filtrados
        else 0
    )
    candidatos = (
        int(filtrados["candidato_tierra"].eq(True).sum())
        if "candidato_tierra" in filtrados
        else 0
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Planetas en el catálogo", f"{len(df):,}")
    k2.metric("Resultados del filtro", f"{len(filtrados):,}")
    k3.metric("Estrellas distintas", f"{estrellas:,}")
    k4.metric("Candidatos tipo Tierra", f"{candidatos:,}")

    st.subheader("Descubrimientos y características")
    if filtrados.empty:
        st.info("No hay planetas que coincidan con los filtros seleccionados.")
    else:
        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown("**Descubrimientos por año**")
            if "anio_descubrimiento" in filtrados:
                por_anio = (
                    pd.to_numeric(filtrados["anio_descubrimiento"], errors="coerce")
                    .dropna()
                    .astype(int)
                    .value_counts()
                    .sort_index()
                )
                st.line_chart(por_anio.rename("Planetas"), height=280)
        with derecha:
            st.markdown("**Métodos más utilizados**")
            campo_metodo = (
                "metodo_espanol"
                if "metodo_espanol" in filtrados
                else "metodo_descubrimiento"
            )
            por_metodo = (
                filtrados[campo_metodo]
                .dropna()
                .value_counts()
                .head(10)
                .sort_values()
            )
            st.bar_chart(por_metodo.rename("Planetas"), height=280)

        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown("**Lugares de descubrimiento**")
            if "lugar_descubrimiento" in filtrados:
                por_lugar = filtrados["lugar_descubrimiento"].value_counts().sort_values()
                st.bar_chart(por_lugar.rename("Planetas"), height=260)
        with derecha:
            st.markdown("**Distribución del radio planetario**")
            histograma(filtrados, "radio_tierras", "Radio planetario")

        izquierda, derecha = st.columns(2)
        with izquierda:
            st.markdown("**Distribución de masa**")
            histograma(filtrados, "masa_tierras", "Masa")
        with derecha:
            st.markdown("**Distribución de distancia**")
            histograma(filtrados, "distancia_sistema_parsec", "Distancia")


with tab_catalogo:
    st.subheader("Catálogo de planetas")
    st.caption(
        f"Mostrando {len(filtrados):,} resultados filtrados de {len(df):,} registros."
    )
    csv = filtrados.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Descargar resultados filtrados en CSV",
        data=csv,
        file_name="exoplanetas_filtrados.csv",
        mime="text/csv",
    )

    if filtrados.empty:
        st.info("Ajusta los filtros para ver planetas.")
    else:
        pagina_tamano = st.selectbox(
            "Registros por página", [25, 50, 100, 250, 500], index=2
        )
        total_paginas = (len(filtrados) + pagina_tamano - 1) // pagina_tamano
        if total_paginas > 1:
            pagina = st.slider("Página", 1, total_paginas, 1)
        else:
            pagina = 1
        inicio = (pagina - 1) * pagina_tamano
        st.dataframe(
            filtrados.iloc[inicio : inicio + pagina_tamano],
            width="stretch",
            hide_index=True,
        )

        st.markdown("#### Ficha del planeta")
        indices = filtrados.index.tolist()

        def etiqueta_planeta(indice):
            registro = filtrados.loc[indice]
            nombre = registro.get("planeta", "Planeta sin nombre")
            estrella = registro.get("estrella")
            sufijo = f" — {estrella}" if pd.notna(estrella) else ""
            return f"{nombre}{sufijo}"

        seleccionado = st.selectbox(
            "Selecciona un planeta",
            indices,
            format_func=etiqueta_planeta,
        )
        registro = filtrados.loc[seleccionado].drop(labels=["_id"], errors="ignore")
        detalle = registro[registro.notna()].astype(str).to_frame(name="Valor")
        st.dataframe(detalle, width="stretch")


with tab_ia:
    st.subheader("Pregúntale al catálogo completo")
    st.caption(
        "La IA recibe estadísticas de toda la colección, rankings y una pequeña "
        "muestra de registros para contestar con más contexto."
    )
    st.caption(
        "Prueba: «¿Cuál planeta tiene mayor radio?», "
        "«¿Cuál es el método de descubrimiento más común?» o "
        "«¿Cuántos candidatos tipo Tierra hay?»"
    )
    pregunta = st.text_input(
        "Escribe tu pregunta",
        key="pregunta_ia",
        placeholder="¿Cuál planeta tiene mayor masa?",
    )
    if st.button("Preguntar", type="primary") and pregunta.strip():
        try:
            with st.spinner("Analizando el catálogo completo..."):
                response = requests.post(
                    f"{API}/preguntar",
                    json={"pregunta": pregunta.strip()},
                    timeout=120,
                )
            if response.ok:
                st.session_state["ultima_respuesta_ia"] = response.json()["respuesta"]
            else:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    detail = response.text
                st.error(f"La API respondió HTTP {response.status_code}: {detail}")
        except requests.RequestException as error:
            st.error(f"No se pudo consultar la IA: {error}")
    if st.session_state.get("ultima_respuesta_ia"):
        st.markdown("**Respuesta**")
        st.info(st.session_state["ultima_respuesta_ia"])


with tab_agregar:
    st.subheader("Agregar un planeta")
    with st.form("nuevo"):
        planeta = st.text_input("Nombre del planeta *")
        estrella = st.text_input("Estrella")
        metodo_descubrimiento = st.selectbox(
            "Método de descubrimiento",
            [
                "Transit",
                "Radial Velocity",
                "Microlensing",
                "Imaging",
                "Transit Timing Variations",
                "Eclipse Timing Variations",
                "Pulsar Timing",
                "Orbital Brightness Modulation",
                "Astrometry",
            ],
        )
        lugar_descubrimiento = st.selectbox(
            "Lugar de descubrimiento", ["Ground", "Space", "Multiple locales"]
        )
        anio_descubrimiento = st.number_input(
            "Año de descubrimiento",
            min_value=1989,
            max_value=2100,
            value=None,
            step=1,
        )
        radio_tierras = st.number_input("Radio (Tierras)", min_value=0.0, value=None)
        insolacion_tierra = st.number_input(
            "Insolación (Tierra = 1)", min_value=0.0, value=None
        )
        distancia_sistema_parsec = st.number_input(
            "Distancia (parsec)", min_value=0.0, value=None
        )
        temperatura_planeta_k = st.number_input(
            "Temperatura (K)", min_value=0.0, value=None
        )
        periodo_orbital_dias = st.number_input(
            "Periodo orbital (días)", min_value=0.0, value=None
        )
        masa_tierras = st.number_input("Masa (Tierras)", min_value=0.0, value=None)
        densidad_planeta = st.number_input(
            "Densidad (g/cm³)", min_value=0.0, value=None
        )
        enviar = st.form_submit_button("Guardar planeta")

    if enviar:
        if not planeta.strip():
            st.error("El nombre del planeta es obligatorio.")
        else:
            payload = {
                "planeta": planeta.strip(),
                "estrella": estrella.strip() or None,
                "metodo_descubrimiento": metodo_descubrimiento,
                "lugar_descubrimiento": lugar_descubrimiento,
                "anio_descubrimiento": (
                    int(anio_descubrimiento) if anio_descubrimiento else None
                ),
                "radio_tierras": radio_tierras,
                "insolacion_tierra": insolacion_tierra,
                "distancia_sistema_parsec": distancia_sistema_parsec,
                "temperatura_planeta_k": temperatura_planeta_k,
                "periodo_orbital_dias": periodo_orbital_dias,
                "masa_tierras": masa_tierras,
                "densidad_planeta": densidad_planeta,
            }
            try:
                response = requests.post(
                    f"{API}/datos", json=payload, timeout=30
                )
                if response.ok:
                    st.success(f"Planeta guardado. ID: {response.json()['id']}")
                    listar.clear()
                else:
                    st.error(f"Error de la API: {response.text}")
            except requests.RequestException as error:
                st.error(f"No se pudo guardar el planeta: {error}")
