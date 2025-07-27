import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime, timedelta
import sqlite3
import hashlib
import sys

class App:
    def no_realizada_tarea(self):
        ahora = datetime.now()
        fecha_str = ahora.strftime("%Y-%m-%d")
        if self.usuario_id is None:
            messagebox.showerror("Error", "No hay usuario seleccionado. Selecciona un usuario antes de marcar tarea no realizada.")
            return
        # Crear tabla si no existe
        self.c.execute('''CREATE TABLE IF NOT EXISTS tareas_no_realizadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
        # Insertar registro
        self.c.execute("INSERT INTO tareas_no_realizadas (usuario_id, fecha) VALUES (?, ?)", (self.usuario_id, fecha_str))
        self.conn.commit()
        dia_nombre_es = self.dias[ahora.weekday()]
        self.contadores_no_realizadas[dia_nombre_es] += 1
        self.labels_dias_no_realizadas[dia_nombre_es].config(text=str(self.contadores_no_realizadas[dia_nombre_es]))
        self.labels_dias_no_realizadas[dia_nombre_es].config(bg="#f9e0e0")
        self.root.after(800, lambda: self.labels_dias_no_realizadas[dia_nombre_es].config(bg="#f7fbff"))
        messagebox.showinfo("Tarea no realizada", f"¡Tarea NO realizada para {dia_nombre_es}!")
    def ensure_usuario_id_column(self):
        cols_tareas = self.c.execute("PRAGMA table_info(tareas_completadas)").fetchall()
        if not any(col[1] == "usuario_id" for col in cols_tareas):
            self.c.execute("ALTER TABLE tareas_completadas ADD COLUMN usuario_id INTEGER NOT NULL DEFAULT 1")
            self.conn.commit()
    def ensure_password_column(self):
        cols_usuarios = self.c.execute("PRAGMA table_info(usuarios)").fetchall()
        if not any(col[1] == "password" for col in cols_usuarios):
            self.c.execute("ALTER TABLE usuarios ADD COLUMN password TEXT NOT NULL DEFAULT ''")
            self.conn.commit()
    def hash_password(self, password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    # ...existing code...
    def __init__(self, root):
        self.root = root
        self.root.title("Seguimiento de Tareas Semanales")
        self.root.configure(bg="#eaf6fb")
        self.root.minsize(700, 600)
        self.tooltip = None  # Inicializa el atributo tooltip

        # Conectarse a la base de datos
        self.conn = sqlite3.connect('tareas.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL)
                        ''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS tareas_completadas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            usuario_id INTEGER,
                            fecha TEXT NOT NULL,
                            hora TEXT NOT NULL,
                            FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
        self.conn.commit()
        self.ensure_usuario_id_column()

        # Variables para los contadores de cada día
        self.dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        self.contadores = {dia: 0 for dia in self.dias}
        self.contadores_no_realizadas = {dia: 0 for dia in self.dias}

        # Obtener la fecha actual
        self.fecha_actual = datetime.now()
        self.dia_actual = self.fecha_actual.strftime("%A")
        self.dia_actual_idx = self.fecha_actual.weekday()  # lunes=0, domingo=6

        # El botón está habilitado todos los días
        self.habilitado = True

        # Usuario actual
        self.usuario_id = None
        self.usuario_nombre = None

        # Ventana de usuario
        self.seleccionar_usuario()

        # Corte automático de mes si es necesario
        self.corte_mes_automatico()

        # Crear la interfaz
        self.crear_widgets()

        # Cargar los datos de la semana actual
        self.cargar_semana_actual()
    def crear_widgets(self):
        # Este método puede estar vacío si la interfaz ya se crea en __init__,
        # o puedes mover aquí la creación de widgets de la interfaz principal.
        # Por ahora, lo dejamos vacío para evitar el error.
        pass

    def corte_mes_automatico(self):
        """
        Realiza el corte de mes automáticamente si detecta tareas del mes anterior sin cortar.
        """
        # Solo ejecuta si hay usuario seleccionado
        if not self.usuario_id:
            return
        hoy = self.fecha_actual
        mes_actual = hoy.month
        anio_actual = hoy.year
        import calendar
        # Buscar tareas de meses anteriores
        self.c.execute("SELECT fecha FROM tareas_completadas WHERE usuario_id=? ORDER BY fecha ASC LIMIT 1", (self.usuario_id,))
        res = self.c.fetchone()
        if not res:
            return  # No hay tareas
        # Usar el import global de datetime
        fecha_mas_antigua = datetime.strptime(res[0], "%Y-%m-%d")
        mes_antiguo = fecha_mas_antigua.month
        anio_antiguo = fecha_mas_antigua.year
        # Si hay tareas de un mes anterior al actual, hacer corte para cada mes pendiente
        while (anio_antiguo < anio_actual) or (anio_antiguo == anio_actual and mes_antiguo < mes_actual):
            primer_dia = f"{anio_antiguo}-{mes_antiguo:02d}-01"
            ultimo_dia = f"{anio_antiguo}-{mes_antiguo:02d}-{calendar.monthrange(anio_antiguo, mes_antiguo)[1]:02d}"
            # Contar tareas del mes
            self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE fecha BETWEEN ? AND ? AND usuario_id=?", (primer_dia, ultimo_dia, self.usuario_id))
            total_mes = self.c.fetchone()[0]
            if total_mes > 0:
                # Guardar resumen en tabla historica
                self.c.execute('''CREATE TABLE IF NOT EXISTS resumen_mensual (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER,
                    mes INTEGER,
                    anio INTEGER,
                    total INTEGER,
                    fecha_corte TEXT,
                    FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
                self.c.execute("INSERT INTO resumen_mensual (usuario_id, mes, anio, total, fecha_corte) VALUES (?, ?, ?, ?, ?)",
                    (self.usuario_id, mes_antiguo, anio_antiguo, total_mes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                # Borrar tareas del mes
                self.c.execute("DELETE FROM tareas_completadas WHERE fecha BETWEEN ? AND ? AND usuario_id=?", (primer_dia, ultimo_dia, self.usuario_id))
                self.conn.commit()
            # Avanzar al siguiente mes
            if mes_antiguo == 12:
                mes_antiguo = 1
                anio_antiguo += 1
            else:
                mes_antiguo += 1

        # --- Top user and date info ---
        frame_top = tk.Frame(self.root, bg="#eaf6fb")
        frame_top.pack(pady=(18, 6), padx=20, fill=tk.X)
        user_icon = tk.Label(frame_top, text="👤", font=("Arial", 20, "bold"), bg="#eaf6fb")
        user_icon.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_usuario = tk.Label(frame_top, text=f"Usuario: {self.usuario_nombre}", font=("Arial", 15, "bold"), bg="#eaf6fb", fg="#2a3a5c")
        self.lbl_usuario.pack(side=tk.LEFT, padx=(0, 16))
        date_icon = tk.Label(frame_top, text="📅", font=("Arial", 16), bg="#eaf6fb")
        date_icon.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_fecha = tk.Label(frame_top, text=f"Fecha: {self.fecha_actual.strftime('%Y-%m-%d')}", font=("Arial", 13, "bold"), bg="#eaf6fb", fg="#2a3a5c")
        self.lbl_fecha.pack(side=tk.LEFT)

        # Separador visual
        sep1 = tk.Frame(self.root, height=2, bd=0, bg="#b2bec3")
        sep1.pack(fill=tk.X, padx=30, pady=8)

        # --- Días de la semana ---
        self.frame_dias = tk.LabelFrame(self.root, text="Tareas por día", font=("Arial", 14, "bold"), bg="#f7fbff", fg="#2a3a5c", bd=2, relief=tk.RIDGE, labelanchor="n")
        self.frame_dias.pack(pady=10, padx=40, fill=tk.X)

        self.labels_dias = {}
        self.labels_dias_no_realizadas = {}
        for i, dia in enumerate(self.dias):
            lbl_dia = tk.Label(self.frame_dias, text=f"{dia}", font=("Arial", 12, "bold"), bg="#f7fbff", fg="#2a3a5c")
            lbl_dia.grid(row=i, column=0, padx=(18, 8), pady=6, sticky="w")
            lbl_contador = tk.Label(self.frame_dias, text="0", font=("Arial", 12, "bold"), bg="#f7fbff", fg="#1a7f37", width=4, relief=tk.SUNKEN, bd=2)
            lbl_contador.grid(row=i, column=1, padx=(8, 8), pady=6)
            self.labels_dias[dia] = lbl_contador
            lbl_no_realizadas = tk.Label(self.frame_dias, text="0", font=("Arial", 12, "bold"), bg="#f7fbff", fg="#c0392b", width=4, relief=tk.SUNKEN, bd=2)
            lbl_no_realizadas.grid(row=i, column=2, padx=(8, 18), pady=6)
            self.labels_dias_no_realizadas[dia] = lbl_no_realizadas
        # Encabezados
        tk.Label(self.frame_dias, text="Hechas", font=("Arial", 11, "bold"), bg="#f7fbff", fg="#1a7f37").grid(row=0, column=1, sticky="n", padx=8)
        tk.Label(self.frame_dias, text="No hechas", font=("Arial", 11, "bold"), bg="#f7fbff", fg="#c0392b").grid(row=0, column=2, sticky="n", padx=8)

        # Separador visual
        sep2 = tk.Frame(self.root, height=2, bd=0, bg="#b2bec3")
        sep2.pack(fill=tk.X, padx=30, pady=8)

        # --- Botones principales ---
        frame_btns = tk.Frame(self.root, bg="#eaf6fb")
        frame_btns.pack(pady=10, padx=40, fill=tk.X)

        btn_font = ("Arial", 11)

        self.btn_completar = tk.Button(frame_btns, text="✅\nCompletar\nTarea", command=self.completar_tarea, bg="#1a7f37", fg="white", activebackground="#2ecc71", activeforeground="white", relief=tk.RAISED, bd=3, font=btn_font, height=2, width=15)
        self.btn_completar.grid(row=0, column=0, padx=8, pady=8, sticky="nsew", ipadx=4, ipady=4)
        self.btn_completar.bind("<Enter>", lambda e: self._show_tooltip("Marca la tarea como completada para hoy", self.btn_completar))
        self.btn_completar.bind("<Leave>", lambda e: self._hide_tooltip())

        self.btn_no_realizada = tk.Button(frame_btns, text="❌\nNo realizada\nhoy", command=self.no_realizada_tarea, bg="#c0392b", fg="white", activebackground="#e74c3c", activeforeground="white", relief=tk.RAISED, bd=3, font=btn_font, height=2, width=15)
        self.btn_no_realizada.grid(row=0, column=3, padx=8, pady=8, sticky="nsew", ipadx=4, ipady=4)
        self.btn_no_realizada.bind("<Enter>", lambda e: self._show_tooltip("Marca la tarea de hoy como NO realizada", self.btn_no_realizada))
        self.btn_no_realizada.bind("<Leave>", lambda e: self._hide_tooltip())

        self.btn_exportar_pdf = tk.Button(frame_btns, text="🗎\nExportar\nPDF", command=self.exportar_pdf, bg="#2a3a5c", fg="white", activebackground="#34495e", activeforeground="white", relief=tk.RAISED, bd=3, font=btn_font)
        self.btn_exportar_pdf.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        self.btn_exportar_pdf.bind("<Enter>", lambda e: self._show_tooltip("Exporta el resumen semanal a PDF", self.btn_exportar_pdf))
        self.btn_exportar_pdf.bind("<Leave>", lambda e: self._hide_tooltip())

        self.btn_grafica_semana = tk.Button(frame_btns, text="📊\nGráfica\nsemanal", command=self.grafica_semanal, bg="#8e44ad", fg="white", font=btn_font)
        self.btn_grafica_semana.grid(row=0, column=2, padx=8, pady=8, sticky="nsew")

        self.btn_grafica_mes = tk.Button(frame_btns, text="📈\nGráfica\nmensual", command=self.grafica_mensual, bg="#2980b9", fg="white", font=btn_font)
        self.btn_grafica_mes.grid(row=1, column=0, padx=8, pady=8, sticky="nsew")

        self.btn_grafica_anual = tk.Button(frame_btns, text="📅\nGráfica\nanual", command=self.grafica_anual, bg="#16a085", fg="white", font=btn_font)
        self.btn_grafica_anual.grid(row=1, column=1, padx=8, pady=8, sticky="nsew")

        self.btn_corte_mes = tk.Button(frame_btns, text="🔄\nCorte\nde mes", command=self.corte_mes, bg="#e67e22", fg="white", font=btn_font)
        self.btn_corte_mes.grid(row=1, column=2, padx=8, pady=8, sticky="nsew")

        self.btn_cambiar_pass = tk.Button(frame_btns, text="🔒\nCambiar\ncontraseña", command=self.cambiar_password, bg="#e67e22", fg="white", activebackground="#f39c12", activeforeground="white", relief=tk.RAISED, bd=2, font=btn_font)
        self.btn_cambiar_pass.grid(row=2, column=0, padx=8, pady=8, sticky="nsew")
        self.btn_cambiar_pass.bind("<Enter>", lambda e: self._show_tooltip("Cambia tu contraseña de usuario", self.btn_cambiar_pass))
        self.btn_cambiar_pass.bind("<Leave>", lambda e: self._hide_tooltip())

        self.btn_control_usuarios = tk.Button(frame_btns, text="👥\nControl\nde usuarios", command=self.control_usuarios, bg="#2980b9", fg="white", activebackground="#3498db", activeforeground="white", relief=tk.RAISED, bd=2, font=("Arial", 11))
        self.btn_control_usuarios.grid(row=2, column=1, padx=8, pady=8, sticky="nsew")
        self.btn_control_usuarios.bind("<Enter>", lambda e: self._show_tooltip("Ver usuarios y tareas realizadas", self.btn_control_usuarios))
        self.btn_control_usuarios.bind("<Leave>", lambda e: self._hide_tooltip())

        self.btn_agregar_usuario = tk.Button(frame_btns, text="➕\nAgregar\nusuario", command=self.agregar_usuario, font=("Arial", 11), bg="#16a085", fg="white", activebackground="#1abc9c", activeforeground="white", relief=tk.RAISED, bd=2, padx=10, pady=6)
        self.btn_agregar_usuario.grid(row=2, column=2, padx=8, pady=8, sticky="nsew")
        self.btn_agregar_usuario.bind("<Enter>", lambda e: self._show_tooltip("Crear un nuevo usuario", self.btn_agregar_usuario))
        self.btn_agregar_usuario.bind("<Leave>", lambda e: self._hide_tooltip())

        for i in range(3):
            frame_btns.rowconfigure(i, weight=1)
        for j in range(4):
            frame_btns.columnconfigure(j, weight=1)
    def grafica_semanal(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib no está instalado. Instala con: pip install matplotlib")
            return
        dias = self.dias
        valores = [self.contadores[dia] for dia in dias]
        valores_no = [self.contadores_no_realizadas[dia] for dia in dias]
        plt.figure(figsize=(8,4))
        width = 0.35
        x = range(len(dias))
        plt.bar(x, valores, width=width, color="#2980b9", label="Hechas")
        plt.bar([i+width for i in x], valores_no, width=width, color="#c0392b", label="No hechas")
        plt.xticks([i+width/2 for i in x], dias)
        plt.title(f"Tareas semanales ({self.usuario_nombre})")
        plt.ylabel("Tareas")
        plt.xlabel("Día")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def grafica_mensual(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib no está instalado. Instala con: pip install matplotlib")
            return
        # Obtener tareas por día del mes actual
        hoy = self.fecha_actual
        mes = hoy.month
        anio = hoy.year
        import calendar
        dias_mes = calendar.monthrange(anio, mes)[1]
        dias = [f"{i+1:02d}" for i in range(dias_mes)]
        valores = []
        valores_no = []
        for i in range(dias_mes):
            fecha = f"{anio}-{mes:02d}-{i+1:02d}"
            self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE fecha=? AND usuario_id=?", (fecha, self.usuario_id))
            valores.append(self.c.fetchone()[0])
            self.c.execute("CREATE TABLE IF NOT EXISTS tareas_no_realizadas (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT NOT NULL, FOREIGN KEY(usuario_id) REFERENCES usuarios(id))")
            self.c.execute("SELECT COUNT(*) FROM tareas_no_realizadas WHERE fecha=? AND usuario_id=?", (fecha, self.usuario_id))
            valores_no.append(self.c.fetchone()[0])
        plt.figure(figsize=(10,4))
        width = 0.35
        x = range(len(dias))
        plt.bar(x, valores, width=width, color="#8e44ad", label="Hechas")
        plt.bar([i+width for i in x], valores_no, width=width, color="#c0392b", label="No hechas")
        plt.xticks([i+width/2 for i in x], dias)
        plt.title(f"Tareas en {hoy.strftime('%B %Y')} ({self.usuario_nombre})")
        plt.ylabel("Tareas")
        plt.xlabel("Día del mes")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def grafica_anual(self):
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib no está instalado. Instala con: pip install matplotlib")
            return
        hoy = self.fecha_actual
        anio = hoy.year
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        valores = []
        valores_no = []
        for m in range(1, 13):
            self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE strftime('%Y', fecha)=? AND strftime('%m', fecha)=? AND usuario_id=?", (str(anio), f"{m:02d}", self.usuario_id))
            valores.append(self.c.fetchone()[0])
            self.c.execute("CREATE TABLE IF NOT EXISTS tareas_no_realizadas (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT NOT NULL, FOREIGN KEY(usuario_id) REFERENCES usuarios(id))")
            self.c.execute("SELECT COUNT(*) FROM tareas_no_realizadas WHERE strftime('%Y', fecha)=? AND strftime('%m', fecha)=? AND usuario_id=?", (str(anio), f"{m:02d}", self.usuario_id))
            valores_no.append(self.c.fetchone()[0])
        plt.figure(figsize=(10,4))
        width = 0.35
        x = range(len(meses))
        plt.bar(x, valores, width=width, color="#16a085", label="Hechas")
        plt.bar([i+width for i in x], valores_no, width=width, color="#c0392b", label="No hechas")
        plt.xticks([i+width/2 for i in x], meses)
        plt.title(f"Tareas en {anio} ({self.usuario_nombre})")
        plt.ylabel("Tareas")
        plt.xlabel("Mes")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def corte_mes(self):
        # Realiza un corte de mes: guarda el resumen y limpia tareas del mes anterior
        hoy = self.fecha_actual
        mes = hoy.month
        anio = hoy.year
        import calendar
        primer_dia = f"{anio}-{mes:02d}-01"
        ultimo_dia = f"{anio}-{mes:02d}-{calendar.monthrange(anio, mes)[1]:02d}"
        # Contar tareas del mes
        self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE fecha BETWEEN ? AND ? AND usuario_id=?", (primer_dia, ultimo_dia, self.usuario_id))
        total_mes = self.c.fetchone()[0]
        # Guardar resumen en tabla historica
        self.c.execute('''CREATE TABLE IF NOT EXISTS resumen_mensual (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            mes INTEGER,
            anio INTEGER,
            total INTEGER,
            fecha_corte TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
        from datetime import datetime
        self.c.execute("INSERT INTO resumen_mensual (usuario_id, mes, anio, total, fecha_corte) VALUES (?, ?, ?, ?, ?)",
            (self.usuario_id, mes, anio, total_mes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # Borrar tareas del mes
        self.c.execute("DELETE FROM tareas_completadas WHERE fecha BETWEEN ? AND ? AND usuario_id=?", (primer_dia, ultimo_dia, self.usuario_id))
        self.conn.commit()
        messagebox.showinfo("Corte de mes", f"Corte realizado. Total tareas del mes: {total_mes}\nAhora puedes iniciar la cuenta para el nuevo mes.")
        self.cargar_semana_actual()

        # Tooltip
        self.tooltip = None

    def _show_tooltip(self, text, widget):
        if self.tooltip:
            self._hide_tooltip()
        x = widget.winfo_rootx() + 40
        y = widget.winfo_rooty() + 30
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=text, font=("Arial", 10), bg="#f7f7f7", fg="#2a3a5c", bd=1, relief=tk.SOLID, padx=8, pady=4)
        label.pack()

    def _hide_tooltip(self):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    def agregar_usuario(self):
        dialog = tk.Toplevel()
        dialog.title("Agregar usuario")
        dialog.geometry("320x210")
        dialog.configure(bg="#f0f4fc")
        tk.Label(dialog, text="Nuevo usuario:", font=("Arial", 12, "bold"), bg="#f0f4fc", fg="#2a3a5c").pack(pady=10)
        var_usuario = tk.StringVar()
        entry_usuario = tk.Entry(dialog, textvariable=var_usuario)
        entry_usuario.pack(pady=5)
        tk.Label(dialog, text="Contraseña:", font=("Arial", 10), bg="#f0f4fc").pack(pady=5)
        var_password = tk.StringVar()
        entry_pass = tk.Entry(dialog, textvariable=var_password, show="*")
        entry_pass.pack(pady=5)
        show_pw = tk.BooleanVar(value=False)
        def toggle_pw():
            entry_pass.config(show='' if show_pw.get() else '*')
        btn_show = tk.Checkbutton(dialog, text="Mostrar contraseña", variable=show_pw, command=toggle_pw, bg="#f0f4fc")
        btn_show.pack(pady=2)

        def crear():
            nombre = var_usuario.get().strip()
            password = var_password.get().strip()
            if not nombre or not password:
                messagebox.showerror("Error", "Debes ingresar usuario y contraseña.")
                return
            if len(password) < 6 or password.isdigit() or password.isalpha():
                messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres y combinar letras y números.")
                return
            # Verificar si usuario existe
            res = self.c.execute("SELECT id FROM usuarios WHERE nombre=?", (nombre,)).fetchone()
            if res:
                messagebox.showerror("Error", "El usuario ya existe.")
                return
            pw_hash = self.hash_password(password)
            self.c.execute("INSERT INTO usuarios (nombre, password) VALUES (?, ?)", (nombre, pw_hash))
            self.conn.commit()
            messagebox.showinfo("Éxito", "Usuario creado correctamente.")
            dialog.destroy()

        btn = tk.Button(dialog, text="Crear", command=crear, font=("Arial", 11), bg="#1a7f37", fg="white")
        btn.pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)
    def control_usuarios(self):
        dialog = tk.Toplevel()
        dialog.title("Control de usuarios y tareas")
        dialog.geometry("400x400")
        dialog.configure(bg="#f0f4fc")
        tk.Label(dialog, text="Usuarios y tareas realizadas", font=("Arial", 13, "bold"), bg="#f0f4fc", fg="#2a3a5c").pack(pady=10)
        frame = tk.Frame(dialog, bg="#e3eafc", bd=2, relief=tk.RIDGE)
        frame.pack(pady=10, fill=tk.BOTH, expand=True)
        usuarios = self.c.execute("SELECT id, nombre FROM usuarios").fetchall()
        for idx, (uid, nombre) in enumerate(usuarios):
            total = self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE usuario_id=?", (uid,)).fetchone()[0]
            tk.Label(frame, text=f"{nombre}", font=("Arial", 11, "bold"), bg="#e3eafc", fg="#2a3a5c").grid(row=idx, column=0, padx=8, pady=6, sticky="w")
            tk.Label(frame, text=f"Tareas hechas: {total}", font=("Arial", 11), bg="#e3eafc", fg="#1a7f37").grid(row=idx, column=1, padx=8, pady=6)
        btn_cerrar = tk.Button(dialog, text="Cerrar", command=dialog.destroy, font=("Arial", 10), bg="#e67e22", fg="white")
        btn_cerrar.pack(pady=10)
    def cambiar_password(self):
        dialog = tk.Toplevel()
        dialog.title("Cambiar contraseña")
        dialog.geometry("320x210")
        dialog.configure(bg="#f0f4fc")
        tk.Label(dialog, text=f"Usuario: {self.usuario_nombre}", font=("Arial", 12, "bold"), bg="#f0f4fc", fg="#2a3a5c").pack(pady=10)
        tk.Label(dialog, text="Contraseña actual:", font=("Arial", 10), bg="#f0f4fc").pack(pady=5)
        var_actual = tk.StringVar()
        entry_actual = tk.Entry(dialog, textvariable=var_actual, show="*")
        entry_actual.pack(pady=5)
        tk.Label(dialog, text="Nueva contraseña:", font=("Arial", 10), bg="#f0f4fc").pack(pady=5)
        var_nueva = tk.StringVar()
        entry_nueva = tk.Entry(dialog, textvariable=var_nueva, show="*")
        entry_nueva.pack(pady=5)
        show_pw = tk.BooleanVar(value=False)
        def toggle_pw():
            entry_nueva.config(show='' if show_pw.get() else '*')
        btn_show = tk.Checkbutton(dialog, text="Mostrar nueva contraseña", variable=show_pw, command=toggle_pw, bg="#f0f4fc")
        btn_show.pack(pady=2)

        def cambiar():
            actual = var_actual.get().strip()
            nueva = var_nueva.get().strip()
            if not actual or not nueva:
                messagebox.showerror("Error", "Debes ingresar ambas contraseñas.")
                return
            if len(nueva) < 6 or nueva.isdigit() or nueva.isalpha():
                messagebox.showerror("Error", "La nueva contraseña debe tener al menos 6 caracteres y combinar letras y números.")
                return
            res = self.c.execute("SELECT password FROM usuarios WHERE id=?", (self.usuario_id,)).fetchone()
            if res and self.hash_password(actual) == res[0]:
                pw_hash = self.hash_password(nueva)
                self.c.execute("UPDATE usuarios SET password=? WHERE id=?", (pw_hash, self.usuario_id))
                self.conn.commit()
                messagebox.showinfo("Éxito", "Contraseña actualizada correctamente.")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "La contraseña actual es incorrecta.")

        btn = tk.Button(dialog, text="Cambiar", command=cambiar, font=("Arial", 11), bg="#1a7f37", fg="white")
        btn.pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def seleccionar_usuario(self):
        # Ventana para seleccionar o crear usuario con contraseña
        usuarios = self.c.execute("SELECT nombre FROM usuarios").fetchall()
        usuarios = [u[0] for u in usuarios]
        dialog = tk.Toplevel()
        dialog.title("Seleccionar usuario")
        dialog.geometry("340x340")
        dialog.configure(bg="#f0f4fc")
        tk.Label(dialog, text="Selecciona o crea un usuario", font=("Arial", 12, "bold"), bg="#f0f4fc", fg="#2a3a5c").pack(pady=10)
        var_usuario = tk.StringVar()
        var_password = tk.StringVar()
        if usuarios:
            tk.Label(dialog, text="Usuarios existentes:", font=("Arial", 10), bg="#f0f4fc").pack()
            listbox = tk.Listbox(dialog, height=5)
            for usuario in usuarios:
                listbox.insert(tk.END, usuario)
            listbox.pack(pady=5)

            def on_listbox_double_click(event):
                selection = listbox.curselection()
                if selection:
                    nombre = listbox.get(selection[0])
                    # Solicitar contraseña
                    pw_dialog = tk.Toplevel(dialog)
                    pw_dialog.title(f"Acceder como {nombre}")
                    pw_dialog.geometry("300x160")
                    pw_dialog.configure(bg="#f0f4fc")
                    tk.Label(pw_dialog, text=f"Contraseña de {nombre}", font=("Arial", 11), bg="#f0f4fc").pack(pady=10)
                    var_pw = tk.StringVar()
                    entry_pw = tk.Entry(pw_dialog, textvariable=var_pw, show="*")
                    entry_pw.pack(pady=5)
                    show_pw = tk.BooleanVar(value=False)
                    def toggle_pw():
                        entry_pw.config(show='' if show_pw.get() else '*')
                    btn_show = tk.Checkbutton(pw_dialog, text="Mostrar contraseña", variable=show_pw, command=toggle_pw, bg="#f0f4fc")
                    btn_show.pack(pady=2)

                    def acceder():
                        password = var_pw.get().strip()
                        res = self.c.execute("SELECT id, password FROM usuarios WHERE nombre=?", (nombre,)).fetchone()
                        if res:
                            db_pw = res[1]
                            pw_hash = self.hash_password(password)
                            # Si el password guardado no tiene formato hash, migrar si coincide con el password ingresado
                            if len(db_pw) != 64 or not all(c in '0123456789abcdef' for c in db_pw.lower()):
                                if password == db_pw:
                                    self.c.execute("UPDATE usuarios SET password=? WHERE id=?", (pw_hash, res[0]))
                                    self.conn.commit()
                                    self.usuario_id = res[0]
                                    self.usuario_nombre = nombre
                                    messagebox.showinfo("Migración", "Tu contraseña ha sido actualizada a formato seguro.", parent=pw_dialog)
                                    pw_dialog.destroy()
                                    dialog.destroy()
                                else:
                                    messagebox.showerror("Error", "Contraseña incorrecta.", parent=pw_dialog)
                            else:
                                if pw_hash == db_pw:
                                    self.usuario_id = res[0]
                                    self.usuario_nombre = nombre
                                    pw_dialog.destroy()
                                    dialog.destroy()
                                else:
                                    messagebox.showerror("Error", "Contraseña incorrecta o usuario no existe.", parent=pw_dialog)
                        else:
                            messagebox.showerror("Error", "Usuario no existe.", parent=pw_dialog)

                    btn_acc = tk.Button(pw_dialog, text="Acceder", command=acceder, font=("Arial", 11), bg="#1a7f37", fg="white")
                    btn_acc.pack(pady=8)
                    pw_dialog.transient(dialog)
                    pw_dialog.wait_visibility()  # Espera a que la ventana sea visible
                    pw_dialog.grab_set()
                    dialog.wait_window(pw_dialog)

            listbox.bind("<Double-Button-1>", on_listbox_double_click)
        else:
            listbox = None
        tk.Label(dialog, text="Nuevo usuario:", font=("Arial", 10), bg="#f0f4fc").pack(pady=5)
        entry = tk.Entry(dialog, textvariable=var_usuario)
        entry.pack(pady=5)
        tk.Label(dialog, text="Contraseña:", font=("Arial", 10), bg="#f0f4fc").pack(pady=5)
        entry_pass = tk.Entry(dialog, textvariable=var_password, show="*")
        entry_pass.pack(pady=5)
        show_pw = tk.BooleanVar(value=False)
        def toggle_pw():
            entry_pass.config(show='' if show_pw.get() else '*')
        btn_show = tk.Checkbutton(dialog, text="Mostrar contraseña", variable=show_pw, command=toggle_pw, bg="#f0f4fc")
        btn_show.pack(pady=2)

        def seleccionar():
            nombre = var_usuario.get().strip()
            password = var_password.get().strip()
            if listbox and listbox.curselection():
                nombre = listbox.get(listbox.curselection()[0])
            if not nombre or not password:
                messagebox.showerror("Error", "Debes ingresar usuario y contraseña.")
                return
            # Verificar si usuario existe
            res = self.c.execute("SELECT id, password FROM usuarios WHERE nombre=?", (nombre,)).fetchone()
            if not res:
                # Crear usuario nuevo
                if len(password) < 6 or password.isdigit() or password.isalpha():
                    messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres y combinar letras y números.")
                    return
                pw_hash = self.hash_password(password)
                self.c.execute("INSERT INTO usuarios (nombre, password) VALUES (?, ?)", (nombre, pw_hash))
                self.conn.commit()
                res = self.c.execute("SELECT id, password FROM usuarios WHERE nombre=?", (nombre,)).fetchone()
                self.usuario_id = res[0]
                self.usuario_nombre = nombre
                dialog.destroy()
            else:
                # Validar contraseña
                if self.hash_password(password) == res[1]:
                    self.usuario_id = res[0]
                    self.usuario_nombre = nombre
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Contraseña incorrecta.")

        def nuevo_usuario():
            add_dialog = tk.Toplevel(dialog)
            add_dialog.title("Agregar nuevo usuario")
            add_dialog.geometry("320x240")
            add_dialog.configure(bg="#f0f4fc")
            tk.Label(add_dialog, text="Usuario:", font=("Arial", 11), bg="#f0f4fc").pack(pady=5)
            var_nuevo_usuario = tk.StringVar()
            entry_nuevo_usuario = tk.Entry(add_dialog, textvariable=var_nuevo_usuario)
            entry_nuevo_usuario.pack(pady=5)
            tk.Label(add_dialog, text="Contraseña:", font=("Arial", 11), bg="#f0f4fc").pack(pady=5)
            var_nueva_password = tk.StringVar()
            entry_nueva_pass = tk.Entry(add_dialog, textvariable=var_nueva_password, show="*")
            entry_nueva_pass.pack(pady=5)
            show_pw = tk.BooleanVar(value=False)
            def toggle_pw():
                entry_nueva_pass.config(show='' if show_pw.get() else '*')
            btn_show = tk.Checkbutton(add_dialog, text="Mostrar contraseña", variable=show_pw, command=toggle_pw, bg="#f0f4fc")
            btn_show.pack(pady=2)

            def validar_password():
                password = var_nueva_password.get().strip()
                if len(password) < 6 or password.isdigit() or password.isalpha():
                    messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres y combinar letras y números.", parent=add_dialog)
                else:
                    messagebox.showinfo("Validación", "Contraseña válida.", parent=add_dialog)

            def crear_nuevo():
                nombre = var_nuevo_usuario.get().strip()
                password = var_nueva_password.get().strip()
                if not nombre or not password:
                    messagebox.showerror("Error", "Debes ingresar usuario y contraseña.", parent=add_dialog)
                    return
                self.ensure_password_column()
                res = self.c.execute("SELECT id FROM usuarios WHERE nombre=?", (nombre,)).fetchone()
                if res:
                    messagebox.showerror("Error", "El usuario ya existe.", parent=add_dialog)
                    return
                if len(password) < 6 or password.isdigit() or password.isalpha():
                    messagebox.showerror("Error", "La contraseña debe tener al menos 6 caracteres y combinar letras y números.", parent=add_dialog)
                    return
                pw_hash = self.hash_password(password)
                self.c.execute("INSERT INTO usuarios (nombre, password) VALUES (?, ?)", (nombre, pw_hash))
                self.conn.commit()
                # Guardar en usuarios.db
                conn2 = sqlite3.connect('usuarios.db')
                c2 = conn2.cursor()
                c2.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nombre TEXT UNIQUE NOT NULL,
                                password TEXT NOT NULL)
                            ''')
                c2.execute("INSERT INTO usuarios (nombre, password) VALUES (?, ?)", (nombre, pw_hash))
                conn2.commit()
                conn2.close()
                messagebox.showinfo("Éxito", "Usuario creado correctamente.", parent=add_dialog)
                if listbox:
                    listbox.insert(tk.END, nombre)
                add_dialog.destroy()

            btn_validar = tk.Button(add_dialog, text="Validar password", command=validar_password, font=("Arial", 10), bg="#2980b9", fg="white")
            btn_validar.pack(pady=5)
            btn_crear = tk.Button(add_dialog, text="Crear", command=crear_nuevo, font=("Arial", 11), bg="#1a7f37", fg="white")
            btn_crear.pack(pady=10)
            add_dialog.transient(dialog)
            add_dialog.grab_set()
            dialog.wait_window(add_dialog)

        btn = tk.Button(dialog, text="Continuar", command=seleccionar, font=("Arial", 11), bg="#1a7f37", fg="white")
        btn.pack(pady=10)
        btn_nuevo = tk.Button(dialog, text="Nuevo usuario", command=nuevo_usuario, font=("Arial", 10), bg="#16a085", fg="white")
        btn_nuevo.pack(pady=5)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def cargar_semana_actual(self):
        hoy = self.fecha_actual
        dia_semana = hoy.weekday()  # lunes=0, domingo=6
        lunes = hoy - timedelta(days=dia_semana)
        for i in range(7):
            fecha = lunes + timedelta(days=i)
            fecha_str = fecha.strftime("%Y-%m-%d")
            self.c.execute("SELECT COUNT(*) FROM tareas_completadas WHERE fecha=? AND usuario_id=?", (fecha_str, self.usuario_id))
            count = self.c.fetchone()[0]
            self.contadores[self.dias[i]] = count
            self.labels_dias[self.dias[i]].config(text=str(count))
            # Tareas no realizadas
            self.c.execute("CREATE TABLE IF NOT EXISTS tareas_no_realizadas (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER, fecha TEXT NOT NULL, FOREIGN KEY(usuario_id) REFERENCES usuarios(id))")
            self.c.execute("SELECT COUNT(*) FROM tareas_no_realizadas WHERE fecha=? AND usuario_id=?", (fecha_str, self.usuario_id))
            count_no = self.c.fetchone()[0]
            self.contadores_no_realizadas[self.dias[i]] = count_no
            self.labels_dias_no_realizadas[self.dias[i]].config(text=str(count_no))

    def completar_tarea(self):
        ahora = datetime.now()
        fecha_str = ahora.strftime("%Y-%m-%d")
        hora_str = ahora.strftime("%H:%M:%S")
        if self.usuario_id is None:
            messagebox.showerror("Error", "No hay usuario seleccionado. Selecciona un usuario antes de completar una tarea.")
            return
        try:
            self.c.execute("INSERT INTO tareas_completadas (usuario_id, fecha, hora) VALUES (?, ?, ?)", (self.usuario_id, fecha_str, hora_str))
            self.conn.commit()
            dia_nombre_es = self.dias[ahora.weekday()]
            self.contadores[dia_nombre_es] += 1
            self.labels_dias[dia_nombre_es].config(text=str(self.contadores[dia_nombre_es]))
            self.labels_dias[dia_nombre_es].config(bg="#d4efdf")
            self.root.after(800, lambda: self.labels_dias[dia_nombre_es].config(bg="#e3eafc"))
            messagebox.showinfo("Tarea registrada", f"¡Tarea registrada para {dia_nombre_es}!")
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Error", f"No se pudo guardar la tarea: {e}")


    def exportar_pdf(self):
        # Verificar usuario antes de exportar
        if not self.usuario_nombre:
            messagebox.showerror("Error", "No se puede exportar a PDF porque no hay usuario seleccionado.\nValor actual: {}".format(repr(self.usuario_nombre)))
            return
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Error", f"No se puede exportar a PDF porque el módulo 'reportlab' no está instalado.\nInstala con: pip install reportlab\nPython ejecutable: {sys.executable}")
            return
        import os
        import re
        # Sanitizar nombre de usuario para el archivo
        usuario_sanitizado = re.sub(r'[^A-Za-z0-9_]', '_', str(self.usuario_nombre))
        nombre_archivo = f"tareas_semana_{usuario_sanitizado}_{self.fecha_actual.strftime('%Y%m%d')}.pdf"
        ruta_absoluta = os.path.abspath(nombre_archivo)
        try:
            c = canvas.Canvas(ruta_absoluta, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, f"Contadores de tareas por día (semana actual)")
            c.setFont("Helvetica-Bold", 13)
            c.drawString(50, height - 80, f"Usuario: {self.usuario_nombre}")
            c.setFont("Helvetica", 12)
            y = height - 120
            for dia in self.dias:
                texto = f"{dia}: {self.contadores[dia]} tareas completadas"
                c.drawString(70, y, texto)
                y -= 25
            c.save()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            messagebox.showerror("Error", f"No se pudo generar el PDF: {e}\nUsuario: {self.usuario_nombre}\nArchivo: {ruta_absoluta}\nPython ejecutable: {sys.executable}\nTraceback:\n{tb}")
            return
        # Verificar si el archivo existe
        if not os.path.exists(ruta_absoluta):
            messagebox.showerror("Error", f"El PDF no se generó correctamente. No se encontró el archivo en:\n{ruta_absoluta}\nUsuario: {self.usuario_nombre}")
            return
        import tkinter.messagebox as mb
        mb.showinfo("Exportación PDF", f"PDF generado correctamente en:\n{ruta_absoluta}\nUsuario: {self.usuario_nombre}")
        # Intentar abrir el PDF automáticamente (Linux)
        try:
            os.system(f'xdg-open "{ruta_absoluta}"')
        except Exception as e:
            messagebox.showwarning("Advertencia", f"No se pudo abrir el PDF automáticamente.\n{e}")

    def guardar_y_cerrar(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass

    def __del__(self):
        self.guardar_y_cerrar()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    def on_closing():
        app.guardar_y_cerrar()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
