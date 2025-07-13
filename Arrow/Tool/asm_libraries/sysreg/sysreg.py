from typing import Union, Optional, List
from Arrow.Tool.register_management.register import Register
from Arrow.Tool.state_management import get_current_state
from Arrow.Tool.asm_libraries.asm_logger import AsmLogger
from Arrow.Utils.configuration_management import Configuration
from .sysreg_fields import SystemRegister
from .sysreg_bitfields import SystemRegisterBitField

class SysReg:
    """
    System Register API class for reading, writing, and manipulating ARM AArch64 system registers.
    
    This class generates assembly code to access system registers using MRS/MSR instructions.
    It provides functionality similar to the trickbox API but for system registers.
    """
    
    def read(self, register: Union[SystemRegister, str], target_register: Register) -> None:
        """
        Read from a system register into a general-purpose register.
        
        Args:
            register: System register to read from (enum or string)
            target_register: Register to store the read value
            
        Raises:
            ValueError: If register is invalid
            RuntimeError: If not ARM architecture
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("System register functionality is only available for ARM architecture")
        
        # Handle both enum and string inputs
        if isinstance(register, SystemRegister):
            register_name = register.value
            enum_name = register.name
        elif isinstance(register, str):
            register_name = register.lower()
            enum_name = register.upper()
        else:
            raise ValueError(f"register must be SystemRegister enum or string, got {type(register)}")
        
        # Generate MRS instruction
        AsmLogger.asm(f"mrs {target_register}, {register_name}", 
                     comment=f"Read {enum_name} into {target_register}")
    
    def write(self, register: Union[SystemRegister, str], 
              value: Optional[int] = None, 
              source_register: Optional[Register] = None) -> None:
        """
        Write to a system register.
        
        Args:
            register: System register to write to (enum or string)
            value: Immediate value to write (mutually exclusive with source_register)
            source_register: Register containing the value to write (mutually exclusive with value)
            
        Raises:
            ValueError: If neither value nor source_register is provided, or if both are provided
            RuntimeError: If not ARM architecture
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("System register functionality is only available for ARM architecture")
        
        if (value is None and source_register is None) or (value is not None and source_register is not None):
            raise ValueError("Must provide exactly one of 'value' or 'source_register'")
        
        # Handle both enum and string inputs
        if isinstance(register, SystemRegister):
            register_name = register.value
            enum_name = register.name
        elif isinstance(register, str):
            register_name = register.lower()
            enum_name = register.upper()
        else:
            raise ValueError(f"register must be SystemRegister enum or string, got {type(register)}")
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        if value is not None:
            # Writing immediate value - need to load it into a register first
            if value == 0:
                # Optimize for zero - use xzr register directly
                AsmLogger.asm(f"msr {register_name}, xzr", 
                             comment=f"Write value 0 to {enum_name}")
            else:
                # Load immediate value into temporary register
                temp_reg = register_manager.get_and_reserve()
                AsmLogger.asm(f"mov {temp_reg}, #{value:#x}", 
                             comment=f"Load immediate value {value:#x}")
                AsmLogger.asm(f"msr {register_name}, {temp_reg}", 
                             comment=f"Write value {value:#x} to {enum_name}")
                register_manager.free(temp_reg)
        else:
            # Writing from register
            AsmLogger.asm(f"msr {register_name}, {source_register}", 
                         comment=f"Write register {source_register} to {enum_name}")
    
    def read_modify_write(self, register: Union[SystemRegister, str],
                         and_mask: Optional[int] = None,
                         or_mask: Optional[int] = None,
                         target_register: Optional[Register] = None) -> Register:
        """
        Perform read-modify-write operation on a system register.
        
        Operation: new_value = (old_value & and_mask) | or_mask
        
        Args:
            register: System register to modify (enum or string)
            and_mask: Mask for AND operation (bits to preserve)
            or_mask: Mask for OR operation (bits to set)
            target_register: Optional register to store final value (if None, uses temporary)
            
        Returns:
            Register containing the final value
            
        Raises:
            ValueError: If neither and_mask nor or_mask is provided
            RuntimeError: If not ARM architecture
        """
        if not Configuration.Architecture.arm:
            raise RuntimeError("System register functionality is only available for ARM architecture")
        
        if and_mask is None and or_mask is None:
            raise ValueError("Must provide at least one of 'and_mask' or 'or_mask'")
        
        # Handle both enum and string inputs
        if isinstance(register, SystemRegister):
            register_name = register.value
            enum_name = register.name
        elif isinstance(register, str):
            register_name = register.lower()
            enum_name = register.upper()
        else:
            raise ValueError(f"register must be SystemRegister enum or string, got {type(register)}")
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        # Determine the register to use for the operation
        if target_register is None:
            work_reg = register_manager.get_and_reserve()
            should_free = True
        else:
            work_reg = target_register
            should_free = False
        
        # Read current value
        AsmLogger.asm(f"mrs {work_reg}, {register_name}", 
                     comment=f"Read current {enum_name} value")
        
        # Apply AND mask if provided
        if and_mask is not None:
            if and_mask == 0:
                # AND with 0 - clear all bits
                AsmLogger.asm(f"mov {work_reg}, #0", 
                             comment=f"Clear all bits (AND with 0x{and_mask:x})")
            elif and_mask != 0xFFFFFFFFFFFFFFFF:  # Skip if AND mask is all 1s
                temp_reg = register_manager.get_and_reserve()
                AsmLogger.asm(f"mov {temp_reg}, #{and_mask:#x}", 
                             comment=f"Load AND mask 0x{and_mask:x}")
                AsmLogger.asm(f"and {work_reg}, {work_reg}, {temp_reg}", 
                             comment=f"Apply AND mask to {enum_name}")
                register_manager.free(temp_reg)
        
        # Apply OR mask if provided
        if or_mask is not None and or_mask != 0:
            temp_reg = register_manager.get_and_reserve()
            AsmLogger.asm(f"mov {temp_reg}, #{or_mask:#x}", 
                         comment=f"Load OR mask 0x{or_mask:x}")
            AsmLogger.asm(f"orr {work_reg}, {work_reg}, {temp_reg}", 
                         comment=f"Apply OR mask to {enum_name}")
            register_manager.free(temp_reg)
        
        # Write back the modified value
        AsmLogger.asm(f"msr {register_name}, {work_reg}", 
                     comment=f"Write modified value back to {enum_name}")
        
        # Return the register containing the final value
        if should_free:
            # If we allocated the register, the caller might want to use it
            # Don't free it yet, let the caller decide
            pass
        
        return work_reg
    
    def set_bits(self, register: Union[SystemRegister, str], 
                 bit_mask: int,
                 target_register: Optional[Register] = None) -> Register:
        """
        Set specific bits in a system register (equivalent to OR operation).
        
        Args:
            register: System register to modify
            bit_mask: Mask of bits to set (1 = set, 0 = leave unchanged)
            target_register: Optional register to store final value
            
        Returns:
            Register containing the final value
        """
        return self.read_modify_write(register, or_mask=bit_mask, target_register=target_register)
    
    def clear_bits(self, register: Union[SystemRegister, str],
                   bit_mask: int,
                   target_register: Optional[Register] = None) -> Register:
        """
        Clear specific bits in a system register (equivalent to AND with inverted mask).
        
        Args:
            register: System register to modify
            bit_mask: Mask of bits to clear (1 = clear, 0 = leave unchanged)
            target_register: Optional register to store final value
            
        Returns:
            Register containing the final value
        """
        # Invert the mask for AND operation
        and_mask = ~bit_mask & 0xFFFFFFFFFFFFFFFF
        return self.read_modify_write(register, and_mask=and_mask, target_register=target_register)
    
    def toggle_bits(self, register: Union[SystemRegister, str],
                    bit_mask: int,
                    target_register: Optional[Register] = None) -> Register:
        """
        Toggle specific bits in a system register (equivalent to XOR operation).
        
        Args:
            register: System register to modify
            bit_mask: Mask of bits to toggle (1 = toggle, 0 = leave unchanged)
            target_register: Optional register to store final value
            
        Returns:
            Register containing the final value
        """
        # Handle both enum and string inputs
        if isinstance(register, SystemRegister):
            register_name = register.value
            enum_name = register.name
        elif isinstance(register, str):
            register_name = register.lower()
            enum_name = register.upper()
        else:
            raise ValueError(f"register must be SystemRegister enum or string, got {type(register)}")
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        # Determine the register to use
        if target_register is None:
            work_reg = register_manager.get_and_reserve()
        else:
            work_reg = target_register
        
        # Read current value
        AsmLogger.asm(f"mrs {work_reg}, {register_name}", 
                     comment=f"Read current {enum_name} value")
        
        # Apply XOR mask
        if bit_mask != 0:
            temp_reg = register_manager.get_and_reserve()
            AsmLogger.asm(f"mov {temp_reg}, #{bit_mask:#x}", 
                         comment=f"Load toggle mask 0x{bit_mask:x}")
            AsmLogger.asm(f"eor {work_reg}, {work_reg}, {temp_reg}", 
                         comment=f"Toggle bits in {enum_name}")
            register_manager.free(temp_reg)
        
        # Write back the modified value
        AsmLogger.asm(f"msr {register_name}, {work_reg}", 
                     comment=f"Write toggled value back to {enum_name}")
        
        return work_reg 

    # === Bit Field Operations ===
    
    def read_field(self, bit_field: SystemRegisterBitField, target_register: Register) -> None:
        """
        Read a specific bit field from a system register.
        
        Args:
            bit_field: Bit field to read
            target_register: Register to store the extracted field value
        """
        # Read the full register
        self.read(bit_field.register, target_register)
        
        # Extract the bit field
        if bit_field.is_single_bit:
            # Single bit - shift right and mask
            if bit_field.shift > 0:
                AsmLogger.asm(f"lsr {target_register}, {target_register}, #{bit_field.shift}", 
                             comment=f"Shift right to extract {bit_field} bit")
            AsmLogger.asm(f"and {target_register}, {target_register}, #1", 
                         comment=f"Mask to get {bit_field} bit value")
        else:
            # Multi-bit field - shift right and mask
            current_state = get_current_state()
            register_manager = current_state.register_manager
            temp_reg = register_manager.get_and_reserve()
            
            if bit_field.shift > 0:
                AsmLogger.asm(f"lsr {target_register}, {target_register}, #{bit_field.shift}", 
                             comment=f"Shift right to extract {bit_field} field")
            
            field_mask = (1 << bit_field.width) - 1
            AsmLogger.asm(f"mov {temp_reg}, #{field_mask:#x}", 
                         comment=f"Load field mask for {bit_field}")
            AsmLogger.asm(f"and {target_register}, {target_register}, {temp_reg}", 
                         comment=f"Mask to get {bit_field} field value")
            
            register_manager.free(temp_reg)
    
    def write_field(self, bit_field: SystemRegisterBitField, 
                   value: Optional[int] = None,
                   source_register: Optional[Register] = None) -> None:
        """
        Write a specific bit field in a system register using read-modify-write.
        
        Args:
            bit_field: Bit field to write
            value: Immediate value to write (mutually exclusive with source_register)
            source_register: Register containing the value to write (mutually exclusive with value)
        """
        if (value is None and source_register is None) or (value is not None and source_register is not None):
            raise ValueError("Must provide exactly one of 'value' or 'source_register'")
        
        current_state = get_current_state()
        register_manager = current_state.register_manager
        
        work_reg = register_manager.get_and_reserve()
        
        # Read current register value
        self.read(bit_field.register, work_reg)
        
        # Clear the target field bits
        inverted_mask = ~bit_field.mask & 0xFFFFFFFFFFFFFFFF
        if inverted_mask != 0xFFFFFFFFFFFFFFFF:  # Only if not all bits are 1
            temp_reg = register_manager.get_and_reserve()
            AsmLogger.asm(f"mov {temp_reg}, #{inverted_mask:#x}", 
                         comment=f"Load inverted mask to clear {bit_field} field")
            AsmLogger.asm(f"and {work_reg}, {work_reg}, {temp_reg}", 
                         comment=f"Clear {bit_field} field bits")
            register_manager.free(temp_reg)
        
        # Prepare the new field value
        if value is not None:
            # Immediate value
            if value != 0:
                # Validate value fits in the field
                max_value = (1 << bit_field.width) - 1
                if value > max_value:
                    raise ValueError(f"Value {value} too large for {bit_field.width}-bit field {bit_field}")
                
                shifted_value = value << bit_field.shift
                temp_reg = register_manager.get_and_reserve()
                AsmLogger.asm(f"mov {temp_reg}, #{shifted_value:#x}", 
                             comment=f"Load new value for {bit_field} field")
                AsmLogger.asm(f"orr {work_reg}, {work_reg}, {temp_reg}", 
                             comment=f"Set {bit_field} field to {value}")
                register_manager.free(temp_reg)
        else:
            # Register value
            temp_reg = register_manager.get_and_reserve()
            
            # Validate and mask the source value
            max_value = (1 << bit_field.width) - 1
            AsmLogger.asm(f"mov {temp_reg}, #{max_value:#x}", 
                         comment=f"Load field mask for {bit_field}")
            AsmLogger.asm(f"and {temp_reg}, {source_register}, {temp_reg}", 
                         comment=f"Mask source register to {bit_field} field width")
            
            # Shift to correct position
            if bit_field.shift > 0:
                AsmLogger.asm(f"lsl {temp_reg}, {temp_reg}, #{bit_field.shift}", 
                             comment=f"Shift {bit_field} field value to correct position")
            
            # OR into the work register
            AsmLogger.asm(f"orr {work_reg}, {work_reg}, {temp_reg}", 
                         comment=f"Set {bit_field} field from register")
            
            register_manager.free(temp_reg)
        
        # Write back the modified register
        self.write(bit_field.register, source_register=work_reg)
        
        register_manager.free(work_reg)
    
    def set_field_bits(self, bit_field: SystemRegisterBitField, bit_mask: int) -> None:
        """
        Set specific bits within a bit field (OR operation within the field).
        
        Args:
            bit_field: Bit field to modify
            bit_mask: Mask of bits to set within the field (relative to field, not register)
        """
        # Validate bit mask fits within the field
        max_mask = (1 << bit_field.width) - 1
        if bit_mask > max_mask:
            raise ValueError(f"Bit mask {bit_mask:#x} too large for {bit_field.width}-bit field {bit_field}")
        
        # Shift the mask to the correct position in the register
        register_mask = bit_mask << bit_field.shift
        
        # Use the existing set_bits method
        self.set_bits(bit_field.register, register_mask)
    
    def clear_field_bits(self, bit_field: SystemRegisterBitField, bit_mask: int) -> None:
        """
        Clear specific bits within a bit field (AND with inverted mask within the field).
        
        Args:
            bit_field: Bit field to modify
            bit_mask: Mask of bits to clear within the field (relative to field, not register)
        """
        # Validate bit mask fits within the field
        max_mask = (1 << bit_field.width) - 1
        if bit_mask > max_mask:
            raise ValueError(f"Bit mask {bit_mask:#x} too large for {bit_field.width}-bit field {bit_field}")
        
        # Shift the mask to the correct position in the register
        register_mask = bit_mask << bit_field.shift
        
        # Use the existing clear_bits method
        self.clear_bits(bit_field.register, register_mask)
    
    def clear_field(self, bit_field: SystemRegisterBitField) -> None:
        """
        Clear an entire bit field (set all bits in the field to 0).
        
        Args:
            bit_field: Bit field to clear
        """
        self.clear_bits(bit_field.register, bit_field.mask)
    
    def set_field(self, bit_field: SystemRegisterBitField, value: int) -> None:
        """
        Set an entire bit field to a specific value.
        
        Args:
            bit_field: Bit field to set
            value: Value to set the field to
        """
        self.write_field(bit_field, value=value) 