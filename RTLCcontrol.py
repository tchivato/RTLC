import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import pandas as pd
import csv
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import hashlib

# Obtener la fecha actual para el campo Lote
current_datetime = time.localtime()
default_lote = f"{current_datetime.tm_mday:02d}{current_datetime.tm_mon:02d}{current_datetime.tm_year % 100:02d}RF"

def listar_puertos():
    """Obtiene los puertos COM disponibles."""
    return [port.device for port in serial.tools.list_ports.comports()]

def enviar_datos():
    """Envía los datos por el puerto serie, registra las respuestas y actualiza el gráfico en tiempo real."""
    global ser, posiciones, cuentas

    lote = entry_lote.get()
    operador = entry_operador.get()
    distancia = entry_distancia.get()
    tiempo = entry_tiempo.get()
    puerto = combobox_puertos.get()

    # Validación de campos
    if not lote:
        messagebox.showerror("Error", "El campo 'Lote' es obligatorio.")
        return
    if not operador.isalpha():
        messagebox.showerror("Error", "El campo 'Operador' solo puede contener letras.")
        return
    if not distancia.isdigit() or not (10 <= int(distancia) <= 150):
        messagebox.showerror("Error", "El campo 'Distancia' debe ser un número entre 10 y 150.")
        return
    if not tiempo.isdigit() or int(tiempo) < 1:
        messagebox.showerror("Error", "El campo 'Tiempo' debe ser un número mayor que 1.")
        return
    if not puerto:
        messagebox.showerror("Error", "Seleccione un puerto COM válido.")
        return

    try:
        # Configurar el puerto serie
        ser = serial.Serial(puerto, baudrate=9600, timeout=1)
        datos = f"{lote},{operador},{distancia},{tiempo}\n"
        ser.write(datos.encode())  # Enviar datos por el puerto serie
        ser.flush()

        # Inicializar el gráfico
        ax.clear()
        ax.set_xlabel("Posición (mm)")
        ax.set_ylabel("Cuentas")
        fig.tight_layout()
        canvas.draw()

        # Inicializar listas de datos
        posiciones = []
        cuentas = []

        # Cambiar el texto del botón a MIDIENDO
        btn_run.config(text="MIDIENDO", state="disabled")

        root.update()

        def finalizar_adquisicion():
            """Finaliza la adquisición y guarda los datos en un archivo CSV."""
            if ser and ser.is_open:
                ser.close()

            # Guardar datos en un archivo CSV
            data = {"Posición": posiciones, "Cuentas": cuentas}
            df = pd.DataFrame(data)
            nombre_csv = f"{lote}.csv"
            df['Posición'] = df['Posición'].apply(lambda x: f"{x:.1f}".replace('.', ','))
            df.to_csv(nombre_csv, index=False, sep=';')
            
            # Añade como metadatos las variables de adquisición
            with open(nombre_csv, mode='a', encoding='utf-8') as archivo:
                archivo.write(f"Lote:;{lote}\nOperador:;{operador}\nRango:;{distancia} mm\nTiempo adquisición:;{tiempo} min\n")
                archivo.write(f"Fecha:;{time.strftime("%d/%m/%Y, %H:%M:%S", time.localtime())}\n")

            # Calcula hash para huella digital y lo añade al final del csv
            with open(nombre_csv, "rb") as archivo:
                hash_sha256 = hashlib.sha256()
                for linea in archivo:
                    hash_sha256.update(linea)
                hash=hash_sha256.hexdigest()
                
            with open(nombre_csv, mode='a', encoding='utf-8') as archivo:
                archivo.write(f"Huella SHA256:;{hash}")
                
            # Restaurar el botón a su estado original
            btn_run.config(text="START", state="normal")

        def leer_puerto():
            """Lee datos del puerto serie y actualiza el gráfico en tiempo real."""
            if ser.in_waiting:
                try:
                    linea = ser.readline().decode('utf-8', errors='ignore').strip()
                    if linea == "end":
                        finalizar_adquisicion()
                        return
                    if linea:
                        posicion, cuenta = map(int, linea.split(";"))
                        posiciones.append(posicion/10)
                        cuentas.append(cuenta)
                        # Actualizar el gráfico
                        ax.clear()
                        ax.plot(posiciones, cuentas, marker="o", markersize=0.1, linestyle="-", color="blue")
                        ax.set_xlabel("Posición (mm)")
                        ax.set_ylabel("Cuentas")
                        ax.set_xlim(0, float(distancia))
                        ax.set_ylim(0,)
                        fig.tight_layout()
                        canvas.draw()
                except ValueError:
                    pass  # Ignorar líneas inválidas

            # Continuar leyendo en el siguiente ciclo
            root.after(100, leer_puerto)

        # Iniciar la lectura del puerto serie
        leer_puerto()

    except serial.SerialException as e:
        messagebox.showerror("Error", f"No se pudo abrir el puerto serie: {e}")
        btn_run.config(text="START", state="normal")
    except Exception as e:
        messagebox.showerror("Error", f"Error inesperado: {e}")
        btn_run.config(text="START", state="normal")

# Crear la ventana principal
root = tk.Tk()
root.title("Control RTLC")

# Etiquetas y campos de entrada
tk.Label(root, text="Lote:", anchor="e").grid(row=0, column=0, padx=10, pady=5, sticky="e")
entry_lote = tk.Entry(root)
entry_lote.insert(0, default_lote)
entry_lote.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Operador:", anchor="e").grid(row=1, column=0, padx=10, pady=5, sticky="e")
entry_operador = tk.Entry(root)
entry_operador.grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Rango (mm):", anchor="e").grid(row=2, column=0, padx=10, pady=5, sticky="e")
entry_distancia = tk.Entry(root)
entry_distancia.grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Tiempo (min):", anchor="e").grid(row=3, column=0, padx=10, pady=5, sticky="e")
entry_tiempo = tk.Entry(root)
entry_tiempo.grid(row=3, column=1, padx=10, pady=5)

# Combobox para los puertos COM
tk.Label(root, text="Puerto COM:", anchor="e").grid(row=4, column=0, padx=10, pady=5, sticky="e")
puertos = listar_puertos()
combobox_puertos = ttk.Combobox(root, values=puertos, state="readonly")
combobox_puertos.grid(row=4, column=1, padx=10, pady=5)

# Botón para enviar datos
btn_run = tk.Button(root, text="START", command=enviar_datos, font=("Helvetica", 15, "bold"))
btn_run.grid(row=6, column=0, columnspan=2, pady=20, sticky="ew")

# Área para el gráfico
fig = Figure(figsize=(5, 3), dpi=100)
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=8, column=0, columnspan=2, pady=10)

# Iniciar la aplicación
root.mainloop()
