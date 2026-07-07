"""
=============================================================================
HELPERS DE VÍAS · MÓDULO DE GESTIÓN DE UBICACIONES
=============================================================================

Este módulo proporciona funciones para gestionar la jerarquía de ubicaciones:

Jerarquía:
    Provincia → Municipio → Tipo de Vía + Calle

Funciones de lectura (GET):
    - cargar_provincias()
    - cargar_municipios(id_provincia, texto)
    - cargar_tipos_via(texto)
    - cargar_calles(id_municipio, id_tipo_via, texto)

Funciones de escritura (POST):
    - insertar_municipio(id_provincia, nombre_mun, codigo_postal)
    - insertar_tipo_via(nombre_tipo)
    - insertar_calle(id_municipio, id_tipo_via, nombre_calle)

Tablas involucradas:
    - tbl_provincias
    - tbl_municipios
    - tbl_tipos_de_vias
    - tbl_calles

Autor: Tino Hierro
Última actualización: 2026-05-23
=============================================================================
"""

from __future__ import annotations

from typing import Any

from services.helpers import ejecutar_consulta, insertar_generico

# =============================================================================
# FUNCIONES DE CARGA (GET)
# =============================================================================


def cargar_provincias() -> list[dict[str, Any]]:
    """
    Carga todas las provincias desde tbl_provincias.

    Returns:
        Lista de diccionarios con estructura:
        [
            {
                'idtbl_provincias': int,
                'provincias': str
            },
            ...
        ]
        Retorna lista vacía [] si no hay provincias o hay error.

    Example:
        >>> provincias = cargar_provincias()
        >>> print(provincias[0])
        {'idtbl_provincias': 1, 'provincias': 'Ávila'}
    """
    query = """
        SELECT 
            idtbl_provincias,
            provincias
        FROM tbl_provincias
        ORDER BY provincias ASC
    """

    resultados = ejecutar_consulta(query, devolver_dict=True, database="bd_tbl_comunes")
    return resultados or []


def cargar_municipios(
    id_provincia: int | None, texto: str = ""
) -> list[dict[str, Any]]:
    """
    Carga municipios de una provincia, con filtrado opcional por texto.

    Args:
        id_provincia: ID de la provincia (None = todos los municipios)
        texto: Texto para filtrar por nombre de municipio (case-insensitive)

    Returns:
        Lista de diccionarios con estructura:
        [
            {
                'idtbl_municipios': int,
                'idtbl_provincias': int,
                'municipios': str
            },
            ...
        ]
        Retorna lista vacía [] si no hay resultados o hay error.

    Example:
        >>> # Todos los municipios de Ávila (provincia 1)
        >>> municipios = cargar_municipios(id_provincia=1)
        >>> print(len(municipios))
        248

        >>> # Filtrar por texto
        >>> municipios = cargar_municipios(id_provincia=1, texto="ávila")
        >>> print(municipios[0])
        {'idtbl_municipios': 395, 'municipios': 'Ávila', ...}
    """
    query = """
        SELECT 
            idtbl_municipios,
            idtbl_provincias,
            municipios
        FROM tbl_municipios
        WHERE 1=1
    """

    params = []

    # Filtrar por provincia si se especifica
    if id_provincia:
        query += " AND idtbl_provincias = %s"
        params.append(id_provincia)

    # Filtrar por texto si se especifica
    if texto:
        query += " AND municipios LIKE %s"
        params.append(f"%{texto}%")

    query += " ORDER BY municipios ASC"

    resultados = ejecutar_consulta(
        query, params, devolver_dict=True, database="bd_tbl_comunes"
    )
    return resultados or []


def cargar_tipos_via(texto: str = "") -> list[dict[str, Any]]:
    """
    Carga tipos de vía con filtrado opcional por texto.

    Args:
        texto: Texto para filtrar por nombre de tipo de vía (case-insensitive)

    Returns:
        Lista de diccionarios con estructura:
        [
            {
                'idtbl_tipos_de_vias': int,
                'tipos_de_vias': str
            },
            ...
        ]
        Retorna lista vacía [] si no hay resultados o hay error.

    Example:
        >>> # Todos los tipos de vía
        >>> tipos = cargar_tipos_via()
        >>> print(tipos[0])
        {'idtbl_tipos_de_vias': 1, 'tipos_de_vias': 'Calle'}

        >>> # Filtrar por texto
        >>> tipos = cargar_tipos_via(texto="avenida")
        >>> print(tipos[0])
        {'idtbl_tipos_de_vias': 2, 'tipos_de_vias': 'Avenida'}
    """
    query = """
        SELECT 
            idtbl_tipos_de_vias,
            tipos_de_vias
        FROM tbl_tipos_de_vias
        WHERE 1=1
    """

    params = []

    # Filtrar por texto si se especifica
    if texto:
        query += " AND tipos_de_vias LIKE %s"
        params.append(f"%{texto}%")

    query += " ORDER BY tipos_de_vias ASC"

    resultados = ejecutar_consulta(
        query, params, devolver_dict=True, database="bd_tbl_comunes"
    )
    return resultados or []


def cargar_calles(
    id_municipio: int | None,
    id_tipo_via: int | None,
    texto: str = "",
) -> list[dict[str, Any]]:
    """
    Carga calles de un municipio y tipo de vía, con filtrado opcional.

    Args:
        id_municipio: ID del municipio (None = todas las calles)
        id_tipo_via: ID del tipo de vía (None = todos los tipos)
        texto: Texto para filtrar por nombre de calle (case-insensitive)

    Returns:
        Lista de diccionarios con estructura:
        [
            {
                'idtbl_calles': int,
                'idtbl_municipios': int,
                'idtbl_tipos_de_vias': int,
                'calles': str
            },
            ...
        ]
        Retorna lista vacía [] si no hay resultados o hay error.

    Example:
        >>> # Calles tipo "Calle" de Ávila
        >>> calles = cargar_calles(
        ...     id_municipio=395,
        ...     id_tipo_via=1
        ... )
        >>> print(len(calles))
        156

        >>> # Filtrar por nombre
        >>> calles = cargar_calles(
        ...     id_municipio=395,
        ...     id_tipo_via=1,
        ...     texto="mayor"
        ... )
        >>> print(calles[0])
        {'idtbl_calles': 100, 'calles': 'Mayor', ...}

    Warning:
        Si id_municipio e id_tipo_via son None, se retornan TODAS las calles
        de la base de datos. Esto puede ser muy lento en bases grandes.
    """
    query = """
        SELECT 
            idtbl_calles,
            idtbl_municipios,
            idtbl_tipos_de_vias,
            calles
        FROM tbl_calles
        WHERE 1=1
    """

    params = []

    # Filtrar por municipio si se especifica
    if id_municipio:
        query += " AND idtbl_municipios = %s"
        params.append(id_municipio)

    # Filtrar por tipo de vía si se especifica
    if id_tipo_via:
        query += " AND idtbl_tipos_de_vias = %s"
        params.append(id_tipo_via)

    # Filtrar por texto si se especifica
    if texto:
        query += " AND calles LIKE %s"
        params.append(f"%{texto}%")

    query += " ORDER BY calles ASC"

    resultados = ejecutar_consulta(
        query, params, devolver_dict=True, database="bd_tbl_comunes"
    )
    return resultados or []


# =============================================================================
# FUNCIONES DE INSERCIÓN (POST)
# =============================================================================


def insertar_municipio(
    id_provincia: int,
    nombre_mun: str,
    codigo_postal: str | None = None,
) -> int:
    """
    Inserta un nuevo municipio en tbl_municipios.

    Args:
        id_provincia: ID de la provincia a la que pertenece (debe existir)
        nombre_mun: Nombre del municipio (será limpiado de espacios)
        codigo_postal: Código postal (opcional, puede ser None)

    Returns:
        ID del municipio recién creado (AUTO_INCREMENT)

    Raises:
        ValueError: Si id_provincia <= 0 o nombre_mun está vacío
        Exception: Si falla la inserción en BD

    Example:
        >>> # Insertar municipio con código postal
        >>> nuevo_id = insertar_municipio(
        ...     id_provincia=1,
        ...     nombre_mun="Arévalo",
        ...     codigo_postal="05200"
        ... )
        >>> print(f"Municipio creado con ID: {nuevo_id}")
        Municipio creado con ID: 396

        >>> # Insertar sin código postal
        >>> nuevo_id = insertar_municipio(
        ...     id_provincia=1,
        ...     nombre_mun="Solosancho"
        ... )
    """
    # Validar id_provincia
    if not id_provincia or id_provincia <= 0:
        raise ValueError("id_provincia debe ser mayor que 0")

    # Validar nombre_mun
    if not nombre_mun or not nombre_mun.strip():
        raise ValueError("nombre_mun no puede estar vacío")

    # Insertar en base de datos
    nuevo_id = insertar_generico(
        tabla="tbl_municipios",
        campos={
            "idtbl_provincias": id_provincia,
            "municipios": nombre_mun.strip(),
            "codigo_postal": codigo_postal,
        },
        database="bd_tbl_comunes",
    )

    # Verificar que se insertó correctamente
    if not nuevo_id:
        raise Exception("No se pudo insertar el municipio")

    return nuevo_id


def insertar_tipo_via(nombre_tipo: str) -> int:
    """
    Inserta un nuevo tipo de vía en tbl_tipos_de_vias.

    Args:
        nombre_tipo: Nombre del tipo de vía (ej: "Calle", "Avenida", "Plaza")
            Será limpiado de espacios al inicio/final

    Returns:
        ID del tipo de vía recién creado (AUTO_INCREMENT)

    Raises:
        ValueError: Si nombre_tipo está vacío
        Exception: Si falla la inserción en BD

    Example:
        >>> # Insertar nuevo tipo de vía
        >>> nuevo_id = insertar_tipo_via("Pasaje")
        >>> print(f"Tipo de vía creado con ID: {nuevo_id}")
        Tipo de vía creado con ID: 12

        >>> # Insertar con espacios (se limpian automáticamente)
        >>> nuevo_id = insertar_tipo_via("  Glorieta  ")
        >>> # Se guarda como "Glorieta"
    """
    # Validar nombre_tipo
    if not nombre_tipo or not nombre_tipo.strip():
        raise ValueError("nombre_tipo no puede estar vacío")

    # Insertar en base de datos
    nuevo_id = insertar_generico(
        tabla="tbl_tipos_de_vias",
        campos={
            "tipos_de_vias": nombre_tipo.strip(),
        },
        database="bd_tbl_comunes",
    )

    # Verificar que se insertó correctamente
    if not nuevo_id:
        raise Exception("No se pudo insertar el tipo de vía")

    return nuevo_id


def insertar_calle(id_municipio: int, id_tipo_via: int, nombre_calle: str) -> int:
    """
    Inserta una nueva calle en tbl_calles.

    Args:
        id_municipio: ID del municipio al que pertenece la calle (debe existir)
        id_tipo_via: ID del tipo de vía (Calle, Avenida, etc.) (debe existir)
        nombre_calle: Nombre de la calle SIN el tipo de vía
            Ejemplo: "Mayor" (NO "Calle Mayor")

    Returns:
        ID de la calle recién creada (AUTO_INCREMENT)

    Raises:
        ValueError: Si algún parámetro es inválido
        Exception: Si falla la inserción en BD

    Example:
        >>> # Insertar "Calle Mayor" en Ávila
        >>> nuevo_id = insertar_calle(
        ...     id_municipio=395,  # Ávila
        ...     id_tipo_via=1,      # Calle
        ...     nombre_calle="Mayor"
        ... )
        >>> print(f"Calle creada con ID: {nuevo_id}")
        Calle creada con ID: 1234

        >>> # Insertar "Avenida de Portugal" en Ávila
        >>> nuevo_id = insertar_calle(
        ...     id_municipio=395,   # Ávila
        ...     id_tipo_via=2,       # Avenida
        ...     nombre_calle="de Portugal"
        ... )

    Note:
        El nombre de la calle NO debe incluir el tipo de vía.

        ✅ Correcto:
            nombre_calle="Mayor"

        ❌ Incorrecto:
            nombre_calle="Calle Mayor"
    """
    # Validar id_municipio
    if not id_municipio or id_municipio <= 0:
        raise ValueError("id_municipio debe ser mayor que 0")

    # Validar id_tipo_via
    if not id_tipo_via or id_tipo_via <= 0:
        raise ValueError("id_tipo_via debe ser mayor que 0")

    # Validar nombre_calle
    if not nombre_calle or not nombre_calle.strip():
        raise ValueError("nombre_calle no puede estar vacío")

    # Insertar en base de datos
    nuevo_id = insertar_generico(
        tabla="tbl_calles",
        campos={
            "idtbl_municipios": id_municipio,
            "idtbl_tipos_de_vias": id_tipo_via,
            "calles": nombre_calle.strip(),
        },
        database="bd_tbl_comunes",
    )

    # Verificar que se insertó correctamente
    if not nuevo_id:
        raise Exception("No se pudo insertar la calle")

    return nuevo_id
