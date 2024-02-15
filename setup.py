from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in monopay_app/__init__.py
from monopay_app import __version__ as version

setup(
	name="monopay_app",
	version=version,
	description="Payment GateWay for Mono",
	author="iKrok",
	author_email="kubliy.n@ikrok.net",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
