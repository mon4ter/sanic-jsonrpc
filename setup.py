from re import search

from setuptools import setup

with open('src/sanic_jsonrpc/__init__.py') as f:
    version = str(search(r"__version__ = '(.*)'", f.read()).group(1))

with open('README.md') as f:
    long_description = f.read()

setup(
    name='sanic-jsonrpc',
    version=version,
    packages=['sanic_jsonrpc'],
    package_dir={'': 'src'},
    install_requires=[
        'Sanic',
        'fashionable>=0.8.5',
        'ujson',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-asyncio'],
    url='https://github.com/mon4ter/sanic-jsonrpc',
    license='MIT',
    author='Dmitry Galkin',
    author_email='mon4ter@gmail.com',
    description='JSON-RPC 2.0 support for Sanic over HTTP and WebSocket',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
