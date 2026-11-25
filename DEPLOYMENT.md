# Deployment Information

**Student:** Vũ Quang Thái — 2A202603545  
**Deployed:** 2026-11-25

## Public URL

https://k5-day14-agent-k8sx.onrender.com

## Platform

Render Blueprint deploys the Docker app from `06-lab-complete/` in Singapore. The Blueprint creates the `k5-day14-agent` web service and the `k5-day14-redis` Key Value dependency on the free plan.

## Test Commands

Set `AGENT_API_KEY` locally to the secret stored in Render before running the authenticated request. Do not commit the key.

```bash
BASE="https://k5-day14-agent-k8sx.onrender.com"

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"                                  # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"                                   # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}' # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}' # 200
```

## Verified Results

Checked from Microsoft Edge on 2026-11-25: `/health` returned HTTP 200 with `status=ok`; `/ready` returned HTTP 200 with `ready=true`; `/ask` returned 401 without a key and 200 with the valid Render key. The key is not included in this repository.

## Environment Variables Set

- `PORT`
- `ENVIRONMENT`
- `AGENT_API_KEY` (generated and stored as a Render secret)
- `REDIS_URL` (Render Key Value connection string)
- `RATE_LIMIT_PER_MINUTE`
- `DAILY_BUDGET_USD`

## Screenshots

- [Deployment dashboard](screenshots/dashboard.jpg)
- [Service running](screenshots/running.jpg)
- [Test result (`/ready`)](screenshots/test.jpg)
