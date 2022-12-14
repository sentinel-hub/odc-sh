import os

from setuptools import find_packages, setup


def get_long_description():
    this_directory = os.path.abspath(os.path.dirname(__file__))

    with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
        long_description = f.read()

    # Removes lines with an image from description
    return "\n".join(
        line
        for line in long_description.split("\n")
        if not line.strip().startswith("![")
    )


def parse_requirements(file):
    required_packages = []
    with open(os.path.join(os.path.dirname(__file__), file)) as req_file:
        for line in req_file:
            required_packages.append(line.strip())
    return required_packages


def get_version():
    for line in open(os.path.join(os.path.dirname(__file__), "odc_sh", "__init__.py")):
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"').strip("'")
    return version


setup(
    name="odc-sh",
    python_requires=">=3.8",
    version=get_version(),
    description="Sentinel HUB support for open datacube framework",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://gitext.sinergise.com/polar/odc-sh/",
    author="Sinergise",
    author_email="info@sinergise.com",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=parse_requirements("requirements.txt"),
    extras_require={},
    zip_safe=False,
    entry_points={},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering",
    ],
)
