# Reporte técnico (LaTeX, formato IEEE)

Reporte técnico del proyecto final en formato de artículo IEEE (`IEEEtran`, modo conferencia), escrito para compilarse en Overleaf.

## Archivos

| Archivo | Descripción |
|---|---|
| `main.tex` | Documento principal |
| `referencias.bib` | 17 referencias en BibTeX, todas citadas en el texto (estilo `IEEEtran`) |
| `figuras/` | Imágenes que usa el reporte |
| `reporte-tecnico.pdf` | PDF compilado |
| `generar_figuras_reporte.py` | Genera `curvas_roc.png`, `curvas_pr.png` y `diagrama_metodologia.png` a partir de los modelos guardados (misma partición y semilla 42) |

## Cómo compilarlo en Overleaf

1. Crear un proyecto con **Upload Project** y subir esta carpeta comprimida en `.zip`.
2. Compilador **pdfLaTeX** y documento principal `main.tex`. BibTeX corre de forma automática.
3. En `main.tex`, cambiar el correo en la línea `\newcommand{\correo}{...}`.
4. Revisar que el contenido principal (sin referencias) tenga entre 8 y 12 páginas.

## Estructura (según la rúbrica de la materia)

1. Título, autor, resumen (239 palabras) y palabras clave
2. Introducción
3. Antecedentes y trabajos relacionados
4. Metodología: base de datos, análisis exploratorio y preprocesamiento, modelos, configuración experimental (con diagrama)
5. Resultados y discusión: modelos base, optimizados, comparación con el estado del arte (5 estudios con NHANES), análisis gráfico (ROC, precisión-recall, matrices de confusión, importancia) y discusión
6. Conclusiones
7. Referencias

## Estado

Compilado con Tectonic 0.17.0 (9 páginas en total, de las cuales las referencias ocupan algo más de media página, así que el contenido principal queda en unas 8.3 páginas). El PDF compilado es `reporte-tecnico.pdf`. Conviene compilarlo también en Overleaf como respaldo y revisar que se vea igual.
