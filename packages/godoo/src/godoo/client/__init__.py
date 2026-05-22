from godoo.client.client import OdooClient, OdooClientConfig
from godoo.client.config import config_from_env, create_client
from godoo.client.errors import (
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
from godoo.client.safety import OperationInfo, SafetyContext
from godoo.client.services.accounting import AccountingService
from godoo.client.services.attendance import AttendanceService
from godoo.client.services.cdc import CdcService
from godoo.client.services.mail import MailService
from godoo.client.services.modules import ModuleManager
from godoo.client.services.properties import PropertiesService
from godoo.client.services.timesheets import TimesheetsService
from godoo.client.services.urls import UrlService

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
