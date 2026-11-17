"""装配系统字典的存储和国家数据源。"""

from data_provider.system.system_countries_source import fetch_countries
from src.application.system.system_dict_service import SystemDictService
from src.infrastructure.persistence.repositories.system_dict_repository import (
    SqlAlchemySystemDictRepository,
)
from src.storage import DatabaseManager


def build_system_dict_service() -> SystemDictService:
    return SystemDictService(
        repository=SqlAlchemySystemDictRepository(DatabaseManager.get_instance()),
        fetch_countries=fetch_countries,
    )
