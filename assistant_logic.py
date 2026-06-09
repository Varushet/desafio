# assistant_logic.py
import os
from pydantic import BaseModel
from typing import Optional, List
from models import db, Gastronomia, Cultura, Evento, UserInteres, Municipio

# Modelos de respuesta (Pydantic)
class Item(BaseModel):
    item_id: int
    nombre: str
    tipo: str
    categoria: str
    provincia: str
    estrella_prevista: float

class ChatResponse(BaseModel):
    suggestion: str
    items: List[Item] = []
    aviso: Optional[str] = None

def get_user_interests_from_db(user_id: int) -> list[int]:
    """Obtiene los IDs de interés directamente de PostgreSQL."""
    if not user_id:
        return []
    # Consulta directa a la tabla intermedia
    intereses = db.session.query(UserInteres.id_interes).filter_by(id_user=user_id).all()
    return [i[0] for i in intereses]

def buscar_recomendaciones(provincia: str, intereses_ids: list[int], top_n=5):
    """Busca en DB real usando SQLAlchemy."""
    resultados = []
    
    # Mapeo simple de IDs de interés a tipos de búsqueda (ejemplo simplificado)
    # En producción usarías la taxonomía completa de asistente.py
    es_gastro = any(i in [21, 22, 23, 24] for i in intereses_ids) if intereses_ids else True
    es_cultura = any(i in [29, 30, 31, 33] for i in intereses_ids) if intereses_ids else True
    
    # Obtener ID de provincia desde el nombre (si llega nombre) o viceversa
    # Aquí asumimos que 'provincia' llega como string "Bizkaia", etc.
    
    if es_gastro:
        query = Gastronomia.query.filter(Gastronomia.active == True)
        if provincia:
            # Unimos con Municipio para filtrar por provincia
            query = query.join(Municipio).filter(Municipio.provincia == provincia)
        
        # Si hay intereses específicos, podríamos filtrar por tipo_comida o cualificaciones
        items = query.order_by(Gastronomia.valoracion.desc()).limit(top_n).all()
        
        for g in items:
            resultados.append(Item(
                item_id=g.id,
                nombre=g.nombre,
                tipo="lugar",
                categoria=g.tipo_comida or "Gastronomía",
                provincia=g.municipio.provincia if g.municipio else provincia,
                estrella_prevista=float(g.valoracion or 4.0)
            ))

    if es_cultura and len(resultados) < top_n:
        query = Cultura.query.filter(Cultura.active == True)
        if provincia:
            query = query.join(Municipio).filter(Municipio.provincia == provincia)
            
        items = query.order_by(Cultura.valoracion.desc()).limit(top_n - len(resultados)).all()
        
        for c in items:
            resultados.append(Item(
                item_id=c.id,
                nombre=c.nombre,
                tipo="lugar",
                categoria=c.tipo_lugar,
                provincia=c.municipio.provincia if c.municipio else provincia,
                estrella_prevista=float(c.valoracion or 4.0)
            ))

    return resultados

def manejar_chat_flask(message: str, session_id: str, user_id: Optional[int] = None):
    """Lógica principal adaptada a Flask + SQLAlchemy."""
    
    # 1. Detección básica de provincia (puedes mejorar esto con regex)
    provincia = None
    msg_lower = message.lower()
    if "bizkaia" in msg_lower or "bilbao" in msg_lower: provincia = "Bizkaia"
    elif "gipuzkoa" in msg_lower or "san sebastian" in msg_lower: provincia = "Gipuzkoa"
    elif "araba" in msg_lower or "vitoria" in msg_lower: provincia = "Araba"
    
    # 2. Obtener intereses reales del usuario desde DB
    intereses_usuario = get_user_interests_from_db(user_id)
    
    # 3. Buscar en DB
    items_db = buscar_recomendaciones(provincia, intereses_usuario)
    
    # 4. Construir respuesta
    suggestion = f"He encontrado {len(items_db)} opciones interesantes en {provincia or 'el País Vasco'}."
    
    return ChatResponse(
        suggestion=suggestion,
        items=items_db,
        aviso=None
    )