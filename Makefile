.PHONY: help install install-dev start stop status clean test

help:
	@echo "Neuralux AI Layer - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install all packages"
	@echo "  make install-dev    Install with development dependencies"
	@echo ""
	@echo "Services:"
	@echo "  make start          Start all services"
	@echo "  make stop           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make status         Check service status"
	@echo "  make logs           View service logs"
	@echo ""
	@echo "Development:"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make clean          Clean generated files"
	@echo ""
	@echo "Models:"
	@echo "  make download-model Download default model"

install:
	@echo "Installing Neuralux packages..."
	pip install -r requirements.txt
	pip install -e packages/common/
	pip install -e packages/cli/
	@echo "✓ Installation complete"

install-dev: install
	pip install pytest pytest-asyncio black ruff mypy
	@echo "✓ Development dependencies installed"

start:
	@echo "Starting Neuralux services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@make status

stop:
	@echo "Stopping Neuralux services..."
	docker-compose down

restart: stop start

status:
	@echo "Neuralux Service Status:"
	@echo ""
	@docker-compose ps
	@echo ""
	@echo "Message Bus:"
	@curl -s http://localhost:8222/varz | grep -q "server_id" && echo "✓ NATS is running" || echo "✗ NATS is not running"
	@echo "Redis:"
	@redis-cli ping 2>/dev/null | grep -q "PONG" && echo "✓ Redis is running" || echo "✗ Redis is not running"
	@echo "Qdrant:"
	@curl -s http://localhost:6333/healthz | grep -q "ok" && echo "✓ Qdrant is running" || echo "✗ Qdrant is not running"

logs:
	docker-compose logs -f

start-llm:
	@echo "Starting LLM service..."
	cd services/llm && python service.py

test:
	pytest tests/ -v

lint:
	black packages/ services/ --check
	ruff check packages/ services/

format:
	black packages/ services/
	ruff check packages/ services/ --fix

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/

download-model:
	@echo "Creating models directory..."
	@mkdir -p models
	@echo ""
	@echo "To use Neuralux, you need to download a model."
	@echo ""
	@echo "Recommended model: Llama-3.2-3B-Instruct (Q4_K_M)"
	@echo "Download from: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF"
	@echo ""
	@echo "Or use this command:"
	@echo "  wget https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf -P models/"
	@echo ""
	@echo "After downloading, the model will be available at:"
	@echo "  ./models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

