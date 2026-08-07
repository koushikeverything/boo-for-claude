# Boo for Claude — developer entrypoints.
.PHONY: check test connector-test validate package doctor clean

# The single command that runs every quality gate.
check:
	bash scripts/quality_gate.sh

# Skill-side tests only.
test:
	python3 -m unittest discover -s tests -p 'test_*.py'

# Connector tests only.
connector-test:
	cd connector && python3 -m unittest discover -s tests -p 'test_*.py'

# Validate the plugin + all golden payloads.
validate:
	python3 scripts/validate_plugin.py .
	@for f in evals/expected/*.json; do \
		python3 skills/daily-brief/scripts/validate_brief.py --schema schemas/daily-brief.schema.json $$f >/dev/null || exit 1; \
	done
	@echo "validated plugin + all golden payloads"

# Build the claude.ai-uploadable Skill ZIPs (dist/*-skill.zip). Re-bundles team-brief first.
package:
	bash scripts/bundle_team_brief.sh
	bash scripts/package_skill.sh daily-brief
	bash scripts/package_skill.sh team-brief

# Diagnose connectors that will fail on a missing env var/token (Claude Code configs).
doctor:
	python3 scripts/connector_doctor.py

clean:
	rm -rf dist boo.db connector/boo.db **/__pycache__ .pytest_cache
