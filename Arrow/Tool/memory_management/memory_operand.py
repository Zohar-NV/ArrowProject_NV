import random
from typing import Optional
from Arrow.Utils.configuration_management import Configuration, get_config_manager
from Arrow.Utils.logger_management import get_logger
from Arrow.Utils.APIs import choice
from Arrow.Tool.memory_management.memory_block import MemoryBlock
from Arrow.Tool.register_management.register import Register
from Arrow.Tool.state_management import get_state_manager, get_current_state
from Arrow.Tool.memory_management.memory_logger import get_memory_logger

VALID_SIZES = [1, 2, 4, 8]  # Valid memory operand sizes

class Memory:

    # generate incremental memory_unique_id
    _memory_initial_seed_id = random.randint(1234, 5678)  # start at a random label

    def __init__(
            self,
            name : Optional[str] = None,
            address : Optional[int] = None,
            byte_size : Optional[int] = 8,
            memory_type : Optional[str] = "WB",
            shared: bool = False,
            init_value:int = None,
            memory_block: MemoryBlock = None,
            memory_block_offset: int = None,
            cross_core: bool = False,
            alignment: Optional[int] = None,
    ):
        """
        Initializes a Memory to be used as memory operand.
        a Memory is just the operand representation of tha MemoryBlock.
        when asked for a Memory without an MemoryBlock, a block will get allocated

        Parameters:
        - name (str): The name reference of the memory
        - byte_size (int): The byte_size of the memory, must be one of VALID_SIZES
        - shared (bool): decide if the memory should be shared or preserve
        - memory_block: needed if memory is part a bigger sequential block
        - address (int): The address of the memory, relevant for 'baremetal' execution_platform
        - type (str): The type of the memory, relevant for 'baremetal' execution_platform
        - cross_core (bool): decide if the memory should be cross-core
        """
        logger = get_logger()
        config_manager = get_config_manager()
        state_manager = get_state_manager()
        curr_state = state_manager.get_active_state()
        curr_page_table = curr_state.current_el_page_table

        Memory._memory_initial_seed_id += 1
        self.name = name if name is not None else f"mem{Memory._memory_initial_seed_id}"
        self.unique_label = self.name if name is None else f"{self.name}_mem{Memory._memory_initial_seed_id}"
        self._address = address
        self.byte_size = byte_size
        self.shared = shared
        self.memory_type = memory_type
        self.init_value = init_value
        self.memory_block = memory_block
        self.memory_block_offset = memory_block_offset
        self.cross_core = cross_core
        self.alignment = alignment
        self.reused_memory = False

        execution_platform = config_manager.get_value('Execution_platform')

        #==================================================
        # input checking
        if address is not None:
                if execution_platform != 'baremetal':
                    raise ValueError(f"Memory with address constraints is not supported in {execution_platform} execution platform.")
                else:
                    raise ValueError("Memory with address constraints is not yet implemented.")

        if memory_block is None:
            if self.memory_block_offset is not None:
                raise ValueError("Memory_block_offset can't be provided without memory_block.")
        else:
            if self.memory_block_offset is None:
                raise ValueError("Memory_block_offset must be provided with memory_block.")
            if self.init_value is not None:
                raise ValueError("Memory.init_value can't be provided when using a memory_block.")
            if shared is None:
                raise ValueError("Memory.shared can't be provided when using a memory_block.")
            if self.byte_size > self.memory_block.byte_size:
                raise ValueError(f"Memory.byte_size cannot exceed MemoryBlock byte_size. Memory.byte_size: {self.byte_size}, MemoryBlock byte_size: {self.memory_block.byte_size}")
            if self.memory_block_offset < 0:
                raise ValueError(f"Memory.memory_block_offset cannot be negative. Memory.memory_block_offset: {self.memory_block_offset}")
            if self.memory_block_offset + self.byte_size > self.memory_block.byte_size:
                raise ValueError(f"Memory byte_size + offset cannot exceed MemoryBlock byte_size. Memory byte_size: {self.byte_size}, MemoryBlock byte_size: {self.memory_block.byte_size}, Memory.memory_block_offset: {self.memory_block_offset}")

        # if address is not None and _parent_block is None:
        #     raise ValueError("Memory with address constraints is not supported at the moment.")
        if init_value is not None and shared:
            # TODO:: is this limitation really needed? why not allow it the first time and force not to use a reused-memory ?
            raise ValueError(f"Can't initialize value in a shared memory")

        if cross_core and shared:
            raise ValueError(f"Cross-core memory can't be shared")
        
        #Validates the size of a memory operand. If no size is provided, it randomly selects one from VALID_SIZES.
        if byte_size is None:
            # Randomize size if not provided
            self.byte_size = random.choice(VALID_SIZES)
        elif byte_size not in VALID_SIZES:
            # Raise error if size is invalid
            raise ValueError(f"Invalid memory byte size: {self.byte_size}. Valid sizes are {VALID_SIZES}.")

        if alignment is None:
            # to reduce the probability of getting "Aliggnment fault" 
            # TODO:: need to model this better
            self.alignment = choice.choice(values={0:10, 1:30, 2:60})

        #==================================================

        if memory_block is None:
            """
            Need to allocate a MemoryBlock that will wrap this Memory instance. 
            if Memory is shared, it might get reused memoryBlock
            """
            if shared:

                reuse_memory_probability = 50 # TODO:: create a knob for this!!!!
                rand_num = random.randint(0,100)
                should_reuse = True if (rand_num < reuse_memory_probability) else False

                if should_reuse and (name is None) and (self._address is None) and (self.init_value is None):
                    # reuse memory only applicable for DATA_SHARED memory, and when no explicit parameter were asked. Notice I'm checking name and not self.name for that usage
                    from Arrow.Tool.memory_management.memory_usage import get_used_memory_block
                    self.memory_block = get_used_memory_block(curr_page_table.segment_manager, byte_size=byte_size, alignment=self.alignment)
                    # check if such shared memory_block exist
                    if self.memory_block is not None:
                        self.reused_memory = True
                        # Randomly select an offset inside the MemoryBlock
                        if self.byte_size > self.memory_block.byte_size:
                            raise ValueError("Inner block size cannot exceed outer block size.")
                        max_offset = self.memory_block.byte_size - self.byte_size
                        
                        # Ensure offset maintains alignment requirement  
                        if self.alignment > 1:
                            # Calculate the first aligned address within this block
                            block_base_addr = self.memory_block.get_address()
                            first_aligned_addr = ((block_base_addr + self.alignment - 1) // self.alignment) * self.alignment
                            
                            # Calculate offset from block base to first aligned address
                            min_offset = first_aligned_addr - block_base_addr
                            
                            # Check if we have space for the aligned allocation
                            if min_offset + self.byte_size <= max_offset + self.byte_size:  # max_offset is available space
                                # Calculate how many additional aligned positions are available
                                remaining_space = (max_offset + self.byte_size) - (min_offset + self.byte_size)
                                additional_positions = remaining_space // self.alignment
                                
                                if additional_positions > 0:
                                    # Choose random position among available aligned positions
                                    chosen_position = random.randint(0, additional_positions)
                                    self.memory_block_offset = min_offset + (chosen_position * self.alignment)
                                else:
                                    # Only one aligned position available
                                    self.memory_block_offset = min_offset
                            else:
                                # This shouldn't happen if filtering worked correctly
                                self.memory_block_offset = 0
                        else:
                            self.memory_block_offset = random.randint(0, max_offset) if max_offset > 0 else 0

                if not self.reused_memory: # Either because reuse_memory=False or wasn't to find valid option

                    # In 50% probability, allocate a bigger memory block to allow later sharing with overlapping
                    byte_size_extension = choice.choice(values={0:50, random.randint(1, 10):45, random.randint(10, 20):5})
                    new_byte_size = self.byte_size + byte_size_extension
                    self.memory_block = MemoryBlock(name=self.unique_label, byte_size=new_byte_size, address=self._address,
                                                    memory_type=self.memory_type, shared=shared, alignment=self.alignment,
                                                    init_value=self.init_value, _use_name_as_unique_label=True)
                    max_offset = new_byte_size - self.byte_size
                    
                    # Ensure offset maintains alignment requirement
                    if self.alignment > 1:
                        # Calculate max number of aligned positions within the offset range
                        max_aligned_positions = max_offset // self.alignment
                        if max_aligned_positions > 0:
                            # Choose random aligned position
                            aligned_position = random.randint(0, max_aligned_positions)
                            self.memory_block_offset = aligned_position * self.alignment
                        else:
                            self.memory_block_offset = 0
                    else:
                        self.memory_block_offset = random.randint(0, max_offset)
            else:
                # creating a dedicated MemoryBlock
                self.memory_block = MemoryBlock(name=self.unique_label, byte_size=self.byte_size, address=self._address,
                                                memory_type=self.memory_type, shared=shared, init_value=self.init_value, 
                                                cross_core=self.cross_core, _use_name_as_unique_label=True, alignment=self.alignment)
                self.memory_block_offset = 0x0
                self.unique_label = self.memory_block.get_label() # unique_label

        else:
            """
            use existing MemoryBlock and all its attributes. current memory will have an offset withing the existing block.
            """
            self.unique_label = self.memory_block.get_label() # unique_label
            if self.name is None:
                self.name = self.memory_block.name
            self.memory_type = self.memory_block.memory_type

            self.reused_memory = False

        self._address = self.memory_block.get_address() + self.memory_block_offset
        self._pa_address = self.memory_block.get_pa_address() + self.memory_block_offset
        self.cross_core = self.memory_block.cross_core

        memory_logger = get_memory_logger()

        self.memory_str = f"Memory access: [ name={self.name}, address={hex(self._address)}, pa_address={hex(self._pa_address)}, memory_block={self.memory_block.name}, memblock_offset={self.memory_block_offset}, shared={self.shared}, reused_memory={self.reused_memory}, bytesize={self.byte_size}, memory_type={self.memory_type}, init_value={self.init_value}, cross_core={self.cross_core} ]"
  
        memory_logger.log(self.memory_str)
        #print(self.memory_str)

    def get_address(self):
        if self.cross_core:
            return self.memory_block.get_address()+self.memory_block_offset
        else:
            return self._address

    def get_pa_address(self):
        return self._pa_address

    def get_label(self):
        if self.cross_core:
            return self.memory_block.get_label()
        else:
            return self.unique_label


    def format_reg_as_label(self, register:Register):
        '''
        print out the memory representation of label + offset, while assuming the register ALREADY holds the need label.
        This function is useful for dynamically formatting memory access instructions where the memory address is defined by a label and offset, rather than a raw address.
        '''

        config_manager = get_config_manager()
        memory_offset = self.memory_block_offset
        execution_platform = config_manager.get_value('Execution_platform')
        # if execution_platform is 'baremetal':
        #     if Configuration.Architecture.x86:

        if Configuration.Architecture.x86:
            op_size_prefix = byte_to_operand_size(self.byte_size)
            offset_str = f" + {memory_offset:#x}" if memory_offset != 0x0 else ""
            return f"{op_size_prefix} [{register}{offset_str}]"
        elif Configuration.Architecture.riscv:
            return f"{memory_offset:#x}({register})"
            # offset_str = f"{memory_offset:#x}" if memory_offset != 0x0 else ""
            # return f"{offset_str}({register})"
        elif Configuration.Architecture.arm:
            offset_str = f",#{memory_offset:#x}" if memory_offset != 0x0 else ""
            return f"[{register}{offset_str}]"
        else:
            raise ValueError(f"Unknown Architecture requested")


    def get_partial(self, byte_size:int, offset:int=0):
        # Check that the requested size is within bounds
        if byte_size > self.byte_size:
            raise ValueError("Partial memory size cannot be larger than the original memory size.")

        # Check that the offset + size does not exceed the original memory bounds
        if offset < 0 or offset + byte_size > self.byte_size:
            raise ValueError("Offset and size exceed the bounds of the original memory space.")

        # Calculate the new address for the partial memory
        partial_address = self.address + offset

        # Create a new Memory instance for the partial memory
        partial_mem = Memory(address=partial_address, byte_size=byte_size, _parent_block=self)

        return partial_mem

    def __str__(self):

        return self.memory_str

        # TODO:: need to replace the string with a per Arch code.
        # TODO:: need to replace the string with a per Arch code. the problem is that in arm or riscv, we need an additional instruction to set the label in a register
        # TODO:: need to replace the string with a per Arch code.

        # TODO:: Mem.str - If someone if printing it should print all the information, and provide an api for mem.label_reg(reg) that will print the memory operand like 0(reg).
        #         # Also replace all such previous usages when in baremetal we need different logic

        # config_manager = get_config_manager()
        # execution_platform = config_manager.get_value('Execution_platform')
        # if execution_platform is 'baremetal':
        if Configuration.Architecture.x86:
            op_size_prefix = byte_to_operand_size(self.byte_size)
            return f"{op_size_prefix} [{self.base_reg} + {self.offset:#x}]"
        elif Configuration.Architecture.riscv:
            return f"{self.offset:#x}({self.base_reg})"
        elif Configuration.Architecture.arm:
            return f"[{self.base_reg},#{self.offset:#x}]"
        else:
            raise ValueError(f"Unknown Architecture requested")

def byte_to_operand_size(byte_size):
    """
    Convert byte size to the corresponding x86 operand size.
    """
    operand_sizes = {
        1: "byte",    # 1 byte -> byte (8 bits)
        2: "word",    # 2 bytes -> word (16 bits)
        4: "dword",   # 4 bytes -> dword (32 bits)
        8: "qword",   # 8 bytes -> qword (64 bits)
        16: "dqword"  # 16 bytes -> dqword (128 bits)
    }

    # Get the operand size, or raise an error if the byte size is unsupported
    if byte_size in operand_sizes:
        return operand_sizes[byte_size]
    else:
        raise ValueError(f"Unsupported byte size: {byte_size}")