#!/home/scratch.zbuchris_cpu/Arrow/ArrowProject_NV/.venv/bin/python3
 
"""
Arrow Project Entry Point
Run this script from the project root to start Arrow.
"""

if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    
    # Capture the original working directory before changing
    original_cwd = os.getcwd()
    
    # If no --output is specified, add it pointing to original directory
    if '--output' not in sys.argv:
        default_output = os.path.join(original_cwd, 'Arrow_output')
        sys.argv.extend(['--output', default_output])
    
    # Resolve relative paths in arguments before changing directories
    # This ensures user-provided relative paths are resolved from their current directory
    for i, arg in enumerate(sys.argv):
        if arg == '--content' and i + 1 < len(sys.argv):
            # Convert relative content path to absolute path from original directory
            content_path = sys.argv[i + 1]
            if not os.path.isabs(content_path):
                sys.argv[i + 1] = os.path.abspath(os.path.join(original_cwd, content_path))
        elif arg == '--output' and i + 1 < len(sys.argv):
            # Convert relative output path to absolute path from original directory
            output_path = sys.argv[i + 1]
            if not os.path.isabs(output_path):
                sys.argv[i + 1] = os.path.abspath(os.path.join(original_cwd, output_path))
    
    # Set up required tool paths for Arrow's use only
    required_tool_paths = [
        '/home/utils/binutils-2.40-2/bin/',
        '/home/utils/gcc-13.3.0-ld/bin/',
    ]
    
    # Create Arrow-specific PATH without modifying user environment
    existing_paths = [p for p in required_tool_paths if os.path.exists(p)]
    arrow_path = ':'.join(existing_paths + [os.environ.get('PATH', '')])
    os.environ['ARROW_TOOL_PATH'] = arrow_path
    
    # Change to the directory where this script is located (project root)
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Add project root to Python path for proper imports
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    from Arrow.Arrow.main import main
    main() 