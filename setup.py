import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="undeux",
    version="0.9",
    author="George Flanagin",
    author_email="me+undeux@georgeflanagin.com",
    description="Build database of files to find duplicates and old disc hogs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/georgeflanagin/undeux",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities"
    ],
)
