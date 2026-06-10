# 🎨 SustraiApp - API de Recomendaciones de Turismo Sostenible

Plataforma inteligente de recomendaciones personalizadas para descubrir gastronomía, patrimonio cultural y eventos en el País Vasco, basada en sistemas de recomendación SVD (Singular Value Decomposition).

## 📋 Tabla de Contenidos

- [Instalación](#instalación)
- [Configuración](#configuración)
- [Endpoints](#endpoints)
- [Flujos Principales](#flujos-principales)
- [Tecnologías](#tecnologías)

---

## 🚀 Instalación

### Requisitos Previos

- Python 3.11+
- PostgreSQL 12+
- Git

### Pasos de Instalación

```bash
# 1. Clonar el repositorio
git clone <repositorio>
cd Desafío

# 2. Crear ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
# Copiar .env y ajustar credenciales de PostgreSQL
```

### Variables de Entorno (.env)

```env
# PostgreSQL
PGHOST=localhost
PGPORT=5432
PGDATABASE=sustraiapp
PGUSER=postgres
PGPASSWORD=postgres

# Admin
ADMIN_DEFAULT_PASSWORD=SuperSecreta123!
```

---

## ⚙️ Configuración

### Base de Datos

La aplicación espera los siguientes esquemas en PostgreSQL:

- `user_data`: Datos de usuarios, reseñas y preferencias
- `market_data`: Gastronomía, patrimonio cultural y eventos
- `shared`: Municipios y datos compartidos

### Modelos de IA

La carpeta `models/` contiene los modelos SVD pre-entrenados:

- `svd_gastro.pkl` - Recomendaciones de gastronomía
- `svd_patrimonio.pkl` - Recomendaciones de patrimonio cultural
- `svd_eventos.pkl` - Recomendaciones de eventos

---

## 📡 Endpoints

### 🏥 Health Check

#### GET /

Verifica que la API está activa.

**Respuesta (200):**

```json
{
  "data": {
    "message": "Bienvenidos a la API SustraiApp"
  }
}
```

#### GET /health

Estado completo del servidor.

**Respuesta (200):**

```json
{
  "status": "ok",
  "gastro": 245,
  "cultura": 89,
  "eventos": 56
}
```

---

## 🔐 Autenticación

### POST /registro

Registra un nuevo usuario en la plataforma.

**Parámetros requeridos:**

```json
{
  "nombre": "Juan",
  "email": "juan@example.com",
  "password": "mipassword123",
  "municipality_id": 5,
  "sexo": "hombre",
  "age": 28
}
```

**Parámetros opcionales:**

- `apellido`: string
- `tlf`: string

**Respuesta exitosa (201):**

```json
{
  "data": {
    "mensaje": "Usuario creado",
    "usuario": {
      "id_user": 1,
      "nombre": "Juan",
      "email": "juan@example.com",
      "municipality_id": 5,
      "sexo": "hombre",
      "age": 28,
      "role": "user"
    }
  }
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
  "data": {
    "mensaje": "Login exitoso",
    "user_id": 1,
    "role": "user"
  }
}
```

**Errores:**

- `400`: Faltan email o password
- `401`: Credenciales inválidas

---

## 🗺️ Municipios

### GET /api/municipios

Obtiene la lista de todos los municipios disponibles.

**Respuesta (200):**

```json
{
  "data": [
    {
      "id": 1,
      "nombre": "Bilbao",
      "provincia": "Bizkaia",
      "province_code": "48"
    },
    {
      "id": 2,
      "nombre": "Vitoria",
      "provincia": "Álava",
      "province_code": "01"
    }
  ]
}
```

---

## 🎪 Eventos

### GET /api/eventos

Lista general de eventos con filtros avanzados.

**Parámetros opcionales:**

- `municipality_id`: integer - Filtrar por municipio
- `is_free`: boolean - Solo eventos gratuitos
- `type`: string - Tipo de evento
- `limit`: integer (default: 20) - Eventos por página
- `offset`: integer (default: 0) - Desplazamiento

**Respuesta (200):**

```json
{
  "data": [
    {
      "id": 1,
      "nombre": "Concierto de Jazz",
      "type": "concierto",
      "start_date": "2026-06-20T20:00:00",
      "municipality_id": 1,
      "is_free": true,
      "language": "ES"
    }
  ],
  "meta": {
    "total": 45,
    "limit": 20,
    "offset": 0
  }
}
```

### GET /api/eventos/esta-semana

Eventos de la semana actual.

### GET /api/eventos/fin-de-semana

Eventos de fin de semana en los próximos 7 días.

### GET /api/eventos/en-euskera

Eventos disponibles en idioma euskera.

### GET /api/eventos/cerca-de-ti

Eventos en el municipio del usuario autenticado.

**Headers requeridos:**

- `X-User-Id`: integer

---

## 🍽️ Gastronomía

### GET /api/gastronomia

Lista general de restaurantes con filtros avanzados.

**Parámetros opcionales:**

- `municipality_id`: integer - Filtrar por municipio
- `tipo_comida`: string - Tipo de comida
- `michelin`: boolean - Solo con estrella Michelin
- `limit`: integer (default: 20)
- `offset`: integer (default: 0)

**Respuesta (200):**

```json
{
  "data": [
    {
      "id": 1,
      "nombre": "Asador Etxebarri",
      "type": "asador",
      "tipo_comida": "vasca",
      "municipality_id": 1,
      "nivel_precio": "alto",
      "valoracion": 4.8,
      "michelin": true
    }
  ],
  "meta": {
    "total": 120,
    "limit": 20,
    "offset": 0
  }
}
```

### GET /api/gastronomia/mejor-valorados

Establecimientos con ≥10 reseñas, ordenados por valoración.

### GET /api/gastronomia/entorno-especial

Restaurantes con entorno especial (Costa, Montaña, etc).

### GET /api/gastronomia/cerca-de-ti

Restaurantes en el municipio del usuario.

**Headers requeridos:**

- `X-User-Id`: integer

### GET /api/gastronomia/{id}/cualificaciones

Obtiene las cualificaciones especiales (Michelin, Repsol, etc) de un restaurante.

---

## 🏛️ Cultura y Patrimonio

### GET /api/cultura

Lista general de lugares culturales.

**Parámetros opcionales:**

- `municipality_id`: integer
- `tipo_lugar`: string (museo | patrimonio cultural | visita_guiada)
- `visita_guiada`: boolean
- `limit`: integer (default: 20)
- `offset`: integer (default: 0)

### GET /api/cultura/museos

Museos disponibles en la plataforma.

### GET /api/cultura/patrimonio

Lugares de patrimonio cultural e histórico.

### GET /api/cultura/visita-guiada

Lugares culturales que ofrecen visitas guiadas.

### GET /api/cultura/cerca-de-ti

Lugares culturales en el municipio del usuario.

**Headers requeridos:**

- `X-User-Id`: integer

---

## 👥 Preferencias del Usuario

### GET /usuarios/{user_id}/preferencias

Obtiene las preferencias de un usuario.

**Respuesta (200):**

```json
{
  "data": {
    "user_id": 1,
    "rango_precio": "medio",
    "movilidad_reducida": false,
    "municipios_interes": [1, 5, 8]
  }
}
```

### PUT /usuarios/{user_id}/preferencias

Actualiza las preferencias de un usuario.

**Parámetros (todos opcionales):**

```json
{
  "rango_precio": "alto",
  "movilidad_reducida": true,
  "municipios_interes": [1, 5, 8, 12]
}
```

**Respuesta (200):**

```json
{
  "data": {
    "mensaje": "Preferencias actualizadas",
    "data": { ...preferencias actualizadas... }
  }
}
```

---

## 🎯 Intereses

### GET /intereses

Obtiene la lista completa de categorías de intereses.

**Respuesta (200):**

```json
{
  "data": [
    {
      "id_interes": 1,
      "nombre": "Gastronomía"
    },
    {
      "id_interes": 2,
      "nombre": "Patrimonio Cultural"
    }
  ]
}
```

### GET /usuarios/{user_id}/intereses

Obtiene los intereses seleccionados por un usuario.

**Respuesta (200):**

```json
{
  "data": {
    "id_user": 1,
    "intereses": [1, 3, 5]
  }
}
```

### POST /usuarios/{user_id}/intereses

Agrega un interés a un usuario.

**Parámetros:**

```json
{
  "id_interes": 3
}
```

**Respuesta (201):**

```json
{
  "data": {
    "mensaje": "Interés agregado"
  }
}
```

### DELETE /usuarios/{user_id}/intereses/{id_interes}

Elimina un interés de un usuario.

**Respuesta (200):**

```json
{
  "data": {
    "mensaje": "Interés eliminado"
  }
}
```

---

## ⭐ Reseñas

### POST /resenas

Crea una reseña para un evento, restaurante o lugar cultural.

**Parámetros:**

```json
{
  "user_id": 1,
  "entidad_tipo": "gastro",
  "entidad_id": 15,
  "puntuacion": 5,
  "texto": "Excelente comida y servicio impecable"
}
```

**Validaciones:**

- `entidad_tipo`: "event" | "gastro" | "cultura"
- `puntuacion`: 1-5

**Respuesta (201):**

```json
{
  "data": {
    "mensaje": "Reseña creada",
    "id": 1
  }
}
```

### GET /resenas/{entidad_tipo}/{entidad_id}

Obtiene todas las reseñas para una entidad.

**Parámetros URL:**

- `entidad_tipo`: "event" | "gastro" | "cultura"
- `entidad_id`: integer

**Respuesta (200):**

```json
{
  "data": [
    {
      "id": 1,
      "user_id": 1,
      "puntuacion": 5,
      "texto": "Excelente comida",
      "created_at": "2026-06-02T10:30:00"
    }
  ]
}
```

---

## 🤖 ChatBot Asistente

### POST /api/chat

Devuelve recomendaciones personalizadas basadas en lenguaje natural.

**Headers requeridos:**

- `X-User-Id`: integer - ID del usuario
- `Content-Type`: application/json

**Parámetros:**

```json
{
  "message": "Quiero comer algo típico en Bilbao",
  "session_id": "conversacion-123"
}
```

**Respuesta (200):**

```json
{
  "data": {
    "suggestion": "Te propongo estos asadores especializados en carne vasca...",
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
      "intereses": [1],
      "fecha_inicio": null,
      "fecha_fin": null
    },
    "aviso": null
  }
}
```

---

## 🎁 Recomendaciones Personalizadas

### GET /recomendaciones/gastro

Obtiene recomendaciones de gastronomía personalizadas.

**Parámetros requeridos:**

- `user_id`: integer - ID del usuario

**Parámetros opcionales:**

- `top_n`: integer (default: 10) - Número de recomendaciones
- `tipo_lugar`: string - Filtrar por tipo
- `provincia`: string - Filtrar por provincia
- `precio`: string - Filtrar por rango

**Respuesta (200):**

```json
{
  "user_id": 1,
  "categoria": "gastro",
  "metodo": "SVD personalizado",
  "ids": [15, 22, 8, 35],
  "resultados": [
    {
      "id": 15,
      "puntuacion_estimada": 4.8,
      "patrocinado": false
    }
  ]
}
```

### GET /recomendaciones/cultura

Obtiene recomendaciones de patrimonio cultural.

**Parámetros:**

- `user_id`: integer (requerido)
- `top_n`: integer (default: 10)
- `tipo_lugar`: string
- `provincia`: string

### GET /recomendaciones/eventos

Obtiene recomendaciones de eventos.

**Parámetros:**

- `user_id`: integer (requerido)
- `top_n`: integer (default: 10)
- `tipo`: string
- `provincia`: string
- `gratis`: boolean - Solo eventos gratuitos
- `finde`: boolean - Solo fin de semana

---

## 📊 Flujos Principales

### Flujo 1: Registro y Onboarding

```
1. POST /registro          → Crear usuario
2. POST /usuarios/{id}/intereses → Agregar intereses
3. PUT /usuarios/{id}/preferencias → Configurar preferencias
```

### Flujo 2: Descubrimiento

```
1. GET /api/municipios     → Ver municipios disponibles
2. GET /api/gastronomia    → Explorar restaurantes
3. GET /api/cultura        → Descubrir patrimonio
4. GET /api/eventos        → Ver eventos próximos
```

### Flujo 3: Recomendaciones Inteligentes

```
1. POST /login             → Autenticarse
2. GET /recomendaciones/gastro → Obtener recomendaciones personalizadas
3. GET /resenas/{tipo}/{id}    → Ver opiniones de otros
4. POST /resenas           → Dejar reseña
```

### Flujo 4: Chat Asistente

```
1. POST /login             → Autenticarse
2. POST /api/chat          → Hacer consulta conversacional
3. GET /api/gastronomia/{id}/cualificaciones → Ver detalles
4. POST /resenas           → Dejar reseña
```

---

## 🔍 Provincias Soportadas

- **Álava/Araba**: Código `01`
- **Guipúzcoa/Gipuzkoa**: Código `20`
- **Vizcaya/Bizkaia**: Código `48`

---

## 🛠️ Tecnologías

- **Backend**: Flask + SQLAlchemy
- **Base de Datos**: PostgreSQL
- **IA/ML**: Scikit-Surprise (SVD)
- **NLP**: Procesamiento de lenguaje natural
- **Auth**: Contraseñas hasheadas (bcrypt)

---

## ⚠️ Códigos de Estado HTTP

- `200 OK` - Solicitud exitosa
- `201 CREATED` - Recurso creado exitosamente
- `400 BAD REQUEST` - Solicitud inválida
- `401 UNAUTHORIZED` - Credenciales inválidas
- `404 NOT FOUND` - Recurso no encontrado
- `409 CONFLICT` - Conflicto (email duplicado, etc)
- `500 INTERNAL SERVER ERROR` - Error del servidor

---

## 📝 Ejemplo Completo de Uso

```bash
# 1. Registrar usuario
curl -X POST http://localhost:5000/registro \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "María",
    "email": "maria@example.com",
    "password": "pass123",
    "municipality_id": 1,
    "sexo": "mujer",
    "age": 32
  }'

# 2. Login
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "maria@example.com",
    "password": "pass123"
  }'

# 3. Actualizar preferencias
curl -X PUT http://localhost:5000/usuarios/1/preferencias \
  -H "Content-Type: application/json" \
  -d '{
    "rango_precio": "alto",
    "municipios_interes": [1, 3, 5]
  }'

# 4. Agregar intereses
curl -X POST http://localhost:5000/usuarios/1/intereses \
  -H "Content-Type: application/json" \
  -d '{"id_interes": 1}'

# 5. Obtener recomendaciones personalizadas
curl -X GET "http://localhost:5000/recomendaciones/gastro?user_id=1&top_n=5" \
  -H "X-User-Id: 1"

# 6. Ver restaurante específico
curl -X GET "http://localhost:5000/api/gastronomia?municipality_id=1&limit=5" \
  -H "X-User-Id: 1"

# 7. Chat asistente
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{
    "message": "Quiero un buen asador en Bilbao",
    "session_id": "chat-001"
  }'

# 8. Dejar reseña
curl -X POST http://localhost:5000/resenas \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "entidad_tipo": "gastro",
    "entidad_id": 15,
    "puntuacion": 5,
    "texto": "Excelente experiencia"
  }'
```

---

## 📞 Soporte

Para reportar bugs o sugerir mejoras, contacta al equipo de desarrollo.
