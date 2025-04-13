from setuptools import setup, find_packages

setup(
    name="prompt-cli",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'openai',
        'python-dotenv',
        'rich',
        'questionary',
        'tiktoken',
        'pyperclip>=1.8.2'
    ],
    entry_points={
        'console_scripts': [
            'prompt-cli=cli.src.cli:main',
        ],
    },
    package_data={
        'cli': ['prompts/*.txt', 'output/*'],
    },
)