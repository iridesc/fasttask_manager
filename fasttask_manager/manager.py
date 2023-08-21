import time
import requests
from retry import retry
from logging import Logger, StreamHandler
from requests.auth import HTTPBasicAuth


class Manager:
    def __init__(self, host: str, task_name: str, protocol: str = "http", port: int = 80, check_gap: int = 15,
                 tries: int = 5, delay: int = 3, logger: Logger = None, log_prefix: str = "",
                 auth_user: str = "", auth_passwd: str = "") -> None:

        self.task_name = task_name
        self.protocol = protocol
        self.host = host
        self.port = port
        self.url = f"{self.protocol}://{self.host}:{self.port}"
        self.tries = tries
        self.delay = delay
        self.check_gap = check_gap
        self.logger = logger
        self.log_prefix = f"{log_prefix}{self.task_name}:"
        self.auth = HTTPBasicAuth(auth_user, auth_passwd)
        if self.logger:
            return

        self.logger = Logger(task_name)
        self.logger.addHandler(StreamHandler())

    def _req(self, path, data: dict = None, method="p", file: str = None, raw_resp: bool = False):
        @retry(tries=self.tries, delay=self.delay)
        def req():
            params = {
                "url": f"{self.url}{path}",
                "auth": self.auth,
                "files": None if not file else {
                    'file': open(file, 'rb')
                }
            }
            if method == "p":
                r = requests.post(json=data, **params)
            elif method == "g":
                r = requests.get(params=data, **params)

            r.raise_for_status()
            return r if raw_resp else r.json()
        return req()

    def run(self, params: dict) -> dict:
        return self._req(path=f"/run/{self.task_name}/", data=params)

    def create_task(self, params: dict) -> dict:
        self.logger.info(f"{self.log_prefix}: task creating...")
        return self._req(path=f"/create/{self.task_name}/", data=params)

    def check(self, result_id: str) -> dict:
        resp = self._req(path=f"/check/{self.task_name}/", data={"result_id": result_id}, method="g")
        self.logger.info(f"{self.log_prefix}: check task: {resp['state']}")
        return resp

    def upload(self, file_path) -> str:
        return self._req("/upload", method="p", file=file_path)["file_name"]

    def download(self, file_name, local_path):
        r = self._req("/download", data={"file_name": file_name}, method="g", raw_resp=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=512):
                f.write(chunk)

    def create_and_wait_result(self, params: dict) -> dict:
        start = time.time()
        resp = self.create_task(params)

        if resp["state"] != "PENDING":
            raise Exception(f"create task error: state unexpected: {resp}")

        result_id = resp["id"]

        while True:
            resp = self.check(result_id=result_id)
            if resp["state"] == "FAILURE":
                self.logger.info(f"{self.log_prefix} cost: {time.time()-start}")
                raise Exception(f"task :{resp['result']}")

            elif resp["state"] == "SUCCESS":
                self.logger.info(f"{self.log_prefix} cost: {time.time()-start}")
                return resp["result"]

            time.sleep(self.check_gap)
