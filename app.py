from flask import Flask, jsonify, request
from config import Config
from models import db, Usuario
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Habilitar CORS para todas las rutas (desarrollo) !!!!
    CORS(app) 
    
    # Inicializar DB
    db.init_app(app)

    # ── Modelos
    path  = 'desafio/models/'

    @app.route('/', methods=['GET'])
    def home():
        return jsonify({'message': 'Bienvenidos a la API'}), 200

    @app.route('/registro', methods=['POST'])
    def registrar_usuario():
        data = request.get_json()
    
        # Validar que haya contraseña
        if not data or not data.get('password'):
            return jsonify({"error": "La contraseña es obligatoria"}), 400
        
        # Verificar si el correo ya existe
        if Usuario.query.filter_by(correo=data['correo']).first():
            return jsonify({"error": "El correo ya está registrado"}), 409
        
        try:
            nuevo_usuario = Usuario(
                nombre=data['nombre'],
                apellido=data.get('apellido', ''),
                correo=data['correo'],
                tlf=data.get('tlf'),
                municipio=data.get('municipio', 'Desconocido'),
                nivel='user'
            )
            
            nuevo_usuario.set_password(data['password'])
            
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            return jsonify({"mensaje": "Usuario creado correctamente", "usuario": nuevo_usuario.to_dict()}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
        
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)