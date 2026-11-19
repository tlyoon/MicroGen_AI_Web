"""Local MicroGen tests package.

Prevents an unrelated site-packages tests package from shadowing
this repository's test helpers on standard Python installations.
"""

# Registry-verified source-only bootstrap; permit local legacy fixture imports
# from both package-style and discovery-style unittest invocations.
from selenium_pipeline.windows_test_helper_import_recovery import bootstrap
bootstrap(__file__)
