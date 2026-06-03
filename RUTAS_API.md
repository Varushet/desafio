# 📋 Documentación de Rutas - SustraiApp API

## 🏠 Ruta Raíz

### GET `/`

**Descripción:** Verifica que la API está activa

**Parámetros:** Ninguno

**Respuesta (200):**

```json
{
  "message": "Bienvenidos a la API SustraiApp"
}
```

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/
```

---

## 👤 Autenticación

### POST `/registro`

**Descripción:** Registra un nuevo usuario en la aplicación

**Campos Requeridos:**

- `nombre` (string): Nombre del usuario
- `email` (string): Email único
- `password` (string): Contraseña
- `municipality_id` (integer): ID del municipio
- `sexo` (string): Sexo del usuario
- `age` (integer): Edad del usuario

**Campos Opcionales:**

- `apellido` (string): Apellido del usuario
- `tlf` (string): Teléfono de contacto

**Respuesta (201):**

```json
{
  "mensaje": "Usuario creado correctamente",
  "usuario": {
    "id_user": 1,
    "nombre": "Juan",
    "email": "juan@example.com",
    "role": "user"
  }
}
```

**Errores:**

- `400` - Faltan campos obligatorios o municipality_id inválido
- `409` - El email ya está registrado
- `500` - Error al registrar

**Ejemplo:**

```bash
curl -X POST http://localhost:5000/registro \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellido": "Pérez",
    "email": "juan@example.com",
    "password": "miContraseña123",
    "municipality_id": 5,
    "sexo": "M",
    "age": 28,
    "tlf": "1234567890"
  }'
```

---

### POST `/login`

**Descripción:** Autentica un usuario y devuelve su ID y rol

**Campos Requeridos:**

- `email` (string): Email del usuario
- `password` (string): Contraseña

**Respuesta (200):**

```json
{
  "mensaje": "Login exitoso",
  "user_id": 1,
  "role": "user"
}
```

**Errores:**

- `400` - Email o password no proporcionados
- `401` - Credenciales inválidas

**Ejemplo:**

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "miContraseña123"
  }'
```

---

## 🏘️ Municipios

### GET `/municipios`

**Descripción:** Obtiene la lista de todos los municipios disponibles (ordenados alfabéticamente)

**Parámetros:** Ninguno

**Respuesta (200):**

```json
[
  {
    "id": 1,
    "nombre": "Bogotá"
  },
  {
    "id": 2,
    "nombre": "Medellín"
  },
  {
    "id": 5,
    "nombre": "Cali"
  }
]
```

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/municipios
```

---

## ⚙️ Preferencias del Usuario

### GET `/usuarios/<user_id>/preferencias`

**Descripción:** Obtiene las preferencias de un usuario

**Parámetros:**

- `user_id` (path): ID del usuario

**Respuesta (200):**

```json
{
  "user_id": 1,
  "rango_precio": "medio",
  "movilidad_reducida": false,
  "municipios_interes": [1, 5, 2],
  "created_at": "2026-06-03T10:30:00",
  "updated_at": "2026-06-03T10:30:00"
}
```

**Errores:**

- `404` - Preferencias no encontradas

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/usuarios/1/preferencias
```

---

### PUT `/usuarios/<user_id>/preferencias`

**Descripción:** Actualiza las preferencias de un usuario

**Parámetros:**

- `user_id` (path): ID del usuario

**Campos Opcionales (en body):**

- `rango_precio` (string): "bajo", "medio", "alto"
- `movilidad_reducida` (boolean): Accesibilidad
- `municipios_interes` (array): Lista de IDs de municipios

**Respuesta (200):**

```json
{
  "mensaje": "Preferencias actualizadas",
  "data": {
    "user_id": 1,
    "rango_precio": "alto",
    "movilidad_reducida": true,
    "municipios_interes": [1, 5],
    "updated_at": "2026-06-03T11:45:00"
  }
}
```

**Errores:**

- `404` - Preferencias no encontradas
- `500` - Error al actualizar

**Ejemplo:**

```bash
curl -X PUT http://localhost:5000/usuarios/1/preferencias \
  -H "Content-Type: application/json" \
  -d '{
    "rango_precio": "alto",
    "movilidad_reducida": true,
    "municipios_interes": [1, 5, 2]
  }'
```

---

## 💡 Intereses

### GET `/intereses`

**Descripción:** Obtiene el árbol completo de categorías de intereses

**Parámetros:** Ninguno

**Respuesta (200):**

```json
[
  {
    "id_interes": 1,
    "nombre": "Gastronomía",
    "descripcion": "Interés en comida y restaurantes"
  },
  {
    "id_interes": 2,
    "nombre": "Cultura",
    "descripcion": "Interés en actividades culturales"
  },
  {
    "id_interes": 3,
    "nombre": "Naturaleza",
    "descripcion": "Interés en actividades al aire libre"
  }
]
```

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/intereses
```

---

### GET `/usuarios/<user_id>/intereses`

**Descripción:** Obtiene todos los intereses de un usuario específico

**Parámetros:**

- `user_id` (path): ID del usuario

**Respuesta (200):**

```json
{
  "id_user": 1,
  "intereses": [1, 3, 5]
}
```

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/usuarios/1/intereses
```

---

### POST `/usuarios/<user_id>/intereses`

**Descripción:** Agrega un nuevo interés a un usuario

**Parámetros:**

- `user_id` (path): ID del usuario

**Body requerido:**

- `id_interes` (integer): ID del interés a agregar

**Respuesta (201):**

```json
{
  "mensaje": "Interés agregado"
}
```

**Errores:**

- `400` - id_interes no proporcionado
- `404` - El interés no existe
- `200` - El usuario ya tiene este interés (sin cambios)
- `500` - Error al agregar

**Ejemplo:**

```bash
curl -X POST http://localhost:5000/usuarios/1/intereses \
  -H "Content-Type: application/json" \
  -d '{
    "id_interes": 3
  }'
```

---

### DELETE `/usuarios/<user_id>/intereses/<id_interes>`

**Descripción:** Elimina un interés de un usuario

**Parámetros:**

- `user_id` (path): ID del usuario
- `id_interes` (path): ID del interés a eliminar

**Respuesta (200):**

```json
{
  "mensaje": "Interés eliminado"
}
```

**Errores:**

- `404` - Relación no encontrada
- `500` - Error al eliminar

**Ejemplo:**

```bash
curl -X DELETE http://localhost:5000/usuarios/1/intereses/3
```

---

## ⭐ Reseñas

### POST `/resenas`

**Descripción:** Crea una nueva reseña para un evento, restaurante o lugar cultural

**Campos Requeridos:**

- `user_id` (integer): ID del usuario que hace la reseña
- `entidad_tipo` (string): Tipo de entidad: "event", "gastro" o "cultura"
- `entidad_id` (integer): ID de la entidad reseñada
- `puntuacion` (integer): Calificación de 1 a 5

**Campos Opcionales:**

- `texto` (string): Comentario o descripción de la reseña

**Respuesta (201):**

```json
{
  "mensaje": "Reseña creada",
  "id": 42
}
```

**Errores:**

- `400` - Faltan campos obligatorios o tipo de entidad inválido
- `400` - Puntuación no está entre 1 y 5
- `500` - Error al crear reseña

**Ejemplo:**

```bash
curl -X POST http://localhost:5000/resenas \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "entidad_tipo": "gastro",
    "entidad_id": 15,
    "puntuacion": 5,
    "texto": "Excelente comida, muy recomendado"
  }'
```

---

### GET `/resenas/<entidad_tipo>/<entidad_id>`

**Descripción:** Obtiene todas las reseñas de una entidad específica

**Parámetros:**

- `entidad_tipo` (path): "event", "gastro" o "cultura"
- `entidad_id` (path): ID de la entidad

**Respuesta (200):**

```json
[
  {
    "id": 42,
    "user_id": 1,
    "puntuacion": 5,
    "texto": "Excelente comida, muy recomendado",
    "created_at": "2026-06-03T14:20:00"
  },
  {
    "id": 43,
    "user_id": 2,
    "puntuacion": 4,
    "texto": "Bueno pero caro",
    "created_at": "2026-06-03T15:10:00"
  }
]
```

**Errores:**

- `400` - Tipo de entidad inválido

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/resenas/gastro/15
```

---

## 📅 Eventos

### GET `/eventos`

**Descripción:** Obtiene los últimos 10 eventos activos (ordenados por fecha de inicio descendente)

**Parámetros:** Ninguno

**Respuesta (200):**

```json
[
  {
    "id": 1,
    "nombre": "Festival de Música",
    "descripcion": "Gran festival de música en vivo",
    "start_date": "2026-06-15T18:00:00",
    "end_date": "2026-06-15T23:00:00",
    "location": "Parque Central",
    "active": true
  },
  {
    "id": 2,
    "nombre": "Exposición de Arte",
    "descripcion": "Exposición de artistas locales",
    "start_date": "2026-06-10T10:00:00",
    "end_date": "2026-06-20T18:00:00",
    "location": "Museo de Arte",
    "active": true
  }
]
```

**Ejemplo:**

```bash
curl -X GET http://localhost:5000/eventos
```

---

## 📝 Tabla de Resumen de Rutas

| Método | Ruta                                    | Descripción                    |
| ------ | --------------------------------------- | ------------------------------ |
| GET    | `/`                                     | Verificar API activa           |
| POST   | `/registro`                             | Registrar nuevo usuario        |
| POST   | `/login`                                | Autenticar usuario             |
| GET    | `/municipios`                           | Listar todos los municipios    |
| GET    | `/usuarios/{id}/preferencias`           | Obtener preferencias           |
| PUT    | `/usuarios/{id}/preferencias`           | Actualizar preferencias        |
| GET    | `/intereses`                            | Listar categorías de intereses |
| GET    | `/usuarios/{id}/intereses`              | Obtener intereses del usuario  |
| POST   | `/usuarios/{id}/intereses`              | Agregar interés al usuario     |
| DELETE | `/usuarios/{id}/intereses/{id_interes}` | Eliminar interés del usuario   |
| POST   | `/resenas`                              | Crear nueva reseña             |
| GET    | `/resenas/{tipo}/{id}`                  | Obtener reseñas de una entidad |
| GET    | `/eventos`                              | Listar últimos eventos activos |

---

## 🔑 Códigos de Estado HTTP

- **200**: Solicitud exitosa
- **201**: Recurso creado exitosamente
- **400**: Solicitud inválida (parámetros faltantes o incorrectos)
- **401**: No autorizado (credenciales inválidas)
- **404**: Recurso no encontrado
- **409**: Conflicto (ej: email duplicado)
- **500**: Error interno del servidor

---

## 📌 Notas Importantes

1. **Autenticación**: Las rutas no incluyen autenticación por token JWT. Considera agregarlo en producción.
2. **CORS**: La API tiene CORS habilitado para todas las rutas.
3. **Base de datos**: Se crea automáticamente al ejecutar la aplicación con `db.create_all()`.
4. **Municipios de interés**: Se guardan como lista en la preferencia del usuario.
5. **Tipos de entidades**: Para reseñas solo se aceptan "event", "gastro" y "cultura".
