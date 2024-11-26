.PHONY: test

test:
	pixi run -e test pytest tests/

feat:
	pixi run -e test pytest tests/test_feat.py