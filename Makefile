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
	@echo "  make start-all      Start infra and all Python services (bg)"
	@echo "  make stop-all       Stop all Python services and infra"
	@echo "  make overlay        Start GUI overlay in background"
	@echo "  make overlay-hotkey Start overlay with hotkey enabled (X11)"
	@echo "  make overlay-stop   Stop GUI overlay"
	@echo "  make overlay-logs   Tail overlay logs"
	@echo "  make smoke          Run overlay smoke test"
	@echo "  make ci             Run tests and linters"
	@echo ""
	@echo "Models:"
	@echo "  make download-model Download default model"
	@echo ""
	@echo "Desktop Integration:"
	@echo "  make desktop         Install .desktop launcher for overlay"
	@echo "  make autostart       Enable overlay autostart on login"
	@echo "  make desktop-clean   Remove launcher and autostart entries"

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
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@make status

stop:
	@echo "Stopping Neuralux services..."
	docker compose down

restart: stop start

status:
	@echo "Neuralux Service Status:"
	@echo ""
	@docker compose ps
	@echo ""
	@echo "Message Bus:"
	@curl -s http://localhost:8222/varz | grep -q "server_id" && echo "✓ NATS is running" || echo "✗ NATS is not running"
	@echo "Redis:"
	@redis-cli ping 2>/dev/null | grep -q "PONG" && echo "✓ Redis is running" || echo "✗ Redis is not running"
	@echo "Qdrant:"
	@curl -s http://localhost:6333/healthz | grep -q "ok" && echo "✓ Qdrant is running" || echo "✗ Qdrant is not running"

logs:
	docker compose logs -f

start-all:
	@bash scripts/start-all.sh

stop-all:
	@bash scripts/stop-all.sh

overlay:
	@echo "Starting overlay with Ctrl+Space hotkey (background)..."
	@mkdir -p data/logs data/run
	@/bin/sh -c 'nohup aish overlay --hotkey --tray > data/logs/overlay.log 2>&1 & echo $$! > data/run/overlay.pid'
	@echo "✓ Overlay started with Ctrl+Space hotkey and tray → logs: data/logs/overlay.log"

overlay-stop:
	@echo "Stopping overlay..."
	@/bin/sh -c 'if [ -f data/run/overlay.pid ]; then PID=$$(cat data/run/overlay.pid); if kill -0 $$PID 2>/dev/null; then kill $$PID 2>/dev/null || true; sleep 1; kill -9 $$PID 2>/dev/null || true; fi; rm -f data/run/overlay.pid; echo "✓ Overlay stopped"; else echo "Overlay not running"; fi'

overlay-logs:
	@tail -f data/logs/overlay.log

smoke:
	@bash scripts/smoke-overlay.sh

start-llm:
	@echo "Starting LLM service..."
	cd services/llm && python service.py

test:
	pytest tests/ -v

lint:
	black packages/ services/ --check
	ruff check packages/ services/

ci: test lint

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

desktop:
	@echo "Installing desktop launcher..."
	@mkdir -p ~/.local/share/applications
	@printf "[Desktop Entry]\nName=Neuralux Overlay\nComment=Open the Neuralux assistant overlay with Ctrl+Space hotkey\nExec=aish overlay --hotkey --tray\nTerminal=false\nType=Application\nIcon=utilities-terminal\nCategories=Utility;\nStartupNotify=false\n" > ~/.local/share/applications/neuralux-overlay.desktop
	@echo "✓ Launcher installed at ~/.local/share/applications/neuralux-overlay.desktop"

autostart: desktop
	@echo "Enabling autostart..."
	@mkdir -p ~/.config/autostart
	@cp ~/.local/share/applications/neuralux-overlay.desktop ~/.config/autostart/
	@echo "✓ Autostart enabled"

desktop-clean:
	@echo "Removing desktop entries..."
	@rm -f ~/.local/share/applications/neuralux-overlay.desktop
	@rm -f ~/.config/autostart/neuralux-overlay.desktop
	@echo "✓ Desktop entries removed"

