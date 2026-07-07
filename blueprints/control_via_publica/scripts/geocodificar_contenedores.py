# geocodificar_contenedores.py

import time
import requests
from db import ejecutar_query

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocodificar_direccion(direccion: str):
    params = {
        "format": "json",
        "limit": 1,
        "q": direccion,
    }
    headers = {
        "User-Agent": "tubby-app-contenedores/1.0",
        "Accept-Language": "es",
    }
    resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None, None
    return float(data[0]["lat"]), float(data[0]["lon"])


def obtener_contenedores_pendientes():
    sql = """
    SELECT
        c.idtbl_control_contenedores,
        tv.tipos_de_vias AS tipo_via,
        ca.calles        AS calles
    FROM control_via_publica.tbl_control_contenedores c
    LEFT JOIN bd_tbl_comunes.tbl_tipos_de_vias tv
      ON tv.idtbl_tipos_de_vias = c.idtbl_tipos_de_vias
    LEFT JOIN bd_tbl_comunes.tbl_calles ca
      ON ca.idtbl_calles = c.idtbl_calles
    WHERE ca.calles IS NOT NULL
      AND c.latitud  IS NULL
      AND c.longitud IS NULL
    """
    return ejecutar_query(sql, nombre_bd="control_via_publica")


def actualizar_coordenadas_contenedor(id_contenedor, lat, lon):
    sql = """
    UPDATE control_via_publica.tbl_control_contenedores
    SET latitud = %s,
        longitud = %s
    WHERE idtbl_control_contenedores = %s
    """
    ejecutar_query(
        sql,
        (lat, lon, id_contenedor),
        nombre_bd="control_via_publica",
        commit=True,
    )


def main():
    filas = obtener_contenedores_pendientes()
    total = len(filas)
    print(f"Encontrados {total} contenedores sin coordenadas")

    for idx, fila in enumerate(filas, start=1):
        tipo_via = (fila.get("tipo_via") or "").strip()
        calle = (fila.get("calles") or "").strip()

        if not calle:
            print(f"[{idx}/{total}] Sin calle, se omite")
            continue

        if tipo_via:
            direccion = f"{tipo_via} {calle}, Ávila, España"
        else:
            direccion = f"{calle}, Ávila, España"

        print(f"[{idx}/{total}] Geocodificando: {direccion!r}")

        try:
            lat, lon = geocodificar_direccion(direccion)
        except Exception as e:
            print(f"  Error geocodificando: {e}")
            lat, lon = None, None

        if lat is not None and lon is not None:
            actualizar_coordenadas_contenedor(
                fila["idtbl_control_contenedores"],
                lat,
                lon,
            )
            print(f"  OK -> lat={lat:.6f}, lon={lon:.6f}")
        else:
            print("  Sin resultado, no se actualiza")

        # Respetar política de Nominatim
        time.sleep(1.1)


if __name__ == "__main__":
    main()
