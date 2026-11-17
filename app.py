"""Aplicacion web del proyecto final: deteccion de posible deficiencia de testosterona.

Integra los tres modelos con mejor desempeno en validacion cruzada (ROC AUC), entrenados en
entrenamiento-modelos.ipynb, y muestra la probabilidad de cada uno para los datos capturados.
Se ejecuta con:  streamlit run app.py
"""
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import streamlit as st

CARPETA = Path(__file__).parent / "modelos"

# Cuantos modelos se integran: los de mayor ROC AUC en validacion cruzada (metrica principal del problema).
# La seleccion no usa el conjunto de prueba.
N_MODELOS = 3

# Datos del proyecto que se muestran en la seccion de informacion general
ALUMNO = "Jesús Pascual Garay Ordaz"
MATRICULA = "306025"
PROGRAMA = "MIC"
MATERIA = "Machine Learning"
ASESOR = "Dra. Olanda Prieto Ordaz"
INSTITUCION = "UACH"  # nombre de la institucion; si se deja vacio no se muestra

# Nombre con acentos para mostrar; los archivos y los metadatos usan los nombres del entrenamiento
MOSTRAR = {"Regresion Logistica": "Regresión Logística"}

# Principio de funcionamiento de cada modelo, para la seccion de informacion general
DESCRIPCION_MODELOS = {
    "XGBoost": "Ensamble secuencial de árboles pequeños (boosting): cada árbol nuevo corrige los errores de "
               "los anteriores, con una tasa de aprendizaje baja para no sobreajustar.",
    "Random Forest": "Ensamble de 300 árboles de decisión entrenados con muestras y subconjuntos de variables "
                     "al azar, cuyas probabilidades se promedian, lo que reduce la varianza de un árbol solo.",
    "SVM": "Máquina de vectores de soporte con kernel RBF, que separa las clases con una frontera no lineal "
           "buscando el mayor margen. Sus probabilidades se calibran con una sigmoide.",
}


def bonito(nombre):
    return MOSTRAR.get(nombre, nombre)


# Texto que ve el usuario para cada variable numerica: (etiqueta, ayuda, decimales)
NUMERICAS = {
    "edad": ("Edad (años)", "Hombres adultos, de 20 años en adelante.", 0),
    "imc": ("IMC (kg/m²)", "Índice de masa corporal.", 1),
    "cintura": ("Cintura (cm)", "Circunferencia de la cintura.", 1),
    "shbg": ("SHBG (nmol/L)", "Globulina fijadora de hormonas sexuales.", 2),
    "estradiol": ("Estradiol (pg/mL)", "Estradiol en sangre.", 1),
    "lh": ("LH (mIU/mL)", "Hormona luteinizante.", 2),
    "fsh": ("FSH (mIU/mL)", "Hormona folículo estimulante.", 2),
    "tragos_por_dia": ("Tragos por día", "Promedio de tragos de alcohol por día en los últimos 12 meses.", 1),
}
# Variables que en los datos de entrenamiento tienen valores faltantes: se permite dejarlas vacias
OPCIONALES = ["imc", "cintura", "estradiol", "tragos_por_dia"]

# Etiquetas de las categoricas: valor con el que se entreno el modelo -> texto para el usuario
CATEGORICAS = {
    "diabetes": ("¿Le han dicho que tiene diabetes?",
                 {"Si": "Sí", "No": "No", "Prediabetes": "Prediabetes"}),
    "hipertension": ("¿Le han dicho que tiene hipertensión?", {"Si": "Sí", "No": "No"}),
    "fumador": ("¿Ha fumado al menos 100 cigarrillos en su vida?", {"Si": "Sí", "No": "No"}),
    "raza_etnia": ("Raza y origen étnico", {
        "Mexico americano": "México-americano", "Otro hispano": "Otro hispano",
        "Blanco no hispano": "Blanco no hispano", "Negro no hispano": "Negro no hispano",
        "Asiatico no hispano": "Asiático no hispano", "Otra o multirracial": "Otra o multirracial"}),
    "escolaridad": ("Escolaridad", {
        "Menos de 9 grado": "Menos de 9.º grado", "9 a 11 grado": "9.º a 11.º grado",
        "Preparatoria completa": "Preparatoria completa", "Universidad incompleta": "Universidad incompleta",
        "Universidad completa o mas": "Universidad completa o más"}),
}


@st.cache_resource
def cargar():
    """Carga los metadatos y los N_MODELOS mejores modelos (por ROC AUC en validacion cruzada) una sola vez."""
    with open(CARPETA / "metadatos.json", encoding="utf-8") as f:
        meta = json.load(f)
    ranking = sorted(meta["modelos"], key=lambda n: meta["modelos"][n]["roc_auc_cv"], reverse=True)
    elegidos = ranking[:N_MODELOS]
    modelos = {nombre: joblib.load(CARPETA / meta["modelos"][nombre]["archivo"]) for nombre in elegidos}
    return meta, modelos, ranking


def campo_numerico(col, meta):
    """Dibuja el campo de una variable numerica y devuelve su valor (o NaN si se deja vacia)."""
    etiqueta, ayuda, decimales = NUMERICAS[col]
    info = meta["variables_numericas"][col]
    vacio = False
    if col in OPCIONALES:
        nombre_var = etiqueta.split(" (")[0]
        nombre_var = nombre_var if nombre_var.isupper() else nombre_var.lower()  # IMC se queda en mayusculas
        vacio = st.checkbox(f"No cuento con {nombre_var}", key=f"vacio_{col}")
    if decimales == 0:
        valor = st.number_input(etiqueta, min_value=int(info["minimo"]), max_value=int(info["maximo"]),
                                value=int(info["mediana"]), step=1, help=ayuda, disabled=vacio, key=col)
    else:
        valor = st.number_input(etiqueta, min_value=float(info["minimo"]), max_value=float(info["maximo"]),
                                value=float(round(info["mediana"], decimales)), step=10.0 ** -decimales,
                                format=f"%.{decimales}f", help=ayuda, disabled=vacio, key=col)
    return np.nan if vacio else float(valor)


def campo_categorico(col, meta):
    """Dibuja el campo de una variable categorica y devuelve el valor con el que se entreno el modelo."""
    etiqueta, textos = CATEGORICAS[col]
    opciones = list(textos)
    moda = meta["variables_categoricas"][col]["moda"]
    return st.selectbox(etiqueta, opciones, index=opciones.index(moda),
                        format_func=lambda v: textos[v], key=col)


def validar(valores, meta):
    """Revisa los datos antes de enviarlos a los modelos y regresa la lista de problemas encontrados."""
    errores = []
    for col, (etiqueta, _, _) in NUMERICAS.items():
        v = valores[col]
        if np.isnan(v):
            if col not in OPCIONALES:
                errores.append(f"{etiqueta} es obligatorio.")
            continue
        info = meta["variables_numericas"][col]
        if not info["minimo"] <= v <= info["maximo"]:
            errores.append(f"{etiqueta} debe estar entre {info['minimo']:g} y {info['maximo']:g} "
                           f"(el rango de los datos de entrenamiento).")
    for col, (etiqueta, _) in CATEGORICAS.items():
        if valores[col] not in meta["variables_categoricas"][col]["opciones"]:
            errores.append(f"El valor de «{etiqueta}» no es una opción válida.")
    return errores


def grafica(resultados):
    """Barras horizontales con la probabilidad de cada modelo y su umbral de decision."""
    fig, ax = plt.subplots(figsize=(7, 0.9 + 0.7 * len(resultados)))
    nombres = list(resultados)
    probs = [100 * resultados[n]["probabilidad"] for n in nombres]
    umbrales = [100 * resultados[n]["umbral"] for n in nombres]
    colores = ["#C44E52" if resultados[n]["alerta"] else "#4C72B0" for n in nombres]
    y = np.arange(len(nombres))
    ax.barh(y, probs, color=colores, height=0.55)
    ax.scatter(umbrales, y, marker="|", s=900, color="black", zorder=3)
    for yi, p in zip(y, probs):
        ax.text(min(p + 1.5, 97), yi, f"{p:.0f}%", va="center", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels([bonito(n) for n in nombres])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Probabilidad de deficiencia (%)")
    # La leyenda va debajo del eje para que no se encime con las barras
    ax.legend([Line2D([0], [0], color="black", lw=2)], ["Umbral de decisión de cada modelo"],
              loc="upper center", bbox_to_anchor=(0.5, -0.28), fontsize=8, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


METRICAS_GRAFICA = ["ROC AUC", "Recall", "Precision", "F1", "Accuracy"]


def grafica_metricas(meta, nombres):
    """Barras agrupadas con las metricas de cada modelo en el conjunto de prueba (valores del experimento)."""
    fig, ax = plt.subplots(figsize=(9, 4))
    ancho = 0.8 / len(nombres)
    x = np.arange(len(METRICAS_GRAFICA))
    colores = ["#4C72B0", "#55A868", "#C44E52", "#8172B3"]
    for i, nombre in enumerate(nombres):
        valores = [meta["modelos"][nombre]["metricas_test"][m] for m in METRICAS_GRAFICA]
        barras = ax.bar(x + (i - (len(nombres) - 1) / 2) * ancho, valores, ancho, label=bonito(nombre),
                        color=colores[i % len(colores)])
        for b, v in zip(barras, valores):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(METRICAS_GRAFICA)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Valor de la métrica")
    ax.set_title("Desempeño en el conjunto de prueba")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=len(nombres), frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


st.set_page_config(page_title="Deficiencia de testosterona", page_icon="🩺", layout="wide")
meta, modelos, ranking = cargar()

st.title("Detección de posible deficiencia de testosterona")
st.caption(f"Proyecto final de {MATERIA} ({PROGRAMA}). Modelos entrenados con NHANES 2021 a 2023, "
           "hombres adultos, con deficiencia definida como testosterona total menor a 300 ng/dL.")

tab_info, tab_pred, tab_desempeno = st.tabs(["Información del proyecto", "Predicción", "Desempeño de los modelos"])

# ---------------------------------------------------------------------------------------------
with tab_info:
    st.subheader("Datos del proyecto")
    filas_info = [("Proyecto", "Detección de posible deficiencia de testosterona en hombres adultos"),
                  ("Alumno", f"{ALUMNO}, matrícula {MATRICULA}")]
    if INSTITUCION:
        filas_info.append(("Institución", INSTITUCION))
    filas_info += [("Programa", PROGRAMA), ("Materia", MATERIA), ("Asesora", ASESOR)]
    for etiqueta, texto in filas_info:
        st.markdown(f"**{etiqueta}:** {texto}")

    st.subheader("Problema y objetivo de la aplicación")
    st.markdown(
        "La deficiencia de testosterona normalmente solo se detecta con un análisis de sangre y muchas veces "
        "pasa desapercibida. El problema es de **clasificación binaria**: dadas 13 variables clínicas, hormonales "
        "y de estilo de vida, decidir si un hombre adulto tiene posible deficiencia.\n\n"
        "El objetivo de la aplicación es que el usuario capture los datos de una persona y compare las "
        "predicciones de los tres mejores modelos del proyecto, como apoyo para decidir a quién conviene "
        "pedirle un análisis de sangre.")

    st.subheader("Base de datos")
    st.markdown(
        "- **Fuente:** encuesta NHANES 2021 a 2023 del CDC (archivos de demografía, hormonas sexuales, medidas "
        "corporales, diabetes, presión arterial, alcohol y tabaco).\n"
        "- **Población:** 2514 hombres de 20 años o más con la testosterona medida.\n"
        "- **Variable objetivo:** `deficiencia_testosterona`, que vale 1 cuando la testosterona total es menor a "
        f"300 ng/dL (criterio de la AUA). El {100 * meta['prevalencia_train']:.1f}% de los hombres la tiene.\n"
        f"- **Partición:** {meta['filas_train']} hombres para entrenar y {meta['filas_test']} para la prueba final, "
        "que se usó una sola vez.")

    st.subheader("Modelos implementados")
    st.markdown(
        "Se integraron los tres modelos con mayor **ROC AUC en validación cruzada** (5 folds sobre los datos de "
        "entrenamiento), que es la métrica principal del problema por ser un problema desbalanceado. El conjunto "
        "de prueba no se usó para elegirlos.")
    tabla_modelos = []
    for nombre in modelos:
        info = meta["modelos"][nombre]
        tabla_modelos.append({
            "Modelo": bonito(nombre),
            "ROC AUC en validación": round(info["roc_auc_cv"], 3),
            "Umbral de decisión": info["umbral"],
            "Hiperparámetros seleccionados": ", ".join(f"{k}={v}" for k, v in info["hiperparametros"].items()),
        })
    st.dataframe(pd.DataFrame(tabla_modelos).set_index("Modelo"), width="stretch")
    for nombre in modelos:
        st.markdown(f"- **{bonito(nombre)}.** {DESCRIPCION_MODELOS.get(nombre, '')}")
    excluidos = [bonito(n) for n in ranking if n not in modelos]
    if excluidos:
        mejor_excluido = ranking[N_MODELOS]
        st.caption(f"{', '.join(excluidos)} quedó fuera por tener el menor ROC AUC en validación "
                   f"({meta['modelos'][mejor_excluido]['roc_auc_cv']:.3f}).")

# ---------------------------------------------------------------------------------------------
with tab_pred:
    st.markdown("**Aviso.** Es un proyecto académico, no un dispositivo médico. "
                "Un resultado positivo solo sugiere confirmar con un análisis de sangre, "
                "y uno negativo no descarta la deficiencia.")
    st.subheader("Datos del paciente")
    col_a, col_b = st.columns(2)
    valores = {}
    with col_a:
        st.markdown("**Medidas y hormonas**")
        for col in NUMERICAS:
            valores[col] = campo_numerico(col, meta)
    with col_b:
        st.markdown("**Antecedentes y datos generales**")
        for col in CATEGORICAS:
            valores[col] = campo_categorico(col, meta)

    if st.button("Predecir", type="primary"):
        errores = validar(valores, meta)
        if errores:
            for e in errores:
                st.error(e)
        else:
            datos = pd.DataFrame([valores])[meta["orden_columnas"]]
            resultados = {}
            for nombre, modelo in modelos.items():
                proba = float(modelo.predict_proba(datos)[0, 1])
                umbral = meta["modelos"][nombre]["umbral"]
                resultados[nombre] = {"probabilidad": proba, "umbral": umbral, "alerta": proba >= umbral}

            st.subheader("Resultado")
            alertas = sum(r["alerta"] for r in resultados.values())
            if alertas == 0:
                st.success(f"Ningún modelo marca posible deficiencia (0 de {len(resultados)}).")
            elif alertas == len(resultados):
                st.error(f"Todos los modelos marcan posible deficiencia ({alertas} de {len(resultados)}). "
                         "Se recomienda confirmar con un análisis de testosterona en sangre.")
            else:
                st.warning(f"{alertas} de {len(resultados)} modelos marcan posible deficiencia. "
                           "Los modelos no coinciden, por lo que conviene confirmar con un análisis de sangre.")

            columnas = st.columns(len(resultados))
            for caja, (nombre, r) in zip(columnas, resultados.items()):
                caja.metric(bonito(nombre), f"{100 * r['probabilidad']:.0f}%")
                caja.markdown(("🔴 **Posible deficiencia**" if r["alerta"] else "🟢 **Sin alerta**")
                              + f"  \nUmbral: {100 * r['umbral']:.0f}%")

            st.markdown("**Detalle por modelo**")
            st.dataframe(pd.DataFrame([{
                "Modelo": bonito(n),
                "Predicción": "Posible deficiencia (clase 1)" if r["alerta"] else "Sin alerta (clase 0)",
                "Probabilidad de deficiencia (%)": round(100 * r["probabilidad"], 2),
                "Umbral (%)": round(100 * r["umbral"], 2),
            } for n, r in resultados.items()]).set_index("Modelo"), width="stretch")

            probs = {n: r["probabilidad"] for n, r in resultados.items()}
            dif = 100 * (max(probs.values()) - min(probs.values()))
            if 0 < alertas < len(resultados):
                a_favor = [bonito(n) for n, r in resultados.items() if r["alerta"]]
                en_contra = [bonito(n) for n, r in resultados.items() if not r["alerta"]]
                st.markdown(f"**Diferencias entre modelos.** Marcan alerta: {', '.join(a_favor)}. "
                            f"No la marcan: {', '.join(en_contra)}. La mayor diferencia entre probabilidades "
                            f"es de {dif:.0f} puntos porcentuales.")
            else:
                st.markdown(f"**Diferencias entre modelos.** Los tres coinciden en la clase predicha. "
                            f"La mayor diferencia entre probabilidades es de {dif:.0f} puntos porcentuales.")

            st.pyplot(grafica(resultados))

            if any(np.isnan(v) for v in valores.values() if isinstance(v, float)):
                st.info("Algún dato quedó vacío: el modelo lo reemplazó por la mediana de los datos de entrenamiento.")

    with st.expander("¿Cómo leer el resultado?"):
        st.markdown(
            "- La **clase predicha** es 1 («posible deficiencia») cuando la probabilidad del modelo supera su "
            "**umbral** de decisión, y 0 («sin alerta») en caso contrario.\n"
            "- Cada modelo entrega la **probabilidad** de deficiencia. Los umbrales son menores a 50% a propósito: "
            "se eligieron para detectar a la mayoría de los hombres con deficiencia (recall cercano a 88% en "
            "Test), porque dejar escapar un caso cuesta más que pedir un análisis de más.\n"
            "- A cambio hay falsas alarmas: en Test, alrededor de la mitad de las alertas fueron correctas "
            "(precisión de 50% a 55%, según el modelo).\n"
            "- La probabilidad no es un riesgo clínico exacto, solo sirve para ordenar y comparar casos.\n"
            "- **Limitaciones:** los modelos se entrenaron solo con hombres de 20 años o más de una encuesta de "
            "Estados Unidos, la deficiencia se definió con una sola medición de testosterona total, y no "
            "sustituyen el criterio médico ni un análisis de sangre.")

# ---------------------------------------------------------------------------------------------
with tab_desempeno:
    st.subheader("Resultados en el conjunto de prueba")
    st.markdown(f"Los tres modelos se evaluaron una sola vez en {meta['filas_test']} hombres que no se usaron para "
                "entrenar ni para elegir hiperparámetros. Las cifras son las del experimento (guardadas en "
                "`modelos/metadatos.json`), no se recalculan en la aplicación.")
    filas = {n: {"Umbral": meta["modelos"][n]["umbral"],
                 "ROC AUC (validación)": meta["modelos"][n]["roc_auc_cv"],
                 **{k: meta["modelos"][n]["metricas_test"][k]
                    for k in ["ROC AUC", "Recall", "Precision", "F1", "Accuracy"]}}
             for n in modelos}
    tabla = pd.DataFrame(filas).T.rename(index=MOSTRAR).rename(columns={"ROC AUC": "ROC AUC (prueba)"})
    st.dataframe(tabla.round(3), width="stretch")

    st.pyplot(grafica_metricas(meta, list(modelos)))

    st.markdown("**Matriz de confusión en prueba** (casos)")
    st.dataframe(pd.DataFrame({
        bonito(n): {k: int(meta["modelos"][n]["metricas_test"][k]) for k in ["TN", "FP", "FN", "TP"]}
        for n in modelos}).rename(index={"TN": "Verdaderos negativos", "FP": "Falsos positivos",
                                         "FN": "Falsos negativos", "TP": "Verdaderos positivos"}),
        width="stretch")
    st.caption("Los tres modelos quedan prácticamente empatados: la diferencia de ROC AUC entre ellos es menor "
               "que la variación entre folds de la validación cruzada, así que no hay un ganador concluyente.")
