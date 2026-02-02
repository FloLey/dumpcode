"""Unit tests for CLI edge cases in main.py."""

from unittest.mock import patch
from pathlib import Path

from dumpcode.main import main


class TestMainEdgeCases:
    """Test CLI edge cases and meta-flags."""
    
    def test_main_path_not_dir(self):
        """Test that main returns error when path is not a directory."""
        # Test with /dev/null (exists but is not a directory)
        test_path = "/dev/null"
        
        with patch('sys.argv', ['dumpcode', test_path]):
            with patch('builtins.print') as mock_print:
                main()
                
                # Should print error about invalid directory
                mock_print.assert_any_call(f"Error: Invalid directory '{Path(test_path).resolve()}'")
    
    def test_main_test_models_flag(self):
        """Test that --test-models flag triggers run_diagnostics."""
        with patch('sys.argv', ['dumpcode', '--test-models']):
            with patch('dumpcode.ai.diagnostics.run_diagnostics') as mock_diagnostics:
                with patch('dumpcode.main.load_env_file'):  # Mock env loading
                    main()
                    
                    # Should call run_diagnostics
                    mock_diagnostics.assert_called_once()
    
    def test_main_test_models_with_path(self):
        """Test that --test-models flag works with path argument."""
        with patch('sys.argv', ['dumpcode', '.', '--test-models']):
            with patch('dumpcode.ai.diagnostics.run_diagnostics') as mock_diagnostics:
                with patch('dumpcode.main.load_env_file'):
                    with patch('pathlib.Path.is_dir', return_value=True):
                        main()
                        
                        mock_diagnostics.assert_called_once()
    
    def test_main_init_flag(self):
        """Test that --init flag triggers interactive_init."""
        with patch('sys.argv', ['dumpcode', '--init']):
            with patch('dumpcode.main.interactive_init') as mock_init:
                with patch('dumpcode.main.load_env_file'):
                    main()
                    
                    mock_init.assert_called_once()
    
    def test_main_new_plan_flag(self):
        """Test that --new-plan flag triggers handle_new_plan."""
        test_plan = "test_plan.md"
        
        with patch('sys.argv', ['dumpcode', '--new-plan', test_plan]):
            with patch('dumpcode.main.handle_new_plan') as mock_new_plan:
                with patch('dumpcode.main.load_env_file'):
                    main()
                    
                    mock_new_plan.assert_called_once()
    
    def test_main_new_plan_stdin(self):
        """Test that --new-plan '-' reads from stdin."""
        with patch('sys.argv', ['dumpcode', '--new-plan', '-']):
            with patch('dumpcode.main.handle_new_plan') as mock_new_plan:
                with patch('dumpcode.main.load_env_file'):
                    main()
                    
                    # Should call handle_new_plan with '-' as second argument
                    mock_new_plan.assert_called_once()
    
    def test_main_change_profile_flag(self):
        """Test that --change-profile flag triggers handle_meta_mode."""
        test_profile = "test-profile"
        test_output = "output.txt"
        
        with patch('sys.argv', ['dumpcode', '--change-profile', test_profile, '--output-file', test_output]):
            with patch('dumpcode.main.handle_meta_mode') as mock_meta_mode:
                with patch('dumpcode.main.load_env_file'):
                    with patch('dumpcode.main.load_or_create_config', return_value={}):
                        with patch('dumpcode.main.setup_logger'):
                            with patch('pathlib.Path.is_dir', return_value=True):
                                main()
                                
                                mock_meta_mode.assert_called_once()
    
    def test_main_reset_version_flag(self):
        """Test that --reset-version flag is passed to load_or_create_config."""
        with patch('sys.argv', ['dumpcode', '--reset-version']):
            with patch('dumpcode.main.load_or_create_config') as mock_load_config:
                with patch('dumpcode.main.load_env_file'):
                    with patch('dumpcode.main.run_dump'):  # Mock run_dump to avoid actual execution
                        with patch('dumpcode.main.setup_logger'):
                            with patch('pathlib.Path.is_dir', return_value=True):
                                main()
                                
                                # Should call load_or_create_config with reset_version=True
                                mock_load_config.assert_called_once()
                                # Check that reset_version argument is True
                                call_kwargs = mock_load_config.call_args[1]
                                assert call_kwargs.get('reset_version') is True
    
    def test_main_verbose_flag(self):
        """Test that --verbose flag is passed to setup_logger."""
        with patch('sys.argv', ['dumpcode', '--verbose']):
            with patch('dumpcode.main.setup_logger') as mock_setup_logger:
                with patch('dumpcode.main.load_env_file'):
                    with patch('dumpcode.main.load_or_create_config', return_value={}):
                        with patch('dumpcode.main.run_dump'):
                            with patch('pathlib.Path.is_dir', return_value=True):
                                main()
                                
                                # Should call setup_logger with verbose=True
                                mock_setup_logger.assert_called_once()
                                call_args = mock_setup_logger.call_args
                                assert call_args[1].get('verbose') is True
    
    def test_main_no_copy_flag(self):
        """Test that --no-copy flag is handled in meta mode."""
        test_profile = "test-profile"
        test_output = "output.txt"
        
        with patch('sys.argv', ['dumpcode', '--change-profile', test_profile, '--output-file', test_output, '--no-copy']):
            with patch('dumpcode.main.handle_meta_mode') as mock_meta_mode:
                with patch('dumpcode.main.load_env_file'):
                    with patch('dumpcode.main.load_or_create_config', return_value={}):
                        with patch('dumpcode.main.setup_logger'):
                            with patch('pathlib.Path.is_dir', return_value=True):
                                main()
                                
                                # Check that args.no_copy is True in the call
                                mock_meta_mode.assert_called_once()
                                args = mock_meta_mode.call_args[0][0]
                                assert args.no_copy is True
    
    def test_main_empty_args(self):
        """Test main with no arguments (defaults to current directory)."""
        with patch('sys.argv', ['dumpcode']):
            with patch('dumpcode.main.load_env_file'):
                with patch('dumpcode.main.load_or_create_config', return_value={}):
                    with patch('dumpcode.main.run_dump') as mock_run_dump:
                        with patch('dumpcode.main.setup_logger'):
                            with patch('pathlib.Path.is_dir', return_value=True):
                                main()
                                
                                # Should call run_dump with current directory
                                mock_run_dump.assert_called_once()
    
    def test_main_custom_args_list(self):
        """Test main with custom args_list parameter."""
        test_args = ['.', '--verbose']
        
        with patch('dumpcode.main.load_env_file'):
            with patch('dumpcode.main.load_or_create_config', return_value={}):
                with patch('dumpcode.main.run_dump') as mock_run_dump:
                    with patch('dumpcode.main.setup_logger'):
                        with patch('pathlib.Path.is_dir', return_value=True):
                            main(test_args)
                            
                            # Should process the custom args list
                            mock_run_dump.assert_called_once()