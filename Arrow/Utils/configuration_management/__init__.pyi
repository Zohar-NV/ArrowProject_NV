from typing import Any, Dict, List, Tuple
from enum import Enum
from Arrow.Utils.configuration_management.knob_manager import Knob

class Architecture:
    x86: bool
    riscv: bool
    arm: bool
    arch_str: bool

class Memory_types(Enum):
    BSP_BOOT_CODE: str
    BOOT_CODE: str
    CODE: str
    DATA_SHARED: str
    DATA_PRESERVE: str
    STACK: str

class Execution_context(Enum):
    EL3: str
    EL2_NS: str
    EL2_S: str
    EL1_NS: str
    EL1_S: str
    EL1_Realm: str
    EL0_NS: str
    EL0_S: str
    EL0_Realm: str

class Page_types(Enum):
    TYPE_CODE: str
    TYPE_DATA: str
    TYPE_DEVICE: str
    TYPE_SYSTEM: str

class Page_sizes(Enum):
    SIZE_4K: int
    SIZE_2M: int
    SIZE_1G: int

class ByteSize(Enum):
    SIZE_1K: int
    SIZE_2K: int
    SIZE_4K: int
    SIZE_8K: int
    SIZE_1M: int
    SIZE_2M: int
    SIZE_4M: int
    SIZE_1G: int
    SIZE_2G: int
    SIZE_4G: int
    
    def in_bytes(self) -> int: ...

class Tag(Enum):
    SLOW: str
    FAST: str
    RECIPE: str
    FEATURE_A: str
    FEATURE_B: str
    FEATURE_C: str
    MEMORY: str
    STACK: str
    REST: str
    DISPATCH: str
    CACHE: str
    BRANCH: str
    POWER: str
    HRO: str

class Priority(Enum):
    HIGH: str
    MEDIUM: str
    LOW: str
    RARE: str

class Frequency(Enum):
    RARE: Tuple[float, float]
    LOW: Tuple[float, float]
    MED: Tuple[float, float]
    HIGH: Tuple[float, float]

# Placeholder for TrickboxRegister and SystemRegister
class TrickboxRegister:
    ...

class SystemRegister:
    ...

class SystemRegisterBitField:
    ...

PRIORITY_WEIGHTS: Dict[Priority, int]

class Configuration:
    Architecture: type[Architecture]
    Memory_types: type[Memory_types]
    Page_types: type[Page_types]
    Page_sizes: type[Page_sizes]
    ByteSize: type[ByteSize]
    Tag: type[Tag]
    Priority: type[Priority]
    PRIORITY_WEIGHTS: Dict[Priority, int]
    Frequency: type[Frequency]
    Execution_context: type[Execution_context]
    TrickboxRegister: type[TrickboxRegister]
    SystemRegister: type[SystemRegister]
    SystemRegisterBitField: type[SystemRegisterBitField]
    
    class Knobs:
        class Config:
            core_count: Knob
            thread_count: Knob
            processor_mode: Knob
            skip_boot: Knob
            exception_level: Knob
            privilege_level: Knob
        
        class Template:
            scenario_count: Knob
            scenario_query: Knob
        
        class Memory:
            code_segment_count: Knob
            data_segment_count: Knob
            shared_memory_reuse: Knob 