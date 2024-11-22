SHELL := /bin/bash

include ./tests/tests.env

.EXPORT_ALL_VARIABLES: unit-tests
.PHONY: unit-tests
unit-tests: 
	@GOJAUNTLY_PRIVATE_KEY=$$(openssl ecparam -genkey -name prime256v1 -noout); \
	pytest tests/unittest

