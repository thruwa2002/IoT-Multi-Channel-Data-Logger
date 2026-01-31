#include <WiFi.h>
#include <PubSubClient.h>
#include <math.h>

// --- Wi-Fi & MQTT Settings ---
const char* ssid = "1111";         //  Wi-Fi name
const char* password = "tttttttt"; // Wi-Fi password
const char* mqtt_server = "broker.hivemq.com";

// --- Topics (Python App ) ---
const char* sensor_topic = "tharusha/esp32/sensors";
const char* command_topic = "tharusha/esp32/commands";

WiFiClient espClient;
PubSubClient client(espClient);

// --- pins ---
#define VOLTAGE_PIN   32
#define CURRENT_PIN   33  
#define TEMP_PIN      35
#define RELAY_PIN     25
#define RED_LED       27
#define GREEN_LED     26

float V_CAL = 0.086, I_CAL = 0.007; 
const float SERIES_RES = 10000.0, NOM_RES = 10000.0, NOM_TEMP = 25.0, B_COEF = 3950.0;
const float I_LIMIT = 0.5, T_LIMIT = 30.0;     

float voltage, current, temp, power, energy = 0;
unsigned long lastTime = 0;
String safetyStatus = "NORMAL";
bool systemLocked = false; 

// --- Wi-Fi Function ---
void setup_wifi() {
  delay(10);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

// --- Python App Commands ---
void callback(char* topic, byte* payload, unsigned int length) {
  String command = "";
  for (int i = 0; i < length; i++) {
    command += (char)payload[i];
  }
  Serial.print("Command received: ");
  Serial.println(command);

  if (command == "ON") {
    systemLocked = false;
    safetyStatus = "NORMAL";
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
  } 
  else if (command == "OFF") {
    systemLocked = true;
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, LOW);
  }
}

// --- MQTT reconnec ---
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_SmartMonitor_Tharusha")) {
      Serial.println("connected");
      client.subscribe(command_topic); 
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  
  digitalWrite(RELAY_PIN, LOW); 
  
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  lastTime = millis();
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  readSensors();
  checkSafety();

  // --- Python GUI  (CSV Format) ---
  String relayLabel = (digitalRead(RELAY_PIN) == HIGH) ? "ON" : "OFF";
  
  // Format: "Time,Voltage,0,Current,0,Power,0,Temp,0,Energy,Relay,Status"
  String payload = String(millis()) + "," + 
                   String(voltage, 1) + ",0," + 
                   String(current, 3) + ",0," + 
                   String(power, 1) + ",0," + 
                   String(temp, 1) + ",0," + 
                   String(energy, 4) + "," + 
                   relayLabel + "," + 
                   safetyStatus;

  client.publish(sensor_topic, payload.c_str());
  
  Serial.println("Data sent: " + payload);
  delay(1000); 
}

void readSensors() {
  // --- ( Sensor Reading Logic ) ---
  int v_max = 0, v_min = 4095;
  for(int i=0; i<300; i++){
    int v = analogRead(VOLTAGE_PIN);
    if(v > v_max) v_max = v;
    if(v < v_min) v_min = v;
  }
  voltage = (v_max - v_min) * V_CAL;
  if (voltage < 10) voltage = 0;

  int i_max = 0, i_min = 4095;
  for(int i=0; i<300; i++){
    int cur = analogRead(CURRENT_PIN);
    if(cur > i_max) i_max = cur;
    if(cur < i_min) i_min = cur;
  }
  current = (i_max - i_min) * I_CAL;
  if (current < 0.2) current = 0;

  int raw = analogRead(TEMP_PIN);
  if(raw == 0) raw = 1;
  float res = SERIES_RES * (4095.0 / (float)raw - 1.0);
  float st = log(res / NOM_RES) / B_COEF;
  st += 1.0 / (NOM_TEMP + 273.15);
  temp = (1.0 / st) - 273.15;

  power = voltage * current;
  unsigned long now = millis();
  energy += (power * (now - lastTime)) / 3600000.0;
  lastTime = now;
}

void checkSafety() {
  // --- ( Safety Logic ) ---
  bool faultDetected = false;
  if (current >= I_LIMIT) { safetyStatus = "OVER_CURRENT"; faultDetected = true; }   
  else if (temp >= T_LIMIT) { safetyStatus = "OVER_TEMP"; faultDetected = true; }

  if (faultDetected) {
    systemLocked = true;
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
  }
  else if (systemLocked) {
    digitalWrite(RELAY_PIN, LOW);
  }
  else {
    safetyStatus = "NORMAL";
  }
}