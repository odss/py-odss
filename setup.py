from setuptools import setup, find_packages

setup(
    name="odss",
    packages=find_packages(),
    version="0.1",
    description="",
    entry_points={
        'console_scripts': [
            'odss = odss.cli.__main__:main'
        ],
    }
)
