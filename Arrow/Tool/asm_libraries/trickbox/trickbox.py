from typing import Union, Optional
from Arrow.Tool.register_management.register import Register
from Arrow.Tool.state_management import get_current_state
from Arrow.Tool.asm_libraries.asm_logger import AsmLogger
from Arrow.Utils.configuration_management import Configuration

class Trickbox:
    """
    Trickbox class for reading and writing to trickbox fields.
    
    This class generates assembly code to access trickbox registers at the base address
    0x13000000 plus the field-specific offsets.
    """
    
    TRICKBOX_BASE_ADDRESS = 0x13000000
    
    def write(self, field: Configuration.TrickboxField, value: Optional[int] = None, register: Optional[Register] = None):
        """
        Write to a trickbox field.
        
        Args:
            field (TrickboxField): The trickbox field enum to write to
            value (Optional[int]): Immediate value to write (mutually exclusive with register)
            register (Optional[Register]): Register containing the value to write (mutually exclusive with value)
            
        Raises:
            ValueError: If neither value nor register is provided, or if both are provided
            TypeError: If field is not a TrickboxField enum
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        if (value is None and register is None) or (value is not None and register is not None):
            raise ValueError("Must provide exactly one of 'value' or 'register'")
        
        if not isinstance(field, Configuration.TrickboxField):
            raise TypeError(f"Field must be a TrickboxField enum, got {type(field)}")
        
        # Get the offset directly from the enum value
        offset = field.value
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        value_reg = register_manager.get_and_reserve()

        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {field.name} address ({target_address:#x})")
                
        if value is not None:
            # Writing immediate value
            if value == 0:
                # Optimize for zero - use wzr/xzr register
                AsmLogger.asm(f"str wzr, [{addr_reg}]", comment=f"Write value 0 to trickbox {field.name}")
            else:
                AsmLogger.asm(f"mov {value_reg.as_size(32)}, #{value:#x}", comment=f"Load immediate value {value:#x}")
                AsmLogger.asm(f"str {value_reg.as_size(32)}, [{addr_reg}]", comment=f"Write value {value:#x} to trickbox {field.name}")
        else:
            # Writing from register
            AsmLogger.asm(f"str {register.as_size(32)}, [{addr_reg}]", comment=f"Write register {register} to trickbox {field.name}")
        
        # Release the address register
        register_manager.free(addr_reg)
        register_manager.free(value_reg)
    
    def read(self, field: Configuration.TrickboxField, register: Register):
        """
        Read from a trickbox field into a register.
        
        Args:
            field (TrickboxField): The trickbox field enum to read from
            register (Register): The register to store the read value
            
        Raises:
            TypeError: If field is not a TrickboxField enum
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        if not isinstance(field, Configuration.TrickboxField):
            raise TypeError(f"Field must be a TrickboxField enum, got {type(field)}")
        
        # Get the offset directly from the enum value
        offset = field.value
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        

        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        
        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {field.name} address ({target_address:#x})")
        
        # Read from the trickbox field
        AsmLogger.asm(f"ldr {register.as_size(32)}, [{addr_reg}]", comment=f"Read trickbox {field.name} into {register}")
        
        # Release the address register
        register_manager.free(addr_reg)
    
