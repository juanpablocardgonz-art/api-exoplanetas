"""
API del Proyecto Final - Programacion Aplicada
===============================================
Backend (FastAPI) que consulta y administra los datos del proyecto,
guardados en MongoDB.

Como ejecutar (en una terminal, dentro de esta carpeta):
    pip install -r requirements.txt
    uvicorn api:app --reload

Luego abre en el navegador:  http://localhost:8000/docs
(ahi puedes probar todos los endpoints sin escribir nada de codigo)

IMPORTANTE - Seguridad:
    La cadena de conexion a Mongo NUNCA se escribe en este archivo.
    Se lee de una variable de entorno llamada MONGO_URI (mira .env.example).
"""

import json
import os
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

# Si existe un archivo .env, carga sus variables (opcional pero recomendado)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 1. CONFIGURACION   👈 AJUSTA ESTOS NOMBRES A TU PROYECTO
# ---------------------------------------------------------------------------
NOMBRE_BD = "proyecto_segundo_corte"            # 👈 tu base de datos en Atlas
NOMBRE_COLECCION = "exoplanetas_limpios"   # 👈 tu coleccion con los datos ya limpios
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODELO_IA = "gemini-3.5-flash-lite"
# ---------------------------------------------------------------------------
# 2. CONEXION A MONGODB (segura: la clave viene de una variable de entorno)
# ---------------------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(
        "Falta la variable de entorno MONGO_URI. "
        "Crea un archivo .env con tu cadena de conexion de Atlas (mira el README)."
    )

cliente = MongoClient(MONGO_URI)
coleccion = cliente[NOMBRE_BD][NOMBRE_COLECCION]

# ---------------------------------------------------------------------------
# 3. LA APLICACION
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API Proyecto Final",
    description="Consulta y administra los datos del proyecto.",
)


def _a_json(doc):
    """El _id de Mongo es un objeto especial; lo pasamos a texto para el JSON."""
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/")
def inicio():
    """Mensaje de bienvenida y lista de endpoints."""
    return {
        "mensaje": "API del Proyecto Final - ve a /docs para probarla",
        "endpoints": ["GET /datos", "GET /estadisticas", "POST /datos", "/docs"],
    }


# ==== LEER =================================================================
@app.get("/datos")
def listar(campo: Optional[str] = None, valor: Optional[str] = None, limite: int = 0):
    """Lista documentos. Opcionalmente filtra por un campo = valor.

    Ejemplos:
        /datos?limite=50
        /datos?campo=sucursal&valor=Norte

    Con limite=0 (valor predeterminado), devuelve todos los documentos.
    """
    filtro = {campo: valor} if campo and valor else {}
    documentos = [_a_json(d) for d in coleccion.find(filtro).limit(limite)]
    return {"cantidad": len(documentos), "datos": documentos}


@app.get("/estadisticas")
def estadisticas(agrupar_por: str, sumar: str):
    """Agrupa por un campo y suma otro (agregacion de MongoDB).

    Ejemplo:
        /estadisticas?agrupar_por=sucursal&sumar=total
    """
    pipeline = [
        {
            "$group": {
                "_id": f"${agrupar_por}",
                "suma": {"$sum": f"${sumar}"},
                "conteo": {"$sum": 1},
            }
        },
        {"$sort": {"suma": -1}},
    ]
    grupos = [
        {agrupar_por: r["_id"], "suma": r["suma"], "conteo": r["conteo"]}
        for r in coleccion.aggregate(pipeline)
    ]
    return {"grupos": grupos}


# ==== CREAR ================================================================
# 👈 CAMBIA estos campos por los de TU coleccion (mismos nombres y tipos).
class NuevoRegistro(BaseModel):
    planeta: str
    estrella: Optional[str] = None
    metodo_descubrimiento: Optional[str] = None
    anio_descubrimiento: Optional[int] = None
    lugar_descubrimiento: Optional[str] = None
    radio_tierras: Optional[float] = None
    insolacion_tierra: Optional[float] = None
    distancia_sistema_parsec: Optional[float] = None
    temperatura_planeta_k: Optional[float] = None
    periodo_orbital_dias: Optional[float] = None
    masa_tierras: Optional[float] = None
    densidad_planeta: Optional[float] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "planeta": "Planeta Prueba b",
                "estrella": "Estrella Prueba",
                "metodo_descubrimiento": "Transit",
                "anio_descubrimiento": 2026,
                "lugar_descubrimiento": "Space",
                "radio_tierras": 1.1,
                "insolacion_tierra": 0.9,
                "distancia_sistema_parsec": 25.4,
                "temperatura_planeta_k": 260.0,
                "periodo_orbital_dias": 40.5,
                "masa_tierras": 1.4,
                "densidad_planeta": 5.2,
            }
        }
    }


@app.post("/datos")
def crear(registro: NuevoRegistro):
    """Inserta un nuevo documento en la coleccion."""
    doc = registro.model_dump()
    resultado = coleccion.insert_one(doc)
    return {"mensaje": "Registro creado", "id": str(resultado.inserted_id)}

# === Preguntar a los datos en lenguaje natural ============================
class Pregunta(BaseModel):
    pregunta: str
 
    model_config = {
        "json_schema_extra": {
            "example": {"pregunta": "¿Cuál sucursal vendió más?"}
        }
    }
 
 
def _resumen_para_ia():
    """Calcula contexto compacto usando toda la coleccion."""
    pipeline = [
        {
            "$facet": {
                "total": [{"$count": "cantidad"}],
                "metodos": [
                    {"$group": {"_id": "$metodo_espanol", "cantidad": {"$sum": 1}}},
                    {"$sort": {"cantidad": -1}},
                    {"$limit": 10},
                ],
                "lugares": [
                    {"$group": {"_id": "$lugar_descubrimiento", "cantidad": {"$sum": 1}}},
                    {"$sort": {"cantidad": -1}},
                    {"$limit": 10},
                ],
                "anios": [
                    {"$match": {"anio_descubrimiento": {"$type": "number"}}},
                    {
                        "$group": {
                            "_id": "$anio_descubrimiento",
                            "cantidad": {"$sum": 1},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ],
                "clasificacion_tierra": [
                    {"$group": {"_id": "$resultado_tierra", "cantidad": {"$sum": 1}}},
                    {"$sort": {"cantidad": -1}},
                ],
                "mayor_radio": [
                    {"$match": {"radio_tierras": {"$type": "number"}}},
                    {"$sort": {"radio_tierras": -1}},
                    {"$limit": 5},
                    {
                        "$project": {
                            "_id": 0,
                            "planeta": 1,
                            "estrella": 1,
                            "radio_tierras": 1,
                        }
                    },
                ],
                "mayor_masa": [
                    {"$match": {"masa_tierras": {"$type": "number"}}},
                    {"$sort": {"masa_tierras": -1}},
                    {"$limit": 5},
                    {
                        "$project": {
                            "_id": 0,
                            "planeta": 1,
                            "estrella": 1,
                            "masa_tierras": 1,
                        }
                    },
                ],
                "mayor_distancia": [
                    {"$match": {"distancia_sistema_parsec": {"$type": "number"}}},
                    {"$sort": {"distancia_sistema_parsec": -1}},
                    {"$limit": 5},
                    {
                        "$project": {
                            "_id": 0,
                            "planeta": 1,
                            "distancia_sistema_parsec": 1,
                        }
                    },
                ],
                "muestra": [
                    {"$sample": {"size": 8}},
                    {
                        "$project": {
                            "_id": 0,
                            "planeta": 1,
                            "estrella": 1,
                            "anio_descubrimiento": 1,
                            "metodo_espanol": 1,
                            "radio_tierras": 1,
                            "masa_tierras": 1,
                            "distancia_sistema_parsec": 1,
                            "resultado_tierra": 1,
                        }
                    },
                ],
            }
        }
    ]
    resultados = list(coleccion.aggregate(pipeline))
    return resultados[0] if resultados else {}


@app.post("/preguntar")
def preguntar(p: Pregunta):
    """Responde una pregunta en lenguaje natural usando los datos de la coleccion."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Falta la GEMINI_API_KEY.")
 
    # 1. Resumenes y rankings calculados sobre toda la coleccion
    contexto = _resumen_para_ia()

    # 2. El prompt: contexto agregado + pregunta
    prompt = (
        "Eres un asistente que responde preguntas sobre un catalogo de exoplanetas. "
        "Responde en español, claro y breve. Basa la respuesta en el contexto; "
        "distingue los resultados calculados sobre toda la coleccion de la muestra. "
        "Si el contexto no permite responder, dilo y no inventes datos.\n\n"
        f"CONTEXTO DEL CATALOGO:\n"
        f"{json.dumps(contexto, ensure_ascii=False, default=str)}\n\n"
        f"PREGUNTA: {p.pregunta}"
    )
 
    # 3. Llamamos a la API del modelo (¡es otra API REST!)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODELO_IA}:generateContent"
    )
    try:
        r = requests.post(
            url,
            headers={"x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        respuesta = data["candidates"][0]["content"]["parts"][0]["text"]
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "desconocido"
        detail = e.response.text[:1000] if e.response is not None else str(e)
        raise HTTPException(
            status_code=502,
            detail=f"Error del modelo (HTTP {status}): {detail}",
        ) from e
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"No fue posible conectar con el modelo: {e}",
        ) from e
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise HTTPException(
            status_code=502,
            detail=f"Respuesta inesperada del modelo: {e}",
        ) from e

    return {"respuesta": respuesta}
# === FIN NUEVO (IA) ========================================================
