#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

#undef BLACK
#undef WHITE

// ── Configuration ──────────────────────────────────────────────────────────
const char* SSID     = "StarkHacks-2";
const char* PASSWORD = "StarkHacks2026";
const char* PI_IP    = "10.10.11.57";
const int   PI_PORT  = 5001;

#define LED_PIN       4
#define LED_COUNT     50
#define TRIG_PIN      5
#define ECHO_PIN      18
#define OLED_RESET    -1
#define OLED_ADDR     0x3C
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64

#define DOOR_OPEN_CM       15     // distance threshold for open door
#define SNAP_DELAY_MS      1500  // wait after door closes before triggering scan
#define RESULT_DISPLAY_MS  30000 // how long to show scan results before going idle

// ── Objects ────────────────────────────────────────────────────────────────
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_SSD1306  display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WebServer         server(80);

// ── State machine ──────────────────────────────────────────────────────────
enum State { IDLE, DOOR_OPEN, SNAP, ANALYZING, RESULT };
State         currentState = IDLE;
State         prevState    = IDLE;
unsigned long stateTimer   = 0;
int           blueOffset   = 0;
bool          scanPending  = false;  // true while waiting for /leds from Pi

// ── Distance ───────────────────────────────────────────────────────────────
uint16_t readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 25000);
  return (dur == 0) ? 999 : (uint16_t)(dur * 0.034 / 2);
}

// ── Display helpers ────────────────────────────────────────────────────────
void showOLED(const char* line1, const char* line2 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 10); display.println(line1);
  display.setCursor(0, 30); display.println(line2);
  display.display();
}

// ── LED helpers ────────────────────────────────────────────────────────────
void setAllLEDs(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < LED_COUNT; i++)
    strip.setPixelColor(i, strip.Color(r, g, b));
  strip.show();
}

// Blue chase animation — call every loop tick while ANALYZING
void playBlueAnimation() {
  static unsigned long lastMove = 0;
  if (millis() - lastMove < 60) return;
  lastMove = millis();
  strip.clear();
  for (int i = 0; i < 2; i++) {
    int p = (blueOffset + i * 25) % LED_COUNT;
    for (int j = 0; j < 5; j++)
      strip.setPixelColor((p + j) % LED_COUNT, strip.Color(0, 0, 255));
  }
  strip.show();
  blueOffset++;
}

// ── Pi communication ───────────────────────────────────────────────────────
void triggerPiScan() {
  WiFiClient client;
  if (!client.connect(PI_IP, PI_PORT)) {
    Serial.println("[esp32] Connection to Pi failed — going idle");
    currentState = IDLE;
    showOLED("PI UNREACHABLE", "Check network");
    return;
  }
  client.println("POST /scan HTTP/1.1");
  client.print("Host: "); client.println(PI_IP);
  client.println("Content-Length: 0");
  client.println("Connection: close");
  client.println();
  client.stop();
  Serial.println("[esp32] Scan triggered on Pi");
  scanPending = true;
}

// ── HTTP handlers ──────────────────────────────────────────────────────────

// POST /leds  {"colors": [[r,g,b], ...]}  — Pi pushes LED state here
void handleSetLEDs() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"no body\"}");
    return;
  }
  // 50 colors × ~3 bytes each + ArduinoJson tree overhead → needs ~3 KB
  DynamicJsonDocument doc(4096);
  DeserializationError err = deserializeJson(doc, server.arg("plain"));
  if (err) {
    server.send(400, "application/json", "{\"error\":\"bad json\"}");
    return;
  }
  JsonArray colors = doc["colors"];
  for (int i = 0; i < min((int)colors.size(), LED_COUNT); i++) {
    JsonArray c = colors[i];
    strip.setPixelColor(i, strip.Color(c[0], c[1], c[2]));
  }
  strip.show();
  server.send(200, "application/json", "{\"ok\":true}");

  // Only transition to RESULT if this LED push came from a scan
  if (scanPending) {
    scanPending   = false;
    currentState  = RESULT;
    stateTimer    = millis();
    showOLED("SCAN COMPLETE", "Pantry updated!");
  }
}

// POST /clear  — turn off all LEDs
void handleClear() {
  setAllLEDs(0, 0, 0);
  scanPending  = false;
  currentState = IDLE;
  server.send(200, "application/json", "{\"ok\":true}");
}

// POST /pulse  — Pi signals scan has started; start animation
void handlePulse() {
  scanPending  = true;
  currentState = ANALYZING;
  server.send(200, "application/json", "{\"ok\":true}");
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  strip.begin();
  strip.show();

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Wire.begin(21, 22);
  if (display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    showOLED("SMART PANTRY", "Connecting WiFi...");
  }

  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println();
  Serial.print("[esp32] IP: "); Serial.println(WiFi.localIP());

  showOLED("READY", WiFi.localIP().toString().c_str());

  server.on("/leds",  HTTP_POST, handleSetLEDs);
  server.on("/clear", HTTP_POST, handleClear);
  server.on("/pulse", HTTP_POST, handlePulse);
  server.begin();
}

// ── Loop ───────────────────────────────────────────────────────────────────
void loop() {
  server.handleClient();
  uint16_t dist = readDistance();
  bool stateChanged = (currentState != prevState);
  prevState = currentState;

  switch (currentState) {

    case IDLE:
      if (stateChanged) {
        setAllLEDs(0, 0, 0);
        showOLED("SMART PANTRY", "Waiting...");
      }
      if (dist < DOOR_OPEN_CM) {
        currentState = DOOR_OPEN;
      }
      break;

    case DOOR_OPEN:
      if (stateChanged) {
        setAllLEDs(255, 255, 255);   // bright white for photography
        showOLED("PANTRY OPEN", "Lights: ON");
      }
      if (dist >= DOOR_OPEN_CM) {
        currentState = SNAP;
        stateTimer   = millis();
      }
      break;

    case SNAP:
      if (stateChanged) {
        showOLED("DOOR CLOSED", "Stabilizing...");
      }
      if (millis() - stateTimer > SNAP_DELAY_MS) {
        currentState = ANALYZING;
        triggerPiScan();
      }
      break;

    case ANALYZING:
      if (stateChanged) {
        showOLED("SCANNING", "Gemini thinking...");
        blueOffset = 0;
      }
      playBlueAnimation();
      // Exit when Pi calls /leds (sets scanPending=false + RESULT)
      // or if stuck > 30s, give up
      if (millis() - stateTimer > 30000) {
        currentState = IDLE;
        showOLED("TIMEOUT", "Scan failed");
        setAllLEDs(0, 0, 0);
      }
      break;

    case RESULT:
      if (stateChanged) {
        // OLED already set by handleSetLEDs
      }
      if (millis() - stateTimer > RESULT_DISPLAY_MS || dist < DOOR_OPEN_CM) {
        currentState = IDLE;
      }
      break;
  }

  delay(10);
}
