from typing import Union, Optional
from Arrow.Tool.asm_libraries.trickbox.trickbox_fields import TrickboxField
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
    
    def write(self, field: str, value: Optional[int] = None, register: Optional[Register] = None):
        """
        Write to a trickbox field.
        
        Args:
            field (str): The name of the trickbox field to write to
            value (Optional[int]): Immediate value to write (mutually exclusive with register)
            register (Optional[Register]): Register containing the value to write (mutually exclusive with value)
            
        Raises:
            ValueError: If neither value nor register is provided, or if both are provided
            ValueError: If the field name is invalid
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        if (value is None and register is None) or (value is not None and register is not None):
            raise ValueError("Must provide exactly one of 'value' or 'register'")
        
        # Get the offset for the field
        try:
            offset = TrickboxField.get_offset(field)
        except ValueError as e:
            raise ValueError(f"Invalid trickbox field: {e}")
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        value_reg = register_manager.get_and_reserve()

        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {field} address ({target_address:#x})")
                
        if value is not None:
            # Writing immediate value
            if value == 0:
                # Optimize for zero - use wzr/xzr register
                AsmLogger.asm(f"str wzr, [{addr_reg}]", comment=f"Write value 0 to trickbox {field}")
            else:
                AsmLogger.asm(f"mov {value_reg.as_size(32)}, #{value:#x}", comment=f"Load immediate value {value:#x}")
                AsmLogger.asm(f"str {value_reg.as_size(32)}, [{addr_reg}]", comment=f"Write value {value:#x} to trickbox {field}")
        else:
            # Writing from register
            AsmLogger.asm(f"str {register.as_size(32)}, [{addr_reg}]", comment=f"Write register {register} to trickbox {field}")
        
        # Release the address register
        register_manager.free(addr_reg)
        register_manager.free(value_reg)
    
    def read(self, field: str, register: Register):
        """
        Read from a trickbox field into a register.
        
        Args:
            field (str): The name of the trickbox field to read from
            register (Register): The register to store the read value
            
        Raises:
            ValueError: If the field name is invalid
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("Trickbox functionality is only available for ARM architecture")
        
        # Get the offset for the field
        try:
            offset = TrickboxField.get_offset(field)
        except ValueError as e:
            raise ValueError(f"Invalid trickbox field: {e}")
        
        # Calculate the target address
        target_address = self.TRICKBOX_BASE_ADDRESS + offset
        

        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        addr_reg = register_manager.get_and_reserve()
        
        # Load the target address
        AsmLogger.asm(f"ldr {addr_reg}, ={target_address:#x}", comment=f"Load trickbox {field} address ({target_address:#x})")
        
        # Read from the trickbox field
        AsmLogger.asm(f"ldr {register.as_size(32)}, [{addr_reg}]", comment=f"Read trickbox {field} into {register}")
        
        # Release the address register
        register_manager.free(addr_reg)
    
    # def get_field_address(self, field: str) -> int:
    #     """
    #     Get the absolute address of a trickbox field.
        
    #     Args:
    #         field (str): The name of the trickbox field
            
    #     Returns:
    #         int: The absolute address of the field
            
    #     Raises:
    #         ValueError: If the field name is invalid
    #     """
    #     try:
    #         offset = TrickboxField.get_offset(field)
    #         return self.TRICKBOX_BASE_ADDRESS + offset
    #     except ValueError as e:
    #         raise ValueError(f"Invalid trickbox field: {e}")
    
    # def list_fields(self):
    #     """
    #     Get a list of all available trickbox fields.
        
    #     Returns:
    #         list: List of field names
    #     """
    #     return TrickboxField.list_fields()
    
    # def __str__(self):
    #     return f"Trickbox(base_address={self.TRICKBOX_BASE_ADDRESS:#x})"
    
    # def __repr__(self):
    #     return self.__str__()
