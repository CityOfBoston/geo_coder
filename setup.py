from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='cob_arcgis_geocoder',
      version='0.0.2',
      description='Python geocoder to be used in ETL pipelines',
      url='later',
      author='many',
      author_email='many',
      packages=['cob_arcgis_geocoder'],
zip_safe=False)

setup(name='cob_arcgis_reverse_geocoder',
      version='0.0.1',
      description='Python reverse geocoder to be used in ETL pipelines',
      url='later',
      author='Brian McMahon',
      author_email='many',
      packages=['cob_arcgis_reverse_geocoder'],
zip_safe=False)