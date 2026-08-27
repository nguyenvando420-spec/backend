# FastAPI Backend API - Clean Architecture Example

Mẫu thiết kế Backend API hoàn chỉnh sử dụng **FastAPI**, **Async SQLAlchemy** và **Pydantic v2** được tổ chức theo kiến trúc **Clean Architecture** (Kiến trúc sạch).

---

## 🏗️ Cấu trúc thư mục (Project Architecture)

```text
Backend/
├── app/
│   ├── core/                           # Cấu hình chung, biến môi trường & exceptions cơ bản
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── domain/                         # TẦNG DOMAIN (Độc lập 100% với DB & Web Framework)
│   │   ├── entities/                   # Business Data Models (Python Dataclasses)
│   │   │   └── item.py
│   │   └── exceptions/                 # Business Domain Exceptions
│   │       └── item_exceptions.py
│   │
│   ├── use_cases/                      # TẦNG USE CASES (Nghiệp vụ ứng dụng)
│   │   ├── interfaces/                 # Repository Interfaces (Abstract Base Classes)
│   │   │   └── item_repository.py
│   │   └── item/                       # Các Use Cases cụ thể
│   │       ├── create_item.py
│   │       ├── get_item.py
│   │       └── list_items.py
│   │
│   ├── infrastructure/                 # TẦNG INFRASTRUCTURE (Chi tiết kỹ thuật: DB, External APIs)
│   │   ├── database/                   # Database Connection & SQLAlchemy ORM Models
│   │   │   ├── connection.py
│   │   │   └── models/
│   │   │       └── item_model.py
│   │   └── repositories/               # Triển khai thực tế Repository Interface (SQLAlchemy Impl)
│   │       └── item_repository_impl.py
│   │
│   └── api/                            # TẦNG API / PRESENTATION (FastAPI Web Framework)
│       └── v1/
│           ├── schemas/                # Request / Response Pydantic DTOs
│           │   └── item_schema.py
│           ├── dependencies.py         # Dependency Injection Container cho FastAPI
│           └── routers/                # API Endpoints (Controllers)
│               └── item_router.py
│   └── main.py                         # Application Entrypoint & Exception Handlers
│
├── tests/                              # Unit & Integration Tests
│   └── test_items.py
├── requirements.txt                    # Danh sách thư viện phụ thuộc
└── README.md                           # Tài liệu hướng dẫn
```

---

## 🎯 Quy tắc phụ thuộc (Dependency Rule)

Trong Clean Architecture, các tầng phía ngoài chỉ được phép phụ thuộc vào các tầng bên trong:
$$\text{API / Presentation} \longrightarrow \text{Infrastructure} \longrightarrow \text{Use Cases} \longrightarrow \text{Domain}$$

1. **Domain Layer**: Chứa Entities và logic cốt lõi. **Không import** FastAPI, Pydantic, SQLAlchemy hay thư viện bên ngoài.
2. **Use Cases Layer**: Định nghĩa luồng xử lý ứng dụng và Interface `ItemRepository`. Phụ thuộc vào Domain.
3. **Infrastructure Layer**: Triển khai `ItemRepositoryImpl` sử dụng SQLAlchemy Async ORM. Phụ thuộc vào Use Cases và Domain.
4. **API Layer**: Sử dụng FastAPI Dependency Injection để nạp (inject) Repository Implementation vào các Use Cases và xử lý HTTP Request/Response DTOs (Pydantic).

---

## 🚀 Hướng dẫn khởi chạy (Setup & Run)

### 1. Tạo môi trường ảo & cài đặt phụ thuộc

```bash
python3 -m venv venv
source venv/bin/activate  # Trên Linux/macOS
# venv\Scripts\activate   # Trên Windows

pip install -r requirements.txt
```

### 2. Khởi chạy Uvicorn Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Truy cập giao diện Swagger UI tự động để test API:
👉 **`http://127.0.0.1:8000/docs`**

---

## 🧪 Chạy Tests (Automated Testing)

Chạy bộ unit test kiểm tra các Use Case (sử dụng InMemory Repository Mock):

```bash
pytest
```

---

## 🐳 Khởi chạy bằng Docker (Docker & Docker Compose)

Chỉ cần một lệnh duy nhất để build và chạy toàn bộ hệ thống gồm **FastAPI Backend** và **PostgreSQL**:

```bash
docker compose up -d --build
```

- **FastAPI API & Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **FastAPI Health & Host IP**: [http://localhost:8000/health](http://localhost:8000/health)
- **Prometheus Metrics Server**: [http://localhost:10001/metrics](http://localhost:10001/metrics)
- **Metrics Health Server**: [http://localhost:10001/health](http://localhost:10001/health)

Để dừng dịch vụ:
```bash
docker compose down
```

---

## 📊 Prometheus Metrics & IP Máy Tính (Host IP)

Hệ thống tích hợp sẵn cơ chế tự động phát hiện IP của máy tính/máy chủ và đính kèm vào Metrics:

1. **Auto-detection**: Hệ thống tự động xác định IP mạng nội bộ của máy chủ (`HOST_IP`). Bạn cũng có thể cấu hình cố định trong file `.env` bằng biến `HOST_IP=192.168.x.x`.
2. **Prometheus Info Metric**: Metric `app_host_info` chứa `host_ip`, `hostname`, `service_name`:
   ```prometheus
   app_host_info{host_ip="192.168.43.54",hostname="my-computer",service_name="FastAPI Clean Architecture Demo"} 1.0
   ```
3. **Mô hình Metrics 2 Tầng (2-Tier Observability)**:
   - **Tầng 1 (Báo cáo Tổng - Toàn hệ thống)**: Luôn ghi nhận 100% requests, responses, in-flight load và phân bổ thời gian toàn server:
     ```prometheus
     # Đếm số lượng Request đi vào server (Incoming)
     http_global_requests_incoming_total{host_ip="192.168.43.54",method="GET"} 1250.0

     # Đếm số lượng Response trả ra cho client (Outgoing)
     http_global_responses_total{host_ip="192.168.43.54",method="GET",status="200"} 1250.0

     # Số lượng Request đang được xử lý đồng thời (In-flight load)
     http_global_requests_in_flight{host_ip="192.168.43.54"} 3.0

     # Phân bổ thời gian phản hồi toàn server (Latency Histogram)
     http_global_request_duration_seconds_bucket{host_ip="192.168.43.54",le="0.005",method="GET"} 1200.0
     ```
   - **Tầng 2 (Báo cáo Riêng - Theo Router được bật / Có thể ẨN - HIDE)**: Đo đếm đầy đủ 4 chỉ số chi tiết cho từng Router được BẬT:
     ```prometheus
     # Đếm Request đi vào của từng Router
     http_requests_incoming_total{api_group="Items",handler="/api/v1/items",host_ip="192.168.43.54",method="GET"} 42.0

     # Đếm Response trả ra của từng Router
     http_responses_total{api_group="Items",handler="/api/v1/items",host_ip="192.168.43.54",method="GET",status="200"} 42.0

     # Số lượng Request đang xử lý dở của từng Router
     http_requests_in_flight{api_group="Items",host_ip="192.168.43.54"} 1.0

     # Độ trễ chi tiết của từng Router
     http_request_duration_seconds_bucket{api_group="Items",handler="/api/v1/items",host_ip="192.168.43.54",le="0.005",method="GET"} 40.0
     ```
4. **Cấu hình Bật / Tắt / Ẩn (Hide) Metrics cho Router qua `.env`**:
   - `PROMETHEUS_EXCLUDED_PATHS`: Ẩn metrics chi tiết theo tiền tố đường dẫn (vd: `/docs,/redoc,/openapi.json,/favicon.ico`).
   - `PROMETHEUS_EXCLUDED_TAGS`: Ẩn metrics chi tiết theo router tag (vd: `no-metrics,Dynamic APIs`).
   *(Khi một router bị ẩn ở Tầng 2, toàn bộ 4 chỉ số trên của router đó sẽ không sinh ra time-series, nhưng số request & response của nó vẫn được tính đầy đủ vào Báo cáo Tổng ở Tầng 1).*

---

## 📡 API Endpoints Mẫu

| HTTP Method | Endpoint | Query Parameters | Description |
|---|---|---|---|
| `GET` | `/` | None | Welcome & Thông tin Host IP |
| `GET` | `/health` | None | Health check & Thông tin Host IP |
| `POST` | `/api/v1/items` | None | Tạo Item mới |
| `GET` | `/api/v1/items` | `skip`, `limit`, `start_date`, `end_date` | Lấy danh sách Item (hỗ trợ phân trang và lọc theo khoảng thời gian) |
| `GET` | `/api/v1/items/{item_id}` | None | Lấy chi tiết Item theo ID |

### Ví dụ Lọc theo Thời gian (ISO 8601):
```http
GET /api/v1/items?start_date=2026-01-01T00:00:00&end_date=2026-12-31T23:59:59
```
