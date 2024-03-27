import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='openimis-be-grievance_social_protection',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    license='GNU AGPL v3',
    description='Fork of the openIMIS Backend Grievance reference module.',
    # long_description=README,
    url='https://soldevelo.com/',
    author='SolDevelo',
    author_email='jdolkowski@soldevelo.com',
    install_requires=[
        'django',
        'django-db-signals',
        'djangorestframework',
        'openimis-be-core',
        'openimis-be-insuree',
        'openimis-be-report',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.1',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
