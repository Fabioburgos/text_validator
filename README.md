# 📚 Validador de Sesgos y Calidad de Texto v1.0

**Auditoría Automática con Google Gemini via Vertex AI**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.50+-red.svg)](https://streamlit.io)

---

## 🎯 ¿Qué hace este validador?

Herramienta especializada para analizar documentos PDF y detectar automáticamente:

### 🔴 Sesgos
- **Género:** Lenguaje no inclusivo, estereotipos
- **Religión:** Proselitismo, favoritismo religioso
- **Política:** Lenguaje tendencioso, propaganda

### 🔵 Calidad Lingüística
- **Ortografía:** Acentuación, mayúsculas, puntuación
- **Gramática:** Concordancia, sintaxis, tiempos verbales
- **Semántica:** Uso inadecuado, ambigüedades, redundancias

---

## ✨ Características Principales

- ✅ **Análisis directo de PDF** sin extracción manual de texto
- ✅ **Detección automática de idioma** (Español/Inglés)
- ✅ **OCR integrado** para PDFs escaneados
- ✅ **Batch processing** eficiente (múltiples páginas en un request)
- ✅ **Respuestas estructuradas** en JSON con schema definido
- ✅ **Interfaz amigable** para usuarios no técnicos
- ✅ **Exportación múltiple** (Markdown, CSV)
- ✅ **Infraestructura empresarial** Google Cloud Platform

---

## 🚀 Inicio Rápido

### 1. Requisitos Previos

- Python 3.12 o superior
- Proyecto de Google Cloud Platform
- API de Vertex AI habilitada
- Credenciales de GCP configuradas

### 2. Instalación

```bash
# Clonar el repositorio
git clone https://github.com/tu-org/text-validator.git
cd text_validator

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración

#### Opción A: Variables de Entorno

Crea un archivo `.env`:

```env
GCP_PROJECT_ID=tu-proyecto-id
GCP_LOCATION=us-east1
GEMINI_MODEL=gemini-2.5-flash-lite
SCOPE=development
```

#### Opción B: Credenciales de GCP

```bash
# Autenticación con Application Default Credentials
gcloud auth application-default login

# O usar Service Account (producción)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### 4. Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en http://localhost:8501

---

## 📖 Guía de Uso

### Paso 1: Cargar Documento
1. Ve a la pestaña **"📤 Cargar Documento"**
2. Arrastra tu PDF o haz clic para seleccionarlo
3. El sistema acepta PDFs estándar y escaneados

### Paso 2: Configurar Análisis
1. Selecciona la **página inicial** (primera página a analizar)
2. Selecciona la **página final** (última página a analizar)
3. Revisa el tiempo estimado de análisis (~3 seg/página)

### Paso 3: Iniciar Análisis
1. Haz clic en **"🚀 Iniciar Análisis"**
2. Observa la barra de progreso en tiempo real
3. Espera la confirmación de análisis completado

### Paso 4: Ver Resultados
1. Ve a la pestaña **"📊 Ver Resultados"**
2. Revisa el resumen estadístico
3. Examina la tabla detallada de hallazgos
4. Descarga los resultados en Markdown o CSV

---

## 📊 Formato de Resultados

### Tabla de Hallazgos

Cada hallazgo incluye:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **categoria** | Tipo de problema | `sesgo_genero`, `ortografia` |
| **prioridad** | Nivel de severidad | `Alta`, `Media`, `Baja` |
| **pagina_pdf** | Número de página en el PDF | `57` |
| **pagina_libro** | Número de página impresa | `57` (o diferente si existe) |
| **fragmento_original** | Texto problemático (≤10 palabras) | `"los alumnos deben"` |
| **recomendacion** | Sugerencia accionable (≤60 palabras) | `"Considerar lenguaje inclusivo..."` |

### Ejemplo de Salida

```markdown
| categoria | prioridad | pagina_pdf | pagina_libro | fragmento_original | recomendacion |
|-----------|-----------|------------|--------------|-------------------|---------------|
| sesgo_genero | Alta | 114 | 114 | los alumnos | Considerar: "el alumnado" o "los y las estudiantes" para lenguaje más inclusivo. |
| ortografia | Media | 57 | 57 | habia una vez | Corregir acentuación: "había una vez". |
```

---

## 🔍 Categorías de Análisis

### 1. sesgo_genero
**Detecta:** Uso exclusivo del masculino genérico, estereotipos de género, invisibilización de identidades.

**Ejemplos:**
- ❌ "Los alumnos deben estudiar"
- ✅ Sugerencia: "El alumnado debe estudiar"

### 2. sesgo_religion
**Detecta:** Proselitismo, lenguaje que favorece/denigra una religión específica.

**Ejemplos:**
- ❌ "Como todos sabemos, Dios creó..."
- ✅ Sugerencia: Nota editorial sobre pluralidad religiosa

### 3. sesgo_politica
**Detecta:** Lenguaje tendencioso, propaganda, parcialidad política.

**Ejemplos:**
- ❌ "El nefasto gobierno anterior"
- ✅ Sugerencia: "El gobierno anterior" (neutral)

### 4. ortografia
**Detecta:** Errores de acentuación, mayúsculas, puntuación.

**Ejemplos:**
- ❌ "habia" → ✅ "había"
- ❌ "TITULO" → ✅ "Título"

### 5. gramatica
**Detecta:** Concordancia, tiempos verbales, sintaxis.

**Ejemplos:**
- ❌ "Los niño corrió" → ✅ "Los niños corrieron"
- ❌ "Habían muchos" → ✅ "Había muchos"

### 6. semantica
**Detecta:** Uso inadecuado de palabras, ambigüedades, redundancias.

**Ejemplos:**
- ❌ "subir arriba" → ✅ "subir"
- ❌ "salir afuera" → ✅ "salir"

---

## ⚙️ Configuración Avanzada

### Ajustar Temperatura del Modelo

Edita `src/gemini_analyzer.py`:

```python
config = types.GenerateContentConfig(
    temperature=0.2,  # Valores más bajos = más consistente
    top_p=0.9,
    max_output_tokens=26050,
    # ...
)
```

### Personalizar el Prompt

Edita el método `_build_system_prompt()` en `src/gemini_analyzer.py` para:
- Agregar más ejemplos específicos
- Ajustar criterios de prioridad
- Incluir reglas específicas de tu contexto

### Modificar Límites de Palabras

En `src/gemini_analyzer.py`, método `_validate_and_clean_hallazgos()`:

```python
# Cambiar límite de fragmento (default: 10 palabras)
if len(palabras_fragmento) > 15:  # Nuevo límite: 15

# Cambiar límite de recomendación (default: 60 palabras)
if len(palabras_recomendacion) > 100:  # Nuevo límite: 100
```

---

## 🏗️ Arquitectura del Proyecto

```
text_validator/
├── app.py                      # Interfaz Streamlit principal
├── logging_config.py           # Configuración de logs (Cloud Run + Local)
├── requirements.txt            # Dependencias Python
├── .env                        # Variables de entorno (no versionar)
├── .env.example               # Plantilla de variables de entorno
├── .gitignore                 # Archivos a ignorar en Git
├── README.md                  # Este archivo
└── src/
    ├── __init__.py            # Inicialización del paquete
    ├── gemini_analyzer.py     # Lógica de análisis con Gemini
    └── report_generator.py    # Generación de reportes
```

---

## 🧪 Testing

### Testing Manual

```bash
# Ejecutar la aplicación
streamlit run app.py

# Cargar un PDF de prueba con:
# - Errores ortográficos intencionales
# - Lenguaje con sesgos de género
# - 3-5 páginas de contenido
```

### Verificar Resultados

Checklist de validación:
- [ ] Todas las categorías son válidas (una de las 6)
- [ ] Fragmentos ≤ 10 palabras
- [ ] Recomendaciones ≤ 60 palabras
- [ ] Prioridad es Alta, Media o Baja
- [ ] pagina_pdf presente
- [ ] pagina_libro presente

---

## 🐛 Troubleshooting

### Error: "Cliente de Vertex AI no inicializado"

**Solución:**
```bash
gcloud auth application-default login
```

### Error: "Error de configuración del sistema"

**Solución:** Verifica que `.env` contiene `GCP_PROJECT_ID`

### Análisis muy lento

**Causa:** Configuración de batch processing no activa

**Solución:** Verifica que `analyze_pdf_pages` procesa múltiples páginas en un request

### Falsos positivos/negativos

**Solución:**
1. Revisa los logs para entender el razonamiento del modelo
2. Ajusta el prompt en `_build_system_prompt()`
3. Modifica la temperatura (valores más bajos = más conservador)

---

## 📈 Métricas de Rendimiento

| Métrica | Objetivo | Actual (estimado) |
|---------|----------|-------------------|
| **Precisión** | ≥90% | 85-95% |
| **Utilidad** | ≥80% | 75-85% |
| **Eficiencia** | 60% reducción tiempo | 60-70% |
| **Velocidad** | ~3 seg/página | 2-4 seg/página |

*Nota: Métricas actuales son estimaciones. Requiere validación con datos reales.*

---

## 🔒 Seguridad y Privacidad

- ✅ Archivos temporales eliminados después del análisis
- ✅ Sin almacenamiento persistente de documentos
- ✅ Session state de Streamlit (temporal)
- ✅ No se envían PII adicionales a Gemini
- ✅ Safety settings configurados apropiadamente

### Recomendaciones:

- No subir documentos con información clasificada sin revisión
- Revisar políticas de Google Cloud para cumplimiento
- Considerar despliegue on-premise para datos sensibles

---

## 🕸️ API (FastAPI)

This repository now exposes a FastAPI backend instead of the Streamlit UI by default.

Run the API server from the project root:

```bash
# (optional) activate your virtualenv
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Endpoint:

- POST /api/v1/validate
    - multipart/form-data
    - fields: `file` (application/pdf), `start_page` (int), `end_page` (int)
    - response: JSON {"results": [{"page": n, "findings": [{categoria, descripcion, score}, ...]}, ...]}

Enable real Gemini (google-genai) calls by installing `google-genai` and setting env vars as described earlier, then set `USE_REAL_GEMINI=1`.

If you prefer the Streamlit UI, the original `app.py` was replaced; you can revert or run an older branch.