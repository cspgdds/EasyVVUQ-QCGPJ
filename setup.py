from setuptools import setup, find_packages

setup(
name='EasyVVUQ-QCGPJ',

version='0.2.0',

description='A lightweight wrapper on EasyVVUQ enabling the execution of VVUQ '
'using the QCG Pilot Job mechanism.',

long_description='A lightweight wrapper on EasyVVUQ enabling the execution of VVUQ '
'using the QCG Pilot Job mechanism.',

url='https://github.com/vecma-project/EasyVVUQ-QCGPJ',

author='Bartosz Bosak',

install_requires=[
    'pytest',
    'pytest-pep8',
    'qcgPilotManager @ git+https://github.com/vecma-project/QCG-PilotJob.git@v0.7.0#egg=qcgPilotManager',
    'easyvvuq @ git+https://github.com/UCL-CCS/EasyVVUQ.git@v0.5.1#egg=easyvvuq'
],

packages=find_packages(),

scripts=[
    'scripts/easyvvuq_app',
    'scripts/easyvvuq_encode',
    'scripts/easyvvuq_execute',
    'scripts/easyvvuq_encode_execute'
],

include_package_data=True
)
