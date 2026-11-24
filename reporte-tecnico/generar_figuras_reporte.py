"""Genera dos figuras del reporte tecnico: curvas Precision-Recall en Test y el diagrama de la metodologia.

Reutiliza el mismo procedimiento de presentacion/generar_figuras.py (misma particion, semilla 42 y
comprobacion contra modelos/metadatos.json). Uso desde la raiz del repositorio:
    python reporte-tecnico/generar_figuras_reporte.py
"""
import json
import warnings
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = Path(__file__).resolve().parent / "figuras"
meta = json.load(open(RAIZ / "modelos" / "metadatos.json", encoding="utf-8"))
TINTA, TINTA_2, GRIS, CUADRICULA = "#1F2A37", "#5B6774", "#9AA5B1", "#E3E8EE"
COLOR = {"Regresion Logistica": "#2a78d6", "SVM": "#eb6834", "Random Forest": "#1baf7a", "XGBoost": "#eda100"}
NOMBRE = {"Regresion Logistica": "Regresión Logística", "SVM": "SVM", "Random Forest": "Random Forest", "XGBoost": "XGBoost"}
ORDEN = list(COLOR)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": TINTA, "axes.labelcolor": TINTA,
                     "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.edgecolor": GRIS, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": CUADRICULA, "axes.axisbelow": True,
                     "savefig.dpi": 300, "legend.frameon": False})

# ---------------- Curvas Precision-Recall en Test ----------------
df = pd.read_csv(RAIZ / "nhanes_testosterona_2021_2023.csv").rename(columns={
    "SEQN": "id_participante", "RIDAGEYR": "edad", "BMXBMI": "imc", "BMXWAIST": "cintura", "LBXSHBG": "shbg",
    "LBXEST": "estradiol", "LBXLUH": "lh", "LBXFSH": "fsh", "DIQ010": "diabetes", "BPQ020": "hipertension",
    "SMQ020": "fumador", "ALQ130": "tragos_por_dia", "RIDRETH3": "raza_etnia", "DMDEDUC2": "escolaridad",
    "LBXTST": "testosterona_total"})
y = df["deficiencia_testosterona"].astype(int)
X = df.drop(columns=["id_participante", "testosterona_total", "deficiencia_testosterona"])
_, X_test, _, y_test = train_test_split(X, y, test_size=0.20, stratify=y, random_state=42)
especiales = {"hipertension": [7, 9], "fumador": [7, 9], "escolaridad": [7, 9], "tragos_por_dia": [777, 999]}
etiquetas = {
    "diabetes": {1: "Si", 2: "No", 3: "Prediabetes"}, "hipertension": {1: "Si", 2: "No"}, "fumador": {1: "Si", 2: "No"},
    "raza_etnia": {1: "Mexico americano", 2: "Otro hispano", 3: "Blanco no hispano", 4: "Negro no hispano",
                   6: "Asiatico no hispano", 7: "Otra o multirracial"},
    "escolaridad": {1: "Menos de 9 grado", 2: "9 a 11 grado", 3: "Preparatoria completa",
                    4: "Universidad incompleta", 5: "Universidad completa o mas"}}
for col, cods in especiales.items():
    X_test[col] = X_test[col].replace(cods, np.nan)
for col, mapa in etiquetas.items():
    X_test[col] = X_test[col].map(mapa)
X_test = X_test[meta["orden_columnas"]]

fig, ax = plt.subplots(figsize=(3.4, 3.4))
prev = y_test.mean()
ax.axhline(prev, color=GRIS, ls="--", lw=1)
ax.text(0.02, prev + 0.015, f"azar = {prev:.3f}", color=TINTA_2, fontsize=8)
for n in ORDEN:
    info = meta["modelos"][n]
    p = joblib.load(RAIZ / "modelos" / info["archivo"]).predict_proba(X_test)[:, 1]
    pr, rc, _ = precision_recall_curve(y_test, p)
    ap = average_precision_score(y_test, p)
    ax.plot(rc, pr, color=COLOR[n], lw=1.6, label=f"{NOMBRE[n]} (AP {ap:.3f})")
    mt = info["metricas_test"]
    ax.plot(mt["Recall"], mt["Precision"], "o", color=COLOR[n], ms=5, mec="white", mew=1)
    print(n, "AP", round(ap, 4))
ax.set_xlabel("Recall"); ax.set_ylabel("Precisión"); ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7.5, handlelength=1.4, columnspacing=1.0)
fig.savefig(SALIDA / "curvas_pr.png", bbox_inches="tight", facecolor="white"); plt.close(fig)

# ---------------- Curvas ROC en Test (mismo estilo que las PR) ----------------
from sklearn.metrics import roc_auc_score, roc_curve
fig, ax = plt.subplots(figsize=(3.4, 3.4))
ax.plot([0, 1], [0, 1], color=GRIS, ls="--", lw=1)
for n in ORDEN:
    info = meta["modelos"][n]
    p_ = joblib.load(RAIZ / "modelos" / info["archivo"]).predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, p_)
    ax.plot(fpr, tpr, color=COLOR[n], lw=1.6, label=f"{NOMBRE[n]} (AUC {roc_auc_score(y_test, p_):.3f})")
    mt = info["metricas_test"]
    ax.plot(mt["FP"] / (mt["FP"] + mt["TN"]), mt["Recall"], "o", color=COLOR[n], ms=5, mec="white", mew=1)
ax.set_xlabel("Tasa de falsos positivos"); ax.set_ylabel("Recall (tasa de verdaderos positivos)")
ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=7.5, handlelength=1.4, columnspacing=1.0)
fig.savefig(SALIDA / "curvas_roc.png", bbox_inches="tight", facecolor="white"); plt.close(fig)

# ---------------- Diagrama de la metodologia ----------------
fig, ax = plt.subplots(figsize=(7.2, 2.9)); ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")


def caja(x, y0, w, h, txt, fc="#E8F1F5", ec="#065A82", bold=False):
    ax.add_patch(FancyBboxPatch((x, y0), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.1))
    ax.text(x + w / 2, y0 + h / 2, txt, ha="center", va="center", fontsize=7.2, color=TINTA,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def flecha(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=TINTA_2, lw=1.1))


caja(0.5, 15, 16, 12, "NHANES\n2021-2023\n7 archivos\npor SEQN", bold=True)
caja(20, 15, 17, 12, "Limpieza\nhombres ≥ 20 años\nobjetivo: T < 300\n2514 filas")
caja(41, 15, 14, 12, "Partición 80/20\nestratificada\nsemilla 42")
caja(60, 29, 26, 10, "Entrenamiento (2011)\nPipeline por fold: imputar,\nescalar y codificar", fc="#FFFFFF")
caja(60, 15, 26, 10, "GridSearchCV, 5 folds\nmaximiza ROC AUC\n4 modelos", fc="#FFFFFF")
caja(60, 1, 26, 10, "Umbral F2 con predicciones\nfuera de muestra\n(fijo desde aquí)", fc="#FFFFFF")
caja(89, 15, 10.5, 12, "Prueba\n(503)\nuna sola\nevaluación", fc="#FDF1E7", ec="#eb6834", bold=True)
flecha(17.2, 21, 19.6, 21); flecha(37.8, 21, 40.6, 21)
flecha(55.4, 24, 59.6, 32); flecha(55.4, 20, 59.6, 20)
flecha(73, 28.6, 73, 25.4); flecha(73, 14.6, 73, 11.4)
flecha(86.4, 6, 94, 14.6)
ax.text(94.2, 29.5, "aislada hasta\nel final", fontsize=6.8, color="#B4501F", ha="center", va="bottom")
fig.savefig(SALIDA / "diagrama_metodologia.png", bbox_inches="tight", facecolor="white"); plt.close(fig)
print("listo")
