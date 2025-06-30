# System Register API package

from .sysreg import SystemRegisterAPI
from .sysreg_fields import SystemRegister
from .sysreg_bitfields import SystemRegisterBitField

# Create a global instance for convenient access
SysReg = SystemRegisterAPI()

# Export the main classes and the global instance
__all__ = [
    'SystemRegisterAPI',
    'SystemRegister', 
    'SystemRegisterBitField',
    'SysReg'
] 