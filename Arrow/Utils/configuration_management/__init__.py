from Arrow.Utils.configuration_management.configuration_management import get_config_manager
from Arrow.Utils.configuration_management.knob_manager import get_knob_manager
from Arrow.Utils.configuration_management.knobs import Knobs


class Configuration:
    from Arrow.Utils.configuration_management.enums import Architecture, Memory_types, Page_types, Page_sizes, ByteSize, Tag, Priority, PRIORITY_WEIGHTS, Frequency, Execution_context
    from Arrow.Tool.asm_libraries.trickbox.trickbox_fields import TrickboxField

    Architecture = Architecture
    Memory_types = Memory_types
    Page_types = Page_types
    Page_sizes = Page_sizes
    ByteSize = ByteSize
    Tag = Tag
    Priority = Priority
    PRIORITY_WEIGHTS = PRIORITY_WEIGHTS
    Frequency = Frequency
    Execution_context = Execution_context
    TrickboxField = TrickboxField

    Knobs = Knobs()



