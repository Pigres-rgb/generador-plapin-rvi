import streamlit as st
import fitz
import json
import os
import io
import google.generativeai as genai

st.set_page_config(page_title="Generador PLAPIN - RVI", layout="wide")

st.title("Generador Automático de PLAPIN (RVI) - SS.SS. Valencia")
st.markdown("Introduce el caso familiar y generaremos el PDF rellenado cuadrado y listo para presentar.")

with st.sidebar:
    st.header("1. Configuración")
    
    # Intenta leer la clave desde los secretos de Streamlit (si está configurada)
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Clave cargada de forma segura")
        api_key_used = st.secrets["GEMINI_API_KEY"]
    else:
        api_key_used = st.text_input("Gemini API Key", type="password")
        
    # Agrega esto temporalmente debajo para asegurarnos de que el texto de Google es literal
    st.markdown("⚠️ **Importante**: Si usaste AI Studio, asegúrate de que tu clave está **íntegra** y el modelo a elegir abajo se autoajuste.")
    
    # Vamos a forzar un listado de modelos compatibles dinámicamente:
    def get_models(key):
        import google.generativeai as gai
        try:
            gai.configure(api_key=key)
            return [m.name for m in gai.list_models() if 'generateContent' in m.supported_generation_methods]
        except: return []

    lista_modelos = []
    if api_key_used:
        lista_modelos = get_models(api_key_used)
    
    if lista_modelos:
        chosen_model = st.selectbox("Modelo IA Autodetectado:", [m.replace("models/", "") for m in lista_modelos])
    else:
        chosen_model = "gemini-1.5-flash"


st.header("2. Datos del Nuevo Caso Familiar")
caso_text = st.text_area("Pega aquí el caso, informe o notas de la familia:", height=300,
    placeholder="Ej: Sonia es una madre de 48 años con problemas de alcoholismo. Tiene una hija de 18 que abandonó los estudios y una de 16... Están en riesgo de desahucio.")

if st.button("Generar PLAPIN en PDF", type="primary"):
    if not api_key_used:
        st.error("Por favor, introduce tu Gemini API Key en la barra lateral.")
        st.stop()
    if not caso_text.strip():
        st.error("Por favor, introduce el texto del caso familiar.")
        st.stop()
    
    genai.configure(api_key=api_key_used)
    # Utilizamos el modelo exacto que hemos detectado de tu cuenta de Google
    try:
        model = genai.GenerativeModel(chosen_model)
    except Exception as em:
        model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
Lee este caso familiar y extrae la información para rellenar el Plan Personalizado de Inclusión.
Devuelve ÚNICAMENTE un objeto JSON válido y sin caracteres extra. No uses markdown ````json ````, solo empieza con {{ y termina con }}.
Estructura exigida:
{{
  "titular": {{"nombre": "Sonia (Titular)", "fecha_nac": "1978 (48a)"}},
  "persona_2": {{"existe": true, "nombre": "Hija Mayor", "parentesco": "Hija", "fecha_nac": "2008 (18a)"}},
  "persona_3": {{"existe": true, "nombre": "Hija Menor", "parentesco": "Hija", "fecha_nac": "2010 (16a)"}},
  "diagnostico": {{
    "1": {{"si": false, "prioridad": "NADA", "obs": "Sin problema indicado"}},
    "2": {{"si": true, "prioridad": "ALTA", "obs": "Motivo vivienda"}},
    "3": {{"si": true, "prioridad": "ALTA", "obs": "Motivo economico"}},
    "4": {{"si": false, "prioridad": "NADA", "obs": "Sin problema"}},
    "5": {{"si": false, "prioridad": "NADA", "obs": "Sin problema"}},
    "6": {{"si": true, "prioridad": "ALTA", "obs": "Motivo salud"}},
    "7": {{"si": true, "prioridad": "MEDIA", "obs": "Motivo formativo"}},
    "8": {{"si": true, "prioridad": "ALTA", "obs": "Motivo laboral"}}
  }},
  "intervencion_comun": {{
    "dinamica": {{"txt1": "Ninguno", "txt2": "Ninguna", "txt3": "Ninguna", "corto": false, "medio": false}},
    "vivienda": {{"txt1": "Objetivos...", "txt2": "Acciones...", "txt3": "Tareas...", "corto": true, "medio": false}},
    "economico": {{"txt1": "Objetivos...", "txt2": "Acciones...", "txt3": "Tareas...", "corto": true, "medio": true}}
  }},
  "intervencion_titular": {{
    "desarrollo_personal": {{"txt1": "Ninguno", "txt2": "Ninguna", "txt3": "Ninguna"}},
    "desarrollo_comun": {{"txt1": "Ninguno", "txt2": "Ninguna", "txt3": "Ninguna"}},
    "sanitario": {{"txt1": "Objs", "txt2": "Accs", "txt3": "Tareas", "corto": true}},
    "formativo_laboral": {{"txt1": "Objs", "txt2": "Accs", "txt3": "Tareas", "medio": true}}
  }},
  "intervencion_otros_miembros": "Resume en texto continuo los objetivos y tareas de persona 2 y persona 3 para adjuntarlos al final. Ejem: PERSONA 2 (HIJA): Objetivos: xxx. Acciones: xxx...",
  "exoneraciones": {{
    "menor_estudiando_num": "3",
    "desempleo_derivacion_labora_nums": "1 y 2",
    "firmantes": ["Sonia (madre) _________________", "Hija (18a) _________________"]
  }}
}}

CASO FAMILIAR:
{caso_text}
"""
    
    with st.spinner("Analizando caso clínico con IA..."):
        try:
            response = model.generate_content(prompt)
            json_str = response.text.strip()
            # Eliminar delimitadores markdown de la IA si existen
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            
            json_str = json_str.strip()
            data = json.loads(json_str)
        except Exception as e:
            st.error(f"Error procesando los datos con la IA: {e}")
            st.stop()
            
    with st.spinner("Rellenando plantilla PDF Oficial..."):
        try:
            # FITZ LOGIC
            doc = fitz.open("Plantilla_RVI.pdf")
            color, font, fs_data, fs_txt, fs_sml = (0, 0, 0.7), "hebo", 10, 9, 8
            
            import uuid
            def insert_centered(page, rect, text, fs=12):
                w = fitz.Widget()
                w.rect = rect
                w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                w.field_name = "f_" + str(uuid.uuid4()).replace("-", "")
                w.field_value = str(text)
                w.text_font = "Helv"
                w.text_fontsize = fs
                w.text_color = list(color)
                w.text_format = 1  # 1 = Centered
                page.add_widget(w)
                
            def insert_text(page, rect, text, fs=fs_sml):
                pad_rect = fitz.Rect(rect.x0+2, rect.y0+2, rect.x1-2, rect.y1-2)
                w = fitz.Widget()
                w.rect = pad_rect
                w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                w.field_name = "f_" + str(uuid.uuid4()).replace("-", "")
                w.field_value = str(text)
                w.text_font = "Helv"
                w.text_fontsize = fs
                w.text_color = list(color)
                w.field_flags = 4096  # 4096 = Multiline
                page.add_widget(w)

            # PAGE 1: Identity Table (8 rows)
            p1 = doc[0]
            
            # --- Corrección dinámica del encabezado maestro ---
            # Borramos el encabezado antiguo/corrupto y creamos el nuevo
            p1.draw_rect(fitz.Rect(50, 60, 580, 280), color=(1,1,1), fill=(1,1,1))
            p1.draw_rect(fitz.Rect(60, 60, 560, 125), color=(0,0,0), width=0.5, fill=(0.75, 0.85, 0.95))
            p1.draw_rect(fitz.Rect(60, 135, 560, 260), color=(0,0,0), width=1, fill=(1,1,1))
            
            p1.insert_textbox(fitz.Rect(60, 61, 560, 85), "Doc. 3. RVI. RENTA VALENCIANA DE INCLUSIÓN", fontname="hebo", fontsize=14, align=fitz.TEXT_ALIGN_CENTER)
            p1.insert_textbox(fitz.Rect(60, 81, 560, 105), "Plan Personalizado de Inclusión (PLAPIN)", fontname="hebo", fontsize=14, align=fitz.TEXT_ALIGN_CENTER)
            p1.insert_textbox(fitz.Rect(60, 101, 560, 125), "Plan de Atención Individual (PAI)", fontname="hebo", fontsize=14, align=fitz.TEXT_ALIGN_CENTER)
            
            fs_h = 10
            p1.insert_text(fitz.Point(70, 153), "ENTIDAD LOCAL: ", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(340, 153), "FECHA: ", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(70, 178), "PROF. REF. AAPP: ", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(390, 178), "Nº COLEGIADO/A: ", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(70, 203), "PROF. ITINERARIOS: ", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(390, 203), "Nº COLEGIADO/A: ", fontname="hebo", fontsize=fs_h)
            p1.draw_line(fitz.Point(60, 222), fitz.Point(560, 222), color=(0,0,0), width=1)
            p1.insert_text(fitz.Point(70, 243), "Exp. RVI:  RGIS/_____ / _____ / ________", fontname="hebo", fontsize=fs_h)
            p1.insert_text(fitz.Point(320, 243), "Centro social: ", fontname="hebo", fontsize=fs_h)
            # ------------------------------------------------
            
            # Entidad Local y otros campos de la cabecera para que sean editables:
            insert_text(p1, fitz.Rect(160, 140, 335, 155), "")
            insert_text(p1, fitz.Rect(385, 140, 555, 155), "")
            insert_text(p1, fitz.Rect(175, 165, 385, 180), "")
            insert_text(p1, fitz.Rect(490, 165, 555, 180), "")
            insert_text(p1, fitz.Rect(185, 190, 385, 205), "")
            insert_text(p1, fitz.Rect(490, 190, 555, 205), "")
            insert_text(p1, fitz.Rect(130, 230, 305, 245), "")
            insert_text(p1, fitz.Rect(390, 230, 555, 245), "")
            
            p1_y = [382.5, 400.5, 421.5, 442.5, 463.5, 484.5, 505.5, 526.5, 549.5]
            v = [57.5, 85.5, 263.5, 426.5, 496.5, 558.5]
            for i in range(8):
                if i == 0:
                    insert_centered(p1, fitz.Rect(v[0], p1_y[i], v[1], p1_y[i+1]), "1", fs_data)
                    insert_centered(p1, fitz.Rect(v[1], p1_y[i], v[2], p1_y[i+1]), data['titular'].get('nombre',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[2], p1_y[i], v[3], p1_y[i+1]), "Titular", fs_data)
                    insert_centered(p1, fitz.Rect(v[3], p1_y[i], v[4], p1_y[i+1]), data['titular'].get('fecha_nac',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[4], p1_y[i], v[5], p1_y[i+1]), "", fs_data)
                elif i == 1 and data['persona_2']['existe']:
                    insert_centered(p1, fitz.Rect(v[0], p1_y[i], v[1], p1_y[i+1]), "2", fs_data)
                    insert_centered(p1, fitz.Rect(v[1], p1_y[i], v[2], p1_y[i+1]), data['persona_2'].get('nombre',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[2], p1_y[i], v[3], p1_y[i+1]), data['persona_2'].get('parentesco',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[3], p1_y[i], v[4], p1_y[i+1]), data['persona_2'].get('fecha_nac',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[4], p1_y[i], v[5], p1_y[i+1]), "", fs_data)
                elif i == 2 and data['persona_3']['existe']:
                    insert_centered(p1, fitz.Rect(v[0], p1_y[i], v[1], p1_y[i+1]), "3", fs_data)
                    insert_centered(p1, fitz.Rect(v[1], p1_y[i], v[2], p1_y[i+1]), data['persona_3'].get('nombre',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[2], p1_y[i], v[3], p1_y[i+1]), data['persona_3'].get('parentesco',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[3], p1_y[i], v[4], p1_y[i+1]), data['persona_3'].get('fecha_nac',''), fs_data)
                    insert_centered(p1, fitz.Rect(v[4], p1_y[i], v[5], p1_y[i+1]), "", fs_data)
                else:
                    insert_centered(p1, fitz.Rect(v[0], p1_y[i], v[1], p1_y[i+1]), str(i+1), fs_data)
                    insert_centered(p1, fitz.Rect(v[1], p1_y[i], v[2], p1_y[i+1]), "", fs_data) # Nombre
                    insert_centered(p1, fitz.Rect(v[2], p1_y[i], v[3], p1_y[i+1]), "", fs_data) # Parentesco
                    insert_centered(p1, fitz.Rect(v[3], p1_y[i], v[4], p1_y[i+1]), "", fs_data) # Fecha Nac
                    insert_centered(p1, fitz.Rect(v[4], p1_y[i], v[5], p1_y[i+1]), "", fs_data) # Telefono
            
            res_adj = p1.search_for("SÍ (debe adjuntarse)")
            if res_adj:
                res3 = p1.search_for("NO")
                for r in res3:
                     if abs(r.y0 - res_adj[0].y0) < 20:
                         insert_centered(p1, fitz.Rect(r.x1 + 5, r.y0 - 2, r.x1 + 25, r.y0 + 15), "X", 12)

            # PAGE 2: Intervenciones Table
            p2 = doc[1]
            p2_y = [151.1, 180.8, 210.6, 240.3, 270.1, 299.8, 329.6, 359.3, 389.1, 418.8, 448.5, 478.3, 505.0]
            p2_x = [67.1, 119.2, 233.0, 454.8, 560.0]
            for r in range(len(p2_y)-1):
                for c in range(len(p2_x)-1):
                    insert_text(p2, fitz.Rect(p2_x[c], p2_y[r], p2_x[c+1], p2_y[r+1]), "")
            
            # P2 Checkboxes Planes adicionales
            insert_centered(p2, fitz.Rect(75, 620, 115, 640), "", 12) # Si checkbox 1
            insert_centered(p2, fitz.Rect(260, 620, 290, 640), "", 12) # No checkbox 1
            insert_centered(p2, fitz.Rect(250, 560, 350, 580), "", 12) # Otros checkboxes Si/No
            insert_centered(p2, fitz.Rect(450, 560, 550, 580), "", 12)
            
            # P3 y P4 Diagnostics
            def fill_diag_row(page, y0, y1, inter):
                v_si_no = "X" if str(inter.get('si')).lower() in ['true', 'yes', 'sí'] or inter.get('si') == True else ""
                v_no = "" if v_si_no else "X"
                pr = str(inter.get('prioridad','')).upper()
                v_baja = "X" if pr == "BAJA" and v_si_no else ""
                v_media = "X" if pr == "MEDIA" and v_si_no else ""
                v_alta = "X" if pr in ["ALTA", "ALTO"] and v_si_no else ""
                
                # Generamos widgets para TODAS las celdas vacías o rellenas
                insert_centered(page, fitz.Rect(253, y0, 276.5, y1), v_si_no, 12)
                insert_centered(page, fitz.Rect(276.5, y0, 322.5, y1), v_no, 12)
                insert_centered(page, fitz.Rect(322.5, y0, 349.5, y1), v_baja, 12)
                insert_centered(page, fitz.Rect(349.5, y0, 395.5, y1), v_media, 12)
                insert_centered(page, fitz.Rect(395.5, y0, 439.5, y1), v_alta, 12)
                
                # Missing middle column cell editable
                insert_text(page, fitz.Rect(439.5, y0, 601, y1), "")

                insert_text(page, fitz.Rect(601, y0, 757, y1), inter.get('obs',''), fs_sml)
                
            p3 = doc[2]
            fill_diag_row(p3, 174.5, 227.5, data['diagnostico'].get("1", {}))
            fill_diag_row(p3, 227.5, 272.5, data['diagnostico'].get("2", {}))
            fill_diag_row(p3, 272.5, 323.5, data['diagnostico'].get("3", {}))
            fill_diag_row(p3, 323.5, 371.5, data['diagnostico'].get("4", {}))
            fill_diag_row(p3, 371.5, 426.5, data['diagnostico'].get("5", {}))
            fill_diag_row(p3, 426.5, 471.5, data['diagnostico'].get("6", {}))
            fill_diag_row(p3, 471.5, 519.5, data['diagnostico'].get("7", {}))
            p4 = doc[3]
            fill_diag_row(p4, 63.5, 111.5, data['diagnostico'].get("8", {}))
            
            # Additional rows in page 4 (A.4 continuation)
            try:
                p4_tab = p4.find_tables().tables[1]
                for r in p4_tab.rows:
                    if r.bbox[1] > 170:
                        fill_diag_row(p4, r.bbox[1], r.bbox[3], {})
            except:
                pass
            
            # P5 Comunes Editable
            p5 = doc[4]
            x5 = [133.5, 297.5, 463.5, 628.5, 670.5, 713.5, 757]
            com = data['intervencion_comun']
            
            def fill_com_row(page, y0, y1, inter):
                insert_text(page, fitz.Rect(x5[0], y0, x5[1], y1), inter.get('txt1', ''))
                insert_text(page, fitz.Rect(x5[1], y0, x5[2], y1), inter.get('txt2', ''))
                insert_text(page, fitz.Rect(x5[2], y0, x5[3], y1), inter.get('txt3', ''))
                insert_centered(page, fitz.Rect(x5[3], y0, x5[4], y1), "X" if inter.get('corto') else "", 12)
                insert_centered(page, fitz.Rect(x5[4], y0, x5[5], y1), "X" if inter.get('medio') else "", 12)
                insert_centered(page, fitz.Rect(x5[5], y0, x5[6], y1), "X" if inter.get('largo') else "", 12)
                
            fill_com_row(p5, 164.5, 251.5, com.get('dinamica', {}))
            insert_text(p5, fitz.Rect(x5[0], 251.5, x5[-1], 272.5), "") # Fila Obs
            fill_com_row(p5, 272.5, 352.5, com.get('vivienda', {}))
            insert_text(p5, fitz.Rect(x5[0], 352.5, x5[-1], 379.5), "")
            fill_com_row(p5, 379.5, 477.5, com.get('economico', {}))
            insert_text(p5, fitz.Rect(x5[0], 477.5, x5[-1], 506.5), "")

            insert_centered(p5, fitz.Rect(56, 558, 70, 580), "1", fs_data)
            insert_centered(p5, fitz.Rect(70, 558, 330, 580), data['titular']['nombre'], fs_data)
            insert_centered(p5, fitz.Rect(340, 558, 440, 580), "Titular", fs_data)
            insert_centered(p5, fitz.Rect(450, 558, 550, 580), data['titular']['fecha_nac'], fs_data)

            # P6 Personalizada Editable
            p6 = doc[5]
            x6 = [144.5, 298.5, 463.5, 629.0, 671.5, 714.5, 758.0]
            tit = data['intervencion_titular']
            
            def fill_per_row(page, y0, y1, inter):
                insert_text(page, fitz.Rect(x6[0], y0, x6[1], y1), inter.get('txt1', ''))
                insert_text(page, fitz.Rect(x6[1], y0, x6[2], y1), inter.get('txt2', ''))
                insert_text(page, fitz.Rect(x6[2], y0, x6[3], y1), inter.get('txt3', ''))
                insert_centered(page, fitz.Rect(x6[3], y0, x6[4], y1), "X" if inter.get('corto') else "", 12)
                insert_centered(page, fitz.Rect(x6[4], y0, x6[5], y1), "X" if inter.get('medio') else "", 12)
                insert_centered(page, fitz.Rect(x6[5], y0, x6[6], y1), "X" if inter.get('largo') else "", 12)
                
            fill_per_row(p6, 127.5, 203.5, tit.get('desarrollo_personal', {}))
            insert_text(p6, fitz.Rect(x6[0], 203.5, x6[-1], 223.5), "")
            fill_per_row(p6, 223.5, 299.5, tit.get('desarrollo_comun', {}))
            insert_text(p6, fitz.Rect(x6[0], 299.5, x6[-1], 319.5), "")
            fill_per_row(p6, 319.5, 393.5, tit.get('sanitario', {}))
            insert_text(p6, fitz.Rect(x6[0], 393.5, x6[-1], 416.5), "")
            fill_per_row(p6, 416.5, 490.5, tit.get('formativo_laboral', {}))
            insert_text(p6, fitz.Rect(x6[0], 490.5, x6[-1], 509.5), "")
            
            # B.3 Dos filas extra (Laboral + Dificultades)
            fill_per_row(p6, 509.5, 583.5, {})
            insert_text(p6, fitz.Rect(x6[0], 583.5, x6[-1], 602.5), "")
            fill_per_row(p6, 602.5, 676.5, {})
            insert_text(p6, fitz.Rect(x6[0], 676.5, x6[-1], 695.5), "")

            # Resto miembros lo movemos un poco para no pisar las celdas nuevas
            insert_text(p6, fitz.Rect(56, 700, 750, 715), "-- SECCIÓN DE ANEXO: INTERVENCIÓN OTROS MIEMBROS --", 11)
            insert_text(p6, fitz.Rect(56, 720, 750, 800), data.get('intervencion_otros_miembros', ''), fs_data)

            # P7 Exoneraciones Generales
            p7 = doc[6]
            exo = data['exoneraciones']
            insert_text(p7, fitz.Rect(380, 110, 545, 138), "") # Bloques en blanco para todas
            insert_text(p7, fitz.Rect(380, 160, 545, 186), "")
            insert_text(p7, fitz.Rect(380, 209, 545, 260), "")
            insert_text(p7, fitz.Rect(380, 298, 545, 318), "")
            insert_text(p7, fitz.Rect(380, 335, 545, 347), "")
            insert_text(p7, fitz.Rect(380, 362, 545, 373), "")
            
            p7_ex = p7.search_for("Estudiante mayor de 16 años")
            if p7_ex:
                insert_text(p7, fitz.Rect(p7_ex[0].x1+3, p7_ex[0].y0-2, 545, p7_ex[0].y1+5), "N.º " + exo.get('menor_estudiando_num', '')) 
            
            insert_text(p7, fitz.Rect(380, 413, 545, 425), "")
            insert_text(p7, fitz.Rect(380, 432, 545, 443), "")
            insert_text(p7, fitz.Rect(380, 459, 545, 479), "")

            # B.3 Dos filas extra (Laboral + Dificultades y celdillas) en P7
            try:
                p7_tab_b3 = p7.find_tables().tables[1]
                # Hacemos editable todas las celdas de la tabla B.3
                for row in p7_tab_b3.rows:
                    for c_idx, cell in enumerate(row.cells):
                        if cell and c_idx > 0:
                            insert_text(p7, fitz.Rect(cell), "", 10)
            except:
                pass
            
            # C) OBSERVACIONES Y COMENTARIOS ADICIONALES (En Página 7 hacia abajo o P8)
            insert_text(p7, fitz.Rect(55, 690, 750, 800), "")

            # P8 Firmas
            p8 = doc[7]
            p8_fdo = p8.search_for("PERSONAS DESTINATARIAS FIRMANTES")
            if p8_fdo:
                base_y = p8_fdo[0].y1 + 10
                for i in range(8):
                    fir = exo.get('firmantes', [])[i] if i < len(exo.get('firmantes', [])) else ""
                    insert_text(p8, fitz.Rect(80, base_y + (25*i), 380, base_y + 20 + (25*i)), fir, fs_data) # Nombre firmante
                    insert_text(p8, fitz.Rect(390, base_y + (25*i), 550, base_y + 20 + (25*i)), "", fs_data) # Hueco firma
                    
                    
            # Caja de observaciones adicional P8
            insert_text(p8, fitz.Rect(55, 100, 750, 300), "")
                    
            # FECHA FINAL Editable
            insert_text(p8, fitz.Rect(325, 60, 550, 90), "")
            insert_text(p8, fitz.Rect(60, 490, 550, 530), "", 12) # Lugar y fecha extra

            pdf_bytes = doc.write()
            doc.close()
            
            st.success("¡Documento PLAPIN generado con éxito!")
            st.download_button("Descargar PDF", data=pdf_bytes, file_name="PLAPIN_Generado.pdf", mime="application/pdf")
            
        except Exception as e:
            import traceback
            st.error(f"Error procesando el PDF: {e}")
            st.code(traceback.format_exc())
