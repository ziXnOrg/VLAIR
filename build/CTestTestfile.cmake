# CMake generated Testfile for 
# Source directory: C:/Users/cisco/Desktop/dev/research/VLTAIR
# Build directory: C:/Users/cisco/Desktop/dev/research/VLTAIR/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
if(CTEST_CONFIGURATION_TYPE MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
  add_test([=[python_unit_tests]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-m" "pytest" "-q" "tests/unit")
  set_tests_properties([=[python_unit_tests]=] PROPERTIES  WORKING_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR" _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;25;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
  add_test([=[python_unit_tests]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-m" "pytest" "-q" "tests/unit")
  set_tests_properties([=[python_unit_tests]=] PROPERTIES  WORKING_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR" _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;25;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Mm][Ii][Nn][Ss][Ii][Zz][Ee][Rr][Ee][Ll])$")
  add_test([=[python_unit_tests]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-m" "pytest" "-q" "tests/unit")
  set_tests_properties([=[python_unit_tests]=] PROPERTIES  WORKING_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR" _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;25;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ww][Ii][Tt][Hh][Dd][Ee][Bb][Ii][Nn][Ff][Oo])$")
  add_test([=[python_unit_tests]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-m" "pytest" "-q" "tests/unit")
  set_tests_properties([=[python_unit_tests]=] PROPERTIES  WORKING_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR" _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;25;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/CMakeLists.txt;0;")
else()
  add_test([=[python_unit_tests]=] NOT_AVAILABLE)
endif()
subdirs("Vesper")
subdirs("bindings/python/pyvesper")
