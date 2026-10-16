class InvalidGraphRelationshipError(ValueError):
    """A graph relationship violates deterministic domain admission rules."""


class EvidenceAdmissionError(InvalidGraphRelationshipError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
