"""Genera las figuras de la presentacion a alta resolucion a partir de los modelos guardados.

Reproduce la particion, el preprocesamiento y las probabilidades de Test del notebook
entrenamiento-modelos.ipynb y comprueba que coinciden con modelos/metadatos.json antes de dibujar
(si algo no coincide, el script se detiene). Las cifras de validacion cruzada (modelos base y
optimizados) se copian de las salidas guardadas de ese notebook.

Uso (desde la raiz del repositorio):  python presentacion/generar_figuras.py
"""
import json
import sys
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from sklearn.metrics import confusion_matrix, recall_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = Path(__file__).resolve().parent / "figuras"
SALIDA.mkdir(exist_ok=True)
meta = json.load(open(RAIZ / "modelos" / "metadatos.json", encoding="utf-8"))

# ---------------------------------------------------------------------------------------------
# Estilo: texto en tinta (nunca del color de la serie), cuadricula y ejes discretos
# ---------------------------------------------------------------------------------------------
TINTA, TINTA_2, GRIS, CUADRICULA = "#1F2A37", "#5B6774", "#9AA5B1", "#E3E8EE"
# Un color por modelo, siempre el mismo en todas las figuras (primeras 4 posiciones de la paleta de referencia)
COLOR = {"Regresion Logistica": "#2a78d6", "SVM": "#eb6834", "Random Forest": "#1baf7a", "XGBoost": "#eda100"}
NOMBRE = {"Regresion Logistica": "Regresión Logística", "SVM": "SVM", "Random Forest": "Random Forest",
          "XGBoost": "XGBoost"}
ORDEN = ["Regresion Logistica", "SVM", "Random Forest", "XGBoost"]
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 14, "text.color": TINTA, "axes.labelcolor": TINTA,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.edgecolor": GRIS, "axes.linewidth": 1,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": CUADRICULA,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "savefig.dpi": 300, "figure.dpi": 100,
    "legend.frameon": False,
})


def guardar(fig, nombre):
    fig.savefig(SALIDA / nombre, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  listo:", nombre)


# ---------------------------------------------------------------------------------------------
# Datos y comprobacion de que se reproduce el experimento
# ---------------------------------------------------------------------------------------------
df = pd.read_csv(RAIZ / "nhanes_testosterona_2021_2023.csv").rename(columns={
    "SEQN": "id_participante", "RIDAGEYR": "edad", "BMXBMI": "imc", "BMXWAIST": "cintura", "LBXSHBG": "shbg",
    "LBXEST": "estradiol", "LBXLUH": "lh", "LBXFSH": "fsh", "DIQ010": "diabetes", "BPQ020": "hipertension",
    "SMQ020": "fumador", "ALQ130": "tragos_por_dia", "RIDRETH3": "raza_etnia", "DMDEDUC2": "escolaridad",
    "LBXTST": "testosterona_total"})
y = df["deficiencia_testosterona"].astype(int)
X = df.drop(columns=["id_participante", "testosterona_total", "deficiencia_testosterona"])
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)
especiales = {"hipertension": [7, 9], "fumador": [7, 9], "escolaridad": [7, 9], "tragos_por_dia": [777, 999]}
etiquetas = {
    "diabetes": {1: "Si", 2: "No", 3: "Prediabetes"}, "hipertension": {1: "Si", 2: "No"}, "fumador": {1: "Si", 2: "No"},
    "raza_etnia": {1: "Mexico americano", 2: "Otro hispano", 3: "Blanco no hispano", 4: "Negro no hispano",
                   6: "Asiatico no hispano", 7: "Otra o multirracial"},
    "escolaridad": {1: "Menos de 9 grado", 2: "9 a 11 grado", 3: "Preparatoria completa",
                    4: "Universidad incompleta", 5: "Universidad completa o mas"}}
for d in (X_train, X_test):
    for col, cods in especiales.items():
        d[col] = d[col].replace(cods, np.nan)
    for col, mapa in etiquetas.items():
        d[col] = d[col].map(mapa)
X_test = X_test[meta["orden_columnas"]]

modelos, proba, pred = {}, {}, {}
for n in ORDEN:
    info = meta["modelos"][n]
    modelos[n] = joblib.load(RAIZ / "modelos" / info["archivo"])
    proba[n] = modelos[n].predict_proba(X_test)[:, 1]
    pred[n] = (proba[n] >= info["umbral"]).astype(int)
    mt = info["metricas_test"]
    ok = (abs(roc_auc_score(y_test, proba[n]) - mt["ROC AUC"]) < 1e-9
          and confusion_matrix(y_test, pred[n]).ravel().tolist() == [mt["TN"], mt["FP"], mt["FN"], mt["TP"]])
    if not ok:
        sys.exit(f"STOP: {n} no reproduce las metricas de Test guardadas en metadatos.json")
print("Comprobacion: los 4 modelos reproducen exactamente las metricas de Test de metadatos.json")

# ---------------------------------------------------------------------------------------------
# 1. Curvas ROC en Test, con el punto de operacion (umbral elegido) de cada modelo
# ---------------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.2, 5.4))
ax.plot([0, 1], [0, 1], ls="--", color=GRIS, lw=1.5, label="Azar (AUC 0.500)")
for n in ORDEN:
    fpr, tpr, _ = roc_curve(y_test, proba[n])
    auc = meta["modelos"][n]["metricas_test"]["ROC AUC"]
    ax.plot(fpr, tpr, color=COLOR[n], lw=2.4, label=f"{NOMBRE[n]} (AUC {auc:.3f})")
    mt = meta["modelos"][n]["metricas_test"]
    ax.scatter([mt["FP"] / (mt["FP"] + mt["TN"])], [mt["TP"] / (mt["TP"] + mt["FN"])], s=90, color=COLOR[n],
               edgecolor="white", linewidth=2, zorder=5)
ax.set_xlabel("Tasa de falsos positivos")
ax.set_ylabel("Tasa de verdaderos positivos (recall)")
ax.set_xlim(-0.01, 1.0)
ax.set_ylim(0, 1.02)
ax.set_aspect("equal")
handles, labels = ax.get_legend_handles_labels()
handles.append(Line2D([0], [0], marker="o", ls="", color=TINTA_2, markersize=9, markeredgecolor="white"))
labels.append("Umbral elegido")
ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=11.5,
          columnspacing=1.2, handlelength=1.6)
guardar(fig, "roc_test.png")

# ---------------------------------------------------------------------------------------------
# 2. Matrices de confusion en Test (2 x 2), un solo tono de azul verdoso: la intensidad es el conteo
# ---------------------------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(5.0, 4.6))
for ax, n in zip(axes.ravel(), ORDEN):
    cm = confusion_matrix(y_test, pred[n])
    ax.imshow(cm, cmap="Blues", vmin=0, vmax=cm.max() * 1.15)
    ax.grid(False)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=17, fontweight="bold",
                    color="white" if cm[i, j] > cm.max() * 0.55 else TINTA)
    ax.set_xticks([0, 1], ["Sin def.", "Con def."], fontsize=11)
    ax.set_yticks([0, 1], ["Sin def.", "Con def."], fontsize=11)
    ax.set_title(NOMBRE[n], fontsize=12.5, color=TINTA, pad=6)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
fig.supxlabel("Predicción", fontsize=12.5, y=0.0)
fig.supylabel("Real", fontsize=12.5, x=0.0)
fig.tight_layout()
guardar(fig, "matrices_test.png")

# ---------------------------------------------------------------------------------------------
# 3. ROC AUC en validacion cruzada: modelo base contra optimizado (grafica de puntos: la escala no
#    empieza en cero a proposito, por eso no se usan barras)
# ---------------------------------------------------------------------------------------------
# Valores copiados de las salidas guardadas del notebook (Fase 3 por defecto y Fase 4 optimizado, 5 folds sobre Train)
AUC_BASE = {"Regresion Logistica": 0.8657, "SVM": 0.8774, "Random Forest": 0.8903, "XGBoost": 0.8644}
AUC_OPT = {"Regresion Logistica": 0.8684, "SVM": 0.8842, "Random Forest": 0.8938, "XGBoost": 0.8957}
for n in ORDEN:  # el valor optimizado tambien esta en los metadatos
    assert abs(meta["modelos"][n]["roc_auc_cv"] - AUC_OPT[n]) < 5e-5, n
fig, ax = plt.subplots(figsize=(9.2, 3.2))
filas = list(reversed(ORDEN))
for k, n in enumerate(filas):
    ax.plot([AUC_BASE[n], AUC_OPT[n]], [k, k], color=GRIS, lw=3, zorder=1, solid_capstyle="round")
    ax.scatter([AUC_BASE[n]], [k], s=170, facecolor="white", edgecolor=COLOR[n], linewidth=2.6, zorder=3)
    ax.scatter([AUC_OPT[n]], [k], s=170, color=COLOR[n], edgecolor="white", linewidth=1.5, zorder=4)
    d = AUC_OPT[n] - AUC_BASE[n]
    ax.text(max(AUC_BASE[n], AUC_OPT[n]) + 0.0016, k, f"{AUC_OPT[n]:.3f}  ({d:+.3f})", va="center", fontsize=12.5,
            color=TINTA)
ax.set_yticks(range(len(filas)), [NOMBRE[n] for n in filas], fontsize=13.5)
ax.set_xlim(0.855, 0.918)
ax.set_xlabel("ROC AUC en validación cruzada (5 folds, Train)")
ax.grid(axis="y", visible=False)
ax.legend([Line2D([0], [0], marker="o", ls="", markerfacecolor="white", markeredgecolor=TINTA_2, markeredgewidth=2.4,
                  markersize=11),
           Line2D([0], [0], marker="o", ls="", color=TINTA_2, markersize=11)],
          ["Parámetros por defecto", "Optimizado"], loc="upper right", fontsize=11.5)
guardar(fig, "auc_base_vs_optimizado.png")

# ---------------------------------------------------------------------------------------------
# 4. Efecto del umbral en Test: umbral estandar 0.5 contra el umbral elegido de cada modelo
# ---------------------------------------------------------------------------------------------
rec05, fp05, rec_e, fp_e = {}, {}, {}, {}
for n in ORDEN:
    p05 = (proba[n] >= 0.5).astype(int)
    rec05[n], fp05[n] = recall_score(y_test, p05), int(((p05 == 1) & (y_test == 0)).sum())
    mt = meta["modelos"][n]["metricas_test"]
    rec_e[n], fp_e[n] = mt["Recall"], int(mt["FP"])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.4))
x = np.arange(len(ORDEN))
w = 0.38
for ax, v05, ve, tit, fmt, tope in ((a1, rec05, rec_e, "Recall (casos detectados)", "{:.2f}", 1.12),
                                    (a2, fp05, fp_e, "Falsas alarmas (de 391 sin deficiencia)", "{:.0f}", 140)):
    for k, n in enumerate(ORDEN):
        ax.bar(k - w / 2 - 0.01, v05[n], w, facecolor="white", edgecolor=COLOR[n], linewidth=2, hatch="///")
        ax.bar(k + w / 2 + 0.01, ve[n], w, color=COLOR[n])
        ax.text(k - w / 2 - 0.01, v05[n] + tope * 0.015, fmt.format(v05[n]), ha="center", fontsize=11.5)
        ax.text(k + w / 2 + 0.01, ve[n] + tope * 0.015, fmt.format(ve[n]), ha="center", fontsize=11.5)
    ax.set_xticks(x, [NOMBRE[n].replace("Regresión ", "Regresión\n").replace("Regresion ", "Regresión\n") for n in ORDEN],
                  fontsize=11.5)
    ax.set_ylim(0, tope)
    ax.set_title(tit, fontsize=14, pad=10)
    ax.grid(axis="x", visible=False)
fig.legend([Patch(facecolor="white", edgecolor=TINTA_2, hatch="///", linewidth=2), Patch(color=TINTA_2)],
           ["Umbral estándar (0.5)", "Umbral elegido (maximiza F2)"], loc="lower center", ncol=2, fontsize=12,
           bbox_to_anchor=(0.5, -0.06))
fig.tight_layout()
guardar(fig, "efecto_umbral.png")

# ---------------------------------------------------------------------------------------------
# 5. Importancia de variables: coeficientes de la regresion logistica e importancia en los arboles
# ---------------------------------------------------------------------------------------------
LEGIBLE = {"shbg": "SHBG", "estradiol": "Estradiol", "imc": "IMC", "cintura": "Cintura", "edad": "Edad", "lh": "LH",
           "fsh": "FSH", "tragos_por_dia": "Tragos por día", "diabetes_Si": "Diabetes (sí)", "diabetes_No": "Diabetes (no)",
           "diabetes_Prediabetes": "Prediabetes", "hipertension_Si": "Hipertensión (sí)",
           "hipertension_No": "Hipertensión (no)", "fumador_Si": "Fumador (sí)", "fumador_No": "Fumador (no)"}


def legible(nombre):
    nombre = nombre.split("__", 1)[-1]
    if nombre in LEGIBLE:
        return LEGIBLE[nombre]
    for pref, txt in (("raza_etnia_", "Raza: "), ("escolaridad_", "Escolaridad: ")):
        if nombre.startswith(pref):
            return txt + nombre[len(pref):]
    return nombre


def valores(n):
    m = modelos[n]
    nombres = [legible(c) for c in m.named_steps["prep"].get_feature_names_out()]
    est = m.named_steps["modelo"]
    v = est.coef_[0] if n == "Regresion Logistica" else est.feature_importances_
    return pd.Series(v, index=nombres)


fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.6))
titulos = {"Regresion Logistica": "Regresión Logística\n(coeficientes)", "Random Forest": "Random Forest\n(importancia)",
           "XGBoost": "XGBoost\n(importancia)"}
for ax, n in zip(axes, ["Regresion Logistica", "Random Forest", "XGBoost"]):
    s = valores(n)
    s = s.reindex(s.abs().sort_values(ascending=False).index)[:8][::-1]
    ax.barh(range(len(s)), s.values, color=COLOR[n], height=0.62)
    ax.set_yticks(range(len(s)), s.index, fontsize=12.5)
    ax.set_title(titulos[n], fontsize=14, pad=8)
    ax.grid(axis="y", visible=False)
    if n == "Regresion Logistica":
        ax.axvline(0, color=TINTA_2, lw=1)
        ax.set_xlabel("← menor riesgo     mayor riesgo →", fontsize=11.5)
fig.tight_layout(w_pad=2.5)
guardar(fig, "importancia_variables.png")
print("Figuras en", SALIDA)
