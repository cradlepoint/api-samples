from setuptools import setup, find_packages
with open("README.md", "r") as fh:
    long_description = fh.read()
setup(
    name="ncm",
    version="0.1.1",
    author="Jon Gaudu - Ericsson",
    author_email="jon.gaudu@ericsson.com.com",
    description="Python client library for Cradlepoint NCM API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cradlepoint/api-samples/tree/master/ncm",
    packages=find_packages(exclude=["tests", "tests.*", "_original_rewrite"]),
    python_requires='>=3.6',
    install_requires=[
        'requests',
        'urllib3'
    ]
)
