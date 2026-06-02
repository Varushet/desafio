from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

# --- ESQUEMA USER_DATA ---

class Usuario(db.Model):
    """
    MODELO: Usuario (Tabla users en esquema user_data)
    
    DESCRIPCIÓN:
        Representa un usuario registrado en la plataforma SustraiApp.
        Almacena información personal, ubicación y credenciales de autenticación.
    
    CAMPOS:
        - id: Identificador único
        - nombre: Nombre del usuario (max 50 caracteres)
        - apellido: Apellido (opcional)
        - email: Email único para login (max 100 caracteres)
        - password_hash: Contraseña encriptada (nunca se guarda en texto plano)
        - tlf: Teléfono (opcional, max 20)
        - municipio: Municipio de residencia (max 100)
        - provincia: Provincia (max 50)
        - sexo: Género (max 10 caracteres)
        - age: Edad (integer)
        - role: Rol del usuario (default: 'user')
        - created_at: Timestamp de creación
        - updated_at: Timestamp de última actualización
    
    MÉTODOS:
        - set_password(password): Encripta y almacena la contraseña
        - check_password(password): Verifica la contraseña
        - to_dict(): Devuelve el usuario en formato JSON
    
    EJEMPLO:
        {
            "id_user": 1,
            "nombre": "Juan",
            "apellido": "García",
            "email": "juan@example.com",
            "municipio": "Madrid",
            "provincia": "Madrid",
            "sexo": "M",
            "age": 28,
            "role": "user"
        }
    """
    __tablename__ = 'users'
    __table_args__ = {'schema': 'user_data'}

    id_user = db.Column('id_user', db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    tlf = db.Column(db.String(20))
    municipio = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(50), nullable=False)
    sexo = db.Column(db.String(10), nullable=False) # Check constraint se maneja en DB o validación app
    age = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id_user,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'email': self.email,
            'municipio': self.municipio,
            'provincia': self.provincia,
            'sexo': self.sexo,
            'age': self.age,
            'role': self.role
        }

class Preferencia(db.Model):
    """
    MODELO: Preferencias del Usuario (Tabla preferences en esquema user_data)
    
    DESCRIPCIÓN:
        Almacena las preferencias personalizadas de cada usuario: qué tipos de 
        actividades le gustan, rango de precio, necesidades de accesibilidad, etc.
        Se crea automáticamente al registrar un nuevo usuario.
    
    CAMPOS:
        - id: Identificador único
        - user_id: ID del usuario propietario (Foreign Key, único)
        - le_gusta_gastro: Boolean, prefiere actividades gastronómicas
        - le_gusta_cultura: Boolean, prefiere eventos culturales
        - le_gusta_eventos: Boolean, prefiere eventos en general
        - le_gusta_compras: Boolean, prefiere experiencias de compra
        - rango_precio: String (ej: "bajo", "medio", "alto")
        - movilidad_reducida: Boolean, requiere accesibilidad
        - municipios_interes: JSONB array de municipios de interés (ej: ["Madrid", "Barcelona"])
        - updated_at: Timestamp de última actualización
    
    EJEMPLO:
        {
            "id": 1,
            "user_id": 1,
            "le_gusta_gastro": true,
            "le_gusta_cultura": false,
            "le_gusta_eventos": true,
            "le_gusta_compras": false,
            "rango_precio": "medio",
            "movilidad_reducida": false,
            "municipios_interes": ["Madrid", "Barcelona"]
        }
    """
    __tablename__ = 'preferences'
    __table_args__ = {'schema': 'user_data'}
    
    id = db.Column(db.Integer, primary_key=True) 

    user_id = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), unique=True, nullable=False)
    le_gusta_gastro = db.Column(db.Boolean, default=False)
    le_gusta_cultura = db.Column(db.Boolean, default=False)
    le_gusta_eventos = db.Column(db.Boolean, default=False)
    le_gusta_compras = db.Column(db.Boolean, default=False)
    rango_precio = db.Column(db.String(10))
    movilidad_reducida = db.Column(db.Boolean, default=False)
    municipios_interes = db.Column(JSONB) # Usa JSONB de PostgreSQL
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'le_gusta_gastro': self.le_gusta_gastro,
            'le_gusta_cultura': self.le_gusta_cultura,
            'le_gusta_eventos': self.le_gusta_eventos,
            'le_gusta_compras': self.le_gusta_compras,
            'rango_precio': self.rango_precio,
            'movilidad_reducida': self.movilidad_reducida,
            'municipios_interes': self.municipios_interes
        }

class Resena(db.Model):
    """
    MODELO: Reseñas/Reviews (Tabla reviews en esquema user_data)
    
    DESCRIPCIÓN:
        Almacena las reseñas (reviews) que los usuarios hacen sobre eventos,
        restaurantes, lugares culturales, etc. Usa un patrón polimórfico donde
        entidad_tipo indica qué tipo de cosa se reseña.
    
    CAMPOS:
        - id: Identificador único
        - user_id: ID del usuario que hace la reseña (Foreign Key)
        - entidad_tipo: Tipo de entidad reseñada ('event', 'gastro', 'cultura')
        - entidad_id: ID de la entidad específica a reseñar
        - puntuacion: Calificación entre 1 y 5 estrellas
        - texto: Opinión/comentario del usuario (Text, max ~1000 caracteres)
        - created_at: Timestamp de cuándo se hizo la reseña
    
    EJEMPLOS:
        Reseña de un restaurante:
        {
            "id": 1,
            "user_id": 1,
            "entidad_tipo": "gastro",
            "entidad_id": 42,
            "puntuacion": 4,
            "texto": "Excelente comida, muy recomendado."
        }
        
        Reseña de un evento:
        {
            "id": 2,
            "user_id": 2,
            "entidad_tipo": "event",
            "entidad_id": 101,
            "puntuacion": 5,
            "texto": "Festival increíble, volvería sin dudarlo."
        }
    """
    __tablename__ = 'reviews'
    __table_args__ = {'schema': 'user_data'}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), nullable=False)
    entidad_tipo = db.Column(db.String(50), nullable=False)
    entidad_id = db.Column(db.Integer, nullable=False)
    puntuacion = db.Column(db.Integer, nullable=False)
    texto = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'entidad_tipo': self.entidad_tipo,
            'entidad_id': self.entidad_id,
            'puntuacion': self.puntuacion,
            'texto': self.texto,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# --- ESQUEMA MARKET_DATA ---

class Evento(db.Model):
    """
    MODELO: Eventos (Tabla events en esquema market_data)
    
    DESCRIPCIÓN:
        Representa los eventos disponibles en la plataforma. Los datos
        provienen de una fuente externa (ej: carga de datos) y se actualizan
        periódicamente. Es la fuente de información sobre qué evento sucede.
    
    CAMPOS:
        - id: Identificador único (string, ej: "evt_001")
        - type_es: Tipo de evento en español (ej: "Concierto", "Festival")
        - name_es: Nombre del evento en español
        - start_date: Fecha/hora de inicio
        - end_date: Fecha/hora de finalización
        - municipality_es: Municipio donde ocurre
        - price_eur: Precio en euros (numérico con 2 decimales)
        - is_free: Boolean, indica si es gratis
    
    EJEMPLO:
        {
            "id": "evt_001",
            "name_es": "Festival de Música Urbana",
            "start_date": "2026-06-15T18:00:00",
            "municipality_es": "Madrid",
            "price_eur": 25.50
        }
    """
    __tablename__ = 'events'
    __table_args__ = {'schema': 'market_data'}

    id = db.Column(db.String(50), primary_key=True)
    type_es = db.Column(db.String(100))
    name_es = db.Column(db.Text)
    start_date = db.Column(db.DateTime(timezone=True))
    end_date = db.Column(db.DateTime(timezone=True))
    municipality_es = db.Column(db.String(100))
    price_eur = db.Column(db.Numeric(10, 2))
    is_free = db.Column(db.Boolean, default=False)
    # ... añade el resto de campos si los necesitas consultar

    def to_dict(self):
        return {
            'id': self.id,
            'name_es': self.name_es,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'municipality_es': self.municipality_es,
            'price_eur': float(self.price_eur) if self.price_eur else None
        }

class Gastronomia(db.Model):
    """
    MODELO: Lugares Gastronómicos (Tabla gastronomy en esquema market_data)
    
    DESCRIPCIÓN:
        Representa restaurantes, bares, cafés y otros lugares de comida
        disponibles en la plataforma. Incluye información de ubicación y 
        clasificación gastronómica.
    
    CAMPOS:
        - id: Identificador único
        - nombre: Nombre del establecimiento
        - municipio: Municipio donde está ubicado
        - provincia: Provincia
        - latitud: Coordenada GPS (formato WGS84)
        - longitud: Coordenada GPS (formato WGS84)
        - tipo_comida: Tipo de cocina (ej: "Italiana", "Japonesa", "Fusion")
        - valoracion: Puntuación promedio (0-5, con 1 decimal)
    
    EJEMPLO:
        {
            "id": 42,
            "nombre": "Restaurante Casa García",
            "municipio": "Madrid",
            "provincia": "Madrid",
            "tipo_comida": "Española",
            "valoracion": 4.5
        }
    """
    __tablename__ = 'gastronomy'
    __table_args__ = {'schema': 'market_data'}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    municipio = db.Column(db.String(100))
    provincia = db.Column(db.String(50))
    latitud = db.Column(db.Numeric(9, 6))
    longitud = db.Column(db.Numeric(9, 6))
    tipo_comida = db.Column(db.String(100))
    valoracion = db.Column(db.Numeric(3, 1))
    michelin = db.Column(db.Boolean, default=False)
    repsol = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)
    google_place_id = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'municipio': self.municipio,
            'tipo_comida': self.tipo_comida,
            'valoracion': float(self.valoracion) if self.valoracion else None
        }

class Cultura(db.Model):
    """
    MODELO: Lugares Culturales (Tabla culture en esquema market_data)
    
    DESCRIPCIÓN:
        Representa museos, galerías, teatros, monumentos y otros lugares
        de interés cultural. Almacena información de ubicación geográfica
        para facilitar búsquedas y recomendaciones por proximidad.
    
    CAMPOS:
        - id: Identificador único
        - nombre: Nombre del lugar cultural
        - tipo_lugar: Clasificación (ej: "Museo", "Teatro", "Galería", "Monumento")
        - municipio: Municipio donde está ubicado
        - provincia: Provincia
        - lat_wgs84: Latitud en formato WGS84
        - lon_wgs84: Longitud en formato WGS84
    
    EJEMPLO:
        {
            "id": 15,
            "nombre": "Museo del Prado",
            "tipo_lugar": "Museo",
            "municipio": "Madrid",
            "provincia": "Madrid"
        }
    """
    __tablename__ = 'culture'
    __table_args__ = {'schema': 'market_data'}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    tipo_lugar = db.Column(db.String(100))
    municipio = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(100), nullable=False)
    lat_wgs84 = db.Column(db.Numeric(9, 6))
    lon_wgs84 = db.Column(db.Numeric(9, 6))

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'tipo_lugar': self.tipo_lugar,
            'municipio': self.municipio
        }
        
class Interes(db.Model):
    """
    MODELO: Intereses/Categorías (Tabla interests en esquema user_data)
    
    DESCRIPCIÓN:
        Representa las categorías de interés disponibles en la plataforma.
        Soporta estructura jerárquica mediante self-referencing (father_id).
    
    CAMPOS:
        - id_interes: Identificador único (PK)
        - nombre: Nombre de la categoría (ej: "Gastronomía", "Restaurantes")
        - descripcion: Texto descriptivo (opcional)
        - father_id: ID del interés padre para crear jerarquía (opcional)
        - created_at: Timestamp de creación
    
    EJEMPLOS DE DATOS:
        - Raíz: {id_interes: 1, nombre: "Gastronomía", father_id: null}
        - Hijo: {id_interes: 2, nombre: "Restaurantes", father_id: 1}
        - Hijo: {id_interes: 3, nombre: "Bares", father_id: 1}
    """
    __tablename__ = 'interests'
    __table_args__ = {'schema': 'user_data'}

    id_interes = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    father_id = db.Column(db.Integer, db.ForeignKey('user_data.interests.id_interes'))  # Para jerarquía
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_interes': self.id_interes,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'father_id': self.father_id
        }

class UserInteres(db.Model):
    """
    MODELO: Relación Usuario-Intereses (Tabla user_interests en esquema user_data)
    
    DESCRIPCIÓN:
        Tabla de unión (many-to-many) que conecta usuarios con sus intereses.
        Un usuario puede tener múltiples intereses y un interés puede 
        ser seleccionado por múltiples usuarios.
    
    CAMPOS:
        - id_user: ID del usuario (PK, Foreign Key)
        - id_interes: ID del interés (Foreign Key)
        - created_at: Timestamp de cuándo se agregó el interés
    
    EJEMPLO:
        Usuario 1 selecciona intereses [5, 7, 12]
        → Crea 3 registros en UserInteres con id_user=1
    """
    __tablename__ = 'user_interests'
    __table_args__ = {'schema': 'user_data'}

    id_user = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), primary_key=True, nullable=False)
    id_interes = db.Column(db.Integer, db.ForeignKey('user_data.interests.id_interes'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id_user': self.id_user,
            'id_interes': self.id_interes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }