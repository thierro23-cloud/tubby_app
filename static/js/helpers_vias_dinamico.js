/* ============================================================================
   🧠 HELPERS VIAS · SELECTORES DINÁMICOS
   ----------------------------------------------------------------------------
   ✔ Carga municipios según provincia
   ✔ Carga calles según municipio
   ✔ Compatible con cualquier formulario
   ============================================================================ */

document.addEventListener("DOMContentLoaded", function () {

    /* ========================================================================
       🟦 SECCIÓN 1 · REFERENCIAS
       ======================================================================== */
    const provinciaSelect = document.getElementById("provincia_select");
    const municipioSelect = document.getElementById("municipio_select");
    const calleSelect = document.getElementById("calle_select");

    /* ========================================================================
       🟧 SECCIÓN 2 · EVENTO PROVINCIA
       ======================================================================== */
    provinciaSelect.addEventListener("change", function () {

        const provinciaId = this.value;

        municipioSelect.innerHTML = '<option value="">Cargando...</option>';
        municipioSelect.disabled = true;

        fetch(`/helpers_vias/api/municipios/${provinciaId}`)
            .then(response => response.json())
            .then(data => {

                municipioSelect.innerHTML = '<option value="">-- Seleccionar municipio --</option>';

                data.forEach(municipio => {
                    municipioSelect.innerHTML +=
                        `<option value="${municipio.id}">${municipio.nombre}</option>`;
                });

                municipioSelect.disabled = false;
            });
    });

    /* ========================================================================
       🟥 SECCIÓN 3 · EVENTO MUNICIPIO
       ======================================================================== */
    municipioSelect.addEventListener("change", function () {

        const municipioId = this.value;

        calleSelect.innerHTML = '<option value="">Cargando...</option>';
        calleSelect.disabled = true;

        fetch(`/helpers_vias/api/calles/${municipioId}`)
            .then(response => response.json())
            .then(data => {

                calleSelect.innerHTML = '<option value="">-- Seleccionar calle --</option>';

                data.forEach(calle => {
                    calleSelect.innerHTML +=
                        `<option value="${calle.id}">${calle.nombre}</option>`;
                });

                calleSelect.disabled = false;
            });
    });

});