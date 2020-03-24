class EndpointResponse(Exception):
    def __init__(self, code: int, message: str):
        self.response = {"status": {"code": code, "message": message}}


class EndpointSuccess(EndpointResponse):
    def __init__(self):
        super().__init__(200, "Success")


class EndpointError(EndpointResponse):
    def __init__(self, code: int, message: str):
        super().__init__(code, message)


class EndpointNotFound(EndpointError):
    def __init__(self, endpoint_key: str):
        super().__init__(400, f"Endpoint {endpoint_key} not found.")


class EndpointBadArguments(EndpointError):
    def __init__(self, endpoint_key: str):
        super().__init__(400, f"Endpoint {endpoint_key} bad arguments.")


class DiscordIDNotFound(EndpointError):
    def __init__(self, id_not_found: int):
        super().__init__(400, f"Discord ID {id_not_found} not found.")


class InternalServerError(EndpointError):
    def __init__(self):
        super().__init__(500, "Internal server error.")
