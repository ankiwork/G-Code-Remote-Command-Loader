import re
import serial.tools.list_ports

from typing import Optional, List, Dict, Tuple, Pattern, Any

from project.station.logging.station_logger import logger
from project.station.config.port_finder.port_finder_config import PortFinderConfig
from project.station.utils.port_finder_utils import verify_port, get_port_info, is_virtual_port


class PortFinder:
    """
    Класс для поиска и идентификации последовательных портов станции.

    Пример использования:
    >>> finder = PortFinder()
    >>> # Поиск с использованием кеша (результат проверяем)
    >>> found_port = finder.find_station_port()
    >>> found_port is None or isinstance(found_port, str)
    True
    >>> # Принудительный поиск нового порта с проверкой
    >>> new_port = finder.find_station_port(use_cached=False)
    >>> new_port is None or isinstance(new_port, str)
    True
    >>> # Очистка кеша с проверкой результата
    >>> cache_cleared = finder.clear_cache()
    >>> isinstance(cache_cleared, bool)
    True
    """

    KNOWN_DEVICES: Dict[Tuple[int, int], str] = {
        (0x1A86, 0x7523): "CH340 Serial Adapter",
        (0x2341, 0x0043): "Arduino Uno",
        (0x2341, 0x0001): "Arduino Mega",
        (0x0403, 0x6001): "FTDI FT232",
        (0x10C4, 0xEA60): "CP210x Serial Adapter",
    }

    COMMON_PATTERNS: List[Pattern[str]] = [
        re.compile(r'laser', re.IGNORECASE),
        re.compile(r'cnc|grbl|serial|usb|ch34|arduino', re.IGNORECASE),
    ]

    def __init__(self) -> None:
        """Инициализация PortFinder с конфигурацией и логгером."""
        self.logger = logger
        self.config = PortFinderConfig()
        self.logger.debug("Инициализация PortFinder")

    def find_station_port(self, vid: Optional[int] = None, pid: Optional[int] = None,
                          preferred_devices: Optional[List[str]] = None,
                          skip_virtual: bool = True, use_cached: bool = True) -> Optional[str]:
        """
        Основной метод поиска порта станции.

        Пример:
        >>> finder = PortFinder()
        >>> port = finder.find_station_port(vid=0x2341, pid=0x0043)  # Поиск Arduino
        >>> print(f"Найден порт: {port}")
        >>> # Пример с предпочтениями
        >>> preferred_port = finder.find_station_port(preferred_devices=["Arduino"])
        >>> preferred_port is None or isinstance(preferred_port, str)  # Проверка типа
        True
        """
        self.logger.info("Запуск процедуры поиска порта")

        if use_cached and (cached_port := self._get_cached_port()):
            self.logger.info("Используется сохраненный порт: %s", cached_port)
            return cached_port

        self.logger.debug("Сканирование доступных последовательных портов")
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            self.logger.warning("Последовательные порты не найдены")
            return None

        self.logger.debug("Найдено %d последовательных портов", len(ports))
        return (self._find_by_vid_pid(vid, pid, ports) or
                self._find_by_preferred(preferred_devices, ports, skip_virtual) or
                self._find_by_patterns(ports, skip_virtual))

    def _get_cached_port(self) -> Optional[str]:
        """
        Проверяет сохраненный порт в конфигурации.

        Пример:
        >>> finder = PortFinder()
        >>> # Сохраняем тестовый порт
        >>> finder._save_port_info(type('obj', (), {'device': 'COM3', 'vid': 1234, 'pid': 5678}))
        >>> # Получаем сохраненный порт
        >>> port = finder._get_cached_port()
        """
        self.logger.debug("Проверка сохраненного порта")
        if cached := self.config.load_port():
            self.logger.debug("Найдена информация о сохраненном порте: %s", cached)
            if verify_port(cached.get('device')):
                self.logger.info("Сохраненный порт подтвержден: %s", cached['device'])
                return cached['device']
            self.logger.debug("Сохраненный порт недоступен")
        return None

    def _find_by_vid_pid(self, vid: Optional[int], pid: Optional[int],
                         ports: List[Any]) -> Optional[str]:
        """
        Поиск порта по точному совпадению VID/PID.

        Пример:
        >>> finder = PortFinder()
        >>> test_ports = [type('obj', (), {'device': 'COM3', 'vid': 0x2341, 'pid': 0x0043})]
        >>> found_port = finder._find_by_vid_pid(0x2341, 0x0043, test_ports)
        >>> assert found_port == 'COM3'
        """
        if vid and pid:
            self.logger.debug("Поиск порта по VID/PID: %04X/%04X", vid, pid)
            for port in ports:
                if hasattr(port, 'vid') and hasattr(port, 'pid'):
                    if port.vid == vid and port.pid == pid:
                        self.logger.info("Найден порт по VID/PID: %s", port.device)
                        self._save_port_info(port)
                        return port.device
        return None

    def _find_by_preferred(self, preferred: Optional[List[str]],
                          ports: List[Any], skip_virtual: bool) -> Optional[str]:
        """
        Поиск порта по предпочтительным устройствам.

        Пример:
        >>> finder = PortFinder()
        >>> test_ports = [type('obj', (), {'device': 'COM3', 'vid': 0x2341, 'pid': 0x0043, 'description': 'Arduino Uno'})]
        >>> port = finder._find_by_preferred(["Arduino"], test_ports, True)
        >>> assert port == 'COM3'
        """
        if not preferred:
            return None

        self.logger.debug("Поиск порта по предпочтительным устройствам: %s", preferred)
        for port in ports:
            if skip_virtual and is_virtual_port(port):
                self.logger.debug("Пропуск виртуального порта: %s", port.device)
                continue

            if hasattr(port, 'vid') and hasattr(port, 'pid'):
                if (port.vid, port.pid) in self.KNOWN_DEVICES:
                    device_type = self.KNOWN_DEVICES[(port.vid, port.pid)]
                    if any(p.lower() in device_type.lower() for p in preferred):
                        self.logger.info("Найдено предпочтительное устройство: %s (%s)",
                                       port.device, device_type)
                        self._save_port_info(port)
                        return port.device
        return None

    def _find_by_patterns(self, ports: List[Any], skip_virtual: bool) -> Optional[str]:
        """
        Поиск порта по регулярным выражениям.

        Пример:
        >>> finder = PortFinder()
        >>> test_ports = [type('obj', (), {'device': 'COM3', 'description': 'Arduino Uno'})]
        >>> port = finder._find_by_patterns(test_ports, True)
        >>> assert port == 'COM3'
        """
        self.logger.debug("Поиск порта по шаблонам")
        for port in ports:
            if skip_virtual and is_virtual_port(port):
                self.logger.debug("Пропуск виртуального порта: %s", port.device)
                continue

            port_description = getattr(port, 'description', '') or ''
            if any(p.search(port_description) for p in self.COMMON_PATTERNS):
                self.logger.info("Найден порт, соответствующий шаблонам: %s (%s)",
                               port.device, port_description)
                self._save_port_info(port)
                return port.device
        return None

    def _save_port_info(self, port: Any) -> bool:
        """
        Сохраняет информацию о порте в конфигурацию.

        Пример:
        >>> finder = PortFinder()
        >>> test_port = type('obj', (), {'device': 'COM3', 'vid': 1234, 'pid': 5678})
        >>> result = finder._save_port_info(test_port)
        >>> assert result is True or result is False
        """
        if port_info := get_port_info(port):
            if self.config.save_port(port_info):
                self.logger.debug("Информация о порте успешно сохранена")
                return True
            self.logger.warning("Не удалось сохранить информацию о порте")
        return False

    def clear_cache(self) -> bool:
        """
        Очищает кеш портов в конфигурации.

        Пример:
        >>> finder = PortFinder()
        >>> result = finder.clear_cache()
        >>> assert result is True or result is False
        """
        self.logger.info("Очистка кеша портов...")
        if self.config.clear_config():
            self.logger.info("Кеш портов успешно очищен")
            return True
        self.logger.warning("Не удалось очистить кеш портов")
        return False
