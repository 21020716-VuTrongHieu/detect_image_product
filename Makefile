include .env
export $(shell sed 's/=.*//' .env)

# Virtual environment
VENV=venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip
GUNICORN=$(VENV)/bin/gunicorn
COUNT_NODE_WORKERS=4
COUNT_THREADS=8

# Tạo virtualenv & cài đặt thư viện
venv:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

# Chạy script tạo database
init_db: venv
	$(PYTHON) scripts/init_db.py

# Chạy migrations (nếu dùng Alembic)
migrate: venv
	alembic upgrade head

# Chạy ứng dụng

run-dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
	
run: venv
	PYTHONPATH=. $(GUNICORN) -w ${COUNT_NODE_WORKERS} --threads ${COUNT_THREADS} -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 app.main:app

# Chạy ứng dụng bằng Docker
docker-build:
	docker build -t detect_image_product .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env detect_image_product

# Xóa database (nếu cần)
drop_db:
	psql -U postgres -h $(DB_HOST) -p $(DB_PORT) -c "DROP DATABASE IF EXISTS $(DB_NAME);"
	psql -U postgres -h $(DB_HOST) -p $(DB_PORT) -c "DROP USER IF EXISTS $(DB_USER);"

# Chạy tất cả (cài đặt, khởi tạo DB, chạy app)
setup: venv init_db migrate run