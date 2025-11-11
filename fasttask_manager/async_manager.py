import time
import asyncio
import httpx
import traceback
import logging
import os  # For the fix in download method
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth

# 🌟 引入 Tenacity 依赖
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,  # 用于在重试前记录日志
)

# 移除自定义的 async_retry 函数


class AsyncManager:
    def __init__(
        self,
        host: str,
        protocol: str = "http",
        port: int = 80,
        tries: int = 5,
        delay: int = 3,
        logger: Logger = None,
        log_prefix: str = "",
        auth_user: str = "",
        auth_passwd: str = "",
        url_base_path: str = "",
        req_timeout: int = 30,
        simple_error_log=True,
        verify_ssl=False,
    ) -> None:
        self.protocol = protocol
        self.host = host
        self.port = port
        self.url = f"{self.protocol}://{self.host}:{self.port}{url_base_path}"
        self.tries = tries
        self.delay = delay
        self.log_prefix = (
            log_prefix if log_prefix else f"fasttask_server={self.host}:{self.port}"
        )
        self.auth = HTTPBasicAuth(auth_user, auth_passwd)
        self.req_timeout = req_timeout
        self.simple_error_log = simple_error_log
        self.verify_ssl = verify_ssl
        if not self.verify_ssl:
            # Note: httpx uses standard library warnings, not urllib3
            pass

        # 修复后的 logger 逻辑：
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f"fasttask_server_{self.host}:{self.port}")
            if not self.logger.handlers:
                # 避免重复添加 StreamHandler，只在没有处理器时添加
                handler = StreamHandler()
                handler.setFormatter(
                    logging.Formatter(
                        f"%(asctime)s - %(name)s - {self.log_prefix} - %(levelname)s - %(message)s"
                    )
                )
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)

    # 🌟 异步请求核心方法，现在使用 Tenacity
    async def _req(
        self,
        path,
        data: dict = None,
        method="p",
        file: str = None,
        raw_resp: bool = False,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ):
        # 参数覆盖逻辑与 Manager 保持同步
        tries = tries or self.tries
        delay = delay or self.delay
        req_timeout = req_timeout or self.req_timeout
        logger = logger or self.logger
        log_prefix = log_prefix or self.log_prefix
        simple_error_log = (
            self.simple_error_log if simple_error_log is None else simple_error_log
        )

        # 🌟 使用 Tenacity 配置重试策略
        retry_config = retry(
            # 停止条件：达到最大尝试次数
            stop=stop_after_attempt(tries),
            # 等待条件：固定延迟
            wait=wait_fixed(delay),
            # 异常条件：只在 httpx 的客户端或状态错误时重试
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
            # 重试前的日志记录，替换了自定义装饰器中的日志逻辑
            before_sleep=before_sleep_log(
                logger,
                logging.WARNING,
                # 自定义消息格式，包含重试信息
                # tenacity 会自动提供 retry_state 对象
                "[%s] Retrying in %%s seconds, attempt %%s of %%s..." % log_prefix,
            ),
        )

        # 🌟 将 Tenacity 装饰器应用到内部函数
        @retry_config
        async def req_with_retry():
            # 使用 httpx.AsyncClient 进行异步请求
            async with httpx.AsyncClient(
                auth=self.auth,
                timeout=req_timeout,
                verify=self.verify_ssl,
                # 🚀 修复：显式禁用从环境变量加载代理，以解决 SOCKS 代理错误
                trust_env=False,
            ) as client:
                # 🚀 修复 2/2：_req 的通用参数中不再包含 files
                params = {
                    "url": f"{self.url}{path}",
                    "timeout": req_timeout,
                }

                # 准备 POST/文件上传请求的额外参数
                post_kwargs = {}
                file_handle = None

                try:
                    req_start = time.time()

                    if method == "p":
                        if file:
                            file_handle = open(file, "rb")
                            post_kwargs["files"] = {"file": file_handle}
                        # POST 请求使用 json=data
                        r = await client.post(json=data, **params, **post_kwargs)
                    elif method == "g":
                        # GET 请求不使用 files 参数
                        r = await client.get(params=data, **params)
                    else:
                        raise ValueError("method must be p or g")

                    logger.info(
                        f"{log_prefix}: url={params['url']} status_code={r.status_code} cost={round(time.time() - req_start)}s"
                    )

                    # 抛出 httpx.HTTPStatusError，Tenacity 会捕获并重试
                    r.raise_for_status()

                except Exception as e:
                    # 捕获 httpx 错误，并在日志中记录，然后重新抛出（Tenacity 会处理重试）
                    error = str(e) if simple_error_log else traceback.format_exc()
                    logger.info(
                        f"{log_prefix}: url={params['url']} cost={round(time.time() - req_start)}s error={error}"
                    )
                    # 🌟 这里的 raise 是为了让 tenacity 捕获异常并决定是否重试
                    raise e
                finally:
                    if file_handle:
                        # 确保文件句柄在请求完成后关闭，防止资源泄露
                        file_handle.close()

                return r if raw_resp else r.json()

        # 外部调用内部的重试函数
        return await req_with_retry()

    # --- 所有公共方法都保持 async 状态 ---

    async def run(self, task_name: str, params: dict, **kwargs) -> dict:
        return await self._req(path=f"/run/{task_name}", data=params, **kwargs)

    async def create_task(self, task_name: str, params: dict, **kwargs) -> dict:
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.info(
            f"{log_prefix if log_prefix is not None else self.log_prefix}: task creating..."
        )
        return await self._req(path=f"/create/{task_name}", data=params, **kwargs)

    async def check(self, task_name, result_id: str, **kwargs) -> dict:
        resp = await self._req(
            path=f"/check/{task_name}",
            data={"result_id": result_id},
            method="g",
            **kwargs,
        )
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.info(
            f"{log_prefix if log_prefix is not None else self.log_prefix}: check task: {resp['state']}"
        )
        return resp

    async def upload(self, file_path, **kwargs) -> str:
        # upload 使用 POST 方法和 file 参数
        return (await self._req("/upload", method="p", file=file_path, **kwargs))[
            "file_name"
        ]

    async def download(self, file_name, local_path, **kwargs):
        # 异步下载和写入：使用 httpx 的流式响应
        async with httpx.AsyncClient(
            auth=self.auth,
            timeout=kwargs.get("req_timeout", self.req_timeout),
            verify=self.verify_ssl,
            trust_env=False,  # 修复：下载时也禁用代理
        ) as client:
            # 🚀 修复: 使用 client.stream 方法进行流式下载
            async with client.stream(
                "GET",
                f"{self.url}/download",
                params={"file_name": file_name},
            ) as r:
                r.raise_for_status()

                # 🌟 修正: 使用标准的同步 open 在异步循环中写入（避免依赖 anyio）
                try:
                    with open(local_path, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=512):
                            f.write(chunk)
                except Exception as e:
                    self.logger.error(f"Failed to write file {local_path}: {e}")
                    raise

            # 响应流由 async with 块自动关闭，无需 r.aclose()

    async def revoke(self, result_id: str, **kwargs) -> dict:
        return await self._req(path="/revoke", data={"result_id": result_id}, **kwargs)

    # 核心：异步等待循环
    async def create_and_wait_result(
        self,
        task_name: str,
        params: dict,
        check_gap: int = 15,
        **kwargs,
    ) -> dict:
        start = time.time()
        log_prefix = kwargs.get("log_prefix", self.log_prefix)

        # 1. 异步创建任务
        resp = await self.create_task(task_name, params, **kwargs)

        self.logger.info(
            f"{log_prefix if log_prefix is not None else self.log_prefix} cost: {time.time() - start} create_task resp: {resp}"
        )

        while True:
            # 2. 异步检查状态
            resp = await self.check(task_name, result_id=resp["id"], **kwargs)

            # 3. 检查状态
            if resp["state"] == "FAILURE":
                self.logger.info(
                    f"{log_prefix if log_prefix is not None else self.log_prefix} cost: {time.time() - start}"
                )
                raise Exception(f"task :{resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(
                    f"{log_prefix if log_prefix is not None else self.log_prefix} cost: {time.time() - start}"
                )
                return resp["result"]

            # 4. 异步等待，释放 Worker 资源
            await asyncio.sleep(check_gap)
