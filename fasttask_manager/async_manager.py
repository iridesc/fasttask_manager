import time
import asyncio
import httpx
import traceback
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)

from .base_manager import BaseManager


class AsyncManager(BaseManager):
    def __init__(
        self,
        host: str,
        protocol: str = "http",
        port: int = 80,
        tries: int = 5,
        delay: int = 3,
        logger=None,
        log_prefix: str = "",
        auth_user: str = "",
        auth_passwd: str = "",
        url_base_path: str = "",
        req_timeout: int = 30,
        simple_error_log=True,
        verify_ssl=False,
    ) -> None:
        super().__init__(
            host=host,
            protocol=protocol,
            port=port,
            tries=tries,
            delay=delay,
            logger=logger,
            log_prefix=log_prefix,
            auth_user=auth_user,
            auth_passwd=auth_passwd,
            url_base_path=url_base_path,
            req_timeout=req_timeout,
            simple_error_log=simple_error_log,
            verify_ssl=verify_ssl,
        )

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
        params = self._prepare_req_params(
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )

        file_handle = None
        result = None

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(params["tries"]),
            wait=wait_fixed(params["delay"]),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        ):
            with attempt:
                req_start = time.time()
                file_handle = None

                async with httpx.AsyncClient(
                    auth=self.auth,
                    timeout=params["req_timeout"],
                    verify=self.verify_ssl,
                    trust_env=False,
                ) as client:
                    req_params = {
                        "url": f"{self.url}{path}",
                        "timeout": params["req_timeout"],
                    }

                    post_kwargs = {}

                    try:
                        if method == "p":
                            if file:
                                file_handle = open(file, "rb")
                                post_kwargs["files"] = {"file": file_handle}
                            r = await client.post(
                                json=data, **req_params, **post_kwargs
                            )
                        elif method == "g":
                            r = await client.get(params=data, **req_params)
                        else:
                            raise ValueError("method must be p or g")

                        params["logger"].debug(
                            f"{params['log_prefix']}: url={req_params['url']} status_code={r.status_code} cost={round(time.time() - req_start)}s resp_data={r.content[:200] if raw_resp else r.content}"
                        )

                        r.raise_for_status()

                    except Exception as e:
                        error = (
                            str(e)
                            if params["simple_error_log"]
                            else traceback.format_exc()
                        )
                        params["logger"].info(
                            f"{params['log_prefix']}: url={req_params['url']} cost={round(time.time() - req_start)}s error={error}"
                        )
                        raise e
                    finally:
                        if file_handle:
                            file_handle.close()

                result = r if raw_resp else r.json()

        return result

    async def download(self, file_name, local_path, **kwargs):
        req_params = self._prepare_req_params(**kwargs)

        async with httpx.AsyncClient(
            auth=self.auth,
            timeout=req_params["req_timeout"],
            verify=self.verify_ssl,
            trust_env=False,
        ) as client:
            async with client.stream(
                "GET",
                f"{self.url}/download",
                params={"file_name": file_name},
            ) as r:
                r.raise_for_status()

                with open(local_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=512):
                        f.write(chunk)

    async def _wait(self, seconds: int):
        await asyncio.sleep(seconds)

    async def run(self, task_name: str, params: dict, **kwargs) -> dict:
        return await self._req(path=f"/run/{task_name}", data=params, **kwargs)

    async def create_task(self, task_name: str, params: dict, **kwargs) -> dict:
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.debug(f"{log_prefix}: task creating...")
        return await self._req(path=f"/create/{task_name}", data=params, **kwargs)

    async def check(self, task_name, result_id: str, **kwargs) -> dict:
        resp = await self._req(
            path=f"/check/{task_name}",
            data={"result_id": result_id},
            method="g",
            **kwargs,
        )
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.debug(f"{log_prefix}: check task: {resp['state']}")
        return resp

    async def upload(self, file_path, **kwargs) -> str:
        return (await self._req("/upload", method="p", file=file_path, **kwargs))[
            "file_name"
        ]

    async def revoke(self, result_id: str, **kwargs) -> dict:
        return await self._req(path="/revoke", data={"result_id": result_id}, **kwargs)

    async def create_and_wait_result(
        self,
        task_name: str,
        params: dict,
        check_gap: int = 15,
        **kwargs,
    ) -> dict:
        start = time.time()
        log_prefix = kwargs.get("log_prefix", self.log_prefix)

        resp = await self.create_task(task_name, params, **kwargs)
        self.logger.info(
            f"{log_prefix}: cost: {time.time() - start} create_task resp: {resp}"
        )

        while True:
            resp = await self.check(task_name, result_id=resp["id"], **kwargs)
            self.logger.debug(f"{log_prefix}: {resp=}")

            if resp["state"] == "FAILURE":
                self.logger.info(f"{log_prefix}: cost: {time.time() - start}")
                raise Exception(f"task: {resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(f"{log_prefix}: cost: {time.time() - start}")
                return resp["result"]

            await self._wait(check_gap)
