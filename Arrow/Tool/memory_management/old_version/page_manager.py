import random
from typing import List, Dict, Optional, Tuple

from Arrow.Utils.configuration_management import Configuration, get_config_manager
from Arrow.Utils.logger_management import get_logger
from Arrow.Tool.state_management import get_current_state, get_state_manager

from Arrow.Tool.memory_management.memory_segments import MemoryRange
from Arrow.Tool.memory_management.memory_page import Page
from Arrow.Tool.memory_management import interval_lib
from Arrow.Tool.memory_management.memory_logger import get_memory_logger


class MMU:
    '''
    Represents a single MMU context with its own virtual address space.
    Each MMU is associated with a specific core, exception level, and security context.

    VA Space Management: Track and allocate virtual address ranges
    Page Table Generation: Create and maintain page table structures
    Mapping Operations: Create VA→PA mappings with attributes
    MMU Configuration: Generate register values (TTBR, TCR, MAIR)
    Attribute Management: Support different memory permissions/cacheability
    '''


    def __init__(self, mmu_name: str, state_name: str, execution_context: Configuration.Execution_context ):
        """
        Initialize an MMU context.
        
        Args:
            mmu_name: Unique identifier for this MMU (e.g., "c0_el3root", "c1_el1NS")
            state_name: State this MMU belongs to (e.g., "core_0", "core_1")
            execution_context: Execution context (EL3, EL1_NS, EL1_S, EL2_NS, EL2_S, etc.)
        """
        logger = get_logger()
        memory_log(f"==================== setting up MMU: {mmu_name} for {state_name}", print_both=True)

        self.mmu_name = mmu_name
        self.state_name = state_name
        self.execution_context = execution_context

        self.va_memory_range = MemoryRange(core="VA", address=Configuration.ByteSize.SIZE_2G.in_bytes() + Configuration.ByteSize.SIZE_2M.in_bytes(), # leaving 2MB for the MMU page table and constants
                                      byte_size=2 * Configuration.ByteSize.SIZE_4G.in_bytes())

        # VA space management - track unmapped, mapped, and allocated regions
        self.unmapped_va_intervals = interval_lib.IntervalLib(
            start_address=self.va_memory_range.address,
            total_size=self.va_memory_range.byte_size,
            default_metadata={"state": "unmapped", "type": "va", "mmu": mmu_name}
        )
        
        self.mapped_va_intervals = interval_lib.IntervalLib(
            default_metadata={"state": "mapped", "type": "va", "mmu": mmu_name}
        )
        
        self.allocated_va_intervals = interval_lib.IntervalLib(
            default_metadata={"state": "allocated", "type": "va", "mmu": mmu_name}
        )
        
        self.non_allocated_va_intervals = interval_lib.IntervalLib(
            default_metadata={"state": "non_allocated", "type": "va", "mmu": mmu_name}
        )

        # Page table entries for this MMU
        self.page_table_entries: List[Page] = []
        self.page_table_entries_by_type = {
            Configuration.Page_types.TYPE_CODE: [],
            Configuration.Page_types.TYPE_DATA: [],
            Configuration.Page_types.TYPE_DEVICE: [],
            Configuration.Page_types.TYPE_SYSTEM: []
        }
        
        # MMU-specific attributes and metadata
        self.attributes = {}
        
        memory_log(f"Created MMU: {mmu_name} for {state_name} at {execution_context.value}")


    def __str__(self):
        return f"MMU({self.mmu_name}, {self.state_name}, {self.execution_context.value})"

    def _find_va_eq_pa_unmapped_region(self, mmu_manager, current_state, state_name, size_bytes, alignment_bits, page_type):
        """
        Find a region that is available at the same address in both VA and PA unmapped spaces
        Uses randomization logic similar to IntervalLib.find_region
        
        Returns: (va_start, pa_start, size) - where va_start == pa_start
        """
        memory_log(f"Searching for unmapped region where VA=PA is possible, size: {size_bytes}, alignment: {alignment_bits}")
        
        # Get the unmapped VA and PA intervals
        #va_intervals = memory_space_manager.state_unmapped_va_intervals[state_name].free_intervals
        va_intervals = self.unmapped_va_intervals.get_intervals()
        pa_intervals = mmu_manager.unmapped_pa_intervals.get_intervals()
        
        memory_log(f"Found {len(va_intervals)} unmapped VA regions and {len(pa_intervals)} unmapped PA regions")
        
        # Find overlapping regions where VA can equal PA
        matching_regions = []
        for va_interval in va_intervals:
            va_start = va_interval.start
            va_size = va_interval.size
            for pa_interval in pa_intervals:
                pa_start = pa_interval.start
                pa_size = pa_interval.size
                
                # Calculate the intersection of the VA and PA intervals
                # For VA=PA, we need the same address to be available in both spaces
                overlap_start = max(va_start, pa_start)
                overlap_end = min(va_start + va_size - 1, pa_start + pa_size - 1)
                
                if overlap_start <= overlap_end:
                    # There is an overlap
                    overlap_size = overlap_end - overlap_start + 1
                    if overlap_size >= size_bytes:
                        # This overlapping region is big enough
                        matching_regions.append((overlap_start, overlap_size))
        
        if not matching_regions:
            memory_log(f"Could not find any unmapped region where VA=PA is possible for size {size_bytes}", "error")
            raise ValueError(f"Could not find any unmapped region where VA=PA is possible for size {size_bytes}")
        
        # Apply alignment and find suitable intervals (similar to find_region logic)
        suitable_intervals = []
        if alignment_bits is not None:
            alignment = 1 << alignment_bits
            for region_start, region_size in matching_regions:
                # Calculate alignment boundaries
                first_aligned = (region_start + alignment - 1) & ~(alignment - 1)
                last_possible_start = region_start + region_size - size_bytes
                last_aligned = last_possible_start & ~(alignment - 1)
                
                if first_aligned <= last_aligned and first_aligned + size_bytes <= region_start + region_size:
                    # This region can accommodate aligned allocation
                    suitable_intervals.append(((region_start, region_size), first_aligned, last_aligned))
        else:
            # No alignment needed, all regions are suitable
            for region_start, region_size in matching_regions:
                suitable_intervals.append(((region_start, region_size), region_start, region_start + region_size - size_bytes))
                
        if not suitable_intervals:
            memory_log(f"Could not find any aligned unmapped region where VA=PA is possible for size {size_bytes}", "error")
            raise ValueError(f"Could not find any aligned unmapped region where VA=PA is possible for size {size_bytes}")
        
        # print(f"zzzzzzzzzzzzzzzzzzzzzzzzzz suitable_intervals:")
        # for interval in suitable_intervals:
        #     print(f"interval: {hex(interval[0][0])}, {hex(interval[0][1])}, {hex(interval[1])}, {hex(interval[2])}")

        # Randomize interval selection (similar to find_region)
        if len(suitable_intervals) > 1:
            chosen_idx = random.randrange(0, len(suitable_intervals))
        else:
            chosen_idx = 0
            
        interval, first_aligned, last_aligned = suitable_intervals[chosen_idx]
        region_start, region_size = interval
        
        # Randomize position within the chosen interval (similar to find_region logic)
        if alignment_bits is not None and alignment_bits > 0:
            alignment = 1 << alignment_bits
            if first_aligned != last_aligned:
                # Count number of possible aligned positions
                count = ((last_aligned - first_aligned) // alignment) + 1
                # Choose a random position
                random_offset = random.randint(0, count - 1) * alignment
                va_start = first_aligned + random_offset
            else:
                # Only one aligned position possible
                va_start = first_aligned
        else:
            # No alignment, randomize within the entire suitable range
            max_start = region_start + region_size - size_bytes
            va_start = random.randint(region_start, max_start)
        
        pa_start = va_start  # VA=PA constraint
        memory_log(f"Selected VA=PA unmapped region at address 0x{va_start:x} (VA=PA), size: {size_bytes}")
        
        return va_start, pa_start, size_bytes

    def allocate_page(self, size:Configuration.Page_sizes=None, alignment_bits:int=None, page_type:Configuration.Page_types=None, permissions:int=None, cacheable:str=None, shareable:str=None, custom_attributes:dict=None, sequential_page_count:int=1, VA_eq_PA:bool=False):
        memory_log("")
        memory_log(f"======================== PageTableManager - allocate_page for '{self.mmu_name}' MMU")
        memory_log(f"==== size: {size}, alignment_bits: {alignment_bits}, page_type: {page_type}, permissions: {permissions}, cacheable: {cacheable}, shareable: {shareable}, custom_attributes: {custom_attributes}, sequential_page_count: {sequential_page_count}, VA_eq_PA: {VA_eq_PA}")

        if size is None:
            size = random.choice([Configuration.Page_sizes.SIZE_4K, Configuration.Page_sizes.SIZE_2M])#, Configuration.Page_sizes.SIZE_1G])
        else:
            if size not in [Configuration.Page_sizes.SIZE_4K, Configuration.Page_sizes.SIZE_2M]:#, Configuration.Page_sizes.SIZE_1G]:
                raise ValueError(f"Size must be 4KB or 2MB. {size} is not valid. 1GB is still not supported.")

        #For a 4 KB page size, you need 12-bit alignment (i.e., addresses must be aligned to 2^12 bytes).
        #For a 2 MB page size, you need 21-bit alignment (i.e., addresses must be aligned to 2^21 bytes).
        #For a 1 GB page size, you need 30-bit alignment (i.e., addresses must be aligned to 2^30 bytes).
        if alignment_bits is None:
            if size == Configuration.Page_sizes.SIZE_4K:
                alignment_bits = 12
            elif size == Configuration.Page_sizes.SIZE_2M:
                alignment_bits = 21
            elif size == Configuration.ByteSize.SIZE_1G.in_bytes():
                alignment_bits = 30
        else:
            if size == Configuration.Page_sizes.SIZE_4K and alignment_bits < 12:
                raise ValueError(f"4KB page size requires at least 12-bit alignment. {alignment_bits} is not valid.")
            elif size == Configuration.Page_sizes.SIZE_2M and alignment_bits < 21:
                raise ValueError(f"2MB page size requires at least 21-bit alignment. {alignment_bits} is not valid.")
            elif size == Configuration.Page_sizes.SIZE_1G and alignment_bits < 30:
                raise ValueError(f"1GB page size requires at least 30-bit alignment. {alignment_bits} is not valid.")

        if page_type is None:
            raise ValueError("page_type is required")
        if permissions is None:
            permissions = Page.PERM_READ | Page.PERM_WRITE | Page.PERM_EXECUTE
        if cacheable is None:
            cacheable = Page.CACHE_WB
        if shareable is None:
            shareable = Page.SHARE_NONE
        if custom_attributes is None:
            custom_attributes = {}

        if sequential_page_count > 1:
            full_size = size.value * sequential_page_count
        else:
            full_size = size.value
            
        # Convert enum sizes to integers for interval operations
        # Explicit conversion to handle all possible cases
        if isinstance(size, Configuration.Page_sizes):
            # Access the Enum value directly
            size_bytes = size.value
        else:
            size_bytes = size  # Assume it's already an integer
            
        if sequential_page_count > 1:
            full_size_bytes = size_bytes * sequential_page_count
        else:
            full_size_bytes = size_bytes
            
        # Get current state and memory space manager
        from Arrow.Tool.memory_management.memory_space_manager import get_mmu_manager

        mmu_manager = get_mmu_manager()
        current_state = get_current_state()
        state_name = current_state.state_name
        
        # Step 1: Find and allocate regions from unmapped space
        try:
            if VA_eq_PA:
                memory_log(f"Allocating unmapped memory with VA=PA constraint, size: {full_size_bytes}, alignment: {alignment_bits}")
                
                # Find a region that is available at the same address in both VA and PA unmapped spaces
                va_start, pa_start, size = self._find_va_eq_pa_unmapped_region(
                    mmu_manager, 
                    current_state, 
                    state_name, 
                    full_size_bytes, 
                    alignment_bits, 
                    page_type
                )
                
                # Allocate the region from unmapped space
                # First, update the unmapped intervals
                # memory_space_manager.state_unmapped_va_intervals[state_name].remove_region(va_start, size)
                self.unmapped_va_intervals.remove_region(va_start, size)
                mmu_manager.unmapped_pa_intervals.remove_region(pa_start, size)
                
                # Map the VA to PA with equal addresses
                mmu_manager.map_va_to_pa(self, va_start, pa_start, size, page_type)
                
                va_size = size
                memory_log(f"Successfully allocated and mapped VA=PA memory at 0x{va_start:x}, size: {size}")
                
            else:
                memory_log(f"Allocating unmapped memory without VA=PA constraint, size: {full_size_bytes}, alignment: {alignment_bits}")

                # Original implementation for non-VA_eq_PA case
                # Use the find_and_remove method which handles state initialization
                va_start, va_size = self.unmapped_va_intervals.find_and_remove(full_size_bytes, alignment_bits)
                #memory_log(f"Successfully allocated VA memory at 0x{va_start:x}, size: {va_size}")
                
                pa_allocation = mmu_manager.allocate_pa_interval(full_size_bytes, alignment_bits=alignment_bits)
                #memory_log(f"Successfully allocated PA memory at 0x{pa_allocation[0]:x}, size: {pa_allocation[1]}")
                pa_start, pa_size = pa_allocation
                
                memory_log(f"Successfully mapped VA to PA at 0x{va_start:x}, 0x{pa_start:x}, size: {va_size}")

                # Step 2: Add the allocated regions to mapped pools
                # First, add to mapped intervals pool, specifying the page type
                mmu_manager.map_va_to_pa(self, va_start, pa_start, va_size, page_type)
                
        except (ValueError, MemoryError) as e:
            memory_log(f"Failed to allocate page memory: {e}", level="error")
            raise ValueError(f"Could not allocate memory regions of size {full_size_bytes} with alignment {alignment_bits}")
        
        # Create the page objects for each page in the sequence
        result = []
        for i in range(sequential_page_count):
            page = Page(
                va=va_start + i * size_bytes, 
                pa=pa_start + i * size_bytes, 
                size=size_bytes, 
                page_type=page_type, 
                permissions=permissions, 
                cacheable=cacheable, 
                shareable=shareable, 
                execution_context=self.execution_context, 
                custom_attributes=custom_attributes
            )
            
            # Add to our tracking collections
            self.page_table_entries.append(page)
            self.page_table_entries_by_type[page.page_type].append(page)
            result.append(page)
            
            memory_log(f"Created page: {page}")
            
        # Return result based on sequential_page_count
        if sequential_page_count == 1:
            return result[0]  
        else:
            return result


    def allocate_cross_core_page(self):
        memory_log("")
        memory_log("======================== PageTableManager - allocate_cross_core_page")

        # from the cross_core_page all is hard-coded for now. TODO:: consider making it configurable in the future.
        size = Configuration.Page_sizes.SIZE_2M # setting big space, as this pages can also be used for non-cross segments 

        if size == Configuration.Page_sizes.SIZE_4K:
            alignment_bits = 12
        elif size == Configuration.Page_sizes.SIZE_2M:
            alignment_bits = 21
        elif size == Configuration.ByteSize.SIZE_1G.in_bytes():
            alignment_bits = 30

        page_type = Configuration.Page_types.TYPE_DATA
        permissions = Page.PERM_READ | Page.PERM_WRITE | Page.PERM_EXECUTE
        cacheable = Page.CACHE_WB
        shareable = Page.SHARE_NONE
        custom_attributes = {}

        memory_log(f"==== size: {size}, alignment_bits: {alignment_bits}, page_type: {page_type}, permissions: {permissions}, cacheable: {cacheable}, shareable: {shareable}, custom_attributes: {custom_attributes}")

        size_bytes = size.value

        # Get current state and memory space manager
        from Arrow.Tool.memory_management.memory_space_manager import get_mmu_manager
        mmu_manager = get_mmu_manager()
        state_manager = get_state_manager()

        
        try:
              # Step 1: Find and allocate regions from unmapped space
            pa_allocation = mmu_manager.allocate_pa_interval(size_bytes, alignment_bits=alignment_bits)
            pa_start, pa_size = pa_allocation

            orig_state = state_manager.get_active_state()
            for state_name in state_manager.get_all_states():
                state_manager.set_active_state(state_name)
                curr_state = state_manager.get_active_state()

                core_mmus = mmu_manager.get_core_mmus(state_name)
                for mmu in core_mmus:

                    va_start, va_size = mmu.unmapped_va_intervals.find_and_remove(size_bytes, alignment_bits)
                    
                    # Step 2: Add the allocated regions to mapped pools
                    # First, add to mapped intervals pool, specifying the page type
                    mmu_manager.map_va_to_pa(mmu, va_start, pa_start, va_size, page_type)
                    
                    # Create the page objects for each page in the sequence
                    page = Page(
                        va=va_start, 
                        pa=pa_start, 
                        size=size_bytes, 
                        page_type=page_type, 
                        permissions=permissions, 
                        cacheable=cacheable, 
                        shareable=shareable, 
                        execution_context=mmu.execution_context, 
                        custom_attributes=custom_attributes,
                        is_cross_core=True
                    )

                    # Add to our tracking collections
                    mmu.page_table_entries.append(page)
                    mmu.page_table_entries_by_type[page.page_type].append(page)
                    
                    
                    memory_log(f"Created Cross-Core page {curr_state.state_name}:{mmu.mmu_name} - {page}")

            state_manager.set_active_state(orig_state.state_name)

        except (ValueError, MemoryError) as e:
            memory_log(f"Failed to allocate page memory: {e}", level="error")
            raise ValueError(f"Could not allocate memory regions of size {size} with alignment {alignment_bits}")
        
    
    def get_pages(self) -> List[Page]:
        """Get all pages in this MMU."""
        return self.page_table_entries
    
    def get_pages_by_type(self, page_type: Configuration.Page_types) -> List[Page]:
        """Get pages of a specific type."""
        return self.page_table_entries_by_type[page_type]
    
    # Query Methods
    def is_mapped(self, va_addr: int, size: int = 1) -> bool:
        """Check if a VA region is mapped."""
        return not self.unmapped_va_intervals.is_region_available(va_addr, size)
    
    def is_allocated(self, va_addr: int, size: int = 1) -> bool:
        """Check if a VA region is allocated (has pages)."""
        va_end = va_addr + size - 1
        for page in self.page_table_entries:
            if page.va <= va_end and page.end_va >= va_addr:
                return True
        return False
    
    def find_available_region(self, size: int, alignment_bits: int = None) -> Optional[Tuple[int, int]]:
        """Find an available unmapped region."""
        try:
            return self.unmapped_va_intervals.find_region(size, alignment_bits)
        except ValueError:
            return None
    
    # Attribute Management
    def set_attribute(self, key: str, value):
        """Set an MMU-specific attribute."""
        self.attributes[key] = value
    
    def get_attribute(self, key: str, default=None):
        """Get an MMU-specific attribute."""
        return self.attributes.get(key, default)
    
    # Statistics and Debugging
    def get_memory_stats(self) -> Dict:
        """Get memory usage statistics for this MMU."""
        unmapped_intervals = self.unmapped_va_intervals.get_intervals()
        mapped_intervals = self.mapped_va_intervals.get_intervals()
        allocated_intervals = self.allocated_va_intervals.get_intervals()
        
        return {
            "mmu_name": self.mmu_name,
            "state_name": self.state_name,
            "execution_context": self.execution_context.value,
            "va_space": {
                "start": hex(self.va_memory_range.address),
                "size": hex(self.va_memory_range.byte_size),
                "unmapped_regions": len(unmapped_intervals),
                "mapped_regions": len(mapped_intervals),
                "allocated_regions": len(allocated_intervals)
            },
            "pages": {
                "total": len(self.page_table_entries),
                "code": len(self.page_table_entries_by_type[Configuration.Page_types.TYPE_CODE]),
                "data": len(self.page_table_entries_by_type[Configuration.Page_types.TYPE_DATA]),
                "device": len(self.page_table_entries_by_type[Configuration.Page_types.TYPE_DEVICE]),
                "system": len(self.page_table_entries_by_type[Configuration.Page_types.TYPE_SYSTEM])
            }
        }
    
    def print_summary(self, verbose: bool = False):
        """Print a comprehensive summary of this MMU's state."""
        stats = self.get_memory_stats()
        memory_log(f"\nMMU Summary: {self.mmu_name}")
        memory_log(f"  State: {stats['state_name']}")
        memory_log(f"  Execution Context: {stats['execution_context']}")
        memory_log(f"  VA Space: {stats['va_space']['start']} - {stats['va_space']['size']}")
        memory_log(f"  Unmapped Regions: {stats['va_space']['unmapped_regions']}")
        memory_log(f"  Mapped Regions: {stats['va_space']['mapped_regions']}")
        memory_log(f"  Allocated Regions: {stats['va_space']['allocated_regions']}")
        memory_log(f"  Pages: {stats['pages']['total']} total ({stats['pages']['code']} code, {stats['pages']['data']} data)")
        
        if verbose:
            memory_log(f"  Device Pages: {stats['pages']['device']}")
            memory_log(f"  System Pages: {stats['pages']['system']}")
            memory_log(f"  Attributes: {self.attributes}")
            
            # Show detailed interval information
            memory_log(f"  Detailed VA Space:")
            unmapped = self.unmapped_va_intervals.get_intervals()
            for i, interval in enumerate(unmapped):
                memory_log(f"    Unmapped {i}: 0x{interval.start:x}-0x{interval.start + interval.size - 1:x} (size: 0x{interval.size:x})")
    
    def print_page_tables(self):
        current_state = get_current_state()
        memory_log("")
        memory_log(f"==================== PageTableManager - print_page_tables {current_state.state_name} - '{self.mmu_name}' MMU")
        for page in self.page_table_entries:
            memory_log(f"Page: {page}")
    