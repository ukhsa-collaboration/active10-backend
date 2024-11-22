SHELL := /bin/bash

.PHONY: unit-tests
unit-tests:
	@source ./tests/tests.env; \
	GOJAUNTLY_PRIVATE_KEY=$$(openssl ecparam -genkey -name prime256v1 -noout); \
	pytest tests/unittest

