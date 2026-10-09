from locust import HttpUser, between, tag, task


class ApiUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @tag("async")
    @task
    def async_wait(self):
        self.client.get("/async-wait")

    @tag("blocking")
    @task
    def blocking_bad(self):
        self.client.get("/blocking-bad")

    @tag("sync")
    @task
    def sync_def(self):
        self.client.get("/sync-def")