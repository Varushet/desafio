"""
SustraiApp · Asistente cultural y gastronómico del País Vasco (servicio orquestador)
====================================================================================
TODO el servicio en un único archivo, organizado por secciones, para que sea fácil
de explicar y de transferir. Solo depende de datos externos (tus CSV de catálogo).

Flujo de un turno de chat:
    1) traducir   (LLM)        lenguaje natural -> consulta estructurada
    2) grounding  (servidor)   valida/corrige provincia, intereses y fechas
    3) recomendar (API modelos) busca lugares/eventos
    4) redactar   (LLM)        resultados -> sugerencia en lenguaje natural
    5) responder               texto + ítems estructurados

Arranque (modo demo, sin modelo):   uvicorn asistente:app --reload --port 8000
Docs automáticos:                   http://localhost:8000/docs

Modos (variables de entorno):
    LLM_PROVIDER   = stub | openai_compatible      (def. stub)
    MODEL_API_MODE = mock | http                   (def. mock)
    CATALOG_DIR    = carpeta con tus CSV reales     (def. ./catalogos)
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════════════════════
# 1) CONFIGURACIÓN  (todo por variables de entorno con defaults para la demo)
# ════════════════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


def _resolver_catalog_dir() -> Path:
    """Localiza la carpeta con los CSV de catálogo, SIN rutas absolutas fijas.
    Orden: 1) variable de entorno CATALOG_DIR; 2) primera ruta candidata que
    contenga gastronomia.csv. Así funciona igual si los CSV están en ./catalogos
    (junto a este archivo) o en la carpeta data/ del repo desafio."""
    if os.getenv("CATALOG_DIR"):
        return Path(os.getenv("CATALOG_DIR"))
    candidatos = [
        BASE_DIR / "catalogos",            # junto a este archivo
        BASE_DIR.parent.parent / "data",   # .../desafio/data  (repo del proyecto)
        BASE_DIR.parent / "data",
        BASE_DIR / "data",
    ]
    for c in candidatos:
        if (c / "gastronomia.csv").exists():
            return c
    return BASE_DIR / "catalogos"          # por defecto (da un error claro si faltan)


CATALOG_DIR = _resolver_catalog_dir()  # tus CSV reales

# LLM (pasos 'traducir' y 'redactar')
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "stub")          # stub | openai_compatible
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama /v1
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")          # Ollama ignora el valor
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
PERSONA = os.getenv(
    "PERSONA",
    "Eres SustraiApp, un asistente cultural y gastronómico del País Vasco. "
    "Hablas en español, con tono cercano, sobrio y de calidad (sin postureo). "
    "Tu público valora experiencias premium pero no elitistas. Sé breve y concreto.",
)

# API de modelos (paso 'recomendar')
MODEL_API_MODE = os.getenv("MODEL_API_MODE", "mock")      # mock | http
# http = ESTRICTO: la API de recsys es la única fuente; si falla, NO cae a CSV (503).
# mock = lee los CSV de CATALOG_DIR (para demos y tests standalone).
MODEL_API_URL = os.getenv("MODEL_API_URL", "http://localhost:8001")


# ════════════════════════════════════════════════════════════════════════════
# 2) DATOS DE DOMINIO  (antes en JSON; ahora aquí para no multiplicar archivos)
# ════════════════════════════════════════════════════════════════════════════
# Taxonomía de demo. En producción se obtiene de la API de modelos: GET /taxonomy.
TAXONOMIA: dict[int, str] = {
    4: "Concierto", 5: "Festival", 6: "Fiestas", 7: "Feria", 8: "Teatro", 9: "Danza",
    10: "Conferencia", 11: "Eventos/jornadas", 12: "Presentación", 13: "Cine y audiovisuales",
    14: "Bertsolarismo", 15: "Exposición", 16: "Formación", 17: "Concurso",
    19: "Queserías", 20: "Tiendas Gourmet", 21: "Restaurante", 22: "Asador", 23: "Sidrería",
    24: "Bodegas", 25: "Agricultura ecológica", 26: "Denominación de Origen", 27: "Eusko Label",
    28: "Euskal Baserri", 29: "Museos: Historia", 30: "Ciencias naturales", 31: "Arte",
    32: "Etnografía", 33: "Patrimonio cultural",
}

# Categorías padre (nivel 0 de intereses.csv) -> ids hoja, para personalización:
# el usuario puede tener guardada una categoría padre, pero los ítems se etiquetan
# con ids hoja. expandir_intereses() convierte unas en otras de forma segura.
INTERES_PADRE_HIJOS: dict[int, list[int]] = {
    1: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],   # Eventos
    2: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28],             # Gastronomía
    3: [29, 30, 31, 32, 33],                                 # Puntos de interés
}


def expandir_intereses(ids: list[int]) -> list[int]:
    """Expande ids padre a sus hojas y descarta cualquier id desconocido."""
    out: list[int] = []
    for i in ids:
        if i in INTERES_PADRE_HIJOS:
            out += INTERES_PADRE_HIJOS[i]
        elif i in TAXONOMIA:
            out.append(i)
    return sorted(set(out))

# término en lenguaje natural -> ids de la taxonomía (se normaliza al usarse)
SINONIMOS: dict[str, list[int]] = {
    "vino": [24, 26], "vinos": [24, 26], "bodega": [24], "bodegas": [24],
    "txakoli": [24, 26], "rioja alavesa": [24, 26], "cata": [24, 26],
    "comer": [21, 22], "cenar": [21, 22], "restaurante": [21], "restaurantes": [21],
    "asador": [22], "parrilla": [22], "carne": [22], "sidra": [23], "sidreria": [23],
    "txotx": [23], "queso": [19], "quesos": [19], "idiazabal": [19, 26],
    "gourmet": [20], "delicatessen": [20], "producto local": [27, 28],
    "ecologico": [25], "ecologica": [25], "denominacion de origen": [26],
    "museo": [29, 30, 31, 32], "museos": [29, 30, 31, 32], "arte": [31], "pintura": [31],
    "historia": [29], "naturaleza": [30], "ciencia": [30], "etnografia": [32],
    "patrimonio": [33], "cultura": [33, 31], "visitar": [33, 29, 31],
    # "lugares de interés" / "puntos de interés" = patrimonio cultural + museos
    "lugar de interes": [33, 29, 31, 32], "lugares de interes": [33, 29, 31, 32],
    "punto de interes": [33, 29, 31, 32], "puntos de interes": [33, 29, 31, 32],
    "sitio de interes": [33, 29, 31, 32], "sitios de interes": [33, 29, 31, 32],
    "que ver": [33, 29, 31], "que visitar": [33, 29, 31], "turismo": [33, 29, 31],
    "concierto": [4], "conciertos": [4], "musica": [4, 5], "festival": [5],
    "festivales": [5], "fiestas": [6], "feria": [7], "ferias": [7], "teatro": [8],
    "danza": [9], "baile": [9], "conferencia": [10], "charla": [10], "cine": [13],
    "bertsos": [14], "bertsolaris": [14], "exposicion": [15], "exposiciones": [15],
    "curso": [16], "taller": [16], "concurso": [17],
}

# municipio/lugar -> provincia
GAZETTEER: dict[str, str] = {
    "bilbao": "Bizkaia", "getxo": "Bizkaia", "barakaldo": "Bizkaia", "portugalete": "Bizkaia",
    "santurtzi": "Bizkaia", "gernika": "Bizkaia", "bermeo": "Bizkaia", "durango": "Bizkaia",
    "mungia": "Bizkaia", "balmaseda": "Bizkaia", "sopela": "Bizkaia", "leioa": "Bizkaia",
    "basauri": "Bizkaia", "sestao": "Bizkaia", "bizkaia": "Bizkaia", "vizcaya": "Bizkaia",
    "san sebastian": "Gipuzkoa", "donostia": "Gipuzkoa", "donosti": "Gipuzkoa",
    "sanse": "Gipuzkoa", "irun": "Gipuzkoa",
    "errenteria": "Gipuzkoa", "eibar": "Gipuzkoa", "zarautz": "Gipuzkoa",
    "hondarribia": "Gipuzkoa", "tolosa": "Gipuzkoa", "getaria": "Gipuzkoa",
    "arrasate": "Gipuzkoa", "mondragon": "Gipuzkoa", "zumaia": "Gipuzkoa",
    "onati": "Gipuzkoa", "bergara": "Gipuzkoa", "hernani": "Gipuzkoa",
    "gipuzkoa": "Gipuzkoa", "guipuzcoa": "Gipuzkoa",
    "vitoria": "Araba", "gasteiz": "Araba", "vitoria-gasteiz": "Araba",
    "laguardia": "Araba", "amurrio": "Araba", "llodio": "Araba", "laudio": "Araba",
    "salvatierra": "Araba", "oyon": "Araba", "araba": "Araba", "alava": "Araba",
}


def _norm(s: str) -> str:
    """minúsculas, sin tildes, sin signos: para emparejar texto de forma robusta."""
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


# ════════════════════════════════════════════════════════════════════════════
# 3) ESQUEMAS  (contrato de entrada/salida que consume Full Stack)
# ════════════════════════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje en lenguaje natural del usuario.")
    session_id: str = Field(..., description="Identificador de la conversación.")
    user_id: Optional[int] = Field(None, description="Id de usuario (opcional). Sin PII.")


class Item(BaseModel):
    item_id: int
    nombre: str
    tipo: str                     # 'lugar' | 'evento'
    categoria: str                # p.ej. 'Bodegas', 'Concierto'
    provincia: str
    municipio: Optional[str] = None
    estrella_prevista: float      # escala común 1-5 (calibrada)
    url: Optional[str] = None


class Consulta(BaseModel):
    intencion: str                # 'lugares' | 'eventos' | 'plan'
    provincia: Optional[str] = None
    intereses: list[int] = []
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None


class ChatResponse(BaseModel):
    suggestion: str
    items: list[Item] = []
    consulta: Consulta
    aviso: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# 4) GROUNDING  (texto humano -> parámetros válidos contra la taxonomía real)
# ════════════════════════════════════════════════════════════════════════════
class Grounding:
    def __init__(self):
        self.sinonimos = {_norm(k): v for k, v in SINONIMOS.items()}
        self.gazetteer = {_norm(k): v for k, v in GAZETTEER.items()}
        self.taxonomia = dict(TAXONOMIA)   # en producción: GET /taxonomy

    def resolver_provincia(self, texto: str) -> str | None:
        t = _norm(texto)
        for lugar, prov in self.gazetteer.items():
            if re.search(rf"\b{re.escape(lugar)}\b", t):
                return prov
        return None

    def resolver_intereses(self, texto: str) -> list[int]:
        t = _norm(texto)
        encontrados: list[int] = []
        for termino, ids in self.sinonimos.items():
            if termino and re.search(rf"\b{re.escape(termino)}\b", t):
                encontrados.extend(ids)
        vistos, validos = set(), []
        for i in encontrados:
            if (not self.taxonomia or i in self.taxonomia) and i not in vistos:
                vistos.add(i); validos.append(i)
        return validos

    def validar_intereses(self, ids: list[int]) -> list[int]:
        """Descarta ids que el LLM se haya inventado y no existan en la taxonomía."""
        if not self.taxonomia:
            return ids
        return [i for i in ids if i in self.taxonomia]

    def resolver_fechas(self, texto: str, hoy: date | None = None) -> tuple[str | None, str | None]:
        """Las fechas se resuelven SIEMPRE en el servidor, nunca las inventa el LLM."""
        t = _norm(texto)
        hoy = hoy or date.today()
        def iso(d): return d.isoformat()
        if "manana" in t:
            d = hoy + timedelta(days=1); return iso(d), iso(d)
        if "hoy" in t or "esta noche" in t or "esta tarde" in t:
            return iso(hoy), iso(hoy)
        if "fin de semana" in t or "finde" in t:
            sab = hoy + timedelta((5 - hoy.weekday()) % 7)
            return iso(sab), iso(sab + timedelta(days=1))
        if "semana que viene" in t or "proxima semana" in t:
            lun = hoy + timedelta(days=(7 - hoy.weekday()))
            return iso(lun), iso(lun + timedelta(days=6))
        if "esta semana" in t:
            return iso(hoy), iso(hoy + timedelta(days=(6 - hoy.weekday())))
        return None, None


# ════════════════════════════════════════════════════════════════════════════
# 5) TOOLS  (definición de herramientas para function calling del LLM)
# ════════════════════════════════════════════════════════════════════════════
def construir_tools(taxonomia: dict[int, str]) -> list[dict]:
    ids = sorted(taxonomia.keys())
    desc_ids = "; ".join(f"{i}={taxonomia[i]}" for i in ids)
    return [
        {"type": "function", "function": {
            "name": "buscar_lugares",
            "description": ("Busca lugares fijos (gastronomía, cultura, puntos de interés) "
                            "que encajen con los intereses del usuario en una provincia."),
            "parameters": {"type": "object", "properties": {
                "provincia": {"type": "string", "enum": ["Araba", "Bizkaia", "Gipuzkoa"]},
                "intereses": {"type": "array", "items": {"type": "integer", "enum": ids},
                              "description": f"Ids de la taxonomía. {desc_ids}"},
                "top_n": {"type": "integer", "default": 5}},
                "required": ["provincia", "intereses"]}}},
        {"type": "function", "function": {
            "name": "buscar_eventos",
            "description": ("Busca eventos (conciertos, exposiciones, ferias, catas...) en una "
                            "provincia y un rango de fechas."),
            "parameters": {"type": "object", "properties": {
                "provincia": {"type": "string", "enum": ["Araba", "Bizkaia", "Gipuzkoa"]},
                "intereses": {"type": "array", "items": {"type": "integer", "enum": ids}},
                "fecha_inicio": {"type": "string", "description": "YYYY-MM-DD"},
                "fecha_fin": {"type": "string", "description": "YYYY-MM-DD"},
                "top_n": {"type": "integer", "default": 5}},
                "required": ["provincia"]}}},
    ]


# ════════════════════════════════════════════════════════════════════════════
# 6) CLIENTE LLM  (stub determinista  /  openai_compatible vía Ollama)
# ════════════════════════════════════════════════════════════════════════════
def _openai_client():
    from openai import OpenAI
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def traducir(message: str, g: Grounding, tools: list[dict]) -> dict:
    if LLM_PROVIDER == "stub":
        return _traducir_stub(message, g)
    return _traducir_llm(message, tools)


def _traducir_stub(message: str, g: Grounding) -> dict:
    """Reglas: provincia (gazetteer) + intereses (sinónimos) + fechas + intención."""
    provincia = g.resolver_provincia(message)
    intereses = g.resolver_intereses(message)
    fi, ff = g.resolver_fechas(message)
    m = message.lower()
    quiere_evento = bool(fi) or any(w in m for w in
        ["evento", "concierto", "festival", "exposicion", "exposición", "feria",
         "agenda", "que hacer", "qué hacer"])
    quiere_lugar = any(w in m for w in
        ["comer", "cenar", "restaurante", "bodega", "vino", "sidra", "museo", "visitar"])
    if quiere_evento and quiere_lugar:
        intencion = "plan"
    elif quiere_evento:
        intencion = "eventos"
    else:
        intencion = "lugares"
    return {"intencion": intencion, "provincia": provincia, "intereses": intereses,
            "fecha_inicio": fi, "fecha_fin": ff}


def _traducir_llm(message: str, tools: list[dict]) -> dict:
    """Function calling real. El LLM elige herramienta y rellena argumentos."""
    cliente = _openai_client()
    sys = ("Eres un traductor de peticiones a llamadas de herramienta para una app cultural "
           "del País Vasco. Usa SOLO los ids de interés de los enum. Si el usuario menciona una "
           "ciudad, deduce su provincia (Araba/Bizkaia/Gipuzkoa). No inventes categorías.")
    resp = cliente.chat.completions.create(
        model=LLM_MODEL, temperature=LLM_TEMPERATURE, tools=tools,
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": message}],
    )
    msg = resp.choices[0].message
    if not msg.tool_calls:
        return {"intencion": "lugares", "provincia": None, "intereses": [],
                "fecha_inicio": None, "fecha_fin": None}
    call = msg.tool_calls[0]
    args = json.loads(call.function.arguments or "{}")
    intencion = "eventos" if call.function.name == "buscar_eventos" else "lugares"
    return {"intencion": intencion, "provincia": args.get("provincia"),
            "intereses": args.get("intereses", []),
            "fecha_inicio": args.get("fecha_inicio"), "fecha_fin": args.get("fecha_fin")}


def redactar(message: str, items: list[dict]) -> str:
    if not items:
        return ("No he encontrado nada que encaje exactamente, pero dime un poco más "
                "(otra zona o fecha) y te propongo alternativas.")
    if LLM_PROVIDER == "stub":
        top = items[:3]
        trozos = [f"{it['nombre']} ({it['categoria']}, {it['estrella_prevista']}★)" for it in top]
        return "Te propongo: " + "; ".join(trozos) + "."
    cliente = _openai_client()
    contexto = json.dumps([{k: it[k] for k in ("nombre", "categoria", "provincia", "estrella_prevista")}
                           for it in items[:6]], ensure_ascii=False)
    resp = cliente.chat.completions.create(
        model=LLM_MODEL, temperature=0.5,
        messages=[
            {"role": "system", "content": PERSONA + " Usa SOLO los sitios de la lista; no inventes."},
            {"role": "user", "content": f"Petición: {message}\nOpciones: {contexto}\n"
                                         "Redacta una sugerencia breve y concreta."}],
    )
    return resp.choices[0].message.content.strip()


# ════════════════════════════════════════════════════════════════════════════
# 7) CLIENTE API DE MODELOS  (mock: lee tus CSV  /  http: API real de recsys)
# ════════════════════════════════════════════════════════════════════════════
GASTRO_TIPO = {"Restaurante": 21, "Asador": 22, "Sidreria": 23, "Bodega": 24,
               "Bodega Txakoli": 24, "queseria": 19, "tienda": 20}
GASTRO_SELLO = {"Agricultura Ecológica": 25, "Denominación de Origen": 26,
                "Eusko Label": 27, "Euskal Baserri": 28}
CULTURA = {"Historia": 29, "Ciencias Naturales": 30, "Arte": 31, "Etnografía": 32,
           "Patrimonio Cultural": 33}
EVENTO = {"Concierto": 4, "Festival": 5, "Fiestas": 6, "Feria": 7, "Teatro": 8,
          "Danza": 9, "Conferencia": 10, "Eventos/jornadas": 11, "Presentación": 12,
          "Cine y audiovisuales": 13, "Bertsolarismo": 14, "Exposición": 15,
          "Formación": 16, "Concurso": 17}
PROV = {"Álava": "Araba", "Alava": "Araba", "Araba": "Araba", "Guipúzcoa": "Gipuzkoa",
        "Gipuzkoa": "Gipuzkoa", "Vizcaya": "Bizkaia", "Bizkaia": "Bizkaia"}
NORA = {1: "Araba", 20: "Gipuzkoa", 48: "Bizkaia"}

_TODOS = {**{v: k for k, v in GASTRO_TIPO.items()}, **{v: k for k, v in GASTRO_SELLO.items()},
          **{v: k for k, v in CULTURA.items()}, **{v: k for k, v in EVENTO.items()}}


def _cat_nombre(i: int) -> str:
    return TAXONOMIA.get(i) or _TODOS.get(i, str(i))


def _txt(v) -> str | None:
    """Limpia NaN/'nan'/vacío a None (para no pintar enlaces falsos)."""
    s = str(v).strip()
    return None if s.lower() in ("", "nan", "none") else s


# --- Origen de datos del backup local: CSV (snapshot) o BD compartida ----------
# DATA_SOURCE=csv  -> lee los CSV de CATALOG_DIR (por defecto; snapshot resiliente)
# DATA_SOURCE=db   -> lee de la BD compartida con Full Stack vía SQLAlchemy
DATA_SOURCE = os.getenv("DATA_SOURCE", "csv")          # csv | db
DATABASE_URL = os.getenv("DATABASE_URL", "")           # p.ej. postgresql+psycopg2://user:pass@host:5432/sustrai
DB_TABLAS = {                                          # ajustar al nombre real de cada tabla
    "gastronomia": os.getenv("DB_TABLA_GASTRO", "gastronomia"),
    "patrimonio": os.getenv("DB_TABLA_PATRIMONIO", "patrimonio"),
    "eventos": os.getenv("DB_TABLA_EVENTOS", "eventos"),
}
_engine = None


def _get_engine():
    """Crea (una vez) el engine de SQLAlchemy hacia la BD compartida."""
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def _leer(nombre: str) -> "pd.DataFrame":
    """Lee una 'tabla' de catálogo desde CSV o desde la BD, según DATA_SOURCE.
    Devuelve el DataFrame en crudo; la normalización de columnas la hace _catalogos()."""
    if DATA_SOURCE == "db":
        return pd.read_sql_table(DB_TABLAS[nombre], _get_engine())
    return pd.read_csv(CATALOG_DIR / f"{nombre}.csv")


@lru_cache(maxsize=1)
def _catalogos():
    g = _leer("gastronomia").rename(columns={"Unnamed: 0": "item_id"})
    g["provincia"] = g["Provincia"].map(PROV).fillna("Bizkaia")
    g["id_interes"] = g["Tipo de lugar"].map(GASTRO_TIPO).fillna(21).astype(int)
    # 'Sello' es opcional: si la fuente no la trae, las Tiendas Gourmet (20) se quedan como 20
    if "Sello" in g.columns:
        sello = g["Sello"].map(GASTRO_SELLO)
        g.loc[g["id_interes"] == 20, "id_interes"] = sello[g["id_interes"] == 20].fillna(20).astype(int)
    g["valoracion"] = g["valoracion"].fillna(4.3)

    c = _leer("patrimonio").rename(columns={"Unnamed: 0": "item_id"})
    c.columns = [x.strip() for x in c.columns]
    c["provincia"] = c["Provincia"].map(PROV).fillna("Bizkaia")
    c["id_interes"] = c["Tipo de Cultura"].map(CULTURA).fillna(33).astype(int)
    c["valoracion"] = c["valoracion"].fillna(4.3)

    e = _leer("eventos").rename(columns={"id_Kulturklik": "item_id"})
    e["provincia"] = e["provinceNoraCode"].map(NORA).fillna("Bizkaia")
    e["id_interes"] = e["typeEs"].map(EVENTO).fillna(11).astype(int)
    return g, c, e


def buscar_lugares(provincia: str, intereses: list[int], top_n: int = 5,
                   user_id: int | None = None) -> list[dict]:
    if MODEL_API_MODE == "http":
        # Modo http ESTRICTO: la API de recsys es la ÚNICA fuente. Si responde
        # (aunque sea []), se usa tal cual. Si falla (caída/timeout/5xx), NO se
        # cae a los CSV: se propaga un 503 para que el fallo sea visible.
        items = _http("/recommendations/places",
                      {"user_id": user_id, "provincia": provincia,
                       "intereses": intereses, "top_n": top_n})
        if items is None:
            raise HTTPException(
                status_code=503,
                detail="La API de recomendaciones (recsys) no está disponible (lugares).")
        return items
    # Modo mock (demos/tests standalone): lee los CSV de catálogo.
    return _lugares_local(provincia, intereses, top_n)


def _lugares_local(provincia: str, intereses: list[int], top_n: int = 5) -> list[dict]:
    """Solo modo mock: calcula lugares desde los CSV de catálogo."""
    g, c, _ = _catalogos()
    out = []
    for df, ncol in [(g, "Nombre"), (c, "Nombre")]:
        sub = df[df["provincia"] == provincia]
        if intereses:
            sub = sub[sub["id_interes"].isin(intereses)]
        sub = sub.sort_values("valoracion", ascending=False).head(top_n)
        for _, r in sub.iterrows():
            out.append({
                "item_id": int(r["item_id"]), "nombre": str(r[ncol]), "tipo": "lugar",
                "categoria": _cat_nombre(int(r["id_interes"])), "provincia": provincia,
                "municipio": _txt(r.get("Municipio")),
                "estrella_prevista": round(float(r["valoracion"]), 2),
                "url": _txt(r.get("WEB"))})
    return sorted(out, key=lambda x: -x["estrella_prevista"])[:top_n]


def buscar_eventos(provincia: str, intereses: list[int] | None = None,
                   fecha_inicio: str | None = None, fecha_fin: str | None = None,
                   top_n: int = 5, user_id: int | None = None) -> list[dict]:
    if MODEL_API_MODE == "http":
        # Modo http ESTRICTO: única fuente la API; si falla, 503 (sin CSV).
        items = _http("/recommendations/events", {
            "user_id": user_id, "provincia": provincia, "intereses": intereses or [],
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin, "top_n": top_n})
        if items is None:
            raise HTTPException(
                status_code=503,
                detail="La API de recomendaciones (recsys) no está disponible (eventos).")
        return items
    # Modo mock (demos/tests standalone): lee los CSV de catálogo.
    return _eventos_local(provincia, intereses, fecha_inicio, fecha_fin, top_n)


def _eventos_local(provincia: str, intereses: list[int] | None = None,
                   fecha_inicio: str | None = None, fecha_fin: str | None = None,
                   top_n: int = 5) -> list[dict]:
    """Solo modo mock: calcula eventos desde los CSV de catálogo."""
    _, _, e = _catalogos()
    sub = e[e["provincia"] == provincia]
    if intereses:
        sub = sub[sub["id_interes"].isin(intereses)]
    sub = sub.head(top_n)
    nombre_col = "nameEs" if "nameEs" in sub.columns else sub.columns[1]
    return [{
        "item_id": int(r["item_id"]), "nombre": str(r[nombre_col]), "tipo": "evento",
        "categoria": _cat_nombre(int(r["id_interes"])), "provincia": provincia,
        "municipio": _txt(r.get("municipalityEs")),
        "estrella_prevista": 4.2,           # placeholder (en prod lo da el modelo + calibración)
        "url": None,
    } for _, r in sub.iterrows()]


def _http(path: str, params: dict) -> list[dict] | None:
    """Llama a la API de modelos (recsys).
    Devuelve la lista de items si responde bien (puede ser [] = sin resultados),
    o None si hubo ERROR (caída, timeout, 5xx) para que el llamante use el backup local."""
    import httpx
    try:
        r = httpx.get(MODEL_API_URL + path, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as exc:
        print(f"[recsys] aviso: API no disponible ({MODEL_API_URL}{path}): {exc}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# 8) ORQUESTADOR  (encadena los 5 pasos de un turno)
# ════════════════════════════════════════════════════════════════════════════
_grounding = Grounding()
_tools = construir_tools(TAXONOMIA)

# --- Memoria de sesión (recuerda SOLO el turno anterior) -----------------------
# Almacén en memoria del proceso: suficiente para la demo. Guarda únicamente
# provincia + intereses del último turno (NUNCA el texto del mensaje ni PII), para
# que un seguimiento como "¿y mañana?" o "¿y en Donosti?" no pierda el contexto.
# En producción con varios workers/réplicas: usar un store compartido con
# expiración (p. ej. Redis con TTL) y un session_id no adivinable (UUID v4)
# ligado al user_id autenticado (ver README, sección 6).
_MEMORIA: dict[str, dict] = {}
_MEM_MAX = 1000  # tope simple anti-DoS por session_ids distintos


def contexto_previo(session_id: str) -> dict:
    """Devuelve {provincia, intereses} del último turno de esa sesión, o {}."""
    return _MEMORIA.get(session_id) or {}


def recordar_contexto(session_id: str, q: dict) -> None:
    """Guarda provincia + intereses del turno actual (sin texto ni PII)."""
    if not session_id:
        return
    if len(_MEMORIA) >= _MEM_MAX and session_id not in _MEMORIA:
        _MEMORIA.clear()  # demo: vaciado simple; prod: TTL/LRU o Redis
    _MEMORIA[session_id] = {
        "provincia": q.get("provincia"),
        "intereses": list(q.get("intereses") or []),
    }


def manejar_chat(req: ChatRequest, hoy: date | None = None) -> ChatResponse:
    # 1) traducir
    q = traducir(req.message, _grounding, _tools)

    # 2) grounding en el servidor (nunca confiar a ciegas en el LLM)
    if not q.get("provincia"):
        q["provincia"] = _grounding.resolver_provincia(req.message)
    # intereses: usa los del LLM si sobreviven a la taxonomía; si no queda ninguno
    # (lista vacía o ids inventados), cae al extractor por reglas. Así no se pierde
    # "vino -> [24, 26]" aunque el modelo mande un id inválido.
    intereses = _grounding.validar_intereses(q.get("intereses") or [])
    if not intereses:
        intereses = _grounding.resolver_intereses(req.message)
    q["intereses"] = intereses
    if not q.get("fecha_inicio"):
        q["fecha_inicio"], q["fecha_fin"] = _grounding.resolver_fechas(req.message, hoy)

    # 2.bis) memoria: si este turno no trae provincia/intereses, hereda del anterior
    prev = contexto_previo(req.session_id)
    if not q["provincia"] and prev.get("provincia"):
        q["provincia"] = prev["provincia"]
    if not q["intereses"] and prev.get("intereses"):
        q["intereses"] = prev["intereses"]

    # 2.ter) personalización: si hay user_id y el turno (ni la memoria) trae intereses,
    #        usa los intereses guardados del usuario en el backend (expandidos a hojas).
    #        Resiliente: si el backend está off/caído, no hace nada.
    if req.user_id and not q["intereses"]:
        try:
            import backend_api
            guardados = backend_api.get_usuario_intereses(req.user_id)
            if guardados:
                q["intereses"] = expandir_intereses(guardados)
        except Exception as exc:
            print(f"[backend] personalización omitida: {exc}")

    aviso = None
    if not q["provincia"]:
        return ChatResponse(
            suggestion="¿En qué zona te mueves —Bizkaia, Gipuzkoa o Araba— y qué te apetece?",
            items=[], consulta=Consulta(intencion=q["intencion"], intereses=q["intereses"]),
            aviso="falta provincia")

    # 3) recomendar según la intención
    items: list[dict] = []
    if q["intencion"] in ("eventos", "plan"):
        items += buscar_eventos(q["provincia"], q["intereses"],
                                q.get("fecha_inicio"), q.get("fecha_fin"),
                                top_n=5, user_id=req.user_id)
    if q["intencion"] in ("lugares", "plan") or not items:
        lugares = buscar_lugares(q["provincia"], q["intereses"], top_n=5, user_id=req.user_id)
        if q["intencion"] == "eventos" and lugares and not items:
            aviso = "No había eventos que encajaran; te propongo lugares afines."
        items += lugares

    items = sorted(items, key=lambda x: -x["estrella_prevista"])[:6]

    # guardar contexto de este turno para el siguiente (solo provincia + intereses)
    recordar_contexto(req.session_id, q)

    # 4) redactar  +  5) responder
    return ChatResponse(
        suggestion=redactar(req.message, items),
        items=[Item(**it) for it in items],
        consulta=Consulta(intencion=q["intencion"], provincia=q["provincia"],
                          intereses=q["intereses"], fecha_inicio=q.get("fecha_inicio"),
                          fecha_fin=q.get("fecha_fin")),
        aviso=aviso,
    )


# ════════════════════════════════════════════════════════════════════════════
# 9) FASTAPI  (POST /chat, GET /health, GET / -> demo)
# ════════════════════════════════════════════════════════════════════════════
app = FastAPI(title="SustraiApp · Asistente cultural", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def demo():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return manejar_chat(req)
