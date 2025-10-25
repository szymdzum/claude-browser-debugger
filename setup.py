"""Setup configuration for Browser Debugger CDP tool.

Implements FR-047, FR-048 from spec.md:
- Package as "browser-debugger" for pip installation
- Support development mode (pip install -e .)
- Support production installation (pip install .)
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements.txt for dependencies
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

# Read requirements-dev.txt for development dependencies
dev_requirements_path = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if dev_requirements_path.exists():
    dev_requirements = [
        line.strip()
        for line in dev_requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="browser-debugger",
    version="0.1.0",
    description="Token-efficient Chrome DevTools Protocol debugging tool for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Browser Debugger Contributors",
    author_email="szymon@kumak.dev",
    url="https://github.com/anthropics/claude-code-skills",  # Update with actual URL
    license="MIT",

    # Package discovery
    packages=find_packages(include=["scripts", "scripts.*"]),
    package_dir={"": "."},

    # Include non-Python files (scripts, configs, etc.)
    include_package_data=True,
    package_data={
        "scripts": [
            "core/*.sh",
            "collectors/*.py",
            "utilities/*.sh",
        ],
    },

    # Dependencies
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },

    # CLI entry point
    entry_points={
        "console_scripts": [
            "cdp=scripts.cdp.cli.main:main",
        ],
    },

    # Python version requirement
    python_requires=">=3.10",

    # PyPI classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Debuggers",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],

    # Keywords for PyPI search
    keywords="chrome devtools cdp debugging browser automation testing",

    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/anthropics/claude-code-skills/issues",
        "Source": "https://github.com/anthropics/claude-code-skills",
        "Documentation": "https://github.com/anthropics/claude-code-skills/blob/main/README.md",
    },
)
