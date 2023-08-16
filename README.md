manager for [fasttask](https://github.com/iridesc/fasttask) 

### create project 

```bash
python -m fasttask_manager.create_project
```


### create a Manager

```python
m = Manager("127.0.0.1", task_name="get_hypotenuse", port=8080)
```


### run a task

```python
result = m.run(params)
```


### create a task and check result later

```python
result_id = m.create_task(params)
# do something...
# do something...
# do something...
result = m.check(result_id)
```

### create a task and wait for result

```python
result = m.create_and_wait_result(params)    
```
