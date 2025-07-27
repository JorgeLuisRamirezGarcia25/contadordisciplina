import os

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    print("Error: No se puede exportar a PDF porque el módulo 'reportlab' no está instalado.\nInstala con: pip install reportlab")
    exit(1)

nombre_archivo = "test_reporte.pdf"
ruta_absoluta = os.path.abspath(nombre_archivo)

try:
    c = canvas.Canvas(ruta_absoluta, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Contadores de tareas por día (semana actual)")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, height - 80, "Usuario: Prueba")
    c.setFont("Helvetica", 12)
    y = height - 120
    for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]:
        texto = f"{dia}: 0 tareas completadas"
        c.drawString(70, y, texto)
        y -= 25
    c.save()
except Exception as e:
    print(f"Error al generar el PDF: {e}")
    exit(1)

if not os.path.exists(ruta_absoluta):
    print(f"Error: El PDF no se generó correctamente. No se encontró el archivo en:\n{ruta_absoluta}")
else:
    print(f"PDF generado correctamente en:\n{ruta_absoluta}")
    # Intentar abrir el PDF automáticamente (Linux)
    try:
        os.system(f'xdg-open "{ruta_absoluta}"')
    except Exception:
        pass