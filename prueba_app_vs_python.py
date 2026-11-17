"""Prueba: las predicciones de la aplicacion coinciden con las de Python directo.

Para cada perfil de entrada se corre la aplicacion con streamlit.testing (sin abrir el navegador), se lee
la tabla de resultados que muestra, y se compara contra cargar los modelos .joblib en Python y llamar
predict_proba con exactamente los mismos datos.

Uso (desde esta carpeta):  python prueba_app_vs_python.py
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

CARPETA = Path(__file__).parent
meta = json.load(open(CARPETA / "modelos" / "metadatos.json", encoding="utf-8"))
N_MODELOS = 3
ranking = sorted(meta["modelos"], key=lambda n: meta["modelos"][n]["roc_auc_cv"], reverse=True)[:N_MODELOS]
modelos = {n: joblib.load(CARPETA / "modelos" / meta["modelos"][n]["archivo"]) for n in ranking}

MEDIANAS = {c: v["mediana"] for c, v in meta["variables_numericas"].items()}
MODAS = {c: v["moda"] for c, v in meta["variables_categoricas"].items()}

PERFILES = {
    "valores por defecto (medianas y modas de Train)": {},
    "perfil de riesgo alto": {
        "edad": 66, "imc": 36.5, "cintura": 121.0, "shbg": 18.0, "estradiol": 11.0, "lh": 3.5, "fsh": 5.0,
        "tragos_por_dia": 3.0, "diabetes": "Si", "hipertension": "Si", "fumador": "Si"},
    "perfil de riesgo bajo": {
        "edad": 27, "imc": 22.0, "cintura": 80.0, "shbg": 60.0, "estradiol": 25.0, "lh": 5.0, "fsh": 4.0,
        "tragos_por_dia": 1.0, "diabetes": "No", "hipertension": "No", "fumador": "No"},
    "perfil con IMC y cintura vacios": {
        "edad": 52, "shbg": 30.0, "lh": 4.0, "fsh": 7.0, "vacios": ["imc", "cintura"]},
}


def correr_app(perfil):
    """Corre la aplicacion con el perfil dado y regresa la tabla de resultados que muestra."""
    at = AppTest.from_file(str(CARPETA / "app.py"), default_timeout=60).run()
    for col, valor in perfil.items():
        if col == "vacios":
            for v in valor:
                at.checkbox(key=f"vacio_{v}").set_value(True)
        elif col in MODAS:
            at.selectbox(key=col).set_value(valor)
        else:
            at.number_input(key=col).set_value(valor)
    at.button[0].click().run()
    assert not at.exception, f"La aplicacion lanzo una excepcion: {at.exception}"
    # st.error tambien se usa cuando los tres modelos marcan alerta; aqui solo importan los errores de validacion
    invalidos = [e.value for e in at.error if "obligatorio" in e.value or "debe estar entre" in e.value
                 or "no es una opción" in e.value]
    assert not invalidos, f"Errores de validacion inesperados: {invalidos}"
    tabla = next(df.value for df in at.dataframe if "Probabilidad de deficiencia (%)" in df.value.columns)
    return tabla


def correr_python(perfil):
    """Mismos datos, modelos cargados directamente en Python."""
    fila = {}
    for col in meta["orden_columnas"]:
        if col in MODAS:
            fila[col] = perfil.get(col, MODAS[col])
        elif col in perfil.get("vacios", []):
            fila[col] = np.nan
        else:
            fila[col] = float(perfil.get(col, round(MEDIANAS[col], 2)))
    datos = pd.DataFrame([fila])[meta["orden_columnas"]]
    return {n: 100 * float(m.predict_proba(datos)[0, 1]) for n, m in modelos.items()}


MOSTRAR = {"Regresion Logistica": "Regresión Logística"}
todo_bien = True
filas = []
for nombre_perfil, perfil in PERFILES.items():
    tabla_app = correr_app(perfil)
    directo = correr_python(perfil)
    for nombre, p_directo in directo.items():
        p_app = float(tabla_app.loc[MOSTRAR.get(nombre, nombre), "Probabilidad de deficiencia (%)"])
        alerta_app = tabla_app.loc[MOSTRAR.get(nombre, nombre), "Predicción"].startswith("Posible")
        alerta_directo = p_directo / 100 >= meta["modelos"][nombre]["umbral"]
        # La aplicacion redondea a 2 decimales, por eso la tolerancia es de 0.01 puntos porcentuales
        coincide = abs(p_app - p_directo) <= 0.01 and alerta_app == alerta_directo
        todo_bien &= coincide
        filas.append({"Perfil": nombre_perfil, "Modelo": nombre, "App (%)": p_app,
                      "Python (%)": round(p_directo, 2), "Clase app": int(alerta_app),
                      "Clase Python": int(alerta_directo), "Coincide": "sí" if coincide else "NO"})

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
print(pd.DataFrame(filas).to_string(index=False))
print("\nRESULTADO:", "las predicciones de la aplicacion coinciden con las de Python en todos los casos"
      if todo_bien else "HAY DIFERENCIAS entre la aplicacion y Python")
sys.exit(0 if todo_bien else 1)
