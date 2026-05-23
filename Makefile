.PHONY: test lint web-typecheck web-lint web-build validate smoke-api prepare-web-env

test:
	pytest -q

lint:
	ruff check .

web-typecheck:
	cd web && npm run typecheck

web-lint:
	cd web && npm run lint

web-build:
	cd web && npm run build

validate: test lint web-typecheck web-lint web-build

smoke-api:
	python3 scripts/smoke_api.py

prepare-web-env:
	python3 scripts/prepare_web_env.py

prod-readiness:
	python3 scripts/check_production_readiness.py
