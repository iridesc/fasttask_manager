import time
from venv import logger
import requests
import traceback
from retry import retry
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth


class Manager:
    def __init__(
        self,
        host: str,
        task_name: str,
        protocol: str = "http",
        port: int = 80,
        check_gap: int = 15,
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
        self.task_name = task_name
        self.protocol = protocol
        self.host = host
        self.port = port
        self.url = f"{self.protocol}://{self.host}:{self.port}{url_base_path}"
        self.tries = tries
        self.delay = delay
        self.check_gap = check_gap
        self.log_prefix = f"{log_prefix} url={self.url} task_name={self.task_name}"
        self.auth = HTTPBasicAuth(auth_user, auth_passwd)
        self.req_timeout = req_timeout
        self.simple_error_log = simple_error_log
        self.verify_ssl = verify_ssl
        if not self.verify_ssl:
            import urllib3

            urllib3.disable_warnings()

        self.logger = logger
        if self.logger:
            return

        self.logger = Logger(task_name)
        self.logger.addHandler(StreamHandler())

    def _req(
        self,
        path,
        data: dict = None,
        method="p",
        file: str = None,
        raw_resp: bool = False,
    ):
        @retry(tries=self.tries, delay=self.delay)
        def req():
            params = {
                "url": f"{self.url}{path}",
                "auth": self.auth,
                "files": None if not file else {"file": open(file, "rb")},
                "timeout": self.req_timeout,
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
                r.raise_for_status()
            except Exception as e:
                error = str(e) if self.simple_error_log else traceback.format_exc()
                self.logger.error(
                    f"{self.log_prefix}: url={params['url']} error={error}"
                )
                raise e
            finally:
                logger.info(f"{self.log_prefix}: cost={int(time.time() - req_start)}s")
            return r if raw_resp else r.json()

        return req()

    def run(self, params: dict) -> dict:
        return self._req(path=f"/run/{self.task_name}", data=params)

    def create_task(self, params: dict) -> dict:
        self.logger.info(f"{self.log_prefix}: task creating...")
        return self._req(path=f"/create/{self.task_name}", data=params)

    def check(self, result_id: str) -> dict:
        resp = self._req(
            path=f"/check/{self.task_name}", data={"result_id": result_id}, method="g"
        )
        self.logger.info(f"{self.log_prefix}: check task: {resp['state']}")
        return resp

    def upload(self, file_path) -> str:
        return self._req("/upload", method="p", file=file_path)["file_name"]

    def download(self, file_name, local_path):
        r = self._req(
            "/download", data={"file_name": file_name}, method="g", raw_resp=True
        )
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=512):
                f.write(chunk)

    def revoke(self, result_id: str) -> dict:
        return self._req(path="/revoke", data={"result_id": result_id})

    def create_and_wait_result(self, params: dict) -> dict:
        start = time.time()
        resp = self.create_task(params)

        self.logger.info(
            f"{self.log_prefix} cost: {time.time() - start} create_task resp: {resp}"
        )

        while True:
            resp = self.check(result_id=resp["id"])
            if resp["state"] == "FAILURE":
                self.logger.info(f"{self.log_prefix} cost: {time.time() - start}")
                raise Exception(f"task :{resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(f"{self.log_prefix} cost: {time.time() - start}")
                return resp["result"]

            time.sleep(self.check_gap)
