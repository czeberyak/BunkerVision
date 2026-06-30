# BunkerVision: Industrial AI Pipeline

**Система автоматического мониторинга уровня заполненности бункеров сырьем (картофель) с использованием Computer Vision (YOLOv8n-cls) и паттернов отказоустойчивой архитектуры.**

## 📋 Описание проекта
Проект разработан как Production-Ready решение для интеграции в производственную линию предприятия по производству картофеля фри. 
Основной фокус сделан на:
* **Отказоустойчивость (Store-and-Forward):** Локальный SQLite-буфер гарантирует сохранность телеметрии при падении локальной сети завода или недоступности ERP-системы (1С).
* **Работа в условиях экстремального дефицита данных:** Синтез датасета ( Albumentations ) для имитации заводских условий (пыль, блики, артефакты RTSP).
* **Автономность:** Работа в виде фоновой службы Windows с автозапуском и алертами в Telegram.

---

## 🏗 Архитектура и Паттерны

1. **Capture (RTSP Polling):** Подключение к камерам IDIS по RTSP. Применение аппаратного таймаута OpenCV и программного ROI (Region of Interest) для отсечения соседних бункеров и устранения шума.
2. **Inference (YOLOv8n-cls):** Легковесная модель классификации (1.4M параметров, инференс <5ms на CPU). Классы: `0%, 25%, 50%, 75%, 100%`.
3. **Store-and-Forward (SQLite + Tenacity):** 
   * Результаты инференса сохраняются в локальную SQLite БД.
   * Модуль `sender.py` использует библиотеку `tenacity` для реализации **Exponential Backoff** при отправке HTTP POST в 1С. Если ERP "лежит", система не зависает, а накапливает данные и повторяет попытки с увеличением задержки.
4. **Alerting:** Мгновенные уведомления в Telegram при достижении критических уровней (<5% или >95%).
5. **Orchestration:** `APScheduler` для независимого поллинга по расписанию (каждые 30 минут).

---

## 📂 Структура проекта

```text
├── cameras_config.json      # Конфигурация потоков, ROI и доступов
├── config.py                # Валидация и загрузка конфигурации (Dataclasses)
├── monitor.py               # Главный оркестратор (APScheduler) и точка входа
├── capture.py               # Захват кадров (OpenCV) с обработкой таймаутов и ROI
├── model.py                 # Обертка для инференса YOLOv8-cls
├── db.py                    # Локальный SQLite-буфер (SQLAlchemy)
├── sender.py                # Отправка HTTP POST в 1С с Retry-политиками
├── telegram.py              # Отправка тревожных уведомлений
├── requirements.txt         # Зависимости Python
├── install_service.bat      # Регистрация службы Windows через NSSM
└── notebooks/               # R&D ноутбуки (ROI, синтетика, обучение)
```

---

## ⚙️ Конфигурация

Настройки системы хранятся в `cameras_config.json`:

```json
{
  "erp_url": "http://192.168.1.100:8080/api/v1/bunker_telemetry",
  "db_path": "sqlite:///data/bunker_buffer.db",
  "model_path": "runs/models/bunker_poc/weights/best.pt",
  "poll_interval_minutes": 30,
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  },
  "cameras": [
    {
      "bunker_id": "BUNKER_15",
      "rtsp_url": "rtsp://admin:password@192.168.1.50:554/stream1",
      "roi_ratio": [0.0, 0.0, 0.55, 1.0]
    }
  ]
}
```
* `roi_ratio`: `[x_min, y_min, x_max, y_max]` в относительных координатах (от 0.0 до 1.0). Позволяет программно отсечь соседние бункеры из кадра.

---

## 🚀 Быстрый старт и Развертывание

### 1. Установка зависимостей
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
*(Требуемые библиотеки: `opencv-python`, `sqlalchemy`, `requests`, `tenacity`, `apscheduler`, `ultralytics`)*

### 2. Настройка
Заполните `cameras_config.json` актуальными RTSP-ссылками и токенами Telegram.

### 3. Запуск в режиме теста
```bash
python monitor.py
```

### 4. Развертывание в качестве службы Windows
Для автономной работы и автозапуска при перезагрузке сервера используется утилита **NSSM** (Non-Sucking Service Manager).
1. Скачайте `nssm.exe` и поместите в корень проекта.
2. Запустите `install_service.bat` от имени Администратора:
   ```bat
   nssm install BunkerVisionService "%cd%\venv\Scripts\python.exe" "%cd%\monitor.py"
   nssm set BunkerVisionService AppDirectory "%cd%"
   nssm start BunkerVisionService
   ```

---

## 🧠 Модель Computer Vision
* **Архитектура:** YOLOv8n-cls (Classification).
* **Обучение:** 10 эпох на синтетическом датасете (500+ кадров, сгенерированных через `albumentations` для имитации пыли, бликов и компрессии RTSP).
* **Метрики:** Top-1 Accuracy > 99% на hold-out выборке.
* **Производительность:** Инференс < 5ms на CPU (Intel Core i5 / Xeon).

---

## 🛡 Обработка исключений и Надежность
* **RTSP Таймауты:** `cv2.VideoCapture` настроен с таймаутами `CAP_PROP_OPEN_TIMEOUT_MSEC` и `CAP_PROP_READ_TIMEOUT_MSEC` (5 сек), чтобы избежать "зависания" потока при обрыве связи.
* **База данных:** Использование `contextmanager` и `session.rollback()` для предотвращения блокировок SQLite.
* **Сеть (ERP):** `tenacity.retry` с `wait_exponential` гарантирует, что при падении 1С система будет экспоненциально увеличивать интервалы между попытками, не "заспамливая" сеть и не падая с `Exception`.
* **Логирование:** Дублирование логов в `stdout` и файл `bunker_vision.log`.
```

### 📌 Примечание к `requirements.txt`
Для работы refactored-кода убедитесь, что в вашем `requirements.txt` добавлена библиотека для ретраев:
```text
opencv-python
sqlalchemy
requests
tenacity
apscheduler
ultralytics
```