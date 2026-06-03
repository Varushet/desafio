from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Integer

db = SQLAlchemy()

# =============================================================================
# ESQUEMA: shared
# =============================================================================

class Municipio(db.Model):
    """
    Fuente única de verdad geográfica.
    Referenciado por Usuario, Evento, Gastronomia y Cultura mediante municipality_id.

    Uso típico:
        municipios = Municipio.query.order_by(Municipio.nombre).all()
        # → para poblar un selector en el frontend al registrarse
    """
    __tablename__ = 'municipalities'
    __table_args__ = {'schema': 'shared'}

    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    provincia     = db.Column(db.String(50),  nullable=False)
    nora_code     = db.Column(db.String(20),  unique=True)
    province_code = db.Column(db.String(5))
    lat           = db.Column(db.Float)
    lng           = db.Column(db.Float)

    def to_dict(self):
        return {
            'id':            self.id,
            'nombre':        self.nombre,
            'provincia':     self.provincia,
            'province_code': self.province_code,
            'lat':           self.lat,
            'lng':           self.lng,
        }


# =============================================================================
# ESQUEMA: market_data
# =============================================================================

class Evento(db.Model):
    """
    Eventos culturales, musicales y de ocio de Euskadi.
    external_id almacena el ID de Kulturklik u otras fuentes externas (opcional).

    Uso típico:
        Evento.query.filter_by(active=True).order_by(Evento.start_date).all()
    """
    __tablename__ = 'events'
    __table_args__ = {'schema': 'market_data'}

    id               = db.Column(db.Integer, primary_key=True)
    external_id      = db.Column(db.String(100), unique=True)       # ID Kulturklik u otra fuente
    municipality_id  = db.Column(db.Integer, db.ForeignKey('shared.municipalities.id'), nullable=False)
    type             = db.Column(db.String(50))
    subtipo          = db.Column(db.String(100))
    start_date       = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date         = db.Column(db.DateTime(timezone=True), nullable=False)
    publication_date = db.Column(db.DateTime(timezone=True))
    language         = db.Column(db.String(10))
    opening_hours    = db.Column(db.String(100))
    price_eur        = db.Column(db.Float)
    is_free          = db.Column(db.Boolean, default=False)
    is_sponsored     = db.Column(db.Boolean, default=False)
    purchase_url     = db.Column(db.Text)
    url_event        = db.Column(db.Text)
    url_online       = db.Column(db.Text)
    images           = db.Column(JSONB)
    online           = db.Column(db.Boolean, default=False)
    establishment    = db.Column(db.String(255))
    place            = db.Column(db.String(255))
    company          = db.Column(db.String(255))
    active           = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    municipio = db.relationship('Municipio', foreign_keys=[municipality_id])

    def to_dict(self):
        return {
            'id':              self.id,
            'external_id':     self.external_id,
            'municipality_id': self.municipality_id,
            'municipio':       self.municipio.nombre if self.municipio else None,
            'type':            self.type,
            'subtipo':         self.subtipo,
            'start_date':      self.start_date.isoformat() if self.start_date else None,
            'end_date':        self.end_date.isoformat() if self.end_date else None,
            'language':        self.language,
            'opening_hours':   self.opening_hours,
            'price_eur':       self.price_eur,
            'is_free':         self.is_free,
            'is_sponsored':    self.is_sponsored,
            'purchase_url':    self.purchase_url,
            'url_event':       self.url_event,
            'url_online':      self.url_online,
            'images':          self.images,
            'online':          self.online,
            'establishment':   self.establishment,
            'place':           self.place,
            'company':         self.company,
            'active':          self.active,
            'created_at':      self.created_at.isoformat() if self.created_at else None,
        }


class Qualification(db.Model):
    """
    Catálogo de distinciones gastronómicas.
    Valores iniciales: Sol Repsol, Estrella Michelin, Denominación de Origen,
                       Q de Calidad, Eusko Label, Agricultura Ecológica, Euskal Baserri.

    Uso típico:
        Qualification.query.all()
        # → para mostrar las distinciones disponibles en un panel de administración
    """
    __tablename__ = 'qualifications'
    __table_args__ = {'schema': 'market_data'}

    id     = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True)   # clave estable para filtros internos
    nombre = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id':     self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
        }


class GastronomyQualification(db.Model):
    """
    Relación M:N entre establecimientos y distinciones.
    Un restaurante puede tener varias distinciones; una distinción
    puede asignarse a varios restaurantes.

    Uso típico:
        GastronomyQualification.query.filter_by(gastronomy_id=5).all()
        # → para mostrar las distinciones de un restaurante concreto
    """
    __tablename__ = 'gastronomy_qualifications'
    __table_args__ = {'schema': 'market_data'}

    id               = db.Column(db.Integer, primary_key=True)
    gastronomy_id    = db.Column(db.Integer, db.ForeignKey('market_data.gastronomy.id'), nullable=False)
    qualification_id = db.Column(db.Integer, db.ForeignKey('market_data.qualifications.id'), nullable=False)

    qualification = db.relationship('Qualification')

    def to_dict(self):
        return {
            'id':               self.id,
            'gastronomy_id':    self.gastronomy_id,
            'qualification_id': self.qualification_id,
            'qualification':    self.qualification.to_dict() if self.qualification else None,
        }


class Gastronomia(db.Model):
    """
    Restaurantes, asadores, sidrerías y otros establecimientos gastronómicos.
    michelin y repsol se han trasladado a gastronomy_qualifications.
    Accede a las distinciones del establecimiento a través de la relación
    `cualificaciones`.

    Uso típico:
        g = Gastronomia.query.get(5)
        g.to_dict()  # incluye lista de cualificaciones
    """
    __tablename__ = 'gastronomy'
    __table_args__ = {'schema': 'market_data'}

    id                    = db.Column(db.Integer, primary_key=True)
    external_id           = db.Column(db.String(100), unique=True)   # google_place_id u otra fuente
    nombre                = db.Column(db.String(255), nullable=False)
    descripcion           = db.Column(db.Text)
    municipality_id       = db.Column(db.Integer, db.ForeignKey('shared.municipalities.id'), nullable=False)
    lat                   = db.Column(db.Float)
    lng                   = db.Column(db.Float)
    type                  = db.Column(db.String(50))
    tipo_comida           = db.Column(db.String(100))
    entorno               = db.Column(db.String(100))
    email                 = db.Column(db.String(100))
    web                   = db.Column(db.Text)
    web_euskadi           = db.Column(db.Text)
    categoria             = db.Column(db.String(50))
    calidad               = db.Column(db.Boolean, default=False)
    url_imagen            = db.Column(db.Text)
    valoracion            = db.Column(db.Float)
    num_resenas           = db.Column(db.Integer)
    nivel_precio          = db.Column(db.String(50))
    national_phone_number = db.Column(db.String(20))
    is_sponsored          = db.Column(db.Boolean, default=False)
    active                = db.Column(db.Boolean, default=True)
    created_at            = db.Column(db.DateTime, default=datetime.utcnow)

    municipio       = db.relationship('Municipio', foreign_keys=[municipality_id])
    cualificaciones = db.relationship('GastronomyQualification', backref='gastronomy',
                                      cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id':                    self.id,
            'external_id':           self.external_id,
            'nombre':                self.nombre,
            'descripcion':           self.descripcion,
            'municipality_id':       self.municipality_id,
            'municipio':             self.municipio.nombre if self.municipio else None,
            'lat':                   self.lat,
            'lng':                   self.lng,
            'tipo_comida':           self.tipo_comida,
            'entorno':               self.entorno,
            'email':                 self.email,
            'web':                   self.web,
            'categoria':             self.categoria,
            'url_imagen':            self.url_imagen,
            'valoracion':            self.valoracion,
            'num_resenas':           self.num_resenas,
            'nivel_precio':          self.nivel_precio,
            'national_phone_number': self.national_phone_number,
            'is_sponsored':          self.is_sponsored,
            'active':                self.active,
            'created_at':            self.created_at.isoformat() if self.created_at else None,
            # Lista de distinciones del establecimiento
            'cualificaciones': [gq.qualification.to_dict()
                                for gq in self.cualificaciones
                                if gq.qualification],
        }


class Cultura(db.Model):
    """
    Museos, teatros, patrimonio cultural y otros espacios de interés.
    external_id almacena el ID de Google Places, Kulturklik u otra fuente.

    Uso típico:
        Cultura.query.filter_by(tipo_lugar='museo', active=True)
                     .order_by(Cultura.valoracion.desc()).all()
    """
    __tablename__ = 'culture'
    __table_args__ = {'schema': 'market_data'}

    id                  = db.Column(db.Integer, primary_key=True)
    external_id         = db.Column(db.String(100), unique=True)
    fuente              = db.Column(db.String(50), nullable=False, default='Manual')
    nombre              = db.Column(db.String(255), nullable=False)
    tipo_lugar          = db.Column(db.String(100), nullable=False)
    tipo_cultura        = db.Column(db.String(100))
    descripcion         = db.Column(db.Text)
    precio              = db.Column(db.String(100))
    horario             = db.Column(JSONB)
    telefono            = db.Column(db.String(50))
    email               = db.Column(db.String(100))
    web                 = db.Column(db.String(255))
    web_amigable        = db.Column(db.String(255))
    imagen_url          = db.Column(db.Text)
    municipality_id     = db.Column(db.Integer, db.ForeignKey('shared.municipalities.id'), nullable=False)
    direccion           = db.Column(db.String(255))
    codigo_postal       = db.Column(db.String(10))
    visita_guiada       = db.Column(db.Boolean, default=False)
    capacidad           = db.Column(db.Integer)
    tienda              = db.Column(db.Boolean, default=False)
    lat                 = db.Column(db.Float, nullable=False)
    lng                 = db.Column(db.Float, nullable=False)
    valoracion          = db.Column(db.Float)
    numero_valoraciones = db.Column(db.Integer)
    is_sponsored        = db.Column(db.Boolean, default=False)
    active              = db.Column(db.Boolean, default=True)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    municipio = db.relationship('Municipio', foreign_keys=[municipality_id])

    def to_dict(self):
        return {
            'id':                  self.id,
            'external_id':         self.external_id,
            'fuente':              self.fuente,
            'nombre':              self.nombre,
            'tipo_lugar':          self.tipo_lugar,
            'tipo_cultura':        self.tipo_cultura,
            'descripcion':         self.descripcion,
            'precio':              self.precio,
            'horario':             self.horario,
            'telefono':            self.telefono,
            'email':               self.email,
            'web':                 self.web,
            'web_amigable':        self.web_amigable,
            'imagen_url':          self.imagen_url,
            'municipality_id':     self.municipality_id,
            'municipio':           self.municipio.nombre if self.municipio else None,
            'direccion':           self.direccion,
            'codigo_postal':       self.codigo_postal,
            'visita_guiada':       self.visita_guiada,
            'capacidad':           self.capacidad,
            'tienda':              self.tienda,
            'lat':                 self.lat,
            'lng':                 self.lng,
            'valoracion':          self.valoracion,
            'numero_valoraciones': self.numero_valoraciones,
            'is_sponsored':        self.is_sponsored,
            'active':              self.active,
            'created_at':          self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# ESQUEMA: user_data
# =============================================================================

class Usuario(db.Model):
    """
    Usuario registrado en la aplicación.
    municipality_id apunta a shared.municipalities (no strings de texto).

    Uso típico:
        u = Usuario.query.filter_by(email='test@sustraiapp.com').first()
        u.check_password('12345678')  # → True/False
    """
    __tablename__ = 'users'
    __table_args__ = {'schema': 'user_data'}

    id_user         = db.Column('id_user', db.Integer, primary_key=True)
    nombre          = db.Column(db.String(100), nullable=False)
    apellido        = db.Column(db.String(100))
    email           = db.Column(db.String(255), unique=True, nullable=False)
    password_hash   = db.Column(db.String(256), nullable=False)
    tlf             = db.Column(db.String(20))
    municipality_id = db.Column(db.Integer, db.ForeignKey('shared.municipalities.id'), nullable=False)
    sexo            = db.Column(db.String(10), nullable=False)
    age             = db.Column(db.Integer,    nullable=False)
    role            = db.Column(db.String(10), nullable=False, default='user')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    municipio = db.relationship('Municipio', foreign_keys=[municipality_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id_user':         self.id_user,
            'nombre':          self.nombre,
            'apellido':        self.apellido,
            'email':           self.email,
            'municipality_id': self.municipality_id,
            'municipio':       self.municipio.nombre   if self.municipio else None,
            'provincia':       self.municipio.provincia if self.municipio else None,
            'sexo':            self.sexo,
            'age':             self.age,
            'role':            self.role,
        }


class Interes(db.Model):
    """
    Árbol de categorías de interés (nivel 0 raíz → nivel 2 hoja).
    Ejemplos: Eventos > Concierto / Gastronomía > Restaurantes > Asador

    Uso típico:
        Interes.query.filter_by(level=0).all()   # solo raíces
        Interes.query.filter_by(father_id=2).all()  # hijos de Gastronomía
    """
    __tablename__ = 'interests'
    __table_args__ = {'schema': 'user_data'}

    id_interes = db.Column(db.Integer, primary_key=True)
    nombre     = db.Column(db.String(100), nullable=False)
    father_id  = db.Column(db.Integer, db.ForeignKey('user_data.interests.id_interes'))
    level      = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            'id_interes': self.id_interes,
            'nombre':     self.nombre,
            'father_id':  self.father_id,
            'level':      self.level,
        }


class UserInteres(db.Model):
    """
    Relación M:N entre usuarios e intereses.
    Reemplaza los booleans le_gusta_* de la versión anterior.

    Uso típico:
        UserInteres.query.filter_by(id_user=7).all()
        # → lista de id_interes seleccionados por el usuario 7
    """
    __tablename__ = 'user_interests'
    __table_args__ = {'schema': 'user_data'}

    id_user    = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'),
                           primary_key=True, nullable=False)
    id_interes = db.Column(db.Integer, db.ForeignKey('user_data.interests.id_interes'),
                           primary_key=True, nullable=False)

    def to_dict(self):
        return {'id_user': self.id_user, 'id_interes': self.id_interes}


class Preferencia(db.Model):
    """
    Preferencias generales del usuario: precio, movilidad y municipios de interés.
    Se crea automáticamente al registrar el usuario (con valores por defecto).
    municipios_interes es un array de IDs de shared.municipalities.

    Uso típico:
        prefs = Preferencia.query.filter_by(user_id=7).first()
        prefs.municipios_interes  # → [1, 3]  (IDs de Bilbao y Barakaldo)
    """
    __tablename__ = 'preferences'
    __table_args__ = {'schema': 'user_data'}

    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'),
                                   unique=True, nullable=False)
    rango_precio       = db.Column(db.String(10))
    movilidad_reducida = db.Column(db.Boolean, default=False)
    municipios_interes = db.Column(ARRAY(Integer), default=list)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                 self.id,
            'user_id':            self.user_id,
            'rango_precio':       self.rango_precio,
            'movilidad_reducida': self.movilidad_reducida,
            'municipios_interes': self.municipios_interes or [],
        }


class Resena(db.Model):
    """
    Reseña de un usuario sobre un evento, establecimiento o lugar cultural.
    Exactamente una de las tres FKs (event_id, gastro_id, culture_id) debe tener valor;
    el resto son NULL. El CHECK de la BD garantiza esto a nivel de base de datos.

    Uso típico — crear reseña de un restaurante:
        r = Resena(user_id=7, gastro_id=42, puntuacion=4, texto='Muy buena txuleta')
        db.session.add(r); db.session.commit()

    Uso típico — leer reseñas de un evento:
        Resena.query.filter_by(event_id=18).all()
    """
    __tablename__ = 'reviews'
    __table_args__ = {'schema': 'user_data'}

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'),   nullable=False)
    event_id   = db.Column(db.Integer, db.ForeignKey('market_data.events.id'),     nullable=True)
    gastro_id  = db.Column(db.Integer, db.ForeignKey('market_data.gastronomy.id'), nullable=True)
    culture_id = db.Column(db.Integer, db.ForeignKey('market_data.culture.id'),    nullable=True)
    puntuacion = db.Column(db.Integer, nullable=False)
    texto      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def entidad_tipo(self):
        if self.event_id:   return 'event'
        if self.gastro_id:  return 'gastro'
        if self.culture_id: return 'cultura'

    def entidad_id_val(self):
        return self.event_id or self.gastro_id or self.culture_id

    def to_dict(self):
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'entidad_tipo': self.entidad_tipo(),
            'entidad_id':   self.entidad_id_val(),
            'puntuacion':   self.puntuacion,
            'texto':        self.texto,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
        }


class Favorito(db.Model):
    """
    Ítems guardados como favoritos por el usuario.
    entidad_tipo: 'evento' | 'gastronomia' | 'cultura'
    UNIQUE (user_id, entidad_id, entidad_tipo) impide duplicados.

    Uso típico — guardar favorito:
        f = Favorito(user_id=7, entidad_id=42, entidad_tipo='gastronomia')
        db.session.add(f); db.session.commit()

    Uso típico — listar favoritos de un usuario:
        Favorito.query.filter_by(user_id=7).all()
    """
    __tablename__ = 'favorites'
    __table_args__ = {'schema': 'user_data'}

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), nullable=False)
    entidad_id   = db.Column(db.Integer, nullable=False)
    entidad_tipo = db.Column(db.String(20), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'entidad_id':   self.entidad_id,
            'entidad_tipo': self.entidad_tipo,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
        }