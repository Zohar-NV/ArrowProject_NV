from typing import Optional, List
from Arrow.Tool.memory_management.memory_operand import Memory
from Arrow.Tool.memory_management.memory_block import MemoryBlock
from Arrow.Tool.memory_management.memlayout.segment import MemorySegment
from Arrow.Utils.configuration_management import Configuration

class MemoryManager_API:
    @staticmethod
    def Memory(
        name: Optional[str] = None,
        address: Optional[int] = None,
        byte_size: Optional[int] = 8,
        memory_type: Optional[str] = "WB",
        shared: bool = False,
        init_value: Optional[int] = None,
        memory_block: Optional[MemoryBlock] = None,
        memory_block_offset: Optional[int] = None,
        cross_core: bool = False,
        alignment: Optional[int] = None,
    ) -> Memory: ...
    
    @staticmethod
    def MemoryBlock(
        byte_size: int,
        name: Optional[str] = None,
        address: Optional[int] = None,
        memory_type: Optional[str] = "WB",
        shared: bool = False,
        alignment: Optional[int] = None,
        cross_core: bool = False,
        init_value: Optional[int] = None,
        init_value_byte_representation: Optional[List[int]] = None,
        _use_name_as_unique_label: bool = False,
    ) -> MemoryBlock: ...
    
    @staticmethod
    def MemorySegment(
        name: str,
        byte_size: int,
        memory_type: Configuration.Memory_types,
    ) -> MemorySegment: ... 