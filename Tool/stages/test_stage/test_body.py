from typing import Optional
from Utils.logger_management import get_logger
from Utils.configuration_management import Configuration
from Tool.state_management import get_state_manager
from Tool.state_management.switch_state import SwitchState
from Tool.scenario_management import ScenarioWrapper, get_scenario_manager
from Tool.asm_libraries.asm_logger import AsmLogger
from Utils.APIs import choice
from Tool.asm_libraries.branch_to_segment import branch_to_segment
from Utils.statistics_managment import get_statistics_manager


def execute_scenario(scenario_instance):
    AsmLogger.comment(f"========================== Start scenario {scenario_instance} ====================")

    # Check if we got a ScenarioWrapper instance
    if not isinstance(scenario_instance, ScenarioWrapper):
        raise ValueError("Error: Expected a ScenarioWrapper instance but got:", type(scenario_instance))

    statistics_manager = get_statistics_manager()
    statistics_manager.increment("scenario_count")

    scenario_instance.func()  # Call the wrapped function

    AsmLogger.comment(f"========================== End scenario {scenario_instance} ====================")

def do_scenario(current_scenario: Optional[int], max_scenario:Optional[int]):
    logger = get_logger()
    state_manager = get_state_manager()
    current_state = state_manager.get_active_state()
    scenario_manager = get_scenario_manager()

    available_blocks = current_state.memory_manager.get_segments(pool_type=Configuration.Memory_types.CODE)
    # Filter the list to exclude the current code block
    available_blocks_without_current = [block for block in available_blocks if block != current_state.current_code_block]
    # Randomly select from the filtered list
    selected_block = choice.choice(values=available_blocks_without_current)

    selected_scenario = scenario_manager.get_random_scenario(tags=dict(Configuration.Knobs.Template.scenario_query.get_value()))

    info_str = f"BODY:: Running {current_state.state_name}, scenario {current_scenario}(:{max_scenario}), scenario {selected_scenario}"
    logger.info(info_str)
    AsmLogger.comment(info_str)

    two_way_branch = choice.choice(values=[True, False])
    if two_way_branch:
        with branch_to_segment.BranchToSegment(selected_block):
            execute_scenario(selected_scenario)
    else:
        branch_to_segment.BranchToSegment(selected_block).one_way_branch()
        execute_scenario(selected_scenario)


def do_body():
    logger = get_logger()
    state_manager = get_state_manager()
    available_states = state_manager.states_dict
    logger.info("============ do_body")

    per_core_scenario_count = {}
    for state_id in available_states:
        core = state_id
        per_core_scenario_count[core] = (1, int(Configuration.Knobs.Template.scenario_count)) # TODO:: replace this with per state knob state_manager.scenario_count

        with SwitchState(core):
            AsmLogger.comment(f"========================= core {core} - TEST BODY - start =====================")

    available_cores = list(available_states.keys())
    while available_cores:
        # go over each of the cores, execute scenarios as long as there is what to execute
        # once a certain core reach out its max scenario count, he will be removed from the list

        # Iterate over a copy of the list to avoid modifying the list during iteration
        for core in available_cores[:]:  # Create a shallow copy of the list
            with SwitchState(core):
                current_scenario, max_scenario = per_core_scenario_count.get(core)
                per_core_scenario_count[core] = (current_scenario + 1, max_scenario)
                if current_scenario == max_scenario:
                    available_cores.remove(core)
                do_scenario(current_scenario, max_scenario)

    available_cores = list(available_states.keys())
    for core in available_cores:
        with SwitchState(core):
            AsmLogger.comment(f"========================= core {core} - TEST BODY - end =====================")
