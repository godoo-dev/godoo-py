from godoo.client import OdooClient, OdooClientConfig
from godoo.config import config_from_env, create_client
from godoo.errors import (
    OdooAccessError,
    OdooAuthError,
    OdooError,
    OdooMissingError,
    OdooNetworkError,
    OdooRpcError,
    OdooSafetyError,
    OdooTimeoutError,
    OdooValidationError,
)
from godoo.safety import OperationInfo, SafetyContext
from godoo.services.accounting import AccountingService
from godoo.services.attendance import AttendanceService
from godoo.services.cdc import CdcService
from godoo.services.mail import MailService
from godoo.services.modules import ModuleManager
from godoo.services.properties import PropertiesService
from godoo.services.timesheets import TimesheetsService
from godoo.services.urls import UrlService

__all__ = [
    "AccountingService",
    "AttendanceService",
    "CdcService",
    "MailService",
    "ModuleManager",
    "OdooAccessError",
    "OdooAuthError",
    "OdooClient",
    "OdooClientConfig",
    "OdooError",
    "OdooMissingError",
    "OdooNetworkError",
    "OdooRpcError",
    "OdooSafetyError",
    "OdooTimeoutError",
    "OdooValidationError",
    "OperationInfo",
    "PropertiesService",
    "SafetyContext",
    "TimesheetsService",
    "UrlService",
    "config_from_env",
    "create_client",
]
