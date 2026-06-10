from flask import Flask, jsonify, request
from config import Config
from models import (db, Municipio, Usuario, Preferencia, Interes,
                    UserInteres, Resena, Evento, Gastronomia, Cultura)
from assistant_logic import manejar_chat_flask
from flask_cors import CORS
from sqlalchemy import text
from datetime import datetime
import logging

import os
import pickle
import unicodedata
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import psycopg2

# Cargar variables de entorno desde .env
load_dotenv()

logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def paginate(query):
    """Aplica limit/offset desde query params y devuelve (items, meta)."""
    limit  = request.args.get('limit',  20,  type=int)
    offset = request.args.get('offset', 0,   type=int)
    total  = query.count()
    items  = query.limit(limit).offset(offset).all()
    return items, {'total': total, 'limit': limit, 'offset': offset}


def ok(data, meta=None, status=200):
    body = {'data': data}
    if meta:
        body['meta'] = meta
    return jsonify(body), status


def err(msg, status=400):
    return jsonify({'error': msg}), status


def get_municipality_id_from_request():
    """
    Extrae municipality_id del usuario autenticado.
    Por ahora lo lee del header X-User-Id y consulta la BD.
    TODO: reemplazar por JWT cuando se implemente auth con tokens.
    """
    user_id = request.headers.get('X-User-Id', type=int)
    if not user_id:
        return None
    user = Usuario.query.get(user_id)
    return user.municipality_id if user else None

# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────
PG = dict(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    dbname=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

N_PATROCINADOS = 2          # nº de patrocinados a incluir al inicio de cada respuesta
SIN_RESULTADOS = "No hay resultados para esta busqueda"

# ──────────────────────────────────────────────────────────────────────────────
# Normalización de provincia y texto (idéntica a los notebooks)
# Vizcaya/Bizkaia → 48 · Guipúzcoa/Gipuzkoa → 20 · Álava/Araba → 01
# ──────────────────────────────────────────────────────────────────────────────
PROVINCIA_ALIAS = {
    "alava": "01", "araba": "01", "araba/alava": "01", "01": "01", "1": "01",
    "guipuzcoa": "20", "gipuzkoa": "20", "20": "20",
    "vizcaya": "48", "bizkaia": "48", "48": "48",
}


def _norm_txt(valor):
    """minúsculas + sin tildes + sin espacios sobrantes ('Álava ' → 'alava')"""
    s = str(valor).strip().lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _cod_provincia(valor):
    """Código de provincia ('01','20','48') o None si no se reconoce."""
    if valor is None:
        return None
    return PROVINCIA_ALIAS.get(_norm_txt(valor))


# ──────────────────────────────────────────────────────────────────────────────
# Carga de modelos y datos (una vez, al arrancar)
# ──────────────────────────────────────────────────────────────────────────────
def _cargar_modelo(nombre):
    with open(os.path.join(MODELS_DIR, nombre), "rb") as f:
        return pickle.load(f)


model_gastro  = _cargar_modelo("svd_gastro.pkl")
model_cultura = _cargar_modelo("svd_patrimonio.pkl")
model_eventos = _cargar_modelo("svd_eventos.pkl")

conn = psycopg2.connect(**PG, options="-c client_encoding=UTF8")
try:
    # ── Gastronomía ──────────────────────────────────────────────────────────
    reviews_gastro = pd.read_sql(
        "SELECT user_id, gastro_id, puntuacion FROM user_data.gastronomy_reviews", conn)
    gastro = pd.read_sql("""
        SELECT g.id           AS gastro_id,
               g.type         AS "Tipo de lugar",
               m.provincia    AS "Provincia",
               g.nivel_precio AS "Nivel precio",
               g.is_sponsored AS is_sponsored,
               g.valoracion   AS valoracion
        FROM market_data.gastronomy g
        JOIN shared.municipalities m ON m.id = g.municipality_id
    """, conn)

    # ── Patrimonio cultural ──────────────────────────────────────────────────
    reviews_cultura = pd.read_sql(
        "SELECT user_id, culture_id, puntuacion FROM user_data.culture_reviews", conn)
    patrimonio = pd.read_sql("""
        SELECT c.id           AS culture_id,
               c.tipo_lugar   AS "Tipo de lugar",
               m.provincia    AS "Provincia",
               c.is_sponsored AS is_sponsored,
               c.valoracion   AS valoracion
        FROM market_data.culture c
        JOIN shared.municipalities m ON m.id = c.municipality_id
    """, conn)

    # ── Eventos ──────────────────────────────────────────────────────────────
    reviews_eventos = pd.read_sql(
        "SELECT user_id, event_id, puntuacion FROM user_data.event_reviews", conn)
    eventos = pd.read_sql("""
        SELECT e.id            AS event_id,
               e.type          AS "typeEs",
               e.is_free       AS is_free,
               e.start_date    AS "startDate",
               m.province_code AS "provinceNoraCode"
        FROM market_data.events e
        JOIN shared.municipalities m ON m.id = e.municipality_id
    """, conn)
finally:
    conn.close()

# Tipos y columnas derivadas (igual que en los notebooks)
gastro["is_sponsored"]     = gastro["is_sponsored"].fillna(False).astype(bool)
patrimonio["is_sponsored"] = patrimonio["is_sponsored"].fillna(False).astype(bool)

eventos["startDate"]        = pd.to_datetime(eventos["startDate"], utc=True, errors="coerce")
eventos["is_weekend"]       = eventos["startDate"].dt.weekday >= 5
eventos["provinceNoraCode"] = pd.to_numeric(eventos["provinceNoraCode"], errors="coerce")


# ──────────────────────────────────────────────────────────────────────────────
# Lógica de recomendación (compartida por las 3 categorías)
# ──────────────────────────────────────────────────────────────────────────────
def _rankear(user_id, modelo, df_reviews, catalogo, id_col, top_n, con_patrocinados):
    """
    Núcleo común: SVD para usuarios con historial, media de reseñas para cold
    start, y (opcionalmente) 2 patrocinados priorizados al inicio del listado.
    Devuelve lista [(id, score, patrocinado), ...] o el string SIN_RESULTADOS.
    """
    if catalogo.empty:
        return SIN_RESULTADOS

    tiene_historial = user_id in df_reviews["user_id"].values
    visitados = set(df_reviews[df_reviews["user_id"] == user_id][id_col])

    no_visitados = [i for i in catalogo[id_col] if i not in visitados]
    if not no_visitados:
        return SIN_RESULTADOS

    if tiene_historial:
        preds  = [(i, modelo.predict(user_id, i).est) for i in no_visitados]
        metodo = "SVD personalizado"
    else:
        media = df_reviews.groupby(id_col)["puntuacion"].mean()
        if "valoracion" in catalogo.columns:
            val = catalogo.set_index(id_col)["valoracion"]
            preds = [(i, float(media.get(i, val.get(i, 4.0)
                                if pd.notna(val.get(i, np.nan)) else 4.0)))
                     for i in no_visitados]
        else:
            preds = [(i, float(media.get(i, 3.5))) for i in no_visitados]
        metodo = "Cold start (media de reseñas)"

    preds.sort(key=lambda x: x[1], reverse=True)

    # ── Priorizar N_PATROCINADOS al inicio del listado ───────────────────────
    ids_sponsor = set()
    if con_patrocinados and "is_sponsored" in catalogo.columns:
        sponsor_all   = set(catalogo.loc[catalogo["is_sponsored"], id_col])
        preds_sponsor = [p for p in preds if p[0] in sponsor_all][:N_PATROCINADOS]
        ids_sponsor   = {p[0] for p in preds_sponsor}
        organico      = [p for p in preds if p[0] not in ids_sponsor]
        preds         = preds_sponsor + organico

    top = preds[:top_n]
    if not top:
        return SIN_RESULTADOS

    return [(int(i), round(float(s), 2), i in ids_sponsor) for i, s in top], metodo


def _respuesta(user_id, categoria, resultado):
    """Convierte el resultado de _rankear en la respuesta JSON de la API."""
    if isinstance(resultado, str):  # SIN_RESULTADOS
        return jsonify({"user_id": user_id, "categoria": categoria,
                        "ids": [], "mensaje": resultado})
    top, metodo = resultado
    return jsonify({
        "user_id":    user_id,
        "categoria":  categoria,
        "metodo":     metodo,
        "ids":        [i for i, _, _ in top],
        "resultados": [{"id": i, "puntuacion_estimada": s, "patrocinado": p}
                       for i, s, p in top],
    })


def _params_comunes():
    """user_id (obligatorio) y top_n (opcional, por defecto 10)."""
    user_id = request.args.get("user_id", type=int)
    top_n   = request.args.get("top_n", default=10, type=int)
    return user_id, top_n

# ─────────────────────────────────────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    # =========================================================================
    # RAÍZ
    # =========================================================================

    @app.route('/', methods=['GET'])
    def home():
        """
        ═══════════════════════════════════════════════════════════════════════
        Verifica que la API está activa y disponible.
        ───────────────────────────────────────────────────────────────────────
        PARA QUÉ SIRVE:
            - Health check básico de la API
            - Verificar que el servidor está respondiendo
        
        CÓMO SE USA:
            GET /
            Sin parámetros requeridos
        
        EJEMPLO DE USO:
            // JavaScript
            fetch('http://localhost:5000/')
                .then(res => res.json())
                .then(data => console.log(data.data.message));
            
            // cURL
            curl -X GET http://localhost:5000/
        
        RESPUESTA ESPERADA (200):
            {"data": {"message": "Bienvenidos a la API SustraiApp"}}
        ═══════════════════════════════════════════════════════════════════════
        """
        return ok({'message': 'Bienvenidos a la API SustraiApp'})

    # =========================================================================
    # AUTENTICACIÓN
    # =========================================================================

    @app.route('/registro', methods=['POST'])
    def registrar_usuario():
        """
        ═══════════════════════════════════════════════════════════════════════
        Registra un nuevo usuario en la plataforma.
        ───────────────────────────────────────────────────────────────────────
        PARA QUÉ SIRVE:
            - Crear cuenta de usuario nuevo
            - Guardar datos personales y de geolocalización
            - Inicializar preferencias del usuario
        
        CÓMO SE USA:
            POST /registro con JSON en body
        
        EJEMPLO DE USO:
            // JavaScript
            const response = await fetch('http://localhost:5000/registro', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    nombre: 'Juan', email: 'juan@example.com',
                    password: 'miPassword123', municipality_id: 5,
                    sexo: 'hombre', //Es importante que sea hombre / mujer
                    age: 28
                })
            });
            const userId = (await response.json()).data.usuario.id_user;
        
        RESPUESTA ESPERADA (201):
            {"data": {"mensaje": "Usuario creado", "usuario": {...}}}
        
        ERRORES: 400, 409, 500
        ═══════════════════════════════════════════════════════════════════════
        """
        data = request.get_json()
        required = ['nombre', 'email', 'password', 'municipality_id', 'sexo', 'age']
        if not all(f in data for f in required):
            return err("Faltan campos obligatorios")
        if Usuario.query.filter_by(email=data['email']).first():
            return err("El email ya está registrado", 409)
        if not Municipio.query.get(data['municipality_id']):
            return err("municipality_id no válido")
        try:
            u = Usuario(
                nombre=data['nombre'], apellido=data.get('apellido'),
                email=data['email'],   tlf=data.get('tlf'),
                municipality_id=int(data['municipality_id']),
                sexo=data['sexo'],     age=int(data['age']), role='user'
            )
            u.set_password(data['password'])
            db.session.add(u)
            db.session.flush()
            db.session.add(Preferencia(user_id=u.id_user))
            db.session.commit()
            return ok({'mensaje': 'Usuario creado', 'usuario': u.to_dict()}, status=201)
        except Exception as e:
            db.session.rollback()
            return err(str(e), 500)

    @app.route('/login', methods=['POST'])
    def login():
        """
        ═══════════════════════════════════════════════════════════════════════
        Autentica un usuario y retorna su ID y rol.
        ───────────────────────────────────────────────────────────────────────
        PARA QUÉ SIRVE:
            - Verificar credenciales del usuario
            - Obtener ID para la sesión
            - Conocer el rol del usuario
        
        CÓMO SE USA:
            POST /login con {"email": "...", "password": "..."}
        
        EJEMPLO DE USO:
            // JavaScript
            const response = await fetch('http://localhost:5000/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: 'juan@example.com',
                    password: 'miPassword123'
                })
            });
            const userId = (await response.json()).data.user_id;
            localStorage.setItem('userId', userId);
        
        RESPUESTA ESPERADA (200):
            {"data": {"mensaje": "Login exitoso", "user_id": 1, "role": "user"}}
        
        ERRORES: 400, 401
        ═══════════════════════════════════════════════════════════════════════
        """
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return err("Email y password requeridos")
        u = Usuario.query.filter_by(email=data['email']).first()
        if u and u.check_password(data['password']):
            return ok({'mensaje': 'Login exitoso', 'user_id': u.id_user, 'role': u.role})
        return err("Credenciales inválidas", 401)

    # =========================================================================
    # MUNICIPIOS
    # =========================================================================

    @app.route('/api/municipios', methods=['GET'])
    def listar_municipios():
        """
        ═══════════════════════════════════════════════════════════════════════
        Obtiene lista de todos los municipios disponibles.
        ───────────────────────────────────────────────────────────────────────
        PARA QUÉ SIRVE:
            - Llenar dropdowns en formularios
            - Filtrar contenido por municipio
            - Seleccionar ubicación del usuario
        
        CÓMO SE USA:
            GET /api/municipios
        
        EJEMPLO DE USO:
            // JavaScript
            const munis = (await fetch('http://localhost:5000/api/municipios')
                .then(r => r.json())).data;
            munis.forEach(m => console.log(`${m.id}: ${m.nombre}`));
        
        RESPUESTA ESPERADA (200):
            {"data": [{"id": 1, "nombre": "Bilbao"}, ...]}
        ═══════════════════════════════════════════════════════════════════════
        """
        municipios = Municipio.query.order_by(Municipio.nombre).all()
        return ok([m.to_dict() for m in municipios])

    # =========================================================================
    # EVENTOS
    # =========================================================================

    @app.route('/api/eventos/esta-semana', methods=['GET'])
    def eventos_esta_semana():
        """
        ═══════════════════════════════════════════════════════════════════════
        Obtiene eventos de la semana actual (lunes a domingo).
        ───────────────────────────────────────────────────────────────────────
        PARA QUÉ SIRVE:
            - Mostrar agenda semanal
            - Planificación de actividades
            - Vista rápida de eventos disponibles esta semana
        
        CÓMO SE USA:
            GET /api/eventos/esta-semana
            Parámetros opcionales: ?limit=20&offset=0
        
        EJEMPLO DE USO:
            // JavaScript
            const eventos = (await fetch(
                'http://localhost:5000/api/eventos/esta-semana')
                .then(r => r.json())).data;
            eventos.forEach(e => console.log(`${e.nombre} - ${e.start_date}`));
        
        RESPUESTA ESPERADA (200):
            {"data": [...], "meta": {"total": 15, "limit": 20, "offset": 0}}
        ═══════════════════════════════════════════════════════════════════════
        """
        q = (Evento.query
             .filter(Evento.active == True)
             .filter(text("""
                 start_date >= date_trunc('week', NOW() AT TIME ZONE 'Europe/Madrid')
                             AT TIME ZONE 'Europe/Madrid'
                 AND start_date <= date_trunc('week', NOW() AT TIME ZONE 'Europe/Madrid')
                             AT TIME ZONE 'Europe/Madrid' + interval '6 days 23:59:59'
             """))
             .order_by(Evento.start_date.asc()))
        items, meta = paginate(q)
        return ok([e.to_dict() for e in items], meta)

    @app.route('/api/eventos/fin-de-semana', methods=['GET'])
    def eventos_fin_de_semana():
        """
        Obtiene eventos de fin de semana en los próximos 7 días.
        PARA QUÉ: Planificar actividades para el fin de semana
        USO: GET /api/eventos/fin-de-semana
        EJEMPLO: const eventos = (await fetch(...).then(r => r.json())).data;
        """
        q = (Evento.query
             .filter(Evento.active == True)
             .filter(text("""
                 EXTRACT(DOW FROM start_date AT TIME ZONE 'Europe/Madrid') IN (0, 6)
                 AND start_date >= NOW()
                 AND start_date <= NOW() + interval '7 days'
             """))
             .order_by(Evento.start_date.asc()))
        items, meta = paginate(q)
        return ok([e.to_dict() for e in items], meta)

    @app.route('/api/eventos/cerca-de-ti', methods=['GET'])
    def eventos_cerca_de_ti():
        """
        Obtiene eventos en el municipio del usuario autenticado.
        PARA QUÉ: Personalizar resultados por ubicación del usuario
        USO: GET /api/eventos/cerca-de-ti (requiere header X-User-Id)
        EJEMPLO: fetch('...', {headers: {'X-User-Id': userId}})
        """
        mun_id = get_municipality_id_from_request()
        if not mun_id:
            return err("Usuario no autenticado o sin municipio", 401)
        q = (Evento.query
             .filter(Evento.active == True)
             .filter(Evento.municipality_id == mun_id)
             .order_by(Evento.start_date.asc()))
        items, meta = paginate(q)
        return ok([e.to_dict() for e in items], meta)

    @app.route('/api/eventos/en-euskera', methods=['GET'])
    def eventos_en_euskera():
        """
        Obtiene eventos disponibles en idioma euskera.
        PARA QUÉ: Filtrar eventos por idioma preferido
        USO: GET /api/eventos/en-euskera
        RESPUESTA: Eventos con language='EU'
        """
        q = (Evento.query
             .filter(Evento.active == True)
             .filter(Evento.language == 'EU')
             .order_by(Evento.start_date.asc()))
        items, meta = paginate(q)
        return ok([e.to_dict() for e in items], meta)

    @app.route('/api/eventos', methods=['GET'])
    def eventos_todos():
        """
        Obtiene lista general de eventos con filtros avanzados.
        PARA QUÉ: Búsqueda y filtrado general de eventos
        USO: GET /api/eventos?municipality_id=5&is_free=true&type=concierto
        EJEMPLO: const url = new URL('http://localhost:5000/api/eventos');
                url.searchParams.append('is_free', 'true');
        """
        q = Evento.query.filter(Evento.active == True)
        if request.args.get('municipality_id'):
            q = q.filter(Evento.municipality_id == request.args.get('municipality_id', type=int))
        if request.args.get('is_free'):
            q = q.filter(Evento.is_free == (request.args.get('is_free') == 'true'))
        if request.args.get('type'):
            q = q.filter(Evento.type == request.args.get('type'))
        q = q.order_by(Evento.start_date.asc())
        items, meta = paginate(q)
        return ok([e.to_dict() for e in items], meta)

    # =========================================================================
    # GASTRONOMÍA
    # =========================================================================

    @app.route('/api/gastronomia/<int:gastro_id>/cualificaciones',methods=['GET'])
    def obtener_cualificaciones_gastronomia(gastro_id):
        """
        Obtiene cualificaciones especiales de un establecimiento gastronómico.
        PARA QUÉ: Ver distinciones (Michelin, Repsol, etc) del restaurante
        USO: GET /api/gastronomia/{id}/cualificaciones
        EJEMPLO: fetch('http://localhost:5000/api/gastronomia/15/cualificaciones')
        """

        gastro = Gastronomia.query.get(gastro_id)

        if not gastro:
            return err("Establecimiento no encontrado", 404)

        return ok({
            'id': gastro.id,
            'nombre': gastro.nombre,
            'cualificaciones': [
                gq.qualification.to_dict()
                for gq in gastro.cualificaciones
                if gq.qualification
            ]
        })

    @app.route('/api/gastronomia/mejor-valorados', methods=['GET'])
    def gastro_mejor_valorados():
        """Establecimientos con >= 10 reseñas, ordenados por valoración."""
        q = (Gastronomia.query
             .filter(Gastronomia.active == True)
             .filter(Gastronomia.num_resenas >= 10)
             .order_by(Gastronomia.valoracion.desc(),
                       Gastronomia.num_resenas.desc()))
        items, meta = paginate(q)
        return ok([g.to_dict() for g in items], meta)

    @app.route('/api/gastronomia/entorno-especial', methods=['GET'])
    def gastro_entorno_especial():
        """
        Obtiene restaurantes con entorno especial (Costa, Montaña, etc).
        PARA QUÉ: Buscar experiencias gastronómicas con vistas especiales
        USO: GET /api/gastronomia/entorno-especial
        EJEMPLO: fetch('http://localhost:5000/api/gastronomia/entorno-especial')
        """
        q = (Gastronomia.query
             .filter(Gastronomia.active == True)
             .filter(Gastronomia.entorno.isnot(None))
             .filter(Gastronomia.entorno != '')
             .order_by(Gastronomia.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([g.to_dict() for g in items], meta)

    @app.route('/api/gastronomia/cerca-de-ti', methods=['GET'])
    def gastro_cerca_de_ti():
        """
        Obtiene restaurantes en el municipio del usuario autenticado.
        PARA QUÉ: Encontrar restaurantes cercanos al usuario
        USO: GET /api/gastronomia/cerca-de-ti (requiere header X-User-Id)
        EJEMPLO: fetch('...', {headers: {'X-User-Id': userId}})
        """
        mun_id = get_municipality_id_from_request()
        if not mun_id:
            return err("Usuario no autenticado o sin municipio", 401)
        q = (Gastronomia.query
             .filter(Gastronomia.active == True)
             .filter(Gastronomia.municipality_id == mun_id)
             .order_by(Gastronomia.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([g.to_dict() for g in items], meta)

    @app.route('/api/gastronomia', methods=['GET'])
    def gastro_todos():
        """
        Obtiene lista general de restaurantes con filtros avanzados.
        PARA QUÉ: Búsqueda avanzada con filtros por tipo, Michelin, municipio
        USO: GET /api/gastronomia?tipo_comida=vasca&michelin=true
        RESPUESTA: Restaurantes ordenados por valoración descendente
        """
        q = Gastronomia.query.filter(Gastronomia.active == True)
        if request.args.get('municipality_id'):
            q = q.filter(Gastronomia.municipality_id == request.args.get('municipality_id', type=int))
        if request.args.get('tipo_comida'):
            q = q.filter(Gastronomia.tipo_comida == request.args.get('tipo_comida'))
        if request.args.get('michelin'):
            q = q.filter(Gastronomia.michelin == (request.args.get('michelin') == 'true'))
        q = q.order_by(Gastronomia.valoracion.desc().nullslast())
        items, meta = paginate(q)
        return ok([g.to_dict() for g in items], meta)

    # =========================================================================
    # CULTURA
    # =========================================================================

    @app.route('/api/cultura/museos', methods=['GET'])
    def cultura_museos():
        """
        Obtiene museos disponibles en la plataforma.
        PARA QUÉ: Descubrir museos y exposiciones
        USO: GET /api/cultura/museos
        RESPUESTA: Museos ordenados por valoración descendente
        """
        q = (Cultura.query
             .filter(Cultura.active == True)
             .filter(Cultura.tipo_lugar == 'museo')
             .order_by(Cultura.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([c.to_dict() for c in items], meta)

    @app.route('/api/cultura/patrimonio', methods=['GET'])
    def cultura_patrimonio():
        """
        Obtiene lugares de patrimonio cultural e histórico.
        PARA QUÉ: Explorar sitios históricos y arqueológicos
        USO: GET /api/cultura/patrimonio
        EJEMPLO: fetch('http://localhost:5000/api/cultura/patrimonio')
        """
        q = (Cultura.query
             .filter(Cultura.active == True)
             .filter(Cultura.tipo_lugar == 'patrimonio cultural')
             .order_by(Cultura.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([c.to_dict() for c in items], meta)

    @app.route('/api/cultura/visita-guiada', methods=['GET'])
    def cultura_visita_guiada():
        """
        Obtiene lugares culturales que ofrecen visitas guiadas.
        PARA QUÉ: Encontrar experiencias con guía especializado
        USO: GET /api/cultura/visita-guiada
        RESPUESTA: Lugares culturales con visita_guiada=true
        """
        q = (Cultura.query
             .filter(Cultura.active == True)
             .filter(Cultura.visita_guiada == True)
             .order_by(Cultura.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([c.to_dict() for c in items], meta)

    @app.route('/api/cultura/cerca-de-ti', methods=['GET'])
    def cultura_cerca_de_ti():
        """
        Obtiene lugares culturales en el municipio del usuario.
        PARA QUÉ: Descubrir cultura local sin viajar
        USO: GET /api/cultura/cerca-de-ti (requiere header X-User-Id)
        EJEMPLO: fetch('...', {headers: {'X-User-Id': userId}})
        """
        mun_id = get_municipality_id_from_request()
        if not mun_id:
            return err("Usuario no autenticado o sin municipio", 401)
        q = (Cultura.query
             .filter(Cultura.active == True)
             .filter(Cultura.municipality_id == mun_id)
             .order_by(Cultura.valoracion.desc().nullslast()))
        items, meta = paginate(q)
        return ok([c.to_dict() for c in items], meta)

    @app.route('/api/cultura', methods=['GET'])
    def cultura_todos():
        """
        Obtiene lista general de lugares culturales con filtros avanzados.
        PARA QUÉ: Búsqueda completa de patrimonio con múltiples criterios
        USO: GET /api/cultura?tipo_lugar=museo&visita_guiada=true
        RESPUESTA: Lugares ordenados por valoración descendente
        """
        q = Cultura.query.filter(Cultura.active == True)
        if request.args.get('municipality_id'):
            q = q.filter(Cultura.municipality_id == request.args.get('municipality_id', type=int))
        if request.args.get('tipo_lugar'):
            q = q.filter(Cultura.tipo_lugar == request.args.get('tipo_lugar'))
        if request.args.get('visita_guiada'):
            q = q.filter(Cultura.visita_guiada == (request.args.get('visita_guiada') == 'true'))
        q = q.order_by(Cultura.valoracion.desc().nullslast())
        items, meta = paginate(q)
        return ok([c.to_dict() for c in items], meta)

    # =========================================================================
    # PREFERENCIAS
    # =========================================================================

    @app.route('/usuarios/<int:user_id>/preferencias', methods=['GET'])
    def obtener_preferencias(user_id):
        """
        Obtiene las preferencias guardadas de un usuario.
        PARA QUÉ: Recuperar rango de precio, accesibilidad y municipios de interés
        USO: GET /usuarios/{user_id}/preferencias
        EJEMPLO: fetch('http://localhost:5000/usuarios/1/preferencias')
        """
        prefs = Preferencia.query.filter_by(user_id=user_id).first()
        if not prefs:
            return err("Preferencias no encontradas", 404)
        return ok(prefs.to_dict())

    @app.route('/usuarios/<int:user_id>/preferencias', methods=['PUT'])
    def actualizar_preferencias(user_id):
        """
        Actualiza las preferencias de un usuario.
        PARA QUÉ: Guardar cambios de rango, accesibilidad y municipios
        USO: PUT /usuarios/{user_id}/preferencias
        BODY: {"rango_precio": "alto", "movilidad_reducida": true, "municipios_interes": [1,5]}
        """
        data  = request.get_json()
        prefs = Preferencia.query.filter_by(user_id=user_id).first()
        if not prefs:
            return err("Preferencias no encontradas", 404)
        try:
            prefs.rango_precio       = data.get('rango_precio',       prefs.rango_precio)
            prefs.movilidad_reducida = data.get('movilidad_reducida', prefs.movilidad_reducida)
            if 'municipios_interes' in data:
                prefs.municipios_interes = [int(m) for m in data['municipios_interes']]
            prefs.updated_at = datetime.utcnow()
            db.session.commit()
            return ok({'mensaje': 'Preferencias actualizadas', 'data': prefs.to_dict()})
        except Exception as e:
            db.session.rollback()
            return err(str(e), 500)

    # =========================================================================
    # INTERESES
    # =========================================================================

    @app.route('/intereses', methods=['GET'])
    def listar_intereses():
        """
        Obtiene la lista completa de categorías de intereses.
        PARA QUÉ: Mostrar opciones al usuario para seleccionar preferencias
        USO: GET /intereses
        RESPUESTA: [{"id_interes": 1, "nombre": "Gastronomía"}, ...]
        """
        return ok([i.to_dict() for i in Interes.query.all()])

    @app.route('/usuarios/<int:user_id>/intereses', methods=['GET'])
    def obtener_intereses_usuario(user_id):
        """
        Obtiene los intereses seleccionados por un usuario.
        PARA QUÉ: Ver qué categorías ha seleccionado el usuario
        USO: GET /usuarios/{user_id}/intereses
        RESPUESTA: {"id_user": 1, "intereses": [1, 3, 5]}
        """
        uis = UserInteres.query.filter_by(id_user=user_id).all()
        return ok({'id_user': user_id, 'intereses': [ui.id_interes for ui in uis]})

    @app.route('/usuarios/<int:user_id>/intereses', methods=['POST'])
    def agregar_interes_usuario(user_id):
        """
        Agrega un nuevo interés a los favoritos del usuario.
        PARA QUÉ: El usuario selecciona nuevas categorías de interés
        USO: POST /usuarios/{user_id}/intereses
        BODY: {"id_interes": 3}
        EJEMPLO: fetch('...', {method:'POST', body: JSON.stringify({id_interes: 3})})
        """
        data       = request.get_json()
        id_interes = data.get('id_interes')
        if not id_interes:
            return err("id_interes es requerido")
        if not Interes.query.get(id_interes):
            return err("El interés no existe", 404)
        if UserInteres.query.filter_by(id_user=user_id, id_interes=id_interes).first():
            return ok({'mensaje': 'El usuario ya tiene este interés'})
        try:
            db.session.add(UserInteres(id_user=user_id, id_interes=id_interes))
            db.session.commit()
            return ok({'mensaje': 'Interés agregado'}, status=201)
        except Exception as e:
            db.session.rollback()
            return err(str(e), 500)

    @app.route('/usuarios/<int:user_id>/intereses/<int:id_interes>', methods=['DELETE'])
    def eliminar_interes_usuario(user_id, id_interes):
        """
        Elimina un interés de los favoritos del usuario.
        PARA QUÉ: El usuario quita categorías de sus intereses
        USO: DELETE /usuarios/{user_id}/intereses/{id_interes}
        EJEMPLO: fetch('...', {method: 'DELETE'})
        """
        rel = UserInteres.query.filter_by(id_user=user_id, id_interes=id_interes).first()
        if not rel:
            return err("Relación no encontrada", 404)
        try:
            db.session.delete(rel)
            db.session.commit()
            return ok({'mensaje': 'Interés eliminado'})
        except Exception as e:
            db.session.rollback()
            return err(str(e), 500)

    # =========================================================================
    # RESEÑAS
    # =========================================================================

    @app.route('/resenas', methods=['POST'])
    def crear_resena():
        """
        Crea una nueva reseña para un evento, restaurante o lugar cultural.
        PARA QUÉ: Los usuarios comparten experiencias y opiniones
        USO: POST /resenas
        BODY: {"user_id": 1, "entidad_tipo": "gastro", "entidad_id": 15,
               "puntuacion": 5, "texto": "Excelente"}
        RESPUESTA: {"data": {"mensaje": "Reseña creada", "id": 42}}
        """
        data = request.get_json()
        required = ['user_id', 'entidad_tipo', 'entidad_id', 'puntuacion']
        if not all(k in data for k in required):
            return err("Faltan campos obligatorios")
        if data['entidad_tipo'] not in ['event', 'gastro', 'cultura']:
            return err("Tipo de entidad inválido")
        if not (1 <= data['puntuacion'] <= 5):
            return err("La puntuación debe ser entre 1 y 5")
        fk_map = {'event': 'event_id', 'gastro': 'gastro_id', 'cultura': 'culture_id'}
        try:
            r = Resena(
                user_id=data['user_id'],
                puntuacion=data['puntuacion'],
                texto=data.get('texto', ''),
                **{fk_map[data['entidad_tipo']]: data['entidad_id']}
            )
            db.session.add(r)
            db.session.commit()
            return ok({'mensaje': 'Reseña creada', 'id': r.id}, status=201)
        except Exception as e:
            db.session.rollback()
            return err(str(e), 500)

    @app.route('/resenas/<string:entidad_tipo>/<int:entidad_id>', methods=['GET'])
    def obtener_resenas_entidad(entidad_tipo, entidad_id):
        """
        Obtiene todas las reseñas de un lugar/evento específico.
        PARA QUÉ: Ver opiniones de otros usuarios sobre el lugar
        USO: GET /resenas/{entidad_tipo}/{entidad_id}
               entidad_tipo: 'event'|'gastro'|'cultura'
        EJEMPLO: fetch('http://localhost:5000/resenas/gastro/15')
        RESPUESTA: [{"id": 42, "puntuacion": 5, "texto": "Excelente", ...}, ...]
        """
        if entidad_tipo not in ['event', 'gastro', 'cultura']:
            return err("Tipo inválido")
        fk_col = {'event': Resena.event_id, 'gastro': Resena.gastro_id, 'cultura': Resena.culture_id}
        resenas = Resena.query.filter(fk_col[entidad_tipo] == entidad_id).all()
        return ok([r.to_dict() for r in resenas])

    # =========================================================================
    # chatbot
    # =========================================================================

    @app.route('/api/chat', methods=['POST'])
    def chat_assistant():
        """
        PARA QUÉ SIRVE:
            - Devolver una sugerencia conversacional y una lista estructurada 
              de lugares o eventos con su "predicción de afinidad".
        
        CÓMO SE USA:
            POST /api/chat con JSON en body y header de autenticación.
        
        PARÁMETROS DE ENTRADA (Body JSON):
            - message (str): La petición del usuario en lenguaje natural.
            - session_id (str): Identificador único de la conversación actual.
        
        HEADERS REQUERIDOS:
            - X-User-Id (int): ID del usuario logueado (para personalización).
            - Content-Type: application/json
        
        EJEMPLO DE USO:
            // JavaScript
            const response = await fetch('http://localhost:5000/api/chat', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-User-Id': 1 
                },
                body: JSON.stringify({
                    message: 'Quiero comer algo típico en Bilbao',
                    session_id: 'conversacion-123'
                })
            });
            const data = await response.json();
        
        RESPUESTA ESPERADA (200):
            {
                "data": {
                    "suggestion": "Te propongo estos asadores...",
                    "items": [
                        {
                            "item_id": 15,
                            "nombre": "Asador Etxebarri",
                            "tipo": "lugar",
                            "categoria": "Asador",
                            "provincia": "Bizkaia",
                            "estrella_prevista": 4.9
                        }
                    ],
                    "consulta": {
                        "intencion": "lugares",
                        "provincia": "Bizkaia",
                        "intereses": [22],
                        "fecha_inicio": null,
                        "fecha_fin": null
                    },
                    "aviso": null
                }
            }
        
        ERRORES: 400 (Falta mensaje), 500 (Error interno del asistente)
        ═══════════════════════════════════════════════════════════════════════
        """
        data = request.get_json()
        if not data or 'message' not in data:
            return err("Falta el mensaje"), 400

        # Obtenemos el usuario del header de seguridad
        user_id = request.headers.get('X-User-Id', type=int)
        
        try:
            # Llamamos a la lógica interna (sin llamadas HTTP externas)
            respuesta = manejar_chat_flask(
                message=data['message'],
                session_id=data.get('session_id', 'demo'),
                user_id=user_id
            )
            
            # Devolvemos el diccionario compatible con jsonify
            return ok(respuesta.dict())
        
        except Exception as e:
            logging.error(f"Error en chat: {e}")
            return err(f"Error en el asistente: {str(e)}"), 500

# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return jsonify({"status": "ok",
                        "gastro": len(gastro), "cultura": len(patrimonio),
                        "eventos": len(eventos)})

    @app.route("/recomendaciones/gastro")
    def recomendaciones_gastro():
        user_id, top_n = _params_comunes()
        if user_id is None:
            return jsonify({"error": "user_id es obligatorio"}), 400

        tipo_lugar = request.args.get("tipo_lugar")
        provincia  = request.args.get("provincia")
        precio     = request.args.get("precio")

        catalogo = gastro
        if tipo_lugar:
            catalogo = catalogo[catalogo["Tipo de lugar"].map(_norm_txt) == _norm_txt(tipo_lugar)]
        if provincia:
            cod = _cod_provincia(provincia)
            if cod is None:
                return _respuesta(user_id, "gastro", SIN_RESULTADOS)
            catalogo = catalogo[catalogo["Provincia"].map(_cod_provincia) == cod]
        if precio:
            catalogo = catalogo[catalogo["Nivel precio"].map(_norm_txt) == _norm_txt(precio)]

        resultado = _rankear(user_id, model_gastro, reviews_gastro, catalogo,
                                "gastro_id", top_n, con_patrocinados=True)
        return _respuesta(user_id, "gastro", resultado)

    @app.route("/recomendaciones/cultura")
    def recomendaciones_cultura():
        user_id, top_n = _params_comunes()
        if user_id is None:
            return jsonify({"error": "user_id es obligatorio"}), 400

        tipo_lugar = request.args.get("tipo_lugar")
        provincia  = request.args.get("provincia")

        catalogo = patrimonio
        if tipo_lugar:
            catalogo = catalogo[catalogo["Tipo de lugar"].map(_norm_txt) == _norm_txt(tipo_lugar)]
        if provincia:
            cod = _cod_provincia(provincia)
            if cod is None:
                return _respuesta(user_id, "cultura", SIN_RESULTADOS)
            catalogo = catalogo[catalogo["Provincia"].map(_cod_provincia) == cod]

        resultado = _rankear(user_id, model_cultura, reviews_cultura, catalogo,
                                "culture_id", top_n, con_patrocinados=True)
        return _respuesta(user_id, "cultura", resultado)

    @app.route("/recomendaciones/eventos")
    def recomendaciones_eventos():
        user_id, top_n = _params_comunes()
        if user_id is None:
            return jsonify({"error": "user_id es obligatorio"}), 400

        tipo            = request.args.get("tipo")
        provincia       = request.args.get("provincia")
        solo_gratis     = request.args.get("gratis", "false").lower() == "true"
        solo_fin_semana = request.args.get("finde",  "false").lower() == "true"

        catalogo = eventos
        if tipo:
            catalogo = catalogo[catalogo["typeEs"].map(_norm_txt) == _norm_txt(tipo)]
        if provincia:
            cod = _cod_provincia(provincia)
            if cod is None:
                return _respuesta(user_id, "eventos", SIN_RESULTADOS)
            catalogo = catalogo[catalogo["provinceNoraCode"] == int(cod)]
        if solo_gratis:
            catalogo = catalogo[catalogo["is_free"] == True]
        if solo_fin_semana:
            catalogo = catalogo[catalogo["is_weekend"] == True]

        resultado = _rankear(user_id, model_eventos, reviews_eventos, catalogo,
                                "event_id", top_n, con_patrocinados=False)
        return _respuesta(user_id, "eventos", resultado)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
