# app.py - Versión optimizada para usuarios finales

import os
import tempfile
import streamlit as st
from dotenv import load_dotenv
from src import GeminiAnalyzer, ReportGenerator

# Cargar variables de entorno
load_dotenv()

# Configuración de página
st.set_page_config(
    page_title="Validador de Textos",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"  # Ocultar sidebar por defecto
)

# CSS personalizado para mejor UX
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .category-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .badge-sesgo {
        background-color: #ffe0e0;
        color: #c00;
    }
    .badge-calidad {
        background-color: #e0f0ff;
        color: #0066cc;
    }
    .metric-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Título principal simplificado
st.markdown('<h1 class="main-header">📚 Validador de Textos</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Auditoría automática de sesgos y calidad lingüística en documentos PDF</p>', unsafe_allow_html=True)

# Verificar configuración en background
project_id = os.getenv('GCP_PROJECT_ID', '')
location = os.getenv('GCP_LOCATION', 'us-east1')
model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')

if not project_id:
    st.error("⚠️ Error de configuración del sistema. Contacta al administrador.")
    st.stop()

# Tabs principales
tab1, tab2, tab3 = st.tabs(["📤 Cargar Documento", "📊 Ver Resultados", "ℹ️ ¿Qué analiza?"])

with tab1:
    # Explicación simple para usuarios
    st.markdown("""
    ### 🎯 ¿Qué hace este validador?
    
    Analiza tu documento PDF página por página para detectar:
    
    <div style="margin: 1.5rem 0;">
        <span class="category-badge badge-sesgo">Sesgos de Género</span>
        <span class="category-badge badge-sesgo">Sesgos Religiosos</span>
        <span class="category-badge badge-sesgo">Sesgos Políticos</span>
        <span class="category-badge badge-calidad">Ortografía</span>
        <span class="category-badge badge-calidad">Gramática</span>
        <span class="category-badge badge-calidad">Semántica</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Carga de archivo simplificada
    st.subheader("📄 Selecciona tu documento")
    
    uploaded_file = st.file_uploader(
        "Arrastra tu PDF aquí o haz clic para seleccionarlo",
        type=['pdf'],
        help="Formatos soportados: PDF (incluyendo PDFs escaneados)"
    )
    
    if uploaded_file:
        st.success(f"✅ Archivo cargado: **{uploaded_file.name}**")
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        # Detectar número de páginas del PDF
        try:
            import PyPDF2
            with open(tmp_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pdf_pages = len(pdf_reader.pages)
        except Exception as e:
            st.warning(f"No se pudo detectar el número de páginas. Error: {e}")
            total_pdf_pages = 1000  # Fallback
        
        st.info(f"📄 El documento tiene **{total_pdf_pages} página(s)**")
        
        st.divider()
        
        # Configuración simple
        st.subheader("⚙️ Configurar análisis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_page = st.number_input(
                "Página inicial",
                min_value=1,
                max_value=total_pdf_pages,
                value=1,
                help="Primera página que deseas analizar"
            )
        
        with col2:
            end_page = st.number_input(
                "Página final",
                min_value=start_page,
                max_value=total_pdf_pages,
                value=min(total_pdf_pages, start_page + 9),
                help="Última página que deseas analizar"
            )
        
        pages_to_analyze = end_page - start_page + 1
        estimated_time = pages_to_analyze * 3
        
        st.info(f"📊 Se analizarán **{pages_to_analyze} página(s)** • Tiempo estimado: ~{estimated_time} segundos")
        
        # Botón de análisis
        if st.button("🚀 Iniciar Análisis", type="primary", use_container_width=True):
            try:
                with st.spinner("🔍 Analizando documento... Por favor espera."):
                    # Crear analizador
                    analyzer = GeminiAnalyzer(
                        project_id=project_id,
                        location=location,
                        model_name=model_name
                    )
                    
                    # Barra de progreso
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(current, total):
                        progress = current / total
                        progress_bar.progress(progress)
                        status_text.text(f"📄 Procesando página {current} de {total}...")
                    
                    # Analizar PDF
                    hallazgos = analyzer.analyze_pdf_pages(
                        pdf_path=tmp_path,
                        start_page=start_page,
                        end_page=end_page,
                        progress_callback=update_progress
                    )
                    
                    # Generar reporte
                    report_gen = ReportGenerator()
                    report_gen.add_hallazgos(hallazgos, document_name=uploaded_file.name)
                    
                    # Guardar en session state
                    st.session_state['hallazgos'] = hallazgos
                    st.session_state['report_gen'] = report_gen
                    st.session_state['analyzed'] = True
                    st.session_state['pdf_name'] = uploaded_file.name
                    st.session_state['pages_analyzed'] = f"{start_page}-{end_page}"
                    st.session_state['total_pages'] = pages_to_analyze
                    
                    progress_bar.progress(1.0)
                    status_text.empty()
                    
                    if len(hallazgos) > 0:
                        st.success(f"✅ Análisis completado. Se encontraron **{len(hallazgos)} hallazgo(s)**")
                        st.balloons()
                    else:
                        st.success("✅ Análisis completado. ¡No se encontraron problemas en las páginas analizadas!")
                    
                    st.info("👉 Ve a la pestaña **Ver Resultados** para revisar el reporte completo")
            
            except Exception as e:
                st.error("❌ Ocurrió un error durante el análisis.")
                st.error("Por favor, intenta nuevamente o contacta al soporte técnico.")
                
                # Solo mostrar detalles técnicos en un expander colapsado
                with st.expander("🔧 Detalles técnicos del error"):
                    st.code(str(e))
            
            finally:
                # Limpiar archivo temporal
                if os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

with tab2:
    st.header("📊 Resultados del Análisis")
    
    if 'analyzed' not in st.session_state or not st.session_state['analyzed']:
        st.info("👈 Primero carga y analiza un documento en la pestaña **Cargar Documento**")
        
        # Mensaje de ayuda
        st.markdown("""
        ### 📝 Instrucciones
        
        1. Ve a la pestaña **Cargar Documento**
        2. Selecciona tu archivo PDF
        3. Elige el rango de páginas a analizar
        4. Haz clic en **Iniciar Análisis**
        5. Regresa aquí para ver los resultados
        """)
    else:
        report_gen = st.session_state['report_gen']
        hallazgos = st.session_state['hallazgos']
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📄 Documento", st.session_state.get('pdf_name', 'N/A')[:20] + "...")
        
        with col2:
            st.metric("📖 Páginas", st.session_state.get('pages_analyzed', 'N/A'))
        
        with col3:
            st.metric("🔍 Hallazgos", len(hallazgos))
        
        with col4:
            # Calcular hallazgos de alta prioridad
            alta_prioridad = sum(1 for h in hallazgos if h.get('prioridad') == 'Alta')
            st.metric("⚠️ Alta prioridad", alta_prioridad)
        
        st.divider()
        
        # Resumen estadístico
        if hallazgos:
            st.subheader("📈 Resumen Estadístico")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Por Categoría:**")
                categorias = {}
                for h in hallazgos:
                    cat = h.get('categoria', 'unknown')
                    categorias[cat] = categorias.get(cat, 0) + 1
                
                for cat, count in sorted(categorias.items()):
                    # Mapear categorías a nombres legibles
                    nombres = {
                        'sesgo_genero': '👥 Sesgo de Género',
                        'sesgo_religion': '🕌 Sesgo Religioso',
                        'sesgo_politica': '🏛️ Sesgo Político',
                        'ortografia': '✍️ Ortografía',
                        'gramatica': '📝 Gramática',
                        'semantica': '💬 Semántica'
                    }
                    st.markdown(f"- {nombres.get(cat, cat)}: **{count}**")
            
            with col2:
                st.markdown("**Por Prioridad:**")
                prioridades = {}
                for h in hallazgos:
                    pri = h.get('prioridad', 'Media')
                    prioridades[pri] = prioridades.get(pri, 0) + 1
                
                for pri in ['Alta', 'Media', 'Baja']:
                    count = prioridades.get(pri, 0)
                    if count > 0:
                        icono = '🔴' if pri == 'Alta' else '🟡' if pri == 'Media' else '🟢'
                        st.markdown(f"- {icono} {pri}: **{count}**")
            
            st.divider()
            
            # Tabla de hallazgos
            st.subheader("📋 Detalle de Hallazgos")
            
            markdown_table = report_gen.generate_markdown_table()
            st.markdown(markdown_table)
            
            st.divider()
            
            # Descargas
            st.subheader("💾 Descargar Resultados")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 Descargar Reporte (Markdown)",
                    data=markdown_table,
                    file_name=f"reporte_{st.session_state.get('pdf_name', 'documento').replace('.pdf', '')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                # Exportar a CSV
                import io
                import pandas as pd
                
                df = pd.DataFrame(hallazgos)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Descargar Datos (CSV)",
                    data=csv_buffer.getvalue(),
                    file_name=f"datos_{st.session_state.get('pdf_name', 'documento').replace('.pdf', '')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.success("✅ ¡Excelente! No se encontraron problemas en las páginas analizadas.")

with tab3:
    st.header("ℹ️ ¿Qué analiza este validador?")
    
    st.markdown("""
    ### 🎯 Objetivo
    
    Este validador analiza documentos PDF para detectar **sesgos** y problemas de **calidad lingüística** 
    de forma automática, neutral y consistente.
    
    ### 📊 Categorías de Análisis
    
    #### 🔴 Sesgos
    
    **1. Sesgo de Género**
    - Lenguaje no inclusivo (uso exclusivo del masculino genérico)
    - Estereotipos de género
    - Exclusión de identidades
    
    *Ejemplo:* "Los alumnos deben entregar..." → Recomendación: "El alumnado debe entregar..." o "Los y las estudiantes..."
    
    **2. Sesgo Religioso**
    - Lenguaje que favorece o denigra una religión específica
    - Proselitismo religioso
    - Imposición de valores religiosos como universales
    
    *Ejemplo:* "Como todos sabemos, Dios..." → Recomendación: Nota editorial sobre neutralidad religiosa
    
    **3. Sesgo Político**
    - Lenguaje tendencioso políticamente
    - Propaganda o parcialidad política
    - Presentación sesgada de hechos políticos
    
    *Ejemplo:* "El nefasto gobierno anterior..." → Recomendación: Usar lenguaje neutral y objetivo
    
    #### 🔵 Calidad Lingüística
    
    **4. Ortografía**
    - Errores de acentuación
    - Uso incorrecto de mayúsculas/minúsculas
    - Errores de puntuación
    
    *Ejemplo:* "habia" → Recomendación: Corregir a "había" (falta tilde)
    
    **5. Gramática**
    - Problemas de concordancia
    - Errores en tiempos verbales
    - Problemas de sintaxis
    
    *Ejemplo:* "Los niño corrió" → Recomendación: Corregir concordancia: "Los niños corrieron" o "El niño corrió"
    
    **6. Semántica**
    - Uso inadecuado de palabras
    - Ambigüedades
    - Redundancias
    
    *Ejemplo:* "Subir arriba" → Recomendación: Eliminar redundancia, usar solo "subir"
    
    ### 🔍 Tratamiento Especial
    
    **Citas Textuales:**
    - No se reescriben las citas directas
    - Se sugiere agregar una nota editorial cuando sea necesario
    - Se respeta el contexto histórico
    
    **Artefactos de OCR/PDF:**
    - Se identifican problemas de digitalización
    - Se recomienda limpieza del documento
    - Se marcan explícitamente en el reporte
    
    **Consolidación:**
    - Errores repetidos en la misma página se agrupan
    - Se evita redundancia en las recomendaciones
    
    ### 📋 Formato de Resultados
    
    Cada hallazgo incluye:
    - **Categoría:** Tipo de problema detectado
    - **Prioridad:** Alta, Media o Baja
    - **Página PDF:** Número de página en el archivo
    - **Página Libro:** Número de página impresa (si está visible)
    - **Fragmento:** Texto problemático (máximo 10 palabras)
    - **Recomendación:** Sugerencia accionable (máximo 60 palabras)
    
    ### 🌍 Idiomas Soportados
    
    - 🇪🇸 Español
    - 🇬🇧 Inglés
    
    *El sistema detecta automáticamente el idioma de cada página.*
    
    ### ⚖️ Neutralidad
    
    Este validador:
    - ✅ Identifica sesgos de forma objetiva
    - ✅ Respeta el contenido original
    - ✅ No censura ni reescribe
    - ✅ Sugiere alternativas inclusivas
    - ❌ No hace juicios ideológicos
    - ❌ No impone valores específicos
    """)

# Footer simple
st.divider()
st.caption("Validador de Textos | Versión 2.0 | © 2025")