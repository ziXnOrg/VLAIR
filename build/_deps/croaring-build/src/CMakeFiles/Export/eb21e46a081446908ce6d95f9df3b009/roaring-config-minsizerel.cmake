#----------------------------------------------------------------
# Generated CMake target import file for configuration "MinSizeRel".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "roaring::roaring" for configuration "MinSizeRel"
set_property(TARGET roaring::roaring APPEND PROPERTY IMPORTED_CONFIGURATIONS MINSIZEREL)
set_target_properties(roaring::roaring PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_MINSIZEREL "C"
  IMPORTED_LOCATION_MINSIZEREL "${_IMPORT_PREFIX}/lib/roaring.lib"
  )

list(APPEND _cmake_import_check_targets roaring::roaring )
list(APPEND _cmake_import_check_files_for_roaring::roaring "${_IMPORT_PREFIX}/lib/roaring.lib" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
