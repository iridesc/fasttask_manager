import os
from fasttask_manager import Manager

if __name__ == "__main__":
    task_name = "get_hypotenuse"
    params = {"a": 4, "b": 3}
    m = Manager(
        "127.0.0.1",
        port=9001,
        protocol="https",
        auth_user="john wick",
        auth_passwd="john_passwd",
    )

    r = m.run(task_name, params)
    assert r["state"] == "SUCCESS" and r["result"]["hypotenuse"] == 5.0
    print("---------------------")

    file_path = m.upload("README.md")
    assert file_path.endswith("README.md")
    print("---------------------")
    if os.path.exists("./download_README.md"): 
        os.remove("./download_README.md")
    m.download(file_path, "./download_README.md")
    assert os.path.exists("./download_README.md")
    print("---------------------")

    r = m.create_and_wait_result(task_name, params, check_gap=1, simple_error_log=False, log_prefix="test:")
    assert r["hypotenuse"] == 5.0
    print("---------------------")

    r = m.create_task(task_name, params)
    assert r["state"] == "PENDING"
    print("---------------------")

    result_id = r["id"]
    r = m.check(task_name, result_id)
    assert r["state"] in ["STARTED", "PENDING"]  
    print("---------------------")

    r = m.revoke(result_id)
    assert r["status"] == "SUCCESS"
    r = m.check(task_name, result_id)
    assert r["state"] == "REVOKED"
    print("---------------------")

    print("done")