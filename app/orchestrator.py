class Orchestrator:

    def __init__(self, api_client):
        self.api_client = api_client

    def execute(self, plan, user_id=None):
        results = []

        if user_id is None:
            return {
                "status": "failed",
                "message": "User ID is required to execute the plan.",
                "results": results
            }

        for step_number, step in enumerate(plan["steps"], start=1):
            endpoint = step["api"]
            parameters = step["parameters"]

            print(f"\nExecuting step {step_number}: {endpoint}")
            print(f"User ID: {user_id}")
            print(f"Parameters: {parameters}")

            result = self.api_client.call(
                endpoint,
                parameters,
                user_id=user_id
            )

            results.append({
                "step": step_number,
                "api": endpoint,
                "result": result
            })

            if not isinstance(result, dict) or result.get("status") != "success":
                print(f"Execution stopped at step {step_number}.")

                return {
                    "status": "failed",
                    "failed_step": step_number,
                    "results": results
                }

        return {
            "status": "success",
            "results": results
        }