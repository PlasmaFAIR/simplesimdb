import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplesimdb",
    version="0.1.0",
    author="Matthias Wiesenberger",
    author_email="mattwi@fysik.dtu.dk",
    description="Create, access and manage simple simulation data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mwiesenberger/simplesimdb",
    pymodules=["simplesimdb"],
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific simulations :: Libraries",
        "Topic :: Utilities",
    ],
    python_requires='>=3.6',
    setup_requires=['pytest-runner'],
    tests_require=['pytest']
)
