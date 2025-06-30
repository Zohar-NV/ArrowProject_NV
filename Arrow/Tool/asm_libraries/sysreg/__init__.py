# System Register API package

# Only import the lightweight enums to avoid circular dependencies
from .sysreg_fields import SystemRegister, SystemRegisterBitField

# Heavy imports moved to conditional/lazy loading to avoid circular dependency
# from .sysreg import SysReg

# Global variable to hold the lazy-loaded instance
_sysreg_instance = None

def get_sysreg_instance():
    """Lazy import and instantiation of SysReg to avoid circular dependencies"""
    global _sysreg_instance
    if _sysreg_instance is None:
        from .sysreg import SysReg
        _sysreg_instance = SysReg()
    return _sysreg_instance

# Create a proxy class for backwards compatibility
class SysRegProxy:
    def __getattr__(self, name):
        return getattr(get_sysreg_instance(), name)

# Create the global instance
SysReg = SysRegProxy()

# Export the main classes and the global instance
__all__ = [
    'SystemRegister', 
    'SystemRegisterBitField',
    'SysReg'
] 