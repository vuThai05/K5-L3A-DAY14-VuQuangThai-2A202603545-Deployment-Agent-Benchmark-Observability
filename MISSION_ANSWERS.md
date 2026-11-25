# Day 14 Lab — Mission Answers

**Student Name:** Vũ Quang Thái

**Student ID:** 2A202603545

**Date:** 2026-11-25

## CP1 — Localhost vs Production

`POST /ask?question=Hello` trên bản develop trả HTTP 200.

Các anti-pattern trong `01-localhost-vs-production/develop/app.py`:

1. API key và database URL viết thẳng trong source code; lộ khi push repository.
2. In API key vào log, làm credential xuất hiện trong log/terminal.
3. `DEBUG = True` cố định, có thể làm lộ thông tin nội bộ.
4. Không có `/health` hoặc `/ready` để platform kiểm tra trạng thái.
5. Chỉ bind `localhost`, nên container/platform không truy cập được từ bên ngoài.
6. Port cố định `8000`, không đọc `PORT` do nền tảng inject.
7. Bật `reload=True` và dùng `print()` khi chạy server.
8. Không chờ request đang xử lý khi nhận SIGTERM.

| Tính năng | Develop | Production | Lý do |
|---|---|---|---|
| Config | Giá trị hard-code | Đọc environment variables | Có thể thay cấu hình theo môi trường, không commit secret |
| Health/readiness | Không có | `/health`, `/ready` | Liveness để restart process; readiness để ngừng route traffic khi chưa sẵn sàng |
| Logging | `print()` và có thể log secret | JSON có cấu trúc | Dễ tìm kiếm/parse, tránh ghi credential |
| Shutdown | Không chờ request | Lifespan chờ server đóng êm | Tránh cắt ngang request khi deploy hoặc dừng container |
| Network/port | `localhost:8000` | `0.0.0.0` và `PORT` từ env | Chạy được trong container và trên cloud |

## CP2 — Docker

### Exercise 2.1

1. Base image develop: `python:3.11`.
2. Working directory: `/app`.
3. Copy `requirements.txt` trước source để Docker tái sử dụng layer cài dependencies khi chỉ source thay đổi.
4. `CMD` đặt lệnh mặc định của container; `ENTRYPOINT` xác định executable chính và thường nhận thêm arguments từ lúc chạy container.

### Exercise 2.2–2.3

Build từ gốc repository. Kích thước đo bằng `docker image inspect`:

| Image | Bytes | `docker images` |
|---|---:|---:|
| `my-agent:develop` | 1,667,792,212 | 1.67 GB |
| `my-agent:advanced` | 239,815,627 | 240 MB |

Bản advanced nhỏ hơn khoảng **85.6%**. Stage builder cài dependencies; stage runtime chỉ nhận phần cần chạy, dùng base `slim` và user non-root.

Container develop khởi động và `POST /ask?question=Hello` trả JSON có trường `answer`.

### Exercise 2.4

```text
Client → Nginx (80/443) → Agent (mạng nội bộ, 8000)
                              ├── Redis (cache/state)
                              └── Qdrant (vector database)
```

Stack `k5-day14-cp2` đã chạy. Qua Nginx, `GET /health` trả **200** và `POST /ask` với JSON `{"question":"Explain microservices"}` trả **200**. Stack và các volume tạo cho bài test đã được dừng/xóa sau khi kiểm tra.

## CP3 — API Security

JWT flow: `POST /auth/token` với `student / demo123` trả token; client gửi token trong `Authorization: Bearer …` khi gọi `POST /ask`. Token ký HS256, hết hạn sau 60 phút. Không lưu token vào file trả lời.

Kết quả kiểm tra thực tế:

| Trường hợp | HTTP |
|---|---:|
| Lấy token | 200 |
| Gọi `/ask` không token | 401 |
| Gọi `/ask` với token hợp lệ | 200 |
| Gửi liên tục đến khi vượt hạn mức | 429 |

Rate limiter mẫu dùng sliding window 60 giây, lưu timestamp trong bộ nhớ của process: student tối đa 10 request/phút; teacher/admin 100 request/phút. Vì state còn trong RAM, bản demo này chưa chia sẻ hạn mức giữa nhiều instance.

Cost guard mẫu kiểm tra trước khi gọi LLM và ghi nhận token sau khi gọi: budget $1/ngày mỗi user, $10/ngày toàn hệ thống; giá mẫu $0.00015/1K input tokens và $0.0006/1K output tokens. Part 6 chuyển rate-limit và cost state sang Redis để dùng chung giữa worker/instance.

## CP4 — Scaling & Reliability

Kiểm tra trên `05-scaling-reliability/develop` bằng Python 3.11 trong WSL:

- `/health`: `status=ok`.
- `/ready`: HTTP 200, `ready=true`.
- Đang có request `/ask`, gửi SIGTERM: request hoàn tất HTTP 200 và process thoát code 0.

Liveness chỉ xác nhận process còn sống; readiness xác nhận instance có thể nhận traffic. Trong bản production, session/history được lưu ở Redis để instance khác đọc được; Nginx phân phối request tới các agent.

**Chưa chạy được** bài Compose scale 3 instance và `test_stateless.py`: Docker Desktop WSL engine hiện báo không gắn được data disk (`/dev/sde` không có thiết bị). Không suy diễn kết quả load balancing khi chưa chạy được stack.

## CP5 — Final Project

Đã hoàn thiện agent trong `06-lab-complete/`: config từ env, API-key auth, Redis sliding-window limiter, Redis cost guard, health/readiness, JSON logging, graceful shutdown, Docker multi-stage/non-root/healthcheck, Compose Redis, `.dockerignore` và Railway config.

Checker đầy đủ chạy trong Python 3.11.18 / POSIX WSL đã xác nhận:

- Runtime checks: health/readiness (kể cả Redis down), auth 401/200, rate limit 429 và state còn sau restart, cost guard 402, env config, JSON logs, graceful SIGTERM: **đều đạt**.
- Docker build: **đạt**, 21 giây.
- Kích thước image: **238 MB**, dưới 500 MB.
- Không hoàn tất kiểm tra `docker run`/`docker stop`: Docker Desktop WSL báo filesystem read-only, sau đó báo không thể provision data disk `/dev/sde`.

Vì vậy trạng thái hiện tại là **10/12 tiêu chí checker đạt; còn 2 kiểm tra phụ thuộc Docker run/stop chưa đạt do Docker Desktop**, không phải do checker bị sửa. `06-lab-complete/check_production_ready.py` được giữ nguyên.
