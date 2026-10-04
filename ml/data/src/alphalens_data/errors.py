"""Stable data error codes without raw provider payloads or credentials."""


class DataContractError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProviderNotSelectedError(DataContractError):
    def __init__(self) -> None:
        super().__init__("PROVIDER_NOT_SELECTED")
