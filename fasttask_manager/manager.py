import time
import requests
import traceback
from retry import retry
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth

from .base_manager import BaseManager


class Manager(BaseManager):
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
        req_timeout=30,
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
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings()

    def _req(
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

        @retry(tries=params["tries"], delay=params["delay"])
        def req():

            file_handle = open(file, "rb") if file else None
            req_params = {
                "url": f"{self.url}{path}",
                "auth": self.auth,
                "files": None if not file_handle else {"file": file_handle},
                "timeout": params["req_timeout"],
                "verify": self.verify_ssl,
            }

            req_start = time.time()

            try:
                if method == "p":
                    r = requests.post(json=data, **req_params)
                elif method == "g":
                    r = requests.get(params=data, **req_params)
                else:
                    raise Exception("method must be p or g")

                params["logger"].debug(
                    f"{params['log_prefix']}: url={req_params['url']} status_code={r.status_code} cost={round(time.time() - req_start)}s resp_data={r.content[:200] if raw_resp else r.content}"
                )

                r.raise_for_status()
            except Exception as e:
                error = str(e) if params["simple_error_log"] else traceback.format_exc()
                params["logger"].info(
                    f"{params['log_prefix']}: url={req_params['url']} cost={round(time.time() - req_start)}s error={error}"
                )
                raise e
            finally:
                if file_handle is not None:
                    file_handle.close()

            return r if raw_resp else r.json()

        return req()

    def download(
        self,
        file_name,
        local_path,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ):
        r = self._req(
            "/download",
            data={"file_name": file_name},
            method="g",
            raw_resp=True,
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=512):
                f.write(chunk)

    def _wait(self, seconds: int):
        time.sleep(seconds)

    def run(self, task_name: str, params: dict, **kwargs) -> dict:
        return self._req(path=f"/run/{task_name}", data=params, **kwargs)

    def create_task(self, task_name: str, params: dict, **kwargs) -> dict:
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.debug(f"{log_prefix}: task creating...")
        return self._req(path=f"/create/{task_name}", data=params, **kwargs)

    def check(self, task_name, result_id: str, **kwargs) -> dict:
        resp = self._req(
            path=f"/check/{task_name}",
            data={"result_id": result_id},
            method="g",
            **kwargs,
        )
        log_prefix = kwargs.get("log_prefix", self.log_prefix)
        self.logger.debug(f"{log_prefix}: check task: {resp['state']}")
        return resp

    def upload(self, file_path, **kwargs) -> str:
        return self._req("/upload", method="p", file=file_path, **kwargs)["file_name"]

    def revoke(self, result_id: str, **kwargs) -> dict:
        return self._req(path="/revoke", data={"result_id": result_id}, **kwargs)

    def create_and_wait_result(
        self,
        task_name: str,
        params: dict,
        check_gap: int = 15,
        **kwargs,
    ) -> dict:
        start = time.time()
        log_prefix = kwargs.get("log_prefix", self.log_prefix)

        resp = self.create_task(task_name, params, **kwargs)
        self.logger.info(
            f"{log_prefix}: cost: {time.time() - start} create_task resp: {resp}"
        )

        while True:
            resp = self.check(task_name, result_id=resp["id"], **kwargs)
            self.logger.debug(f"{log_prefix}: {resp=}")

            if resp["state"] == "FAILURE":
                self.logger.info(f"{log_prefix}: cost: {time.time() - start}")
                raise Exception(f"task: {resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(f"{log_prefix}: cost: {time.time() - start}")
                return resp["result"]

            self._wait(check_gap)
