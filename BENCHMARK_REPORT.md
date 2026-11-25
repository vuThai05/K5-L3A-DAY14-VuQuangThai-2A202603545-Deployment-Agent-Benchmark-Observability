# Benchmark & Observability Report — Day 14

**Họ tên:** Vũ Quang Thái  
**MSSV:** 2A202603545  
**Ngày chạy:** 2026-11-25 đến 2026-11-26 (GMT+7)  
**Môi trường:** Windows host, Python 3.11.9, Uvicorn; agent v1 tại cổng 8001, v2 tại cổng 8002. Load tests dùng 300 request mỗi lần.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Giới hạn tail latency để đa số request phản hồi nhanh. |
| Error rate `/ask` | ≤ 2% | Cho phép lỗi mock ngẫu nhiên nhỏ nhưng giữ độ sẵn sàng cao. |
| Accuracy trên golden dataset sau sửa KB | 100% | Bộ eval có 23 câu cố định; yêu cầu quality gate nghiêm ngặt sau khi sửa. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4.14 | 204.4 | 243.1 | 1701.6 | 1.33% | PASS |
| 10 | 34.69 | 207.4 | 247.7 | 1709.7 | 1.00% | PASS |
| 50 | 78.13 | 345.5 | 478.5 | 1835.0 | 0.67% | PASS |
| 100 | 80.02 | 666.7 | 1969.0 | 2186.8 | 1.00% | FAIL — p95 |

**Nhận xét:** Throughput tăng mạnh từ concurrency 1 đến 50, nhưng gần như đứng lại ở 100. p95 tăng lên 1.97 s tại concurrency 100, nên tăng đồng thời không còn cải thiện thông lượng hữu ích. p99 cao ở mọi mức do mock cố tình chèn request chậm; mức trung bình sẽ che khuất trải nghiệm của nhóm request ở đuôi.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---:|---:|---:|---:|
| 0 | 244.0 | 486.9 | 543.0 |
| 0.03 (mặc định) | 310.0 | 365.8 | 1775.3 |
| 0.1 | 391.7 | 1734.8 | 1765.1 |

**Nhận xét:** Tăng tỷ lệ slow request làm average tăng và khiến p99 nhảy từ 543 ms lên khoảng 1.8 s; khi 10% request chậm, p95 cũng vượt SLO. p99 gần như bão hòa quanh thời gian slow cố định 1.5 s. Percentile cho thấy nhóm người dùng bị ảnh hưởng; average không biểu đạt rõ nhóm này.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 sau sửa KB |
|---|---:|---:|---:|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56.7 | 109.3 | 117.3 |
| Tổng cost (USD) | 0.000399 | 0.000764 | 0.000822 |
| Cost / câu đúng (USD) | 0.00039855 | 0.00003639 | 0.00003573 |
| Quality gate | FAIL | PASS (≥80%, không regression) | PASS (100%, không regression) |

**Câu v2 sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Sửa trong knowledge base |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm giải thích JWT so với API key, có token expiry và kiểm tra chữ ký. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm entry về Kubernetes HPA scale theo CPU, memory và custom metrics. |

**Trade-off:** v2 ban đầu tăng accuracy 87 điểm phần trăm so với v1; p95 tăng 31 ms và tổng cost tăng khoảng 1.9 lần trên 23 câu. Do v2 trả lời đúng nhiều hơn, cost trên mỗi câu đúng thấp hơn khoảng 11 lần. Sau khi bổ sung hai entry KB, v2 đạt 23/23; quality gate đặt ở 100% PASS và không có regression.

**Quality gate trong CI:** `run_eval.py` trả exit code 0 khi đạt ngưỡng accuracy và không regression, ngược lại trả 1. Cho lệnh eval làm một bước GitHub Actions; exit code khác 0 sẽ làm job thất bại và chặn merge. Đã chạy v1 so với baseline v2: gate FAIL, exit code 1.

---

## 4. Observability stack (production)

Không chạy phần này theo yêu cầu dừng CP8. Không có kết quả Grafana, Jaeger, Prometheus alerts hoặc ảnh observability.

## 5. Benchmark scaling (production)

Không chạy Locust/Docker scale test theo yêu cầu dừng CP8; không có CSV `scale_1_stats.csv` hoặc `scale_3_stats.csv`.

---

## 6. Kết luận

1. p95/p99 cho thấy tail latency và vi phạm SLO mà latency trung bình có thể che mất.
2. v2 tốn nhiều token hơn nhưng trả lời đúng tốt hơn; cost trên mỗi câu đúng hữu ích hơn cost trên mỗi request.
3. Eval baseline có thể làm quality gate tự động; exit code khác 0 giúp CI chặn regression trước merge.

Trong production thật, cần thêm alert cho saturation/queue depth và theo dõi error budget theo cửa sổ thời gian. Phần này là đề xuất, chưa được chạy trong lab.