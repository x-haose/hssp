from pathlib import Path
from setuptools import setup, find_packages


def read(file_name):
    with open(Path(__file__).parent / file_name, mode="r", encoding="utf-8") as f:
        return f.read()


setup(
    name='hssp',
    version='0.3.1',
    author='昊色居士',
    author_email='xhrtxh@gmail.com',
    description='一个简单快速的异步爬虫框架',
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    packages=find_packages(),
    url='https://github.com/x-haose/hssp',
    license='MIT',
    classifiers=[
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: BSD",
        "Operating System :: Microsoft :: Windows",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "aiohttp==3.7.4.post0",
        "parsel==1.6.0",
        "loguru==0.5.3",
        "tenacity==7.0.0",
        "furl==2.1.2",
        "httpx==0.18.2",
        "openpyxl>=3.0.9",
        "aiomysql>=0.0.22",
        "fake-useragent>=0.1.11",
        "pyppeteer>=0.0.25",
        "pandas>=0.25.3",
        "orjson>=3.6.1",
        "aiofiles>=0.8.0",
        "uvloop; sys_platform != 'win32' and implementation_name == 'cpython'"
    ]
)
