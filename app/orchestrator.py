class Orchestrator:

    def __init__(self, api_client):
        self.api_client = api_client

    def execute(self, plan):
        results = []

        for step_number, step in enumerate(plan["steps"], start=1):

            endpoint = step["api"]
            parameters = step["parameters"]

            print(f"\nExecuting step {step_number}: {endpoint}")
            print(f"Parameters: {parameters}")

            result = self.api_client.call(
                endpoint,
                parameters
            )

            results.append({
                "step": step_number,
                "api": endpoint,
                "result": result
            })

            # Stop execution immediately if an API fails
            if result.get("status") != "success":

                print(
                    f"Execution stopped at step {step_number}."
                )

                return {
                    "status": "failed",
                    "failed_step": step_number,
                    "results": results
                }

        return {
            "status": "success",
            "results": results
        }