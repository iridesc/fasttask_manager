from fasttask_manager import Manager

if __name__ == "__main__":
    params = {"a": 4, "b": 3}
    m = Manager(
        "127.0.0.1",
        task_name="get_hypotenuse",
        port=9001,
        protocol="https",
        auth_user="john wick",
        auth_passwd="john_passwd",
    )

    r = m.run(params)
    print(f"m.run {r=}")
    print("---------------------")

    file_path = m.upload("README.md")
    print(f"m.upload {file_path=}")
    print("---------------------")

    m.download(file_path, "./download_README.md")
    print("m.download done")
    print("---------------------")

    r = m.create_and_wait_result(params)
    print(f"m.create_and_wait_result {r=}")
    print("---------------------")

    r = m.create_task(params)
    print(f"m.create_task {r=}")
    print("---------------------")

    result_id = r["id"]
    r = m.check(result_id)
    print(f"m.check {r=}")
    print("---------------------")

    r = m.revoke(result_id)
    print(f"m.revoke {r=}")
    r = m.check(result_id)
    assert r["state"] == "REVOKED"
    print("---------------------")

    print("done")