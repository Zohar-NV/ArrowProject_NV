from enum import Enum
from .sysreg_fields import SystemRegister

class SystemRegisterBitField(Enum):
    """
    Enumeration of System Register Bit Fields
    
    Each enum value contains: (register, field_name, bit_range, description)
    bit_range can be a single bit (int) or a tuple (start_bit, end_bit) for multi-bit fields
    """
    
    # === CPACR_EL1 Bit Fields ===
    CPACR_EL1_FPEN = (SystemRegister.CPACR_EL1, "FPEN", (21, 20), "Floating-point Enable")
    CPACR_EL1_ZEN = (SystemRegister.CPACR_EL1, "ZEN", (17, 16), "SVE Enable")
    CPACR_EL1_SMEN = (SystemRegister.CPACR_EL1, "SMEN", (25, 24), "SME Enable")
    CPACR_EL1_E0POE = (SystemRegister.CPACR_EL1, "E0POE", 28, "EL0 Access to POE registers")
    
    raise Exception(" Please provide additional sysreg bitfields of your choice")


    def __str__(self):
        return f"{self.value[0].name}.{self.value[1]}"
        
    @property
    def register(self):
        """Get the system register associated with this bit field"""
        return self.value[0]
        
    @property 
    def field_name(self):
        """Get the field name"""
        return self.value[1]
        
    @property
    def bit_range(self):
        """Get the bit range (single bit or tuple)"""
        return self.value[2]
        
    @property
    def description(self):
        """Get the field description"""
        return self.value[3]
        
    @property
    def is_single_bit(self):
        """Check if this is a single bit field"""
        return isinstance(self.bit_range, int)
        
    @property
    def mask(self):
        """Get the bit mask for this field"""
        if self.is_single_bit:
            return 1 << self.bit_range
        else:
            start_bit, end_bit = self.bit_range
            return ((1 << (end_bit - start_bit + 1)) - 1) << start_bit
            
    @property 
    def shift(self):
        """Get the bit shift for this field (position of least significant bit)"""
        if self.is_single_bit:
            return self.bit_range
        else:
            return self.bit_range[1]  # start bit is the lower bit number (LSB position)
            
    @property
    def width(self):
        """Get the width of this bit field"""
        if self.is_single_bit:
            return 1
        else:
            start_bit, end_bit = self.bit_range
            return end_bit - start_bit + 1 