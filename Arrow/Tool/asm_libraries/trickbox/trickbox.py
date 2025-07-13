from typing import Union, Optional
from Arrow.Tool.register_management.register import Register
from Arrow.Tool.state_management import get_current_state
from Arrow.Tool.asm_libraries.asm_logger import AsmLogger
from Arrow.Utils.configuration_management import Configuration

class Trickbox:
    """
    Trickbox class for reading and writing to trickbox fields.
    
    This class generates assembly code to access trickbox registers at the base address
    """
    
    raise Exception(" Please provide Trickbox base address of your choice")
    TRICKBOX_BASE_ADDRESS = 0x0
    
    def write(self, register: Configuration.TrickboxRegister, value: Optional[int] = None, source_register: Optional[Register] = None):
        """
        Write to a trickbox register.
        
        Args:
            register (TrickboxRegister): The trickbox register enum to write to
            value (Optional[int]): Immediate value to write (mutually exclusive with source_register)
            source_register (Optional[Register]): Register containing the value to write (mutually exclusive with value)
            
        Raises:
            ValueError: If neither value nor source_register is provided, or if both are provided
            TypeError: If register is not a TrickboxRegister enum
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        if (value is None and source_register is None) or (value is not None and source_register is not None):
            raise ValueError("Must provide exactly one of 'value' or 'source_register'")
        
        if not isinstance(register, Configuration.TrickboxRegister):
            raise TypeError(f"Register must be a TrickboxRegister enum, got {type(register)}")
        
        # Get the offset directly from the enum value
        offset = register.value
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        value_reg = register_manager.get_and_reserve()

        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {register.name} address ({target_address:#x})")
                
        if value is not None:
            # Writing immediate value
            if value == 0:
                # Optimize for zero - use wzr/xzr register
                AsmLogger.asm(f"str wzr, [{addr_reg}]", comment=f"Write value 0 to trickbox {register.name}")
            else:
                AsmLogger.asm(f"mov {value_reg.as_size(32)}, #{value:#x}", comment=f"Load immediate value {value:#x}")
                AsmLogger.asm(f"str {value_reg.as_size(32)}, [{addr_reg}]", comment=f"Write value {value:#x} to trickbox {register.name}")
        else:
            # Writing from register
            AsmLogger.asm(f"str {source_register.as_size(32)}, [{addr_reg}]", comment=f"Write register {source_register} to trickbox {register.name}")
        
        # Release the address register
        register_manager.free(addr_reg)
        register_manager.free(value_reg)
    
    def read(self, register: Configuration.TrickboxRegister, target_register: Register):
        """
        Read from a trickbox register into a target register.
        
        Args:
            register (TrickboxRegister): The trickbox register enum to read from
            target_register (Register): The register to store the read value
            
        Raises:
            TypeError: If register is not a TrickboxRegister enum
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        if not isinstance(register, Configuration.TrickboxRegister):
            raise TypeError(f"Register must be a TrickboxRegister enum, got {type(register)}")
        
        # Get the offset directly from the enum value
        offset = register.value
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        

        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        
        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {register.name} address ({target_address:#x})")
        
        # Read from the trickbox register
        AsmLogger.asm(f"ldr {target_register.as_size(32)}, [{addr_reg}]", comment=f"Read trickbox {register.name} into {target_register}")
        
        # Release the address register
        register_manager.free(addr_reg)
    
