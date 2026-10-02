# GhostAPI checks. `make check` is the source of truth for non-VM work.
# Real macOS VM integration is BLOCKED_VM_STORAGE: `make test-vm` says so and fails.

UV := uv run --frozen

.PHONY: check lint format format-check typecheck test invariants secrets swift test-vm demo-synthetic

check: lint format-check typecheck test invariants secrets swift
	@echo "make check: PASSED (non-VM checks only; REAL VM integration: BLOCKED_VM_STORAGE)"

lint:
	$(UV) ruff check .

format:
	$(UV) ruff format .

format-check:
	$(UV) ruff format --check .

typecheck:
	$(UV) mypy

test:
	$(UV) pytest -m "not vm"

invariants:
	$(UV) python tools/invariants.py

secrets:
	gitleaks git --no-banner --redact .
	gitleaks git --pre-commit --no-banner --redact .

swift:
	@echo "swift: no Swift package yet. MacOSBridge is BLOCKED_VM_STORAGE; swift build/test/swiftlint not run."

test-vm:
	@echo "BLOCKED_VM_STORAGE: real VM integration tests need a disposable macOS VM (insufficient host storage)."
	@echo "No VM tests were run. This is not a pass."
	@exit 3

demo-synthetic:
	$(UV) python tools/demo_synthetic.py
