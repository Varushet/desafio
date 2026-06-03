from flask import Flask, jsonify, request
from config import Config
from models import db, Municipio, Usuario, Preferencia, Interes, UserInteres, Resena, Evento, Gastronomia, Cultura
from flask_cors import CORS
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)

    # ═══════════════════════════════════════════════════════════════════════════════
    # RUTA RAÍZ
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/', methods=['GET'])
    def home():
        return jsonify({'message': 'Bienvenidos a la API SustraiApp'}), 200

    # ═══════════════════════════════════════════════════════════════════════════════
    # AUTENTICACIÓN
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/registro', methods=['POST'])
    def registrar_usuario():
        """
        POST /registro
        Campos requeridos: nombre, email, password, municipality_id, sexo, age
        Campos opcionales: apellido, tlf
        """
        data = request.get_json()

        required_fields = ['nombre', 'email', 'password', 'municipality_id', 'sexo', 'age']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        if Usuario.query.filter_by(email=data['email']).first():
            return jsonify({"error": "El email ya está registrado"}), 409

        # Verificar que el municipio existe
        if not Municipio.query.get(data['municipality_id']):
            return jsonify({"error": "municipality_id no válido"}), 400

        try:
            nuevo_usuario = Usuario(
                nombre=data['nombre'],
                apellido=data.get('apellido'),
                email=data['email'],
                tlf=data.get('tlf'),
                municipality_id=int(data['municipality_id']),
                sexo=data['sexo'],
                age=int(data['age']),
                role='user'
            )
            nuevo_usuario.set_password(data['password'])
            db.session.add(nuevo_usuario)
            db.session.flush()

            prefs = Preferencia(user_id=nuevo_usuario.id_user)
            db.session.add(prefs)
            db.session.commit()

            return jsonify({
                "mensaje": "Usuario creado correctamente",
                "usuario": nuevo_usuario.to_dict()
            }), 201

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error al registrar usuario: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/login', methods=['POST'])
    def login():
        """POST /login — email + password → user_id + role"""
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email y password requeridos"}), 400

        usuario = Usuario.query.filter_by(email=data['email']).first()
        if usuario and usuario.check_password(data['password']):
            return jsonify({
                "mensaje": "Login exitoso",
                "user_id": usuario.id_user,
                "role":    usuario.role
            }), 200

        return jsonify({"error": "Credenciales inválidas"}), 401

    # ═══════════════════════════════════════════════════════════════════════════════
    # MUNICIPIOS (utilidad para el frontend al registrar o seleccionar municipios)
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/municipios', methods=['GET'])
    def listar_municipios():
        """GET /municipios — devuelve la lista de municipios disponibles"""
        municipios = Municipio.query.order_by(Municipio.nombre).all()
        return jsonify([m.to_dict() for m in municipios]), 200

    # ═══════════════════════════════════════════════════════════════════════════════
    # PREFERENCIAS
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/usuarios/<int:user_id>/preferencias', methods=['GET'])
    def obtener_preferencias(user_id):
        """GET /usuarios/{user_id}/preferencias"""
        prefs = Preferencia.query.filter_by(user_id=user_id).first()
        if not prefs:
            return jsonify({"error": "Preferencias no encontradas"}), 404
        return jsonify(prefs.to_dict()), 200

    @app.route('/usuarios/<int:user_id>/preferencias', methods=['PUT'])
    def actualizar_preferencias(user_id):
        """
        PUT /usuarios/{user_id}/preferencias
        Campos opcionales: rango_precio, movilidad_reducida,
                           municipios_interes (lista de IDs de municipios)
        NOTA: los gustos por categoría (gastro, cultura…) ahora se gestionan
              a través de /usuarios/{user_id}/intereses
        """
        data = request.get_json()
        prefs = Preferencia.query.filter_by(user_id=user_id).first()

        if not prefs:
            return jsonify({"error": "Preferencias no encontradas"}), 404

        try:
            prefs.rango_precio       = data.get('rango_precio',       prefs.rango_precio)
            prefs.movilidad_reducida = data.get('movilidad_reducida', prefs.movilidad_reducida)

            if 'municipios_interes' in data:
                # Acepta lista de IDs enteros
                prefs.municipios_interes = [int(m) for m in data['municipios_interes']]

            prefs.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({"mensaje": "Preferencias actualizadas", "data": prefs.to_dict()}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════════
    # INTERESES
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/intereses', methods=['GET'])
    def listar_intereses():
        """GET /intereses — árbol completo de categorías"""
        intereses = Interes.query.all()
        return jsonify([i.to_dict() for i in intereses]), 200

    @app.route('/usuarios/<int:user_id>/intereses', methods=['GET'])
    def obtener_intereses_usuario(user_id):
        """GET /usuarios/{user_id}/intereses — IDs de intereses del usuario"""
        user_intereses = UserInteres.query.filter_by(id_user=user_id).all()
        return jsonify({"id_user": user_id, "intereses": [ui.id_interes for ui in user_intereses]}), 200

    @app.route('/usuarios/<int:user_id>/intereses', methods=['POST'])
    def agregar_interes_usuario(user_id):
        """POST /usuarios/{user_id}/intereses — body: {id_interes: int}"""
        data = request.get_json()
        id_interes = data.get('id_interes')

        if not id_interes:
            return jsonify({"error": "id_interes es requerido"}), 400

        if not Interes.query.get(id_interes):
            return jsonify({"error": "El interés no existe"}), 404

        if UserInteres.query.filter_by(id_user=user_id, id_interes=id_interes).first():
            return jsonify({"mensaje": "El usuario ya tiene este interés"}), 200

        try:
            db.session.add(UserInteres(id_user=user_id, id_interes=id_interes))
            db.session.commit()
            return jsonify({"mensaje": "Interés agregado"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/usuarios/<int:user_id>/intereses/<int:id_interes>', methods=['DELETE'])
    def eliminar_interes_usuario(user_id, id_interes):
        """DELETE /usuarios/{user_id}/intereses/{id_interes}"""
        relacion = UserInteres.query.filter_by(id_user=user_id, id_interes=id_interes).first()
        if not relacion:
            return jsonify({"error": "Relación no encontrada"}), 404

        try:
            db.session.delete(relacion)
            db.session.commit()
            return jsonify({"mensaje": "Interés eliminado"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════════
    # RESEÑAS
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/resenas', methods=['POST'])
    def crear_resena():
        """
        POST /resenas
        Campos requeridos: user_id, entidad_tipo ('event'|'gastro'|'cultura'),
                           entidad_id, puntuacion (1-5)
        Campo opcional:    texto
        """
        data = request.get_json()

        required = ['user_id', 'entidad_tipo', 'entidad_id', 'puntuacion']
        if not all(k in data for k in required):
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        if data['entidad_tipo'] not in ['event', 'gastro', 'cultura']:
            return jsonify({"error": "Tipo de entidad inválido"}), 400

        if not (1 <= data['puntuacion'] <= 5):
            return jsonify({"error": "La puntuación debe ser entre 1 y 5"}), 400

        # Mapear entidad_tipo → columna FK correcta
        fk_map = {'event': 'event_id', 'gastro': 'gastro_id', 'cultura': 'culture_id'}
        fk_field = fk_map[data['entidad_tipo']]

        try:
            nueva_resena = Resena(
                user_id=data['user_id'],
                puntuacion=data['puntuacion'],
                texto=data.get('texto', ''),
                **{fk_field: data['entidad_id']}
            )
            db.session.add(nueva_resena)
            db.session.commit()
            return jsonify({"mensaje": "Reseña creada", "id": nueva_resena.id}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/resenas/<string:entidad_tipo>/<int:entidad_id>', methods=['GET'])
    def obtener_resenas_entidad(entidad_tipo, entidad_id):
        """GET /resenas/{entidad_tipo}/{entidad_id}"""
        if entidad_tipo not in ['event', 'gastro', 'cultura']:
            return jsonify({"error": "Tipo inválido"}), 400

        fk_map = {'event': Resena.event_id, 'gastro': Resena.gastro_id, 'cultura': Resena.culture_id}
        resenas = Resena.query.filter(fk_map[entidad_tipo] == entidad_id).all()
        return jsonify([r.to_dict() for r in resenas]), 200

    # ═══════════════════════════════════════════════════════════════════════════════
    # EVENTOS
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/eventos', methods=['GET'])
    def listar_eventos():
        """GET /eventos — últimos 10 eventos activos"""
        eventos = (Evento.query
                   .filter_by(active=True)
                   .order_by(Evento.start_date.desc())
                   .limit(10)
                   .all())
        return jsonify([e.to_dict() for e in eventos]), 200

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
