# safe-deployment-simulator
system that safely deploys a mock service across multiple regions, monitors the rollout, and automatically performs a rollback if health checks fail.


- Runs a **mock HTTP service** in multiple “regions”
- Safely **rolls out** a new version across regions, one by one
- Performs **health checks** during the rollout and **automatically rolls back** if something goes wrong
- Exposes **Prometheus metrics** for each region
- Visualizes regional health in **Grafana**

## Architecture Overview

### Components

1. **Mock Service (Flask)**
   - Endpoints:
     - `GET /` – returns JSON `{status, version, region}`
     - `GET /health` – returns random failures based on `FAILURE_RATE`
     - `GET /metrics` – returns Prometheus metrics:
       - `service_up{version,region}` (gauge)
       - `service_info{version,region}` (gauge)
   - Configured via environment:
     - `VERSION` – version string (e.g. `v1`, `v2`)
     - `REGION` – logical region name (e.g. `us-west`, `eu-west`)
     - `FAILURE_RATE` – probability (0.0–1.0) that `/health` returns unhealthy

2. **Multi-Region Setup (Docker Compose)**
   - Regions are modeled as **four separate services**:
     - `region-us-west` → exposed on `localhost:8081`
     - `region-us-east` → `localhost:8082`
     - `region-eu-west` → `localhost:8083`
     - `region-ap-south` → `localhost:8084`
   - All use the same image, but different `REGION` env vars.

3. **Prometheus**
   - Scrapes all four regional services at `/metrics`.
   - Configured via `prometheus.yml`.

4. **Grafana**
   - Uses Prometheus as a datasource.
   - Auto-provisioned with:
     - `grafana-datasources.yml` – points to Prometheus
     - `grafana-dashboards.yml` – loads dashboards from a folder
     - `simple-dashboard.json` – a ready-made dashboard:
       - Shows `service_up` per region as a Stat panel.

5. **Deployment Controller (`deploy-with-rollback.py`)**
   - Safely rolls out a new `VERSION` with a given `FAILURE_RATE`.
   - Operates region-by-region using `docker compose`.
   - Verifies:
     - Container is up
     - `/` reports the expected `version`
     - `/health` passes (with retries)
   - On any failure:
     - Performs **rollback** to the previous (stable) version across all regions that were already updated.



## Running the Stack

Follow these steps to run the full multi-region system, including Prometheus, Grafana, and the deployment controller.

---

### 1. Install Dependencies

#### Controller dependencies:
```bash
cd controller
pip install -r requirements.txt
```

### 2. Build All Docker Images
```bash
cd service
docker compose build
```

### 3. Start the Entire Stack
```bash
docker compose up -d
```

### 4. Verify Services are up
```bash
curl http://localhost:8081/
curl http://localhost:8081/health
curl http://localhost:8081/metrics
```

### 5. Run the rollout controller
```bash
python controller/deploy-with-rollback.py v2
```

### 6. Simulate a bad release
```bash
python controller/deploy-with-rollback.py v3 0.8
```

This deploys:
- version v3
- 80% health failure probability
  
#### Expected behavior:
- First region becomes unhealthy
- Rollback is triggered
- All previously updated regions revert to stable version

