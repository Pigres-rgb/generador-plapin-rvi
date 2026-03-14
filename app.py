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
    api_key = st.text_input("Gemini API Key", type="password", help="Genera una clave gratuita en Google AI Studio")
    st.markdown("Esta clave no se guarda, se usa solo durante la sesión.")

st.header("2. Datos del Nuevo Caso Familiar")
caso_text = st.text_area("Pega aquí el caso, informe o notas de la familia:", height=300,
    placeholder="Ej: Sonia es una madre de 48 años con problemas de alcoholismo. Tiene una hija de 18 que abandonó los estudios y una de 16... Están en riesgo de desahucio.")

if st.button("Generar PLAPIN en PDF", type="primary"):
    if not api_key:
        st.error("Por favor, introduce tu Gemini API Key en la barra lateral.")
        st.stop()
    if not caso_text.strip():
        st.error("Por favor, introduce el texto del caso familiar.")
        st.stop()
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')

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
            if json_str.startswith("```json"):
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif json_str.startswith("```"):
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
        except Exception as e:
            st.error(f"Error parseando datos: {e}")
            st.code(response.text)
            st.stop()
            
    with st.spinner("Rellenando plantilla PDF Oficial..."):
        try:
            # FITZ LOGIC
            doc = fitz.open("Plantilla_RVI.pdf")
            color, font, fs_data, fs_txt, fs_sml = (0, 0, 0.7), "hebo", 10, 9, 8
            
            def insert_centered(page, rect, text, fs=12):
                page.insert_textbox(rect, str(text), fontname=font, fontsize=fs, color=color, align=fitz.TEXT_ALIGN_CENTER)
            def insert_text(page, rect, text, fs=fs_sml):
                pad_rect = fitz.Rect(rect.x0+2, rect.y0+2, rect.x1-2, rect.y1-2)
                page.insert_textbox(pad_rect, str(text), fontname=font, fontsize=fs, color=color, align=fitz.TEXT_ALIGN_LEFT)

            p1 = doc[0]
            v = [57.5, 85.5, 263.5, 426.5, 496.5, 558.5]
            insert_centered(p1, fitz.Rect(v[1], 382.5, v[2], 400.5), data['titular']['nombre'], fs_data)
            insert_centered(p1, fitz.Rect(v[2], 382.5, v[3], 400.5), "Titular", fs_data)
            insert_centered(p1, fitz.Rect(v[3], 382.5, v[4], 400.5), data['titular']['fecha_nac'], fs_data)
            
            if data['persona_2']['existe']:
                insert_centered(p1, fitz.Rect(v[0], 400.5, v[1], 421.5), "2", fs_data)
                insert_centered(p1, fitz.Rect(v[1], 400.5, v[2], 421.5), data['persona_2']['nombre'], fs_data)
                insert_centered(p1, fitz.Rect(v[2], 400.5, v[3], 421.5), data['persona_2']['parentesco'], fs_data)
                insert_centered(p1, fitz.Rect(v[3], 400.5, v[4], 421.5), data['persona_2']['fecha_nac'], fs_data)
            if data['persona_3']['existe']:
                insert_centered(p1, fitz.Rect(v[0], 421.5, v[1], 442.5), "3", fs_data)
                insert_centered(p1, fitz.Rect(v[1], 421.5, v[2], 442.5), data['persona_3']['nombre'], fs_data)
                insert_centered(p1, fitz.Rect(v[2], 421.5, v[3], 442.5), data['persona_3']['parentesco'], fs_data)
                insert_centered(p1, fitz.Rect(v[3], 421.5, v[4], 442.5), data['persona_3']['fecha_nac'], fs_data)
            
            res3 = p1.search_for("NO")
            for r in res3:
                 if abs(r.y0 - p1.search_for("SÍ (debe adjuntarse)")[0].y0) < 20:
                     p1.insert_text(fitz.Point(r.x1 + 10, r.y0+8), "X", fontname=font, fontsize=12, color=color)

            # P3 y P4 Diagnostics
            def fill_diag_row(page, y0, y1, inter, obs):
                if inter['si'] or inter.get('si') == "true":
                    insert_centered(page, fitz.Rect(253, y0, 276.5, y1), "X", 12)
                    pr = str(inter.get('prioridad','')).upper()
                    if pr == "BAJA": insert_centered(page, fitz.Rect(322.5, y0, 349.5, y1), "X", 12)
                    elif pr == "MEDIA": insert_centered(page, fitz.Rect(349.5, y0, 395.5, y1), "X", 12)
                    elif pr in ["ALTA", "ALTO"]: insert_centered(page, fitz.Rect(395.5, y0, 439.5, y1), "X", 12)
                else:
                    insert_centered(page, fitz.Rect(276.5, y0, 322.5, y1), "X", 12)
                insert_text(page, fitz.Rect(601, y0, 757, y1), inter.get('obs',''), fs_sml)
                
            p3 = doc[2]
            fill_diag_row(p3, 174.5, 227.5, data['diagnostico']["1"], data['diagnostico']["1"]['obs'])
            fill_diag_row(p3, 227.5, 272.5, data['diagnostico']["2"], data['diagnostico']["2"]['obs'])
            fill_diag_row(p3, 272.5, 323.5, data['diagnostico']["3"], data['diagnostico']["3"]['obs'])
            fill_diag_row(p3, 323.5, 371.5, data['diagnostico']["4"], data['diagnostico']["4"]['obs'])
            fill_diag_row(p3, 371.5, 426.5, data['diagnostico']["5"], data['diagnostico']["5"]['obs'])
            fill_diag_row(p3, 426.5, 471.5, data['diagnostico']["6"], data['diagnostico']["6"]['obs'])
            fill_diag_row(p3, 471.5, 519.5, data['diagnostico']["7"], data['diagnostico']["7"]['obs'])
            p4 = doc[3]
            fill_diag_row(p4, 63.5, 111.5, data['diagnostico']["8"], data['diagnostico']["8"]['obs'])
            
            # P5 Comunes
            p5 = doc[4]
            x5 = [133.5, 297.5, 463.5, 628.5, 670.5, 713.5, 757]
            com = data['intervencion_comun']
            insert_text(p5, fitz.Rect(x5[0], 164.5, x5[1], 251.5), com['dinamica']['txt1'])
            insert_text(p5, fitz.Rect(x5[1], 164.5, x5[2], 251.5), com['dinamica']['txt2'])
            insert_text(p5, fitz.Rect(x5[2], 164.5, x5[3], 251.5), com['dinamica']['txt3'])
            insert_text(p5, fitz.Rect(x5[0], 272.5, x5[1], 352.5), com['vivienda']['txt1'])
            insert_text(p5, fitz.Rect(x5[1], 272.5, x5[2], 352.5), com['vivienda']['txt2'])
            insert_text(p5, fitz.Rect(x5[2], 272.5, x5[3], 352.5), com['vivienda']['txt3'])
            if com['vivienda'].get('corto'): insert_centered(p5, fitz.Rect(x5[3], 272.5, x5[4], 352.5), "X", 12)
            insert_text(p5, fitz.Rect(x5[0], 379.5, x5[1], 477.5), com['economico']['txt1'])
            insert_text(p5, fitz.Rect(x5[1], 379.5, x5[2], 477.5), com['economico']['txt2'])
            insert_text(p5, fitz.Rect(x5[2], 379.5, x5[3], 477.5), com['economico']['txt3'])
            if com['economico'].get('corto'): insert_centered(p5, fitz.Rect(x5[3], 379.5, x5[4], 477.5), "X", 12)
            if com['economico'].get('medio'): insert_centered(p5, fitz.Rect(x5[4], 379.5, x5[5], 477.5), "X", 12)

            insert_centered(p5, fitz.Rect(56, 558, 70, 580), "1", fs_data)
            insert_centered(p5, fitz.Rect(70, 558, 330, 580), data['titular']['nombre'], fs_data)
            insert_centered(p5, fitz.Rect(340, 558, 440, 580), "Titular", fs_data)
            insert_centered(p5, fitz.Rect(450, 558, 550, 580), data['titular']['fecha_nac'], fs_data)

            # P6 Personalizada Titular
            p6 = doc[5]
            x6 = [144.5, 298.5, 463.5, 629.0, 671.5, 714.5, 758.0]
            tit = data['intervencion_titular']
            insert_text(p6, fitz.Rect(x6[0], 127.5, x6[1], 203.5), tit['desarrollo_personal']['txt1'])
            insert_text(p6, fitz.Rect(x6[1], 127.5, x6[2], 203.5), tit['desarrollo_personal']['txt2'])
            insert_text(p6, fitz.Rect(x6[2], 127.5, x6[3], 203.5), tit['desarrollo_personal']['txt3'])
            insert_text(p6, fitz.Rect(x6[0], 223.5, x6[1], 299.5), tit['desarrollo_comun']['txt1'])
            insert_text(p6, fitz.Rect(x6[1], 223.5, x6[2], 299.5), tit['desarrollo_comun']['txt2'])
            insert_text(p6, fitz.Rect(x6[2], 223.5, x6[3], 299.5), tit['desarrollo_comun']['txt3'])
            insert_text(p6, fitz.Rect(x6[0], 319.5, x6[1], 393.5), tit['sanitario']['txt1'])
            insert_text(p6, fitz.Rect(x6[1], 319.5, x6[2], 393.5), tit['sanitario']['txt2'])
            insert_text(p6, fitz.Rect(x6[2], 319.5, x6[3], 393.5), tit['sanitario']['txt3'])
            if tit['sanitario'].get('corto'): insert_centered(p6, fitz.Rect(x6[3], 319.5, x6[4], 393.5), "X", 12)
            insert_text(p6, fitz.Rect(x6[0], 416.5, x6[1], 490.5), tit['formativo_laboral']['txt1'])
            insert_text(p6, fitz.Rect(x6[1], 416.5, x6[2], 490.5), tit['formativo_laboral']['txt2'])
            insert_text(p6, fitz.Rect(x6[2], 416.5, x6[3], 490.5), tit['formativo_laboral']['txt3'])
            if tit['formativo_laboral'].get('medio'): insert_centered(p6, fitz.Rect(x6[4], 416.5, x6[5], 490.5), "X", 12)

            # Resto miembros
            p6.insert_text(fitz.Point(56, 525), "-- SECCIÓN DE ANEXO: INTERVENCIÓN OTROS MIEMBROS --", fontname="hebo", fontsize=11, color=color)
            p6.insert_textbox(fitz.Rect(56, 535, 750, 680), data['intervencion_otros_miembros'], fontname="helv", fontsize=fs_data, color=color)

            # P7 Exoneraciones
            p7 = doc[6]
            exo = data['exoneraciones']
            p7_ex = p7.search_for("Estudiante mayor de 16 años")
            if p7_ex and exo.get('menor_estudiando_num'):
                insert_centered(p7, fitz.Rect(p7_ex[0].x1+3, p7_ex[0].y0, p7_ex[0].x1+60, p7_ex[0].y1), "N.º " + exo['menor_estudiando_num'], 12) 
            p7_des = p7.search_for("Situación de desempleo")
            if p7_des and exo.get('desempleo_derivacion_labora_nums'):
                insert_centered(p7, fitz.Rect(p7_des[0].x1+10, p7_des[0].y0, p7_des[0].x1+120, p7_des[0].y1), "N.º " + exo['desempleo_derivacion_labora_nums'], 12) 
            p7_lab = p7.search_for("LABORA")
            if p7_lab:
                insert_centered(p7, fitz.Rect(p7_lab[0].x1+5, p7_lab[0].y0, p7_lab[0].x1+40, p7_lab[0].y1), "X", 12) 

            # P8 Firmas
            p8 = doc[7]
            p8_fdo = p8.search_for("PERSONAS DESTINATARIAS FIRMANTES")
            if p8_fdo:
                base_y = p8_fdo[0].y1 + 10
                for i, fir in enumerate(exo.get('firmantes', [])):
                    p8.insert_text(fitz.Point(80, base_y + 10 + (25*i)), fir, fontname=font, fontsize=fs_data, color=color)

            pdf_bytes = doc.write()
            doc.close()
            
            st.success("¡Documento PLAPIN generado con éxito!")
            st.download_button("Descargar PDF", data=pdf_bytes, file_name="PLAPIN_Generado.pdf", mime="application/pdf")
            
        except Exception as e:
            st.error(f"Error procesando el PDF: {e}")
