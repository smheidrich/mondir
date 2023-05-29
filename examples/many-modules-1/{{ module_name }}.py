{% thisfile for * in modules %}
import sys

__author__ = "{{ module_author }}"
__version__ = "{{ module_version }}"

class {{ module_name|camelcase }}Runner:
  def run(self):
    print("Hello from {{ module_name }}!")
