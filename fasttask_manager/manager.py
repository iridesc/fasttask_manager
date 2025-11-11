import time
import requests
import traceback
from retry import retry
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth


class Manager:
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
            import urllib3

            urllib3.disable_warnings()

        if logger:
            self.logger = logger
        else:
            self.logger = Logger(f"fasttask_server_{self.host}:{self.port}")
            self.logger.addHandler(StreamHandler())

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
        tries = tries or self.tries
        delay = delay or self.delay
        req_timeout = req_timeout or self.req_timeout
        logger = logger or self.logger
        log_prefix = log_prefix or self.log_prefix
        simple_error_log = (
            self.simple_error_log if simple_error_log is None else simple_error_log
        )

        @retry(tries=tries, delay=delay)
        def req():
            params = {
                "url": f"{self.url}{path}",
                "auth": self.auth,
                "files": None if not file else {"file": open(file, "rb")},
                "timeout": req_timeout,
                "verify": self.verify_ssl,
            }

            req_start = time.time()

            try:
                if method == "p":
                    r = requests.post(json=data, **params)
                elif method == "g":
                    r = requests.get(params=data, **params)
                else:
                    raise Exception("method must be p or g")
                logger.info(
                    f"{log_prefix}: url={params['url']} status_code={r.status_code=}  cost={round(time.time() - req_start)}s"
                )
                r.raise_for_status()
            except Exception as e:
                error = str(e) if simple_error_log else traceback.format_exc()

                logger.info(
                    f"{log_prefix}: url={params['url']}  cost={round(time.time() - req_start)}s error={error}"
                )
                raise e
    
            return r if raw_resp else r.json()

        return req()

    def run(
        self,
        task_name: str,
        params: dict,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> dict:
        return self._req(
            path=f"/run/{task_name}",
            data=params,
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )

    def create_task(
        self,
        task_name: str,
        params: dict,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> dict:
        self.logger.info(
            f"{self.log_prefix if log_prefix is None else log_prefix}: task creating..."
        )
        return self._req(
            path=f"/create/{task_name}",
            data=params,
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )

    def check(
        self,
        task_name,
        result_id: str,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> dict:
        resp = self._req(
            path=f"/check/{task_name}",
            data={"result_id": result_id},
            method="g",
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )
        self.logger.info(
            f"{self.log_prefix if log_prefix is None else log_prefix}: check task: {resp['state']}"
        )
        return resp

    def upload(
        self,
        file_path,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> str:
        return self._req(
            "/upload",
            method="p",
            file=file_path,
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )["file_name"]

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

    def revoke(
        self,
        result_id: str,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> dict:
        return self._req(
            path="/revoke",
            data={"result_id": result_id},
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )

    def create_and_wait_result(
        self,
        task_name: str,
        params: dict,
        check_gap: int = 15,
        tries=None,
        delay=None,
        req_timeout=None,
        logger=None,
        log_prefix=None,
        simple_error_log=None,
    ) -> dict:
        start = time.time()
        resp = self.create_task(
            task_name,
            params,
            tries=tries,
            delay=delay,
            req_timeout=req_timeout,
            logger=logger,
            log_prefix=log_prefix,
            simple_error_log=simple_error_log,
        )

        self.logger.info(
            f"{self.log_prefix if log_prefix is None else log_prefix} cost: {time.time() - start} create_task resp: {resp}"
        )

        while True:
            resp = self.check(
                task_name,
                result_id=resp["id"],
                tries=tries,
                delay=delay,
                req_timeout=req_timeout,
                logger=logger,
                log_prefix=log_prefix,
                simple_error_log=simple_error_log,
            )
            if resp["state"] == "FAILURE":
                self.logger.info(
                    f"{self.log_prefix if log_prefix is None else log_prefix} cost: {time.time() - start}"
                )
                raise Exception(f"task :{resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(
                    f"{self.log_prefix if log_prefix is None else log_prefix} cost: {time.time() - start}"
                )
                return resp["result"]

            time.sleep(check_gap)
