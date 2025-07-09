from typing import Union, List, Dict, Any, Optional, Tuple, Type
from peewee import Expression
from Arrow.Tool.generation_management.generate import GeneratedInstruction
from Arrow.Tool.register_management.register import Register
from Arrow.Tool.memory_management.memlayout.segment import CodeSegment
from Arrow.Tool.asm_libraries.loop.loop_base import LoopBase
from Arrow.Tool.asm_libraries.event_trigger.event_trigger_base import EventTriggerBase
from Arrow.Tool.asm_libraries.branch_to_segment.branch_to_segment_base import BranchToSegmentBase
from Arrow.Tool.asm_libraries.memory_array.memory_array import MemoryArray
from Arrow.Tool.asm_libraries.barrier.barrier import Barrier
from Arrow.Tool.asm_libraries.switch_el import SwitchEL
from Arrow.Tool.state_management.switch_state import SwitchState
from Arrow.Tool.ingredient_management.ingredient import Ingredient
from Arrow.Tool.decorators.scenario_decorator import scenario_decorator
from Arrow.Tool.decorators.ingredient_decorator import ingredient_decorator
from Arrow.Utils.configuration_management import Configuration
from Arrow.Externals.db_manager.models import Instruction

class AR:
    # Decorators
    scenario_decorator: Type[scenario_decorator]
    ingredient_decorator: Type[ingredient_decorator]
    
    # Database models
    Instruction: Type[Instruction]
    Ingredient: Type[Ingredient]
    
    # Core methods
    @staticmethod
    def asm(asm_code: str, comment: Optional[str] = None) -> None: ...
    
    @staticmethod
    def comment(comment: str) -> None: ...
    
    @staticmethod
    def Label(postfix: str) -> Any: ...
    
    @staticmethod
    def choice(
        values: Union[Dict[Any, int], List[Any]],
        name: Optional[str] = None,
    ) -> Any: ...
    
    @staticmethod
    def rangeWithPeak(start: int, end: int, peak: int, peak_width: str = 'normal') -> int: ...
    
    @staticmethod
    def adaptive_choice(values: Dict[Any, Union[int, Tuple[int, int]]]) -> Any: ...
    
    @staticmethod
    def generate(
        instruction_count: Optional[int] = 1,
        query: Optional[Union[Expression, Dict]] = None,
        src: Any = None,
        dest: Any = None,
        comment: Optional[str] = None,
    ) -> List[GeneratedInstruction]: ...
    
    @staticmethod
    def switch_EL(target_el_level: int) -> SwitchEL: ...
    
    @staticmethod
    def Loop(
        counter: int,
        counter_type: Optional[str] = None,
        counter_direction: Optional[str] = None,
        label: Optional[str] = None,
        additional_param: Optional[int] = None
    ) -> LoopBase: ...
    
    @staticmethod
    def EventTrigger(
        frequency: Configuration.Frequency = Configuration.Frequency.LOW,
    ) -> EventTriggerBase: ...
    
    @staticmethod
    def MemoryArray(
        array_name: str,
        elements: Any,
        element_size: int = 4
    ) -> MemoryArray: ...
    
    @staticmethod
    def BranchToSegment(code_block: CodeSegment) -> BranchToSegmentBase: ...
    
    @staticmethod
    def Barrier(barrier_name: str) -> Barrier: ...
    
    @staticmethod
    def store_value_into_register(register: Register, value: int) -> None: ...
    
    # Nested classes
    class Trickbox:
        @staticmethod
        def write(
            register: Configuration.TrickboxRegister,
            value: Optional[int] = None,
            source_register: Optional[Register] = None
        ) -> None: ...
        
        @staticmethod
        def read(register: Configuration.TrickboxRegister, target_register: Register) -> None: ...
    
    class Sysreg:
        @staticmethod
        def write(
            register: Configuration.SystemRegister,
            value: Optional[int] = None,
            source_register: Optional[Register] = None
        ) -> None: ...
        
        @staticmethod
        def read(register: Configuration.SystemRegister, target_register: Register) -> None: ...
    
    class State:
        @staticmethod
        def get_current_state_name() -> str: ...
        
        @staticmethod
        def get_current_state_id() -> int: ...
        
        @staticmethod
        def get_all_states_names() -> List[str]: ...
        
        @staticmethod
        def switch_state(state_name: str) -> SwitchState: ...
    
    class Stack:
        @staticmethod
        def push(register_list: List[Register], comment: Optional[str] = None) -> None: ...
        
        @staticmethod
        def pop(register_list: List[Register], comment: Optional[str] = None) -> None: ...
        
        @staticmethod
        def read(offset: int, register: Register, comment: Optional[str] = None) -> None: ...
        
        @staticmethod
        def write(offset: int, register: Register, comment: Optional[str] = None) -> None: ... 