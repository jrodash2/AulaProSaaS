from io import BytesIO
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from academico.models import GradoInstitucion, Seccion
from .models import Alumno, AlumnoEncargado, Encargado, Familia, ImportacionAlumnos, Inscripcion

HEADERS=["CUI","PRIMER_NOMBRE","SEGUNDO_NOMBRE","OTROS_NOMBRES","PRIMER_APELLIDO","SEGUNDO_APELLIDO","FECHA_NACIMIENTO","SEXO","TELEFONO","EMAIL","DIRECCION","CODIGO_FAMILIA","CUI_ENCARGADO","NOMBRES_ENCARGADO","APELLIDOS_ENCARGADO","PARENTESCO","TELEFONO_ENCARGADO","EMAIL_ENCARGADO","PRINCIPAL","RESPONSABLE_FINANCIERO","CODIGO_OFERTA","CODIGO_GRADO","CODIGO_SECCION"]

def crear_plantilla(institucion,ciclo):
    wb=Workbook(); ws=wb.active; ws.title="ESTUDIANTES"; ws.append(HEADERS); ws.freeze_panes="A2"
    grados=wb.create_sheet("CATALOGO_GRADOS"); grados.append(["CODIGO_OFERTA","OFERTA","CODIGO_GRADO","GRADO"])
    for g in GradoInstitucion.objects.filter(institucion=institucion,ciclo=ciclo,activo=True).select_related("oferta"): grados.append([g.oferta.codigo_interno,g.oferta.nombre_mostrado,g.codigo,g.nombre])
    sec=wb.create_sheet("CATALOGO_SECCIONES"); sec.append(["CODIGO_GRADO","CODIGO_SECCION","SECCION","JORNADA"])
    for s in Seccion.objects.filter(institucion=institucion,ciclo=ciclo,activa=True).select_related("grado","jornada"): sec.append([s.grado.codigo,s.codigo,s.nombre,s.jornada.nombre if s.jornada else ""])
    ins=wb.create_sheet("INSTRUCCIONES"); ins.append(["PLANTILLA AULAPRO"]); ins.append(["Requeridos: primer nombre, primer apellido, fecha de nacimiento, sexo, oferta, grado y sección."]); ins.append(["CUI: 13 dígitos o vacío si está pendiente. Fecha: AAAA-MM-DD. Sexo: F, M u O."]); ins.append(["Use los códigos exactos de las hojas auxiliares. No agregue una columna de institución."])
    out=BytesIO(); wb.save(out); out.seek(0); return out

def prevalidar(archivo,institucion,ciclo):
    archivo.seek(0)
    try: wb=load_workbook(archivo,read_only=True,data_only=True)
    except Exception as exc: return {"filas":[],"errores":[f"Archivo XLSX inválido: {exc}"],"advertencias":[]}
    if "ESTUDIANTES" not in wb.sheetnames: return {"filas":[],"errores":["No existe la hoja ESTUDIANTES."],"advertencias":[]}
    ws=wb["ESTUDIANTES"]; headers=[str(v or "").strip().upper() for v in next(ws.iter_rows(values_only=True))]
    idx={h:i for i,h in enumerate(headers)}; faltantes=[h for h in HEADERS if h not in idx]
    if faltantes: return {"filas":[],"errores":["Faltan columnas: "+", ".join(faltantes)],"advertencias":[]}
    existentes={a.cui:a for a in Alumno.objects.filter(institucion=institucion,cui__isnull=False)}
    familias={f.codigo:f for f in Familia.objects.filter(institucion=institucion,codigo__isnull=False)}
    encargados={e.cui:e for e in Encargado.objects.filter(institucion=institucion,cui__isnull=False)}
    grados={(g.oferta.codigo_interno,g.codigo):g for g in GradoInstitucion.objects.filter(institucion=institucion,ciclo=ciclo).select_related("oferta")}
    secciones={(s.grado_id,s.codigo):s for s in Seccion.objects.filter(institucion=institucion,ciclo=ciclo).select_related("grado")}
    vistos=set(); filas=[]; errores=[]; advertencias=[]
    for numero,raw in enumerate(ws.iter_rows(min_row=2,values_only=True),2):
        if not any(v not in (None,"") for v in raw): continue
        data={h:raw[i] for h,i in idx.items()}; row_errors=[]; row_warn=[]
        cui=str(data["CUI"] or "").strip().replace(".0","")
        if cui and (not cui.isdigit() or len(cui)!=13): row_errors.append("CUI inválido")
        if cui and cui in vistos: row_errors.append("CUI repetido en el archivo")
        if cui: vistos.add(cui)
        for req in ("PRIMER_NOMBRE","PRIMER_APELLIDO","FECHA_NACIMIENTO","SEXO","CODIGO_OFERTA","CODIGO_GRADO","CODIGO_SECCION"):
            if not data[req]: row_errors.append(f"{req} es requerido")
        grado=grados.get((str(data["CODIGO_OFERTA"] or "").strip(),str(data["CODIGO_GRADO"] or "").strip()))
        if not grado: row_errors.append("Grado no encontrado")
        seccion=secciones.get((grado.pk,str(data["CODIGO_SECCION"] or "").strip())) if grado else None
        if grado and not seccion: row_errors.append("Sección no encontrada")
        alumno=existentes.get(cui) if cui else None
        if alumno and alumno.nombre_completo.lower()!=f'{data["PRIMER_NOMBRE"]} {data["PRIMER_APELLIDO"]}'.strip().lower(): row_warn.append("El CUI existe y los nombres no coinciden; no se actualizarán datos personales")
        if alumno and Inscripcion.objects.filter(alumno=alumno,ciclo=ciclo,estado=Inscripcion.Estado.ACTIVA).exists(): row_errors.append("El alumno ya tiene inscripción activa en este ciclo")
        fila={"numero":numero,"data":data,"cui":cui,"alumno":alumno,"grado":grado,"seccion":seccion,"familia":familias.get(str(data["CODIGO_FAMILIA"] or "").strip()),"encargado":encargados.get(str(data["CUI_ENCARGADO"] or "").strip()),"errores":row_errors,"advertencias":row_warn,"accion":"Alumno existente / nueva inscripción" if alumno else "Nuevo alumno"}
        filas.append(fila); errores.extend([f"Fila {numero}: {e}" for e in row_errors]); advertencias.extend([f"Fila {numero}: {e}" for e in row_warn])
    if not errores:
        from suscripciones.services import validar_cupo_alumnos
        try: validar_cupo_alumnos(institucion,len(filas))
        except ValidationError as exc: errores.extend(exc.messages)
    return {"filas":filas,"errores":errores,"advertencias":advertencias}

@transaction.atomic
def ejecutar_importacion(registro):
    resultado=prevalidar(registro.archivo_original,registro.institucion,registro.ciclo)
    if resultado["errores"]:
        registro.estado=ImportacionAlumnos.Estado.FALLIDA; registro.errores=len(resultado["errores"]); registro.detalle_errores=resultado["errores"]; registro.fecha_fin=timezone.now(); registro.save(); raise ValidationError("La importación contiene errores críticos.")
    creados=existentes=inscripciones=0
    for fila in resultado["filas"]:
        d=fila["data"]; alumno=fila["alumno"]
        if not alumno:
            alumno=Alumno.objects.create(institucion=registro.institucion,familia=fila["familia"],cui=fila["cui"] or None,primer_nombre=str(d["PRIMER_NOMBRE"]),segundo_nombre=str(d["SEGUNDO_NOMBRE"] or ""),otros_nombres=str(d["OTROS_NOMBRES"] or ""),primer_apellido=str(d["PRIMER_APELLIDO"]),segundo_apellido=str(d["SEGUNDO_APELLIDO"] or ""),fecha_nacimiento=d["FECHA_NACIMIENTO"],sexo=str(d["SEXO"]).upper(),telefono=str(d["TELEFONO"] or ""),email=str(d["EMAIL"] or ""),direccion=str(d["DIRECCION"] or ""),fecha_ingreso=timezone.localdate()); creados+=1
        else: existentes+=1
        enc_cui=str(d["CUI_ENCARGADO"] or "").strip() or None; encargado=fila["encargado"]
        if not encargado and d["NOMBRES_ENCARGADO"]:
            encargado=Encargado.objects.create(institucion=registro.institucion,cui=enc_cui,nombres=str(d["NOMBRES_ENCARGADO"]),apellidos=str(d["APELLIDOS_ENCARGADO"] or ""),telefono=str(d["TELEFONO_ENCARGADO"] or ""),email=str(d["EMAIL_ENCARGADO"] or ""))
        if encargado: AlumnoEncargado.objects.get_or_create(institucion=registro.institucion,alumno=alumno,encargado=encargado,defaults={"parentesco":str(d["PARENTESCO"] or "OTRO").upper(),"parentesco_otro":"No especificado" if str(d["PARENTESCO"] or "OTRO").upper()=="OTRO" else "","es_principal":str(d["PRINCIPAL"] or "").upper() in ("SI","SÍ","1","TRUE"),"es_responsable_financiero":str(d["RESPONSABLE_FINANCIERO"] or "").upper() in ("SI","SÍ","1","TRUE")})
        g=fila["grado"]; Inscripcion.objects.create(institucion=registro.institucion,alumno=alumno,ciclo=registro.ciclo,oferta_academica=g.oferta,grado=g,seccion=fila["seccion"],fecha_inscripcion=timezone.localdate()); inscripciones+=1
    registro.estado=ImportacionAlumnos.Estado.PROCESADA; registro.total_filas=len(resultado["filas"]); registro.creados=creados; registro.actualizados=existentes; registro.inscripciones_creadas=inscripciones; registro.errores=0; registro.fecha_fin=timezone.now(); registro.save(); return registro
