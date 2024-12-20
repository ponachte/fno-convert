from ..prefix import Prefix

import subprocess
import re
import argparse


def get_help_output(command):
    """
    Run the command with --help to get the help output.

    Args:
        command (str): The command to run.

    Returns:
        str: The help text.

    Raises:
        ValueError: If the command or its help flag is not supported.
    """
    try:
        result = subprocess.run(
            [command, '--help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError(f"The command '{command}' does not support '--help'.")
        return result.stdout
    except FileNotFoundError:
        raise ValueError(f"The command '{command}' was not found.")
    except ValueError as e:
        raise ValueError(f"Error while fetching help for '{command}': {str(e)}")

class CommandDescriptor:
    
    @staticmethod
    def from_str(self, cmd, args):
        fun_uri = Prefix.base()[cmd]
        
        keyword = None
        keywords = []
        positional = []
        for i, arg in enumerate(args):
            if arg.startswith('-'):
                # arg is a keyword
                pass