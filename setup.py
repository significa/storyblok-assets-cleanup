import os
import re
from pathlib import Path

from setuptools import setup

long_description = (Path(__file__).parent / 'README.md').read_text()
requirements = (Path(__file__).parent / 'requirements.txt').read_text().split('\n')

version = re.sub(
    r'^v',
    '',
    os.getenv('VERSION', 'v0.0.1')
)

print(f'Publishing version {version}')

setup(
    name='storyblok-assets-cleanup',
    version=version,
    description='Utility to clean unused storyblok assets.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'storyblok-assets-cleanup = storyblok_assets_cleanup:main'
        ],
    },
    license='MIT',
    url='https://github.com/significa/storyblok-assets-cleanup',
    keywords='storyblok',
    author='Significa',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Utilities',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
