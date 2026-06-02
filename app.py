from flask import Flask, jsonify, request
from config import Config
from models import db, Usuario, Preferencia, Interes, UserInteres, Resena, Evento
from flask_cors import CORS
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Configuración básica de logs
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Habilitar CORS para todas las rutas (desarrollo) !!!!
    CORS(app) 
    
    # Inicializar DB
    db.init_app(app)

    # ═══════════════════════════════════════════════════════════════════════════════
    # RUTA RAÍZ - VERIFICACIÓN DE API
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/', methods=['GET'])
    def home():
        """
        RUTA: GET /
        
        DESCRIPCIÓN: 
            Verifica que la API está funcionando correctamente.
        
        PARÁMETROS: Ninguno
        
        RESPUESTA:
            - Status: 200 OK
            - Body: {"message": "Bienvenidos a la API SustraiApp"}
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/
            
            Respuesta:
            {
              "message": "Bienvenidos a la API SustraiApp"
            }
        """
        return jsonify({'message': 'Bienvenidos a la API SustraiApp'}), 200

    # ═══════════════════════════════════════════════════════════════════════════════
    # RUTAS DE AUTENTICACIÓN - REGISTRO Y LOGIN
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @app.route('/registro', methods=['POST'])
    def registrar_usuario():
        """
        RUTA: POST /registro
        
        DESCRIPCIÓN:
            Registra un nuevo usuario en el sistema. Crea automáticamente sus 
            preferencias vacías por defecto.
        
        PARÁMETROS REQUERIDOS (JSON):
            - nombre: string (max 50 caracteres)
            - email: string (único, max 100 caracteres)
            - password: string (se encripta automáticamente)
            - municipio: string (max 100 caracteres)
            - provincia: string (max 50 caracteres)
            - sexo: string (max 10 caracteres) hombre / mujer
            - age: integer (edad del usuario)
        
        PARÁMETROS OPCIONALES (JSON):
            - apellido: string (max 50 caracteres)
            - tlf: string (teléfono, max 20 caracteres)
        
        RESPUESTAS:
            ✓ 201 CREATED - Usuario creado exitosamente
            ✗ 400 BAD REQUEST - Faltan campos obligatorios
            ✗ 409 CONFLICT - El email ya está registrado
            ✗ 500 INTERNAL SERVER ERROR - Error de servidor
        
        EJEMPLO DE USO:
            curl -X POST http://localhost:5000/registro \\
              -H "Content-Type: application/json" \\
              -d '{
                "nombre": "Juan",
                "apellido": "García",
                "email": "juan@example.com",
                "password": "mipassword123",
                "municipio": "Madrid",
                "provincia": "Madrid",
                "sexo": "hombre",
                "age": 28,
                "tlf": "+34612345678"
              }'
            
            Respuesta exitosa (201):
            {
              "mensaje": "Usuario creado correctamente",
              "usuario": {
                "id_user": 1,
                "nombre": "Juan",
                "apellido": "García",
                "email": "juan@example.com",
                "municipio": "Madrid",
                "provincia": "Madrid",
                "sexo": "hombre",
                "age": 28,
                "role": "user"
              }
            }
        """
        data = request.get_json()
    
        # Validación de campos obligatorios
        required_fields = ['nombre', 'email', 'password', 'municipio', 'provincia', 'sexo', 'age']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Faltan campos obligatorios"}), 400
        
        # Verificar duplicidad
        if Usuario.query.filter_by(email=data['email']).first():
            return jsonify({"error": "El email ya está registrado"}), 409
        
        try:
            nuevo_usuario = Usuario(
                nombre=data['nombre'],
                apellido=data.get('apellido'),
                email=data['email'],
                tlf=data.get('tlf'),
                municipio=data['municipio'],
                provincia=data['provincia'],
                sexo=data['sexo'],
                age=int(data['age']),
                role='user' # Siempre user
            )
            
            nuevo_usuario.set_password(data['password'])
            
            db.session.add(nuevo_usuario)
            db.session.flush() # Para obtener el ID antes del commit
            
            # Crear preferencias vacías por defecto
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
        """
        RUTA: POST /login
        
        DESCRIPCIÓN:
            Autentica un usuario con email y contraseña. Retorna el ID del usuario
            y su rol para gestionar sesiones en el frontend.
        
        PARÁMETROS REQUERIDOS (JSON):
            - email: string (email registrado)
            - password: string (contraseña del usuario)
        
        RESPUESTAS:
            ✓ 200 OK - Login exitoso
            ✗ 400 BAD REQUEST - Faltan email o password
            ✗ 401 UNAUTHORIZED - Credenciales inválidas
        
        EJEMPLO DE USO:
            curl -X POST http://localhost:5000/login \\
              -H "Content-Type: application/json" \\
              -d '{
                "email": "juan@example.com",
                "password": "mipassword123"
              }'
            
            Respuesta exitosa (200):
            {
              "mensaje": "Login exitoso",
              "user_id": 1,
              "role": "user"
            }
            
            Respuesta fallida (401):
            {
              "error": "Credenciales inválidas"
            }
        """
        data = request.get_json()
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email y password requeridos"}), 400

        usuario = Usuario.query.filter_by(email=data['email']).first()

        if usuario and usuario.check_password(data['password']):
            return jsonify({
                "mensaje": "Login exitoso",
                "user_id": usuario.id_user,
                "role": usuario.role
            }), 200
        else:
            return jsonify({"error": "Credenciales inválidas"}), 401
        
    # ═══════════════════════════════════════════════════════════════════════════════
    # RUTAS DE PREFERENCIAS DEL USUARIO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @app.route('/usuarios/<int:user_id>/preferencias', methods=['GET'])
    def obtener_preferencias(user_id):
        """
        RUTA: GET /usuarios/{user_id}/preferencias
        
        DESCRIPCIÓN:
            Obtiene las preferencias personalizadas de un usuario (gustos, rango de 
            precio, accesibilidad, municipios de interés).
        
        PARÁMETROS:
            - user_id: integer (ID del usuario en la URL)
        
        RESPUESTAS:
            ✓ 200 OK - Preferencias obtenidas
            ✗ 404 NOT FOUND - Preferencias no encontradas para el usuario
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/usuarios/1/preferencias
            
            Respuesta (200):
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
        prefs = Preferencia.query.filter_by(user_id=user_id).first()
        if not prefs:
            return jsonify({"error": "Preferencias no encontradas"}), 404
        return jsonify(prefs.to_dict()), 200

    @app.route('/usuarios/<int:user_id>/preferencias', methods=['PUT'])
    def actualizar_preferencias(user_id):
        """
        RUTA: PUT /usuarios/{user_id}/preferencias
        
        DESCRIPCIÓN:
            Actualiza las preferencias de un usuario. Solo actualiza los campos 
            que se envíen en el JSON.
        
        PARÁMETROS EN URL:
            - user_id: integer (ID del usuario)
        
        PARÁMETROS EN JSON (todos opcionales):
            - le_gusta_gastro: boolean
            - le_gusta_cultura: boolean
            - le_gusta_eventos: boolean
            - le_gusta_compras: boolean
            - rango_precio: string (ej: "bajo", "medio", "alto")
            - movilidad_reducida: boolean
            - municipios_interes: array of strings
        
        RESPUESTAS:
            ✓ 200 OK - Preferencias actualizadas
            ✗ 404 NOT FOUND - Preferencias no encontradas
            ✗ 500 INTERNAL SERVER ERROR - Error de servidor
        
        EJEMPLO DE USO:
            curl -X PUT http://localhost:5000/usuarios/1/preferencias \\
              -H "Content-Type: application/json" \\
              -d '{
                "le_gusta_gastro": true,
                "le_gusta_cultura": true,
                "rango_precio": "alto",
                "municipios_interes": ["Madrid", "Barcelona", "Valencia"]
              }'
            
            Respuesta (200):
            {
              "mensaje": "Preferencias actualizadas",
              "data": {
                "id": 1,
                "user_id": 1,
                "le_gusta_gastro": true,
                "le_gusta_cultura": true,
                "le_gusta_eventos": false,
                "le_gusta_compras": false,
                "rango_precio": "alto",
                "movilidad_reducida": false,
                "municipios_interes": ["Madrid", "Barcelona", "Valencia"]
              }
            }
        """
        data = request.get_json()
        prefs = Preferencia.query.filter_by(user_id=user_id).first()
        
        if not prefs:
            return jsonify({"error": "Preferencias no encontradas"}), 404

        try:
            # Actualizar campos booleanos y otros
            prefs.le_gusta_gastro = data.get('le_gusta_gastro', prefs.le_gusta_gastro)
            prefs.le_gusta_cultura = data.get('le_gusta_cultura', prefs.le_gusta_cultura)
            prefs.le_gusta_eventos = data.get('le_gusta_eventos', prefs.le_gusta_eventos)
            prefs.le_gusta_compras = data.get('le_gusta_compras', prefs.le_gusta_compras)
            prefs.rango_precio = data.get('rango_precio', prefs.rango_precio)
            prefs.movilidad_reducida = data.get('movilidad_reducida', prefs.movilidad_reducida)
            
            # JSONB para municipios
            if 'municipios_interes' in data:
                prefs.municipios_interes = data['municipios_interes']
            
            prefs.updated_at = datetime.utcnow()
            
            db.session.commit()
            return jsonify({"mensaje": "Preferencias actualizadas", "data": prefs.to_dict()}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
    # RUTAS DE INTERESES (CATEGORÍAS JERÁRQUICAS)
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/intereses', methods=['GET'])
    def listar_intereses():
        """
        RUTA: GET /intereses
        
        DESCRIPCIÓN:
            Devuelve la lista completa de intereses/categorías disponibles en la 
            plataforma. Incluye la estructura jerárquica (padre_id) para que el 
            frontend pueda construir un árbol de categorías.
        
        PARÁMETROS: Ninguno
        
        RESPUESTAS:
            ✓ 200 OK - Lista de intereses
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/intereses
            
            Respuesta (200):
            [
              {
                "id_interes": 1,
                "nombre": "Gastronomía",
                "descripcion": "Eventos y lugares gastronómicos",
                "father_id": null
              },
              {
                "id_interes": 2,
                "nombre": "Restaurantes",
                "descripcion": "Establecimientos de comida",
                "father_id": 1
              },
              {
                "id_interes": 3,
                "nombre": "Cultura",
                "descripcion": "Eventos y lugares culturales",
                "father_id": null
              }
            ]
        """
        intereses = Interes.query.all()
        return jsonify([i.to_dict() for i in intereses]), 200

    @app.route('/usuarios/<int:user_id>/intereses', methods=['GET'])
    def obtener_intereses_usuario(user_id):
        """
        RUTA: GET /usuarios/{user_id}/intereses
        
        DESCRIPCIÓN:
            Obtiene los IDs de todos los intereses que el usuario ha seleccionado.
            Retorna solo los IDs para que el frontend pueda hacer matching con 
            la lista completa de intereses.
        
        PARÁMETROS:
            - user_id: integer (ID del usuario en la URL)
        
        RESPUESTAS:
            ✓ 200 OK - Lista de intereses del usuario
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/usuarios/1/intereses
            
            Respuesta (200):
            {
              "id_user": 1,
              "intereses": [1, 3, 5, 7]
            }
        """
        user_intereses = UserInteres.query.filter_by(id_user=user_id).all()
        # Retornamos solo los IDs para facilitar el frontend
        ids = [ui.id_interes for ui in user_intereses]
        return jsonify({"id_user": user_id, "intereses": ids}), 200

    @app.route('/usuarios/<int:user_id>/intereses', methods=['POST'])
    def agregar_interes_usuario(user_id):
        """
        RUTA: POST /usuarios/{user_id}/intereses
        
        DESCRIPCIÓN:
            Agrega un interés a la lista de intereses del usuario. Evita duplicados.
        
        PARÁMETROS EN URL:
            - user_id: integer (ID del usuario)
        
        PARÁMETROS EN JSON:
            - id_interes: integer (ID del interés a agregar)
        
        RESPUESTAS:
            ✓ 201 CREATED - Interés agregado exitosamente
            ✗ 400 BAD REQUEST - Falta id_interes
            ✗ 404 NOT FOUND - El interés no existe
            ✗ 500 INTERNAL SERVER ERROR - Error de servidor
        
        EJEMPLO DE USO:
            curl -X POST http://localhost:5000/usuarios/1/intereses \\
              -H "Content-Type: application/json" \\
              -d '{
                "id_interes": 5
              }'
            
            Respuesta (201):
            {
              "mensaje": "Interés agregado"
            }
            
            Respuesta si ya existe (200):
            {
              "mensaje": "El usuario ya tiene este interés"
            }
        """
        data = request.get_json()
        id_interes = data.get('id_interes')

        if not id_interes:
            return jsonify({"error": "id_interes es requerido"}), 400

        # Verificar si el interés existe
        interes = Interes.query.get(id_interes)
        if not interes:
            return jsonify({"error": "El interés no existe"}), 404

        # Verificar si ya lo tiene
        existente = UserInteres.query.filter_by(id_user=user_id, id_interes=id_interes).first()
        if existente:
            return jsonify({"mensaje": "El usuario ya tiene este interés"}), 200

        try:
            nuevo_relacion = UserInteres(id_user=user_id, id_interes=id_interes)
            db.session.add(nuevo_relacion)
            db.session.commit()
            return jsonify({"mensaje": "Interés agregado"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/usuarios/<int:user_id>/intereses/<int:id_interes>', methods=['DELETE'])
    def eliminar_interes_usuario(user_id, id_interes):
        """
        RUTA: DELETE /usuarios/{user_id}/intereses/{id_interes}
        
        DESCRIPCIÓN:
            Elimina un interés de la lista de intereses del usuario.
        
        PARÁMETROS EN URL:
            - user_id: integer (ID del usuario)
            - id_interes: integer (ID del interés a eliminar)
        
        RESPUESTAS:
            ✓ 200 OK - Interés eliminado
            ✗ 404 NOT FOUND - La relación no existe
            ✗ 500 INTERNAL SERVER ERROR - Error de servidor
        
        EJEMPLO DE USO:
            curl -X DELETE http://localhost:5000/usuarios/1/intereses/5
            
            Respuesta (200):
            {
              "mensaje": "Interés eliminado"
            }
        """
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
    # RUTAS DE RESEÑAS (POLIMÓRFICAS - PARA EVENTOS, GASTRONOMÍA, CULTURA)
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/resenas', methods=['POST'])
    def crear_resena():
        """
        RUTA: POST /resenas
        
        DESCRIPCIÓN:
            Crea una reseña para cualquier tipo de entidad (eventos, 
            gastronomía, cultura). La puntuación debe estar entre 1 y 5.
        
        PARÁMETROS EN JSON:
            - user_id: integer (ID del usuario que hace la reseña)
            - entidad_tipo: string (REQUERIDO: 'event', 'gastro' o 'cultura')
            - entidad_id: integer (ID de la entidad a reseñar)
            - puntuacion: integer (REQUERIDO: entre 1 y 5)
            - texto: string (opcional: opinión del usuario)
        
        RESPUESTAS:
            ✓ 201 CREATED - Reseña creada
            ✗ 400 BAD REQUEST - Faltan campos obligatorios
            ✗ 400 BAD REQUEST - Puntuación fuera de rango (1-5)
            ✗ 400 BAD REQUEST - Tipo de entidad inválido
            ✗ 500 INTERNAL SERVER ERROR - Error de servidor
        
        EJEMPLO DE USO:
            curl -X POST http://localhost:5000/resenas \\
              -H "Content-Type: application/json" \\
              -d '{
                "user_id": 1,
                "entidad_tipo": "gastro",
                "entidad_id": 42,
                "puntuacion": 4,
                "texto": "Excelente comida, muy recomendado. El servicio fue rápido."
              }'
            
            Respuesta (201):
            {
              "mensaje": "Reseña creada",
              "id": 1
            }
        """
        data = request.get_json()
        
        # Validaciones básicas
        required = ['user_id', 'entidad_tipo', 'entidad_id', 'puntuacion']
        if not all(k in data for k in required):
            return jsonify({"error": "Faltan campos obligatorios"}), 400
        
        if data['entidad_tipo'] not in ['event', 'gastro', 'cultura']:
            return jsonify({"error": "Tipo de entidad inválido"}), 400
        
        if not (1 <= data['puntuacion'] <= 5):
            return jsonify({"error": "La puntuación debe ser entre 1 y 5"}), 400

        try:
            nueva_resena = Resena(
                user_id=data['user_id'],
                entidad_tipo=data['entidad_tipo'],
                entidad_id=data['entidad_id'],
                puntuacion=data['puntuacion'],
                texto=data.get('texto', '')
            )
            db.session.add(nueva_resena)
            db.session.commit()
            return jsonify({"mensaje": "Reseña creada", "id": nueva_resena.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/resenas/<string:entidad_tipo>/<int:entidad_id>', methods=['GET'])
    def obtener_resenas_entidad(entidad_tipo, entidad_id):
        """
        RUTA: GET /resenas/{entidad_tipo}/{entidad_id}
        
        DESCRIPCIÓN:
            Obtiene todas las reseñas para una entidad específica 
            (evento, restaurante, lugar cultural, etc.).
        
        PARÁMETROS EN URL:
            - entidad_tipo: string ('event', 'gastro' o 'cultura')
            - entidad_id: integer (ID de la entidad)
        
        RESPUESTAS:
            ✓ 200 OK - Lista de reseñas
            ✗ 400 BAD REQUEST - Tipo de entidad inválido
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/resenas/gastro/42
            
            Respuesta (200):
            [
              {
                "id": 1,
                "user_id": 1,
                "entidad_tipo": "gastro",
                "entidad_id": 42,
                "puntuacion": 4,
                "texto": "Excelente comida, muy recomendado.",
                "created_at": "2026-06-02T10:30:00"
              },
              {
                "id": 2,
                "user_id": 2,
                "entidad_tipo": "gastro",
                "entidad_id": 42,
                "puntuacion": 5,
                "texto": "Perfectamente delicioso!",
                "created_at": "2026-06-02T11:45:00"
              }
            ]
        """
        if entidad_tipo not in ['event', 'gastro', 'cultura']:
            return jsonify({"error": "Tipo inválido"}), 400
            
        resenas = Resena.query.filter_by(entidad_tipo=entidad_tipo, entidad_id=entidad_id).all()
        return jsonify([r.to_dict() for r in resenas]), 200

    # ═══════════════════════════════════════════════════════════════════════════════
    # RUTAS DE EVENTOS
    # ═══════════════════════════════════════════════════════════════════════════════

    @app.route('/eventos', methods=['GET'])
    def listar_eventos():
        """
        RUTA: GET /eventos
        
        DESCRIPCIÓN:
            Obtiene los últimos eventos más recientes disponibles en la plataforma.
            Útil para mostrar eventos próximos en el feed o página de inicio.
        
        PARÁMETROS: Ninguno (actualmente devuelve los 10 más recientes)
        
        RESPUESTAS:
            ✓ 200 OK - Lista de eventos
        
        EJEMPLO DE USO:
            curl -X GET http://localhost:5000/eventos
            
            Respuesta (200):
            [
              {
                "id": "evt_001",
                "name_es": "Festival de Música Urbana",
                "start_date": "2026-06-15T18:00:00",
                "municipality_es": "Madrid",
                "price_eur": 25.50
              },
              {
                "id": "evt_002",
                "name_es": "Concierto de Jazz",
                "start_date": "2026-06-20T20:00:00",
                "municipality_es": "Barcelona",
                "price_eur": null
              }
            ]
        """
        # Ejemplo simple: últimos 10 eventos
        eventos = Evento.query.order_by(Evento.start_date.desc()).limit(10).all()
        return jsonify([e.to_dict() for e in eventos]), 200

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)