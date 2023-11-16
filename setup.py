from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in ghaima_custom/__init__.py
from ghaima_custom import __version__ as version

setup(
	name="ghaima_custom",
	version=version,
	description="for report",
	author="jay",
	author_email="sarnajay@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
