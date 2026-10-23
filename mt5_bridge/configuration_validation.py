"""Compatibility adapter; the rules live in geraset_domain."""
from geraset_domain.uni_configuration import Configuration
from geraset_domain.uni_configuration import validate_configuration as shared_validate
from geraset_domain.errors import UniValidationError
from .errors import BridgeError


def validate_configuration(values, contract):
    try:
        return shared_validate(values, contract)
    except UniValidationError as exc:
        raise BridgeError(exc.code, exc.message, exc.status) from exc
