"""
ATM Data Generator
==================

A configurable synthetic data generator for ATM telemetry, failures, and maintenance events.
Designed for training predictive maintenance models.

Author: ATM Breakdown Model Team
Version: 1.0.0
"""

__version__ = "1.0.0"

from .core.generator import ATMDataGenerator
from .core.config import GeneratorConfig

__all__ = ['ATMDataGenerator', 'GeneratorConfig']
