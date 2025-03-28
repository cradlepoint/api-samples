from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ncm",
    version="0.0.39",
    author="Nathan Wiens - Cradlepoint",
    author_email="nathan.wiens@cradlepoint.com",
    description="Python client library for Cradlepoint NCM API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cradlepoint/api-samples/tree/master/ncm",
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'requests',
        'urllib3'
    ]
)
