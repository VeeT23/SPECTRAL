#include <Arduino.h>
#include "screen.h"
#include "joystick.h"
#include "pin_def.h"
#include "radio.h"
#include "packet.h"

uint8_t robotMAC[] = {0x78, 0x42, 0x1C, 0x1F, 0xE9, 0xBC};
Radio<ControlPacket, TelemetryPacket> radio;

Joystick joy_left(PINS::JOY_LEFT::X, PINS::JOY_LEFT::Y, PINS::JOY_LEFT::BUTTON, true, false);
Joystick joy_right(PINS::JOY_RIGHT::X, PINS::JOY_RIGHT::Y, PINS::JOY_RIGHT::BUTTON, false, true);

void setup()
{
  delay(10000);
  Wire.begin();
  Serial.begin(115200);
  Screen::instance().init(0x3C);

  if (!radio.begin(robotMAC))
  {
    Serial.println("Radio init failed!");
    while (true)
      ;
  }

  // Telemetry received from robot
  radio.onPacket = [](const TelemetryPacket &pkt)
  {
    Serial.print("Battery: ");
    Serial.println(pkt.battery_v);
  };

  // Robot stopped responding
  radio.onTimeout = []()
  {
    Serial.println("Robot link lost!");
  };
}

void loop()
{

  joy_left.poll();
  joy_right.poll();

  static uint32_t lastSend = 0;

  // Send commands at 100 Hz
  if (millis() - lastSend >= 10)
  {
    lastSend = millis();

    ControlPacket cmd{};
    cmd.left_vel = joy_left.y();
    cmd.right_vel = joy_right.y();
    cmd.flags = 0;

    radio.send(cmd);
  }

  radio.update();

  Screen::instance().gfx().clearDisplay();
  joy_left.draw(0, 0);
  joy_right.draw(64, 0);
  Screen::instance().gfx().display();
}
