import time
import logging
import os
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth


class BaseManager:
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
        simple_error_log: bool = True,
        verify_ssl: bool = False,
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

        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(f"fasttask_server_{self.host}:{self.port}")
            if not self.logger.handlers:
                handler = StreamHandler()
                handler.setFormatter(
                    logging.Formatter(
                        f"%(asctime)s - %(name)s - {self.log_prefix} - %(levelname)s - %(message)s"
                    )
                )
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)

        debug_env = os.environ.get(
            f"{self.__class__.__name__}_DEBUG".upper(), "false"
        ).lower()
        if debug_env in ("true", "1", "yes"):
            self.logger.setLevel(logging.DEBUG)

    def _prepare_req_params(
        self,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ):
        return {
            "tries": tries or self.tries,
            "delay": delay or self.delay,
            "req_timeout": req_timeout or self.req_timeout,
            "logger": logger or self.logger,
            "log_prefix": log_prefix or self.log_prefix,
            "simple_error_log": self.simple_error_log
            if simple_error_log is None
            else simple_error_log,
        }

    def _req(self, path, data=None, method="p", file=None, raw_resp=False, **kwargs):
        raise NotImplementedError("_req must be implemented by subclass")

    def _wait(self, seconds: int):
        raise NotImplementedError("_wait must be implemented by subclass")

    def download(self, file_name, local_path, **kwargs):
        raise NotImplementedError("download must be implemented by subclass")

    def run(self, task_name: str, params: dict, **kwargs) -> dict:
        raise NotImplementedError("run must be implemented by subclass")

    def create_task(self, task_name: str, params: dict, **kwargs) -> dict:
        raise NotImplementedError("create_task must be implemented by subclass")

    def check(self, task_name, result_id: str, **kwargs) -> dict:
        raise NotImplementedError("check must be implemented by subclass")

    def upload(self, file_path, **kwargs) -> str:
        raise NotImplementedError("upload must be implemented by subclass")

    def revoke(self, result_id: str, **kwargs) -> dict:
        raise NotImplementedError("revoke must be implemented by subclass")

    def create_and_wait_result(
        self,
        task_name: str,
        params: dict,
        check_gap: int = 15,
        **kwargs,
    ) -> dict:
        raise NotImplementedError(
            "create_and_wait_result must be implemented by subclass"
        )
