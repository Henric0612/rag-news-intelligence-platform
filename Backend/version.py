"""Runtime build identity.

Release images inject APP_VERSION and GIT_SHA at build time; local builds and
native runs fall back to development defaults. Values are read on every call so
the environment is the single source.
"""
import os


DEFAULT_APP_VERSION = '0.0.0-dev'
DEFAULT_GIT_SHA = 'unknown'


def get_build_info():
    """Return the current build identity from the process environment."""
    return {
        'version': os.environ.get('APP_VERSION', DEFAULT_APP_VERSION),
        'git_sha': os.environ.get('GIT_SHA', DEFAULT_GIT_SHA),
    }
