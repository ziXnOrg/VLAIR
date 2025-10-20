# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-src")
  file(MAKE_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-src")
endif()
file(MAKE_DIRECTORY
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-build"
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix"
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/tmp"
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/src/gbench-populate-stamp"
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/src"
  "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/src/gbench-populate-stamp"
)

set(configSubDirs Debug)
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/src/gbench-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "C:/Users/cisco/Desktop/dev/research/VLTAIR/build/_deps/gbench-subbuild/gbench-populate-prefix/src/gbench-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
