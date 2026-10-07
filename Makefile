# LIFEGRID Lambda build Makefile
# Used by SAM CLI (BuildMethod: makefile) to assemble Lambda deployment packages.
# Each target receives ARTIFACTS_DIR from SAM and copies the necessary sources.

# Common sources needed by all Lambdas
BACKEND_SRC := backend
DATA_SRC := backend/data
DYNAMO_STORE := lambda/shared/dynamo_store.py

.PHONY: build-LifegridApiFunction build-LifegridRiskProcessorFunction \
        build-LifegridResourceProcessorFunction build-LifegridNotificationProcessorFunction

build-LifegridApiFunction:
	cp lambda/api/handler.py $(ARTIFACTS_DIR)/handler.py
	cp $(DYNAMO_STORE) $(ARTIFACTS_DIR)/dynamo_store.py
	cp -r $(BACKEND_SRC) $(ARTIFACTS_DIR)/backend
	cp -r backend/data $(ARTIFACTS_DIR)/backend/data

build-LifegridRiskProcessorFunction:
	cp lambda/risk_processor/handler.py $(ARTIFACTS_DIR)/handler.py
	cp $(DYNAMO_STORE) $(ARTIFACTS_DIR)/dynamo_store.py
	cp -r $(BACKEND_SRC) $(ARTIFACTS_DIR)/backend
	cp -r backend/data $(ARTIFACTS_DIR)/backend/data

build-LifegridResourceProcessorFunction:
	cp lambda/resource_processor/handler.py $(ARTIFACTS_DIR)/handler.py
	cp $(DYNAMO_STORE) $(ARTIFACTS_DIR)/dynamo_store.py
	cp -r $(BACKEND_SRC) $(ARTIFACTS_DIR)/backend
	cp -r backend/data $(ARTIFACTS_DIR)/backend/data

build-LifegridNotificationProcessorFunction:
	cp lambda/notification_processor/handler.py $(ARTIFACTS_DIR)/handler.py
	cp $(DYNAMO_STORE) $(ARTIFACTS_DIR)/dynamo_store.py
	cp -r $(BACKEND_SRC) $(ARTIFACTS_DIR)/backend
	cp -r backend/data $(ARTIFACTS_DIR)/backend/data
