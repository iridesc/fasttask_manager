from fasttask_manager import Manager

if __name__ == "__main__":
    params = {"a": 4, "b": 3}
    m = Manager("127.0.0.1", task_name="get_hypotenuse", port=8080)
    # result = m.run(params)
    # print(result)
    result = m.create_and_wait_result(params)
    print(result)
