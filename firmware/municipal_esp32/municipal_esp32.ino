/*
  TazaBAK Municipal ESP32 firmware

  Hardware (ESP32 DevKit):
    DS18B20 DATA -> GPIO 4, with a 4.7 kOhm pull-up to 3V3
    HC-SR04 Trig -> GPIO 5
    HC-SR04 Echo -> GPIO 18 THROUGH A 5V-to-3.3V voltage divider
    SG90 signal  -> GPIO 13

  The physical bin is 25 cm deep. The FastAPI backend maps 25 cm to 0%
  and 7 cm to 100%. One DS18B20 is used inside the bin: FastAPI declares
  FIRE_RISK immediately when its reading is strictly above 50 C and then
  sends CLOSE_LID through the WebSocket below.

  Install in Arduino IDE:
    OneWire, DallasTemperature, ESP32Servo, ArduinoJson,
    WebSockets (Markus Sattler / Links2004)
*/

#include <Arduino.h>
#include <ArduinoJson.h>
#include <DallasTemperature.h>
#include <ESP32Servo.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <WebSocketsClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// ---------- Change these values before uploading ----------
// Fill these values locally before uploading the sketch. Do not commit real credentials.
constexpr char WIFI_SSID[] = "YOUR_WIFI_SSID";
constexpr char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";
constexpr char DEVICE_ID[] = "municipal-prototype-001";

// Куда отправлять — единственный переключатель во всём скетче.
//
//   0 — ноутбук в той же Wi-Fi сети, обычный HTTP на 8000. Так идёт защита:
//       backend стоит в двух метрах, задержка минимальная, интернет не нужен.
//   1 — развёрнутый сервис, HTTPS и WSS на 443. Так бак работает без
//       ноутбука вообще, только с Wi-Fi.
//
// Адрес и порт подставляются сами: указать HTTP на 443 или TLS на 8000
// теперь невозможно.
#define TAZABAK_CLOUD 0

#if TAZABAK_CLOUD
constexpr bool USE_TLS = true;
constexpr char BACKEND_HOST[] = "tazabak-api.onrender.com";
constexpr uint16_t BACKEND_PORT = 443;
#else
constexpr bool USE_TLS = false;
constexpr char BACKEND_HOST[] = "192.168.1.100";  // LAN IP ноутбука с FastAPI
constexpr uint16_t BACKEND_PORT = 8000;
#endif
// ----------------------------------------------------------------
constexpr uint8_t TEMP_PIN = 4;
constexpr uint8_t TRIG_PIN = 5;
constexpr uint8_t ECHO_PIN = 18;
constexpr uint8_t SERVO_PIN = 13;

constexpr int LID_CLOSED_ANGLE = 0;
constexpr int LID_OPEN_ANGLE = 120;
constexpr unsigned long TELEMETRY_INTERVAL_MS = 15UL * 1000UL;

// The API keeps temp_out only for diagnostic compatibility. There is no
// second hardware sensor in this prototype, and this value does not affect
// the fire decision.
constexpr float TEMP_OUT_REFERENCE_C = 25.0F;

OneWire oneWire(TEMP_PIN);
DallasTemperature temperatureSensors(&oneWire);
Servo lidServo;
WebSocketsClient webSocket;

bool lidIsClosed = false;
unsigned long lastTelemetryAt = 0;


void setLid(bool closeLid) {
  lidServo.write(closeLid ? LID_CLOSED_ANGLE : LID_OPEN_ANGLE);
  lidIsClosed = closeLid;
  Serial.printf("Lid: %s\n", closeLid ? "CLOSED" : "OPEN");
}


float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (duration == 0) {
    return -1.0F;
  }
  return (static_cast<float>(duration) * 0.0343F) / 2.0F;
}


void sendCommandAck(long commandId) {
  if (commandId <= 0) {
    return;
  }
  StaticJsonDocument<128> ack;
  ack["action"] = "COMMAND_ACK";
  ack["command_id"] = commandId;

  String payload;
  serializeJson(ack, payload);
  webSocket.sendTXT(payload);
}


void webSocketEvent(WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      Serial.printf("WebSocket connected: %s\n", payload);
      break;

    case WStype_DISCONNECTED:
      Serial.println("WebSocket disconnected; reconnecting automatically");
      break;

    case WStype_TEXT: {
      StaticJsonDocument<256> command;
      const DeserializationError error = deserializeJson(command, payload, length);
      if (error) {
        Serial.printf("WebSocket JSON error: %s\n", error.c_str());
        return;
      }

      const char *action = command["action"] | "";
      const long commandId = command["command_id"] | 0L;
      Serial.printf("Command received: %s (#%ld)\n", action, commandId);

      if (strcmp(action, "CLOSE_LID") == 0) {
        setLid(true);
      } else if (strcmp(action, "OPEN_LID") == 0) {
        setLid(false);
      } else {
        Serial.println("Ignoring unknown command");
        return;
      }
      sendCommandAck(commandId);
      break;
    }

    default:
      break;
  }
}


void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.printf("Connecting to Wi-Fi %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const unsigned long startedAt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startedAt < 20000UL) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi connected. ESP32 IP: ");
    Serial.println(WiFi.localIP());
    if (USE_TLS) {
      // У ESP32 нет часов на батарейке: после включения он считает, что
      // сейчас 1970 год. Проверка сертификата в такой дате не проходит
      // никогда, поэтому время берём из сети. Сейчас проверка выключена, но
      // включить её без этой строки было бы невозможно.
      configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    }
  } else {
    Serial.println("Wi-Fi not connected; will retry.");
  }
}


void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Telemetry skipped: Wi-Fi is offline");
    return;
  }

  temperatureSensors.requestTemperatures();
  const float tempIn = temperatureSensors.getTempCByIndex(0);
  const float distance = readDistanceCm();

  if (tempIn == DEVICE_DISCONNECTED_C) {
    Serial.println("Telemetry skipped: DS18B20 is disconnected");
    return;
  }
  if (distance <= 0.0F || distance > 400.0F) {
    Serial.printf("Telemetry skipped: invalid HC-SR04 distance %.2f cm\n", distance);
    return;
  }

  StaticJsonDocument<256> telemetry;
  telemetry["device_id"] = DEVICE_ID;
  telemetry["distance"] = distance;
  telemetry["temp_in"] = tempIn;
  telemetry["temp_out"] = TEMP_OUT_REFERENCE_C;

  String requestBody;
  serializeJson(telemetry, requestBody);

  const String url = String(USE_TLS ? "https://" : "http://") + BACKEND_HOST +
                     ":" + BACKEND_PORT + "/api/sensors/ingest";

  HTTPClient http;
  // static, а не локальная переменная: TLS-контекст выделяет десятки килобайт
  // на каждое соединение, и создавать его заново каждые пятнадцать секунд
  // означает фрагментировать кучу до отказа за несколько суток непрерывной
  // работы. Плата в баке должна жить месяцами.
  static WiFiClientSecure secureClient;
  if (USE_TLS) {
    // Соединение шифруется, но подлинность сервера не проверяется.
    //
    // Это осознанная уступка, а не недосмотр. Проверка требует хранить
    // корневой сертификат в прошивке, а сертификаты меняются: плата,
    // закопанная в бак, замолчала бы в день ротации, и понять почему было бы
    // некому. Для уровня заполнения и температуры цена перехвата невелика.
    //
    // Для эксплуатации: secureClient.setCACert(корневой_сертификат) плюс
    // синхронизация часов ниже — без верного времени проверка не проходит.
    secureClient.setInsecure();
    http.begin(secureClient, url);
  } else {
    http.begin(url);
  }
  http.addHeader("Content-Type", "application/json");

  // Пока идёт POST, webSocket.loop() не вызывается, и плата глуха к командам.
  // В локальной сети двух секунд хватает с запасом. Через интернет столько
  // занимает одно рукопожатие TLS, а бесплатный инстанс после простоя ещё и
  // просыпается около минуты — поэтому в облачном режиме ждём дольше, платя
  // за это более длинной слепой зоной. Неудачная отправка не страшна:
  // следующая уйдёт через пятнадцать секунд.
  const uint16_t timeoutMs = USE_TLS ? 12000 : 2000;
  http.setConnectTimeout(timeoutMs);
  http.setTimeout(timeoutMs);
  const int httpCode = http.POST(requestBody);
  const String response = http.getString();
  http.end();

  Serial.printf(
      "Telemetry: distance=%.2f cm, DS18B20=%.2f C, HTTP=%d\n",
      distance,
      tempIn,
      httpCode);
  if (response.length() > 0) {
    Serial.println(response);
  }
}


void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\nTazaBAK municipal ESP32 starting");

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  temperatureSensors.begin();
  temperatureSensors.setResolution(10);
  Serial.printf("DS18B20 found: %d\n", temperatureSensors.getDeviceCount());

  lidServo.setPeriodHertz(50);
  lidServo.attach(SERVO_PIN, 500, 2400);
  setLid(false);

  connectWiFi();
  const String wsPath = String("/ws/device/") + DEVICE_ID;
  if (USE_TLS) {
    // WSS к тому же адресу. Проверка сертификата не включается по той же
    // причине, что и у телеметрии: см. комментарий в sendTelemetry.
    webSocket.beginSSL(BACKEND_HOST, BACKEND_PORT, wsPath);
  } else {
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsPath);
  }
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000UL);
  // Без heartbeat оборванное соединение не обнаруживается: плата продолжает
  // считать себя подключённой, а команды на закрытие заслонки не приходят.
  // Wi-Fi роняет соединение молча, а через облачный прокси простаивающий
  // сокет закрывают ещё и по таймауту. Пинг каждые 15 с, ответ ждём 3 с, две
  // неудачи подряд считаем разрывом — тогда сработает переподключение выше.
  webSocket.enableHeartbeat(15000UL, 3000UL, 2);
}


void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  webSocket.loop();

  const unsigned long now = millis();
  if (now - lastTelemetryAt >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryAt = now;
    sendTelemetry();
  }

  delay(10);
}
