"""Construye la presentacion del proyecto final (PowerPoint) con python-pptx.

Estilo de la diapositiva de muestra: 16:9, titulos en Cambria azul verdoso, texto en Calibri, tarjetas claras.
Las cifras salen de modelos/metadatos.json, de las salidas guardadas de entrenamiento-modelos.ipynb y de los
articulos citados (verificados en sus resumenes o textos). Las figuras las genera generar_figuras.py.

Uso (desde la raiz del repositorio):  python presentacion/construir_presentacion.py
"""
import json
import math
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

RAIZ = Path(__file__).resolve().parent.parent
FIG = Path(__file__).resolve().parent / "figuras"
SALIDA = Path(__file__).resolve().parent / "presentacion-proyecto-final.pptx"
meta = json.load(open(RAIZ / "modelos" / "metadatos.json", encoding="utf-8"))
T = {n: meta["modelos"][n]["metricas_test"] for n in meta["modelos"]}

TEAL, INK, MUTED = RGBColor(0x06, 0x5A, 0x82), RGBColor(0x1F, 0x2A, 0x37), RGBColor(0x5B, 0x67, 0x74)
CARD, LIGHT, WHITE, LINE = RGBColor(0xE8, 0xF1, 0xF5), RGBColor(0xF4, 0xF8, 0xFA), RGBColor(255, 255, 255), RGBColor(0xC9, 0xD3, 0xDB)
URL_APP = "https://deteccion-testosterona-ml.streamlit.app/"
URL_REPO = "https://github.com/paskcual/deteccion-testosterona-ml"
TOTAL = 25

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
REVISION = []  # (diapositiva, descripcion, alto estimado, alto disponible) para detectar texto que no cabe


def segmentos(txt):
    """Divide 'normal **negrita** normal' en [(texto, negrita)]."""
    partes = txt.split("**")
    return [(p, i % 2 == 1) for i, p in enumerate(partes) if p]


def estimar_alto(parrafos, size, ancho_in, vineta, interlineado=1.12, espacio=6):
    """Altura aproximada en pulgadas de un bloque de texto (heuristica para detectar desbordes)."""
    ancho_pt = ancho_in * 72 - (30 if vineta else 0) - 14
    total = 0
    for p in parrafos:
        plano = "".join(t for t, _ in segmentos(p))
        lineas = max(1, math.ceil(len(plano) * size * 0.5 / ancho_pt))
        total += lineas * size * interlineado + espacio
    return total / 72


def poner_runs(par, txt, size, color, fuente, negrita_base=False):
    for t, neg in segmentos(txt):
        r = par.add_run()
        r.text = t
        r.font.size, r.font.name, r.font.bold = Pt(size), fuente, (neg or negrita_base)
        r.font.color.rgb = color


def vineta_xml(par, nivel_sangria=0.28):
    pPr = par._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(nivel_sangria))))
    pPr.set("indent", str(-int(Inches(nivel_sangria))))
    for hijo in list(pPr):
        if hijo.tag in (qn("a:buNone"), qn("a:buChar")):
            pPr.remove(hijo)
    bu = pPr.makeelement(qn("a:buChar"), {"char": "•"})
    pPr.append(bu)


def texto(sl, x, y, w, h, parrafos, size=18, color=INK, fuente="Calibri", negrita=False, vineta=False,
          alinear=PP_ALIGN.LEFT, ancla=MSO_ANCHOR.TOP, espacio=6, revisar=True):
    if isinstance(parrafos, str):
        parrafos = [parrafos]
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = ancla
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, p in enumerate(parrafos):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = alinear
        par.space_after = Pt(espacio)
        if vineta:
            vineta_xml(par)
        poner_runs(par, p, size, color, fuente, negrita)
    if revisar:
        REVISION.append((len(prs.slides), parrafos[0][:40], estimar_alto(parrafos, size, w, vineta, espacio=espacio), h))
    return tb


def rect(sl, x, y, w, h, relleno=CARD, borde=None, redondo=True):
    forma = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if redondo else MSO_SHAPE.RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    if redondo:
        forma.adjustments[0] = 0.08
    forma.fill.solid()
    forma.fill.fore_color.rgb = relleno
    if borde is None:
        forma.line.fill.background()
    else:
        forma.line.color.rgb = borde
        forma.line.width = Pt(1)
    forma.shadow.inherit = False
    return forma


def tarjeta(sl, x, y, w, h, cifra, leyenda, size_cifra=36, size_ley=14):
    rect(sl, x, y, w, h)
    texto(sl, x + 0.15, y + 0.08, w - 0.3, h * 0.52, cifra, size=size_cifra, color=TEAL, fuente="Cambria", negrita=True,
          ancla=MSO_ANCHOR.MIDDLE, revisar=False)
    texto(sl, x + 0.15, y + h * 0.55, w - 0.3, h * 0.42, leyenda, size=size_ley, revisar=False)


def tabla(sl, x, y, anchos, filas, size=14, alto_fila=0.42, alinear=None, resaltar_ultima=False, alto_encabezado=None):
    n, m = len(filas), len(anchos)
    forma = sl.shapes.add_table(n, m, Inches(x), Inches(y), Inches(sum(anchos)), Inches(alto_fila * n))
    tb = forma.table
    tblPr = tb._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    for j, a in enumerate(anchos):
        tb.columns[j].width = Inches(a)
    total_est = 0
    for i, fila in enumerate(filas):
        max_lin = 1
        for j, valor in enumerate(fila):
            c = tb.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            enc = i == 0
            ult = resaltar_ultima and i == n - 1
            c.fill.fore_color.rgb = TEAL if enc else (CARD if ult else (WHITE if i % 2 else LIGHT))
            par = c.text_frame.paragraphs[0]
            par.alignment = (alinear[j] if alinear else PP_ALIGN.LEFT)
            poner_runs(par, str(valor), size, WHITE if enc else INK, "Calibri", negrita_base=enc or ult)
            c.text_frame.word_wrap = True
            plano = "".join(t for t, _ in segmentos(str(valor)))
            lin = max(1, math.ceil(len(plano) * size * 0.5 / (anchos[j] * 72 - 14)))
            max_lin = max(max_lin, lin)
        h_fila = max(alto_fila if not (i == 0 and alto_encabezado) else alto_encabezado, max_lin * size * 1.2 / 72 + 0.08)
        tb.rows[i].height = Inches(h_fila)
        total_est += h_fila
    REVISION.append((len(prs.slides), "tabla", total_est, None))
    return forma, total_est


def imagen(sl, nombre, x, y, w, h, alinear="centro"):
    ruta = FIG / nombre
    ancho_px, alto_px = Image.open(ruta).size
    esc = min(w / ancho_px, h / alto_px)
    ww, hh = ancho_px * esc, alto_px * esc
    px = x + (w - ww) / 2 if alinear == "centro" else x
    return sl.shapes.add_picture(str(ruta), Inches(px), Inches(y + (h - hh) / 2), Inches(ww), Inches(hh))


def flecha(sl, x1, y1, x2, y2, color=MUTED):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(2)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def linea(sl, x1, y1, x2, y2, color=LINE):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(2)
    return c


def diapositiva(seccion, titulo, fuentes=None, notas=None):
    sl = prs.slides.add_slide(BLANK)
    n = len(prs.slides)
    if seccion:
        texto(sl, 0.6, 0.22, 12.1, 0.3, seccion.upper(), size=12, color=MUTED, negrita=True, revisar=False)
    texto(sl, 0.6, 0.48, 12.1, 0.9, titulo, size=28, color=TEAL, fuente="Cambria", negrita=True, ancla=MSO_ANCHOR.TOP,
          revisar=False)
    if len(titulo) > 62:
        REVISION.append((n, "TITULO LARGO: " + titulo[:30], len(titulo), 62))
    if fuentes:
        texto(sl, 0.6, 6.68, 12.1, 0.3, "Fuentes: " + fuentes, size=11, color=MUTED, revisar=False)
    texto(sl, 0.6, 7.05, 10.0, 0.3, "Proyecto final de Machine Learning  |  NHANES 2021 a 2023", size=11, color=MUTED,
          revisar=False)
    texto(sl, 11.2, 7.05, 1.5, 0.3, f"{n} / {TOTAL}", size=11, color=MUTED, alinear=PP_ALIGN.RIGHT, revisar=False)
    if notas:
        sl.notes_slide.notes_text_frame.text = notas
    return sl


f3 = lambda v: f"{v:.3f}"

# =============================================================================================
# 1. Portada
# =============================================================================================
sl = prs.slides.add_slide(BLANK)
rect(sl, 0, 0, 13.333, 7.5, relleno=TEAL, redondo=False)
texto(sl, 0.9, 1.25, 11.5, 0.4, "PROYECTO FINAL DE MACHINE LEARNING", size=16, color=RGBColor(0xBF, 0xDD, 0xEA), negrita=True,
      revisar=False)
texto(sl, 0.9, 1.8, 11.5, 2.3, "Detección de posible deficiencia de testosterona en hombres adultos", size=42, color=WHITE,
      fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.9, 4.0, 11.5, 0.6, "Regresión Logística, SVM, Random Forest y XGBoost con la base NHANES 2021 a 2023",
      size=22, color=RGBColor(0xE8, 0xF1, 0xF5), revisar=False)
texto(sl, 0.9, 5.3, 11.5, 1.4, ["**Jesús Pascual Garay Ordaz**  |  Matrícula 306025",
                                 "Programa MIC, UACH  |  Machine Learning",
                                 "Docente: Dra. Olanda Prieto Ordaz  |  Noviembre de 2026"],
      size=18, color=WHITE, espacio=4, revisar=False)
sl.notes_slide.notes_text_frame.text = (
    "Tiempo sugerido: 30 segundos.\n"
    "Buenas tardes, voy a presentar mi proyecto final de Machine Learning, que consiste en identificar a hombres adultos con "
    "posible deficiencia de testosterona a partir de variables clínicas y hormonales de la encuesta NHANES 2021 a 2023, "
    "comparando cuatro modelos que son la regresión logística, el SVM, el Random Forest y XGBoost, y terminando con una "
    "aplicación web que ya está publicada y que voy a mostrar al final.")

# =============================================================================================
# 2. Contenido
# =============================================================================================
sl = diapositiva("Contenido", "Qué voy a presentar", notas=(
    "Tiempo sugerido: 30 segundos.\n"
    "La presentación sigue el orden del proyecto, empezando por el problema, su importancia y lo que se ha investigado antes, "
    "después la metodología con los datos, los modelos y el diseño de los experimentos, luego los resultados con la comparación "
    "contra el estado del arte, y al final la aplicación y las conclusiones, de modo que si alguien tiene una duda sobre una "
    "decisión metodológica puede ubicar de inmediato en qué parte se justificó."))
bloques = [("1", "Introducción y antecedentes", "Problema, tarea de aprendizaje y trabajos previos"),
           ("2", "Justificación", "Por qué importa y qué se quiere demostrar"),
           ("3", "Metodología", "Datos, preparación, modelos y configuración experimental"),
           ("4", "Resultados y análisis", "Modelos base, optimizados, estado del arte y gráficas"),
           ("5", "Conclusiones", "Hallazgos, limitaciones y trabajo futuro"),
           ("6", "Aplicación y referencias", "Interfaz en Streamlit y bibliografía")]
for i, (num, tit, sub) in enumerate(bloques):
    col, fila = i % 2, i // 2
    x, y = 0.6 + col * 6.15, 1.65 + fila * 1.65
    rect(sl, x, y, 5.95, 1.4)
    texto(sl, x + 0.2, y + 0.15, 0.8, 1.1, num, size=40, color=TEAL, fuente="Cambria", negrita=True, ancla=MSO_ANCHOR.MIDDLE,
          revisar=False)
    texto(sl, x + 1.05, y + 0.22, 4.75, 0.5, tit, size=21, negrita=True, revisar=False)
    texto(sl, x + 1.05, y + 0.78, 4.75, 0.55, sub, size=15, color=MUTED, revisar=False)

# =============================================================================================
# 3. Introduccion
# =============================================================================================
sl = diapositiva("1. Introducción y antecedentes", "La deficiencia de testosterona suele pasar desapercibida",
                 fuentes="[2], [3], [4]", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "El área de aplicación es la salud masculina, entre la endocrinología y la urología, que son las dos especialidades de las guías "
    "que uso como referencia. La deficiencia de testosterona, que también se llama hipogonadismo bioquímico, se define con un criterio de laboratorio, "
    "ya que la guía de la American Urological Association considera razonable un corte de 300 ng/dL de testosterona total y pide "
    "confirmarla con dos mediciones matutinas y con síntomas, lo que implica que la condición solo se detecta cuando alguien "
    "pide el análisis de sangre. En los cuatro ciclos de NHANES que analiza Goulian, que son 2011 a 2016 y 2021 a 2023, el 25.7% de los "
    "hombres cumplía ese criterio, con una baja a 20.3% en el ciclo 2021 a 2023, y la condición se asocia con obesidad, con glucosa alterada y con diabetes, lo que "
    "hace pensar en una herramienta que use datos fáciles de obtener para decidir a quién conviene pedirle el análisis.\n"
    "Idea principal: no se busca diagnosticar, sino priorizar."))
texto(sl, 0.6, 1.6, 7.4, 4.9, [
    "**Área de aplicación.** Salud masculina, entre la endocrinología y la urología, donde se decide a quién estudiarle las hormonas [2], [3].",
    "**Definición.** Testosterona total menor a 300 ng/dL, criterio de la American Urological Association [2].",
    "**Confirmación.** El diagnóstico requiere síntomas y mediciones matutinas repetidas [2], [3].",
    "**Asociaciones.** Obesidad (OR ajustado 2.69), glucosa alterada y diabetes se asocian con la deficiencia [4].",
    "**El problema y la idea.** Solo se detecta cuando alguien pide el análisis de sangre y las guías no recomiendan tamizar a toda la población [3]; se busca usar datos fáciles de obtener para decidir a quién pedírselo."],
      size=18, vineta=True, espacio=9)
tarjeta(sl, 8.5, 1.7, 4.2, 1.9, "25.7%", "de los hombres tenía deficiencia en NHANES (2011 a 2016 y 2021 a 2023); 20.3% en 2021 a 2023 [4]", size_cifra=44)
tarjeta(sl, 8.5, 3.85, 4.2, 1.9, "300 ng/dL", "umbral de testosterona total que define la deficiencia [2]", size_cifra=38)

# =============================================================================================
# 4. Tarea y objetivo
# =============================================================================================
sl = diapositiva("1. Introducción y antecedentes", "Tarea de aprendizaje y objetivo del proyecto", notas=(
    "Tiempo sugerido: 1 minuto.\n"
    "La tarea es de clasificación binaria supervisada, en la que a partir de trece variables de cada hombre el modelo estima la "
    "probabilidad de tener deficiencia, y como la clase positiva es solo el 22% de los casos hay que cuidar el desbalance en cada "
    "decisión. El objetivo general es construir y comparar cuatro modelos con exactamente el mismo protocolo para que la "
    "comparación sea justa, y los objetivos específicos van desde preparar los datos sin fuga de información hasta poner los "
    "modelos en una interfaz que cualquiera pueda abrir."))
rect(sl, 0.6, 1.6, 5.6, 4.9)
texto(sl, 0.8, 1.72, 5.2, 0.4, "Tarea", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.8, 2.2, 5.2, 4.2, [
    "**Clasificación binaria supervisada**",
    "**Entrada:** 13 variables clínicas, hormonales y de estilo de vida",
    "**Salida:** probabilidad de deficiencia y una decisión sí o no con un umbral",
    "**Clase positiva:** 22.2% de los hombres, por lo que hay desbalance"], size=18, vineta=True, espacio=10)
texto(sl, 6.6, 1.72, 6.1, 0.4, "Objetivo general", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 6.6, 2.2, 6.1, 1.2, "Construir y comparar cuatro modelos de clasificación con el mismo protocolo para identificar "
      "hombres con posible deficiencia de testosterona, y ponerlos a disposición en una interfaz web.", size=18)
texto(sl, 6.6, 3.55, 6.1, 0.4, "Objetivos específicos", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 6.6, 4.0, 6.1, 2.6, [
    "Preparar los datos sin fuga de información",
    "Entrenar y optimizar cuatro modelos con el mismo protocolo",
    "Elegir un umbral que priorice detectar los casos",
    "Evaluar una sola vez en Test y analizar las variables",
    "Implementar y desplegar una interfaz"], size=17, vineta=True, espacio=5)

# =============================================================================================
# 5. Antecedentes
# =============================================================================================
sl = diapositiva("1. Introducción y antecedentes", "Qué se ha investigado antes", fuentes="[4] a [10]", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "Revisé trabajos que usan NHANES para este mismo problema y trabajos con aprendizaje automático en otros datos, y lo que se "
    "ve es que los estudios con NHANES se concentran en índices antropométricos y metabólicos evaluados con curvas ROC, como el "
    "índice TyG-WHtR con un AUC de 0.776 en Zhang y de 0.762 en Guo, y que el único que compara varios modelos de aprendizaje "
    "automático sobre NHANES es Yu, con AUC entre 0.688 y 0.746, mientras que Goulian usa el mismo ciclo que yo pero con una "
    "regresión logística explicativa. En los trabajos con otros datos, Novaes y Kivrak encuentran que XGBoost y los ensambles "
    "funcionan bien y que el desbalance obliga a cuidar la sensibilidad, que es justo lo que guía las decisiones de este proyecto."))
rect(sl, 0.6, 1.6, 6.0, 4.95)
texto(sl, 0.8, 1.7, 5.6, 0.4, "Con la base NHANES", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.8, 2.2, 5.6, 4.3, [
    "**Índices simples con curva ROC:** TyG-WHtR alcanza AUC 0.776 [6] y 0.762 [7]; el índice cardiometabólico, 0.724 [8].",
    "**Aprendizaje automático:** seis modelos con AUC de 0.688 a 0.746; el mejor, LightGBM [5].",
    "**Enfoque explicativo:** regresión logística con el ciclo 2021 a 2023, sin métricas predictivas [4]."],
      size=17, vineta=True, espacio=9)
rect(sl, 6.85, 1.6, 5.85, 4.95)
texto(sl, 7.05, 1.7, 5.45, 0.4, "Con otros datos clínicos", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 7.05, 2.2, 5.45, 2.2, [
    "**Cohorte de 3397 pacientes:** XGBoost fue el mejor clasificador base y el ensamble por promedio ponderado el mejor en general [10].",
    "**Efecto del desbalance:** XGBoost fue el modelo más adecuado en prueba, con SMOTE [9]."],
      size=17, vineta=True, espacio=9)
texto(sl, 7.05, 4.45, 5.45, 0.4, "Cómo se relaciona con este proyecto", size=18, color=TEAL, fuente="Cambria", negrita=True,
      revisar=False)
texto(sl, 7.05, 4.9, 5.45, 1.6, [
    "Árboles y boosting suelen ser competitivos",
    "El desbalance obliga a cuidar la sensibilidad",
    "Aquí se agregan SHBG, estradiol, LH y FSH"], size=16, vineta=True, espacio=4)

# =============================================================================================
# 6. Justificacion
# =============================================================================================
sl = diapositiva("2. Justificación", "Por qué vale la pena resolver este problema", fuentes="[2], [3], [4]", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "El problema es relevante porque la deficiencia de testosterona se asocia con obesidad, diabetes e hipertensión y porque el "
    "análisis que la confirma no se pide de forma rutinaria, de modo que una herramienta basada en datos que ya se conocen "
    "ayuda a decidir a quién pedírselo, aunque nunca sustituye el criterio médico ni el análisis. Comparar varios algoritmos es "
    "pertinente porque cada uno representa una hipótesis distinta sobre los datos, ya que la regresión logística supone una "
    "relación lineal, el SVM una frontera no lineal y los árboles interacciones entre variables, y con los mismos datos y el "
    "mismo protocolo se puede responder si la complejidad extra realmente aporta algo."))
preguntas = [("¿Por qué es relevante?", "La deficiencia se asocia con obesidad, diabetes e hipertensión y solo se detecta cuando se pide el análisis [2] a [4]."),
             ("¿Qué aporta el aprendizaje automático?", "Una herramienta de apoyo con datos ya disponibles para priorizar a quién pedirle el análisis, no un diagnóstico."),
             ("¿Por qué comparar algoritmos?", "Cada uno supone algo distinto: relación lineal, frontera no lineal o interacciones entre variables."),
             ("¿Qué se quiere demostrar?", "Si la complejidad extra mejora al modelo lineal, y qué pesan la optimización y el umbral de decisión.")]
for i, (q, r) in enumerate(preguntas):
    col, fila = i % 2, i // 2
    x, y = 0.6 + col * 6.15, 1.65 + fila * 2.45
    rect(sl, x, y, 5.95, 2.25)
    texto(sl, x + 0.2, y + 0.15, 5.55, 0.5, q, size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
    texto(sl, x + 0.2, y + 0.75, 5.55, 1.45, r, size=17)

# =============================================================================================
# 7. Base de datos
# =============================================================================================
sl = diapositiva("3.1 Descripción de la base de datos", "NHANES 2021 a 2023: 2514 hombres y 13 predictoras", fuentes="[1]", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "La base viene de la encuesta NHANES 2021 a 2023 del CDC, de la que uní siete archivos de demografía, hormonas sexuales, "
    "medidas corporales, diabetes, presión arterial, alcohol y tabaco, y me quedé con los hombres de 20 años o más que tienen la "
    "testosterona medida, lo que da 2514 hombres. La variable objetivo vale 1 cuando la testosterona total es menor a 300 ng/dL, "
    "y eso ocurre en 559 hombres, el 22.2%, por lo que la clase positiva es minoritaria. Las trece predictoras incluyen cuatro "
    "hormonas, tres medidas corporales y seis variables de antecedentes y sociodemográficas, y deliberadamente excluí la "
    "testosterona total porque con ella se calcula el objetivo y sería fuga de información."))
tarjeta(sl, 0.6, 1.65, 3.8, 1.55, "2514", "hombres de 20 años o más con testosterona medida", size_cifra=38, size_ley=14)
tarjeta(sl, 0.6, 3.4, 3.8, 1.55, "13", "predictoras (8 numéricas y 5 categóricas)", size_cifra=38, size_ley=14)
tarjeta(sl, 0.6, 5.15, 3.8, 1.4, "22.2%", "con deficiencia: 559 contra 1955", size_cifra=38, size_ley=14)
tabla(sl, 4.75, 1.65, [2.5, 5.45], [
    ["Grupo", "Variables"],
    ["Hormonas", "SHBG, estradiol, LH y FSH"],
    ["Medidas corporales", "Edad, IMC y cintura"],
    ["Antecedentes", "Diabetes, hipertensión, fumador y tragos por día"],
    ["Sociodemográficas", "Raza y origen étnico, escolaridad"],
    ["**Variable objetivo**", "Deficiencia: testosterona total menor a 300 ng/dL"]], size=15, alto_fila=0.62)
texto(sl, 4.75, 5.6, 7.95, 0.95, "No son predictoras: el identificador y la testosterona total, porque con ella se calcula "
      "el objetivo y sería fuga de información.", size=15, color=MUTED)

# =============================================================================================
# 8. EDA
# =============================================================================================
sl = diapositiva("3.1 Análisis exploratorio (solo Train)", "Hallazgos del análisis exploratorio", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "El análisis exploratorio se hizo únicamente con Train, que tiene 2011 hombres, y muestra varias cosas, que son el desbalance de "
    "clases con 22% de positivos, unos pocos valores faltantes, destacando los tragos por día con 12.4% y la cintura con 3.7%, "
    "y los valores atípicos, que con la regla del rango intercuartílico llegan a 9.6% en la FSH y a 6.8% en la LH, hormonas con "
    "distribuciones muy sesgadas a la derecha. Decidí no eliminarlos, porque en variables sesgadas como las hormonas esos valores "
    "altos son esperables y no necesariamente errores, y porque la imputación con la mediana y el escalado los toleran, mientras "
    "que los árboles no se ven afectados. Las correlaciones con el objetivo muestran que la cintura y el IMC se relacionan "
    "positivamente con 0.31 y la SHBG y el estradiol negativamente con 0.29 y 0.24, y como la cintura y el IMC están muy "
    "correlacionadas entre sí, con 0.92, la regresión logística le da poco peso a una de las dos. Entre los antecedentes, la "
    "deficiencia aparece en 36% de los hombres con diabetes contra 19% de los que no la tienen, y en 27% de los hipertensos contra 19%."))
imagen(sl, "../../reporte-tecnico/figuras/correlaciones.png", 0.6, 1.6, 6.4, 3.7)
texto(sl, 0.6, 5.4, 6.4, 0.8, "Correlación de Pearson de cada variable numérica con la deficiencia (Train, 2011 hombres).",
      size=13, color=MUTED)
texto(sl, 7.25, 1.6, 5.45, 4.95, [
    "**Desbalance:** 22.2% con deficiencia (447 de 2011 en Train)",
    "**Faltantes:** tragos por día 12.4%, cintura 3.7%, IMC 1.2%, estradiol 0.5%",
    "**Atípicos** (regla del IQR): FSH 9.6% y LH 6.8%, con distribuciones sesgadas a la derecha; no se eliminan",
    "**Más asociadas:** cintura (+0.31), IMC (+0.31), SHBG (-0.29) y estradiol (-0.24)",
    "**Redundancia:** cintura e IMC se correlacionan 0.92 entre sí",
    "**Antecedentes:** deficiencia en 36% con diabetes contra 19% sin ella, y en 27% con hipertensión contra 19%"],
      size=16, vineta=True, espacio=8)

# =============================================================================================
# 9. Preparacion y fuga
# =============================================================================================
sl = diapositiva("3.2 Preparación y procesamiento de los datos", "Preparación de los datos y control de la fuga de información",
                 notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "Lo más importante aquí es cómo se evitó la fuga de información, y para eso la partición 80/20 estratificada se hace antes de "
    "ajustar cualquier cosa, y todo lo que aprende de los datos, que es la imputación con la mediana o la moda, el escalado y la "
    "codificación, vive dentro de un Pipeline que se ajusta solo con los datos de entrenamiento de cada fold. Los códigos de "
    "rehuso y de no sabe, como 7, 9, 777 y 999, se pasan a faltante con una regla fija que no aprende nada de los datos, y el "
    "desbalance se trata con pesos de clase y con un umbral de decisión elegido con predicciones fuera de muestra, sin usar SMOTE, "
    "porque con 22% de positivos el peso de clase fue suficiente y no se generan datos sintéticos. Además se conservan las trece "
    "predictoras, sin selección ni reducción de variables, ya que la docente confirmó que con trece es suficiente y los modelos de "
    "árboles y la penalización L1 de la regresión logística ya ponderan por sí solos la importancia de cada una, y los valores "
    "atípicos de las hormonas no se eliminan por las razones que mencioné en el análisis exploratorio."))
pasos = [("1", "Variables", "se excluyen el identificador y la testosterona total (con ella se calcula el objetivo); se conservan las 13 predictoras, sin selección ni reducción"),
         ("2", "Reglas fijas", "los códigos 7, 9, 777 y 999 pasan a faltante y los códigos se cambian por su significado"),
         ("3", "Partición", "80/20 estratificada con semilla 42: 2011 en Train y 503 en Test, antes de ajustar nada"),
         ("4", "Pipeline", "mediana y escalado en las numéricas, moda y OneHotEncoder en las categóricas, ajustados solo con Train de cada fold"),
         ("5", "Desbalance y atípicos", "pesos de clase y umbral elegido con predicciones fuera de muestra, sin SMOTE; los atípicos de las hormonas no se eliminan"),
         ("6", "Test aislado", "no se usa para elegir modelos, hiperparámetros ni umbral; se evalúa una sola vez")]
for i, (num, tit, desc) in enumerate(pasos):
    col, fila = i % 2, i // 2
    x, y = 0.6 + col * 6.15, 1.6 + fila * 1.65
    rect(sl, x, y, 5.95, 1.5)
    texto(sl, x + 0.15, y + 0.1, 0.7, 1.3, num, size=34, color=TEAL, fuente="Cambria", negrita=True, ancla=MSO_ANCHOR.MIDDLE,
          revisar=False)
    texto(sl, x + 0.85, y + 0.08, 5.0, 0.4, tit, size=18, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
    texto(sl, x + 0.85, y + 0.5, 5.0, 1.0, desc, size=14)

# =============================================================================================
# 10. Modelos
# =============================================================================================
sl = diapositiva("3.3 Modelos implementados", "Cuatro modelos con distintas hipótesis sobre los datos",
                 fuentes="[11] a [14]", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "Se eligieron cuatro modelos que representan hipótesis distintas, empezando por la regresión logística, que es lineal y sirve "
    "como referencia interpretable, el SVM con kernel RBF, que busca una frontera no lineal con el mayor margen, el Random Forest, "
    "que promedia 300 árboles entrenados con muestras y variables al azar para reducir la varianza, y XGBoost, que construye los "
    "árboles de forma secuencial para que cada uno corrija los errores del anterior. Como el SVM no entrega probabilidades por sí "
    "solo, se calibra con una sigmoide, que es la alternativa que recomienda scikit-learn, y eso permite compararlo con los demás "
    "en la interfaz."))
mod = [("Regresión Logística", "Modelo lineal con regularización. Es la referencia: sencilla, rápida e interpretable por sus coeficientes."),
       ("SVM con kernel RBF [14]", "Busca una frontera no lineal con el mayor margen. Se calibra con una sigmoide para entregar probabilidades."),
       ("Random Forest [12]", "300 árboles entrenados con muestras y variables al azar, cuyas probabilidades se promedian para reducir la varianza."),
       ("XGBoost [13]", "Árboles pequeños construidos en secuencia, donde cada uno corrige los errores del anterior (boosting).")]
for i, (tit, desc) in enumerate(mod):
    col, fila = i % 2, i // 2
    x, y = 0.6 + col * 6.15, 1.6 + fila * 2.4
    rect(sl, x, y, 5.95, 2.2)
    texto(sl, x + 0.2, y + 0.12, 5.55, 0.5, tit, size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
    texto(sl, x + 0.2, y + 0.72, 5.55, 1.45, desc, size=16)
texto(sl, 0.6, 6.4, 12.1, 0.3, "Implementados con scikit-learn [11] y xgboost; el SVM usa SVC con calibración (CalibratedClassifierCV).",
      size=13, color=MUTED)

# =============================================================================================
# 11. Configuracion experimental (diagrama)
# =============================================================================================
sl = diapositiva("3.4 Configuración experimental", "Diseño experimental: del dato a la evaluación final", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "Este diagrama resume el procedimiento, que es el mismo para los cuatro modelos y que repite el de mis proyectos anteriores, "
    "y lo importante es distinguir las etapas, ya que el entrenamiento, la selección de hiperparámetros y la elección del umbral "
    "usan solo Train, con validación cruzada estratificada de cinco folds y el ROC AUC como criterio, mientras que Test, que son "
    "503 hombres con 112 casos positivos, se evalúa una sola vez al final con el umbral que ya estaba fijo. Esto es lo que permite "
    "que las métricas de Test sean una estimación honesta y que los modelos guardados sean exactamente los que se evaluaron."))
fila1 = [("Datos", "NHANES 2021 a 2023, 2514 hombres"), ("Partición", "80/20 estratificada, semilla 42"),
         ("Pipeline", "Imputar, escalar y codificar dentro de cada fold"),
         ("GridSearchCV", "5 folds estratificados, criterio ROC AUC"), ("Umbral", "Maximiza F2 con predicciones fuera de muestra")]
fila2 = [("Ajuste final", "Con todo Train, umbral fijo"), ("Evaluación", "Test (503 hombres), una sola vez"),
         ("Guardado", "Pipelines en .joblib y metadatos"), ("Aplicación", "Streamlit con 3 modelos")]
w, g = 2.1, 0.4
for i, (tit, desc) in enumerate(fila1):
    x = 0.6 + i * (w + g)
    rect(sl, x, 1.75, w, 1.7, relleno=CARD if i > 1 else LIGHT, borde=LINE)
    texto(sl, x + 0.1, 1.82, w - 0.2, 0.4, tit, size=17, color=TEAL, fuente="Cambria", negrita=True, alinear=PP_ALIGN.CENTER,
          revisar=False)
    texto(sl, x + 0.1, 2.3, w - 0.2, 1.1, desc, size=13.5, alinear=PP_ALIGN.CENTER)
    if i < 4:
        flecha(sl, x + w + 0.03, 2.6, x + w + g - 0.03, 2.6)
for i, (tit, desc) in enumerate(fila2):
    x = 0.6 + i * (w + g)
    rect(sl, x, 4.2, w, 1.7, relleno=TEAL if i == 1 else CARD, borde=None if i == 1 else LINE)
    texto(sl, x + 0.1, 4.27, w - 0.2, 0.4, tit, size=17, color=WHITE if i == 1 else TEAL, fuente="Cambria", negrita=True,
          alinear=PP_ALIGN.CENTER, revisar=False)
    texto(sl, x + 0.1, 4.75, w - 0.2, 1.1, desc, size=13.5, color=WHITE if i == 1 else INK, alinear=PP_ALIGN.CENTER)
    if i < 3:
        flecha(sl, x + w + 0.03, 5.05, x + w + g - 0.03, 5.05)
# Conector en codo: de la ultima caja de la fila 1 a la primera de la fila 2
x_fin, x_ini = 0.6 + 4 * (w + g) + w / 2, 0.6 + w / 2
linea(sl, x_fin, 3.47, x_fin, 3.83)
linea(sl, x_fin, 3.83, x_ini, 3.83)
flecha(sl, x_ini, 3.83, x_ini, 4.17)
texto(sl, 0.6, 6.15, 12.1, 0.5, "Todo lo que se aprende (imputación, escalado, hiperparámetros y umbral) usa solo Train. "
      "Test se evalúa una sola vez.", size=15, color=MUTED)

# =============================================================================================
# 12. Hiperparametros y metricas
# =============================================================================================
sl = diapositiva("3.4 Configuración experimental", "Búsqueda de hiperparámetros y métricas de evaluación",
                 notas=(
    "Tiempo sugerido: 1 minuto.\n"
    "A cada modelo se le hizo una búsqueda en rejilla con validación cruzada de cinco folds sobre Train, con 20 combinaciones "
    "para la regresión logística, 60 para el SVM, 48 para Random Forest y 96 para XGBoost, y siempre se incluyó el peso de la "
    "clase positiva porque en mis proyectos anteriores fue lo que más cambió el recall. El ROC AUC es el criterio para elegir "
    "modelos porque no depende del umbral y funciona con clases desbalanceadas, mientras que el recall y el F2 se usan para fijar "
    "el umbral, ya que dejar escapar un caso cuesta más que pedir un análisis de más, y la precisión, el F1 y la exactitud se "
    "reportan como complemento. Todo usa la semilla 42 con scikit-learn 1.9.1 y XGBoost 3.4.1."))
tabla(sl, 0.6, 1.6, [2.4, 6.9, 2.8], [
    ["Modelo", "Rejilla de búsqueda", "Combinaciones"],
    ["Regresión Logística", "C de 0.01 a 100, l1_ratio (0 o 1), class_weight", "20"],
    ["SVM RBF", "C de 0.01 a 100, gamma (scale o de 0.001 a 10), class_weight", "60"],
    ["Random Forest", "max_depth, min_samples_leaf, max_features y class_weight (300 árboles)", "48"],
    ["XGBoost", "n_estimators, learning_rate, max_depth, subsample, colsample_bytree y scale_pos_weight", "96"]],
      size=14, alto_fila=0.55, alinear=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER])
rect(sl, 0.6, 4.6, 12.1, 1.6)
texto(sl, 0.8, 4.7, 11.7, 1.45, [
    "**ROC AUC** elige modelos e hiperparámetros: no depende del umbral y sirve con clases desbalanceadas.",
    "**Recall y F2** fijan el umbral de decisión: dejar escapar un caso cuesta más que pedir un análisis de más.",
    "**Precisión, F1 y exactitud** se reportan como complemento. Semilla 42, scikit-learn 1.9.1 y XGBoost 3.4.1."],
      size=16, vineta=True, espacio=6)

# =============================================================================================
# 13. Resultados: modelos base
# =============================================================================================
sl = diapositiva("4.1 Comparación de modelos base", "Modelos con parámetros por defecto: validación cruzada", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "Con parámetros por defecto los cuatro modelos quedan en un ROC AUC de 0.864 a 0.890, con Random Forest arriba con 0.890 y "
    "XGBoost y la regresión logística abajo, pero todos comparten el mismo problema, que es que el recall se queda entre 0.48 y "
    "0.56, lo que significa que con el umbral estándar de 0.5 detectan a solo la mitad de los hombres con deficiencia porque "
    "ninguno compensa el desbalance. Además Random Forest y XGBoost llegan a un ROC AUC de 1.000 en entrenamiento contra 0.890 y "
    "0.864 en validación, es decir que memorizan Train, y por eso van a necesitar regularización."))
tabla(sl, 0.6, 1.6, [3.0, 1.55, 1.55, 1.55, 1.55, 1.45, 1.4], [
    ["Modelo (por defecto)", "Exactitud", "Precisión", "Recall", "F1", "ROC AUC", "AUC en Train"],
    ["Regresión Logística", "0.841", "0.696", "0.508", "0.584", "0.866", "0.876"],
    ["SVM RBF", "0.841", "0.716", "0.481", "0.573", "0.877", "0.932"],
    ["Random Forest", "0.854", "0.756", "0.510", "0.608", "0.890", "1.000"],
    ["XGBoost", "0.833", "0.645", "0.562", "0.600", "0.864", "1.000"]],
      size=16, alto_fila=0.6, alinear=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 6)
texto(sl, 0.6, 4.7, 12.1, 0.4, "Validación cruzada estratificada de 5 folds sobre Train, con umbral de 0.5.", size=14, color=MUTED)
texto(sl, 0.6, 5.15, 12.1, 1.5, [
    "**ROC AUC de 0.864 a 0.890,** pero con el umbral de 0.5 los cuatro detectan solo la mitad de los casos (recall de 0.48 a 0.56).",
    "**Random Forest y XGBoost memorizan Train** (AUC de 1.000 contra 0.890 y 0.864 en validación), por lo que necesitan regularización."],
      size=17, vineta=True, espacio=7)

# =============================================================================================
# 14. Optimizacion
# =============================================================================================
sl = diapositiva("4.2 Mejores resultados obtenidos", "Optimización de hiperparámetros", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "La optimización ayudó poco a la regresión logística, al SVM y al Random Forest, con mejoras de 0.003 a 0.007 de ROC AUC, "
    "pero ayudó mucho a XGBoost, que subió de 0.864 a 0.896, y la causa fue la regularización, ya que eligió árboles de "
    "profundidad 2 con una tasa de aprendizaje de 0.03 y muestreo de 0.7 en filas y columnas, lo que bajó su ROC AUC de "
    "entrenamiento de 1.000 a 0.934. Hay que tener presente que las diferencias entre los tres primeros, 0.884, 0.894 y 0.896, "
    "son menores que la desviación entre folds, que va de 0.008 a 0.022, por lo que en realidad están casi empatados."))
tabla(sl, 0.6, 1.55, [2.2, 5.9, 1.3, 1.2, 1.5], [
    ["Modelo", "Mejor configuración", "ROC AUC", "Desv.", "Mejora"],
    ["Regresión Logística", "C 0.1, penalización L1, pesos balanceados", "0.868", "0.019", "+0.003"],
    ["SVM RBF", "C 10, gamma 0.01, pesos balanceados", "0.884", "0.022", "+0.007"],
    ["Random Forest", "Profundidad libre, hoja mínima 3, max_features 0.5, balanceado", "0.894", "0.008", "+0.004"],
    ["XGBoost", "300 árboles, tasa 0.03, prof. 2, subsample 0.7, colsample 0.7", "0.896", "0.014", "+0.031"]],
      size=13.5, alto_fila=0.5, alinear=[PP_ALIGN.LEFT, PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 3)
imagen(sl, "auc_base_vs_optimizado.png", 0.6, 4.3, 7.0, 2.3)
texto(sl, 7.9, 4.4, 4.8, 2.2, [
    "**XGBoost ganó más** (+0.031) porque la regularización redujo su sobreajuste (AUC en Train de 1.000 a 0.934).",
    "**Los tres primeros están empatados:** sus diferencias son menores que la desviación entre folds."],
      size=15, vineta=True, espacio=6)

# =============================================================================================
# 15. Umbral y Test
# =============================================================================================
sl = diapositiva("4.2 Mejores resultados obtenidos", "El umbral de decisión y la evaluación en Test", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "El umbral que maximiza F2 es distinto para cada modelo, 0.45 en la regresión logística, 0.35 en Random Forest, 0.22 en SVM y "
    "0.16 en XGBoost, lo que no significa que unos sean mejores que otros sino que cada uno reparte sus probabilidades de forma "
    "diferente. En Test los cuatro detectan a casi los mismos hombres con deficiencia, 98 o 99 de los 112, con 13 o 14 casos que "
    "se escapan, por lo que la diferencia está en las falsas alarmas, 80 en el SVM y en Random Forest, 97 en XGBoost y 118 en la "
    "regresión logística. Con el umbral de 0.5, en cambio, el recall de XGBoost caería de 0.884 a 0.473 y el del SVM a 0.509, es "
    "decir que dejarían escapar a la mitad de los casos, y eso es lo que hace que el umbral sea la decisión que más cambia el "
    "resultado."))
imagen(sl, "efecto_umbral.png", 0.6, 1.55, 6.9, 3.1)
filas = [["Modelo", "Umbral", "ROC AUC", "Recall", "Precisión", "F1"]]
for n, nombre in (("Regresion Logistica", "Reg. Logística"), ("SVM", "SVM"), ("Random Forest", "Random Forest"),
                  ("XGBoost", "XGBoost")):
    filas.append([nombre, f"{meta['modelos'][n]['umbral']:.2f}", f3(T[n]["ROC AUC"]), f3(T[n]["Recall"]),
                  f3(T[n]["Precision"]), f3(T[n]["F1"])])
tabla(sl, 7.7, 1.65, [1.55, 0.7, 0.8, 0.7, 0.8, 0.5], filas, size=12.5, alto_fila=0.5,
      alinear=[PP_ALIGN.LEFT] + [PP_ALIGN.CENTER] * 5)
texto(sl, 7.7, 4.3, 5.0, 0.4, "Resultados en Test (503 hombres, 112 con deficiencia)", size=12.5, color=MUTED)
texto(sl, 0.6, 4.85, 12.1, 1.75, [
    "**Con el umbral elegido** los cuatro detectan 98 o 99 de los 112 casos; lo que cambia son las falsas alarmas (80 en SVM y Random Forest, 118 en Regresión Logística).",
    "**Con el umbral de 0.5** el recall de XGBoost caería de 0.884 a 0.473 y el del SVM a 0.509: el umbral es la decisión que más cambia el resultado."],
      size=16, vineta=True, espacio=7)

# =============================================================================================
# 16. ROC y matrices
# =============================================================================================
sl = diapositiva("4.4 Análisis gráfico de resultados", "Curvas ROC y matrices de confusión en Test", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "Las curvas ROC de los tres modelos no lineales casi se encuentran, con áreas de 0.892 a 0.901, y la de la regresión "
    "logística, con 0.866, queda claramente por debajo en la zona de falsos positivos entre 0.2 y 0.5, que es justo donde caen los "
    "puntos de operación elegidos. Las matrices de confusión muestran lo mismo desde otro ángulo, ya que con el umbral elegido "
    "los cuatro detectan 98 o 99 de los 112 casos y se les escapan 13 o 14, de modo que la diferencia está en las falsas "
    "alarmas, donde el SVM y el Random Forest tienen 80 y la regresión logística 118, y esto es lo que le da la ventaja a los "
    "modelos no lineales, que es una ventaja en precisión y no en capacidad de encontrar los casos."))
imagen(sl, "roc_test.png", 0.6, 1.55, 4.6, 4.95)
imagen(sl, "matrices_test.png", 5.35, 1.55, 4.3, 3.95)
texto(sl, 9.8, 1.6, 2.95, 3.9, [
    "**Los tres modelos no lineales** tienen curvas casi iguales (AUC de 0.892 a 0.901).",
    "**La regresión logística** queda debajo entre 0.2 y 0.5 de falsos positivos.",
    "**Los puntos** marcan el umbral elegido."], size=14.5, vineta=True, espacio=7)
texto(sl, 5.35, 5.6, 7.35, 1.0, ["**Matrices de confusión:** a los cuatro modelos se les escapan 13 o 14 casos; la ventaja de "
                                  "SVM y Random Forest está en las falsas alarmas (80 contra 118), no en detectar más casos."],
      size=15)

# =============================================================================================
# 17. Importancia
# =============================================================================================
sl = diapositiva("4.4 Análisis gráfico de resultados", "Variables más importantes en los tres tipos de modelo", notas=(
    "Tiempo sugerido: 1 minuto.\n"
    "Los tres modelos coinciden en las variables más importantes, que son la SHBG y el estradiol, en el primer y segundo lugar "
    "tanto en Random Forest como en XGBoost y con los coeficientes más grandes y negativos en la regresión logística, lo que "
    "significa que a menor SHBG y menor estradiol, mayor probabilidad de deficiencia. Después aparecen la cintura, el IMC y la "
    "edad, que coinciden con la literatura que relaciona la obesidad con la testosterona baja, y la escolaridad y la raza aportan "
    "muy poco. Una precaución importante es que la SHBG y el estradiol salen del mismo análisis de sangre que la testosterona, "
    "por lo que si ya se tiene ese panel lo práctico sería medir la testosterona directamente, lo que limita el uso de esta "
    "herramienta como tamizaje."))
imagen(sl, "importancia_variables.png", 0.6, 1.55, 12.1, 3.6)
texto(sl, 0.6, 5.2, 12.1, 1.45, [
    "**SHBG y estradiol** son las más importantes en los tres modelos: a menor valor, mayor probabilidad de deficiencia.",
    "**Cintura, IMC y edad** siguen en los modelos de árboles, de acuerdo con la relación entre obesidad y testosterona baja [4].",
    "**Precaución:** SHBG y estradiol salen del mismo análisis de sangre que la testosterona."],
      size=15.5, vineta=True, espacio=5)

# =============================================================================================
# 18. Estado del arte (tabla)
# =============================================================================================
sl = diapositiva("4.3 Comparación con el estado del arte", "Estudios previos frente a este proyecto",
                 fuentes="[4] a [10]; cifras tomadas de los artículos", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "Esta tabla reúne los trabajos que encontré y verifiqué, empezando por los que usan NHANES, como Yu, con seis modelos de "
    "aprendizaje automático y un mejor AUC de 0.746 con LightGBM, Zhang, Guo y Xu y Li, que evalúan índices individuales con "
    "curvas ROC y obtienen AUC entre 0.724 y 0.776, y Goulian, que usa el mismo ciclo 2021 a 2023 que yo pero con una regresión "
    "logística explicativa y sin métricas predictivas. Después aparecen dos trabajos con otros datos, Kivrak y Novaes, que "
    "comparan varios clasificadores y encuentran que XGBoost y los ensambles son los mejores, y al final está este proyecto, "
    "con AUC en prueba de 0.866 a 0.901, aunque como voy a explicar en la siguiente diapositiva esos números no son directamente "
    "comparables."))
cuerpo = [
    ["Yu et al., 2025 [5]", "NHANES 2011 a 2014; 2628 hombres; 25.8% con deficiencia", "SVM, LGBM, GBDT, CatBoost, XGBoost y RF; partición 80/20", "AUC",
     "LGBM 0.746 (mejor); RF 0.722; SVM 0.713; XGBoost 0.688"],
    ["Zhang et al., 2025 [6]", "NHANES 2013 a 2016; 1514 hombres", "8 índices simples, curva ROC por índice", "AUC", "TyG-WHtR 0.776 (IC 95%: 0.746 a 0.806)"],
    ["Guo et al., 2025 [7]", "NHANES 2011 a 2016; 3540 hombres", "15 índices de obesidad y lípidos, curva ROC", "AUC", "TyG-WHtR 0.762 (IC 95%: 0.743 a 0.782)"],
    ["Xu y Li, 2024 [8]", "NHANES 2013 a 2020; 5012 hombres; 25.7% con deficiencia", "Índice cardiometabólico, curva ROC", "AUC, sens., esp.",
     "AUC 0.724; sensibilidad 60.1% y especificidad 71.3%"],
    ["Goulian et al., 2026 [4]", "NHANES 2011 a 2016 y 2021 a 2023; 10357 hombres", "Regresión logística ponderada (explicativa)", "Odds ratio",
     "Sin métricas predictivas; obesidad OR 2.69"],
    ["Kivrak et al., 2024 [9]", "1886 pacientes con diabetes tipo 2; 5 predictoras", "7 clasificadores con y sin SMOTE; partición 70/30", "Sensib., F1",
     "XGBoost mejor en prueba; no reporta AUC"],
    ["Novaes et al., 2021 [10]", "3397 pacientes; 6 predictoras", "10 clasificadores base y 3 ensambles; prueba independiente", "PR-AUC, Brier",
     "Mejor ensamble: promedio ponderado; mejor base: XGBoost"],
    ["**Este proyecto**", "NHANES 2021 a 2023; 2514 hombres; 22.2% con deficiencia", "LR, SVM, RF y XGBoost; 80/20 y validación cruzada",
     "ROC AUC, recall", "ROC AUC en Test: SVM 0.901; XGBoost 0.898; RF 0.892; LR 0.866"]]
tabla(sl, 0.6, 1.45, [2.05, 3.0, 3.05, 1.2, 2.8], [["Estudio", "Base de datos", "Modelos o método", "Métrica", "Resultado"]] + cuerpo,
      size=12, alto_fila=0.5, resaltar_ultima=True, alto_encabezado=0.38)

# =============================================================================================
# 19. Estado del arte (comparabilidad)
# =============================================================================================
sl = diapositiva("4.3 Comparación con el estado del arte", "Qué tan comparables son estos resultados",
                 fuentes="[4] a [8]", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "El ROC AUC de este trabajo, de 0.866 a 0.901, es mayor que el de Yu, de 0.688 a 0.746, y que el de los índices, de 0.724 a "
    "0.776, pero no concluyo que mis modelos sean mejores, porque utilizar la misma base de datos no garantiza que los "
    "experimentos sean equivalentes. Cambian el ciclo de la encuesta y la población, cambian las variables, ya que ellos usan "
    "índices antropométricos y metabólicos y yo agrego SHBG, estradiol, LH y FSH, que pertenecen al mismo eje hormonal que la "
    "testosterona y que probablemente explican buena parte de la diferencia, cambia el protocolo, porque los índices se evalúan "
    "con curvas ROC sin entrenar clasificadores, y cambian las métricas, de las que solo el AUC es común. Además Yu reporta un "
    "recall de 1.000 en los seis modelos, un valor difícil de interpretar que por eso no uso para comparar, y mi conjunto de "
    "prueba tiene solo 112 casos positivos, lo que agrega incertidumbre."))
texto(sl, 0.6, 1.6, 7.0, 0.4, "Diferencias que limitan la comparación", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.6, 2.1, 7.0, 4.5, [
    "**Población y ciclo:** los demás usan NHANES 2011 a 2020; solo [4] incluye 2021 a 2023 y no entrena modelos predictivos.",
    "**Variables:** [6] a [8] evalúan índices antropométricos y metabólicos; aquí se agregan SHBG, estradiol, LH y FSH.",
    "**Protocolo:** los índices se evalúan con curvas ROC sin entrenar clasificadores; [5] usa partición 80/20; aquí hay validación cruzada y una prueba única.",
    "**Métricas:** solo el AUC es común. [5] reporta recall de 1.000 en los seis modelos, un valor difícil de interpretar, por lo que no se compara."],
      size=16, vineta=True, espacio=9)
rect(sl, 7.9, 1.6, 4.8, 3.0)
texto(sl, 8.1, 1.68, 4.4, 0.4, "Lectura prudente", size=19, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 8.1, 2.15, 4.4, 2.4, "El ROC AUC de este trabajo (0.866 a 0.901) es mayor que el de [5] (0.688 a 0.746) y el de los índices "
      "(0.724 a 0.776), pero **no se concluye que los modelos sean mejores:** cambian la población, las variables y el protocolo.",
      size=15)
rect(sl, 7.9, 4.8, 4.8, 1.8)
texto(sl, 8.1, 4.86, 4.4, 0.4, "Lo que distingue a este trabajo", size=17, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 8.1, 5.3, 4.4, 1.3, ["Ciclo 2021 a 2023", "Cuatro modelos con el mismo protocolo", "Umbral que prioriza detectar casos"],
      size=14, vineta=True, espacio=2)

# =============================================================================================
# 20. Interfaz
# =============================================================================================
sl = diapositiva("Aplicación", "Interfaz en Streamlit con los tres mejores modelos", fuentes="[1]; app y repositorio públicos", notas=(
    "Tiempo sugerido: 2 minutos.\n"
    "La aplicación ya está publicada en Streamlit Community Cloud y cualquiera puede abrirla desde su navegador sin instalar nada. "
    "Integra los tres modelos con mejor ROC AUC en validación cruzada, que son XGBoost, Random Forest y SVM, y la regresión "
    "logística quedó fuera por ser la más débil. El usuario captura las trece variables, que se validan antes de enviarse a los "
    "modelos, y la aplicación muestra la probabilidad, la clase predicha y el umbral de cada modelo, además de en qué casos "
    "difieren, y en otra pestaña se ven las métricas de Test que salen de los experimentos y no se recalculan. Para comprobar que "
    "los resultados corresponden a los modelos entrenados, comparé las predicciones de la aplicación con las de Python con los "
    "mismos datos en cuatro perfiles y tres modelos, y coincidieron los doce casos.\n"
    "Aquí conviene hacer la demostración en vivo con el perfil por defecto y con uno de riesgo alto."))
captura = FIG / "captura_app.png"
if captura.exists():
    imagen(sl, "captura_app.png", 0.6, 1.55, 5.6, 5.0)
else:
    # Sin captura de pantalla: tarjeta de demostracion en vivo (se reemplaza sola al guardar presentacion/figuras/captura_app.png)
    rect(sl, 0.6, 1.6, 5.6, 4.9)
    texto(sl, 0.85, 1.85, 5.1, 0.9, "Demostración en vivo", size=30, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
    texto(sl, 0.85, 2.9, 5.1, 3.4, ["Perfil por defecto: ningún modelo marca alerta (XGBoost 5%, Random Forest 1%, SVM 9%)",
                                     "Perfil de riesgo alto: los tres marcan alerta (94%, 96% y 97%)",
                                     "Perfil con IMC y cintura vacíos: los modelos discrepan (XGBoost marca alerta; Random Forest y SVM no)"],
          size=16, vineta=True, espacio=9)
texto(sl, 6.5, 1.6, 6.2, 3.3, [
    "**Tres modelos** elegidos por ROC AUC en validación: XGBoost, Random Forest y SVM",
    "**Entrada validada** de las 13 variables, con las mismas transformaciones del entrenamiento",
    "**Resultado:** probabilidad, clase predicha, umbral y diferencias entre modelos",
    "**Desempeño en Test** con tabla y gráfica, tomado de los experimentos",
    "**Prueba:** aplicación contra Python con los mismos datos, 12 de 12 casos coinciden"], size=16, vineta=True, espacio=6)
rect(sl, 6.5, 5.1, 6.2, 1.45)
texto(sl, 6.7, 5.15, 5.8, 0.35, "Aplicación desplegada", size=15, color=TEAL, negrita=True, revisar=False)
texto(sl, 6.7, 5.5, 5.8, 0.4, URL_APP, size=15, revisar=False)
texto(sl, 6.7, 5.9, 5.8, 0.3, "Código y reporte", size=15, color=TEAL, negrita=True, revisar=False)
texto(sl, 6.7, 6.2, 5.8, 0.35, URL_REPO, size=13, revisar=False)

# =============================================================================================
# 21. Conclusiones
# =============================================================================================
sl = diapositiva("5. Conclusiones", "Conclusiones", notas=(
    "Tiempo sugerido: 1 minuto y 30 segundos.\n"
    "El objetivo se cumplió, porque se entrenaron cuatro modelos con el mismo protocolo, se evaluaron una sola vez en Test y se "
    "publicaron en una aplicación. El SVM obtuvo el mejor resultado en Test, con un ROC AUC de 0.901 y un F1 de 0.680, pero XGBoost y "
    "Random Forest quedaron a menos de 0.01, una diferencia menor que la desviación entre folds, por lo que no puedo decir que uno "
    "sea claramente mejor que los otros dos, mientras que la regresión logística fue la más débil, sobre todo en precisión. Los "
    "modelos no lineales mejoran solo un poco al lineal, lo que sugiere que la relación entre las variables y la deficiencia es "
    "suave y en buena parte lineal, y el hallazgo más claro es que el umbral de decisión cambia más el resultado que la "
    "optimización."))
rect(sl, 0.6, 1.6, 12.1, 4.95)
texto(sl, 0.85, 1.75, 11.6, 4.7, [
    "**Objetivo cumplido:** cuatro modelos con el mismo protocolo, evaluados una sola vez en Test y publicados en una aplicación.",
    "**Mejor desempeño:** SVM (ROC AUC 0.901, F1 0.680), pero SVM, XGBoost y Random Forest quedan empatados (diferencia menor a 0.01, menor que la desviación entre folds).",
    "**Hallazgos:** el umbral cambia más el resultado que la optimización; los modelos no lineales mejoran poco a la Regresión Logística; SHBG y estradiol pesan más.",
    "**Frente a los trabajos previos:** el ROC AUC es mayor que el de los estudios con NHANES, sin afirmar que sea mejor por las diferencias de población, variables y protocolo.",
    "**Uso:** apoyo para decidir a quién pedirle el análisis de sangre, no un diagnóstico."],
      size=19.5, vineta=True, espacio=13)

# =============================================================================================
# 22. Limitaciones y trabajo futuro
# =============================================================================================
sl = diapositiva("5. Conclusiones", "Limitaciones y trabajo futuro", notas=(
    "Tiempo sugerido: 1 minuto.\n"
    "La limitación principal es que con un recall cercano a 0.88 la precisión queda entre 45% y 55%, es decir que casi la mitad de "
    "las alertas serían falsas alarmas, lo que es aceptable para una herramienta de apoyo pero no para un diagnóstico, y además "
    "el conjunto de prueba tiene solo 112 casos positivos, por lo que todas las métricas tienen incertidumbre. Otra limitación es "
    "que las hormonas que más pesan salen del mismo análisis de sangre que la testosterona, que la deficiencia se definió con una "
    "sola medición cuando las guías piden dos, y que los modelos se entrenaron solo con hombres de Estados Unidos. Como trabajo "
    "futuro, lo más valioso sería validar en otros ciclos de NHANES o en una cohorte externa y probar los modelos sin las "
    "hormonas, que es el escenario realista de tamizaje."))
rect(sl, 0.6, 1.6, 5.95, 4.95)
texto(sl, 0.8, 1.7, 5.55, 0.4, "Limitaciones", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.8, 2.2, 5.55, 4.3, [
    "**Precisión de 45% a 55%:** casi la mitad de las alertas son falsas alarmas.",
    "**Test con 112 casos positivos:** las métricas tienen incertidumbre.",
    "**Hormonas del mismo análisis:** SHBG, estradiol, LH y FSH salen del mismo análisis de sangre que la testosterona.",
    "**Una sola medición** de testosterona y solo hombres de Estados Unidos."], size=18, vineta=True, espacio=11)
rect(sl, 6.75, 1.6, 5.95, 4.95)
texto(sl, 6.95, 1.7, 5.55, 0.4, "Trabajo futuro", size=20, color=TEAL, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 7.0, 2.2, 5.55, 4.3, [
    "Validar en otros ciclos de NHANES o en una cohorte externa",
    "Probar modelos sin las hormonas, el escenario realista de tamizaje",
    "Estimar intervalos de confianza con bootstrap",
    "Reentrenar con todos los datos antes de un uso real",
    "Explorar ensambles de los modelos"], size=18, vineta=True, espacio=11)

# =============================================================================================
# 23 y 24. Referencias
# =============================================================================================
REFS = [
    "[1] Centers for Disease Control and Prevention, National Center for Health Statistics, \"National Health and Nutrition Examination Survey (NHANES), 2021 to 2023 cycle.\" [Online]. Available: https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?Cycle=2021-2023",
    "[2] J. P. Mulhall et al., \"Evaluation and management of testosterone deficiency: AUA guideline,\" J. Urol., vol. 200, no. 2, pp. 423 to 432, 2018, doi: 10.1016/j.juro.2018.03.115.",
    "[3] S. Bhasin et al., \"Testosterone therapy in men with hypogonadism: An Endocrine Society clinical practice guideline,\" J. Clin. Endocrinol. Metab., vol. 103, no. 5, pp. 1715 to 1744, 2018, doi: 10.1210/jc.2018-00229.",
    "[4] A. J. Goulian, A. Ashkezari, and S. V. Eleswarapu, \"Unmasking masculinity: Biological, behavioral, and social determinants of testosterone deficiency in U.S. men, 2011 to 2023,\" Am. J. Men's Health, vol. 20, 2026, Art. no. 15579883261433808, doi: 10.1177/15579883261433808.",
    "[5] L. Yu, S. Cao, B. Song, and Y. Hu, \"Predictive role of the muscle quality index for testosterone deficiency in adult males based on interpretable machine learning methods,\" BMC Public Health, vol. 25, Art. no. 2934, 2025, doi: 10.1186/s12889-025-24212-y.",
    "[6] B. Zhang, Y. Gu, Y. Li, and X. Feng, \"Prediction of testosterone deficiency using different screening indexes in adult American men: An NHANES cross-sectional study,\" PLoS ONE, vol. 20, no. 6, Art. no. e0323900, 2025, doi: 10.1371/journal.pone.0323900.",
    "[7] W. Guo, S. Zhao, Q. Chang, J. Sun, Y. Fan, and J. Liu, \"Negative association between 15 obesity- and lipid-related indices and testosterone in adult males: A population based cross-sectional study,\" Lipids Health Dis., vol. 24, Art. no. 24, 2025, doi: 10.1186/s12944-025-02436-6."]
REFS2 = [
    "[8] J. Xu and Y.-C. Li, \"Negative correlation between cardiometabolic index and testosterone in male adults,\" Front. Endocrinol., vol. 15, 2024, doi: 10.3389/fendo.2024.1447230.",
    "[9] M. Kivrak, U. Avci, H. Uzun, and C. Ardic, \"The impact of the SMOTE method on machine learning and ensemble learning performance results in addressing class imbalance in data used for predicting total testosterone deficiency in type 2 diabetes patients,\" Diagnostics, vol. 14, no. 23, Art. no. 2634, 2024, doi: 10.3390/diagnostics14232634.",
    "[10] M. T. Novaes et al., \"Prediction of secondary testosterone deficiency using machine learning: A comparative analysis of ensemble and base classifiers, probability calibration, and sampling strategies in a slightly imbalanced dataset,\" Inform. Med. Unlocked, vol. 23, Art. no. 100538, 2021, doi: 10.1016/j.imu.2021.100538.",
    "[11] F. Pedregosa et al., \"Scikit-learn: Machine learning in Python,\" J. Mach. Learn. Res., vol. 12, pp. 2825 to 2830, 2011.",
    "[12] L. Breiman, \"Random forests,\" Mach. Learn., vol. 45, no. 1, pp. 5 to 32, 2001, doi: 10.1023/A:1010933404324.",
    "[13] T. Chen and C. Guestrin, \"XGBoost: A scalable tree boosting system,\" in Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discov. Data Mining, 2016, pp. 785 to 794, doi: 10.1145/2939672.2939785.",
    "[14] C. Cortes and V. Vapnik, \"Support-vector networks,\" Mach. Learn., vol. 20, no. 3, pp. 273 to 297, 1995, doi: 10.1007/BF00994018."]
import re
REFS = [re.sub(r"(pp\. \d+) to (\d+)", r"\1-\2", r) for r in REFS]
REFS2 = [re.sub(r"(pp\. \d+) to (\d+)", r"\1-\2", r) for r in REFS2]
for lista, parte in ((REFS, "1 de 2"), (REFS2, "2 de 2")):
    sl = diapositiva("6. Referencias", f"Referencias ({parte})", notas="Tiempo sugerido: no se presenta, queda como respaldo para las preguntas.")
    texto(sl, 0.6, 1.5, 12.1, 5.2, lista, size=14, espacio=9)

# =============================================================================================
# 25. Preguntas
# =============================================================================================
sl = prs.slides.add_slide(BLANK)
rect(sl, 0, 0, 13.333, 7.5, relleno=TEAL, redondo=False)
texto(sl, 0.9, 2.2, 11.5, 1.2, "Gracias", size=54, color=WHITE, fuente="Cambria", negrita=True, revisar=False)
texto(sl, 0.9, 3.5, 11.5, 0.8, "Preguntas", size=30, color=RGBColor(0xE8, 0xF1, 0xF5), revisar=False)
texto(sl, 0.9, 5.0, 11.5, 1.3, [f"Aplicación: {URL_APP}", f"Repositorio: {URL_REPO}", "Jesús Pascual Garay Ordaz  |  Matrícula 306025"],
      size=17, color=WHITE, espacio=4, revisar=False)
sl.notes_slide.notes_text_frame.text = (
    "Tiempo sugerido: 2 minutos para preguntas o más.\n"
    "Preguntas probables y respuestas cortas.\n"
    "1. ¿No es trampa usar SHBG, LH, FSH y estradiol? No es fuga técnica, porque no son la testosterona, pero vienen del mismo análisis "
    "de sangre, así que en la práctica quien ya tiene ese panel mide la testosterona directo, y esa es la principal limitación como tamizaje.\n"
    "2. ¿La mejora del RBF sobre el lineal es significativa? En ROC AUC es pequeña, menor que la desviación entre folds, y la mejora "
    "práctica grande viene del peso de clase y del umbral, no del kernel.\n"
    "3. ¿Por qué ROC AUC para elegir y F2 para el umbral? El AUC no depende del umbral y sirve con desbalance, y el F2 da más peso al "
    "recall porque dejar escapar un caso cuesta más que una falsa alarma.\n"
    "4. ¿Por qué no SMOTE? Con 22% de positivos el peso de clase fue suficiente y evita generar datos sintéticos.\n"
    "5. ¿Cómo sé que no hay fuga? La partición va antes de ajustar nada, todo el preprocesamiento vive en el Pipeline por fold, el "
    "umbral sale de predicciones fuera de muestra y Test se evalúa una sola vez.\n"
    "6. ¿Mejoran al estado del arte? No lo afirmo, porque cambian población, variables, protocolo y métricas.")

assert len(prs.slides) == TOTAL, f"hay {len(prs.slides)} diapositivas y TOTAL vale {TOTAL}"
prs.save(SALIDA)
print("Guardada:", SALIDA, f"({len(prs.slides)} diapositivas)")

# Revision de textos que podrian no caber
problemas = [(n, d, round(a, 2), disp) for n, d, a, disp in REVISION if disp is not None and a > disp * 1.0]
print("\nPosibles desbordes de texto (alto estimado > alto de la caja):" if problemas else "\nSin desbordes de texto detectados.")
for n, d, a, disp in problemas:
    print(f"  diapositiva {n}: '{d}' necesita ~{a} in y hay {disp} in")
for n, d, a, disp in REVISION:
    if d == "tabla":
        print(f"  tabla de la diapositiva {n}: alto estimado {a:.2f} in")
