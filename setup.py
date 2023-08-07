import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fasttask_manager",
    version="0.0.2",
    author="Irid",
    author_email="irid.zzy@gmail.com",
    description="fasttask's manager ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iridesc/fasttask_manager",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "retry"
    ],
)