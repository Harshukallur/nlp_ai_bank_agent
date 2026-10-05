import json


class APIValidator:

    def __init__(self, catalog_path):

        with open(catalog_path, "r") as file:
            catalog = json.load(file)

        self.apis = {
            api["endpoint"]: api
            for api in catalog["apis"]
        }

    # --------------------------------------------------
    # Type validation helper
    # --------------------------------------------------

    def validate_type(self, value, expected_type):

        if expected_type == "string":
            return isinstance(value, str)

        if expected_type == "number":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )

        if expected_type == "integer":
            return (
                isinstance(value, int)
                and not isinstance(value, bool)
            )

        if expected_type == "boolean":
            return isinstance(value, bool)

        return True

    # --------------------------------------------------
    # Main validation
    # --------------------------------------------------

    def validate(self, plan):

        # --------------------------------------------------
        # 1. Check plan structure
        # --------------------------------------------------

        if not isinstance(plan, dict):

            return (
                False,
                "Plan must be a JSON object."
            )

        # --------------------------------------------------
        # 2. Check status
        # --------------------------------------------------

        if "status" in plan:

            if plan["status"] != "success":

                return (
                    False,
                    "Plan status must be 'success'."
                )

        # --------------------------------------------------
        # 3. Check steps
        # --------------------------------------------------

        if "steps" not in plan:

            return (
                False,
                "Missing 'steps' in API plan."
            )

        if not isinstance(plan["steps"], list):

            return (
                False,
                "'steps' must be a list."
            )

        if len(plan["steps"]) == 0:

            return (
                False,
                "API plan must contain at least one step."
            )

        # --------------------------------------------------
        # 4. Validate every API step
        # --------------------------------------------------

        for step_number, step in enumerate(
            plan["steps"],
            start=1
        ):

            # --------------------------------------------------
            # Check step structure
            # --------------------------------------------------

            if not isinstance(step, dict):

                return (
                    False,
                    f"Step {step_number} must be a JSON object."
                )

            if "api" not in step:

                return (
                    False,
                    f"Missing API endpoint in step {step_number}."
                )

            if "parameters" not in step:

                return (
                    False,
                    f"Missing parameters in step {step_number}."
                )

            endpoint = step["api"]

            parameters = step["parameters"]

            # --------------------------------------------------
            # Parameters must be an object
            # --------------------------------------------------

            if not isinstance(parameters, dict):

                return (
                    False,
                    f"Parameters for {endpoint} must be a JSON object."
                )

            # --------------------------------------------------
            # 5. API must exist in catalog
            # --------------------------------------------------

            if endpoint not in self.apis:

                return (
                    False,
                    f"Unknown API: {endpoint}"
                )

            api_definition = self.apis[endpoint]

            expected_parameters = (
                api_definition.get(
                    "parameters",
                    {}
                )
            )

            # --------------------------------------------------
            # 6. Check required parameters
            # --------------------------------------------------

            for (
                param_name,
                param_definition
            ) in expected_parameters.items():

                if param_name not in parameters:

                    return (
                        False,
                        f"Missing parameter '{param_name}' "
                        f"for {endpoint}"
                    )

                value = parameters[param_name]

                # --------------------------------------------------
                # 7. Validate parameter type
                # --------------------------------------------------

                expected_type = param_definition.get(
                    "type"
                )

                if expected_type:

                    if not self.validate_type(
                        value,
                        expected_type
                    ):

                        return (
                            False,
                            f"Invalid type for parameter "
                            f"'{param_name}' in {endpoint}. "
                            f"Expected {expected_type}, "
                            f"received {type(value).__name__}."
                        )

                # --------------------------------------------------
                # 8. Normalize currency
                # --------------------------------------------------

                if (
                    param_name == "currency"
                    and isinstance(value, str)
                ):

                    normalized_value = (
                        value.strip().lower()
                    )

                    currency_map = {
                        "rupees": "INR",
                        "rupee": "INR",
                        "rs": "INR",
                        "₹": "INR",
                        "inr": "INR"
                    }

                    if normalized_value in currency_map:

                        parameters[param_name] = (
                            currency_map[
                                normalized_value
                            ]
                        )

                        value = parameters[param_name]

                # --------------------------------------------------
                # 9. Validate allowed values
                # --------------------------------------------------

                allowed_values = (
                    param_definition.get(
                        "allowed_values"
                    )
                )

                if allowed_values:

                    if value not in allowed_values:

                        return (
                            False,
                            f"Invalid value '{value}' "
                            f"for parameter '{param_name}' "
                            f"in {endpoint}. "
                            f"Allowed values: "
                            f"{allowed_values}"
                        )

            # --------------------------------------------------
            # 10. Reject unexpected parameters
            # --------------------------------------------------

            for param_name in parameters:

                if param_name not in expected_parameters:

                    return (
                        False,
                        f"Unexpected parameter "
                        f"'{param_name}' for {endpoint}"
                    )

        # --------------------------------------------------
        # 11. Everything passed
        # --------------------------------------------------

        return (
            True,
            "API validation passed."
        )