# src.report_generator.py

from typing import List, Dict
import pandas as pd

class ReportGenerator:
    """Generador de tabla Markdown con hallazgos"""
    
    def __init__(self):
        self.hallazgos = []
        self.document_name = ""
    
    def add_hallazgos(self, hallazgos: List[Dict], document_name: str = ""):
        """
        Agrega hallazgos a la lista
        
        Args:
            hallazgos: Lista de hallazgos
            document_name: Nombre del documento analizado
        """
        self.hallazgos.extend(hallazgos)
        if document_name:
            self.document_name = document_name

    def generate_markdown_table(self) -> str:
        """
        Genera tabla en formato Markdown según especificación
        
        Formato:
        | categoria | prioridad | pagina_pdf | pagina_libro | fragmento_original | recomendacion |
        """
        # Header con nombre del documento
        lines = []
        if self.document_name:
            lines.append(f"### Resultados para: {self.document_name}\n")
        
        if not self.hallazgos:
            lines.append("\nNo se encontraron hallazgos en el documento analizado.")
            return '\n'.join(lines)
        
        # Ordenar por página PDF, luego por categoría
        hallazgos_ordenados = sorted(
            self.hallazgos,
            key=lambda x: (x.get('pagina_pdf', 0), x.get('categoria', ''))
        )
        
        # Construir tabla manualmente para control exacto del formato
        lines.append("\n| categoria | prioridad | pagina_pdf | pagina_libro | fragmento_original | recomendacion |")
        lines.append("|-----------|-----------|------------|--------------|-------------------|---------------|")
        
        for h in hallazgos_ordenados:
            categoria = h.get('categoria', '—')
            prioridad = h.get('prioridad', 'Media')
            pagina_pdf = h.get('pagina_pdf', '—')
            pagina_libro = h.get('pagina_libro', '—')
            fragmento = h.get('fragmento_original', '—')
            recomendacion = h.get('recomendacion', '—')
            
            # Limpiar fragmento: max 10 palabras según PRD
            if fragmento != '—' and len(fragmento.split()) > 10:
                palabras = fragmento.split()[:10]
                fragmento = ' '.join(palabras) + '...'
            
            # Limpiar recomendación: max 60 palabras según PRD
            if recomendacion != '—' and len(recomendacion.split()) > 60:
                palabras = recomendacion.split()[:60]
                recomendacion = ' '.join(palabras) + '...'
            
            # Escapar pipes en el contenido
            fragmento_escaped = str(fragmento).replace('|', '\\|')
            recomendacion_escaped = str(recomendacion).replace('|', '\\|')
            
            linea = f"| {categoria} | {prioridad} | {pagina_pdf} | {pagina_libro} | {fragmento_escaped} | {recomendacion_escaped} |"
            lines.append(linea)
        
        return '\n'.join(lines)
    
    def generate_summary(self) -> str:
        """Genera resumen estadístico de hallazgos"""
        if not self.hallazgos:
            return "Sin hallazgos"
        
        total = len(self.hallazgos)
        
        # Contar por categoría
        por_categoria = {}
        for h in self.hallazgos:
            cat = h.get('categoria', 'unknown')
            por_categoria[cat] = por_categoria.get(cat, 0) + 1
        
        # Contar por prioridad
        por_prioridad = {}
        for h in self.hallazgos:
            pri = h.get('prioridad', 'Media')
            por_prioridad[pri] = por_prioridad.get(pri, 0) + 1
        
        # Construir resumen
        lineas = [
            f"**Total de hallazgos:** {total}",
            "",
            "**Por categoría:**"
        ]
        for cat, count in sorted(por_categoria.items()):
            lineas.append(f"- {cat}: {count}")
        
        lineas.append("")
        lineas.append("**Por prioridad:**")
        for pri in ['Alta', 'Media', 'Baja']:
            count = por_prioridad.get(pri, 0)
            if count > 0:
                lineas.append(f"- {pri}: {count}")
        
        return '\n'.join(lineas)
    
    def export_to_csv(self, filename: str):
        """Exporta hallazgos a CSV"""
        if not self.hallazgos:
            return
        
        df = pd.DataFrame(self.hallazgos)
        columnas = ['categoria', 'prioridad', 'pagina_pdf', 'pagina_libro', 
                   'fragmento_original', 'recomendacion']
        
        # Reordenar columnas si existen
        columnas_existentes = [c for c in columnas if c in df.columns]
        df = df[columnas_existentes]
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    def clear(self):
        """Limpia todos los hallazgos"""
        self.hallazgos = []
        self.document_name = ""