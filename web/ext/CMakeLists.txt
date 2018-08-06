cmake_minimum_required(VERSION 3.2.0)

project(sampler)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS 1)

option(ENABLE_JEMALLOC "Link against jemalloc if available" OFF)
set(META_STATIC_UTF ON)
set(BUILD_STATIC_ICU ON)
add_subdirectory(deps/meta EXCLUDE_FROM_ALL)
add_subdirectory(deps/pybind11)

pybind11_add_module(mdmm_sampler src/sampler.cpp)
target_link_libraries(mdmm_sampler PUBLIC meta-stats meta-util)
