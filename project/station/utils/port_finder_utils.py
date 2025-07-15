import datetime
import serial.tools.list_ports

from typing import Dict, Union, Any

from project.station.logging.station_logger import logger


def verify_port(port_name: str) -> bool:
    """
    Проверяет доступность последовательного порта и его соответствие критериям.

    Args:
        port_name: Имя порта для проверки (например, 'COM3').

    Returns:
        bool: True если порт существует и доступен, False в противном случае.
    """
    try:
        logger.debug("Проверка доступности порта: %s", port_name)
        ports = serial.tools.list_ports.comports()

        if not ports:
            logger.warning("Не найдено ни одного последовательного порта")
            return False

        port_exists = any(p.device == port_name for p in ports)

        if port_exists:
            logger.info("Порт %s доступен и соответствует критериям", port_name)
        else:
            logger.warning("Порт %s не найден среди доступных портов", port_name)

        return port_exists

    except Exception as e:
        logger.error("Ошибка при проверке порта %s: %s", port_name, str(e))
        return False


def get_port_info(port: Any) -> Dict[str, Union[str, int, None]]:
    """
    Собирает подробную информацию о последовательном порте.

    Args:
        port: Объект порта из serial.tools.list_ports.comports().

    Returns:
        Dict: Словарь с информацией о порте.
    """
    try:
        logger.debug("Получение информации о порте: %s", port.device if port else 'None')

        if not port:
            logger.warning("Передан пустой объект порта")
            return {}

        port_info = {
            'device': port.device,
            'description': port.description,
            'hwid': port.hwid,
            'vid': port.vid if hasattr(port, 'vid') else None,
            'pid': port.pid if hasattr(port, 'pid') else None,
            'serial_number': port.serial_number if hasattr(port, 'serial_number') else None,
            'location': port.location if hasattr(port, 'location') else None,
            'manufacturer': port.manufacturer if hasattr(port, 'manufacturer') else None,
            'product': port.product if hasattr(port, 'product') else None,
            'interface': port.interface if hasattr(port, 'interface') else None,
            'found_at': datetime.datetime.now().isoformat(),
        }

        logger.debug("Собранная информация о порте: %s", port_info)
        return port_info

    except Exception as e:
        logger.error("Ошибка при получении информации о порте: %s", str(e))
        return {}


def is_virtual_port(port: Any) -> bool:
    """
    Определяет, является ли порт виртуальным, на основе его описания.

    Args:
        port: Объект порта из serial.tools.list_ports.comports().

    Returns:
        bool: True если порт считается виртуальным.
    """
    try:
        if not port:
            logger.debug("Передан пустой объект порта")
            return False

        if not port.description:
            logger.debug("Порт %s не имеет описания, считаем физическим", port.device)
            return False

        is_virtual = any(word in port.description.lower()
                        for word in ['bluetooth', 'virtual', 'com0com', 'tcp', 'network'])

        if is_virtual:
            logger.info("Порт %s идентифицирован как виртуальный", port.device)
        else:
            logger.debug("Порт %s считается физическим", port.device)

        return is_virtual

    except Exception as e:
        logger.error("Ошибка при проверке виртуального порта: %s", str(e))
        return False
