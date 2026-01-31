Multi-Channel Voltage/Current Data Logger (IoT)

This is an industrial-grade Smart Data Logger designed for real-time monitoring and safety of electrical systems and AC motors. The system acquires critical data—Voltage, Current, Power, and Temperature—using an ESP32 microcontroller and transmits it via the MQTT protocol to a customized Python-based GUI dashboard.
Features

    Real-time Monitoring: Live visualization of voltage, current, power, and temperature.

    Automated Protection: Features protection logic that automatically deactivates the load via a relay if current or temperature thresholds are exceeded.

    Remote Control: Supports manual Relay ON/OFF commands via the Python dashboard.

    Data Logging: Automatically saves all live sensor data into a CSV file for long-term analysis.

Hardware Components

    Microcontroller: ESP32 (utilizing built-in Wi-Fi for MQTT).

    Sensors:

        Voltage: ZMPT101B.

        Current: ACS712.

        Temperature: 10k NTC Thermistor.

    Actuators/Indicators: * Relay Module for load control.

        Green LED (Normal Operation) and Red LED (Safety Fault).

    Power: 12V Power adapter with a voltage regulator.

Pin Configuration (ESP32)

    Analog Inputs: * Pin 32: Voltage Sensor.

        Pin 33: Current Sensor.

        Pin 35: Temperature Sensor.

    Digital Outputs:

        Pin 25: Relay Module Trigger.

        Pin 26 & 27: Status LEDs.

Communication Details (MQTT)

    Broker: broker.hivemq.com (Port: 1883).

    Topics:

        Sensor Topic: tharusha/esp32/sensors (Publishes telemetry data).

        Command Topic: tharusha/esp32/commands (Receives Relay control signals).

    Library: PubSubClient.h for Arduino IDE.

System Status Logic

    NORMAL: System operates within safe limits; Green LED is ON.

    OVER CURRENT / OVER TEMPERATURE: System triggers a fault; Red LED turns ON, and the Relay is automatically switched OFF for protection.

Project by: R.L.A.T.P.M.Rajakaruna (Index: T01343). Date: 25/01/2026.
