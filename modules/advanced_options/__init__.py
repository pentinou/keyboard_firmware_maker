"""Onglet "Options avancées" — expose les Kconfig/define ZMK et QMK utiles
au-delà du paramétrage standard de KFM (NKRO, BLE passkey, tap-dance,
sticky keys, RGB start, etc.).

Le widget est conçu pour rester lisible : QScrollArea + sections par thème,
options ZMK-only / QMK-only grisées et tooltips explicatifs.
"""

from modules.advanced_options.widget import AdvancedOptionsWidget

__all__ = ["AdvancedOptionsWidget"]
