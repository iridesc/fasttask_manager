from fasttask_manager import Manager

if __name__ == "__main__":
    params = {"a": 4, "b": 3}
    m = Manager(
        "127.0.0.1",
        task_name="get_hypotenuse",
        port=80,
        auth_user="john wick",
        auth_passwd="john_passwd",
    )

    result = m.run(params)
    print(f"{result=}")

    file_path = m.upload("README.md")
    print(f"{file_path=}")
    m.download(file_path, "./download_README.md")

    result = m.create_and_wait_result(params)
    print(result)
