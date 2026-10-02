from setuptools import find_packages, setup


package_name = "wheelchair_memory"


setup(
    name=package_name,
    version="0.0.0",

    packages=find_packages(
        exclude=["test"]
    ),

    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
    ],

    install_requires=[
        "setuptools",
    ],

    zip_safe=True,

    tests_require=['pytest'],

    maintainer="iratxefagoaga",

    maintainer_email="iratxefagoaga@gmail.com",

    description=(
        "ROS 2 interface for the TFM "
        "robot memory system"
    ),

    license="Apache-2.0",

    entry_points={
        'console_scripts': [
            'memory_node = wheelchair_memory.memory_node:main',
            'navigation_memory_node = wheelchair_memory.navigation_memory_node:main',
            'navigation_adapter = wheelchair_memory.navigation_adapter:main',
        ],
    },
)
