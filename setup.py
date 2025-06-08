from setuptools import setup, find_packages

setup(
    name="namebot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "pymongo>=4.0.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A library for identifying anime characters from images",
    keywords="anime, character, identification, telegram",
    url="https://github.com/yourusername/namebot",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
)
