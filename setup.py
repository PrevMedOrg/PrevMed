from setuptools import find_packages, setup

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="PrevMed",
    version="0.9.6",
    description="Générateur dynamique de questionnaires cliniques avec interface Gradio et scoring automatisé en R ou Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PrevMedOrg/PrevMed/",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    license="GPLv3",
    keywords=[
        "prevention",
        "preventive",
        "medical",
        "care",
        "health",
        "formulaires",
        "surveys",
        "clinical",
        "clinique",
        "APHP",
        "AP-HP",
        "hopital",
        "hospital",
        "healthcare",
        "patients",
    ],
    entry_points={
        "console_scripts": [
            "prevmed=PrevMed.__main__:cli_launcher",
            "PrevMed=PrevMed.__main__:cli_launcher",
        ],
    },
    python_requires="==3.13",  # bind to 3.13 as it's faster but not as recent as 3.14+
    install_requires=[
        "reportlab  == 4.4.4",
        "gradio     == 5.49.1",
        "loguru     == 0.7.3",
        "pyr2       == 2.0.0",
        "pyyaml     == 6.0.3",
        "rpy2[all]  == 3.6.4",
        "filelock   == 3.20.0",  # Used for cross-platform atomic CSV updates
    ],
)
