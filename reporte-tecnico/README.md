# Reporte técnico (LaTeX)

Borrador completo del reporte técnico del proyecto final, escrito para compilarse en Overleaf.

## Archivos

| Archivo | Descripción |
|---|---|
| `main.tex` | Documento principal |
| `referencias.bib` | 20 referencias, todas citadas en el texto |
| `figuras/` | Imágenes que usa el reporte: las gráficas se generaron a partir de `../entrenamiento-modelos.ipynb` y la captura de la interfaz con la app corriendo |

## Cómo compilarlo en Overleaf

1. En Overleaf, crear un proyecto nuevo con **Upload Project** y subir esta carpeta comprimida en `.zip`, o crear un proyecto en blanco y subir `main.tex`, `referencias.bib` y la carpeta `figuras/`.
2. Verificar que el compilador sea **pdfLaTeX** (el predeterminado) y que el documento principal sea `main.tex`.
3. Compilar. Las referencias requieren que BibTeX corra, lo que Overleaf hace de forma automática.

El documento usa solo paquetes que vienen en Overleaf: `babel` (español), `natbib`, `booktabs`, `graphicx`, `float`, `caption`, `amsmath` y `hyperref`.

## Estructura

La estructura sigue lo anotado en el pizarrón:

1. **Resumen**
2. **Antecedentes**: la deficiencia de testosterona, trabajos relacionados (6 artículos) y objetivos.
3. **Metodología**
   - Base de datos
   - Modelos
   - Implementación (preprocesamiento e imputación, validación y optimización, umbral, interfaz y herramientas)
   - Resultados
4. **Conclusiones**
5. **Referencias** (mínimo 15, el reporte cita 20)

## Estado

El reporte **no se ha compilado**: no había un compilador de LaTeX en el equipo donde se escribió. Antes de entregarlo hay que compilarlo en Overleaf y revisar si aparece algún error o advertencia. Se verificó con un revisor de sintaxis propio que los entornos y las llaves están balanceados, que las 20 citas coinciden con las entradas del `.bib`, que todas las referencias cruzadas existen, que las figuras existen y que cada fila de las tablas tiene el número correcto de columnas, pero eso no sustituye a una compilación real.

## Pendiente

- **Datos verificados en línea el 1 de noviembre de 2026:**
  - Chen y Guestrin (2016), Cortes y Vapnik (1995) y Bhasin et al. (2018): autores, publicación, volumen, páginas y DOI coinciden con Crossref.
  - Breiman (2001): título, revista, volumen, número, páginas y DOI coinciden en varias fuentes (Crossref no respondió por límite de consultas).
  - Las unidades de las variables de la Tabla 2 (nmol/L, pg/mL, mIU/mL) coinciden con el diccionario de NHANES (archivo TST\_L).
  - La guía de la AUA usa 300 ng/dL como corte y pide dos mediciones matutinas y síntomas; la de la Endocrine Society pide síntomas y una testosterona baja de forma consistente, y no recomienda tamizaje de rutina en la población general. El reporte lo menciona.
- **Sin verificar:** los detalles de los seis artículos de la literatura (Yu, Zhang, Kivrak, Goulian, Novaes y Tong) se tomaron de las notas de F_2 y de la propuesta, donde se habían leído del texto de cada artículo, y no se volvieron a consultar.
- **Fecha de entrega, formato y extensión.** No se sabe si la docente pidió un número de páginas o una plantilla.
- **Fecha en la portada.** Dice «Noviembre de 2026», conviene ajustarla al día de entrega.
