#include <Arduino.h>

unsigned long lastSend = 0;
const unsigned long interval = 250; // 250 ms

// --- Telemetry state variables ---
float battery_voltage = 12.4;
float temperature     = 25.0;
int motor_rpm         = 1000;
float pos_x           = 0.0;
float pos_y           = 0.0;

unsigned long seq = 0; // sequence counter

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }
  Serial.println("Fake telemetry generator started (JSON mode)");
}

void loop() {
  if (millis() - lastSend >= interval) {
    lastSend = millis();
    seq++;

    // --- Drift values slightly ---
    battery_voltage += (random(-2, 3) * 0.01); // ±0.02 V drift
    temperature     += (random(-2, 3) * 0.05); // ±0.1 °C drift
    motor_rpm       += random(-20, 21);        // ±20 RPM drift (slower changes)
    pos_x           += (random(-2, 3) * 0.1);  // ±0.2 drift
    pos_y           += (random(-2, 3) * 0.1);

    // --- Clamp to reasonable ranges ---
    if (battery_voltage < 11.0) battery_voltage = 11.0;
    if (battery_voltage > 12.6) battery_voltage = 12.6;

    if (temperature < 20.0) temperature = 20.0;
    if (temperature > 40.0) temperature = 40.0;

    if (motor_rpm < 0) motor_rpm = 0;
    if (motor_rpm > 5000) motor_rpm = 5000;

    // --- Print JSON ---
    Serial.printf(
      "{\"seq\":%lu,"
      "\"time\":%lu,"
      "\"battery_voltage\":%.2f,"
      "\"temperature\":%.2f,"
      "\"motor_rpm\":%d,"
      "\"pos_x\":%.2f,"
      "\"pos_y\":%.2f}\n",
      seq,
      millis(),
      battery_voltage,
      temperature,
      motor_rpm,
      pos_x,
      pos_y
    );
  }
}
