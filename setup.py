from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='cob-arcgis-geocoder',
      version='0.0.1',
      description='Python geocoder to be used in ETL pipelines',
      url='later',
      author='many',
      author_email='many',
      packages=['cob-arcgis-geocoder'],
zip_safe=False)