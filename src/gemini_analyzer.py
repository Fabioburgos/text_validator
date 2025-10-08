# src/gemini_analyzer.py

import io
import json
import logging
from google import genai
from google.genai import types
from typing import List, Dict, Optional
from logging_config import configure_logging

# Importar PyPDF2 para separar páginas
try:
    from PyPDF2 import PdfReader, PdfWriter
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logging.warning("PyPDF2 no está instalado. Instálalo con: pip install PyPDF2")

configure_logging()
logger = logging.getLogger("GeminiAnalyzer")

class GeminiAnalyzer:
    """Analizador de sesgos y calidad lingüística usando Gemini via Vertex AI"""
    
    CATEGORIAS_VALIDAS = {
        'sesgo_genero',
        'sesgo_religion', 
        'sesgo_politica',
        'ortografia',
        'gramatica',
        'semantica'
    }
    
    def __init__(self, project_id: str, location: str, model_name: str):
        """
        Inicializa el cliente de Gemini via Vertex AI
        
        Args:
            project_id: ID del proyecto de Google Cloud
            location: Ubicación de Vertex AI (default: us-east1)
            model_name: Nombre del modelo a usar
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa el cliente de Vertex AI"""
        try:
            logger.info(f"Inicializando Vertex AI...")
            logger.info(f"Proyecto: {self.project_id}")
            logger.info(f"Ubicación: {self.location}")
            logger.info(f"Modelo: {self.model_name}")

            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )
            logger.info("Auth: Application Default Credentials (ADC)")
            
            logger.info("Cliente de Vertex AI inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Vertex AI: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Construye el prompt del sistema para análisis"""
        system_prompt = """
        AUDITOR EDITORIAL - Detecta SOLO errores objetivos verificables.

        ## -- REGLA #1: MASCULINO GENÉRICO TRADICIONAL = NO ES ERROR -- ##

        Los siguientes usos del masculino genérico son CORRECTOS y NO deben reportarse:

        NUNCA REPORTAR:
        • "los profesores" → CORRECTO (uso tradicional)
        • "los maestros" → CORRECTO (uso tradicional)
        • "los alumnos" → CORRECTO (uso tradicional)
        • "los estudiantes" → CORRECTO (uso tradicional)
        • "los niños" → CORRECTO (uso tradicional)
        • "los docentes" → CORRECTO (uso tradicional)
        • "los padres" → CORRECTO (uso tradicional)
        • "el director" → CORRECTO (uso tradicional)
        • "el profesor" → CORRECTO (uso tradicional)
        • "todos los maestros" → CORRECTO (uso tradicional)

        IMPORTANTE: Estas frases NO tienen error de concordancia, NO tienen error de género.
        Son usos editoriales válidos del español.

        QUÉ SÍ REPORTAR (sesgo_genero)

        SOLO reporta sesgo de género en estos casos específicos:

        ESTEREOTIPOS ACTIVOS:
        • "las sensibles enfermeras" → Adjetivo estereotipado
        • "los agresivos policías" → Adjetivo estereotipado
        • Recomendación: "Eliminar estereotipo de género: 'sensibles'."

        DISCRIMINACIÓN EXPLÍCITA:
        • "las mujeres no sirven para matemáticas"
        • "los hombres son mejores líderes"
        • Recomendación: "Eliminar afirmación discriminatoria."

        LENGUAJE INCLUSIVO MAL USADO:
        • "la profesore" → Error gramatical
        • "le estudiante" → Error gramatical
        • "la niñe" → Error gramatical
        • Recomendación: "Corregir: 'la profesora' / 'el estudiante' / 'la niña'."

        ## -- QUÉ SÍ REPORTAR (otras categorías) -- ##

        sesgo_religion:
        "Como todos sabemos, La religión cristiana dice que..." → Imposición religiosa

        sesgo_politica:
        "el nefasto gobierno" → Lenguaje tendencioso

        ortografia:
        "habia" → Falta tilde: "había"
        "des-de" → Artefacto OCR: "desde"

        gramatica (SOLO errores técnicos reales):
        "Los niño corrió" → Concordancia: "Los niños corrieron"
        "Habían personas" → Verbo impersonal: "Había personas"
        "El estudiante que no cumplan" → Concordancia: "que no cumpla"

        NO ES ERROR DE GRAMÁTICA:
        ✗ "Los profesores deben llegar" → CORRECTO
        ✗ "El director debe supervisar" → CORRECTO
        ✗ "Todos los maestros deben" → CORRECTO

        semantica:
        "subir arriba" → Redundancia
        "salir afuera" → Redundancia

        ## -- EJEMPLOS COMPLETOS (ESTUDIA ESTOS) -- ##

        CASO 1 - NO REPORTAR:
        Texto: "Los profesores deben llegar puntualmente"
        Acción: NO reportar (uso tradicional válido)

        CASO 2 - NO REPORTAR:
        Texto: "El director debe supervisar que todos los docentes cumplan"
        Acción: NO reportar (uso tradicional válido)

        CASO 3 - NO REPORTAR:
        Texto: "Los maestros deben preparar sus clases"
        Acción: NO reportar (uso tradicional válido)

        CASO 4 - NO REPORTAR:
        Texto: "Todos los padres deben firmar"
        Acción: NO reportar (uso tradicional válido)

        CASO 5 - SÍ REPORTAR:
        Texto: "Habia una vez"
        categoria: ortografia
        prioridad: Media
        fragmento_original: "Habia"
        recomendacion: "Corregir tilde: 'Había'."

        CASO 6 - SÍ REPORTAR:
        Texto: "las sensibles maestras de preescolar"
        categoria: sesgo_genero
        prioridad: Alta
        fragmento_original: "las sensibles maestras"
        recomendacion: "Eliminar estereotipo de género: 'sensibles'."

        CASO 7 - SÍ REPORTAR:
        Texto: "subir arriba al segundo piso"
        categoria: semantica
        prioridad: Baja
        fragmento_original: "subir arriba"
        recomendacion: "Eliminar redundancia: 'subir'."

        CASO 8 - NO REPORTAR:
        Texto: "Tabla 1: Cantidad de Profesores"
        Acción: NO reportar (título institucional válido)

        ## -- FORMATO DE RECOMENDACIÓN -- ##

        [Acción específica]: [Sugerencia concreta].

        Ejemplos correctos:
        • "Corregir tilde: 'había'."
        • "Eliminar estereotipo de género: 'sensibles'."
        • "Eliminar redundancia: 'subir'."
        • "Artefacto OCR: corregir a 'desde'."

        ## -- PRINCIPIOS FINALES -- ##

        ✓ Máximo 5 hallazgos por página (los MÁS relevantes)
        ✓ Fragmento: máximo 10 palabras
        ✓ Recomendación: máximo 60 palabras
        ✓ Si no hay errores REALES, devolver hallazgos: []
        ✓ NUNCA reportes masculino genérico tradicional como error
        ✓ Solo reporta errores que REALMENTE existen
        """
        return system_prompt
    
    def _get_response_schema(self) -> dict:
        """Define el schema JSON para la respuesta estructurada"""
        schema_instruction = {
            "type": "OBJECT",
            "properties": {
                "idioma_detectado": {
                    "type": "STRING",
                    "enum": ["español", "inglés"]
                },
                "pagina_impresa": {
                    "type": "STRING"
                },
                "hallazgos": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "categoria": {
                                "type": "STRING",
                                "enum": [
                                    "sesgo_genero",
                                    "sesgo_religion",
                                    "sesgo_politica",
                                    "ortografia",
                                    "gramatica",
                                    "semantica"
                                ]
                            },
                            "prioridad": {
                                "type": "STRING",
                                "enum": ["Alta", "Media", "Baja"]
                            },
                            "fragmento_original": {
                                "type": "STRING"
                            },
                            "recomendacion": {
                                "type": "STRING"
                            }
                        },
                        "required": ["categoria", "prioridad", "fragmento_original", "recomendacion"]
                    }
                }
            },
            "required": ["idioma_detectado", "pagina_impresa", "hallazgos"]
        }
        return schema_instruction
    
    def _extract_single_page_pdf(self, pdf_path: str, page_num: int) -> bytes:
        """
        Extrae UNA página específica del PDF y la retorna como bytes de un PDF nuevo.
        
        Args:
            pdf_path: Ruta al archivo PDF original
            page_num: Número de página a extraer (1-indexed)
            
        Returns:
            Bytes del PDF con solo esa página
        """
        if not HAS_PYPDF2:
            raise Exception("PyPDF2 no está instalado. Instálalo con: pip install PyPDF2")
        
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num - 1])
            
            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)
            
            return output_buffer.read()
            
        except Exception as e:
            logger.error(f"Error al extraer página {page_num}: {e}")
            raise
    
    def _validate_and_clean_hallazgos(self, hallazgos: List[Dict]) -> List[Dict]:
        """
        Valida y limpia los hallazgos para asegurar cumplimiento de límites
        
        Args:
            hallazgos: Lista de hallazgos a validar
            
        Returns:
            Lista de hallazgos validados y limpiados
        """
        cleaned = []
        
        for h in hallazgos:
            # Validar categoría
            if h.get('categoria') not in self.CATEGORIAS_VALIDAS:
                logger.warning(f"Categoría inválida: {h.get('categoria')}, omitiendo hallazgo")
                continue
            
            # Validar y limpiar fragmento (máximo 10 palabras)
            fragmento = h.get('fragmento_original', '')
            palabras_fragmento = fragmento.split()
            if len(palabras_fragmento) > 10:
                fragmento = ' '.join(palabras_fragmento[:10]) + '...'
                h['fragmento_original'] = fragmento
            
            # Validar y limpiar recomendación (máximo 60 palabras)
            recomendacion = h.get('recomendacion', '')
            palabras_recomendacion = recomendacion.split()
            if len(palabras_recomendacion) > 60:
                recomendacion = ' '.join(palabras_recomendacion[:60]) + '...'
                h['recomendacion'] = recomendacion
            
            # Validar prioridad
            if h.get('prioridad') not in ['Alta', 'Media', 'Baja']:
                h['prioridad'] = 'Media'
            
            cleaned.append(h)
        
        return cleaned
    
    def analyze_pdf_pages(self, pdf_path: str, start_page: int = 1, end_page: int = 10, progress_callback: Optional[callable] = None) -> List[Dict]:
        """
        Analiza un rango de páginas del PDF usando Gemini via Vertex AI
        ESTRATEGIA: Extrae cada página como PDF individual antes de analizar
        
        Args:
            pdf_path: Ruta al archivo PDF
            start_page: Página inicial (1-indexed)
            end_page: Página final (1-indexed)
            progress_callback: Función opcional para reportar progreso
            
        Returns:
            Lista consolidada de todos los hallazgos con metadatos
        """
        if not self.client:
            raise Exception("Cliente de Vertex AI no inicializado")
        
        if not HAS_PYPDF2:
            raise Exception("PyPDF2 no está instalado. Instálalo con: pip install PyPDF2")
        
        todos_hallazgos = []
        
        all_pages = list(range(start_page, end_page + 1))
        total_pages = len(all_pages)
        
        logger.info(f"Total de páginas a analizar: {total_pages}")
        logger.info(f"Estrategia: Extraer cada página como PDF individual")
        
        for idx, page_num in enumerate(all_pages):
            logger.info(f"Procesando página {page_num}...")
            
            if progress_callback:
                progress_callback(idx + 1, total_pages)
            
            try:
                logger.info(f"Extrayendo página {page_num} del PDF...")
                single_page_pdf_bytes = self._extract_single_page_pdf(pdf_path, page_num)
                logger.info(f"Página {page_num} extraída: {len(single_page_pdf_bytes)} bytes")
                
                hallazgos_pagina = self._analyze_single_page(
                    pdf_bytes=single_page_pdf_bytes,
                    page_num=page_num
                )
                
                todos_hallazgos.extend(hallazgos_pagina)
                
                logger.info(f"Página {page_num} completada: {len(hallazgos_pagina)} hallazgo(s)")
                
            except Exception as e:
                logger.error(f"Error en página {page_num}: {e}")
                continue
        
        logger.info(f"Análisis completado: {len(todos_hallazgos)} hallazgo(s) encontrado(s)")
        return todos_hallazgos
    
    def _analyze_single_page(self, pdf_bytes: bytes, page_num: int) -> List[Dict]:
        """
        Analiza UNA SOLA página del PDF (que ya viene como PDF de 1 página)
        
        Args:
            pdf_bytes: Bytes del PDF de UNA sola página
            page_num: Número de página original (para metadatos)
            
        Returns:
            Lista de hallazgos de esa página
        """
        hallazgos_pagina = []
        
        user_prompt = f"""
        Analiza este documento PDF (página {page_num}).

        CRÍTICO: NO reportes como error el uso tradicional del masculino genérico:
        - "los profesores", "los maestros", "los alumnos" = CORRECTO
        - "el director", "el profesor" = CORRECTO

        Si no hay errores REALES, devuelve hallazgos: []
        """
        
        try:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=user_prompt),
                        types.Part.from_bytes(
                            data=pdf_bytes,
                            mime_type="application/pdf"
                        )
                    ]
                )
            ]
            
            config = types.GenerateContentConfig(
                temperature=0.1,  # Reducido para mayor consistencia
                top_p=0.9,
                max_output_tokens=54000,
                response_mime_type="application/json",
                response_schema=self._get_response_schema(),
                system_instruction=[types.Part.from_text(text=self._build_system_prompt())],
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
                ]
            )
            
            logger.info(f"Enviando request para página {page_num}...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            
            result = self._parse_response(response)
            
            if result:
                idioma = result.get('idioma_detectado', 'español')
                pagina_impresa = result.get('pagina_impresa', str(page_num))
                
                try:
                    pagina_impresa_int = int(pagina_impresa)
                except:
                    pagina_impresa_int = page_num
                
                hallazgos = result.get('hallazgos', [])
                hallazgos = self._validate_and_clean_hallazgos(hallazgos)
                
                for hallazgo in hallazgos:
                    hallazgo['pagina_pdf'] = page_num
                    hallazgo['pagina_libro'] = pagina_impresa_int
                    hallazgo['idioma'] = idioma
                    hallazgos_pagina.append(hallazgo)
            
        except Exception as e:
            logger.error(f"Error en _analyze_single_page para página {page_num}: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return hallazgos_pagina
    
    def _parse_response(self, response) -> Optional[Dict]:
        """
        Parsea la respuesta JSON estructurada de Gemini para UNA página
        
        Args:
            response: Respuesta de Gemini
            
        Returns:
            Diccionario con resultado de la página o None si hay error
        """
        try:
            if not response or not hasattr(response, 'candidates') or not response.candidates:
                logger.warning(f"Sin candidates en respuesta")
                return None
            
            candidate = response.candidates[0]
            
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)
                logger.info(f"Finish reason: {finish_reason}")
                
                if 'MAX_TOKENS' in finish_reason:
                    logger.error(f"⚠️ MAX_TOKENS alcanzado.")
                    
                if 'SAFETY' in finish_reason:
                    logger.error(f"Respuesta bloqueada por seguridad")
                    return None
            
            if not hasattr(candidate, 'content') or candidate.content is None:
                logger.warning(f"Sin content en candidate")
                return None
            
            parts = candidate.content.parts if hasattr(candidate.content, 'parts') else []
            if not parts:
                logger.warning(f"Sin parts en content")
                return None
            
            response_text = ""
            for part in parts:
                if hasattr(part, 'text') and part.text:
                    response_text += part.text
            
            if not response_text:
                logger.warning(f"Respuesta vacía")
                return None
            
            result = json.loads(response_text)
            
            if not isinstance(result, dict):
                logger.warning(f"La respuesta no es un objeto")
                return None
            
            logger.info(f"Respuesta parseada correctamente")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            if 'response_text' in locals():
                logger.info(f"Respuesta: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error procesando respuesta: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def analyze_single_page(self, pdf_path: str, page_num: int) -> List[Dict]:
        """
        Analiza una sola página del PDF (método público)
        
        Args:
            pdf_path: Ruta al archivo PDF
            page_num: Número de página (1-indexed)
            
        Returns:
            Lista de hallazgos de esa página
        """
        return self.analyze_pdf_pages(pdf_path, page_num, page_num)