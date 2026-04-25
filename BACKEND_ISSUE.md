# Backend Container Crash Issue

## Problem Summary

The backend container in Kubernetes is failing with:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for SessionMemory
session_id
  Field required [type=missing, input_value={}, input_type=dict]
```

## Error Trace

```
File "/app/services/memory_service.py", line 125, in get_memory_service
    _memory_service = MemoryService(persist_path=persist_path)
File "/app/services/memory_service.py", line 17, in __init__
    self._load()
File "/app/services/memory_service.py", line 103, in _load
    self._store[session_id] = SessionMemory(**payload)
```

## Root Cause Analysis

### 1. Session Memory Persistence Format

The `_load()` method in `services/memory_service.py:98-103` reads:
```python
def _load(self) -> None:
    if not self._persist_path or not self._persist_path.exists():
        return
    data = json.loads(self._persist_path.read_text(encoding="utf-8"))
    for session_id, payload in data.items():
        self._store[session_id] = SessionMemory(**payload)
```

The `_save()` method writes:
```python
def _save(self) -> None:
    payload = {
        session_id: session.model_dump()
        for session_id, session in self._store.items()
    }
```

### 2. JSON Format

The saved JSON looks like:
```json
{
  "session123": {
    "session_id": "session123",
    "updated_at": 1234567890,
    "last_user_query": "coffee",
    ...
  }
}
```

### 3. Likely Corruption Scenarios

1. **Old/corrupted data file**: The persistent file may contain entries without `session_id` field
2. **Init container race**: The init command creates `{"sessions": {}}` but this may not be mounted in time
3. **Empty payload entries**: The file may have empty dict `{}` as values instead of SessionMemory objects

### 4. Deployment Initialization Issue

The deployment YAML has:
```yaml
command: ["/bin/sh", "-c"]
args:
  - |
    mkdir -p /app/data
    echo '{"sessions": {}}' > /app/data/session_memory.json
    exec uvicorn main:app --host 0.0.0.0 --port 8000
```

But this creates `{"sessions": {}}` while the code expects a dict where keys are session IDs with SessionMemory objects as values.

## Agent Task

1. **Read `backend/services/memory_service.py` completely**
2. **Understand how `_load()` and `_save()` work together**
3. **Fix the `_load()` method to be resilient to:**
   - Empty payloads
   - Missing `session_id` field in payload (use the dict key instead)
   - Corrupted/invalid entries (skip them)
4. **Consider adding a version/validation marker to the JSON file**
5. **Test the fix locally**
6. **Rebuild Docker image**
7. **Push to Docker Hub**
8. **Redeploy to Kubernetes**

## Expected Fix

The `_load()` method should:
1. Validate each payload before creating SessionMemory
2. Use session_id from dict key if missing from payload
3. Skip invalid entries instead of crashing
4. Log warnings for skipped entries