import paho.mqtt.client as mqtt
import csv
import datetime
import time
import threading
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import queue
import json

class ESP32MQTTMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Industry IoT Monitor (MQTT) - Tharusha")
        self.root.state('zoomed') 
        
        # --- MQTT Configuration ---
        self.broker = "broker.hivemq.com" # Public Broker (Industry වලදී මෙය ඔබගේ Server IP එක වේ)
        self.port = 1883
        self.sensor_topic = "tharusha/esp32/sensors"
        self.command_topic = "tharusha/esp32/commands"
        
        self.title_font = ('Arial', 20, 'bold')
        self.value_font = ('Arial', 14, 'bold')
        
        self.connected = False
        self.is_logging = False
        self.gui_queue = queue.Queue()
        self.running = True
        
        # Data storage
        self.max_data_points = 100
        self.time_data = deque(maxlen=self.max_data_points)
        self.voltage_data = deque(maxlen=self.max_data_points)
        self.current_data = deque(maxlen=self.max_data_points)
        self.power_data = deque(maxlen=self.max_data_points)
        self.temperature_data = deque(maxlen=self.max_data_points)
        
        self.session_start_time = time.time()
        self.csv_file = ""

        self.setup_gui()
        self.setup_mqtt()
        self.setup_animation()
        self.check_gui_queue()

    def setup_gui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        for i in range(3): main_frame.columnconfigure(i, weight=1)
        main_frame.rowconfigure(2, weight=3)

        ttk.Label(main_frame, text="🌐 ESP32 Smart IoT Monitor - Industry Level (MQTT)", font=self.title_font).grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # --- Control Panel ---
        ctrl = ttk.LabelFrame(main_frame, text="🔧 Connectivity & Control", padding="10")
        ctrl.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.conn_lbl = tk.Label(ctrl, text="MQTT: DISCONNECTED", fg="red", font=('Arial', 10, 'bold'))
        self.conn_lbl.grid(row=0, column=0, columnspan=2, pady=5)

        self.log_btn = ttk.Button(ctrl, text="🔴 Start Logging (Excel)", command=self.toggle_logging)
        self.log_btn.grid(row=1, column=0, padx=5, pady=5)
        
        # Relay Controls
        btn_f = ttk.Frame(ctrl)
        btn_f.grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(btn_f, text="Relay ON", command=lambda: self.send_cmd("ON")).pack(side="left", padx=2)
        ttk.Button(btn_f, text="Relay OFF", command=lambda: self.send_cmd("OFF")).pack(side="left", padx=2)

        # Safety & Values
        stat_p = ttk.LabelFrame(main_frame, text="🛡️ System Status", padding="10")
        stat_p.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.safety_var, self.relay_var = tk.StringVar(value="WAITING..."), tk.StringVar(value="RELAY: ---")
        self.safety_lbl = tk.Label(stat_p, textvariable=self.safety_var, font=self.value_font, bg="gray", fg="white")
        self.safety_lbl.pack(expand=True, fill="both", pady=2)
        self.relay_lbl = tk.Label(stat_p, textvariable=self.relay_var, font=self.value_font, bg="gray", fg="white")
        self.relay_lbl.pack(expand=True, fill="both", pady=2)

        val_p = ttk.LabelFrame(main_frame, text="📊 Live Telemetry", padding="10")
        val_p.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)
        self.v_var, self.i_var, self.t_var = tk.StringVar(value="0.0 V"), tk.StringVar(value="0.000 A"), tk.StringVar(value="0.0 °C")
        tk.Label(val_p, textvariable=self.v_var, font=self.value_font, fg="#2196F3").pack()
        tk.Label(val_p, textvariable=self.i_var, font=self.value_font, fg="#f44336").pack()
        tk.Label(val_p, textvariable=self.t_var, font=self.value_font, fg="#ff9800").pack()

        # Graphs
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(10, 6))
        plt.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().grid(row=2, column=0, columnspan=3, sticky="nsew", pady=10)

        self.console = scrolledtext.ScrolledText(main_frame, height=5, font=("Consolas", 10), bg="#2d2d2d", fg="#00ff00")
        self.console.grid(row=3, column=0, columnspan=3, sticky="nsew")

    # --- MQTT Logic ---
    def setup_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self.log(f"Connecting to Broker: {self.broker}...")
        except Exception as e:
            self.log(f"Connection Failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.client.subscribe(self.sensor_topic)
            self.conn_lbl.config(text="MQTT: CONNECTED", fg="#2ecc71")
            self.log("✅ Successfully connected to MQTT Broker")
        else:
            self.log(f"❌ Connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.conn_lbl.config(text="MQTT: DISCONNECTED", fg="red")
        self.log("🔴 Disconnected from Broker")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        self.gui_queue.put(('data', payload))

    def send_cmd(self, cmd):
        if self.connected:
            self.client.publish(self.command_topic, cmd)
            self.log(f"📡 Command Sent: {cmd}")
        else:
            messagebox.showwarning("Warning", "Not connected to MQTT Broker")

    # --- Data Processing ---
    def check_gui_queue(self):
        while not self.gui_queue.empty():
            m_type, val = self.gui_queue.get_nowait()
            if m_type == 'data': self.process_data(val)
        self.root.after(50, self.check_gui_queue)

    def process_data(self, data):
        # අපේක්ෂිත දත්ත හැඩය (CSV format): V,230,A,1.2,P,276,T,35,R,ON,S,NORMAL
        parts = data.split(',')
        if len(parts) >= 12:
            try:
                v, i, p, t = float(parts[1]), float(parts[3]), float(parts[5]), float(parts[7])
                rel, saf = parts[10], parts[11]
                
                self.v_var.set(f"{v:.1f} V"); self.i_var.set(f"{i:.3f} A"); self.t_var.set(f"{t:.1f} °C")
                self.relay_var.set(f"RELAY: {rel}"); self.safety_var.set(saf)
                self.safety_lbl.config(bg="green" if saf=="NORMAL" else "red")
                self.relay_lbl.config(bg="#2ecc71" if rel=="ON" else "#e74c3c")
                
                curr_time = time.time() - self.session_start_time
                self.time_data.append(curr_time); self.voltage_data.append(v)
                self.current_data.append(i); self.power_data.append(p); self.temperature_data.append(t)

                if self.is_logging:
                    with open(self.csv_file, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), v, i, p, t, rel, saf])
            except Exception as e:
                pass

    # --- Utilities ---
    def toggle_logging(self):
        if not self.is_logging:
            self.csv_file = f"MQTT_Log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(self.csv_file, mode='w', newline='') as f:
                csv.writer(f).writerow(['Timestamp', 'Voltage', 'Current', 'Power', 'Temp', 'Relay', 'Status'])
            self.is_logging = True
            self.log_btn.config(text="⏹️ Stop Logging")
            self.log(f"📝 Logging to: {self.csv_file}")
        else:
            self.is_logging = False
            self.log_btn.config(text="🔴 Start Logging (Excel)")
            self.log("✅ File saved.")

    def setup_animation(self):
        def update_charts(frame):
            if len(self.time_data) > 0:
                axes = [self.ax1, self.ax2, self.ax3, self.ax4]
                data_sets = [self.voltage_data, self.current_data, self.power_data, self.temperature_data]
                titles = ["Voltage (V)", "Current (A)", "Power (W)", "Temp (°C)"]
                colors = ['#2196F3', '#f44336', '#4CAF50', '#FF9800']

                for ax, data, title, color in zip(axes, data_sets, titles, colors):
                    ax.clear()
                    ax.plot(list(self.time_data), list(data), color)
                    ax.set_title(title); ax.grid(True, alpha=0.3)
                self.canvas.draw_idle()
        self.ani = FuncAnimation(self.fig, update_charts, interval=1000, cache_frame_data=False)

    def log(self, msg):
        self.console.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.console.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ESP32MQTTMonitor(root)
    root.mainloop()