from setuptools import setup, find_packages

setup(
    name='odss.core',
    packages=find_packages(),
    version='0.1',
    description='',
    install_requires=['odss.common==1.0'],
    namespace_packages=['odss']
)
