cmake_minimum_required(VERSION 3.22)
project(VLTAIR LANGUAGES C CXX)

# Global C++ standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build Vesper core first (optional in CI when Vesper/ is absent)
if (EXISTS "${CMAKE_SOURCE_DIR}/Vesper/CMakeLists.txt")
  add_subdirectory(Vesper)
else()
  message(STATUS "Vesper subdirectory not found; skipping Vesper build")
endif()

# Python bindings (pyvesper)
add_subdirectory(bindings/python/pyvesper)

# PyTest integration via CTest (Batch 1 Python unit tests)
include(CTest)
find_package(Python3 COMPONENTS Interpreter)
if (Python3_Interpreter_FOUND)
  # Detect pytest availability
  execute_process(
    COMMAND ${Python3_EXECUTABLE} -c "import sys, importlib.util as u; sys.exit(0 if u.find_spec('pytest') else 1)"
    RESULT_VARIABLE HAVE_PYTEST
  )
  if (HAVE_PYTEST EQUAL 0)
    add_test(
      NAME python_unit_tests
      COMMAND ${Python3_EXECUTABLE} -m pytest -q tests/unit
      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    )
    # E2E dispatch (integration) subset if present
    add_test(
      NAME python_integration_tests
      COMMAND ${Python3_EXECUTABLE} -m pytest -q tests/integration
      WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    )
  else()
    message(STATUS "pytest not found; skipping python_unit_tests registration")
  endif()
endif()


