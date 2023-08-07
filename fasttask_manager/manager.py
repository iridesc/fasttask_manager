import time
import requests
from retry import retry
from logging import Logger, StreamHandler


class Manager:
    def __init__(self, host: str, task_name: str, protocol: str = "http", port: int = 80, check_gap: int = 15,
                 tries: int = 5, delay: int = 3, logger: Logger = None, log_prefix: str = "") -> None:

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
        if self.logger:
            return

        self.logger = Logger(task_name)
        self.logger.addHandler(StreamHandler())

    def _req(self, path, data: dict, method="p"):
        @retry(tries=self.tries, delay=self.delay)
        def req():
            if method == "p":
                r = requests.post(f"{self.url}{path}", json=data)
            elif method == "g":
                r = requests.get(f"{self.url}{path}", params=data)

            r.raise_for_status()
            return r.json()
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

    def create_and_wait_result(self, params: dict) -> dict:
        start = time.time()
        resp = self.create_task(params)

        if resp["state"] != "PENDING":
            raise Exception(f"create task error: state unexpected: {resp['state']}")

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
