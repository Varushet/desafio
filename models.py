from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'user_data'}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    tlf = db.Column(db.String(20), nullable=True)
    municipio = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(10), nullable=False, default='user') # Siempre 'user' por defecto

    def set_password(self, password):
        """Hashea la contraseña y la guarda"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'correo': self.correo,
            'tlf': self.tlf,
            'municipio': self.municipio,
            'nivel': self.nivel
        }