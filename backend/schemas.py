from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str
    full_name: str
    sector: str
    needs_password_change: bool
    permissions: Optional[Dict[str, bool]] = None

class User(BaseModel):
    username: str
    role: str
    full_name: Optional[str] = None
    sector: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

class PasswordChange(BaseModel):
    new_password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    sector: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None

class RoleCreate(BaseModel):
    role_name: str

class RoleUpdate(BaseModel):
    permissions: Dict[str, bool]

class MetaUpdateRequest(BaseModel):
    direccion: Optional[str] = None
    gerencia: Optional[str] = None
    trata_reporte: Optional[str] = None
    tratas_incluidas: List[str]
    buzones_ingreso: List[str]
    analistas_oficiales: List[str]
    acronimos_egreso: List[str]
    activo: bool
    firmantes_egreso: Optional[List[str]] = None
    buzones_ingreso_intervenciones: Optional[List[str]] = None
    descripciones_validas: Optional[List[str]] = None
    descripcion_trata: Optional[str] = None

class MetaCreateRequest(BaseModel):
    direccion: str
    gerencia: str
    trata_reporte: str
    tratas_incluidas: List[str] = []
    buzones_ingreso: List[str] = []
    analistas_oficiales: List[str] = []
    acronimos_egreso: List[str] = []
    activo: bool = True
    firmantes_egreso: Optional[List[str]] = []
    buzones_ingreso_intervenciones: Optional[List[str]] = []
    descripciones_validas: Optional[List[str]] = []
    descripcion_trata: Optional[str] = ""

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class FamiliaUpdate(BaseModel):
    tratas: List[str]

class FamiliaCreate(BaseModel):
    nombre: str
    tratas: List[str]

class BuzonAccesoUpdate(BaseModel):
    tipo_sujeto: str
    nombre_sujeto: str
    buzones: List[str]

class AddAnalystRequest(BaseModel):
    usuario: str

class SearchRule(BaseModel):
    field: str
    operator: str
    value: Any

class AdvancedSearchRequest(BaseModel):
    conjunction: str
    rules: List[SearchRule]

class FavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FolderCreateRequest(BaseModel):
    name: str

class MoveFavoriteRequest(BaseModel):
    expediente: str
    folder_id: Optional[int] = None

class FavoriteNoteRequest(BaseModel):
    note_text: str

class FichaEditRequest(BaseModel):
    direccion: Optional[str] = None
    notas_internas: Optional[str] = None
    responsable: Optional[str] = None
    estado: Optional[str] = None
    prioridad: Optional[str] = None
    proxima_reunion: Optional[bool] = False

class FichaInternalNoteEditRequest(BaseModel):
    note_text: str

# Ciudad 3D / LFI Schemas
class LFIAssignRequest(BaseModel):
    seccion: str
    manzana: str

class LFINoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

class LFIDisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str

class AssignRequest(BaseModel):
    seccion: str
    manzana: str

class NoteRequest(BaseModel):
    seccion: str
    manzana: str
    nota: str

class ReviewRequest(BaseModel):
    seccion: str
    manzana: str
    decision: str
    comentario: Optional[str] = None
    disposicion: Optional[str] = None

class DisposicionRequest(BaseModel):
    seccion: str
    manzana: str
    disposicion: str
