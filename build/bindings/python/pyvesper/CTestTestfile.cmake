# CMake generated Testfile for 
# Source directory: C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper
# Build directory: C:/Users/cisco/Desktop/dev/research/VLTAIR/build/bindings/python/pyvesper
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
if(CTEST_CONFIGURATION_TYPE MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
  add_test([=[pyvesper_import]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-c" "import pyvesper; e=pyvesper.Engine(); print('ok')")
  set_tests_properties([=[pyvesper_import]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;46;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
  add_test([=[pyvesper_import]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-c" "import pyvesper; e=pyvesper.Engine(); print('ok')")
  set_tests_properties([=[pyvesper_import]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;46;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Mm][Ii][Nn][Ss][Ii][Zz][Ee][Rr][Ee][Ll])$")
  add_test([=[pyvesper_import]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-c" "import pyvesper; e=pyvesper.Engine(); print('ok')")
  set_tests_properties([=[pyvesper_import]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;46;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ww][Ii][Tt][Hh][Dd][Ee][Bb][Ii][Nn][Ff][Oo])$")
  add_test([=[pyvesper_import]=] "C:/Users/cisco/AppData/Local/Programs/Python/Python312/python.exe" "-c" "import pyvesper; e=pyvesper.Engine(); print('ok')")
  set_tests_properties([=[pyvesper_import]=] PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;46;add_test;C:/Users/cisco/Desktop/dev/research/VLTAIR/bindings/python/pyvesper/CMakeLists.txt;0;")
else()
  add_test([=[pyvesper_import]=] NOT_AVAILABLE)
endif()
subdirs("../../../_deps/pybind11_proj-build")
