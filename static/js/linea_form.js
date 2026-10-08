// Calcula el total del año y el costo mientras se escribe en el formulario de línea.
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const campos = MESES.concat(['precio_unitario_est']);
const formato = new Intl.NumberFormat('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function recalcular() {
  let total = 0;
  MESES.forEach(function (mes) {
    total += parseInt(document.getElementById('id_' + mes).value, 10) || 0;
  });
  const precio = parseFloat(document.getElementById('id_precio_unitario_est').value.replace(',', '.')) || 0;
  document.getElementById('total-anual').textContent = total;
  document.getElementById('costo-estimado').textContent = formato.format(total * precio);
}

campos.forEach(function (nombre) {
  document.getElementById('id_' + nombre).addEventListener('input', recalcular);
});
recalcular();  // al abrir, calcula con lo que ya tenga (útil al editar)