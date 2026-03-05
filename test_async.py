import os
import asyncio
import logging
from re import DEBUG
import trace
import traceback
from fasttask_manager import AsyncManager  # 假设 AsyncManager 在这里
# from fasttask_manager import Manager  # 仅作对比，实际测试不需要 Manager

# 配置日志，确保在异步环境中能看到输出
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AsyncTest")
logger.setLevel(logging.INFO)


async def async_test_suite():
    """
    异步测试套件，用于测试 AsyncManager 的所有异步方法。
    """
    task_name = "get_hypotenuse"
    params = {"a": 4, "b": 3}

    # 1. 初始化 AsyncManager
    # 传入 logger 以便在 AsyncManager 中使用
    am = AsyncManager(
        "127.0.0.1",
        port=9001,
        protocol="https",
        auth_user="john wick",
        auth_passwd="john_passwd",
        logger=logger,
    )

    logger.info("--- 开始异步测试套件 ---")

    # --- 测试 run 方法 (Run a task directly) ---
    logger.info("--- 1. 测试 run 方法 ---")
    r = await am.run(task_name, params)  # 🌟 使用 await
    assert r["state"] == "SUCCESS" and r["result"]["hypotenuse"] == 5.0
    logger.info("✅ run 测试通过")
    print("---------------------")

    # --- 测试 upload 方法 ---
    logger.info("--- 2. 测试 upload 方法 ---")
    # 假设当前目录下有 README.md 文件
    file_path = await am.upload("README.md")  # 🌟 使用 await
    assert file_path.endswith("README.md")
    logger.info("✅ upload 测试通过")
    print("---------------------")

    # --- 测试 download 方法 ---
    logger.info("--- 3. 测试 download 方法 ---")
    local_download_path = "./download_README_async.md"
    if os.path.exists(local_download_path):
        os.remove(local_download_path)

    await am.download(file_path, local_download_path)  # 🌟 使用 await
    assert os.path.exists(local_download_path)
    logger.info("✅ download 测试通过")
    print("---------------------")

    # --- 测试 create_and_wait_result 方法 (Poll and Wait) ---
    logger.info("--- 4. 测试 create_and_wait_result 方法 ---")
    r = await am.create_and_wait_result(
        task_name,
        params,
        check_gap=1,  # 间隔1秒轮询，在异步中不会阻塞 Worker
        simple_error_log=False,
        log_prefix="test_async:",
    )  # 🌟 使用 await
    assert r["hypotenuse"] == 5.0
    logger.info("✅ create_and_wait_result 测试通过")
    print("---------------------")

    # --- 测试 create_task, check, 和 revoke 方法 ---
    logger.info("--- 5. 测试 create_task, check, revoke 流程 ---")

    # 5a. create_task
    r = await am.create_task(task_name, params)  # 🌟 使用 await
    assert r["state"] == "PENDING"
    logger.info("✅ create_task 测试通过")
    print("---------------------")

    # 5b. check (非等待，仅检查状态)
    result_id = r["id"]
    r = await am.check(task_name, result_id)  # 🌟 使用 await
    assert r["state"] in ["STARTED", "PENDING"]
    logger.info("✅ check (PENDING/STARTED) 测试通过")
    print("---------------------")

    # 5c. revoke and check
    r = await am.revoke(result_id)  # 🌟 使用 await
    assert r["status"] == "SUCCESS"

    # 检查最终状态是否为 REVOKED
    r = await am.check(task_name, result_id)  # 🌟 使用 await
    assert r["state"] == "REVOKED"
    logger.info("✅ revoke/check (REVOKED) 测试通过")
    print("---------------------")

    logger.info("--- 所有异步测试完成 ---")


if __name__ == "__main__":
    for debug in [True, False]:
        os.environ["ASYNCMANAGER_DEBUG"]  = str(debug)
        asyncio.run(async_test_suite())
        logger.info("所有测试脚本执行完毕。")
