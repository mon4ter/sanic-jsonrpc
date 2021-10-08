from re import search

from setuptools import setup

with open('src/sanic_jsonrpc/__init__.py') as f:
    version = str(search(r"__version__ = '(.*)'", f.read()).group(1))

with open('README.md') as f:
    long_description = f.read()

setup(
    name='sanic-jsonrpc',
    version=version,
    packages=[
        'sanic_jsonrpc',
        'sanic_jsonrpc._middleware',
        'sanic_jsonrpc.jsonrpc',
        'sanic_jsonrpc.models',
    ],
    package_dir={'': 'src'},
    install_requires=[
        "sanic ~= 19.3.1; python_version < '3.6'",
        "sanic ~= 20.12.3; python_version == '3.6'",
        "sanic ~= 21.6.2; python_version >= '3.7'",
        "fashionable ~= 0.12.2",
        "ujson ~= 3.2.0; python_version < '3.6'",
        "ujson ~= 4.1.0; python_version >= '3.6'",
        "websockets ~= 6.0; python_version < '3.6'",
        "websockets ~= 8.1; python_version == '3.6'",
        "websockets ~= 9.1; python_version >= '3.7'",
    ],
    setup_requires=[
        "pytest-runner ~= 5.2; python_version < '3.6'",
        "pytest-runner ~= 5.3.1; python_version >= '3.6'",
    ],
    tests_require=[
        "pytest ~= 6.1.2; python_version < '3.6'",
        "pytest ~= 6.2.4; python_version >= '3.6'",
        "pytest-cov ~= 2.12.1",
        "pytest-sanic ~= 1.1.2; python_version < '3.6'",
        "pytest-sanic ~= 1.7.0; python_version == '3.6'",
        "pytest-sanic ~= 1.8.1; python_version >= '3.7'",
    ],
    url='https://github.com/mon4ter/sanic-jsonrpc',
    license='MIT',
    author='Dmitry Galkin',
    author_email='mon4ter@gmail.com',
    description='JSON-RPC 2.0 support for Sanic over HTTP and WebSocket',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
