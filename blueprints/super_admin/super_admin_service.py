# =============================================================================
# 👑 SUPER ADMIN SERVICE · PRODUCCIÓN CON ROLES Y PERMISOS
# =============================================================================
# 🎯 OBJETIVO:
# Este servicio gestiona:
#   - Paneles, módulos y endpoints visibles en el panel Super Admin.
#   - Usuarios/gestores (policías, admins, operadores, etc.).
#   - Roles (SUPER_ADMIN, GESTOR, POLICIA, ...).
#   - Permisos por endpoint (VER_USUARIOS, EDITAR_PLZAS, etc.).
#
# DISEÑO DE TABLAS (ESQUEMA TÍPICO):
#
#   usuarios
#   --------
#   id              INT PK
#   nombre          VARCHAR
#   email           VARCHAR UNIQUE
#   activo          BOOL
#
#   roles
#   -----
#   id              INT PK
#   nombre          VARCHAR UNIQUE   (ej. 'SUPER_ADMIN', 'GESTOR', 'POLICIA')
#   descripcion     VARCHAR
#
#   usuario_roles
#   --------------
#   id_usuario      INT FK → usuarios.id
#   id_rol          INT FK → roles.id
#
#   paneles
#   -------
#   id              INT PK
#   nombre          VARCHAR UNIQUE   (ej. 'panel_usuarios_bp')
#
#   modulos
#   -------
#   id              INT PK
#   id_panel        INT FK → paneles.id
#   nombre          VARCHAR          (ej. 'gestores', 'plazas')
#
#   endpoints
#   ----------
#   id              INT PK
#   id_modulo       INT FK → modulos.id
#   endpoint_name   VARCHAR          (ej. 'usuarios_bp.listar')
#   ruta            VARCHAR          (ej. '/usuarios/')
#   activo          BOOL
#
#   permisos
#   --------
#   id              INT PK
#   codigo          VARCHAR UNIQUE   (ej. 'VER_USUARIOS', 'EDITAR_PLAZAS')
#   descripcion     VARCHAR
#
#   rol_permisos
#   -------------
#   id_rol          INT FK → roles.id
#   id_permiso      INT FK → permisos.id
#
#   permisos_endpoints
#   -------------------
#   id_permiso      INT FK → permisos.id
#   id_endpoint     INT FK → endpoints.id
#
# LÓGICA:
#   - Un usuario tiene uno o varios roles.
#   - Un rol tiene uno o varios permisos (abstractos).
#   - Un permiso se asocia a uno o varios endpoints.
#   - Para saber si un usuario puede usar un endpoint:
#       usuario → roles → permisos → endpoints autorizados.
#
# Las funciones de este servicio devuelven estructuras listas para el blueprint:
#   - listar_paneles()        → paneles para la UI
#   - listar_modulos(panel)   → módulos por panel
#   - listar_endpoints()      → endpoints con estado activo
#   - listar_gestores()       → usuarios/gestores que se muestran
#   - listar_permisos(id)     → permisos efectivos por gestor/usuario
#   - activar_endpoint()      → marca endpoint activo en BD
#   - desactivar_endpoint()   → marca endpoint inactivo en BD
#   - toggle_permiso()        → asigna/quita permiso a un rol de un usuario
# =============================================================================

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

# Aquí asumo que tienes modelos SQLAlchemy ya definidos:
# from app.models import Usuario, Rol, UsuarioRol, Panel, Modulo, Endpoint, Permiso, RolPermiso, PermisoEndpoint

# Para hacer este archivo autocontenido, usaré nombres genéricos de modelos.
# Solo tienes que mapearlos a tus modelos reales.


# =============================================================================
# 1️⃣ HELPERS DE BAJO NIVEL · ENVOLTURA DE BD
# =============================================================================

class SuperAdminRepo:
    """
    Capa de acceso a datos (repositorio) para el módulo Super Admin.
    Recibe una sesión de SQLAlchemy en cada método.
    """

    # -------------------------------------------------------------------------
    # 1.1️⃣ PANEL / MÓDULO / ENDPOINTS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_paneles(db: Session) -> List[Dict[str, Any]]:
        """
        Devuelve todos los paneles registrados.
        """
        rows = db.execute("""
            SELECT id, nombre
            FROM paneles
            ORDER BY nombre
        """).mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    def get_modulos_por_panel(db: Session, nombre_panel: str) -> List[Dict[str, Any]]:
        """
        Devuelve módulos asociados a un panel por su nombre.
        """
        rows = db.execute("""
            SELECT m.id, m.nombre, p.nombre AS panel
            FROM modulos m
            JOIN paneles p ON m.id_panel = p.id
            WHERE p.nombre = :nombre_panel
            ORDER BY m.nombre
        """, {"nombre_panel": nombre_panel}).mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    def get_endpoints(db: Session) -> List[Dict[str, Any]]:
        """
        Devuelve todos los endpoints conocidos con su estado.
        """
        rows = db.execute("""
            SELECT
                e.id,
                e.endpoint_name AS endpoint,
                e.ruta,
                e.activo,
                m.nombre       AS modulo,
                p.nombre       AS panel
            FROM endpoints e
            JOIN modulos  m ON e.id_modulo = m.id
            JOIN paneles  p ON m.id_panel  = p.id
            ORDER BY p.nombre, m.nombre, e.ruta
        """).mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    def set_endpoint_activo(db: Session, endpoint_name: str, activo: bool) -> bool:
        """
        Activa o desactiva un endpoint en BD.
        """
        result = db.execute("""
            UPDATE endpoints
            SET activo = :activo
            WHERE endpoint_name = :endpoint_name
        """, {"activo": 1 if activo else 0, "endpoint_name": endpoint_name})
        db.commit()
        return result.rowcount > 0

    # -------------------------------------------------------------------------
    # 1.2️⃣ USUARIOS / GESTORES / POLICÍAS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_gestores(db: Session) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de usuarios/gestores que se quieren administrar
        desde el panel super admin.

        Aquí puedes filtrar por tipo (gestores, policías, etc.) usando roles
        o un campo específico de la tabla usuarios.
        """
        rows = db.execute("""
            SELECT u.id            AS idtbl_gestores,
                   u.nombre        AS nombre,
                   u.email         AS email,
                   u.activo        AS activo
            FROM usuarios u
            ORDER BY u.nombre
        """).mappings().all()
        return [dict(r) for r in rows]

    @staticmethod
    def get_roles_de_usuario(db: Session, id_usuario: int) -> List[str]:
        """
        Devuelve la lista de nombres de roles que tiene un usuario.
        """
        rows = db.execute("""
            SELECT r.nombre
            FROM roles r
            JOIN usuario_roles ur ON ur.id_rol = r.id
            WHERE ur.id_usuario = :id_usuario
        """, {"id_usuario": id_usuario}).mappings().all()
        return [r["nombre"] for r in rows]

    # -------------------------------------------------------------------------
    # 1.3️⃣ PERMISOS EFECTIVOS POR USUARIO
    # -------------------------------------------------------------------------
    @staticmethod
    def get_permisos_efectivos_usuario(db: Session, id_usuario: int) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de endpoints con un flag tiene_permiso para un usuario.

        Resolución:
          usuario → roles → rol_permisos → permisos_endpoints → endpoints
        """
        rows = db.execute("""
            SELECT
                e.id,
                e.endpoint_name AS endpoint,
                e.ruta,
                e.activo,
                m.nombre       AS modulo,
                p.nombre       AS panel,
                1              AS tiene_permiso
            FROM usuario_roles ur
            JOIN roles r             ON ur.id_rol = r.id
            JOIN rol_permisos rp     ON rp.id_rol = r.id
            JOIN permisos per        ON per.id    = rp.id_permiso
            JOIN permisos_endpoints pe ON pe.id_permiso = per.id
            JOIN endpoints e         ON e.id      = pe.id_endpoint
            JOIN modulos m           ON m.id      = e.id_modulo
            JOIN paneles p           ON p.id      = m.id_panel
            WHERE ur.id_usuario      = :id_usuario
        """, {"id_usuario": id_usuario}).mappings().all()

        return [dict(r) for r in rows]

    @staticmethod
    def toggle_permiso_rol_sobre_endpoint(
        db: Session,
        id_rol: int,
        id_permiso: int,
    ) -> bool:
        """
        Alterna relación rol ↔ permiso (añade o elimina).
        """
        # ¿Existe ya?
        exists = db.execute("""
            SELECT 1
            FROM rol_permisos
            WHERE id_rol = :id_rol
              AND id_permiso = :id_permiso
        """, {"id_rol": id_rol, "id_permiso": id_permiso}).scalar()

        if exists:
            # Eliminar relación
            db.execute("""
                DELETE FROM rol_permisos
                WHERE id_rol = :id_rol
                  AND id_permiso = :id_permiso
            """, {"id_rol": id_rol, "id_permiso": id_permiso})
            db.commit()
            return True
        else:
            # Insertar relación
            db.execute("""
                INSERT INTO rol_permisos (id_rol, id_permiso)
                VALUES (:id_rol, :id_permiso)
            """, {"id_rol": id_rol, "id_permiso": id_permiso})
            db.commit()
            return True


# =============================================================================
# 2️⃣ SERVICIO DE ALTO NIVEL · API QUE USA EL BLUEPRINT
# =============================================================================

class SuperAdminService:
    """
    Capa de servicio que usa SuperAdminRepo y devuelve estructuras
    listas para consumir en el blueprint super_admin_bp.
    """

    # -------------------------------------------------------------------------
    # 2.1️⃣ PANEL / MÓDULOS / ENDPOINTS
    # -------------------------------------------------------------------------
    @staticmethod
    def listar_paneles(db: Session) -> List[Dict[str, Any]]:
        """
        Wrap de repo.get_paneles, por si quieres meter caching, filtrado, etc.
        """
        return SuperAdminRepo.get_paneles(db)

    @staticmethod
    def listar_modulos(db: Session, nombre_panel: str) -> List[Dict[str, Any]]:
        """
        Wrap de repo.get_modulos_por_panel.
        """
        return SuperAdminRepo.get_modulos_por_panel(db, nombre_panel)

    @staticmethod
    def listar_endpoints(db: Session) -> List[Dict[str, Any]]:
        """
        Devuelve todos los endpoints con su estado activo/inactivo.
        """
        return SuperAdminRepo.get_endpoints(db)

    @staticmethod
    def activar_endpoint(db: Session, nombre_endpoint: str) -> bool:
        """
        Activa un endpoint concreto.
        """
        ok = SuperAdminRepo.set_endpoint_activo(db, nombre_endpoint, True)
        if ok:
            print(f"[SUPER_ADMIN] Activado endpoint: {nombre_endpoint} @ {datetime.now()}")
        return ok

    @staticmethod
    def desactivar_endpoint(db: Session, nombre_endpoint: str) -> bool:
        """
        Desactiva un endpoint concreto.
        """
        ok = SuperAdminRepo.set_endpoint_activo(db, nombre_endpoint, False)
        if ok:
            print(f"[SUPER_ADMIN] Desactivado endpoint: {nombre_endpoint} @ {datetime.now()}")
        return ok

    # -------------------------------------------------------------------------
    # 2.2️⃣ GESTORES / USUARIOS / POLICÍAS
    # -------------------------------------------------------------------------
    @staticmethod
    def listar_gestores(db: Session) -> List[Dict[str, Any]]:
        """
        Devuelve todos los usuarios/gestores visibles en el panel.

        Aquí podrías:
          - Filtrar por rol (solo GESTOR, POLICIA, etc.).
          - Excluir SUPER_ADMIN si quieres.
        """
        gestores = SuperAdminRepo.get_gestores(db)
        for g in gestores:
            g["roles"] = SuperAdminRepo.get_roles_de_usuario(db, g["idtbl_gestores"])
        return gestores

    @staticmethod
    def listar_permisos(db: Session, id_gestor: int) -> List[Dict[str, Any]]:
        """
        Devuelve los permisos efectivos de un gestor sobre los endpoints.

        La UI puede usar esto para marcar qué endpoints tiene ese gestor
        (o mejor dicho, sus roles) permitidos.
        """
        return SuperAdminRepo.get_permisos_efectivos_usuario(db, id_gestor)

    # -------------------------------------------------------------------------
    # 2.3️⃣ TOGGLE PERMISO · A NIVEL DE ROL
    # -------------------------------------------------------------------------
    @staticmethod
    def toggle_permiso(
        db: Session,
        id_rol: int,
        id_permiso: int,
    ) -> bool:
        """
        Alterna un permiso concreto para un rol (SUPER_ADMIN, GESTOR, POLICIA…).

        Tu flujo sería algo así:
          - Desde la UI, seleccionas rol (ej. POLICIA) y permiso (ej. VER_PLACAS).
          - Llamas a este método para asociar o desasociar el permiso a ese rol.
          - Automáticamente, todos los usuarios con ese rol ganan/pierden ese permiso.
        """
        ok = SuperAdminRepo.toggle_permiso_rol_sobre_endpoint(db, id_rol, id_permiso)
        if ok:
            print(f"[SUPER_ADMIN] Toggle permiso id_permiso={id_permiso} para rol id_rol={id_rol}")
        return ok
