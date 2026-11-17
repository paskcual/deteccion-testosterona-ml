# Proyecto final: detección de posible deficiencia de testosterona

Proyecto final de Machine Learning (MIC, docente Olanda Prieto Ordaz). Entrena cuatro modelos (Regresión Logística, SVM, Random Forest y XGBoost) con la base NHANES 2021 a 2023 de hormonas sexuales masculinas. Los **tres con mejor ROC AUC en validación cruzada** (XGBoost, Random Forest y SVM) se integran en una aplicación web en Streamlit que recibe los datos de un paciente y devuelve la predicción de cada modelo. La Regresión Logística, que quedó cuarta, se conserva en el entrenamiento y en el reporte pero no está en la aplicación.

**Aplicación desplegada:** https://deteccion-testosterona-ml.streamlit.app/

Si al abrirla aparece un mensaje de que la app se durmió por inactividad, basta con pulsar el botón para despertarla (Streamlit Community Cloud duerme las apps tras 12 horas sin visitas) y espera un par de minutos mientras arranca.

Continúa los proyectos F_1 (regresión logística) y F_2 (SVM) de la misma materia, con el mismo dataset, la misma partición y el mismo preprocesamiento.

## Contenido de la carpeta

| Archivo | Descripción |
|---|---|
| `entrenamiento-modelos.ipynb` | Notebook ejecutado: entrena, optimiza, evalúa y guarda los cuatro modelos |
| `app.py` | Aplicación web en Streamlit (información del proyecto, predicción y desempeño de los tres mejores modelos) |
| `prueba_app_vs_python.py` | Prueba que compara las predicciones de la aplicación contra las de Python directo con los mismos datos |
| `modelos/` | Los cuatro modelos entrenados (`.joblib`) y `metadatos.json` con umbrales, métricas e información de las variables |
| `nhanes_testosterona_2021_2023.csv` | Dataset (copia del usado en F_1 y F_2) |
| `requirements.txt` | Dependencias de la aplicación, con las versiones con las que se entrenó y probó |
| `requirements-entrenamiento.txt` | Lo anterior más lo necesario para volver a ejecutar el notebook de entrenamiento |
| `reporte-tecnico/` | Reporte técnico en LaTeX (`main.tex`, `referencias.bib` y figuras), con su propio README |

## Problema y datos

- **Fuente:** NHANES 2021 a 2023 del CDC, 2514 hombres de 20 años o más con la testosterona medida.
- **Objetivo:** `deficiencia_testosterona`, que vale 1 cuando la testosterona total es menor a 300 ng/dL (criterio de la AUA). Clasificación binaria con 22.2% de positivos.
- **13 predictoras** (la docente confirmó que con 13 es suficiente):
  - Numéricas (8): edad, IMC, cintura, SHBG, estradiol, LH, FSH y tragos por día.
  - Categóricas (5): diabetes, hipertensión, tabaquismo, raza y escolaridad.
- **No son predictoras:** el identificador, la testosterona total (con ella se calcula el objetivo, sería fuga de información) y el propio objetivo.

## Procedimiento de entrenamiento

Es el mismo para los cuatro modelos y repite el de F_1 y F_2:

1. Partición 80/20 estratificada con `random_state=42` (2011 hombres en Train y 503 en Test).
2. Los códigos de "rehuso" y "no sabe" (7, 9, 777 y 999) pasan a faltante, y los códigos de las categóricas se cambian por su significado.
3. Pipeline: numéricas con imputación por mediana y `StandardScaler`, categóricas con imputación por moda y `OneHotEncoder`, y el modelo. Todo se ajusta solo con los datos de entrenamiento de cada fold.
4. Búsqueda de hiperparámetros con `GridSearchCV`, validación cruzada estratificada de 5 folds sobre Train, maximizando ROC AUC.
5. Probabilidades fuera de muestra (OOF) y umbral de decisión que maximiza F2 (da más peso al recall), fijo desde ese momento.
6. Evaluación en Test una sola vez. Los modelos guardados están entrenados solo con Train para que las métricas sigan siendo válidas.

| Modelo | Rejilla | Mejor combinación |
|---|---|---|
| Regresión Logística | `C` [0.01 a 100], `l1_ratio` [0, 1], `class_weight` (20 combinaciones) | `C=0.1`, L1, `balanced` |
| SVM RBF | `C` [0.01 a 100], `gamma` [scale, 0.001 a 10], `class_weight` (60) | `C=10`, `gamma=0.01`, `balanced` |
| Random Forest (300 árboles) | `max_depth`, `min_samples_leaf`, `max_features`, `class_weight` (48) | sin límite de profundidad, `min_samples_leaf=3`, `max_features=0.5`, `balanced` |
| XGBoost | `n_estimators`, `learning_rate`, `max_depth`, `subsample`, `colsample_bytree`, `scale_pos_weight` (96) | 300 árboles, `learning_rate=0.03`, `max_depth=2`, `subsample=0.7`, `colsample_bytree=0.7`, sin ponderar |

La Regresión Logística usa `l1_ratio` en lugar de `penalty` (obsoleto desde scikit-learn 1.8): `l1_ratio=0` equivale a L2 y `l1_ratio=1` a L1. El SVM se envuelve en `CalibratedClassifierCV` (sigmoide, 5 folds) para entregar probabilidades, que es lo que recomienda scikit-learn en lugar de `probability=True`.

## Resultados

ROC AUC en validación cruzada (5 folds, Train): XGBoost 0.896, Random Forest 0.894, SVM 0.884, Regresión Logística 0.868.

Evaluación en Test (503 hombres, 112 con deficiencia), con el umbral de cada modelo:

| Modelo | Umbral | ROC AUC | Recall | Precisión | F1 | TN | FP | FN | TP |
|---|---|---|---|---|---|---|---|---|---|
| Regresión Logística | 0.45 | 0.866 | 0.875 | 0.454 | 0.598 | 273 | 118 | 14 | 98 |
| SVM | 0.22 | 0.901 | 0.884 | 0.553 | 0.680 | 311 | 80 | 13 | 99 |
| Random Forest | 0.35 | 0.892 | 0.875 | 0.551 | 0.676 | 311 | 80 | 14 | 98 |
| XGBoost | 0.16 | 0.898 | 0.884 | 0.505 | 0.643 | 294 | 97 | 13 | 99 |

Los resultados de la Regresión Logística y del SVM coinciden con los de F_1 y F_2, lo que confirma que la partición, el preprocesamiento y la semilla son los mismos.

**Hallazgos principales**

- SVM, XGBoost y Random Forest quedan prácticamente empatados (menos de 0.01 de ROC AUC de diferencia, menor que la desviación entre folds). La Regresión Logística es la más débil, sobre todo en precisión.
- El umbral de decisión es lo que hace útiles a los modelos: con el umbral de 0.5 el recall en Test cae a entre 0.47 y 0.80, y con el umbral elegido sube a 0.875 o 0.884.
- Con ese recall la precisión queda entre 45% y 55%, es decir que casi la mitad de las alertas son falsas alarmas. Es aceptable como apoyo para decidir a quién pedirle un análisis de sangre y no como diagnóstico ni como tamizaje de la población general, que la guía de la Endocrine Society no recomienda.
- SHBG y estradiol son las variables más importantes en los tres tipos de modelo, seguidas de cintura, IMC y edad.

## Aplicación web (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador (por defecto en `http://localhost:8501`) y tiene tres pestañas:

- **Información del proyecto:** nombre, alumno y matrícula, programa, materia, asesora, descripción del problema, objetivo de la aplicación, base de datos y los tres modelos (principio de funcionamiento, ROC AUC en validación, umbral e hiperparámetros seleccionados).
- **Predicción:** pide las 13 variables, con rangos y valores iniciales tomados de Train (`modelos/metadatos.json`), y valida los datos antes de enviarlos a los modelos. Permite dejar vacíos IMC, cintura, estradiol y tragos por día (las variables con faltantes en los datos): el Pipeline los reemplaza por la mediana de Train. Muestra la probabilidad, la clase predicha y el umbral de cada modelo, las diferencias entre ellos, una gráfica y una explicación de cómo leer el resultado y sus limitaciones.
- **Desempeño de los modelos:** métricas de los tres modelos en el conjunto de prueba (tabla, gráfica de barras y matrices de confusión), tomadas de los experimentos y no recalculadas.

Los tres modelos se eligen en `app.py` ordenando los cuatro por `roc_auc_cv` (validación cruzada), por lo que el conjunto de prueba no interviene en la selección. Es un proyecto académico, no un dispositivo médico: un resultado positivo solo sugiere confirmar con un análisis de sangre.

### Prueba: aplicación contra Python directo

```bash
python prueba_app_vs_python.py
```

Corre la aplicación con `streamlit.testing` y, con los mismos datos, carga los `.joblib` en Python y llama a `predict_proba`. Se probaron cuatro perfiles (valores por defecto, riesgo alto, riesgo bajo y uno con IMC y cintura vacíos) con los tres modelos. En los 12 casos la probabilidad y la clase coinciden (tolerancia de 0.01 puntos porcentuales por el redondeo de la tabla). Además se levantó el servidor real (`streamlit run`) y respondió sin errores.

| Perfil | XGBoost | Random Forest | SVM |
|---|---|---|---|
| Valores por defecto | 4.95% | 0.94% | 8.88% |
| Riesgo alto | 94.31% | 95.90% | 97.01% |
| Riesgo bajo | 1.04% | 0.18% | 0.24% |
| IMC y cintura vacíos | 16.77% (alerta) | 27.36% | 15.79% |

## Despliegue en Streamlit Community Cloud

La aplicación está desplegada en https://deteccion-testosterona-ml.streamlit.app/ (repositorio `paskcual/deteccion-testosterona-ml`, rama `main`, archivo principal `app.py`). Los pasos para reproducir el despliegue son:

La aplicación se publica desde un repositorio de **GitHub** (Streamlit Community Cloud no se conecta a GitLab). El repositorio puede ser esta carpeta tal cual, con `app.py` y `requirements.txt` en la raíz.

1. Crear el repositorio en GitHub y subir el contenido de esta carpeta (sin credenciales; el dataset NHANES es público).
2. Entrar a [share.streamlit.io](https://share.streamlit.io) con la cuenta de GitHub y elegir **Create app**.
3. Seleccionar el repositorio y la rama, poner `app.py` como archivo principal y, en configuración avanzada, elegir **Python 3.12** (la versión con la que se probó).
4. Desplegar, abrir la URL pública y repetir la prueba con un perfil de ejemplo: los tres modelos deben dar las probabilidades de la tabla anterior.

Los `.joblib` solo cargan con las mismas versiones de scikit-learn y XGBoost con las que se guardaron, por eso `requirements.txt` las fija. Si el despliegue falla al cargar un modelo, hay que revisar primero que se haya instalado `scikit-learn==1.9.1` y `xgboost==3.4.1`.

## Cómo volver a entrenar

Desde esta carpeta, para que encuentre el CSV:

```bash
pip install -r requirements-entrenamiento.txt
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=3000 entrenamiento-modelos.ipynb
```

Todo usa `random_state=42`, por lo que al repetir el entrenamiento con las mismas versiones se obtienen las mismas cifras.

## Limitaciones

- La partición es única (80/20): con solo 112 positivos en Test, las diferencias pequeñas entre modelos no son concluyentes.
- Los modelos se entrenaron solo con Train para conservar válido Test. Una versión final podría reentrenarse con todos los datos.
- Los umbrales se eligieron con las predicciones de Train; sobre una población con otra prevalencia de deficiencia, la precisión sería distinta.
- Las probabilidades no son un riesgo clínico exacto, solo sirven para ordenar y comparar casos.
