from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Integer

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# ESQUEMA: shared
# ---------------------------------------------------------------------------

class Municipio(db.Model):
    __tablename__ = 'municipalities'
    __table_args__ = {'schema': 'shared'}

    id             = db.Column(db.Integer, primary_key=True)
    nombre         = db.Column(db.String(100), nullable=False)
    provincia      = db.Column(db.String(50), nullable=False)
    nora_code      = db.Column(db.String(20), unique=True)
    province_code  = db.Column(db.String(5))
    lat            = db.Column(db.Float)
    lng            = db.Column(db.Float)

    def to_dict(self):
        return {
            'id':           self.id,
            'nombre':       self.nombre,
            'provincia':    self.provincia,
            'province_code': self.province_code,
            'lat':          self.lat,
            'lng':          self.lng,
        }

# ---------------------------------------------------------------------------
# ESQUEMA: market_data
# ---------------------------------------------------------------------------

class Evento(db.Model):
    __tablename__ = 'events'
    __table_args__ = {'schema': 'market_data'}

    id              = db.Column(db.Integer, primary_key=True)
    id_kulturklik   = db.Column(db.String(50), unique=True, nullable=False)
    municipality_id = db.Column(db.Integer, db.ForeignKey('shared.municipalities.id'), nullable=False)
    type            = db.Column(db.String(50))
    subtipo         = db.Column(db.String(100))
    start_date      = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date        = db.Column(db.DateTime(timezone=True), nullable=False)
    publication_date = db.Column(db.DateTime(timezone=True))
    language        = db.Column(db.String(10))
    opening_hours   = db.Column(db.String(100))
    price_eur       = db.Column(db.Float)
    is_free         = db.Column(db.Boolean, default=False)
    purchase_url    = db.Column(db.Text)
    url_event       = db.Column(db.Text)
    url_online      = db.Column(db.Text)
    images          = db.Column(JSONB)
    online          = db.Column(db.Boolean, default=False)
    establishment   = db.Column(db.String(255))
    place           = db.Column(db.String(255))
    company         = db.Column(db.String(255))
    active          = db.Column(db.Boolean, default=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    municipio       = db.relationship('Municipio', foreign_keys=[municipality_id])

    def to_dict(self):
        return {
            'id':             self.id,
            'id_kulturklik':  self.id_kulturklik,
            'municipality_id': self.municipality_id,
            'municipio':      self.municipio.nombre if self.municipio else None,
            'type':           self.type,
            'subtipo':        self.subtipo,
            'start_date':     self.start_date.isoformat() if self.start_date else None,
            'end_date':       self.end_date.isoformat() if self.end_date else None,
            'price_eur':      self.price_eur,
            'is_free':        self.is_free,
            'place':          self.place,
            'online':         self.online,
            'active':         self.active,
        }


class Gastronomia(db.Model):
    __tablename__ = 'gastronomy'
    __table_args__ = {'schema': 'market_data'}

    id                    = db.Column(db.Integer, primary_key=True)
    google_place_id       = db.Column(db.String(100), unique=True, nullable=False)
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
    michelin              = db.Column(db.Boolean, default=False)
    repsol                = db.Column(db.Boolean, default=False)
    active                = db.Column(db.Boolean, default=True)
    created_at            = db.Column(db.DateTime, default=datetime.utcnow)

    municipio             = db.relationship('Municipio', foreign_keys=[municipality_id])

    def to_dict(self):
        return {
            'id':           self.id,
            'nombre':       self.nombre,
            'municipio':    self.municipio.nombre if self.municipio else None,
            'tipo_comida':  self.tipo_comida,
            'valoracion':   self.valoracion,
            'michelin':     self.michelin,
            'repsol':       self.repsol,
        }


class Cultura(db.Model):
    __tablename__ = 'culture'
    __table_args__ = {'schema': 'market_data'}

    id                  = db.Column(db.Integer, primary_key=True)
    google_place_id     = db.Column(db.String(100), unique=True)
    kulturklik_id       = db.Column(db.String(50), unique=True)
    fuente              = db.Column(db.String(50), nullable=False, default='Open Data')
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
    active              = db.Column(db.Boolean, default=True)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    municipio           = db.relationship('Municipio', foreign_keys=[municipality_id])

    def to_dict(self):
        return {
            'id':         self.id,
            'nombre':     self.nombre,
            'tipo_lugar': self.tipo_lugar,
            'municipio':  self.municipio.nombre if self.municipio else None,
            'valoracion': self.valoracion,
        }

# ---------------------------------------------------------------------------
# ESQUEMA: user_data
# ---------------------------------------------------------------------------

class Usuario(db.Model):
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
    age             = db.Column(db.Integer, nullable=False)
    role            = db.Column(db.String(10), nullable=False, default='user')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    municipio       = db.relationship('Municipio', foreign_keys=[municipality_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id_user':       self.id_user,
            'nombre':        self.nombre,
            'apellido':      self.apellido,
            'email':         self.email,
            'municipality_id': self.municipality_id,
            'municipio':     self.municipio.nombre if self.municipio else None,
            'provincia':     self.municipio.provincia if self.municipio else None,
            'sexo':          self.sexo,
            'age':           self.age,
            'role':          self.role,
        }


class Interes(db.Model):
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
    __tablename__ = 'user_interests'
    __table_args__ = {'schema': 'user_data'}

    id_user    = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), primary_key=True, nullable=False)
    id_interes = db.Column(db.Integer, db.ForeignKey('user_data.interests.id_interes'), primary_key=True, nullable=False)

    def to_dict(self):
        return {
            'id_user':    self.id_user,
            'id_interes': self.id_interes,
        }


class Preferencia(db.Model):
    __tablename__ = 'preferences'
    __table_args__ = {'schema': 'user_data'}

    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), unique=True, nullable=False)
    rango_precio       = db.Column(db.String(10))
    movilidad_reducida = db.Column(db.Boolean, default=False)
    # INTEGER[] — lista de IDs de shared.municipalities
    municipios_interes = db.Column(ARRAY(Integer), default=list)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':                  self.id,
            'user_id':             self.user_id,
            'rango_precio':        self.rango_precio,
            'movilidad_reducida':  self.movilidad_reducida,
            'municipios_interes':  self.municipios_interes or [],
        }


class Resena(db.Model):
    __tablename__ = 'reviews'
    __table_args__ = {'schema': 'user_data'}

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user_data.users.id_user'), nullable=False)
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

    def entidad_id(self):
        return self.event_id or self.gastro_id or self.culture_id

    def to_dict(self):
        return {
            'id':           self.id,
            'user_id':      self.user_id,
            'entidad_tipo': self.entidad_tipo(),
            'entidad_id':   self.entidad_id(),
            'puntuacion':   self.puntuacion,
            'texto':        self.texto,
            'created_at':   self.created_at.isoformat() if self.created_at else None,
        }
