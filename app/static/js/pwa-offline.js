// pwa-offline.js - Gestor IndexedDB y Sincronización Automática Offline/Online

const DB_NAME = 'germania_offline_db';
const DB_VERSION = 1;
const STORE_NAME = 'asistencias_pendientes';

let dbInstance = null;

// Abrir base de datos IndexedDB
function abrirDB() {
  return new Promise((resolve, reject) => {
    if (dbInstance) return resolve(dbInstance);

    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
      }
    };
    request.onsuccess = (e) => {
      dbInstance = e.target.result;
      resolve(dbInstance);
    };
    request.onerror = (e) => reject(e.target.error);
  });
}

// Guardar registro de asistencia local en IndexedDB
async function guardarAsistenciaLocal(registro) {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.add(registro);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Obtener todos los registros pendientes
async function obtenerPendientes() {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Limpiar registros sincronizados
async function limpiarPendientes() {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.clear();
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// Sincronizar registros locales hacia el backend
async function sincronizarPendientesConBackend() {
  const pendientes = await obtenerPendientes();
  if (!pendientes || pendientes.length === 0) return;

  mostrarBannerSincronizacion(`Detectada conexión: Sincronizando ${pendientes.length} registros pendientes...`, 'info');

  const batchPayload = {
    sede_id: 1,
    docente_id: 4,
    timestamp_envio: new Date().toISOString(),
    registros_asistencia: pendientes.map(p => ({
      tipo_documento: p.tipo_documento,
      numero_documento: p.documento,
      fecha: p.fecha,
      id_horario: p.id_horario || 1,
      minutos_retardo: p.minutos_retraso,
      estado_calculado: p.estado,
      valor_inasistencia: p.valor_inasistencia
    }))
  };

  try {
    const response = await fetch('/api/v1/asistencia/sincronizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(batchPayload)
    });

    const data = await response.json();
    if (data.success) {
      await limpiarPendientes();
      mostrarBannerSincronizacion(`¡Sincronización completada! ${data.data.procesados_con_exito} registros guardados en servidor.`, 'success');
      actualizarContadorPendientes();
    } else {
      mostrarBannerSincronizacion(`Error al sincronizar: ${data.error}`, 'error');
    }
  } catch (err) {
    mostrarBannerSincronizacion(`Reintento de sincronización aplazado (sin red)`, 'warning');
  }
}

// Notificador visual en pantalla
function mostrarBannerSincronizacion(mensaje, tipo) {
  let banner = document.getElementById('pwa-sync-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'pwa-sync-banner';
    banner.className = 'fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl text-xs font-bold border transition duration-300';
    document.body.appendChild(banner);
  }

  if (tipo === 'success') {
    banner.className = 'fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl text-xs font-bold border bg-emerald-600 text-white border-emerald-700';
  } else if (tipo === 'info') {
    banner.className = 'fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl text-xs font-bold border bg-blue-600 text-white border-blue-700 animate-pulse';
  } else {
    banner.className = 'fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg shadow-xl text-xs font-bold border bg-amber-600 text-white border-amber-700';
  }

  banner.innerHTML = `<i class="fa-solid fa-arrows-rotate mr-2"></i> ${mensaje}`;
  banner.style.display = 'block';

  if (tipo === 'success') {
    setTimeout(() => { banner.style.display = 'none'; }, 4000);
  }
}

async function actualizarContadorPendientes() {
  const pendientes = await obtenerPendientes();
  const badge = document.getElementById('offline-count-badge');
  if (badge) {
    if (pendientes.length > 0) {
      badge.innerText = `${pendientes.length} guardados offline`;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }
}

// Escuchadores de conectividad
window.addEventListener('online', () => {
  sincronizarPendientesConBackend();
});

window.addEventListener('offline', () => {
  mostrarBannerSincronizacion('Modo sin conexión activado. La asistencia se guardará en IndexedDB local.', 'warning');
});

// Registrar Service Worker si el navegador lo soporta
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .then(reg => console.log('[PWA] Service Worker registrado exitosamente:', reg.scope))
      .catch(err => console.log('[PWA] Error al registrar Service Worker:', err));
  });
}

// Inicializar al cargar
document.addEventListener('DOMContentLoaded', () => {
  actualizarContadorPendientes();
  if (navigator.onLine) {
    sincronizarPendientesConBackend();
  }
});

