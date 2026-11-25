# ============================================================
# TODO (tiêu chí 1): viết lại thành Dockerfile production
#   • Multi-stage build: stage builder cài dependencies, stage runtime chỉ copy kết quả
#   • Base image slim (vd python:3.11-slim) và chạy bằng user non-root
#   • Có HEALTHCHECK gọi GET /health
#   • Image cuối < 500 MB
#   • CMD lắng nghe theo biến PORT (mặc định 8000) và uvicorn phải là PID 1
#     (exec form, hoặc `sh -c "exec uvicorn ..."`) để nhận SIGTERM khi `docker stop`
#
# Bản dưới đây build và chạy được nhưng CHƯA đạt yêu cầu nào ở trên.
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PORT=8000
RUN groupadd --system agent && useradd --system --gid agent --home-dir /app agent
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=agent:agent app/ ./app/
COPY --chown=agent:agent utils/ ./utils/
USER agent
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','8000'), timeout=2)"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
