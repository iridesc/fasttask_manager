# fasttask_manager

Manager for [fasttask](https://github.com/iridesc/fasttask)

## Installation

```bash
pip install fasttask_manager
```

## Usage

### Create a Manager

**Synchronous Manager:**

```python
from fasttask_manager import Manager

m = Manager("127.0.0.1", port=8080)
```

**Asynchronous Manager:**

```python
import asyncio
from fasttask_manager import AsyncManager

async def main():
    am = AsyncManager("127.0.0.1", port=8080)
    # use await
    result = await am.run(params)
```

### Run a task

```python
result = m.run(params)
```

### Create a task and check result later

```python
result_id = m.create_task(params)
# do something...
result = m.check(result_id)
```

### Create a task and wait for result

```python
result = m.create_and_wait_result(params)
```

### Upload a file

```python
file_name = m.upload("/path/to/file.txt")
```

### Download a file

```python
m.download("file.txt", "/path/to/save.txt")
```

### Revoke a task

```python
m.revoke(result_id)
```

## Configuration

| Parameter | Type | Default | Description |
|------------|------|---------|-------------|
| host | str | - | Server host |
| protocol | str | "http" | HTTP protocol |
| port | int | 80 | Server port |
| tries | int | 5 | Max retry attempts |
| delay | int | 3 | Retry delay (seconds) |
| logger | Logger | None | Custom logger |
| log_prefix | str | "" | Log prefix |
| auth_user | str | "" | Basic auth username |
| auth_passwd | str | "" | Basic auth password |
| url_base_path | str | "" | URL base path |
| req_timeout | int | 30 | Request timeout (seconds) |
| simple_error_log | bool | True | Simple error logging |
| verify_ssl | bool | False | Verify SSL certificate |

## Architecture

```
BaseManager (shared initialization and utilities)
├── Manager (synchronous implementation)
│   ├── _req: uses requests library
│   └── _wait: uses time.sleep
└── AsyncManager (asynchronous implementation)
    ├── _req: uses httpx async client
    └── _wait: uses asyncio.sleep
```
