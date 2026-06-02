# 📚 Documentación API SustraiApp

## 🔐 Autenticación

### POST /registro

Registra un nuevo usuario en el sistema.

**Parámetros requeridos:**

```json
{
  "nombre": "Juan",
  "email": "juan@example.com",
  "password": "mipassword123",
  "municipio": "Madrid",
  "provincia": "Madrid",
  "sexo": "M",
  "age": 28
}
```

**Parámetros opcionales:**

- `apellido`: string
- `tlf`: string

**Respuesta exitosa (201):**

```json
{
  "mensaje": "Usuario creado correctamente",
  "usuario": {
    "id_user": 1,
    "nombre": "Juan",
    "email": "juan@example.com",
    "municipio": "Madrid",
    "provincia": "Madrid",
    "sexo": "M",
    "age": 28,
    "role": "user"
  }

```

**Errores:**

- `400`: Faltan campos obligatorios
- `409`: El email ya está registrado
- `500`: Error de servidor

---

### POST /login

Autentica un usuario.

**Parámetros:**

```json
{
  "email": "juan@example.com",
  "password": "mipassword123"
}
```

**Respuesta exitosa (200):**

```json
{
  "mensaje": "Login exitoso",
  "user_id": 1,
  "role": "user"
}
```

**Errores:**

- `400`: Faltan email o password
- `401`: Credenciales inválidas

---

## 👥 Preferencias del Usuario

### GET /usuarios/{user_id}/preferencias

Obtiene las preferencias de un usuario.

**Parámetro URL:**

- `user_id`: integer

**Respuesta (200):**

```json
{
  "id": 1,
  "id_user": 1,
  "le_gusta_gastro": true,
  "le_gusta_cultura": false,
  "le_gusta_eventos": true,
  "le_gusta_compras": false,
  "rango_precio": "medio",
  "movilidad_reducida": false,
  "municipios_interes": ["Madrid", "Barcelona"]
}
```

---

### PUT /usuarios/{user_id}/preferencias

Actualiza las preferencias de un usuario.

**Parámetros (todos opcionales):**

```json
{
  "le_gusta_gastro": true,
  "le_gusta_cultura": true,
  "rango_precio": "alto",
  "movilidad_reducida": false,
  "municipios_interes": ["Madrid", "Barcelona", "Valencia"]
}
```

**Respuesta (200):**

```json
{
  "mensaje": "Preferencias actualizadas",
  "data": {
    "id": 1,
    "id_user": 1,
    "le_gusta_gastro": true,
    "le_gusta_cultura": true,
    "le_gusta_eventos": false,
    "le_gusta_compras": false,
    "rango_precio": "alto",
    "movilidad_reducida": false,
    "municipios_interes": ["Madrid", "Barcelona", "Valencia"]
  }
}
```

---

## 🎯 Intereses

### GET /intereses

Obtiene la lista completa de intereses/categorías disponibles.

**Respuesta (200):**

```json
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
  }
]
```

---

### GET /usuarios/{user_id}/intereses

Obtiene los intereses seleccionados por un usuario.

**Parámetro URL:**

- `user_id`: integer

**Respuesta (200):**

```json
{
  "id_user": 1,
  "intereses": [1, 3, 5, 7]
}
```

---

### POST /usuarios/{user_id}/intereses

Agrega un interés a un usuario.

**Parámetros:**

```json
{
  "id_interes": 5
}
```

**Respuesta (201):**

```json
{
  "mensaje": "Interés agregado"
}
```

**Errores:**

- `400`: Falta id_interes
- `404`: El interés no existe

---

### DELETE /usuarios/{user_id}/intereses/{id_interes}

Elimina un interés de un usuario.

**Parámetros URL:**

- `user_id`: integer
- `id_interes`: integer

**Respuesta (200):**

```json
{
  "mensaje": "Interés eliminado"
}
```

**Errores:**

- `404`: La relación no existe

---

## ⭐ Reseñas

### POST /resenas

Crea una reseña para un evento, restaurante o lugar cultural.

**Parámetros:**

```json
{
  "user_id": 1,
  "entidad_tipo": "gastro",
  "entidad_id": 42,
  "puntuacion": 4,
  "texto": "Excelente comida, muy recomendado."
}
```

**Validaciones:**

- `entidad_tipo`: "event" | "gastro" | "cultura"
- `puntuacion`: 1-5

**Respuesta (201):**

```json
{
  "mensaje": "Reseña creada",
  "id": 1
}
```

**Errores:**

- `400`: Faltan campos obligatorios
- `400`: Tipo de entidad inválido
- `400`: Puntuación fuera de rango

---

### GET /resenas/{entidad_tipo}/{entidad_id}

Obtiene todas las reseñas para una entidad.

**Parámetros URL:**

- `entidad_tipo`: "event" | "gastro" | "cultura"
- `entidad_id`: integer

**Respuesta (200):**

```json
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
```

**Errores:**

- `400`: Tipo de entidad inválido

---

## 🎪 Eventos

### GET /eventos

Obtiene los últimos 10 eventos más recientes.

**Respuesta (200):**

```json
[
  {
    "id": "evt_001",
    "name_es": "Festival de Música Urbana",
    "start_date": "2026-06-15T18:00:00",
    "municipality_es": "Madrid",
    "price_eur": 25.5
  },
  {
    "id": "evt_002",
    "name_es": "Concierto de Jazz",
    "start_date": "2026-06-20T20:00:00",
    "municipality_es": "Barcelona",
    "price_eur": null
  }
]
```

---

## 🏁 Verificación

### GET /

Verifica que la API está funcionando.

**Respuesta (200):**

```json
{
  "message": "Bienvenidos a la API SustraiApp"
}
```

---

## 📋 Ejemplo de Flujo Completo

### 1. Registrar usuario

```bash
curl -X POST http://localhost:5000/registro \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "email": "juan@example.com",
    "password": "pass123",
    "municipio": "Madrid",
    "provincia": "Madrid",
    "sexo": "M",
    "age": 28
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "password": "pass123"
  }'
```

### 3. Actualizar preferencias

```bash
curl -X PUT http://localhost:5000/usuarios/1/preferencias \
  -H "Content-Type: application/json" \
  -d '{
    "le_gusta_gastro": true,
    "rango_precio": "medio"
  }'
```

### 4. Ver intereses disponibles

```bash
curl -X GET http://localhost:5000/intereses
```

### 5. Agregar interés

```bash
curl -X POST http://localhost:5000/usuarios/1/intereses \
  -H "Content-Type: application/json" \
  -d '{"id_interes": 3}'
```

### 6. Ver intereses del usuario

```bash
curl -X GET http://localhost:5000/usuarios/1/intereses
```

### 7. Crear reseña

```bash
curl -X POST http://localhost:5000/resenas \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "entidad_tipo": "gastro",
    "entidad_id": 42,
    "puntuacion": 5,
    "texto": "¡Excelente experiencia!"
  }'
```

### 8. Ver reseñas de un lugar

```bash
curl -X GET http://localhost:5000/resenas/gastro/42
```

### 9. Ver eventos recientes

```bash
curl -X GET http://localhost:5000/eventos
```

---

## 🔗 Estructura de Bases de Datos

### Esquema: user_data

- `users` - Tabla de usuarios
- `user_preferences` - Preferencias por usuario
- `user_intereses` - Relación usuario-intereses
- `intereses` - Categorías de intereses
- `reviews` - Reseñas de usuarios

### Esquema: market_data

- `events` - Eventos disponibles
- `gastronomy` - Lugares gastronómicos
- `culture` - Lugares culturales

---

## ⚠️ Códigos de Estado HTTP

- `200 OK` - Solicitud exitosa
- `201 CREATED` - Recurso creado exitosamente
- `400 BAD REQUEST` - Solicitud inválida o parámetros incorrectos
- `401 UNAUTHORIZED` - Credenciales inválidas
- `404 NOT FOUND` - Recurso no encontrado
- `409 CONFLICT` - Conflicto (ej: email duplicado)
- `500 INTERNAL SERVER ERROR` - Error del servidor
