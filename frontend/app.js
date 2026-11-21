"use strict";

/* Interfaz minima del corte vertical (semana 15).
 * No guarda estado en el navegador: cada resultado se obtiene de la API real.
 * El backend decide reglas, estados, identificadores y codigos de error.
 */

const BASE = "/api/v1";

function porId(id) {
  return document.getElementById(id);
}

function valor(id) {
  return porId(id).value.trim();
}

function entero(id) {
  if (valor(id) === "") return NaN;
  const numero = Number(valor(id));
  return Number.isInteger(numero) ? numero : NaN;
}

function mensaje(destino, texto, tipo) {
  const elemento = porId(destino);
  elemento.textContent = texto;
  elemento.className = texto ? "mensaje " + tipo : "mensaje";
}

function estado(destino, texto) {
  porId(destino).textContent = texto;
}

async function pedir(url, opciones) {
  try {
    const respuesta = await fetch(url, opciones);
    let datos = null;
    const cuerpo = await respuesta.text();
    if (cuerpo) {
      try {
        datos = JSON.parse(cuerpo);
      } catch (error) {
        datos = null;
      }
    }
    return {
      comunicacion: false,
      ok: respuesta.ok,
      status: respuesta.status,
      datos: datos,
    };
  } catch (error) {
    return {
      comunicacion: true,
      ok: false,
      status: 0,
      datos: null,
      detalle: error && error.message ? error.message : "sin detalle",
    };
  }
}

function explicarRechazo(resultado, accion) {
  const codigo = resultado.datos && resultado.datos.codigo
    ? resultado.datos.codigo
    : "sin codigo";
  const detalle = resultado.datos && resultado.datos.detail
    ? resultado.datos.detail
    : "El backend no devolvio detalle adicional.";
  return accion + ": rechazo HTTP " + resultado.status + " (" + codigo + "). "
    + detalle + " Corrija los datos y vuelva a enviar.";
}

function avisoComunicacion(accion, resultado) {
  return accion + ": no se pudo contactar la API (" + resultado.detalle + "). "
    + "El resultado no queda confirmado; no reintente automaticamente. "
    + "Puede consultar el catalogo para verificar lo que se registro.";
}

function avisoServidor(accion, resultado) {
  return accion + ": el servidor no esta disponible (HTTP " + resultado.status + "). "
    + "El resultado no queda confirmado; no reintente automaticamente.";
}

function faltanCampos(ids) {
  return ids.filter(function (id) { return valor(id) === ""; });
}

function jsonCuerpo(datos) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  };
}

async function crearFicha(evento) {
  evento.preventDefault();
  const boton = porId("btn-crear");
  if (boton.disabled) return;

  mensaje("resultado-crear", "", "");
  const obligatorios = [
    "refugio_id", "nombre", "especie", "edad_meses", "tamano",
    "nivel_energia", "experiencia_requerida", "fecha_publicacion",
  ];
  const ausentes = faltanCampos(obligatorios);
  if (ausentes.length) {
    mensaje("resultado-crear", "Faltan campos obligatorios: " + ausentes.join(", ") + ".", "rechazo");
    return;
  }

  const fotografias = valor("fotografias")
    .split(",")
    .map(function (texto) { return texto.trim(); })
    .filter(function (texto) { return texto.length > 0; });

  const cuerpo = {
    refugio_id: entero("refugio_id"),
    nombre: valor("nombre"),
    raza: valor("raza") || null,
    especie: valor("especie"),
    edad_meses: entero("edad_meses"),
    tamano: valor("tamano"),
    nivel_energia: valor("nivel_energia"),
    experiencia_requerida: valor("experiencia_requerida"),
    apta_con_menores: porId("apta_con_menores").checked,
    apta_con_mascotas: porId("apta_con_mascotas").checked,
    historial_salud: valor("historial_salud") || null,
    historial_comportamiento: valor("historial_comportamiento") || null,
    fecha_publicacion: valor("fecha_publicacion"),
    fotografias: fotografias,
  };

  boton.disabled = true;
  estado("estado-crear", "Enviando...");
  const resultado = await pedir(BASE + "/mascotas", jsonCuerpo(cuerpo));
  boton.disabled = false;
  estado("estado-crear", "");

  if (resultado.comunicacion) {
    mensaje("resultado-crear", avisoComunicacion("Crear ficha", resultado), "error");
    return;
  }
  if (resultado.ok && resultado.datos && resultado.datos.id) {
    const ficha = resultado.datos;
    porId("id-editar").value = String(ficha.id);
    porId("refugio-editar").value = String(ficha.refugio_id);
    porId("nombre-editar").value = ficha.nombre;
    mensaje(
      "resultado-crear",
      "Ficha creada por la API con id " + ficha.id + ", estado '" + ficha.estado
        + "' y " + (ficha.fotografias ? ficha.fotografias.length : 0)
        + " fotografias. El id ya esta listo para editar o dar de baja.",
      "exito"
    );
    return;
  }
  if ([400, 404, 409].indexOf(resultado.status) >= 0) {
    mensaje("resultado-crear", explicarRechazo(resultado, "Crear ficha"), "rechazo");
    return;
  }
  if (resultado.status >= 500) {
    mensaje("resultado-crear", avisoServidor("Crear ficha", resultado), "error");
    return;
  }
  mensaje(
    "resultado-crear",
    "Crear ficha: respuesta inesperada HTTP " + resultado.status + ". No se confirma la creacion.",
    "error"
  );
}

async function editarFicha() {
  const boton = porId("btn-editar");
  if (boton.disabled) return;
  mensaje("resultado-editar", "", "");

  const id = entero("id-editar");
  const refugio = entero("refugio-editar");
  if (!(id > 0) || !(refugio > 0) || valor("nombre-editar") === "") {
    mensaje("resultado-editar", "Indique un id positivo, un refugio y un nombre para actualizar.", "rechazo");
    return;
  }

  const cuerpo = { refugio_id: refugio, nombre: valor("nombre-editar") };
  boton.disabled = true;
  porId("btn-baja").disabled = true;
  estado("estado-editar", "Enviando...");
  const resultado = await pedir(
    BASE + "/mascotas/" + id,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) }
  );
  boton.disabled = false;
  porId("btn-baja").disabled = false;
  estado("estado-editar", "");

  if (resultado.comunicacion) {
    mensaje("resultado-editar", avisoComunicacion("Actualizar ficha", resultado), "error");
    return;
  }
  if (resultado.ok && resultado.datos && resultado.datos.id) {
    mensaje(
      "resultado-editar",
      "Ficha " + resultado.datos.id + " actualizada por la API. Nombre actual: '"
        + resultado.datos.nombre + "'; estado: '" + resultado.datos.estado + "'.",
      "exito"
    );
    return;
  }
  if ([400, 403, 404].indexOf(resultado.status) >= 0) {
    mensaje("resultado-editar", explicarRechazo(resultado, "Actualizar ficha"), "rechazo");
    return;
  }
  if (resultado.status >= 500) {
    mensaje("resultado-editar", avisoServidor("Actualizar ficha", resultado), "error");
    return;
  }
  mensaje("resultado-editar", "Actualizar ficha: respuesta inesperada HTTP " + resultado.status + ".", "error");
}

async function darDeBaja() {
  const boton = porId("btn-baja");
  if (boton.disabled) return;
  mensaje("resultado-editar", "", "");

  const id = entero("id-editar");
  const refugio = entero("refugio-editar");
  if (!(id > 0) || !(refugio > 0)) {
    mensaje("resultado-editar", "Indique un id positivo y un refugio para dar de baja.", "rechazo");
    return;
  }

  boton.disabled = true;
  porId("btn-editar").disabled = true;
  estado("estado-editar", "Enviando...");
  const resultado = await pedir(
    BASE + "/mascotas/" + id + "?refugio_id=" + refugio,
    { method: "DELETE" }
  );
  boton.disabled = false;
  porId("btn-editar").disabled = false;
  estado("estado-editar", "");

  if (resultado.comunicacion) {
    mensaje("resultado-editar", avisoComunicacion("Dar de baja", resultado), "error");
    return;
  }
  if (resultado.ok) {
    mensaje(
      "resultado-editar",
      "Baja confirmada por la API para la ficha " + id + " (HTTP "
        + resultado.status + "). Vuelva a consultar el catalogo para comprobar que ya no aparece.",
      "exito"
    );
    return;
  }
  if ([400, 403, 404].indexOf(resultado.status) >= 0) {
    mensaje("resultado-editar", explicarRechazo(resultado, "Dar de baja"), "rechazo");
    return;
  }
  if (resultado.status >= 500) {
    mensaje("resultado-editar", avisoServidor("Dar de baja", resultado), "error");
    return;
  }
  mensaje("resultado-editar", "Dar de baja: respuesta inesperada HTTP " + resultado.status + ".", "error");
}

function limpiarCatalogo() {
  porId("cuerpo-catalogo").replaceChildren();
}

function agregarFila(mascota) {
  const fila = document.createElement("tr");
  [
    mascota.id,
    mascota.nombre,
    mascota.especie,
    mascota.tamano,
    mascota.edad_meses,
    mascota.refugio_nombre,
  ].forEach(function (valorCelda) {
    const celda = document.createElement("td");
    celda.textContent = valorCelda === null || valorCelda === undefined ? "" : String(valorCelda);
    fila.appendChild(celda);
  });
  porId("cuerpo-catalogo").appendChild(fila);
}

async function consultarCatalogo(evento) {
  evento.preventDefault();
  const boton = porId("btn-consultar");
  if (boton.disabled) return;

  mensaje("resultado-catalogo", "", "");
  limpiarCatalogo();

  const pagina = entero("filtro-pagina");
  const porPagina = entero("filtro-por-pagina");
  if (!(pagina > 0) || !(porPagina > 0)) {
    mensaje("resultado-catalogo", "La pagina y el tamano de pagina deben ser enteros positivos.", "rechazo");
    return;
  }

  const parametros = new URLSearchParams();
  [
    ["especie", "filtro-especie"],
    ["tamano", "filtro-tamano"],
    ["edad_min", "filtro-edad-min"],
    ["edad_max", "filtro-edad-max"],
  ].forEach(function (par) {
    if (valor(par[1]) !== "") parametros.set(par[0], valor(par[1]));
  });
  parametros.set("pagina", String(pagina));
  parametros.set("por_pagina", String(porPagina));

  boton.disabled = true;
  estado("estado-catalogo", "Consultando...");
  const resultado = await pedir(BASE + "/mascotas?" + parametros.toString());
  boton.disabled = false;
  estado("estado-catalogo", "");

  if (resultado.comunicacion) {
    mensaje("resultado-catalogo", avisoComunicacion("Consultar catalogo", resultado), "error");
    return;
  }
  if (resultado.ok && resultado.datos) {
    const paginaDatos = resultado.datos;
    const lista = paginaDatos.mascotas || [];
    lista.forEach(agregarFila);
    if (paginaDatos.total === 0 || lista.length === 0) {
      mensaje(
        "resultado-catalogo",
        "La API devolvio total " + paginaDatos.total + ": no hay mascotas que coincidan con los filtros.",
        "vacio"
      );
    } else {
      mensaje(
        "resultado-catalogo",
        "API HTTP " + resultado.status + ": total " + paginaDatos.total
          + ", pagina " + paginaDatos.pagina + ", " + lista.length
          + " mascota(s) mostrada(s). Datos recuperados del servidor.",
        "exito"
      );
    }
    return;
  }
  if (resultado.status === 400) {
    mensaje("resultado-catalogo", explicarRechazo(resultado, "Consultar catalogo"), "rechazo");
    return;
  }
  if (resultado.status >= 500) {
    mensaje(
      "resultado-catalogo",
      avisoServidor("Consultar catalogo", resultado)
        + " La tabla se limpio para no mostrar datos anteriores como vigentes.",
      "error"
    );
    return;
  }
  mensaje(
    "resultado-catalogo",
    "Consultar catalogo: respuesta inesperada HTTP " + resultado.status + ".",
    "error"
  );
}

porId("form-crear").addEventListener("submit", crearFicha);
porId("form-editar").addEventListener("submit", function (evento) { evento.preventDefault(); });
porId("form-catalogo").addEventListener("submit", consultarCatalogo);
porId("btn-editar").addEventListener("click", editarFicha);
porId("btn-baja").addEventListener("click", darDeBaja);
