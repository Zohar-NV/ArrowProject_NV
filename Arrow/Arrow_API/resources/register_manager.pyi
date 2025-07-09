from typing import Optional, List
from Arrow.Tool.register_management.register import Register

class RegisterManager_API:
    @staticmethod
    def get_free_registers(reg_type: Optional[str] = None) -> List[Register]: ...
    
    @staticmethod
    def get_used_registers(reg_type: Optional[str] = None) -> List[Register]: ...
    
    @staticmethod
    def get(reg_name: Optional[str] = None, reg_type: Optional[str] = None) -> Register: ...
    
    @staticmethod
    def get_and_reserve(reg_type: str = "gpr") -> Register: ...
    
    @staticmethod
    def reserve(register: Register) -> None: ...
    
    @staticmethod
    def free(register: Register) -> None: ...
    
    @staticmethod
    def print_reg_status() -> None: ... 