from enum import Enum

class TrickboxRegister(Enum):
    """
    Enumeration of Trickbox fields with their offsets from base address 
    """
    # Base address fields
    TUBE = 0x0000
    CONFIGURATION = 0x0004
    SCHEDULE_FIQ = 0x0008
    SCHEDULE_IRQ = 0x000C

    raise Exception(" Please provide additional trickbox fields of your choice")


    def __str__(self):
        return self.name
