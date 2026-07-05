CREATE OR REPLACE VIEW vw_agenda_via_publica_por_calle AS
SELECT
    ac.idtbl_calles,
    c.idtbl_tipos_de_vias,
    c.nombre_calle,

    a.idtbl_agenda,
    t.codigo              AS codigo_tipo_evento,
    t.nombre_publico      AS nombre_tipo_evento,
    t.color_hex,
    t.icono_css,
    t.prioridad,

    a.titulo,
    a.descripcion,
    a.fecha_inicio,
    a.fecha_fin,
    a.all_day,

    ac.numero_via_desde,
    ac.numero_via_hasta,
    ac.sentido,
    ac.observaciones      AS observaciones_tramo,

    a.origen_tabla,
    a.origen_id,

    a.creado_en,
    a.actualizado_en
FROM tbl_agenda_calles_afectadas ac
JOIN tbl_agenda_via_publica a
  ON ac.idtbl_agenda = a.idtbl_agenda
JOIN tbl_tipos_evento_via_publica t
  ON a.idtbl_tipos_evento = t.idtbl_tipos_evento
JOIN tbl_calles c
  ON ac.idtbl_calles = c.idtbl_calles;