cmake_minimum_required(VERSION 3.22)
project(pyvesper LANGUAGES C CXX)

include(FetchContent)

# Python and pybind11
find_package(Python3 REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 QUIET)
if (NOT pybind11_FOUND)
  FetchContent_Declare(
    pybind11_proj
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG        v2.11.1
  )
  FetchContent_MakeAvailable(pybind11_proj)
endif()

set(PYVESPER_SOURCES
  module.cpp
  engine.cpp
)

pybind11_add_module(pyvesper MODULE ${PYVESPER_SOURCES})
target_compile_features(pyvesper PRIVATE cxx_std_20)

# Includes: this dir + Vesper public headers
target_include_directories(pyvesper PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_SOURCE_DIR}/Vesper/include)

# Link to Vesper headers interface (and core later when Engine calls it)
if (TARGET vesper_headers)
  target_link_libraries(pyvesper PRIVATE vesper_headers)
endif()

# Warnings
if (MSVC)
  target_compile_options(pyvesper PRIVATE /W4)
else()
  target_compile_options(pyvesper PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Windows: ensure correct module name (no lib prefix)
set_target_properties(pyvesper PROPERTIES PREFIX "")

# Simple smoke test (ctest): import module and construct Engine
enable_testing()
add_test(
  NAME pyvesper_import
  COMMAND ${Python3_EXECUTABLE} -c "import pyvesper; e=pyvesper.Engine(); print('ok')"
)

# Ensure Python can import the freshly built module
set_tests_properties(pyvesper_import PROPERTIES
  WORKING_DIRECTORY $<TARGET_FILE_DIR:pyvesper>
  ENVIRONMENT "PYTHONPATH=$<TARGET_FILE_DIR:pyvesper>"
)

